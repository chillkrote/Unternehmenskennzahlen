"""Liest die Finanzkalender der Unternehmen und schreibt bestätigte Berichtstermine nach termine/rohdaten/finanzkalender.csv.

Je Unternehmen eine Kalenderseite: entweder aus termine/finanzkalender_quellen.csv (unternehmen_id;url, von Hand gepflegt, hat Vorrang)
oder automatisch: Website laut universum.csv laden, Links mit "Finanzkalender", "Financial Calendar", "Termine" usw. folgen (höchstens
zwei Ebenen). Auf der Seite zählt jede Zeile (bzw. jedes Tabellenfeld) mit Datum und einem Berichts-Stichwort (Quartal, Q1–Q4, Halbjahr,
Zwischenbericht, Geschäftsbericht, Ergebnis, Quarter, Half-year, Interim, Annual Report, Results). Hauptversammlung, Dividenden und
Telefonkonferenzen werden verworfen. Seiten mit Bot-Schutz (403/429/Captcha) werden vermerkt und nicht umgangen.
Nur Termine ab heute minus 30 Tage. Seiten, die ihren Kalender per JavaScript nachladen, liefern nichts: dafür termine_manuell.csv.

Aufruf: python3 finanzkalender_scan.py [--nur=<id,id>]
"""
import concurrent.futures as cf
import csv
import html
import re
import sys
import time
from datetime import date, timedelta
from urllib.parse import urljoin, urlparse

import requests

import tlib

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
KALENDER_LINK = re.compile(r"finanzkalender|financial[-_ ]?calendar|finanztermine|financial[-_ ]?dates|termine|events?[-_/]|"
                           r"ir[-_/]?kalender|investor[-_ ]?calendar|calendar|kalender|veranstaltungen", re.I)
IR_LINK = re.compile(r"investor|/ir\b|/ir/|aktion[aä]r|financial|finanz", re.I)
BERICHT = re.compile(r"quartal|\bq[1-4]\b|[1-4]\.?\s?quartal|halbjahr|\bh[12]\b|9[- ]?monat|zwischen(bericht|mitteilung)|"
                     r"gesch[aä]ftsbericht|jahresfinanzbericht|jahresabschluss|ergebnis|zahlen|quarter|half[- ]year|interim|"
                     r"annual (report|results)|full[- ]year|results|nine[- ]months|trading statement", re.I)
VERWERFEN = re.compile(r"hauptversammlung|annual general meeting|\bagm\b|dividende|dividend|ex-tag|telefonkonferenz|conference call|"
                       r"capital markets day|kapitalmarkttag|roadshow|konferenz|conference|webcast|bilanzpressekonferenz.*einladung", re.I)
MONATE = {m: i + 1 for i, ms in enumerate([
    ("januar", "january", "jan", "janv"), ("februar", "february", "feb", "févr"), ("märz", "maerz", "march", "mär", "mar"),
    ("april", "apr"), ("mai", "may"), ("juni", "june", "jun"), ("juli", "july", "jul"), ("august", "aug"),
    ("september", "sep", "sept"), ("oktober", "october", "okt", "oct"), ("november", "nov"), ("dezember", "december", "dez", "dec")])
    for m in ms}
D1 = re.compile(r"(?<!\d)(\d{1,2})\.\s?(\d{1,2})\.\s?(20\d\d)(?!\d)")
D2 = re.compile(r"(?<![\w])(\d{1,2})\.?\s?(?:of\s)?([A-Za-zäÄ]{3,9})\.?,?\s+(20\d\d)(?!\d)")
D3 = re.compile(r"(?<![\w])([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d\d)(?!\d)")
D4 = re.compile(r"(?<!\d)(20\d\d)-(\d\d)-(\d\d)(?!\d)")


def daten(zeile):
    out = []
    for m in D1.finditer(zeile):
        out.append((int(m[3]), int(m[2]), int(m[1])))
    for m in D4.finditer(zeile):
        out.append((int(m[1]), int(m[2]), int(m[3])))
    for m in D2.finditer(zeile):
        if m[2].lower() in MONATE:
            out.append((int(m[3]), MONATE[m[2].lower()], int(m[1])))
    for m in D3.finditer(zeile):
        if m[1].lower() in MONATE:
            out.append((int(m[3]), MONATE[m[1].lower()], int(m[2])))
    ok = []
    for j, mo, t in out:
        try:
            ok.append(date(j, mo, t))
        except ValueError:
            pass
    return ok


def als_text(h):
    h = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", h)
    h = re.sub(r"(?i)</(tr|p|div|li|h\d|section|article|dt|dd|table|br)>|<br\s*/?>", "\n", h)
    h = re.sub(r"(?i)</(td|th|span|a)>", " | ", h)
    h = re.sub(r"<[^>]+>", " ", h)
    return [" ".join(z.split()) for z in html.unescape(h).split("\n") if z.strip()]


def termine_aus_text(zeilen, heute):
    out = {}
    for i, z in enumerate(zeilen):
        d = daten(z)
        if not d:
            continue
        # Datum und Stichwort müssen in derselben Zeile (Tabellenzeile) stehen; Folgezeilen-Kontext erzeugte zu viele Fehltreffer
        text = z if BERICHT.search(z) else None
        if not text or VERWERFEN.search(text) or len(text) > 220:
            continue
        for t in d:
            if t >= heute - timedelta(days=30) and t <= heute + timedelta(days=550):
                out[(t, text[:120])] = None
    return list(out)


def holen(s, url):
    try:
        r = s.get(url, timeout=20)
    except Exception as e:
        return None, f"fehler {type(e).__name__}"
    if r.status_code in (403, 429, 503) or re.search(r"captcha|cf-chl|are you a human|incapsula", r.text[:4000], re.I):
        return None, "gesperrt"
    if r.status_code >= 400 or "html" not in r.headers.get("content-type", ""):
        return None, f"http {r.status_code}"
    return r, "ok"


def kalenderseiten(s, start):
    """Kalender-URLs auf der Website: Startseite -> IR-/Kalender-Links (zwei Ebenen)."""
    host = urlparse(start).netloc.replace("www.", "")
    basis = ".".join(host.split(".")[-2:])
    besucht, queue, treffer = set(), [(start, 0)], []
    while queue and len(besucht) < 14:
        url, tiefe = queue.pop(0)
        if url in besucht:
            continue
        besucht.add(url)
        r, st = holen(s, url)
        if r is None:
            continue
        for m in re.finditer(r"""href\s*=\s*["']([^"'#]+)["'][^>]*>(.*?)</a>""", r.text, re.I | re.S):
            ziel = urljoin(r.url, m[1].strip())
            label = " ".join(re.sub(r"<[^>]+>", " ", m[2]).split())[:120]
            if ziel.lower().split("?")[0].endswith((".pdf", ".zip", ".xlsx", ".jpg", ".png")) or not ziel.startswith("http"):
                continue
            if basis not in urlparse(ziel).netloc:
                continue
            if KALENDER_LINK.search(ziel + " " + label) and re.search(r"finanz|financial|ir|investor|calendar|kalender|termine|aktion", ziel + label, re.I):
                if ziel not in treffer:
                    treffer.append(ziel)
            elif tiefe < 1 and IR_LINK.search(ziel + " " + label):
                queue.append((ziel, tiefe + 1))
        time.sleep(0.2)
    return treffer[:4]


def scan(uid, u, url_vorgabe, heute):
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "de-DE,de;q=0.9,en;q=0.6"})
    start = url_vorgabe or u.get("website") or ""
    if not start:
        return uid, [], "keine website"
    if not start.startswith("http"):
        start = "https://" + start
    seiten = [start] if url_vorgabe else kalenderseiten(s, start)
    gefunden, status = [], "kein Kalender gefunden" if not seiten else "keine Termine"
    for url in seiten:
        r, st = holen(s, url)
        if r is None:
            status = st
            continue
        t = termine_aus_text(als_text(r.text), heute)
        if t:
            gefunden += [(d, text, r.url) for d, text in t]
            status = "ok"
            break
    return uid, gefunden, status


def main():
    nur = set(next((x.split("=")[1] for x in sys.argv if x.startswith("--nur=")), "").split(",")) - {""}
    heute = date.today()
    uni = {k: v for k, v in tlib.unternehmen().items() if not nur or k in nur}
    vorgabe = {r["unternehmen_id"]: r["url"] for r in tlib.lese_csv(tlib.QUELLEN_FK) if r.get("url")}
    zeilen, bericht = [], {}
    with cf.ThreadPoolExecutor(8) as ex:
        futs = [ex.submit(scan, k, v, vorgabe.get(k), heute) for k, v in uni.items() if v.get("website") or k in vorgabe]
        for f in cf.as_completed(futs):
            uid, gefunden, status = f.result()
            bericht[uid] = status
            u = uni[uid]
            fye = tlib.geschaeftsjahresende_monat(uid, u["isin"])
            for d, text, url in gefunden:
                ende, art = tlib.periode(d, fye)
                if re.search(r"gesch[aä]ftsbericht|annual report|jahresfinanzbericht", text, re.I):
                    art = "Jahresbericht" if ende and ende.month == fye else art
                zeilen.append({"unternehmen_id": uid, "berichtsart": art, "periode_ende": ende.isoformat() if ende else "",
                               "termin": d.isoformat(), "status": "bestätigt", "quelle_url": url, "hinweis": f"Finanzkalender: {text}"})
    ziel = tlib.TERMINE / "rohdaten" / "finanzkalender.csv"
    ziel.parent.mkdir(exist_ok=True)
    kopf = ["unternehmen_id", "berichtsart", "periode_ende", "termin", "status", "quelle_url", "hinweis"]
    if nur and ziel.exists():  # Teillauf: andere Unternehmen behalten
        zeilen += [r for r in tlib.lese_csv(ziel) if r["unternehmen_id"] not in nur]
    zeilen.sort(key=lambda z: (z["unternehmen_id"], z["termin"]))
    with open(ziel, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, kopf, delimiter=";")
        w.writeheader()
        w.writerows(zeilen)
    stat = {}
    for st in bericht.values():
        stat[st] = stat.get(st, 0) + 1
    (tlib.TERMINE / "rohdaten" / "finanzkalender_status.json").write_text(
        __import__("json").dumps(bericht, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(f"{len(zeilen)} Termine; Seitenstatus: {stat}")


if __name__ == "__main__":
    main()
