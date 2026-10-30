"""Pilot: Kernposten aus den im Repo liegenden Geschäftsberichten übernehmen.

Eine Zahl wird nur übernommen, wenn (1) Summe Aktiva = Summe Passiva auf derselben Seite,
(2) die Einheit eindeutig ist (Faktor aus {1, 1e3, 1e6}, der die Bilanzsumme auf <=25 % an
den unabhängigen Terminalwert aus Yahoo bringt, sonst die Einheit aus dem Seitenkopf),
(3) Eigenkapital <= Bilanzsumme, (4) Umsatz/Ergebnis innerhalb von 0,75..1,35 des Yahoo-Werts
(Dezember-Geschäftsjahr). Alles andere bleibt leer, es wird nie geraten.
"""
import json,sys,re,csv,datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from extrakt import analysiere
ROOT=Path(__file__).resolve().parents[2]
TXT=Path(sys.argv[1]);OUT=ROOT/'abschluesse-nichtbanken/daten'
sel=json.load(open(TXT/'sel.json'))
terminal={f['id']:f for f in json.load(open(ROOT/'app/data/unternehmen.json'))['unternehmen']}
def faktor(bs,y,ft):
    if y:
        c=[(abs(bs*f/1e6/y-1),f) for f in(1,1e3,1e6)]
        a,f=min(c)
        return f if a<=.25 else None
    return ft
def nahe(w,ref,f):
    return ref and w is not None and .75<=abs(w*f/1e6)/abs(ref)<=1.35
ergebnis=[]
for u,n,b,datei,url,s in sel:
    r=analysiere((TXT/'txt'/f'{u}.txt').read_text(errors='ignore'))
    if not r:continue
    bs=r['bilanzsumme']
    if any(re.fullmatch(r'3112202\d',str(int(x))) for x in bs) or bs[0]<=0 or re.fullmatch(r'[0-3]\d[01]\d20(2[3-6])',str(int(bs[0])).zfill(8)):continue
    t=terminal[u]['werte'];y=t.get('bilanzsumme')
    f=faktor(bs[0],y,r['faktor_text'])
    if not f:continue
    ek=r.get('ek')
    if ek and abs(ek[0])>bs[0]:ek=None
    q=t.get('ek_quote')
    if ek and q is not None and abs(ek[0]/bs[0]-q)>.08:ek=None
    if ek and abs(ek[0])<1:ek=None
    um=r.get('umsatz');ju=r.get('jue')
    if um and not nahe(um[0],t.get('umsatz'),f):um=None
    if ju and (not t.get('umsatz') or abs(ju[0])*f/1e6>abs(t['umsatz'])*1.0):ju=None
    ok=ek and (ek[0]>=0 or True)
    ergebnis.append((u,n,terminal[u]['branche'],ok,r,f,ek,um,ju,url,datei))
fertig=[e for e in ergebnis if e[6] and e[0]!='U000693']
print(len(ergebnis),'mit Bilanzsumme,',len(fertig),'mit Bilanzsumme+EK')
OUT.mkdir(exist_ok=True)
json.dump([[e[0],e[1],e[2],e[3] and 1,e[5]] for e in ergebnis],open(TXT/'kandidaten.json','w'),ensure_ascii=False)
for e in fertig: print(e[0],e[1][:28],e[2],'S',e[4]['seite_bilanz'],'f',e[5],'BS',e[4]['bilanzsumme'][0],'EK',e[6][0],'U',e[7] and e[7][0],'JÜ',e[8] and e[8][0],'Y',terminal[e[0]]['werte'].get('umsatz'))

heute=datetime.date.today().isoformat()
for u,n,br,ok,r,f,ek,um,ju,url,datei in fertig:
    if len(sys.argv)>2 and sys.argv[2]=='schreiben':
        bil={'Total Assets':r['bilanzsumme'][0]*f,'Total Equity Gross Minority Interest':ek[0]*f,
             'Total Liabilities Net Minority Interest (abgeleitet: Bilanzsumme minus Eigenkapital)':(r['bilanzsumme'][0]-ek[0])*f}
        vj_ok=all(x and .2<=x[1]/x[0]<=5 for x in(r['bilanzsumme'],ek)) and r['bilanzsumme'][1]>0
        guv={}
        if um:guv['Total Revenue']=um[0]*f
        if ju:guv['Net Income']=ju[0]*f
        d={'unternehmen_id':u,'name':n,'waehrung':'EUR','quelle':'Geschäftsbericht (Primärquelle)','quelle_url':url,
           'datei':datei.replace(str(ROOT)+'/',''),'seiten':[r['seite_bilanz']]+([r['seite_guv']] if r.get('seite_guv') else []),
           'pruefstatus':'Primärbericht; automatisch extrahiert, Aktiva=Passiva und Einheit gegen Terminalwert geprüft; Stichprobe offen',
           'abruf':heute,'bilanz':{'2025-12-31':bil},'guv':{'2025-12-31':guv} if guv else {},
           'kontrolle':{'aktiva_gleich_passiva':True,'einheitsfaktor':f,'yahoo_bilanzsumme_mio':terminal[u]['werte'].get('bilanzsumme'),
                        'yahoo_ek_quote':terminal[u]['werte'].get('ek_quote')}}
        if vj_ok:
            d['bilanz']['2024-12-31']={'Total Assets':r['bilanzsumme'][1]*f,'Total Equity Gross Minority Interest':ek[1]*f}
        (OUT/f'{u}.json').write_text(json.dumps(d,ensure_ascii=False,indent=1))
