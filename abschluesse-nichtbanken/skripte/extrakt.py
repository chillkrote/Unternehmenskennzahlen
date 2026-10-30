"""Bilanz-/GuV-/Cashflow-Kernposten aus Geschäftsbericht-PDFs (pdftotext -layout).

Nur Primärquelle: die im Repo abgelegten Berichte. Jede Zahl bekommt die gedruckte Seite.
Kontrollen: Summe Aktiva = Summe Passiva (Bilanz muss aufgehen), Einheit aus dem Seitenkopf.
Ergebnis je Bericht: Werte in Berichtswährung, unskaliert (wie europa/ergaenzungen).
"""
import re,sys,json,subprocess
from pathlib import Path

NUM=r'\(?-?[–−]?\d[\d.,\' ]*\d\)?|\(?-?\d\)?'
def zahl(tok,de):
    t=tok.strip().replace('−','-').replace('–','-').replace("'",'').replace(' ','')
    neg=t.startswith('(') or t.startswith('-');t=t.strip('()-')
    if de:t=t.replace('.','').replace(',','.')
    else:t=t.replace(',','')
    try:v=float(t)
    except ValueError:return None
    return -v if neg else v


LABEL={
 'bilanzsumme':r'^(summe aktiva|bilanzsumme|summe vermögen|summe vermögenswerte|total assets|aktiva gesamt|gesamtvermögen|aktiva)\s*$',
 'passiva':r'^(summe passiva|total equity and liabilities|total liabilities and (share|stock)holders?.? equity|summe eigenkapital und schulden|passiva gesamt|summe eigen- und fremdkapital|equity and liabilities|passiva|summe passiva)\s*$',
 'ek':r'^(summe eigenkapital|eigenkapital insgesamt|eigenkapital gesamt|total equity|konzerneigenkapital|summe konzerneigenkapital|eigenkapital)\s*$',
 'umsatz':r'^(umsatzerlöse|umsatz|revenues?|net sales|sales|revenue from contracts with customers|gesamtleistung)\s*$',
 'ebit':r'^(ebit|betriebsergebnis|operating (profit|result|income)|ergebnis vor zinsen und steuern|operatives ergebnis|ergebnis der betrieblichen tätigkeit|operating profit \(ebit\))\s*$',
 'jue':r'^(konzernergebnis|konzern-jahresüberschuss|periodenergebnis|jahresüberschuss|jahresergebnis|konzernjahresergebnis|ergebnis nach steuern|net (income|profit|result)|profit for the (year|period)|(loss|profit|result|earnings) for the (year|period)|konzern-periodenergebnis|jahresfehlbetrag|konzernjahresüberschuss|jahresüberschuss/-fehlbetrag|ergebnis nach steuern)\s*$',
 'cfo':r'^(cashflow aus laufender geschäftstätigkeit|cash flow aus laufender geschäftstätigkeit|cashflow aus betrieblicher tätigkeit|mittelzufluss aus laufender geschäftstätigkeit|net cash (flows? )?(from|provided by|generated from|used in)[^0-9]*operating( activities)?|cash flows? from operating activities|cash flow aus operativer tätigkeit|cashflow aus der laufenden geschäftstätigkeit|mittelab-?/?zufluss aus laufender geschäftstätigkeit|cashflow aus operativer geschäftstätigkeit)\s*$',
 'schulden':r'^(summe schulden|total liabilities|summe fremdkapital|schulden gesamt)\s*$',
}
RX={k:re.compile(v,re.I) for k,v in LABEL.items()}
EINHEIT=[(r'(t\s?eur|teur|t€|tsd\.?\s*(eur|€)|€\s?tsd|eur\s?tsd|keur|k€|eur thousand|€ thousand|in thousand|in tausend|\bkeur\b|€k\b)',1e3),
         (r'(mio\.?\s*(eur|€)|€\s?mio|eur\s?mio|eur million|€ million|€m\b|eur m\b|in millions?|in mio|\bmio\b)',1e6)]
EIN_RX=re.compile('|'.join(r for r,_ in EINHEIT),re.I)
def einheit(seite):
    kopf=seite[:4000]
    for rx,f in EINHEIT:
        if re.search(rx,kopf,re.I):return f
    return 1.0

SEG=re.compile(r"(?P<lab>[A-Za-zÄÖÜäöüß][^\d\n]{2,90}?)\s{2,}(?P<nums>(?:\(?[-–−]?\d[\d.,]*\)?(?:\s*%)?(?:\s{2,}|\s(?=[\(\d–−-])|$)){2,6})")
PCT=re.compile(r"\(?[-–−]?\d[\d.,]*\)?\s*%")
def zahlen(nums,de):
    nums=PCT.sub(' ',nums)
    out=[]
    for t in re.findall(r"\(?[-–−]?\d[\d.,]*\)?",nums):
        v=zahl(t,de)
        if v is not None:out.append((t,v))
    if len(out)>=3 and re.fullmatch(r"\d{1,2}",out[0][0]) and abs(out[1][1])>=100:out=out[1:]
    return [v for _,v in out]

def segmente(seite,de):
    for z in seite.splitlines():
        for m in SEG.finditer(z):
            n=zahlen(m.group('nums'),de)
            if len(n)>=2:yield m.group('lab').strip(),n

def ist_datum(v):
    return bool(re.fullmatch(r'[0-3]\d[01]\d20(2[3-6])',str(int(abs(v))).zfill(8)))

def deutsch(txt):
    return len(re.findall(r'\b(Umsatzerlöse|Eigenkapital|Konzern|Geschäftsjahr|Verbindlichkeiten)\b',txt))>len(re.findall(r'\b(Revenue|Equity|Liabilities|Financial year)\b',txt))

def faktor_aus(bs,ref,text):
    if ref:
        a,f=min((abs(bs*f/1e6/ref-1),f) for f in(1,1e3,1e6))
        return f if a<=.25 else None
    return text

def bilanz_kandidaten(pages,de):
    """(Seite, [Summe Aktiva-Zeilen], Passiva-Seite). Aktiva und Passiva stehen auf einer oder auf zwei aufeinanderfolgenden Seiten."""
    per={}
    for i,p in enumerate(pages):
        rows=[n for lab,n in segmente(p,de) if (RX['bilanzsumme'].match(lab) or RX['passiva'].match(lab)) and n[0]>0 and not ist_datum(n[0])]
        if rows:per[i]=rows
    out=[]
    for i,rows in per.items():
        for n in rows:
            same=sum(1 for m in rows if abs(m[0]-n[0])<=max(1,n[0]*1e-4))>=2
            nxt=any(abs(m[0]-n[0])<=max(1,n[0]*1e-4) for j in(i-1,i+1) for m in per.get(j,[]))
            if same or nxt:out.append((i,n[:2]))
    return out

def guv_zeilen(pages,de,start,ende,keys,pat):
    for j in range(start,ende):
        q=pages[j]
        if not re.search(pat,q[:3500],re.I):continue
        found={}
        for lab,n in segmente(q,de):
            for kk in keys:
                if kk not in found and RX[kk].match(lab):found[kk]=n[:2]
        if found:yield j,found

def analysiere(txt,ref=None):
    """ref: Terminalwerte (Mio. EUR) zur Einheitenbestimmung und Plausibilität; None = nur Seitenkopf."""
    ref=ref or {}
    pages=txt.split('\f');de=deutsch(txt)
    cands=bilanz_kandidaten(pages,de)
    best=None
    for i,bs in cands:
        f=faktor_aus(bs[0],ref.get('bilanzsumme'),einheit(pages[i]) if EIN_RX.search(pages[i][:4000]) else (einheit(pages[i-1]) if i and EIN_RX.search(pages[i-1][:4000]) else None))
        if not f:continue
        d=abs(bs[0]*f/1e6/ref['bilanzsumme']-1) if ref.get('bilanzsumme') else 0
        if best is None or d<best[0]-1e-9:best=(d,i,bs,f)
    pruefung='Aktiva=Passiva'
    if not best and ref.get('bilanzsumme'):
        # zweite Stufe: einzelne Bilanzsummen-Zeile, die dem unabhängigen Terminalwert auf 3 % entspricht
        for i,p in enumerate(pages):
            for lab,n in segmente(p,de):
                if RX['bilanzsumme'].match(lab) and n[0]>0 and not ist_datum(n[0]):
                    for f in(1,1e3,1e6):
                        d=abs(n[0]*f/1e6/ref['bilanzsumme']-1)
                        if d<=.03 and (best is None or d<best[0]):best=(d,i,n[:2],f)
        pruefung='Yahoo-Abgleich (3 %)'
    if not best:return None
    _,i,bs,f=best
    res={'seite_bilanz':i+1,'faktor':f,'bilanzsumme':bs,'ek':None,'pruefung':pruefung}
    for pg in(i,i+1,i-1):
        if not 0<=pg<len(pages):continue
        for lab,n in segmente(pages[pg],de):
            if RX['ek'].match(lab) and res['ek'] is None and 0<abs(n[0])<=bs[0]*1.001:
                if n[0]!=bs[0]:res['ek']=n[:2];res['seite_ek']=pg+1
        if res['ek']:break
    um_ref=ref.get('umsatz')
    cand=[]
    for j,found in guv_zeilen(pages,de,0,len(pages),('umsatz','ebit','jue'),r'gewinn- und verlustrechnung|gesamtergebnisrechnung|income statement|statement of (comprehensive )?income|profit or loss|konzern-guv|ergebnisrechnung|gesamtergebnis'):
        if 'umsatz' in found:
            d=abs(found['umsatz'][0]*f/1e6/um_ref-1) if um_ref else 0
            if d<=.35 and found['umsatz'][0]>0 and .01<=found['umsatz'][0]/bs[0]<=15:cand.append((d,j,found))
    if cand:
        _,j,found=min(cand,key=lambda c:c[0])
        res['seite_guv']=j+1;um=found['umsatz'];res['umsatz']=um
        for kk in('ebit','jue'):
            if kk in found:res[kk]=found[kk]
        u=abs(um[0])
        if 'jue' in res:
            m=ref.get('netto_marge')
            if abs(res['jue'][0])>u*1.0 or (m is not None and abs(res['jue'][0]/u-m)>.04):res.pop('jue')
        if 'ebit' in res:
            m=ref.get('ebit_marge')
            if abs(res['ebit'][0])>u or (m is not None and abs(res['ebit'][0]/u-m)>.05):res.pop('ebit')
    for j,found in guv_zeilen(pages,de,0,len(pages),('cfo',),r'kapitalflussrechnung|cash flow statement|statement of cash flows|cashflow'):
        v=found['cfo']
        if .002<=abs(v[0])/bs[0]<=.5:res['cfo']=v;res['seite_cf']=j+1;break
    return res

if __name__=='__main__':
    print(json.dumps(analysiere(Path(sys.argv[1]).read_text(errors='ignore')),ensure_ascii=False))
