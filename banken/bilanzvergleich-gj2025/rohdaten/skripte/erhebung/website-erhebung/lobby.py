import json, re, subprocess, urllib.parse, sys, concurrent.futures as cf
def get(u):
    return subprocess.run(["curl","-sS","--max-time","40",u],capture_output=True).stdout.decode("utf-8","replace")
names=[l[2:].split('|')[0].strip() for l in open('/mnt/project-files/bilanzvergleich/rohdaten/luecken.md') if l.startswith('- ')]
def term(n):
    n=re.sub(r"\(.*?\)","",n)
    n=re.sub(r"\b(AG|SE|GmbH|eG|KGaA|mbH|& Co\.? KG|Co KG|für Privatkunden und Handel)\b","",n)
    return " ".join(n.split()[:3])
def norm(s): return "".join(c for c in s.lower() if c.isalnum())
def one(n):
    t=term(n)
    try: j=json.loads(get("https://www.lobbyregister.bundestag.de/sucheJson?q="+urllib.parse.quote(t)))
    except Exception as e: return n,t,[],str(e)
    hits=[]
    for r in j.get("results",[]):
        nm=r["lobbyistIdentity"].get("name","")
        if norm(t)[:10] in norm(nm):
            h=get(r["registerEntryDetails"]["detailsPageUrl"])
            pdfs=[urllib.parse.urljoin("https://www.lobbyregister.bundestag.de",x) for x in re.findall(r'href="([^"]*/media/[^"]+\.pdf)"',h) if "Detailansicht" not in x]
            hits.append({"name":nm,"url":r["registerEntryDetails"]["detailsPageUrl"],"pdfs":pdfs})
    return n,t,hits,None
res={}
with cf.ThreadPoolExecutor(4) as ex:
    for n,t,h,e in ex.map(one,names):
        res[n]={"term":t,"hits":h,"err":e}
        if h: print(n,"|",t,"|",[(x["name"],[p.split('/')[-1] for p in x["pdfs"]]) for x in h])
json.dump(res,open("crawl/lobby.json","w"),ensure_ascii=False,indent=1)
