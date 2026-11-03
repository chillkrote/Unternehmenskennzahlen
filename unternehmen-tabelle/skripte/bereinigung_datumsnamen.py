"""Bereinigt 31 US-Zeilen, deren Name ein Datum ist ("July 8, 1997"). Es sind Berichts-/IR-Dokumente, keine Unternehmen.
Das Unternehmen ergibt sich aus der Website/URL. Existiert es schon als Zeile, wird die Datumszeile entfernt und das Dokument im Blatt
"Quellen-Dokumente" auf die vorhandene Zeile umgehängt; sonst wird die Zeile umbenannt. Nicht erkennbare Fälle bleiben stehen (Prüfliste).
Protokoll: bereinigung_protokoll_datumsnamen.csv."""
import csv, re
from pathlib import Path
import openpyxl
T = Path(__file__).resolve().parents[1]
MON = r'(January|February|March|April|May|June|July|August|September|October|November|December)'
# Teil der Website/URL -> (Unternehmen vorhanden als Zeile | neuer Name)
ZUORD = [('lockheedmartin.com', 'Lockheed Martin Corp.'), ('NYSE_WMT', 'WALMART INC CMN'), ('goldmansachs.com', 'Goldman Sachs Group'),
 ('PHILIPS', 'KONINKLIJKE PHILIPS'), ('t-mobile.com', 'T-MOBILE US CMN'), ('etrade.net', 'E*Trade'), ('quifax', 'Equifax Inc.'),
 ('accenture.com', 'Accenture plc'), ('usatodayco.com', 'USA TODAY Co.'), ('investor.ti.com', 'Texas Instruments'), ('astrazeneca.com', 'AstraZeneca'),
 ('vertiv.com', 'VERTIV HOLDINGS CLASS A'), ('tesla.com', 'TESLA, INC.'), ('ubs.com', 'UBS GROUP AG'), ('mdt-', 'Medtronic plc'),
 ('pginvestor.com', 'Procter & Gamble'), ('merck.com', 'Merck & Co.'), ('att.com', 'AT&T Inc')]
wb = openpyxl.load_workbook(T / 'Unternehmen_Tabelle.xlsx'); ws = wb['Unternehmen']
rows = [list(r) for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]
ids = [x[0] for x in list(csv.reader(open(T / 'Unternehmen_Tabelle.csv', encoding='utf-8-sig'), delimiter=';'))[1:]]
assert len(ids) == len(rows)
byname = {r[0]: i for i, r in enumerate(rows) if not re.fullmatch(MON + r' \d{1,2}, \d{4}', str(r[0]))}
log, weg, umbenannt, neu = [], set(), {}, {}
for i, r in enumerate(rows):
    if not re.fullmatch(MON + r' \d{1,2}, \d{4}', str(r[0]).strip()) or r[2] != 'USA': continue
    z = next((n for k, n in ZUORD if k in (r[12] or '') + (r[16] or '')), None)
    if z is None: log.append((r[0], 'bleibt', '', 'Unternehmen aus URL nicht erkennbar: ' + str(r[16])[:90])); continue
    if z in byname and not ids[i]:
        neu[r[0]] = z; weg.add(i); log.append((r[0], 'zusammengelegt', z, 'Dokumentzeile, Unternehmen vorhanden'))
    elif z in byname: log.append((r[0], 'bleibt', z, 'hat ID, nicht gelöscht'))
    else:
        neu[r[0]] = z; byname[z] = i; r[0] = z
        r[15] = (r[15] + ' | ' if r[15] else '') + 'Bereinigung: Name war ein Datum, nach Unternehmen aus der URL umbenannt'
        log.append((neu_alt := [k for k, v in neu.items() if v == z][0], 'umbenannt', z, 'Unternehmen aus URL'))
rows = [r for i, r in enumerate(rows) if i not in weg]; ids = [x for i, x in enumerate(ids) if i not in weg]
q = wb['Quellen-Dokumente']; n = 0
for row in range(2, q.max_row + 1):
    v = q.cell(row, 1).value
    if v in neu: q.cell(row, 1).value = neu[v]; n += 1
ws.delete_rows(2, ws.max_row)
for r in rows: ws.append(r)
wb.save(T / 'Unternehmen_Tabelle.xlsx')
head = [c.value for c in ws[1]]
with open(T / 'Unternehmen_Tabelle.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter=';'); w.writerow(['unternehmen_id'] + head)
    for i, r in zip(ids, rows): w.writerow([i] + ['' if v is None else v for v in r])
with open(T / 'bereinigung_protokoll_datumsnamen.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f); w.writerow(['name_alt', 'aktion', 'name_neu', 'grund']); w.writerows(log)
import collections
print(collections.Counter(a[1] for a in log), 'Dokumente umgehängt', n, 'Zeilen', len(rows))
