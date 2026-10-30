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
    # Historie (2015 bis 2025, lang): eine Ausgabe je Herausgeber, Ausgabe und Größe; hat bei gleicher Ausgabe Vorrang vor der breiten Datei
    hist, hist_keys = {}, set()
    for r in _csv("prognosen_institute_historie.csv"):
        try:
            v = float(r["wert"])
        except ValueError:
            continue
        g = hist.setdefault((r["geo"], r["herausgeber"], r["ausgabe"], r["groesse"]), {"geo": r["geo"], "herausgeber": r["herausgeber"], "ausgabe": r["ausgabe"], "datum": r["veroeffentlicht"],
                                                                                     "groesse": r["groesse"], "einheit": r["einheit"], "werte": {}, "beleg": r["beleg"], "url": r["url"], "hinweis": r["hinweis"]})
        g["werte"][r["jahr"]] = v
        hist_keys.add((r["herausgeber"], r["veroeffentlicht"][:7], r["groesse"]))
    for r in _csv("prognosen_institute.csv"):
        if (r["herausgeber"], r["veroeffentlicht"][:7], r["groesse"]) in hist_keys:
            continue
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
    aus += list(gruppen.values()) + list(hist.values())
    aus += _prognosen_international()
    return aus


_MON = {"Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "Mai": "05", "Jun": "06", "Jul": "07", "Aug": "08", "Sep": "09", "Okt": "10", "Nov": "11", "Dez": "12",
        "February": "02", "April": "04", "June": "06", "July": "07", "August": "08", "October": "10", "November": "11", "December": "12"}


def _monat_aus_ausgabe(a):
    """Fehlt das Veröffentlichungsdatum, gilt der Monat der Runde (Eurosystem Jun 2026 -> 2026-06, SPF 2026-Q4 -> Umfragemonat 2026-10)."""
    import re
    m = re.search(r"(\d{4})-Q([1-4])", a)
    if m:
        return f"{m.group(1)}-{(int(m.group(2)) - 1) * 3 + 1:02d}"
    m = re.search(r"\b([A-Z][a-zäöü]+)\.? (\d{4})\b", a)
    if m and m.group(1) in _MON:
        return f"{m.group(2)}-{_MON[m.group(1)]}"
    return ""


def _prognosen_international():
    """Konsensumfragen und Zentralbankprognosen anderer Länder (prognosen_international.csv): eine Zeile je Herausgeber, Ausgabe und Größe."""
    gruppen = {}
    for r in _csv("prognosen_international.csv"):
        try:
            v = float(r["wert"])
        except ValueError:
            continue
        k = (r["geo"], r["herausgeber"], r["ausgabe"], r["groesse"])
        g = gruppen.setdefault(k, {"geo": r["geo"], "herausgeber": r["herausgeber"], "ausgabe": r["ausgabe"], "datum": r["veroeffentlicht"] or _monat_aus_ausgabe(r["ausgabe"]),
                                   "groesse": r["groesse"], "einheit": r["einheit"], "werte": {}, "beleg": r["beleg"], "url": r["url"], "hinweis": r["hinweis"]})
        g["werte"][r["jahr"]] = v
    return list(gruppen.values())


def _abgleich():
    """Tatsächliche Werte, Prognosefehler und Treffsicherheit (volkswirtschaft/skripte/abgleich_prognosen.py) als kompakte Listen."""
    def zahl(x):
        try:
            return float(x)
        except ValueError:
            return None
    ist = [{"groesse": r["groesse"], "jahr": int(r["jahr"]), "vintage": r["vintage"], "wert": zahl(r["wert"]), "einheit": r["einheit"], "quelle": r["quelle"], "url": r["url"], "hinweis": r["hinweis"]}
           for r in _csv("prognosen_ist.csv")]
    fehler = [{"h": r["herausgeber"], "a": r["ausgabe"], "d": r["veroeffentlicht"], "g": r["groesse"], "j": int(r["jahr"]), "m": int(r["abstand_monate"]), "hz": r["horizont"],
               "p": zahl(r["prognose"]), "ie": zahl(r["ist_erst"]), "ia": zahl(r["ist_aktuell"]), "fe": zahl(r["fehler_erst"]), "fa": zahl(r["fehler_aktuell"])}
              for r in _csv("prognosen_fehler.csv")]
    treff = [{"h": r["herausgeber"], "g": r["groesse"], "hz": r["horizont"], "v": r["ist_vintage"], "n": int(r["n"]), "mae": zahl(r["mae"]), "bias": zahl(r["bias"]), "rmse": zahl(r["rmse"]),
              "von": int(r["jahr_von"]), "bis": int(r["jahr_bis"])} for r in _csv("prognosen_treffsicherheit.csv")]
    return {"ist": ist, "fehler": fehler, "treffsicherheit": treff}


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
    return {"serien": s, "laender": _csv("laender.csv"), "themen": _csv("themen.csv"), "berichte": _csv("berichte.csv"), "indikatoren": _csv("konjunkturindikatoren.csv"), "prognosen": _prognosen(), "abgleich": _abgleich(), "daten": daten,
            "stand": max((x.get("abruf", "") for x in serien), default="")}


if __name__ == "__main__":
    d = lade()
    print(len(d["serien"]), "Reihen", len(d["prognosen"]), "Prognosen", sum(len(p) for g in d["daten"].values() for p in g.values()), "Werte")
