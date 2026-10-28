"""Alle gelieferten jährlichen Bilanz-/GuV-Posten, mit Originalbezeichnung und Berichtswährung.

Keine Quartals- oder TTM-Daten, keine Schätzungen, keine aufgefüllten Nullwerte.
Der Anbieter ist eine Sekundärquelle; ein erfolgreicher Abruf ist keine Prüfung des Originals.
"""
import argparse,json,math,re,time,unicodedata
from datetime import datetime,timezone
from difflib import SequenceMatcher
from pathlib import Path

HERE=Path(__file__).resolve().parent

def normalized(s):
    s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()
    s=s.replace('&',' and ').replace('grp','group').replace('hldg','holding')
    s=re.sub(r'\b(ag|se|plc|sa|nv|ab|as|asa|spa|group|holding|holdings|limited|ltd|inc|company|corporation|the|and|co|a|b|p|r|n)\b',' ',s)
    return re.sub('[^a-z0-9]','',s)

def identity_ok(company,info):
    names=[company['name'],company.get('ticker_kandidat_name','')]
    actual=[info.get('longName',''),info.get('shortName','')]
    return any(a and b and (a==b or (min(len(a),len(b))>=5 and (a in b or b in a)) or SequenceMatcher(None,a,b).ratio()>=.82)
               for a in map(normalized,names) for b in map(normalized,actual))

def table(df,minimum=2010,maximum=2025):
    out={}
    if df is None or df.empty:return out
    for col in df.columns:
        date=str(col)[:10]
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date) or not minimum<=int(date[:4])<=maximum:continue
        values={}
        for i,label in enumerate(df.index):
            try:value=float(df.iloc[i][col])
            except (ValueError,TypeError):continue
            if math.isfinite(value):values[str(label)]=value
        if values:out[date]=values
    return out

def load_cached(company,root):
    isin=company.get('isin')
    p=root/'boersennotierte-unternehmen/rohdaten/yahoo'/f'{isin}.json'
    if isin and p.exists():
        d=json.loads(p.read_text())
        if any(d.get(k) for k in ('bilanz','guv')):return d
    return None

def fetch(company):
    import yfinance as yf
    candidates=[]
    for k in ('ticker','ticker_kandidat'):
        if company.get(k) and company[k] not in candidates:candidates.append(company[k])
    if not candidates:
        quotes=yf.Search(company['name'],max_results=5,news_count=0).quotes
        candidates=[q['symbol'] for q in quotes if q.get('quoteType')=='EQUITY']
    errors=[]
    for symbol in candidates[:4]:
        try:
            t=yf.Ticker(symbol);info=t.info or {}
            if not identity_ok(company,info):
                errors.append(f'{symbol}: Unternehmensidentität nicht bestätigt');continue
            currency=info.get('financialCurrency')
            if not currency:
                errors.append(f'{symbol}: Berichtswährung fehlt');continue
            raw={'ticker':symbol,'isin':company.get('isin'),'abruf':datetime.now(timezone.utc).isoformat(),
                 'info':{k:info.get(k) for k in ['longName','shortName','country','website','financialCurrency','currency']},
                 'bilanz':table(t.balance_sheet),'guv':table(t.income_stmt)}
            if raw['bilanz'] or raw['guv']:return raw
            errors.append(f'{symbol}: Keine jährlichen Bilanz-/GuV-Daten')
        except Exception as e:errors.append(f'{symbol}: {type(e).__name__}: {str(e)[:180]}')
    raise ValueError('; '.join(errors) or 'Keine eindeutig passende Aktie gefunden')

def annual_only(raw,company):
    result={'unternehmen_id':company['unternehmen_id'],'name':company['name'],'ticker':raw.get('ticker'),
            'waehrung':raw.get('info',{}).get('financialCurrency'),'abruf':raw.get('abruf'),
            'quelle':'Yahoo Finance (Sekundärquelle; Originalabgleich offen)',
            'quelle_url':f"https://finance.yahoo.com/quote/{raw.get('ticker','')}/financials/",
            'identitaet':raw.get('info',{}),'abschluss':'Konzernabschluss laut Anbieter',
            'einheit':'Währungseinheiten (unskaliert); EPS je Aktie und Aktienanzahl gemäß Originalposten',
            'bilanz':{},'guv':{}}
    for family in ('bilanz','guv'):
        for end,values in raw.get(family,{}).items():
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',end) or not 2010<=int(end[:4])<=2025 or not isinstance(values,dict):continue
            clean={k:v for k,v in values.items() if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)}
            if clean:result[family][end]=clean
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fetch',action='store_true');p.add_argument('--shard',default='0/1');p.add_argument('--limit',type=int);p.add_argument('--output',type=Path,default=HERE/'daten');a=p.parse_args()
    part,count=map(int,a.shard.split('/'));assert 0<=part<count
    companies=json.loads((HERE/'unternehmen.json').read_text());a.output.mkdir(parents=True,exist_ok=True);statuses=[]
    selected=[c for i,c in enumerate(companies) if i%count==part][:a.limit]
    for company in selected:
        target=a.output/(company['unternehmen_id']+'.json');status={'unternehmen_id':company['unternehmen_id'],'name':company['name']}
        try:
            raw=load_cached(company,HERE.parent)
            if raw is None and a.fetch:raw=fetch(company);time.sleep(1)
            if raw is None:raise ValueError('Keine lokale Quelle; Onlineabruf noch offen')
            d=annual_only(raw,company)
            if not d['waehrung']:raise ValueError('Berichtswährung nicht belegt')
            if not d['bilanz'] and not d['guv']:raise ValueError('Keine Jahresabschlussdaten bis 2025')
            target.write_text(json.dumps(d,ensure_ascii=False,indent=1,allow_nan=False)+'\n')
            status.update(status='Sekundärquelle geladen; Originalabgleich offen',jahre=sorted(set(x[:4] for k in ('bilanz','guv') for x in d[k])),posten=sum(len(v) for k in ('bilanz','guv') for v in d[k].values()))
        except Exception as e:status.update(status='offen',grund=str(e)[:500])
        statuses.append(status);print(company['unternehmen_id'],company['name'],status['status'],flush=True)
        if a.fetch:time.sleep(.4)
    (a.output/f'status_{part}.json').write_text(json.dumps(statuses,ensure_ascii=False,indent=1)+'\n')
    print(json.dumps({'versucht':len(statuses),'geladen':sum(s['status']!='offen' for s in statuses)}))

if __name__=='__main__':main()
