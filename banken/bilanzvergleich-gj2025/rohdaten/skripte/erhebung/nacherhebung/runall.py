import json, sys, os, re
sys.argv=[sys.argv[0]]+sys.argv[1:]
from pcc2 import parse, year_of
dl = json.load(open(sys.argv[1]))
res = []
for r in dl:
    t = open("txt/" + os.path.basename(r["file"])[:-4] + ".txt", errors="replace").read() if os.path.exists("txt/" + os.path.basename(r["file"])[:-4] + ".txt") else ""
    y = year_of(t); p = parse(t) if t else None
    r2 = dict(r, year=y, cc2=p, chars=len(t))
    res.append(r2)
json.dump(res, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
ok = [x for x in res if x["cc2"] and x["cc2"]["bilanzsumme"]]
for x in res:
    c = x["cc2"]
    if c: print(f"{x['bank'][:38]:38} {x['year']} {x['fn'][:40]:40} BS {c['bilanzsumme']} EK {c['eigenkapital']} F {c['fonds']} BG {c['bilanzgewinn']} chk {c['chk_a']}/{c['chk_p']}")
print(len(ok), "mit CC2 von", len(res))
