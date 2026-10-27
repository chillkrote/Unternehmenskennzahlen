import sys, re, json, subprocess, urllib.parse, concurrent.futures as cf
from crawl import get, PDF, PAGE
LINK = re.compile(r"offenleg|geschaeftsbericht|geschäftsbericht|berichte|jahresabschluss|zahlen|presse|portrait|bilanz|ueber-uns|ihre-sparkasse-vor-ort|pflichtangaben|rechtlich|hinweise", re.I)
def final(u):
    r = subprocess.run(["curl", "-sSL", "--max-time", "20", "-A", "Mozilla/5.0", "-o", "/dev/null", "-w", "%{url_effective}", u], capture_output=True, text=True)
    return r.stdout.strip()
def crawl(dom):
    fu = final("https://www." + dom + "/")
    if not fu.startswith("http"): return {"domain": dom, "pdfs": {}, "pages": 0}
    p = urllib.parse.urlparse(fu); base = f"{p.scheme}://{p.netloc}"
    seen = set(); pdfs = {}
    level = [base + "/", fu, base + "/de/home/toolbar/preise-und-hinweise.html"]
    sm = get(base + "/sitemap.xml")
    locs = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", sm)
    for s in [l for l in locs if l.endswith(".xml")][:5]:
        locs += re.findall(r"<loc>\s*([^<]+?)\s*</loc>", get(s))
    level += sorted({l for l in locs if not l.endswith(".xml") and LINK.search(l)}, key=len)[:40]
    for depth in range(2):
        nxt = []
        level = [u for u in dict.fromkeys(level) if u not in seen][:60]
        seen.update(level)
        def one(pg):
            h = get(pg); res = []; links = []
            for m in re.finditer(r'href="([^"]+)"', h, re.I):
                raw = m.group(1).replace("&amp;", "&").replace("&#61;", "=")
                u = urllib.parse.urljoin(pg, raw)
                if re.search(r"\.pdf|scene7\.com/is/content/", u, re.I):
                    if PDF.search(urllib.parse.unquote(u)): res.append((u, pg))
                elif urllib.parse.urlparse(u).netloc == p.netloc and LINK.search(u) and u.endswith((".html", "/")) or (urllib.parse.urlparse(u).netloc == p.netloc and ".html?" in u and LINK.search(u)):
                    links.append(u.split("#")[0])
            return res, links
        with cf.ThreadPoolExecutor(6) as ex:
            for res, links in ex.map(one, level):
                for u, pg in res: pdfs.setdefault(u, pg)
                nxt += links
        level = nxt
    return {"domain": dom, "base": base, "pdfs": pdfs, "pages": len(seen)}
if __name__ == "__main__":
    res = {}
    with cf.ThreadPoolExecutor(4) as ex:
        for d, r in zip(sys.argv[1:], ex.map(crawl, sys.argv[1:])):
            res[d] = r; print(d, r.get("base"), r["pages"], len(r["pdfs"]), file=sys.stderr)
    print(json.dumps(res, ensure_ascii=False, indent=1))
