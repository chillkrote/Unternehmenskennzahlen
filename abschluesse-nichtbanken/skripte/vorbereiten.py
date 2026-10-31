"""Auswahl: Nicht-Banken ohne Abschlussposten im Terminal, mit Geschäftsbericht 2025 im Repo; Text per pdftotext.
Aufruf: python3 vorbereiten.py <Arbeitsordner>   (schreibt <Arbeitsordner>/sel.json und txt/<ID>.txt)"""
import csv,glob,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];W=Path(sys.argv[1]);(W/'txt').mkdir(parents=True,exist_ok=True)
TERM=json.load(open(ROOT/'app/data/unternehmen.json'))['unternehmen']
nb={f['id']:f for f in TERM if (not f.get('abschluesse') or (ROOT/f'abschluesse-nichtbanken/daten/{f["id"]}.json').exists()) and f.get('branche')!='banken'}
ART=['Geschäftsbericht','Jahresfinanzbericht','Konzernabschluss','Jahresabschluss','Bericht']  # Reihenfolge = Vorrang
sel=[]
for p in glob.glob(str(ROOT/'boersennotierte-unternehmen/*/dokumente/index.csv')):
    for r in csv.DictReader(open(p,encoding='utf-8-sig'),delimiter=';'):
        if r['dokumentart'] in ART and r['unternehmen_id'] in nb and r['geschaeftsjahr']=='2025':
            f=os.path.join(os.path.dirname(p),r['datei'].replace('dokumente/','',1))
            sel.append([r['unternehmen_id'],nb[r['unternehmen_id']]['name'],nb[r['unternehmen_id']]['branche'],f,r['quelle_url'],int(r['seiten'] or 0),r['dokumentart']])
sel.sort(key=lambda x:ART.index(x[6]))
erste={}
for x in sel:erste.setdefault(x[0],x)
sel=[x[:6] for x in erste.values()]
for x in sel:
    out=W/'txt'/f'{x[0]}.txt';out.unlink(missing_ok=True)
    subprocess.run(['pdftotext','-layout',str(x[3]),str(out)],timeout=180,stderr=subprocess.DEVNULL)
json.dump(sel,open(W/'sel.json','w'),ensure_ascii=False);print(len(sel),'Berichte')
