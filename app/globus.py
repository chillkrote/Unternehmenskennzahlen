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
NETZE = HIER.parent / "stammdaten/beziehungen"

SCHALE = """
<div id="globus" hidden>
  <div id="gk-karte">
    <div class="gk-kopf">
      <a class="gk-marke" href="#globus" title="Weltkugel"><b>TRM</b>Weltkugel</a>
      <label class="gk-suche" for="gk-suchfeld"><span>&gt;</span><input id="gk-suchfeld" list="gk-liste" placeholder="Land oder Unternehmen suchen, dann Enter" autocomplete="off"></label>
      <button type="button" class="gk-knopf" data-gkebenen aria-pressed="false">Ebenen</button>
    </div>
    <div class="gk-formen" id="gk-formen" role="tablist" aria-label="Darstellungsform"></div>
    <aside id="gk-seite-links" aria-label="Weitere gewählte Länder" hidden></aside>
    <div class="gk-ebenen" id="gk-ebenen" hidden></div>
    <div class="gk-stufen" id="gk-stufen" role="group" aria-label="Zoomstufe"></div>
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


# API-Fassung (build.py --api): Spalten nur für das Stammdaten-Fenster bleiben auf dem Server (/companies/{id}); rund 7 MB weniger.
# k ist in jeder Zeile gleich id (Schlüssel der Unternehmenstabelle) und wird in der Seite aus id gesetzt.
NUR_SERVER = ("k", "rf", "boerse", "lei", "hr", "web", "bank", "text", "quelle")


def tabelle_schlank(tab):
    if not tab:
        return tab
    if any(z[0] != z[1] for z in tab["zeilen"]):
        raise SystemExit("geo-tabelle: Zeile ohne Unternehmens-ID; die API-Fassung braucht k == id")
    behalten = [j for j, s in enumerate(tab["spalten"]) if s not in NUR_SERVER]
    return {"spalten": [tab["spalten"][j] for j in behalten], "schlank": True,
            "listen": {k: v for k, v in tab["listen"].items() if k not in NUR_SERVER},
            "zeilen": [[z[j] for j in behalten] for z in tab["zeilen"]]}


def netze():
    """Unternehmensnetze (Standorte und Beziehungen je Konzern) aus stammdaten/beziehungen/daten, geprüft."""
    if not (NETZE / "beziehungen.py").exists():
        return {}
    sys.path.insert(0, str(NETZE))
    import beziehungen  # noqa: E402
    return beziehungen.laden()


# Wahlkreisgrenzen, die wahlen.js erst lädt, wenn eine Wahl mit dieser Einheit auf der Karte ist (hält die Seite klein, Artifact-Grenze 16 MB).
# Schlüssel = "geo" der Einheit in data/wahlen.json, properties.id = Schlüssel der Werte.
WAHL_GEO = [("landtagswahlkreise-nw", "geo/landtagswahlkreise_nw.geojson"), ("wahlkreise-gb", "geo/wahlkreise_gb.geojson"),
            ("wahlkreise-fr", "geo/wahlkreise_fr.geojson"), ("wahlkreise-ca", "geo/wahlkreise_ca.geojson"), ("wahlkreise-au", "geo/wahlkreise_au.geojson"),
            ("gemeinden-at", "geo/gemeinden_at.geojson"), ("wahlkreise-us", "geo/wahlkreise_us.geojson"), ("wahlkreise-es", "geo/wahlkreise_es.geojson"),
            ("wahlkreise-no", "geo/wahlkreise_no.geojson"), ("wahlkreise-us22", "geo/wahlkreise_us22.geojson"), ("kreise-us", "geo/kreise_us.geojson"), ("wahlkreise-us20", "geo/wahlkreise_us20.geojson"), ("gemeinden-ch", "geo/gemeinden_ch.geojson")]


WERTE_NACHLADEN_AB = 800      # Einheiten mit so vielen Werten (Gemeinden) stehen nicht in der Seite, sondern in wahlgeo/werte-<wahl>-<einheit>.json
WERTE_NACHLADEN_AB_API = 10   # API-Fassung (eigener Server, keine Dateigrenze): schon ab 10 Werten je Einheit nachladen (rund 2,1 MB weniger)
# API-Fassung: Grenzen, die sonst eingebettet sind, ebenfalls als Datei nachladen (wahlen.js: Schlüssel je Art); rund 3,4 MB weniger
GEO_NACH_API = {"kommunen": ("geo/kommunen_nrw.geojson", "id"), "wahlkreise-bund": ("geo/wahlkreise_bund.geojson", "nr"),
                "kreise-de": ("geo/kreise_de.geojson", "id")}


def wahlkreise_bund_schlank(fc):
    """Bundestagswahlkreise nur mit Grenze, Nummer, Name und Land (Ergebnisse stehen im Wahlregister)."""
    for ft in fc["features"]:
        ft["properties"] = {k: ft["properties"][k] for k in ("nr", "name", "land")}
    return fc


def geo_nach_api():
    """{art: (Inhalt als JSON-Text, Schlüssel)} der in der API-Fassung ausgelagerten Grenzen."""
    aus = {}
    for art, (datei, schluessel) in GEO_NACH_API.items():
        p = HIER / datei
        if p.exists():
            fc = json.loads(p.read_text())
            if art == "wahlkreise-bund":
                fc = wahlkreise_bund_schlank(fc)
            aus[art] = (json.dumps(fc, ensure_ascii=False, separators=(",", ":")), schluessel)
    return aus


def wahlen_aufteilen(ab=WERTE_NACHLADEN_AB):
    """Wahlregister für die Seite: große Einheiten (Gemeinden) ohne Werte, dafür mit "nach" (Datei) und "anzahl"; zurück (Register, {Datei: Werte})."""
    pfad = HIER / "data/wahlen.json"
    if not pfad.exists():
        return None, {}
    d, dateien = json.loads(pfad.read_text()), {}
    for w in d["wahlen"]:
        for u in w.get("einheiten") or []:
            if len(u.get("werte") or {}) >= ab:
                datei = f"wahlgeo/werte-{w['id']}-{u['id']}.json"
                dateien[datei] = u["werte"]
                u.update({"werte": {}, "nach": datei, "anzahl": len(dateien[datei])})
    return d, dateien


def wahlgeo_schreiben(ziel, api=False):
    """Kopiert die nachzuladenden Wahlkreisgrenzen nach <ziel>/wahlgeo/<art>.json, dazu die ausgelagerten Gemeindewerte; gibt die Dateien zurück.
    api=True: zusätzlich Kommunen, Bundestagswahlkreise und Kreise, Werte schon ab WERTE_NACHLADEN_AB_API."""
    ziel = Path(ziel)
    (ziel / "wahlgeo").mkdir(parents=True, exist_ok=True)
    out = []
    for art, datei in WAHL_GEO:
        if (HIER / datei).exists():
            (ziel / "wahlgeo" / f"{art}.json").write_text((HIER / datei).read_text(), encoding="utf-8")
            out.append(ziel / "wahlgeo" / f"{art}.json")
    if api:
        for art, (inhalt, _) in geo_nach_api().items():
            (ziel / "wahlgeo" / f"{art}.json").write_text(inhalt, encoding="utf-8")
            out.append(ziel / "wahlgeo" / f"{art}.json")
    for datei, werte in wahlen_aufteilen(WERTE_NACHLADEN_AB_API if api else WERTE_NACHLADEN_AB)[1].items():
        (ziel / datei).write_text(json.dumps(werte, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        out.append(ziel / datei)
    return out


def seite(terminal_seite, api=False):
    """Terminal-Seite (Fragment ohne Dokumentgerüst) -> Weltkugel-Fragment. api=True: Stammdaten-Details nicht einbetten."""
    v = HIER / "vendor/maplibre-gl"
    mlcss = (v / "maplibre-gl.css").read_text()
    mljs = "\n".join(z for z in (v / "maplibre-gl.js").read_text().splitlines() if not z.startswith("//# sourceMappingURL"))
    glyphen = {p.name.rsplit("-0-255", 1)[0]: base64.b64encode(p.read_bytes()).decode() for p in sorted((HIER / "geo/glyphs").glob("*-0-255.pbf"))}
    laender = (HIER / "geo/laender.geojson").read_text()
    s = sitze()
    tab = tabelle_schlank(tabelle()) if api else tabelle()
    teile = [
        terminal_seite.replace("<title>Terminal</title>", "<title>Weltkugel-Terminal</title>", 1),
        "<style>\n" + mlcss + "\n</style>",
        "<style>\n" + (HIER / "src/globus.css").read_text() + "\n</style>",
        SCHALE,
        '<script id="geo-laender" type="application/json">' + _js(laender) + "</script>",
        '<script id="geo-sitze" type="application/json">' + _js(json.dumps(s, ensure_ascii=False, separators=(",", ":"))) + "</script>",
        '<script id="geo-tabelle" type="application/json">' + _js(json.dumps(tab, ensure_ascii=False, separators=(",", ":"))) + "</script>",
        '<script id="geo-glyphen" type="application/json">' + json.dumps(glyphen) + "</script>",
        '<script id="geo-stufen" type="application/json">' + (_js((HIER / "data/handel_stufen.json").read_text()) if (HIER / "data/handel_stufen.json").exists() else "null") + "</script>",
        "<script>\n" + mljs + "\n</script>",
        "<script>\n" + (HIER / "src/globus.js").read_text() + "\n</script>",
        # Wahlen (Politik & Wahlen, Ansicht Wahlen): einheitliches Wahlregister (wahlen_daten.py) und Kreisgrenzen für die Europawahl
        "<style>\n" + (HIER / "src/wahlen.css").read_text() + "\n</style>",
        '<script id="kreise-de-geo" type="application/json">' + (_js((HIER / "geo/kreise_de.geojson").read_text()) if (HIER / "geo/kreise_de.geojson").exists() and not api else "null") + "</script>",
        # Wahlkreisgrenzen einzelner Länder werden nicht eingebettet, sondern bei Bedarf nachgeladen (dist/wahlgeo/<art>.json, siehe wahlgeo_schreiben)
        '<script id="wa-geo-nachladen" type="application/json">' + json.dumps({**{art: f"wahlgeo/{art}.json" for art, datei in WAHL_GEO if (HIER / datei).exists()},
                                                                                **({art: f"wahlgeo/{art}.json" for art in geo_nach_api()} if api else {})}) + "</script>",
        '<script id="wa-geo-schluessel" type="application/json">' + json.dumps({art: k for art, (_, k) in GEO_NACH_API.items()} if api else {}) + "</script>",
        '<script id="wahlen-daten" type="application/json">' + _js(json.dumps(wahlen_aufteilen(WERTE_NACHLADEN_AB_API if api else WERTE_NACHLADEN_AB)[0], ensure_ascii=False, separators=(",", ":"))) + "</script>",
        "<script>\n" + (HIER / "src/wahlen.js").read_text() + "\n</script>",
        # Unternehmensnetz: eigene Ebene und eigenes Panel, hängt sich über GLOBUS.ebene und das Ereignis "globus:firma" ein
        "<style>\n" + (HIER / "src/netz.css").read_text() + "\n</style>",
        '<script id="geo-netze" type="application/json">' + _js(json.dumps(netze(), ensure_ascii=False, separators=(",", ":"))) + "</script>",
        "<script>\n" + (HIER / "src/netz.js").read_text() + "\n</script>",
    ]
    return "\n".join(teile), len(s["zeilen"])
