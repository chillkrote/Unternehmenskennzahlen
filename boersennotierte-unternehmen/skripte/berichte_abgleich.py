"""Gleicht die Yahoo-Abschlusszahlen mit den Geschäftsberichten im Repo ab und zieht Rohdaten aus den Berichten.

Je Bericht (PDF -> Text mit pdftotext -layout):
  1. Abgleich: Kommt der Yahoo-Wert (Umsatz, Ergebnis, EBIT, Bilanzsumme, Eigenkapital, operativer Cashflow;
     jedes Jahr, das Yahoo kennt) als Zahl in einer Zeile mit passender Bezeichnung vor? Einheit (EUR, Tsd., Mio., Mrd.)
     wird durchprobiert, Toleranz 0,5 %. Ergebnis: bestätigt (mit Jahr, Seite) oder nicht bestätigt.
  2. Berichtswert-Kandidat: erste Tabellenzeile mit der Bezeichnung und Zahlen, dazu die vermutete Einheit und Seite.
  3. Mitarbeiter und Dividende je Aktie: Kandidaten aus dem Text (häufigste Werte).
  4. Segmente: Rohzeilen der Segmenttabelle (Anhang) mit Seitenzahl und Kopfzeile, unbereinigt.
Schreibt rohdaten/berichte_abgleich.json. Die Texte werden nicht abgelegt.

Aufruf: python3 berichte_abgleich.py [unternehmen_id ...]
"""
import csv
import json
import re
import subprocess
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HIER = Path(__file__).resolve().parent
BASIS = HIER.parent
sys.path.insert(0, str(HIER))
from build import posten  # noqa: E402

METRIKEN = {
    "Umsatz": dict(label=r"umsatzerl|^\s*umsatz\b|revenues?\b|net sales|^\s*sales\b|gesamtleistung|total revenue",
                   yahoo=("guv", ["Total Revenue", "Operating Revenue"])),
    "Ergebnis Aktionäre": dict(label=r"konzernergebnis|jahres(über|ueber)schuss|net income|profit for the (year|period)|"
                                     r"ergebnis nach steuern|periodenergebnis|konzern-?jahresergebnis|ergebnis der aktion|"
                                     r"earnings after tax|net profit",
                               yahoo=("guv", ["Net Income Common Stockholders", "Net Income"])),
    "EBIT": dict(label=r"\bebit\b|betriebsergebnis|operating (income|profit|result)|operatives ergebnis",
                 yahoo=("guv", ["EBIT", "Operating Income"])),
    "Bilanzsumme": dict(label=r"bilanzsumme|summe (der )?aktiva|total assets|summe vermögen|gesamtvermögen",
                        yahoo=("bilanz", ["Total Assets"])),
    "Eigenkapital": dict(label=r"eigenkapital|total equity|shareholders.? equity|equity attributable",
                         yahoo=("bilanz", ["Total Equity Gross Minority Interest", "Common Stock Equity", "Stockholders Equity"])),
    "Operativer Cashflow": dict(label=r"cash ?flow aus (der )?laufenden|cash ?flow aus betriebs|operating cash ?flow|"
                                      r"cash ?flows? from operating|mittelzufluss aus (der )?laufenden|net cash from operating",
                                yahoo=("cashflow", ["Operating Cash Flow"])),
}
ZAHL = re.compile(r"\(?[-–−]?\d{1,3}(?:[.,\s  ]\d{3})+(?:[.,]\d+)?\)?|\(?[-–−]?\d+(?:[.,]\d+)?\)?")
EINHEITEN = [(1, "EUR"), (1e3, "Tsd."), (1e6, "Mio."), (1e9, "Mrd.")]
EINHEIT_TEXT = re.compile(r"(in|€|eur|usd|chf|\$)\s*(mio|million|millions|tsd|teur|t€|thousand|tausend|mrd|billion)|"
                          r"\b(teur|t€|tchf|tusd|mio\.? ?€|€ ?mio|€ ?million|in millions|in thousands|in mio|in tsd)", re.I)
SEG_KOPF = re.compile(r"segmentberichterstattung|segment reporting|segmentinformation|angaben zu den segmenten|"
                      r"informationen zu den geschäftssegmenten|segmentierung|operating segments|geschäftssegmente|"
                      r"segment information|segmentbericht", re.I)
SEG_ZEILE = re.compile(r"umsatz|revenue|sales|ebit|ergebnis|segmentergebnis|vermögen|assets|investition|capex|mitarbeiter|"
                       r"employees|abschreibung|depreciation|schulden|liabilities|auftrag|order", re.I)


def zahlen(zeile):
    """Alle Zahlen einer Zeile als Liste von Rohtext -> mögliche Werte (Locale-agnostisch)."""
    out = []
    for m in ZAHL.finditer(zeile):
        t = m.group(0).strip()
        out.append(t)
    return out


def werte(token):
    """Mögliche Zahlenwerte eines Tokens (deutsch/englisch), ohne Vorzeichen."""
    t = re.sub(r"[()\s  –−-]", "", token)
    if not t:
        return []
    cand = set()
    seps = [c for c in t if c in ".,"]
    if not seps:
        cand.add(float(t))
        return list(cand)
    # Variante A: letztes Trennzeichen ist Dezimaltrenner, alle anderen Tausender
    letzter = max(t.rfind("."), t.rfind(","))
    a = t[:letzter].replace(".", "").replace(",", "") + "." + t[letzter + 1:]
    # Variante B: alle Trennzeichen sind Tausender
    b = t.replace(".", "").replace(",", "")
    for v in (a, b):
        try:
            cand.add(float(v))
        except ValueError:
            pass
    return list(cand)


def passt(token, ziel, zeile=""):
    """Passt eine Zahl im Text auf den Zielwert (volle Einheiten)? Gibt die Einheit zurück oder None."""
    z = abs(ziel)
    if z == 0:
        return None
    if re.fullmatch(r"\(?[-–−]?(19[89]\d|20[0-3]\d)\)?", token.strip()):
        return None  # Jahreszahl
    mrd = re.search(r"mrd|billion|milliard", zeile, re.I)
    for v in werte(token):
        for f, name in EINHEITEN:
            if f == 1e9 and not mrd:
                continue
            x = v * f
            if x == 0:
                continue
            tol = 0.005 if v >= 100 else 0.03  # kurze Zahlen (19,7 Mrd.) sind gerundet
            if abs(x - z) / z <= tol:
                return name
    return None


def seiten_text(pdf):
    r = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, errors="replace", timeout=300)
    return r.stdout.split("\f")


def einheit_vor(zeilen, i):
    for k in range(i, max(-1, i - 60), -1):
        m = EINHEIT_TEXT.search(zeilen[k])
        if m:
            return m.group(0).strip()
    return None


def pruefe(pdf, yahoo):
    seiten = seiten_text(pdf)
    out = {"seiten": len(seiten), "abgleich": {}, "segmente": []}
    labels = {k: re.compile(v["label"], re.I) for k, v in METRIKEN.items()}
    ziele = {}
    for k, v in METRIKEN.items():
        tab = yahoo.get(v["yahoo"][0]) or {}
        ziele[k] = {j: posten(tab, j, v["yahoo"][1]) for j in sorted(tab, reverse=True)[:4]}
        ziele[k] = {j: w for j, w in ziele[k].items() if w}
    erste = {}
    mitarb, dividende = Counter(), Counter()
    for pn, text in enumerate(seiten, 1):
        zeilen = text.split("\n")
        for i, z in enumerate(zeilen):
            zl = z.strip()
            if not zl or len(zl) > 400:
                continue
            toks = zahlen(zl)
            if not toks:
                continue
            for k, lab in labels.items():
                if not lab.search(zl):
                    continue
                if k not in out["abgleich"] or not out["abgleich"][k].get("bestaetigt"):
                    for j, w in ziele[k].items():
                        for t in toks:
                            e = passt(t, w, zl)
                            if e:
                                out["abgleich"][k] = {"bestaetigt": True, "jahr": j[:4], "seite": pn, "einheit": e, "zeile": zl[:160]}
                                break
                        if out["abgleich"].get(k, {}).get("bestaetigt"):
                            break
                # Kandidat: Tabellenzeile, die mit der Bezeichnung beginnt und mindestens zwei Zahlen hat
                if k not in erste and len(toks) >= 2 and lab.match(zl.lower()) and pn > 2:
                    erste[k] = {"seite": pn, "zeile": re.sub(r"\s{2,}", "  ", zl)[:200], "einheit": einheit_vor(zeilen, i)}
            low = zl.lower()
            if re.search(r"mitarbeit|beschäftigte|arbeitnehmer|employees|headcount|\bfte\b|vollzeit", low):
                for t in toks:
                    for v in werte(t):
                        if v == int(v) and 20 <= v <= 1_000_000 and not (1990 <= v <= 2035):
                            mitarb[int(v)] += 1
            if re.search(r"dividende|dividend", low) and re.search(r"je aktie|pro aktie|per share|je stückaktie", low):
                for t in toks:
                    for v in werte(t):
                        if 0.005 <= v <= 100 and v != int(v) and not (1990 <= v <= 2035):
                            dividende[round(v, 4)] += 1
    for k in METRIKEN:
        a = out["abgleich"].get(k) or {"bestaetigt": False}
        a["yahoo"] = {j[:4]: w for j, w in ziele[k].items()}
        if k in erste:
            a["kandidat"] = erste[k]
        out["abgleich"][k] = a
    out["mitarbeiter_kandidaten"] = [[n, c] for n, c in mitarb.most_common(4)]
    out["dividende_kandidaten"] = [[n, c] for n, c in dividende.most_common(4)]
    # Segmente: Anhangseiten mit Segment-Überschrift, Zeilen mit Bezeichnung und >= 2 Zahlen
    start = len(seiten) // 3
    gefunden = 0
    for pn in range(start, len(seiten) + 1):
        text = seiten[pn - 1]
        zeilen = text.split("\n")
        kopf_idx = next((i for i, z in enumerate(zeilen[:25]) if SEG_KOPF.search(z)), None)
        if kopf_idx is None:
            continue
        zeilen_ok = []
        for i, z in enumerate(zeilen):
            zl = z.strip()
            if not zl or len(zl) > 300:
                continue
            toks = zahlen(zl)
            if len(toks) >= 2 and SEG_ZEILE.search(zl[:60]):
                zeilen_ok.append(re.sub(r"\s{2,}", "  ", zl)[:220])
        if len(zeilen_ok) >= 3:
            kopf = [re.sub(r"\s{2,}", "  ", z.strip())[:200] for z in zeilen[kopf_idx:kopf_idx + 6] if z.strip()]
            out["segmente"].append({"seite": pn, "ueberschrift": kopf[:4], "zeilen": zeilen_ok[:40], "einheit": einheit_vor(zeilen, min(len(zeilen) - 1, kopf_idx + 6))})
            gefunden += 1
            if gefunden >= 3:
                break
    return out


def job(arg):
    uid, pdf, yahoo = arg
    try:
        return uid, str(pdf), pruefe(pdf, yahoo)
    except Exception as e:  # defekte PDFs nicht den Lauf abbrechen lassen
        return uid, str(pdf), {"fehler": f"{type(e).__name__}: {e}"}


def main():
    nur = set(a for a in sys.argv[1:] if not a.startswith("--"))
    uni = {u["unternehmen_id"]: u for u in csv.DictReader(open(BASIS / "universum" / "universum.csv", encoding="utf-8-sig"), delimiter=";")}
    aufgaben = []
    for p in BASIS.glob("*/dokumente/index.csv"):
        for z in csv.DictReader(open(p, encoding="utf-8-sig"), delimiter=";"):
            uid = z["unternehmen_id"]
            if uid not in uni or (nur and uid not in nur):
                continue
            yp = BASIS / "rohdaten" / "yahoo" / f"{uni[uid]['isin_haupt']}.json"
            yahoo = json.loads(yp.read_text(encoding="utf-8")) if yp.exists() else {}
            aufgaben.append((uid, p.parent.parent / z["datei"], {k: yahoo.get(k) for k in ("guv", "bilanz", "cashflow")}))
    ziel = BASIS / "rohdaten" / "berichte_abgleich.json"
    erg = json.loads(ziel.read_text(encoding="utf-8")) if ziel.exists() else {}
    with ProcessPoolExecutor(6) as ex:
        for uid, pdf, r in ex.map(job, aufgaben):
            erg.setdefault(uid, {})[Path(pdf).name] = r
            a = r.get("abgleich", {})
            print(uid, "|", " ".join(f"{k[:4]}={'J' if v.get('bestaetigt') else 'n'}" for k, v in a.items()), r.get("fehler", ""), flush=True)
    ziel.write_text(json.dumps(erg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
