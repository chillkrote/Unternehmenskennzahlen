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


def _prognosen():
    """Prognosen als Liste von Ausgaben: Institute (Deutschland, handgepflegt, breit) und OECD Economic Outlook (alle Länder, lang)."""
    aus = []
    for r in _csv("prognosen_institute.csv"):
        w = {}
        for j in ("2025", "2026", "2027", "2028"):
            try:
                w[j] = float(r["j" + j])
            except (KeyError, ValueError):
                pass
        if w:
            aus.append({"geo": r["geo"], "herausgeber": r["herausgeber"], "ausgabe": r["ausgabe"], "datum": r["veroeffentlicht"], "groesse": r["groesse"],
                        "einheit": r["einheit"], "werte": w, "beleg": r["beleg"], "url": r["url"], "hinweis": r["hinweis"]})
    gruppen = {}
    for r in _csv("prognosen_oecd.csv"):
        try:
            v = float(r["wert"])
        except ValueError:
            continue
        g = gruppen.setdefault((r["geo"], r["ausgabe"], r["groesse"]), {"geo": r["geo"], "herausgeber": r["herausgeber"], "ausgabe": r["ausgabe"], "datum": r["veroeffentlicht"],
                                                                         "groesse": r["groesse"], "einheit": r["einheit"], "werte": {}, "beleg": r["beleg"], "url": r["url"], "hinweis": ""})
        g["werte"][r["jahr"]] = v
    aus += list(gruppen.values())
    return aus


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
            "abruf", "erster_zeitraum", "letzter_zeitraum", "prognose_ab", "hinweis")
    s = [{**{k: x[k] for k in keep if k in x}, "kern": x.get("kern") == "1"} for x in serien if x["serie_id"] in daten]
    return {"serien": s, "laender": _csv("laender.csv"), "themen": _csv("themen.csv"), "berichte": _csv("berichte.csv"), "indikatoren": _csv("konjunkturindikatoren.csv"), "prognosen": _prognosen(), "daten": daten,
            "stand": max((x.get("abruf", "") for x in serien), default="")}


if __name__ == "__main__":
    d = lade()
    print(len(d["serien"]), "Reihen", len(d["prognosen"]), "Prognosen", sum(len(p) for g in d["daten"].values() for p in g.values()), "Werte")
