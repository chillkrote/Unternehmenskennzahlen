"""Gemeinsames Schema der Importvorlage: Spalten, Dropdown-Listen und feste Kennzahlenliste.

Wird von erstelle_vorlage.py (baut die Excel-Datei) und importieren.py (liest und prüft sie) benutzt, damit
Vorlage und Import nie auseinanderlaufen. Neue Kennzahl: nur hier in KENNZAHLEN eintragen, Vorlage neu bauen.
"""

VERSION = "1.0"
BEISPIEL = "[Beispiel]"  # Zeilen, deren Unternehmensname so beginnt, werden beim Import ignoriert

# (Spaltenname, Pflicht, Breite, Hinweis)
UNTERNEHMEN = [
    ("Name", True, 38, "Offizielle Firma wie im Handelsregister/Geschäftsbericht, inkl. Rechtsform. Eindeutig im Blatt."),
    ("Rechtsform", False, 14, "z. B. AG, SE, GmbH, KGaA, eG, plc, S.A., N.V., Inc."),
    ("Land", True, 16, "Land des Sitzes, englischer Name aus der Liste."),
    ("Sitz", False, 18, "Ort des Hauptsitzes."),
    ("ISIN", False, 16, "12 Zeichen, Prüfziffer wird geprüft. Leer bei nicht börsennotierten Unternehmen. Mehrere ISINs: mit | trennen."),
    ("Ticker", False, 12, "Kürzel an der Hauptbörse, z. B. SAP.DE (Yahoo-Schreibweise bevorzugt)."),
    ("Börse", False, 18, "Hauptbörse/Segment, z. B. Xetra, Frankfurt Prime Standard, Euronext Paris."),
    ("Börsennotiert", True, 14, "ja oder nein (Aktien zum Handel zugelassen)."),
    ("Branche", True, 22, "Eine Branche aus der Liste (Branchenschlüssel des Repos)."),
    ("WZ/NACE-Code", False, 14, "NACE Rev. 2 bzw. WZ 2008, z. B. 62.01."),
    ("LEI", False, 24, "20 Zeichen, Prüfsumme wird geprüft. Quelle: GLEIF (kostenlos)."),
    ("Handelsregisternummer", False, 22, "z. B. HRB 12345, Amtsgericht München."),
    ("Website", False, 30, "Offizielle Website (https://...)."),
    ("Bank", True, 8, "ja bei Kreditinstituten (Bankbilanz), sonst nein."),
    ("Index-Zugehörigkeit", False, 24, "z. B. DAX, MDAX, SDAX, TecDAX, STOXX Europe 600; mehrere mit | trennen."),
    ("Beschreibung", False, 50, "1 bis 2 Sätze zum Geschäft, nur belegbare Fakten."),
    ("Quelle Stammdaten (URL)", True, 40, "Seite, auf der Name/ISIN/Sitz belegt sind (Börse, Register, Unternehmensseite)."),
]

KENNZAHLEN_SPALTEN = [
    ("Unternehmen", True, 38, "Name exakt wie im Blatt Unternehmen (Dropdown)."),
    ("Geschäftsjahr", True, 13, "Vierstellig; das Jahr, in dem das Geschäftsjahr endet (GJ bis 30.06.2025 = 2025)."),
    ("Stichtag", True, 13, "Abschlussstichtag als Datum TT.MM.JJJJ (bei Marktkapitalisierung: Bewertungstag)."),
    ("Rechnungslegung", True, 16, "HGB, IFRS, US-GAAP oder Sonstige."),
    ("Währung", True, 10, "ISO-Code der Berichtswährung (Dropdown), keine Umrechnung."),
    ("Einheit", True, 12, "Einheit, in der der Wert in der Zelle steht (Dropdown)."),
    ("Kennzahl", True, 34, "Nur Einträge aus dem Blatt Kennzahlenliste (Dropdown)."),
    ("Wert", True, 18, "Zahl ohne Tausenderpunkt/Einheitentext; Minus für negative Werte. Leer lassen, wenn unbekannt: dann Zeile weglassen."),
    ("Quelle", True, 30, "Dokument/Seite der Quelle, z. B. Konzernabschluss 2025, Konzernbilanz."),
    ("URL", True, 40, "Direkter Link auf das Dokument (https://...)."),
    ("Seite", False, 9, "Seite im PDF bzw. gedruckte Seitenzahl."),
    ("Hinweis", False, 30, "z. B. angepasst, Pro-forma, Rumpfgeschäftsjahr, abgeleitet aus ..."),
]

QUELLEN_SPALTEN = [
    ("Unternehmen", True, 38, "Name exakt wie im Blatt Unternehmen (Dropdown)."),
    ("Dokumentart", True, 26, "Aus der Liste."),
    ("Geschäftsjahr", False, 13, "Falls zutreffend."),
    ("Titel", True, 40, "Titel des Dokuments."),
    ("URL", True, 50, "Direkter Link auf PDF/Seite."),
    ("Abrufdatum", True, 13, "Datum des Abrufs TT.MM.JJJJ."),
    ("Sprache", False, 9, "de, en, ..."),
    ("Hinweis", False, 30, "Zugangsbeschränkung, Seitenumfang, Besonderheiten."),
]

RECHNUNGSLEGUNG = ["HGB", "IFRS", "US-GAAP", "Sonstige"]
EINHEITEN = ["absolut", "Tausend", "Millionen", "Milliarden", "Prozent", "Anzahl"]
FAKTOR = {"absolut": 1, "Tausend": 1e3, "Millionen": 1e6, "Milliarden": 1e9, "Prozent": 1, "Anzahl": 1}
JA_NEIN = ["ja", "nein"]
WAEHRUNGEN = ["EUR", "USD", "GBP", "CHF", "SEK", "NOK", "DKK", "PLN", "CZK", "HUF", "RON", "JPY", "CNY", "HKD",
              "CAD", "AUD", "KRW", "INR", "BRL", "TRY", "ZAR", "MXN", "SGD", "AED", "SAR", "ILS"]
BRANCHEN = ["banken", "versicherungen", "finanzdienstleister", "immobilien", "industrie", "automobil", "chemie-rohstoffe",
            "energie", "energie-versorger", "handel-konsum", "pharma-gesundheit", "software-it", "technologie",
            "telekom-medien", "transport-logistik", "sonstige"]
LAENDER = ["Germany", "Austria", "Switzerland", "Liechtenstein", "Luxembourg", "Netherlands", "Belgium", "France",
           "UK", "Ireland", "Italy", "Spain", "Portugal", "Greece", "Denmark", "Sweden", "Norway", "Finland", "Iceland",
           "Poland", "Czechia", "Hungary", "Romania", "Slovakia", "Slovenia", "Croatia", "Bulgaria", "Estonia", "Latvia",
           "Lithuania", "Malta", "Cyprus", "Turkey", "USA", "Canada", "Mexico", "Brazil", "Japan", "China", "Hong Kong",
           "South Korea", "India", "Australia", "Singapore", "Israel", "South Africa", "United Arab Emirates",
           "Saudi Arabia", "Jordan", "Taiwan", "Sonstige"]
DOKUMENTARTEN = ["Geschäftsbericht", "Konzernabschluss", "Jahresabschluss", "Lagebericht", "Halbjahresbericht",
                 "Offenlegungsbericht", "Nachhaltigkeitsbericht", "Unternehmensregister/Bundesanzeiger",
                 "SEC-Filing", "Registerauszug", "Börsenprospekt", "Sonstiges"]

# (Bezeichnung, Code, Bereich, Typ, Bank-spezifisch, Definition)
# Typ: Geld = Betrag in Währung; JeAktie = Betrag je Aktie in Währung (Einheit absolut); Prozent; Anzahl
KENNZAHLEN = [
    ("Bilanzsumme", "BILANZSUMME", "Bilanz", "Geld", False, "Summe der Aktiva = Summe der Passiva laut Bilanz."),
    ("Summe Aktiva", "SUMME_AKTIVA", "Bilanz", "Geld", False, "Nur angeben, wenn Aktiva- und Passivseite getrennt ausgewiesen sind (für Bilanzprobe)."),
    ("Summe Passiva", "SUMME_PASSIVA", "Bilanz", "Geld", False, "Siehe Summe Aktiva."),
    ("Anlagevermögen", "ANLAGEVERMOEGEN", "Bilanz", "Geld", False, "Langfristige Vermögenswerte (non-current assets)."),
    ("Umlaufvermögen", "UMLAUFVERMOEGEN", "Bilanz", "Geld", False, "Kurzfristige Vermögenswerte (current assets)."),
    ("Vorräte", "VORRAETE", "Bilanz", "Geld", False, "Vorräte/Inventories."),
    ("Forderungen aus Lieferungen und Leistungen", "FORDERUNGEN_LL", "Bilanz", "Geld", False, "Trade receivables."),
    ("Liquide Mittel", "LIQUIDE_MITTEL", "Bilanz", "Geld", False, "Kassenbestand, Bankguthaben, Zahlungsmitteläquivalente."),
    ("Eigenkapital", "EIGENKAPITAL", "Bilanz", "Geld", False, "Gesamtes Eigenkapital inkl. Anteile Dritter."),
    ("Eigenkapital der Anteilseigner", "EIGENKAPITAL_MUTTER", "Bilanz", "Geld", False, "Eigenkapital ohne Anteile Dritter (Minderheiten)."),
    ("Verbindlichkeiten gesamt", "VERBINDLICHKEITEN", "Bilanz", "Geld", False, "Fremdkapital: alle Schulden inkl. Rückstellungen (= Bilanzsumme minus Eigenkapital)."),
    ("Finanzverbindlichkeiten", "FINANZVERBINDLICHKEITEN", "Bilanz", "Geld", False, "Verzinsliche Schulden (Anleihen, Bankkredite, Leasing)."),
    ("Rückstellungen", "RUECKSTELLUNGEN", "Bilanz", "Geld", False, "Summe der Rückstellungen inkl. Pensionen."),
    ("Kurzfristige Verbindlichkeiten", "VERBINDLICHKEITEN_KURZ", "Bilanz", "Geld", False, "Fällig innerhalb eines Jahres."),
    ("Langfristige Verbindlichkeiten", "VERBINDLICHKEITEN_LANG", "Bilanz", "Geld", False, "Fällig nach mehr als einem Jahr."),
    ("Umsatz", "UMSATZ", "GuV", "Geld", False, "Umsatzerlöse (Banken: leer lassen, stattdessen Zins- und Provisionsüberschuss)."),
    ("Bruttoergebnis", "BRUTTOERGEBNIS", "GuV", "Geld", False, "Umsatz minus Umsatzkosten."),
    ("EBITDA", "EBITDA", "GuV", "Geld", False, "Nur wenn im Abschluss ausgewiesen oder aus Posten berechenbar (Hinweis eintragen)."),
    ("EBIT", "EBIT", "GuV", "Geld", False, "Operatives Ergebnis vor Zinsen und Steuern."),
    ("Finanzergebnis", "FINANZERGEBNIS", "GuV", "Geld", False, "Zinserträge minus Zinsaufwendungen und übrige Finanzposten."),
    ("Ergebnis vor Steuern", "EBT", "GuV", "Geld", False, "Ergebnis vor Ertragsteuern."),
    ("Ertragsteuern", "STEUERN", "GuV", "Geld", False, "Steueraufwand positiv, Steuerertrag negativ."),
    ("Jahresergebnis", "JAHRESERGEBNIS", "GuV", "Geld", False, "Jahresüberschuss/-fehlbetrag inkl. Anteile Dritter; Verlust negativ."),
    ("Jahresergebnis der Anteilseigner", "JAHRESERGEBNIS_MUTTER", "GuV", "Geld", False, "Ergebnis nach Anteilen Dritter."),
    ("Zinsüberschuss", "ZINSUEBERSCHUSS", "GuV", "Geld", True, "Nur Banken: Zinsergebnis."),
    ("Provisionsüberschuss", "PROVISIONSUEBERSCHUSS", "GuV", "Geld", True, "Nur Banken: Provisionsergebnis."),
    ("Operativer Cashflow", "CF_OPERATIV", "Cashflow", "Geld", False, "Cashflow aus laufender Geschäftstätigkeit."),
    ("Investitions-Cashflow", "CF_INVESTITION", "Cashflow", "Geld", False, "Cashflow aus Investitionstätigkeit (meist negativ)."),
    ("Finanzierungs-Cashflow", "CF_FINANZIERUNG", "Cashflow", "Geld", False, "Cashflow aus Finanzierungstätigkeit."),
    ("Investitionen (Capex)", "CAPEX", "Cashflow", "Geld", False, "Auszahlungen für Sachanlagen und immaterielle Werte, als positiver Betrag."),
    ("Mitarbeiter", "MITARBEITER", "Sonstige", "Anzahl", False, "Beschäftigte zum Stichtag (Köpfe oder FTE, im Hinweis nennen)."),
    ("Mitarbeiter im Durchschnitt", "MITARBEITER_DURCHSCHNITT", "Sonstige", "Anzahl", False, "Durchschnittlich Beschäftigte im Geschäftsjahr."),
    ("Dividende je Aktie", "DIVIDENDE_JE_AKTIE", "Sonstige", "JeAktie", False, "Für das Geschäftsjahr beschlossen/vorgeschlagen; Einheit absolut."),
    ("Dividende gesamt", "DIVIDENDE_GESAMT", "Sonstige", "Geld", False, "Ausschüttungssumme für das Geschäftsjahr."),
    ("Ergebnis je Aktie", "EPS", "Sonstige", "JeAktie", False, "Unverwässert; Einheit absolut."),
    ("Aktienanzahl", "AKTIEN", "Sonstige", "Anzahl", False, "Ausgegebene Aktien zum Stichtag."),
    ("Marktkapitalisierung", "MARKTKAPITALISIERUNG", "Markt", "Geld", False, "Börsenwert am Stichtag (Kurs mal Aktien); Stichtag = Bewertungstag."),
    ("Aktienkurs", "KURS", "Markt", "JeAktie", False, "Schlusskurs am Stichtag; Einheit absolut."),
    ("Kernkapitalquote (CET1)", "CET1_QUOTE", "Bank", "Prozent", True, "Nur Banken: harte Kernkapitalquote in Prozent (12,5 = 12,5 %)."),
    ("Gesamtkapitalquote", "GESAMTKAPITALQUOTE", "Bank", "Prozent", True, "Nur Banken, in Prozent."),
    ("Risikogewichtete Aktiva (RWA)", "RWA", "Bank", "Geld", True, "Nur Banken: Gesamtrisikobetrag."),
    ("Kundenforderungen", "KUNDENFORDERUNGEN", "Bank", "Geld", True, "Nur Banken: Forderungen an Kunden."),
    ("Kundeneinlagen", "KUNDENEINLAGEN", "Bank", "Geld", True, "Nur Banken: Verbindlichkeiten gegenüber Kunden."),
]
BEZ2CODE = {k[0]: k[1] for k in KENNZAHLEN}
CODE2K = {k[1]: k for k in KENNZAHLEN}
