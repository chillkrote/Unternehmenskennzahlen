import json,re,openpyxl,collections
D='/mnt/project-files/unternehmen-merge/'
o=json.load(open('/tmp/g/us.json'))
def lei_ok(l): return bool(re.fullmatch(r'[A-Z0-9]{18}[0-9]{2}',l)) and int(''.join(str(int(ch,36)) for ch in l))%97==1
def isin_ok(i):
    if not re.fullmatch(r'[A-Z]{2}[A-Z0-9]{9}[0-9]',i): return False
    d=''.join(str(int(ch,36)) for ch in i);t=0
    for n,ch in enumerate(reversed(d)):
        x=int(ch)
        if n%2==1: x*=2;x=x//10+x%10
        t+=x
    return t%10==0
def branche(sic):
    try: s=int(sic)
    except: return None
    if s in(6021,6022,6029,6035,6036): return 'banken'
    if 6300<=s<=6411: return 'versicherungen'
    if s==6798 or 6500<=s<=6553: return 'immobilien'
    if 6100<=s<=6299: return 'finanzdienstleister'
    if s==6770: return None
    if 2834<=s<=2836 or 3841<=s<=3851 or 8000<=s<=8099 or s==5122: return 'pharma-gesundheit'
    if 2800<=s<=2899 or 1000<=s<=1099 or 1400<=s<=1499 or 3300<=s<=3399: return 'chemie-rohstoffe'
    if 1300<=s<=1389 or 2900<=s<=2999 or s==5171: return 'energie'
    if 4900<=s<=4999: return 'energie-versorger'
    if 7370<=s<=7379 or s==7389: return 'software-it'
    if 4800<=s<=4899 or 2700<=s<=2799 or 7810<=s<=7841: return 'telekom-medien'
    if 3570<=s<=3579 or 3660<=s<=3679 or 3820<=s<=3829 or 3690<=s<=3699: return 'technologie'
    if 3710<=s<=3719 or 5500<=s<=5599: return 'automobil'
    if 4000<=s<=4799: return 'transport-logistik'
    if 5200<=s<=5999 or 2000<=s<=2199 or 2300<=s<=2399 or 3140<=s<=3149: return 'handel-konsum'
    if 1500<=s<=1799 or 3400<=s<=3569 or 3580<=s<=3659 or 3700<=s<=3799: return 'industrie'
    return None
wb=openpyxl.load_workbook(D+'Importvorlage_Unternehmen_befuellt_zusammengelegt.xlsx');ws=wb['Unternehmen']
used=collections.Counter(ws.cell(r,5).value for r in range(2,ws.max_row+1) if ws.cell(r,5).value)
usedl=collections.Counter(ws.cell(r,11).value for r in range(2,ws.max_row+1) if ws.cell(r,11).value)
st=collections.Counter()
for k,v in o.items():
    r=int(k)
    assert ws.cell(r,3).value=='USA'
    fil=[]
    def put(c,val,lab):
        if val and not ws.cell(r,c).value: ws.cell(r,c).value=val;fil.append(lab);st[lab]+=1
    if v.get('city'): put(4,v['city'].title()+(', '+v['st'] if v.get('st') else ''),'Sitz')
    b=branche(v.get('sic'))
    if b and ws.cell(r,9).value=='sonstige': ws.cell(r,9).value=b;fil.append('Branche');st['Branche']+=1
    if b=='banken' and ws.cell(r,14).value=='nein': ws.cell(r,14).value='ja';fil.append('Bank');st['Bank']+=1
    g=v.get('gl') or []
    if len(g)==1 and lei_ok(g[0]['lei']) and usedl[g[0]['lei']]==0 and not ws.cell(r,11).value:
        x=g[0];put(11,x['lei'],'LEI');usedl[x['lei']]+=1
        put(2,x['form'],'Rechtsform')
        isins=[i for i in v.get('isins',[]) if isin_ok(i)]
        if len(isins)==1 and used[isins[0]]==0 and not ws.cell(r,5).value:
            ws.cell(r,5).value=isins[0];used[isins[0]]+=1;fil.append('ISIN');st['ISIN']+=1
    if fil:
        old=ws.cell(r,16).value
        ws.cell(r,16).value=(old+' | ' if old else '')+f"SEC (CIK {int(v['cik'])}, SIC {v.get('sic')} {v.get('sicd')}) / GLEIF: "+', '.join(fil)
        st['Zeilen']+=1
wb.save(D+'Importvorlage_Unternehmen_befuellt_USA-ergaenzt.xlsx')
print(dict(st))
