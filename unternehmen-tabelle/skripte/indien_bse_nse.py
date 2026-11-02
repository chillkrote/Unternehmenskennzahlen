"""Arbeitet die BSE-Listen (Equity.csv, EQT0.csv) und die NSE-Liste (EQUITY_L.csv) in die Unternehmenstabelle ein (Indien).
Aufruf: python3 indien_bse_nse.py <Equity.csv> <EQT0.csv> <EQUITY_L.csv>
Zuordnung: ISIN, dann Ticker (BSE Security Id / NSE Symbol, nur bei Zeilen ohne ISIN), dann eindeutiger Name.
Nur leere Felder werden gefüllt; jede Ergänzung steht in der Beschreibung (bitte prüfen). Eine ISIN steht nie bei zwei Zeilen."""
import csv, re, sys
from pathlib import Path
import openpyxl
T = Path(__file__).resolve().parents[1]
def isin_ok(s):
    if not re.fullmatch(r'[A-Z]{2}[A-Z0-9]{9}\d', s or ''): return False
    d = ''.join(str(int(c, 36)) for c in s); return sum(int(x) if i % 2 == 0 else (lambda v: v // 10 + v % 10)(int(x) * 2) for i, x in enumerate(reversed(d))) % 10 == 0
STOP = {'limited', 'ltd', 'private', 'pvt', 'the', 'co', 'company', 'corporation', 'corp', 'india', 'indian', 'of', 'and'}
def norm(n): return ' '.join(w for w in re.sub(r'[^a-z0-9 ]', ' ', (n or '').lower().replace('&', ' and ')).split() if w not in STOP)
def lies(p):
    with open(p, encoding='utf-8-sig', newline='') as f: return [{(k or '').strip(): (v if isinstance(v, str) else '').strip() for k, v in r.items()} for r in csv.DictReader(f)]
eq, eqt, nse = (lies(a) for a in sys.argv[1:4])
wb = openpyxl.load_workbook(T / 'Unternehmen_Tabelle.xlsx'); ws = wb['Unternehmen']
rows = [list(r) for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]
ids = [x[0] for x in list(csv.reader(open(T / 'Unternehmen_Tabelle.csv', encoding='utf-8-sig'), delimiter=';'))[1:]]
assert len(ids) == len(rows)
byisin, bytk, byname, names = {}, {}, {}, set(r[0] for r in rows)
for i, r in enumerate(rows):
    if r[4]: byisin.setdefault(r[4], []).append(i)
    if r[2] in ('India', 'Sonstige'):
        if r[5]: bytk.setdefault(r[5].upper(), []).append(i)
        byname.setdefault(norm(r[0]), []).append(i)
# Eintragsliste: ISIN -> Angaben
cand = {}
def add(isin, name, tk, boerse, quelle, info):
    if not isin_ok(isin): return
    c = cand.setdefault(isin, {'name': name, 'tk': '', 'bse': '', 'nse': '', 'q': set(), 'info': []})
    if tk and boerse == 'BSE' and not c['bse']: c['bse'] = tk
    if tk and boerse == 'NSE' and not c['nse']: c['nse'] = tk
    c['q'].add(quelle); c['info'].append(info)
    if boerse == 'NSE' or not c['name']: c['name'] = name or c['name']
for r in eq:
    if r.get('Status', 'Active') == 'Active': add(r['ISIN No'], r['Issuer Name'], r['Security Id'], 'BSE', 'BSE', 'BSE Gruppe ' + r['Group'])
for r in eqt:
    add(r['ISIN No'], r['Issuer Name'], '', 'BSE', 'BSE', 'BSE T0-Liste')
for r in nse:
    add(r['ISIN NUMBER'], r['NAME OF COMPANY'], r['SYMBOL'], 'NSE', 'NSE', 'NSE Serie ' + r['SERIES'] + ', Listing ' + r['DATE OF LISTING'])
QB = 'https://www.bseindia.com/corporates/List_Scrips.html'; QN = 'https://www.nseindia.com/market-data/securities-available-for-trading'
st = dict(neu=0, isin=0, tk=0, bs=0, belegt=0, name=0)
def setf(r, j, v, felder, nm):
    if not r[j] and v: r[j] = v; felder.append(nm)
def vermerk(r, quelle, felder, unsicher):
    if not felder: return
    t = f"{quelle} (Abgleich per {unsicher}, bitte prüfen): {', '.join(felder)}"
    r[15] = (r[15] + ' | ' if r[15] else '') + t
for isin, c in cand.items():
    ziel, how = None, ''
    if isin in byisin: ziel, how = byisin[isin][0], 'ISIN'
    else:
        tks = [t for t in (c['nse'], c['bse']) if t]
        for t in tks:
            tr = [i for i in bytk.get(t.upper(), []) if not rows[i][4]]
            if len(tr) == 1: ziel, how = tr[0], 'Ticker'; break
        if ziel is None:
            nr = [i for i in byname.get(norm(c['name']), []) if not rows[i][4]]
            if len(nr) == 1 and norm(c['name']): ziel, how = nr[0], 'Name'
    quelle = ' und '.join(sorted(c['q'])) + '-Liste'
    if ziel is not None:
        r = rows[ziel]; f = []
        if how != 'ISIN':
            setf(r, 4, isin, f, 'ISIN'); byisin.setdefault(isin, []).append(ziel); st['isin'] += 1
        if r[2] == 'Sonstige' and how != 'ISIN': r[2] = 'India'; f.append('Land')
        elif r[2] == 'Sonstige': pass
        tk = c['nse'] or c['bse']
        if not r[5] and tk: r[5] = tk; f.append('Ticker'); st['tk'] += 1
        if not r[6]:
            r[6] = 'National Stock Exchange of India' if c['nse'] else 'Bse Ltd'; f.append('Börse'); st['bs'] += 1
        vermerk(r, quelle, f, how)
        if f: st['belegt'] += 1
    else:
        name = c['name']
        if name in names: name = f"{name} ({c['nse'] or c['bse']})"
        if name in names: continue
        names.add(name)
        b = 'National Stock Exchange of India' if c['nse'] else 'Bse Ltd'
        row = [name, None, 'India', None, isin, c['nse'] or c['bse'], b, 'ja', 'sonstige', None, None, None, None, 'nein',
               ' / '.join(sorted(c['q'])), f"Quelle {quelle} ({'; '.join(sorted(set(c['info']))[:2])}); Branche/Bank-Flag Platzhalter, bitte prüfen",
               QN if c['nse'] else QB]
        rows.append(row); ids.append(''); byisin[isin] = [len(rows) - 1]; st['neu'] += 1
print(st, len(rows))
wb['Unternehmen'].delete_rows(2, ws.max_row)
for r in rows: ws.append(r)
wb.save(T / 'Unternehmen_Tabelle.xlsx')
head = [c.value for c in ws[1]]
with open(T / 'Unternehmen_Tabelle.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter=';'); w.writerow(['unternehmen_id'] + head)
    for i, r in zip(ids, rows): w.writerow([i] + ['' if v is None else v for v in r])
