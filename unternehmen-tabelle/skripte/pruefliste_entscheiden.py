"""Setzt die Entscheidungen zu bereinigung_pruefliste.csv um (Stand 02.11.2026) und trägt sie in die Prüfliste ein.

Zusammengelegt wird, was dasselbe Unternehmen ist (weitere Börsencodes derselben Gesellschaft werden im Vermerk genannt).
Getrennt bleiben eigene Rechtsträger, Aktiengattungen und Unternehmen mit verschiedenen Börsencodes; dort nur Eintrag in der Prüfliste.
Die IDs der vier französischen Dubletten werden auf die behaltene ID gesetzt (siehe stammdaten/zusammenfuehren.py).
"""
import csv, sys, re
from pathlib import Path
import openpyxl
T = Path(__file__).resolve().parents[1]
IDMAP = {'U001284': 'U001058', 'U001285': 'U001235', 'U001286': 'U001165', 'U001287': 'U000867'}
# (behalten, [zusammenzulegen], Begründung)
MERGES = [
 ('Fielmann Group AG', ['Fielmann Group'], 'dasselbe Unternehmen, Zeile ohne Daten'),
 ('DHL AG', ['DHL', 'DHL AG (DHL)'], 'dasselbe Unternehmen (Deutsche Post DHL), Börsenzeile und Kürzel'),
 ('SGH (SGH)', ['SGH'], 'Kürzel-Zeile ohne Daten, ASX-Code SGH'),
 ('Wisr Limited (WZR)', ['WISR'], 'Kürzel-Zeile ohne Daten, gleicher Name'),
 ('AXA SA (CS)', ['AXA'], 'gleiche Gesellschaft (ISIN FR0000120628 laut Zeile), Börsenzeile mit Registereintrag'),
 ('BSE LTD (BSE)', ['BSE'], 'Kürzel-Zeile ohne Daten, gleicher Name'),
 ('UCB SA (UCB)', ['UCB'], 'gleiche Gesellschaft, Börsenzeile mit Registereintrag'),
 ('HEINEKEN NV (HEIA)', ['Heineken'], 'gleiche Gesellschaft; Heineken Holding bleibt eigene Zeile'),
 ('The Israel Corporation Ltd.', ['Israel'], 'gleicher Ticker ILCO, verkürzter Name'),
 ('Meridian Energy', ['MERIDIAN ENERGY LTD (MEL)'], 'gleiche Gesellschaft, zusätzlich am NZX (MEL)'),
 ('VALTERRA PLATINUM LTD', ['VALTERRA PLATINUM LTD (VALT)'], 'gleiche Gesellschaft, zusätzlich London (VALT)'),
 ('Avenira Limited', ['Avenira Limited (AEVN)'], 'gleiche Gesellschaft, weiterer ASX-Code AEVN'),
 ('Bpm Minerals Limited', ['Bpm Minerals Limited (BPMN)'], 'gleiche Gesellschaft, weiterer ASX-Code BPMN'),
 ('Charger Metals Nl', ['Charger Metals Nl (CHRCB)'], 'gleiche Gesellschaft, weiterer ASX-Code CHRCB'),
 ('Cynata Therapeutics Limited', ['Cynata Therapeutics Limited (CYPN)'], 'gleiche Gesellschaft, weiterer ASX-Code CYPN'),
 ('Emu Nl', ['Emu Nl (EMUCA)'], 'gleiche Gesellschaft, weiterer ASX-Code EMUCA'),
 ('Enova Mining Limited', ['Enova Mining Limited (ENVN)'], 'gleiche Gesellschaft, weiterer ASX-Code ENVN'),
 ('Latrobe Magnesium Limited', ['Latrobe Magnesium Limited (LMGN)'], 'gleiche Gesellschaft, weiterer ASX-Code LMGN'),
 ('Schneider Electric', ['SCHNEIDER ELECTRIC (SU)'], 'gleiche ID nach Registerzusammenführung'),
 ('TotalEnergies', ['TOTALENERGIES (TTE)'], 'gleiche ID nach Registerzusammenführung'),
]
def grund_getrennt(g, n1, n2, tk):
    z = (n1 + ' ' + n2)
    if re.search(r'\(\d{3,6}\)', z) and re.search(r'\d{3,6}', tk): return 'verschiedene Börsencodes (Taiwan/China/Korea), eigene Unternehmen mit ähnlichem Namen'
    if re.search(r'Holdings?|HOLDINGS', z) and g.startswith('ISIN'): return 'Holding und Operativgesellschaft sind eigene Rechtsträger mit eigener ISIN'
    if g.startswith('ISIN'): return 'ISIN/LEI widersprechen sich: verschiedene Wertpapiere oder Rechtsträger'
    if re.search(r'DVR|DVR\)|NWS|AXIA|Asian Hotels', z): return 'andere Aktiengattung bzw. eigene Rechtsträger'
    return 'kein gemeinsamer Ticker/keine gemeinsame ISIN, Zuordnung nicht belegt: getrennt gelassen'
wb = openpyxl.load_workbook(T / 'Unternehmen_Tabelle.xlsx'); ws = wb['Unternehmen']
head = [c.value for c in ws[1]]
rows = [list(r) for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]
ids = [x[0] for x in list(csv.reader(open(T / 'Unternehmen_Tabelle.csv', encoding='utf-8-sig'), delimiter=';'))[1:]]
assert len(ids) == len(rows)
ids = [IDMAP.get(i, i) for i in ids]
idx = {}
for i, r in enumerate(rows): idx.setdefault(r[0], []).append(i)
weg = set(); log = []
for keep, dups, grund in MERGES:
    ks = idx.get(keep)
    if not ks or len(ks) != 1: log.append(('Fehler: Behaltene Zeile nicht eindeutig', keep, '', '')); continue
    k = ks[0]; a = rows[k]
    for dn in dups:
        for d in idx.get(dn, []):
            b = rows[d]
            if a[4] and b[4] and a[4] != b[4]: log.append(('Fehler: ISIN widerspricht', keep, dn, '')); continue
            ch = []
            for j in range(1, 15):
                if not a[j] and b[j]: a[j] = b[j]; ch.append(head[j])
            if a[2] == 'Sonstige' and b[2] != 'Sonstige': a[2] = b[2]; ch.append('Land')
            if not ids[k] and ids[d]: ids[k] = ids[d]
            zus = ''
            if b[5] and a[5] and str(b[5]) != str(a[5]): zus = '; weiterer Börsencode %s' % b[5]
            a[15] = (a[15] + ' | ' if a[15] else '') + 'Prüfliste: "%s" zusammengelegt (%s%s)%s' % (b[0], grund, zus, (', ergänzt: ' + ', '.join(ch)) if ch else '')
            weg.add(d)
            log.append(('zusammengelegt', keep, dn, grund))
keep_idx = [i for i in range(len(rows)) if i not in weg]
ws.delete_rows(2, ws.max_row)
for i in keep_idx: ws.append(rows[i])
wb.save(T / 'Unternehmen_Tabelle.xlsx')
with open(T / 'Unternehmen_Tabelle.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f, delimiter=';'); w.writerow(['unternehmen_id'] + head)
    for i in keep_idx: w.writerow([ids[i]] + ['' if v is None else v for v in rows[i]])
# id_zuordnung: IDs umhängen
p = T / 'id_zuordnung.csv'
z = list(csv.reader(open(p, encoding='utf-8')))
neu = [z[0]]; seen = set()
for r in z[1:]:
    r[0] = IDMAP.get(r[0], r[0]); neu.append(r)
with open(p, 'w', newline='', encoding='utf-8') as f: csv.writer(f).writerows(neu)
# Prüfliste mit Entscheidungen
pl = list(csv.reader(open(T / 'bereinigung_pruefliste.csv', encoding='utf-8')))
merged_names = {dn for _, ds, _ in MERGES for dn in ds} | {k for k, _, _ in MERGES}
with open(T / 'bereinigung_pruefliste.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(pl[0] + ['entscheidung', 'begruendung'])
    for r in pl[1:]:
        g, n1, n2, tk = (r + ['', '', '', ''])[:4]
        namen = {n1} | set(n2.split('|'))
        m = [x for x in MERGES if x[0] in namen or any(d in namen for d in x[1])]
        if m: w.writerow(r + ['zusammengelegt', '; '.join(x[2] for x in m)])
        else: w.writerow(r + ['getrennt gelassen', grund_getrennt(g, n1, n2, tk)])
with open(T / 'bereinigung_protokoll_pruefliste.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['aktion', 'name_behalten', 'name_entfernt', 'begruendung']); w.writerows(log)
print(len(keep_idx), sum(1 for l in log if l[0] == 'zusammengelegt'), [l for l in log if l[0].startswith('Fehler')])
