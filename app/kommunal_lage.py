#!/usr/bin/env python3
"""Lage (Längen-/Breitengrad) der Kommunen aus Wikidata (CC0) -> app/geo/kommunen_lage.json

Wikidata führt für jede Gemeinde den Amtlichen Gemeindeschlüssel (P439) und die Koordinate (P625). Zuordnung zu den Gebieten
in data/kommunal.json über Name (ohne Klammerzusatz) und Kreis; kreisfreie Städte über den 8-stelligen Schlüssel mit 000 am Ende.
Kreise haben bei Wikidata meist keine Koordinate: Punkt = Mittelwert der Lagen ihrer Gemeinden.
Der Abruf läuft nur von Hand (python3 app/kommunal_lage.py); kommunal_daten.py liest die Datei.
"""
import json, re, sys
from pathlib import Path
import requests

HIER = Path(__file__).parent
AUS = HIER / "geo/kommunen_lage.json"
Q = '''SELECT ?s ?l ?ags ?c ?kl WHERE { ?s wdt:P439 ?ags . FILTER(STRSTARTS(?ags,"05")) ?s wdt:P625 ?c . ?s rdfs:label ?l FILTER(LANG(?l)="de")
 OPTIONAL { ?s wdt:P131 ?k . ?k rdfs:label ?kl FILTER(LANG(?kl)="de") } }'''


def nn(s):
    return re.sub(r"[^a-zäöüß]", "", re.sub(r"\(.*?\)", "", s.lower()))


def punkt(c):
    m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", c)
    return [round(float(m.group(1)), 4), round(float(m.group(2)), 4)]


def main():
    r = requests.get("https://query.wikidata.org/sparql", params={"query": Q, "format": "json"},
                     headers={"User-Agent": "Unternehmenskennzahlen/1.0 (Kommunen NRW)"}, timeout=180)
    r.raise_for_status()
    wd = [{k: v["value"] for k, v in x.items()} for x in r.json()["results"]["bindings"]]
    gebiete = json.loads((HIER / "data/kommunal.json").read_text())["gebiete"]
    out, fehlt = {}, []
    for g in gebiete:
        if g["typ"] in ("Kreis", "Städteregion"):
            continue
        c = [x for x in wd if nn(x["l"]) == nn(g["name"]) and len(x["ags"]) == 8]
        if g["typ"] == "kreisfreie Stadt":
            c = [x for x in c if x["ags"].endswith("000")] or ([x for x in c if g["name"] == "Aachen" and x["ags"] == "05334002"])
        else:
            if len(c) > 1:
                c = [x for x in c if nn(x.get("kl", "")) == nn(g["kreis"])] or c
        if len(c) >= 1:
            out[g["id"]] = punkt(c[0]["c"])
        else:
            fehlt.append(g["name"])
    for g in gebiete:
        if g["typ"] in ("Kreis", "Städteregion"):
            pk = [out[x["id"]] for x in gebiete if x["typ"] == "Gemeinde" and x["kreis"] == g["name"] and x["id"] in out]
            if pk:
                out[g["id"]] = [round(sum(p[0] for p in pk) / len(pk), 4), round(sum(p[1] for p in pk) / len(pk), 4)]
            else:
                fehlt.append(g["name"])
    AUS.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(out)} von {len(gebiete)} Gebieten mit Lage; fehlt: {fehlt}")


if __name__ == "__main__":
    main()
