"""Bundestagswahlkreise 2025: Grenzen und Ergebnisse je Wahlkreis (Pilot der Wahlebenen).

Quellen (Die Bundeswahlleiterin, Datenlizenz Deutschland - Namensnennung 2.0):
  Grenzen:    btw25_geometrie_wahlkreise_vg250_shp_geo.zip (Wahlkreiseinteilung, WGS84)
  Ergebnisse: opendata/btw25/csv/kerg2.csv (endgültiges Ergebnis nach Wahlkreisen)
Ausgabe: app/geo/wahlkreise_bund.geojson (je Wahlkreis: nr, name, land, wb, w, e = Erststimmen, z = Zweitstimmen).
Aufruf:  pip install pyshp shapely requests;  python3 app/wahlkreise_daten.py [geo.zip] [kerg2.csv]
"""
import csv, io, json, sys, zipfile
from pathlib import Path
import requests, shapefile
from shapely.geometry import shape, mapping

B = "https://www.bundeswahlleiterin.de/"
GEO = B + "dam/jcr/a3b60aa9-8fa5-4223-9fb4-0a3a3cebd7d1/btw25_geometrie_wahlkreise_vg250_shp_geo.zip"
ERG = B + "bundestagswahlen/2025/ergebnisse/opendata/btw25/csv/kerg2.csv"
OUT = Path(__file__).parent / "geo" / "wahlkreise_bund.geojson"

def holen(url, pfad):
    if pfad: return Path(pfad).read_bytes()
    return requests.get(url, timeout=120).content

def zahl(s):
    s = (s or "").strip()
    return int(s) if s.isdigit() else None

def main():
    geo = holen(GEO, sys.argv[1] if len(sys.argv) > 1 else None)
    z = zipfile.ZipFile(io.BytesIO(geo)); pre = next(n[:-4] for n in z.namelist() if n.endswith(".shp"))
    r = shapefile.Reader(shp=io.BytesIO(z.read(pre + ".shp")), dbf=io.BytesIO(z.read(pre + ".dbf")), shx=io.BytesIO(z.read(pre + ".shx")), encoding="utf-8")
    erg = {}
    txt = holen(ERG, sys.argv[2] if len(sys.argv) > 2 else None).decode("utf-8-sig")
    rows = csv.reader(io.StringIO(txt), delimiter=";")
    for row in rows:
        if len(row) < 12 or row[2] != "Wahlkreis": continue
        nr = int(row[3]); d = erg.setdefault(nr, {"wb": None, "w": None, "e": {}, "z": {}})
        art, name, st, n = row[7], row[8], row[10], zahl(row[11])
        if art == "System-Gruppe":
            if name == "Wahlberechtigte": d["wb"] = n
            elif name == "Wählende": d["w"] = n
        elif n and st in ("1", "2"):
            d["e" if st == "1" else "z"][name.replace("EB:", "Einzelbewerber ")] = n
    feats = []
    for sr in r.iterShapeRecords():
        nr, name, _, land = sr.record
        d = erg[nr]
        g = shape(sr.shape.__geo_interface__).simplify(0.002, preserve_topology=True)
        p = {"nr": nr, "name": name, "land": land, "wb": d["wb"], "w": d["w"]}
        for k in ("e", "z"):
            L = sorted(d[k].items(), key=lambda x: -x[1])
            p[k] = [[a, b] for a, b in L]
        feats.append({"type": "Feature", "properties": p, "geometry": {"type": g.geom_type, "coordinates": json.loads(json.dumps(mapping(g)["coordinates"], default=list))}})
        # Koordinaten runden
    def rund(c): return [rund(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(c[0], 4), round(c[1], 4)]
    for f in feats: f["geometry"]["coordinates"] = rund(f["geometry"]["coordinates"])
    OUT.write_text(json.dumps({"type": "FeatureCollection", "quelle": "Die Bundeswahlleiterin, Bundestagswahl 2025, endgültiges Ergebnis; Datenlizenz Deutschland - Namensnennung 2.0", "features": feats}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    # Plausibilität
    fehl = [f["properties"]["nr"] for f in feats if not f["properties"]["e"] or not f["properties"]["z"]]
    print(len(feats), "Wahlkreise,", OUT.stat().st_size // 1024, "KB, ohne Ergebnis:", fehl)

if __name__ == "__main__": main()
