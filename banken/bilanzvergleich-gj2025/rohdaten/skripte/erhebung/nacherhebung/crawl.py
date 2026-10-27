import sys, re, json, subprocess, urllib.parse, concurrent.futures as cf
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
def get(u, t=25):
    r = subprocess.run(["curl", "-sSL", "--max-time", str(t), "-A", UA, u], capture_output=True)
    return r.stdout.decode("utf-8", "replace")
PAGE = re.compile(r"preise-und-hinweise|presse-center|offenleg|geschaeftsbericht|geschäftsbericht|jahresabschluss|bericht|zahlen|bilanz|presse|kennzahl|daten-fakten|fakten|veroeffentlich|publikation|ueber-uns|wir-ueber-uns|ihre-sparkasse/.*(portrait|profil)", re.I)
PDF = re.compile(r"offenleg|geschaeft|geschäft|jahresab|lagebericht|bilanz|jahrespresse|pressemit|finanzbericht|jahresbericht|presseinfo|offenlegung", re.I)
def crawl(dom):
    base = "https://www." + dom if not dom.startswith("http") else dom
    sm = get(base + "/sitemap.xml")
    locs = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", sm)
    subs = [l for l in locs if l.endswith(".xml")]
    for s in subs[:8]:
        locs += re.findall(r"<loc>\s*([^<]+?)\s*</loc>", get(s))
    pages = [l for l in locs if not l.endswith(".xml") and PAGE.search(l)]
    pages = sorted(set(pages), key=len)[:60]
    pages = [base + "/", base + "/de/home/toolbar/preise-und-hinweise.html", base + "/de/home/ihre-sparkasse/presse-center.html", base + "/de/home/ihre-sparkasse/presse.html"] + pages
    pdfs = {}
    def one(p):
        h = get(p)
        out = []
        for m in re.finditer(r'href="([^"]+?(?:\.pdf[^"]*|scene7\.com/is/content/[^"]+))"', h, re.I):
            u = urllib.parse.urljoin(p, m.group(1).replace("&amp;", "&").replace("&#61;", "="))
            if PDF.search(urllib.parse.unquote(u)):
                out.append((u, p))
        return out
    with cf.ThreadPoolExecutor(6) as ex:
        for res in ex.map(one, pages):
            for u, p in res:
                pdfs.setdefault(u, p)
    return {"domain": dom, "n_sitemap": len(locs), "pages": len(pages), "pdfs": pdfs}
if __name__ == "__main__":
    doms = sys.argv[1:]
    res = {}
    with cf.ThreadPoolExecutor(4) as ex:
        for d, r in zip(doms, ex.map(crawl, doms)):
            res[d] = r
            print(d, r["n_sitemap"], r["pages"], len(r["pdfs"]), file=sys.stderr)
    print(json.dumps(res, ensure_ascii=False, indent=1))
