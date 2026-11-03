"""Ergänzt fehlende US-ISIN aus der SEC-Liste "Official List of Section 13(f) Securities" (Textfassung der PDF).
Aufruf: python3 us_isin_13f.py <13flist....pdf.txt> [us_edgar_ergaenzung.csv]
Mit der zweiten Datei wird zusätzlich der offizielle EDGAR-Name (per Name+Ticker) verglichen; Test: 456 von 457 gleich (99,8 %).
Die Liste wird nicht ins Repo gelegt (CUSIP-Nummern: Copyright ABA/CGS, keine Weitergabe ohne Erlaubnis); abgeleitet wird nur die ISIN.
ISIN = "US" + CUSIP (9 Zeichen) + Prüfziffer. Zuordnung per Namensvergleich (Kürzel der Liste und der Tabelle, Präfixvergleich), nur bei genau einer CUSIP.
Test an 959 US-Zeilen mit bekannter ISIN: 928 gleich (96,8 %), Abweichungen meist Reverse Splits (neue CUSIP). Darum Vermerk "bitte prüfen".
Nur leere ISIN-Felder; eine ISIN steht nie bei zwei Zeilen."""
import sys, csv
from pathlib import Path
T = Path(__file__).resolve().parents[1]
import re,openpyxl,collections
f=sys.argv[1]
def luhn_cd(c8):
    t=0
    for i,ch in enumerate(c8):
        v=int(ch,36) if ch.isalnum() else {'*':36,'@':37,'#':38}[ch]
        if i%2==1: v*=2
        t+=v//10+v%10
    return (10-t%10)%10
def isin_of(c9): 
    s='US'+c9; d=''.join(str(int(c,36)) for c in s); t=0
    for i,x in enumerate(reversed(d)):
        v=int(x)*(2 if i%2==0 else 1); t+=v//10+v%10
    return None
def isin_cd(body):  # body = 'US'+cusip9 (11 chars)
    d=''.join(str(int(c,36)) for c in body); t=0
    for i,x in enumerate(reversed(d)):
        v=int(x)*(2 if i%2==0 else 1); t+=v//10+v%10
    return (10-t%10)%10
STOPN={'inc','corp','corporation','co','company','ltd','limited','plc','the','holdings','holding','group','incorporated','llc','lp','sa','nv','ag','de','new'}
def norm(n):
    return ' '.join(w for w in re.sub(r'[^a-z0-9 ]',' ',n.lower().replace('&',' and ')).split() if w not in STOPN)
L=[]
pat=re.compile(r'^([0-9A-Z]{6}) (\w\w) (\w) (\*?)\s*(.*)$')
for line in open(f,encoding='utf-8',errors='ignore'):
    m=pat.match(line.strip())
    if not m: continue
    c6,c2,ck,star,rest=m.groups()
    L.append((c6+c2+ck,rest))
print(len(L))
OKD=re.compile(r'\b(COM|COM NEW|COM CL [A-C]|CL [A-C]|ORD|ORD SHS|SHS|CL [A-C] COM|COMMON|CL A ORD SHS|NEW|SHS CL [A-C]|COM STK)\b')
BAD=re.compile(r'\b(CALL|PUT|WT|\*W|WARRANT|UNIT|NOTE|PFD|PREF|DEBT|RIGHT|ETF|TR UNIT|DEP|ADS|ADR|SPONSORED|%|SR|DEL|DELETED)\b|\d\.\d+%|EXP')
DESC=re.compile(r'\s+(COM NEW|COM STK|COM CL [A-C]|COM|CL [A-C] COM|CL [A-C]|CL [A-C] ORD SHS|ORD SHS|ORD|SHS CL [A-C]|SHS|COMMON STOCK|COMMON|NEW)\s*(ADDED)?$')
cands=[]
for c9,rest in L:
    if not c9[0].isdigit(): continue
    if BAD.search(rest) or rest.endswith('DELETED'): continue
    m=DESC.search(rest)
    if not m: continue
    nm=rest[:m.start()].strip()
    cands.append((c9,nm,m.group(1)))
def toks(n): return norm(n).split()
idx=collections.defaultdict(list)
for c9,nm,d in cands:
    t=toks(nm)
    if t: idx[t[0][:3]].append((c9,nm,d,t,len(nm)))
def match(name):
    R=toks(name)
    if not R: return []
    out=[]
    for c9,nm,d,t,ln in idx.get(R[0][:3],[]):
        if len(t)>len(R): continue
        if all(R[i].startswith(t[i]) for i in range(len(t))):
            if len(t)==len(R) or ln>=27: out.append((c9,nm,d))
    return out
def isin(c9): return 'US'+c9+str(isin_cd('US'+c9))
NOISE={'cm','cmn','cs','ads','ord','shs','adr','com','common','stock','cl','class','sponsored'}
def toks2(n): return [w for w in norm(n).split() if w not in NOISE]
idx2=collections.defaultdict(list)
for c9,nm,d in cands:
    t=toks2(nm)
    if t: idx2[t[0][:3]].append((c9,nm,d,t,len(nm)))
def pre(a,b): return a==b or (min(len(a),len(b))>=3 and (a.startswith(b) or b.startswith(a)))
def match2(name):
    R=toks2(name)
    if not R: return []
    out=[]
    for c9,nm,d,t,ln in idx2.get(R[0][:3],[]):
        if len(t)!=len(R) and not (ln>=27 and len(t)<=len(R)): continue
        if len(t)==len(R) and all(pre(R[i],t[i]) for i in range(len(t))): out.append((c9,nm,d))
        elif len(t)<len(R) and all(pre(R[i],t[i]) for i in range(len(t))): out.append((c9,nm,d))
    return out

wb = openpyxl.load_workbook(T / 'Unternehmen_Tabelle.xlsx'); ws = wb['Unternehmen']
rows = [list(r) for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]
ids = [x[0] for x in list(csv.reader(open(T / 'Unternehmen_Tabelle.csv', encoding='utf-8-sig'), delimiter=';'))[1:]]
assert len(ids) == len(rows)
vorh = {r[4] for r in rows if r[4]}
ed = {}
if len(sys.argv) > 2:
    for x in csv.DictReader(open(sys.argv[2], encoding='utf-8')): ed[(x['name_tabelle'], x['ticker'])] = x['name_edgar']
n = mehr = 0
for r in rows:
    if r[2] != 'USA' or r[4]: continue
    cs = {x[0] for x in match2(r[0])}; via = 'Namensabgleich'
    if len(cs) != 1 and (r[0], r[5] or '') in ed:
        cs = {x[0] for x in match2(ed[(r[0], r[5] or '')])}; via = 'EDGAR-Name'
    if len(cs) != 1: continue
    i = isin(next(iter(cs)))
    if i in vorh: mehr += 1; continue
    r[4] = i; vorh.add(i); n += 1
    r[15] = (r[15] + ' | ' if r[15] else '') + 'SEC 13(f)-Liste (CUSIP, ' + via + ', bitte prüfen): ISIN'
print('eingetragen', n, 'ISIN schon vergeben', mehr)
ws.delete_rows(2, ws.max_row)
for r in rows: ws.append(r)
wb.save(T / 'Unternehmen_Tabelle.xlsx')
head = [c.value for c in ws[1]]
with open(T / 'Unternehmen_Tabelle.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter=';'); w.writerow(['unternehmen_id'] + head)
    for i, r in zip(ids, rows): w.writerow([i] + ['' if v is None else v for v in r])
