import json, os, re, sys, openpyxl
from pja import parse as pja
wb = openpyxl.load_workbook("/mnt/project-files/bilanzvergleich/Bilanzvergleich_Banken_GJ2025.xlsx", data_only=True)
BS = {}
for r in wb["Übersicht"].iter_rows(min_row=2, values_only=True):
    if r[3] and isinstance(r[6], (int, float)): BS[r[3]] = r[6]
json.dump(BS, open("bs2025.json", "w"), ensure_ascii=False)
out = []
for f in sys.argv[1:]:
    for r in json.load(open(f)):
        t = "txt/" + os.path.basename(r["file"])[:-4] + ".txt"
        if not os.path.exists(t): continue
        tx = open(t, errors="replace").read()
        if "ffenleg" in r["fn"] and "Summe der Aktiva" not in tx: continue
        hint = BS.get(r["bank"])
        p = pja(tx, hint)
        if p and "fehler" in p:
            p2 = pja(tx, None); p = dict(p2 or {}, fehler_hint=p["fehler"]) if p2 else p
        if p and p.get("bilanzsumme"):
            out.append(dict(r, ja=p))
            print(f"{r['bank'][:34]:34} {r['fn'][:38]:38} BS {p.get('bilanzsumme')} VJ {p.get('vj_bilanzsumme')} F {p.get('fonds')}/{p.get('vj_fonds')} EK {p.get('eigenkapital')}/{p.get('vj_eigenkapital_summe_unterposten')} JÜ {p.get('ju')}/{p.get('vj_ju')} BG {p.get('bilgew')} {'HINT-FEHLER' if p.get('fehler_hint') else ''}")
json.dump(out, open("crawl/ja_parsed.json", "w"), ensure_ascii=False, indent=1)
