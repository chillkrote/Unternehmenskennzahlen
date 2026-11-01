#!/usr/bin/env python3
"""Liest die ausgefüllte Importvorlage, prüft sie und übernimmt sie (optional) ins Repo.

  python3 vorlagen/importieren.py Datei.xlsx              nur prüfen, Bericht ausgeben (ändert nichts)
  python3 vorlagen/importieren.py Datei.xlsx --schreiben  neue Unternehmen über stammdaten/ids.py registrieren und
                                                           Kennzahlen nach import/daten/<ID>.json schreiben
Exit-Code 1, wenn Fehler gefunden wurden (dann wird auch mit --schreiben nichts geschrieben).
Prüfungen: Pflichtfelder, Listenwerte, ISIN-Prüfziffer, LEI-Prüfsumme, Datum/Geschäftsjahr, Einheit je Kennzahltyp,
Quelle+URL je Wert, doppelte Zeilen, Dubletten gegen den Bestand (ISIN/LEI/Name), Bilanzprobe Aktiva = Passiva,
Bilanzsumme = Eigenkapital + Verbindlichkeiten, Anlage- + Umlaufvermögen.
"""
import argparse
import csv
import datetime as dt
import difflib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HIER = Path(__file__).resolve().parent
REPO = HIER.parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(REPO / "stammdaten"))
import schema as S  # noqa: E402

try:
    import ids as IDS  # noqa: E402
except Exception:  # pragma: no cover
    IDS = None

AUSGABE = REPO / "import" / "daten"
LAND_ISO = {"DE": "Germany", "AT": "Austria", "CH": "Switzerland", "LI": "Liechtenstein", "LU": "Luxembourg",
            "NL": "Netherlands", "BE": "Belgium", "FR": "France", "GB": "UK", "IE": "Ireland", "IT": "Italy",
            "ES": "Spain", "PT": "Portugal", "GR": "Greece", "DK": "Denmark", "SE": "Sweden", "NO": "Norway",
            "FI": "Finland", "PL": "Poland", "CZ": "Czechia", "US": "USA", "JO": "Jordan"}
GLEICH_TOL = 0.005
SUMME_TOL = 0.01
GROB_TOL = 0.03


class Bericht:
    def __init__(self):
        self.fehler, self.warnungen, self.info = [], [], []

    def f(self, ort, text):
        self.fehler.append(f"{ort}: {text}")

    def w(self, ort, text):
        self.warnungen.append(f"{ort}: {text}")


def lei_ok(lei):
    if not re.fullmatch(r"[A-Z0-9]{18}[0-9]{2}", lei or ""):
        return False
    return int("".join(str(int(c, 36)) for c in lei)) % 97 == 1


def zahl(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(" ", "").replace(" ", "")
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", s):
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d+,\d+", s):
        s = s.replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", s):
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def datum(v):
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    s = str(v or "").strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def text(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def blatt_lesen(wb, name, spalten, b):
    if name not in wb.sheetnames:
        b.f(name, "Blatt fehlt")
        return []
    ws = wb[name]
    kopf = [text(c.value).rstrip(" *") for c in ws[1]]
    erwartet = [s[0] for s in spalten]
    fehlend = [e for e in erwartet if e not in kopf]
    if fehlend:
        b.f(name, f"Spalten fehlen oder umbenannt: {', '.join(fehlend)}")
        return []
    idx = {n: kopf.index(n) for n in erwartet}
    zeilen = []
    for nr, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
        d = {n: row[i] if i < len(row) else None for n, i in idx.items()}
        if all(text(v) == "" for v in d.values()):
            continue
        d["_zeile"] = nr
        zeilen.append(d)
    return zeilen


def ist_beispiel(name):
    return text(name).startswith(S.BEISPIEL)


def pruefe_unternehmen(zeilen, reg, b):
    ok, namen, isins, leis, schl = {}, {}, {}, {}, {}
    pflicht = [s[0] for s in S.UNTERNEHMEN if s[1]]
    for z in zeilen:
        ort = f"Unternehmen Z{z['_zeile']}"
        name = text(z["Name"])
        if ist_beispiel(name):
            continue
        for p in pflicht:
            if text(z[p]) == "":
                b.f(ort, f"Pflichtfeld {p} leer ({name or 'ohne Name'})")
        if not name:
            continue
        ort = f"Unternehmen Z{z['_zeile']} ({name})"
        if name in namen:
            b.f(ort, f"Name doppelt (auch Z{namen[name]})")
        namen[name] = z["_zeile"]
        k = IDS.schluessel(name) if IDS else name.lower()
        if k in schl and schl[k] != name:
            b.f(ort, f"Gleicher Name wie '{schl[k]}' (nur andere Schreibweise)")
        schl[k] = name
        land = text(z["Land"])
        land = LAND_ISO.get(land.upper(), land)
        if land and land not in S.LAENDER:
            b.f(ort, f"Land '{land}' nicht in der Liste")
        for feld, liste in (("Börsennotiert", S.JA_NEIN), ("Bank", S.JA_NEIN), ("Branche", S.BRANCHEN)):
            v = text(z[feld]).lower() if feld != "Branche" else text(z[feld])
            if v and v not in liste:
                b.f(ort, f"{feld} '{v}' nicht erlaubt ({', '.join(liste[:4])}...)")
        liste_isin = [i.strip().upper() for i in text(z["ISIN"]).split("|") if i.strip()]
        for i in liste_isin:
            if IDS and not IDS.isin_pruefsumme_ok(i):
                b.f(ort, f"ISIN {i} hat falsche Form oder Prüfziffer")
            if i in isins:
                b.f(ort, f"ISIN {i} steht auch bei '{isins[i]}'")
            isins[i] = name
        if text(z["Börsennotiert"]).lower() == "ja" and not liste_isin:
            b.w(ort, "börsennotiert, aber keine ISIN angegeben")
        if text(z["Börsennotiert"]).lower() == "nein" and liste_isin:
            b.w(ort, "als nicht börsennotiert markiert, aber ISIN angegeben")
        lei = text(z["LEI"]).upper()
        if lei:
            if not lei_ok(lei):
                b.f(ort, f"LEI {lei} hat falsche Länge oder Prüfsumme")
            if lei in leis:
                b.f(ort, f"LEI {lei} steht auch bei '{leis[lei]}'")
            leis[lei] = name
        web = text(z["Website"])
        if web and not web.lower().startswith("http"):
            b.w(ort, "Website sollte mit https:// beginnen")
        if not text(z["Quelle Stammdaten (URL)"]).lower().startswith("http") and text(z["Quelle Stammdaten (URL)"]):
            b.f(ort, "Quelle Stammdaten (URL) ist kein Link")
        # Abgleich Bestand
        treffer = {}
        if reg:
            for i in liste_isin:
                if i in reg.nach_isin:
                    treffer[f"ISIN {i}"] = reg.nach_isin[i]
            if lei:
                for uid, r in reg.unternehmen.items():
                    if r.get("lei") and r["lei"].upper() == lei:
                        treffer[f"LEI {lei}"] = uid
            u = reg.aufloesen(name)
            if u:
                treffer["Name"] = u
        uids = set(treffer.values())
        bestand = None
        if len(uids) > 1:
            b.f(ort, "Widerspruch zum Bestand: " + "; ".join(f"{k} → {v}" for k, v in treffer.items()))
        elif uids:
            bestand = next(iter(uids))
            b.info.append(f"{name}: bereits im Bestand als {bestand} ({reg.name(bestand)}) – Stammdaten werden nur ergänzt, keine neue ID")
        elif reg:
            ks = IDS.schluessel(name)
            for uid, r in reg.unternehmen.items():
                n2 = IDS.schluessel(r["name"])
                if n2 and (difflib.SequenceMatcher(None, ks, n2).ratio() >= 0.9):
                    b.w(ort, f"ähnlicher Name im Bestand: {r['name']} ({uid}); bitte prüfen, ob dasselbe Unternehmen")
                    break
        ok[name] = {"zeile": z, "isins": liste_isin, "lei": lei, "land": land, "bestand": bestand}
    return ok


def pruefe_kennzahlen(zeilen, unt, b):
    werte = {}
    gesehen = {}
    heute = dt.date.today()
    for z in zeilen:
        name = text(z["Unternehmen"])
        if ist_beispiel(name):
            continue
        ort = f"Kennzahlen Z{z['_zeile']}"
        for p in [s[0] for s in S.KENNZAHLEN_SPALTEN if s[1]]:
            if text(z[p]) == "":
                b.f(ort, f"Pflichtfeld {p} leer")
        if name not in unt:
            b.f(ort, f"Unternehmen '{name}' fehlt im Blatt Unternehmen")
            continue
        bez = text(z["Kennzahl"])
        if bez not in S.BEZ2CODE:
            b.f(ort, f"Kennzahl '{bez}' nicht in der Kennzahlenliste")
            continue
        code = S.BEZ2CODE[bez]
        _, _, bereich, typ, nur_bank, _ = S.CODE2K[code]
        wert = zahl(z["Wert"])
        if text(z["Wert"]) != "" and wert is None:
            b.f(ort, f"Wert '{text(z['Wert'])}' ist keine Zahl")
            continue
        if wert is None:
            continue
        try:
            gj = int(zahl(z["Geschäftsjahr"]))
        except (TypeError, ValueError):
            b.f(ort, "Geschäftsjahr ist keine Jahreszahl")
            continue
        if not 2000 <= gj <= heute.year + 1:
            b.f(ort, f"Geschäftsjahr {gj} außerhalb 2000..{heute.year + 1}")
        sd = datum(z["Stichtag"])
        if not sd:
            b.f(ort, "Stichtag ist kein Datum (TT.MM.JJJJ)")
        else:
            if code not in ("MARKTKAPITALISIERUNG", "KURS") and sd.year not in (gj, gj + 1):
                b.f(ort, f"Stichtag {sd:%d.%m.%Y} passt nicht zu Geschäftsjahr {gj}")
            if sd > heute:
                b.f(ort, "Stichtag liegt in der Zukunft (keine Prognosen)")
        if text(z["Rechnungslegung"]) not in S.RECHNUNGSLEGUNG:
            b.f(ort, f"Rechnungslegung '{text(z['Rechnungslegung'])}' nicht erlaubt")
        einheit = text(z["Einheit"])
        waehrung = text(z["Währung"]).upper()
        if einheit not in S.EINHEITEN:
            b.f(ort, f"Einheit '{einheit}' nicht erlaubt")
            continue
        if typ == "Geld" and einheit in ("Prozent", "Anzahl"):
            b.f(ort, f"{bez}: Einheit muss absolut/Tausend/Millionen/Milliarden sein")
        if typ == "JeAktie" and einheit != "absolut":
            b.f(ort, f"{bez}: Einheit muss absolut sein")
        if typ == "Prozent" and einheit != "Prozent":
            b.f(ort, f"{bez}: Einheit muss Prozent sein")
        if typ == "Anzahl" and einheit in ("Prozent", "Milliarden"):
            b.f(ort, f"{bez}: Einheit muss Anzahl/absolut/Tausend/Millionen sein")
        if typ in ("Geld", "JeAktie") and waehrung not in S.WAEHRUNGEN:
            b.f(ort, f"Währung '{waehrung}' nicht in der Liste")
        if not text(z["URL"]).lower().startswith("http"):
            b.f(ort, "URL fehlt oder ist kein Link")
        if nur_bank and unt[name]["zeile"]["Bank"] and text(unt[name]["zeile"]["Bank"]).lower() != "ja":
            b.w(ort, f"{bez} nur für Banken vorgesehen, Unternehmen ist keine Bank")
        if typ == "Anzahl" and (wert < 0 or (code == "MITARBEITER" and wert != int(wert))):
            b.f(ort, f"{bez}: Anzahl muss eine nichtnegative ganze Zahl sein")
        if code in ("MARKTKAPITALISIERUNG", "AKTIEN", "KURS", "BILANZSUMME", "SUMME_AKTIVA", "SUMME_PASSIVA") and wert <= 0:
            b.f(ort, f"{bez} muss größer als 0 sein")
        if typ == "Prozent" and not -100 <= wert <= 100:
            b.f(ort, f"{bez}: {wert} außerhalb -100..100 Prozent (Prozentzahl, nicht Anteil)")
        schluessel = (name, gj, code)
        if schluessel in gesehen:
            b.f(ort, f"doppelt: {bez} {gj} (auch Z{gesehen[schluessel]})")
            continue
        gesehen[schluessel] = z["_zeile"]
        absolut = wert * S.FAKTOR[einheit] if typ in ("Geld", "Anzahl") else wert
        werte[schluessel] = {
            "geschaeftsjahr": gj, "stichtag": sd.isoformat() if sd else None, "rechnungslegung": text(z["Rechnungslegung"]),
            "waehrung": waehrung if typ in ("Geld", "JeAktie") else None, "kennzahl": bez, "code": code, "bereich": bereich,
            "wert": absolut, "eingabe_wert": wert, "eingabe_einheit": einheit, "quelle": text(z["Quelle"]),
            "url": text(z["URL"]), "seite": text(z["Seite"]), "hinweis": text(z["Hinweis"]), "zeile": z["_zeile"]}
    return werte


def bilanzprobe(werte, b):
    je = defaultdict(dict)
    for (name, gj, code), w in werte.items():
        je[(name, gj)][code] = w
    for (name, gj), d in sorted(je.items()):
        ort = f"Bilanzprobe {name} GJ{gj}"
        waehr = {w["waehrung"] for c, w in d.items() if S.CODE2K[c][2] == "Bilanz"}
        if len(waehr) > 1:
            b.f(ort, f"Bilanzposten in mehreren Währungen: {', '.join(sorted(waehr))}")
            continue
        if len({w["rechnungslegung"] for w in d.values()}) > 1:
            b.w(ort, "mehrere Rechnungslegungsarten im selben Jahr")
        v = lambda c: d[c]["wert"] if c in d else None  # noqa: E731
        a, p = v("SUMME_AKTIVA"), v("SUMME_PASSIVA")
        bs = v("BILANZSUMME")
        if a and p and abs(a - p) / max(a, p) > GLEICH_TOL:
            b.f(ort, f"Aktiva {a:,.0f} ≠ Passiva {p:,.0f} (Abweichung {abs(a - p) / max(a, p):.2%})")
        for seite, x in (("Aktiva", a), ("Passiva", p)):
            if bs and x and abs(bs - x) / max(bs, x) > GLEICH_TOL:
                b.f(ort, f"Bilanzsumme {bs:,.0f} ≠ Summe {seite} {x:,.0f}")
        ek, vb = v("EIGENKAPITAL"), v("VERBINDLICHKEITEN")
        if bs and ek is not None and vb is not None and abs(ek + vb - bs) / bs > SUMME_TOL:
            b.f(ort, f"Eigenkapital + Verbindlichkeiten = {ek + vb:,.0f} ≠ Bilanzsumme {bs:,.0f} "
                     f"(Abweichung {abs(ek + vb - bs) / bs:.2%}; Rückstellungen in Verbindlichkeiten gesamt enthalten?)")
        av, uv = v("ANLAGEVERMOEGEN"), v("UMLAUFVERMOEGEN")
        if bs and av is not None and uv is not None and abs(av + uv - bs) / bs > GROB_TOL:
            b.w(ort, f"Anlage- + Umlaufvermögen = {av + uv:,.0f} weicht {abs(av + uv - bs) / bs:.1%} von der Bilanzsumme ab (Rechnungsabgrenzung? sonst prüfen)")
        if bs and ek is not None and ek > bs * 1.0001:
            b.w(ort, "Eigenkapital größer als Bilanzsumme (negatives Fremdkapital)")
        if bs and v("LIQUIDE_MITTEL") and v("LIQUIDE_MITTEL") > bs:
            b.f(ort, "Liquide Mittel größer als Bilanzsumme")
        if not bs and not (a and p):
            b.info.append(f"{name} GJ{gj}: keine Bilanzsumme, Bilanzprobe nicht möglich")


def pruefe_quellen(zeilen, unt, b):
    out = []
    for z in zeilen:
        name = text(z["Unternehmen"])
        if ist_beispiel(name):
            continue
        ort = f"Quellen Z{z['_zeile']}"
        for p in [s[0] for s in S.QUELLEN_SPALTEN if s[1]]:
            if text(z[p]) == "":
                b.f(ort, f"Pflichtfeld {p} leer")
        if name not in unt:
            b.f(ort, f"Unternehmen '{name}' fehlt im Blatt Unternehmen")
        if text(z["Dokumentart"]) and text(z["Dokumentart"]) not in S.DOKUMENTARTEN:
            b.f(ort, f"Dokumentart '{text(z['Dokumentart'])}' nicht erlaubt")
        if text(z["URL"]) and not text(z["URL"]).lower().startswith("http"):
            b.f(ort, "URL ist kein Link")
        d = datum(z["Abrufdatum"])
        if text(z["Abrufdatum"]) and not d:
            b.f(ort, "Abrufdatum ist kein Datum")
        out.append({"unternehmen": name, "dokumentart": text(z["Dokumentart"]), "geschaeftsjahr": text(z["Geschäftsjahr"]),
                    "titel": text(z["Titel"]), "url": text(z["URL"]), "abruf": d.isoformat() if d else "",
                    "sprache": text(z["Sprache"]), "hinweis": text(z["Hinweis"])})
    return out


def laden_und_pruefen(pfad):
    from openpyxl import load_workbook
    b = Bericht()
    wb = load_workbook(pfad, data_only=True)
    reg = IDS.lade() if IDS else None
    uz = blatt_lesen(wb, "Unternehmen", S.UNTERNEHMEN, b)
    kz = blatt_lesen(wb, "Kennzahlen", S.KENNZAHLEN_SPALTEN, b)
    qz = blatt_lesen(wb, "Quellen-Dokumente", S.QUELLEN_SPALTEN, b)
    unt = pruefe_unternehmen(uz, reg, b)
    werte = pruefe_kennzahlen(kz, unt, b)
    bilanzprobe(werte, b)
    quellen = pruefe_quellen(qz, unt, b)
    for name in unt:
        if not any(k[0] == name for k in werte):
            b.w(f"Unternehmen {name}", "keine Kennzahlen im Blatt Kennzahlen")
    return b, reg, unt, werte, quellen


def schreiben(reg, unt, werte, quellen, quelle_datei):
    AUSGABE.mkdir(parents=True, exist_ok=True)
    zuordnung = {}
    for name, u in unt.items():
        z = u["zeile"]
        felder = dict(rechtsform=text(z["Rechtsform"]), sitz=text(z["Sitz"]), land=u["land"], lei=u["lei"],
                      ticker=text(z["Ticker"]), gruppe="", hinweis=text(z["Beschreibung"]), herkunft="Importvorlage")
        if u["bestand"]:
            uid = u["bestand"]
            reg.aktualisieren(uid, weitere_isins="|".join(u["isins"]),
                              **{k: v for k, v in felder.items() if v and k not in ("hinweis", "herkunft")})
        else:
            haupt = u["isins"][0] if u["isins"] else ""
            uid = reg.registrieren(name=name, branche=text(z["Branche"]), isin=haupt, weitere_isins=u["isins"][1:],
                                   status="börsennotiert" if text(z["Börsennotiert"]).lower() == "ja" else "nicht börsennotiert",
                                   **felder)
        zuordnung[name] = uid
    reg.speichern()
    heute = dt.date.today().isoformat()
    for name, uid in zuordnung.items():
        pfad = AUSGABE / f"{uid}.json"
        alt = json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else {"unternehmen_id": uid, "eintraege": [], "quellen": []}
        eintraege = {(e["geschaeftsjahr"], e["code"]): e for e in alt["eintraege"]}
        for (n, gj, code), w in werte.items():
            if n == name:
                w = {k: v for k, v in w.items() if k != "zeile"}
                eintraege[(gj, code)] = dict(w, importdatei=quelle_datei, importdatum=heute)
        alt["name"] = name
        alt["eintraege"] = [eintraege[k] for k in sorted(eintraege)]
        urls = {q["url"] for q in alt["quellen"]}
        alt["quellen"] += [q for q in quellen if q["unternehmen"] == name and q["url"] not in urls]
        pfad.write_text(json.dumps(alt, ensure_ascii=False, indent=1), encoding="utf-8")
    return zuordnung


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("datei")
    ap.add_argument("--schreiben", action="store_true", help="Unternehmen registrieren und Kennzahlen ablegen")
    ap.add_argument("--bericht", help="Prüfbericht zusätzlich als Markdown-Datei speichern")
    a = ap.parse_args(argv)
    b, reg, unt, werte, quellen = laden_und_pruefen(a.datei)
    zeilen = [f"# Prüfbericht {Path(a.datei).name}", "",
              f"{len(unt)} Unternehmen, {len(werte)} Kennzahlenwerte, {len(quellen)} Dokumente. "
              f"{len(b.fehler)} Fehler, {len(b.warnungen)} Warnungen.", ""]
    for titel, liste in (("Fehler", b.fehler), ("Warnungen", b.warnungen), ("Hinweise", b.info)):
        if liste:
            zeilen += [f"## {titel}", *[f"- {x}" for x in liste], ""]
    bericht = "\n".join(zeilen)
    print(bericht)
    if a.bericht:
        Path(a.bericht).write_text(bericht, encoding="utf-8")
    if b.fehler:
        print("\nNichts geschrieben: erst die Fehler beheben.", file=sys.stderr)
        return 1
    if a.schreiben:
        z = schreiben(reg, unt, werte, quellen, Path(a.datei).name)
        print(f"\nGeschrieben: {len(z)} Unternehmen → {AUSGABE.relative_to(REPO)}; IDs: " +
              ", ".join(f"{n}={u}" for n, u in z.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
