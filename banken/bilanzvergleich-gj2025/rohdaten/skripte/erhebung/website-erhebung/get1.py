import sys, json, hashlib, subprocess, os
# usage: get1.py "Bank" url [url...]  -> appends to crawl/manual.json
bank=sys.argv[1]; L=json.load(open("crawl/manual.json")) if os.path.exists("crawl/manual.json") else []
for u in sys.argv[2:]:
    h=hashlib.md5(u.encode()).hexdigest()[:8]; out=f"pdf/{h}.pdf"
    if not os.path.exists(out) or os.path.getsize(out)<2000:
        subprocess.run(["curl","-sSL","--max-time","180","-A","Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",u,"-o",out])
    t=f"txt/{h}.txt"; subprocess.run(["pdftotext","-layout",out,t],capture_output=True)
    typ=subprocess.run(["file","-b",out],capture_output=True,text=True).stdout[:30]
    n=len(open(t,errors="replace").read()) if os.path.exists(t) else 0
    print(bank[:30], h, typ, os.path.getsize(out) if os.path.exists(out) else 0, "chars", n, u.split("/")[-1][:60])
    L=[x for x in L if x["url"]!=u]+[{"bank":bank,"url":u,"fn":u.split("?")[0].split("/")[-1],"file":out}]
json.dump(L,open("crawl/manual.json","w"),ensure_ascii=False,indent=1)
