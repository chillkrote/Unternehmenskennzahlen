"""Weltkugel, Darstellungsform Börse & Finanzen: erzeugt data/boerse_welt.json.

Inhalt (alles kostenlos und ohne Schlüssel):
 - plaetze: Börsenplätze mit Lage und Leitindex aus app/geo/boersenplaetze.csv (von Hand gepflegt); die Kurse selbst kommen
   aus data/boerse.json (Bereich BÖR, Yahoo Finance) und werden erst im Browser zugeordnet.
 - leitzins: Leitzinsen der Zentralbanken, Monatsende, zehn Jahre (BIS Central bank policy rates, WS_CBPOL; Nutzung mit
   Quellenangabe, https://www.bis.org/terms_statistics.htm). Euroraum unter "XM".
 - rendite10: Rendite langfristiger Staatsanleihen (in der Regel 10 Jahre), Monatswerte, zehn Jahre
   (OECD Financial market statistics, IRLT; CC BY 4.0).
 - devisen: Referenzkurse der EZB gegen den Euro (täglich), daraus Veränderung zum US-Dollar.
 - rohstoffe: Brent, WTI, Erdgas Henry Hub (täglich), Kupfer und Weizen (monatlich, IMF-Preise) über FRED.

    python3 app/boerse_welt.py
"""
import csv
import io
import json
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

HIER = Path(__file__).resolve().parent
ZIEL = HIER / "data/boerse_welt.json"
UA = {"User-Agent": "Unternehmenskennzahlen/1.0"}
BIS = "https://stats.bis.org/api/v1/data/WS_CBPOL/M.?startPeriod={}&format=csv"
OECD = ("https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_FINMARK,4.0/.M.IRLT.PA.....?startPeriod={}"
        "&dimensionAtObservation=AllDimensions&format=csvfile")
EZB = "https://data-api.ecb.europa.eu/service/data/EXR/D.{}.EUR.SP00.A?startPeriod={}&format=csvdata"
WAEHRUNGEN = ["USD", "GBP", "JPY", "CNY", "CHF", "INR", "BRL", "KRW", "AUD", "CAD", "SEK", "NOK", "PLN", "TRY", "ZAR", "MXN", "HKD", "SGD"]
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
ROHSTOFFE = [("DCOILBRENTEU", "Rohöl Brent", "USD je Barrel"), ("DCOILWTICO", "Rohöl WTI", "USD je Barrel"),
             ("DHHNGSP", "Erdgas Henry Hub", "USD je MMBtu"), ("PCOPPUSDM", "Kupfer", "USD je Tonne"),
             ("PWHEAMTUSDM", "Weizen", "USD je Tonne")]


def text(url, versuche=4):
    for i in range(versuche):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return r.read().decode("utf-8")
        except Exception as e:  # noqa: BLE001
            if i == versuche - 1:
                raise
            print("  Wiederholung", url[:90], e, file=sys.stderr)
            time.sleep(5 * (i + 1))


def zeilen(url):
    return list(csv.DictReader(io.StringIO(text(url))))


def reihe_kurz(werte, n=120):
    return [[z, round(v, 3)] for z, v in sorted(werte.items())[-n:]]


def leitzinsen(start):
    out = {}
    for z in zeilen(BIS.format(start)):
        if z["OBS_VALUE"] in ("", "NaN"):
            continue
        out.setdefault(z["REF_AREA"], {})[z["TIME_PERIOD"]] = float(z["OBS_VALUE"])
    return {k: reihe_kurz(v) for k, v in out.items()}


def renditen(start, a3_nach_iso):
    out = {}
    for z in zeilen(OECD.format(start)):
        iso = a3_nach_iso.get(z["REF_AREA"], "XM" if z["REF_AREA"] == "EA20" else None)
        if not iso or z["OBS_VALUE"] == "":
            continue
        out.setdefault(iso, {})[z["TIME_PERIOD"]] = float(z["OBS_VALUE"])
    return {k: reihe_kurz(v) for k, v in out.items()}


def devisen(start):
    kurse = {}
    for w in WAEHRUNGEN:
        kurse[w] = {z["TIME_PERIOD"]: float(z["OBS_VALUE"]) for z in zeilen(EZB.format(w, start)) if z["OBS_VALUE"]}
        time.sleep(.3)
    usd = kurse["USD"]
    jahr = str(date.today().year)
    out = {}
    for w, k in kurse.items():
        tage = sorted(k)
        if not tage:
            continue
        letzt = tage[-1]
        vj = [t for t in tage if t < jahr]
        basis = vj[-1] if vj else tage[0]
        j1 = [t for t in tage if t <= str(int(letzt[:4]) - 1) + letzt[4:]]
        # Wert der Währung in US-Dollar: (USD je EUR) / (Währung je EUR); Veränderung > 0 = Währung hat zum Dollar gewonnen
        in_usd = lambda t: usd[t] / k[t] if t in usd else None  # noqa: E731
        def aend(t):
            a, b = in_usd(letzt), in_usd(t) if t else None
            return round(a / b - 1, 5) if a and b else None
        out[w] = {"je_eur": k[letzt], "datum": letzt, "usd_ytd": aend(basis), "usd_1j": aend(j1[-1] if j1 else None),
                  "eur_ytd": round(k[basis] / k[letzt] - 1, 5) if w != "EUR" else None,
                  "verlauf": [[t, k[t]] for t in tage[-260::5]]}
    return out


def rohstoffe():
    out = []
    for sid, name, einheit in ROHSTOFFE:
        try:
            z = [l.split(",") for l in text(FRED.format(sid)).strip().splitlines()[1:]]
        except Exception as e:  # noqa: BLE001
            print("  FRED", sid, e, file=sys.stderr)
            continue
        w = [(d, float(v)) for d, v in z if v not in ("", ".")]
        if not w:
            continue
        d, v = w[-1]
        jahr = [x for x in w if x[0] < d[:4]]
        vor = [x for x in w if x[0] <= str(int(d[:4]) - 1) + d[4:]]
        out.append({"id": sid, "name": name, "einheit": einheit, "wert": round(v, 2), "datum": d,
                    "ytd": round(v / jahr[-1][1] - 1, 4) if jahr else None, "r1j": round(v / vor[-1][1] - 1, 4) if vor else None,
                    "verlauf": [[x[0], round(x[1], 2)] for x in (w[-260::5] if len(w) > 400 else w[-60:])],
                    "url": f"https://fred.stlouisfed.org/series/{sid}"})
        time.sleep(1)
    return out


def main():
    feat = json.loads((HIER / "geo/laender.geojson").read_text())["features"]
    a3 = {f["properties"]["a3"]: f["properties"]["iso"] for f in feat if f["properties"].get("a3")}
    alt = json.loads(ZIEL.read_text()) if ZIEL.exists() else {}
    start = str(date.today().year - 10)
    out = {"abruf": date.today().isoformat(), "plaetze": list(csv.DictReader(open(HIER / "geo/boersenplaetze.csv", encoding="utf-8"))),
           "quellen": {
               "leitzins": {"name": "BIS, Central bank policy rates (WS_CBPOL), Monatsende", "url": "https://data.bis.org/topics/CBPOL"},
               "rendite10": {"name": "OECD, Langfristige Zinsen (IRLT, Staatsanleihen meist 10 Jahre), CC BY 4.0",
                             "url": "https://data-explorer.oecd.org/"},
               "devisen": {"name": "EZB, Euro-Referenzkurse", "url": "https://data.ecb.europa.eu/data/datasets/EXR"},
               "rohstoffe": {"name": "FRED (EIA-Ölpreise und Erdgas, IMF-Rohstoffpreise)", "url": "https://fred.stlouisfed.org/"}}}
    for kurz, f in (("leitzins", lambda: leitzinsen(start + "-01")), ("rendite10", lambda: renditen(start + "-01", a3)),
                    ("devisen", lambda: devisen(f"{date.today().year - 1}-01-01")), ("rohstoffe", rohstoffe)):
        try:
            out[kurz] = f()
            print(f"  {kurz}: {len(out[kurz])}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"{kurz} nicht abrufbar, alter Stand bleibt:", e, file=sys.stderr)
            out[kurz] = alt.get(kurz, {} if kurz != "rohstoffe" else [])
    ZIEL.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"{ZIEL}: {len(out['plaetze'])} Börsenplätze, {len(out['leitzins'])} Leitzinsen, {len(out['rendite10'])} Renditen", file=sys.stderr)


if __name__ == "__main__":
    main()
