"""Reichert die Unternehmenstabelle in Zehnerblöcken an (Reihenfolge wie in der Tabelle), Stand je Block in anreicherung/stand.csv.
Aufruf: python3 batch_anreichern.py [anzahl=10] [bloecke=1]
Reihenfolge: zuerst börsennotierte Unternehmen mit Ticker (dort liefert Yahoo am meisten), jeweils in Tabellenreihenfolge, danach alle übrigen.
Je Unternehmen:
 1. Stammdaten (nur leere Felder, mit Vermerk "bitte prüfen"): LEI/Sitz/Handelsregisternummer aus GLEIF (per ISIN, sonst Name+Land), Rechtsform aus dem Firmennamen.
 2. Kennzahlen (Bilanz, GuV, Cashflow, je Aktie) aus Yahoo Finance (fundamentals-timeseries, frei, Sekundärquelle) nach import/daten/<ID>.json im Format der Importvorlage.
 3. Geschäftsbericht: Liegt in "Quellen-Dokumente" ein PDF-Link, wird der Bericht geladen und geprüft, ob die Yahoo-Werte des letzten Jahres dort stehen.
    Treffer: Quelle = Geschäftsbericht mit Seite. Kein Bericht/kein Treffer: Quelle bleibt Yahoo und wird im Stand vermerkt.
Keine Werte werden geschätzt; ohne Daten wird das Unternehmen im Stand vermerkt und übersprungen."""
import csv, json, re, sys, time, subprocess, tempfile, datetime as dt, urllib.request, urllib.parse, concurrent.futures as cf
from pathlib import Path
import openpyxl
T = Path(__file__).resolve().parents[1]; REPO = T.parent
sys.path.insert(0, str(REPO / 'vorlagen')); import schema as S
STAND = T / 'anreicherung' / 'stand.csv'; AUSGABE = REPO / 'import' / 'daten'
UA = {'User-Agent': 'Mozilla/5.0 (compatible; Unternehmenskennzahlen-Abruf)'}
SUFFIX = {'Wiener Börse': ['.VI'], 'Xetra': ['.DE'], 'Deutsche Boerse Xetra': ['.DE'], 'Euronext Paris': ['.PA'], 'Euronext Amsterdam': ['.AS'], 'Euronext Brussels': ['.BR'],
          'Euronext Lisbon': ['.LS'], 'Borsa Italiana': ['.MI'], 'Bolsa de Madrid': ['.MC'], 'SIX Swiss Exchange': ['.SW'], 'London Stock Exchange': ['.L'], 'Nasdaq Stockholm': ['.ST'],
          'Oslo Bors Asa': ['.OL'], 'Nasdaq Copenhagen': ['.CO'], 'Nasdaq Helsinki': ['.HE'], 'Warsaw Stock Exchange': ['.WA'], 'Tokyo Stock Exchange': ['.T'], 'Taiwan Stock Exchange (TWSE)': ['.TW'],
          'Taipei Exchange (TPEx)': ['.TWO'], 'Shanghai Stock Exchange': ['.SS'], 'Shenzhen Stock Exchange': ['.SZ'], 'Australian Securities Exchange': ['.AX'],
          'National Stock Exchange of India': ['.NS'], 'Bse Ltd': ['.BO'], 'Nasdaq': [''], 'New York Stock Exchange': [''], 'New York Stock Exchange Inc.': ['']}
LAND_SUFFIX = {'Austria': ['.VI'], 'Germany': ['.DE', '.F'], 'France': ['.PA'], 'Netherlands': ['.AS'], 'Belgium': ['.BR'], 'Italy': ['.MI'], 'Spain': ['.MC'], 'Switzerland': ['.SW'],
               'UK': ['.L'], 'Sweden': ['.ST'], 'Norway': ['.OL'], 'Denmark': ['.CO'], 'Finland': ['.HE'], 'Poland': ['.WA'], 'USA': [''], 'Japan': ['.T'], 'Canada': ['.TO'], 'Brazil': ['.SA'],
              'Australia': ['.AX'], 'India': ['.NS'], 'Hong Kong': ['.HK'], 'South Korea': ['.KS', '.KQ'], 'Portugal': ['.LS'], 'Ireland': ['.IR', '.L'], 'Greece': ['.AT'], 'Czechia': ['.PR']}
YT = {  # Yahoo-Schlüssel -> (Kennzahl, Vorzeichen: abs = Betrag)
 'TotalAssets': ('Bilanzsumme', 1), 'CurrentAssets': ('Umlaufvermögen', 1), 'Inventory': ('Vorräte', 1), 'AccountsReceivable': ('Forderungen aus Lieferungen und Leistungen', 1),
 'CashAndCashEquivalents': ('Liquide Mittel', 1), 'StockholdersEquity': ('Eigenkapital der Anteilseigner', 1), 'TotalEquityGrossMinorityInterest': ('Eigenkapital', 1),
 'TotalLiabilitiesNetMinorityInterest': ('Verbindlichkeiten gesamt', 1), 'TotalDebt': ('Finanzverbindlichkeiten', 1), 'CurrentLiabilities': ('Kurzfristige Verbindlichkeiten', 1),
 'TotalNonCurrentLiabilitiesNetMinorityInterest': ('Langfristige Verbindlichkeiten', 1), 'TotalRevenue': ('Umsatz', 1), 'GrossProfit': ('Bruttoergebnis', 1), 'EBITDA': ('EBITDA', 1),
 'EBIT': ('EBIT', 1), 'PretaxIncome': ('Ergebnis vor Steuern', 1), 'TaxProvision': ('Ertragsteuern', 1), 'NetIncomeIncludingNoncontrollingInterests': ('Jahresergebnis', 1),
 'NetIncomeCommonStockholders': ('Jahresergebnis der Anteilseigner', 1), 'OperatingCashFlow': ('Operativer Cashflow', 1), 'InvestingCashFlow': ('Investitions-Cashflow', 1),
 'FinancingCashFlow': ('Finanzierungs-Cashflow', 1), 'CapitalExpenditure': ('Investitionen (Capex)', 'abs'), 'DilutedEPS': ('Ergebnis je Aktie', 1),
 'OrdinarySharesNumber': ('Aktienanzahl', 1), 'CashDividendsPaid': ('Dividende gesamt', 'abs'), 'InterestExpense': (None, 1)}
KZ = {k[0]: k for k in S.KENNZAHLEN}
def get(u, tries=3, js=True, **kw):
    for t in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=kw.get('h', UA)), timeout=40) as f:
                d = f.read(); return json.loads(d) if js else d
        except Exception: time.sleep(1.5 * (t + 1))
    return None
def yahoo(symbol):
    ty = ','.join('annual' + k for k in YT if YT[k][0])
    d = get(f'https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{urllib.parse.quote(symbol)}?type={ty}&period1=1400000000&period2=1900000000')
    out = {}
    for res in ((d or {}).get('timeseries') or {}).get('result') or []:
        for key, arr in res.items():
            if not key.startswith('annual') or not isinstance(arr, list): continue
            for p in arr:
                if p and p.get('reportedValue') and p['reportedValue'].get('raw') is not None:
                    out.setdefault(p['asOfDate'], {})[key[6:]] = (p['reportedValue']['raw'], p.get('currencyCode'))
    return out
def yahoo_suche(name, land):
    """Findet das Yahoo-Kürzel über die freie Suche, nur bei gleichem Namen (ohne Rechtsform) und passender Börse."""
    d = get('https://query2.finance.yahoo.com/v1/finance/search?quotesCount=8&newsCount=0&q=' + urllib.parse.quote(name))
    def nz(x): return re.sub(r'\b(inc|corp|corporation|plc|ag|se|nv|sa|as|a/s|ab|asa|oyj|ltd|limited|group|holding|holdings|co|the|company|spa)\b', ' ', re.sub(r'[^a-z0-9/ ]', ' ', (x or '').lower().replace('&', ' and '))).split()
    treffer = []
    for q in (d or {}).get('quotes') or []:
        if q.get('quoteType') != 'EQUITY': continue
        sym = q.get('symbol', ''); suff = '.' + sym.split('.')[-1] if '.' in sym else ''
        if land in LAND_SUFFIX and suff not in LAND_SUFFIX[land]: continue
        if nz(q.get('longname') or q.get('shortname')) == nz(name): treffer.append(sym)
    return treffer[0] if len(set(treffer)) == 1 else None
def gleif(isin, name, land):
    B = 'https://api.gleif.org/api/v1/lei-records'; h = {'Accept': 'application/vnd.api+json'}
    c = []
    if isin:
        d = get(f'{B}?filter%5Bisin%5D={isin}', h=h); c = (d or {}).get('data') or []
    if not c and name:
        d = get(f'{B}?filter%5Bentity.legalName%5D={urllib.parse.quote(name)}&page%5Bsize%5D=5', h=h); c = (d or {}).get('data') or []
        c = [x for x in c if re.sub(r'\W', '', x['attributes']['entity']['legalName']['name'].lower()) == re.sub(r'\W', '', name.lower())]
        if len(c) != 1: c = []
    if len(c) != 1: return None
    e = c[0]['attributes']['entity']
    return dict(lei=c[0]['id'], name=e['legalName']['name'], sitz=(e.get('legalAddress') or {}).get('city'), reg=e.get('registeredAs'), jur=e.get('jurisdiction'))
FORMS = ['AG', 'SE', 'GmbH', 'KGaA', 'plc', 'N.V.', 'NV', 'S.A.', 'SA', 'Inc.', 'Inc', 'Corp.', 'Ltd', 'ASA', 'AB', 'Oyj', 'S.p.A.', 'SpA', 'A/S', 'Oy', 'AS', 'SAB']
def rechtsform(name):
    m = re.search(r'[\s,]((?:' + '|'.join(re.escape(f) for f in FORMS) + r'))\.?(?:\s*\(.*\))?$', name.strip())
    return m.group(1) if m else None
def finde_berichte(seiten):
    """Sucht auf IR-/Website-Seiten (eine Ebene) PDF-Links, die nach Geschäftsbericht aussehen; beste zuerst."""
    gef = {}
    for u in seiten:
        if not u or not str(u).startswith('http'): continue
        h = get(u, tries=1, js=False)
        if not h: continue
        h = h.decode('utf-8', 'ignore')
        for m in re.finditer(r'href=[\"\']([^\"\'#]+?\.pdf[^\"\']*)[\"\']', h, re.I):
            l = urllib.parse.urljoin(u, m.group(1).replace('&amp;', '&')); lo = l.lower()
            sc = sum(k in lo for k in ('annual', 'geschaeftsbericht', 'geschaftsbericht', 'gb', 'report', 'konzern', 'integrated', 'financial-statement', 'abschluss', '10-k', '20-f')) \
                + (2 if re.search(r'2025|fy25|2024|fy24', lo) else 0) - (3 if re.search(r'q[1-4]|quarter|halbjahr|half|interim|presentation|esg|sustainab|nachhaltig|remuneration|proxy|invitation|einladung', lo) else 0)
            if sc >= 2: gef[l] = max(gef.get(l, -9), sc)
    return [u for u, _ in sorted(gef.items(), key=lambda x: -x[1])][:3]
def bericht_pruefen(name, urls, jahr, werte):
    """Sucht die letzten Yahoo-Werte im Geschäftsbericht-PDF. Rückgabe: {kennzahl: (url, seite)}"""
    treffer = {}
    for u in urls:
        try:
            d = get(u, tries=1, js=False, h={'User-Agent': UA['User-Agent'], 'Accept': 'application/pdf'})
            if not d or d[:4] != b'%PDF' or len(d) > 90e6: continue
            with tempfile.TemporaryDirectory() as td:
                p = Path(td) / 'a.pdf'; p.write_bytes(d)
                txt = subprocess.run(['pdftotext', '-layout', str(p), '-'], capture_output=True, text=True, timeout=180).stdout
        except Exception: continue
        seiten = txt.split('\f')
        for kz, v in werte.items():
            if kz not in ('Bilanzsumme', 'Umsatz', 'Jahresergebnis', 'Eigenkapital') or abs(v) < 1e5: continue
            cands = set()
            for div in (1, 1e3, 1e6):
                x = round(abs(v) / div)
                if x >= 1000:
                    s = f'{x:,}'; cands |= {s, s.replace(',', '.'), s.replace(',', ' '), s.replace(',', "'")}
                for dec in (1,):
                    y = abs(v) / div
                    if div == 1e6 and y >= 10: s = f'{y:,.1f}'; cands |= {s, s.replace(',', 'X').replace('.', ',').replace('X', '.')}
            for i, sp in enumerate(seiten):
                if any(re.search(r'(?<![\d.,])' + re.escape(c) + r'(?![\d])', sp) for c in cands) and re.search(r'total assets|bilanzsumme|summe aktiva|revenue|umsatz|net (income|profit)|ergebnis|equity|eigenkapital', sp, re.I):
                    treffer.setdefault(kz, (u, i + 1)); break
        if treffer: break
    return treffer
def verarbeite(r, uid, urls):
    name, land, isin, tk, bse = r[0], r[2], r[4], r[5], r[6]
    notiz = []; ergaenzt = []
    # Stammdaten
    g = gleif(isin, name, land)
    if g:
        if not r[10] and g['lei']: r[10] = g['lei']; ergaenzt.append('LEI')
        if not r[3] and g['sitz']: r[3] = g['sitz'].title(); ergaenzt.append('Sitz')
        if not r[11] and g['reg'] and g['jur']: r[11] = f"{g['reg']} ({g['jur'][:2]})"; ergaenzt.append('Handelsregisternummer')
    else: notiz.append('GLEIF: kein eindeutiger Treffer')
    if not r[1] and rechtsform(name): r[1] = rechtsform(name); ergaenzt.append('Rechtsform (aus Name)')
    if ergaenzt: r[15] = (r[15] + ' | ' if r[15] else '') + 'Anreicherung (' + ('GLEIF, ' if g else '') + 'bitte prüfen): ' + ', '.join(ergaenzt)
    # Kennzahlen
    sy = None; daten = {}
    if tk:
        t2 = str(tk).strip().replace(' ', '-')
        cands = [t2] if '.' in t2 else [t2 + s for s in (SUFFIX.get(bse) or LAND_SUFFIX.get(land) or [''])]
        for c in cands:
            daten = yahoo(c)
            if daten: sy = c; break
    if not daten:
        sym = yahoo_suche(name, land)
        if sym:
            daten = yahoo(sym)
            if daten: sy = sym; notiz.append(f'Yahoo-Kürzel {sym} über Namenssuche (Name gleich), Ticker in Tabelle fehlte/passte nicht')
    if not daten:
        notiz.append('keine Kennzahlen: weder Geschäftsbericht gefunden noch bei Yahoo Daten' + (f' (Ticker {tk})' if tk else ' (kein Ticker)'))
        return ergaenzt, 0, '', notiz
    heute = dt.date.today().isoformat(); eintraege = []
    spaet = max(daten)
    last = {KZ[YT[k][0]][0]: v[0] * (-1 if (YT[k][1] == 'abs' and v[0] < 0) else 1) if YT[k][1] == 'abs' else v[0] for k, v in daten[spaet].items() if YT.get(k, (None,))[0]}
    bt = bericht_pruefen(name, urls, spaet, last) if urls else {}
    for sd in sorted(daten):
        for k, (v, cur) in daten[sd].items():
            if not YT.get(k, (None,))[0]: continue
            kn = YT[k][0]; wert = abs(v) if YT[k][1] == 'abs' else v
            _, code, bereich, typ, *_ = KZ[kn]
            q, url, seite = 'Yahoo Finance (Sekundärquelle, Geschäftsbericht nicht abgeglichen)', f'https://finance.yahoo.com/quote/{sy}/financials/', ''
            hint = 'Rechnungslegung nicht angegeben (Yahoo)'
            if sd == spaet and kn in bt: q, url, seite = f'Geschäftsbericht (Wert mit Yahoo abgeglichen)', bt[kn][0], str(bt[kn][1]); hint = 'Wert aus Yahoo, im Bericht auf der Seite gefunden; Rechnungslegung nicht geprüft'
            eintraege.append(dict(geschaeftsjahr=int(sd[:4]), stichtag=sd, rechnungslegung='Sonstige', waehrung=cur if typ in ('Geld', 'JeAktie') else None, kennzahl=kn, code=code, bereich=bereich,
                                  wert=wert, eingabe_wert=wert, eingabe_einheit='absolut', quelle=q, url=url, seite=seite, hinweis=hint, importdatei='batch_anreichern.py', importdatum=heute))
    AUSGABE.mkdir(parents=True, exist_ok=True); pf = AUSGABE / f'{uid}.json'
    alt = json.loads(pf.read_text(encoding='utf-8')) if pf.exists() else {'unternehmen_id': uid, 'name': name, 'eintraege': [], 'quellen': []}
    ex = {(e['geschaeftsjahr'], e['code']): e for e in alt['eintraege']}
    for e in eintraege: ex[(e['geschaeftsjahr'], e['code'])] = e
    alt['eintraege'] = [ex[k] for k in sorted(ex)]; alt['name'] = name
    pf.write_text(json.dumps(alt, ensure_ascii=False, indent=1), encoding='utf-8')
    jahre = sorted({e['geschaeftsjahr'] for e in eintraege})
    quelle = 'Geschäftsbericht (teilweise) + Yahoo' if bt else 'Yahoo'
    if urls and not bt: notiz.append('Geschäftsbericht-Link vorhanden, Werte dort nicht gefunden')
    if not urls: notiz.append('kein Geschäftsbericht-PDF gefunden (Quellen-Dokumente und IR-Seite)')
    return ergaenzt, len(eintraege), f'{quelle}; GJ {jahre[0]}-{jahre[-1]}', notiz
def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    bloecke = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    stand = list(csv.DictReader(open(STAND, encoding='utf-8'))) if STAND.exists() else []
    fertig = {s['unternehmen_id'] for s in stand}; charge = max([int(s['charge']) for s in stand] or [0]) + 1
    wb = openpyxl.load_workbook(T / 'Unternehmen_Tabelle.xlsx'); ws = wb['Unternehmen']
    rows = [list(r) for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]
    ids = [x[0] for x in list(csv.reader(open(T / 'Unternehmen_Tabelle.csv', encoding='utf-8-sig'), delimiter=';'))[1:]]
    assert len(ids) == len(rows)
    docs = {}
    for d in wb['Quellen-Dokumente'].iter_rows(min_row=2, values_only=True):
        if d[0] and d[4] and '.pdf' in str(d[4]).lower(): docs.setdefault(d[0], []).append(str(d[4]))
    offen = [i for i in range(len(rows)) if ids[i] and ids[i] not in fertig]
    offen.sort(key=lambda i: (0 if (str(rows[i][7]).lower() == 'ja' and rows[i][5]) else 1, i))
    todo = offen[:n * bloecke]
    neu = []
    for pos, i in enumerate(todo):
        charge_i = charge + pos // n
        r, uid = rows[i], ids[i]
        try: erg, k, qu, notiz = verarbeite(r, uid, docs.get(r[0], [])[:3] or finde_berichte([r[16], r[13]]))
        except Exception as ex: erg, k, qu, notiz = [], 0, '', [f'Fehler: {ex}']
        neu.append(dict(unternehmen_id=uid, name=r[0], charge=charge_i, stammdaten_ergaenzt='; '.join(erg), kennzahlen=k, quelle=qu, notiz=' | '.join(notiz)))
        print(uid, r[0], '->', k, 'Kennzahlen;', qu, ';', erg, ';', notiz, flush=True)
    ws.delete_rows(2, ws.max_row)
    for r in rows: ws.append(r)
    wb.save(T / 'Unternehmen_Tabelle.xlsx')
    head = [c.value for c in ws[1]]
    with open(T / 'Unternehmen_Tabelle.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, delimiter=';'); w.writerow(['unternehmen_id'] + head)
        for i, r in zip(ids, rows): w.writerow([i] + ['' if v is None else v for v in r])
    STAND.parent.mkdir(exist_ok=True)
    with open(STAND, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, ['unternehmen_id', 'name', 'charge', 'stammdaten_ergaenzt', 'kennzahlen', 'quelle', 'notiz']); w.writeheader(); w.writerows(stand + neu)
main()
