"""Lädt je Bank und Jahr den bestplatzierten Berichts-Link aus alte_berichte_suchen.py herunter.

Aufruf: python3 -I alte_berichte_laden.py LINKS.json ZIELORDNER INDEX.csv
Schreibt ZIELORDNER/<bank-slug>/<jahr>_<hash>.pdf und INDEX.csv (bank, jahr, url, datei, sha256, abruf).
Nur Dateien, die wirklich mit %PDF beginnen; max. 80 MB je Datei.
"""
import concurrent.futures as cf
import csv
import datetime
import hashlib
import json
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
GUT = re.compile(r"gesch(?:ae|ä)ftsbericht|jahresabschluss|jahresbericht|lagebericht", re.I)


def slug(n):
    import unicodedata
    s = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def wahl(funde):
    je_jahr = {}
    for u, x in funde.items():
        je_jahr.setdefault(x["jahr"], []).append((0 if GUT.search(urllib.parse.unquote(u) + x["text"]) else 1, len(u), u))
    return {j: sorted(l)[0][2] for j, l in je_jahr.items()}


def laden(job):
    bank, jahr, u, ziel = job
    d = ziel / slug(bank)
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{jahr}_{hashlib.md5(u.encode()).hexdigest()[:8]}.pdf"
    if not f.exists():
        subprocess.run(["curl", "-sSL", "--max-time", "120", "--max-filesize", str(80_000_000), "-A", UA,
                        urllib.parse.quote(u, safe=":/?=&%#@+,;~"), "-o", str(f)], capture_output=True)
    if not f.exists() or f.stat().st_size < 5000 or f.read_bytes()[:4] != b"%PDF":
        f.unlink(missing_ok=True)
        return None
    return [bank, jahr, u, str(f.relative_to(ziel)), hashlib.sha256(f.read_bytes()).hexdigest(), datetime.date.today().isoformat()]


def main():
    links, ziel, index = json.load(open(sys.argv[1])), Path(sys.argv[2]), sys.argv[3]
    jobs = [(b, j, u, ziel) for b, funde in links.items() for j, u in sorted(wahl(funde).items())]
    with cf.ThreadPoolExecutor(8) as ex:
        res = [r for r in ex.map(laden, jobs) if r]
    with open(index, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["bank", "jahr", "url", "datei", "sha256", "abruf"])
        w.writerows(res)
    print(len(jobs), "Links,", len(res), "PDFs geladen")


if __name__ == "__main__":
    main()
