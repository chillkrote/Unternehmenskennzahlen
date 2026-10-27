"""Tägliche Börsendaten der börsennotierten Banken (bzw. ihrer Mütter) über yfinance.

Schreibt data/markt.json, getrennt von den Bilanzdaten des Geschäftsjahrs.
Zuordnung Bank -> Ticker steht in boersen_ticker.json.
"""
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

import datenschicht

HIER = Path(__file__).resolve().parent


def _rendite(serie, tage=None, seit=None):
    """Veränderung des letzten Schlusskurses gegenüber dem Kurs vor `tage` Kalendertagen bzw. dem letzten Kurs vor `seit`."""
    letzter_tag, letzter = serie[-1]
    if seit is not None:
        vorher = [c for d, c in serie if d < seit]
    else:
        grenze = datetime.fromisoformat(letzter_tag).toordinal() - tage
        vorher = [c for d, c in serie if datetime.fromisoformat(d).toordinal() <= grenze]
    return letzter / vorher[-1] - 1 if vorher else None


def abruf(eintrag):
    t = yf.Ticker(eintrag["ticker"])
    h = t.history(period="2y", auto_adjust=False)
    serie = [(d.date().isoformat(), round(float(c), 4)) for d, c in h["Close"].items() if c == c]
    if not serie:
        raise RuntimeError("keine Kurse")
    fi = t.fast_info
    jahr = serie[-1][0][:4]
    aktien = fi.get("shares")
    return {
        "waehrung": fi.get("currency"),
        "datum": serie[-1][0],
        "kurs": serie[-1][1],
        "r_1t": _rendite(serie, tage=1) if len(serie) > 1 else None,
        "r_1m": _rendite(serie, tage=30),
        "r_ytd": _rendite(serie, seit=f"{jahr}-01-01"),
        "r_1j": _rendite(serie, tage=365),
        "hoch_52w": max(c for d, c in serie[-260:]),
        "tief_52w": min(c for d, c in serie[-260:]),
        "aktien": aktien,
        "marktkap": serie[-1][1] * aktien if aktien else fi.get("marketCap"),
        # Kursverlauf: ein Jahr täglich
        "kurse": serie[-260:],
    }


def main():
    zuordnung = json.loads((HIER / "boersen_ticker.json").read_text())["ticker"]
    banken = [b["bank"] for b in datenschicht.lade()]
    cache, werte, fehler = {}, [], []
    for e in zuordnung:
        treffer = [n for n in banken if re.search(e["muster"], n)]
        if not treffer:
            fehler.append(f"{e['muster']}: keine Bank im Datensatz")
            continue
        try:
            if e["ticker"] not in cache:
                cache[e["ticker"]] = abruf(e)
        except Exception as ex:  # einzelne Ticker dürfen fehlen
            fehler.append(f"{e['ticker']}: {ex}")
            continue
        werte.append({"bank": treffer[0], "ticker": e["ticker"], "ebene": e["ebene"], "mutter": e.get("mutter"), **cache[e["ticker"]]})
    for w in werte:
        for k, v in list(w.items()):
            if isinstance(v, float) and not math.isfinite(v):
                w[k] = None
    out = {"abruf": datetime.now(timezone.utc).isoformat(timespec="seconds"), "quelle": "Yahoo Finance (yfinance), Schlusskurse",
           "werte": werte, "fehler": fehler}
    (HIER / "data").mkdir(exist_ok=True)
    (HIER / "data/markt.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(werte)} Banken mit Kursen, {len(fehler)} Fehler -> data/markt.json")
    for f in fehler:
        print("  ", f)


if __name__ == "__main__":
    main()
