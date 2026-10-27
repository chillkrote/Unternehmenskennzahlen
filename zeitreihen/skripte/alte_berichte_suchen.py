"""Sucht auf den Websites der Banken nach Geschäfts-/Jahresberichten älterer Jahre (frei zugängliche Links).

Crawlt je Host Startseite, Sitemap und zwei Linkebenen (nur Seiten mit Berichts-Stichwörtern), sammelt PDF-Links,
deren URL oder Linktext ein Jahr 2012-2024 und ein Berichtswort enthält. Keine Anmeldung, keine Umgehung von
Bot-Schutz: Hosts, die Verbindungen abbrechen oder 403 melden, werden übersprungen.
Aufruf: python3 -I alte_berichte_suchen.py HOSTS.json AUS.json [--max N]
HOSTS.json: {Bankname: [Host, ...]}. AUS.json: {Bankname: {url: {"jahr": J, "text": ...}}}
"""
import concurrent.futures as cf
import html
import json
import re
import subprocess
import sys
import urllib.parse

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
SEITE = re.compile(r"geschaeftsbericht|geschäftsbericht|jahresabschluss|jahresbericht|finanzbericht|bericht|publikation|download|archiv|zahlen|investor|veroeffentlich|veröffentlich|offenleg|ueber-uns|presse", re.I)
PDF = re.compile(r"\.pdf|scene7\.com/is/content/", re.I)
BERICHT = re.compile(r"gesch(?:ae|ä)fts|jahresab|jahresbericht|finanzbericht|annual|lagebericht|gb[-_ ]?20|jab[-_ ]?20|bericht", re.I)
AUSSCHLUSS = re.compile(r"halbjahr|zwischen|quartal|teiloffenleg|nachhaltig|csr|esg|vergütung|verguetung|satzung|preis|flyer|broschuere|broschüre|marktbericht|ifrs|q[1-4][-_ ]?20", re.I)
JAHR = re.compile(r"(?<!\d)(20[12]\d)(?!\d)")


def get(u, t=20):
    r = subprocess.run(["curl", "-sSL", "--max-time", str(t), "-A", UA, u], capture_output=True)
    return r.stdout.decode("utf-8", "replace")


def kandidat(url, text):
    s = urllib.parse.unquote(url) + " " + text
    if not BERICHT.search(s) or AUSSCHLUSS.search(s):
        return None
    jahre = {int(j) for j in JAHR.findall(s)}
    jahre = {j for j in jahre if 2012 <= j <= 2024}
    return max(jahre) if jahre else None


def crawl(host):
    base = "https://" + host
    seen, funde = set(), {}
    ebene = [base + "/"]
    sm = get(base + "/sitemap.xml")
    locs = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", sm)
    for s in [l for l in locs if l.endswith(".xml")][:4]:
        locs += re.findall(r"<loc>\s*([^<]+?)\s*</loc>", get(s))
    ebene += sorted({l for l in locs if not l.endswith(".xml") and SEITE.search(l)}, key=len)[:30]
    for _ in range(2):
        nxt = []
        for seite in [u for u in dict.fromkeys(ebene) if u not in seen][:50]:
            seen.add(seite)
            h = get(seite)
            for m in re.finditer(r'<a\b[^>]*?href="([^"]+)"[^>]*>(.*?)</a>', h, re.I | re.S):
                u = urllib.parse.urljoin(seite, html.unescape(m.group(1)))
                text = re.sub(r"<[^>]+>|\s+", " ", html.unescape(m.group(2))).strip()[:120]
                if PDF.search(u):
                    j = kandidat(u, text)
                    if j:
                        funde.setdefault(u, {"jahr": j, "text": text})
                elif urllib.parse.urlparse(u).netloc == host and SEITE.search(u) and not PDF.search(u):
                    nxt.append(u.split("#")[0])
        ebene = nxt
    return funde


def main():
    hosts = json.load(open(sys.argv[1]))
    aus = sys.argv[2]
    ergebnis = {}

    def bank(item):
        name, hs = item
        f = {}
        for h in hs:
            try:
                f.update(crawl(h))
            except Exception:
                pass
        return name, f

    with cf.ThreadPoolExecutor(10) as ex:
        for name, f in ex.map(bank, hosts.items()):
            ergebnis[name] = f
            print(name, len(f), file=sys.stderr, flush=True)
    json.dump(ergebnis, open(aus, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
