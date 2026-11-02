"""Führt zwei Registereinträge desselben Unternehmens zusammen (Regel aus README: kleinere ID behalten, andere als Alias).

Aufruf: python3 stammdaten/zusammenfuehren.py BEHALTEN VERWORFEN "Begründung" [...weitere Tripel]
Die verworfene ID bleibt als Zeile stehen (hinweis), verliert ISIN/LEI/Ticker an die behaltene ID, wird Alias (id_alt);
die Namens-Aliase der verworfenen ID zeigen auf die behaltene ID; dubletten.csv bekommt eine Zeile.
Danach: python3 stammdaten/migriere_ids.py (stellt Verweise in CSVs um) und python3 stammdaten/pruefe_ids.py --gegen=origin/main.
"""
import csv, sys
from pathlib import Path
S = Path(__file__).resolve().parent

def lies(p):
    with open(S / p, encoding='utf-8-sig', newline='') as f: return list(csv.reader(f))
def schreibe(p, rows, bom):
    with open(S / p, 'w', encoding='utf-8-sig' if bom else 'utf-8', newline='') as f: csv.writer(f, lineterminator='\n').writerows(rows)

def main(args):
    tripel = [args[i:i + 3] for i in range(0, len(args), 3)]
    raw = (S / 'unternehmen_ids.csv').read_bytes().startswith(b'\xef\xbb\xbf')
    reg = lies('unternehmen_ids.csv'); kopf = reg[0]; ix = {c: i for i, c in enumerate(kopf)}
    zeile = {r[0]: r for r in reg[1:]}
    isins = lies('isin_zuordnung.csv'); al = lies('unternehmen_aliase.csv'); du = lies('dubletten.csv')
    for keep, drop, grund in tripel:
        k, d = zeile[keep], zeile[drop]
        assert keep < drop, 'die kleinere ID bleibt'
        alt = (k[ix['name']], k[ix['rechtsform']])
        for feld in ('rechtsform', 'isin_haupt', 'weitere_isins', 'lei', 'ticker', 'sitz'):
            if not k[ix[feld]] and d[ix[feld]]: k[ix[feld]] = d[ix[feld]]
        k[ix['name']] = d[ix['name']]            # amtlicher Name aus dem Piloten
        k[ix['hinweis']] = (k[ix['hinweis']] + ' | ' if k[ix['hinweis']] else '') + 'Zusammengeführt mit %s (%s)' % (drop, grund)
        for feld in ('isin_haupt', 'weitere_isins', 'lei', 'ticker'): d[ix[feld]] = ''
        d[ix['hinweis']] = 'Dublette von %s, zusammengeführt am 02.11.2026 (%s)' % (keep, grund)
        for r in isins[1:]:
            if r[1] == drop: r[1] = keep
        for r in al[1:]:
            if r[1] == drop: r[1] = keep
        al.append([drop, keep, 'id_alt'])
        if [alt[0], keep, 'name'] not in al[1:] and alt[0] != k[ix['name']]: al.append([alt[0], keep, 'name'])
        du.append(['zusammengeführt', keep, k[ix['name']], keep, d[ix['name']], drop, grund])
    schreibe('unternehmen_ids.csv', reg, raw)
    schreibe('isin_zuordnung.csv', isins, False)
    schreibe('unternehmen_aliase.csv', al, (S / 'unternehmen_aliase.csv').read_bytes().startswith(b'\xef\xbb\xbf'))
    schreibe('dubletten.csv', du, (S / 'dubletten.csv').read_bytes().startswith(b'\xef\xbb\xbf'))

if __name__ == '__main__': main(sys.argv[1:])
