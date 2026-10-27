"""Erstellt die Abrufliste für manuelle Downloads (Unternehmensregister): je Bank die kleinste Menge Geschäftsjahre,
deren Jahresabschlüsse alle noch fehlenden Bilanzsummen-Jahre abdecken (ein Abschluss enthält Berichtsjahr und Vorjahr).

Aufruf: python3 -I abrufliste.py [--von 2016]
Ergebnis: zeitreihen/abrufliste_unternehmensregister.csv, sortiert nach Bilanzsumme 2025 (Stufe A = 50 größte, B = nächste 50, C = Rest).
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LANG = REPO / "zeitreihen/zeitreihe_lang.csv"
STAMM = REPO / "zeitreihen/stammdaten.csv"
AUS = REPO / "zeitreihen/abrufliste_unternehmensregister.csv"
BIS = 2023            # 2024 und 2025 liegen mit den GJ2025-Berichten vor


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--von", type=int, default=2016)
    a = p.parse_args()
    da, groesse = defaultdict(set), {}
    with open(LANG, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["kennzahl"] == "bilanzsumme" and r["rechnungslegung"] == "HGB":
                da[r["unternehmen_id"]].add(int(r["stichtag"][:4]))
                if r["stichtag"][:4] == "2025":
                    groesse[r["unternehmen_id"]] = float(r["wert"])
    zeilen = []
    with open(STAMM, encoding="utf-8", newline="") as f:
        for s in csv.DictReader(f):
            if s["branche"] != "banken" or s["gruppe"] in ("Gruppe", ""):
                continue
            fehlt = sorted(set(range(a.von, BIS + 1)) - da.get(s["unternehmen_id"], set()))
            if not da.get(s["unternehmen_id"]):
                continue                                   # Bank ohne jeden HGB-Wert: nicht Teil der Zeitreihe
            holen, offen = [], set(fehlt)
            while offen:                                   # größtes offenes Jahr; der Abschluss deckt dieses und das Vorjahr ab
                j = max(offen)
                holen.append(j)
                offen -= {j, j - 1}
            if holen:
                zeilen.append([s["gruppe"], s["name"], s["unternehmen_id"], round(groesse.get(s["unternehmen_id"], 0)), len(fehlt), " ".join(map(str, fehlt)), " ".join(map(str, holen)), len(holen)])
    zeilen.sort(key=lambda z: -z[3])                       # größte Banken zuerst
    for i, z in enumerate(zeilen):
        z.insert(0, "A" if i < 50 else "B" if i < 100 else "C")
    with open(AUS, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["prioritaet", "gruppe", "bank", "unternehmen_id", "bilanzsumme_2025_mio_eur", "fehlende_jahre_anzahl", "fehlende_jahre", "abschluesse_zu_holen_gj", "anzahl_abschluesse"])
        w.writerows(zeilen)
    for t in "ABC":
        print("Stufe", t, sum(1 for z in zeilen if z[0] == t), "Banken,", sum(z[8] for z in zeilen if z[0] == t), "Abschlüsse")


if __name__ == "__main__":
    main()
