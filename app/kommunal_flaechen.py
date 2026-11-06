#!/usr/bin/env python3
"""Gebietsgrenzen der Kommunen -> app/geo/kommunen_nrw.geojson

Quelle: Bundesamt für Kartographie und Geodäsie (BKG), Verwaltungsgebiete 1:250 000 (VG250), Stand 31.12.2025,
Datenlizenz Deutschland – Namensnennung – Version 2.0 (https://gdz.bkg.bund.de/). Das Archiv enthält ganz Deutschland
mit Amtlichem Gemeindeschlüssel (AGS); das Skript nimmt nur die Länder, für die Wahldaten vorliegen (LAENDER, bisher NRW = 05).
Es lädt das Shape-Archiv, rechnet von ETRS89/UTM 32N nach WGS84 um, vereinfacht leicht und ordnet jede Fläche
einem Gebiet aus data/kommunal.json zu:
  Gemeinden und kreisfreie Städte: die Wikidata-Lage (geo/kommunen_lage.json) liegt in der Fläche,
  Kreise: über den Namen (Kreisfläche ohne "Kreis").
Eigenschaften je Fläche: id, ags, ebene ("gem", "stadt", "kreis"), name. Nur Flächen mit GF = 4 (Land ohne Gewässer).
  pip install pyshp pyproj shapely;  python3 app/kommunal_flaechen.py
"""
import io, json, re, sys, zipfile
from pathlib import Path

import requests
import shapefile
from pyproj import Transformer
from shapely.geometry import Point, shape, mapping
from shapely.ops import transform

HIER = Path(__file__).parent
URL = "https://daten.gdz.bkg.bund.de/produkte/vg/vg250_ebenen_1231/aktuell/vg250_12-31.utm32s.shape.ebenen.zip"
LAENDER = ("05",)       # Landesschlüssel der Länder mit Wahldaten (05 = Nordrhein-Westfalen)
AUS = HIER / "geo/kommunen_nrw.geojson"
T = Transformer.from_crs("EPSG:25832", "EPSG:4326", always_xy=True)


def lesen(z, name):
    pre = "vg250_ebenen_1231/" + name
    r = shapefile.Reader(shp=io.BytesIO(z.read(pre + ".shp")), dbf=io.BytesIO(z.read(pre + ".dbf")), shx=io.BytesIO(z.read(pre + ".shx")), encoding="utf-8")
    out = []
    for rec, sh in zip(r.records(), r.shapes()):
        a = rec.as_dict()
        if a["GF"] == 4 and a["AGS"].startswith(LAENDER):
            out.append((a, transform(T.transform, shape(sh.__geo_interface__))))
    return out


def nn(s):
    return re.sub(r"[^a-zäöüß]", "", s.lower().replace("a.d.", "an der"))


def runden(g):
    return json.loads(json.dumps(mapping(g), separators=(",", ":")), parse_float=lambda x: round(float(x), 4))


def main():
    cache = Path(sys.argv[1]) if len(sys.argv) > 1 else None          # optional: schon geladenes Archiv
    if cache and cache.exists():
        z = zipfile.ZipFile(cache)
    else:
        buf = io.BytesIO()
        for _ in range(8):                       # Verbindung bricht bei großen Archiven zuweilen ab: ab der erreichten Stelle fortsetzen
            try:
                kopf = {"Range": f"bytes={buf.tell()}-"} if buf.tell() else {}
                with requests.get(URL, stream=True, timeout=120, headers=kopf) as r:
                    r.raise_for_status()
                    for teil in r.iter_content(1 << 20):
                        buf.write(teil)
                break
            except requests.exceptions.RequestException as e:
                print("Abbruch, setze fort:", e, file=sys.stderr)
        else:
            raise SystemExit("Download des VG250-Archivs gescheitert")
        z = zipfile.ZipFile(buf)
    gem, krs = lesen(z, "VG250_GEM"), lesen(z, "VG250_KRS")
    gebiete = json.loads((HIER / "data/kommunal.json").read_text())["gebiete"]
    lage = json.loads((HIER / "geo/kommunen_lage.json").read_text())
    feats, benutzt, fehlt = [], set(), []
    for g in gebiete:
        if g["typ"] in ("Kreis", "Städteregion"):
            kn = nn(re.sub(r"^Kreis ", "", g["name"]))      # VG250 führt Kreise als "Heinsberg", "Rhein-Kreis Neuss", "Städteregion Aachen"
            f = [(a, s) for a, s in krs if nn(a["GEN"]) == kn and a["BEZ"] != "Kreisfreie Stadt"]
            ebene = "kreis"
        else:
            p = Point(lage.get(g["id"], [0, 0]))
            f = [(a, s) for a, s in gem if s.contains(p)]
            ebene = "stadt" if g["typ"] == "kreisfreie Stadt" else "gem"
        if len(f) != 1:
            fehlt.append((g["name"], len(f)))
            continue
        a, s = f[0]
        if a["AGS"] in benutzt and ebene != "kreis":
            fehlt.append((g["name"], "doppelt"))
            continue
        benutzt.add(a["AGS"])
        feats.append({"type": "Feature", "properties": {"id": g["id"], "ags": a["AGS"], "ebene": ebene, "name": re.sub(r"^Kreis ", "", g["name"])}, "geometry": runden(s.simplify(0.0004, preserve_topology=True))})
    AUS.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(feats)} Flächen von {len(gebiete)} Gebieten, {AUS.stat().st_size // 1024} KB; ohne Fläche: {fehlt}")


if __name__ == "__main__":
    main()
