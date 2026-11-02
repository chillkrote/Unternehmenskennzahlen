"""Arbeitet die JPX-Liste "List of TSE-listed Issues" (data_e.xlsx) in die Unternehmenstabelle ein (Japan).
Aufruf: python3 japan_jpx.py <data_e.xlsx>
Aufgenommen werden Aktienmärkte (Prime, Standard, Growth, PRO, Foreign); ETFs/ETNs und REIT/Fonds sind keine Unternehmen und bleiben draußen.
Zuordnung zu vorhandenen Zeilen per Ticker (Local Code) oder eindeutigem Namen; nur leere Felder werden gefüllt, Vermerk in Beschreibung.
Die Liste enthält keine ISIN: ISIN bleibt leer. Branche aus den 33 TSE-Sektoren grob abgebildet (bitte prüfen)."""
import csv, re, sys
from pathlib import Path
import openpyxl
T = Path(__file__).resolve().parents[1]
BR = {'Banks': 'banken', 'Insurance': 'versicherungen', 'Securities and Commodities Futures': 'finanzdienstleister', 'Other Financing Business': 'finanzdienstleister',
 'Real Estate': 'immobilien', 'Information & Communication': 'telekom-medien', 'Pharmaceutical': 'pharma-gesundheit', 'Chemicals': 'chemie-rohstoffe',
 'Oil and Coal Products': 'chemie-rohstoffe', 'Mining': 'chemie-rohstoffe', 'Iron and Steel': 'chemie-rohstoffe', 'Nonferrous Metals': 'chemie-rohstoffe',
 'Electric Power and Gas': 'energie-versorger', 'Transportation Equipment': 'automobil', 'Retail Trade': 'handel-konsum', 'Wholesale Trade': 'handel-konsum', 'Foods': 'handel-konsum',
 'Land Transportation': 'transport-logistik', 'Marine Transportation': 'transport-logistik', 'Air Transportation': 'transport-logistik', 'Warehousing and Harbor Transportation Service': 'transport-logistik',
 'Machinery': 'industrie', 'Electric Appliances': 'technologie', 'Precision Instruments': 'technologie', 'Construction': 'industrie', 'Metal Products': 'industrie'}
STOP = {'co', 'ltd', 'inc', 'corp', 'corporation', 'company', 'limited', 'the', 'holdings', 'group', 'kk', 'plc'}
def norm(n): return ' '.join(w for w in re.sub(r'[^a-z0-9 ]', ' ', (n or '').lower().replace('&', ' and ')).split() if w not in STOP)
src = openpyxl.load_workbook(sys.argv[1], read_only=True).active
lst = [r for r in src.iter_rows(min_row=2, values_only=True) if r[1] and re.search(r'Market|Prime|Standard|Growth|PRO', str(r[3])) and 'ETF' not in str(r[3]) and 'REIT' not in str(r[3])]
wb = openpyxl.load_workbook(T / 'Unternehmen_Tabelle.xlsx'); ws = wb['Unternehmen']
rows = [list(r) for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]
ids = [x[0] for x in list(csv.reader(open(T / 'Unternehmen_Tabelle.csv', encoding='utf-8-sig'), delimiter=';'))[1:]]
assert len(ids) == len(rows)
bytk, byname, names = {}, {}, set(r[0] for r in rows)
alle = set(norm(r[0]) for r in rows)
for i, r in enumerate(rows):
    if r[2] in ('Japan', 'Sonstige'):
        if r[5]: bytk.setdefault(str(r[5]).split('.')[0].upper(), []).append(i)
        byname.setdefault(norm(r[0]), []).append(i)
Q = 'https://www.jpx.co.jp/english/markets/statistics-equities/misc/01.html'
st = dict(neu=0, ergaenzt=0)
for r0 in lst:
    code, name, markt, sek = str(r0[1]), str(r0[2]).strip(), str(r0[3]), str(r0[5])
    br = BR.get(sek, 'sonstige'); bank = 'ja' if sek == 'Banks' else 'nein'
    z = bytk.get(code.upper(), [])
    if len(z) != 1:
        z = [i for i in byname.get(norm(name), []) if not rows[i][5] or str(rows[i][5]).split('.')[0] == code]
    if len(z) == 1:
        r = rows[z[0]]; f = []
        if not r[5]: r[5] = code; f.append('Ticker')
        if not r[6]: r[6] = 'Tokyo Stock Exchange'; f.append('Börse')
        if r[2] == 'Sonstige': r[2] = 'Japan'; f.append('Land')
        if r[8] == 'sonstige' and br != 'sonstige': r[8] = br; f.append('Branche')
        if f: r[15] = (r[15] + ' | ' if r[15] else '') + f"JPX-Liste TSE (Abgleich per Ticker/Name, bitte prüfen): {', '.join(f)}"; st['ergaenzt'] += 1
    else:
        n = name if (name not in names and norm(name) not in alle) else f'{name} (TSE {code})'
        if n in names: continue
        names.add(n); alle.add(norm(n))
        rows.append([n, None, 'Japan', None, None, code, 'Tokyo Stock Exchange', 'ja', br, None, None, None, None, bank, 'TSE ' + markt.split('(')[0].strip(),
                     f'Quelle JPX-Liste TSE-listed Issues (Stand {r0[0]}, {markt}, Sektor {sek}); Branche grob aus 33 TSE-Sektoren, keine ISIN, bitte prüfen', Q])
        ids.append(''); st['neu'] += 1
print(st, len(rows))
ws.delete_rows(2, ws.max_row)
for r in rows: ws.append(r)
wb.save(T / 'Unternehmen_Tabelle.xlsx')
head = [c.value for c in ws[1]]
with open(T / 'Unternehmen_Tabelle.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter=';'); w.writerow(['unternehmen_id'] + head)
    for i, r in zip(ids, rows): w.writerow([i] + ['' if v is None else v for v in r])
