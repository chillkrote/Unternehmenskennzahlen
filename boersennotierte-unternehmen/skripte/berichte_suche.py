"""Sucht auf den Unternehmenswebsites den Geschäftsbericht bzw. Jahresfinanzbericht für ein Geschäftsjahr.

Vorgehen je Unternehmen: Startseite (Website laut Yahoo bzw. Börse) laden, Links zu Investor-Relations-
und Berichtsseiten folgen (höchstens zwei Ebenen, höchstens MAX_SEITEN Seiten), alle PDF-Links sammeln
und nach Stichworten und Jahr bewerten. Keine Umgehung von Bot-Schutz: Seiten, die mit 403/429 oder
einer Captcha-Seite antworten, werden als gesperrt vermerkt.

Aufruf: python3 berichte_suche.py <eingabe.json> <ausgabe.json> [--jahr=2025]
  eingabe.json: Liste von {"id", "name", "website"}
"""
import concurrent.futures as cf
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
import hoeflich  # noqa: E402

UA = hoeflich.UA
MAX_SEITEN = int(__import__("os").environ.get("MAX_SEITEN", 30))
MAX_TIEFE = int(__import__("os").environ.get("MAX_TIEFE", 2))
SONDERPFADE = ["/investor-relations", "/ir", "/de/investor-relations", "/investoren", "/en/investor-relations", "/finanzberichte", "/investor-relations/finanzberichte", "/investor-relations/berichte", "/de/investor-relations/finanzberichte-und-praesentationen", "/de/ir", "/aktie", "/investor", "/unternehmen/investor-relations", "/downloads", "/publikationen"]
IR_WORTE = re.compile(r"investor|/ir\b|/ir/|aktionär|aktionaer|finanzbericht|finanzpublikation|publikation|berichte|reports?\b|"
                      r"geschäftsbericht|geschaeftsbericht|annual|veröffentlichung|veroeffentlichung|downloads?|financial|"
                      r"jahresabschluss|hauptversammlung|unternehmen/zahlen|kennzahlen|news-?center|presse", re.I)
PDF_GUT = re.compile(r"gesch(ä|ae|a)ftsbericht|annual[-_ ]?report|jahresfinanzbericht|konzernabschluss|jahresabschluss|"
                     r"konzernbericht|geschaeftsjahr|integrated[-_ ]?report|annual[-_ ]?financial|financial[-_ ]?report|"
                     r"\bgb[-_ ]?\d\d|\bar[-_ ]?20|jahresbericht", re.I)
PDF_SCHLECHT = re.compile(r"halbjahr|half[-_ ]?year|quartal|quarter|\bq[1-3]\b|h1[-_ ]|9m|interim|zwischen|präsentation|presentation|"
                          r"factsheet|einladung|invitation|agenda|tagesordnung|abstimmung|voting|rede|speech|vergütungsbericht|"
                          r"remuneration|nachhaltigkeit|sustainability|esg|cdp|corporate[-_ ]?governance|entsprechens|"
                          r"compliance|policy|richtlinie|satzung|articles|conf[-_. ]?call|earnings[-_ ]?call|einberufung|flyer|shareholdings|"
                          r"anteilsbesitz|disposal|alternative[-_ ]performance|transaktion|aufsichtsrat|comment|kommentar|update|montega|research|"
                          r"nfe\b|nichtfinanz|non[-_ ]financial|\bh1|info[-_]|implementing|list[-_ ]of|bestätigungsvermerk|kurzbericht|summary|auszug|excerpt|fact[-_ ]?book|"
                          r"tabellen|tables|xlsx|kennzahlen[-_ ]?übersicht", re.I)


def holen(session, url, timeout=15):
    if not hoeflich.erlaubt(url):
        return None, "robots.txt"
    try:
        r = session.get(url, timeout=timeout, allow_redirects=True, stream=True)
        if "pdf" in r.headers.get("content-type", "") or int(r.headers.get("content-length") or 0) > 5_000_000:
            r.close()  # PDFs und große Dateien nicht herunterladen, nur vermerken
            r._content = b""
            return r, "ok"
        r._content = r.raw.read(3_000_000, decode_content=True)
    except Exception as e:
        return None, f"fehler: {type(e).__name__}"
    if r.status_code in (403, 429, 503) or re.search(r"captcha|cf-chl|are you a human|incapsula", r.text[:5000], re.I):
        return r, "gesperrt"
    if r.status_code >= 400:
        return r, f"http {r.status_code}"
    return r, "ok"


def links(base, text):
    for m in re.finditer(r"""href\s*=\s*["']([^"'#]+)["'][^>]*>(.*?)</a>""", text, re.I | re.S):
        href = m.group(1).strip()
        if href.startswith(("mailto:", "javascript:", "tel:")):
            continue
        label = re.sub(r"<[^>]+>", " ", m.group(2))
        yield urljoin(base, href), " ".join(label.split())[:200]


def bewerte(url, label, jahr):
    s = url + " " + label
    datei = urlparse(url).path.rsplit("/", 1)[-1] + " " + label  # Jahr im Dateinamen zählt mehr als im Pfad (Upload-Ordner)
    p = 0
    if PDF_GUT.search(s):
        p += 10
    if PDF_SCHLECHT.search(s):
        p -= 12
    if re.search(r"gesch(ä|ae|a)ftsbericht|annual[-_ ]?report|jahresfinanzbericht|integrated|konzern|group|\bgb", s, re.I):
        p += 3  # Konzern-Geschäftsbericht vor HGB-Einzelabschluss
    if re.search(r"einzelabschluss|financial[-_ ]statements[-_ ]for|hgb", s, re.I):
        p -= 3
    jahre = {int(j) for j in re.findall(r"(?<!\d)(20[0-3]\d)(?!\d)", datei)}
    kurz = {2000 + int(j) for j in re.findall(r"(?:gb|ar|fy|gj)[-_ ]?(\d\d)(?!\d)", datei, re.I)}
    jahre |= kurz
    if jahr in jahre or f"{jahr}/{str(jahr + 1)[2:]}" in datei or f"{jahr - 1}/{str(jahr)[2:]}" in datei:
        p += 8
    elif jahre and max(jahre) < jahr:
        p -= 8
    elif str(jahr) in url:
        p += 2
    if re.search(r"(^|[-_/])(de|deu|german|deutsch)([-_.]|$)", url, re.I):
        p += 1
    return p


def suche(eintrag, jahr):
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "de-DE,de;q=0.9,en;q=0.6"})
    start = eintrag.get("website") or ""
    if not start:
        return {**eintrag, "status": "keine website", "kandidaten": []}
    if not start.startswith("http"):
        start = "https://" + start
    host = urlparse(start).netloc.replace("www.", "")
    besucht, warteschlange, pdfs = set(), [(start, 0)], {}
    if MAX_TIEFE > 2:  # Zweitlauf: übliche IR-Pfade und Sitemap zusätzlich anlaufen
        basis = "{u.scheme}://{u.netloc}".format(u=urlparse(start))
        warteschlange += [(basis + pf, 1) for pf in SONDERPFADE]
        r0, st0 = holen(session, basis + "/sitemap.xml")
        if st0 == "ok" and r0 is not None:
            for loc in re.findall(r"<loc>([^<]+)</loc>", r0.text)[:4000]:
                if IR_WORTE.search(loc) and not loc.lower().endswith((".xml", ".jpg", ".png")):
                    warteschlange.append((loc, 2))
    status = None
    ende = time.time() + 150  # höchstens 2,5 Minuten je Website
    while warteschlange and len(besucht) < MAX_SEITEN and time.time() < ende:
        url, tiefe = warteschlange.pop(0)
        if url in besucht:
            continue
        besucht.add(url)
        r, st = holen(session, url)
        if status is None:
            status = st
        if st != "ok" or r is None:
            continue
        ct = r.headers.get("content-type", "")
        if "pdf" in ct:
            pdfs.setdefault(r.url, "")
            continue
        if "html" not in ct:
            continue
        for ziel, label in links(r.url, r.text):
            h = urlparse(ziel).netloc.replace("www.", "")
            if ziel.lower().split("?")[0].endswith(".pdf") or "pdf" in ziel.lower().split("/")[-1][-12:]:
                if len(label) > len(pdfs.get(ziel, "")):
                    pdfs[ziel] = label
                else:
                    pdfs.setdefault(ziel, label)
            elif tiefe < MAX_TIEFE and (host.split(".")[-2] in h) and IR_WORTE.search(ziel + " " + label):
                ziel = ziel.split("#")[0]
                if ziel not in besucht:
                    warteschlange.append((ziel, tiefe + 1))
        time.sleep(0.3)
    kand = sorted(({"url": u, "label": l, "punkte": bewerte(u, l, jahr)} for u, l in pdfs.items()),
                  key=lambda k: -k["punkte"])
    return {**eintrag, "status": status or "leer", "seiten": len(besucht), "kandidaten": kand[:15]}


def main():
    ein, aus = sys.argv[1], sys.argv[2]
    jahr = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--jahr=")), 2025))
    eintraege = json.load(open(ein, encoding="utf-8"))
    ergebnisse = []
    with cf.ThreadPoolExecutor(16) as ex:
        for e in (f.result() for f in cf.as_completed([ex.submit(suche, x, jahr) for x in eintraege])):
            beste = e["kandidaten"][0] if e["kandidaten"] else {}
            print(e["id"], e["status"], beste.get("punkte"), beste.get("url", "")[:120], flush=True)
            ergebnisse.append(e)
    json.dump(ergebnisse, open(aus, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
