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
WK_CA_GEO = HIER / "geo" / "wahlkreise_ca.geojson"
WK_AU_GEO = HIER / "geo" / "wahlkreise_au.geojson"
GEM_AT_GEO = HIER / "geo" / "gemeinden_at.geojson"
WK_US_GEO = HIER / "geo" / "wahlkreise_us.geojson"
WK_ES_GEO = HIER / "geo" / "wahlkreise_es.geojson"
GEM_CH_GEO = HIER / "geo" / "gemeinden_ch.geojson"
CH_GRENZEN = "https://data.geo.admin.ch/ch.swisstopo.swissboundaries3d/swissboundaries3d_2024-01/swissboundaries3d_2024-01_2056_5728.shp.zip"  # swisstopo, OGD
WK_NO_GEO = HIER / "geo" / "wahlkreise_no.geojson"
NE_A1 = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_1_states_provinces.geojson"   # gemeinfrei

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
CA_GE25 = {"kandidaten": ("https://www.elections.ca/res/rep/off/ovrGE45/62/data_donnees/table_tableau12.csv", "ca_ge25_kandidaten.csv"),
           "wahlkreise": ("https://www.elections.ca/res/rep/off/ovrGE45/62/data_donnees/table_tableau11.csv", "ca_ge25_wahlkreise.csv"),
           "vor": (("https://open.canada.ca/data/dataset/08c4ffbc-c513-41a4-b741-d35b41b50c22/resource/463aa010-d9c1-470e-b6e3-d18a1c7a6a4a/"
                    "download/transposition_343_fed_vote_count.csv"),
                   "ca_ge21_umgerechnet.csv")}   # Elections Canada, Open Government Licence – Canada
CA_GRENZEN = "https://www.elections.ca/res/cir/mapsCorner/edb/FederalElectoralDistricts_SHP.zip"
# Partei im Kandidatenfeld „Vorname Name EnglischePartei/FranzösischePartei“: französischer Teil -> (englischer Teil, Anzeige)
CA_PARTEI = {"Libéral": ("Liberal", "Liberale"), "Conservateur": ("Conservative", "Konservative"), "NPD-Nouveau Parti démocratique": ("NDP-New Democratic Party", "NDP"),
             "Bloc Québécois": ("Bloc Québécois", "Bloc Québécois"), "Parti Vert": ("Green Party", "Grüne"), "Parti populaire - PPC": ("People's Party - PPC", "PPC"),
             "Indépendant(e)": ("Independent", "Unabhängige"), "Aucune appartenance": ("No Affiliation", "Unabhängige"),
             "Parti Rhinocéros Party": ("Parti Rhinocéros Party", "Rhinocéros"), "Parti Protection Animaux": ("Animal Protection Party", "Tierschutz"),
             "Communiste": ("Communist", "Kommunisten"), "Libertarien": ("Libertarian", "Libertäre"), "Parti Avenir Canadien": ("Canadian Future Party", "Canadian Future"),
             "Marxiste-Léniniste": ("Marxist-Leninist", "Marxisten-Leninisten"), "Centriste": ("Centrist", "Zentristen"),
             "Parti de l'Héritage Chrétien": ("Christian Heritage Party", "Christian Heritage"), "Parti Uni du Canada (UP)": ("United Party of Canada (UP)", "United Party"),
             "Parti Marijuana": ("Marijuana Party", "Marijuana")}
CA_LANG = [(r"^Liberal Party", "Liberale"), (r"^Conservative Party", "Konservative"), (r"^New Democratic", "NDP"), (r"^Bloc", "Bloc Québécois"),
           (r"^Green Party", "Grüne"), (r"^People's Party", "PPC"), (r"^(Independent|No Affiliation)", "Unabhängige"), (r"Rhinocéros", "Rhinocéros"),
           (r"^Animal Protection", "Tierschutz"), (r"^Communist", "Kommunisten"), (r"^Libertarian", "Libertäre"), (r"^Marxist", "Marxisten-Leninisten"),
           (r"^Centrist", "Zentristen"), (r"^Christian Heritage", "Christian Heritage"), (r"^Marijuana", "Marijuana")]
CA_FARBEN = {"Liberale": "#d71920", "Konservative": "#1a4782", "NDP": "#f37021", "Bloc Québécois": "#33b2cc", "Grüne": "#3d9b35", "PPC": "#4e2a84",
             "Unabhängige": "#9aa3ad", "Sonstige": "#8b95a3"}
AU_ERG = "https://results.aec.gov.au/31496/Website/Downloads/{}-31496.csv"     # AEC Tally Room, Wahl 3. Mai 2025 (Event 31496), CC BY 4.0
AU_GE25 = {"HouseFirstPrefsByCandidateByVoteTypeDownload": "au_ge25_erstpraeferenzen.csv", "HouseTcpByCandidateByVoteTypeDownload": "au_ge25_zwei_kandidaten.csv",
           "HouseTurnoutByDivisionDownload": "au_ge25_beteiligung.csv", "HouseFirstPrefsByPartyDownload": "au_ge25_parteien.csv",
           "HouseTppByDivisionDownload": "au_ge25_labor_koalition.csv"}
AU_GRENZEN = ("https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs/edition-3-july-2021-june-2026/"
              "access-and-downloads/digital-boundary-files/CED_2025_AUST_GDA2020.zip")   # ABS, Commonwealth Electoral Divisions 2025, CC BY 4.0
AU_PARTEI = {"ALP": "Labor", "LP": "Liberale", "LNP": "LNP", "NP": "Nationals", "CLP": "CLP", "GRN": "Grüne", "IND": "Unabhängige", "NAFD": "Unabhängige",
             "ON": "One Nation", "KAP": "Katter", "XEN": "Centre Alliance", "CYA": "Trumpet of Patriots", "FFP": "Family First", "LTP": "Libertarian",
             "HMP": "Legalise Cannabis", "AJP": "Animal Justice", "GRPF": "People First"}
AU_FARBEN = {"Labor": "#de3533", "Liberale": "#1c4f9c", "LNP": "#3a7bd5", "Nationals": "#0b7a4b", "CLP": "#f08a24", "Grüne": "#10c25b", "Unabhängige": "#9aa3ad",
             "One Nation": "#f36c21", "Katter": "#b50204", "Centre Alliance": "#ff6300", "Koalition": "#1c4f9c", "Trumpet of Patriots": "#e8c400",
             "Family First": "#5b2a86", "Legalise Cannabis": "#4c9a2a", "Sonstige": "#8b95a3"}
CH_NRW23 = "https://ogd-static.voteinfo-app.ch/v1/ogd/sd-t-17.02-NRW2023-{}.json"   # BFS, Eidgenössische Wahlen 2023, opendata.swiss (Nutzung frei, Quellenangabe)
CH_KANTON = ["ZH", "BE", "LU", "UR", "SZ", "OW", "NW", "GL", "ZG", "FR", "SO", "BS", "BL", "SH", "AR", "AI", "SG", "GR", "AG", "TG", "TI", "VD", "VS", "NE", "GE", "JU"]
CH_PARTEI = {1: "FDP", 3: "SP", 4: "SVP", 5: "LDP", 7: "EVP", 8: "CSP", 9: "PdA/Sol.", 12: "AL", 13: "Grüne", 14: "SD", 16: "EDU", 18: "Lega",
             31: "GLP", 33: "MCG", 34: "Mitte", 35: "Übrige"}
CH_FARBEN = {"SVP": "#2f7a33", "SP": "#e3000f", "Mitte": "#f39200", "FDP": "#1f63b5", "Grüne": "#84c341", "GLP": "#d4e157", "EVP": "#e6c700",
             "EDU": "#8c5a2b", "Lega": "#4d5c9a", "MCG": "#f4d03f", "PdA/Sol.": "#b3122e", "AL": "#9b2242", "LDP": "#5d8ad6", "CSP": "#3aa6a0",
             "SD": "#7d6b4a", "Übrige": "#8b95a3"}
AT_NRW = {"2024": ("https://www.bmi.gv.at/412/nationalratswahlen/nationalratswahl_2024/files/endgueltiges_ergebnis_beschluss_bundeswahlbehoerde_16102024.xlsx",
                    "at_nrw24.csv"),
          "2019": ("https://www.bmi.gv.at/412/Nationalratswahlen/Nationalratswahl_2019/files/endgultiges_gesamtergebnis_nrw19_16102019.xlsx", "at_nrw19.csv")}  # BMI
AT_GRENZEN = ("https://www.statistik.gv.at/gs-open/GEODATA/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=GEODATA:STATISTIK_AUSTRIA_GEM_20240101"
              "&outputFormat=SHAPE-ZIP&format_options=CHARSET:UTF-8")   # Statistik Austria, Gemeinden 01.01.2024, CC BY 4.0
AT_PARTEI = {"GRÜNE": "Grüne", "KEINE": "Keine von denen", "BIER": "Bierpartei", "JETZT": "JETZT", "WANDL": "Wandel", "GAZA": "Liste Gaza", "LMP": "Liste Madeleine Petrovic"}
AT_FARBEN = {"FPÖ": "#1f5fbf", "ÖVP": "#63c3d0", "SPÖ": "#e4002b", "NEOS": "#e84188", "Grüne": "#88b626", "KPÖ": "#a3201c", "Bierpartei": "#e7b416",
             "JETZT": "#a5a5a5", "BZÖ": "#f39a00", "MFG": "#5a3e8c", "Keine von denen": "#6b7280", "Wandel": "#7d3c98"}
# Sitze im Nationalrat laut Mandatsspiegel der Bundeswahlbehörde (24.10.2024); 2019 zum Vergleich
AT_SITZE = [["FPÖ", 57, 31], ["ÖVP", 51, 71], ["SPÖ", 41, 40], ["NEOS", 18, 15], ["Grüne", 16, 26]]
US_HOUSE24 = "https://clerk.house.gov/member_info/electionInfo/2024/statistics2024.pdf"   # Clerk of the House, gemeinfrei (US-Bundesbehörde)
US_GRENZEN = "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_cd119_5m.zip"         # Census Bureau, Cartographic Boundary Files, gemeinfrei
US_FIPS = {"ALABAMA": "01", "ALASKA": "02", "ARIZONA": "04", "ARKANSAS": "05", "CALIFORNIA": "06", "COLORADO": "08", "CONNECTICUT": "09", "DELAWARE": "10",
           "FLORIDA": "12", "GEORGIA": "13", "HAWAII": "15", "IDAHO": "16", "ILLINOIS": "17", "INDIANA": "18", "IOWA": "19", "KANSAS": "20", "KENTUCKY": "21",
           "LOUISIANA": "22", "MAINE": "23", "MARYLAND": "24", "MASSACHUSETTS": "25", "MICHIGAN": "26", "MINNESOTA": "27", "MISSISSIPPI": "28", "MISSOURI": "29",
           "MONTANA": "30", "NEBRASKA": "31", "NEVADA": "32", "NEW HAMPSHIRE": "33", "NEW JERSEY": "34", "NEW MEXICO": "35", "NEW YORK": "36",
           "NORTH CAROLINA": "37", "NORTH DAKOTA": "38", "OHIO": "39", "OKLAHOMA": "40", "OREGON": "41", "PENNSYLVANIA": "42", "RHODE ISLAND": "44",
           "SOUTH CAROLINA": "45", "SOUTH DAKOTA": "46", "TENNESSEE": "47", "TEXAS": "48", "UTAH": "49", "VERMONT": "50", "VIRGINIA": "51", "WASHINGTON": "53",
           "WEST VIRGINIA": "54", "WISCONSIN": "55", "WYOMING": "56"}
US_KEINE_STIMME = re.compile(r"^(Blanks?|Void|Scattering|Over ?Votes?|Under ?Votes?|Continuing Ballots|Exhausted Ballots)$", re.I)
US_FARBEN = {"Republikaner": "#d7263d", "Demokraten": "#1f5bb5", "Libertäre": "#f2b705", "Grüne": "#2e9b45", "Unabhängige": "#9aa3ad", "Sonstige": "#8b95a3"}
ES_CONG23 = "https://www.boe.es/boe/dias/2023/09/01/pdfs/BOE-A-2023-18907.pdf"   # Junta Electoral Central, Resumen de resultados (BOE, frei nutzbar)
ES_PROV = {"Albacete": "ES-AB", "Alicante/Alacant": "ES-A", "Almería": "ES-AL", "Araba/Álava": "ES-VI", "Asturias": "ES-O", "Ávila": "ES-AV",
           "Badajoz": "ES-BA", "Balears (Illes)": "ES-PM", "Barcelona": "ES-B", "Bizkaia": "ES-BI", "Burgos": "ES-BU", "Cáceres": "ES-CC", "Cádiz": "ES-CA",
           "Cantabria": "ES-S", "Castellón/Castelló": "ES-CS", "Ciudad Real": "ES-CR", "Córdoba": "ES-CO", "Coruña (A)": "ES-C", "Cuenca": "ES-CU",
           "Gipuzkoa": "ES-SS", "Girona": "ES-GI", "Granada": "ES-GR", "Guadalajara": "ES-GU", "Huelva": "ES-H", "Huesca": "ES-HU", "Jaén": "ES-J",
           "León": "ES-LE", "Lleida": "ES-L", "Lugo": "ES-LU", "Madrid": "ES-M", "Málaga": "ES-MA", "Murcia": "ES-MU", "Navarra": "ES-NA", "Ourense": "ES-OR",
           "Palencia": "ES-P", "Palmas (Las)": "ES-GC", "Pontevedra": "ES-PO", "Rioja (La)": "ES-LO", "Salamanca": "ES-SA", "Santa Cruz de Tenerife": "ES-TF",
           "Segovia": "ES-SG", "Sevilla": "ES-SE", "Soria": "ES-SO", "Tarragona": "ES-T", "Teruel": "ES-TE", "Toledo": "ES-TO", "Valencia/València": "ES-V",
           "Valladolid": "ES-VA", "Zamora": "ES-ZA", "Zaragoza": "ES-Z", "Ceuta": "ES-CE", "Melilla": "ES-ML"}
ES_PARTEI = {"PSC": "PSOE", "VOX": "Vox", "SUMAR": "Sumar", "JUNTS": "Junts", "EAJ-PNV": "PNV", "CCa": "Coalición Canaria"}
ES_FARBEN = {"PP": "#1d84ce", "PSOE": "#e30613", "Vox": "#63be21", "Sumar": "#e51c55", "ERC": "#ffb232", "Junts": "#20c0b2", "EH Bildu": "#00b2a9",
             "PNV": "#2b8a3e", "BNG": "#76b3dd", "Coalición Canaria": "#ffd700", "UPN": "#2a52be", "PACMA": "#9bc53d", "CUP-PR": "#ffed00"}
NO_ST25 = "https://valgresultat.no/api/2025/st"     # Valgdirektoratet, Stortingswahl 2025, NLOD
NO_PARTEI = {"A": "Ap", "FRP": "FrP", "H": "Høyre", "SV": "SV", "SP": "Sp", "RØDT": "Rødt", "MDG": "MDG", "KRF": "KrF", "V": "Venstre"}
NO_KREIS = {"31": "01", "32": "02", "33": "06", "39": "07", "40": "08", "55": "19", "56": "20"}   # neue Fylkesnummern der Wahlkreise -> alte (Grenzen)
NO_FARBEN = {"Ap": "#e4202c", "FrP": "#1e5aa8", "Høyre": "#0065f1", "SV": "#eb4040", "Sp": "#00843d", "Rødt": "#a51e1e", "MDG": "#5f9c3b",
             "KrF": "#ffbe00", "Venstre": "#00807b", "Sonstige": "#8b95a3"}
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


# ---------------------------------------------------------------- Kanada: Unterhauswahl 28.04.2025 je Wahlkreis (Elections Canada)
def ca_laden(abruf, grenzen_zip=None):
    for url, datei in CA_GE25.values():
        laden(url, QUELLEN / datei, abruf)
    if WK_CA_GEO.exists():
        return
    z = Path(grenzen_zip or "/tmp/ca_fed_shp.zip")
    if not laden(CA_GRENZEN, z, abruf):
        return
    import shapefile
    from pyproj import CRS, Transformer
    from shapely.geometry import mapping, shape
    from shapely.ops import transform
    zf = zipfile.ZipFile(z)
    name = next(n for n in zf.namelist() if n.endswith(".shp"))[:-4]
    sf = shapefile.Reader(shp=io.BytesIO(zf.read(name + ".shp")), shx=io.BytesIO(zf.read(name + ".shx")), dbf=io.BytesIO(zf.read(name + ".dbf")), encoding="utf-8")
    tr = Transformer.from_crs(CRS.from_wkt(zf.read(name + ".prj").decode()), "EPSG:4326", always_xy=True)
    feats = []
    for rec, shp in zip(sf.records(), sf.shapes()):
        d = rec.as_dict()
        g = transform(tr.transform, shape(shp.__geo_interface__).buffer(0).simplify(300, preserve_topology=True))   # 300 m in der Lambert-Projektion
        feats.append({"type": "Feature", "properties": {"id": str(d["ED_CF_NUM"]), "name": d["ED_NAMEE"]}, "geometry": mapping(g)})
    WK_CA_GEO.write_text(json.dumps({"type": "FeatureCollection", "quelle": "Elections Canada, Federal Electoral Districts (Representation Order 2023), Open Government Licence – Canada",
                                     "features": feats}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def _ca_kandidat(feld):
    links, _, fr = feld.replace("**", " ").rpartition("/")
    en, partei = CA_PARTEI.get(fr.strip(), ("", fr.strip() or "Sonstige"))
    links = " ".join(links.split())
    name = links[: -len(en)].strip() if en and links.endswith(en) else links
    return name, partei


def ca_ge25():
    """Unterhauswahl 28. April 2025: 343 Wahlkreise, relative Mehrheitswahl; Vergleich: Wahl 2021 umgerechnet auf die Grenzen 2023 (Elections Canada)."""
    pk, pw, pv = (QUELLEN / CA_GE25[k][1] for k in ("kandidaten", "wahlkreise", "vor"))
    if not (pk.exists() and pw.exists()):
        return None
    wk = {}
    for z in csv.reader(pw.read_text(encoding="utf-8-sig").splitlines()[1:]):
        wk[z[2]] = {"n": z[1].replace("--", "–"), "wb": zahl(z[4]), "gueltig": zahl(z[6]) or 0, "w": zahl(z[10]) or 0, "p": {}, "sieger": None}
    for z in csv.reader(pk.read_text(encoding="utf-8-sig").splitlines()[1:]):
        W = wk.get(z[2])
        if not W:
            continue
        name, partei = _ca_kandidat(z[3])
        W["p"][partei] = W["p"].get(partei, 0) + (zahl(z[6]) or 0)
        if z[8].strip():
            W["sieger"] = {"name": name, "partei": partei}
    vor = {}
    if pv.exists():
        r = list(csv.reader(pv.read_text(encoding="utf-8-sig").splitlines()))
        kopf = r[0]
        spalten = []
        for i, k in enumerate(kopf[5:-4], 5):
            en = k.split("/")[0]
            spalten.append((i, next((a for m, a in CA_LANG if re.search(m, en)), en)))
        for z in r[1:]:
            p = {}
            for i, a in spalten:
                if z[i] not in ("", "NA"):
                    p[a] = p.get(a, 0) + int(float(z[i]))
            vor[z[2]] = {"p": p, "gueltig": sum(p.values()), "w": int(float(z[-3])) if z[-3] not in ("", "NA") else 0,
                         "wb": int(float(z[-2])) if z[-2] not in ("", "NA") else 0}

    def stimmen(W, V):
        l = anteile(list(W["p"].items()), W["gueltig"] or None)
        if V and V["gueltig"]:
            for x in l:
                x[3] = r1(V["p"][x[0]] / V["gueltig"] * 100) if x[0] in V["p"] else None
        return l
    werte, sitze, ges, ges_v = {}, {}, {"p": {}, "gueltig": 0}, {"p": {}, "gueltig": 0}
    for k, W in wk.items():
        V = vor.get(k)
        werte[k] = {"n": W["n"], "s": {"s": stimmen(W, V)}, "wb": W["wb"], "w": W["w"], "bet": r1(W["w"] / W["wb"] * 100) if W["wb"] else None}
        if V and V["wb"]:
            werte[k]["bet_vor"] = r1(V["w"] / V["wb"] * 100)
        if W["sieger"]:
            werte[k]["direkt"] = W["sieger"]
            sitze[W["sieger"]["partei"]] = sitze.get(W["sieger"]["partei"], 0) + 1
        for G, Q in ((ges, W), (ges_v, V)):
            if Q:
                G["gueltig"] += Q["gueltig"]
                for p, n in Q["p"].items():
                    G["p"][p] = G["p"].get(p, 0) + n
    wb, w = sum(W["wb"] or 0 for W in wk.values()), sum(W["w"] for W in wk.values())
    wb_v, w_v = sum(V["wb"] for V in vor.values()), sum(V["w"] for V in vor.values())
    g = {"s": {"s": stimmen(ges, ges_v if vor else None)}, "sitze": [[p, n, None] for p, n in sorted(sitze.items(), key=lambda x: -x[1])],
         "sitze_n": sum(sitze.values()), "sitze_hinweis": "Sitze = gewonnene Wahlkreise am Wahlabend (nach Nachzählungen)",
         "wb": wb, "w": w, "bet": r1(w / wb * 100) if wb else None, "bet_vor": r1(w_v / wb_v * 100) if wb_v else None}
    return {"g": g, "farben": CA_FARBEN, "stimmarten": [["s", "Stimmen"]], "status": "endgültig", "datum": "2025-04-28",
            "system": "Relative Mehrheitswahl in 343 Einerwahlkreisen: wer in einem Wahlkreis die meisten Stimmen hat, gewinnt den Sitz.",
            "vor": {"datum": "2021-09-20", "titel": "Unterhauswahl 2021", "hinweis": "umgerechnet auf die Wahlkreise 2023 (Elections Canada)"},
            "einheiten": [{"id": "wk", "name": "Wahlkreise (Ridings)", "einzahl": "Wahlkreis", "art": "wahlkreis", "geo": "wahlkreise-ca", "werte": werte}],
            "quelle": {"name": "Elections Canada, Official Voting Results 45th General Election; Grenzen: Elections Canada",
                       "url": "https://www.elections.ca/content.aspx?section=res&dir=rep/off/45gedata&document=index&lang=e",
                       "lizenz": "Open Government Licence – Canada"}}


# ---------------------------------------------------------------- Australien: Repräsentantenhaus 03.05.2025 je Division (AEC)
def _au_zeilen(datei):
    """AEC-Dateien: erste Zeile ist eine Beschreibung, danach CSV mit Kopf."""
    pfad = QUELLEN / datei
    return list(csv.DictReader(pfad.read_text(encoding="utf-8-sig").splitlines()[1:])) if pfad.exists() else []


def _au_partei(z):
    return AU_PARTEI.get(z["PartyAb"], z["PartyNm"] or "Sonstige")


def au_laden(abruf, grenzen_zip=None):
    for quelle, datei in AU_GE25.items():
        laden(AU_ERG.format(quelle), QUELLEN / datei, abruf)
    if WK_AU_GEO.exists():
        return
    ids = {z["DivisionNm"]: z["DivisionID"] for z in _au_zeilen(AU_GE25["HouseTurnoutByDivisionDownload"])}
    z = Path(grenzen_zip or "/tmp/au_ced25.zip")
    if not ids or not laden(AU_GRENZEN, z, abruf):
        return
    import shapefile
    from shapely.geometry import mapping, shape
    zf = zipfile.ZipFile(z)
    name = next(n for n in zf.namelist() if n.lower().endswith(".shp"))[:-4]
    sf = shapefile.Reader(shp=io.BytesIO(zf.read(name + ".shp")), shx=io.BytesIO(zf.read(name + ".shx")), dbf=io.BytesIO(zf.read(name + ".dbf")), encoding="utf-8")
    feats = []
    for rec, shp in zip(sf.records(), sf.shapes()):
        d = rec.as_dict()
        if d["CED_NAME25"] not in ids or not shp.points:
            continue        # ohne „Migratory“, „No usual address“, „Outside Australia“
        g = shape(shp.__geo_interface__).buffer(0).simplify(0.003, preserve_topology=True)
        feats.append({"type": "Feature", "properties": {"id": ids[d["CED_NAME25"]], "name": d["CED_NAME25"]}, "geometry": mapping(g)})
    WK_AU_GEO.write_text(json.dumps({"type": "FeatureCollection", "quelle": "Australian Bureau of Statistics, Commonwealth Electoral Divisions (ASGS Ed. 3) 2025, CC BY 4.0",
                                     "features": feats}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def au_ge25():
    """Wahl zum Repräsentantenhaus 3. Mai 2025: 150 Divisionen, Präferenzwahl (Instant-Runoff). Zwei Stimmarten: Ergebnis nach Verteilung der
    Präferenzen auf die letzten zwei Kandidaten (entscheidet den Sitz) und Erstpräferenzen. Veränderung: AEC-Swing zur Wahl 2022 (fiktiv auf neuen Grenzen)."""
    ep, zk, bet, pa, tpp = (_au_zeilen(AU_GE25[k]) for k in AU_GE25)
    if not ep:
        return None
    div = {}
    for z in bet:
        div[z["DivisionID"]] = {"n": z["DivisionNm"], "wb": zahl(z["Enrolment"]), "w": zahl(z["Turnout"]), "bet": r1(float(z["TurnoutPercentage"])),
                                "bet_vor": r1(float(z["TurnoutPercentage"]) - float(z["TurnoutSwing"])), "ep": {}, "zk": {}, "sieger": None}

    def sammeln(zeilen, art):
        for z in zeilen:
            D = div.get(z["DivisionID"])
            if not D or z["Surname"] == "Informal":
                continue
            p, n = _au_partei(z), zahl(z["TotalVotes"]) or 0
            alt = D[art].get(p)
            # Swing der AEC gilt je Kandidat; bei mehreren Kandidaten derselben Gruppe (Unabhängige) kein Vergleich
            D[art][p] = [n + (alt[0] if alt else 0), None if alt else (float(z["Swing"]) if z["Swing"] not in ("", None) else None)]
            if art == "zk" and z["Elected"] == "Y":
                D["sieger"] = {"name": f"{z['GivenNm']} {z['Surname'].title()}", "partei": p}
    sammeln(ep, "ep")
    sammeln(zk, "zk")

    def liste(d):
        s = sum(v[0] for v in d.values()) or 1
        return sorted([[p, n, r1(n / s * 100), r1(n / s * 100 - sw) if sw is not None and abs(sw) < 100 and n / s * 100 - sw >= 0.05 else None]
                       for p, (n, sw) in d.items()], key=lambda x: -x[1])
    werte, sitze = {}, {}
    for k, D in div.items():
        werte[k] = {"n": D["n"], "s": {"zk": liste(D["zk"]), "ep": liste(D["ep"])}, "wb": D["wb"], "w": D["w"], "bet": D["bet"], "bet_vor": D["bet_vor"]}
        if D["sieger"]:
            werte[k]["direkt"] = D["sieger"]
            sitze[D["sieger"]["partei"]] = sitze.get(D["sieger"]["partei"], 0) + 1
    ges = {}
    for z in pa:
        p = AU_PARTEI.get(z["PartyAb"], z["PartyNm"] or "Sonstige")
        alt = ges.get(p)
        ges[p] = [zahl(z["TotalVotes"]) + (alt[0] if alt else 0), float(z["TotalSwing"]) + (alt[1] if alt else 0)]
    s = sum(v[0] for v in ges.values()) or 1
    g_ep = sorted([[p, n, r1(n / s * 100), r1(n / s * 100 - sw)] for p, (n, sw) in ges.items()], key=lambda x: -x[1])
    alp = sum(zahl(z["Australian Labor Party Votes"]) or 0 for z in tpp)
    koa = sum(zahl(z["Liberal/National Coalition Votes"]) or 0 for z in tpp)
    g_zk = [["Labor", alp, r1(alp / (alp + koa) * 100), 52.1], ["Koalition", koa, r1(koa / (alp + koa) * 100), 47.9]] if alp + koa else []
    wb, w = sum(D["wb"] or 0 for D in div.values()), sum(D["w"] or 0 for D in div.values())
    g = {"s": {"zk": g_zk, "ep": g_ep}, "sitze": [[p, n, None] for p, n in sorted(sitze.items(), key=lambda x: -x[1])], "sitze_n": sum(sitze.values()),
         "sitze_hinweis": "Sitze = gewonnene Divisionen; landesweit „nach Präferenzen“ = Labor gegen Koalition (two-party preferred, Vergleich 2022: 52,1 zu 47,9)",
         "wb": wb, "w": w, "bet": r1(w / wb * 100) if wb else None}
    return {"g": g, "farben": AU_FARBEN, "stimmarten": [["zk", "Nach Präferenzen"], ["ep", "Erstpräferenzen"]], "status": "endgültig", "datum": "2025-05-03",
            "system": ("Präferenzwahl in 150 Einerwahlkreisen (Divisionen): Wähler nummerieren alle Kandidaten; wer keine absolute Mehrheit der Erstpräferenzen hat, "
                       "fällt nacheinander aus, seine Stimmen gehen an die nächste Präferenz, bis zwei übrig sind. Wahlpflicht."),
            "vor": {"datum": "2022-05-21", "titel": "Wahl 2022", "hinweis": "Swing der AEC, umgerechnet auf die neuen Grenzen"},
            "einheiten": [{"id": "wk", "name": "Wahlkreise (Divisionen)", "einzahl": "Division", "art": "wahlkreis", "geo": "wahlkreise-au", "werte": werte}],
            "quelle": {"name": "Australian Electoral Commission, Tally Room 2025 Federal Election; Grenzen: ABS (Commonwealth Electoral Divisions 2025)",
                       "url": "https://results.aec.gov.au/31496/Website/HouseDefault-31496.htm", "lizenz": "CC BY 4.0"}}


# ---------------------------------------------------------------- Schweiz: Nationalrat 22.10.2023, Wahlkreis = Kanton (BFS)
def ch_laden(abruf):
    """Parteiergebnisse und Wahlbeteiligung des BFS; gespeichert nur Ebene Schweiz und Kantone (die Gemeindeebene hätte 8 MB)."""
    import requests
    for art, datei in (("parteien", "ch_nrw23_parteien.json"), ("wahlbeteiligung", "ch_nrw23_beteiligung.json")):
        ziel = QUELLEN / datei
        if ziel.exists() or not abruf:
            continue
        r = requests.get(CH_NRW23.format(art), timeout=300)
        r.raise_for_status()
        d = r.json()
        _ch_gemeinden_schreiben(art, d.pop("level_gemeinden", None) or [])
        ziel.write_text(json.dumps(d, ensure_ascii=False, indent=0), encoding="utf-8")
    if not GEM_CH_GEO.exists():
        z = Path("/tmp/ch_swissboundaries3d.zip")
        if laden(CH_GRENZEN, z, abruf):
            ch_gemeindeflaechen(z)


CH_GEM_SPALTEN = {"parteien": ["gemeinde_nummer", "gemeinde_bezeichnung", "kanton_nummer", "partei_id", "stimmen_partei", "partei_staerke", "letzte_wahl_partei_staerke"],
                  "wahlbeteiligung": ["gemeinde_nummer", "gemeinde_bezeichnung", "kanton_nummer", "wahlberechtigte", "eingelegte_wahlzettel", "wahlbeteiligung",
                                      "letzte_wahl_wahlbeteiligung"]}


def _ch_gemeinden_schreiben(art, zeilen):
    """Gemeindeebene des BFS als schlanke CSV (nur die Spalten, die die Karte braucht)."""
    with (QUELLEN / f"ch_nrw23_gemeinden_{art}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CH_GEM_SPALTEN[art])
        for z in zeilen:
            w.writerow([("" if z.get(k) is None else (round(z[k], 3) if isinstance(z[k], float) else z[k])) for k in CH_GEM_SPALTEN[art]])


def ch_gemeindeflaechen(zip_pfad):
    """swissBOUNDARIES3D Hoheitsgebiete (Stand 01.2024) -> Gemeinden (BFS-Nummer), vereinfacht auf rund 100 m, WGS84."""
    import shapefile
    from pyproj import CRS, Transformer
    from shapely.geometry import mapping, shape
    from shapely.ops import transform, unary_union
    zf = zipfile.ZipFile(zip_pfad)
    name = next(n for n in zf.namelist() if n.endswith("HOHEITSGEBIET.shp"))[:-4]
    sf = shapefile.Reader(shp=io.BytesIO(zf.read(name + ".shp")), shx=io.BytesIO(zf.read(name + ".shx")), dbf=io.BytesIO(zf.read(name + ".dbf")), encoding="utf-8")
    tr = Transformer.from_crs(CRS.from_wkt(zf.read(name + ".prj").decode()), "EPSG:4326", always_xy=True)
    teile, namen = {}, {}
    for rec, shp in zip(sf.records(), sf.shapes()):
        d = rec.as_dict()
        if d["OBJEKTART"] != "Gemeindegebiet":
            continue
        g = shape(shp.__geo_interface__)
        if g.has_z:
            from shapely import force_2d
            g = force_2d(g)
        teile.setdefault(str(d["BFS_NUMMER"]), []).append(g.buffer(0))
        namen[str(d["BFS_NUMMER"])] = d["NAME"]
    feats = []
    for k, gs in teile.items():
        g = transform(tr.transform, unary_union(gs).simplify(100, preserve_topology=True))
        feats.append({"type": "Feature", "properties": {"id": k, "name": namen[k]}, "geometry": mapping(g)})
    GEM_CH_GEO.write_text(json.dumps({"type": "FeatureCollection", "quelle": "swisstopo, swissBOUNDARIES3D 2024-01 (Open Government Data)", "features": feats},
                                     ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def ch_nrw23():
    """Nationalratswahl 2023: Proporz in 26 Kantonen (Wahlkreise), Sitze je Kanton nach Bevölkerung (1 bis 36). Kantone mit einem Sitz wählen faktisch nach Mehrheit."""
    pp, pb = QUELLEN / "ch_nrw23_parteien.json", QUELLEN / "ch_nrw23_beteiligung.json"
    if not (pp.exists() and pb.exists()):
        return None
    P, B = json.loads(pp.read_text()), json.loads(pb.read_text())
    gewaehlte = {}
    pg = QUELLEN / "ch_nrw23_gewaehlte.json"
    for x in (json.loads(pg.read_text()) if pg.exists() else []):
        gewaehlte.setdefault(x["kanton_nummer"], []).append(x)
    name = lambda i: CH_PARTEI.get(i, "Übrige")
    werte = {}
    for b in B["level_kantone"]:
        k = "CH-" + CH_KANTON[b["kanton_nummer"] - 1]
        werte[k] = {"n": "Kanton " + b["kanton_bezeichnung"], "s": {"s": []}, "sitze": [], "wb": b["wahlberechtigte"], "w": b["eingelegte_wahlzettel"],
                    "bet": r1(b["wahlbeteiligung"]), "bet_vor": r1(b["letzte_wahl_wahlbeteiligung"]) if b.get("letzte_wahl_wahlbeteiligung") is not None else None}
        el = gewaehlte.get(b["kanton_nummer"], [])
        if len(el) == 1:                      # Ein-Sitz-Kanton: die gewählte Person
            werte[k]["direkt"] = {"name": f"{el[0]['vorname']} {el[0]['name']}", "partei": name(el[0]["kandidat_partei_id"])}
    for x in P["level_kantone"]:
        W = werte["CH-" + CH_KANTON[x["kanton_nummer"] - 1]]
        if x["partei_staerke"] is None:
            continue
        W["s"]["s"].append([name(x["partei_id"]), x["stimmen_partei"], r1(x["partei_staerke"]),
                            r1(x["letzte_wahl_partei_staerke"]) if x.get("letzte_wahl_partei_staerke") is not None else None])
        if x["anzahl_gewaehlte"] or x.get("letzte_wahl_anzahl_gewaehlte"):
            W["sitze"].append([name(x["partei_id"]), x["anzahl_gewaehlte"], x.get("letzte_wahl_anzahl_gewaehlte")])
    for W in werte.values():
        W["s"]["s"].sort(key=lambda y: -(y[2] or 0))
        W["sitze_n"] = sum(y[1] for y in W["sitze"])
    l = sorted([[name(x["partei_id"]), x["fiktive_waehlende"], r1(x["partei_staerke"]), r1(x["letzte_wahl_partei_staerke"]) if x.get("letzte_wahl_partei_staerke") is not None else None]
                for x in P["level_ch"]], key=lambda y: -(y[2] or 0))
    sitze = sorted([[name(x["partei_id"]), x["anzahl_gewaehlte"], x["letzte_wahl_anzahl_gewaehlte"]] for x in P["level_ch"] if x["anzahl_gewaehlte"] or x["letzte_wahl_anzahl_gewaehlte"]],
                   key=lambda y: -y[1])
    c = B["level_ch"]
    g = {"s": {"s": l}, "sitze": sitze, "sitze_n": sum(y[1] for y in sitze), "wb": c["wahlberechtigte"], "w": c["eingelegte_wahlzettel"],
         "bet": r1(c["wahlbeteiligung"]), "bet_vor": r1(c["letzte_wahl_wahlbeteiligung"]),
         "sitze_hinweis": "Parteistärke landesweit aus „fiktiven Wählenden“ des BFS (Parteistimmen geteilt durch die Sitzzahl des Kantons)"}
    einheiten = [{"id": "kanton", "name": "Kantone (Wahlkreise)", "einzahl": "Kanton", "art": "wahlkreis", "geo": "gliedstaaten", "werte": werte}]
    gp, gb = QUELLEN / "ch_nrw23_gemeinden_parteien.csv", QUELLEN / "ch_nrw23_gemeinden_wahlbeteiligung.csv"
    if gp.exists() and gb.exists():
        gem = {}
        for z in csv.DictReader(gb.open(encoding="utf-8")):
            gem[z["gemeinde_nummer"]] = {"n": z["gemeinde_bezeichnung"].strip(), "s": {"s": []}, "wb": zahl(z["wahlberechtigte"]), "w": zahl(z["eingelegte_wahlzettel"]),
                                         "bet": r1(float(z["wahlbeteiligung"])) if z["wahlbeteiligung"] else None,
                                         "bet_vor": r1(float(z["letzte_wahl_wahlbeteiligung"])) if z["letzte_wahl_wahlbeteiligung"] else None}
        for z in csv.DictReader(gp.open(encoding="utf-8")):
            G = gem.get(z["gemeinde_nummer"])
            if G is None or not z["partei_staerke"] or float(z["partei_staerke"]) <= 0:
                continue
            G["s"]["s"].append([name(int(z["partei_id"])), zahl(z["stimmen_partei"]), r1(float(z["partei_staerke"])),
                                r1(float(z["letzte_wahl_partei_staerke"])) if z["letzte_wahl_partei_staerke"] else None])
        for G in gem.values():
            G["s"]["s"].sort(key=lambda y: -(y[2] or 0))
        einheiten.append({"id": "gem", "name": "Gemeinden", "einzahl": "Gemeinde", "art": "zaehlgebiet", "geo": "gemeinden-ch", "werte": gem})
    return {"g": g, "farben": CH_FARBEN, "stimmarten": [["s", "Parteistärke"]], "status": "endgültig",
            "system": ("Verhältniswahl in 26 Kantonen (Wahlkreise) mit 1 bis 36 Sitzen; Listen, Panaschieren und Kumulieren. "
                       "In Kantonen mit einem Sitz ist gewählt, wer die meisten Stimmen hat."),
            "vor": {"datum": "2019-10-20", "titel": "Nationalratswahl 2019"},
            "einheiten": einheiten,
            "quelle": {"name": "Bundesamt für Statistik, Eidgenössische Wahlen 2023 (opendata.swiss); Gemeindegrenzen: swisstopo", "url": "https://www.bfs.admin.ch/bfs/de/home/statistiken/politik/wahlen.html",
                       "lizenz": "opendata.swiss, freie Nutzung mit Quellenangabe"}}


# ---------------------------------------------------------------- Österreich: Nationalrat 29.09.2024 je Bundesland und Gemeinde (BMI)
def at_laden(abruf, grenzen_zip=None):
    """BMI-Ergebnisdateien (xlsx) -> CSV mit Stimmen (ohne Prozentspalten); Gemeindegrenzen der Statistik Austria."""
    import tempfile
    for url, datei in AT_NRW.values():
        ziel = QUELLEN / datei
        if ziel.exists():
            continue
        x = Path(tempfile.gettempdir()) / (datei + ".xlsx")
        if not laden(url, x, abruf):
            continue
        import openpyxl
        rows = list(openpyxl.load_workbook(x, read_only=True).worksheets[0].iter_rows(values_only=True))
        kopf = ["GKZ", "Gebiet", "Wahlberechtigte", "Abgegebene", "Ungültige", "Gültige"] + [k for k in rows[0][6::2] if k]
        with ziel.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(kopf)
            for r in rows:
                if r[0] and str(r[0]).startswith("G") and str(r[0]) != "GKZ":
                    w.writerow(list(r[:6]) + [("" if v is None else v) for v in r[6::2][: len(kopf) - 6]])
    if GEM_AT_GEO.exists():
        return
    z = Path(grenzen_zip or "/tmp/at_gem24.zip")
    if not laden(AT_GRENZEN, z, abruf):
        return
    import shapefile
    from pyproj import CRS, Transformer
    from shapely.geometry import mapping, shape
    from shapely.ops import transform
    zf = zipfile.ZipFile(z)
    name = next(n for n in zf.namelist() if n.endswith(".shp"))[:-4]
    sf = shapefile.Reader(shp=io.BytesIO(zf.read(name + ".shp")), shx=io.BytesIO(zf.read(name + ".shx")), dbf=io.BytesIO(zf.read(name + ".dbf")), encoding="utf-8")
    tr = Transformer.from_crs(CRS.from_wkt(zf.read(name + ".prj").decode()), "EPSG:4326", always_xy=True)
    feats = []
    for rec, shp in zip(sf.records(), sf.shapes()):
        d = rec.as_dict()
        g = transform(tr.transform, shape(shp.__geo_interface__).buffer(0).simplify(120, preserve_topology=True))     # 120 m in MGI Lambert
        feats.append({"type": "Feature", "properties": {"id": d["g_id"], "name": d["g_name"]}, "geometry": mapping(g)})
    GEM_AT_GEO.write_text(json.dumps({"type": "FeatureCollection", "quelle": "Statistik Austria, Gemeinden 01.01.2024, CC BY 4.0", "features": feats},
                                     ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def _at_zeilen(datei):
    pfad = QUELLEN / datei
    if not pfad.exists():
        return {}
    out = {}
    for z in csv.DictReader(pfad.open(encoding="utf-8")):
        p = {AT_PARTEI.get(k, k): int(float(v)) for k, v in list(z.items())[6:] if v not in ("", None) and float(v) > 0}
        out[z["GKZ"][1:]] = {"n": z["Gebiet"].strip(), "wb": zahl(z["Wahlberechtigte"]), "w": zahl(z["Abgegebene"]), "gueltig": zahl(z["Gültige"]) or 0, "p": p}
    return out


def at_nrw24():
    """Nationalratswahl 2024: Verhältniswahl in drei Ermittlungsverfahren (39 Regional-, 9 Landeswahlkreise, Bund), 4-%-Hürde oder Grundmandat.
    Wahlkreise hier = Landeswahlkreise (Bundesländer); Zählgebiete = Gemeinden (Urnenstimmen; Wahlkarten zählt der Bezirk)."""
    A, V = _at_zeilen(AT_NRW["2024"][1]), _at_zeilen(AT_NRW["2019"][1])
    if not A:
        return None

    def wert(k, X, mit_bet=True):
        x, v = X[k], V.get(k)
        l = anteile(list(x["p"].items()), x["gueltig"] or None)
        if v and v["gueltig"]:
            for y in l:
                y[3] = r1(v["p"][y[0]] / v["gueltig"] * 100) if y[0] in v["p"] else None
        o = {"n": x["n"], "s": {"s": l}, "wb": x["wb"]}
        if mit_bet:                           # Gemeinden: ohne Wahlkarten wären Wählende und Beteiligung zu niedrig
            o["w"] = x["w"]
        if mit_bet and x["wb"]:
            o["bet"] = r1(x["w"] / x["wb"] * 100)
            if v and v["wb"]:
                o["bet_vor"] = r1(v["w"] / v["wb"] * 100)
        return o
    laender = {f"AT-{k[0]}": wert(k, A) for k in A if re.fullmatch(r"[1-9]0000", k)}
    gemeinden = {k: wert(k, A, False) for k in A if re.fullmatch(r"\d{5}", k) and not k.endswith(("00", "99"))}
    for k, x in gemeinden.items():
        x["n"] = re.sub(r"^Wien-", "Wien, ", x["n"])
    g = wert("00000", A)
    g.pop("n")
    g.update({"sitze": AT_SITZE, "sitze_n": 183, "sitze_hinweis": "Sitze laut Mandatsspiegel der Bundeswahlbehörde"})
    return {"g": g, "farben": AT_FARBEN, "stimmarten": [["s", "Stimmen"]], "status": "endgültig",
            "system": ("Verhältniswahl mit Vorzugsstimmen in drei Ermittlungsverfahren: Regionalwahlkreise, Landeswahlkreise (Bundesländer), Bund. "
                       "In den Nationalrat kommt, wer landesweit 4 % oder ein Grundmandat in einem Regionalwahlkreis erreicht."),
            "vor": {"datum": "2019-09-29", "titel": "Nationalratswahl 2019"},
            "einheiten": [{"id": "land", "name": "Landeswahlkreise (Bundesländer)", "einzahl": "Landeswahlkreis", "art": "wahlkreis", "geo": "gliedstaaten", "werte": laender},
                          {"id": "gem", "name": "Gemeinden (ohne Wahlkarten)", "einzahl": "Gemeinde", "art": "zaehlgebiet", "geo": "gemeinden-at", "werte": gemeinden}],
            "quelle": {"name": "Bundesministerium für Inneres, Endgültiges Ergebnis (Bundeswahlbehörde 16.10.2024); Grenzen: Statistik Austria",
                       "url": "https://www.bmi.gv.at/412/Nationalratswahlen/Nationalratswahl_2024/start.aspx", "lizenz": "Amtliches Ergebnis; Grenzen CC BY 4.0"}}


# ---------------------------------------------------------------- USA: Repräsentantenhaus 05.11.2024 je Kongresswahlkreis (Clerk of the House)
def _us_pdf_lesen(pdf, ziel):
    """Statistik des Clerk (PDF, mit pdftotext -layout) -> CSV Staat, Wahlkreis (0 = at large), Kandidat, Partei, Stimmen (leer = ohne Gegenkandidat
    nicht auf dem Stimmzettel). Zeilen mit nur einer Partei unter einem Kandidaten (Fusion, z. B. New York) werden dem Kandidaten zugeschlagen."""
    import subprocess
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout.splitlines()
    zeile = re.compile(r"^(\s*)(?:(\d+)\.\s+)?(\S.*?)\s*\.{3,}[\s.]*([\d,]+|\(\d+\))\s*$")
    staat = abschnitt = wk = spalte = None
    reihen, letzter = [], None
    for l in txt:
        st = l.strip()
        k = re.sub(r"—Continued$", "", st)
        if k in US_FIPS:
            staat, abschnitt = k, None
            continue
        if st.startswith("FOR UNITED STATES REPRESENTATIVE"):
            abschnitt = "rep"
            continue
        if st.startswith(("FOR ", "Recapitulation")):
            abschnitt = None
            continue
        if abschnitt != "rep" or not staat:
            continue
        if st == "AT LARGE":
            wk = 0
            continue
        m = zeile.match(l)
        if not m:
            continue
        ind, nr, text, zahl_ = m.groups()
        if nr:
            wk, spalte = int(nr), l.index(text)
        elif spalte is None:
            spalte = len(ind)
        stimmen = None if zahl_.startswith("(") else int(zahl_.replace(",", ""))
        if l.index(text) > spalte + 2 and letzter and letzter[:2] == [staat, wk]:
            letzter[4] = (letzter[4] or 0) + (stimmen or 0)
            continue
        name, _, partei = text.rpartition(",") if "," in text else (text, "", text)
        if re.fullmatch(r"\s*(Jr\.|Sr\.|II|III|IV)", partei):
            name, partei = text, ""
        letzter = [staat, wk, name.strip(), partei.strip(), stimmen]
        reihen.append(letzter)
    with ziel.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["staat", "wahlkreis", "kandidat", "partei", "stimmen"])
        w.writerows(reihen)


def us_laden(abruf, grenzen_zip=None):
    pdf, csv_ = QUELLEN / "us_house24_clerk.pdf", QUELLEN / "us_house24_kandidaten.csv"
    if laden(US_HOUSE24, pdf, abruf) and not csv_.exists():
        _us_pdf_lesen(pdf, csv_)
    if WK_US_GEO.exists():
        return
    z = Path(grenzen_zip or "/tmp/us_cd119.zip")
    if not laden(US_GRENZEN, z, abruf):
        return
    import shapefile
    from shapely.geometry import mapping, shape
    zf = zipfile.ZipFile(z)
    name = next(n for n in zf.namelist() if n.endswith(".shp"))[:-4]
    sf = shapefile.Reader(shp=io.BytesIO(zf.read(name + ".shp")), shx=io.BytesIO(zf.read(name + ".shx")), dbf=io.BytesIO(zf.read(name + ".dbf")))
    feats = []
    for rec, shp in zip(sf.records(), sf.shapes()):
        d = rec.as_dict()
        if d["STATEFP"] not in US_FIPS.values() or d["CD119FP"] in ("98", "ZZ"):
            continue        # ohne DC, Puerto Rico und Außengebiete (Delegierte ohne Stimmrecht)
        g = shape(shp.__geo_interface__).buffer(0).simplify(0.004, preserve_topology=True)
        feats.append({"type": "Feature", "properties": {"id": d["GEOID"]}, "geometry": mapping(g)})
    WK_US_GEO.write_text(json.dumps({"type": "FeatureCollection", "quelle": "U.S. Census Bureau, Cartographic Boundary Files 2024, 119th Congressional Districts",
                                     "features": feats}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def _us_partei(p):
    if p == "Republican":
        return "Republikaner"
    if p.startswith("Democrat"):
        return "Demokraten"
    if p.startswith("Libertarian"):
        return "Libertäre"
    if "Green" in p:
        return "Grüne"
    if re.match(r"(Independent|Unaffiliated|No Party|Nonpartisan|Unenrolled|No Political)", p):
        return "Unabhängige"
    return "Sonstige"


def us_house24():
    """Wahl zum Repräsentantenhaus 5. November 2024: 435 Einerwahlkreise, meist relative Mehrheit (Maine und Alaska mit Rangfolgewahl:
    Maine 2 zeigt die letzte Runde; Louisiana: offene Wahl aller Parteien)."""
    pfad = QUELLEN / "us_house24_kandidaten.csv"
    if not pfad.exists():
        return None
    wk = {}
    for z in csv.DictReader(pfad.open(encoding="utf-8")):
        if US_KEINE_STIMME.match(z["kandidat"].strip()):
            continue
        n = int(z["wahlkreis"])
        k = US_FIPS[z["staat"]] + f"{n:02d}"
        W = wk.setdefault(k, {"n": z["staat"].title() + (" (At Large)" if n == 0 else f" {n}"), "p": {}, "k": []})
        p, st = _us_partei(z["partei"]), int(z["stimmen"]) if z["stimmen"] else None
        W["p"][p] = W["p"].get(p, 0) + (st or 0)
        W["k"].append((st if st is not None else -1, z["kandidat"], p))
    werte, sitze, ges = {}, {}, {}
    for k, W in wk.items():
        gueltig = sum(W["p"].values())
        st, name, partei = max(W["k"])
        werte[k] = {"n": W["n"], "s": {"s": anteile([x for x in W["p"].items() if x[1]], gueltig or None) if gueltig else []}, "w": gueltig or None,
                    "direkt": {"name": name, "partei": partei}}
        sitze[partei] = sitze.get(partei, 0) + 1
        for p, n in W["p"].items():
            ges[p] = ges.get(p, 0) + n
    g = {"s": {"s": anteile(list(ges.items()), sum(ges.values()))}, "sitze": [[p, n, None] for p, n in sorted(sitze.items(), key=lambda x: -x[1])],
         "sitze_n": sum(sitze.values()), "w": sum(ges.values()),
         "sitze_hinweis": "Sitze = Wahlkreissieger; Stimmen ohne Wahlkreise mit nur einem Kandidaten, der nicht auf dem Stimmzettel stand"}
    return {"id": "US-unterhaus-2024", "e": 1, "land": "US", "gebiet": "US", "geo": "laender", "name": "", "titel": "Parlamentswahl",
            "gremium": "House of Representatives", "kammer": "unterhaus", "datum": "2024-11-05", "status": "endgültig", "g": g, "farben": US_FARBEN,
            "stimmarten": [["s", "Stimmen"]],
            "system": ("Relative Mehrheitswahl in 435 Einerwahlkreisen (Maine und Alaska mit Rangfolgewahl, Louisiana mit offener Wahl). "
                       "Die Wahl vom 3. November 2026 ist noch nicht amtlich ausgezählt."),
            "einheiten": [{"id": "wk", "name": "Kongresswahlkreise", "einzahl": "Wahlkreis", "art": "wahlkreis", "geo": "wahlkreise-us", "werte": werte}],
            "quelle": {"name": "Clerk of the U.S. House of Representatives, Statistics of the Presidential and Congressional Election 2024; Grenzen: U.S. Census Bureau",
                       "url": "https://clerk.house.gov/Members/ElectionInformation", "lizenz": "gemeinfrei (US-Bundesbehörden)"}}


# ---------------------------------------------------------------- Wahlkreisgrenzen aus Natural Earth (Spanien: Provinzen, Norwegen: Fylker vor 2020)
def ne_wahlkreise(abruf, iso, ziel, quelle_roh=None):
    """Natural Earth Admin 1 (gemeinfrei): Provinzen Spaniens = Wahlkreise des Congreso; alte 19 Fylker Norwegens = Wahlkreise des Storting."""
    if ziel.exists():
        return
    roh = Path(quelle_roh or "/tmp/ne_10m_admin_1.geojson")
    if not laden(NE_A1, roh, abruf):
        return
    from shapely.geometry import mapping, shape
    feats = []
    for f in json.loads(roh.read_text())["features"]:
        pr = f["properties"]
        if pr["iso_a2"] != iso or not re.fullmatch(r"[A-Z]{2}-[A-Z0-9]{1,3}", pr["iso_3166_2"] or "") or pr["iso_3166_2"] == "NO-21":
            continue        # ohne Svalbard und unbewohnte Inseln
        g = shape(f["geometry"]).buffer(0).simplify(0.003, preserve_topology=True)
        feats.append({"type": "Feature", "properties": {"id": pr["iso_3166_2"], "name": pr["name"]}, "geometry": mapping(g)})
    ziel.write_text(json.dumps({"type": "FeatureCollection", "quelle": "Natural Earth 1:10 Mio., Admin 1 (gemeinfrei)", "features": feats},
                               ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


# ---------------------------------------------------------------- Spanien: Congreso 23.07.2023 je Provinz (Junta Electoral Central, BOE)
def es_laden(abruf):
    """BOE-Bekanntmachung der Junta Electoral Central (PDF) -> zwei CSV: Kennzahlen je Provinz (Cuadro I) und Stimmen/Sitze je Partei (Cuadro II und III)."""
    pdf = QUELLEN / "es_cong23_boe.pdf"
    zk, zp = QUELLEN / "es_cong23_resumen.csv", QUELLEN / "es_cong23_partidos.csv"
    if not laden(ES_CONG23, pdf, abruf) or (zk.exists() and zp.exists()):
        return
    import subprocess
    import pdfplumber
    nr = lambda x: int(x.replace(".", "")) if x and re.fullmatch(r"[\d.]+", x.strip()) else None
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    teil = txt[txt.index("CUADRO I"): txt.index("CUADRO II")]
    with zk.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["codigo", "provincia", "electores", "votantes", "validos", "candidaturas", "blanco", "nulos"])
        for l in teil.splitlines():
            m = re.match(r"^\s*(\S.*?)\s{2,}([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$", l)
            if m and m.group(1).strip() in ES_PROV:
                w.writerow([ES_PROV[m.group(1).strip()], m.group(1).strip()] + [nr(x) for x in m.groups()[1:]])
    reihen = []
    with pdfplumber.open(pdf) as doc:
        for seite in doc.pages[2:30]:
            for tb in seite.extract_tables():
                if len(tb) < 3 or not any("Votos" in (c or "") for c in tb[1]):
                    continue
                spalten, partei = {}, None
                for c in range(1, len(tb[0])):
                    kopf = (tb[0][c] or "").replace("\n", " ").strip()
                    if kopf and "Total" not in kopf:
                        partei = kopf
                    elif kopf:
                        partei = None
                    art = (tb[1][c] or "").strip()
                    if partei and art in ("Votos", "Escaños"):
                        spalten[c] = (partei, art)
                for z in tb[2:]:
                    prov = re.sub(r"\s+", " ", (z[0] or "").replace("\n", " ")).replace("/ ", "/").rstrip(".").strip()
                    if prov not in ES_PROV:
                        continue
                    werte = {}
                    for c, (partei, art) in spalten.items():
                        v = nr(z[c] or "")
                        if v is not None:
                            werte.setdefault(partei, {})[art] = v
                    for partei, v in werte.items():
                        if v.get("Votos"):
                            reihen.append([ES_PROV[prov], prov, partei, v["Votos"], v.get("Escaños", 0)])
    with zp.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["codigo", "provincia", "partido", "votos", "escanos"])
        w.writerows(reihen)


def _es_kurz(partei):
    m = re.findall(r"\(([^()]+)\)", partei)
    k = m[-1].strip() if m else partei.rstrip(".")
    return ES_PARTEI.get(k, k)


def es_cong23():
    """Congreso de los Diputados 23.07.2023: Verhältniswahl (D'Hondt, 3-%-Hürde je Provinz) in 52 Wahlkreisen (50 Provinzen, Ceuta, Melilla)."""
    zk, zp = QUELLEN / "es_cong23_resumen.csv", QUELLEN / "es_cong23_partidos.csv"
    if not (zk.exists() and zp.exists()):
        return None
    werte, ges, sitze = {}, {}, {}
    kenn = {z["codigo"]: z for z in csv.DictReader(zk.open(encoding="utf-8"))}
    st = {}
    for z in csv.DictReader(zp.open(encoding="utf-8")):
        p = _es_kurz(z["partido"])
        d = st.setdefault(z["codigo"], {"p": {}, "s": {}})
        d["p"][p] = d["p"].get(p, 0) + int(z["votos"])
        d["s"][p] = d["s"].get(p, 0) + int(z["escanos"] or 0)
    for k, K in kenn.items():
        d = st.get(k, {"p": {}, "s": {}})
        validos = int(K["validos"])                      # Bezug: gültige Stimmen einschließlich leerer Stimmzettel (wie im spanischen Recht)
        werte[k] = {"n": K["provincia"], "s": {"s": anteile(list(d["p"].items()), validos)},
                    "sitze": [[p, n, None] for p, n in sorted(d["s"].items(), key=lambda x: -x[1]) if n], "wb": int(K["electores"]), "w": int(K["votantes"]),
                    "bet": r1(int(K["votantes"]) / int(K["electores"]) * 100)}
        werte[k]["sitze_n"] = sum(x[1] for x in werte[k]["sitze"])
        for p, n in d["p"].items():
            ges[p] = ges.get(p, 0) + n
        for p, n in d["s"].items():
            sitze[p] = sitze.get(p, 0) + n
    wb, w, validos = (sum(int(K[x]) for K in kenn.values()) for x in ("electores", "votantes", "validos"))
    g = {"s": {"s": anteile(list(ges.items()), validos)}, "sitze": [[p, n, None] for p, n in sorted(sitze.items(), key=lambda x: -x[1]) if n],
         "sitze_n": sum(sitze.values()), "wb": wb, "w": w, "bet": r1(w / wb * 100),
         "sitze_hinweis": "PSOE einschließlich PSC (Katalonien); Anteile an den gültigen Stimmen einschließlich leerer Stimmzettel"}
    return {"g": g, "farben": ES_FARBEN, "stimmarten": [["s", "Stimmen"]], "status": "endgültig",
            "system": "Verhältniswahl mit geschlossenen Listen in 52 Wahlkreisen (Provinzen, Ceuta, Melilla); Sitzverteilung nach D'Hondt je Provinz, 3-%-Hürde.",
            "einheiten": [{"id": "prov", "name": "Provinzen (Wahlkreise)", "einzahl": "Provinz", "art": "wahlkreis", "geo": "wahlkreise-es", "werte": werte}],
            "quelle": {"name": "Junta Electoral Central, Resumen de los resultados (BOE-A-2023-18907); Grenzen: Natural Earth", "url": ES_CONG23,
                       "lizenz": "amtliche Bekanntmachung; Grenzen gemeinfrei"}}


# ---------------------------------------------------------------- Norwegen: Storting 08.09.2025 je Wahlkreis (19 alte Fylker, Valgdirektoratet)
def no_laden(abruf):
    ziel = QUELLEN / "no_st25.json"
    if ziel.exists() or not abruf:
        return
    import requests
    land = requests.get(NO_ST25, timeout=120).json()
    kreise = [requests.get("https://valgresultat.no/api" + r["href"], timeout=120).json() for r in land["_links"]["related"]]
    knapp = lambda d: {k: d[k] for k in ("id", "antallsb", "mandater", "stemmer", "frammote", "partier")}
    ziel.write_text(json.dumps({"land": knapp(land), "kreise": [knapp(k) for k in kreise]}, ensure_ascii=False, indent=0), encoding="utf-8")


def no_st25():
    """Stortingswahl 2025: Verhältniswahl (modifiziertes Sainte-Laguë) in 19 Wahlkreisen, 150 Sitze direkt, 19 Ausgleichsmandate (4-%-Hürde)."""
    pfad = QUELLEN / "no_st25.json"
    if not pfad.exists():
        return None
    d = json.loads(pfad.read_text())

    def wert(x):
        l, sitze = [], []
        for p in x["partier"]:
            n = NO_PARTEI.get(p["id"]["partikode"], "Sonstige")
            r = p["stemmer"]["resultat"]
            if p["id"]["partikode"] == "Andre" or not (r.get("antall") or {}).get("total") or r.get("prosent") is None:   # „Andre“ = Summe der übrigen
                continue
            alt = next((y for y in l if y[0] == n), None)
            if alt:
                alt[1] += r["antall"]["total"]
                alt[2] = r1(alt[2] + r["prosent"])
                alt[3] = None
            else:
                end = (r.get("endring") or {}).get("samme")
                l.append([n, r["antall"]["total"], r1(r["prosent"]), r1(r["prosent"] - end) if end is not None else None])
            m = (p.get("mandater") or {}).get("resultat") or {}
            if m.get("antall") or m.get("endring"):
                sitze.append([n, m.get("antall", 0), m.get("antall", 0) - (m.get("endring") or 0)])
        o = {"s": {"s": sorted(l, key=lambda y: -y[1])}, "sitze": sorted(sitze, key=lambda y: -y[1]), "sitze_n": x["mandater"]["antall"],
             "wb": x["antallsb"], "w": x["stemmer"]["total"], "bet": r1(x["frammote"]["prosent"])}
        return o
    werte = {}
    for k in d["kreise"]:
        werte["NO-" + NO_KREIS.get(k["id"]["nr"], k["id"]["nr"])] = {"n": k["id"]["navn"], **wert(k)}
    g = wert(d["land"])
    g["sitze_hinweis"] = "einschließlich 19 Ausgleichsmandate; Veränderung zur Wahl 2021"
    return {"g": g, "farben": NO_FARBEN, "stimmarten": [["s", "Stimmen"]], "status": "endgültig",
            "system": ("Verhältniswahl in 19 Wahlkreisen (die Fylker vor der Reform 2020); 150 Sitze in den Wahlkreisen nach modifiziertem Sainte-Laguë, "
                       "dazu 19 Ausgleichsmandate für Parteien ab 4 % landesweit."),
            "vor": {"datum": "2021-09-13", "titel": "Stortingswahl 2021"},
            "einheiten": [{"id": "wk", "name": "Wahlkreise (Fylker vor 2020)", "einzahl": "Wahlkreis", "art": "wahlkreis", "geo": "wahlkreise-no", "werte": werte}],
            "quelle": {"name": "Valgdirektoratet, valgresultat.no; Grenzen: Natural Earth", "url": "https://valgresultat.no/valg/2025/st", "lizenz": "NLOD 2.0; Grenzen gemeinfrei"}}


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
    ca_laden(not a.ohne_abruf)
    au_laden(not a.ohne_abruf)
    ch_laden(not a.ohne_abruf)
    at_laden(not a.ohne_abruf)
    us_laden(not a.ohne_abruf)
    es_laden(not a.ohne_abruf)
    no_laden(not a.ohne_abruf)
    ne_wahlkreise(not a.ohne_abruf, "ES", WK_ES_GEO)
    ne_wahlkreise(not a.ohne_abruf, "NO", WK_NO_GEO)
    for geo in (KREISE_GEO, LWK_NW_GEO, WK_GB_GEO, WK_FR_GEO, WK_CA_GEO, WK_AU_GEO, GEM_AT_GEO, WK_US_GEO, WK_ES_GEO, WK_NO_GEO, GEM_CH_GEO):
        kompakt(geo)
    wahlen = [w for w in national(pa) if w["land"] != "DE" or w["kammer"] != "unterhaus"]
    wahlen.append(bundestag(pa, HIER / "geo/wahlkreise_bund.geojson", HIER / "geo/de_laender.geojson"))
    if ew:
        wahlen.append(ew)
    gb, fr, ca, au, ch, at, es = gb_ge24(), fr_leg24(), ca_ge25(), au_ge25(), ch_nrw23(), at_nrw24(), es_cong23()
    no = no_st25()
    for w in wahlen:
        if no and w["id"] == "NO-unterhaus-2025":
            w.update(no)
        if es and w["id"] == "ES-unterhaus-2023":
            w.update(es)
        if at and w["id"] == "AT-unterhaus-2024":
            w.update(at)
        if ch and w["id"] == "CH-unterhaus-2023":
            w.update(ch)
        if au and w["id"] == "AU-unterhaus-2025":
            w.update(au)
        if ca and w["id"] == "CA-unterhaus-2025":
            w.update(ca)
        if gb and w["id"] == "GB-unterhaus-2024":
            w.update(gb)
        if fr and w["id"] == "FR-unterhaus-2024":
            w.update(fr)
    us = us_house24()
    if us:
        # Die Wahl 2026 ist noch nicht ausgezählt (nur heutige Zusammensetzung): bis dahin zeigt die Karte die Wahl 2024, damit sich keine zwei Wahlen überdecken
        alt = [i for i, w in enumerate(wahlen) if w["land"] == "US" and w["kammer"] == "unterhaus" and not (w["g"].get("s") or {}).get("s")]
        if alt:
            wahlen[alt[0]] = us
        else:
            wahlen.append(us)
    wahlen += regional(pa, ko) + kommunal(ko)
    daten = {"stand": date.today().isoformat(), "ebenen": EBENEN_NAMEN, "eu": sorted(EU), "farben": {"DE": DE_FARBEN}, "ordnung": {"DE": DE_ORDNUNG}, "wahlen": wahlen}
    OUT.write_text(json.dumps(daten, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    from collections import Counter
    print(f"{len(wahlen)} Wahlen -> {OUT} ({OUT.stat().st_size // 1024} KB); je Ebene:", dict(sorted(Counter(w['e'] for w in wahlen).items())))


if __name__ == "__main__":
    main()
