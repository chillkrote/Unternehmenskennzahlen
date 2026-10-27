"""Erzeugt aus dem Langformat eine Excel mit einem Blatt je Kennzahl (Zeilen = Unternehmen, Spalten = Jahre).

Die Jahresspalten ergeben sich aus den Daten; neue Jahre erscheinen ohne Codeänderung.
Aufruf: python3 -I excel_export.py
"""
import csv
from collections import defaultdict
from pathlib import Path

import openpyxl
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

HIER = Path(__file__).resolve().parents[1]
BLAETTER = [("bilanzsumme", "Bilanzsumme (Mio. €)"), ("eigenkapital", "Eigenkapital (Mio. €)"),
            ("fonds_340g", "Fonds § 340g (Mio. €)"), ("jahresueberschuss", "Jahresüberschuss (Mio. €)"),
            ("cet1_quote", "CET1-Quote"), ("gk_quote", "Gesamtkapitalquote"), ("leverage_ratio", "Verschuldungsquote"),
            ("lcr", "LCR"), ("nsfr", "NSFR")]
QUOTEN = {"cet1_quote", "gk_quote", "leverage_ratio", "lcr", "nsfr"}


def main():
    stamm = {r["unternehmen_id"]: r for r in csv.DictReader(open(HIER / "stammdaten.csv", encoding="utf-8"))}
    # (kennzahl, unternehmen) -> {jahr: (wert, rechnungslegung, ebene)}
    daten = defaultdict(dict)
    for r in csv.DictReader(open(HIER / "zeitreihe_lang.csv", encoding="utf-8")):
        # HGB-Reihen je Jahr, aufsichtliche Reihen je Stichtag (Quartale)
        daten[(r["kennzahl"], r["unternehmen_id"])][r["stichtag"][:4] if r["rechnungslegung"] == "HGB" else r["stichtag"]] = (float(r["wert"]), r["rechnungslegung"], r["ebene"])
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for kz, titel in BLAETTER:
        ids = sorted({u for (k, u) in daten if k == kz}, key=lambda u: (stamm[u]["gruppe"], stamm[u]["name"]))
        if not ids:
            continue
        jahre = sorted({j for u in ids for j in daten[(kz, u)]})
        ws = wb.create_sheet(titel.split(" (")[0][:31])
        ws.append(["Gruppe", "Rolle", "Bank"] + jahre + ["Rechnungslegung / Ebene (letztes Jahr)"])
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="1F2A37")
        for u in ids:
            reihe = daten[(kz, u)]
            letzte = reihe[max(reihe)]
            ws.append([stamm[u]["gruppe"], stamm[u]["rolle"], stamm[u]["name"]]
                      + [reihe[j][0] if j in reihe else "n. v." for j in jahre] + [f"{letzte[1]} / {letzte[2]}"])
        fmt = "0.00%" if kz in QUOTEN else "#,##0.0"
        for row in ws.iter_rows(min_row=2, min_col=4, max_col=3 + len(jahre)):
            for c in row:
                c.number_format = fmt
        for i, w in enumerate([22, 10, 44] + [12] * len(jahre) + [30], 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = "D2"
    # Bundesbank-Gruppenreihen (Jahre als Spalten), falls vorhanden
    gdatei = HIER / "gruppen_lang.csv"
    if gdatei.exists():
        g = defaultdict(dict)
        for r in csv.DictReader(open(gdatei, encoding="utf-8")):
            g[(r["gruppe"], r["kennzahl"], r["einheit"])][r["stichtag"][:4]] = float(r["wert"])
        jahre = sorted({j for v in g.values() for j in v})
        ws = wb.create_sheet("Gruppen (Bundesbank)")
        ws.append(["Gruppe", "Kennzahl", "Einheit"] + jahre)
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="1F2A37")
        for (gruppe, kz, einheit), v in sorted(g.items()):
            ws.append([gruppe, kz, einheit] + [v.get(j, "n. v.") for j in jahre])
        for i, w in enumerate([26, 34, 10] + [11] * len(jahre), 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = "D2"
    wb.save(HIER / "Zeitreihen_Banken.xlsx")
    print("gespeichert:", HIER / "Zeitreihen_Banken.xlsx", wb.sheetnames)


if __name__ == "__main__":
    main()
