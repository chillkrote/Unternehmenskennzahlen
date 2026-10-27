"""Erfasst die Veröffentlichungstermine von Quartals-, Halbjahres- und Jahresberichten und schreibt termine/termine.csv.

Quellen (nach Rang, höher gewinnt):
  1. yahoo          yfinance Ticker.get_earnings_dates()/calendar: kostenlos, deckt fast alle Börsenwerte ab, Termine in der Zukunft
                    sind meist Schätzungen (Status "erwartet"); vergangene Termine mit gemeldetem Ergebnis gelten als "erschienen".
  2. finanzkalender finanzkalender_scan.py liest die Finanzkalender-Seiten der Unternehmen (finanzkalender_quellen.csv), Status "bestätigt".
  3. manuell        termine_manuell.csv, von Hand gepflegt (bestätigte Termine aus IR-Kalendern, Börsen-Kalender), Status "bestätigt".

Je Bericht (Unternehmen + Periodenende + Berichtsart) bleibt ein Eintrag. Der Abrufstand (abruf_status, versuche, datei, sha256)
aus früheren Läufen bleibt erhalten. Termine älter als --rueck Tage und ohne Abrufstand werden nicht neu aufgenommen.

Aufruf: python3 termine_erfassen.py [--rueck=45] [--nur=<id,id>] [--ohne-yahoo]
"""
import concurrent.futures as cf
import sys
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import tlib

BERLIN = ZoneInfo("Europe/Berlin")


def yahoo_termine(uid, u):
    import yfinance as yf
    t = yf.Ticker(u["ticker"])
    for versuch in range(3):
        try:
            df = t.get_earnings_dates(limit=16)
            break
        except Exception:
            df, _ = None, time.sleep(2 * (versuch + 1))
    out = []
    if df is None or df.empty:
        return out
    for ts, r in df.iterrows():
        tag = ts.tz_convert(BERLIN).date() if ts.tzinfo else ts.date()
        # Yahoo-Zeitstempel stehen in US-Zeit: 0-Uhr-Stempel New York wird in Berlin zum Vortagabend bzw. gleichen Tag, daher auf das Datum in New York runden
        tag_ny = ts.date()
        if ts.tzinfo and ts.hour < 6:
            tag = tag_ny
        gemeldet = r.get("Reported EPS") == r.get("Reported EPS") and r.get("Reported EPS") is not None
        out.append({"termin": tag, "erschienen": bool(gemeldet)})
    return out


def lese_zusatz(pfad, quelle):
    out = []
    for r in tlib.lese_csv(pfad):
        if not r.get("unternehmen_id") or not r.get("termin"):
            continue
        r["quelle"] = r.get("quelle") or quelle
        out.append(r)
    return out


def main():
    a = sys.argv[1:]
    rueck = int(next((x.split("=")[1] for x in a if x.startswith("--rueck=")), 45))
    nur = set(next((x.split("=")[1] for x in a if x.startswith("--nur=")), "").split(",")) - {""}
    heute = date.today()
    uni = {k: v for k, v in tlib.unternehmen().items() if not nur or k in nur}
    alt = {(z["unternehmen_id"], z["periode_ende"], z["berichtsart"]): z for z in tlib.lese_csv(tlib.CSV_PFAD)}
    neu = {}

    def eintrag(uid, u, termin, quelle, status, url="", hinweis="", art=None, ende=None):
        fye = tlib.geschaeftsjahresende_monat(uid, u["isin"])
        e, ba = tlib.periode(termin, fye)
        e = ende or e
        schl = (uid, e.isoformat() if e else "", art or ba)
        z = {"unternehmen_id": uid, "name": u["name"], "branche": u["branche"], "ticker": u["ticker"], "berichtsart": art or ba,
             "periode_ende": schl[1], "termin": termin.isoformat(), "quelle": quelle, "quelle_url": url, "status": status,
             "stand": heute.isoformat(), "hinweis": hinweis}
        if schl in neu and tlib.RANG[neu[schl]["quelle"]] > tlib.RANG[quelle]:
            return
        neu[schl] = z

    if "--ohne-yahoo" not in a:
        with cf.ThreadPoolExecutor(4) as ex:
            futs = {ex.submit(yahoo_termine, k, v): k for k, v in uni.items()}
            for f in cf.as_completed(futs):
                uid = futs[f]
                try:
                    termine = f.result()
                except Exception as e:
                    print("Yahoo-Fehler", uid, type(e).__name__, flush=True)
                    continue
                for t in termine:
                    if (heute - t["termin"]).days > rueck:
                        continue
                    eintrag(uid, uni[uid], t["termin"], "yahoo", "erschienen" if t["erschienen"] and t["termin"] <= heute else "erwartet",
                            hinweis="Yahoo-Finance-Kalender; Zukunftstermine sind Schätzungen")
    for quelle, pfad in (("finanzkalender", tlib.TERMINE / "rohdaten" / "finanzkalender.csv"), ("manuell", tlib.MANUELL)):
        for r in lese_zusatz(pfad, quelle):
            uid = r["unternehmen_id"]
            if uid not in uni:
                continue
            try:
                termin = date.fromisoformat(r["termin"])
                ende = date.fromisoformat(r["periode_ende"]) if r.get("periode_ende") else None
            except ValueError:
                continue
            eintrag(uid, uni[uid], termin, quelle, r.get("status") or "bestätigt", r.get("quelle_url", ""), r.get("hinweis", ""),
                    r.get("berichtsart") or None, ende)
    # Ein bestätigter Termin ersetzt die Yahoo-Schätzung desselben Berichts auch dann, wenn die Periodenableitung abwich:
    # liegt ein bestätigter Termin höchstens 20 Tage vom geschätzten entfernt, fällt die Schätzung weg.
    bestaetigt = [z for z in neu.values() if z["quelle"] != "yahoo"]
    for k, z in list(neu.items()):
        if z["quelle"] == "yahoo" and any(b["unternehmen_id"] == z["unternehmen_id"] and
                                           abs((date.fromisoformat(b["termin"]) - date.fromisoformat(z["termin"])).days) <= 20 for b in bestaetigt):
            del neu[k]
    # Abrufstand übernehmen; frühere Einträge, die nicht mehr geliefert werden, bleiben nur mit Abrufstand erhalten
    for k, z in neu.items():
        o = alt.get(k)
        if o:
            for f in ("abruf_status", "versuche", "datei", "sha256"):
                z[f] = o.get(f, "")
            if o.get("status") == "erschienen" and z["status"] == "erwartet":
                z["status"] = "erschienen"
            if o.get("termin") != z["termin"]:
                z["hinweis"] = (z["hinweis"] + f" Termin verschoben (vorher {o.get('termin')})").strip()
    for k, o in alt.items():
        if k not in neu and ("--ohne-yahoo" in a and o.get("quelle") == "yahoo" or o.get("datei") or o.get("abruf_status") == "geladen" or
                              (o.get("quelle") != "yahoo" and date.fromisoformat(o["termin"]) >= heute - timedelta(days=rueck))):
            neu[k] = o
    if nur:  # Teillauf: übrige Einträge unverändert lassen
        for k, o in alt.items():
            if o["unternehmen_id"] not in nur:
                neu.setdefault(k, o)
    tlib.schreibe_termine(list(neu.values()))
    zukunft = [z for z in neu.values() if z["termin"] >= heute.isoformat()]
    print(f"{len(neu)} Termine, davon {len(zukunft)} ab heute, für {len({z['unternehmen_id'] for z in neu.values()})} Unternehmen")


if __name__ == "__main__":
    main()
