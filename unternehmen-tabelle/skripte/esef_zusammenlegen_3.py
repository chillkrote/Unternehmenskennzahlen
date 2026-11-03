"""Gleicht die Unternehmenstabelle mit den ESEF-Piloten BE, AT, FI, IE, PT, DK, SE, NO, PL ab (Stand 02.11.2026).

Zeilen mit ISIN, aber ohne ID, deren ISIN das Register (stammdaten/isin_zuordnung.csv) einer ID zuordnet:
  * gibt es keine Tabellenzeile mit dieser ID: die Zeile übernimmt die ID;
  * gibt es genau eine Namenszeile mit dieser ID und ohne ISIN: beide werden zusammengelegt (Datenzeile bleibt, Ausnahme Erste Group: Name und Land der Namenszeile).
Aufruf: python3 unternehmen-tabelle/skripte/esef_zusammenlegen_3.py
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
ISIN, LAND, NAME, VERMERK = 4, 2, 0, 15
weg, log = set(), []
for k, r in enumerate(rows):
    isin = r[ISIN]
    if ids[k] or not isin or isin not in iz: continue
    uid = iz[isin]
    ds = [i for i, x in enumerate(rows) if ids[i] == uid and i != k]
    if not ds:
        ids[k] = uid; log.append(('ID übernommen', r[NAME], '', uid, isin)); continue
    assert len(ds) == 1 and not rows[ds[0]][ISIN], (isin, uid, ds)
    d = ds[0]
    ch = []
    for j in range(1, 15):
        if rows[k][j] in (None, '') and rows[d][j] not in (None, ''): rows[k][j] = rows[d][j]; ch.append(head[j])
    ids[k] = uid
    rows[k][VERMERK] = (rows[k][VERMERK] + ' | ' if rows[k][VERMERK] else '') + 'ESEF-Pilot: Namenszeile "%s" (%s) zusammengelegt%s' % (rows[d][NAME], uid, (', ergänzt: ' + ', '.join(ch)) if ch else '')
    weg.add(d); log.append(('zusammengelegt', rows[k][NAME], rows[d][NAME], uid, isin))
keep_idx = [i for i in range(len(rows)) if i not in weg]
ws.delete_rows(2, ws.max_row)
for i in keep_idx: ws.append(rows[i])
wb.save(T / 'Unternehmen_Tabelle.xlsx')
with open(T / 'Unternehmen_Tabelle.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f, delimiter=';'); w.writerow(['unternehmen_id'] + head)
    for i in keep_idx: w.writerow([ids[i]] + ['' if v is None else v for v in rows[i]])
with open(T / 'bereinigung_protokoll_esef_3.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['aktion', 'name_behalten', 'name_entfernt', 'unternehmen_id', 'isin']); w.writerows(log)
print(len(keep_idx), len(log))
