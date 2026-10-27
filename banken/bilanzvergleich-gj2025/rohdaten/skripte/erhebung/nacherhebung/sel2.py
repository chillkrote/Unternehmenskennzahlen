import json,re,urllib.parse,sys
D={}
for f in ['domains.json','domains2.json','domains3.json']: D.update(json.load(open(f)))
R={v:k for k,v in D.items()}
cr=json.load(open(sys.argv[1]))
old=set()
for f in ['crawl/spk_dl.json','crawl/geno_dl.json','crawl/priv_dl.json']:
    old|={r['url'] for r in json.load(open(f))}
KW=re.compile(r"offenleg|gesch(ae|ä|%C3%A4)ftsbericht|jahresabschluss|jahresbericht|lagebericht|bilanz",re.I)
sel={}
for dom,r in cr.items():
    for u in r['pdfs']:
        fn=urllib.parse.unquote(u.split('?')[0]).split('/')[-1]
        if u in old or not KW.search(urllib.parse.unquote(u)): continue
        if re.search(r"tagesbilanz|nachhaltig|csr|esg|klima|halbj|offenlegung-?nach|institutsverg|verguetung|vergütung",fn,re.I): continue
        ys=[int(y) for y in re.findall(r"20[12]\d",urllib.parse.unquote(u))]
        if ys and not any(2021<=y<=2026 for y in ys): continue
        sel.setdefault(R[dom],[]).append(u)
json.dump(sel,open(sys.argv[2],'w'),ensure_ascii=False,indent=1)
print(len(sel),sum(map(len,sel.values())))
