"""Geschlechterschätzung (auf Anweisung von Robin, 05.11.2026): aus Vornamen + punktuelle Websuche.
Getrennt von den dokumentierten Angaben (geschlecht_belege.csv). Läuft nach build.py/berechnung.py, schreibt nur in governance/berechnungen/.
Aufruf aus Repo-Wurzel: python3 governance/skripte/geschlecht_schaetzung.py"""
import csv, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _vornamen import schaetze
from statistics import mean
D = 'governance'
rd = lambda f: list(csv.DictReader(open(f'{D}/{f}', encoding='utf-8-sig')))
MB, VG = rd('gremien_mitglieder.csv'), rd('verguetung.csv')
dok = {(r['name'], r['unternehmen_id']): r for r in rd('berechnungen/geschlecht_belege.csv')}
rows, seen = [], set()
for m in MB:
    k = (m['name'], m['unternehmen_id'], m['organ'])
    if k in seen or m['name'].startswith('CEO '):
        continue
    seen.add(k)
    if (m['name'], m['unternehmen_id']) in dok:
        g, c, b, meth = 'w', 'dokumentiert', dok[(m['name'], m['unternehmen_id'])]['beleg'], 'Bericht'
    else:
        g, c, b = schaetze(m['name']); meth = 'Schätzung (Vorname/Recherche)'
    rows.append(dict(unternehmen_id=m['unternehmen_id'], organ=m['organ'], name=m['name'], geschlecht={'w': 'weiblich', 'm': 'männlich', '': ''}[g], konfidenz=c, methode=meth, beleg=b))
def w(f, rs):
    with open(f'{D}/berechnungen/{f}', 'w', newline='', encoding='utf-8-sig') as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rs[0].keys())); wr.writeheader(); wr.writerows(rs)
w('geschlecht_schaetzung.csv', rows)
G = {(r['unternehmen_id'], r['organ'], r['name']): r for r in rows}
# Frauenquote je Unternehmen/Organ
fq = []
for u in sorted({r['unternehmen_id'] for r in rows}):
    for o in ('Vorstand', 'Aufsichtsrat'):
        rs = [r for r in rows if r['unternehmen_id'] == u and r['organ'] == o]
        if not rs: continue
        f = sum(r['geschlecht'] == 'weiblich' for r in rs); mm = sum(r['geschlecht'] == 'männlich' for r in rs); un = len(rs) - f - mm
        fq.append(dict(unternehmen_id=u, organ=o, n_gesamt=len(rs), n_frauen=f, n_maenner=mm, n_unklar=un, frauenanteil_pct=round(100 * f / (f + mm), 1) if f + mm else '',
                       n_nur_geschaetzt=sum(1 for r in rs if r['methode'].startswith('Schätzung') and r['geschlecht']),
                       bemerkung='Mitglieder lt. gremien_mitglieder.csv (inkl. im Jahr Ausgeschiedene); Geschlecht teils geschätzt'))
w('frauenquote_geschaetzt.csv', fq)
# Gender Pay Gap Vorstand (unbereinigt), ganzjährige Mitglieder, mit geschätzten Geschlechtern
def voll(m): return not m['bis'] and (not m['seit'].startswith('2025') or (m['unternehmen_id'] == 'U000502' and m['seit'] == '2025-01-01'))
gap = []
for u in sorted({r['unternehmen_id'] for r in rows if r['organ'] == 'Vorstand'}):
    vs = []
    for m in MB:
        if m['unternehmen_id'] != u or m['organ'] != 'Vorstand' or not voll(m): continue
        v = next((x for x in VG if x['unternehmen_id'] == u and x['gremium'] == 'Vorstand' and x['name'] == m['name']), None)
        if v and v['betrag_tsd_eur']: vs.append((m['name'], float(v['betrag_tsd_eur'])))
    f = [(n, t) for n, t in vs if G[(u, 'Vorstand', n)]['geschlecht'] == 'weiblich']
    mm = [(n, t) for n, t in vs if G[(u, 'Vorstand', n)]['geschlecht'] == 'männlich']
    unklar = [n for n, t in vs if not G[(u, 'Vorstand', n)]['geschlecht']]
    geschaetzt = [n for n, t in f + mm if G[(u, 'Vorstand', n)]['methode'].startswith('Schätzung')]
    if not f or not mm:
        continue
    mf, mmn = mean(t for _, t in f), mean(t for _, t in mm)
    gap.append(dict(unternehmen_id=u, gj=2025, n_frauen=len(f), n_maenner=len(mm), ø_frauen_teur=round(mf, 1), ø_maenner_teur=round(mmn, 1), gender_pay_gap_pct=round((mmn - mf) / mmn * 100, 1),
                    davon_geschaetzt='; '.join(geschaetzt), unklar_ausgeschlossen='; '.join(unklar),
                    bemerkung='unbereinigt, kleine Fallzahl; nur ganzjährige Mitglieder; Geschlecht teils aus Vornamen geschätzt'))
w('gender_pay_gap_vorstand_geschaetzt.csv', gap)
from collections import Counter
print(len(rows), 'Personen-Organ-Zeilen;', Counter(r['konfidenz'] for r in rows), len(gap), 'Gap-Zeilen')
