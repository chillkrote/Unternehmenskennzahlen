"""Übernimmt die KM1-Werte aller Stichtage aus dem EBA-Pillar-3-Hub (Export per Oberfläche, Land Deutschland) ins Langformat.

Quelle: banken/bilanzvergleich-gj2025/rohdaten/eba-hub/eba_hub_km1_de_alle_stichtage.xlsx (Spalte 0010, EU KM1).
Zuordnung LEI -> Bank über rohdaten/eba_hub_neu_2025.json. Bestehende Zeilen werden nicht überschrieben.
Aufruf: python3 -I eba_hub_quartale.py
"""
import csv
import json
import re
import sys
from pathlib import Path

import openpyxl

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "stammdaten"))
import ids as stamm  # noqa: E402  zentrale Unternehmens-IDs (stammdaten/)
ROH = REPO / "banken/bilanzvergleich-gj2025/rohdaten"
LANG = REPO / "zeitreihen/zeitreihe_lang.csv"

# KM1-Zeile -> (kennzahl, Faktor); Beträge in EUR -> Mio. EUR, Quoten als Anteil
ZEILEN = {
    "0010": ("cet1", 1e-6), "0020": ("t1", 1e-6), "0030": ("eigenmittel", 1e-6), "0040": ("rwa", 1e-6),
    "0050": ("cet1_quote", 1), "0060": ("t1_quote", 1), "0070": ("gk_quote", 1),
    "0190": ("gk_anforderung", 1), "0210": ("leverage_exposure", 1e-6), "0220": ("leverage_ratio", 1),
    "0280": ("hqla", 1e-6), "0320": ("lcr", 1), "0350": ("nsfr", 1),
}
QUOTEN = {"cet1_quote", "t1_quote", "gk_quote", "gk_anforderung", "leverage_ratio", "lcr", "nsfr"}


def main():
    j = json.load(open(ROH / "eba_hub_neu_2025.json"))
    lei = {e["lei"]: stamm.lade().aufloesen(e["name"]) for k in ("neu", "bestehend") for e in j[k]}
    lei = {k: v for k, v in lei.items() if v}
    ws = openpyxl.load_workbook(ROH / "eba-hub/eba_hub_km1_de_alle_stichtage.xlsx").active
    werte = {}
    for r in ws.iter_rows(min_row=4, values_only=True):
        if r[0] not in lei or r[8] not in ZEILEN or r[10] != "0010" or r[14] in (None, ""):
            continue
        try:
            v = float(r[14])
        except (TypeError, ValueError):
            continue
        kz, f = ZEILEN[r[8]]
        werte[(lei[r[0]], kz, r[13].strftime("%Y-%m-%d"))] = (v * f, r[1])
    with open(LANG, encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        felder, zeilen = rd.fieldnames, list(rd)
    da = {(r["unternehmen_id"], r["kennzahl"], r["stichtag"]) for r in zeilen if r["rechnungslegung"] == "aufsichtlich"}
    neu = 0
    for (uid, kz, tag), (v, name) in sorted(werte.items()):
        if (uid, kz, tag) in da:
            continue
        neu += 1
        zeilen.append({"unternehmen_id": uid, "kennzahl": kz, "stichtag": tag, "wert": round(v, 6 if kz in QUOTEN else 3),
                       "einheit": "Anteil" if kz in QUOTEN else "Mio. EUR", "waehrung": "EUR", "rechnungslegung": "aufsichtlich",
                       "ebene": "höchste Ebene im Hub", "quelle": "EBA Pillar-3-Datenhub, EU KM1, Spalte a (Export 27.10.2026)",
                       "pruefstatus": "geparst"})
    zeilen.sort(key=lambda r: (r["unternehmen_id"], r["kennzahl"], r["stichtag"]))
    with open(LANG, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, felder)
        w.writeheader()
        w.writerows(zeilen)
    print(neu, "neue Zeilen,", len({u for u, _, _ in werte}), "Banken")


if __name__ == "__main__":
    main()
