"""Zieht das Blatt "Quellen-Dokumente" nach der Bereinigung nach: Verweise auf zusammengelegte Zeilen zeigen auf die behaltene Zeile.
Liest bereinigung_protokoll.csv. Verweise auf umbenannte Zeilen mit Spaltenüberschrift als Namen werden auf den neuen Namen gesetzt."""
import csv
from pathlib import Path
import openpyxl
T = Path(__file__).resolve().parents[1]
neu = {}; loesch = set()
for a in csv.DictReader(open(T / 'bereinigung_protokoll.csv', encoding='utf-8')):
    if a['aktion'] == 'zusammengelegt': neu[a['name_entfernt']] = a['name_behalten']
    elif a['aktion'] == 'umbenannt': neu[a['name_entfernt']] = a['name_behalten']
zweit = T / 'bereinigung_protokoll_pruefliste.csv'
if zweit.exists():
    for a in csv.DictReader(open(zweit, encoding='utf-8')):
        if a['aktion'] == 'zusammengelegt': neu[a['name_entfernt']] = a['name_behalten']
wb = openpyxl.load_workbook(T / 'Unternehmen_Tabelle.xlsx'); ws = wb['Quellen-Dokumente']
namen = {r[0] for r in wb['Unternehmen'].iter_rows(min_row=2, values_only=True)}
n = d = 0
for row in range(ws.max_row, 1, -1):
    v = ws.cell(row, 1).value
    if v in neu and v not in namen: ws.cell(row, 1).value = neu[v]; n += 1
    elif v in loesch and v not in namen: ws.delete_rows(row); d += 1
wb.save(T / 'Unternehmen_Tabelle.xlsx'); print('umgehängt', n, 'gelöscht', d)
