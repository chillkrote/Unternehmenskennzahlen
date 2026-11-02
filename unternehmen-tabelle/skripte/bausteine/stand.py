import openpyxl,collections,sys,csv
sys.path.insert(0,'/tmp/g')
from gleif import norm
D='/mnt/project-files/unternehmen-merge/'
ws=openpyxl.load_workbook(D+'Unternehmen_aktuell.xlsx',read_only=True)['Unternehmen']
it=ws.iter_rows(values_only=True); H=[h.replace(' *','') for h in next(it)]
R=[r for r in it if r[0]]
N=len(R); F=[h for h in H]
miss=lambda v: v is None or str(v).strip()==''
by=collections.defaultdict(list)
for r in R: by[r[2] or '(leer)'].append(r)
FL=['Rechtsform','Sitz','ISIN','Ticker','Börse','Branche','WZ/NACE-Code','LEI','Handelsregisternummer','Website','Beschreibung']
ix={h:H.index(h) for h in H}
def m(rows,f):
    j=ix[f]
    if f=='Branche': return sum(1 for r in rows if miss(r[j]) or r[j]=='sonstige')
    return sum(1 for r in rows if miss(r[j]))
L=[]
L.append('# Zwischenstand Unternehmensliste\n')
L.append(f'Quelle: Unternehmen_aktuell.xlsx, Blatt "Unternehmen" (Stand 02.11.2026). **{N:,} Unternehmen** in {len(by)} Ländern.\n'.replace(',','.'))
L.append('## Fehlende Angaben gesamt\n\n| Feld | fehlt | Anteil |\n|---|---:|---:|')
for f in FL:
    k=m(R,f); L.append(f'| {f}{" (inkl. Platzhalter sonstige)" if f=="Branche" else ""} | {k:,} | {100*k/N:.0f} % |'.replace(',','.'))
k=sum(1 for r in R if miss(r[ix['Quelle Stammdaten (URL)']])); L.append(f'| Quelle Stammdaten (Pflicht) | {k} | {100*k/N:.0f} % |')
nb=sum(1 for r in R if r[ix['Börsennotiert']]=='ja'); L.append(f'\nBörsennotiert = ja: {nb:,} ({100*nb/N:.0f} %); Bank = ja: {sum(1 for r in R if r[ix["Bank"]]=="ja"):,}.\n'.replace(',','.'))
L.append('## Je Land (Anzahl, Anteil fehlend in %)\n\n| Land | Anzahl | ISIN | LEI | Sitz | Rechtsform | Ticker | Börse | Branche (inkl. sonstige) | Website |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
csvrows=[]
for land,rows in sorted(by.items(),key=lambda x:-len(x[1])):
    n=len(rows); p=lambda f: f'{100*m(rows,f)/n:.0f}'
    L.append(f'| {land} | {n:,} | {p("ISIN")} | {p("LEI")} | {p("Sitz")} | {p("Rechtsform")} | {p("Ticker")} | {p("Börse")} | {p("Branche")} | {p("Website")} |'.replace(',','.'))
    csvrows.append([land,n]+[m(rows,f) for f in FL])
w=csv.writer(open(D+'zwischenstand/fehlend_je_land.csv','w',newline='',encoding='utf-8-sig'),delimiter=';'); w.writerow(['Land','Anzahl']+['fehlt '+f for f in FL]); w.writerows(csvrows)
# checks
isin=collections.defaultdict(list); lei=collections.defaultdict(list); nm=collections.defaultdict(list)
for i,r in enumerate(R):
    if r[ix['ISIN']]: isin[r[ix['ISIN']]].append(r[0])
    if r[ix['LEI']]: lei[r[ix['LEI']]].append(r[0])
    nm[(r[2],norm(str(r[0])))].append(r[0])
di={k:v for k,v in isin.items() if len(v)>1}; dl={k:v for k,v in lei.items() if len(v)>1}; dn={k:v for k,v in nm.items() if len(v)>1 and k[1]}
desc=[str(r[ix['Beschreibung']] or '') for r in R]
pr=sum(1 for d in desc if 'Platzhalter' in d); bp=sum(1 for d in desc if 'bitte prüfen' in d)
sons=sum(1 for r in R if r[2]=='Sonstige'); lon=sum(1 for r in R if not r[2] or r[2]=='(leer)')
L.append('\n## Prüfpunkte\n')
L.append(f'- **Doppelte ISIN:** {len(di)} ISIN stehen bei mehreren Zeilen (z. B. Aktiengattungen/Doppelzeilen)\n- **Doppelte LEI:** {len(dl)} LEI bei mehreren Zeilen (Gattungen oder Dubletten)\n- **Gleicher Name im selben Land:** {len(dn)} Namen kommen mehrfach vor\n- **Platzhalter** (Branche/Bank automatisch gesetzt, in der Beschreibung vermerkt): {pr:} Zeilen\n- **"bitte prüfen" in der Beschreibung** (automatisch ergänzte Werte): {bp} Zeilen\n- **Land "Sonstige":** {sons} Zeilen, Land leer: {lon}\n- **Restfehler importieren.py:** 2 aus der Basis (AENA.MC/ANA.MC, CAE Inc./CA, Inc.) und 4 französische Registerdubletten im Repo (LVMH, Capgemini, Schneider Electric, TotalEnergies)\n- Basis enthält Fremdzeilen wie "Company name", "Decimal Places", ETF-Kürzel (VAS, WOW, XRO) als Firmennamen: gesondert bereinigen')
L.append('''
## Eingearbeitete Listen (Reihenfolge)

Basis Unternehmen-Tabelle 1 plus 10 Länderlisten; Ergänzung per GLEIF/Wikidata; USA (SEC, 13F-ISINs, EDGAR-Ergänzung vom Massive-Thread: CIK, Börse, SIC-Branche); China (SSE, SZSE); Jordan; iShares-Listen; Hongkong (HKEX); Südkorea (KRX); Indien (NSE); Australien (ASX); Taiwan (TWSE/TPEx OpenAPI).

## Noch nicht eingearbeitet

- US-ISIN-Datei des Massive-Threads (bisher nur Zwischenstand mit 150 Zeilen, 25 sichere ISIN)
- Japan (JPX), Indien BSE: Datei von Robin nötig; Saudi-Arabien, VAE, Baltikum nicht abgerufen
- GLEIF-Namenssuche für Australien und Taiwan (läuft)
- Branche bei den neuen Börsenzeilen (Indien, Australien, Taiwan, Südkorea, China) nur Platzhalter; WZ/NACE-Code nirgends befüllt

## Hinweis zur Lesart

Alle Zeilen stehen als börsennotiert=ja, auch ETF-Kürzel und Fremdzeilen der Basis. Die Zahl der Länder-Zeilen enthält Aktiengattungen als eigene Zeilen.
''')
open(D+'zwischenstand/Zwischenstand_Unternehmensliste.md','w').write('\n'.join(L)+'\n')
print('\n'.join(L[:20])); print(L[-3:])
# sample dup names
print(list(dn.items())[:5])
