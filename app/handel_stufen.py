"""Weltkugel, Zoomstufen: erzeugt data/handel_stufen.json (Nachbarländer, Nettostrom) für Stufe 3.
(Kontinentströme von Stufe 1 und Länderströme von Stufe 2 rechnet die Oberfläche selbst aus data/handel.json.)

 - nachbarn: Länder mit gemeinsamer Grenze (aus gemeinsamen Eckpunkten der Natural-Earth-Flächen), für Stufe 3.
 - strom: Nettostromimporte je Land (TWh, positiv = Nettoimport) aus Ember über das Open-Access-Paket von Our World in Data
   (owid-energy-data.csv, CC BY 4.0). Es gibt keine bilateralen Stromflüsse in frei zugänglicher Form (ENTSO-E braucht ein
   Konto bzw. Token, die Daten gibt es nur für Europa).

    python3 app/handel_stufen.py [--strom pfad/zur/owid-energy-data.csv]
"""
import argparse
import csv
import io
import json
import urllib.request
from collections import defaultdict
from pathlib import Path

HIER = Path(__file__).resolve().parent
OWID = "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv"


def nachbarn(feat):
    """ISO2 -> Menge ISO2: Flächen, die mindestens zwei Eckpunkte teilen (auf 0,001 Grad gerundet)."""
    pkt = defaultdict(set)
    def lauf(c, iso):
        if isinstance(c[0], (int, float)):
            pkt[iso].add((round(c[0], 3), round(c[1], 3)))
        else:
            for x in c:
                lauf(x, iso)
    for f in feat:
        lauf(f["geometry"]["coordinates"], f["properties"]["iso"])
    index = defaultdict(set)
    for iso, s in pkt.items():
        for p in s:
            index[p].add(iso)
    zaehl = defaultdict(int)
    for isos in index.values():
        l = sorted(isos)
        for i, a in enumerate(l):
            for b in l[i + 1:]:
                zaehl[(a, b)] += 1
    out = defaultdict(list)
    for (a, b), n in zaehl.items():
        if n >= 2:
            out[a].append(b); out[b].append(a)
    return {k: sorted(v) for k, v in sorted(out.items())}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strom")
    a = ap.parse_args()
    geo = json.loads((HIER / "geo/laender.geojson").read_text())["features"]
    handel = json.loads((HIER / "data/handel.json").read_text())

    # Strom
    if a.strom:
        text = Path(a.strom).read_text(encoding="utf-8")
    else:
        with urllib.request.urlopen(urllib.request.Request(OWID, headers={"User-Agent": "Unternehmenskennzahlen-Terminal/1.0"}), timeout=120) as r:
            text = r.read().decode("utf-8")
    a3 = {f["properties"]["a3"]: f["properties"]["iso"] for f in geo}
    strom = {}
    for r in csv.DictReader(io.StringIO(text)):
        iso = a3.get(r["iso_code"])
        if iso and r["net_elec_imports"]:
            j = int(r["year"])
            if iso not in strom or j > strom[iso]["jahr"]:
                strom[iso] = {"jahr": j, "netto": float(r["net_elec_imports"]),
                              "bedarf": float(r["electricity_demand"]) if r["electricity_demand"] else None}
    out = {"nachbarn": nachbarn(geo), "strom": strom,
           "quellen": {"handel": handel["quelle"], "strom": "Ember (Yearly Electricity Data) über Our World in Data, CC BY 4.0",
                       "strom_url": "https://ourworldindata.org/electricity-mix", "handel_abruf": handel["abruf"]}}
    ziel = HIER / "data/handel_stufen.json"
    ziel.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"{ziel} {ziel.stat().st_size // 1024} KB; Stromländer {len(strom)}; Nachbarländer {len(out['nachbarn'])}")


main()
