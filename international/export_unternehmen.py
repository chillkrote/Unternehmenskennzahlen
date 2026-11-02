"""Exportiert die Unternehmenstabelle aus der Datenbank wieder als CSV (und optional XLSX) im Format von unternehmen-tabelle/.
Excel/CSV bleiben damit Ausgabeformate; die Datenbank ist die Arbeitsfassung.
Aufruf: INTERNATIONAL_DATABASE_URL=... python3 international/export_unternehmen.py AUSGABE.csv [--xlsx AUSGABE.xlsx] [--mit-pruefmarken]
"""
import argparse
import csv
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
import db  # noqa: E402
from import_unternehmen import SPALTEN  # noqa: E402

SQL = ("SELECT entity_id, name, legal_form, country_name, seat, isin, ticker, exchange, listed, sector, nace, lei, register_no, website, is_bank,"
       " indices, description, source_url, row_key FROM international.company_register WHERE active ORDER BY row_no")


def zeilen_holen(conn):
    for r in conn.execute(SQL):
        z = ["" if v is None else v for v in r]
        z[8] = "ja" if z[8] else "nein"
        z[14] = "ja" if z[14] else "nein"
        yield z


def exportieren(conn, ziel, xlsx=None, mit_marken=False):
    marken = {}
    if mit_marken:
        for k, c in conn.execute("SELECT row_key, string_agg(code, '|' ORDER BY code) FROM international.review_flag WHERE decision IS NULL GROUP BY row_key"):
            marken[k] = c
    kopf = SPALTEN + (["pruefmarken"] if mit_marken else [])
    n = 0
    zeilen = []
    for z in zeilen_holen(conn):
        k = z.pop()
        if mit_marken:
            z.append(marken.get(k, ""))
        zeilen.append(z)
        n += 1
    with open(ziel, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\r\n")
        w.writerow(kopf)
        w.writerows(zeilen)
    if xlsx:
        from openpyxl import Workbook
        wb = Workbook(write_only=True)
        ws = wb.create_sheet("Unternehmen")
        ws.append(kopf[1:])                     # wie die Importvorlage: ohne ID-Spalte
        for z in zeilen:
            ws.append(z[1:])
        wb.save(xlsx)
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("ziel")
    ap.add_argument("--xlsx")
    ap.add_argument("--mit-pruefmarken", action="store_true")
    a = ap.parse_args()
    with db.verbinden() as c:
        print(exportieren(c, a.ziel, a.xlsx, a.mit_pruefmarken), "Zeilen exportiert")
