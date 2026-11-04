"""Gemeinsames Schema der Governance-Importvorlage (Blätter, Spalten, Listen, Feldliste).

Wird von erstelle_vorlage.py (baut die Excel-Datei) und importieren.py (liest und prüft sie) benutzt, damit
Vorlage und Import nie auseinanderlaufen. Neues Feld: hier eintragen, Vorlage neu bauen, Import anpassen.
Ziel-Tabellen: governance/*.csv (Schema siehe governance/README.md).
"""

VERSION = "1.0"
BEISPIEL = "[Beispiel]"  # Zeilen mit diesem Präfix (Name/Bemerkung) werden beim Import ignoriert

# Spalte = (Name, Pflicht, Breite, Hinweis)
_ID = ("Unternehmens-ID", True, 14, "ID aus stammdaten/unternehmen_ids.csv (Format U000123), siehe Blatt ID-Liste. Nicht selbst vergeben.")
_GJ = ("Geschäftsjahr", True, 12, "Vierstellig; das Jahr, in dem das Geschäftsjahr endet (GJ bis 30.09.2025 = 2025).")
_QUELLE = ("Quelle", True, 46, "Pfad im Repo (governance/dokumente/<Ordner>/<Datei>.pdf) oder direkter https-Link auf das Dokument.")
_SEITE = ("Seite", True, 9, "PDF-Seite (nicht die aufgedruckte Seitenzahl). Bereich 12-13 oder Liste 12, 14 erlaubt.")
_STAND = ("Stand", False, 12, "Datum, auf das sich die Angabe bezieht (TT.MM.JJJJ), z. B. 31.12.2025 oder Datum der Hauptversammlung.")
_BEM = ("Bemerkung", False, 40, "Besonderheiten, Abgrenzungen, warum ein Feld leer ist. Nie Schätzungen eintragen.")
_AUTO = ("Unternehmen (automatisch)", False, 30, "Wird per Formel aus der ID-Liste gefüllt, nur zur Kontrolle. Beim Import ignoriert.")

ORGANE = ["Vorstand", "Aufsichtsrat", "Geschäftsführung", "Gesellschafterausschuss", "Verwaltungsrat", "Beirat"]
VERTRETERART = ["Anteilseigner", "Arbeitnehmer", "Arbeitnehmer (Gewerkschaft)", "Arbeitnehmer (leitende Angestellte)"]
GREMIEN_VERG = ["Vorstand", "Aufsichtsrat", "Geschäftsführung", "Gesellschafterausschuss", "Verwaltungsrat", "Beirat"]
MANDAT_TYP = ["a", "b"]
GESCHLECHT = ["weiblich", "männlich", "divers"]
VARIANTEN = ["A", "B", "Bericht"]
BEZUG_PAYRATIO = ["Vorstandsvorsitzender", "Ø Vorstandsmitglied", "höchstbezahlte Person", "Ausweis laut Bericht"]
MITBESTIMMUNG = ["MitbestG", "DrittelbG", "MontanMitbestG", "Montan-Mitbestimmungsergänzungsgesetz", "SE-Beteiligungsvereinbarung", "keine"]
VERG_ARTEN = [
    "Gewährte und geschuldete Vergütung gem. § 162 AktG (Gesamtvergütung)",
    "Gewährte und geschuldete Vergütung (Grund- und Ausschussvergütung)",
    "Gesamtbezüge gem. § 285 Nr. 9a HGB",
    "Gesamtvergütung laut DCGK-Tabelle (Zufluss)",
    "Gesamtvergütung laut DCGK-Tabelle (Zuwendung)",
    "Gesamtvergütung",
]
WERDEGANG_ARTEN = ["Beruf laut Organverzeichnis", "Funktion laut Mandatsverzeichnis", "Lebenslauf laut Geschäftsbericht", "Lebenslauf laut Website des Unternehmens"]
DOKUMENTARTEN = ["Geschäftsbericht", "Vergütungsbericht", "Corporate-Governance-Erklärung", "Jahresabschluss (HGB)", "Nachhaltigkeitsbericht",
                 "Organverzeichnis / Gremienübersicht", "Hauptversammlungsunterlagen", "Website des Unternehmens", "Sonstige"]
JA_NEIN = ["ja", "nein"]

# --- Blatt-Definitionen: (Blattname, Spalten)
GREMIEN = [
    _ID, _AUTO, _GJ,
    ("Organ", True, 18, "Vorstand, Aufsichtsrat, Geschäftsführung, Gesellschafterausschuss, Verwaltungsrat oder Beirat (Dropdown)."),
    ("Name", True, 28, "Name wie im Dokument, mit Titel (Dr., Prof.). Dieselbe Person in allen Blättern gleich schreiben; daraus wird die Personen-ID gebildet."),
    ("Funktion", False, 26, "z. B. Vorsitzender (CEO), stellv. Vorsitzender, Mitglied, Finanzen (CFO), Arbeitsdirektorin."),
    ("Vertreterart", False, 24, "Nur Aufsichtsrat: Anteilseigner, Arbeitnehmer, Arbeitnehmer (Gewerkschaft), Arbeitnehmer (leitende Angestellte). Leer, wenn im Dokument nicht ausgewiesen."),
    ("Mitglied seit", False, 13, "Datum TT.MM.JJJJ (oder nur Jahr/Monat als Text JJJJ-MM). Leer, wenn nicht belegt; leer heißt nicht ganzjährig."),
    ("Mitglied bis", False, 13, "Austrittsdatum, falls im Berichtsjahr ausgeschieden."),
    ("Beruf laut Dokument", False, 36, "Ausgeübter Beruf bzw. Hauptfunktion wörtlich laut Organverzeichnis. Nur Beruflich-Relevantes, kein Wohnort, keine Familie."),
    _QUELLE, _SEITE, _STAND, _BEM,
]
VERGUETUNG = [
    _ID, _AUTO, _GJ,
    ("Gremium", True, 18, "Vorstand, Aufsichtsrat usw. (Dropdown)."),
    ("Name", True, 28, "Name der Person (wie im Blatt Gremienmitglieder) oder Summenzeile: Name beginnt mit Gesamt, Barwert oder Zahlungen."),
    ("Betrag (TEUR)", True, 14, "Betrag in Tausend Euro (T€), Zahl ohne Tausenderpunkt. Bei Angabe in Euro durch 1000 teilen und im Hinweis den Originalwert nennen. Keine Umrechnung fremder Währungen."),
    ("Art", True, 46, "Was genau der Betrag ist, möglichst wörtlich (Dropdown mit Vorschlägen; eigener Text zulässig)."),
    _QUELLE, _SEITE, _STAND, _BEM,
]
KENNZAHLEN = [
    _ID, _AUTO, _GJ,
    ("Feld", True, 32, "Eintrag aus dem Blatt Feldliste (Dropdown)."),
    ("Wert", True, 16, "Zahl (Personen, %) oder Text bei mitbestimmung_ar. Nur eintragen, wenn im Dokument belegt; sonst Zeile weglassen."),
    ("Einheit", False, 12, "Personen, % oder leer. Vorbelegt durch die Feldliste, wird sonst ergänzt."),
    _QUELLE, _SEITE, _STAND, _BEM,
]
PAYRATIO = [
    _ID, _AUTO, _GJ,
    ("Variante", True, 10, "A = Ø-Vergütung der Beschäftigten in Deutschland (vergleichende Darstellung § 162 AktG); B = Konzern (Personalaufwand/Beschäftigte); Bericht = vom Unternehmen ausgewiesene Pay Ratio."),
    ("Bezug", False, 24, "Worauf sich die Quote bezieht: Vorstandsvorsitzender, Ø Vorstandsmitglied, höchstbezahlte Person oder Ausweis laut Bericht."),
    ("Pay Ratio (berichtet)", False, 14, "Nur Variante Bericht: das vom Unternehmen genannte Verhältnis (z. B. 125,83). Nicht selbst berechnen."),
    ("Ø-Vergütung Beschäftigte (TEUR)", False, 16, "Nur Variante A: durchschnittliche Jahresvergütung der Vergleichsbelegschaft in T€."),
    ("Personalaufwand Konzern (Mio. EUR)", False, 16, "Nur Variante B: Personalaufwand laut Konzern-GuV in Mio. €."),
    ("Beschäftigte (Anzahl)", False, 13, "Nur Variante B: Zahl der Beschäftigten (Köpfe/FTE/Ø/Stichtag siehe Basis)."),
    ("Beschäftigtenkreis / Basis", True, 44, "Exakte Definition der Belegschaft/Basis: z. B. Deutschland, Vollzeitäquivalente; Konzern, Ø Köpfe."),
    _QUELLE, _SEITE, _STAND, _BEM,
]
GESCHLECHT_BELEGE = [
    ("Name", True, 28, "Name wie im Blatt Gremienmitglieder."),
    _ID, _AUTO,
    ("Geschlecht", True, 12, "weiblich, männlich oder divers (Dropdown)."),
    ("Beleg", True, 50, "Wörtlicher Beleg im Dokument: Anrede, Funktionsbezeichnung (Vorständin), Possessivpronomen, Geschlechtsangabe in Tabelle. NIE aus dem Vornamen ableiten."),
    _QUELLE, _SEITE,
]
MANDATE = [
    ("Name", True, 28, "Name der Person (wie im Blatt Gremienmitglieder oder in personen.csv)."),
    ("Typ", True, 6, "a = gesetzlicher Aufsichtsrat im Inland, b = vergleichbares in- oder ausländisches Kontrollgremium (§ 285 Nr. 10 HGB / § 125 AktG)."),
    ("Gesellschaft", True, 34, "Name der Gesellschaft, in der das Mandat besteht."),
    ("Gesellschaft-ID", False, 14, "Unternehmens-ID (U000123), wenn die Gesellschaft selbst in stammdaten/ steht; sonst leer."),
    ("Sitz", False, 16, "Sitz der Gesellschaft laut Dokument."),
    ("Funktion", False, 28, "z. B. Mitglied des Aufsichtsrats, Vorsitzender des Verwaltungsrats."),
    ("Gültig", False, 22, "Zeitbezug laut Dokument, z. B. seit 2025-05-22 oder bis 2024-12-31."),
    ("Gemeldet von (Unternehmens-ID)", True, 16, "Unternehmen, dessen Bericht das Mandat nennt (Quelle)."),
    ("Gemeldet von (automatisch)", False, 28, "Formel, nur Kontrolle."),
    _GJ, _QUELLE, _SEITE, _BEM,
]
WERDEGANG = [
    ("Name", True, 28, "Name der Person (wie im Blatt Gremienmitglieder oder in personen.csv)."),
    ("Station", True, 60, "Berufliche Station: Funktion und Arbeitgeber, kurz. Nur beruflich Relevantes."),
    ("Organisation", False, 28, "Arbeitgeber/Organisation getrennt, falls sinnvoll."),
    ("Zeitraum", False, 18, "z. B. 2015-2020, seit 2021, lt. Dokument."),
    ("Art", False, 38, "Art der Quelle der Station (Dropdown, eigener Text zulässig)."),
    _QUELLE, _SEITE,
]
QUELLEN = [
    _ID, _AUTO,
    ("Dokumentart", True, 30, "Aus der Liste."),
    _GJ,
    ("Titel", True, 44, "Titel des Dokuments."),
    ("URL", True, 50, "Direkter Link oder Pfad im Repo."),
    ("Abrufdatum", True, 13, "Datum des Abrufs TT.MM.JJJJ."),
    ("Veröffentlicht am", False, 15, "Veröffentlichungsdatum des Dokuments, falls bekannt."),
    ("Sprache", False, 9, "de, en, ..."),
    ("Hinweis", False, 36, "Zugangsbeschränkung, Seitenumfang, Besonderheiten."),
]

# Feldliste Kennzahlen Gremien: (Feld, Typ, Einheit, Definition)
FELDER = [
    ("vorstand_mitglieder_zahl", "Zahl", "Personen", "Zahl der Vorstandsmitglieder zum Stichtag bzw. im Berichtsjahr (angeben, welches in der Bemerkung)."),
    ("vorstand_frauen_zahl", "Zahl", "Personen", "Frauen im Vorstand laut Dokument (Zahl oder namentlich belegte Frauen). Nur, wenn im Dokument ausgewiesen."),
    ("geschaeftsfuehrung_mitglieder_zahl", "Zahl", "Personen", "Mitglieder der Geschäftsführung (GmbH, KG)."),
    ("geschaeftsfuehrung_frauen_zahl", "Zahl", "Personen", "Frauen in der Geschäftsführung."),
    ("gesellschafterausschuss_mitglieder_zahl", "Zahl", "Personen", "Mitglieder des Gesellschafterausschusses (KGaA)."),
    ("ar_mitglieder_zahl", "Zahl", "Personen", "Mitglieder des Aufsichtsrats (ohne Ersatzmitglieder)."),
    ("ar_frauen_zahl", "Zahl", "Personen", "Frauen im Aufsichtsrat laut Dokument."),
    ("ar_anteilseigner_zahl", "Zahl", "Personen", "Vertreter der Anteilseigner im Aufsichtsrat."),
    ("ar_arbeitnehmervertreter_zahl", "Zahl", "Personen", "Arbeitnehmervertreter im Aufsichtsrat, einschließlich Gewerkschaftsvertreter und leitender Angestellter."),
    ("ar_gewerkschaftsvertreter_zahl", "Zahl", "Personen", "Davon von Gewerkschaften entsandte Mitglieder."),
    ("ar_betriebsraete_zahl", "Zahl", "Personen", "Davon Betriebsräte (falls ausgewiesen)."),
    ("mitbestimmung_ar", "Text", "", "Anwendbares Mitbestimmungsregime im Aufsichtsrat: MitbestG, DrittelbG, MontanMitbestG, SE-Beteiligungsvereinbarung oder keine."),
    ("mitarbeiter_jahresdurchschnitt", "Zahl", "Personen", "Durchschnittliche Mitarbeiterzahl im Geschäftsjahr laut Bericht (Köpfe oder FTE in der Bemerkung angeben)."),
    ("gender_pay_gap_belegschaft_pct", "Zahl", "%", "Vom Unternehmen ausgewiesener unbereinigter Gender Pay Gap der Belegschaft in Prozent."),
]
FELD_NAMEN = [f[0] for f in FELDER]
FELD_EINHEIT = {f[0]: f[2] for f in FELDER}
FELD_TYP = {f[0]: f[1] for f in FELDER}

BLAETTER = {  # Blattname -> Spalten
    "Gremienmitglieder": GREMIEN,
    "Vergütung": VERGUETUNG,
    "Kennzahlen Gremien": KENNZAHLEN,
    "Pay Ratio": PAYRATIO,
    "Geschlecht (Belege)": GESCHLECHT_BELEGE,
    "Mandate extern": MANDATE,
    "Werdegang": WERDEGANG,
    "Quellen-Dokumente": QUELLEN,
}
