import json,sys,os
# rec.py '<json>'  keys: bank, gj, bs, ek, fonds, f340e, vj_bs, vj_ek, vj_fonds, ju, vj_ju, bilgew, url, doc, typ, note  (Mio. €)
E=json.load(open("erg.json")) if os.path.exists("erg.json") else {}
d=json.loads(sys.argv[1]); E[d["bank"]]=d
json.dump(E,open("erg.json","w"),ensure_ascii=False,indent=1); print(len(E),"Einträge")
