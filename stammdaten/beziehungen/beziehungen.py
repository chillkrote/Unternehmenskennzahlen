"""Unternehmensnetze: Standorte und Beziehungen je Konzern (für die Weltkugel).

Je Konzern eine Datei daten/<Unternehmens-ID>_<name>.json (Aufbau siehe README.md). Dieses Skript
  * prüft die Dateien (python3 beziehungen.py pruefen),
  * ergänzt fehlende Koordinaten über OpenStreetMap Nominatim, Ortsmitte, mit Cache (python3 beziehungen.py koordinaten),
  * liefert alle Netze kompakt für die Weltkugel (laden(), von app/globus.py aufgerufen).

Nur freie Quellen; Nominatim höchstens eine Anfrage pro Sekunde (Nutzungsrichtlinie)."""
import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
DATEN = HIER / "daten"
CACHE = HIER / "koordinaten_cache.json"
IDS = HIER.parent / "unternehmen_ids.csv"

ARTEN_STANDORT = {"hauptsitz", "hauptsitz_tochter", "fahrzeugwerk", "komponentenwerk", "werk", "filiale", "batterie", "finanzen", "vertrieb",
                  "entwicklung", "joint_venture", "beteiligung", "partner", "kunde", "eigentuemer", "lieferant"}
ARTEN_BEZIEHUNG = {"tochter", "produktion", "lieferung", "logistik", "joint_venture", "beteiligung", "eigentuemer", "kunde", "lieferant", "partner", "filiale"}


def dateien():
    return sorted(DATEN.glob("U*.json"))


def lesen(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def pruefen(d, name="", bekannte_ids=None):
    """Liste von Fehlern (leer = in Ordnung)."""
    f = []
    q = d.get("quellen", {})
    ids = [s["id"] for s in d.get("standorte", [])]
    if len(ids) != len(set(ids)):
        f.append("doppelte Standort-IDs: " + ", ".join(sorted({i for i in ids if ids.count(i) > 1})))
    ids = set(ids)
    for k, v in q.items():
        if not (v.get("titel") and v.get("url", "").startswith("http") and v.get("jahr")):
            f.append(f"Quelle {k}: titel, url und jahr nötig")
    for s in d.get("standorte", []):
        w = f"Standort {s.get('id')}"
        if s.get("art") not in ARTEN_STANDORT:
            f.append(f"{w}: unbekannte art {s.get('art')!r}")
        for feld in ("name", "ort", "land", "taetigkeit"):
            if not s.get(feld):
                f.append(f"{w}: {feld} fehlt")
        if not s.get("quellen"):
            f.append(f"{w}: keine Quelle")
        for k in s.get("quellen", []) + [z.get("quelle") for z in s.get("kennzahlen", []) if z.get("quelle")]:
            if k not in q:
                f.append(f"{w}: Quelle {k} nicht definiert")
        for z in s.get("kennzahlen", []):
            if not (isinstance(z.get("wert"), (int, float)) and z.get("einheit") and z.get("jahr")):
                f.append(f"{w}: Kennzahl {z.get('name')!r} braucht wert, einheit, jahr")
        if s.get("lat") is None or s.get("lon") is None:
            f.append(f"{w}: Koordinate fehlt (python3 beziehungen.py koordinaten)")
        if bekannte_ids is not None and s.get("unternehmen_id") and s["unternehmen_id"] not in bekannte_ids:
            f.append(f"{w}: Unternehmens-ID {s['unternehmen_id']} nicht in stammdaten/unternehmen_ids.csv")
    for i, b in enumerate(d.get("beziehungen", [])):
        w = f"Beziehung {i + 1} ({b.get('von')} -> {b.get('nach')})"
        if b.get("von") not in ids or b.get("nach") not in ids:
            f.append(f"{w}: Standort unbekannt")
        if b.get("von") == b.get("nach"):
            f.append(f"{w}: von und nach gleich")
        if b.get("art") not in ARTEN_BEZIEHUNG:
            f.append(f"{w}: unbekannte art {b.get('art')!r}")
        if not b.get("quellen"):
            f.append(f"{w}: keine Quelle")
        for k in b.get("quellen", []):
            if k not in q:
                f.append(f"{w}: Quelle {k} nicht definiert")
        m = b.get("menge")
        if m and not (isinstance(m.get("wert"), (int, float)) and m.get("einheit") and m.get("jahr")):
            f.append(f"{w}: menge braucht wert, einheit, jahr")
    return [f"{name}: {x}" for x in f]


def bekannte_ids():
    if not IDS.exists():
        return None
    return {r["unternehmen_id"] for r in csv.DictReader(open(IDS, encoding="utf-8"))}


def alle_pruefen():
    ids, fehler = bekannte_ids(), []
    # Registerzeilen haben ebenfalls IDs (unternehmen-tabelle); dort nachsehen, bevor eine ID als unbekannt gilt
    tab = HIER.parent.parent / "unternehmen-tabelle/Unternehmen_Tabelle.csv"
    if ids is not None and tab.exists():
        ids |= {r.get("unternehmen_id", "") for r in csv.DictReader(open(tab, encoding="utf-8-sig"), delimiter=";")}
    for p in dateien():
        d = lesen(p)
        if not p.name.startswith(d.get("unternehmen_id", "?") + "_"):
            fehler.append(f"{p.name}: Dateiname passt nicht zur unternehmen_id")
        fehler += pruefen(d, p.name, ids)
    return fehler


def _nominatim(ort, land):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({"q": ort, "countrycodes": land.lower(), "format": "json", "limit": 1})
    req = urllib.request.Request(url, headers={"User-Agent": "Unternehmenskennzahlen-Weltkugel/1.0 (github.com/chillkrote/Unternehmenskennzahlen)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        t = json.loads(r.read().decode())
    return (round(float(t[0]["lat"]), 4), round(float(t[0]["lon"]), 4)) if t else None


def koordinaten():
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    for p in dateien():
        d, neu = lesen(p), 0
        for s in d["standorte"]:
            if s.get("lat") is not None and s.get("koordinate") != "ort":
                continue                                   # von Hand gesetzte Koordinate bleibt
            k = f"{s['land']}|{s['ort']}"
            if k not in cache:
                time.sleep(1.1)
                cache[k] = _nominatim(s["ort"], s["land"])
                print("Nominatim", k, cache[k])
            if not cache[k]:
                print("nicht gefunden:", k, file=sys.stderr)
                continue
            lat, lon = cache[k]
            dx, dy = s.get("versatz", [0, 0])            # mehrere Standorte im selben Ort leicht auseinanderziehen
            s["lat"], s["lon"], s["koordinate"] = round(lat + dy, 4), round(lon + dx, 4), "ort"
            neu += 1
        p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(p.name, neu, "Koordinaten gesetzt")
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def laden():
    """Alle Netze für die Weltkugel: {Unternehmens-ID: Datensatz}. Ungültige Dateien werden übersprungen (mit Hinweis)."""
    netze = {}
    for p in dateien():
        d = lesen(p)
        f = pruefen(d, p.name)
        if f:
            print(f"Unternehmensnetz {p.name} übersprungen: {f[0]} (und {len(f) - 1} weitere)", file=sys.stderr)
            continue
        netze[d["unternehmen_id"]] = d
    return netze


if __name__ == "__main__":
    befehl = sys.argv[1] if len(sys.argv) > 1 else "pruefen"
    if befehl == "koordinaten":
        koordinaten()
    fehler = alle_pruefen()
    for x in fehler:
        print(x)
    print(f"{len(dateien())} Datei(en), {len(fehler)} Fehler")
    sys.exit(1 if fehler else 0)
