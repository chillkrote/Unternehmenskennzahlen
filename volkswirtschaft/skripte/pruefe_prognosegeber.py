"""Prüft die URLs in prognosegeber_oecd.csv auf Erreichbarkeit und schreibt http_status und geprueft zurück.

Es wird nur ein einfacher GET mit offenem User-Agent gesendet. Bot-Sperren (403/429/JS-Challenge) werden
nicht umgangen, sondern als Status vermerkt. Geprüft wird nur die URL, nicht der Inhalt der Seite.
"""
import csv, ssl, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

DATEI = Path(__file__).resolve().parent.parent / "prognosegeber_oecd.csv"
UA = "Mozilla/5.0 (compatible; Unternehmenskennzahlen-Linkcheck; +https://github.com/chillkrote/Unternehmenskennzahlen)"


def status(url):
    if not url:
        return ""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=25, context=ssl.create_default_context()) as r:
            r.read(2048)
            return str(r.status)
    except urllib.error.HTTPError as e:
        return str(e.code)
    except Exception as e:
        return "Fehler: " + type(e).__name__


def main():
    with open(DATEI, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    felder = [k for k in rows[0] if k not in ("http_status_url", "http_status_daten", "geprueft")]
    urls = sorted({r[k] for r in rows for k in ("url", "daten_url") if r[k]})
    with ThreadPoolExecutor(12) as ex:
        st = dict(zip(urls, ex.map(status, urls)))
    heute = date.today().isoformat()
    for r in rows:
        r["http_status_url"] = st.get(r["url"], "")
        r["http_status_daten"] = st.get(r["daten_url"], "")
        r["geprueft"] = heute
    with open(DATEI, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, felder + ["http_status_url", "http_status_daten", "geprueft"])
        w.writeheader()
        w.writerows(rows)
    z = {}
    for v in st.values():
        z[v] = z.get(v, 0) + 1
    print(len(urls), "URLs", dict(sorted(z.items())))


if __name__ == "__main__":
    main()
