"""Weltkugel: alternative Oberfläche des Terminals (dist/weltkugel.html), gebaut aus derselben Seite wie das klassische Terminal.

Ergänzt die Terminal-Seite um Karte (MapLibre GL, eingebettet), Ländergrenzen (Natural Earth), Firmensitze
(stammdaten/geo/sitz_geo.csv) und eingebettete Schriften für die Beschriftung. Wird von build.py aufgerufen."""
import base64
import csv
import json
from pathlib import Path

HIER = Path(__file__).resolve().parent
SITZE = HIER.parent / "stammdaten/geo/sitz_geo.csv"

SCHALE = """
<div id="globus" hidden>
  <div id="gk-karte">
    <div class="gk-kopf">
      <a class="gk-marke" href="#start" title="Klassisches Terminal"><b>TRM</b>Weltkugel</a>
      <label class="gk-suche" for="gk-suchfeld"><span>&gt;</span><input id="gk-suchfeld" list="gk-liste" placeholder="Land oder Unternehmen suchen, dann Enter" autocomplete="off"></label>
      <button type="button" class="gk-knopf" data-gkebenen aria-pressed="false">Ebenen</button>
      <a class="gk-knopf" href="#start">Klassisches Terminal</a>
    </div>
    <div class="gk-ebenen" id="gk-ebenen" hidden></div>
    <div class="gk-hinweis" id="gk-hinweis" style="opacity:0" role="status"></div>
  </div>
  <aside id="gk-seite" aria-label="Länderdaten"></aside>
</div>
<div id="gk-fenster" hidden></div>
<div id="gk-dock" hidden></div>
<a id="gk-zurueck" class="gk-knopf" href="#globus" hidden>◉ Weltkugel</a>
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


def seite(terminal_seite):
    """Terminal-Seite (Fragment ohne Dokumentgerüst) -> Weltkugel-Fragment."""
    v = HIER / "vendor/maplibre-gl"
    mlcss = (v / "maplibre-gl.css").read_text()
    mljs = "\n".join(z for z in (v / "maplibre-gl.js").read_text().splitlines() if not z.startswith("//# sourceMappingURL"))
    glyphen = {p.name.rsplit("-0-255", 1)[0]: base64.b64encode(p.read_bytes()).decode() for p in sorted((HIER / "geo/glyphs").glob("*-0-255.pbf"))}
    laender = (HIER / "geo/laender.geojson").read_text()
    s = sitze()
    teile = [
        terminal_seite.replace("<title>Terminal</title>", "<title>Weltkugel-Terminal</title>", 1),
        "<style>\n" + mlcss + "\n</style>",
        "<style>\n" + (HIER / "src/globus.css").read_text() + "\n</style>",
        SCHALE,
        '<script id="geo-laender" type="application/json">' + _js(laender) + "</script>",
        '<script id="geo-sitze" type="application/json">' + _js(json.dumps(s, ensure_ascii=False, separators=(",", ":"))) + "</script>",
        '<script id="geo-glyphen" type="application/json">' + json.dumps(glyphen) + "</script>",
        "<script>\n" + mljs + "\n</script>",
        "<script>\n" + (HIER / "src/globus.js").read_text() + "\n</script>",
    ]
    return "\n".join(teile), len(s["zeilen"])
