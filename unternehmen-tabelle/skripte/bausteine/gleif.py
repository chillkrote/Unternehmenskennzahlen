import openpyxl,csv,json,re,unicodedata,sys,time,urllib.request,urllib.parse,concurrent.futures as cf
SRC='/mnt/project-files/unternehmen-merge/Importvorlage_Unternehmen_befuellt_zusammengefuehrt.xlsx'
ISO={'Austria':'AT','Germany':'DE','Switzerland':'CH','Liechtenstein':'LI','Luxembourg':'LU','Netherlands':'NL','Belgium':'BE','France':'FR','UK':'GB','Ireland':'IE','Italy':'IT','Spain':'ES','Portugal':'PT','Greece':'GR','Denmark':'DK','Sweden':'SE','Norway':'NO','Finland':'FI','Iceland':'IS','Poland':'PL','Czechia':'CZ','Hungary':'HU','Romania':'RO','Slovakia':'SK','Slovenia':'SI','Croatia':'HR','Bulgaria':'BG','Estonia':'EE','Latvia':'LV','Lithuania':'LT','Malta':'MT','Cyprus':'CY','Turkey':'TR','USA':'US','Canada':'CA','Mexico':'MX','Brazil':'BR','Japan':'JP','China':'CN','Hong Kong':'HK','South Korea':'KR','India':'IN','Australia':'AU','Singapore':'SG','Israel':'IL','South Africa':'ZA','United Arab Emirates':'AE','Saudi Arabia':'SA'}
elf={}
for r in csv.DictReader(open('/tmp/g/elf.csv',encoding='utf-8-sig')):
    elf[r['ELF Code']]=(r['Abbreviations Local language'] or r['Entity Legal Form name Local name']).split(';')[0].strip()
def norm(s):
    s=unicodedata.normalize('NFKD',s.lower()); s=''.join(c for c in s if not unicodedata.combining(c))
    s=re.sub(r'\([^)]*\)',' ',s)
    s=re.sub(r'\b(ab|asa|as|a/s|oyj|abp|plc|sa|nv|ag|se|spa|s\.p\.a\.|s\.a\.|n\.v\.|inc|corp|corporation|ltd|limited|co|company|holding|holdings|group|the|oy|publ|ord|cmn|class|cl|a|b)\b',' ',s)
    return re.sub(r'[^a-z0-9]','',s)
def get(u):
    for t in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u,headers={'Accept':'application/vnd.api+json'}),timeout=25) as f: return json.load(f)
        except Exception as e:
            time.sleep(1.5*(t+1))
    return None
B='https://api.gleif.org/api/v1/lei-records'
def info(rec):
    a=rec['attributes'];e=a['entity']
    return dict(lei=rec['id'],name=e['legalName']['name'],city=(e['legalAddress'] or {}).get('city'),jur=e.get('jurisdiction') or '',form=elf.get((e.get('legalForm') or {}).get('id'),''),reg=e.get('registeredAs') or '',status=a['registration']['status'],ent=e.get('status'))
def work(args):
    i,name,land,isin=args
    res=None
    if isin:
        d=get(f"{B}?filter%5Bisin%5D={isin}")
        if d and d['data']:
            c=[info(x) for x in d['data']]
            res={'how':'isin','cand':c}
    elif land in ISO and land!='Sonstige':
        d=get(f"{B}?filter%5Bfulltext%5D={urllib.parse.quote(name)}&page%5Bsize%5D=15")
        if d:
            n=norm(name)
            c=[info(x) for x in d['data'] if norm(x['attributes']['entity']['legalName']['name'])==n and n and x['attributes']['entity']['jurisdiction'].startswith(ISO[land])]
            c=[x for x in c if x['ent']=='ACTIVE'] or c
            res={'how':'name','cand':c}
            if len(c)==1:
                d2=get(f"{B}/{c[0]['lei']}/isins")
                res['isins']=[x['attributes']['isin'] if 'attributes' in x else x.get('id') for x in (d2 or {}).get('data',[])]
    return i,res
if __name__=='__main__':
    wb=openpyxl.load_workbook(SRC);ws=wb['Unternehmen']
    jobs=[(r,ws.cell(r,1).value,ws.cell(r,3).value,ws.cell(r,5).value) for r in range(2,ws.max_row+1) if ws.cell(r,1).value]
    out={};n=0
    with cf.ThreadPoolExecutor(12) as ex:
        for i,res in ex.map(work,jobs):
            out[i]=res;n+=1
            if n%200==0:
                print(n,flush=True);json.dump(out,open('/tmp/g/cache.json','w'),ensure_ascii=False)
    json.dump(out,open('/tmp/g/cache.json','w'),ensure_ascii=False);print('done',flush=True)
