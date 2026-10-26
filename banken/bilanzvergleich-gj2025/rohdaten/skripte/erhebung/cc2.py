import re,sys,json
NUM=re.compile(r'(?<![\w.,])(-?\d{1,3}(?:\.\d{3})*(?:,\d+)?|-?\d+(?:,\d+)?|---|–|-)(?![\w.,])')
AK=[('barreserve',r'Barreserve'),('schuldtitel_oeff',r'Schuldtitel'),('ford_ki',r'Forderungen an Kredit'),('ford_kunden',r'Forderungen an Kund'),
    ('schuldverschr',r'Schuldverschreibung'),('aktien',r'Aktien'),('handel_a',r'Handelsbestand'),('beteiligungen',r'Beteiligungen'),
    ('verb_unt',r'verbundenen'),('treuhand_a',r'Treuhand'),('ausgleich',r'Ausgleichsford'),('immat',r'Immaterielle'),('sachanlagen',r'Sachanlagen'),
    ('sonst_vg',r'Sonstige Vermögens'),('rap_a',r'Rechnungsabgrenzung'),('akt_lat',r'latente'),('aktiv_ub',r'Unterschiedsbetrag'),('leasing',r'Leasing')]
PK=[('verb_ki',r'Verbindlichkeiten gegenüber Kredit'),('verb_kunden',r'Verbindlichkeiten gegenüber Kund'),('verbrieft',r'Verbriefte'),
    ('handel_p',r'Handelsbestand'),('treuhand_p',r'Treuhand'),('sonst_verb',r'Sonstige Verbindlichk'),('rap_p',r'Rechnungsabgrenzung'),
    ('pas_lat',r'latente'),('rueckst',r'Rückstellungen'),('sonderposten',r'bauspartechn|Sonderposten'),('nachrang',r'Nachrangige'),('genuss',r'Genussrecht'),
    ('fonds',r'Fonds für allgemeine'),('at1',r'zusätzlichen'),('ek',r'^\s*(\d+\.?\s+)?Eigenkapital\s*(?!insgesamt)')]
TOL=[3]
def val(s):
    if s in ('---','–','-'): return 0.0
    return abs(float(s.replace('.','').replace(',','.')))
def parse(txt):
    i=txt.find('Barreserve'); seg=txt[i-200:]
    lines=seg.split('\n'); lines[0]=lines[0][lines[0].find('Barreserve')-20 if 'Barreserve' in lines[0] else 0:]
    lines=seg.split('\n')
    # anchor
    anc=None; tot={}
    for l in lines:
        if re.search(r'Aktiva insgesamt|Aktiva gesamt|Gesamtaktiva|Summe der Aktiva|Summe Aktiva|Bilanzsumme',l):
            m=[x for x in NUM.finditer(l) if x.group(1) not in ('-','–','---')]
            if m: anc=m[0].end(); tot['a']=val(m[0].group(1)); break
    side='a'; a={}; p={}; pend=None; eki=None; carry=''
    for l in lines:
        if re.search(r'Passiva insgesamt|Gesamtpassiva|Summe der Passiva|Summe Passiva',l):
            m=[x for x in NUM.finditer(l) if abs(x.end()-anc)<=TOL[0]]; tot['p']=val(m[0].group(1)) if m else None; break
        if re.search(r'Passiva|Passivseite',l) and not re.search(r'latente|Unterschiedsbetrag',l): side='p'; pend=None; continue
        if re.search(r'Eigenkapital insgesamt',l):
            m=[x for x in NUM.finditer(l) if abs(x.end()-anc)<=TOL[0]]; eki=val(m[0].group(1)) if m else None; continue
        if re.search(r'davon|darunter|insgesamt|Gesamt',l): pend=None; continue
        keys=AK if side=='a' else PK
        m=[x for x in NUM.finditer(l) if abs(x.end()-anc)<=TOL[0] and x.start()>30]
        lab=l if re.match(r'^\s*\d+\.?\s+[A-ZÄÖÜ]',l) or not carry else carry+' '+l.strip()
        carry=lab.rstrip() if (not m and re.search(r'gegenüber\s*$|-\s*$',lab)) else ''
        k=next((k for k,rx in keys if re.search(rx,re.sub(r'-\s+','',lab))),None)
        if carry and not k: continue
        d=a if side=='a' else p
        if not k:
            if pend and m and not re.match(r'^\s*\d+\.?\s+[A-ZÄÖÜ]',l): d[pend]=val(m[0].group(1)); pend=None
            elif re.match(r'^\s*\d+\.?\s+[A-ZÄÖÜ]',l): pend=None
            continue
        if k in d and d[k]: continue
        if m: d[k]=val(m[0].group(1)); pend=None
        else: d[k]=0.0; pend=k
    if not p.get('ek') and tot.get('p'): p['ek']=round(tot['p']-sum(v for k,v in p.items() if k!='ek'),3); tot['ek_als_rest']=True
    return a,p,tot
def best(txt):
    r=[]
    for tl in (2,3,4,5,6,7,8):
        TOL[0]=tl
        try: a,p,t=parse(txt)
        except Exception: continue
        if not t.get('a') or not t.get('p'): continue
        r.append((abs(sum(a.values())-t['a'])+abs(sum(p.values())-t['p']),tl,(a,p,t)))
    r.sort(key=lambda x:x[:2]); return r[0][2] if r else (None,None,{})
if __name__=='__main__':
    a,p,t=best(open(sys.argv[1],errors='ignore').read())
    print(json.dumps({'a':a,'p':p,'tot':t},ensure_ascii=False)); print('dA',round(sum(a.values())-t.get('a',0),2),'dP',round(sum(p.values())-(t.get('p') or 0),2))
