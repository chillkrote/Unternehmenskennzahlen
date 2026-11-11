# Datenquellenverzeichnis (Arbeitsstand)

Stand 10.11.2026 (B2, erste Prüfrunde). Erste Fassung 09.11.2026 aus dem Code (`app/*.py`, `international/*.py`, `volkswirtschaft/`,
`termine/`) und den Notizen (`app/OFFENE_DATENFELDER.md`, `app/KONZEPT_Handelsrouten.md`, `international/LUECKEN.md`).

**Kennzeichnung der Lizenzspalte:** „geprüft 10.11.“ = Bedingungen beim Herausgeber nachgelesen (Fundstelle verlinkt);
„sekundär 10.11.“ = nur über Dritte oder Suchauszüge belegt, die Originalseite war nicht abrufbar (403) oder nicht auffindbar;
„Repo“ = im Projekt dokumentiert; „allgemeine Kenntnis“ = noch nicht nachgelesen. Das ist eine fachliche Vorprüfung, keine
Rechtsberatung. Vor der öffentlichen Weiterverbreitung über den eigenen Server entscheidet Robin die offenen Punkte (Abschnitt
„Entscheidungen“ unten); bis dahin gilt eine Quelle ohne „geeignet“ nicht als freigegeben.

| Quelle | genutzt für | Abruf (Skript) | Schlüssel | Lizenz / Weiterverbreitung | Bewertung |
|---|---|---|---|---|---|
| Unternehmensberichte (HGB/IFRS, PDF), Bank-Websites, Lobbyregister | Bilanzvergleich, Zeitreihen, Dokumente | Handarbeit, Crawler (`banken/…/skripte`, `termine/`) | nein | Veröffentlichungspflicht; Weitergabe der Originaldokumente urheberrechtlich zu prüfen | prüfen |
| EBA Pillar-3-Hub | Kapital, RWA (Banken) | Export über Browser (Repo-Notiz) | nein | sekundär 10.11.: Ziel des Hubs ist ausdrücklich Zugang und Wiederverwendung der Offenlegungen ([EBA](https://www.eba.europa.eu/risk-and-data-analysis/pillar-3-data-hub)); eigene Lizenzklausel nicht gefunden. Inhalte sind Pflichtveröffentlichungen der Banken | voraussichtlich geeignet mit Quellenangabe; Rechtshinweis der EBA noch nachlesen |
| GLEIF | LEI, Sitz, Register-Nr. | `api.gleif.org` (mehrere Skripte) | nein | allgemein bekannt CC0 | voraussichtlich geeignet |
| SEC EDGAR (Companyfacts) | US-/FPI-Abschlüsse | `international/sec.py` | User-Agent mit Kontakt | US-Behördendaten | voraussichtlich geeignet |
| filings.xbrl.org (ESEF) | EU-Abschlüsse | `international/esef.py` | nein | geprüft 10.11.: „At present, there are no restrictions on the ways that the data can be used“ ([About](https://filings.xbrl.org/about.html)); Quelle der Berichte sind die nationalen Sammelstellen (OAM) | geeignet, Quellenangabe empfohlen |
| OpenDART (Südkorea) | KR-Abschlüsse | `international/dart.py` | `DART_API` (nur Server) | sekundär 10.11.: Nutzungsbedingungen ([terms](https://opendart.fss.or.kr/intro/terms.do)) verweisen für Ungeregeltes auf Urheberrechts- und Gesetz über öffentliche Daten; keine ausdrückliche Weitergabeklausel gefunden; FSS bittet um Quellenangabe | voraussichtlich geeignet mit Quellenangabe; Originaltext (Koreanisch) noch prüfen |
| Yahoo Finance (yfinance) | Kurse, Konzernkennzahlen, Live-Werte | `marktdaten.py`, `boersen_abruf.py`, `kurse_historie.py`, `finanz_abruf.py`, `live_abruf.py`, `termine/` | nein | sekundär 10.11.: yfinance selbst: „intended for personal use only“, verweist auf Yahoos Bedingungen; Yahoo gewährt nur eine persönliche, nicht übertragbare Lizenz; Kursdaten stammen von Börsen mit eigenen Weitergaberechten | **kritisch**: keine Weiterverbreitung auf dem öffentlichen Server ohne Vereinbarung (Entscheidung E1) |
| EZB Data Portal | Wechselkurse, Zinskurven, CISS, Bankensektor | `finanz_abruf.py`, `finanz_makro.py` | nein | Wiederverwendung mit Quellenangabe (allgemeine Kenntnis) | voraussichtlich geeignet |
| US-Finanzministerium | US-Zinskurve | `finanz_abruf.py` | nein | US-Behördendaten | voraussichtlich geeignet |
| OECD SDMX / Data Explorer | Prognosen, Inflation, Renditen | `vwl.py`-Zuträger, `finanz_makro.py`, `volkswirtschaft/skripte` | nein | seit 2024 überwiegend CC BY 4.0 (allgemeine Kenntnis); oecd.org-Seiten 403 | voraussichtlich geeignet |
| Weltbank | BIP, Schulden, Börsenwert/BIP | `welt_daten.py`, `finanz_makro.py` | nein | CC BY 4.0 (allgemeine Kenntnis) | voraussichtlich geeignet |
| Eurostat | Strom, Indikatoren, BIP je Einwohner in KKS je Kreis (NUTS-3) | `welt_daten.py`, `volkswirtschaft/skripte/abruf_regional.py` | nein | Wiederverwendung mit Quellenangabe | voraussichtlich geeignet |
| VGR der Länder (Statistische Ämter des Bundes und der Länder) | Kreisergebnisse: BIP, Bruttowertschöpfung, Erwerbstätige, Einwohner, Produktivität (400 Kreise, 2000 bis 2024) | `volkswirtschaft/skripte/abruf_regional.py` | nein | geprüft 11.11.: Impressum der Datei (Reihe 2 Band 1, [statistikportal.de](https://www.statistikportal.de/de/vgrdl/ergebnisse-kreisebene/bruttoinlandsprodukt-bruttowertschoepfung-kreise)): „Vervielfältigung und Verbreitung, auch auszugsweise, mit Quellenangabe gestattet.“ Erwerbstätige und Einwohner nur mit einer Nachkommastelle (in Tausend) weitergeben (das Skript rundet so) | geeignet mit Quellenangabe |
| BIS | Leitzinsen | `finanz_makro.py` | nein | sekundär 10.11. ([Bedingungen](https://www.bis.org/terms_statistics.htm), Seite 403): Nutzung uneingeschränkt, wenn die BIS als Quelle genannt wird, keine Billigung/Zugehörigkeit vorgetäuscht und nichts als Anlageberatung dargestellt wird; Leitzinsen zusätzlich mit nationaler Quelle | geeignet mit Namensnennung „BIS“ und Zentralbank |
| FRED (St. Louis Fed) | US-Reihen | `volkswirtschaft/skripte` | nein | je Reihe eigene Rechte Dritter | **prüfen je Reihe** |
| Zentralbanken, Institute, Konsensumfragen (Prognosen) | Prognosegeber | `volkswirtschaft/` (`PROGNOSEGEBER.md`) | nein | je Herausgeber | prüfen |
| CEPII BACI | Exporte je Gut | `gueter_baci.py` | nein | Repo: keine CC BY-NC-Quellen im Handelsbereich (Projektnotiz 09.11.2026); BACI unter Etalab-Lizenz (allgemeine Kenntnis) | voraussichtlich geeignet |
| UN Comtrade | Handelsströme | `handel_abruf.py` | Free-Tier ohne Schlüssel | sekundär 10.11.: Nutzungsvereinbarung ([Lizenz](https://comtrade.un.org/licenseagreement.html)) beschränkt Kopie, automatischen Abruf, Weiterverbreitung und kommerzielle Nutzung; Weiterverbreitung unveränderter Daten setzt laut UN-Shop ein Premium-Pro-Abo voraus; Anfragen an comtrade@un.org | **kritisch**: auf dem öffentlichen Server nur abgeleitete Kennzahlen oder BACI (Entscheidung E2) |
| ENTSO-E Transparency Platform | Stromflüsse je Grenze und Monat | `entsoe_abruf.py` | ja (`entsoe_api`, nur Server/Umgebung) | sekundär 10.11.: seit 2019 erlauben die aktualisierten Nutzungsbedingungen die freie Weiterverwendung eines Teils der Daten ([ENTSO-E 2019](https://www.entsoe.eu/news/2019/02/01/tsos-increase-number-of-open-data-available-through-entso-e-s-transparency-platform/), [Jahresbericht 2019](https://annualreport2019.entsoe.eu/transparency-regulation/)); übrige Daten nur nach Prüfung beim jeweiligen Netzbetreiber; Day-Ahead-Preise voraussichtlich nicht frei; genutzt werden nur physikalische Flüsse | **prüfen**: Liste der frei nutzbaren Datensätze in den Primärbedingungen bestätigen, bis dahin Namensnennung „ENTSO-E Transparency Platform“ |
| WTO | Zölle | `handel_wto.py` | nein | sekundär 10.11. ([Terms of Use](https://ttd.wto.org/docs/Terms_of_Use_WTO_Tariff_and_Trade_Data.pdf)): Veröffentlichung von Daten und Auswertungen erlaubt, wenn das WTO-Urheberrecht genannt wird; ältere TAO-Bedingungen: keine Weitergabe „for profit or commercial advantage“; WTO-Logo nicht verwenden | geeignet bei nicht kommerziellem Betrieb mit Nennung „© WTO“; kommerziell klären |
| Wikipedia | Häfen/Flughäfen-Rangfolgen, Parlamente | `verkehrsknoten.py`, `parlamente_daten.py` | nein | Repo: CC BY-SA 4.0 (Namensnennung, Weitergabe unter gleichen Bedingungen) | geeignet mit Namensnennung |
| Wikidata | Regierungen, Parteien | `parlamente_daten.py`, `politik_daten.py` | nein | Repo: CC0 | geeignet |
| IPU Parline | Parlamente, Sitzverteilung | `parlamente_daten.py` | nein | sekundär 10.11.: CC BY-NC-SA 4.0 ([Terms of Use](https://www.ipu.org/terms-use), [About](https://data.ipu.org/about), Seiten 403); Zitierform „Inter-Parliamentary Union: dataset_name, month_year“; Weitergabe nur unter derselben Lizenz und kostenfrei | **eingeschränkt**: nur bei nicht kommerziellem Betrieb, Teile mit IPU-Daten unter CC BY-NC-SA (Entscheidung E3) |
| Wahlbehörden (Bundeswahlleiterin, NRW, UK Parliament, Innenministerium FR, Elections Canada, AEC, BFS, BMI AT, Clerk of the House, BOE, Valgdirektoratet) | Wahlergebnisse | `wahlen_daten.py`, `wahlkreise_daten.py`, `kommunal_daten.py` | nein | Repo: teils angegeben (AEC CC BY 4.0, Statistik Austria CC BY 4.0, BKG dl-de/by-2-0) | je Behörde prüfen |
| Statistisches Landesamt Sachsen-Anhalt (Landtagswahl 2026) | Landtagswahl 06.09.2026: Land, 41 Wahlkreise, 14 Kreise, Sitze, Vergleich 2021; Grenzen der Wahlkreise | `landtagswahlen.py` | nein | geprüft 10.11.: Grenzen © GeoBasis-DE / LVermGeo ST, dl-de/by-2-0 (Angabe auf der [Wahlkreiskarte](https://wahlergebnisse.sachsen-anhalt.de/wahlen/lt26/karten_wkr.html)); Ergebnisdateien: amtliches Endergebnis, auf der [Downloadseite](https://wahlergebnisse.sachsen-anhalt.de/wahlen/lt26/downloads.html) ohne ausdrückliche Lizenzangabe | voraussichtlich geeignet mit Quellenangabe |
| Statistisches Landesamt Baden-Württemberg (Landtagswahl 2026) | Landtagswahl 08.03.2026: Land, 70 Wahlkreise, Gewählte, Veränderung zu 2021; Grenzen der Wahlkreise | `landtagswahlen.py` | nein | geprüft 11.11.: [Impressum der Wahlpräsentation](https://www.statistik-bw.de/info/impressum/wahlpraesentation/): Vervielfältigung und Verbreitung, auch auszugsweise, mit Quellenangabe gestattet; © Statistisches Landesamt Baden-Württemberg, Stuttgart 2026 | voraussichtlich geeignet mit Quellenangabe |
| Landeswahlleitung Berlin / Amt für Statistik Berlin-Brandenburg (Abgeordnetenhauswahl 2026) | Wahl 20.09.2026: Land, 78 Wahlkreise, Gewählte, Veränderung zu 2023; Grenzen der Wahlkreise | `landtagswahlen.py` | nein | geprüft 11.11.: [Impressum](https://www.wahlen-berlin.de/impressum.asp): Vervielfältigung und Verbreitung, auch auszugsweise, mit Quellenangabe gestattet; Rechte Dritter an einzelnen Dateien vorbehalten | voraussichtlich geeignet mit Quellenangabe |
| Landeswahlleiter Rheinland-Pfalz (Landtagswahl 2026) | Landtagswahl 22.03.2026: Land, 52 Wahlkreise, Gewählte, Landesvergleich 2021; Ergebnis der kreisfreien Städte Mainz, Ludwigshafen, Koblenz und Kaiserslautern | `landtagswahlen.py` | nein | geprüft 11.11.: weder [Ergebnisseite](https://www.wahlen.rlp.de/landtagswahl/ergebnisse) noch Impressum nennen eine Lizenz; amtliches Endergebnis. Grenzen seit 11.11.2026 nicht mehr aus dem Shape des Landeswahlleiters, sondern aus BKG VG250 und den Stadtbezirken Trier (E7) | voraussichtlich geeignet mit Quellenangabe (amtliche Ergebnisse) |
| Landeswahlleiter Mecklenburg-Vorpommern (Landtagswahl 2026) | Landtagswahl 20.09.2026: Land, 36 Wahlkreise, Mandate, Gewählte, Vergleich 2021; Ergebnis der Städte Schwerin, Neubrandenburg und Stralsund | `landtagswahlen.py` | nein | geprüft 11.11.: CSV mit Vermerk „(c) Der Landeswahlleiter Mecklenburg-Vorpommern“; amtliches Endergebnis. Grenzen seit 11.11.2026 aus BKG VG250 und den statistischen Bezirken Rostock statt aus dem Shape des Amtes für Geoinformation (E7) | voraussichtlich geeignet mit Quellenangabe (amtliche Ergebnisse) |
| Harvard Dataverse (MEDSL) | US-Wahlen | `wahlen_daten.py` | Token `Harvard_Database` (nur Server) | sekundär 10.11.: MEDSL-Datensätze auf Dataverse unter CC0 1.0 (Datensatzseiten, über Aggregator); Datensätze mit Gästebuch je Datensatz prüfen | voraussichtlich geeignet (CC0), Zitierempfehlung übernehmen |
| DAWUM | Umfragen | `politik_daten.py` | nein | geprüft 10.11.: ODC-ODbL ([API](https://dawum.de/API/)), Namensnennung „Daten von dawum.de (Open Database License (ODbL))“; abgeleitete veröffentlichte Datenbanken ebenfalls unter ODbL | geeignet mit Namensnennung; Weitergabe der Umfragetabelle unter ODbL |
| Natural Earth | Ländergrenzen | `app/geo/` | nein | gemeinfrei | geeignet |
| BKG (VG1000, VG250, Wahlkreise) | Kreise, Wahlkreise, Gemeinden (Landtagswahlkreise RP, MV) | `app/geo/` | nein | Repo: dl-de/by-2-0 | geeignet mit Namensnennung |
| Stadt Trier (Stadtbezirke), Hanse- und Universitätsstadt Rostock (statistische Bezirke) | Grenzen innerhalb der auf mehrere Landtagswahlkreise geteilten Städte | `landtagswahlen.py` (`STADTTEILE`) | nein | Trier: dl-de/by-2-0 ([Geoportal RLP](https://www.geoportal.rlp.de/spatial-objects/470)); Rostock: CC0 1.0 ([OpenData.HRO](https://geo.sv.rostock.de/download/opendata/statistische_bezirke/)) | geeignet mit Namensnennung (Trier) |
| OpenFreeMap / OpenMapTiles / OSM | Kartenkacheln im Browser | `globus.js` | nein | OSM ODbL, Kacheln kostenlos | geeignet; bei Wachstum eigene PMTiles erwägen |
| OurAirports, UN/LOCODE | Verkehrsknoten | `verkehrsknoten.py` | nein | Repo: OurAirports gemeinfrei | geeignet |
| EMODnet | Schiffsdichte | Konzept Handelsrouten | nein | Repo: CC BY | geeignet mit Namensnennung |
| Google News RSS | Störungsmeldungen | `news_routen.py` | nein | Inhalte Dritter (Verlage); Google-Nutzungsbedingungen | **kritisch**: nur Überschrift und Link anzeigen, keine Texte speichern (Entscheidung E4) |
| GDELT (Original-Datensätze) | Störungsmeldungen | `news_routen.py` | nein | sekundär 10.11.: „unlimited and unrestricted use for any academic, commercial, or governmental use of any kind without fee“, Weitergabe mit Zitat und Link; GDELT Cloud hat abweichende Bedingungen | geeignet mit Zitat und Link (nicht GDELT Cloud); verlinkte Artikel bleiben Inhalte Dritter |
| get.geojs.io | Land des Besuchers (Weltkugel, Knopf „per IP“) | `globus.js` | nein | Dritter erhält die IP des Besuchers | erledigt: Voreinstellung aus Zeitzone und Browsersprache; die IP-Abfrage läuft nur auf Knopfdruck und wird vorher erklärt |

## Entscheidungen vor dem öffentlichen Betrieb (Robin)

Lizenzfragen sind laut Master-Auftrag zustimmungspflichtig. Bis zur Entscheidung läuft nichts davon öffentlich; GitHub Pages
und der lokale Betrieb bleiben, wie sie sind.

| Nr. | Frage | Betroffen | Vorschlag |
|---|---|---|---|
| E1 | Kurse und Konzernkennzahlen aus Yahoo auf sphaerae.de | MKT, Börse & Finanzen (Kurse, Verläufe, Indizes), Korrelation mit Kursen, Kurse in Profilen | Auf dem öffentlichen Server ausblenden (Schalter im Build, Hinweis „nur lokal“), bis eine freie Quelle oder Vereinbarung vorliegt; Zinsen, Wechselkurse, Renditen kommen schon aus EZB/OECD/BIS |
| E2 | Handelsströme aus UN Comtrade | HDL F2/F3, Handel auf der Weltkugel | Rohdaten nicht ausliefern; Länderströme aus CEPII BACI (Etalab 2.0) berechnen, die schon für die Güter genutzt wird |
| E3 | IPU Parline (CC BY-NC-SA) | Parlamente, Sitzverteilungen | Nutzen, solange sphaerae.de nicht kommerziell ist (keine Werbung, keine Bezahlfunktionen); Quellenvermerk mit Lizenz an der Ansicht; bei Kommerzialisierung durch Wikidata/Wahlbehörden ersetzen |
| E4 | Google News RSS | Störungsmeldungen an Engstellen | Nur Überschrift, Quelle, Datum und Link; keine Volltexte, nichts dauerhaft speichern |
| E5 | Originaldokumente (Geschäftsberichte als PDF) | Dokumentlisten im Profil | Auf dem Server verlinken (Fundstelle beim Unternehmen bzw. Bundesanzeiger) statt die PDFs selbst auszuliefern |

Umsetzung E1: `python3 app/build.py --nur-seite --api /api/v1 --oeffentlich --ziel dist-api` baut die Server-Fassung ohne Yahoo-Daten (Marktdaten, Wochenkurse, Börsenbereich, Kurs- und Bewertungswerte der Unternehmen, Yahoo-Einträge im Finanzpuls; `build.py: YAHOO_WERTE`). **Entschieden (Robin, 10.11.2026): ausblenden.** Seit dann schaltet `--api` den Schalter immer ein (lokal abschaltbar mit `--mit-yahoo`), und der Import in die Server-Datenbank (`server/etl/profile.py`) übernimmt die Yahoo-Kennzahlen nicht (`server/plattform/lizenz.py`; für eine lokale Datenbank `SPHAERAE_MIT_YAHOO=1`).

Schutz der fertigen Ausgabe: `python3 -m plattform.lizenz ../app/dist-api` (aus `server/`) durchsucht den Build nach Yahoo-Dateien,
-Blöcken und -Werten und bricht bei einem Fund ab; der Workflow `server.yml` führt die Prüfung nach jedem Build aus. `--mit-yahoo`
ist für Server-Ordner gesperrt, `SPHAERAE_MIT_YAHOO=1` bricht in Produktion (`PLATTFORM_UMGEBUNG=produktion`) ab.

**E6 (neu, offen):** E1 sperrt Kurse und Bewertungswerte. Die Abschlusszahlen von Nichtbanken stammen aber ebenfalls aus Yahoo:
4.457 von 4.664 Abschlüssen, 11.727 daraus gerechnete Kennzahlenwerte, Berichtstermine von 155 Unternehmen. Empfehlung: auf
sphaerae.de ebenfalls sperren, bis die Zahlen aus Originalquellen (ESEF, SEC, DART) kommen. Schalter: Build
`--ohne-yahoo-abschluesse`, ETL `SPHAERAE_OHNE_YAHOO_ABSCHLUESSE=1`, Prüfung `--streng`. Stand: aus, bis Robin entscheidet.

**E7 (entschieden 11.11.2026):** Die Wahlkreisgrenzen der Landtagswahlen Rheinland-Pfalz und Mecklenburg-Vorpommern werden nicht mehr
aus den Shapes der Landeswahlleitungen (ohne Lizenz) gebaut, sondern aus den Gemeinden der BKG-Verwaltungsgebiete VG250 (dl-de/by-2-0)
zusammengesetzt (`landtagswahlen.wk_aus_gemeinden`). Die Zuordnung Gemeinde → Wahlkreis steht in `wahlen/quellen/<rp|mv>_ltw26_gemeinden_wahlkreise.csv`
(ermittelt durch Verschneiden mit der amtlichen Einteilung; 3 024 Gemeinden). Neun Städte sind auf mehrere Wahlkreise geteilt. Für Trier
(Stadtbezirke, dl-de/by-2-0) und Rostock (statistische Bezirke, CC0) gibt es offene Stadtteilgrenzen; in Rostock folgen die Wahlkreise nicht
genau den Bezirken, die Fläche weicht dort je Wahlkreis um bis zu 11 % ab (Trier unter 1 %). Mainz, Ludwigshafen, Koblenz, Kaiserslautern,
Schwerin, Neubrandenburg und Stralsund stehen als ein Gebiet mit dem amtlichen Ergebnis der Stadt auf der Karte (Schlüssel `S` + Gemeindeschlüssel).
Außerhalb dieser Städte weichen die Flächen um höchstens 0,7 % (RP) bzw. 3,4 % (MV) von der amtlichen Einteilung ab (Vereinfachung, Küstengewässer).

ENTSO-E: Abruf über 36 Monate in Fenstern von höchstens einem Jahr; Monate mit weniger als 99,5 % der Stunden sind in
`strom_entsoe.json` unter `abdeckung` vermerkt.

## Pflichtangaben (Namensnennung) für die Seite „Quellen“

Wikipedia (CC BY-SA 4.0, mit Link zum Artikel), DAWUM (ODbL), BKG (dl-de/by-2-0, „© GeoBasis-DE / BKG“), AEC und Statistik
Austria (CC BY 4.0), EMODnet (CC BY), OpenStreetMap/OpenMapTiles (ODbL, „© OpenStreetMap-Mitwirkende“), Weltbank und OECD
(CC BY 4.0), BIS mit nationaler Zentralbank, WTO („© WTO“), IPU („Inter-Parliamentary Union: dataset, Monat Jahr“, CC BY-NC-SA 4.0),
GDELT (Zitat und Link), CEPII BACI (Etalab 2.0), VGR der Länder („Statistische Ämter des Bundes und der Länder, VGRdL“). Die vorhandene Fußleiste (`app/seiten/`) ist der Ort dafür.

Für jede Quelle noch zu ergänzen: Aktualisierungstakt, Nutzungsgrenzen (Rate Limits), typische Fehler, nicht erhobene Felder;
die mit „sekundär“ oder „allgemeine Kenntnis“ markierten Zeilen beim Herausgeber nachlesen, sobald die Seiten erreichbar sind.
Dieser Katalog steht seit P3.1 als Tabelle `data_source` in der Datenbank und unter `/api/v1/data-catalog` (ETL `server/etl/katalog.py`). Die Texte der Tabelle oben sind die Quelle; `server/katalog/datenquellen.csv` ergänzt je Zeile Kennung, Bereich, Status, Entscheidung, Pflichtangabe und Aliase. Eine neue Zeile hier braucht eine Zeile dort (gleicher Name in der Spalte `quelle`), sonst bricht der Import ab.
