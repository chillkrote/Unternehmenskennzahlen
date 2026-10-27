import sys,re
# pas.py txt : druckt aus der Bilanz/CC2-Seite die Zeilen ab "Fonds f. allg." bzw. "Eigenkapital" bis Summe Passiva, plus Kopfzeile mit Jahreszahlen
P=open(sys.argv[1],errors='replace').read().split("\f")
mx=int(sys.argv[2]) if len(sys.argv)>2 else 2
n=0
for i,p in enumerate(P):
    L=p.splitlines()
    end=[k for k,l in enumerate(L) if re.search(r"Summe der Passiva|Summe Passiva|Passiva insgesamt|Summe der Passivposten|Gesamtsumme Passiva|Summe der Verbindlichkeiten und",l,re.I)]
    if not end: continue
    e=end[0]
    st=next((k for k in range(e,-1,-1) if re.search(r"Fonds f.r allgemeine|Eigenkapital",L[k])),max(0,e-15))
    st=max(0,min(st,e-14))
    hdr=[l for l in L[:15] if re.search(r"20[12]\d",l)][:3]
    print(f"=== S.{i+1}"); 
    for l in hdr+["..."]+L[st:e+1]:
        if l.strip(): print(re.sub(r" {3,}","   ",l.rstrip())[:200])
    n+=1
    if n>=mx: break
