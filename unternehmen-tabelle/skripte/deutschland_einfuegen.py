"""Fügt die deutschen Unternehmen des Repos (stammdaten/unternehmen_ids.csv, Land Germany) in die Unternehmen-Tabelle ein.

Aufruf: python3 unternehmen-tabelle/skripte/deutschland_einfuegen.py EINGABE.xlsx AUSGABE.xlsx

Regeln: Abgleich je Registerzeile über ISIN (haupt/weitere), LEI, dann eindeutigen normalisierten Namen im Land
Germany. Treffer: nur leere Felder füllen (Branche nur, wenn leer/"sonstige"), Vermerk in "Beschreibung".
Kein Treffer: neue Zeile. Eine ISIN/LEI steht danach nie bei zwei Zeilen. Schreibt zusätzlich
unternehmen-tabelle/id_zuordnung.csv (Tabellenname -> Unternehmens-ID U000123).
"""
import csv, re, sys, unicodedata, collections
from pathlib import Path
import openpyxl

REPO = Path(__file__).resolve().parents[2]
QUELLE = 'https://github.com/chillkrote/Unternehmenskennzahlen/blob/main/stammdaten/unternehmen_ids.csv'

def norm(s):
    s = str(s).lower()
    for a, b in (('ä', 'ae'), ('ö', 'oe'), ('ü', 'ue'), ('ß', 'ss')): s = s.replace(a, b)
    s = unicodedata.normalize('NFKD', s); s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'\([^)]*\)', ' ', s)
    s = re.sub(r'\b(ab|asa|as|oyj|plc|sa|nv|ag|aktiengesellschaft|se|spa|inc|corp|corporation|ltd|limited|co|kgaa|kg|gmbh|ev|eg|company|holding|holdings|group|the|publ|ord|class)\b', ' ', s)
    return re.sub(r'[^a-z0-9]', '', s)

def lies_csv(p, delim=','):
    return list(csv.DictReader(open(p, encoding='utf-8-sig'), delimiter=delim))

def main(src, out):
    reg = [x for x in lies_csv(REPO/'stammdaten/unternehmen_ids.csv') if x['land'] == 'Germany']
    uni = {x['unternehmen_id']: x for x in lies_csv(REPO/'boersennotierte-unternehmen/universum/universum.csv', ';')}
    wb = openpyxl.load_workbook(src); ws = wb['Unternehmen']
    rows = [list(r) for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]
    by_isin = {r[4]: i for i, r in enumerate(rows) if r[4]}
    by_lei = {r[10]: i for i, r in enumerate(rows) if r[10]}
    by_name = collections.defaultdict(list)
    for i, r in enumerate(rows):
        if r[2] in ('Germany', 'Sonstige'): by_name[norm(r[0])].append(i)
    st = collections.Counter(); zuord = []
    def vermerk(r, t): r[15] = (r[15] + ' | ' if r[15] else '') + t
    for x in reg:
        isins = [i for i in [x['isin_haupt']] + x['weitere_isins'].replace(',', ';').split(';') if i.strip()]
        isins = [i.strip() for i in isins]
        u = uni.get(x['unternehmen_id'], {})
        i = next((by_isin[k] for k in isins if k in by_isin), None)
        how = 'ISIN'
        if i is None and x['lei'] and x['lei'] in by_lei: i, how = by_lei[x['lei']], 'LEI'
        if i is None:
            c = by_name.get(norm(x['name']), [])
            if len(c) == 1: i, how = c[0], 'Name'
        bank = 'ja' if x['branche'] == 'banken' else 'nein'
        boerse = ('Deutsche Börse (%s)' % u['segment']) if u.get('segment') else None
        if i is not None:
            r = rows[i]; ch = []
            for idx, wert, nm in [(1, x['rechtsform'], 'Rechtsform'), (3, x['sitz'] or (u.get('sitz') or '').split(',')[0], 'Sitz'),
                                  (5, x['ticker'] or u.get('kuerzel'), 'Ticker'), (6, boerse, 'Börse'), (10, x['lei'], 'LEI'),
                                  (12, u.get('website'), 'Website')]:
                if not r[idx] and wert: r[idx] = wert; ch.append(nm)
            if not r[4] and isins and isins[0] not in by_isin: r[4] = isins[0]; by_isin[isins[0]] = i; ch.append('ISIN')
            if (not r[8] or r[8] == 'sonstige') and x['branche']: r[8] = x['branche']; ch.append('Branche')
            if r[2] == 'Sonstige': r[2] = 'Germany'; ch.append('Land')
            if ch: vermerk(r, 'Repo-Stammdaten %s (Abgleich über %s): %s ergänzt' % (x['unternehmen_id'], how, ', '.join(ch))); st['ergänzt'] += 1
            else: st['vollständig'] += 1
            zuord.append((x['unternehmen_id'], r[0], 'bestehend', how))
        else:
            n = x['name']
            rows.append([n, x['rechtsform'] or None, 'Germany', x['sitz'] or (u.get('sitz') or '').split(',')[0] or None,
                         isins[0] if isins and isins[0] not in by_isin else None, x['ticker'] or u.get('kuerzel') or None, boerse,
                         'ja' if x['status'] == 'börsennotiert' else 'nein', x['branche'] or 'sonstige', None, x['lei'] or None, None,
                         u.get('website') or None, bank, None,
                         'Aus Repo-Stammdaten %s (%s)' % (x['unternehmen_id'], x['herkunft']), QUELLE])
            if rows[-1][4]: by_isin[rows[-1][4]] = len(rows) - 1
            st['neu'] += 1; zuord.append((x['unternehmen_id'], n, 'neu', ''))
    ws.delete_rows(2, ws.max_row)
    for r in rows: ws.append(r)
    wb.save(out)
    p = REPO/'unternehmen-tabelle/id_zuordnung.csv'
    with open(p, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['unternehmen_id', 'name_in_tabelle', 'art', 'abgleich']); w.writerows(zuord)
    print(dict(st), len(rows))

if __name__ == '__main__': main(sys.argv[1], sys.argv[2])
