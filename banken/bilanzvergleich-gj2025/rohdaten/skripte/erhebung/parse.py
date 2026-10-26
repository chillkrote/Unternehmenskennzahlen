import json,re,os,sys,openpyxl
A=[('barreserve',r'Barreserve|Cash reserve'),('schuldtitel_oeff',r'Schuldtitel öffentlicher Stellen|Debt instruments of public'),('ford_ki',r'Forderungen an Kreditinstitute|Receivables from banks|Loans and advances to banks'),
   ('ford_kunden',r'Forderungen an Kund(innen und Kund)?en|Receivables from customers|Loans and advances to customers'),('schuldverschr',r'Schuldverschreibungen und andere\s*(festverzinsliche)?|Bonds and other fixed'),
   ('aktien',r'Aktien und andere nicht|Equity shares and other|Shares and other variable'),('handel_a',r'Handelsbestand|Trading assets'),('beteiligungen',r'Beteiligungen|Participating interests|Equity investments'),
   ('verb_unt',r'Anteile an verbundenen Unternehmen|Investments in affiliated|Interests in affiliated|Shares in affiliated'),('treuhand_a',r'Treuhandvermögen|Assets held in trust|Trust assets'),('ausgleich',r'Ausgleichsforderungen'),
   ('immat',r'Immaterielle Anlagewerte|Intangible'),('sachanlagen',r'Sachanlagen|Tangible assets|Property and equipment|Fixed assets'),('ausst_einl',r'(Ausstehende Einlagen|Eingefordertes)'),('sonst_vg',r'Sonstige Vermögensgegenstände|Other assets|Sundry assets'),
   ('rap_a',r'Rechnungsabgrenzungsposten|Prepaid expenses|Deferred items'),('akt_lat',r'Aktive latente Steuern|Deferred tax assets'),('aktiv_ub',r'Aktiver Unterschiedsbetrag|Excess of plan assets|Active difference|Overfunded plan assets|Positive difference'),('fehlbetrag',r'Nicht durch Eigenkapital')]
P=[('verb_ki',r'Verbindlichkeiten gegenüber\s*Kreditinstituten|Liabilities to banks|Deposits from banks'),('verb_kunden',r'Verbindlichkeiten gegenüber\s*Kunden|Liabilities to customers|Deposits from customers|Customer [Dd]eposits|Amounts due to customers'),('verbrieft',r'Verbriefte Verbindlichkeiten|Liabilities in certificate form|Securitised liabilities|Securitized liabilities'),
   ('handel_p',r'Handelsbestand|Trading liabilities'),('treuhand_p',r'Treuhandverbindlichkeiten|Liabilities held in trust|Trust liabilities'),('sonst_verb',r'Sonstige Verbindlichkeiten|Other liabilities|Sundry liabilities'),('rap_p',r'Rechnungsabgrenzungsposten|Deferred income'),
   ('pas_lat',r'Passive latente Steuern|Deferred tax liabilities'),('rueckst',r'Rückstellungen|Provisions'),('sonderposten',r'Sonderposten mit Rücklage'),('nachrang',r'Nachrangige Verbindlichkeiten|Subordinated liabilities'),
   ('genuss',r'Genussrechtskapital|Profit participation|Participation rights capital'),('fonds',r'Fonds für allgemeine Bankrisiken|Fund for general banking risks'),('at1',r'Instrumente des zusätzlichen|Additional Tier 1|Instruments for Additional|Additional Regulatory Tier|Additional equity components'),('ek',r'Eigenkapital|Capital and reserves|Equity')]
SPACE=[False]
COMMA=[False]
NUM_CM=re.compile(r'(?<![\w.,])(-?\d{1,3}(?:,\d{3})+|-?\d+)(?![\w]|,\d|\.\d|\.(?=\s))')
PREV=[False]
NUM_SP=re.compile(r'(?<![\w.,])(-?\d{1,3}(?: \d{3})+(?:,\d+)?|-?\d+,\d+|-?\d+)(?![\w]|\.\d|\.(?=\s)| \d{3}(?!\d))')
NUM=re.compile(r'(?<![\w.,])(-?\d{1,3}(?:\.\d{3})+(?:,\d+)?|-?\d+,\d+|-?\d+)(?![\w]|\.\d|\.(?=\s))')
def nums(line):
    out=[]
    for m in (NUM_CM if COMMA[0] else NUM_SP if SPACE[0] else NUM).finditer(line):
        if m.start()<12 and re.match(r'^\s*\d{1,2}[a-z]?\.?\s',line[:m.end()+2]) : continue
        s=m.group(1)
        if re.fullmatch(r'\d{4}',s) and 1990<int(s)<2030: continue
        v=float(s.replace(',','')) if COMMA[0] else float(s.replace(' ','').replace('.','').replace(',','.'))
        out.append((m.end(),v))
    return out
NUMA={'1':'barreserve','2':'schuldtitel_oeff','3':'ford_ki','4':'ford_kunden','5':'schuldverschr','6':'aktien','6a':'handel_a','7':'beteiligungen','8':'verb_unt','9':'treuhand_a','10':'ausgleich','11':'immat','12':'sachanlagen','13':'ausst_einl','14':'sonst_vg','15':'rap_a','16':'akt_lat','17':'aktiv_ub','18':'fehlbetrag'}
NUMP={'1':'verb_ki','2':'verb_kunden','3':'verbrieft','3a':'handel_p','4':'treuhand_p','5':'sonst_verb','6':'rap_p','6a':'pas_lat','7':'rueckst','8':'sonderposten','9':'nachrang','10':'genuss','11':'fonds','12':'ek'}
def header(line,keys):
    line=line.replace('\x07','').replace('\xad','')
    t=line.strip()
    t2=re.sub(r'^(\d{1,2}[a-z]?\.?|[a-z]\))\s*','',t)
    for k,rx in keys:
        if re.match(rx,t2): return k
    return None
def parse_side(text,keys,sumrx,strategy='col'):
    text=text.replace('\t','    ')
    SPACE[0]=len(re.findall(r'\d{1,3} \d{3}(?!\d)',text))>10 and len(re.findall(r'\b\d{1,3}\.\d{3}\b(?!\.)',text))<5
    COMMA[0]=len(re.findall(r'\b\d{1,3},\d{3}\b',text))>10 and len(re.findall(r',\d{2}\b(?!\d)',text))<5
    lines=text.split('\n')
    si=[n for n,l in enumerate(lines) if re.search(sumrx,l)]
    if not si: return None,'kein Summenzeile'
    s=si[0]; sn=nums(re.sub(r'\(.*?\)','',lines[s]))
    if not sn: return None,'Summe ohne Zahl'
    if strategy=='col':
        if len(sn)<2: return None,'Summe ohne 2 Zahlen'
        if PREV[0]: sn=sn+[(sn[-1][0]+40,0)]
        C=sn[-2][0]; total=sn[-2][1]; TOL=max(3,min(10,(sn[-1][0]-C)/2))
    elif strategy=='hdr':
        total=sn[-2][1] if len(sn)>=2 else sn[0][1]; C=None; TOL=6
    else:
        total=sn[0][1] if strategy=='cent' else (sn[-2][1] if len(sn)>=2 else sn[0][1])
    res={}; cur=None
    for l in lines[:s]:
        if strategy=='hdr':
            m1=re.search(r'31\.12\.2025|Dec\.? 31, 2025',l); m2=re.search(r'31\.12\.2024|Dec\.? 31, 2024',l)
            if m1 and m2: C=m1.end(); TOL=max(3,min(8,(m2.end()-C)/2))
        h=header(l,keys)
        numbered=re.match(r'^\s*\d{1,2}[a-z]?\.\s',l)
        if h and (numbered or h not in res):
            cur=h; res.setdefault(cur,0.0)
        elif numbered and not h:
            nn=re.match(r'^\s*(\d{1,2}[a-z]?)\.',l).group(1)
            M=NUMA if keys is A else NUMP
            cur=M.get(nn,'?'+l.strip()[:40]) if not re.search(r'Leasing',l) else 'leasing'; res.setdefault(cur,0.0)
        if not cur: continue
        if re.search(r'Übertrag|Carried forward|Zwischensumme',l): continue
        if strategy in ('col','hdr'):
            if re.search(r'darunter|davon|thereof|of which',l): continue
            if strategy=='hdr' and C is None: continue
            for e,v in nums(re.sub(r'[—–]','0',l)):
                if abs(e-C)<=TOL: res[cur]=v
        else:
            if re.search(r'darunter|davon|thereof|of which',l): continue
            ll=re.sub(r'\(.*?\)','',l)
            if strategy=='cent':
                vs=[v for e,v in nums(ll) if re.search(r',\d\d$', '%s'%v) or True]
                vs=[float(m.replace('.','').replace(',','.')) for m in re.findall(r'(?<![\d.,])-?\d{1,3}(?:\.\d{3})*,\d{2}(?!\d)',ll)]
            else:
                ns=nums(ll); vs=[v for e,v in ns[:-1]] if len(ns)>=2 else []
            if vs: res[cur]=max(res[cur],max(vs))
    return {'total':total,'pos':res},None
SA=r'Total assets|Summe der Aktiva|Summe Aktiva|Aktiva insgesamt|Summe der Aktivseite|^\s*Summe\s+[\d.]|Bilanzsumme'
SP=r'Total liabilities and|Summe der Passiva|Summe Passiva|Passiva insgesamt|Summe der Passivseite|^\s*Summe\s+[\d.]|Bilanzsumme'
def good(x):
    return bool(x) and x['total']>=500 and sum(1 for v in x['pos'].values() if v)>=4 and abs(sum(x['pos'].values())-x['total'])<=max(3,x['total']*2e-5)
def best(page,keys,rx):
    last=(None,'?')
    for st in (('col',) if PREV[0] else ('col','hdr','cent','drop')):
        try: r,e=parse_side(page,keys,rx,st)
        except Exception as ex: r,e=None,str(ex)
        if good(r): r['strategy']=st; return r,None
        if r and last[0] is None: last=(r,e)
    return last
def run(i,pa,pp):
    pages=open(f'txt/{i}.txt',errors='ignore').read().split('\f')
    if pa==pp:
        pg=pages[pa].replace('\t','    ')
        xs=[l.find('Verbindlichkeiten gegenüber') for l in pg.split('\n') if l.find('Verbindlichkeiten gegenüber')>40]
        x=min(xs)-6 if xs else len(pg)
        left='\n'.join(l[:x] for l in pg.split('\n')); right='\n'.join(l[x:] for l in pg.split('\n'))
        a,ea=best(left,A,SA); p,ep=best(right,P,SP)
    else:
        a,ea=best(pages[pa],A,SA)
        p,ep=best(pages[pp],P,SP)
    return a,ea,p,ep
if __name__=='__main__':
    pg=json.load(open('pages.json')); S={x['i']:x for x in json.load(open('src.json'))}
    wb=openpyxl.load_workbook('/mnt/project-files/bilanzvergleich/Bilanzvergleich_Banken_GJ2025.xlsx',data_only=True)
    ws=wb['Übersicht']; K={r[3]:r for r in ws.iter_rows(min_row=2,values_only=True) if r[3]}
    out={}
    for i,v in pg.items():
        i=int(i); nm=S[i]['name']; PREV[0]= i in (17,55)
        if not v['a'] or not v['p']: print(i,nm[:30],'PAGES?'); continue
        pa=v['a'][-1] if i in (2,9,24,61,72,76) else v['a'][0]
        pp=[x for x in v['p'] if x>=pa] or v['p']; pp=pp[0]
        try: a,ea,p,ep=run(i,pa,pp)
        except Exception as e: print(i,nm[:30],'ERR',e); continue
        bs=K.get(nm,[None]*12)[6]
        if not a or not p: print(i,nm[:30],'FAIL',ea,ep); continue
        sc=bs/a['total'] if bs else None
        sa=sum(a['pos'].values()); sp=sum(p['pos'].values())
        ok=abs(sa-a['total'])<=max(2,a['total']*1e-5) and abs(sp-p['total'])<=max(2,p['total']*1e-5) and abs(a['total']-p['total'])<2
        print(i,nm[:30],'OK' if ok else 'MISMATCH', 'scale',sc and round(sc,6), 'A',a['total'],round(sa,1),'P',p['total'],round(sp,1))
        out[i]={'name':nm,'pa':pa,'pp':pp,'a':a,'p':p,'scale':sc,'ok':ok}
    json.dump(out,open('parsed.json','w'),ensure_ascii=False,indent=0)
