import openpyxl,json,re,sys,urllib.parse,concurrent.futures as cf,collections
sys.path.insert(0,'/tmp/g')
from gleif import norm,get,B,info
D='/mnt/project-files/unternehmen-merge/'
wb=openpyxl.load_workbook(D+'Importvorlage_Unternehmen_befuellt_USA-ergaenzt.xlsx');ws=wb['Unternehmen']
def n2(s): 
    s=norm(re.sub(r'\b(class [ab]|class|a|h)\s*$','',s.lower().strip()))
    return re.sub(r'(china|co|ltd|limited|shares?)','',s)
jobs=[(r,ws.cell(r,1).value) for r in range(2,ws.max_row+1) if ws.cell(r,3).value=='China']
def work(j):
    r,name=j
    q=re.sub(r'\b(Co\.?|Ltd\.?|Limited|Class [AH]|A|H)\b','',name).strip()
    res=[]
    for term in dict.fromkeys([name,q]):
        g=get(f"{B}?filter%5Bfulltext%5D={urllib.parse.quote(term)}&page%5Bsize%5D=15")
        if g:
            for x in g['data']:
                e=x['attributes']['entity']
                if e['jurisdiction'].startswith('CN') and n2(e['legalName']['name'])==n2(name): res.append(info(x))
        if res: break
    res=list({x['lei']:x for x in res}.values())
    res=[x for x in res if x['ent']=='ACTIVE'] or res
    return r,res
out={}
with cf.ThreadPoolExecutor(8) as ex:
    for r,res in ex.map(work,jobs): out[r]=res
json.dump(out,open('/tmp/g/cn.json','w'),ensure_ascii=False)
print(collections.Counter(len(v) for v in out.values()))
for r,v in list(out.items())[:8]: print(ws.cell(r,1).value,[(x['name'],x['city'],x['form']) for x in v])
