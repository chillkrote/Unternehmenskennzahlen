"""Regionaldaten für die Weltkugel (Volkswirtschaft, Kreisebene): volkswirtschaft/regional/*.csv (abruf_regional.py) -> kompaktes JSON.

Schlüssel ist der Kreisschlüssel (AGS, wie geo/kreise_de.geojson und die Wahlergebnisse je Kreis), damit Karte, Wahl- und
Wirtschaftsdaten ohne weitere Zuordnung zusammenpassen; der NUTS-3-Code steht je Region dabei (API: /regions/{code}).
Format: {"stand", "quelle", "jahre": [2000, …], "serien": [{id, name, einheit, format, art, hinweis, letzter, datensatz}],
         "regionen": {ags: [nuts3, name, land]}, "werte": {serie: {ags: [wert je Jahr oder null]}}}
"""
import csv
import json
from pathlib import Path

HIER = Path(__file__).resolve().parent
ORDNER = HIER.parent / "volkswirtschaft" / "regional"
DATEI = HIER / "data" / "regional.json"


def _csv(name):
    p = ORDNER / name
    if not p.exists():
        return []
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def lade():
    serien, regionen = _csv("serien.csv"), _csv("regionen.csv")
    if not serien or not regionen:
        return None
    ags = {r["nuts3"]: r["ags"] for r in regionen}
    roh, jahre = {}, set()
    for z in _csv("zeitreihe_lang.csv"):
        if z["geo"] in ags:
            roh.setdefault(z["serie_id"], {}).setdefault(ags[z["geo"]], {})[z["zeit"]] = float(z["wert"])
            jahre.add(z["zeit"])
    jahre = sorted(jahre)

    def rund(v):
        return None if v is None else (round(v) if abs(v) >= 1000 else round(v, 2))
    werte = {sid: {a: [rund(w.get(j)) for j in jahre] for a, w in sorted(g.items())} for sid, g in roh.items()}
    return {"stand": max(s["abruf"] for s in serien),
            "quelle": "Arbeitskreis „Volkswirtschaftliche Gesamtrechnungen der Länder“ (Statistische Ämter des Bundes und der Länder), "
                      "Kreisergebnisse Reihe 2 Band 1; BIP in Kaufkraftstandards: Eurostat",
            "lizenz": "VGRdL: Vervielfältigung und Verbreitung mit Quellenangabe gestattet; Eurostat: CC BY 4.0", "jahre": [int(j) for j in jahre],
            "serien": [{"id": s["serie_id"], "name": s["name"], "einheit": s["einheit"], "format": s["format"], "art": s["art"], "kern": s["kern"] == "1",
                        "hinweis": s["hinweis"], "letzter": s["letzter_zeitraum"], "stand_quelle": s["stand_quelle"], "datensatz": s["datensatz"],
                        "quelle": s["quelle"]}
                       for s in serien if s["serie_id"] in werte],
            "regionen": {r["ags"]: [r["nuts3"], r["name"], r["land"]] for r in regionen},
            "werte": werte}


def schreiben():
    d = lade()
    if d is None:
        return None
    DATEI.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return DATEI


if __name__ == "__main__":
    p = schreiben()
    print(p, round(p.stat().st_size / 1e6, 2), "MB" if p else "keine Regionaldaten")
