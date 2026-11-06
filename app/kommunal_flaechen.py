#!/usr/bin/env python3
"""Gebietsgrenzen der Kommunen NRW -> app/geo/kommunen_nrw.geojson

Quelle: Geobasis NRW, Digitale Verwaltungsgrenzen NW, niedrige Stützpunktdichte (DVG2), Stand 12.11.2025,
Datenlizenz Deutschland – Zero – Version 2.0 (https://open.nrw/dataset/f9098786-f5af-4fc6-a775-5b9152c83161).
Das Skript lädt das Shape-Archiv, rechnet von ETRS89/UTM 32N nach WGS84 um, vereinfacht leicht und ordnet jede Fläche
einem Gebiet aus data/kommunal.json zu:
  Gemeinden und kreisfreie Städte: die Wikidata-Lage (geo/kommunen_lage.json) liegt in der Fläche,
  Kreise: über den Namen (Kreisfläche ohne "Kreis").
Eigenschaften je Fläche: id, ebene ("gem", "stadt", "kreis"), name.
  pip install pyshp pyproj shapely;  python3 app/kommunal_flaechen.py
"""
import io, json, re, sys, zipfile, urllib.request
from pathlib import Path

import shapefile
from pyproj import Transformer
from shapely.geometry import Point, shape, mapping
from shapely.ops import transform

HIER = Path(__file__).parent
URL = "https://www.opengeodata.nrw.de/produkte/geobasis/vkg/dvg/dvg2/dvg2_EPSG25832_Shape.zip"
AUS = HIER / "geo/kommunen_nrw.geojson"
T = Transformer.from_crs("EPSG:25832", "EPSG:4326", always_xy=True)


def lesen(z, name):
    r = shapefile.Reader(shp=io.BytesIO(z.read(name + ".shp")), dbf=io.BytesIO(z.read(name + ".dbf")), shx=io.BytesIO(z.read(name + ".shx")), encoding="utf-8")
    return [(rec.as_dict(), transform(T.transform, shape(sh.__geo_interface__))) for rec, sh in zip(r.records(), r.shapes())]


def nn(s):
    return re.sub(r"[^a-zäöüß]", "", s.lower().replace("a.d.", "an der"))


def runden(g):
    return json.loads(json.dumps(mapping(g), separators=(",", ":")), parse_float=lambda x: round(float(x), 4))


def main():
    z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(URL, timeout=120).read()))
    gem, krs = lesen(z, "dvg2gem_nw"), lesen(z, "dvg2krs_nw")
    gebiete = json.loads((HIER / "data/kommunal.json").read_text())["gebiete"]
    lage = json.loads((HIER / "geo/kommunen_lage.json").read_text())
    feats, benutzt, fehlt = [], set(), []
    for g in gebiete:
        if g["typ"] in ("Kreis", "Städteregion"):
            kn = nn(re.sub(r"^Kreis ", "", g["name"]))
            f = [(a, s) for a, s in krs if nn(a["GN"]) == kn]
            ebene = "kreis"
        else:
            p = Point(lage.get(g["id"], [0, 0]))
            f = [(a, s) for a, s in gem if s.contains(p)]
            ebene = "stadt" if g["typ"] == "kreisfreie Stadt" else "gem"
        if len(f) != 1:
            fehlt.append((g["name"], len(f)))
            continue
        a, s = f[0]
        if a["KN"] in benutzt and ebene != "kreis":
            fehlt.append((g["name"], "doppelt"))
            continue
        benutzt.add(a["KN"])
        feats.append({"type": "Feature", "properties": {"id": g["id"], "ebene": ebene, "name": re.sub(r"^Kreis ", "", g["name"])}, "geometry": runden(s.simplify(0.0003, preserve_topology=True))})
    AUS.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(feats)} Flächen von {len(gebiete)} Gebieten, {AUS.stat().st_size // 1024} KB; ohne Fläche: {fehlt}")


if __name__ == "__main__":
    main()
