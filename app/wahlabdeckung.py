#!/usr/bin/env python3
"""Maschinenlesbare Übersicht der Wahldaten: je Wahl im Wahlregister (app/data/wahlen.json) Quelle, Tiefe und Lücken.

Schreibt wahlen/abdeckung.csv. Stufen:
  A  amtliche Quelle mit Untereinheiten und Grenzen (Wahlkreise, Kreise, Gemeinden)
  B  amtliche Quelle, nur Gesamtergebnis oder Untereinheiten ohne Grenzen
  C  Wahlartikel (Wikipedia): Stimmenanteile, keine absoluten Stimmen, keine Untereinheiten
  D  nur Sitzverteilung (IPU Parline oder heutige Zusammensetzung), keine Stimmen

Aufruf: python3 app/wahlabdeckung.py [--pruefen]   (--pruefen: Fehler, wenn die Datei im Repository nicht zum Wahlregister passt)
"""
import csv
import io
import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
REGISTER = HIER / "data" / "wahlen.json"
ZIEL = HIER.parent / "wahlen" / "abdeckung.csv"
SPALTEN = ["id", "ebene", "land", "gebiet", "name", "gremium", "datum", "status", "stufe", "stimmen_absolut", "stimmarten", "vergleich_vorwahl",
           "sitze", "einheiten_mit_grenzen", "einheiten_ohne_grenzen", "quelle", "lizenz", "luecken"]


def stufe(w):
    q = (w.get("quelle") or {}).get("name", "")
    sekundaer = q.startswith(("Wikipedia", "IPU"))
    stimmen = any(w["g"].get("s", {}).values())
    if not stimmen:
        return "D"
    if sekundaer:
        return "C"
    return "A" if w["e"] >= 3 or any(u.get("geo") for u in w.get("einheiten") or []) else "B"     # E3/E4: die Kommune selbst ist die Karteneinheit


def zeile(w):
    g = w["g"]
    listen = [l for l in (g.get("s") or {}).values() if l]
    absolut = any(x[1] is not None for l in listen for x in l)
    vor = any(len(x) > 3 and x[3] is not None for l in listen for x in l)
    anzahl = lambda u: u.get("anzahl") or len(u.get("werte") or {})
    mit = [f"{u['name']} ({anzahl(u)})" for u in w.get("einheiten") or [] if u.get("geo")]
    ohne = [f"{u['name']} ({anzahl(u)})" for u in w.get("einheiten") or [] if not u.get("geo")]
    s = stufe(w)
    luecken = []
    if not listen:
        luecken.append("keine Stimmen")
    elif not absolut:
        luecken.append("keine absoluten Stimmen")
    if listen and not vor:
        luecken.append("kein Vergleich zur Vorwahl")
    if not g.get("sitze"):
        luecken.append("keine Sitze")
    if not mit and w["e"] <= 2:
        luecken.append("keine Untereinheiten auf der Karte")
    if g.get("bet") is None:
        luecken.append("keine Wahlbeteiligung")
    if s in "CD":
        luecken.append("keine amtliche Quelle")
    q = w.get("quelle") or {}
    return {"id": w["id"], "ebene": f"E{w['e']}", "land": w["land"], "gebiet": w.get("gebiet") or "", "name": w.get("name") or "", "gremium": w.get("gremium") or "",
            "datum": w.get("datum") or "", "status": w.get("status") or "", "stufe": s, "stimmen_absolut": "ja" if absolut else "nein",
            "stimmarten": "/".join(t for _, t in w.get("stimmarten") or []), "vergleich_vorwahl": "ja" if vor else "nein", "sitze": "ja" if g.get("sitze") else "nein",
            "einheiten_mit_grenzen": "; ".join(mit), "einheiten_ohne_grenzen": "; ".join(ohne), "quelle": q.get("name", ""), "lizenz": q.get("lizenz", ""),
            "luecken": "; ".join(luecken)}


def tabelle(register=None):
    d = register or json.loads(REGISTER.read_text(encoding="utf-8"))
    return sorted((zeile(w) for w in d["wahlen"]), key=lambda z: (z["ebene"], z["land"], z["gebiet"], z["datum"], z["id"]))


def text(zeilen):
    aus = io.StringIO()
    w = csv.DictWriter(aus, SPALTEN, lineterminator="\n")
    w.writeheader()
    w.writerows(zeilen)
    return aus.getvalue()


def main(argv=None):
    neu = text(tabelle())
    if "--pruefen" in (argv if argv is not None else sys.argv[1:]):
        if not ZIEL.exists() or ZIEL.read_text(encoding="utf-8") != neu:
            print(f"{ZIEL} passt nicht zum Wahlregister: python3 app/wahlabdeckung.py ausführen", file=sys.stderr)
            return 1
        return 0
    ZIEL.write_text(neu, encoding="utf-8")
    from collections import Counter
    z = tabelle()
    print(f"{len(z)} Wahlen -> {ZIEL}; je Ebene und Stufe:", dict(sorted(Counter(x['ebene'] + x['stufe'] for x in z).items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
