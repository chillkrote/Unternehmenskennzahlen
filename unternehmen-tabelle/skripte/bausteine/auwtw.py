import sys,re,json,urllib.parse,collections,concurrent.futures as cf,openpyxl
sys.path.insert(0,'/tmp/g')
import gleif
from gleif import norm,get,B,info
D='/mnt/project-files/unternehmen-merge/'
wb=openpyxl.load_workbook(D+'Unternehmen_aktuell.xlsx'); ws=wb['Unternehmen']
rows=[list(r) for r in ws.iter_rows(min_row=2,values_only=True)]
jobs=[]
for i,r in enumerate(rows):
    if r[2] in('Australia','Taiwan') and not r[10] and r[0]:
        if r[2]=='Australia': q=re.sub(r'\s*\([A-Z0-9]+\)$','',r[0])
        else:
            m=re.search(r'chin\. Name ([^;)]+)',r[15] or '')
            if not m: continue
            q=m.group(1).strip()
        jobs.append((i,q,'AU' if r[2]=='Australia' else 'TW'))
print(len(jobs),flush=True)
def work(j):
    i,q,cc=j
    d=get(f"{B}?filter%5Bfulltext%5D={urllib.parse.quote(q)}&page%5Bsize%5D=15")
    if not d: return i,None
    c=[]
    for x in d['data']:
        e=x['attributes']['entity']; n=e['legalName']['name']
        ok = (norm(n)==norm(q) and norm(q)) if cc=='AU' else n.strip()==q
        if ok and (e.get('jurisdiction') or '').startswith(cc): c.append(info(x))
    c=[x for x in c if x['ent']=='ACTIVE'] or c
    res={'cand':c,'cc':cc}
    if len(c)==1:
        d2=get(f"{B}/{c[0]['lei']}/isins")
        res['isins']=[x['attributes']['isin'] if 'attributes' in x else x.get('id') for x in (d2 or {}).get('data',[])]
    return i,res
out={}
with cf.ThreadPoolExecutor(12) as ex:
    for n,(i,res) in enumerate(ex.map(work,jobs)):
        out[i]=res
        if n%500==0: print(n,flush=True)
json.dump(out,open('/tmp/g/auwtw.json','w'),ensure_ascii=False)
allisin={r[4] for r in rows if r[4]}; alllei={r[10] for r in rows if r[10]}
st=collections.Counter()
for i,res in out.items():
    if not res or len(res['cand'])!=1: st['kein/mehrdeutig']+=1; continue
    c=res['cand'][0]; r=rows[i]; cc=res['cc']; ch=[]
    if c['lei'] in alllei: st['LEI schon vergeben']+=1; continue
    r[10]=c['lei']; alllei.add(c['lei']); ch.append('LEI')
    if not r[3] and c['city']: r[3]=c['city'].title(); ch.append('Sitz')
    if not r[1] and c['form']: r[1]=c['form']; ch.append('Rechtsform')
    if not r[11] and c['reg']: r[11]=c['reg']+f' ({cc})'; ch.append('Handelsregisternummer')
    ii=[x for x in res.get('isins',[]) if x and x.startswith(cc)]
    if not r[4] and len(ii)==1 and ii[0] not in allisin: r[4]=ii[0]; allisin.add(ii[0]); ch.append('ISIN')
    r[15]=(r[15]+' | ' if r[15] else '')+'GLEIF (Namensabgleich): '+', '.join(ch)+' ergänzt, bitte prüfen'
    for k in ch: st[(cc,k)]+=1
    st[cc+' Treffer']+=1
ws.delete_rows(2,ws.max_row)
for r in rows: ws.append(r)
wb.save(D+'Importvorlage_Unternehmen_befuellt_GLEIF-AU-TW.xlsx'); print(dict(st))
