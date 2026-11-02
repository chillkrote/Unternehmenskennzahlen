import json,re,sys,time,urllib.request,collections,concurrent.futures as cf,openpyxl
sys.path.insert(0,'/tmp/g')
from gleif import norm,get,B,elf,info
UA="Unternehmenskennzahlen-Erhebung (Forschung, kein Kontakt)"
D='/mnt/project-files/unternehmen-merge/'
def toks(s): return set(re.findall(r'[a-z0-9]{3,}',re.sub(r'\b(inc|corp|corporation|ltd|holdings?|hldgs?|group|grp|co|company|cmn|class|cl|ord|common|stock|the|plc)\b','',s.lower())))
d=json.load(open('/tmp/g/sec.json'));f=d['fields']
bt=collections.defaultdict(list)
for x in d['data']:
    r=dict(zip(f,x));bt[r['ticker'].upper()].append(r)
wb=openpyxl.load_workbook(D+'Importvorlage_Unternehmen_befuellt_zusammengelegt.xlsx');ws=wb['Unternehmen']
jobs=[]
for r in range(2,ws.max_row+1):
    if ws.cell(r,3).value!='USA': continue
    t=(ws.cell(r,6).value or '').upper().strip();c=bt.get(t)
    if not c or len(c)>1: continue
    a=toks(ws.cell(r,1).value);b=toks(c[0]['name'])
    if not (a&b) and not any(x[:4]==y[:4] for x in a for y in b): continue
    jobs.append((r,c[0]['cik'],c[0]['name']))
print(len(jobs),flush=True)
def sub(cik):
    for t in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(f'https://data.sec.gov/submissions/CIK{int(cik):010d}.json',headers={'User-Agent':UA}),timeout=25) as fh: return json.load(fh)
        except Exception: time.sleep(2*(t+1))
def work(j):
    r,cik,nm=j;s=sub(cik);o={'row':r,'cik':cik,'sec':nm}
    if s:
        a=s['addresses']['business'];o.update(name=s['name'],sic=s.get('sic'),sicd=s.get('sicDescription'),city=a.get('city'),st=a.get('stateOrCountry'),inc=s.get('stateOfIncorporation'),web=s.get('website'))
        g=get(f"{B}?filter%5Bfulltext%5D={urllib.parse.quote(s['name'])}&page%5Bsize%5D=15")
        n=norm(s['name']);cands=[]
        if g:
            for x in g['data']:
                e=x['attributes']['entity']
                if norm(e['legalName']['name'])==n and e['jurisdiction'].startswith('US'): cands.append(info(x))
            cands=[x for x in cands if x['ent']=='ACTIVE'] or cands
        o['gl']=cands
        if len(cands)==1:
            g2=get(f"{B}/{cands[0]['lei']}/isins");o['isins']=[x['attributes']['isin'] for x in (g2 or {}).get('data',[]) if 'attributes' in x]
    return o
import urllib.parse
out={}
with cf.ThreadPoolExecutor(6) as ex:
    for n,o in enumerate(ex.map(work,jobs),1):
        out[o['row']]=o
        if n%300==0: print(n,flush=True)
json.dump(out,open('/tmp/g/us.json','w'),ensure_ascii=False);print('done',flush=True)
