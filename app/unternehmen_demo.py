"""Beispieldaten für die Branchenansichten des Terminals (nur bis echte Branchentabellen vorliegen).

Holt für rund 40 große deutsche Börsenunternehmen aus 10 Branchen Kurse, Konzernabschluss und
rechnet die Kennzahlen des Katalogs. Schreibt data/unternehmen_demo.json. Das ist eine
Stichprobe zur Gestaltung der Ansichten, keine Vollerhebung: das Universum aller deutschen
Börsenunternehmen und deren geprüfte Daten entstehen in banken-fremden Erhebungen unter `unternehmen/`.
"""
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

HIER = Path(__file__).resolve().parent

STICHPROBE = {
    "auto": [("Volkswagen AG", "VOW3.DE"), ("BMW AG", "BMW.DE"), ("Mercedes-Benz Group AG", "MBG.DE"), ("Porsche AG", "P911.DE"), ("Continental AG", "CON.DE")],
    "chemie-pharma": [("BASF SE", "BAS.DE"), ("Bayer AG", "BAYN.DE"), ("Merck KGaA", "MRK.DE"), ("Symrise AG", "SY1.DE"), ("Fresenius SE", "FRE.DE"), ("Sartorius AG", "SRT3.DE")],
    "industrie": [("Siemens AG", "SIE.DE"), ("Airbus SE", "AIR.DE"), ("MTU Aero Engines AG", "MTX.DE"), ("Heidelberg Materials AG", "HEI.DE"), ("Rheinmetall AG", "RHM.DE"), ("Siemens Energy AG", "ENR.DE")],
    "technologie": [("SAP SE", "SAP.DE"), ("Infineon Technologies AG", "IFX.DE"), ("Nemetschek SE", "NEM.DE"), ("Aixtron SE", "AIXA.DE")],
    "konsum": [("adidas AG", "ADS.DE"), ("Puma SE", "PUM.DE"), ("Beiersdorf AG", "BEI.DE"), ("Henkel AG & Co. KGaA", "HEN3.DE"), ("Zalando SE", "ZAL.DE"), ("Hugo Boss AG", "BOSS.DE")],
    "energie-versorger": [("E.ON SE", "EOAN.DE"), ("RWE AG", "RWE.DE"), ("EnBW Energie Baden-Württemberg AG", "EBK.DE")],
    "telekom-medien": [("Deutsche Telekom AG", "DTE.DE"), ("Deutsche Börse AG", "DB1.DE"), ("ProSiebenSat.1 Media SE", "PSM.DE")],
    "logistik": [("Deutsche Post AG (DHL Group)", "DHL.DE"), ("Deutsche Lufthansa AG", "LHA.DE"), ("Hapag-Lloyd AG", "HLAG.DE")],
    "immobilien": [("Vonovia SE", "VNA.DE"), ("LEG Immobilien SE", "LEG.DE"), ("TAG Immobilien AG", "TEG.DE")],
    "versicherungen": [("Allianz SE", "ALV.DE"), ("Münchener Rückversicherungs-Gesellschaft AG", "MUV2.DE"), ("Hannover Rück SE", "HNR1.DE"), ("Talanx AG", "TLX.DE")],
}


def posten(df, spalte, namen):
    if spalte is None:
        return None
    for n in namen:
        if n in df.index:
            v = df.loc[n, spalte]
            if v == v:
                return float(v)
    return None


def q(a, b):
    return a / b if a is not None and b not in (None, 0) else None


def wachstum(a, b):
    return a / b - 1 if a is not None and b not in (None, 0) and b > 0 else None


def abruf(name, ticker, branche):
    t = yf.Ticker(ticker)
    h = t.history(period="2y", auto_adjust=False)
    serie = [(d.date().isoformat(), round(float(c), 4)) for d, c in h["Close"].items() if c == c]
    fi = t.fast_info
    if not serie or fi.get("currency") != "EUR":
        raise RuntimeError("keine EUR-Kurse")
    kurs, aktien = serie[-1][1], fi.get("shares")
    mk = kurs * aktien if aktien else fi.get("marketCap")
    gj = t.income_stmt
    bil, cf = t.balance_sheet, t.cashflow
    cols = list(gj.columns)[:2]
    a_c, v_c = (cols + [None, None])[:2]
    g = lambda df, c, *n: posten(df, c if c in df.columns else None, n) if c is not None else None
    umsatz, vumsatz = g(gj, a_c, "Total Revenue"), g(gj, v_c, "Total Revenue")
    ebit, ebitda = g(gj, a_c, "EBIT", "Operating Income"), g(gj, a_c, "EBITDA", "Normalized EBITDA")
    jue, vjue = g(gj, a_c, "Net Income Common Stockholders", "Net Income"), g(gj, v_c, "Net Income Common Stockholders", "Net Income")
    eps = g(gj, a_c, "Diluted EPS", "Basic EPS")
    ek, bs = g(bil, a_c, "Common Stock Equity", "Stockholders Equity"), g(bil, a_c, "Total Assets")
    schulden, cash = g(bil, a_c, "Total Debt"), g(bil, a_c, "Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments")
    netto = g(bil, a_c, "Net Debt")
    if netto is None and schulden is not None and cash is not None:
        netto = schulden - cash
    fcf = g(cf, a_c, "Free Cash Flow")
    div = t.dividends
    d12 = float(div[div.index > h.index[-1] - pd.Timedelta(days=365)].sum()) if div is not None and len(div) else None
    m = 1e6
    w = {
        "marktkap": mk / m if mk else None, "kurs": kurs,
        "r_ytd": kurs / ([c for d, c in serie if d < f"{serie[-1][0][:4]}-01-01"] or [None])[-1] - 1 if [c for d, c in serie if d < f"{serie[-1][0][:4]}-01-01"] else None,
        "r_1j": kurs / serie[max(0, len(serie) - 260)][1] - 1,
        "kgv": q(kurs, eps) if eps and eps > 0 else None,
        "kbv": q(mk, ek) if ek and ek > 0 else None,
        "kuv": q(mk, umsatz),
        "ev_ebitda": q((mk + netto) if mk and netto is not None else None, ebitda) if ebitda and ebitda > 0 else None,
        "div_rendite": q(d12, kurs) if d12 is not None else None,
        "umsatz": umsatz / m if umsatz else None, "ebitda": ebitda / m if ebitda else None, "ebit": ebit / m if ebit else None, "jue": jue / m if jue is not None else None,
        "ebitda_marge": q(ebitda, umsatz), "ebit_marge": q(ebit, umsatz), "netto_marge": q(jue, umsatz),
        "roe": q(jue, ek) if ek and ek > 0 else None, "roa": q(jue, bs),
        "bilanzsumme": bs / m if bs else None, "ek": ek / m if ek is not None else None, "ek_quote": q(ek, bs),
        "nettoschulden": netto / m if netto is not None else None,
        "verschuldung": q(netto, ebitda) if ebitda and ebitda > 0 and netto is not None else None,
        "fcf": fcf / m if fcf is not None else None, "fcf_marge": q(fcf, umsatz),
        "w_umsatz": wachstum(umsatz, vumsatz), "w_jue": wachstum(jue, vjue),
    }
    w = {k: (None if isinstance(v, float) and not math.isfinite(v) else v) for k, v in w.items()}
    return {"name": name, "ticker": ticker, "branche": branche, "segment": "Stichprobe",
            "gj": a_c.year if a_c is not None else None, "werte": {k: v for k, v in w.items() if v is not None},
            "kurse": serie[-260:], "datum": serie[-1][0]}


def main():
    out, fehler = [], []
    for branche, liste in STICHPROBE.items():
        for name, ticker in liste:
            try:
                out.append(abruf(name, ticker, branche))
            except Exception as ex:
                fehler.append(f"{ticker}: {ex}")
    d = {"quelle": "Stichprobe über Yahoo Finance (yfinance), Konzernabschlüsse, Beträge in Mio. €",
         "abruf": datetime.now(timezone.utc).isoformat(timespec="seconds"), "unternehmen": out, "fehler": fehler}
    (HIER / "data").mkdir(exist_ok=True)
    (HIER / "data/unternehmen_demo.json").write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(out)} Unternehmen, {len(fehler)} Fehler")
    for f in fehler:
        print("  ", f)


if __name__ == "__main__":
    main()
