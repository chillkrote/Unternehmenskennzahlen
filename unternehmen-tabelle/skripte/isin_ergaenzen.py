"""Ergänzt fehlende ISIN in der Unternehmenstabelle aus zwei freien Quellen. Nur leere ISIN-Felder; eine ISIN steht nie bei zwei Zeilen.
1. Taiwan (TWSE/TPEx, 4-stellige Codes): ISIN = "TW000" + Code + "00" + Prüfziffer. Das Schema ist an 64 von 64 Wikidata-ISIN bestätigt.
2. Wikidata (SPARQL, frei): ISIN über Börsenkürzel + Börse, für Japan, USA, UK. Für China und Australien ist die Trefferquote zu schwach (79-85 % an Zeilen mit bekannter ISIN), dort wird nichts eingetragen.
Jede Ergänzung steht mit "bitte prüfen" in der Beschreibung.
Aufruf: python3 isin_ergaenzen.py"""
import csv, json, re, collections, urllib.parse, urllib.request
from pathlib import Path
import openpyxl
T = Path(__file__).resolve().parents[1]
def pz(body):
    d = ''.join(str(int(c, 36)) for c in body); t = 0
    for i, x in enumerate(reversed(d)):
        v = int(x) * (2 if i % 2 == 0 else 1); t += v // 10 + v % 10
    return (10 - t % 10) % 10
def nt(t): return re.sub(r'^0+', '', str(t).split('.')[0].upper().strip())
def kl(s):
    s = (s or '').lower()
    for k, v in (('shanghai', 'SH'), ('shenzhen', 'SZ'), ('hong kong', 'HK'), ('tokyo', 'TSE'), ('australia', 'ASX'), ('asx', 'ASX'), ('nasdaq', 'NAS'),
                 ('new york', 'NYSE'), ('nyse', 'NYSE'), ('london', 'LSE'), ('xetra', 'XET'), ('frankfurt', 'FRA')):
        if k in s: return v
    return None
def wikidata(pfx):
    q = ('SELECT ?isin ?tk ?exl WHERE { ?c wdt:P946 ?isin . FILTER(STRSTARTS(?isin,"%s")) ?c p:P414 ?st . ?st ps:P414 ?ex . ?st pq:P249 ?tk . '
         '?ex rdfs:label ?exl . FILTER(LANG(?exl)="en") } LIMIT 30000' % pfx)
    u = 'https://query.wikidata.org/sparql?format=json&query=' + urllib.parse.quote(q)
    rq = urllib.request.Request(u, headers={'User-Agent': 'Unternehmenskennzahlen-Abruf (Forschung)'})
    return json.load(urllib.request.urlopen(rq, timeout=120))['results']['bindings']
wb = openpyxl.load_workbook(T / 'Unternehmen_Tabelle.xlsx'); ws = wb['Unternehmen']
rows = [list(r) for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]
ids = [x[0] for x in list(csv.reader(open(T / 'Unternehmen_Tabelle.csv', encoding='utf-8-sig'), delimiter=';'))[1:]]
assert len(ids) == len(rows)
vorh = {r[4] for r in rows if r[4]}
def gueltig(i): return bool(re.fullmatch(r'[A-Z]{2}[A-Z0-9]{9}\d', i)) and pz(i[:-1]) == int(i[-1])
def setze(r, isin, quelle):
    if r[4] or isin in vorh or not gueltig(isin): return False
    r[4] = isin; vorh.add(isin)
    r[15] = (r[15] + ' | ' if r[15] else '') + quelle + ' (bitte prüfen): ISIN'; return True
st = collections.Counter()
for r in rows:
    if r[2] == 'Taiwan' and not r[4] and r[5] and re.fullmatch(r'\d{4}', str(r[5]).strip()):
        b = 'TW000' + str(r[5]).strip() + '00'
        if setze(r, b + str(pz(b)), 'berechnet (Schema TW000+Code+00+Prüfziffer, an Wikidata bestätigt)'): st['Taiwan'] += 1
for pfx, land in (('JP', 'Japan'), ('US', 'USA'), ('GB', 'UK')):
    wd = collections.defaultdict(set)
    for b in wikidata(pfx): wd[(nt(b['tk']['value']), kl(b['exl']['value']))].add(b['isin']['value'])
    for r in rows:
        if r[2] != land or r[4] or not r[5] or kl(r[6]) is None: continue
        c = wd.get((nt(r[5]), kl(r[6])))
        if c and len(c) == 1 and setze(r, next(iter(c)), 'Wikidata (Ticker+Börse)'): st[land] += 1
print(dict(st))
ws.delete_rows(2, ws.max_row)
for r in rows: ws.append(r)
wb.save(T / 'Unternehmen_Tabelle.xlsx')
head = [c.value for c in ws[1]]
with open(T / 'Unternehmen_Tabelle.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter=';'); w.writerow(['unternehmen_id'] + head)
    for i, r in zip(ids, rows): w.writerow([i] + ['' if v is None else v for v in r])
