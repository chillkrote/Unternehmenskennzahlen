"""Ordnet Tabellenzeilen mit ISIN, aber ohne ID, die ID des Registers zu (DART-Pilot Südkorea, Stand 03.11.2026).

Gilt für Zeilen, deren ISIN stammdaten/isin_zuordnung.csv einer ID zuordnet und für die es keine andere Tabellenzeile mit dieser ID gibt (Namenszeilen
werden hier nie zusammengelegt; gäbe es eine, bricht das Skript ab). Schreibt unternehmen-tabelle/bereinigung_protokoll_dart.csv.
Aufruf: python3 unternehmen-tabelle/skripte/dart_zuordnen.py
"""
import csv
from pathlib import Path
import openpyxl
T = Path(__file__).resolve().parents[1]
REPO = T.parent
iz = {r['isin']: r['unternehmen_id'] for r in csv.DictReader(open(REPO / 'stammdaten' / 'isin_zuordnung.csv', encoding='utf-8'))}
wb = openpyxl.load_workbook(T / 'Unternehmen_Tabelle.xlsx'); ws = wb['Unternehmen']
head = [c.value for c in ws[1]]
rows = [list(r) for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]
ids = [x[0] for x in list(csv.reader(open(T / 'Unternehmen_Tabelle.csv', encoding='utf-8-sig'), delimiter=';'))[1:]]
assert len(ids) == len(rows)
ISIN, NAME, VERMERK = 4, 0, 15
vorhanden = {i for i in ids if i}
log = []
for k, r in enumerate(rows):
    isin = r[ISIN]
    if ids[k] or not isin or isin not in iz or not isin.startswith('KR'):
        continue
    uid = iz[isin]
    assert uid not in vorhanden, (isin, uid)      # andere Zeile mit dieser ID: bewusst nicht automatisch zusammenlegen
    ids[k] = uid; vorhanden.add(uid)
    r[VERMERK] = (r[VERMERK] + ' | ' if r[VERMERK] else '') + 'DART-Pilot: ID %s aus dem Register übernommen' % uid
    log.append(('ID übernommen', r[NAME], uid, isin))
for i, r in enumerate(rows):                       # Tabelle zurückschreiben
    for j, v in enumerate(r):
        ws.cell(row=i + 2, column=j + 1).value = v
wb.save(T / 'Unternehmen_Tabelle.xlsx')
with open(T / 'Unternehmen_Tabelle.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f, delimiter=';'); w.writerow(['unternehmen_id'] + head)
    for i, r in enumerate(rows): w.writerow([ids[i]] + ['' if v is None else v for v in r])
with open(T / 'bereinigung_protokoll_dart.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['aktion', 'name', 'unternehmen_id', 'isin']); w.writerows(log)
print(len(rows), len(log))
