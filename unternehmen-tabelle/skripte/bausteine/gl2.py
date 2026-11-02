import openpyxl,json,sys,urllib.parse,concurrent.futures as cf,collections
sys.path.insert(0,'/tmp/g')
from gleif import norm,get,B,info,ISO
D='/mnt/project-files/unternehmen-merge/'
wb=openpyxl.load_workbook(D+'Importvorlage_Unternehmen_befuellt_iShares.xlsx');ws=wb['Unternehmen']
jobs=[(r,ws.cell(r,1).value,ws.cell(r,3).value) for r in range(2,ws.max_row+1) if ws.cell(r,3).value in ISO and ws.cell(r,3).value!='USA' and not ws.cell(r,11).value]
print(len(jobs),flush=True)
ISO2=dict(ISO)
def work(j):
    r,name,land=j
    n=norm(name)
    if not n or len(n)<3: return r,[]
    g=get(f"{B}?filter%5Bfulltext%5D={urllib.parse.quote(name)}&page%5Bsize%5D=15")
    c=[]
    if g:
        for x in g['data']:
            e=x['attributes']['entity']
            if norm(e['legalName']['name'])==n and e['jurisdiction'].startswith(ISO2[land]): c.append(info(x))
    c=list({x['lei']:x for x in c}.values());c=[x for x in c if x['ent']=='ACTIVE'] or c
    o={'c':c}
    if len(c)==1:
        g2=get(f"{B}/{c[0]['lei']}/isins");o['isins']=[x['attributes']['isin'] for x in (g2 or {}).get('data',[]) if 'attributes' in x]
    return r,o
out={}
with cf.ThreadPoolExecutor(10) as ex:
    for n,(r,o) in enumerate(ex.map(work,jobs),1):
        out[r]=o
        if n%1000==0: print(n,flush=True)
json.dump(out,open('/tmp/g/gl2.json','w'),ensure_ascii=False);print('done',flush=True)
