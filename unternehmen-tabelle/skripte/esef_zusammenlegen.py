"""Legt sieben Namenszeilen (Stammdaten-ID ohne Daten) mit der Tabellenzeile derselben Gesellschaft zusammen (Stand 02.11.2026).

Auslöser: die ESEF-Piloten NL/IT/ES haben ISIN und LEI auf die vorhandene ID gesetzt; die Tabellenzeile mit derselben ISIN hatte noch keine ID.
Behalten wird die Zeile mit den Daten (Kürzel-Name), sie übernimmt die ID der Namenszeile; die Namenszeile entfällt.
Aufruf: python3 unternehmen-tabelle/skripte/esef_zusammenlegen.py
"""
import csv
from pathlib import Path
import openpyxl
T = Path(__file__).resolve().parents[1]
# (behaltene Datenzeile, entfallende Namenszeile mit ID, ISIN zur Kontrolle)
MERGES = [
 ('Abn Amro', 'ABN AMRO BANK', 'NL0011540547'),
 ('ASML', 'ASML HLDG', 'NL0010273215'),
 ('AMS.MC', 'AMADEUS IT GROUP', 'ES0109067019'),
 ('IBE.MC', 'IBERDROLA', 'ES0144580Y14'),
 ('NTGY.MC', 'Naturgy Energy Group', 'ES0116870314'),
 ('SAN.MC', 'BCO SANTANDER', 'ES0113900J37'),
 ('TEF.MC', 'TELEFONICA', 'ES0178430E18'),
]
wb = openpyxl.load_workbook(T / 'Unternehmen_Tabelle.xlsx'); ws = wb['Unternehmen']
head = [c.value for c in ws[1]]
rows = [list(r) for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]
ids = [x[0] for x in list(csv.reader(open(T / 'Unternehmen_Tabelle.csv', encoding='utf-8-sig'), delimiter=';'))[1:]]
assert len(ids) == len(rows)
weg, log = set(), []
for keep, dup, isin in MERGES:
    ks = [i for i, r in enumerate(rows) if r[0] == keep and r[4] == isin and not ids[i]]
    ds = [i for i, r in enumerate(rows) if r[0] == dup and ids[i] and not r[4]]
    assert len(ks) == 1 and len(ds) == 1, (keep, dup, ks, ds)
    k, d = ks[0], ds[0]
    ch = []
    for j in range(1, 15):
        if not rows[k][j] and rows[d][j]: rows[k][j] = rows[d][j]; ch.append(head[j])
    ids[k] = ids[d]
    rows[k][15] = (rows[k][15] + ' | ' if rows[k][15] else '') + 'ESEF-Pilot: Namenszeile "%s" (%s) zusammengelegt%s' % (dup, ids[d], (', ergänzt: ' + ', '.join(ch)) if ch else '')
    weg.add(d); log.append(('zusammengelegt', keep, dup, ids[d], isin))
keep_idx = [i for i in range(len(rows)) if i not in weg]
ws.delete_rows(2, ws.max_row)
for i in keep_idx: ws.append(rows[i])
wb.save(T / 'Unternehmen_Tabelle.xlsx')
with open(T / 'Unternehmen_Tabelle.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f, delimiter=';'); w.writerow(['unternehmen_id'] + head)
    for i in keep_idx: w.writerow([ids[i]] + ['' if v is None else v for v in rows[i]])
with open(T / 'bereinigung_protokoll_esef.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['aktion', 'name_behalten', 'name_entfernt', 'unternehmen_id', 'isin']); w.writerows(log)
print(len(keep_idx), len(log))
