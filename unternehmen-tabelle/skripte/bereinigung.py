"""Gezielte Bereinigung der Unternehmen-Tabelle: nur eindeutige Fälle, alles andere als Prüfliste.

Aufruf: python3 unternehmen-tabelle/skripte/bereinigung.py
Liest/schreibt unternehmen-tabelle/Unternehmen_Tabelle.xlsx und .csv und schreibt bereinigung_protokoll.csv und bereinigung_pruefliste.csv.

Regeln
1. Zeilen, deren Name eine Spaltenüberschrift der Quelle ist, werden anhand ihrer Website/Quelle umbenannt (3 bekannte Fälle).
2. Zusammenlegen zweier Zeilen desselben Landes (oder Land "Sonstige"), wenn die Gruppe genau zwei Zeilen hat,
   die eine aus einer Börsenliste stammt (Name endet auf "(CODE)" und Ticker passt) oder nur aus einem Kürzel besteht,
   die andere der Basissatz ist, ISIN/LEI sich nicht widersprechen und höchstens eine Zeile eine Unternehmens-ID hat.
   Die Basiszeile behält ihre Werte, leere Felder werden aus der Börsenzeile gefüllt, Vermerk in "Beschreibung".
3. Alles andere (3+ Zeilen, gleiche Namen mit verschiedenen Tickern) kommt in die Prüfliste.
"""
import csv, re, sys, collections
from pathlib import Path
import openpyxl
sys.path.insert(0, str(Path(__file__).parent))
from deutschland_einfuegen import norm

REPO = Path(__file__).resolve().parents[2]
T = REPO / 'unternehmen-tabelle'
FREMD = {'company name', 'decimal places', 'isin', 'name', 'ticker', 'symbol'}

def code_von(name):
    m = re.search(r'\(([A-Za-z0-9.\-]+)\)\s*$', name)
    return m.group(1) if m else None

def tk(t): return str(t or '').split('.')[0].upper()

wb = openpyxl.load_workbook(T / 'Unternehmen_Tabelle.xlsx'); ws = wb['Unternehmen']
head = [c.value for c in ws[1]]
rows = [list(r) for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]
ids = [x[0] for x in list(csv.reader(open(T / 'Unternehmen_Tabelle.csv', encoding='utf-8-sig'), delimiter=';'))[1:]]
assert len(ids) == len(rows)
prot = []; weg = set()
UMBENENNEN = {'isin': 'Fielmann Group', 'decimal places': 'Korea Investment Corporation (KIC)', 'company name': 'Yatra Online'}
for i, r in enumerate(rows):
    alt = str(r[0]).strip().lower()
    if alt in UMBENENNEN:
        prot.append(('umbenannt', UMBENENNEN[alt], r[2], r[0], '')); r[15] = (r[15] + ' | ' if r[15] else '') + 'Bereinigung: Name war Spaltenüberschrift "%s", nach Website/Quelle umbenannt' % r[0]; r[0] = UMBENENNEN[alt]
def bank_zeile(r):  # stammt aus Börsenliste / Kürzel
    c = code_von(r[0])
    return (c is not None and tk(c) == tk(r[5])) or (r[5] and re.fullmatch(r'[A-Z0-9]{2,5}', str(r[0]).strip()) and str(r[0]).strip() == str(r[5]).strip()) or re.fullmatch(r'[A-Z0-9]{2,5}', str(r[0]).strip()) is not None
gr = collections.defaultdict(list)
for i, r in enumerate(rows):
    if i in weg: continue
    gr[norm(r[0])].append(i)
# Kürzel-Zeilen (Name = Ticker einer anderen Zeile) gesondert
tick = collections.defaultdict(list)
for i, r in enumerate(rows):
    if r[5] and i not in weg: tick[(r[2], str(r[5]).upper())].append(i)
pruef = []
def verschmelze(k, d, grund):
    a, b = rows[k], rows[d]
    ch = []
    for j in range(1, 15):
        if not a[j] and b[j]: a[j] = b[j]; ch.append(head[j])
    if a[2] == 'Sonstige' and b[2] != 'Sonstige': a[2] = b[2]; ch.append('Land')
    a[15] = (a[15] + ' | ' if a[15] else '') + 'Bereinigung: Doppelzeile "%s" zusammengelegt (%s)%s' % (b[0], grund, ', ergänzt: ' + ', '.join(ch) if ch else '')
    weg.add(d); prot.append(('zusammengelegt', a[0], a[2], b[0], ', '.join(ch)))
def vertraeglich(a, b):
    if a[4] and b[4] and a[4] != b[4]: return False
    if a[10] and b[10] and a[10] != b[10]: return False
    return True
for n, idx in gr.items():
    idx = [i for i in idx if i not in weg]
    if len(idx) < 2 or not n: continue
    lands = {rows[i][2] for i in idx}
    # gleiche Landgruppe oder Sonstige + ein Land
    if len(lands - {'Sonstige'}) > 1: continue
    if len(idx) != 2:
        pruef.append(('mehr als zwei Zeilen', rows[idx[0]][0], '|'.join(str(rows[i][0]) for i in idx), '|'.join(str(rows[i][5] or '') for i in idx))); continue
    i, j = idx
    ri, rj = rows[i], rows[j]
    bi, bj = bank_zeile(ri), bank_zeile(rj)
    if bi == bj: pruef.append(('beide gleichartig', ri[0], rj[0], '%s|%s' % (ri[5], rj[5]))); continue
    k, d = (j, i) if bi else (i, j)   # k = Basis, d = Börsenzeile
    if ids[d] and ids[k]: pruef.append(('beide mit ID', rows[k][0], rows[d][0], '')); continue
    if ids[d]: k, d = d, k
    if not vertraeglich(rows[k], rows[d]): pruef.append(('ISIN/LEI widersprüchlich', rows[k][0], rows[d][0], '')); continue
    ck = tk(code_von(rows[d][0]) or rows[d][5]); tkk = tk(rows[k][5])
    if tkk and ck and tkk != ck: pruef.append(('Ticker verschieden', rows[k][0], rows[d][0], '%s|%s' % (rows[k][5], rows[d][5]))); continue
    verschmelze(k, d, 'gleicher Name, Ticker passt')
# Kürzel-Zeilen wie WOW/XRO (Name = Ticker) in die Zeile mit diesem Ticker
for i, r in enumerate(rows):
    if i in weg or not re.fullmatch(r'[A-Z0-9]{2,5}', str(r[0]).strip()) or r[5]: continue
    c = [j for j in tick.get((r[2], str(r[0]).strip().upper()), []) if j != i and j not in weg]
    if len(c) == 1 and not ids[i]: verschmelze(c[0], i, 'Name war nur das Kürzel')
keep = [i for i in range(len(rows)) if i not in weg]
ws.delete_rows(2, ws.max_row)
for i in keep: ws.append(rows[i])
wb.save(T / 'Unternehmen_Tabelle.xlsx')
with open(T / 'Unternehmen_Tabelle.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f, delimiter=';'); w.writerow(['unternehmen_id'] + head)
    for i in keep: w.writerow([ids[i]] + ['' if v is None else v for v in rows[i]])
# id_zuordnung: Namen bleiben (nur Zeilen ohne ID entfallen)
with open(T / 'bereinigung_protokoll.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['aktion', 'name_behalten', 'land', 'name_entfernt', 'ergaenzt']); w.writerows(prot)
with open(T / 'bereinigung_pruefliste.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['grund', 'name_1', 'name_2', 'ticker']); w.writerows(pruef)
print(collections.Counter(p[0] for p in prot), collections.Counter(p[0] for p in pruef), len(keep))
