"""Wahlregister: alle Wahlen der Weltkugel in einem einheitlichen Format (app/data/wahlen.json).

Konzept (Robin, 06.11.2026): Die Karte zeigt immer genau eine Wahl. Jede Wahl hat eine Ebene E0 bis E4 (Supranational, National,
Regional, Kommunal, Lokal; Namen je Land in EBENEN_NAMEN), ein Gremium oder Amt, einen Termin, eine oder mehrere Stimmarten und
Auszählungseinheiten von grob nach fein (Gesamt, Teilgebiete, Wahlkreise). "wahlkreis" heißt: dort wird ein Mandat vergeben
(durchgezogene Grenze), "zaehlgebiet" heißt: dort wird nur ausgezählt (gestrichelte Grenze).

Jede Quelle ist ein Leser, der dasselbe Format füllt:
  national()      Unterhaus bzw. Einkammerparlament und direkt gewählte Oberhäuser aller Staaten (data/parlamente.json: IPU Parline, Wikipedia)
  bundestag()     Bundestagswahl 2025: Gesamt, 16 Länder, 299 Wahlkreise (geo/wahlkreise_bund.geojson, Die Bundeswahlleiterin)
  europawahl()    Europawahl 2024 in Deutschland: Gesamt, 16 Länder, 400 Kreise (Die Bundeswahlleiterin, ew24 kerg2.csv)
  regional()      Landtage und Parlamente der Gliedstaaten und Regionen (data/parlamente.json); NRW 2022 zusätzlich je Kreis (IT.NRW Heft 1)
  kommunal()      Kommunalwahl NRW 2025: Räte, Kreistage, Gemeinderäte, Bezirksvertretungen (data/kommunal.json, IT.NRW)

Format je Wahl (Listen statt Objekten, damit die Datei klein bleibt):
  { id, e, land, gebiet, geo, name, titel, gremium, kammer, datum, status, stimmarten: [[schlüssel, Name]], system,
    g: { s: { stimmart: [[partei, stimmen|null, prozent, prozent_vorwahl|null]] }, sitze: [[partei, sitze, sitze_vorwahl|null]],
         sitze_n, sitze_hinweis, wb, w, bet, bet_vor, amt: {amt, name, partei, anteil, wahl} },
    vor: { datum }, einheiten: [{ id, name, einzahl, art, geo, werte: { schlüssel: { n, s: {stimmart: [[partei, stimmen, prozent, vor]]}, wb, w, bet } } }],
    quelle: { name, url, lizenz } }

Aufruf:  pip install pyshp shapely pyproj requests
         python3 app/wahlen_daten.py                 (lädt ew24 kerg2.csv und VG1000-Kreise, falls nicht vorhanden)
         python3 app/wahlen_daten.py --ohne-abruf    (nur vorhandene Dateien)
"""
import argparse
import csv
import io
import json
import re
import zipfile
from datetime import date
from pathlib import Path

HIER = Path(__file__).resolve().parent
QUELLEN = HIER.parent / "wahlen" / "quellen"
OUT = HIER / "data" / "wahlen.json"
KREISE_GEO = HIER / "geo" / "kreise_de.geojson"
LWK_NW_GEO = HIER / "geo" / "landtagswahlkreise_nw.geojson"
WK_GB_GEO = HIER / "geo" / "wahlkreise_gb.geojson"
WK_FR_GEO = HIER / "geo" / "wahlkreise_fr.geojson"

EW24_URL = "https://www.bundeswahlleiterin.de/europawahlen/2024/ergebnisse/opendata/ew24/csv/kerg2.csv"
LTW_NW22 = "https://www.wahlergebnisse.nrw/landtagswahlen/2022/"
LTW_NW22_DATEIEN = {"LW22_WK_insgesamt.txt": "nw_ltw22_wahlkreise.csv", "LW22_Ergebnisse_fr%C3%BCherer_Wahlen.csv": "nw_ltw22_fruehere_wahlen.csv",
                    "LW22_Bewerber_WK.txt": "nw_ltw22_gewaehlte_wk.csv"}
LTW_NW22_SHP = LTW_NW22 + "wahlkreiskarten/16_LW2022_NRW_Wahlkreise.zip"
GB_ERG = "https://electionresults.parliament.uk/general-elections/{}/candidacies.csv"    # UK Parliament, Open Parliament Licence v3.0
GB_GE = {"2024": (6, "gb_ge24_kandidaturen.csv"), "2019n": (5, "gb_ge19_fiktiv_kandidaturen.csv")}   # 5 = Wahl 2019 umgerechnet auf die Grenzen 2024
GB_GRENZEN = ("https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
              "Westminster_Parliamentary_Constituencies_July_2024_Boundaries_UK_BUC/FeatureServer/0/query")   # ONS, OGL v3.0
GB_SPALTEN = ["Country name", "Constituency name", "Constituency geographic code", "Electorate", "Election valid vote count", "Election invalid vote count",
              "Candidate given name", "Candidate family name", "Main party abbreviation", "Main party name", "Candidate is standing as Commons Speaker",
              "Candidate is standing as independent", "Candidate vote count", "Candidate result position"]
GB_PARTEI = {"Lab": "Labour", "Con": "Conservatives", "RUK": "Reform UK", "BRX": "Reform UK", "LD": "Lib Dems", "Green": "Grüne", "SNP": "SNP",
             "SF": "Sinn Féin", "WPB": "Workers Party", "PC": "Plaid Cymru", "DUP": "DUP", "APNI": "Alliance", "UUP": "UUP", "SDLP": "SDLP", "TUV": "TUV"}
GB_FARBEN = {"Labour": "#e4003b", "Conservatives": "#0087dc", "Reform UK": "#12b6cf", "Lib Dems": "#faa61a", "Grüne": "#02a95b", "SNP": "#fdf38e",
             "Sinn Féin": "#326760", "Workers Party": "#9b2335", "Plaid Cymru": "#005b54", "DUP": "#d46a4c", "Alliance": "#f6cb2f", "UUP": "#48a5ee",
             "SDLP": "#2aa82c", "TUV": "#0c3a6a", "Unabhängige": "#9aa3ad", "Speaker": "#6b7280"}
FR_LEG24 = {"t1": ("https://static.data.gouv.fr/resources/elections-legislatives-des-30-juin-et-7-juillet-2024-resultats-definitifs-du-1er-tour/"
                    "20240710-171413/resultats-definitifs-par-circonscriptions-legislatives.csv", "fr_leg24_t1.csv"),
            "t2": ("https://static.data.gouv.fr/resources/elections-legislatives-des-30-juin-et-7-juillet-2024-resultats-definitifs-du-2nd-tour/"
                   "20240710-170728/resultats-definitifs-par-circonscription.csv", "fr_leg24_t2.csv")}       # Ministère de l'Intérieur, Licence Ouverte 2.0
FR_GRENZEN = ("https://static.data.gouv.fr/resources/contours-geographiques-des-circonscriptions-legislatives/"
              "20240613-191520/circonscriptions-legislatives-p10.geojson")                                      # data.gouv.fr, Licence Ouverte 2.0
FR_UEBERSEE = {"971": "ZA", "972": "ZB", "973": "ZC", "974": "ZD", "975": "ZS", "976": "ZM"}             # Départements in den Ergebnissen -> Kürzel in den Grenzen
FR_NUANCE = {"UG": "NFP", "RN": "RN", "ENS": "Ensemble", "LR": "LR", "UXD": "LR-RN (Ciotti)", "DVG": "Divers gauche", "DVD": "Divers droite",
             "DVC": "Divers centre", "HOR": "Horizons", "REG": "Regionalisten", "ECO": "Écologistes", "DIV": "Divers", "REC": "Reconquête", "EXG": "Extrême gauche",
             "EXD": "Extrême droite", "DSV": "Souverainistes", "UDI": "UDI", "FI": "LFI", "SOC": "PS", "COM": "PCF", "VEC": "Les Écologistes", "RDG": "PRG"}
FR_FARBEN = {"NFP": "#e4032e", "RN": "#0d378a", "Ensemble": "#ffc400", "LR": "#0066cc", "LR-RN (Ciotti)": "#3c4a7a", "Divers gauche": "#f29ab0",
             "Divers droite": "#74b9c9", "Divers centre": "#f5c98b", "Horizons": "#4f6fd6", "Regionalisten": "#c9a27a", "Écologistes": "#57b45d", "Divers": "#9aa3ad",
             "Reconquête": "#333a4d", "Extrême gauche": "#9b0d1b", "Extrême droite": "#4a4f5a", "Souverainistes": "#7d4cb0", "UDI": "#4ac3d6", "LFI": "#c9462c",
             "PS": "#e75480", "PCF": "#a80000", "Les Écologistes": "#2e9b45", "PRG": "#f0a0a0"}
VG1000_URL = "https://daten.gdz.bkg.bund.de/produkte/vg/vg1000_ebenen_1231/aktuell/vg1000_12-31.utm32s.shape.ebenen.zip"

# Ebenennamen je Land (None = Ebene gibt es dort nicht); "_" gilt für alle übrigen Länder
EU = {"AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK"}
EBENEN_NAMEN = {
    "_": ["Supranational", "Staat", "Region", "Kommune", "Gemeinde"],
    "_EU": ["Europa", "Staat", "Region", "Kommune", "Gemeinde"],
    "DE": ["Europa", "Bund", "Land", "Kreis/Stadt", "Gemeinde/Bezirk"],
    "AT": ["Europa", "Bund", "Land", "Bezirk", "Gemeinde"],
    "CH": [None, "Bund", "Kanton", "Bezirk", "Gemeinde"],
    "US": [None, "Bund", "Bundesstaat", "County", "Stadt/Gemeinde"],
    "GB": [None, "Vereinigtes Königreich", "Landesteil", "Council", "Gemeinde"],
    "FR": ["Europa", "Staat", "Region", "Département", "Kommune"],
    "IT": ["Europa", "Staat", "Region", "Provinz", "Kommune"],
    "ES": ["Europa", "Staat", "Autonome Gemeinschaft", "Provinz", "Gemeinde"],
    "NL": ["Europa", "Staat", "Provinz", None, "Gemeinde"],
    "BE": ["Europa", "Föderalstaat", "Region", "Provinz", "Gemeinde"],
    "CA": [None, "Bund", "Provinz", None, "Gemeinde"],
    "AU": [None, "Bund", "Bundesstaat", None, "Gemeinde"],
    "IN": [None, "Union", "Bundesstaat", "Distrikt", "Gemeinde"],
    "BR": [None, "Bund", "Bundesstaat", None, "Gemeinde"],
    "MX": [None, "Bund", "Bundesstaat", None, "Gemeinde"],
}

# Deutsche Parteien: Kurzname und Farbe (für dunklen Hintergrund geprüft; CDU grau statt schwarz, CSU dunkler als AfD)
DE_FARBEN = {"CDU": "#5f6672", "CSU": "#2c5aa8", "SPD": "#e3000f", "GRÜNE": "#46962b", "FDP": "#ffd600", "AfD": "#00a6e0", "Die Linke": "#be3075",
             "BSW": "#7d254f", "FREIE WÄHLER": "#f39200", "SSW": "#4f86c6", "Volt": "#6b3fa0", "Die PARTEI": "#b5152b", "Tierschutzpartei": "#3d8c84",
             "ÖDP": "#ff6400", "PIRATEN": "#f8a01c", "FAMILIE": "#c49a4a", "Sonstige": "#8b95a3", "Wählergruppen": "#a58fc7", "CDU/CSU": "#5f6672"}
DE_ORDNUNG = ["Die Linke", "BSW", "SPD", "GRÜNE", "SSW", "Volt", "Die PARTEI", "Tierschutzpartei", "ÖDP", "PIRATEN", "FAMILIE", "Sonstige",
              "Wählergruppen", "FREIE WÄHLER", "FDP", "CDU", "CSU", "CDU/CSU", "AfD"]
DE_MUSTER = [(r"Christlich Demokratische|Christian Democratic Union|^CDU", "CDU"), (r"Christlich-Soziale|Christian Social Union|^CSU", "CSU"),
             (r"Sozialdemokratische|Social Democratic Party|^SPD", "SPD"), (r"Grüne|Greens|GRÜNE|Green Party|Alliance 90", "GRÜNE"),
             (r"Linke|Left Party|^The Left", "Die Linke"), (r"Alternative für|Alternative for Germany|^AfD", "AfD"),
             (r"Freie Demokratische|Free Democratic|^FDP", "FDP"), (r"Wagenknecht|^BSW", "BSW"), (r"Freie Wähler|Free Voters|FREIE WÄHLER", "FREIE WÄHLER"),
             (r"SSW|South.?Schleswig|Südschleswig", "SSW"), (r"^Volt", "Volt"), (r"Tierschutz|Animal Protection", "Tierschutzpartei")]
DE_LAND_NR = {"01": "DE-SH", "02": "DE-HH", "03": "DE-NI", "04": "DE-HB", "05": "DE-NW", "06": "DE-HE", "07": "DE-RP", "08": "DE-BW",
              "09": "DE-BY", "10": "DE-SL", "11": "DE-BE", "12": "DE-BB", "13": "DE-MV", "14": "DE-SN", "15": "DE-ST", "16": "DE-TH"}
DE_LAND_TITEL = {"DE-BE": ("Wahl zum Abgeordnetenhaus", "Abgeordnetenhaus von Berlin"), "DE-HB": ("Bürgerschaftswahl", "Bremische Bürgerschaft"),
                 "DE-HH": ("Bürgerschaftswahl", "Hamburgische Bürgerschaft")}


def de_kurz(n):
    n = (n or "").strip()
    if n in DE_FARBEN:
        return n
    if n.upper() == "DIE LINKE":
        return "Die Linke"
    for m, k in DE_MUSTER:
        if re.search(m, n):
            return k
    return n


def hell(farbe):
    """Sehr dunkle Parteifarben (Schwarz) sind auf der dunklen Karte nicht von "keine Daten" zu unterscheiden: aufhellen."""
    f = (farbe or "").strip()
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", f):
        return f or "#8b95a3"
    r, g, b = (int(f[i:i + 2], 16) for i in (1, 3, 5))
    return "#5f6672" if 0.2126 * r + 0.7152 * g + 0.0722 * b < 40 else f


def r1(x):
    return None if x is None else round(x, 1)


def anteile(liste, gueltig=None):
    """[(partei, stimmen)] -> [[partei, stimmen, prozent, None]] absteigend."""
    t = gueltig or sum(n for _, n in liste) or 1
    return [[p, n, r1(n / t * 100), None] for p, n in sorted(liste, key=lambda x: -x[1])]


# ---------------------------------------------------------------- national
def kammer_ergebnis(k, de=False):
    """Gesamtergebnis einer Kammer aus parlamente.json: Stimmen laut Wahlartikel, Sitze nach der Wahl (IPU) bzw. laut Wahlartikel."""
    st = k.get("stimmen") or {}
    parteien = [p for p in st.get("parteien") or [] if p.get("prozent") is not None and p["prozent"] <= 100]
    name = (lambda p: de_kurz(p)) if de else (lambda p: p)
    g = {"s": {"s": [[name(p["partei"]), None, p["prozent"], None] for p in parteien]} if parteien else {}}
    farben = {name(p["partei"]): hell(p.get("farbe")) for p in parteien}
    w = k.get("wahl") or {}
    if w.get("sitze") and (not st.get("datum") or w.get("datum") == st.get("datum")):
        g["sitze"] = [[name(x[0]), x[1], None] for x in w["sitze"] if x[1] is not None]
        farben.update({name(x[0]): hell(x[2]) for x in w["sitze"] if len(x) > 2})
        g["sitze_hinweis"] = "Sitze nach der Wahl laut IPU Parline"
    elif parteien and any(p.get("sitze") is not None for p in parteien):
        g["sitze"] = [[name(p["partei"]), p["sitze"], None] for p in parteien if p.get("sitze") is not None]
        g["sitze_hinweis"] = "Sitze der größten Parteien laut Wahlartikel (Wikipedia); kleinere Parteien fehlen"
    elif (k.get("aktuell") or {}).get("sitze"):
        a = k["aktuell"]
        g["sitze"] = [[name(x["partei"]), x["sitze"], None] for x in a["sitze"] if x["partei"] != "vakant"]
        farben.update({name(x["partei"]): hell(x.get("farbe")) for x in a["sitze"]})
        g["sitze_hinweis"] = f"Heutige Zusammensetzung laut Wikipedia (Abruf {a.get('abruf', '')}), kein Wahlergebnis"
    if g.get("sitze"):
        g["sitze_n"] = sum(x[1] for x in g["sitze"])
    if st.get("beteiligung"):
        g["bet"] = st["beteiligung"]
    elif w.get("beteiligung"):
        g["bet"] = w["beteiligung"]
    datum = st.get("datum") or w.get("datum") or (k.get("letzte_wahl") or {}).get("datum")
    quelle = {"name": "Wikipedia (Wahlartikel)" if parteien else "IPU Parline", "url": st.get("url") or w.get("url") or "",
              "lizenz": "CC BY-SA 4.0" if parteien else "CC BY-NC-SA 4.0"}
    status = "vorläufig" if st.get("laufend") or (k.get("juengst") or {}).get("ergebnis", "").startswith("vorläufig") else ""
    return g, farben, datum, quelle, status


def national(pa):
    out = []
    for iso, s in sorted(pa["staaten"].items()):
        for k in s["kammern"]:
            if k["typ"] == "oberhaus" and not (k.get("stimmen") or {}).get("parteien"):
                continue                              # Oberhäuser ohne Stimmen sind meist nicht direkt gewählt
            g, farben, datum, quelle, status = kammer_ergebnis(k)
            if not (g.get("s") or g.get("sitze")) or not datum:
                continue
            kammer = "oberhaus" if k["typ"] == "oberhaus" else "unterhaus"
            out.append({"id": f"{iso}-{kammer}-{datum[:4]}", "e": 1, "land": iso, "gebiet": iso, "geo": "laender", "name": "",
                        "titel": "Parlamentswahl" if kammer == "unterhaus" else "Wahl zum Oberhaus", "gremium": k.get("name_lokal") or k.get("name"),
                        "kammer": kammer, "datum": datum, "status": status, "stimmarten": [["s", "Stimmen"]], "g": g, "farben": farben,
                        "quelle": quelle, "einheiten": []})
    return out


# ---------------------------------------------------------------- Bundestag 2025
def bundestag(pa, wk_geo, laender_geo):
    wk = json.loads(wk_geo.read_text())
    namen = {f["properties"]["name"].replace("Freie Hansestadt ", ""): f["properties"]["code"] for f in json.loads(laender_geo.read_text())["features"]}
    land_s = {}
    werte_wk = {}
    for f in wk["features"]:
        p = f["properties"]
        code = namen[p["land"]]
        L = land_s.setdefault(code, {"n": p["land"], "e": {}, "z": {}, "wb": 0, "w": 0})
        L["wb"] += p["wb"] or 0
        L["w"] += p["w"] or 0
        for st in ("e", "z"):
            for partei, n in p[st]:
                L[st][partei] = L[st].get(partei, 0) + n
        werte_wk[str(p["nr"])] = {"n": f"{p['nr']} {p['name']}", "l": code, "s": {st: [x[:3] for x in anteile([(de_kurz(a), b) for a, b in p[st]])] for st in ("z", "e")},
                                 "wb": p["wb"], "w": p["w"]}
    werte_land = {c: {"n": L["n"], "s": {st: [x[:3] for x in anteile([(de_kurz(a), b) for a, b in L[st].items()])] for st in ("z", "e")}, "wb": L["wb"], "w": L["w"]}
                  for c, L in land_s.items()}
    ges = {st: {} for st in ("z", "e")}
    for L in land_s.values():
        for st in ("z", "e"):
            for partei, n in L[st].items():
                ges[st][de_kurz(partei)] = ges[st].get(de_kurz(partei), 0) + n
    wb, w = sum(L["wb"] for L in land_s.values()), sum(L["w"] for L in land_s.values())
    k = next(k for k in pa["staaten"]["DE"]["kammern"] if k["typ"] == "unterhaus")
    sitze = [[de_kurz(x[0]), x[1], None] for x in k["wahl"]["sitze"]]
    return {"id": "DE-BT-2025", "e": 1, "land": "DE", "gebiet": "DE", "geo": "laender", "name": "Deutschland", "titel": "Bundestagswahl",
            "gremium": "Deutscher Bundestag", "kammer": "unterhaus", "datum": "2025-02-23", "status": "endgültig",
            "stimmarten": [["z", "Zweitstimmen"], ["e", "Erststimmen"]],
            "system": "Verhältniswahl mit Erst- und Zweitstimme, 630 Sitze. Die Zweitstimmen bestimmen die Sitzverteilung; ein Wahlkreissieger erhält sein Mandat seit 2025 nur, wenn die Zweitstimmen seiner Partei es decken.",
            "g": {"s": {st: anteile(list(ges[st].items())) for st in ("z", "e")}, "sitze": sitze, "sitze_n": sum(x[1] for x in sitze),
                  "sitze_hinweis": "Sitze nach der Wahl laut IPU Parline", "wb": wb, "w": w, "bet": r1(w / wb * 100)},
            "einheiten": [{"id": "land", "name": "Länder", "einzahl": "Land", "art": "teilgebiet", "geo": "de-laender", "werte": werte_land},
                          {"id": "wk", "name": "Wahlkreise", "einzahl": "Wahlkreis", "art": "wahlkreis", "geo": "wahlkreise-bund", "werte": werte_wk}],
            "quelle": {"name": "Die Bundeswahlleiterin, endgültiges Ergebnis (kerg2.csv)", "url": "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/ergebnisse.html",
                       "lizenz": "Datenlizenz Deutschland – Namensnennung 2.0"}}


# ---------------------------------------------------------------- Europawahl 2024 (Deutschland)
def zahl(s):
    s = (s or "").strip().replace(".", "")
    return int(s) if s.isdigit() else None


def pz(s):
    s = (s or "").strip().replace(",", ".")
    try:
        return round(float(s), 1)
    except ValueError:
        return None


def europawahl(csv_pfad):
    if not csv_pfad.exists():
        return None
    rows = list(csv.reader(io.StringIO(csv_pfad.read_text(encoding="utf-8-sig")), delimiter=";"))
    kopf = next(i for i, r in enumerate(rows) if r and r[0] == "Wahlart")
    sp = {n: i for i, n in enumerate(rows[kopf])}
    geb = {}
    for r in rows[kopf + 1:]:
        if len(r) < len(sp) - 2:
            continue
        art, nr = r[sp["Gebietsart"]], r[sp["Gebietsnummer"]]
        d = geb.setdefault((art, nr), {"n": r[sp["Gebietsname"]], "s": [], "wb": None, "w": None, "wb_v": None, "w_v": None})
        gruppe, name = r[sp["Gruppenart"]], r[sp["Gruppenname"]]
        if gruppe == "System-Gruppe":
            if name == "Wahlberechtigte":
                d["wb"], d["wb_v"] = zahl(r[sp["Anzahl"]]), zahl(r[sp["VorpAnzahl"]])
            elif name == "Wählende":
                d["w"], d["w_v"] = zahl(r[sp["Anzahl"]]), zahl(r[sp["VorpAnzahl"]])
        elif gruppe == "Partei" and zahl(r[sp["Anzahl"]]):
            d["s"].append([de_kurz(name), zahl(r[sp["Anzahl"]]), pz(r[sp["Prozent"]]), pz(r[sp["VorpProzent"]])])
    fertig = lambda d: {"n": d["n"], "s": {"s": sorted(d["s"], key=lambda x: -x[1])}, "wb": d["wb"], "w": d["w"]}
    bund = geb[("Bund", "99")]
    laender = {DE_LAND_NR[nr]: fertig(d) for (art, nr), d in geb.items() if art == "Land"}
    kreise = {nr: fertig(d) for (art, nr), d in geb.items() if art == "Kreis"}
    return {"id": "DE-EP-2024", "e": 0, "land": "DE", "gebiet": "DE", "geo": "laender", "name": "Deutschland", "titel": "Europawahl",
            "gremium": "Europäisches Parlament (96 Abgeordnete aus Deutschland)", "kammer": "unterhaus", "datum": "2024-06-09", "status": "endgültig",
            "stimmarten": [["s", "Stimmen"]],
            "system": "Verhältniswahl mit einer Stimme ohne Sperrklausel; Bundes- oder Landeslisten. Es gibt keine Wahlkreise: Länder und Kreise sind nur Zählgebiete.",
            "g": {"s": {"s": sorted(bund["s"], key=lambda x: -x[1])}, "wb": bund["wb"], "w": bund["w"], "bet": r1(bund["w"] / bund["wb"] * 100),
                  "bet_vor": r1(bund["w_v"] / bund["wb_v"] * 100) if bund["wb_v"] else None},
            "vor": {"datum": "2019-05-26", "titel": "Europawahl 2019"},
            "einheiten": [{"id": "land", "name": "Länder", "einzahl": "Land", "art": "zaehlgebiet", "geo": "de-laender", "werte": laender},
                          {"id": "kreis", "name": "Kreise", "einzahl": "Kreis", "art": "zaehlgebiet", "geo": "kreise-de", "werte": kreise}],
            "quelle": {"name": "Die Bundeswahlleiterin, Europawahl 2024, Ergebnisse nach Kreisen (kerg2.csv)", "url": EW24_URL,
                       "lizenz": "Datenlizenz Deutschland – Namensnennung 2.0"}}


def kreise_flaechen(zip_pfad, namen):
    """VG1000 (BKG, 1:1 Mio.) -> geo/kreise_de.geojson, WGS84, vereinfacht; Schlüssel = fünfstelliger Kreisschlüssel wie bei der Bundeswahlleiterin."""
    import shapefile
    from pyproj import Transformer
    from shapely.geometry import mapping, shape
    from shapely.ops import transform, unary_union
    z = zipfile.ZipFile(zip_pfad)
    pre = next(n[:-4] for n in z.namelist() if n.upper().endswith("VG1000_KRS.SHP"))
    r = shapefile.Reader(shp=io.BytesIO(z.read(pre + ".shp")), dbf=io.BytesIO(z.read(pre + ".dbf")), encoding="utf-8")
    felder = [f[0] for f in r.fields[1:]]
    tr = Transformer.from_crs("EPSG:25832", "EPSG:4326", always_xy=True).transform
    teile = {}
    for sr in r.iterShapeRecords():
        rec = dict(zip(felder, sr.record))
        if rec["GF"] != 4:                         # nur Landflächen (ohne Gewässer/Küstenmeer)
            continue
        teile.setdefault(rec["AGS"], []).append(shape(sr.shape.__geo_interface__))
    def rund(c):
        return [rund(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(c[0], 4), round(c[1], 4)]
    feats = []
    for ags, gs in sorted(teile.items()):
        g = transform(tr, unary_union(gs)).simplify(0.004, preserve_topology=True)
        feats.append({"type": "Feature", "properties": {"id": ags, "name": namen.get(ags, ags)}, "geometry": {"type": g.geom_type, "coordinates": rund(mapping(g)["coordinates"])}})
    KREISE_GEO.write_text(json.dumps({"type": "FeatureCollection", "quelle": "© GeoBasis-DE / BKG (2025), VG1000, dl-de/by-2-0", "features": feats},
                                     ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(feats)


# ---------------------------------------------------------------- Landtagswahl NRW 2022 je Landtagswahlkreis
def _nw_zeilen(pfad, wahl):
    """Zeilen einer Ergebnisdatei der Landeswahlleiterin NRW (Kopfzeile beginnt mit "Wahl;"), nur die Zeilen der Wahl `wahl`."""
    zeilen = pfad.read_text(encoding="utf-8-sig").splitlines()
    i = next(n for n, z in enumerate(zeilen) if z.startswith("Wahl;"))
    kopf = next(csv.reader([zeilen[i]], delimiter=";"))
    return kopf, [z for z in csv.reader(zeilen[i + 1:], delimiter=";") if z and z[0] == wahl]


def _nw_stimmen(kopf, z, st):
    """[(partei, stimmen)] einer Zeile für Erst- (E) oder Zweitstimmen (Z); Einzelbewerber zusammengefasst, Sonstige und Gültig/Ungültig weg."""
    out, eb = [], 0
    for k, v in zip(kopf, z):
        if not k.endswith(f" [{st}]") or k.startswith(("Ungültige", "Gültige", "Sonstige")):
            continue
        n = zahl(v) or 0
        name = k[:-4].strip()
        if name.startswith("Einzelbewerber"):
            if name != "Einzelbewerber/-innen":      # Landeszeile fasst sie schon in einer Spalte zusammen
                eb += n
            else:
                eb = max(eb, n)
            continue
        if n:
            out.append((de_kurz(name), n))
    if eb:
        out.append(("Einzelbewerber", eb))
    return out


def _nw_kennzahlen(kopf, z):
    d = dict(zip(kopf, z))
    wb = zahl(d.get("Wahlberechtigte insgesamt"))
    w = zahl(d.get("Wähler/-innen"))
    gz = zahl(d.get("Gültige Stimmen [Z]"))
    ge = zahl(d.get("Gültige Stimmen [E]"))
    return wb, w, gz, ge


def ltw_nw22(sitze_ergebnis):
    """Landtagswahl NRW 15.05.2022: Gesamtergebnis und 128 Landtagswahlkreise mit Erst- und Zweitstimmen,
    Veränderung zur Landtagswahl 2017 (von der Landeswahlleiterin auf die Wahlkreise 2022 umgerechnet)."""
    wk_p, fr_p, gw_p = (QUELLEN / f for f in LTW_NW22_DATEIEN.values())
    gewaehlt = {}                                  # direkt gewählte Abgeordnete je Wahlkreis
    if gw_p.exists():
        for z in csv.reader(gw_p.read_text(encoding="utf-8-sig").splitlines(), delimiter=";"):
            if len(z) >= 4 and z[0].strip().isdigit():
                nach, _, vor_n = z[3].partition(",")
                gewaehlt[str(int(z[0]))] = {"name": f"{vor_n.strip()} {nach.strip()}".strip(), "partei": de_kurz(z[2])}
    if not wk_p.exists():
        return None
    kopf, zeilen = _nw_zeilen(wk_p, "LW22")
    vor = {}
    if fr_p.exists():
        k17, z17 = _nw_zeilen(fr_p, "LW17")
        summe = {"wb": 0, "w": 0, "z": {}, "e": {}, "gz": 0, "ge": 0}    # Landesergebnis 2017 = Summe der Wahlkreise (die Datei hat keine Landeszeile)
        for z in z17:
            wb, w, gz, ge = _nw_kennzahlen(k17, z)
            vor[z[1]] = {"bet": r1(w / wb * 100) if wb and w else None,
                         **{st: {p: n / g * 100 for p, n in _nw_stimmen(k17, z, st.upper())} for st, g in (("z", gz), ("e", ge)) if g}}
            summe["wb"] += wb or 0
            summe["w"] += w or 0
            summe["gz"] += gz or 0
            summe["ge"] += ge or 0
            for st in ("z", "e"):
                for p, n in _nw_stimmen(k17, z, st.upper()):
                    summe[st][p] = summe[st].get(p, 0) + n
        if z17 and "000" not in vor:
            vor["000"] = {"bet": r1(summe["w"] / summe["wb"] * 100) if summe["wb"] else None,
                          **{st: {p: n / summe["g" + st] * 100 for p, n in summe[st].items()} for st in ("z", "e") if summe["g" + st]}}

    def ergebnis(z):
        wb, w, gz, ge = _nw_kennzahlen(kopf, z)
        v = vor.get(z[1], {})
        s = {}
        for st, g in (("z", gz), ("e", ge)):
            l = anteile(_nw_stimmen(kopf, z, st.upper()), g)
            for x in l:
                x[3] = r1(v.get(st, {}).get(x[0])) if v.get(st) else None
            s[st] = l
        return {"s": s, "wb": wb, "w": w, "bet": r1(w / wb * 100) if wb and w else None, "bet_vor": v.get("bet")}

    land = next(z for z in zeilen if z[1] == "000")
    werte = {}
    for z in zeilen:
        if z[1] == "000":
            continue
        e = ergebnis(z)
        werte[str(int(z[1]))] = {"n": f"{int(z[1])} {z[2]}", "s": e["s"], "wb": e["wb"], "w": e["w"], "bet": e["bet"], "bet_vor": e["bet_vor"]}
        if str(int(z[1])) in gewaehlt:
            werte[str(int(z[1]))]["direkt"] = gewaehlt[str(int(z[1]))]
    g = ergebnis(land)
    g.update({k: v for k, v in (sitze_ergebnis or {}).items() if k.startswith("sitze")})
    quelle = {"name": "Die Landeswahlleiterin NRW, endgültiges Ergebnis (LW22_WK_insgesamt), Grenzen: Wahlkreiskarten LTW 2022",
              "url": LTW_NW22 + "index.shtml"}
    return g, werte, quelle


def lwk_nw_flaechen(zip_pfad):
    """Shapefile der Landtagswahlkreise 2022 (DHDN Gauß-Krüger Zone 2) -> geo/landtagswahlkreise_nw.geojson, WGS84, vereinfacht."""
    import shapefile
    from pyproj import Transformer
    from shapely.geometry import mapping, shape
    from shapely.ops import transform
    z = zipfile.ZipFile(zip_pfad)
    pre = next(n[:-4] for n in z.namelist() if n.upper().endswith(".SHP"))
    r = shapefile.Reader(shp=io.BytesIO(z.read(pre + ".shp")), dbf=io.BytesIO(z.read(pre + ".dbf")), encoding="utf-8")
    tr = Transformer.from_crs("EPSG:31466", "EPSG:4326", always_xy=True).transform

    def rund(c):
        return [rund(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(c[0], 4), round(c[1], 4)]
    feats = []
    for sr in r.iterShapeRecords():
        nr, name = int(sr.record[0]), sr.record[1]
        g = transform(tr, shape(sr.shape.__geo_interface__)).simplify(0.0015, preserve_topology=True)
        feats.append({"type": "Feature", "properties": {"id": str(nr), "name": name}, "geometry": {"type": g.geom_type, "coordinates": rund(mapping(g)["coordinates"])}})
    feats.sort(key=lambda f: int(f["properties"]["id"]))
    LWK_NW_GEO.write_text(json.dumps({"type": "FeatureCollection", "quelle": "Die Landeswahlleiterin NRW, Wahlkreiskarten Landtagswahl 2022", "features": feats},
                                     ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(feats)


# ---------------------------------------------------------------- Vereinigtes Königreich: Unterhauswahl 2024 je Wahlkreis
def gb_laden(abruf):
    """Kandidaturen der Unterhauswahlen 2024 und 2019 (fiktiv, Grenzen 2024) vom UK Parliament, gekürzt auf die nötigen Spalten."""
    import requests
    for nr, datei in GB_GE.values():
        ziel = QUELLEN / datei
        if ziel.exists() or not abruf:
            continue
        r = requests.get(GB_ERG.format(nr), timeout=300)
        r.raise_for_status()
        zeilen = list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig"))))
        with ziel.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, GB_SPALTEN, extrasaction="ignore")
            w.writeheader()
            w.writerows(zeilen)
    if not WK_GB_GEO.exists() and abruf:
        r = requests.get(GB_GRENZEN, params={"where": "1=1", "outFields": "PCON24CD,PCON24NM", "outSR": 4326, "f": "geojson", "resultRecordCount": 2000}, timeout=300)
        r.raise_for_status()
        fc = r.json()

        def rund(c):
            return [rund(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(c[0], 4), round(c[1], 4)]
        feats = [{"type": "Feature", "properties": {"id": f["properties"]["PCON24CD"], "name": f["properties"]["PCON24NM"]},
                  "geometry": {"type": f["geometry"]["type"], "coordinates": rund(f["geometry"]["coordinates"])}} for f in fc["features"] if f.get("geometry")]
        WK_GB_GEO.write_text(json.dumps({"type": "FeatureCollection", "quelle": "Office for National Statistics, Westminster Parliamentary Constituencies (July 2024) BUC, OGL v3.0",
                                         "features": feats}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def _gb_partei(z):
    if z["Candidate is standing as Commons Speaker"] == "true":
        return "Speaker"
    if z["Candidate is standing as independent"] == "true" or not z["Main party abbreviation"]:
        return "Unabhängige"
    return GB_PARTEI.get(z["Main party abbreviation"], z["Main party name"] or z["Main party abbreviation"])


def _gb_wahlkreise(pfad):
    wk = {}
    for z in csv.DictReader(pfad.open(encoding="utf-8")):
        k = z["Constituency geographic code"]
        W = wk.setdefault(k, {"n": z["Constituency name"], "land": z["Country name"], "wb": zahl(z["Electorate"]),
                              "gueltig": zahl(z["Election valid vote count"]) or 0, "ungueltig": zahl(z["Election invalid vote count"]) or 0, "p": {}, "sieger": None})
        p = _gb_partei(z)
        W["p"][p] = W["p"].get(p, 0) + (zahl(z["Candidate vote count"]) or 0)
        if z["Candidate result position"] == "1":
            W["sieger"] = {"name": f"{z['Candidate given name']} {z['Candidate family name']}".strip(), "partei": p}
    return wk


def gb_ge24():
    """Unterhauswahl 4. Juli 2024: Gesamtergebnis, Sitze (Wahlkreissieger) und 650 Wahlkreise; Veränderung zur Wahl 2019, umgerechnet auf die Grenzen 2024."""
    p24, p19 = (QUELLEN / GB_GE[k][1] for k in ("2024", "2019n"))
    if not p24.exists():
        return None
    wk, vor = _gb_wahlkreise(p24), (_gb_wahlkreise(p19) if p19.exists() else {})

    def stimmen(W, V):
        l = anteile(list(W["p"].items()), W["gueltig"] or None)
        if V and V["gueltig"]:
            for x in l:
                x[3] = r1(V["p"].get(x[0], 0) / V["gueltig"] * 100) if x[0] in V["p"] else None
        return l
    werte, ges, ges_v, sitze = {}, {"p": {}, "gueltig": 0}, {"p": {}, "gueltig": 0}, {}
    wb = w = 0
    for k, W in wk.items():
        V = vor.get(k)
        werte[k] = {"n": W["n"], "s": {"s": stimmen(W, V)}, "wb": W["wb"], "w": W["gueltig"] + W["ungueltig"],
                    "bet": r1((W["gueltig"] + W["ungueltig"]) / W["wb"] * 100) if W["wb"] else None}
        if W["sieger"]:
            werte[k]["direkt"] = W["sieger"]
            sitze[W["sieger"]["partei"]] = sitze.get(W["sieger"]["partei"], 0) + 1
        wb += W["wb"] or 0
        w += W["gueltig"] + W["ungueltig"]
        for G, Q in ((ges, W), (ges_v, V)):
            if Q:
                G["gueltig"] += Q["gueltig"]
                for p, n in Q["p"].items():
                    G["p"][p] = G["p"].get(p, 0) + n
    sitze_v = {}
    for V in vor.values():
        if V["sieger"]:
            sitze_v[V["sieger"]["partei"]] = sitze_v.get(V["sieger"]["partei"], 0) + 1
    wb_v = sum(V["wb"] or 0 for V in vor.values())
    w_v = sum(V["gueltig"] + V["ungueltig"] for V in vor.values())
    g = {"s": {"s": stimmen(ges, ges_v if vor else None)}, "sitze": [[p, n, sitze_v.get(p, 0) if vor else None] for p, n in sorted(sitze.items(), key=lambda x: -x[1])],
         "sitze_n": sum(sitze.values()), "sitze_hinweis": "Sitze = gewonnene Wahlkreise (relative Mehrheit); Vergleich: Wahl 2019 auf den Grenzen 2024",
         "wb": wb, "w": w, "bet": r1(w / wb * 100) if wb else None, "bet_vor": r1(w_v / wb_v * 100) if wb_v else None}
    return {"g": g, "farben": GB_FARBEN, "stimmarten": [["s", "Stimmen"]], "status": "endgültig",
            "system": "Relative Mehrheitswahl in 650 Einerwahlkreisen: wer in einem Wahlkreis die meisten Stimmen hat, gewinnt den Sitz.",
            "vor": {"datum": "2019-12-12", "titel": "Unterhauswahl 2019", "hinweis": "umgerechnet auf die Wahlkreise 2024"},
            "einheiten": [{"id": "wk", "name": "Wahlkreise", "einzahl": "Wahlkreis", "art": "wahlkreis", "geo": "wahlkreise-gb", "werte": werte}],
            "quelle": {"name": "UK Parliament, Election results (House of Commons Library); Grenzen: ONS", "url": "https://electionresults.parliament.uk/general-elections/6",
                       "lizenz": "Open Parliament Licence v3.0, Open Government Licence v3.0"}}


# ---------------------------------------------------------------- Frankreich: Assemblée nationale 2024 je Wahlkreis (zwei Wahlgänge)
def fr_laden(abruf, grenzen_roh=None):
    for url, datei in FR_LEG24.values():
        laden(url, QUELLEN / datei, abruf)
    if WK_FR_GEO.exists():
        return
    roh = Path(grenzen_roh or "/tmp/fr_circ_p10.geojson")
    if not laden(FR_GRENZEN, roh, abruf):
        return
    from shapely.geometry import mapping, shape
    fc = json.loads(roh.read_text())

    def rund(c):
        return [rund(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(c[0], 4), round(c[1], 4)]
    feats = []
    for f in fc["features"]:
        pr = f["properties"]
        g = shape(f["geometry"]).simplify(0.004, preserve_topology=True)
        feats.append({"type": "Feature", "properties": {"id": pr["codeCirconscription"], "name": f"{pr['nomDepartement']}, {pr['nomCirconscription']}"},
                      "geometry": {"type": g.geom_type, "coordinates": rund(mapping(g)["coordinates"])}})
    WK_FR_GEO.write_text(json.dumps({"type": "FeatureCollection", "quelle": "data.gouv.fr, Contours géographiques des circonscriptions législatives, Licence Ouverte 2.0",
                                     "features": feats}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def _fr_runde(pfad):
    """Ergebnis eines Wahlgangs je Wahlkreis: Schlüssel wie in den Grenzen (Département zweistellig bzw. ZA… + Nummer)."""
    out = {}
    if not pfad.exists():
        return out
    r = list(csv.reader(pfad.read_text(encoding="utf-8-sig").splitlines(), delimiter=";"))
    kopf = r[0]
    for z in r[1:]:
        d = dict(zip(kopf, z))
        dep = d["Code département"]
        k = FR_UEBERSEE.get(dep, dep.zfill(2)) + d["Code circonscription législative"][-2:]
        p, gewaehlt = {}, None
        for i in range(1, 40):
            if not d.get(f"Nuance candidat {i}"):
                continue
            partei = FR_NUANCE.get(d[f"Nuance candidat {i}"], d[f"Nuance candidat {i}"])
            p[partei] = p.get(partei, 0) + (zahl(d[f"Voix {i}"]) or 0)
            if d.get(f"Elu {i}", "").lower().startswith("élu"):
                gewaehlt = {"name": f"{d[f'Prénom candidat {i}']} {d[f'Nom candidat {i}'].title()}", "partei": partei}
        out[k] = {"n": f"{d['Libellé département']} {int(d['Code circonscription législative'][-2:])}", "wb": zahl(d["Inscrits"]), "w": zahl(d["Votants"]),
                  "gueltig": zahl(d["Exprimés"]) or 0, "p": p, "gewaehlt": gewaehlt}
    return out


def fr_leg24():
    """Wahl zur Assemblée nationale 30.06./07.07.2024: 577 Wahlkreise, absolute Mehrheit im 1. Wahlgang oder relative im 2.
    Stimmart „entscheidender Wahlgang“ = 2. Wahlgang, wo es einen gab, sonst der 1.; daneben der 1. Wahlgang überall."""
    t1, t2 = (_fr_runde(QUELLEN / FR_LEG24[k][1]) for k in ("t1", "t2"))
    if not t1:
        return None
    werte, sitze, ges = {}, {}, {"t1": [{}, 0], "ent": [{}, 0]}
    wb = w = 0
    for k, R1 in t1.items():
        R2 = t2.get(k)
        ent = R2 or R1
        el = (R2 or {}).get("gewaehlt") or R1["gewaehlt"]
        werte[k] = {"n": R1["n"], "s": {"ent": anteile(list(ent["p"].items()), ent["gueltig"] or None), "t1": anteile(list(R1["p"].items()), R1["gueltig"] or None)},
                    "wb": ent["wb"], "w": ent["w"], "bet": r1(ent["w"] / ent["wb"] * 100) if ent["wb"] else None,
                    "runde": 2 if R2 else 1}
        if el:
            werte[k]["direkt"] = el
            sitze[el["partei"]] = sitze.get(el["partei"], 0) + 1
        wb += R1["wb"] or 0
        w += R1["w"] or 0
        for st, R in (("t1", R1), ("ent", ent)):
            ges[st][1] += R["gueltig"]
            for p, n in R["p"].items():
                ges[st][0][p] = ges[st][0].get(p, 0) + n
    g = {"s": {st: anteile(list(ges[st][0].items()), ges[st][1]) for st in ("ent", "t1")},
         "sitze": [[p, n, None] for p, n in sorted(sitze.items(), key=lambda x: -x[1])], "sitze_n": sum(sitze.values()),
         "sitze_hinweis": "Sitze = gewählte Abgeordnete nach Nuance des Innenministeriums am Wahltag (nicht die späteren Fraktionen)",
         "wb": wb, "w": w, "bet": r1(w / wb * 100) if wb else None}
    return {"g": g, "farben": FR_FARBEN, "stimmarten": [["ent", "Entscheidender Wahlgang"], ["t1", "1. Wahlgang"]], "status": "endgültig",
            "datum": "2024-07-07",
            "system": ("Absolute Mehrheitswahl in 577 Einerwahlkreisen mit zwei Wahlgängen: gewählt ist im 1. Wahlgang, wer mehr als die Hälfte der Stimmen "
                       "und ein Viertel der Eingeschriebenen erreicht; sonst entscheidet am 7. Juli die relative Mehrheit. Wahlbeteiligung: 1. Wahlgang."),
            "einheiten": [{"id": "wk", "name": "Wahlkreise (Circonscriptions)", "einzahl": "Wahlkreis", "art": "wahlkreis", "geo": "wahlkreise-fr", "werte": werte}],
            "quelle": {"name": "Ministère de l'Intérieur, Résultats définitifs (1er et 2nd tour); Grenzen: data.gouv.fr", "url": "https://www.data.gouv.fr/fr/datasets/668b4092826ddcf70e9e62cd/",
                       "lizenz": "Licence Ouverte 2.0"}}


# ---------------------------------------------------------------- Grenzen kompakt halten (Artifact-Grenze 16 MB)
def kompakt(pfad, stellen=3):
    """Koordinaten auf `stellen` Nachkommastellen (3 = rund 100 m), doppelte Folgepunkte und zu kleine Ringe weg. Idempotent."""
    if not pfad.exists():
        return
    fc = json.loads(pfad.read_text())

    def ring(r):
        out = []
        for x, y in r:
            q = [round(x, stellen), round(y, stellen)]
            if not out or out[-1] != q:
                out.append(q)
        return out if len(out) >= 4 else None

    def poly(rs):
        rs = [ring(r) for r in rs]
        return [r for r in rs if r] if rs and rs[0] else None
    for f in fc["features"]:
        g = f["geometry"]
        if g["type"] == "Polygon":
            g["coordinates"] = poly(g["coordinates"]) or g["coordinates"]
        elif g["type"] == "MultiPolygon":
            ps = [p for p in (poly(p) for p in g["coordinates"]) if p]
            g["coordinates"] = ps or g["coordinates"]
    pfad.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


# ---------------------------------------------------------------- Landtage, Gliedstaaten, Regionen
def regional(pa, ko):
    out = []
    for iso, gl in sorted(pa.get("gliedstaaten", {}).items()):
        for code, g in sorted(gl.items()):
            kam = [k for k in g.get("kammern") or [] if k["typ"] in ("einkammer", "unterhaus", "kammer")] or (g.get("kammern") or [])[:1]
            if not kam:
                continue
            k = kam[0]
            ergebnis, farben, datum, quelle, status = kammer_ergebnis(k, de=iso == "DE")
            if not (ergebnis.get("s") or ergebnis.get("sitze")) or not datum:
                continue
            name = g.get("name_de") or g.get("name") or code
            titel, gremium = ("Parlamentswahl", k.get("name") or "Parlament")
            if iso == "DE":
                titel, gremium = DE_LAND_TITEL.get(code, ("Landtagswahl", "Landtag " + name))
                farben = {**farben, **{p: DE_FARBEN[p] for p in farben if p in DE_FARBEN}}
            w = {"id": f"{code}-parl-{datum[:4]}", "e": 2, "land": iso, "gebiet": code, "geo": "de-laender" if iso == "DE" else "gliedstaaten", "name": name,
                 "titel": titel, "gremium": gremium, "kammer": "unterhaus", "datum": datum, "status": status, "stimmarten": [["s", "Stimmen"]],
                 "g": ergebnis, "farben": farben, "quelle": quelle, "einheiten": []}
            if code == "DE-NW" and datum.startswith("2022"):
                nw = ltw_nw22(ergebnis)
                w["stimmarten"] = [["z", "Zweitstimmen"], ["e", "Erststimmen"]]
                w["system"] = ("Personalisierte Verhältniswahl mit Erst- und Zweitstimme, 128 Landtagswahlkreise; die Zweitstimmen bestimmen die Sitzverteilung "
                               "(mindestens 181 Sitze, Überhang- und Ausgleichsmandate möglich).")
                if nw:
                    w["g"], wk_werte, w["quelle"] = nw
                    w["status"] = "endgültig"
                    w["vor"] = {"datum": "2017-05-14", "titel": "Landtagswahl 2017", "hinweis": "auf die Wahlkreise 2022 umgerechnet"}
                if ko:
                    werte = {}
                    for geb in ko["gebiete"]:
                        v = ((geb.get("vergleich") or {}).get("werte") or {}).get("ltw22")
                        if v and geb["typ"] != "Gemeinde":
                            werte[geb["id"]] = {"n": geb["name"], "s": {"z": [[de_kurz(p), None, x, None] for p, x in sorted(v, key=lambda y: -y[1])]},
                                                "bet": ((geb.get("vergleich") or {}).get("beteiligung") or {}).get("ltw22")}
                    w["einheiten"].append({"id": "kreis", "name": "Kreise und kreisfreie Städte", "einzahl": "Kreis/Stadt", "art": "zaehlgebiet", "geo": "kommunen", "werte": werte,
                                           "quelle": "IT.NRW, Kommunalwahlen 2025 Heft 1 (Ergebnisse früherer Wahlen), Zweitstimmen in %"})
                if nw:
                    w["einheiten"].append({"id": "lwk", "name": "Landtagswahlkreise", "einzahl": "Landtagswahlkreis", "art": "wahlkreis", "geo": "landtagswahlkreise-nw", "werte": wk_werte})
            out.append(w)
    return out


# ---------------------------------------------------------------- Kommunalwahl NRW 2025
def kommunal(ko):
    if not ko:
        return []
    out = []
    q = ko.get("quelle") or {}
    quelle = {"name": q.get("name", "IT.NRW"), "url": q.get("url", ""), "lizenz": q.get("lizenz", "")}
    wgr = lambda geb, p: (geb.get("wgr") or {}).get(p)
    for geb in ko["gebiete"]:
        e = 4 if geb["typ"] == "Gemeinde" else 3
        s = [[de_kurz(x["partei"]), x["stimmen"], x["prozent"], x.get("prozent_2020")] for x in geb["stimmen"] if x.get("stimmen")]
        sitze = [[de_kurz(x["partei"]), x["gesamt"], x.get("gesamt_2020")] for x in geb["sitze"] if x.get("gesamt")]
        g = {"s": {"s": sorted(s, key=lambda x: -x[1])}, "sitze": sitze, "sitze_n": geb.get("sitze_gesamt"), "wb": geb.get("wahlberechtigte"), "w": geb.get("waehler"),
             "bet": r1(geb["waehler"] / geb["wahlberechtigte"] * 100) if geb.get("wahlberechtigte") else None,
             "bet_vor": r1(geb["waehler_2020"] / geb["wahlberechtigte_2020"] * 100) if geb.get("wahlberechtigte_2020") else None}
        if geb.get("buergermeister"):
            g["amt"] = geb["buergermeister"]
        gremium = {"Rat": f"Rat der Stadt {geb['name']}", "Kreistag": f"Kreistag {geb['name']}", "Gemeinderat": f"Rat {geb['name']}"}.get(geb.get("gremium"), f"{geb.get('gremium', 'Rat')} {geb['name']}")
        w = {"id": f"NW-KW25-{geb['id']}", "e": e, "land": "DE", "gebiet": geb["id"], "geo": "kommunen", "name": geb["name"], "titel": "Kommunalwahl NRW",
             "gremium": gremium, "kammer": "rat", "datum": ko.get("wahltag", "2025-09-14"), "status": "endgültig", "stimmarten": [["s", "Stimmen"]],
             "system": "Eine Stimme für den Bewerber im Kommunalwahlbezirk, die zugleich für die Reserveliste zählt; Verhältnisausgleich ohne Sperrklausel.",
             "g": g, "vor": {"datum": ko.get("vergleich", "2020-09-13"), "titel": "Kommunalwahl 2020"}, "quelle": quelle, "einheiten": [],
             "wgr": geb.get("wgr") or {}, "region": "DE-NW"}
        out.append(w)
        if geb.get("bezirke"):
            werte, summe = {}, {}
            for i, b in enumerate(geb["bezirke"], 1):
                bs = [[de_kurz(x["partei"]), x["stimmen"], x["prozent"], None] for x in b["stimmen"] if x.get("stimmen")]
                werte[str(i)] = {"n": b["name"], "s": {"s": sorted(bs, key=lambda x: -x[1])}, "wb": b.get("wahlberechtigte"), "w": b.get("waehler"),
                                 "sitze": [[de_kurz(x["partei"]), x["sitze"], None] for x in b["stimmen"] if x.get("sitze")], "sitze_n": b.get("sitze_gesamt")}
                for p, n, *_ in bs:
                    summe[p] = summe.get(p, 0) + n
            wb = sum(b.get("wahlberechtigte") or 0 for b in geb["bezirke"])
            ww = sum(b.get("waehler") or 0 for b in geb["bezirke"])
            out.append({"id": f"NW-BV25-{geb['id']}", "e": 4, "land": "DE", "gebiet": geb["id"], "geo": "kommunen", "name": geb["name"],
                        "titel": "Bezirksvertretungswahlen", "gremium": f"{len(werte)} Bezirksvertretungen {geb['name']}", "kammer": "bv",
                        "datum": ko.get("wahltag", "2025-09-14"), "status": "endgültig", "stimmarten": [["s", "Stimmen"]],
                        "system": "Je Stadtbezirk eine eigene Bezirksvertretung. Die Karte färbt die Stadt nach der Summe aller Stadtbezirke; Grenzen der Stadtbezirke liegen noch nicht vor.",
                        "g": {"s": {"s": anteile(list(summe.items()))}, "wb": wb, "w": ww, "bet": r1(ww / wb * 100) if wb else None, "summe": True},
                        "quelle": quelle, "einheiten": [{"id": "bv", "name": "Stadtbezirke", "einzahl": "Stadtbezirk", "art": "wahlkreis", "geo": None, "werte": werte}],
                        "wgr": geb.get("wgr") or {}, "region": "DE-NW"})
    return out


def laden(url, pfad, abruf):
    if pfad.exists() or not abruf:
        return pfad.exists()
    import requests
    pfad.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, timeout=300)
    r.raise_for_status()
    pfad.write_bytes(r.content)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ohne-abruf", action="store_true")
    ap.add_argument("--vg1000", help="Pfad zur VG1000-Zip (sonst Download, nicht im Repo)")
    a = ap.parse_args()
    pa = json.loads((HIER / "data/parlamente.json").read_text())
    ko_p = HIER / "data/kommunal.json"
    ko = json.loads(ko_p.read_text()) if ko_p.exists() else None
    ew_csv = QUELLEN / "ew24_kerg2.csv"
    laden(EW24_URL, ew_csv, not a.ohne_abruf)
    ew = europawahl(ew_csv)
    if ew and not KREISE_GEO.exists():
        vg = Path(a.vg1000) if a.vg1000 else Path("/tmp/vg1000.zip")
        if laden(VG1000_URL, vg, not a.ohne_abruf):
            print("Kreise:", kreise_flaechen(vg, {k: v["n"] for k, v in ew["einheiten"][1]["werte"].items()}))
    for quelle, ziel in LTW_NW22_DATEIEN.items():
        laden(LTW_NW22 + quelle, QUELLEN / ziel, not a.ohne_abruf)
    if not LWK_NW_GEO.exists():
        lwk = Path("/tmp/lwk_nw22.zip")
        if laden(LTW_NW22_SHP, lwk, not a.ohne_abruf):
            print("Landtagswahlkreise NRW:", lwk_nw_flaechen(lwk))
    gb_laden(not a.ohne_abruf)
    fr_laden(not a.ohne_abruf)
    for geo in (KREISE_GEO, LWK_NW_GEO, WK_GB_GEO, WK_FR_GEO):
        kompakt(geo)
    wahlen = [w for w in national(pa) if w["land"] != "DE" or w["kammer"] != "unterhaus"]
    wahlen.append(bundestag(pa, HIER / "geo/wahlkreise_bund.geojson", HIER / "geo/de_laender.geojson"))
    if ew:
        wahlen.append(ew)
    gb, fr = gb_ge24(), fr_leg24()
    for w in wahlen:
        if gb and w["id"] == "GB-unterhaus-2024":
            w.update(gb)
        if fr and w["id"] == "FR-unterhaus-2024":
            w.update(fr)
    wahlen += regional(pa, ko) + kommunal(ko)
    daten = {"stand": date.today().isoformat(), "ebenen": EBENEN_NAMEN, "eu": sorted(EU), "farben": {"DE": DE_FARBEN}, "ordnung": {"DE": DE_ORDNUNG}, "wahlen": wahlen}
    OUT.write_text(json.dumps(daten, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    from collections import Counter
    print(f"{len(wahlen)} Wahlen -> {OUT} ({OUT.stat().st_size // 1024} KB); je Ebene:", dict(sorted(Counter(w['e'] for w in wahlen).items())))


if __name__ == "__main__":
    main()
