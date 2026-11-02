import openpyxl,csv,json,re,sys,collections
sys.path.insert(0,'/tmp/g')
from gleif import norm
SRC='/mnt/project-files/unternehmen-merge/Unternehmen_aktuell.xlsx'
OUT='/mnt/project-files/unternehmen-merge/Importvorlage_Unternehmen_befuellt_IN-AU-TW.xlsx'
def isin_ok(s):
    if not s or not re.fullmatch(r'[A-Z]{2}[A-Z0-9]{9}\d',s): return False
    d=''.join(str(int(c,36)) for c in s); t=0
    for i,c in enumerate(reversed(d)):
        n=int(c)
        if i%2==1:
            n*=2; n=n//10+n%10
        t+=n
    return t%10==0
wb=openpyxl.load_workbook(SRC); ws=wb['Unternehmen']
rows=[list(r) for r in ws.iter_rows(min_row=2,values_only=True)]
def idx(land):
    tk={};nm=collections.defaultdict(list)
    for i,r in enumerate(rows):
        if r[2]==land:
            if r[5]: tk[str(r[5]).strip().upper()]=i
            nm[norm(str(r[0]))].append(i)
    return tk,nm
allisin={r[4]:i for i,r in enumerate(rows) if r[4]}
allnorm={norm(str(r[0])) for r in rows if r[0]}
st=collections.Counter()
def add(r,t):
    rows.append(r); allnorm.add(norm(r[0])); st[t]+=1
def note(r,t):
    r[15]=(r[15]+' | ' if r[15] else '')+t
# India NSE
tk,nm=idx('India')
for x in csv.reader(open('/tmp/dl/nse.csv',encoding='utf-8')):
    if not x or x[0]=='SYMBOL': continue
    sym,name,ser,dt,_,_,isn=[c.strip() for c in x[:7]]
    if ser not in('EQ','BE','BZ') or not isin_ok(isn): continue
    i=tk.get(sym.upper())
    if i is None:
        c=nm.get(norm(name),[])
        if len(c)==1: i=c[0]
    if i is not None:
        r=rows[i]; ch=[]
        if not r[4] and (isn not in allisin or allisin[isn]==i):
            r[4]=isn; allisin[isn]=i; ch.append('ISIN')
        if not r[5]: r[5]=sym; ch.append('Ticker')
        if not r[6]: r[6]='National Stock Exchange of India'; ch.append('Börse')
        if ch: note(r,'NSE-Liste: '+', '.join(ch)+' ergänzt'); st['IN ergänzt']+=1
        else: st['IN vollständig']+=1
    elif isn not in allisin:
        n=name
        if norm(n) in allnorm: n=f'{name} ({sym})'
        add([n,None,'India',None,isn,sym,'National Stock Exchange of India','ja','sonstige',None,None,None,None,'nein','NSE',
             'Quelle NSE EQUITY_L.csv (Listing '+dt+'); Branche/Bank-Flag Platzhalter, bitte prüfen','https://www.nseindia.com/market-data/securities-available-for-trading'],'IN neu')
        allisin[isn]=len(rows)-1
# Australia ASX
tk,nm=idx('Australia')
for x in csv.DictReader(open('/tmp/dl/asx.csv',encoding='utf-8-sig')):
    code=x['ASX code'].strip(); name=x['Company name'].strip().title().replace('Limited','Limited'); g=x['GICs industry group']
    i=tk.get(code.upper())
    if i is None:
        c=nm.get(norm(name),[])+ [j for j in nm.get(norm(code),[])]
        if len(set(c))==1: i=c[0]
    if i is not None:
        r=rows[i]; ch=[]
        if not r[5]: r[5]=code; ch.append('Ticker')
        if not r[6]: r[6]='Australian Securities Exchange'; ch.append('Börse')
        if ch: note(r,'ASX-Liste: '+', '.join(ch)+' ergänzt'); st['AU ergänzt']+=1
        else: st['AU vollständig']+=1
    else:
        n=name
        if norm(n) in allnorm: n=f'{name} ({code})'
        add([n,None,'Australia',None,None,code,'Australian Securities Exchange','ja','sonstige',None,None,None,None,'nein','ASX',
             f'Quelle ASX-Firmenverzeichnis (GICS-Branchengruppe: {g}); Branche/Bank-Flag Platzhalter, bitte prüfen','https://www.asx.com.au/markets/trade-our-cash-market/directory'],'AU neu')
# Taiwan
seen=set()
twx={}
for i,r in enumerate(rows):
    if r[2]=='Sonstige' and r[6] and ('Taiwan' in r[6] or 'Taipei' in r[6]) and r[5]: twx[str(r[5]).strip()]=i
for f,ex,ck,en,wsite,reg in[('/tmp/dl/tw_l.json','Taiwan Stock Exchange (TWSE)','公司代號','英文簡稱','網址','外國企業註冊地國'),
        ('/tmp/dl/tw_o.json','Taipei Exchange (TPEx)','SecuritiesCompanyCode','Symbol','WebAddress','Registration')]:
    for d in json.load(open(f)):
        code=d[ck].strip()
        if code in seen: continue
        seen.add(code)
        if code in twx:
            r=rows[twx[code]]; r[2]='Taiwan'
            if not r[12]:
                w=d[wsite].replace('\u3000','').strip()
                if w: r[12]=w if w.startswith('http') else 'http://'+w
            note(r,'Land aus Börsenliste (TWSE/TPEx OpenAPI) auf Taiwan gesetzt'); st['TW ergänzt']+=1; continue
        e=re.sub(r'\s+',' ',d[en].replace('\u3000',' ')).strip()
        nmc=d.get('公司簡稱') or d.get('CompanyAbbreviation')
        n=f'{e or nmc} ({code})'
        w=d[wsite].replace('\u3000','').strip()
        if w and not w.startswith('http'): w='http://'+w
        rg=d[reg].replace('－','').strip()
        rows.append([n,None,'Taiwan',None,None,code,ex,'ja','sonstige',None,None,None,w or None,'nein',None,
            f'Quelle {"TWSE" if "TWSE" in ex else "TPEx"} OpenAPI (chin. Name {d.get("公司名稱") or d.get("CompanyName")}'+(f'; Registrierung {rg}' if rg else '')+'); keine ISIN in der Quelle; Branche/Bank-Flag Platzhalter, bitte prüfen',
            'https://openapi.twse.com.tw/' if 'TWSE' in ex else 'https://www.tpex.org.tw/openapi/'])
        st['TW neu']+=1
ws.delete_rows(2,ws.max_row)
for r in rows: ws.append(r)
wb.save(OUT); print(dict(st),len(rows))
