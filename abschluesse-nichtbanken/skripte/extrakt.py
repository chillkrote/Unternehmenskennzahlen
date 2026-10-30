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

SEG=re.compile(r"(?P<lab>[A-Za-zÄÖÜäöüß][^\d\n]{2,90}?)\s{2,}(?P<nums>(?:\(?[-–−]?\d[\d.,]*\)?(?:\s{2,}|\s(?=[\(\d–−-])|$)){2,5})")
def zahlen(nums,de):
    out=[]
    for t in re.findall(r"\(?[-–−]?\d[\d.,]*\)?",nums):
        v=zahl(t,de)
        if v is not None:out.append((t,v))
    # Anhangsspalte (kleine Ganzzahl ohne Trennzeichen vor ≥2 größeren Werten) entfernen
    if len(out)>=3 and re.fullmatch(r"\d{1,2}",out[0][0]) and abs(out[1][1])>=100:out=out[1:]
    return [v for _,v in out]

def segmente(seite,de):
    for z in seite.splitlines():
        for m in SEG.finditer(z):
            n=zahlen(m.group('nums'),de)
            if len(n)>=2:yield m.group('lab').strip(),n

def analysiere(txt):
    pages=txt.split('\f')
    de=len(re.findall(r'\b(Umsatzerlöse|Eigenkapital|Konzern|Geschäftsjahr|Verbindlichkeiten)\b',txt))>len(re.findall(r'\b(Revenue|Equity|Liabilities|Financial year)\b',txt))
    for i,p in enumerate(pages):
        ak=[n for lab,n in segmente(p,de) if RX['bilanzsumme'].match(lab) or RX['passiva'].match(lab)]
        gl=[n for n in ak if n[0]!=0 and sum(1 for m in ak if abs(m[0]-n[0])<=max(1,abs(n[0])*1e-4))>=2]
        if not gl:continue
        res={'seite_bilanz':i+1,'de':de,'bilanzsumme':gl[0][:2],'ek':None,'schulden':None}
        for key in('ek','schulden'):
            for lab,n in segmente(p,de):
                if RX[key].match(lab) and abs(n[0])<=abs(gl[0][0])*1.001:res[key]=n[:2];break
        for k,pat in(('umsatz',r'gewinn- und verlustrechnung|gesamtergebnisrechnung|income statement|statement of (comprehensive )?income|profit or loss|gesamtergebnis|konzern-guv'),('cfo',r'kapitalflussrechnung|cash flow statement|statement of cash flows')):
            for j,q in enumerate(pages):
                if not re.search(pat,q[:3000],re.I):continue
                found={}
                for lab,n in segmente(q,de):
                    for kk in(('umsatz','ebit','jue') if k=='umsatz' else('cfo',)):
                        if kk not in found and RX[kk].match(lab):found[kk]=n[:2]
                if found.get(k):
                    for kk,v in found.items():res[kk]=v
                    res['seite_'+('guv' if k=='umsatz' else 'cf')]=j+1;break
        # Einheit: Seitenkopf der Bilanz, sonst vorherige Seite
        res['faktor_text']=einheit(p) if EIN_RX.search(p[:4000]) else (einheit(pages[i-1]) if i and EIN_RX.search(pages[i-1][:4000]) else None)
        return res
    return None

if __name__=='__main__':
    print(json.dumps(analysiere(Path(sys.argv[1]).read_text(errors='ignore')),ensure_ascii=False))
