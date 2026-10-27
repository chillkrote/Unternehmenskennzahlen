import openpyxl,json,sys
from collections import Counter
wb=openpyxl.load_workbook("/mnt/project-files/bilanzvergleich/Bilanzvergleich_Banken_GJ2025.xlsx",data_only=True)
def rows(name,bankcol):
    ws=wb[name]; hdr=[c.value for c in ws[1]]
    return {r[bankcol]:dict(zip(hdr,r)) for r in ws.iter_rows(min_row=2,values_only=True) if r[bankcol] and r[1] in("Top 40","Landesbank","Zusatz","EBA-Hub")}
U=rows("Übersicht",3); Z=rows("Zeitreihe 2021-2025",3); O=rows("Offenlegung 31.12.2025",2); C=rows("Eigenmittel CC1",2); V=rows("RWA-Aufteilung OV1",2); B=rows("Bilanzen 31.12.2025",2)
nv=lambda v: v in (None,"","n. v.")
gaps=[]
for n,u in U.items():
    g=[]
    for k,c in (("Sitz","Sitz"),("BS","Bilanzsumme (Mio. €)"),("EK","Eigenkapital (Mio. €)"),("Fonds","Fonds § 340g (Mio. €)"),("VJ","VJ Bilanzsumme (Mio. €)"),("VJEK","VJ Eigenkapital (Mio. €)"),("VJF","VJ Fonds § 340g (Mio. €)"),("KK","Bilanzgewinn (Mio. €)"),("CET1N","CET1-Näherung (Mio. €)")):
        if nv(u[c]): g.append(k)
    z=Z.get(n,{})
    if nv(z.get("Jahresüberschuss 2025 (Mio. €)")): g.append("JÜ")
    if nv(z.get("Jahresüberschuss 2024 (Mio. €)")): g.append("JÜ24")
    for y in (2021,2022,2023):
        if nv(z.get(f"Bilanzsumme {y} (Mio. €)")): g.append(f"BS{y}")
    if nv(O.get(n,{}).get("Hartes Kernkapital CET1 (Mio. €)")): g.append("KM1")
    if nv(C.get(n,{}).get("Hartes Kernkapital CET1 (Mio. €)")): g.append("CC1")
    if nv(V.get(n,{}).get("RWA gesamt (Mio. €)")): g.append("OV1")
    if nv(B.get(n,{}).get("Summe der Aktiva")): g.append("BIL")
    gaps.append((u["Gruppe"],u["Rolle"],n,g))
print(len(gaps), sorted(Counter(x for *_,g in gaps for x in g).items()))
json.dump(gaps,open(sys.argv[1] if len(sys.argv)>1 else "gaps_now.json","w"),ensure_ascii=False)
