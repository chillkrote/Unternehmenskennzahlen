import json,re,urllib.parse,subprocess,os,hashlib,sys,concurrent.futures as cf
sel=json.load(open(sys.argv[1])); out_json=sys.argv[2]
jobs=[]
for bank,L in sel.items():
    for u in L:
        if u.startswith("//"): u="https:"+u
        fn=urllib.parse.unquote(u.split("?")[0]).split("/")[-1]
        ys=[int(y) for y in re.findall(r"20[12]\d",fn)]
        if ys and max(ys)<2021: continue
        if re.search(r"teiloffenleg|halbjahres|Halbjahr|1HJ|IFRS|financial|30062|30092|31032|art450|csr|Image_|OffenlegungsVO",fn,re.I): continue
        if re.search(r"offenlegungsbericht-20(1|20)\b",fn): continue
        jobs.append((bank,u,fn))
print(len(jobs))
os.makedirs("pdf",exist_ok=True); os.makedirs("txt",exist_ok=True)
def dl(j):
    bank,u,fn=j
    h=hashlib.md5(u.encode()).hexdigest()[:8]
    out=f"pdf/{h}.pdf"
    if not os.path.exists(out):
        subprocess.run(["curl","-sSL","--max-time","120","-A","Mozilla/5.0",urllib.parse.quote(u,safe=":/?=&%"),"-o",out])
    t=f"txt/{h}.txt"
    if not os.path.exists(t): subprocess.run(["pdftotext","-layout",out,t],capture_output=True)
    return {"bank":bank,"url":u,"fn":fn,"file":out}
with cf.ThreadPoolExecutor(8) as ex: res=list(ex.map(dl,jobs))
json.dump(res,open(out_json,"w"),ensure_ascii=False,indent=1)
