"""Börse & Finanzen, Welle 2: Inflation, Realzins, Staatsverschuldung, Börsenwert/BIP, Renditeaufschläge und Bankensektor.
Erzeugt data/finanz_makro.json. Alles kostenlos und ohne Schlüssel:
 - inflation: Verbraucherpreise, Veränderung zum Vorjahr, monatlich, rund 45 Länder (OECD, Preisstatistik; CC BY 4.0).
 - realzins: Leitzins (BIS) und 10-jährige Rendite (OECD) abzüglich der jüngsten Inflationsrate, aus data/boerse_welt.json gerechnet.
 - schulden, defizit, boersenwert_bip: Weltbank (Zentralstaatsschuld, Finanzierungssaldo des Zentralstaats, Börsenwert in % des BIP),
   jeweils letzter verfügbarer Jahreswert je Land (CC BY 4.0). Die Weltbank-Reihen sind lückenhaft und hinken ein bis zwei Jahre.
 - aufschlag: Rendite 10 Jahre minus Bund, Euro-Länder auch als Verlauf. Ersatz für CDS, die nicht kostenlos verfügbar sind.
 - bankensektor: EZB, Supervisory Banking Statistics (bedeutende Institute je Land, vierteljährlich): CET1-Quote, Eigenkapitalrendite,
   Aufwand-Ertrags-Quote, Quote notleidender Kredite, Liquiditätsdeckung, Verschuldungsquote.
Eine Quelle, die ausfällt, behält ihren alten Stand.

    python3 app/finanz_makro.py
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
ZIEL = HIER / "data/finanz_makro.json"
UA = {"User-Agent": "Unternehmenskennzahlen/1.0"}
OECD_CPI = ("https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0/.M.N.CPI.PA._T.N.GY?startPeriod={}"
            "&dimensionAtObservation=AllDimensions&format=csvfile")
WB = "https://api.worldbank.org/v2/country/all/indicator/{}?format=json&per_page=400&mrnev=1"
WB_REIHEN = {"schulden": ("GC.DOD.TOTL.GD.ZS", "Schuldenstand des Zentralstaats, % des BIP"),
             "defizit": ("GC.NLD.TOTL.GD.ZS", "Finanzierungssaldo des Zentralstaats, % des BIP"),
             "boersenwert_bip": ("CM.MKT.LCAP.GD.ZS", "Börsenwert der inländischen Unternehmen, % des BIP")}
SUP = "https://data-api.ecb.europa.eu/service/data/SUP/Q..W0._Z.{}._T.SII._Z._Z._Z.PCT.C?lastNObservations=8&format=csvdata"
SUP_ITEMS = {"I4008": ("cet1", "CET1-Quote"), "I2003": ("roe", "Eigenkapitalrendite"), "I2100": ("cir", "Aufwand-Ertrags-Quote"),
             "I7005": ("npl", "Quote notleidender Kredite"), "I3017": ("lcr", "Liquiditätsdeckung (LCR)"), "KSV13": ("lev", "Verschuldungsquote")}
EURO = {"AT", "BE", "BG", "CY", "DE", "EE", "ES", "FI", "FR", "GR", "HR", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PT", "SI", "SK"}
SUP_LAND = {"GR": "GR", "EL": "GR"}  # die EZB schreibt Griechenland GR


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


def inflation(a3):
    start = f"{date.today().year - 2}-01"
    out = {}
    for z in csv.DictReader(io.StringIO(text(OECD_CPI.format(start)))):
        iso = a3.get(z["REF_AREA"], "XM" if z["REF_AREA"] == "EA20" else None)
        if iso and z["OBS_VALUE"] not in ("", "NaN"):
            out.setdefault(iso, {})[z["TIME_PERIOD"]] = float(z["OBS_VALUE"])
    res = {}
    for iso, d in out.items():
        l = sorted(d.items())
        res[iso] = {"v": round(l[-1][1], 2), "zeit": l[-1][0], "l": [[t, round(v, 2)] for t, v in l[-24:]]}
    return res


def weltbank(kennung, a3):
    d = json.loads(text(WB.format(kennung)))
    out = {}
    for x in d[1] or []:
        iso = a3.get(x.get("countryiso3code"))
        # veraltete Weltbank-Werte (älter als sieben Jahre) würden ein falsches Bild geben und fehlen lieber
        if iso and x["value"] is not None and int(x["date"]) >= date.today().year - 7:
            out[iso] = {"v": round(x["value"], 2), "jahr": x["date"]}
    return out


def letzt(reihe):
    return (reihe[-1][0], reihe[-1][1]) if reihe else (None, None)


def realzins(bw, infl):
    out = {}
    for iso, i in infl.items():
        lz = bw.get("leitzins", {}).get(iso) or (bw.get("leitzins", {}).get("XM") if iso in EURO else None)
        r10 = bw.get("rendite10", {}).get(iso)
        if iso == "XM":
            lz, r10 = bw.get("leitzins", {}).get("XM"), bw.get("rendite10", {}).get("XM")
        e = {"infl": i["v"], "zeit_infl": i["zeit"]}
        if lz:
            t, v = letzt(lz)
            e.update({"leit": round(v, 2), "zeit_leit": t, "real": round(v - i["v"], 2)})
        if r10:
            t, v = letzt(r10)
            e.update({"rend": round(v, 2), "zeit_rend": t, "real10": round(v - i["v"], 2)})
        if "real" in e or "real10" in e:
            out[iso] = e
    return out


def aufschlag(bw):
    r = bw.get("rendite10", {})
    de = dict(r.get("DE", []))
    if not de:
        return {}
    neu = max(t for t, _ in r["DE"])
    out = {}
    for iso, l in r.items():
        if iso in ("DE", "XM"):
            continue
        gem = [(t, round(v - de[t], 3)) for t, v in l if t in de]
        if not gem:
            continue
        if gem[-1][0] < f"{int(neu[:4]) - 1}-{neu[5:7]}":
            continue  # Reihe endet vor mehr als einem Jahr (z. B. Russland): kein aktueller Aufschlag
        e = {"v": gem[-1][1], "zeit": gem[-1][0], "rend": round(l[-1][1], 2)}
        if iso in EURO or iso in ("GB", "CH", "SE", "DK", "NO", "PL", "CZ", "HU", "US"):
            e["l"] = [[t, v] for t, v in gem[-60:]]
        out[iso] = e
    return out


def bankensektor():
    items = "+".join(SUP_ITEMS)
    out = {}
    for z in csv.DictReader(io.StringIO(text(SUP.format(items)))):
        if z["OBS_VALUE"] in ("", "NaN"):
            continue
        land = z["REF_AREA"]
        land = "SSM" if land == "B01" else SUP_LAND.get(land, land)
        if len(land) != 2 and land != "SSM":
            continue
        k = SUP_ITEMS.get(z["CB_ITEM"])
        if k:
            out.setdefault(land, {}).setdefault(k[0], {})[z["TIME_PERIOD"]] = float(z["OBS_VALUE"])
    res = {}
    for land, d in out.items():
        e = {}
        for k, reihe in d.items():
            l = sorted(reihe.items())
            e[k] = {"v": round(l[-1][1], 2), "zeit": l[-1][0], "l": [[t, round(v, 2)] for t, v in l]}
        res[land] = e
    return res


def main():
    feat = json.loads((HIER / "geo/laender.geojson").read_text())["features"]
    a3 = {f["properties"]["a3"]: f["properties"]["iso"] for f in feat if f["properties"].get("a3")}
    alt = json.loads(ZIEL.read_text()) if ZIEL.exists() else {}
    bw = json.loads((HIER / "data/boerse_welt.json").read_text()) if (HIER / "data/boerse_welt.json").exists() else {}
    bw = {k: {i: l for i, l in (bw.get(k) or {}).items()} for k in ("leitzins", "rendite10")}
    out = {"abruf": date.today().isoformat(), "quellen": {
        "inflation": {"name": "OECD, Verbraucherpreise (CPI), Veränderung zum Vorjahr, CC BY 4.0", "url": "https://data-explorer.oecd.org/"},
        "realzins": {"name": "Leitzins (BIS) beziehungsweise 10-jährige Rendite (OECD) minus jüngste Inflationsrate; gerechnet", "url": "https://data.bis.org/topics/CBPOL"},
        "aufschlag": {"name": "Rendite 10 Jahre (OECD) minus Rendite Deutschland; Ersatz für CDS, die nicht kostenlos verfügbar sind", "url": "https://data-explorer.oecd.org/"},
        "bankensektor": {"name": "EZB, Supervisory Banking Statistics, bedeutende Institute je Land, viertelj.", "url": "https://data.ecb.europa.eu/data/datasets/SUP"},
        **{k: {"name": f"Weltbank, {n}, letzter Jahreswert, CC BY 4.0", "url": f"https://data.worldbank.org/indicator/{kz}"} for k, (kz, n) in WB_REIHEN.items()}}}
    schritte = [("inflation", lambda: inflation(a3)), ("aufschlag", lambda: aufschlag(bw)), ("bankensektor", bankensektor)]
    schritte += [(k, (lambda kz=kz: weltbank(kz, a3))) for k, (kz, _) in WB_REIHEN.items()]
    for kurz, f in schritte:
        try:
            out[kurz] = f()
            if not out[kurz] and alt.get(kurz):
                out[kurz] = alt[kurz]
                print(f"{kurz} leer, alter Stand bleibt", file=sys.stderr)
            print(f"  {kurz}: {len(out[kurz])}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"{kurz} nicht abrufbar, alter Stand bleibt:", e, file=sys.stderr)
            out[kurz] = alt.get(kurz, {})
    out["realzins"] = realzins(bw, out.get("inflation", {}))
    print(f"  realzins: {len(out['realzins'])}", file=sys.stderr)
    ZIEL.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"{ZIEL}: {len(out['inflation'])} Inflationsreihen, {len(out['bankensektor'])} Bankensektoren", file=sys.stderr)


if __name__ == "__main__":
    main()
