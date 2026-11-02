import openpyxl,collections,sys,re,difflib,json
sys.path.insert(0,'/tmp/g')
from gleif import norm,get,B
D='/mnt/project-files/unternehmen-merge/'
wb=openpyxl.load_workbook(D+'Importvorlage_Unternehmen_befuellt_geprueft.xlsx');ws=wb['Unternehmen']
rows={r:[ws.cell(r,c).value for c in range(1,18)] for r in range(2,ws.max_row+1) if ws.cell(r,1).value}
BLOCK={'Engie Energia Chile','TotalEnergies Marketing Maroc','New China Life Insurance Co Ltd','Israel','The Israel Corporation Ltd.','EAGLE BANCORP (MT)','EAGLE BANCORP INC','FIRST BANCORP (NC)','FIRST BANCORP, INC','Wonik','Wonik Holdings'}
rows={r:v for r,v in rows.items()}
par={r:r for r in rows}
def f(x):
    while par[x]!=x: par[x]=par[par[x]];x=par[x]
    return x
def union(a,b):
    if rows[a][0] in BLOCK or rows[b][0] in BLOCK: return
    ra,rb=f(a),f(b)
    if ra!=rb: par[max(ra,rb)]=min(ra,rb)
def ok(a,b):
    x,y=norm(rows[a][0]),norm(rows[b][0]);la,lb=rows[a][2],rows[b][2]
    if not x or not y: return False
    ratio=difflib.SequenceMatcher(None,x,y).ratio()
    pref=x.startswith(y) or y.startswith(x)
    if la==lb: return x==y or ratio>=.75 or (pref and min(len(x),len(y))>=4)
    if 'Sonstige' in (la,lb): return x==y or ratio>=.85
    return x==y and bool((rows[a][4] and rows[a][4]==rows[b][4]) or (rows[a][10] and rows[a][10]==rows[b][10]))
by=collections.defaultdict(list)
for r,v in rows.items():
    if v[4]: by[('i',v[4])].append(r)
    if v[10]: by[('l',v[10])].append(r)
    if norm(v[0]): by[('n',v[2],norm(v[0]))].append(r)
sn=collections.defaultdict(list)
for r,v in rows.items():
    if norm(v[0]): sn[norm(v[0])].append(r)
for k,l in sn.items():
    lands={rows[r][2] for r in l}
    if len(l)>1 and 'Sonstige' in lands and len(lands-{'Sonstige'})<=1:
        for r in l[1:]:
            if all(rows[x][0] not in BLOCK for x in (l[0],r)): union(l[0],r)
for k,l in by.items():
    for r in l[1:]:
        if k[0]=='n' or ok(l[0],r): union(l[0],r)
cl=collections.defaultdict(list)
for r in rows: cl[f(r)].append(r)
merged=0;removed=[];log=[]
for rep,mem in cl.items():
    if len(mem)<2: continue
    v=ws
    others=[m for m in mem if m!=rep]
    notes=[]
    for o in others:
        for c in range(1,18):
            cur=ws.cell(rep,c).value;val=rows[o][c-1]
            if c==16: continue
            if c==3 and cur=='Sonstige' and val and val!='Sonstige': ws.cell(rep,c).value=val;continue
            if c in(1,): continue
            if not cur and val: ws.cell(rep,c).value=val
            elif c in(5,6,11) and val and cur and val!=cur: notes.append(f'abweichend {ws.cell(1,c).value}: {val}')
        d=rows[o][15]
        if d: notes.append(d)
    names='; '.join(rows[o][0] for o in others)
    old=ws.cell(rep,16).value
    ws.cell(rep,16).value=(old+' | ' if old else '')+f'Zusammengeführt mit: {names}'+(' | '+' | '.join(dict.fromkeys(notes)) if notes else '')
    ws.cell(rep,16).value=ws.cell(rep,16).value[:1500]
    removed+=others;merged+=1
    log.append((rows[rep][0],rows[rep][2],[(rows[o][0],rows[o][2]) for o in others]))
name_map={}
for rep,mem in cl.items():
    for o in mem:
        if o!=rep: name_map[rows[o][0]]=rows[rep][0]
q=wb['Quellen-Dokumente'];qn=0
for r in range(2,q.max_row+1):
    v=q.cell(r,1).value
    if v in name_map: q.cell(r,1).value=name_map[v];qn+=1
print('Quellen umbenannt',qn)
# ISIN/LEI-Konflikte nach Merge
live=[r for r in rows if r not in set(removed)]
isi=collections.defaultdict(list)
for r in live:
    i=ws.cell(r,5).value
    if i: isi[i].append(r)
cleared=[]
for i,l in isi.items():
    if len(l)<2: continue
    d=get(f"{B}?filter%5Bisin%5D={i}");gname=d['data'][0]['attributes']['entity']['legalName']['name'] if d and d['data'] else ''
    glei=d['data'][0]['id'] if d and d['data'] else ''
    best=max(l,key=lambda r:difflib.SequenceMatcher(None,norm(ws.cell(r,1).value),norm(gname)).ratio()) if gname else None
    if not gname: continue
    keep=best if best and difflib.SequenceMatcher(None,norm(ws.cell(best,1).value),norm(gname)).ratio()>=.6 else None
    for r in l:
        if r==keep: continue
        old=ws.cell(r,16).value
        ws.cell(r,5).value=None
        if ws.cell(r,11).value and ws.cell(r,11).value==glei: ws.cell(r,11).value=None
        ws.cell(r,16).value=(old+' | ' if old else '')+f'ISIN {i} entfernt (gehört laut GLEIF zu {gname or "unbekannt"})'
        cleared.append((ws.cell(r,1).value,i,gname))
# ungültige ISINs
def isin_ok(i):
    if not re.fullmatch(r'[A-Z]{2}[A-Z0-9]{9}[0-9]',i): return False
    d=''.join(str(int(ch,36)) for ch in i);t=0
    for n,ch in enumerate(reversed(d)):
        x=int(ch)
        if n%2==1: x*=2;x=x//10+x%10
        t+=x
    return t%10==0
bad=[]
for r in live:
    i=ws.cell(r,5).value
    if i and not isin_ok(i):
        old=ws.cell(r,16).value;ws.cell(r,5).value=None
        ws.cell(r,16).value=(old+' | ' if old else '')+f'ISIN {i} entfernt (Prüfziffer ungültig)';bad.append((ws.cell(r,1).value,i))
# LEI-Mehrfach nach Merge: bei Rest-Konflikt LEI von Zeilen entfernen, die nicht zur Zeile mit gleicher LEI passen -> nur melden
for r in sorted(removed,reverse=True): ws.delete_rows(r)
wb.save(D+'Importvorlage_Unternehmen_befuellt_zusammengelegt.xlsx')
json.dump({'merged':log,'cleared':cleared,'bad':bad},open('/tmp/g/zus.json','w'),ensure_ascii=False,indent=1)
print(merged,len(removed),len(cleared),len(bad),ws.max_row)
