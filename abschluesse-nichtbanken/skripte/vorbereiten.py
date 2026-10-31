"""Auswahl: Nicht-Banken ohne Abschlussposten im Terminal, mit Geschäftsbericht 2025 im Repo; Text per pdftotext.
Aufruf: python3 vorbereiten.py <Arbeitsordner>   (schreibt <Arbeitsordner>/sel.json und txt/<ID>.txt)"""
import csv,glob,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];W=Path(sys.argv[1]);(W/'txt').mkdir(parents=True,exist_ok=True)
nb={f['id']:f for f in json.load(open(ROOT/'app/data/unternehmen.json'))['unternehmen'] if not f.get('abschluesse') and f.get('branche')!='banken'}
sel=[]
for p in glob.glob(str(ROOT/'boersennotierte-unternehmen/*/dokumente/index.csv')):
    for r in csv.DictReader(open(p,encoding='utf-8-sig'),delimiter=';'):
        if r['dokumentart']=='Geschäftsbericht' and r['unternehmen_id'] in nb and r['geschaeftsjahr']=='2025':
            f=os.path.join(os.path.dirname(p),r['datei'].replace('dokumente/','',1))
            sel.append([r['unternehmen_id'],nb[r['unternehmen_id']]['name'],nb[r['unternehmen_id']]['branche'],f,r['quelle_url'],int(r['seiten'] or 0)])
            out=W/'txt'/f"{r['unternehmen_id']}.txt"
            if not out.exists():subprocess.run(['pdftotext','-layout',f,str(out)],timeout=180,stderr=subprocess.DEVNULL)
json.dump(sel,open(W/'sel.json','w'),ensure_ascii=False);print(len(sel),'Berichte')
