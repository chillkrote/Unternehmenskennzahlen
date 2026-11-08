"""Börse & Finanzen, Marktpuls, Zinsstrukturkurven und Währungen: erzeugt data/finanz.json.

Alles kostenlos und ohne Schlüssel:
 - puls: Stimmungs- und Preisgrößen (VIX, VXN, OVX, GVZ, MOVE, Gold, Silber, Brent, Dollar-Index, Bitcoin, Ether) über
   Yahoo Finance (yfinance, wie Bereich BÖR), dazu EUR/USD (EZB), Zinsabstand 2J/10J der USA (US-Treasury),
   Zinsabstand 2J/10J im Euroraum und EZB-Stressindex CISS.
 - kurven: Zinsstrukturkurve Euroraum (EZB, AAA-Staatsanleihen, Svensson-Kurve) und USA (US-Treasury, Par Yield Curve) für
   heute, vor einem Monat und vor einem Jahr.
 - waehrungen: alle EZB-Referenzkurse gegen den Euro, Monatswerte über zehn Jahre.
Eine Quelle, die ausfällt, behält ihren alten Stand (nie Fehlwerte). VSTOXX und VDAX sind bei Yahoo nicht frei verfügbar.

    python3 app/finanz_abruf.py
"""
import csv
import io
import json
import sys
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

HIER = Path(__file__).resolve().parent
ZIEL = HIER / "data/finanz.json"
UA = {"User-Agent": "Unternehmenskennzahlen/1.0"}
EZB = "https://data-api.ecb.europa.eu/service/data/"
TREASURY = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{j}/all"
            "?type=daily_treasury_yield_curve&field_tdr_date_value={j}&page&_format=csv")

# (id, Name, Yahoo-Symbol, Einheit, Gruppe)
YAHOO = [("vix", "VIX (S&P 500, implizite Schwankung)", "^VIX", "Punkte", "angst"), ("vxn", "VXN (Nasdaq 100)", "^VXN", "Punkte", "angst"),
         ("ovx", "OVX (Rohöl)", "^OVX", "Punkte", "angst"), ("gvz", "GVZ (Gold)", "^GVZ", "Punkte", "angst"),
         ("move", "MOVE (US-Anleihen)", "^MOVE", "Punkte", "angst"), ("gold", "Gold", "GC=F", "USD je Unze", "rohstoff"),
         ("silber", "Silber", "SI=F", "USD je Unze", "rohstoff"), ("brent", "Rohöl Brent", "BZ=F", "USD je Barrel", "rohstoff"),
         ("dxy", "US-Dollar-Index", "DX-Y.NYB", "Punkte", "devise"), ("btc", "Bitcoin", "BTC-USD", "USD", "krypto"),
         ("eth", "Ether", "ETH-USD", "USD", "krypto")]
NAMEN = {"USD": "US-Dollar", "JPY": "Japanischer Yen", "BGN": "Bulgarischer Lew", "CZK": "Tschechische Krone", "DKK": "Dänische Krone",
         "GBP": "Britisches Pfund", "HUF": "Ungarischer Forint", "PLN": "Polnischer Zloty", "RON": "Rumänischer Leu", "SEK": "Schwedische Krone",
         "CHF": "Schweizer Franken", "ISK": "Isländische Krone", "NOK": "Norwegische Krone", "TRY": "Türkische Lira", "AUD": "Australischer Dollar",
         "BRL": "Brasilianischer Real", "CAD": "Kanadischer Dollar", "CNY": "Chinesischer Renminbi", "HKD": "Hongkong-Dollar", "IDR": "Indonesische Rupiah",
         "ILS": "Israelischer Schekel", "INR": "Indische Rupie", "KRW": "Südkoreanischer Won", "MXN": "Mexikanischer Peso", "MYR": "Malaysischer Ringgit",
         "NZD": "Neuseeland-Dollar", "PHP": "Philippinischer Peso", "SGD": "Singapur-Dollar", "THB": "Thailändischer Baht", "ZAR": "Südafrikanischer Rand",
         "HRK": "Kroatische Kuna"}
EZB_LZ = [("SR_3M", .25, "3 M"), ("SR_6M", .5, "6 M"), ("SR_1Y", 1, "1 J"), ("SR_2Y", 2, "2 J"), ("SR_3Y", 3, "3 J"), ("SR_5Y", 5, "5 J"),
          ("SR_7Y", 7, "7 J"), ("SR_10Y", 10, "10 J"), ("SR_15Y", 15, "15 J"), ("SR_20Y", 20, "20 J"), ("SR_30Y", 30, "30 J")]
US_LZ = [("3 Mo", .25, "3 M"), ("6 Mo", .5, "6 M"), ("1 Yr", 1, "1 J"), ("2 Yr", 2, "2 J"), ("3 Yr", 3, "3 J"), ("5 Yr", 5, "5 J"),
         ("7 Yr", 7, "7 J"), ("10 Yr", 10, "10 J"), ("20 Yr", 20, "20 J"), ("30 Yr", 30, "30 J")]


def text(url, versuche=4):
    for i in range(versuche):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return r.read().decode("utf-8")
        except Exception as e:  # noqa: BLE001
            if i == versuche - 1:
                raise
            print("  Wiederholung", url[:90], e, file=sys.stderr)
            time.sleep(4 * (i + 1))


def zeilen(url):
    return list(csv.DictReader(io.StringIO(text(url))))


def bis(reihe, tag):
    """Letzter Eintrag der nach Datum sortierten Liste [(datum, wert)] bis einschließlich tag."""
    z = [x for x in reihe if x[0] <= tag]
    return z[-1] if z else None


def vor(tag, tage):
    return (date.fromisoformat(tag) - timedelta(days=tage)).isoformat()


def kurzreihe(reihe, n=130):
    """Höchstens n Punkte: bei langen Reihen gleichmäßig ausgedünnt, der letzte Wert bleibt."""
    if len(reihe) <= n:
        return [[d, round(v, 4)] for d, v in reihe]
    schritt = len(reihe) / n
    idx = sorted({int(i * schritt) for i in range(n)} | {len(reihe) - 1})
    return [[reihe[i][0], round(reihe[i][1], 4)] for i in idx]


def aend(reihe, tage):
    """Relative Veränderung des letzten Werts gegenüber dem Wert vor `tage` Tagen."""
    if len(reihe) < 2:
        return None
    d, v = reihe[-1]
    a = bis(reihe, vor(d, tage))
    return round(v / a[1] - 1, 5) if a and a[1] else None


def ytd(reihe):
    d, v = reihe[-1]
    a = bis(reihe, f"{int(d[:4]) - 1}-12-31")
    return round(v / a[1] - 1, 5) if a and a[1] else None


def yahoo(alt):
    import yfinance as yf
    out = []
    alt = {x["id"]: x for x in alt}
    for sid, name, sym, einheit, gruppe in YAHOO:
        try:
            h = yf.Ticker(sym).history(period="2y", interval="1d", auto_adjust=False)["Close"].dropna()
            reihe = [(i.strftime("%Y-%m-%d"), float(v)) for i, v in h.items()]
            if len(reihe) < 20:
                raise ValueError("zu wenige Werte")
        except Exception as e:  # noqa: BLE001
            print("  Yahoo", sym, e, "- alter Stand bleibt" if sid in alt else "", file=sys.stderr)
            if sid in alt:
                out.append(alt[sid])
            continue
        d, v = reihe[-1]
        out.append({"id": sid, "name": name, "gruppe": gruppe, "einheit": einheit, "wert": round(v, 2), "datum": d, "r1t": aend(reihe, 1),
                    "r1m": aend(reihe, 30), "ytd": ytd(reihe), "r1j": aend(reihe, 365), "verlauf": kurzreihe(reihe[-260:]),
                    "quelle": "Yahoo Finance", "url": f"https://finance.yahoo.com/quote/{sym}"})
        time.sleep(.5)
    return out


def ezb_kurve():
    schluessel = "+".join(k for k, _, _ in EZB_LZ)
    start = vor(date.today().isoformat(), 430)
    z = zeilen(f"{EZB}YC/B.U2.EUR.4F.G_N_A.SV_C_YM.{schluessel}?startPeriod={start}&format=csvdata")
    je = {}
    for r in z:
        if r["OBS_VALUE"]:
            je.setdefault(r["DATA_TYPE_FM"], []).append((r["TIME_PERIOD"], float(r["OBS_VALUE"])))
    for k in je:
        je[k].sort()
    if "SR_10Y" not in je:
        raise ValueError("keine 10-Jahres-Rendite")
    letzt = je["SR_10Y"][-1][0]

    def stand(tag):
        out = []
        for k, lz, lab in EZB_LZ:
            a = bis(je.get(k, []), tag)
            if a:
                out.append(round(a[1], 3))
            else:
                out.append(None)
        return out
    d1, d2 = vor(letzt, 30), vor(letzt, 365)
    zeiten = {"heute": {"datum": letzt, "werte": stand(letzt)}, "m1": {"datum": bis(je["SR_10Y"], d1)[0], "werte": stand(d1)}}
    if bis(je["SR_10Y"], d2):
        zeiten["j1"] = {"datum": bis(je["SR_10Y"], d2)[0], "werte": stand(d2)}
    a2 = dict(je["SR_2Y"])
    abst = [(d, v - a2[d]) for d, v in je["SR_10Y"] if d in a2]
    return {"name": "Euroraum", "quelle": "EZB, Renditekurve AAA-Staatsanleihen (Svensson-Modell), täglich",
            "url": "https://data.ecb.europa.eu/data/datasets/YC", "laufzeiten": [x[1] for x in EZB_LZ], "etiketten": [x[2] for x in EZB_LZ],
            "kurven": zeiten, "abstand_2j10j": kurzreihe(abst[-260:], 120)}


def us_kurve():
    daten = {}
    for j in (date.today().year, date.today().year - 1):
        try:
            for r in csv.DictReader(io.StringIO(text(TREASURY.format(j=j)))):
                m, t, y = r["Date"].split("/")
                daten[f"{y}-{m}-{t}"] = {k: float(r[k]) for k, _, _ in US_LZ if r.get(k)}
        except Exception as e:  # noqa: BLE001
            if j == date.today().year:
                raise
            print("  Treasury", j, e, file=sys.stderr)
    tage = sorted(daten)
    if not tage:
        raise ValueError("keine Treasury-Daten")
    letzt = tage[-1]

    def stand(tag):
        t = [x for x in tage if x <= tag]
        if not t:
            return None, None
        return t[-1], [daten[t[-1]].get(k) for k, _, _ in US_LZ]
    zeiten = {}
    for sch, tag in (("heute", letzt), ("m1", vor(letzt, 30)), ("j1", vor(letzt, 365))):
        d, w = stand(tag)
        if d and (sch != "j1" or d[:4] != "") and w:
            zeiten[sch] = {"datum": d, "werte": w}
    abst = [(d, daten[d]["10 Yr"] - daten[d]["2 Yr"]) for d in tage if "10 Yr" in daten[d] and "2 Yr" in daten[d]]
    return {"name": "USA", "quelle": "US-Finanzministerium, Daily Treasury Par Yield Curve Rates, täglich",
            "url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates", "laufzeiten": [x[1] for x in US_LZ],
            "etiketten": [x[2] for x in US_LZ], "kurven": zeiten, "abstand_2j10j": kurzreihe(abst[-260:], 120)}


def ciss():
    start = vor(date.today().isoformat(), 400)
    z = zeilen(f"{EZB}CISS/D.U2.Z0Z.4F.EC.SS_CIN.IDX?startPeriod={start}&format=csvdata")
    reihe = sorted((r["TIME_PERIOD"], float(r["OBS_VALUE"])) for r in z if r["OBS_VALUE"])
    d, v = reihe[-1]
    return {"id": "ciss", "name": "EZB-Stressindex CISS (Euroraum)", "gruppe": "angst", "einheit": "0 bis 1", "wert": round(v, 3), "datum": d,
            "r1t": None, "r1m": None, "ytd": None, "r1j": None, "verlauf": kurzreihe(reihe[-260:], 130),
            "quelle": "EZB, Composite Indicator of Systemic Stress", "url": "https://data.ecb.europa.eu/data/datasets/CISS"}


def waehrungen():
    start = date.today().year - 10
    monat = {}
    for r in zeilen(f"{EZB}EXR/M..EUR.SP00.A?startPeriod={start}-01&format=csvdata"):
        if r["OBS_VALUE"]:
            monat.setdefault(r["CURRENCY"], {})[r["TIME_PERIOD"]] = float(r["OBS_VALUE"])
    tag = {}
    for r in zeilen(f"{EZB}EXR/D..EUR.SP00.A?startPeriod={vor(date.today().isoformat(), 14)}&format=csvdata"):
        if r["OBS_VALUE"]:
            tag.setdefault(r["CURRENCY"], []).append((r["TIME_PERIOD"], float(r["OBS_VALUE"])))
    out = {}
    jahr = str(date.today().year)
    for w, mm in monat.items():
        if w not in tag:
            continue  # nicht mehr notierte Währung
        d, v = sorted(tag[w])[-1]
        reihe = sorted(mm.items())
        vj = [x for x in reihe if x[0] < jahr]
        j1 = [x for x in reihe if x[0] <= f"{int(d[:4]) - 1}-{d[5:7]}"]
        # Wert der Währung in Euro: 1/Kurs; Veränderung > 0 = Währung hat zum Euro gewonnen
        out[w] = {"name": NAMEN.get(w, w), "je_eur": v, "datum": d, "ytd": round(vj[-1][1] / v - 1, 5) if vj else None,
                  "r1j": round(j1[-1][1] / v - 1, 5) if j1 else None, "monat": [[z, round(x, 5)] for z, x in reihe]}
    return out


def abstand_euro(kurve):
    z = kurve["kurven"]["heute"]["werte"]
    return round(z[7] - z[3], 3) if z[7] is not None and z[3] is not None else None


def main():
    alt = json.loads(ZIEL.read_text()) if ZIEL.exists() else {}
    out = {"abruf": date.today().isoformat(), "puls": [], "kurven": {}, "waehrungen": {}}
    for kurz, f, leer in (("puls", lambda: yahoo(alt.get("puls", [])), []), ("euro", ezb_kurve, None), ("usa", us_kurve, None),
                          ("ciss", ciss, None), ("waehrungen", waehrungen, {})):
        try:
            erg = f()
            if kurz == "euro" or kurz == "usa":
                out["kurven"][kurz] = erg
            elif kurz == "ciss":
                out["puls"].append(erg)
            elif kurz == "puls":
                out["puls"] = erg + out["puls"]
            else:
                out[kurz] = erg
            print(f"  {kurz}: ok", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"{kurz} nicht abrufbar, alter Stand bleibt:", e, file=sys.stderr)
            if kurz in ("euro", "usa"):
                if alt.get("kurven", {}).get(kurz):
                    out["kurven"][kurz] = alt["kurven"][kurz]
            elif kurz == "ciss":
                out["puls"] += [x for x in alt.get("puls", []) if x["id"] == "ciss"]
            elif kurz == "puls":
                out["puls"] = alt.get("puls", []) + out["puls"]
            else:
                out[kurz] = alt.get(kurz, leer)
    # abgeleitete Größen: Zinsabstände und EUR/USD
    for key, name in (("usa", "Zinsabstand 10J minus 2J, USA"), ("euro", "Zinsabstand 10J minus 2J, Euroraum")):
        k = out["kurven"].get(key)
        if k and k["abstand_2j10j"]:
            reihe = [(d, v) for d, v in k["abstand_2j10j"]]
            d, v = reihe[-1]
            a1, a2 = bis(reihe, vor(d, 30)), bis(reihe, vor(d, 365))
            out["puls"].append({"id": "abst_" + key, "name": name, "gruppe": "zins", "einheit": "Prozentpunkte", "wert": round(v, 2), "datum": d,
                                "r1t": None, "r1m": round(v - a1[1], 2) if a1 else None, "ytd": None, "r1j": round(v - a2[1], 2) if a2 else None,
                                "diff": True, "verlauf": reihe, "quelle": k["quelle"], "url": k["url"]})
    usd = out["waehrungen"].get("USD")
    if usd:
        m = usd["monat"]
        out["puls"].append({"id": "eurusd", "name": "Euro in US-Dollar", "gruppe": "devise", "einheit": "USD je EUR", "wert": round(usd["je_eur"], 4),
                            "datum": usd["datum"], "r1t": None, "r1m": None, "ytd": round(1 / (1 + usd["ytd"]) - 1, 5) if usd["ytd"] is not None else None,
                            "r1j": round(1 / (1 + usd["r1j"]) - 1, 5) if usd["r1j"] is not None else None, "verlauf": m[-60:],
                            "quelle": "EZB-Referenzkurs", "url": "https://data.ecb.europa.eu/data/datasets/EXR"})
    out["quellen"] = {"puls": "Yahoo Finance (inoffizielle Schnittstelle, ohne Gewähr), EZB, US-Finanzministerium",
                      "nicht_frei": "VSTOXX und VDAX sind bei Yahoo nicht frei verfügbar; Credit Spreads (ICE BofA über FRED) siehe Konzept."}
    ZIEL.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"{ZIEL}: {len(out['puls'])} Marktgrößen, {len(out['kurven'])} Kurven, {len(out['waehrungen'])} Währungen", file=sys.stderr)


if __name__ == "__main__":
    main()
