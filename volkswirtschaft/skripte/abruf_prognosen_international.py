"""Pilot: Prognosen internationaler Geber (Konsensumfragen und G7-Zentralbanken) -> prognosen_international.csv.

Quellen (alle frei, ohne Schlüssel; Bot-Schutz wird nicht umgangen):
  EZB SPF (API), Philadelphia Fed SPF (PDF), HM Treasury Forecasts for the UK economy (XLSX, mit Einzelprognostikern),
  Funcas Panel (PDF, mit Einzelpanelisten), Fed SEP (HTML), Bank of Canada MPR (PDF), Bank of Japan Outlook Report (PDF).
Die Rohdateien landen unverändert in rohdaten/prognosen/. Die Ausgabe ist ein Langformat wie prognosen_oecd.csv.
Die jeweils neueste Ausgabe wird über die Übersichtsseiten gefunden; ältere Ausgaben der Datei bleiben stehen, nur die
Zeilen derselben Ausgabe werden ersetzt. Abhängigkeiten: openpyxl, pdftotext (poppler).
"""
import csv
import json, html, io, json, re, subprocess, sys, urllib.error, urllib.request
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
    sammel = {"Independent": "HM-Treasury-Konsens: Durchschnitt unabhängiger Prognostiker (letzte 3 Monate)", "Median": "HM-Treasury-Konsens: Median"}
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
                herausgeber, h = sammel[name], hin
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


# --- EZB/Eurosystem-Stabsprognosen (Annex-Excel je Runde) und Prognosen der nationalen Zentralbanken (EZB-Datenbank MPD) ---
EZB_RUNDEN = {"03": "Mar", "06": "Jun", "09": "Sep", "12": "Dez"}
MPD_CODE = {"03": "W", "06": "G", "09": "S", "12": "A"}   # Kennung der Runde in der MPD: Buchstabe + Jahr (Dez. 2025 = A25), über den Vergleich mit den Annex-Dateien bestimmt
NCB = {"AT": "Oesterreichische Nationalbank", "BE": "Nationale Bank van België", "DE": "Deutsche Bundesbank", "EE": "Eesti Pank",
       "ES": "Banco de España", "FI": "Suomen Pankki", "FR": "Banque de France", "GR": "Bank of Greece", "IE": "Central Bank of Ireland",
       "IT": "Banca d'Italia", "LT": "Lietuvos bankas", "LU": "Banque centrale du Luxembourg", "LV": "Latvijas Banka", "NL": "De Nederlandsche Bank",
       "PT": "Banco de Portugal", "SI": "Banka Slovenije", "SK": "Národná banka Slovenska"}


def ezb_stab():
    import openpyxl
    basis = "https://www.ecb.europa.eu/press/projections/html/"
    idx = hole(basis + "index.en.html").decode("utf-8", "ignore")
    seiten = sorted(set(re.findall(r"(ecb\.projections(\d{6})_\w+~\w+\.en\.html)", idx)), key=lambda x: x[1])
    zeilen = []
    for datei, ym in seiten:
        h = hole(basis + datei).decode("utf-8", "ignore")
        m = re.search(r'href="(/pub/pdf/other/[^"]*annex[^"]*xlsx)"', h)
        if not m:
            continue
        name = f"ezb_annex_{ym}.xlsx"
        speichere(name, hole("https://www.ecb.europa.eu" + m.group(1)))
        wb = openpyxl.load_workbook(ROH / name, data_only=True)

        def spalte(blatt, kopf, block=0):
            ws = wb[blatt]
            zl = list(ws.iter_rows(values_only=True))
            kr = next(r for r in zl if r[0] == "Reference period")
            c = [i for i, v in enumerate(kr) if isinstance(v, str) and v.strip().replace("\n", " ") == kopf][block]
            return {r[0].year: r[c] for r in zl if hasattr(r[0], "year") and r[0].year >= 2025 and isinstance(r[c], (int, float))}
        reihen = [("bip_wachstum", "%", spalte("Real Economy (annual)", "Real GDP"), "reales BIP, Veränderung zum Vorjahr"),
                  ("inflation_hvpi", "%", spalte("Prices (annual)", "HICP"), "HVPI, Veränderung zum Vorjahr"),
                  ("arbeitslosenquote", "%", spalte("Real Economy (annual)", "Unemployment rate"), "Arbeitslosenquote in % der Erwerbspersonen"),
                  ("finanzierungssaldo", "% des BIP", spalte("Fiscal", "General government budget balance"), "gesamtstaatlicher Haushaltssaldo")]
        ausgabe = f"Stabsprognose {EZB_RUNDEN[ym[4:]]} {ym[:4]}"
        art = "Eurosystem" if ym[4:] in ("06", "12") else "EZB"
        url = basis + datei
        for g, e, d, hin in reihen:
            for jahr, v in d.items():
                zeilen.append(z("EA20", "EZB und Eurosystem" if art == "Eurosystem" else "EZB", ausgabe, "", g, e, str(jahr), float(v), "Primärdokument", url,
                                f"Euroraum; {hin}; Annex-Excel der Runde"))
    return [x for x in zeilen if x]


def ncb_mpd():
    """Prognosen der nationalen Zentralbanken des Euroraums aus der Macroeconomic Projections Database der EZB (Runden Juni und Dezember)."""
    jetzt = date.today()
    runden = []
    for jj in range(jetzt.year - 2, jetzt.year + 1):
        for mm, bez in (("06", "G"), ("12", "A")):
            if f"{jj}{mm}" <= f"{jetzt.year}{jetzt.month:02d}":
                runden.append((f"{jj}-{mm}", bez + str(jj)[2:]))
    reihen = [("YER", "A", "bip_wachstum", "reales BIP, Veränderung zum Vorjahr"), ("HIC", "A", "inflation_hvpi", "HVPI, Veränderung zum Vorjahr"),
              ("URX", "F", "arbeitslosenquote", "Arbeitslosenquote in % der Erwerbspersonen")]
    zeilen, roh = [], []
    laender = "+".join(NCB)
    for monat, code in runden:
        for item, denom, g, hin in reihen:
            url = f"https://data-api.ecb.europa.eu/service/data/MPD/A.{laender}.{item}.{denom}.{code}.0000?format=csvdata&startPeriod=2025"
            try:
                txt = hole(url.replace("+", "%2B"), "text/csv").decode("utf-8")
            except urllib.error.HTTPError:
                continue
            roh.append(txt)
            for r in csv.DictReader(io.StringIO(txt)):
                geo = "EL" if r["REF_AREA"] == "GR" else r["REF_AREA"]
                zeilen.append(z(geo, f"{NCB[r['REF_AREA']]} (Eurosystem-Projektion)", f"Runde {EZB_RUNDEN[monat[5:]]} {monat[:4]}", "", g, "%",
                                r["TIME_PERIOD"], float(r["OBS_VALUE"]), "API", url.split("?")[0],
                                f"{hin}; Beitrag der nationalen Zentralbank zur Eurosystem-Runde, EZB Macroeconomic Projections Database (Runde {code})"))
    speichere("ezb_mpd_ncb.csv", "\n".join(roh).encode())
    return [x for x in zeilen if x]


# --- Bank of England Monetary Policy Report ---------------------------------------------------------------------------------------
def boe():
    basis = "https://www.bankofengland.co.uk"
    mon = ["february", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
    jahr = date.today().year
    treffer = None
    for m in reversed(mon):   # jüngste veröffentlichte Ausgabe des Jahres mit PDF
        pdf = f"{basis}/-/media/boe/files/monetary-policy-report/{jahr}/{m}/monetary-policy-report-{m}-{jahr}.pdf"
        try:
            daten = hole(pdf)
        except urllib.error.HTTPError:
            continue
        if daten[:4] == b"%PDF":
            treffer = (m, pdf, daten)
            break
    if not treffer:
        return []
    m, pdf, daten = treffer
    speichere(f"boe_mpr_{m}_{jahr}.pdf", daten)
    t = pdf_text(ROH / f"boe_mpr_{m}_{jahr}.pdf")
    blk = t[t.index("Summary of outputs of the central projection and scenarios"):]
    blk = blk[:blk.index("Milder scenario")]
    kopf = re.search(r"((?:20\d\d Q\d\s+){4})", blk).group(1).split()
    perioden = [f"{kopf[i]} {kopf[i + 1]}" for i in range(0, 8, 2)]
    ausgabe = f"MPR {m.capitalize()} {jahr}"
    zeilen = []
    for pat, g, e in ((r"CPI inflation \(b\)", "inflation_vpi", "%"), (r"GDP \(c\)", "bip_wachstum", "%"), (r"Unemployment rate \(e\)", "arbeitslosenquote", "%"),
                      (r"Bank Rate \(i\)", "leitzins", "%")):
        mm = re.search(pat + r"\s+((?:-?\d+\.\d\s+){4})", blk)
        for per, v in zip(perioden, mm.group(1).split()):
            zeilen.append(z("UK", "Bank of England Monetary Policy Report", ausgabe, "", g, e, per.replace(" ", "-"), float(v), "Primärdokument", pdf,
                            "Zentrale Projektion des MPC; Vierquartalswert im jeweiligen dritten Quartal (nicht Kalenderjahr); Bank Rate = Marktpfad"))
    return [x for x in zeilen if x]


# --- Schweden: Riksbank, offene API für Prognosen (alle Runden seit 2015, je Runde der Prognosepfad in Quartalen/Monaten) ----
def riksbank():
    url = "https://api.riksbank.se/monetary_policy_data/v1/forecasts"
    roh = hole(url)
    speichere("riksbank_prognosen.json", roh)
    daten = {s["external_id"]: s["vintages"] for s in json.loads(roh)["data"]}
    seite = "https://www.riksbank.se/en-gb/statistics/macro-indicators/forecasts-and-outcomes/"
    zeilen = []
    for v in daten["SEQGDPNAACA"]:
        runde = v["metadata"]["policy_round"]
        ende = v["metadata"]["policy_round_end_dtm"]
        j0 = int(ende[:4])
        ausgabe = "Geldpolitischer Bericht " + runde
        jahre = [str(j0), str(j0 + 1), str(j0 + 2)]

        def reihe(sid):
            return {o["dt"]: o["value"] for x in daten[sid] if x["metadata"]["policy_round"] == runde for o in x["observations"]}

        def jahres(sid, anz, fkt):
            r = reihe(sid)
            out = {}
            for j in jahre:
                w = [r[d] for d in r if d.startswith(j)]
                if len(w) == anz:
                    out[j] = fkt(w)
            return out
        gdp = reihe("SEQGDPNAACA")
        summe = {j: sum(x for d, x in gdp.items() if d.startswith(j)) for j in [str(j0 - 1)] + jahre if sum(1 for d in gdp if d.startswith(j)) == 4}
        bip = {j: (summe[j] / summe[str(int(j) - 1)] - 1) * 100 for j in jahre if j in summe and str(int(j) - 1) in summe}
        mittel = lambda w: sum(w) / len(w)
        index = {}
        for sid, g in (("SEMCPIFNAANA", "inflation_cpif"), ("SEMCPINAANA", "inflation_vpi")):
            r = reihe(sid)
            jm = {j: mittel([x for d, x in r.items() if d.startswith(j)]) for j in [str(j0 - 1)] + jahre if sum(1 for d in r if d.startswith(j)) == 12}
            index[g] = {j: (jm[j] / jm[str(int(j) - 1)] - 1) * 100 for j in jahre if j in jm and str(int(j) - 1) in jm}
        arb = jahres("SEQLABUEASA", 4, mittel)
        zins = {j: reihe("SEQRATENAYNA").get(f"{j}-12-31") for j in jahre}
        saldo = {j: reihe("SEAPBSNAYNA").get(f"{j}-12-31") for j in jahre}
        n = "Kalenderjahr; "
        for g, ser, hin in (("bip_wachstum", bip, n + "Jahressumme des kalenderbereinigten BIP (aus den Quartalsniveaus der API berechnet)"),
                            ("inflation_cpif", index["inflation_cpif"], n + "CPIF (Zielgröße der Riksbank), Jahresdurchschnitt aus den Monatsindizes der API"),
                            ("inflation_vpi", index["inflation_vpi"], n + "VPI, Jahresdurchschnitt aus den Monatsindizes der API"),
                            ("arbeitslosenquote", arb, n + "Mittel der vier saisonbereinigten Quartalswerte, Alter 15-74"),
                            ("leitzins", zins, "Politikzins am Jahresende (Prognosepfad der Riksbank)"),
                            ("finanzierungssaldo", saldo, "Staatlicher Finanzierungssaldo in % des BIP")):
            for j, x in ser.items():
                zeilen.append(z("SE", "Sveriges Riksbank", ausgabe, ende, g, "% des BIP" if g == "finanzierungssaldo" else "%", j, x, "API", seite, hin))
    return [x for x in zeilen if x]


# --- Norwegen: Norges Bank, Tabelle "Projections" im Geldpolitischen Bericht (Ausgaben seit 2024) ----------
def norges():
    basis = "https://www.norges-bank.no"
    idx = hole(basis + "/en/topics/Monetary-policy/Monetary-Policy-Report/").decode("utf-8", "ignore")
    seiten = sorted(set(re.findall(r'href="(/en/news-events/publications/Monetary-Policy-Report/(20\d\d)/mpr-(\d)(20\d\d)/)"', idx)), key=lambda x: (x[1], x[2]))
    zeilen = []
    for pfad, jahr, nr, _ in seiten:
        h = hole(basis + pfad).decode("utf-8", "ignore")
        m = re.search(r'href="(/contentassets/[^"?]*/(?:mpr|MPR)[^"?/]*\.pdf)', h)
        if not m:
            continue
        url = basis + m.group(1)
        name = f"norges_mpr_{nr}_{jahr}.pdf"
        speichere(name, hole(url))
        t = pdf_text(ROH / name)
        blk = t
        jahre = [str(int(jahr) - 1 + i) for i in range(5)]
        ausgabe = f"Geldpolitischer Bericht {nr}/{jahr}"
        for g, pat, hin in (("inflation_vpi", r"^\s+CPI\s", "VPI, Veränderung zum Vorjahr; Jahresdurchschnitt"),
                            ("bip_wachstum", r"^\s+GDP, mainland Norway", "BIP des Festlands (ohne Öl und Gas), Veränderung zum Vorjahr; Gesamt-BIP inkl. Öl und Gas steht im Bericht"),
                            ("arbeitslosenquote", r"^\s+Registered unemployment \(rate, level\)", "Registrierte Arbeitslosigkeit (NAV), nicht die Erwerbsumfrage; Jahresdurchschnitt")):
            kand = [re.findall(r"-?\d+\.\d", re.sub(r"\([^)]*\)", "", x)) for x in blk.splitlines() if re.match(pat, x)]
            kand = [w for w in kand if len(w) >= 5]
            if not kand:
                continue
            werte = kand[-1][-5:]
            for j, v in zip(jahre, werte):
                zeilen.append(z("NO", "Norges Bank", ausgabe, "", g, "%", j, float(v), "Primärdokument", url, hin))
    return [x for x in zeilen if x]


# --- Australien: RBA, Prognosearchiv zum Statement on Monetary Policy (Excel, eine Spalte je Ausgabe, Zeilen = Juni/Dezember) ----------
def rba():
    import openpyxl
    url = "https://www.rba.gov.au/statistics/xls/smp-forecast-archive.xlsx"
    speichere("rba_smp_forecast_archive.xlsx", hole(url))
    wb = openpyxl.load_workbook(ROH / "rba_smp_forecast_archive.xlsx", data_only=True)
    seite = "https://www.rba.gov.au/publications/smp/forecasts-archive.html"
    zeilen = []
    for blatt, g, e, hin in (("RGDP", "bip_wachstum", "%", "Veränderung des BIP im Dezemberquartal zum Vorjahresquartal"),
                             ("CPI", "inflation_vpi", "%", "VPI, Veränderung im Dezemberquartal zum Vorjahresquartal"),
                             ("UR", "arbeitslosenquote", "%", "Arbeitslosenquote im Dezemberquartal"),
                             ("CR", "leitzins", "%", "Zielzins (Cash Rate) im Dezemberquartal; Annahme der RBA, ab Mai 2024 gemäß Marktpreisen")):
        ws = wb[blatt]
        rows = list(ws.iter_rows(min_row=4, values_only=True))
        kopf = rows[0]
        for ci, pub in enumerate(kopf):
            if ci == 0 or not isinstance(pub, str) or "-" not in pub:
                continue
            mon, jahr = pub.split("-")
            for r in rows[2:]:
                if not isinstance(r[0], str) or not r[0].startswith("Dec-") or ci >= len(r) or not isinstance(r[ci], (int, float)):
                    continue
                if int(r[0][4:]) < int(jahr):
                    continue
                zeilen.append(z("AU", "Reserve Bank of Australia", f"SMP {mon} {jahr}", "", g, e, r[0][4:], float(r[ci]), "Primärdokument", seite, hin + "; Archivtabelle des RBA, Rundung je Ausgabe unterschiedlich"))
    return [x for x in zeilen if x]


# --- Südkorea: Bank of Korea, Korea Economic Outlook (Zusammenfassungstabelle im PDF; Liste über listCont.do der englischen Seite) ----------
def bok():
    basis = "https://www.bok.or.kr"
    liste = hole(basis + "/eng/singl/newsDataEng/listCont.do?pageIndex=&targetDepth=3&menuNo=400413&syncMenuChekKey=1&searchCnd=1&searchKwd=&depth2=400065&depth3=400413").decode("utf-8", "ignore")
    zeilen = []
    for pfad, rest in re.findall(r'href="(/eng/bbs/B0000358/view\.do\?nttId=\d+)[^"]*"(.*?)</a>', liste, flags=re.S):
        titel = html.unescape(re.sub(r"<[^>]+>|\s+", " ", rest)).strip()
        mt = re.search(r"Korea Economic Outlook \((\w+) (20\d\d)\)$", titel)
        if not mt:
            continue
        seite = hole(basis + pfad + "&menuNo=400413").decode("utf-8", "ignore")
        pdf = re.search(r'href="(/fileSrc/eng/[^"\s]*\.pdf)', seite)
        if not pdf:
            continue
        monat, jahr = mt.groups()
        name = f"bok_outlook_{monat.lower()}_{jahr}.pdf"
        url = basis + pdf.group(1)
        speichere(name, hole(url))
        t = pdf_text(ROH / name)
        for g, pat, hin in (("bip_wachstum", r"^[^A-Za-z]*GDP growth rate", "BIP, Veränderung zum Vorjahr"),
                            ("inflation_vpi", r"^[^A-Za-z]*Headline infla\w+", "VPI gesamt, Veränderung zum Vorjahr (Kerninflation steht im Bericht)")):
            kand = [re.findall(r"-?\d+\.\d", re.sub(r"\([^)]*\)", "", x)) for x in t.splitlines() if re.match(pat, x, re.I)]
            kand = [w for w in kand if 3 <= len(w) <= 4]
            if not kand:
                continue
            for i, v in enumerate(kand[0]):
                zeilen.append(z("KR", "Bank of Korea", f"Korea Economic Outlook {monat[:3]} {jahr}", "", g, "%", str(int(jahr) - 1 + i), float(v), "Primärdokument", url,
                                hin + "; erstes Jahr = Istwert"))
    return [x for x in zeilen if x]


# --- Schweiz: SECO-Expertengruppe (Anhang zur Medienmitteilung, aktuelle Prognose und in Klammern die vorherige) ----------
MON_DE = {"03": "Mar", "06": "Jun", "09": "Sep", "12": "Dez"}


def seco():
    seite = "https://www.seco.admin.ch/seco/de/home/wirtschaftslage---wirtschaftspolitik/Wirtschaftslage/Konjunkturprognosen.html"
    h = hole(seite).decode("utf-8", "ignore")
    url = re.search(r'href="([^"]*prognose-konjunktur-schweiz-SECO\.pdf)"', h).group(1)
    speichere("seco_konjunkturprognose.pdf", hole(url))
    t = pdf_text(ROH / "seco_konjunkturprognose.pdf")
    m = re.search(r"Medienmitteilung des SECO vom (\d\d)\.(\d\d)\.(20\d\d)", t)
    neu_d = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    v = re.search(r"Prognosen vom (\d\d)\.(\d\d)\.(20\d\d)\s+in Klammern", t)
    alt_d = f"{v.group(3)}-{v.group(2)}-{v.group(1)}"
    num = r"(-?\d+\.\d)"
    hin = "Kalenderjahr, Jahresdurchschnitt; BIP Sportevent-bereinigt; Inflation = Landesindex der Konsumentenpreise"
    zeilen = []
    for g, pat in (("bip_wachstum", r"\n\s+BIP\s+"), ("arbeitslosenquote", r"Arbeitslosenquote in %\s+"), ("inflation_vpi", r"Landesindex der Konsumentenpreise\s+")):
        mm = re.search(pat + num + r"\s+" + num + r"\s+" + num + r"\s+\(" + num + r"\)\s+" + num + r"\s+\(" + num + r"\)", t)
        w = mm.groups()
        for d, jahr, x in ((neu_d, "2026", w[2]), (neu_d, "2027", w[4]), (alt_d, "2026", w[3]), (alt_d, "2027", w[5])):
            zeilen.append(z("CH", "SECO Expertengruppe des Bundes", f"{MON_DE[d[5:7]]} {d[:4]}", d, g, "%", jahr, float(x), "Primärdokument", url, hin))
    return [x for x in zeilen if x]


QUELLEN = [("EZB SPF", ezb_spf), ("Philadelphia SPF", philly_spf), ("HM Treasury", hmt), ("Funcas", funcas), ("Fed SEP", fed_sep),
           ("Bank of Canada", boc), ("Bank of Japan", boj), ("EZB-Stabsprognosen", ezb_stab),
           ("Nationale Zentralbanken (MPD)", ncb_mpd), ("Bank of England", boe), ("SECO Schweiz", seco), ("Riksbank Schweden", riksbank), ("Norges Bank", norges), ("RBA Australien", rba), ("Bank of Korea", bok)]


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
