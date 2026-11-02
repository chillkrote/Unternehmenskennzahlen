import csv,glob,re,collections,openpyxl,sys,unicodedata
sys.path.insert(0,'/tmp/g')
from gleif import norm
D='/mnt/project-files/unternehmen-merge/'
H='/mnt/user-data/uploads/hearth/'
SRC=[('SSAC','iShares MSCI ACWI (SSAC)',glob.glob(H+'e72d1072*/*')[0]),('IS3N','iShares MSCI EM IMI (IS3N)',glob.glob(H+'0283d9b7*/*')[0]),('CEBZ','iShares MSCI Europe (CEBZ)',glob.glob(H+'ed87e309*/*')[0])]
LAND={'United States':'USA','Vereinigte Staaten':'USA','Korea (South)':'South Korea','Korea':'South Korea','United Kingdom':'UK','Vereinigtes Königreich':'UK','Indien':'India','Brasilien':'Brazil','Saudi-Arabien':'Saudi Arabia','Südafrika':'South Africa','Türkei':'Turkey','Ver. Arabische Emirate':'United Arab Emirates','Russland':'Sonstige','Russian Federation':'Sonstige','Mexiko':'Mexico','Polen':'Poland','Griechenland':'Greece','Ungarn':'Hungary','Tschechien':'Czechia','Irland':'Ireland','Hongkong':'Hong Kong','Deutschland':'Germany','Kanada':'Canada','Singapur':'Singapore','Schweiz':'Switzerland','Taiwan':'Sonstige','Japan':'Japan'}
SEK={'Financials':'finanzdienstleister','Finanzwesen':'finanzdienstleister','Information Technology':'technologie','IT':'technologie','Communication':'telekom-medien','Kommunikation':'telekom-medien','Health Care':'pharma-gesundheit','Gesundheitsversorgung':'pharma-gesundheit','Energy':'energie','Energie':'energie','Utilities':'energie-versorger','Versorger':'energie-versorger','Real Estate':'immobilien','Immobilien':'immobilien','Consumer Staples':'handel-konsum','Consumer Discretionary':'handel-konsum','Zyklische Konsumgüter':'handel-konsum','Nichtzyklische Konsumgüter':'handel-konsum','Industrials':'industrie','Industrie':'industrie','Materials':'chemie-rohstoffe','Materialien':'chemie-rohstoffe'}
LST=set(openpyxl.load_workbook(D+'Importvorlage_Unternehmen_befuellt_Jordan.xlsx')['Listen']['F'][1:])
LST={c.value for c in openpyxl.load_workbook(D+'Importvorlage_Unternehmen_befuellt_Jordan.xlsx')['Listen']['F'][1:] if c.value}
items={};stat=collections.Counter()
for code,idx,f in SRC:
    rows=list(csv.reader(open(f,encoding='utf-8-sig')))
    h=[i for i,r in enumerate(rows) if r and r[0] in('Ticker','Emittententicker')][0]
    for r in rows[h+1:]:
        if len(r)!=12: continue
        t,name,sec,ac,loc,ex,cur=r[0],r[1].strip(),r[2].strip('\xa0 '),r[3],r[9].strip(),r[10],r[11]
        if ac not in('Equity','Aktien'): stat['nicht Aktie']+=1;continue
        if not name or name.endswith('DUMMY') or re.search(r'\bETF\b|UCITS|\bFUND\b',name) or ex.startswith('NO MARKET') or loc in('-','Europäische Union','European Union'): stat['ausgesondert']+=1;continue
        land=LAND.get(loc,loc)
        if land=='Sonstige' and loc in('Taiwan',): pass
        key=(land,t)
        if key in items: items[key]['idx'].append(code);continue
        items[key]=dict(name=name,tick=t,sec=sec,loc=loc,ex=ex,cur=cur,idx=[code])
print(len(items),dict(stat))
wb=openpyxl.load_workbook(D+'Importvorlage_Unternehmen_befuellt_Jordan.xlsx');ws=wb['Unternehmen']
byname=collections.defaultdict(list);bytick=collections.defaultdict(list);allnorm=collections.Counter()
for r in range(2,ws.max_row+1):
    n=norm(ws.cell(r,1).value or '');allnorm[n]+=1
    byname[(ws.cell(r,3).value,n)].append(r)
    if ws.cell(r,6).value: bytick[(ws.cell(r,3).value,str(ws.cell(r,6).value).upper())].append(r)
st=collections.Counter();nr=ws.max_row;newnames=set()
for key,a in items.items():
    land=LAND.get(a['loc'],a['loc']);lst=land if land in LST else 'Sonstige'
    n=norm(a['name'])
    m=byname.get((lst,n)) or bytick.get((lst,a['tick'].upper()))
    if lst=='Sonstige' and not m:  # Sonstige/Land-Mix: auch Name im Land versuchen
        m=byname.get(('Sonstige',n))
    idxs=', '.join(dict.fromkeys(i for i in a['idx']))
    if m:
        r=m[0];fil=[]
        if not ws.cell(r,6).value: ws.cell(r,6).value=a['tick'];fil.append('Ticker')
        if not ws.cell(r,7).value: ws.cell(r,7).value=a['ex'];fil.append('Börse')
        b=SEK.get(a['sec'])
        if b and ws.cell(r,9).value=='sonstige': ws.cell(r,9).value=b;fil.append('Branche')
        if fil:
            old=ws.cell(r,16).value;ws.cell(r,16).value=(old+' | ' if old else '')+f'iShares-Bestandsliste {idxs} (Abgleich per Name/Ticker, bitte prüfen): '+', '.join(fil);st['ergänzt']+=1
        else: st['bereits vollständig']+=1
        continue
    name=a['name'];nn=n
    if nn in allnorm or nn in newnames or not nn: name=f"{a['name']} ({a['tick']})"
    newnames.add(norm(name))
    nr+=1
    note=f"Neu aus iShares-Bestandsliste {idxs}; Branche aus Sektor \"{a['sec']}\", Bank-Flag Platzhalter"+('' if lst!='Sonstige' else f"; Land: {a['loc']}")
    for c,v in {1:name,3:lst,6:a['tick'],7:a['ex'],8:'ja',9:SEK.get(a['sec'],'sonstige'),14:'nein',15:idxs,16:note,17:'https://www.ishares.com/'}.items(): ws.cell(nr,c).value=v
    st['neu']+=1
wb.save(D+'Importvorlage_Unternehmen_befuellt_iShares.xlsx');print(dict(st))
