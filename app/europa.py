"""Tabellenuniversum und vollständige gelieferte Bilanz-/GuV-Posten ins Terminal einbinden."""
import json
from pathlib import Path

COUNTRIES={'Germany':'DE','Deutschland':'DE','UK':'GB','United Kingdom':'GB','France':'FR','Netherlands':'NL','Belgium':'BE','Italy':'IT','Spain':'ES','Sweden':'SE','Switzerland':'CH','Finland':'FI','Denmark':'DK','Norway':'NO','Austria':'AT','Portugal':'PT','Poland':'PL','Greece':'GR','Ireland':'IE','Luxembourg':'LU','United States':'US','Canada':'CA','China':'CN','Czech Republic':'CZ','Czechia':'CZ','Malta':'MT','Cyprus':'CY','Bulgaria':'BG','Liechtenstein':'LI','Hong Kong':'HK','Australia':'AU','Japan':'JP'}
MAP={'bilanzsumme':('bilanz','Total Assets'),'ek':('bilanz','Stockholders Equity'),'umsatz':('guv','Total Revenue'),'ebit':('guv','EBIT'),'ebitda':('guv','EBITDA'),'jue':('guv','Net Income')}

def ergaenzen(root,firmen,nach_id,register):
    root=Path(root);p=root/'europa/unternehmen.json'
    roster=json.loads(p.read_text()) if p.exists() else []
    for c in roster:
        uid=c['unternehmen_id']
        if uid not in register.unternehmen:raise ValueError(f'Unbekannte Unternehmens-ID {uid}')
        f=nach_id.get(uid)
        if f is None:
            f={'id':uid,'name':register.name(uid),'branche':c.get('branche') or 'sonstige','werte':{},'notiert':True}
            firmen.append(f);nach_id[uid]=f
        f.update(tabellenname=c['name'],indizes=c['indizes'],archiv_url=c.get('archiv_url'),archiv_status=c.get('pruefstatus'),im_tabellenuniversum=True)
        for key in ('ticker','isin'):
            if c.get(key) and not f.get(key):f[key]=c[key]
        f['land']=c.get('land') or register.unternehmen[uid].get('land') or 'Unbekannt'
        f['land_basis']='STOXX-Klassifikation' if c.get('land_stoxx') else 'Unternehmensstammdaten'
        file=root/'europa/daten'/f'{uid}.json'
        f['abschluesse']=[]
        if not file.exists():continue
        data=json.loads(file.read_text())
        if data.get('unternehmen_id')!=uid:raise ValueError(f'Identitätskonflikt in {file}')
        dates=sorted(set(data.get('bilanz',{}))|set(data.get('guv',{})),reverse=True)
        for end in dates:
            f['abschluesse'].append({'ende':end,'jahr':int(end[:4]),'waehrung':data.get('waehrung') or 'Unbekannt',
                'bilanz':data.get('bilanz',{}).get(end,{}),'guv':data.get('guv',{}).get(end,{}),
                'quelle':data['quelle'],'quelle_url':data['quelle_url'],'abruf':data.get('abruf'),
                'status':'Sekundärquelle; Originalabgleich offen'})
        # Vergleichsfelder sind Mio. EUR. Fremdwährungsbeträge bleiben ausschließlich in den
        # Originalabschluss-Tabellen; keine stillschweigende Umrechnung oder Währungsmischung.
        latest=next((a for a in f['abschluesse'] if a['jahr']==2025),None)
        if latest:
            for key,(family,label) in MAP.items():
                value=latest[family].get(label)
                if value is not None and latest['waehrung']=='EUR':f['werte'].setdefault(key,value/1e6)
            for key,numerator,denominator in [('ek_quote',('bilanz','Stockholders Equity'),('bilanz','Total Assets')),('ebit_marge',('guv','EBIT'),('guv','Total Revenue'))]:
                a=latest[numerator[0]].get(numerator[1]);b=latest[denominator[0]].get(denominator[1])
                if a is not None and b not in (None,0):f['werte'].setdefault(key,a/b)
    for f in firmen:
        if not f.get('land'):f['land']=register.unternehmen.get(f['id'],{}).get('land') or 'Unbekannt'
        f['land_code']=COUNTRIES.get(f['land'],'ZZ')
    return len(roster)
