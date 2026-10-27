"""Wochenkurse (zehn Jahre) für alle börsennotierten Unternehmen -> data/kurse_woche.json.

Quelle: Yahoo Finance über yfinance (kostenlos). Ticker kommen aus data/unternehmen.json (Feld ticker) und data/markt.json.
Je Woche der Schlusskurs der Woche (Datum = Montag der Woche); fehlende Wochen bleiben null.
Eigene Datei statt markt.json, damit das Terminal klein bleibt: 535 Ticker x 520 Wochen sind etwa 2 MB, tägliche Kurse wären rund 20 MB.
Tägliche Kurse gibt es weiter für die Banken in markt.json (kurse_hist).
Aufruf: python3 app/kurse_historie.py [--jahre 10]"""
import argparse
import json
import math
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yfinance as yf

HIER = Path(__file__).resolve().parent


def tickerliste():
    t = set()
    u = HIER / "data/unternehmen.json"
    if u.exists():
        t |= {f["ticker"] for f in json.loads(u.read_text())["unternehmen"] if f.get("ticker")}
    m = HIER / "data/markt.json"
    if m.exists():
        t |= {w["ticker"] for w in json.loads(m.read_text())["werte"]}
    return sorted(t)


def runden(x):
    return None if x is None or not math.isfinite(x) else float(f"{x:.5g}")


SUFFIXE = [".DE", ".F", ".MU", ".DU", ".SG", ".HM", ".BE"]   # wie boersennotierte-unternehmen/skripte/yahoo_abruf.py


def montag(d):
    return (d - timedelta(days=d.weekday())).date().isoformat()


def laden(symbole, jahre, block):
    """Wochenschlusskurse je Yahoo-Symbol: {symbol: {montag: kurs}}"""
    erg = {}
    for i in range(0, len(symbole), block):
        b = symbole[i:i + block]
        df = None
        for versuch in range(3):
            try:
                df = yf.download(b, period=f"{jahre}y", interval="1wk", auto_adjust=False, group_by="ticker", progress=False, threads=True)
                break
            except Exception:
                time.sleep(5 * (versuch + 1))
        for sym in b:
            try:
                s = df[sym]["Close"].dropna()
            except Exception:
                continue
            if len(s) >= 20:
                erg[sym] = {montag(d): runden(float(c)) for d, c in s.items()}
        print(f"  {min(i + block, len(symbole))}/{len(symbole)} Symbole, {len(erg)} mit Kursen", flush=True)
    return erg


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--jahre", type=int, default=10)
    p.add_argument("--block", type=int, default=40)
    a = p.parse_args()
    tick = tickerliste()
    # Ticker ohne Börsenendung (Kürzel der Deutschen Börse) werden nacheinander an den deutschen Handelsplätzen gesucht, nie ohne Endung (Verwechslung mit US-Tickern)
    offen, reihen, symbol = list(tick), {}, {}
    for suf in [None] + SUFFIXE:
        if not offen:
            break
        kand = {t: (t if "." in t or not suf else t + suf) for t in offen if "." in t or suf}
        if not kand:
            continue
        print(f"Runde {suf or 'Ticker mit Endung'}: {len(kand)} Ticker", flush=True)
        erg = laden(sorted(set(kand.values())), a.jahre, a.block)
        for t, sym in kand.items():
            if sym in erg:
                reihen[t] = erg[sym]; symbol[t] = sym; offen.remove(t)
    daten = sorted({d for r in reihen.values() for d in r})
    out = {"abruf": datetime.now(timezone.utc).isoformat(timespec="seconds"), "quelle": "Yahoo Finance (yfinance), Wochenschlusskurse in Börsenwährung (Londoner Kurse in Pence)",
           "daten": daten, "symbol": {t: s for t, s in symbol.items() if s != t}, "t": {t: [r.get(d) for d in daten] for t, r in sorted(reihen.items())}, "fehler": offen}
    ziel = HIER / "data/kurse_woche.json"
    # Teilausfall (Yahoo 429): fallen über zehn Prozent der bisherigen Ticker weg, bleibt der letzte gute Stand liegen
    if ziel.exists():
        alt = len(json.loads(ziel.read_text())["t"])
        if alt and len(reihen) < alt * 0.9:
            print(f"::warning::Nur {len(reihen)} von {alt} Tickern mit Kursen, kurse_woche.json bleibt unverändert")
            return
    ziel.write_text(json.dumps(out, separators=(",", ":")))
    print(f"{len(reihen)} Ticker, {len(daten)} Wochen, {len(offen)} ohne Kurse -> data/kurse_woche.json")


if __name__ == "__main__":
    main()
