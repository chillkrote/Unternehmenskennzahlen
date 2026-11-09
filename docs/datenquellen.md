# Datenquellenverzeichnis (Arbeitsstand)

Stand 09.11.2026. Erste Fassung aus dem Code (`app/*.py`, `international/*.py`, `volkswirtschaft/`, `termine/`) und den
vorhandenen Notizen (`app/OFFENE_DATENFELDER.md`, `app/KONZEPT_Handelsrouten.md`, `international/LUECKEN.md`).
**Die Spalte „Lizenz“ ist nicht am einzelnen Datensatz geprüft**, außer wo „Repo“ steht (dort im Projekt dokumentiert). Vor der
öffentlichen Weiterverbreitung über den eigenen Server wird jede Zeile geprüft (Paket B2); bis dahin gilt keine Lizenz als geeignet.

| Quelle | genutzt für | Abruf (Skript) | Schlüssel | Lizenz / Weiterverbreitung | Bewertung |
|---|---|---|---|---|---|
| Unternehmensberichte (HGB/IFRS, PDF), Bank-Websites, Lobbyregister | Bilanzvergleich, Zeitreihen, Dokumente | Handarbeit, Crawler (`banken/…/skripte`, `termine/`) | nein | Veröffentlichungspflicht; Weitergabe der Originaldokumente urheberrechtlich zu prüfen | prüfen |
| EBA Pillar-3-Hub | Kapital, RWA (Banken) | Export über Browser (Repo-Notiz) | nein | ungeprüft | prüfen |
| GLEIF | LEI, Sitz, Register-Nr. | `api.gleif.org` (mehrere Skripte) | nein | allgemein bekannt CC0 | voraussichtlich geeignet |
| SEC EDGAR (Companyfacts) | US-/FPI-Abschlüsse | `international/sec.py` | User-Agent mit Kontakt | US-Behördendaten | voraussichtlich geeignet |
| filings.xbrl.org (ESEF) | EU-Abschlüsse | `international/esef.py` | nein | Repo: „Lizenz ungeprüft“ (`international/README.md`) | prüfen |
| OpenDART (Südkorea) | KR-Abschlüsse | `international/dart.py` | `DART_API` (nur Server) | ungeprüft | prüfen |
| Yahoo Finance (yfinance) | Kurse, Konzernkennzahlen, Live-Werte | `marktdaten.py`, `boersen_abruf.py`, `kurse_historie.py`, `finanz_abruf.py`, `live_abruf.py`, `termine/` | nein | Nutzungsbedingungen erlauben keine Weiterverbreitung ohne Vereinbarung (allgemeine Kenntnis) | **kritisch** für öffentlichen Server; Alternativen: Börsen-/Zentralbankdaten, EZB, eigene Berechnung aus frei lizenzierten Reihen |
| EZB Data Portal | Wechselkurse, Zinskurven, CISS, Bankensektor | `finanz_abruf.py`, `finanz_makro.py` | nein | Wiederverwendung mit Quellenangabe (allgemeine Kenntnis) | voraussichtlich geeignet |
| US-Finanzministerium | US-Zinskurve | `finanz_abruf.py` | nein | US-Behördendaten | voraussichtlich geeignet |
| OECD SDMX / Data Explorer | Prognosen, Inflation, Renditen | `vwl.py`-Zuträger, `finanz_makro.py`, `volkswirtschaft/skripte` | nein | seit 2024 überwiegend CC BY 4.0 (allgemeine Kenntnis); oecd.org-Seiten 403 | voraussichtlich geeignet |
| Weltbank | BIP, Schulden, Börsenwert/BIP | `welt_daten.py`, `finanz_makro.py` | nein | CC BY 4.0 (allgemeine Kenntnis) | voraussichtlich geeignet |
| Eurostat | Strom, Indikatoren | `welt_daten.py` | nein | Wiederverwendung mit Quellenangabe | voraussichtlich geeignet |
| BIS | Leitzinsen | `finanz_makro.py` | nein | eigene Bedingungen | prüfen |
| FRED (St. Louis Fed) | US-Reihen | `volkswirtschaft/skripte` | nein | je Reihe eigene Rechte Dritter | **prüfen je Reihe** |
| Zentralbanken, Institute, Konsensumfragen (Prognosen) | Prognosegeber | `volkswirtschaft/` (`PROGNOSEGEBER.md`) | nein | je Herausgeber | prüfen |
| CEPII BACI | Exporte je Gut | `gueter_baci.py` | nein | Repo: keine CC BY-NC-Quellen im Handelsbereich (Projektnotiz 09.11.2026); BACI unter Etalab-Lizenz (allgemeine Kenntnis) | voraussichtlich geeignet |
| UN Comtrade | Handelsströme | `handel_abruf.py` | Free-Tier ohne Schlüssel | Nutzungsbedingungen beschränken Weitergabe von Massendaten (allgemeine Kenntnis) | **prüfen** |
| WTO | Zölle | `handel_wto.py` | nein | ungeprüft | prüfen |
| Wikipedia | Häfen/Flughäfen-Rangfolgen, Parlamente | `verkehrsknoten.py`, `parlamente_daten.py` | nein | Repo: CC BY-SA 4.0 (Namensnennung, Weitergabe unter gleichen Bedingungen) | geeignet mit Namensnennung |
| Wikidata | Regierungen, Parteien | `parlamente_daten.py`, `politik_daten.py` | nein | Repo: CC0 | geeignet |
| IPU Parline | Parlamente, Sitzverteilung | `parlamente_daten.py` | nein | Repo: CC BY-NC-SA 4.0 (nicht kommerziell) | **eingeschränkt**: nur bei nicht kommerziellem Betrieb |
| Wahlbehörden (Bundeswahlleiterin, NRW, UK Parliament, Innenministerium FR, Elections Canada, AEC, BFS, BMI AT, Clerk of the House, BOE, Valgdirektoratet) | Wahlergebnisse | `wahlen_daten.py`, `wahlkreise_daten.py`, `kommunal_daten.py` | nein | Repo: teils angegeben (AEC CC BY 4.0, Statistik Austria CC BY 4.0, BKG dl-de/by-2-0) | je Behörde prüfen |
| Harvard Dataverse (MEDSL) | US-Wahlen | `wahlen_daten.py` | Token `Harvard_Database` (nur Server) | je Datensatz | prüfen |
| DAWUM | Umfragen | `politik_daten.py` | nein | ungeprüft | prüfen |
| Natural Earth | Ländergrenzen | `app/geo/` | nein | gemeinfrei | geeignet |
| BKG (VG1000, Wahlkreise) | Kreise, Wahlkreise | `app/geo/` | nein | Repo: dl-de/by-2-0 | geeignet mit Namensnennung |
| OpenFreeMap / OpenMapTiles / OSM | Kartenkacheln im Browser | `globus.js` | nein | OSM ODbL, Kacheln kostenlos | geeignet; bei Wachstum eigene PMTiles erwägen |
| OurAirports, UN/LOCODE | Verkehrsknoten | `verkehrsknoten.py` | nein | Repo: OurAirports gemeinfrei | geeignet |
| EMODnet | Schiffsdichte | Konzept Handelsrouten | nein | Repo: CC BY | geeignet mit Namensnennung |
| Google News RSS, GDELT | Störungsmeldungen | `news_routen.py` | nein | Inhalte Dritter; nur Überschriften und Links | **kritisch**: nur verlinken, nicht speichern |
| get.geojs.io | Land des Besuchers beim Start der Weltkugel (Browser) | `globus.js` | nein | Dritter erhält die IP des Besuchers | **ersetzen** auf dem eigenen Server (z. B. Sprache/Zeitzone des Browsers) |

Für jede Quelle noch zu ergänzen (B2): Aktualisierungstakt, Nutzungsgrenzen (Rate Limits), typische Fehler, nicht erhobene Felder.
Dieser Katalog wird in Paket P3.1 als Tabelle `data_source` in die Datenbank übernommen und über `/api/v1/data-catalog` ausgeliefert.
