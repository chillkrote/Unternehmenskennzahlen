"""Pilot: Prognosen internationaler Geber (Konsensumfragen und G7-Zentralbanken) -> prognosen_international.csv.

Quellen (alle frei, ohne Schlüssel; Bot-Schutz wird nicht umgangen):
  EZB SPF (API), Philadelphia Fed SPF (PDF), HM Treasury Forecasts for the UK economy (XLSX, mit Einzelprognostikern),
  Funcas Panel (PDF, mit Einzelpanelisten), Fed SEP (HTML), Bank of Canada MPR (PDF), Bank of Japan Outlook Report (PDF).
Die Rohdateien landen unverändert in rohdaten/prognosen/. Die Ausgabe ist ein Langformat wie prognosen_oecd.csv.
Die jeweils neueste Ausgabe wird über die Übersichtsseiten gefunden; ältere Ausgaben der Datei bleiben stehen, nur die
Zeilen derselben Ausgabe werden ersetzt. Abhängigkeiten: openpyxl, pdftotext (poppler).
"""
import csv, html, io, json, re, subprocess, sys, urllib.error, urllib.request
from datetime import date
from pathlib import Path

AUS = Path(__file__).resolve().parents[1]
ROH = AUS / "rohdaten" / "prognosen"
ZIEL = AUS / "prognosen_international.csv"
FELDER = ["geo", "herausgeber", "ausgabe", "veroeffentlicht", "groesse", "einheit", "jahr", "wert", "beleg", "url", "abruf", "hinweis"]
UA = "Mozilla/5.0 (compatible; Unternehmenskennzahlen-Abruf; +https://github.com/chillkrote/Unternehmenskennzahlen)"
HEUTE = date.today().isoformat()
MONATE = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def hole(url, accept="*/*"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    for versuch in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except (TimeoutError, urllib.error.URLError):
            if versuch == 2:
                raise


def speichere(name, daten):
    ROH.mkdir(parents=True, exist_ok=True)
    (ROH / name).write_bytes(daten)


def pdf_text(pfad):
    return subprocess.run(["pdftotext", "-layout", str(pfad), "-"], capture_output=True, text=True, check=True).stdout


def zahl(s):
    s = s.strip().replace("−", "-").replace("+", "").replace(",", ".")
    return None if s in ("", "--", "-", "N.A.", "n.a.") else float(s)


def z(geo, herausgeber, ausgabe, veroeffentlicht, groesse, einheit, jahr, wert, beleg, url, hinweis=""):
    if wert is None:
        return None
    return dict(geo=geo, herausgeber=herausgeber, ausgabe=ausgabe, veroeffentlicht=veroeffentlicht, groesse=groesse, einheit=einheit,
                jahr=jahr, wert=round(wert, 3), beleg=beleg, url=url, abruf=HEUTE, hinweis=hinweis)


# --- EZB Survey of Professional Forecasters (SDMX-CSV) -------------------------------------------------------------
def ezb_spf():
    basis = "https://data-api.ecb.europa.eu/service/data/SPF/Q.U2.{}...Q.AVG?startPeriod=2025-Q4&format=csvdata"
    zeilen, roh = [], []
    for thema in ("HICP", "RGDP", "UNEM"):
        url = basis.format(thema)
        txt = hole(url, "text/csv").decode("utf-8")
        roh.append(txt)
        for r in csv.DictReader(io.StringIO(txt)):
            if r["FCT_BREAKDOWN"] != "POINT" or not re.fullmatch(r"20\d\d|LT", r["FCT_HORIZON"]):
                continue
            if r["FCT_HORIZON"] in ("2030", "2031"):
                continue
            g = {"HICP": ("inflation_hvpi", "%"), "RGDP": ("bip_wachstum", "%"), "UNEM": ("arbeitslosenquote", "%")}[thema]
            jahr = "langfristig" if r["FCT_HORIZON"] == "LT" else r["FCT_HORIZON"]
            zeilen.append(z("EA20", "EZB Survey of Professional Forecasters (Mittelwert)", "SPF " + r["TIME_PERIOD"], "", g[0], g[1], jahr,
                            float(r["OBS_VALUE"]), "API", url.split("?")[0],
                            "Mittelwert der Punktprognosen der Teilnehmer; Euroraum; Jahresrate bzw. Jahresdurchschnitt; ausgabe = Umfragerunde"))
    speichere("ezb_spf.csv", "\n".join(roh).encode())
    return [x for x in zeilen if x]


# --- Philadelphia Fed SPF ----------------------------------------------------------------------------------------------
def philly_spf():
    seite = hole("https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/survey-of-professional-forecasters").decode("utf-8", "ignore")
    runden = sorted(set(re.findall(r"spf-q([1-4])-(20\d\d)", seite)), key=lambda m: (m[1], m[0]))
    q, jahr = runden[-1]
    unterseite = f"https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/spf-q{q}-{jahr}"
    s2 = hole(unterseite).decode("utf-8", "ignore")
    pdf = re.search(r'href="([^"]*spfQ%s%s\.pdf[^"]*)"' % (q, jahr[2:]), s2, re.I)
    url = "https://www.philadelphiafed.org" + html.unescape(pdf.group(1))
    daten = hole(url)
    speichere(f"philly_spf_q{q}_{jahr}.pdf", daten)
    t = pdf_text(ROH / f"philly_spf_q{q}_{jahr}.pdf")
    m = re.search(r"Release Date:\s*(\w+) (\d+), (\d{4})", t)
    veroeff = f"{m.group(3)}-{MONATE[m.group(1)[:3].lower()]:02d}-{int(m.group(2)):02d}"
    ausgabe = f"SPF {jahr}-Q{q}"
    ziel = "Philadelphia Fed Survey of Professional Forecasters (Median)"
    hin = "Median der Prognostiker; BIP und Arbeitslosenquote als Jahresdurchschnitt, Inflation Q4/Q4 (Wert der aktuellen Umfrage)"
    zeilen = []
    # BIP/Arbeitslosigkeit: Block 'Annual data' - Spalten: GDP prev/new, UR prev/new, payrolls prev/new
    blk = t[t.index("Annual data"):]
    for jahrzahl, a, b, c, d in re.findall(r"^\s*(20\d\d)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+\S+\s+\S+\s*$", blk, re.M)[:4]:
        zeilen.append(z("US", ziel, ausgabe, veroeff, "bip_wachstum", "%", jahrzahl, zahl(b), "Primärdokument", url, hin))
        zeilen.append(z("US", ziel, ausgabe, veroeff, "arbeitslosenquote", "%", jahrzahl, zahl(d), "Primärdokument", url, hin))
    blk = t[t.index("Q4/Q4 Annual Averages"):]
    for jahrzahl, a, b, c, d, e, f, g, h in re.findall(r"^\s*(20\d\d)\s+" + r"\s+".join([r"(\S+)"] * 8) + r"\s*$", blk, re.M)[:3]:
        zeilen.append(z("US", ziel, ausgabe, veroeff, "inflation_vpi", "%", jahrzahl, zahl(b), "Primärdokument", url, hin + "; Headline CPI Q4/Q4"))
        zeilen.append(z("US", ziel, ausgabe, veroeff, "inflation_pce", "%", jahrzahl, zahl(f), "Primärdokument", url, hin + "; Headline PCE Q4/Q4"))
    return [x for x in zeilen if x]


# --- HM Treasury: Forecasts for the UK economy (Konsens und Einzelprognostiker) --------------------------------------
def hmt():
    import openpyxl
    seite = hole("https://www.gov.uk/government/collections/data-forecasts").decode("utf-8", "ignore")
    slugs = re.findall(r"/government/statistics/(forecasts-for-the-uk-economy-([a-z]+)-(\d{4}))", seite)
    neu = max(slugs, key=lambda m: (m[2], ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"].index(m[1])))
    inh = json.loads(hole("https://www.gov.uk/api/content/government/statistics/" + neu[0]))
    xl = [a for a in inh["details"]["attachments"] if a["url"].endswith(".xlsx")][0]["url"]
    veroeff = inh["first_published_at"][:10]
    speichere("hmt_forecasts_uk.xlsx", hole(xl))
    wb = openpyxl.load_workbook(ROH / "hmt_forecasts_uk.xlsx", data_only=True)
    seiten = "https://www.gov.uk/government/statistics/" + neu[0]
    ausgabe = f"Forecasts for the UK economy {neu[1].capitalize()} {neu[2]}"
    # Tabelle 1/4: BIP (Spalte E), Tabelle 2/5: CPI (Spalte E, Q4/Q4), Tabelle 3/6: LFS-Arbeitslosenquote Q4 (Spalte I)
    tabellen = [("Table 1", 2026, "bip_wachstum", 4), ("Table 2", 2026, "inflation_vpi", 4), ("Table 3", 2026, "arbeitslosenquote", 8),
                ("Table 4", 2027, "bip_wachstum", 4), ("Table 5", 2027, "inflation_vpi", 4), ("Table 6", 2027, "arbeitslosenquote", 8)]
    zeilen = []
    sammel = {"Independent": "Konsens (Durchschnitt unabhängiger Prognostiker der letzten 3 Monate)", "Median": "Konsens (Median)"}
    for blatt, jahr, groesse, sp in tabellen:
        ws = wb[blatt]
        hin = {"bip_wachstum": "BIP, Jahreswachstum", "inflation_vpi": "VPI (CPI) Q4 gegenüber Vorjahres-Q4",
               "arbeitslosenquote": "Arbeitslosenquote LFS, Q4"}[groesse]
        for row in ws.iter_rows(min_row=1, values_only=True):
            name, stand, wert = row[1], row[2], row[sp]
            if not isinstance(name, str) or not isinstance(wert, (int, float)):
                continue
            name = name.strip()
            if name in sammel:
                herausgeber, h = "HM Treasury Konsens: " + sammel[name], hin
            elif name in ("Highest", "Lowest", "Received this month (marked *)", "City"):
                continue
            else:
                herausgeber, h = name, hin + (f"; Prognosestand {stand}" if stand else "")
            zeilen.append(z("UK", herausgeber, ausgabe, veroeff, groesse, "%", jahr, float(wert), "Primärdokument", seiten, h))
    return [x for x in zeilen if x]


# --- Funcas Panel de previsiones (Spanien) -------------------------------------------------------------------------------
def funcas():
    heute = date.today()
    for k in range(0, 10):
        mon = heute.month - k
        jj, mm = heute.year + (mon - 1) // 12, (mon - 1) % 12 + 1
        url = f"https://www.funcas.es/wp-content/uploads/{jj}/{mm:02d}/PP{str(jj)[2:]}{mm:02d}.pdf"
        try:
            daten = hole(url)
            if daten[:4] == b"%PDF":
                break
        except Exception:
            continue
    speichere("funcas_panel.pdf", daten)
    t = pdf_text(ROH / "funcas_panel.pdf")
    m = re.search(r"Fecha de publicación:\s*(\d+) DE (\w+) DE (\d{4})", t)
    meses = {"ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4, "MAYO": 5, "JUNIO": 6, "JULIO": 7, "AGOSTO": 8, "SEPTIEMBRE": 9, "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12}
    veroeff = f"{m.group(3)}-{meses[m.group(2).upper()]:02d}-{int(m.group(1)):02d}"
    ausgabe = "Panel de previsiones " + re.search(r"(ENERO|FEBRERO|MARZO|ABRIL|MAYO|JUNIO|JULIO|AGOSTO|SEPTIEMBRE|OCTUBRE|NOVIEMBRE|DICIEMBRE) (\d{4})", t).group(0).title()
    num = r"(-?\d+,\d(?:\s*\[\d\])?|--)"

    def parse(block, n):
        out = []
        for ln in block.splitlines():
            m2 = re.match(r"^\s{2,}([A-Za-zÁ-úÑñ].*?)\s{2,}((?:" + num + r"\s*){%d})\s*$" % n, ln)
            if m2:
                out.append((m2.group(1).strip(), [re.sub(r"\s*\[\d\]", "", v) for v in re.findall(num, m2.group(2))]))
        return out
    c1 = t[t.index("Cuadro 1. Panel"):t.index("Cuadro 1 (Cont.)")]
    c2 = t[t.index("Cuadro 1 (Cont.)"):]
    zeilen = []
    hin = "Panelist: Einzelprognose; Jahresrate bzw. Durchschnitt; Panel von rund 19 Analysediensten"
    spez = {"CONSENSO (MEDIA)": "Funcas-Panel Konsens (Mittelwert)"}
    ok = {"Gobierno": "Regierung", "Banco de España": "Banco de España", "AIReF": "AIReF", "CE ": "Europäische Kommission", "FMI": "IWF", "OCDE": "OECD"}

    def herausgeber(n):
        n = re.sub(r"\s*\[\d\]", "", n)
        if n in spez:
            return spez[n], hin.replace("Panelist: Einzelprognose", "Konsens")
        for k, v in ok.items():
            if n.startswith(k.strip()) and "(" in n:
                return f"{v} (zitiert im Funcas-Panel)", "Vom Funcas-Panel zitierte Prognose; Stand " + n[n.index("("):]
        if n.startswith(("Máximo", "Mínimo", "Diferencia", "-")):
            return None, None
        return n, hin
    # Namen im ersten Cuadro sind abgeschnitten; maßgeblich sind die vollständigen Namen aus dem zweiten
    voll = [n for n, _ in parse(c2, 14)]

    def kanon(n):
        return next((v for v in voll if v.startswith(n) or n.startswith(v)), n)
    # Spalten Cuadro 1: PIB 2026/2027 sind die ersten 2; Cuadro 1 (Cont.): IPC 26/27, IPC sub, Rem., Empleo, Paro (Spalten 9-10), Saldo (13-14)
    for n, w in parse(c1, 18):
        h, hh = herausgeber(kanon(n))
        if h:
            for i, jahr in enumerate(("2026", "2027")):
                zeilen.append(z("ES", h, ausgabe, veroeff, "bip_wachstum", "%", jahr, zahl(w[i]), "Primärdokument", url, hh))
    for n, w in parse(c2, 14):
        h, hh = herausgeber(n)
        if h:
            for i, jahr in enumerate(("2026", "2027")):
                zeilen.append(z("ES", h, ausgabe, veroeff, "inflation_vpi", "%", jahr, zahl(w[i]), "Primärdokument", url, hh + "; IPC, Jahresdurchschnitt"))
                zeilen.append(z("ES", h, ausgabe, veroeff, "arbeitslosenquote", "%", jahr, zahl(w[8 + i]), "Primärdokument", url, hh + "; EPA-Quote, Jahresdurchschnitt"))
                zeilen.append(z("ES", h, ausgabe, veroeff, "finanzierungssaldo", "% des BIP", jahr, zahl(w[12 + i]), "Primärdokument", url, hh))
    return [x for x in zeilen if x]


# --- Federal Reserve SEP ---------------------------------------------------------------------------------------------------
def fed_sep():
    kal = hole("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm").decode("utf-8", "ignore")
    datum = sorted(set(re.findall(r"fomcprojtabl(\d{8})\.htm", kal)))[-1]
    url = f"https://www.federalreserve.gov/monetarypolicy/fomcprojtabl{datum}.htm"
    seite = hole(url)
    speichere(f"fed_sep_{datum}.htm", seite)
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", seite.decode("utf-8", "ignore"))))
    veroeff = f"{datum[:4]}-{datum[4:6]}-{datum[6:]}"
    ausgabe = "SEP " + veroeff
    jahr0 = int(datum[:4])
    namen = [("Change in real GDP", "bip_wachstum", "Q4/Q4"), ("Unemployment rate", "arbeitslosenquote", "Q4-Durchschnitt"),
             ("PCE inflation", "inflation_pce", "Q4/Q4"), ("Federal funds rate", "leitzins", "Jahresende")]
    zeilen = []
    for n, g, basis in namen:
        m = re.search(re.escape(n) + r"(?: \d)? ((?:\d+\.\d+ ){4}\d+\.\d+)", t)
        if not m:
            continue
        w = m.group(1).split()
        for i, jahr in enumerate([str(jahr0), str(jahr0 + 1), str(jahr0 + 2), str(jahr0 + 3), "langfristig"]):
            zeilen.append(z("US", "Federal Reserve FOMC (Median)", ausgabe, veroeff, g, "%", jahr, float(w[i]), "Primärdokument", url,
                            f"Median der Projektionen der FOMC-Teilnehmer; {basis}"))
    return [x for x in zeilen if x]


# --- Bank of Canada MPR ---------------------------------------------------------------------------------------------------------
def boc():
    seite = hole("https://www.bankofcanada.ca/publications/mpr/").decode("utf-8", "ignore")
    d = sorted(set(re.findall(r"mpr/mpr-(20\d\d-\d\d-\d\d)/", seite)))[-1]
    url = f"https://www.bankofcanada.ca/wp-content/uploads/{d[:4]}/{d[5:7]}/mpr-{d}.pdf"
    speichere(f"boc_mpr_{d}.pdf", hole(url))
    t = pdf_text(ROH / f"boc_mpr_{d}.pdf")
    blk = t[t.index("Summary of the quarterly projection for Canada"):][:2500]
    zeilen = []
    for name, g, pat in (("CPI", "inflation_vpi", r"CPI inflation \(year-over-year percentage\s+((?:-?\d+\.\d\s+){8})"),
                         ("GDP", "bip_wachstum", r"Real GDP \(year-over-year percentage\s+((?:-?\d+\.\d\s+){8})")):
        m = re.search(pat, blk)
        if not m:
            continue
        w = m.group(1).split()
        for jahr, v in zip(("2026", "2027", "2028"), w[5:8]):
            zeilen.append(z("CA", "Bank of Canada Monetary Policy Report", f"MPR {d}", d, g, "%", jahr, float(v), "Primärdokument", url,
                            "Projektion des Stabs; Q4 gegenüber Vorjahres-Q4"))
    return [x for x in zeilen if x]


# --- Bank of Japan Outlook Report ---------------------------------------------------------------------------------------------------
def boj():
    idx = hole("https://www.boj.or.jp/en/mopo/outlook/index.htm").decode("utf-8", "ignore")
    name = sorted(set(re.findall(r"gor(\d{4})a\.pdf", idx)))[-1]
    url = f"https://www.boj.or.jp/en/mopo/outlook/gor{name}a.pdf"
    speichere(f"boj_outlook_{name}.pdf", hole(url))
    t = pdf_text(ROH / f"boj_outlook_{name}.pdf")
    m = re.search(r"(\w+) (\d+), (20\d\d)\s+Bank of Japan\s+Outlook for Economic Activity", t)
    veroeff = f"{m.group(3)}-{MONATE[m.group(1)[:3].lower()]:02d}-{int(m.group(2)):02d}"
    blk = t[t.index("Forecasts of the Majority of the Policy Board Members"):][:2500]
    zeilen = []
    for fj, jahr in (("Fiscal 2026", "2026"), ("Fiscal 2027", "2027"), ("Fiscal 2028", "2028")):
        i = blk.index(fj)
        stuck = blk[i:i + 400]
        med = re.search(r"\[\+?(-?\d\.\d)\]\s+\[\+?(-?\d\.\d)\]\s+\[\+?(-?\d\.\d)\]", stuck)
        if med:
            for g, v in (("bip_wachstum", med.group(1)), ("inflation_vpi", med.group(2))):
                zeilen.append(z("JP", "Bank of Japan Outlook Report (Median der Vorstandsprognosen)", f"Outlook {veroeff[:7]}", veroeff, g, "%", jahr,
                                float(v), "Primärdokument", url,
                                "Fiskaljahr (April bis März); Inflation = VPI ohne frische Lebensmittel, Veränderung zum Vorjahr; Median der Punktprognosen"))
    return [x for x in zeilen if x]


QUELLEN = [("EZB SPF", ezb_spf), ("Philadelphia SPF", philly_spf), ("HM Treasury", hmt), ("Funcas", funcas), ("Fed SEP", fed_sep),
           ("Bank of Canada", boc), ("Bank of Japan", boj)]


def main():
    alt = []
    if ZIEL.exists():
        with open(ZIEL, newline="", encoding="utf-8") as f:
            alt = list(csv.DictReader(f))
    neu = []
    for name, fkt in QUELLEN:
        try:
            z_ = fkt()
            print(f"{name}: {len(z_)} Zeilen")
            neu += z_
        except Exception as e:
            print(f"{name}: FEHLER {type(e).__name__}: {e}", file=sys.stderr)
    ausgaben = {(r["geo"], r["ausgabe"]) for r in neu}
    # Zeilen derselben Ausgabe einer erfolgreich abgerufenen Quelle werden ersetzt, alles andere bleibt stehen
    alt = [r for r in alt if (r["geo"], r["ausgabe"]) not in ausgaben]
    with open(ZIEL, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, FELDER)
        w.writeheader()
        w.writerows(alt + neu)
    print(len(alt) + len(neu), "Zeilen gesamt")


if __name__ == "__main__":
    main()
