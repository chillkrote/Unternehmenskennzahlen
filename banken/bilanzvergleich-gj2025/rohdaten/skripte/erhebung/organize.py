import json,os,re,hashlib,shutil,csv,unicodedata,datetime,subprocess
S='/tmp/claude-0/-home-user/9059df30-471a-5482-b7c9-6ef849729b0a/scratchpad/'
OUT='/home/user/unternehmenskennzahlen/banken/bilanzvergleich-gj2025/'
U=json.load(open(S+'urls_all.json'))
R={m['url']:m for m in json.load(open(S+'dlall/results.json'))}
# local fallbacks
loc={}
for x in json.load(open(S+'bil/src.json')): loc[x['url']]=S+f"bil/pdf/{x['i']}.pdf"
for l in open(S+'bil2/ol_urls.tsv'):
    k,n,u=l.rstrip('\n').split('\t'); loc[u]=S+f'bil2/ol/{k}.pdf'
B=json.load(open('/mnt/project-files/bilanzvergleich/rohdaten/bilanzen_2025.json'))
named={'Deutsche Apotheker- und Ärztebank eG (apoBank)':'apo','Ostsächsische Sparkasse Dresden':'osd','Förde Sparkasse':'foe','Kreissparkasse Heilbronn':'hn',
 'Landessparkasse zu Oldenburg':'lzo_Geschaeftsjahr_2025','UmweltBank AG':'umw','MERKUR PRIVATBANK KGaA':'mer','GRENKE BANK AG':'gre','Bank11 für Privatkunden und Handel GmbH':'b11',
 'Hanseatic Bank GmbH & Co KG':'han','Sparda-Bank München eG':'spm'}
for n,f in named.items(): loc[B[n]['source_url']]=S+f'bil2/pdf/{f}.pdf'
def ispdf(p): return os.path.exists(p) and open(p,'rb').read(5)==b'%PDF-'
def slug(s):
    s=unicodedata.normalize('NFKD',s.replace('ß','ss').replace('ä','ae').replace('ö','oe').replace('ü','ue').replace('Ä','Ae').replace('Ö','Oe').replace('Ü','Ue')).encode('ascii','ignore').decode()
    return re.sub(r'[^A-Za-z0-9]+','-',s).strip('-').lower()[:60]
def kind(u):
    l=u.lower()
    for k,rx in [('Offenlegungsbericht',r'offenleg|disclosure|pillar|cc2|433'),('Halbjahresbericht',r'halbjahr|half|30-?06|h1'),('Rangliste/Verband',r'rangliste|bvr\.de|dsgv|liste_alle|allebanken|all.local'),
                 ('Jahresabschluss/Geschäftsbericht',r'jahresabschluss|geschaeftsbericht|gesch%c3%a4ftsbericht|jahresfinanzbericht|annual|_ja|ja2|ja-|jahresbericht|gb20|gb_20|bilanz|lagebericht|geschaeftsjahr|report|einzelabschluss|finanzbericht|testat|abschluss')]:
        if re.search(rx,l): return k
    return 'Sonstiges'
import openpyxl
wb=openpyxl.load_workbook('/mnt/project-files/bilanzvergleich/Bilanzvergleich_Banken_GJ2025.xlsx',data_only=True)
CAN=[r[3] for r in wb['Übersicht'].iter_rows(min_row=2,values_only=True) if r[3]]
def canon(b):
    if b in CAN: return b
    k=slug(b)
    for c in CAN:
        kc=slug(c)
        if k.startswith(kc[:18]) or kc.startswith(k[:18]): return c
    return b
rows=[]; today='2026-10-26'
shutil.rmtree(OUT+'dokumente',ignore_errors=True); shutil.rmtree(OUT+'webseiten',ignore_errors=True)
os.makedirs(OUT+'dokumente',exist_ok=True); os.makedirs(OUT+'webseiten',exist_ok=True)
for u,ctx in sorted(U.items()):
    banks=sorted({canon(b) for b,_ in ctx if b and not b.startswith('http')})
    m=R.get(u,{}); f=S+'dlall/files/'+m.get('h','x'); src='Download 26.10.2026'
    if not ispdf(f) and u in loc and ispdf(loc[u]): f=loc[u]; src='Download 24.–26.10.2026 (Originaldatei aus der Auswertung)'
    folder=slug(banks[0]) if len(banks)==1 else '_mehrere-banken'
    base=os.path.basename(re.sub(r'[?#].*','',u)) or 'index'
    base=slug(re.sub(r'\.(pdf|html?)$','',base,flags=re.I).replace('%20','-'))[:80] or 'dokument'
    if ispdf(f):
        dst=f'dokumente/{folder}/{base}.pdf'; status='Originaldokument (PDF)'
    elif m.get('code')=='200' and os.path.exists(f) and os.path.getsize(f)>2000 and 'HTML' in m.get('file',''):
        dst=f'webseiten/{folder}/{base}.html'; status='Webseiten-Schnappschuss (HTML)'
    else:
        dst=''; status=f"nicht abrufbar (HTTP {m.get('code','?')})"
    sha=''
    if dst:
        p=OUT+dst; i=2
        while os.path.exists(p): p=OUT+dst.replace('.','-%d.'%i,1) if False else re.sub(r'(\.\w+)$',f'-{i}\\1',OUT+dst); i+=1
        os.makedirs(os.path.dirname(p),exist_ok=True); shutil.copyfile(f,p); dst=p[len(OUT):]
        sha=hashlib.sha256(open(p,'rb').read()).hexdigest()
    yr=sorted(set(re.findall(r'(?<!\d)(20[12]\d)(?!\d)',u)))
    rows.append({'bank':'; '.join(banks) if banks else '','dokumentart':kind(u),'jahr_laut_link':', '.join(yr),'datei':dst,'status':status,'quelle_url':u,
                 'abruf':src if dst else today,'sha256':sha,'verwendet_in':'; '.join(sorted({c for _,c in ctx}))})
with open(OUT+'dokumente/index.csv','w',newline='',encoding='utf-8-sig') as o:
    w=csv.DictWriter(o,fieldnames=list(rows[0]),delimiter=';'); w.writeheader(); w.writerows(rows)
import collections; print(collections.Counter(r['status'].split(' (')[0] for r in rows))
