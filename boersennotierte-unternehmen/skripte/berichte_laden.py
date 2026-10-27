"""Lädt die gefundenen Geschäftsberichte, prüft sie und legt sie im Branchenordner ab.

Aufruf: python3 berichte_laden.py <suche.json> [--jahr=2025]
  suche.json: Ausgabe von berichte_suche.py (bzw. Handliste mit "kandidaten": [{"url": ...}])

Je Unternehmen werden die Kandidaten in Reihenfolge der Bewertung geladen, bis einer die Prüfung besteht:
  - Datei ist ein PDF mit mindestens MIN_SEITEN Seiten,
  - die ersten Seiten nennen Geschäfts-/Jahres-/Finanzbericht bzw. Annual Report oder (Konzern-)Abschluss,
  - und das Geschäftsjahr (2025, 2024/25 oder 2025/26).
Abgelegt wird unter <branche>/dokumente/<unternehmen_id>/<Dateiname>, eingetragen in <branche>/dokumente/index.csv
(Spalten wie bei banken/bilanzvergleich-gj2025). Fehlversuche stehen in rohdaten/berichte_status.json.
"""
import csv
import hashlib
import io
import json
import re
import sys
import time
import concurrent.futures as cf
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from pypdf import PdfReader

HIER = Path(__file__).resolve().parent
BASIS = HIER.parent
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
MIN_SEITEN = 16
MAX_BYTES = 95_000_000  # GitHub-Grenze 100 MB je Datei
BERICHT = re.compile(r"gesch(ä|ae)ftsbericht|annual\s+report|jahresfinanzbericht|jahresbericht|konzernabschluss|"
                     r"jahresabschluss|integrated\s+report|annual\s+financial\s+report|financial\s+statements|"
                     r"konzernlagebericht|group\s+management\s+report|lagebericht", re.I)
UNTERJ = re.compile(r"halbjahres|half[- ]year|quartals|quarterly|zwischenbericht|interim\s+report|9[- ]?monats", re.I)

KOPF = ["unternehmen", "unternehmen_id", "dokumentart", "geschaeftsjahr", "datei", "status", "quelle_url", "abruf", "sha256",
        "seiten", "bytes", "verwendet_in", "hinweis"]


def jahr_muster(jahr):
    v, n = str(jahr - 1), str(jahr + 1)
    return re.compile(rf"(?<!\d)({jahr}(?!\d)|{v}\s*/\s*(20)?{str(jahr)[2:]}(?!\d)|{jahr}\s*/\s*(20)?{n[2:]}(?!\d))")


def pruefe(daten, jahr):
    try:
        pdf = PdfReader(io.BytesIO(daten))
        seiten = len(pdf.pages)
        text = " ".join((pdf.pages[i].extract_text() or "") for i in range(min(4, seiten)))
    except Exception as e:
        return False, f"kein lesbares PDF ({type(e).__name__})", 0, ""
    text = " ".join(text.split())
    if seiten < MIN_SEITEN:
        return False, f"nur {seiten} Seiten", seiten, text
    if UNTERJ.search(text[:1500]) and not BERICHT.search(text[:300]):
        return False, "unterjähriger Bericht", seiten, text
    if not BERICHT.search(text):
        return False, "kein Geschäftsbericht/Abschluss erkennbar", seiten, text
    if not jahr_muster(jahr).search(text[:4000]):
        return False, "Geschäftsjahr nicht erkennbar", seiten, text
    return True, "ok", seiten, text


def dokumentart(text, url):
    s = (text[:3000] + " " + url).lower()
    if re.search(r"jahresfinanzbericht|annual financial report", s):
        return "Jahresfinanzbericht"
    if re.search(r"gesch(ä|ae)ftsbericht|annual report|integrated report|jahresbericht", s):
        return "Geschäftsbericht"
    if "konzernabschluss" in s or "consolidated financial statements" in s:
        return "Konzernabschluss"
    if "jahresabschluss" in s or "financial statements" in s:
        return "Jahresabschluss"
    return "Bericht"


def dateiname(url, cd):
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', cd or "")
    n = unquote(m.group(1) if m else urlparse(url).path.rsplit("/", 1)[-1]) or "bericht.pdf"
    n = re.sub(r"[^A-Za-z0-9._-]+", "_", n).strip("_")[:120]
    return n if n.lower().endswith(".pdf") else n + ".pdf"


def lade(e, jahr, nur_konzern=False, ohne=()):
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "application/pdf,*/*"})
    versuche = []
    for k in e.get("kandidaten", [])[:6]:
        if k["url"] in ohne:
            continue
        if k.get("punkte", 99) < 4:
            break
        try:
            r = s.get(k["url"], timeout=90)
        except Exception as ex:
            versuche.append({"url": k["url"], "grund": type(ex).__name__})
            continue
        if r.status_code != 200:
            versuche.append({"url": k["url"], "grund": f"http {r.status_code}"})
            continue
        if len(r.content) > MAX_BYTES:
            versuche.append({"url": k["url"], "grund": f"zu groß ({len(r.content) // 1_000_000} MB)"})
            continue
        if re.search(r"halbjahr|hjb|[-_]hj[-_]|h1|quartal|q[1-3][-_]|10-k", k["url"].rsplit("/", 1)[-1], re.I):
            versuche.append({"url": k["url"], "grund": "unterjährig laut Dateiname"})
            continue
        ok, grund, seiten, text = pruefe(r.content, jahr)
        if not ok:
            versuche.append({"url": k["url"], "grund": grund})
            continue
        art = dokumentart(text, k["url"])
        if nur_konzern and art == "Jahresabschluss":
            versuche.append({"url": k["url"], "grund": "nur Einzelabschluss"})
            continue
        return {"ok": True, "url": r.url if r.url.lower().endswith(".pdf") else k["url"], "daten": r.content,
                "name": dateiname(k["url"], r.headers.get("content-disposition")), "seiten": seiten,
                "art": art, "versuche": versuche}
    return {"ok": False, "versuche": versuche}


def main():
    suche = json.load(open(sys.argv[1], encoding="utf-8"))
    jahr = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--jahr=")), 2025))
    uni = {u["unternehmen_id"]: u for u in csv.DictReader(open(BASIS / "universum" / "universum.csv", encoding="utf-8-sig"), delimiter=";")}
    status_p = BASIS / "rohdaten" / "berichte_status.json"
    status = json.loads(status_p.read_text(encoding="utf-8")) if status_p.exists() else {}
    heute = date.today().strftime("%d.%m.%Y")
    neue = {}
    zweit = "--konzern" in sys.argv  # Zweitlauf: nur für Firmen, von denen bisher nur ein Einzelabschluss vorliegt
    vorhanden = {}
    for p in BASIS.glob("*/dokumente/index.csv"):
        for z in csv.DictReader(open(p, encoding="utf-8-sig"), delimiter=";"):
            vorhanden.setdefault(z["unternehmen_id"], []).append(z)
    if zweit:
        suche = [e for e in suche if e["id"] in vorhanden and all(z["dokumentart"] == "Jahresabschluss" for z in vorhanden[e["id"]])]
    else:
        suche = [e for e in suche if e["id"] not in vorhanden or "--neu" in sys.argv]
    with cf.ThreadPoolExecutor(8) as ex:
        futs = {ex.submit(lade, e, jahr, zweit, {z["quelle_url"] for z in vorhanden.get(e["id"], [])}): e
                for e in suche if e["id"] in uni}
        for f in cf.as_completed(futs):
            e, r = futs[f], f.result()
            u = uni[e["id"]]
            if not r["ok"]:
                if zweit:
                    continue
                status[e["id"]] = {"status": "nicht gefunden", "suche": e.get("status"), "versuche": r["versuche"]}
                print("--", e["id"], e.get("status"), r["versuche"][:1], flush=True)
                continue
            ziel = BASIS / u["branche"] / "dokumente" / e["id"] / r["name"]
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_bytes(r["daten"])
            sha = hashlib.sha256(r["daten"]).hexdigest()
            neue.setdefault(u["branche"], []).append({
                "unternehmen": u["name"], "unternehmen_id": e["id"], "dokumentart": r["art"], "geschaeftsjahr": str(jahr),
                "datei": str(ziel.relative_to(BASIS / u["branche"])), "status": "Originaldokument (PDF)", "quelle_url": r["url"],
                "abruf": f"Download {heute}", "sha256": sha, "seiten": r["seiten"], "bytes": len(r["daten"]),
                "verwendet_in": "", "hinweis": e.get("hinweis", ""),
            })
            status[e["id"]] = {"status": "geladen", "datei": str(ziel.relative_to(BASIS)), "url": r["url"]}
            print("OK", e["id"], r["art"], r["seiten"], r["name"], flush=True)
    for branche, zeilen in neue.items():
        p = BASIS / branche / "dokumente" / "index.csv"
        alt = list(csv.DictReader(open(p, encoding="utf-8-sig"), delimiter=";")) if p.exists() else []
        dateien = {z["datei"] for z in zeilen}
        alle = [z for z in alt if z["datei"] not in dateien] + zeilen
        alle.sort(key=lambda z: (z["unternehmen_id"], z["geschaeftsjahr"], z["datei"]))
        with open(p, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, KOPF, delimiter=";", extrasaction="ignore")
            w.writeheader()
            w.writerows(alle)
    status_p.write_text(json.dumps(status, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
