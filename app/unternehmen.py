"""Unternehmensverzeichnis des Terminals: alle Unternehmen aller Branchen, Banken eingeschlossen.

Quellen (alle optional, alles wächst ohne Codeänderung mit):

* Branchen-Excel unter beliebigen Ordnern im Repo (außer banken/, zeitreihen/, app/). Kopfzeile mit
  „Unternehmen“/„Name“ in den ersten 10 Zeilen; Spalten werden über die Überschrift erkannt
  (Aliasse in unternehmen_katalog.json). Branche aus Spalte „Branche“, sonst Blatt- oder Ordnername.
  Optionale Spalten: ID, Ticker, ISIN, Sitz, Gruppe/Untergruppe, Börsennotiert, Rechtsform.
* Banken aus datenschicht.py (Bilanzvergleich) und markt.json (nur selbst notierte Institute).
* zeitreihen/stammdaten.csv: weitere Unternehmen, auch nicht börsennotierte (Spalten
  unternehmen_id, name, branche, gruppe, optional notiert/isin/ticker/sitz).
* zeitreihen/zeitreihe_lang.csv: Zeitreihen je Unternehmen; der letzte Wert füllt fehlende Kennzahlen.
* Dokumente: jede Datei in einem Ordner dokumente/, webseiten/, berichte/ oder geschaeftsberichte/,
  deren Unterordner die Unternehmens-ID ist, dazu index.csv-Dateien in solchen Ordnern
  (Spalten unternehmen_id/name, datei/pfad, titel, typ, jahr, url, abrufdatum).

Die Unternehmens-ID kommt ausschließlich aus stammdaten/ (U000123); Namen, ISIN, alte IDs und Ordnernamen werden dort aufgelöst.
Unbekannte Unternehmen brechen den Bau ab (erst in die Stammdaten aufnehmen).

Solange keine Unternehmen außerhalb der Banken vorliegen, kommen Beispieldaten aus
unternehmen_demo.py dazu (je Unternehmen als demo markiert).
"""
import csv
import json
import os
import re
import subprocess
import unicodedata
from pathlib import Path

import openpyxl

REPO = Path(__file__).resolve().parent.parent
import sys  # noqa: E402
sys.path.insert(0, str(REPO / "stammdaten"))
import ids as stamm  # noqa: E402  zentrale Unternehmens-IDs (stammdaten/)
HIER = Path(__file__).resolve().parent
KATALOG = json.loads((HIER / "unternehmen_katalog.json").read_text())
GITHUB_REPO = os.environ.get("TERMINAL_REPO", "chillkrote/Unternehmenskennzahlen")
NAMEN = ("unternehmen", "name", "gesellschaft", "firma", "emittent")
META = {"id": ("id", "unternehmen_id", "unternehmens-id"), "ticker": ("ticker", "symbol", "kürzel"), "isin": ("isin",),
        "branche": ("branche", "sektor"), "gruppe": ("gruppe", "untergruppe", "unterbranche", "teilbranche", "subbranche"),
        "sitz": ("sitz", "ort"), "segment": ("segment", "index", "marktsegment"), "notiert": ("börsennotiert", "notiert", "notierung"),
        "rechtsform": ("rechtsform",)}
SKIP_DIRS = {"banken", "app", "zeitreihen", ".git", ".github", "dokumente", "webseiten"}
DOK_ORDNER = {"dokumente", "webseiten", "berichte", "geschaeftsberichte", "documents"}
# Kennzahlen im Langformat -> Schlüssel im Katalog
LANG_KZ = {"bilanzsumme": "bilanzsumme", "eigenkapital": "ek", "jahresueberschuss": "jue", "umsatz": "umsatz",
           "ebit": "ebit", "ebitda": "ebitda", "cet1_quote": "cet1_quote", "gk_quote": "gk_quote", "leverage_ratio": "lr"}


def slug(name):
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _norm(s):
    s = re.sub(r"\(.*?\)", "", str(s)).lower().replace("–", "-")
    return re.sub(r"\s+", " ", s).strip()


ALIAS = {_norm(a): k["key"] for k in KATALOG["kennzahlen"] for a in k["aliase"] + [k["name"]]}
BRANCHE = {_norm(a): b["id"] for b in KATALOG["branchen"] for a in b["aliase"] + [b["name"], b["id"]]}
KATALOG_FMT = {k["key"]: k["fmt"] for k in KATALOG["kennzahlen"]}


def branche_id(text):
    n = _norm(text or "")
    if not n:
        return None
    if n in BRANCHE:
        return BRANCHE[n]
    for a, i in BRANCHE.items():
        if a and len(n) > 3 and (a in n or n in a):
            return i
    return None


def _fmt_aus_ueberschrift(h):
    n = _norm(h)
    if "%" in str(h) or any(w in n for w in ("quote", "marge", "rendite", "wachstum")):
        return "pct"
    if "mio" in str(h).lower():
        return "mio"
    if n.startswith(("kgv", "kbv", "ev/")) or "/ebitda" in n:
        return "x"
    return "zahl"


def _zahl(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _ja(v):
    return str(v).strip().lower() in ("ja", "yes", "true", "1", "x", "börsennotiert", "notiert")


def lese_excel(pfad, ordner_branche=None):
    wb = openpyxl.load_workbook(pfad, data_only=True, read_only=True)
    firmen, extra = [], {}
    # Arbeitsmappen mit Blatt „Übersicht“ (eine Zeile je Unternehmen) tragen daneben GuV-, Bilanz- und Rohdatenblätter: nur die Übersicht zählt
    blaetter = [ws for ws in wb.worksheets if _norm(ws.title) == "uebersicht" or ws.title == "Übersicht"] or wb.worksheets
    for ws in blaetter:
        zellen = list(ws.iter_rows())
        zeilen = [[c.value for c in r] for r in zellen]
        kopf_i = next((i for i, r in enumerate(zeilen[:10]) if any(_norm(c) in NAMEN for c in r if c)), None)
        if kopf_i is None:
            continue
        kopf = [str(c).strip() if c is not None else "" for c in zeilen[kopf_i]]
        spalten, meta_sp = {}, {}
        pct_spalten, blatt_firmen = {}, []
        # Spalte ist als Prozent formatiert (Zahl = Anteil, 0,49 = 49 %): dann nie umrechnen
        als_prozent = {j for r in zellen[kopf_i + 1:] for j, c in enumerate(r) if isinstance(c.value, (int, float)) and "%" in (c.number_format or "")}
        for j, h in enumerate(kopf):
            n = _norm(h)
            if n in NAMEN and "name" not in meta_sp:
                meta_sp["name"] = j
            elif any(n in v for v in META.values()):
                meta_sp.setdefault(next(k for k, v in META.items() if n in v), j)
            elif n in ALIAS and ALIAS[n] not in {k for k, _ in spalten.values()}:
                spalten[j] = (ALIAS[n], h)
            elif h:  # unbekannt oder zweite Spalte derselben Kennzahl (z. B. „KGV (12M, Yahoo)“ neben „KGV (GJ)“): eigene Kennzahl, erste Spalte gilt
                spalten[j] = (None, h)
        blatt_branche = branche_id(ws.title) or ordner_branche
        for r in zeilen[kopf_i + 1:]:
            name = r[meta_sp["name"]] if "name" in meta_sp and meta_sp["name"] < len(r) else None
            if not name or not isinstance(name, str) or name.strip().lower().startswith(("quelle", "median", "summe")):
                continue
            f = {"name": name.strip(), "werte": {}}
            for k, j in meta_sp.items():
                if k != "name" and j < len(r) and r[j] not in (None, ""):
                    f[k] = str(r[j]).strip()
            f["branche"] = branche_id(f.get("branche")) or blatt_branche or "sonstige"
            for j, (key, h) in spalten.items():
                v = _zahl(r[j]) if j < len(r) else None
                if v is None:
                    continue
                if key is None:
                    # unbekannte Spalte: als eigene Kennzahl führen, wenn überhaupt Zahlen drinstehen
                    key = "x_" + re.sub(r"[^a-z0-9]+", "_", _norm(h)).strip("_")
                    kurzname = re.sub(r"\s*\(.*?\)", "", h).strip()
                    extra.setdefault(key, {"key": key, "name": h if _norm(kurzname) in ALIAS else kurzname, "fmt": _fmt_aus_ueberschrift(h),
                                           "gruppe": "Weitere Kennzahlen", "hoch": None, "einheit": (re.search(r"\((.*?)\)", h) or [None, None])[1]})
                if "%" in h and (KATALOG_FMT.get(key) or extra.get(key, {}).get("fmt")) == "pct":
                    pct_spalten[key] = j in als_prozent
                f["werte"][key] = v
            f["notiert"] = _ja(f["notiert"]) if "notiert" in f else bool(f.get("ticker") or f.get("isin") or f["werte"].get("marktkap"))
            firmen.append(f)
            blatt_firmen.append(f)
        # Einheit je Spalte: steht „%“ in der Überschrift und sind die Zellen nicht als Prozent formatiert, entscheidet der größte Betrag der Spalte (über 1,5 = Prozentpunkte)
        # (ein einzelner Wert wie 1,2 % in einer Prozentpunkte-Spalte wird so nicht als 120 % gelesen)
        for key, formatiert in pct_spalten.items():
            if formatiert:      # Anteile: nur offensichtliche Ausreißer über 150 % sind Prozentpunkte (z. B. Yahoo-Insider 2,26 für 2,26 %)
                for g in blatt_firmen:
                    if key in g["werte"] and abs(g["werte"][key]) > 1.5:
                        g["werte"][key] /= 100
            elif max((abs(g["werte"][key]) for g in blatt_firmen if key in g["werte"]), default=0) > 1.5:
                for g in blatt_firmen:
                    if key in g["werte"]:
                        g["werte"][key] /= 100
    return firmen, list(extra.values())


def _q(a, b):
    return a / b if a is not None and b not in (None, 0) else None


def aus_banken(banken, markt):
    """Banken des Bilanzvergleichs als Branche Banken (HGB-Einzelabschluss; Börsendaten nur bei selbst notierten Instituten)."""
    nach_bank = {}
    for m in (markt or {}).get("werte", []):
        nach_bank.setdefault(m["bank"], m)
    out = []
    for b in banken:
        if not b.get("bank") or b.get("gruppe") in (None, "Gruppe"):  # Median- und Kopfzeilen der Excel
            continue
        zr = b.get("zr") or {}
        jue_r = zr.get("jahresueberschuss") or (b.get("zeitreihe") or {}).get("Jahresüberschuss") or {}
        jue = jue_r.get(max(jue_r)) if jue_r else None
        wachstum = _q(b.get("bs"), b.get("vj_bs"))
        w = {"bilanzsumme": b.get("bs"), "ek": b.get("ek"), "ek_quote": b.get("ek_quote"), "jue": jue,
             "roe": _q(jue, b.get("ek")), "roa": _q(jue, b.get("bs")), "fonds_bs": b.get("fonds_bs"),
             "cet1_quote": b.get("cet1_quote"), "gk_quote": b.get("gk_quote"), "lr": b.get("lr"), "rwa_dichte": b.get("rwa_dichte"),
             "w_bilanzsumme": wachstum - 1 if wachstum else None}
        f = {"id": b["id"], "name": b["bank"], "branche": "banken", "gruppe": b.get("gruppe"), "rolle": b.get("rolle"),
             "sitz": b.get("sitz"), "bank": b["bank"], "notiert": False, "abschluss": "HGB-Einzelabschluss"}
        m = nach_bank.get(b["bank"])
        if m and m.get("ebene") == "Institut":
            kz = m.get("kz") or {}
            f.update(notiert=True, ticker=m["ticker"], datum=m.get("datum"))
            w.update(kurs=m.get("kurs"), r_ytd=m.get("r_ytd"), r_1j=m.get("r_1j"), kgv=kz.get("kgv"), kbv=kz.get("kbv"),
                     div_rendite=kz.get("div_rendite"))
            if m.get("waehrung") == "EUR" and m.get("marktkap"):
                w["marktkap"] = m["marktkap"] / 1e6
        elif m:
            f["mutter"] = {"name": m.get("mutter"), "ticker": m["ticker"]}
        f["werte"] = {k: v for k, v in w.items() if isinstance(v, (int, float)) and v == v}
        out.append(f)
    return out


def lese_stammdaten(wurzel):
    datei = Path(wurzel) / "zeitreihen/stammdaten.csv"
    if not datei.exists():
        return []
    with open(datei, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def lese_reihen(wurzel):
    """{id: {key: {"punkte": [[jahr, wert]], "basis": "HGB Einzel"}}}; je Kennzahl die Reihe mit den meisten Jahren."""
    datei = Path(wurzel) / "zeitreihen/zeitreihe_lang.csv"
    if not datei.exists():
        return {}
    roh = {}
    with open(datei, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                v = float(r["wert"])
            except (TypeError, ValueError):
                continue
            key = LANG_KZ.get(r["kennzahl"]) or ALIAS.get(_norm(r["kennzahl"])) or r["kennzahl"]
            basis = " ".join(x for x in (r.get("rechnungslegung"), r.get("ebene")) if x)
            roh.setdefault(r["unternehmen_id"], {}).setdefault(key, {}).setdefault(basis, {})[r["stichtag"][:4]] = v
    out = {}
    for uid, kzs in roh.items():
        for key, varianten in kzs.items():
            basis, pkt = max(varianten.items(), key=lambda x: len(x[1]))
            out.setdefault(uid, {})[key] = {"basis": basis, "punkte": sorted([int(j), v] for j, v in pkt.items())}
    return out


def _git_dateien(wurzel):
    try:
        r = subprocess.run(["git", "-C", str(wurzel), "ls-files", "-z"], capture_output=True, check=True)
        return [p for p in r.stdout.decode().split("\0") if p]
    except Exception:
        return [str(p.relative_to(wurzel)) for p in Path(wurzel).rglob("*") if p.is_file() and ".git" not in p.parts]


def _groesse(pfad):
    """Dateigröße in KB; bei Git-LFS-Zeigern die Größe des eigentlichen Dokuments."""
    try:
        with open(pfad, "rb") as fh:
            kopf = fh.read(200)
        if kopf.startswith(b"version https://git-lfs"):
            m = re.search(rb"size (\d+)", kopf)
            return round(int(m.group(1)) / 1024) if m else None
        return round(os.path.getsize(pfad) / 1024)
    except OSError:
        return None


def dok_typ(name):
    n = name.lower()
    for typ, muster in (("Offenlegungsbericht", r"offenlegung|pillar|disclosure|ol20"),
                        ("Zwischenbericht", r"halbjahr|quartal|q[1-4]|interim|zwischen"),
                        ("Jahresabschluss", r"jahresabschluss|einzelabschluss|financial-statements|jahresbilanz|abschluss"),
                        ("Geschäftsbericht", r"geschaeftsbericht|geschäftsbericht|annual|jahresbericht|jahresfinanzbericht|gb[-_]?20|_gb|bericht"),
                        ("Webseite (Sicherung)", r"\.html?$")):
        if re.search(muster, n):
            return typ
    return "Dokument"


def dok_jahr(name):
    js = [int(j) for j in re.findall(r"(?<!\d)(20[0-3]\d|19[89]\d)(?!\d)", name)]
    return max(js) if js else None


def _dok(wurzel, pfad):
    name = pfad.rsplit("/", 1)[-1]
    return {"pfad": pfad, "titel": name, "typ": dok_typ(name), "jahr": dok_jahr(name),
            "format": name.rsplit(".", 1)[-1].upper() if "." in name else "", "kb": _groesse(Path(wurzel) / pfad)}


def _finder(ids):
    """Name, Ordnername, alte ID oder neue ID -> Unternehmens-ID (nur solche, die in ids vorkommen); Auflösung über stammdaten/."""
    reg = stamm.lade()

    def finde(name):
        uid = reg.aufloesen(name) if name else None
        return uid if uid in ids else None
    return finde


def dokumente(wurzel, ids):
    """{id: [dokument]} aus den Dokumentordnern (Unterordner = Unternehmens-ID) und ihren index.csv."""
    finde = _finder(ids)
    out, index_dateien = {}, []
    for p in _git_dateien(wurzel):
        teile = p.split("/")
        if teile[-1] == "index.csv" and DOK_ORDNER & set(teile):
            index_dateien.append(p)
            continue
        for i, t in enumerate(teile[:-2]):
            uid = finde(teile[i + 1]) if t in DOK_ORDNER else None
            if uid:
                out.setdefault(uid, {})[p] = _dok(wurzel, p)
                break
    for p in index_dateien:  # Angaben aus index.csv ergänzen die automatische Erkennung
        _index_lesen(wurzel, p, finde, out)
    return {uid: sorted(d.values(), key=lambda x: (-(x["jahr"] or 0), x["typ"], x["titel"])) for uid, d in out.items()}


def berichtstermine(wurzel, nach_id):
    """termine/termine.csv (termine/skripte/termine_erfassen.py): je Unternehmen f["termine"] = Quartals-/Halbjahres-/Jahresberichte
    mit Termin, Status (erwartet / bestätigt / erschienen), Quelle und - falls der Abruf-Script den Bericht geladen hat - der Datei im Repo."""
    p = Path(wurzel) / "termine" / "termine.csv"
    if not p.exists():
        return
    finde = _finder(set(nach_id))
    basis = lambda t: (t or "").split(".")[0].upper()
    nach_ticker = {}
    for u in nach_id.values():
        if u.get("ticker"):
            nach_ticker.setdefault(basis(u["ticker"]), []).append(u)
    with open(p, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            uid = finde(r.get("unternehmen_id"))
            u = nach_id.get(uid)
            if u is None or not r.get("termin"):
                continue
            t = {k: r.get(k, "") for k in ("berichtsart", "periode_ende", "termin", "quelle", "quelle_url", "status", "stand", "abruf_status", "datei")}
            # dieselbe Aktie kann unter zwei Kennungen geführt sein (Bank aus dem Bilanzvergleich, Börsenunternehmen): Termin an beide
            for x in {id(u): u, **{id(y): y for y in nach_ticker.get(basis(r.get("ticker")), [])}}.values():
                x.setdefault("termine", []).append(t)
    for u in nach_id.values():
        if u.get("termine"):
            u["termine"].sort(key=lambda t: t["termin"])


def _index_lesen(wurzel, p, finde, out):
    """index.csv (Komma oder Semikolon): Unternehmen über ID oder Name, Datei relativ zum Repo, zur index.csv oder zur Erhebung."""
    ordner = (Path(wurzel) / p).parent
    if not (Path(wurzel) / p).exists():  # z. B. bei teilweisem (sparse) Checkout
        return
    text = (Path(wurzel) / p).read_text(encoding="utf-8-sig")
    kopf = text.split("\n", 1)[0]
    for r in csv.DictReader(text.splitlines(), delimiter=";" if kopf.count(";") > kopf.count(",") else ","):
        r = {_norm(k): (v or "").strip() for k, v in r.items() if k}
        uid = finde(r.get("unternehmen_id") or r.get("id") or "") or finde(r.get("unternehmen") or r.get("bank") or r.get("name") or "")
        datei = r.get("datei") or r.get("pfad") or r.get("path") or r.get("file")
        ziel = next((x for x in (Path(wurzel) / datei, ordner / datei, ordner.parent / datei) if x.exists()), None) if datei else None
        if not uid or ziel is None:
            continue
        pfad = str(ziel.resolve().relative_to(Path(wurzel).resolve()))
        d = out.setdefault(uid, {}).setdefault(pfad, _dok(wurzel, pfad))
        for feld, spalten in (("titel", ("titel", "bezeichnung")), ("url", ("url", "quelle_url", "link")),
                              ("abruf", ("abrufdatum", "abruf")), ("sha256", ("sha256",))):
            v = next((r[s] for s in spalten if r.get(s)), None)
            if v:
                d[feld] = v
        typ = r.get("typ") or r.get("dokumentart") or ""
        if typ and d["typ"] == "Dokument" and typ.lower() != "sonstiges":
            d["typ"] = typ
        j = r.get("jahr") or r.get("jahr_laut_link") or r.get("gj") or ""
        if re.fullmatch(r"\d{4}", j[:4]):
            d["jahr"] = int(j[:4])


def lade(wurzel=REPO, banken=None, markt=None, demo=HIER / "data/unternehmen_demo.json"):
    """Gibt {branchen, kennzahlen, unternehmen, quellen, demo, repo} zurück."""
    firmen, extra, quellen = branchen_excel(wurzel)
    if banken:
        bk = aus_banken(banken, markt)
        ids = {b["id"]: b for b in bk}
        rest = []
        for f in firmen:          # notierte Bank in Branchenmappe und Bilanzvergleich: Bilanzvergleich führt, Börsendaten ergänzen
            b = ids.get(f["id"])
            if b is None:
                rest.append(f)
                continue
            for k, v in f["werte"].items():
                b["werte"].setdefault(k, v)
            for k in ("ticker", "isin", "sitz", "segment"):
                if f.get(k) and not b.get(k):
                    b[k] = f[k]
            if f.get("notiert"):
                b["notiert"] = True
        firmen = rest + bk
        quellen.append("banken/bilanzvergleich-gj2025")
    nach_id = {f["id"]: f for f in firmen}
    stammdaten(wurzel, firmen, nach_id)
    from europa import ergaenzen, nichtbanken
    ergaenzen(wurzel, firmen, nach_id, stamm.lade())
    nichtbanken(wurzel, firmen)
    ist_demo = beispieldaten(demo, firmen, nach_id, quellen)
    zeitreihen(wurzel, nach_id)
    for uid, docs in dokumente(wurzel, set(nach_id)).items():
        nach_id[uid]["dokumente"] = docs
    governance(wurzel, nach_id)
    berichtstermine(wurzel, nach_id)
    benutzt = {k for f in firmen for k in f["werte"]}
    kennzahlen = [k for k in KATALOG["kennzahlen"] if k["key"] in benutzt] + [e for k, e in extra.items() if k in benutzt]
    return {"demo": ist_demo, "quellen": quellen, "repo": GITHUB_REPO, "zweig": "main",
            "gruppen": KATALOG["gruppen"] + ["Weitere Kennzahlen"], "branchen": branchenliste(firmen),
            "kennzahlen": kennzahlen, "unternehmen": firmen,
            # alte Schreibweisen der IDs -> zentrale ID (Lesezeichen #firma-<alt> bleiben gültig)
            "alt_ids": {a["alias"]: a["unternehmen_id"] for a in stamm.lade().aliase if a["art"] == "id_alt"}}


def _csv(pfad):
    if not pfad.exists():
        return []
    with open(pfad, encoding="utf-8-sig", newline="") as fh:
        return [{k: (v or "").strip() for k, v in r.items() if k} for r in csv.DictReader(fh)]


def _num(v):
    try:
        return float(v.replace(",", ".")) if v else None
    except ValueError:
        return None


def governance(wurzel, nach_id):
    """governance/*.csv (Schema siehe governance/README.md) -> f["gov"] je unternehmen_id.

    Nichts ist fest verdrahtet: jedes Unternehmen, dessen unternehmen_id in den Tabellen vorkommt, bekommt
    Gremien, Vergütung, Kennzahlen und die externen Mandate / Stationen seiner Mitglieder."""
    ordner = Path(wurzel) / "governance"
    mit, kz, vg = (_csv(ordner / n) for n in ("gremien_mitglieder.csv", "kennzahlen_gremien.csv", "verguetung.csv"))
    mandate, werdegang = _csv(ordner / "mandate_extern.csv"), _csv(ordner / "werdegang.csv")
    man_p, wer_p = {}, {}
    for r in mandate:
        man_p.setdefault(r["person_id"], []).append({k: r[k] for k in ("typ", "gesellschaft", "gesellschaft_unternehmen_id", "funktion", "gueltig", "ueber_unternehmen_id") if r.get(k)})
    for r in werdegang:
        wer_p.setdefault(r["person_id"], []).append({k: r[k] for k in ("station", "organisation", "zeitraum", "art") if r.get(k)})
    gov = {}

    def g(uid):
        return gov.setdefault(uid, {"mitglieder": [], "kennzahlen": [], "verguetung": [], "quellen": set()}) if uid in nach_id else None

    for r in mit:
        d = g(r["unternehmen_id"])
        if d is None:
            continue
        pid = r["person_id"]
        d["mitglieder"].append({"gj": int(r["gj"]), "organ": r["organ"], "pid": pid, "name": r["name"], "funktion": r["funktion"],
                                "art": r["vertreter_art"], "seit": r["seit"], "bis": r["bis"], "beruf": r["beruf_laut_dokument"],
                                "seite": r["seite"], "bem": r["bemerkung"], "mandate": man_p.get(pid, []), "werdegang": wer_p.get(pid, [])})
        d["quellen"].add(r["quelle_dokument"])
    for r in kz:
        d = g(r["unternehmen_id"])
        if d is not None:
            d["kennzahlen"].append({"gj": int(r["gj"]), "feld": r["feld"], "wert": r["wert"], "einheit": r["einheit"], "seite": r["seite"], "bem": r["bemerkung"]})
            d["quellen"].add(r["quelle_dokument"])
    for r in vg:
        d = g(r["unternehmen_id"])
        if d is not None:
            d["verguetung"].append({"gj": int(r["gj"]), "gremium": r["gremium"], "name": r["name"], "pid": r["person_id"],
                                    "betrag": _num(r["betrag_tsd_eur"]), "art": r["art"], "seite": r["seite"], "bem": r["bemerkung"]})
            d["quellen"].add(r["quelle_dokument"])
    for uid, d in gov.items():
        d["quellen"] = sorted(q for q in d["quellen"] if q)
        nach_id[uid]["gov"] = d


def branchen_excel(wurzel):
    firmen, extra, quellen = [], {}, []
    for datei in sorted(Path(wurzel).rglob("*.xlsx")):
        teile = datei.relative_to(wurzel).parts
        if teile[0] in SKIP_DIRS or datei.name.startswith("~$") or "archiv" in teile or "quellen" in teile or "rohdaten" in teile:
            continue
        ordner_branche = next((branche_id(t) for t in teile[:-1] if branche_id(t)), None)
        try:
            f, e = lese_excel(datei, ordner_branche)
        except Exception as ex:  # eine kaputte Datei soll den Build nicht stoppen
            print(f"  übersprungen: {datei.name} ({ex})")
            continue
        if f:
            quellen.append("/".join(teile))
            firmen += f
            extra.update({k["key"]: k for k in e})
    reg = stamm.lade()
    gesehen, eindeutig, unbekannt = set(), [], []
    for f in firmen:       # dieselbe Gesellschaft in Gesamt- und Branchenmappe nur einmal (erste Fundstelle zuerst)
        uid = reg.aufloesen(f.get("id")) or reg.aufloesen(f.get("isin")) or reg.aufloesen(f["name"])
        if uid is None:
            unbekannt.append(f"{f['name']} ({f.get('isin') or 'ohne ISIN'})")
            continue
        f["id"] = uid
        if uid in gesehen:
            continue
        gesehen.add(uid)
        eindeutig.append(f)
    if unbekannt:
        raise SystemExit("Nicht in stammdaten/unternehmen_ids.csv: " + "; ".join(sorted(set(unbekannt))[:20])
                         + " -> zuerst über stammdaten/ids.py registrieren (Universum-Skript oder ids.lade().registrieren)")
    return eindeutig, extra, quellen


def stammdaten(wurzel, firmen, nach_id):
    """Untergruppe und Rolle ergänzen; Unternehmen, die nur in den Stammdaten stehen (auch nicht notierte), aufnehmen."""
    for s in lese_stammdaten(wurzel):
        uid = stamm.lade().aufloesen(s.get("unternehmen_id")) or stamm.lade().aufloesen(s.get("name"))
        if uid is None:
            continue
        if s.get("gruppe") == "Gruppe" or "(Median)" in (s.get("name") or ""):  # Auswertungszeilen der Excel, keine Unternehmen
            continue
        f = nach_id.get(uid)
        if f is None:
            f = {"id": uid, "name": s.get("name") or uid, "werte": {},
                 "branche": branche_id(s.get("branche")) or slug(s.get("branche") or "sonstige"),
                 "notiert": _ja(s["notiert"]) if s.get("notiert") else bool(s.get("isin") or s.get("ticker"))}
            for k in ("ticker", "isin", "sitz", "rechtsform"):
                if s.get(k):
                    f[k] = s[k]
            firmen.append(f)
            nach_id[uid] = f
        for k in ("gruppe", "rolle", "nachfolger_von"):
            if s.get(k) and not f.get(k):
                f[k] = s[k]


def beispieldaten(demo, firmen, nach_id, quellen):
    """Stichprobe aus Yahoo, solange außer den Banken keine Branche Daten hat."""
    if any(f["branche"] != "banken" for f in firmen) or not Path(demo).exists():
        return False
    d = json.loads(Path(demo).read_text())
    for f in d["unternehmen"]:
        uid = stamm.lade().aufloesen(f.get("isin")) or stamm.lade().aufloesen(f["name"])
        if uid is None:  # Beispieldaten ohne Eintrag in den Stammdaten bleiben draußen
            continue
        f.update(id=uid, branche=f.get("branche") or "sonstige", notiert=True, demo=True)
        if f["id"] not in nach_id:
            firmen.append(f)
            nach_id[f["id"]] = f
    quellen.append(d["quelle"])
    return True


def zeitreihen(wurzel, nach_id):
    """Reihen fürs Profil; der letzte Wert füllt fehlende Kennzahlen."""
    for uid, kzs in lese_reihen(wurzel).items():
        f = nach_id.get(uid)
        if f is None:
            continue
        f["reihen"] = kzs
        for key, r in kzs.items():
            if key in KATALOG_FMT and f["werte"].get(key) is None and r["punkte"]:
                f["werte"][key] = r["punkte"][-1][1]


def branchenliste(firmen):
    ids = {f["branche"] for f in firmen}
    branchen = [dict(b) for b in KATALOG["branchen"] if b["id"] in ids]
    for i in sorted(ids - {b["id"] for b in branchen}):  # Branche aus der Tabelle, die der Katalog nicht kennt
        branchen.append({"id": i, "name": i.replace("-", " ").title(), "schwerpunkt": ["ebit_marge", "umsatz", "kgv", "div_rendite", "roe", "ek_quote"]})
    for b in branchen:  # Untergruppen: Reihenfolge aus dem Katalog, dann weitere aus den Daten
        da = {f.get("gruppe") for f in firmen if f["branche"] == b["id"] and f.get("gruppe")}
        b["gruppen"] = [g for g in b.get("gruppen", []) if g in da] + sorted(da - set(b.get("gruppen", [])))
        b.pop("aliase", None)
    return branchen


if __name__ == "__main__":
    import datenschicht
    mk = HIER / "data/markt.json"
    d = lade(banken=datenschicht.lade(), markt=json.loads(mk.read_text()) if mk.exists() else None)
    u = d["unternehmen"]
    print(f"{len(u)} Unternehmen ({sum(f['notiert'] for f in u)} notiert) in {len(d['branchen'])} Branchen, "
          f"{len(d['kennzahlen'])} Kennzahlen, {sum(len(f.get('dokumente', [])) for f in u)} Dokumente bei "
          f"{sum(1 for f in u if f.get('dokumente'))} Unternehmen, Quellen: {d['quellen']}")

