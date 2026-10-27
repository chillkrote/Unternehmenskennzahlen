"""Kapitalmarkt- und Abschlussdaten je Aktie über yfinance (Yahoo Finance).

Liest universum/rohdaten_instrumente_roh.csv bzw. universum/universum_instrumente.csv und schreibt
je ISIN rohdaten/yahoo/<ISIN>.json mit:
  info          Stammdaten und Marktdaten laut Yahoo (Kurs, Börsenwert, Aktienzahl, Mitarbeiter, Multiples)
  guv/bilanz/cashflow   Jahresabschlüsse (Konzern), je Geschäftsjahr alle von Yahoo gelieferten Posten
  dividenden    gezahlte Dividenden je Ex-Tag
  kurse_monat   Monatsschlusskurse seit 2019
  aktionaere    major_holders und institutional_holders
Bereits vorhandene Dateien werden übersprungen (--neu erzwingt Neuabruf).

Ticker-Suche: <Kürzel>.DE (Xetra), sonst .F (Frankfurt), .MU (München), .DU (Düsseldorf),
.SG (Stuttgart), .HM (Hamburg), .BE (Berlin).
"""
import csv
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

HIER = Path(__file__).resolve().parent
BASIS = HIER.parent
ZIEL = BASIS / "rohdaten" / "yahoo"
SUFFIXE = [".DE", ".F", ".MU", ".DU", ".SG", ".HM", ".BE"]


def _wert(v):
    if v is None:
        return None
    if isinstance(v, (pd.Timestamp, datetime)):
        return v.isoformat()[:10]
    try:
        f = float(v)
    except (TypeError, ValueError):
        return v
    return None if math.isnan(f) or math.isinf(f) else f


def _tabelle(df):
    if df is None or df.empty:
        return {}
    out = {}
    for spalte in df.columns:
        out[str(spalte)[:10]] = {str(k): _wert(df.loc[k, spalte]) for k in df.index if _wert(df.loc[k, spalte]) is not None}
    return out


def instrumente():
    for name in ("universum_instrumente.csv", "rohdaten_instrumente_roh.csv"):
        p = BASIS / "universum" / name
        if p.exists():
            return list(csv.DictReader(open(p, encoding="utf-8-sig"), delimiter=";"))
    raise SystemExit("Universum fehlt")


def ticker_kandidaten(z):
    k = (z.get("kuerzel") or "").strip()
    out = []
    if z.get("yahoo"):
        out.append(z["yahoo"])
    if k:
        out += [k + s for s in SUFFIXE]
    try:  # Rückfall: Yahoo-Suche nach der ISIN
        out += [q["symbol"] for q in yf.Search(z["isin"], max_results=5).quotes if q.get("symbol") not in out]
    except Exception:
        pass
    return out


def abruf(z):
    for tk in ticker_kandidaten(z):
        t = yf.Ticker(tk)
        try:
            hist = t.history(period="max", interval="1mo", auto_adjust=False)
        except Exception:
            hist = None
        if hist is None or hist.empty:
            continue
        try:
            info = t.info or {}
        except Exception as e:
            info = {"_fehler": str(e)}
        d = {"isin": z["isin"], "ticker": tk, "abruf": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "info": {k: _wert(v) for k, v in info.items() if not isinstance(v, (list, dict))}}
        h = hist[hist.index >= "2019-01-01"]
        d["kurse_monat"] = {str(i)[:10]: _wert(r["Close"]) for i, r in h.iterrows() if _wert(r["Close"]) is not None}
        try:
            tag = t.history(period="5d", interval="1d", auto_adjust=False)
            if not tag.empty:
                d["kurs_letzter"] = {"datum": str(tag.index[-1])[:10], "schluss": _wert(tag["Close"].iloc[-1])}
        except Exception:
            pass
        for k, attr in (("guv", "income_stmt"), ("bilanz", "balance_sheet"), ("cashflow", "cashflow")):
            try:
                d[k] = _tabelle(getattr(t, attr))
            except Exception as e:
                d[k] = {"_fehler": str(e)}
        try:
            div = t.dividends
            d["dividenden"] = {str(i)[:10]: _wert(v) for i, v in div.items()}
        except Exception:
            d["dividenden"] = {}
        try:
            mh = t.major_holders
            d["aktionaere"] = {"major": {str(i): _wert(r.iloc[0]) for i, r in mh.iterrows()} if mh is not None else {}}
            ih = t.institutional_holders
            d["aktionaere"]["institutionen"] = [{c: _wert(r[c]) for c in ih.columns} for _, r in ih.iterrows()] if ih is not None else []
        except Exception:
            d["aktionaere"] = {}
        return d
    return None


def info_nachholen():
    """Holt Stammdaten (t.info) nach, wo der erste Abruf wegen Rate-Limits nur einen Fehler gespeichert hat."""
    for p in sorted(ZIEL.glob("[A-Z]*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if len(d.get("info", {})) > 5:
            continue
        for versuch in range(3):
            try:
                info = yf.Ticker(d["ticker"]).info or {}
                if len(info) > 5:
                    break
            except Exception:
                info = {}
            time.sleep(10 * (versuch + 1))
        if len(info) > 5:
            d["info"] = {k: _wert(v) for k, v in info.items() if not isinstance(v, (list, dict))}
            p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            print("info", d["isin"], d["info"].get("longName"), flush=True)
        else:
            print("info fehlt weiter", d["isin"], d["ticker"], flush=True)
        time.sleep(1)


def main():
    if "--info" in sys.argv:
        return info_nachholen()
    neu = "--neu" in sys.argv
    nur = [a for a in sys.argv[1:] if not a.startswith("--")]
    teil = next((a.split("=")[1] for a in sys.argv if a.startswith("--teil=")), None)  # z. B. --teil=2/4
    ZIEL.mkdir(parents=True, exist_ok=True)
    fehlend = []
    for i, z in enumerate(instrumente()):
        if teil and i % int(teil.split("/")[1]) != int(teil.split("/")[0]):
            continue
        if nur and z["isin"] not in nur:
            continue
        p = ZIEL / f"{z['isin']}.json"
        if p.exists() and not neu:
            continue
        for versuch in range(3):
            try:
                d = abruf(z)
                break
            except Exception as e:
                print("Fehler", z["isin"], e, file=sys.stderr)
                time.sleep(20 * (versuch + 1))
        else:
            d = None
        if d is None:
            fehlend.append(z["isin"])
            print("kein Ticker", z["isin"], z["name_boerse"], flush=True)
            continue
        p.write_text(json.dumps(d, ensure_ascii=False, indent=1, sort_keys=False), encoding="utf-8")
        print(z["isin"], d["ticker"], d["info"].get("longName"), flush=True)
        time.sleep(0.5)
    if teil:
        return
    (ZIEL / "_ohne_yahoo.json").write_text(json.dumps(fehlend, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
