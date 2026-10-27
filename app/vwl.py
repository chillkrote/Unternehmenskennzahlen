"""Datenschicht des volkswirtschaftlichen Terminals: volkswirtschaft/*.csv -> kompaktes JSON für das Terminal.

Alles kommt aus den CSV-Dateien, die volkswirtschaft/skripte/abruf_eurostat.py schreibt (serien, laender, themen,
zeitreihe_lang) und aus berichte.csv. Neue Reihen erscheinen im Terminal ohne Codeänderung."""
import csv
import json
from pathlib import Path

HIER = Path(__file__).resolve().parent
ORDNER = HIER.parent / "volkswirtschaft"


def _csv(name):
    p = ORDNER / name
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return [{k: (v or "").strip() for k, v in r.items() if k} for r in csv.DictReader(fh)]


def lade():
    """Gibt None zurück, wenn keine Reihen vorliegen."""
    serien = _csv("serien.csv")
    if not serien:
        return None
    daten = {}
    for r in _csv("zeitreihe_lang.csv"):
        try:
            v = float(r["wert"])
        except ValueError:
            continue
        daten.setdefault(r["serie_id"], {}).setdefault(r["geo"], []).append([r["zeit"], v])
    for geos in daten.values():
        for pts in geos.values():
            pts.sort()
    keep = ("serie_id", "thema", "name", "einheit", "format", "art", "frequenz", "kern", "quelle", "datensatz", "filter", "url",
            "abruf", "erster_zeitraum", "letzter_zeitraum", "hinweis")
    s = [{**{k: x[k] for k in keep if k in x}, "kern": x.get("kern") == "1"} for x in serien if x["serie_id"] in daten]
    return {"serien": s, "laender": _csv("laender.csv"), "themen": _csv("themen.csv"), "berichte": _csv("berichte.csv"), "daten": daten,
            "stand": max((x.get("abruf", "") for x in serien), default="")}


if __name__ == "__main__":
    d = lade()
    print(len(d["serien"]), "Reihen", sum(len(p) for g in d["daten"].values() for p in g.values()), "Werte")
