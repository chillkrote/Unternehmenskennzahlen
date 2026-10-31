"""Yahoo-Jahresabschlüsse (Sekundärquelle) aus den im Repo liegenden Rohdaten übernehmen.

Quelle: boersennotierte-unternehmen/rohdaten/yahoo/<ISIN>.json (ISIN-gebunden, deshalb identitätssicher).
Es werden alle jährlichen Bilanz-, GuV- und Cashflow-Posten mit Originalbezeichnung übernommen, Berichtswährung aus
info.financialCurrency; fehlt sie, bleibt das Unternehmen offen (Datei `offen.csv`), es wird keine Währung angenommen.
Nur Nicht-Banken ohne Abschlüsse in europa/. Ausgabe: abschluesse-nichtbanken/yahoo/<ID>.json
"""
import csv,json,math,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'abschluesse-nichtbanken/yahoo'
term=json.load(open(ROOT/'app/data/unternehmen.json'))['unternehmen']
uni={r['unternehmen_id']:r for r in csv.DictReader(open(ROOT/'boersennotierte-unternehmen/universum/universum.csv',encoding='utf-8-sig'),delimiter=';')}
def sauber(tab):
    out={}
    for end,vals in (tab or {}).items():
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',end) or not 2010<=int(end[:4])<=2025 or not isinstance(vals,dict):continue
        v={k:x for k,x in vals.items() if isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)}
        if v:out[end]=v
    return out
OUT.mkdir(exist_ok=True);offen=[];n=0;jahre={}
for f in term:
    if f.get('branche')=='banken' or f.get('abschluesse'):continue
    isin=uni.get(f['id'],{}).get('isin_haupt');p=ROOT/f'boersennotierte-unternehmen/rohdaten/yahoo/{isin}.json'
    if not isin or not p.exists():offen.append((f['id'],f['name'],'keine Yahoo-Rohdaten'));continue
    r=json.load(open(p));info=r.get('info') or {}
    b,g,c=sauber(r.get('bilanz')),sauber(r.get('guv')),sauber(r.get('cashflow'))
    if not b and not g:offen.append((f['id'],f['name'],'keine Jahresabschlussdaten'));continue
    if not info.get('financialCurrency'):offen.append((f['id'],f['name'],'Berichtswährung nicht belegt'));continue
    d={'unternehmen_id':f['id'],'name':f['name'],'ticker':r.get('ticker'),'isin':isin,'waehrung':info['financialCurrency'],'abruf':r.get('abruf'),
       'quelle':'Yahoo Finance (Sekundärquelle; Originalabgleich offen)','quelle_url':f"https://finance.yahoo.com/quote/{r.get('ticker','')}/financials/",
       'einheit':'Währungseinheiten (unskaliert)','bilanz':b,'guv':g,'cashflow':c}
    (OUT/f"{f['id']}.json").write_text(json.dumps(d,ensure_ascii=False,indent=1,allow_nan=False)+'\n');n+=1
    jahre[len(b)]=jahre.get(len(b),0)+1
with open(OUT/'offen.csv','w',encoding='utf-8-sig',newline='') as fh:
    w=csv.writer(fh,delimiter=';');w.writerow(['unternehmen_id','name','grund']);w.writerows(offen)
print(n,'übernommen,',len(offen),'offen',jahre)
