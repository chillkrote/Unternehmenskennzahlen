"""Kernposten aus den im Repo liegenden Geschäftsberichten 2025 übernehmen (Nicht-Banken ohne Abschlussposten).

Prüfregeln (alles andere bleibt leer, es wird nie geraten):
- Bilanzsumme: Summe Aktiva = Summe Passiva (gleiche oder Folgeseite), sonst einzelne Zeile, die dem Terminalwert (Yahoo) auf 3 % entspricht (Feld `pruefung`).
- Einheit: Faktor aus {1, 1e3, 1e6}, der die Bilanzsumme auf 25 % an den Terminalwert bringt, sonst Seitenkopf.
- Eigenkapital <= Bilanzsumme und Eigenkapitalquote innerhalb 8 Punkten der Yahoo-Quote.
- Umsatz innerhalb 35 % des Yahoo-Werts; Ergebnis/EBIT gegen Yahoo-Nettomarge (4 Punkte) bzw. EBIT-Marge (5 Punkte).
- Operativer Cashflow: Kapitalflussrechnung-Seite, Betrag kleiner als die Bilanzsumme (keine Gegenprobe vorhanden, im Feld `kontrolle` vermerkt).
Aufruf: uebernehmen.py <Arbeitsordner> [schreiben]
"""
import json,sys,datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from extrakt import analysiere
ROOT=Path(__file__).resolve().parents[2]
TXT=Path(sys.argv[1]);OUT=ROOT/'abschluesse-nichtbanken/daten'
sel=json.load(open(TXT/'sel.json'))
terminal={f['id']:f for f in json.load(open(ROOT/'app/data/unternehmen.json'))['unternehmen']}
SPERRE={'U000693':'Berichtswährung nicht EUR belegt','U000259':'Berichtswährung CNY'}
heute=datetime.date.today().isoformat();stat={'bericht':len(sel),'bilanz':0,'ek':0,'umsatz':0,'jue':0,'ebit':0,'cfo':0};log=[]
for u,n,br,datei,url,s in sel:
    if u in SPERRE:continue
    w=terminal[u]['werte']
    r=analysiere((TXT/'txt'/f'{u}.txt').read_text(errors='ignore'),w)
    if not r:continue
    f=r['faktor'];bs=r['bilanzsumme'];ek=r['ek']
    q=w.get('ek_quote')
    if ek and (abs(ek[0])<1 or (q is not None and abs(ek[0]/bs[0]-q)>.08)):ek=None
    stat['bilanz']+=1;stat['ek']+=bool(ek)
    bil={'Total Assets':bs[0]*f}
    if ek:
        bil['Total Equity Gross Minority Interest']=ek[0]*f
        bil['Total Liabilities Net Minority Interest (abgeleitet: Bilanzsumme minus Eigenkapital)']=(bs[0]-ek[0])*f
    guv={}
    for k,lab in(('umsatz','Total Revenue'),('ebit','EBIT'),('jue','Net Income')):
        if k in r:guv[lab]=r[k][0]*f;stat[k]+=1
    d={'unternehmen_id':u,'name':n,'waehrung':'EUR','quelle':'Geschäftsbericht (Primärquelle)','quelle_url':url,
       'datei':str(datei),'seiten':sorted({r[k] for k in('seite_bilanz','seite_ek','seite_guv','seite_cf') if k in r}),
       'pruefstatus':'Primärbericht; automatisch extrahiert und gegen Terminalwerte geprüft; Stichprobe offen',
       'abruf':heute,'bilanz':{'2025-12-31':bil},'guv':{'2025-12-31':guv} if guv else {},
       'kontrolle':{'bilanzsumme':r['pruefung'],'einheitsfaktor':f,'yahoo_bilanzsumme_mio':w.get('bilanzsumme'),'yahoo_ek_quote':q}}
    if bs[1]>0 and .2<=bs[1]/bs[0]<=5:
        d['bilanz']['2024-12-31']={'Total Assets':bs[1]*f}
        if ek and ek[1]>0 and abs(ek[1])<=bs[1]:d['bilanz']['2024-12-31']['Total Equity Gross Minority Interest']=ek[1]*f
    if 'cfo' in r:
        d['cashflow']={'2025-12-31':{'Operating Cash Flow':r['cfo'][0]*f}};stat['cfo']+=1
        d['kontrolle']['cashflow']='Seite gelesen, keine Gegenprobe'
    log.append(u)
    if len(sys.argv)>2 and sys.argv[2]=='schreiben':
        OUT.mkdir(exist_ok=True);(OUT/f'{u}.json').write_text(json.dumps(d,ensure_ascii=False,indent=1))
print(json.dumps(stat))
