"""Datenschicht für Unternehmen außerhalb des Bankensektors.

Liest alle Excel-Dateien unter `unternehmen/` im Repo (eine Erhebung je Branche, z. B.
`unternehmen/<erhebung>/auswertung/*.xlsx`) und erkennt Spalten über ihre Überschrift
(Aliasse in unternehmen_katalog.json). Aufbau der Blätter:

* Kopfzeile mit Spalte „Unternehmen“ (oder „Name“, „Gesellschaft“, „Firma“) in den ersten 10 Zeilen
* optionale Spalten „Ticker“/„ISIN“/„Branche“/„Sitz“/„Index“
* Branche: Spalte „Branche“, sonst Blattname, sonst Ordnername
* Kennzahlen: jede Spalte, die im Katalog (Aliasse) vorkommt; unbekannte numerische Spalten
  werden als zusätzliche Kennzahlen übernommen, die Formatierung wird aus der Überschrift
  abgeleitet („%“, „Quote“, „Marge“ -> Anteil; „Mio.“ -> Mio.; sonst Zahl)
* Prozentwerte als Anteil (0,12) oder in Prozent (12) – bei Überschrift mit „%“ und Werten > 1,5
  wird durch 100 geteilt

Neue Branchen und neue Spalten kommen ohne Codeänderung mit. Solange keine Branchentabellen
vorliegen, nutzt das Terminal die Beispieldaten aus unternehmen_demo.py (als Demo markiert).
Banken bleiben in der eigenen Datenschicht (datenschicht.py) und werden hier nur verlinkt.
"""
import json
import re
from pathlib import Path

import openpyxl

REPO = Path(__file__).resolve().parent.parent
HIER = Path(__file__).resolve().parent
KATALOG = json.loads((HIER / "unternehmen_katalog.json").read_text())
NAMEN = ("unternehmen", "name", "gesellschaft", "firma", "emittent")
META = {"ticker": ("ticker", "symbol", "kürzel"), "isin": ("isin",), "branche": ("branche", "sektor"),
        "sitz": ("sitz", "ort"), "segment": ("segment", "index", "marktsegment")}
SKIP_DIRS = {"banken", "app", ".git", ".github", "dokumente", "webseiten"}


def _norm(s):
    s = re.sub(r"\(.*?\)", "", str(s)).lower().replace("–", "-")
    return re.sub(r"\s+", " ", s).strip()


ALIAS = {_norm(a): k for k in KATALOG["kennzahlen"] for a in k["aliase"] + [k["name"]]}
BRANCHE = {_norm(a): b["id"] for b in KATALOG["branchen"] for a in b["aliase"] + [b["name"], b["id"]]}


def branche_id(text):
    n = _norm(text or "")
    if n in BRANCHE:
        return BRANCHE[n]
    for a, i in BRANCHE.items():
        if a and (a in n or n in a) and len(n) > 3:
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


def lese_excel(pfad, ordner_branche=None):
    wb = openpyxl.load_workbook(pfad, data_only=True, read_only=True)
    firmen, extra = [], {}
    for ws in wb.worksheets:
        zeilen = list(ws.iter_rows(values_only=True))
        kopf_i = next((i for i, r in enumerate(zeilen[:10]) if any(_norm(c) in NAMEN for c in r if c)), None)
        if kopf_i is None:
            continue
        kopf = [str(c).strip() if c is not None else "" for c in zeilen[kopf_i]]
        spalten, meta_sp = {}, {}
        for j, h in enumerate(kopf):
            n = _norm(h)
            if n in NAMEN and "name" not in meta_sp:
                meta_sp["name"] = j
            elif any(n in v for v in META.values()):
                meta_sp[next(k for k, v in META.items() if n in v)] = j
            elif n in ALIAS:
                spalten[j] = (ALIAS[n], h)
            elif h:
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
                    extra.setdefault(key, {"key": key, "name": re.sub(r"\s*\(.*?\)", "", h).strip(), "fmt": _fmt_aus_ueberschrift(h),
                                           "gruppe": "Weitere Kennzahlen", "hoch": None, "einheit": (re.search(r"\((.*?)\)", h) or [None, None])[1]})
                if "%" in h and abs(v) > 1.5 and (KATALOG_FMT.get(key) or extra.get(key, {}).get("fmt")) == "pct":
                    v /= 100
                f["werte"][key] = v
            firmen.append(f)
    return firmen, list(extra.values())


KATALOG_FMT = {k["key"]: k["fmt"] for k in KATALOG["kennzahlen"]}


def lade(wurzel=REPO, demo=HIER / "data/unternehmen_demo.json"):
    """Gibt {branchen, kennzahlen, unternehmen, quellen, demo} zurück."""
    firmen, extra, quellen = [], {}, []
    for datei in sorted(Path(wurzel).rglob("*.xlsx")):
        teile = datei.relative_to(wurzel).parts
        if teile[0] in SKIP_DIRS or datei.name.startswith("~$") or "archiv" in teile:
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
    ist_demo = False
    if not firmen and Path(demo).exists():
        d = json.loads(Path(demo).read_text())
        firmen, quellen, ist_demo = d["unternehmen"], [d["quelle"]], True
        for f in firmen:
            f["branche"] = f.get("branche") or "sonstige"
    # Duplikate (gleicher Name) zusammenführen: spätere Werte ergänzen frühere
    nach_name = {}
    for f in firmen:
        t = nach_name.setdefault(f["name"], f)
        if t is not f:
            t["werte"].update(f["werte"])
    firmen = list(nach_name.values())
    benutzt = {k for f in firmen for k in f["werte"]}
    kennzahlen = [k for k in KATALOG["kennzahlen"] if k["key"] in benutzt] + [e for k, e in extra.items() if k in benutzt]
    ids = {f["branche"] for f in firmen}
    branchen = [b for b in KATALOG["branchen"] if b["id"] in ids]
    for i in ids - {b["id"] for b in branchen}:  # Branche aus der Tabelle, die der Katalog nicht kennt
        branchen.append({"id": i, "name": i.replace("-", " ").title(), "schwerpunkt": ["ebit_marge", "umsatz", "kgv", "div_rendite", "roe", "ek_quote"]})
    return {"demo": ist_demo, "quellen": quellen, "gruppen": KATALOG["gruppen"] + ["Weitere Kennzahlen"],
            "branchen": branchen, "kennzahlen": kennzahlen, "unternehmen": firmen}


if __name__ == "__main__":
    d = lade()
    print(f"{len(d['unternehmen'])} Unternehmen in {len(d['branchen'])} Branchen, {len(d['kennzahlen'])} Kennzahlen, Quellen: {d['quellen']}")
