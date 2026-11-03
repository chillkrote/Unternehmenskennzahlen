"""Ländergrenzen für die Weltkugel: Natural Earth 1:50 Mio. (gemeinfrei) -> app/geo/laender.geojson.

Behalten werden nur die Felder, die die Oberfläche braucht (ISO-Code, deutscher Name, Kontinent, Bevölkerung und BIP laut
Natural Earth als Grundangabe für Länder ohne VWL-Daten, Position der Beschriftung). Koordinaten auf 0,01 Grad (gut 1 km) gerundet.
Nur neu bauen, wenn Natural Earth eine neue Fassung herausgibt:

    python3 app/geo/laender_bauen.py [pfad/zu/ne_50m_admin_0_countries.geojson]
"""
import json
import sys
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
# Natural Earth führt einige Inselstaaten als "Seven seas (open ocean)"; die Oberfläche kennt nur sechs Kontinente
KONTINENT_KORREKTUR = {"MV": "Asia", "MU": "Africa", "SC": "Africa"}
URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"


def runde(c):
    if isinstance(c[0], (int, float)):
        return [round(c[0], 2), round(c[1], 2)]
    out = [runde(x) for x in c]
    if out and isinstance(out[0][0], (int, float)):        # Ring: doppelte Punkte nach dem Runden entfernen
        r = [out[0]] + [p for i, p in enumerate(out[1:], 1) if p != out[i - 1]]
        return r if len(r) >= 4 else out
    return out


def main():
    quelle = sys.argv[1] if len(sys.argv) > 1 else None
    roh = json.load(open(quelle)) if quelle else json.load(urllib.request.urlopen(URL))
    feats = []
    for f in roh["features"]:
        p = f["properties"]
        iso = p["ISO_A2_EH"] if p["ISO_A2_EH"] not in ("-99", "") else p["ADM0_A3"]
        feats.append({"type": "Feature", "id": len(feats), "properties": {
            "iso": iso, "a3": p["ADM0_A3"], "name": p.get("NAME_DE") or p["NAME"], "name_en": p["NAME"], "kontinent": KONTINENT_KORREKTUR.get(iso, p["CONTINENT"]),
            "region": p["SUBREGION"], "einwohner": p["POP_EST"], "einwohner_jahr": p["POP_YEAR"], "bip_mio_usd": p["GDP_MD"],
            "bip_jahr": p["GDP_YEAR"], "einkommen": p["INCOME_GRP"][3:], "lx": round(p["LABEL_X"], 2), "ly": round(p["LABEL_Y"], 2)},
            "geometry": {"type": f["geometry"]["type"], "coordinates": runde(f["geometry"]["coordinates"])}})
    ziel = HIER / "laender.geojson"
    ziel.write_text(json.dumps({"type": "FeatureCollection", "quelle": "Natural Earth 1:50m Admin 0 Countries (gemeinfrei), naturalearthdata.com",
                                "features": feats}, ensure_ascii=False, separators=(",", ":")))
    print(len(feats), "Länder ->", ziel, ziel.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
