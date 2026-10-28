"""Börsendaten für den Bereich BÖR des Terminals: Aktienindizes (Welt, OECD, Nicht-OECD) und große Unternehmen weltweit -> data/boerse.json.

Quelle: Yahoo Finance über yfinance (kostenlos, keine Schlüssel). Der Katalog steht in boersen_katalog.json:
  indizes     id, name, land, gruppe (Welt / OECD / Nicht-OECD), region, symbole (Yahoo-Kandidaten; der erste mit Kursen gewinnt)
  unternehmen name, symbol, land, sektor
Je Eintrag: Wochenschlusskurse über zehn Jahre (Datum = Montag der Woche, null bei Lücken) plus Kennzahlen aus den Tageskursen
(Stand, 1 Tag, 1 Woche, 1 Monat, 3 Monate, laufendes Jahr, 1 Jahr, 3/5/10 Jahre, 52-Wochen-Spanne). Bei Unternehmen zusätzlich
Börsenwert in Mrd. US-Dollar (Yahoo fast_info, umgerechnet mit Yahoo-Wechselkursen).
Unternehmen, die schon in stammdaten/unternehmen_ids.csv stehen (über den Ticker), tragen deren ID (Feld id) und verlinken auf die
Profilseite. Neue IDs werden hier nie vergeben: ausländische Großunternehmen laufen unter ihrem Yahoo-Symbol.
Fällt Yahoo teilweise aus (429), bleibt der letzte gute Stand liegen.
Aufruf: python3 app/boersen_abruf.py [--jahre 10] [--nur indizes|unternehmen]"""
import argparse
import csv
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yfinance as yf

HIER = Path(__file__).resolve().parent
ZIEL = HIER / "data/boerse.json"


def runden(x, n=5):
    return None if x is None or not math.isfinite(x) else float(f"{x:.{n}g}")


def montag(d):
    return (d - timedelta(days=d.weekday())).date().isoformat()


def herunterladen(symbole, **kw):
    """{symbol: Series der Schlusskurse}; Fehlversuche werden wiederholt, fehlende Symbole fehlen im Ergebnis."""
    erg = {}
    for i in range(0, len(symbole), 40):
        b = symbole[i:i + 40]
        df = None
        for versuch in range(3):
            try:
                df = yf.download(b, auto_adjust=False, group_by="ticker", progress=False, threads=True, **kw)
                break
            except Exception:
                time.sleep(5 * (versuch + 1))
        if df is None:
            continue
        for s in b:
            try:
                z = df[s]["Close"].dropna()
            except Exception:
                continue
            if len(z) >= 5:
                erg[s] = z
        print(f"  {min(i + 40, len(symbole))}/{len(symbole)} Symbole, {len(erg)} mit Kursen", flush=True)
    return erg


def kennzahlen(tag, woche):
    """Aus Tagesserie (2 Jahre) und Wochenserie (10 Jahre) die Anzeigewerte."""
    letzt, d1 = float(tag.iloc[-1]), tag.index[-1]

    def vor(tage):
        s = tag[tag.index <= d1 - timedelta(days=tage)]
        return float(s.iloc[-1]) if len(s) else None

    def rend(basis):
        return None if not basis else runden(letzt / basis - 1, 4)

    jahr0 = tag[tag.index < datetime(d1.year, 1, 1)]
    ein_jahr = tag[tag.index > d1 - timedelta(days=365)]

    def weit(jahre):
        ziel = d1 - timedelta(days=365 * jahre)
        s = woche[woche.index <= ziel]
        return rend(float(s.iloc[-1])) if len(s) and (ziel - s.index[-1]).days < 20 else None

    return {"kurs": runden(letzt), "datum": d1.date().isoformat(), "r1t": rend(float(tag.iloc[-2])) if len(tag) > 1 else None, "r1w": rend(vor(7)), "r1m": rend(vor(30)),
            "r3m": rend(vor(91)), "ytd": rend(float(jahr0.iloc[-1])) if len(jahr0) else None, "r1j": rend(vor(365)), "r3j": weit(3), "r5j": weit(5), "r10j": weit(10),
            "hoch52": runden(float(ein_jahr.max())), "tief52": runden(float(ein_jahr.min()))}


def laden_gruppe(eintraege, kandidaten, jahre):
    """eintraege: Liste von Dicts; kandidaten(e) -> Liste Yahoo-Symbole. Ergebnis: Liste (eintrag, symbol, kennzahlen, {montag: kurs})."""
    offen = list(eintraege)
    erg = []
    for runde in range(3):
        if not offen:
            break
        sym = {id(e): (kandidaten(e)[runde] if len(kandidaten(e)) > runde else None) for e in offen}
        liste = sorted({s for s in sym.values() if s})
        if not liste:
            break
        print(f"Runde {runde + 1}: {len(liste)} Symbole", flush=True)
        wo = herunterladen(liste, period=f"{jahre}y", interval="1wk")
        tg = herunterladen([s for s in liste if s in wo], period="2y", interval="1d")
        weiter = []
        for e in offen:
            s = sym[id(e)]
            if s and s in wo and s in tg:
                w, t = wo[s], tg[s]
                reihe = {montag(d): runden(float(c)) for d, c in w.items()}
                reihe[montag(t.index[-1])] = runden(float(t.iloc[-1]))   # laufende Woche mit dem letzten Tagesschluss
                erg.append((e, s, kennzahlen(t, w), reihe))
            else:
                weiter.append(e)
        offen = weiter
    return erg, offen


FX = {}


def fx_usd(w):
    """Kurs der Währung in US-Dollar (Yahoo-Paar XXXUSD=X); Unterwährungen (Pence, Agorot, Cent) über Faktor."""
    teil = {"GBp": ("GBP", 100), "GBX": ("GBP", 100), "ILA": ("ILS", 100), "ZAc": ("ZAR", 100)}
    basis, f = teil.get(w, (w, 1))
    if basis == "USD":
        return 1.0 / f
    if basis not in FX:
        try:
            h = yf.Ticker(f"{basis}USD=X").history(period="5d")["Close"].dropna()
            FX[basis] = float(h.iloc[-1]) if len(h) else None
        except Exception:
            FX[basis] = None
    return None if FX[basis] is None else FX[basis] / f


def boerswert(symbol):
    try:
        fi = yf.Ticker(symbol).fast_info
        mc, w = fi["marketCap"], fi["currency"]
        k = fx_usd(w)
        return (runden(mc * k / 1e9, 4) if mc and k else None), w
    except Exception:
        return None, None


def ids_nach_ticker():
    erg = {}
    p = HIER.parent / "stammdaten/unternehmen_ids.csv"
    if p.exists():
        with open(p, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r.get("ticker"):
                    erg[r["ticker"].upper()] = r["unternehmen_id"]
    return erg


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--jahre", type=int, default=10)
    p.add_argument("--nur", choices=["indizes", "unternehmen"])
    a = p.parse_args()
    kat = json.loads((HIER / "boersen_katalog.json").read_text())
    alt = json.loads(ZIEL.read_text()) if ZIEL.exists() else None
    ind, uf = [], []
    if a.nur != "unternehmen":
        er, uf_i = laden_gruppe(kat["indizes"], lambda e: e["symbole"], a.jahre)
        ind = er
        print(f"Indizes: {len(er)} von {len(kat['indizes'])} mit Kursen; ohne: {[e['name'] for e in uf_i]}")
        ind_fehlt = [e["name"] for e in uf_i]
    if a.nur != "indizes":
        er, uf = laden_gruppe(kat["unternehmen"], lambda e: [e["symbol"]], a.jahre)
        print(f"Unternehmen: {len(er)} von {len(kat['unternehmen'])} mit Kursen; ohne: {[e['name'] for e in uf]}")
        with ThreadPoolExecutor(8) as ex:
            bw = list(ex.map(lambda t: boerswert(t[1]), er))
        idmap = ids_nach_ticker()
        unt = []
        for (e, s, k, r), (mc, w) in zip(er, bw):
            o = {**e, "symbol": s, **k, "boerswert": mc, "waehrung": w, "t": r}
            if s.upper() in idmap:
                o["id"] = idmap[s.upper()]
            unt.append(o)
        unt_fehlt = [e["name"] for e in uf]
    # Teilläufe (--nur) ergänzen den bisherigen Stand der anderen Gruppe
    ind_out = [{**e, "symbol": s, **k, "t": r} for e, s, k, r in ind] if a.nur != "unternehmen" else (alt or {}).get("indizes", [])
    unt_out = unt if a.nur != "indizes" else (alt or {}).get("unternehmen", [])
    wochen = sorted({d for x in ind_out + unt_out for d in x["t"]})
    if len(wochen) > 0:
        wochen = [d for d in wochen if d >= (date.today() - timedelta(days=int(365.25 * a.jahre) + 14)).isoformat()]
    for x in ind_out + unt_out:
        if isinstance(x["t"], dict):
            x["t"] = [x["t"].get(d) for d in wochen]
        else:   # Bestand aus Teillauf: auf neues Raster umrechnen
            alte = dict(zip((alt or {}).get("wochen", []), x["t"]))
            x["t"] = [alte.get(d) for d in wochen]
        x.pop("symbole", None)
    out = {"abruf": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "quelle": "Yahoo Finance (yfinance); Wochenschlusskurse in Landeswährung (Londoner Kurse in Pence), Börsenwert in Mrd. US-Dollar",
           "wochen": wochen, "indizes": ind_out, "unternehmen": unt_out,
           "ohne_kurse": {"indizes": locals().get("ind_fehlt", []), "unternehmen": locals().get("unt_fehlt", [])}}
    # Teilausfall (Yahoo 429): fallen über zehn Prozent der bisherigen Einträge weg, bleibt der letzte gute Stand liegen
    if alt and len(ind_out) + len(unt_out) < 0.9 * (len(alt["indizes"]) + len(alt["unternehmen"])):
        print(f"::warning::Nur {len(ind_out) + len(unt_out)} Einträge mit Kursen, boerse.json bleibt unverändert")
        return
    ZIEL.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(ind_out)} Indizes, {len(unt_out)} Unternehmen, {len(wochen)} Wochen -> data/boerse.json")


if __name__ == "__main__":
    main()
