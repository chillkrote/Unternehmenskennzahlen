import json
R=json.load(open("ref.json")); N=json.load(open("nacherhebung.json"))
bad=0;ok=0
for b,d in N.items():
    zr=R["zr"].get(b,{})
    for y,dd in d["jahre"].items():
        for k,v in dd.items():
            r=(zr.get(y) or {}).get(k)
            if r is None: continue
            if abs(v["wert"]-r)>0.01*max(abs(r),1e-9) and abs(v["wert"]-r)>0.2:
                bad+=1; print(f"ABW {b[:35]:35} {y} {k:6} neu {v['wert']} alt {r} | {v['dokument'][:40]} {v['quelle'][-50:]}")
            else: ok+=1
print("ok",ok,"abw",bad)
