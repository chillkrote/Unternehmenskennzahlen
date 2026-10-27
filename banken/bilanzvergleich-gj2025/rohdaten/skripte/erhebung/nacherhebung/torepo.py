import json,os,re,csv,hashlib,shutil,unicodedata,urllib.parse,glob
R="/home/user/unternehmenskennzahlen/banken/bilanzvergleich-gj2025/"
ne=json.load(open('/mnt/project-files/bilanzvergleich/rohdaten/nacherhebung_2026-10-27.json'))
loc={}
for f in glob.glob('crawl/*_dl.json'):
    for r in json.load(open(f)): loc.setdefault(r['url'],r['file'])
idx=list(csv.reader(open(R+'dokumente/index.csv',encoding='utf-8-sig'),delimiter=';'))
hdr,rows=idx[0],idx[1:]
known={r[5] for r in rows}; shas={r[7] for r in rows}
def slug(s):
    s=unicodedata.normalize('NFKD',s.replace('ß','ss').replace('ä','ae').replace('ö','oe').replace('ü','ue').replace('Ä','Ae').replace('Ö','Oe').replace('Ü','Ue')).encode('ascii','ignore').decode()
    return re.sub(r'[^A-Za-z0-9]+','-',s).strip('-').lower()[:60]
used={}
for bank,e in ne.items():
    for y,dd in (e.get('jahre') or {}).items():
        for k,v in dd.items():
            if isinstance(v,dict) and v.get('quelle'): used.setdefault((bank,v['quelle']),(y,v.get('dokument','')))
    b2=e.get('bilanz2025')
    if isinstance(b2,dict) and b2.get('quelle'): used.setdefault((bank,b2['quelle']),('2025','Bilanz'))
new=0;miss=[]
for (bank,u),(y,doc) in sorted(used.items()):
    if u in known: continue
    p=loc.get(u)
    if not p or not os.path.exists(p) or open(p,'rb').read(5)!=b'%PDF-': miss.append((bank,u)); continue
    sha=hashlib.sha256(open(p,'rb').read()).hexdigest()
    if sha in shas: continue
    base=slug(re.sub(r'\.pdf$','',urllib.parse.unquote(u.split('?')[0]).split('/')[-1],flags=re.I))[:80] or 'dokument'
    d=R+'dokumente/'+slug(bank)+'/'; os.makedirs(d,exist_ok=True)
    fn=base+'.pdf'
    if os.path.exists(d+fn): fn=f"{base}-{sha[:6]}.pdf"
    shutil.copy(p,d+fn)
    art='Offenlegungsbericht' if 'Offenlegung' in doc or 'ffenleg' in u else 'Jahresabschluss/Geschäftsbericht'
    rows.append([bank,art,y,'dokumente/'+slug(bank)+'/'+fn,'Originaldokument (PDF)',u,'Abruf 27.10.2026',sha,'Nacherhebung 27.10.2026 (Lückenfüllung)','',''])
    shas.add(sha); known.add(u); new+=1
w=csv.writer(open(R+'dokumente/index.csv','w',encoding='utf-8-sig',newline=''),delimiter=';')
w.writerow(hdr); w.writerows(rows)
print('neu',new,'fehlend',len(miss)); [print(m) for m in miss[:20]]
