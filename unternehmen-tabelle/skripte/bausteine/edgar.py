import openpyxl,csv,sys,collections
sys.path.insert(0,'/tmp/g')
from gleif import norm
D='/mnt/project-files/unternehmen-merge/'
wb=openpyxl.load_workbook(D+'Unternehmen_aktuell.xlsx'); ws=wb['Unternehmen']
rows=[list(r) for r in ws.iter_rows(min_row=2,values_only=True)]
def br(s):
    if not s: return None
    s=int(s)
    if s in(6021,6022,6029,6035,6036,6111): return 'banken'
    if 6300<=s<=6499: return 'versicherungen'
    if 6500<=s<=6553 or s in(6798,): return 'immobilien'
    if 6000<=s<=6999: return 'finanzdienstleister'
    if 2833<=s<=2836 or 3841<=s<=3851 or 8000<=s<=8099 or s in(8731,5122,5047,3826,3827,3829): return 'pharma-gesundheit'
    if s in(1311,1381,1382,1389,2911,5171,5172,2990,1321,4610,4922,4923,4924): return 'energie'
    if 4900<=s<=4991: return 'energie-versorger'
    if 100<=s<=999 or 1000<=s<=1499 or 2800<=s<=2899 or 2600<=s<=2699 or 3300<=s<=3399 or 3080<=s<=3099 or 3200<=s<=3299: return 'chemie-rohstoffe'
    if s in(3711,3713,3714,3715,3716,3751,3790,5500,5510,5511,5521,5531,5541) : return 'automobil'
    if 7370<=s<=7379: return 'software-it'
    if s in(3570,3571,3572,3575,3576,3577,3578,3579,3661,3663,3669,3670,3672,3674,3675,3677,3678,3679,3690,3695,3559,3810,3812,3820,3823,3825,3826): return 'technologie'
    if 4800<=s<=4899 or 2700<=s<=2799 or 7810<=s<=7841 or s in(7900,7990,7200,7310,7311,7320,7330): return 'telekom-medien' if s not in(7900,7990,7200,7310,7311,7320,7330) else None
    if 4000<=s<=4799: return 'transport-logistik'
    if 5000<=s<=5999 or 2000<=s<=2199 or 2300<=s<=2399 or 3140<=s<=3149 or 3900<=s<=3999 or 7000<=s<=7099 or 5812==s or 7800<=s<=7999: return 'handel-konsum'
    if 1500<=s<=1799 or 3000<=s<=3999 or 2400<=s<=2599 or 2200<=s<=2299: return 'industrie'
    return None
us=collections.defaultdict(list); tk=collections.defaultdict(list); nm=collections.defaultdict(list)
for i,r in enumerate(rows):
    if r[2]=='USA':
        us[(r[0],str(r[5]))].append(i)
        if r[5]: tk[str(r[5]).upper()].append(i)
        nm[norm(str(r[0]))].append(i)
st=collections.Counter(); EX={'Nasdaq':'Nasdaq','NYSE':'New York Stock Exchange Inc.','CBOE':'Cboe'}
seen=set()
for x in csv.DictReader(open('/mnt/project-files/us-ergaenzung/us_edgar_ergaenzung.csv',encoding='utf-8')):
    c=us.get((x['name_tabelle'],x['ticker'])) or (tk.get(x['ticker'].upper()) if len(tk.get(x['ticker'].upper(),[]))==1 else None) or (nm.get(norm(x['name_tabelle'])) if len(nm.get(norm(x['name_tabelle']),[]))==1 else None)
    if not c or len(c)!=1: st['nicht zugeordnet']+=1; continue
    i=c[0]
    if i in seen: continue
    seen.add(i); r=rows[i]; ch=[]
    if not r[11] and x['cik']: r[11]=f"{x['cik']} (SEC CIK)"; ch.append('CIK')
    if not r[6] and x['boerse_edgar'] in EX: r[6]=EX[x['boerse_edgar']]; ch.append('Börse')
    b=br(x['sic'])
    if b and (not r[8] or r[8]=='sonstige'):
        r[8]=b; ch.append('Branche aus SIC'); 
    elif b and r[8]!=b: st['Branche abweichend (belassen)']+=1
    if ch:
        t=f"EDGAR (SIC {x['sic']} {x['sic_beschreibung']}): "+', '.join(ch)+' ergänzt'
        r[15]=(r[15]+' | ' if r[15] else '')+t+(' - Branche bitte prüfen' if 'Branche aus SIC' in ch else '')
        for k in ch: st[k]+=1
        st['Zeilen ergänzt']+=1
    else: st['nichts zu ergänzen']+=1
ws.delete_rows(2,ws.max_row)
for r in rows: ws.append(r)
wb.save(D+'Importvorlage_Unternehmen_befuellt_EDGAR.xlsx'); print(dict(st))
