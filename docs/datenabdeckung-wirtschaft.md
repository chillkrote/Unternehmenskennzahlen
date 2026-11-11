# Datenabdeckung Wirtschaft

Stand 11.11.2026. Gegenstück zu `docs/datenabdeckung-wahlen.md`: welche Wirtschafts-, Energie- und Handelsdaten es auf welcher
geografischen Ebene gibt, wie weit sie reichen und wie weit sie eingebunden sind. Zahlen aus den Dateien des Repos
(`volkswirtschaft/`, `volkswirtschaft/regional/`, `app/data/`); Stand der Server-Datenbank laut `GET /api/v1/data-quality`.

## Stufen der Einbindung

| Stufe | Bedeutung |
|---|---|
| Code | Abrufskript und Datei vorhanden |
| Test | automatische Tests (Berechnung, Import, API) |
| Primär | fachlich gegen die Primärquelle oder eine unabhängige Summe geprüft |
| Oberfläche | im Terminal oder auf der Weltkugel nutzbar |
| Server | in PostgreSQL und über `/api/v1` abrufbar |

## Stand je Ebene und Bereich

| Ebene | Bereich | Quelle | Umfang | Zeitraum | Code | Test | Primär | Oberfläche | Server |
|---|---|---|---|---|---|---|---|---|---|
| Staaten (Europa) | Konjunktur: BIP, Verwendung, HVPI, Arbeitsmarkt, Produktion, Stimmung, Staatsfinanzen | Eurostat | 27 Reihen, 29 Gebiete | 2005 bis 2026-Q3 | ja | ja | teilweise (Prognoseabgleich) | ja | ja (`/series`) |
| Staaten (OECD) | Konjunktur, Economic Outlook mit Projektionen | OECD | 28 Reihen, 42 Gebiete | 2000 bis 2027 (Projektion) | ja | ja | teilweise | ja | ja |
| Staaten (Welt) | BIP, Inflation, Arbeitslosigkeit, Leistungsbilanz, Schulden, Handel/BIP, FDI, Zölle | Weltbank (`welt.json`) | 13 Kennzahlen, 215 Länder | Jahreswerte | ja | teilweise | nein | ja (Weltkugel) | nein (Datei) |
| Staaten | Finanzmarkt-Makro (Realzins, Aufschläge, Bankensektor) | EZB, BIS, OECD (`finanz_makro.json`) | | | ja | ja | nein | ja | nein (Datei) |
| Staaten | Prognosen (Institute, OECD, Konsens, Zentralbanken) mit Treffsicherheit | Herausgeber | 38 OECD-Länder | 2015 bis 2028 | ja | ja | ja (Primärdokumente, siehe `beleg`) | ja | Datei (`vwl_prognosen.json`) |
| Staaten | Warenhandel bilateral | UN Comtrade (`handel.json`) | 167 Meldeländer | letztes Meldejahr | ja | ja | nein | ja | nein; Lizenz **kritisch** (E2) |
| Staaten | Exporte und Importe je Gut, HHI, Abhängigkeiten | CEPII BACI | 22 Gütergruppen, 226 Länder | 2015 bis 2024 | ja | ja | nein | ja (HDL F5, Weltkugel) | ja (`/trade`) |
| Grenzen | Physische Stromflüsse je Grenze und Richtung | ENTSO-E | 136 Richtungen, monatlich | 2023-11 bis 2026-10; 44 Monate teilweise | ja | ja | nein | ja (HDL F4, Weltkugel) | nein (Datei); Repo-Secret `ENTSOE_API_KEY` fehlt |
| Orte | Häfen und Flughäfen | Betreiber, OurAirports, EMODnet | 58 Seehäfen, 53 Flughäfen | letztes Jahr | ja | teilweise | nein | ja | nein |
| **Kreise (NUTS-3, DE)** | **BIP, Wachstum, BIP je Einwohner/Erwerbstätigen/Arbeitsstunde, Einwohner, Erwerbstätige, Bruttowertschöpfung und Struktur** | **VGR der Länder** (Primärquelle), Eurostat (KKS-Index) | **12 Reihen (VGRdL) + KKS-Index (Eurostat), 400 Kreise** | **2000 bis 2024** | ja | ja | ja (Summe der Kreise = Bundes-BIP; Abgleich mit Eurostat) | ja (Weltkugel, Volkswirtschaft) | ja (`/regions`, `/series?level=nuts3`) |
| Kreise (DE) | Verknüpfung mit Wahlergebnissen je Kreis | Wahlregister + VGRdL | Europawahl 2024 (400 Kreise), Landtagswahl Sachsen-Anhalt 2026 (14 Kreise) | | ja | ja (Browsertest) | ja (Statistik wie KOR.stat) | ja („Wirtschaft und Wahl“) | Wirtschaft ja, Wahlen nein |
| Länder (NUTS-1/2) | BIP, Arbeitsmarkt der Bundesländer und Regionen | VGRdL / Eurostat | – | – | nein | – | – | – | – |
| Gemeinden | Steuerkraft, Beschäftigte am Arbeitsort, Arbeitslose | Regionaldatenbank, BA | – | – | nein | – | – | – | – |
| Kreise (EU) | BIP und Bevölkerung NUTS-3 aller EU-Staaten | Eurostat | rund 1 150 Regionen | 2000 bis 2023 | Abruf vorbereitet (nur DE eingelesen) | – | – | – | – |

## Befund: Kreiswerte bei Eurostat und bei den Statistischen Ämtern

Die Kreisergebnisse der VGR der Länder (Ausgabe September 2026, Revision 2024, Berechnungsstand August 2025) reichen bis 2024.
Eurostat (`nama_10r_3gdp`, Stand 10.02.2026) reicht nur bis 2023. Die Summe über alle 400 Kreise ist in beiden Quellen gleich dem
Bundes-BIP (2023: 4 219 310 Mio. €), die Verteilung auf die Kreise aber nicht: in 2023 liegt der Median der Abweichung bei −0,3 %,
einzelne Kreise weichen um bis zu 36 % ab (`volkswirtschaft/regional/abgleich_eurostat.csv`, nur Abweichungen über 1 %, 1 349
Kreisjahre). Am stärksten: Mainz 2023 (VGRdL 14,5 Mrd. €, Eurostat 19,7 Mrd. €), Landkreis Erlangen-Höchstadt 2022/2023 (−31 %/−26 %).
Deshalb gilt für deutsche Kreise die VGRdL-Datei als Primärquelle; Eurostat liefert nur das BIP je Einwohner in Kaufkraftstandards
(EU-27 = 100) für den europäischen Vergleich.

## Nächste Lücken (Reihenfolge)

1. Wahlergebnisse in die Datenbank (Tabelle je Wahl, Einheit und Partei mit Kreisschlüssel), damit `/regions/cross-section` auch
   Wahlanteile rechnen kann; bisher verknüpft nur die Oberfläche.
2. Bundestagswahl 2025 und Landtagswahlen je Kreis (die Bundestagswahl liegt nur je Wahlkreis vor; Kreisergebnisse der
   Bundeswahlleiterin einlesen).
3. Arbeitslosenquote je Kreis (Bundesagentur für Arbeit, monatlich) und verfügbares Einkommen je Einwohner (VGRdL Reihe 2 Band 3).
4. NUTS-3 der übrigen EU-Staaten (Eurostat; Grenzen GISCO, Lizenz prüfen).
5. ENTSO-E: Repo-Secret `ENTSOE_API_KEY` anlegen, damit der Workflow die Stromflüsse fortschreibt.
