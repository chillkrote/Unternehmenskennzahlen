"""Erzeugt die Excel-Auswertungen je Branche und die Gesamtübersicht.

Eingaben:
  universum/universum.csv, universum/universum_instrumente.csv
  rohdaten/yahoo/<ISIN>.json                       (yahoo_abruf.py)
  rohdaten/bafin/stimmrechte_gesamtexport_*.csv    (BaFin-Datenbank bedeutender Stimmrechtsanteile, Gesamtexport)
  rohdaten/berichte_kennzahlen.json                (optional: aus den Geschäftsberichten erhobene Werte, z. B. Mitarbeiter, Segmente)
  <branche>/dokumente/index.csv                    (berichte_laden.py)
Ausgaben:
  <branche>/auswertung/<Branche>_Kennzahlen_GJ2025.xlsx
  auswertung/Boersennotierte_Unternehmen_Gesamtuebersicht.xlsx

Beträge in Mio. der Berichtswährung (Spalte Währung), Kurse in Handelswährung, Börsenwert in Mio. Handelswährung.
"""
import csv
import glob
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HIER = Path(__file__).resolve().parent
BASIS = HIER.parent
sys.path.insert(0, str(BASIS / "universum" / "skripte"))
from universum import BRANCHEN  # noqa: E402
from unternehmen import schluessel  # noqa: E402

STAND = date.today().strftime("%d.%m.%Y")
MIO = 1e6

# --- Posten (erster vorhandener Yahoo-Name gewinnt) -------------------------------------------------------------
GUV = [
    ("Umsatzerlöse", ["Total Revenue", "Operating Revenue"]),
    ("Umsatzkosten", ["Cost Of Revenue", "Reconciled Cost Of Revenue"]),
    ("Bruttoergebnis", ["Gross Profit"]),
    ("Forschung und Entwicklung", ["Research And Development"]),
    ("Vertriebs- und Verwaltungskosten", ["Selling General And Administration"]),
    ("Operativer Aufwand", ["Operating Expense"]),
    ("Operatives Ergebnis", ["Operating Income", "Total Operating Income As Reported"]),
    ("EBITDA", ["EBITDA", "Normalized EBITDA"]),
    ("Abschreibungen", ["Reconciled Depreciation", "Depreciation And Amortization In Income Statement"]),
    ("EBIT", ["EBIT"]),
    ("Zinserträge", ["Interest Income", "Interest Income Non Operating"]),
    ("Zinsaufwand", ["Interest Expense", "Interest Expense Non Operating"]),
    ("Zinsergebnis", ["Net Interest Income", "Net Non Operating Interest Income Expense"]),
    ("Sondereffekte", ["Total Unusual Items"]),
    ("Ergebnis vor Steuern", ["Pretax Income"]),
    ("Ertragsteuern", ["Tax Provision"]),
    ("Ergebnis fortgeführte Aktivitäten", ["Net Income Continuous Operations"]),
    ("Ergebnis aufgegebene Aktivitäten", ["Net Income Discontinuous Operations"]),
    ("Konzernergebnis inkl. Minderheiten", ["Net Income Including Noncontrolling Interests"]),
    ("Minderheitenanteile", ["Minority Interests"]),
    ("Ergebnis Aktionäre", ["Net Income Common Stockholders", "Net Income"]),
    ("Ergebnis je Aktie unverwässert", ["Basic EPS"]),
    ("Ergebnis je Aktie verwässert", ["Diluted EPS"]),
    ("Ø Aktien unverwässert (Mio.)", ["Basic Average Shares"]),
    ("Versicherungsleistungen", ["Net Policyholder Benefits And Claims", "Insurance And Claims"]),
]
BILANZ = [
    ("Bilanzsumme", ["Total Assets"]),
    ("Langfristige Vermögenswerte", ["Total Non Current Assets"]),
    ("Sachanlagen", ["Net PPE"]),
    ("Geschäfts- oder Firmenwert", ["Goodwill"]),
    ("Goodwill und immaterielle Werte", ["Goodwill And Other Intangible Assets"]),
    ("Als Finanzinvestition gehaltene Immobilien", ["Investment Properties"]),
    ("Finanzanlagen und Beteiligungen", ["Investmentin Financial Assets", "Long Term Equity Investment"]),
    ("Aktive latente Steuern", ["Non Current Deferred Taxes Assets"]),
    ("Kurzfristige Vermögenswerte", ["Current Assets"]),
    ("Vorräte", ["Inventory"]),
    ("Forderungen LuL", ["Accounts Receivable", "Receivables"]),
    ("Liquide Mittel", ["Cash And Cash Equivalents", "Cash Financial"]),
    ("Liquide Mittel und kurzfr. Anlagen", ["Cash Cash Equivalents And Short Term Investments"]),
    ("Eigenkapital gesamt", ["Total Equity Gross Minority Interest"]),
    ("Eigenkapital Aktionäre", ["Common Stock Equity", "Stockholders Equity"]),
    ("Minderheitenanteile im EK", ["Minority Interest"]),
    ("Gezeichnetes Kapital", ["Capital Stock", "Common Stock"]),
    ("Kapitalrücklage", ["Additional Paid In Capital"]),
    ("Gewinnrücklagen", ["Retained Earnings"]),
    ("Fremdkapital", ["Total Liabilities Net Minority Interest"]),
    ("Langfristige Schulden", ["Total Non Current Liabilities Net Minority Interest"]),
    ("Pensionsrückstellungen", ["Non Current Pension And Other Postretirement Benefit Plans", "Pensionand Other Post Retirement Benefit Plans Current"]),
    ("Langfristige Rückstellungen", ["Long Term Provisions"]),
    ("Kurzfristige Schulden", ["Current Liabilities"]),
    ("Verbindlichkeiten LuL", ["Accounts Payable", "Payables"]),
    ("Finanzschulden gesamt", ["Total Debt"]),
    ("davon Leasing", ["Capital Lease Obligations"]),
    ("Nettofinanzschulden (Yahoo)", ["Net Debt"]),
    ("Working Capital", ["Working Capital"]),
    ("Materielles Eigenkapital", ["Tangible Book Value"]),
    ("Ausgegebene Aktien (Mio.)", ["Ordinary Shares Number", "Share Issued"]),
    ("Eigene Aktien (Mio.)", ["Treasury Shares Number"]),
]
CASHFLOW = [
    ("Operativer Cashflow", ["Operating Cash Flow"]),
    ("Investitions-Cashflow", ["Investing Cash Flow"]),
    ("Finanzierungs-Cashflow", ["Financing Cash Flow"]),
    ("Investitionen Sachanlagen/Immaterielle (Capex)", ["Capital Expenditure", "Capital Expenditure Reported"]),
    ("Free Cashflow", ["Free Cash Flow"]),
    ("Abschreibungen (CF)", ["Depreciation And Amortization"]),
    ("Veränderung Working Capital", ["Change In Working Capital"]),
    ("Unternehmenserwerbe", ["Purchase Of Business"]),
    ("Gezahlte Dividenden", ["Cash Dividends Paid", "Common Stock Dividend Paid"]),
    ("Aktienrückkauf", ["Repurchase Of Capital Stock", "Common Stock Payments"]),
    ("Kapitalerhöhung", ["Issuance Of Capital Stock", "Common Stock Issuance"]),
    ("Aufnahme Finanzschulden", ["Issuance Of Debt"]),
    ("Tilgung Finanzschulden", ["Repayment Of Debt"]),
    ("Gezahlte Zinsen", ["Interest Paid Cff", "Interest Paid Cfo"]),
    ("Gezahlte Steuern", ["Taxes Refund Paid"]),
    ("Liquide Mittel Periodenende", ["End Cash Position"]),
]
STUECK = {"Ergebnis je Aktie unverwässert", "Ergebnis je Aktie verwässert"}  # nicht in Mio.


def posten(tab, jahr, namen):
    v = (tab or {}).get(jahr) or {}
    for n in namen:
        if v.get(n) is not None:
            return v[n]
    return None


def mio(name, v):
    if v is None:
        return None
    if name in STUECK:
        return round(v, 4)
    return round(v / MIO, 3)


def teile(a, b, faktor=1.0):
    if a is None or b in (None, 0):
        return None
    return a / b * faktor


# --- Daten laden -------------------------------------------------------------------------------------------------
def lade():
    uni = list(csv.DictReader(open(BASIS / "universum" / "universum.csv", encoding="utf-8-sig"), delimiter=";"))
    yahoo = {}
    for p in glob.glob(str(BASIS / "rohdaten" / "yahoo" / "[A-Z]*.json")):
        d = json.load(open(p, encoding="utf-8"))
        yahoo[d["isin"]] = d
    bafin = []
    for p in sorted(glob.glob(str(BASIS / "rohdaten" / "bafin" / "stimmrechte_gesamtexport_*.csv")))[-1:]:
        for r in csv.reader(open(p, encoding="utf-8-sig"), delimiter=";"):
            if len(r) >= 10:
                z = lambda s: float(s.replace(",", ".")) if s.strip() else None  # noqa: E731
                bafin.append({"emittent": r[0], "sitz": r[1], "land": r[2], "meldepflichtiger": r[3], "m_sitz": r[4],
                              "m_land": r[5], "stimmrechte": z(r[6]), "instrumente": z(r[7]), "summe": z(r[8]), "datum": r[9],
                              "quelle": Path(p).name})
    zusatz = {}
    p = BASIS / "rohdaten" / "berichte_kennzahlen.json"
    if p.exists():
        zusatz = json.loads(p.read_text(encoding="utf-8"))
    ap = BASIS / "rohdaten" / "berichte_abgleich.json"
    if ap.exists():
        for uid, berichte in json.loads(ap.read_text(encoding="utf-8")).items():
            gut = [(sum(1 for a in r["abgleich"].values() if a.get("bestaetigt")), len(r.get("segmente", [])), n, r)
                   for n, r in berichte.items() if "abgleich" in r]
            if gut:
                _, _, n, r = max(gut, key=lambda g: g[:2])
                zusatz.setdefault(uid, {}).update({"abgleich": r["abgleich"], "bericht_datei": n,
                                                    "bericht_mitarbeiter": r.get("mitarbeiter_kandidaten", []),
                                                    "bericht_dividende": r.get("dividende_kandidaten", []),
                                                    "bericht_segmente": r.get("segmente", [])})
    dok = {}
    for p in glob.glob(str(BASIS / "*" / "dokumente" / "index.csv")):
        for z in csv.DictReader(open(p, encoding="utf-8-sig"), delimiter=";"):
            z["branche"] = Path(p).parts[-3]
            dok.setdefault(z["unternehmen_id"], []).append(z)
    return uni, yahoo, bafin, zusatz, dok


def bafin_zuordnung(uni, bafin):
    """Ordnet die Meldungen den Unternehmen über den normierten Emittentennamen zu."""
    idx = {}
    for u in uni:
        for n in {u["name"], u.get("name_boerse", "")}:
            if n:
                idx.setdefault(schluessel(n), u["unternehmen_id"])
        if u.get("bafin_name"):
            idx[schluessel(u["bafin_name"])] = u["unternehmen_id"]
    def finde(name):
        k = schluessel(name)
        if k in idx:
            return idx[k]
        # Präfix-Treffer (z. B. "merck" ~ "merck kommanditgesellschaft auf aktien"), nur wenn eindeutig
        t = [uid for kk, uid in idx.items() if len(kk) >= 4 and (k.startswith(kk + " ") or kk.startswith(k + " "))]
        return t[0] if len(set(t)) == 1 else None
    out = {}
    for b in bafin:
        uid = finde(b["emittent"])
        if uid:
            out.setdefault(uid, []).append(b)
    for v in out.values():
        v.sort(key=lambda b: -(b["summe"] if b["summe"] is not None else (b["stimmrechte"] or 0)))
    return out


def jahre(d):
    ys = sorted({j for j in (d.get("guv") or {}) if re.match(r"\d{4}-", j)} | {j for j in (d.get("bilanz") or {}) if re.match(r"\d{4}-", j)}, reverse=True)
    return ys[:5]


def dividenden_je_jahr(d):
    out = {}
    for tag, v in (d.get("dividenden") or {}).items():
        out[int(tag[:4])] = out.get(int(tag[:4]), 0) + (v or 0)
    return out


def jahresschluss(d):
    out = {}
    for tag, v in sorted((d.get("kurse_monat") or {}).items()):
        out[int(tag[:4])] = v  # letzter Monatswert des Jahres
    return out


# --- Zeilen bauen ------------------------------------------------------------------------------------------------
# Offensichtliche Datenfehler (Yahoo-Felder bei Holdings, Sonderfällen) nicht anzeigen; als Anteil (1,0 = 100 %)
GRENZEN = {"Ausschüttungsquote (Yahoo)": (0, 3), "Dividendenrendite": (0, 0.5), "EBIT-Marge": (-5, 1),
           "Nettomarge": (-5, 1), "KGV (12M, Yahoo)": (0, 1000), "KGV (GJ)": (0, 1000)}


def plausibel(z):
    for k, (lo, hi) in GRENZEN.items():
        v = z.get(k)
        if isinstance(v, (int, float)) and not lo <= v <= hi:
            z[k] = None
    return z


def zeile_uebersicht(u, d, bafin, dok, zusatz):
    info = (d or {}).get("info", {})
    js = jahre(d or {})
    j0 = js[0] if js else None
    g = lambda n: posten(d.get("guv"), j0, n) if d else None  # noqa: E731
    b = lambda n: posten(d.get("bilanz"), j0, n) if d else None  # noqa: E731
    c = lambda n: posten(d.get("cashflow"), j0, n) if d else None  # noqa: E731
    ums, ebitda, ebit = g(["Total Revenue", "Operating Revenue"]), g(["EBITDA", "Normalized EBITDA"]), g(["EBIT"])
    jue = g(["Net Income Common Stockholders", "Net Income"])
    bs, ek = b(["Total Assets"]), b(["Total Equity Gross Minority Interest"])
    eka = b(["Common Stock Equity", "Stockholders Equity"])
    schulden, liq = b(["Total Debt"]), b(["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"])
    netto = (schulden - liq) if schulden is not None and liq is not None else None
    ocf, fcf = c(["Operating Cash Flow"]), c(["Free Cash Flow"])
    ums_v = posten(d.get("guv"), js[1], ["Total Revenue", "Operating Revenue"]) if d and len(js) > 1 else None
    kurs = (d or {}).get("kurs_letzter", {}).get("schluss") or info.get("currentPrice") or info.get("regularMarketPrice")
    mcap = info.get("marketCap")
    aktien = info.get("sharesOutstanding") or b(["Ordinary Shares Number", "Share Issued"])
    mcap_berechnet = False
    if mcap is None and kurs and aktien:
        mcap, mcap_berechnet = kurs * aktien, True  # Yahoo liefert keinen Börsenwert: Kurs × Aktienzahl laut Bilanz
    gross = bafin.get(u["unternehmen_id"], [])
    fremd = [x for x in gross if schluessel(x["meldepflichtiger"]) != schluessel(x["emittent"])]
    top = fremd[0] if fremd else None
    dk = sorted(dok.get(u["unternehmen_id"], []), key=lambda x: x["geschaeftsjahr"], reverse=True)
    div = dividenden_je_jahr(d or {})
    gleiche_waehrung = info.get("financialCurrency") in (None, info.get("currency"))
    hinweise = []
    if not d:
        hinweise.append("keine Yahoo-Daten")
    else:
        if not js:
            hinweise.append("kein Abschluss bei Yahoo")
        elif not j0.startswith(("2025", "2026")):
            hinweise.append(f"letzter Abschluss {j0[:4]}, nicht GJ 2025")
        if not gleiche_waehrung:
            hinweise.append(f"Berichtswährung {info.get('financialCurrency')} ≠ Kurswährung {info.get('currency')}")
        if mcap is None:
            hinweise.append("Börsenwert fehlt")
        elif mcap_berechnet:
            hinweise.append("Börsenwert = Kurs × Aktienzahl laut Bilanz (Yahoo liefert keinen)")
        if js and ums is None and ebit is None and jue is None:
            hinweise.append("GuV leer")
        if ums is not None and ums_v and abs(ums / ums_v - 1) > 2:
            hinweise.append("Umsatz ändert sich um mehr als 200 % zum Vorjahr, prüfen")
        if bs is not None and ek is not None and bs and abs(ek) > bs * 1.05:
            hinweise.append("Eigenkapital größer als Bilanzsumme, prüfen")
        if kurs and info.get("sharesOutstanding") and mcap and abs(kurs * info["sharesOutstanding"] / mcap - 1) > 0.5:
            hinweise.append("Börsenwert weicht stark von Kurs × Aktienzahl ab (mehrere Gattungen?)")
    z = zusatz.get(u["unternehmen_id"], {})
    ab = z.get("abgleich") or {}
    if ab:
        ok = [k for k, a in ab.items() if a.get("bestaetigt")]
        if len(ok) < len([a for a in ab.values() if a.get("yahoo")]) / 2:
            hinweise.append(f"nur {len(ok)} von {len(ab)} Yahoo-Kennzahlen im Bericht wiedergefunden, prüfen")
    ma = z.get("bericht_mitarbeiter") or []
    mitarb = z.get("mitarbeiter") or info.get("fullTimeEmployees")
    if mitarb is None and ma and ma[0][1] >= 3:
        mitarb = ma[0][0]
        hinweise.append("Mitarbeiterzahl häufigster Wert im Bericht, ungeprüft")
    z = {
        "Hinweise zur Datenqualität": "; ".join(hinweise) or None,
        "Unternehmen": u["name"], "ISIN": u["isin_haupt"], "Weitere Gattungen": u["weitere_isins"], "Kürzel": u["kuerzel"],
        "Yahoo-Ticker": u["yahoo"], "Segment": u["segment"], "Weitere Segmente": u["weitere_segmente"], "Index": u["index"],
        "Land": u["land"], "Sitz (Yahoo)": u["sitz"], "Subsektor (Börse)": u["subsektor_db"], "Industrie (Yahoo)": u["industrie_yahoo"],
        "Website": u["website"],
        "Letztes GJ (Ende)": j0, "Berichtswährung": info.get("financialCurrency"),
        "Mitarbeiter": mitarb,
        "Mitarbeiter laut Bericht (Kandidaten)": ", ".join(f"{n} ({c}×)" for n, c in ma[:3]) or None,
        "Abgleich Yahoo mit Bericht": (" · ".join(f"{k} {'✓' if a.get('bestaetigt') else '✗'}" for k, a in ab.items()) if ab else None),
        "Dividende je Aktie laut Bericht (Kandidaten)": ", ".join(f"{n} ({c}×)" for n, c in (z.get("bericht_dividende") or [])[:3]) or None,
        "Umsatz (Mio.)": mio("", ums), "Umsatzwachstum": teile(ums - ums_v, abs(ums_v)) if ums is not None and ums_v else None,
        "EBITDA (Mio.)": mio("", ebitda), "EBIT (Mio.)": mio("", ebit), "EBIT-Marge": teile(ebit, ums),
        "Ergebnis Aktionäre (Mio.)": mio("", jue), "Nettomarge": teile(jue, ums),
        "EPS verwässert": posten(d.get("guv"), j0, ["Diluted EPS", "Basic EPS"]) if d else None,
        "Bilanzsumme (Mio.)": mio("", bs), "Eigenkapital (Mio.)": mio("", ek), "EK-Quote": teile(ek, bs),
        "EK-Rendite (EK Aktionäre)": teile(jue, eka), "Nettofinanzschulden (Mio.)": mio("", netto),
        "Nettoschulden/EBITDA": teile(netto, ebitda) if ebitda and ebitda > 0 else None,
        "Operativer Cashflow (Mio.)": mio("", ocf), "Free Cashflow (Mio.)": mio("", fcf),
        "Handelswährung": info.get("currency"), "Kurs": kurs, "Kursdatum": (d or {}).get("kurs_letzter", {}).get("datum"),
        "Aktien (Mio.)": mio("", aktien), "Börsenwert (Mio.)": mio("", mcap),
        "Enterprise Value (Mio.)": mio("", info.get("enterpriseValue")),
        "KGV (GJ)": teile(mcap, jue) if gleiche_waehrung and jue and jue > 0 else None,
        "KGV (12M, Yahoo)": info.get("trailingPE"), "KGV erwartet (Yahoo)": info.get("forwardPE"),
        "KBV": teile(mcap, eka) if gleiche_waehrung and eka and eka > 0 else info.get("priceToBook"),
        "KUV (12M)": info.get("priceToSalesTrailing12Months"), "EV/EBITDA (12M)": info.get("enterpriseToEbitda"),
        "EV/Umsatz (12M)": info.get("enterpriseToRevenue"),
        "Dividende je Aktie (letzte 12M)": info.get("trailingAnnualDividendRate"),
        "Dividendenrendite": teile(info.get("trailingAnnualDividendRate"), kurs) if kurs else None,
        "Dividende gezahlt 2025": div.get(2025), "Dividende gezahlt 2026": div.get(2026),
        "Ausschüttungsquote (Yahoo)": info.get("payoutRatio"),
        "Kursänderung 52W": info.get("52WeekChange") if info.get("52WeekChange") is not None else (info.get("fiftyTwoWeekChangePercent") / 100 if info.get("fiftyTwoWeekChangePercent") is not None else None),
        "52W-Hoch": info.get("fiftyTwoWeekHigh"), "52W-Tief": info.get("fiftyTwoWeekLow"), "Beta": info.get("beta"),
        "Ø Volumen 3M (Stück)": info.get("averageVolume"),
        "Größter Meldepflichtiger (BaFin)": top["meldepflichtiger"] if top else None,
        "Anteil Stimmrechte % (BaFin)": (top["summe"] if top["summe"] is not None else top["stimmrechte"]) if top else None,
        "Meldung vom": top["datum"] if top else None, "Anzahl Meldepflichtige (BaFin)": len(fremd) or None,
        "Eigene Aktien % (BaFin)": next(((x["summe"] if x["summe"] is not None else x["stimmrechte"]) for x in gross if x not in fremd), None),
        "Insider % (Yahoo)": info.get("heldPercentInsiders"), "Institutionen % (Yahoo)": info.get("heldPercentInstitutions"),
        "Geschäftsbericht (Repo)": dk[0]["datei"] if dk else None, "Geschäftsbericht (Quelle)": dk[0]["quelle_url"] if dk else None,
    }
    return plausibel(z)


PROZENT = {"Umsatzwachstum", "EBIT-Marge", "Nettomarge", "EK-Quote", "EK-Rendite (EK Aktionäre)", "Dividendenrendite",
           "Ausschüttungsquote (Yahoo)", "Kursänderung 52W", "Insider % (Yahoo)", "Institutionen % (Yahoo)",
           "Bruttomarge", "EBITDA-Marge", "FCF-Marge", "Capex/Umsatz", "Gesamtkapitalrendite", "Steuerquote", "Ausschüttung/Ergebnis"}


def zeilen_abschluss(u, d, liste, schluessel_tab):
    out = []
    if not d:
        return out
    tab = d.get(schluessel_tab) or {}
    for j in sorted((k for k in tab if re.match(r"\d{4}-", k)), reverse=True)[:5]:
        z = {"Unternehmen": u["name"], "ISIN": u["isin_haupt"], "GJ-Ende": j, "Währung": d["info"].get("financialCurrency")}
        werte = {name: mio(name, posten(tab, j, namen)) for name, namen in liste}
        if not any(v is not None for v in werte.values()):
            continue
        z.update(werte)
        out.append(z)
    return out


def zeilen_kennzahlen(u, d):
    out = []
    if not d:
        return out
    js = sorted({k for k in (d.get("guv") or {}) if re.match(r"\d{4}-", k)}, reverse=True)[:5]
    for i, j in enumerate(js):
        g = lambda n: posten(d.get("guv"), j, n)  # noqa: E731
        b = lambda n: posten(d.get("bilanz"), j, n)  # noqa: E731
        c = lambda n: posten(d.get("cashflow"), j, n)  # noqa: E731
        ums = g(["Total Revenue", "Operating Revenue"])
        vor = posten(d.get("guv"), js[i + 1], ["Total Revenue", "Operating Revenue"]) if i + 1 < len(js) else None
        ebitda, ebit, jue = g(["EBITDA", "Normalized EBITDA"]), g(["EBIT"]), g(["Net Income Common Stockholders", "Net Income"])
        bs, ek, eka = b(["Total Assets"]), b(["Total Equity Gross Minority Interest"]), b(["Common Stock Equity", "Stockholders Equity"])
        schulden, liq = b(["Total Debt"]), b(["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"])
        netto = schulden - liq if schulden is not None and liq is not None else None
        capex, fcf, div = c(["Capital Expenditure"]), c(["Free Cash Flow"]), c(["Cash Dividends Paid", "Common Stock Dividend Paid"])
        vst, st = g(["Pretax Income"]), g(["Tax Provision"])
        out.append({
            "Unternehmen": u["name"], "ISIN": u["isin_haupt"], "GJ-Ende": j, "Währung": d["info"].get("financialCurrency"),
            "Umsatzwachstum": teile(ums - vor, abs(vor)) if ums is not None and vor else None,
            "Bruttomarge": teile(g(["Gross Profit"]), ums), "EBITDA-Marge": teile(ebitda, ums), "EBIT-Marge": teile(ebit, ums),
            "Nettomarge": teile(jue, ums), "EK-Rendite (EK Aktionäre)": teile(jue, eka), "Gesamtkapitalrendite": teile(jue, bs),
            "EK-Quote": teile(ek, bs), "Nettofinanzschulden (Mio.)": mio("", netto),
            "Nettoschulden/EBITDA": teile(netto, ebitda) if ebitda and ebitda > 0 else None,
            "Capex/Umsatz": teile(-capex if capex else None, ums), "FCF-Marge": teile(fcf, ums),
            "Steuerquote": teile(st, vst) if vst and vst > 0 else None,
            "Ausschüttung/Ergebnis": teile(-div if div else None, jue) if jue and jue > 0 else None,
            "Umsatz je Mitarbeiter (Tsd., aktuelle MA-Zahl)": teile(ums, d["info"].get("fullTimeEmployees"), 1e-3) if i == 0 else None,
        })
    return out


def zeilen_markt(u, d):
    if not d:
        return []
    js, div = jahresschluss(d), dividenden_je_jahr(d)
    z = {"Unternehmen": u["name"], "ISIN": u["isin_haupt"], "Ticker": d["ticker"], "Währung": d["info"].get("currency")}
    for y in range(2019, 2026):
        z[f"Kurs Ende {y}"] = js.get(y)
    z["Kurs aktuell"] = d.get("kurs_letzter", {}).get("schluss")
    z["Kursdatum"] = d.get("kurs_letzter", {}).get("datum")
    for y in range(2019, 2027):
        z[f"Dividende {y}"] = div.get(y)
    for y in (2021, 2023, 2024, 2025):
        a, e = js.get(y - 1), js.get(2025)
        z[f"Kursänderung {y - 1}–2025" if y != 2025 else "Kursänderung 2025"] = teile(e - a, a) if a and e is not None else None
    return [z]


def zeilen_aktionaere(u, bafin):
    return [{"Unternehmen": u["name"], "ISIN": u["isin_haupt"], "Emittent (BaFin)": b["emittent"],
             "Meldepflichtiger": b["meldepflichtiger"], "Sitz": b["m_sitz"], "Land": b["m_land"],
             "Stimmrechte §§ 33, 34 WpHG %": b["stimmrechte"], "Instrumente § 38 WpHG %": b["instrumente"],
             "Summe § 39 WpHG %": b["summe"], "Veröffentlichung": b["datum"]} for b in bafin.get(u["unternehmen_id"], [])]


def zeilen_roh(u, d):
    out = []
    if not d:
        return out
    for tab_name, tab in (("GuV", d.get("guv")), ("Bilanz", d.get("bilanz")), ("Cashflow", d.get("cashflow"))):
        for j, werte in sorted((tab or {}).items(), reverse=True):
            if not isinstance(werte, dict):
                continue
            for k, v in sorted(werte.items()):
                out.append({"Unternehmen": u["name"], "ISIN": u["isin_haupt"], "Rechenwerk": tab_name, "GJ-Ende": j,
                            "Posten (Yahoo)": k, "Wert": v})
    return out


def zeilen_abgleich(u, zusatz, dok):
    z = zusatz.get(u["unternehmen_id"], {})
    out = []
    art = next((x["dokumentart"] for x in dok.get(u["unternehmen_id"], []) if x["datei"].endswith("/" + (z.get("bericht_datei") or "-"))), None)
    for k, a in (z.get("abgleich") or {}).items():
        y = a.get("yahoo") or {}
        neueste = max(y) if y else None
        kand = a.get("kandidat") or {}
        out.append({"Unternehmen": u["name"], "ISIN": u["isin_haupt"], "Kennzahl": k,
                    "Yahoo-Wert neuestes Jahr (Mio.)": mio("", y[neueste]) if neueste else None, "Yahoo-Jahr": neueste,
                    "im Bericht bestätigt": "ja" if a.get("bestaetigt") else ("nein" if y else "kein Yahoo-Wert"),
                    "bestätigtes Jahr": a.get("jahr"), "Seite im Bericht": a.get("seite"), "Einheit im Bericht": a.get("einheit"),
                    "Fundstelle (Textzeile)": a.get("zeile"),
                    "Berichtszeile (erste Tabellenzeile, ungeprüft)": kand.get("zeile"), "Seite Berichtszeile": kand.get("seite"),
                    "Einheit laut Tabellenkopf (vermutet)": kand.get("einheit"), "Bericht": z.get("bericht_datei"), "Dokumentart": art})
    return out


def zeilen_segmente(u, zusatz):
    z = zusatz.get(u["unternehmen_id"], {})
    out = []
    for seg in z.get("bericht_segmente", []):
        kopf = " | ".join(seg.get("ueberschrift", [])[:3])
        for zeile in seg.get("zeilen", []):
            out.append({"Unternehmen": u["name"], "ISIN": u["isin_haupt"], "Seite im Bericht": seg["seite"], "Überschrift": kopf,
                        "Zeile (Bezeichnung und Werte)": zeile, "Einheit (vermutet)": seg.get("einheit"), "Bericht": z.get("bericht_datei")})
    return out


def zeilen_zusatz(u, zusatz):
    z = zusatz.get(u["unternehmen_id"])
    if not z:
        return []
    out = []
    for seg in z.get("segmente", []):
        out.append({"Unternehmen": u["name"], "ISIN": u["isin_haupt"], **seg})
    return out


# --- Excel -------------------------------------------------------------------------------------------------------
ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
KOPF_FILL = PatternFill("solid", fgColor="1F3864")
KOPF_FONT = Font(color="FFFFFF", bold=True)


def blatt(wb, titel, zeilen, hinweis=None, breite=None):
    ws = wb.create_sheet(titel[:31])
    start = 1
    if hinweis:
        ws.cell(1, 1, hinweis).font = Font(italic=True, color="555555")
        start = 3
    if not zeilen:
        ws.cell(start, 1, "keine Daten")
        return ws
    spalten = list(dict.fromkeys(k for z in zeilen for k in z))
    for i, s in enumerate(spalten, 1):
        c = ws.cell(start, i, s)
        c.fill, c.font = KOPF_FILL, KOPF_FONT
        c.alignment = Alignment(wrap_text=True, vertical="top")
    for r, z in enumerate(zeilen, start + 1):
        for i, s in enumerate(spalten, 1):
            v = z.get(s)
            if isinstance(v, str):
                v = ILLEGAL.sub("", v)
            c = ws.cell(r, i, v)
            if isinstance(v, float):
                if s in PROZENT:
                    c.number_format = "0.0%"
                elif abs(v) >= 100:
                    c.number_format = "#,##0"
                else:
                    c.number_format = "#,##0.00"
            if isinstance(v, str) and v.startswith("http"):
                c.hyperlink = v
                c.font = Font(color="0563C1", underline="single")
    ws.freeze_panes = ws.cell(start + 1, 3 if len(spalten) > 3 else 1)
    ws.auto_filter.ref = f"A{start}:{get_column_letter(len(spalten))}{start + len(zeilen)}"
    for i, s in enumerate(spalten, 1):
        ws.column_dimensions[get_column_letter(i)].width = breite or (32 if i == 1 else max(10, min(22, len(s) + 2)))
    ws.row_dimensions[start].height = 45
    return ws


METHODIK = [
    ("Erhebung", "Kennzahlen der in Deutschland notierten Aktiengesellschaften, Geschäftsjahr 2025 (bzw. letztes verfügbares), Stand {stand}"),
    ("Universum", "siehe universum/README.md: Frankfurter Wertpapierbörse (Prime Standard, General Standard, Scale, Basic Board), "
                  "Börse München m:access, Börse Düsseldorf Primärmarkt, weitere Aktien deutscher Emittenten im Freiverkehr/an Regionalbörsen"),
    ("Abschlussdaten", "Konzernabschlüsse laut Yahoo Finance (über yfinance), standardisierte Posten; Beträge in Mio. der Berichtswährung. "
                       "Bis zu vier/fünf Geschäftsjahre. Für Banken/Versicherungen sind Posten wie Umsatz/EBIT nur eingeschränkt aussagekräftig."),
    ("Kapitalmarktdaten", "Kurs, Börsenwert, Enterprise Value, Multiples (12 Monate), Dividenden, Monatskurse laut Yahoo Finance, Abruf {stand}. "
                          "KGV (GJ) und KBV = Börsenwert / Ergebnis bzw. EK der Aktionäre des letzten GJ, nur bei gleicher Handels- und Berichtswährung."),
    ("Stimmrechte", "BaFin-Datenbank bedeutender Stimmrechtsanteile (§§ 33, 34, 38, 39 WpHG), Gesamtexport. Zuordnung über den Emittentennamen. "
                    "Nur Emittenten im regulierten Markt sind meldepflichtig; für Freiverkehrswerte gibt es dort keine Einträge."),
    ("Mitarbeiter", "Vollzeitkräfte laut Yahoo (fullTimeEmployees), soweit nicht aus dem Geschäftsbericht erhoben."),
    ("Geschäftsberichte", "Originaldokumente unter <branche>/dokumente/<unternehmen>/, index.csv mit Quelle, Abrufdatum und SHA-256."),
    ("Rohdaten Yahoo", "Blatt mit allen von Yahoo gelieferten Posten je Geschäftsjahr (Originalbezeichnungen, volle Einheiten)."),
    ("Bekannte Grenzen", "Yahoo-Daten sind nicht geprüft und können von den Geschäftsberichten abweichen (Definitionen von EBITDA/EBIT, "
                         "Umgliederungen, aufgegebene Geschäftsbereiche). Segmentangaben und weitere Pflichtangaben werden schrittweise "
                         "aus den Geschäftsberichten ergänzt (Blatt Segmente, sobald erhoben)."),
]


def mappe(pfad, titel, firmen, yahoo, bafin, zusatz, dok, branchenspalte=False):
    wb = Workbook()
    wb.remove(wb.active)
    ueb, guv, bil, cf, kz, mk, akt, roh, seg, doks, abg, segb = [], [], [], [], [], [], [], [], [], [], [], []
    for u in firmen:
        d = yahoo.get(u["isin_haupt"])
        z = zeile_uebersicht(u, d, bafin, dok, zusatz)
        if branchenspalte:
            z = {"Branche": u["branche_name"], **z}
        ueb.append(z)
        guv += zeilen_abschluss(u, d, GUV, "guv")
        bil += zeilen_abschluss(u, d, BILANZ, "bilanz")
        cf += zeilen_abschluss(u, d, CASHFLOW, "cashflow")
        kz += zeilen_kennzahlen(u, d)
        mk += zeilen_markt(u, d)
        akt += zeilen_aktionaere(u, bafin)
        seg += zeilen_zusatz(u, zusatz)
        abg += zeilen_abgleich(u, zusatz, dok)
        segb += zeilen_segmente(u, zusatz)
        if not branchenspalte:
            roh += zeilen_roh(u, d)
        for x in dok.get(u["unternehmen_id"], []):
            doks.append({"Unternehmen": u["name"], "ISIN": u["isin_haupt"], "Dokumentart": x["dokumentart"],
                         "Geschäftsjahr": x["geschaeftsjahr"], "Datei (Repo)": f"{x['branche']}/{x['datei']}",
                         "Seiten": int(x["seiten"]) if x.get("seiten") else None, "Quelle": x["quelle_url"],
                         "Abruf": x["abruf"], "SHA-256": x["sha256"]})
    blatt(wb, "Übersicht", ueb, f"{titel}: {len(firmen)} Unternehmen. Beträge in Mio. Berichtswährung, letztes Geschäftsjahr laut Yahoo; Kapitalmarktdaten Stand {STAND}.")
    blatt(wb, "GuV", guv, "Konzern-GuV je Geschäftsjahr (Yahoo Finance), Mio. Berichtswährung; EPS in Währungseinheiten.")
    blatt(wb, "Bilanz", bil, "Konzernbilanz je Geschäftsjahr (Yahoo Finance), Mio. Berichtswährung.")
    blatt(wb, "Cashflow", cf, "Konzern-Kapitalflussrechnung je Geschäftsjahr (Yahoo Finance), Mio. Berichtswährung.")
    blatt(wb, "Kennzahlen", kz, "Aus GuV, Bilanz und Cashflow berechnet.")
    blatt(wb, "Kapitalmarkt", mk, "Jahresschlusskurse (letzter Monatsschluss, nicht dividendenbereinigt) und gezahlte Dividenden je Kalenderjahr (Ex-Tag).")
    blatt(wb, "Aktionäre (BaFin)", akt, "Stimmrechtsmitteilungen laut BaFin-Datenbank (Stand des Gesamtexports), absteigend nach Anteil.")
    if seg:
        blatt(wb, "Segmente", seg, "Segmentangaben aus den Geschäftsberichten.")
    blatt(wb, "Abgleich Bericht", abg, "Yahoo-Zahlen gegen den Geschäftsbericht im Repo: ist der Wert (irgendeines der letzten Jahre, in EUR/Tsd./Mio.) in einer passend bezeichneten Zeile des Berichts zu finden? Automatische Textsuche, Fundstelle zum Nachprüfen.")
    blatt(wb, "Segmente (Bericht)", segb, "Ungeprüfter Rohextrakt der Segmenttabellen aus dem Anhang der Geschäftsberichte (Zeilen mit Umsatz/Ergebnis/Vermögen/Investitionen usw.). Spalten und Einheit stehen im Bericht auf der angegebenen Seite.", breite=40)
    blatt(wb, "Dokumente", doks, "Im Repo abgelegte Originaldokumente.")
    if roh:
        blatt(wb, "Rohdaten Yahoo", roh, "Alle Posten wie von Yahoo geliefert (volle Einheiten, Berichtswährung).")
    ws = wb.create_sheet("Methodik")
    for i, (a, b) in enumerate(METHODIK, 1):
        ws.cell(i, 1, a).font = Font(bold=True)
        ws.cell(i, 2, b.format(stand=STAND)).alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 22, 120
    pfad.parent.mkdir(parents=True, exist_ok=True)
    wb.save(pfad)
    return len(ueb)


def readme_branche(slug, name, firmen, yahoo, dok, datei):
    mit_daten = sum(1 for u in firmen if (yahoo.get(u["isin_haupt"]) or {}).get("guv"))
    mit_dok = sum(1 for u in firmen if dok.get(u["unternehmen_id"]))
    zeilen = [f"# {name}", "",
              f"Teil der Erhebung [Börsennotierte Unternehmen in Deutschland](../README.md). Stand {STAND}.", ""]
    if slug == "banken":
        zeilen += ["Die Banken sind ausführlich im [Bilanzvergleich Banken GJ 2025](../../banken/bilanzvergleich-gj2025/) erhoben "
                   "(HGB-Bilanzen, Eigenmittel, Pillar-3-Offenlegung, Geschäftsberichte). Hier stehen nur die börsennotierten Banken "
                   "mit Kapitalmarktdaten und Konzernzahlen laut Yahoo; Dokumente liegen im Bankenordner.", ""]
    zeilen += [
        f"- **Unternehmen:** {len(firmen)} (Liste in `../universum/universum.csv`, Spalte `branche` = `{slug}`)",
        f"- **Abschlussdaten (Yahoo):** {mit_daten} von {len(firmen)}",
        f"- **Geschäftsberichte im Repo:** {mit_dok} von {len(firmen)} (`dokumente/`, Verzeichnis in `dokumente/index.csv`)",
        f"- **Auswertung:** [`auswertung/{datei.name}`](auswertung/{datei.name})", "",
        "| Unternehmen | Segment | Index | Geschäftsbericht |", "|---|---|---|---|"]
    for u in sorted(firmen, key=lambda u: u["name"].lower()):
        d = sorted(dok.get(u["unternehmen_id"], []), key=lambda x: x["geschaeftsjahr"], reverse=True)
        gb = f"[{d[0]['dokumentart']} {d[0]['geschaeftsjahr']}]({d[0]['datei']})" if d else "–"
        zeilen.append(f"| {u['name']} | {u['segment']} | {u['index'] or ''} | {gb} |")
    (BASIS / slug / "README.md").write_text("\n".join(zeilen) + "\n", encoding="utf-8")


def main():
    uni, yahoo, bafin_roh, zusatz, dok = lade()
    bafin = bafin_zuordnung(uni, bafin_roh)
    for slug, name in BRANCHEN.items():
        firmen = [u for u in uni if u["branche"] == slug]
        if not firmen:
            continue
        datei = BASIS / slug / "auswertung" / f"{slug.replace('-', '_').title()}_Kennzahlen_GJ2025.xlsx"
        n = mappe(datei, name, firmen, yahoo, bafin, zusatz, dok)
        readme_branche(slug, name, firmen, yahoo, dok, datei)
        print(f"{slug}: {n} Unternehmen -> {datei.relative_to(BASIS)}")
    n = mappe(BASIS / "auswertung" / "Boersennotierte_Unternehmen_Gesamtuebersicht.xlsx", "Alle Branchen",
              [u for u in uni if u["branche"]], yahoo, bafin, zusatz, dok, branchenspalte=True)
    print("gesamt:", n)


if __name__ == "__main__":
    main()
