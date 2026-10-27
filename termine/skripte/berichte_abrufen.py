"""Lädt Quartals-, Halbjahres- und Jahresberichte herunter, sobald ihr Termin erreicht ist.

Für jeden Eintrag in termine.csv mit termin <= heute (höchstens --fenster Tage zurück, Standard 21), der noch nicht geladen ist:
Website des Unternehmens (bei Banken berichte_url aus finanzkalender_quellen.csv) laden, zwei Ebenen Investor-Relations-Links folgen,
alle PDF-Links einsammeln und nach Berichtsart und Periode bewerten, den besten Kandidaten laden und prüfen (PDF lesbar, Berichts-
stichwort und Jahr auf den ersten Seiten, kein Foliensatz). Bestanden: Datei nach <branche>/dokumente/<id>/ (Banken: banken/unterjahr/
dokumente/<id>/), Eintrag in der index.csv dort, abruf_status "geladen" mit SHA-256. Nicht gefunden: versuche +1; täglicher
Neuversuch bis --maxversuche (Standard 10), danach abruf_status "nicht_gefunden". Seiten mit Bot-Schutz werden nicht umgangen
(abruf_status "gesperrt"). Dateien über 95 MB werden nicht gespeichert, sondern in termine/rohdaten/zu_gross.txt gemeldet.

Aufruf: python3 berichte_abrufen.py [--fenster=21] [--maxversuche=10] [--nur=<id,id>] [--trocken]
"""
import concurrent.futures as cf
import csv
import hashlib
import io
import re
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse

import logging
import requests

logging.getLogger("pypdf").setLevel(logging.ERROR)

import tlib

sys.path.insert(0, str(tlib.REPO / "boersennotierte-unternehmen" / "skripte"))
import berichte_suche as bs  # noqa: E402  (holen, links, IR_WORTE, UA)

MAX_BYTES = 95_000_000
KOPF = ["unternehmen", "unternehmen_id", "dokumentart", "geschaeftsjahr", "datei", "status", "quelle_url", "abruf", "sha256",
        "seiten", "bytes", "verwendet_in", "hinweis"]
ART = {
    "Q1-Bericht": (r"q1|1\.?\s?quartal|erstes\s+quartal|first[-_ ]quarter|three[-_ ]months|3[-_ ]?m\b|quarterly[-_ ](statement|report)|quartalsmitteilung|quartalsfinanz", "Quartalsbericht"),
    "Halbjahresbericht": (r"h1|q2|halbjahr|half[-_ ]?year|hjb|2\.?\s?quartal|second[-_ ]quarter|six[-_ ]months|interim|zwischenbericht|6[-_ ]?m\b", "Halbjahresbericht"),
    "Q3-Bericht": (r"q3|9m|9[-_ ]?monat|neun|nine[-_ ]months|3\.?\s?quartal|third[-_ ]quarter|quartalsmitteilung|quarterly[-_ ](statement|report)", "Quartalsbericht"),
    "Jahresbericht": (r"gesch(ä|ae)ftsbericht|annual[-_ ]report|jahresfinanzbericht|jahresabschluss|annual[-_ ]financial", "Geschäftsbericht"),
}
# Stichworte im Text des Berichts, die genau diese Periode belegen
PERIODE_TEXT = {
    "Q1-Bericht": r"q1|first quarter|1\.\s?quartal|erstes quartal|(march|märz|maerz)\s+31|31\.\s?märz|three months|3 months|drei monate|31\.03\.",
    "Halbjahresbericht": r"h1|q2|half[- ]year|halbjahr|second quarter|2\.\s?quartal|(june|juni)\s+30|30\.\s?juni|six months|6 months|sechs monate|30\.06\.",
    "Q3-Bericht": r"q3|third quarter|3\.\s?quartal|nine months|9 months|9m|neun monate|(september|sept?\.)\s+30|30\.\s?september|30\.09\.",
}
SCHLECHT = re.compile(r"praesentation|präsentation|presentation|slides?|folien|investor[-_ ]?deck|factsheet|call|speech|rede|transcript|"
                      r"einladung|invitation|hauptversammlung|agm|nachhaltigkeit|sustainab|esg|verguetung|vergütung|remuneration|"
                      r"corporate[-_ ]governance|satzung|ad[-_ ]?hoc|pressemitteilung|press[-_ ]release|stimmrecht|voting|"
                      r"pillar|offenlegung|disclosure|tabellen|tables|xlsx|kennzahlen[-_ ]?uebersicht|datenblatt|databook|supplement|"
                      r"erklärung|erklaerung|presse|news", re.I)


def bewerten(url, label, art, ende):
    muster = ART[art][0]
    s = (url + " " + label).lower()
    datei = unquote(urlparse(url).path.rsplit("/", 1)[-1]).lower() + " " + label.lower()
    p = 0
    if re.search(muster, s):
        p += 10
    if SCHLECHT.search(s):
        p -= 12
    if art != "Jahresbericht" and re.search(r"gesch(ä|ae)ftsbericht|annual[-_ ]report", datei) and not re.search(muster, datei):
        p -= 10
    jahre = {int(j) for j in re.findall(r"(?<!\d)(20[0-3]\d)(?!\d)", datei)} | {2000 + int(j) for j in re.findall(r"(?:q[1-4]|h[12]|9m|fy|gj|gb)[-_ ]?(\d\d)(?!\d)", datei)}
    for andere, (m, _) in ART.items():  # Dateiname nennt eine andere Berichtsart (z. B. q1 statt q3)
        if andere != art and andere != "Jahresbericht" and re.search(rf"(?<![a-z0-9])({m})(?![a-z0-9])", datei) and not re.search(muster, datei):
            p -= 10
    if ende and ende.year in jahre or (ende and f"{ende.year}" in datei):
        p += 8
    elif jahre and ende and max(jahre) < ende.year:
        p -= 10
    if ende and f"{ende.year}-{ende.month:02d}" in s:
        p += 2
    return p


def pruefe(daten, art, ende):
    from pypdf import PdfReader
    try:
        pdf = PdfReader(io.BytesIO(daten))
        n = len(pdf.pages)
        text = " ".join((pdf.pages[i].extract_text() or "") for i in range(min(4, n)))
    except Exception as e:
        return False, f"kein lesbares PDF ({type(e).__name__})", 0
    text = " ".join(text.split())
    if n < 3:
        return False, f"nur {n} Seiten", n
    if art != "Jahresbericht" and n > 90 and not re.search(r"quartal|quarter|halbjahr|half|interim|zwischen", text[:2500], re.I):
        return False, "kein unterjähriger Bericht", n
    if not re.search(ART[art][0] + r"|quartal|quarter|halbjahr|half[- ]year|interim|zwischen|gesch(ä|ae)ftsbericht|annual", text[:3500], re.I):
        return False, "Berichtsart nicht erkennbar", n
    if ende and not re.search(rf"(?<!\d){ende.year}(?!\d)|{ende.year - 1}\s*/\s*(20)?{str(ende.year)[2:]}|{ende.year}\s*/\s*(20)?{str(ende.year + 1)[2:]}", text[:5000]):
        return False, "Jahr nicht erkennbar", n
    if art in PERIODE_TEXT and not re.search(PERIODE_TEXT[art], text[:3500], re.I):
        return False, "Periode nicht erkennbar", n
    if re.search(r"präsentation|presentation|conference call|earnings call|investor presentation", text[:400], re.I):
        return False, "Foliensatz", n
    return True, "ok", n


SEITE_GUT = re.compile(r"quartal|quarter|interim|zwischen|halbjahr|half|finanzbericht|financial[-_ ]?(report|result|publication)|"
                       r"berichte|reports|publikation|publication|ergebnis|results|download", re.I)


def alle_pdfs(start, max_seiten=40, max_sek=120):
    """Wie berichte_suche.suche, aber ohne Kürzung der Kandidaten; Seiten mit Berichtsbezug zuerst."""
    s = requests.Session()
    s.headers.update({"User-Agent": bs.UA, "Accept-Language": "de-DE,de;q=0.9,en;q=0.6"})
    if not start.startswith("http"):
        start = "https://" + start
    host = urlparse(start).netloc.replace("www.", "")
    basis = ".".join(host.split(".")[-2:])
    besucht, queue, pdfs, status = set(), [(0, start, 0)], {}, None
    ende = time.time() + max_sek
    while queue and len(besucht) < max_seiten and time.time() < ende:
        queue.sort(key=lambda q: (q[0], q[2]))
        _, url, tiefe = queue.pop(0)
        if url in besucht:
            continue
        besucht.add(url)
        r, st = bs.holen(s, url)
        status = status or st
        if r is None or st != "ok":
            continue
        ct = r.headers.get("content-type", "")
        if "pdf" in ct:
            pdfs.setdefault(r.url, "")
            continue
        if "html" not in ct:
            continue
        for ziel, label in bs.links(r.url, r.text):
            if ziel.lower().split("?")[0].endswith(".pdf") or "pdf" in ziel.lower().split("/")[-1][-12:]:
                pdfs[ziel] = max(label, pdfs.get(ziel, ""), key=len)
            elif tiefe < 2 and basis in urlparse(ziel).netloc and bs.IR_WORTE.search(ziel + " " + label):
                ziel = ziel.split("#")[0]
                if ziel not in besucht:
                    queue.append((0 if SEITE_GUT.search(ziel + " " + label) else 1, ziel, tiefe + 1))
        time.sleep(0.2)
    return pdfs, status


def suchen_und_laden(z, u, start):
    art = z["berichtsart"]
    ende = date.fromisoformat(z["periode_ende"]) if z["periode_ende"] else None
    if not start:
        return {"ok": False, "grund": "keine website"}
    pdfs, status = alle_pdfs(start)
    if status == "gesperrt" and not pdfs:
        return {"ok": False, "grund": "gesperrt"}
    bew = sorted(({"url": u_, "label": l, "p": bewerten(u_, l, art, ende)} for u_, l in pdfs.items()), key=lambda k: -k["p"])
    s = requests.Session()
    s.headers.update({"User-Agent": bs.UA, "Accept": "application/pdf,*/*"})
    versuche = []
    for k in bew[:6]:
        if k["p"] < 6:
            break
        try:
            r = s.get(k["url"], timeout=90)
        except Exception as e:
            versuche.append((k["url"], type(e).__name__))
            continue
        if r.status_code != 200:
            versuche.append((k["url"], f"http {r.status_code}"))
            continue
        if len(r.content) > MAX_BYTES:
            return {"ok": False, "grund": "zu groß", "url": k["url"], "mb": len(r.content) // 1_000_000}
        ok, grund, n = pruefe(r.content, art, ende)
        if ok:
            return {"ok": True, "url": k["url"], "daten": r.content, "seiten": n}
        versuche.append((k["url"], grund))
    return {"ok": False, "grund": "nicht gefunden", "versuche": versuche[:3]}


def dateiname(url, ende, art):
    n = re.sub(r"[^A-Za-z0-9._-]+", "_", unquote(urlparse(url).path.rsplit("/", 1)[-1])).strip("_")[:90] or "bericht.pdf"
    n = n if n.lower().endswith(".pdf") else n + ".pdf"
    kurz = {"Q1-Bericht": "Q1", "Halbjahresbericht": "H1", "Q3-Bericht": "Q3", "Jahresbericht": "GB"}[art]
    return f"{ende.year if ende else 'x'}_{kurz}_{n}"


def index_schreiben(pfad, zeilen):
    alt = []
    if not pfad.exists() and subprocess.run(["git", "ls-files", "--error-unmatch", str(pfad)], cwd=tlib.REPO, capture_output=True).returncode == 0:
        raise SystemExit(f"{pfad} ist im Git, fehlt aber im Arbeitsverzeichnis (Sparse-Checkout?); index.csv würde überschrieben")
    if pfad.exists():
        with open(pfad, encoding="utf-8-sig", newline="") as f:
            alt = list(csv.DictReader(f, delimiter=";"))
    dat = {z["datei"] for z in zeilen}
    alle = [z for z in alt if z["datei"] not in dat] + zeilen
    alle.sort(key=lambda z: (z["unternehmen_id"], z.get("geschaeftsjahr", ""), z["datei"]))
    assert len(alle) >= len(alt), f"{pfad}: index.csv würde schrumpfen"
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with open(pfad, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, KOPF, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(alle)


def main():
    a = sys.argv[1:]
    fenster = int(next((x.split("=")[1] for x in a if x.startswith("--fenster=")), 21))
    maxv = int(next((x.split("=")[1] for x in a if x.startswith("--maxversuche=")), 10))
    nur = set(next((x.split("=")[1] for x in a if x.startswith("--nur=")), "").split(",")) - {""}
    heute = date.today()
    uni = tlib.unternehmen()
    start = {k: v.get("website") for k, v in uni.items()}
    start.update({r["unternehmen_id"]: r["berichte_url"] for r in tlib.lese_csv(tlib.QUELLEN_FK) if r.get("berichte_url")})
    zeilen = tlib.lese_csv(tlib.CSV_PFAD)
    faellig = [z for z in zeilen if z["unternehmen_id"] in uni and (not nur or z["unternehmen_id"] in nur)
               and z["abruf_status"] not in ("geladen", "nicht_gefunden")
               and heute - timedelta(days=fenster) <= date.fromisoformat(z["termin"]) <= heute
               and (z["status"] != "erwartet" or z["quelle"] != "yahoo" or z["termin"] < heute.isoformat())
               and int(z["versuche"] or 0) < maxv]
    print(f"{len(faellig)} fällige Berichte")
    if "--trocken" in a:
        for z in faellig:
            print(" ", z["termin"], z["unternehmen_id"], z["berichtsart"], z["periode_ende"])
        return
    neue, gross = {}, []
    with cf.ThreadPoolExecutor(6) as ex:
        futs = {ex.submit(suchen_und_laden, z, uni[z["unternehmen_id"]], start.get(z["unternehmen_id"])): z for z in faellig}
        for f in cf.as_completed(futs):
            z, r = futs[f], f.result()
            u = uni[z["unternehmen_id"]]
            ende = date.fromisoformat(z["periode_ende"]) if z["periode_ende"] else None
            z["stand"] = heute.isoformat()
            if r["ok"]:
                name = dateiname(r["url"], ende, z["berichtsart"])
                ziel = tlib.REPO / u["ordner"] / u["ordner_name"] / name
                ziel.parent.mkdir(parents=True, exist_ok=True)
                ziel.write_bytes(r["daten"])
                sha = hashlib.sha256(r["daten"]).hexdigest()
                z.update(abruf_status="geladen", datei=str(ziel.relative_to(tlib.REPO)), sha256=sha, quelle_url=z["quelle_url"] or r["url"],
                         status="erschienen", versuche=str(int(z["versuche"] or 0) + 1))
                dok = tlib.REPO / u["ordner"] / "index.csv"
                neue.setdefault(dok, []).append({
                    "unternehmen": u["name"], "unternehmen_id": z["unternehmen_id"], "dokumentart": ART[z["berichtsart"]][1],
                    "geschaeftsjahr": str(ende.year if ende else ""), "datei": f"{u['ordner_name']}/{name}",
                    "status": "Originaldokument (PDF)", "quelle_url": r["url"], "abruf": f"Download {heute.strftime('%d.%m.%Y')}",
                    "sha256": sha, "seiten": r["seiten"], "bytes": len(r["daten"]), "verwendet_in": "",
                    "hinweis": f"{z['berichtsart']} Periode bis {z['periode_ende']}, Termin {z['termin']}"})
                print("OK", z["unternehmen_id"], z["berichtsart"], name, flush=True)
            else:
                z["versuche"] = str(int(z["versuche"] or 0) + 1)
                if r["grund"] == "zu groß":
                    gross.append(f"{z['unternehmen_id']} {z['berichtsart']} {r['mb']} MB {r['url']}")
                    z["abruf_status"] = "zu_gross"
                elif r["grund"] == "gesperrt":
                    z["abruf_status"] = "gesperrt"
                elif int(z["versuche"]) >= maxv:
                    z["abruf_status"] = "nicht_gefunden"
                else:
                    z["abruf_status"] = "offen"
                print("--", z["unternehmen_id"], z["berichtsart"], r["grund"], flush=True)
    for pfad, rows in neue.items():
        index_schreiben(pfad, rows)
    if gross:
        p = tlib.TERMINE / "rohdaten" / "zu_gross.txt"
        p.parent.mkdir(exist_ok=True)
        p.write_text("\n".join(sorted(set((p.read_text().splitlines() if p.exists() else []) + gross))) + "\n", encoding="utf-8")
    tlib.schreibe_termine(zeilen)


if __name__ == "__main__":
    main()
