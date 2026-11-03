"""Weltkugel: alternative Oberfläche des Terminals (dist/weltkugel.html), gebaut aus derselben Seite wie das klassische Terminal.

Ergänzt die Terminal-Seite um Karte (MapLibre GL, eingebettet), Ländergrenzen (Natural Earth), Firmensitze
(stammdaten/geo/sitz_geo.csv) und eingebettete Schriften für die Beschriftung. Wird von build.py aufgerufen."""
import base64
import csv
import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
SITZE = HIER.parent / "stammdaten/geo/sitz_geo.csv"
TABELLE = HIER.parent / "unternehmen-tabelle/Unternehmen_Tabelle.csv"
TABELLE_GEO = HIER.parent / "stammdaten/geo/tabelle_geo.csv"
# Spalten der Unternehmenstabelle im Stammdaten-Fenster; Werte mit vielen Wiederholungen als Verweis auf eine Werteliste
TAB_SPALTEN = [("name", "Name *"), ("rf", "Rechtsform"), ("sitz", "Sitz"), ("isin", "ISIN"), ("ticker", "Ticker"), ("boerse", "Börse"),
               ("notiert", "Börsennotiert *"), ("branche", "Branche *"), ("lei", "LEI"), ("hr", "Handelsregisternummer"), ("web", "Website"),
               ("bank", "Bank *"), ("index", "Index-Zugehörigkeit"), ("text", "Beschreibung"), ("quelle", "Quelle Stammdaten (URL) *")]
TAB_LISTE = {"rf", "boerse", "notiert", "branche", "bank", "index"}

SCHALE = """
<div id="globus" hidden>
  <div id="gk-karte">
    <div class="gk-kopf">
      <a class="gk-marke" href="#globus" title="Weltkugel"><b>TRM</b>Weltkugel</a>
      <label class="gk-suche" for="gk-suchfeld"><span>&gt;</span><input id="gk-suchfeld" list="gk-liste" placeholder="Land oder Unternehmen suchen, dann Enter" autocomplete="off"></label>
      <button type="button" class="gk-knopf" data-gkebenen aria-pressed="false">Ebenen</button>
    </div>
    <div class="gk-ebenen" id="gk-ebenen" hidden></div>
    <div class="gk-hinweis" id="gk-hinweis" style="opacity:0" role="status"></div>
  </div>
  <aside id="gk-seite" aria-label="Länderdaten"></aside>
</div>
<div id="gk-fenster" hidden></div>
<div id="gk-dock" hidden></div>
<a id="gk-zurueck" class="gk-knopf" href="#start" title="Zwischen Weltkugel und Terminal wechseln">▤ Terminal</a>
<datalist id="gk-liste"></datalist>
"""


def _js(s):
    return s.replace("</", "<\\/")


def sitze():
    """Firmensitze mit Koordinate als kompakte Tabelle {spalten, zeilen}."""
    spalten = ["id", "lat", "lon", "ort", "land", "quelle"]
    zeilen = []
    if SITZE.exists():
        for r in csv.DictReader(open(SITZE, encoding="utf-8")):
            if r["lat"] and r["lon"]:
                zeilen.append([r["unternehmen_id"], float(r["lat"]), float(r["lon"]), r["ort"], r["land_code"], r["quelle_ort"]])
    return {"spalten": spalten, "zeilen": zeilen}


def tabelle():
    """Alle Zeilen der Unternehmenstabelle mit Punkt aus tabelle_geo.csv, spaltenweise und mit Wertelisten (rund 32.000 Zeilen)."""
    if not (TABELLE.exists() and TABELLE_GEO.exists()):
        return None
    sys.path.insert(0, str(HIER.parent / "stammdaten/geo"))
    import tabelle_geo as tg  # noqa: E402
    geo = {r["schluessel"]: r for r in csv.DictReader(open(TABELLE_GEO, encoding="utf-8"))}
    listen = {k: [] for k in TAB_LISTE}
    pos = {k: {} for k in TAB_LISTE}
    spalten = ["k", "id", "land", "lat", "lon", "genau", "ort", "q"] + [k for k, _ in TAB_SPALTEN]
    zeilen, gesehen = [], set()
    for r in csv.DictReader(open(TABELLE, encoding="utf-8-sig"), delimiter=";"):
        cc = tg.LAND.get(r["Land *"].strip(), "")
        k = tg.schluessel(r, cc)
        # Rückfall auf ISIN bzw. Land+Name, falls die Zeile seit dem letzten Lauf von tabelle_geo.py eine Unternehmens-ID bekommen hat
        g = geo.get(k) or geo.get("ISIN:" + r["ISIN"].strip()) or geo.get(f"N:{cc}:{r['Name *'].strip()}")
        if k in gesehen or not g or not g["lat"]:
            continue
        gesehen.add(k)
        z = [k, r["unternehmen_id"], g["land_code"], float(g["lat"]), float(g["lon"]), 1 if g["genauigkeit"] == "ort" else 0, g["ort"], g["quelle"]]
        for kurz, sp in TAB_SPALTEN:
            v = (r.get(sp) or "").strip()
            if kurz == "text" and len(v) > 320:
                v = v[:317].rsplit(" ", 1)[0] + " …"
            if kurz in TAB_LISTE:
                if v not in pos[kurz]:
                    pos[kurz][v] = len(listen[kurz])
                    listen[kurz].append(v)
                v = pos[kurz][v]
            z.append(v)
        zeilen.append(z)
    return {"spalten": spalten, "listen": listen, "zeilen": zeilen}


def seite(terminal_seite):
    """Terminal-Seite (Fragment ohne Dokumentgerüst) -> Weltkugel-Fragment."""
    v = HIER / "vendor/maplibre-gl"
    mlcss = (v / "maplibre-gl.css").read_text()
    mljs = "\n".join(z for z in (v / "maplibre-gl.js").read_text().splitlines() if not z.startswith("//# sourceMappingURL"))
    glyphen = {p.name.rsplit("-0-255", 1)[0]: base64.b64encode(p.read_bytes()).decode() for p in sorted((HIER / "geo/glyphs").glob("*-0-255.pbf"))}
    laender = (HIER / "geo/laender.geojson").read_text()
    s = sitze()
    tab = tabelle()
    teile = [
        terminal_seite.replace("<title>Terminal</title>", "<title>Weltkugel-Terminal</title>", 1),
        "<style>\n" + mlcss + "\n</style>",
        "<style>\n" + (HIER / "src/globus.css").read_text() + "\n</style>",
        SCHALE,
        '<script id="geo-laender" type="application/json">' + _js(laender) + "</script>",
        '<script id="geo-sitze" type="application/json">' + _js(json.dumps(s, ensure_ascii=False, separators=(",", ":"))) + "</script>",
        '<script id="geo-tabelle" type="application/json">' + _js(json.dumps(tab, ensure_ascii=False, separators=(",", ":"))) + "</script>",
        '<script id="geo-glyphen" type="application/json">' + json.dumps(glyphen) + "</script>",
        '<script id="geo-handel" type="application/json">' + (_js((HIER / "data/handel.json").read_text()) if (HIER / "data/handel.json").exists() else "null") + "</script>",
        "<script>\n" + mljs + "\n</script>",
        "<script>\n" + (HIER / "src/globus.js").read_text() + "\n</script>",
    ]
    return "\n".join(teile), len(s["zeilen"])
