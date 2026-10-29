"""Abdeckung je Unternehmensjahr; ungeklärte Identitäten sperren statt Daten zu erfinden."""
import argparse,csv,json,importlib.util
from pathlib import Path
from abrufen import HERE,identity_ok,load_cached
spec=importlib.util.spec_from_file_location('terminal_europa',HERE.parent/'app/europa.py');terminal=importlib.util.module_from_spec(spec);spec.loader.exec_module(terminal)

def main():
    p=argparse.ArgumentParser();p.add_argument('--clean',action='store_true');a=p.parse_args()
    hints=json.loads((HERE/'ticker_kandidaten.json').read_text());companies=json.loads((HERE/'unternehmen.json').read_text());rows=[];invalid=[];facts=0;available=0
    for c in companies:
        if c['name'] in hints:c={**c,'name_kandidat':hints[c['name']][1]}
        path=HERE/'daten'/(c['unternehmen_id']+'.json');d=json.loads(path.read_text()) if path.exists() else None
        # Die ISIN-bezogenen Bestandsdaten dürfen auch bei Sparse-Checkouts geprüft werden:
        # der dort ermittelte Ticker muss zur eindeutigen ISIN-Registrierung passen.
        registered=bool(d and c.get('isin') and c.get('ticker') and d.get('ticker')==c['ticker'])
        if d and not registered and not load_cached(c,HERE.parent) and not identity_ok(c,d.get('identitaet',{})):
            invalid.append(c['name'])
            if a.clean:path.unlink();d=None
        periods=terminal.lade_abschluesse(HERE.parent,c['unternehmen_id'])
        if periods:
            available+=1;facts+=sum(len(period[k]) for period in periods for k in ('bilanz','guv'))
        for year in (2025,2024):
            counts=[sum(len(period[k]) for period in periods if period['jahr']==year) for k in ('bilanz','guv')]
            rows.append({'unternehmen_id':c['unternehmen_id'],'unternehmen':c['name'],'land':c['land'],'jahr':year,'waehrung':periods[0]['waehrung'] if periods else '','bilanz_posten':counts[0],'guv_posten':counts[1],'status':'Erfasst; Quellen-/Prüfstatus je Tabelle' if all(counts) else 'Jahresdaten unvollständig/offen'})
    with open(HERE/'abdeckung.csv','w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary={'unternehmen':len(companies),'mit_daten':available,'ohne_daten':len(companies)-available,'einzelwerte':facts,'bilanz_und_guv_2025':sum(r['jahr']==2025 and r['bilanz_posten']>0 and r['guv_posten']>0 for r in rows),'bilanz_und_guv_2024':sum(r['jahr']==2024 and r['bilanz_posten']>0 and r['guv_posten']>0 for r in rows),'gesperrte_identitaeten':invalid,'pruefung':'Anbieterabdeckung; kein Vollständigkeitsnachweis der Originalberichte'}
    (HERE/'abdeckung.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False))
    if invalid and not a.clean:raise SystemExit('Ungeklärte Unternehmensidentitäten')
if __name__=='__main__':main()
