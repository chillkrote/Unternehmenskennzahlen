"""Trägt ISIN (und LEI, falls leer) aus us_isin_ergaenzung.csv (GLEIF-Abgleich, nur Status "ok") in US-Zeilen ein.
Aufruf: python3 us_isin_einfuegen.py <us_isin_ergaenzung.csv>
Zuordnung per Name + Ticker (Zeilennummern der Datei beziehen sich auf einen älteren Stand). Nur leere Felder; steht die ISIN schon bei einer anderen Zeile, wird nichts eingetragen und die Zeile gemeldet."""
import csv, sys, re
from pathlib import Path
import openpyxl
T = Path(__file__).resolve().parents[1]
def luhn(s):
    d = ''.join(str(int(c, 36)) for c in s); t = 0
    for i, x in enumerate(reversed(d)):
        v = int(x) * (2 if i % 2 == 1 else 1); t += v // 10 + v % 10
    return t % 10 == 0
wb = openpyxl.load_workbook(T / 'Unternehmen_Tabelle.xlsx'); ws = wb['Unternehmen']
rows = [list(r) for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]
ids = [x[0] for x in list(csv.reader(open(T / 'Unternehmen_Tabelle.csv', encoding='utf-8-sig'), delimiter=';'))[1:]]
assert len(ids) == len(rows)
vorh = {r[4]: i for i, r in enumerate(rows) if r[4]}; lei = {r[10] for r in rows if r[10]}
ok, skip = 0, []
for x in csv.DictReader(open(sys.argv[1], encoding='utf-8')):
    if x['status'] != 'ok' or not re.fullmatch(r'US[A-Z0-9]{9}\d', x['isin']) or not luhn(x['isin']): continue
    m = [i for i, r in enumerate(rows) if r[2] == 'USA' and r[0] == x['name_tabelle'] and (r[5] or '') == x['ticker']]
    if len(m) != 1: skip.append((x['name_tabelle'], 'Zeile nicht eindeutig')); continue
    r = rows[m[0]]
    if r[4]: continue
    if x['isin'] in vorh: skip.append((x['name_tabelle'], f"ISIN schon bei {rows[vorh[x['isin']]][0]}")); continue
    r[4] = x['isin']; vorh[x['isin']] = m[0]; f = ['ISIN']
    if not r[10] and x['lei'] and x['lei'] not in lei: r[10] = x['lei']; lei.add(x['lei']); f.append('LEI')
    r[15] = (r[15] + ' | ' if r[15] else '') + f"GLEIF (Name/Ticker-Abgleich, bitte prüfen): {', '.join(f)}"; ok += 1
print('eingetragen', ok); [print('übersprungen:', s) for s in skip]
ws.delete_rows(2, ws.max_row)
for r in rows: ws.append(r)
wb.save(T / 'Unternehmen_Tabelle.xlsx')
head = [c.value for c in ws[1]]
with open(T / 'Unternehmen_Tabelle.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter=';'); w.writerow(['unternehmen_id'] + head)
    for i, r in zip(ids, rows): w.writerow([i] + ['' if v is None else v for v in r])
