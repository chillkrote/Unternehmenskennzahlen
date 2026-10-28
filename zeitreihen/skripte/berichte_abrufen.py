"""Ruft die Jahresabschlüsse der Abrufliste (abrufliste_unternehmensregister.csv) aus frei zugänglichen Quellen ab.

Phasen (alle wiederholbar, vorhandene Dateien werden nicht erneut geladen):
  links     Websites der Banken nach Berichts-PDFs durchsuchen (nutzt alte_berichte_suchen.py), Ergebnis berichte_links.json
  laden     je Bank und Geschäftsjahr den besten Link laden
  wayback   für noch fehlende Berichte Archivkopien der Bank-Hosts im Internet Archive suchen und laden
  checkliste  zeitreihen/berichte_checkliste.csv und berichte_index.csv schreiben

Aufruf: python3 -I berichte_abrufen.py ZIELORDNER [phase ...]   (ohne Phase: laden wayback checkliste)
Ablage: ZIELORDNER/<ID>_<Name>/<GJ>/<Name>_GJ<GJ>_<hash>.pdf, keine PDFs im Repo.
Keine Umgehung von Captcha oder Bot-Schutz: Seiten mit 403/Abbruch werden übersprungen.
"""
import concurrent.futures as cf
import csv
import datetime
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import time
import unicodedata
import urllib.parse
from pathlib import Path

HIER = Path(__file__).resolve().parent
ZR = HIER.parent
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
GUT = re.compile(r"gesch(?:ae|ä)ftsbericht|jahresabschluss|jahresbericht|lagebericht|annual|finanzbericht|offenlegung", re.I)
AUSSCHLUSS = re.compile(r"halbjahr|zwischen|quartal|nachhaltig|csr|esg|verg(?:ü|ue)tung|satzung|flyer|broschuere|broschüre|q[1-4][-_ ]?20", re.I)
LINKS = ZR / "rohdaten" / "berichte_links.json"
HOSTS = ZR / "rohdaten" / "berichte_hosts.json"
WB = ZR / "rohdaten" / "berichte_wayback.json"


def slug(n):
    s = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")[:50]


def bedarf():
    r = csv.DictReader(open(ZR / "abrufliste_unternehmensregister.csv", encoding="utf-8-sig"), delimiter=";")
    return [(x["unternehmen_id"], x["bank"], int(g), x["prioritaet"]) for x in r for g in x["abschluesse_zu_holen_gj"].split()]


def curl(url, ziel=None, t=60):
    cmd = ["curl", "-sSL", "--max-time", str(t), "-A", UA]
    if ziel:
        cmd += ["-o", str(ziel)]
    r = subprocess.run(cmd + [url], capture_output=True)
    return None if ziel else r.stdout.decode("utf-8", "replace")


def pfad(root, uid, bank, gj, url):
    d = root / f"{uid}_{slug(bank)}" / str(gj)
    return d / f"{slug(bank)}_GJ{gj}_{hashlib.md5(url.encode()).hexdigest()[:8]}.pdf"


def hole(root, uid, bank, gj, url, art):
    f = pfad(root, uid, bank, gj, url)
    f.parent.mkdir(parents=True, exist_ok=True)
    if not f.exists():
        curl(url, f, 180)
    b = f.read_bytes() if f.exists() else b""
    if not b.startswith(b"%PDF") or len(b) > 150e6:
        f.unlink(missing_ok=True)
        return None
    return dict(unternehmen_id=uid, bank=bank, gj=gj, quelle_url=url, treffer=art, datei=str(f.relative_to(root)),
                sha256=hashlib.sha256(b).hexdigest(), bytes=len(b), abruf=datetime.date.today().isoformat())


def rang(u, text=""):
    return (0 if GUT.search(urllib.parse.unquote(u) + text) else 1, len(u))


def vorhandene(root):
    """Bereits geladene Berichte aus dem Dateibaum (Bank-ID, GJ) -> Datei."""
    return {(p.parts[-3].split("_")[0], int(p.parts[-2])): p for p in root.glob("*/*/*.pdf")}


def phase_links():
    spec = importlib.util.spec_from_file_location("s", HIER / "alte_berichte_suchen.py")
    s = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(s)
    import threading
    tl = threading.local()
    orig = s.get

    def get(u, t=12):
        if time.time() > getattr(tl, "dl", 1e18):
            raise TimeoutError
        return orig(u, min(t, 12))
    s.get = get
    hosts = json.load(open(HOSTS))
    res = {}

    def bank(it):
        n, hs = it
        f = {}
        for h in hs:
            tl.dl = time.time() + 240
            try:
                f.update(s.crawl(h))
            except Exception:
                pass
        return n, f
    with cf.ThreadPoolExecutor(24) as ex:
        for n, f in ex.map(bank, hosts.items()):
            res[n] = f
    json.dump(res, open(LINKS, "w"), ensure_ascii=False)


def phase_laden(root):
    links = json.load(open(LINKS))
    have = vorhandene(root)
    jobs = []
    for uid, bank, gj, _ in bedarf():
        if (uid, gj) in have:
            continue
        f = links.get(bank, {})
        for art, jahr in (("direkt", gj), ("folgejahr", gj + 1)):
            c = sorted((rang(u, x["text"]), u) for u, x in f.items() if x["jahr"] == jahr)
            if c:
                jobs.append((uid, bank, gj, c[0][1], art))
                break
    with cf.ThreadPoolExecutor(8) as ex:
        ok = [r for r in ex.map(lambda j: hole(root, *j), jobs) if r]
    print("laden:", len(ok), "von", len(jobs))


def phase_wayback(root):
    """Archivkopien aus dem Internet Archive (frei, ohne Anmeldung); höflich: eine Anfrage je Sekunde."""
    hosts = json.load(open(HOSTS))
    cache = json.load(open(WB)) if WB.exists() else {}
    have = vorhandene(root)
    fehlt = [(u, b, g) for u, b, g, _ in bedarf() if (u, g) not in have and hosts.get(b)]
    for bank in sorted({b for _, b, _ in fehlt}):
        for h in hosts[bank]:
            if h in cache:
                continue
            q = ("https://web.archive.org/cdx/search/cdx?url=" + urllib.parse.quote(h) + "&matchType=domain"
                 "&filter=mimetype:application/pdf&filter=statuscode:200&collapse=urlkey&fl=timestamp,original&limit=20000")
            txt = curl(q, t=120) or ""
            cache[h] = [l.split(" ", 1) for l in txt.splitlines() if " " in l]
            json.dump(cache, open(WB, "w"), ensure_ascii=False)
            time.sleep(1)
    n = 0
    for uid, bank, gj in fehlt:
        cand = []
        for h in hosts[bank]:
            for ts, orig in cache.get(h, []):
                s = urllib.parse.unquote(orig)
                if AUSSCHLUSS.search(s) or not GUT.search(s):
                    continue
                jahre = {int(j) for j in re.findall(r"(?<!\d)(20[12]\d)(?!\d)", s)}
                for art, jahr in (("wayback-direkt", gj), ("wayback-folgejahr", gj + 1)):
                    if jahr in jahre:
                        cand.append((art != "wayback-direkt", rang(orig), ts, orig, art))
        for _, _, ts, orig, art in sorted(cand)[:3]:
            r = hole(root, uid, bank, gj, f"https://web.archive.org/web/{ts}id_/{orig}", art)
            time.sleep(1)
            if r:
                n += 1
                break
    print("wayback:", n, "von", len(fehlt))


def phase_checkliste(root):
    have = vorhandene(root)
    alt = {}
    ip = ZR / "berichte_index.csv"
    if ip.exists():
        for r in csv.DictReader(open(ip, encoding="utf-8-sig"), delimiter=";"):
            alt[(r["unternehmen_id"], int(r["gj"]))] = r
    idx, chk = [], []
    for uid, bank, gj, prio in bedarf():
        p = have.get((uid, gj))
        if p:
            b = p.read_bytes()
            a = alt.get((uid, gj), {})
            idx.append(dict(unternehmen_id=uid, bank=bank, gj=gj, datei=str(p.relative_to(root)), sha256=hashlib.sha256(b).hexdigest(),
                            bytes=len(b), quelle_url=a.get("quelle_url", ""), treffer=a.get("treffer", ""),
                            abruf=a.get("abruf") or datetime.date.fromtimestamp(p.stat().st_mtime).isoformat()))
        chk.append(dict(prioritaet=prio, unternehmen_id=uid, bank=bank, gj=gj, status="geladen" if p else "offen",
                        zielordner=f"Berichte/{uid}_{slug(bank)}/{gj}/",
                        suche="https://www.unternehmensregister.de/ureg/search1.2.html?submitaction=language&language=de",
                        hinweis="" if p else "Jahresabschluss GJ %d: Unternehmensregister (Sicherheitsabfrage) oder Bankwebsite" % gj))
    for name, rows in (("berichte_index.csv", idx), ("berichte_checkliste.csv", chk)):
        if not rows:
            continue
        with open(ZR / name, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, rows[0].keys(), delimiter=";")
            w.writeheader()
            w.writerows(rows)
    print("geladen:", len(idx), "offen:", len(chk) - len(idx))


if __name__ == "__main__":
    root = Path(sys.argv[1]).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    phasen = sys.argv[2:] or ["laden", "wayback", "checkliste"]
    for ph in phasen:
        {"links": phase_links, "laden": lambda: phase_laden(root), "wayback": lambda: phase_wayback(root),
         "checkliste": lambda: phase_checkliste(root)}[ph]()
