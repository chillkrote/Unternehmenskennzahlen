"""Tägliche Börsendaten der börsennotierten Banken (bzw. ihrer Mütter) über yfinance.

Neben Kursen auch die letzten Konzernabschlüsse (GuV, Bilanz) laut Yahoo und daraus
gebräuchliche Kennzahlen (KGV, KBV, RoE, RoTE, Cost-Income-Ratio, Zinsmarge, ...).

Schreibt data/markt.json, getrennt von den Bilanzdaten des Geschäftsjahrs.
Zuordnung Bank -> Ticker steht in boersen_ticker.json.
"""
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
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


# Posten der Jahresabschlüsse (Konzern, wie von Yahoo geliefert). Erster vorhandener Name gewinnt.
GUV = {
    "ertraege": ["Total Revenue"],
    "zinsueberschuss": ["Net Interest Income"],
    "vorsteuer": ["Pretax Income"],
    "steuern": ["Tax Provision"],
    "jue": ["Net Income Common Stockholders", "Net Income"],
    "eps": ["Diluted EPS", "Basic EPS"],
}
# Verwaltungsaufwand: 'Operating Expense', sonst Summe der Non-Interest-Expense-Posten (US-Banken)
AUFWAND_TEILE = ["Selling And Marketing Expense", "General And Administrative Expense",
                 "Professional Expense And Contract Services Expense", "Other Non Interest Expense"]
BILANZ = {
    "bilanzsumme": ["Total Assets"],
    "ek": ["Common Stock Equity", "Stockholders Equity"],
    "tbv": ["Tangible Book Value"],
    "kredite": ["Net Loan"],
    "goodwill": ["Goodwill And Other Intangible Assets"],
}


def _posten(df, spalte, namen):
    for n in namen:
        if n in df.index:
            v = df.loc[n, spalte]
            if v == v:
                return float(v)
    return None


def abschluesse(t):
    """Jahresabschlüsse (neuestes zuerst) als Liste von Dicts, Beträge in Bilanzwährung."""
    guv, bil = t.income_stmt, t.balance_sheet
    out = []
    for spalte in list(guv.columns)[:4]:
        j = {"jahr": spalte.year}
        for k, namen in GUV.items():
            j[k] = _posten(guv, spalte, namen)
        j["aufwand"] = _posten(guv, spalte, ["Operating Expense"])
        if j["aufwand"] is None:
            teile = [_posten(guv, spalte, [n]) for n in AUFWAND_TEILE]
            j["aufwand"] = sum(v for v in teile if v) or None
        b_spalte = next((c for c in bil.columns if c.year == spalte.year), None)
        for k, namen in BILANZ.items():
            j[k] = _posten(bil, b_spalte, namen) if b_spalte is not None else None
        out.append(j)
    return out


def _q(a, b):
    return a / b if a is not None and b not in (None, 0) else None


def _wachstum(a, b):
    return a / b - 1 if a is not None and b not in (None, 0) and b > 0 else None


def kennzahlen(js, kurs, marktkap, dividenden_12m, fx):
    """Gebräuchliche Bilanz-, GuV- und Bewertungskennzahlen aus dem letzten Geschäftsjahr.
    fx = Kurswährung je Einheit Bilanzwährung (1, wenn gleich)."""
    if not js:
        return {}
    a, v = js[0], (js[1] if len(js) > 1 else {})
    mittel = lambda k: (a[k] + v[k]) / 2 if a.get(k) and v.get(k) else a.get(k)
    mk = marktkap / fx if marktkap else None          # Börsenwert in Bilanzwährung
    eps_kw = a["eps"] * fx if a.get("eps") is not None else None
    nii = a["zinsueberschuss"] if a.get("zinsueberschuss") and a["zinsueberschuss"] > 0 else None  # Yahoo liefert bei Nicht-Kreditbanken teils Unsinn
    cir = _q(a["aufwand"], a["ertraege"])
    if cir is not None and not 0 < cir < 1.5:
        cir = None
    return {
        "gj": a["jahr"],
        # Bewertung
        "kgv": _q(kurs, eps_kw) if eps_kw and eps_kw > 0 else None,
        "kbv": _q(mk, a["ek"]),
        "ktbv": _q(mk, a["tbv"]),
        "div_rendite": _q(dividenden_12m, kurs) if dividenden_12m is not None else None,
        "ausschuettung": _q(dividenden_12m, eps_kw) if eps_kw and eps_kw > 0 and dividenden_12m is not None else None,
        # Rentabilität
        "roe": _q(a["jue"], mittel("ek")),
        "rote": _q(a["jue"], mittel("tbv")),
        "roa": _q(a["jue"], mittel("bilanzsumme")),
        "cir": cir,
        "vst_marge": _q(a["vorsteuer"], a["ertraege"]),
        "steuerquote": _q(a["steuern"], a["vorsteuer"]) if a.get("vorsteuer") and a["vorsteuer"] > 0 else None,
        "zinsanteil": _q(nii, a["ertraege"]),
        "zinsmarge": _q(nii, mittel("bilanzsumme")),
        # Bilanz
        "ek_quote": _q(a["ek"], a["bilanzsumme"]),
        "kredit_anteil": _q(a["kredite"], a["bilanzsumme"]),
        "goodwill_ek": _q(a["goodwill"], a["ek"]),
        # Wachstum zum Vorjahr
        "w_ertraege": _wachstum(a.get("ertraege"), v.get("ertraege")),
        "w_jue": _wachstum(a.get("jue"), v.get("jue")),
        "w_eps": _wachstum(a.get("eps"), v.get("eps")),
        "w_bilanzsumme": _wachstum(a.get("bilanzsumme"), v.get("bilanzsumme")),
    }


def devisenkurs(von, nach):
    if not von or von == nach:
        return 1.0
    h = yf.Ticker(f"{von}{nach}=X").history(period="5d")["Close"].dropna()
    return float(h.iloc[-1])


def abruf(eintrag):
    t = yf.Ticker(eintrag["ticker"])
    h = t.history(period="10y", auto_adjust=False)   # zehn Jahre täglich: Kursverlauf der Ansichten = letztes Jahr, Rest für die Korrelation
    fi = t.fast_info
    waehrung, teiler = fi.get("currency"), 1
    if waehrung == "GBp":  # Londoner Kurse in Pence
        waehrung, teiler = "GBP", 100
    serie = [(d.date().isoformat(), round(float(c) / teiler, 4)) for d, c in h["Close"].items() if c == c]
    if not serie:
        raise RuntimeError("keine Kurse")
    jahr = serie[-1][0][:4]
    aktien = fi.get("shares")
    marktkap = serie[-1][1] * aktien if aktien else None
    div = t.dividends
    grenze = h.index[-1] - pd.Timedelta(days=365)
    dividenden_12m = float(div[div.index > grenze].sum()) / teiler if div is not None else None
    bilanzwaehrung = eintrag.get("bilanzwaehrung", waehrung)
    try:
        js = abschluesse(t)
    except Exception:
        js = []
    kz = kennzahlen(js, serie[-1][1], marktkap, dividenden_12m, devisenkurs(bilanzwaehrung, waehrung)) if js else {}
    return {
        "bilanzwaehrung": bilanzwaehrung,
        "abschluesse": js,
        "kz": kz,
        "dividenden_12m": dividenden_12m,
        "waehrung": waehrung,
        "datum": serie[-1][0],
        "kurs": serie[-1][1],
        "r_1t": _rendite(serie, tage=1) if len(serie) > 1 else None,
        "r_1m": _rendite(serie, tage=30),
        "r_ytd": _rendite(serie, seit=f"{jahr}-01-01"),
        "r_1j": _rendite(serie, tage=365),
        "hoch_52w": max(c for d, c in serie[-260:]),
        "tief_52w": min(c for d, c in serie[-260:]),
        "aktien": aktien,
        "marktkap": marktkap,
        # Kursverlauf: ein Jahr täglich
        "kurse": serie[-260:],
        # volle Historie (bis zu zehn Jahre, täglich) für die Korrelationsauswertung
        "kurse_hist": serie,
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
        daten = dict(cache[e["ticker"]])
        if any(w["ticker"] == e["ticker"] for w in werte):
            daten.pop("kurse_hist", None)  # mehrere Banken, ein Ticker (z. B. Deutsche Bank): Historie nur einmal speichern
        werte.append({"bank": treffer[0], "ticker": e["ticker"], "ebene": e["ebene"], "mutter": e.get("mutter"), **daten})
    def sauber(x):
        if isinstance(x, float):
            return x if math.isfinite(x) else None
        if isinstance(x, dict):
            return {k: sauber(v) for k, v in x.items()}
        if isinstance(x, list):
            return [sauber(v) for v in x]
        return x
    werte = sauber(werte)
    out = {"abruf": datetime.now(timezone.utc).isoformat(timespec="seconds"), "quelle": "Yahoo Finance (yfinance), Schlusskurse",
           "werte": werte, "fehler": fehler}
    (HIER / "data").mkdir(exist_ok=True)
    ziel = HIER / "data/markt.json"
    # Teilausfall (Yahoo 429, Sperre): bricht mehr als ein Drittel weg, bleibt der letzte gute Stand liegen
    if ziel.exists():
        alt = len(json.loads(ziel.read_text())["werte"])
        if alt and len(werte) < alt * 2 / 3:
            print(f"::warning::Nur {len(werte)} von {alt} Banken mit Kursen, markt.json bleibt unverändert")
            for f in fehler:
                print("  ", f)
            return
    ziel.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(werte)} Banken mit Kursen, {len(fehler)} Fehler -> data/markt.json")
    for f in fehler:
        print("  ", f)


if __name__ == "__main__":
    main()
