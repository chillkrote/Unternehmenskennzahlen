# Offene Datenfelder der Weltkugel

Stand 04.11.2026 (nach dem Bau von Börse, Unternehmen und Politik). Hier steht, welche Daten die fünf Darstellungsformen der Weltkugel (Handel, Volkswirtschaft, Börse & Finanzen, Unternehmen, Politik & Wahlen) noch nicht haben und warum. Regel des Projekts: nur kostenlose Quellen ohne Bezahlschranke. Ein Feld bleibt offen, solange es keine solche Quelle gibt oder die Quelle einen (kostenlosen) Schlüssel braucht, den wir noch nicht eingerichtet haben.

Spalte "Weg" sagt, was zum Schließen nötig wäre.

## Handel

| Feld | Stand jetzt | Warum offen | Weg |
|---|---|---|---|
| Aktuelle Sonderzölle (z. B. US-Zölle seit 2025, Gegenzölle) je Land und Partner | Weltbank-Durchschnitt aller Waren (jüngstes Jahr meist 2021 bis 2023); für die USA zusätzlich die effektive Zollbelastung je Quartal aus FRED | WTO-Zolldaten (Tariff & Trade Data API) brauchen einen kostenlosen Schlüssel; bilaterale Sonderzölle gibt es nirgends als offene Tabelle | WTO-API-Schlüssel anlegen (kostenlos, api.wto.org) und als Secret hinterlegen; Sonderzölle der großen Länder von Hand in einer CSV mit Quelle pflegen |
| Handelsströme zu allen Nachbarn | UN Comtrade, je Land die 15 größten Partner | Volle Partnerlisten nur über die Comtrade-API mit Schlüssel (kostenlos, aber Tageslimit) | Comtrade-Schlüssel (kostenlos) als Secret; Abruf der vollen Matrix einmal je Jahr |
| Stromhandel außerhalb Europas | Eurostat bilateral (europäische Meldeländer), sonst Nettosaldo je Land (Ember) | ENTSO-E braucht ein Token, EIA (USA/Kanada/Mexiko) einen Schlüssel, für Asien, Afrika, Südamerika keine freie bilaterale Quelle | EIA-Schlüssel und ENTSO-E-Token (beide kostenlos) beantragen |
| Verkehrsmengen auf den Routen (Schiffe je Tag, TEU, Bahncontainer) | Routen und Engstellen ohne Mengen | IMF PortWatch erlaubt die Weiterverwendung nur mit Genehmigung; Bahn- und Lkw-Mengen nirgends offen | Bei IMF PortWatch die Nutzung anfragen |
| Meldungen zu Routenstörungen in anderen Sprachen | Englisch und Deutsch | Bewusst begrenzt, damit die Titelprüfung (Ort + Störungswort) verlässlich bleibt | Störungswörter je Sprache in app/news_routen.py ergänzen |

## Volkswirtschaft

| Feld | Stand jetzt | Warum offen | Weg |
|---|---|---|---|
| Prognosen für alle Länder (BIP, Inflation) | Prognosegeber der OECD-Länder (eigener Bereich) | IMF World Economic Outlook: Lizenz erlaubt keine Weiterverbreitung ohne Zustimmung | IMF um Zustimmung bitten oder bei OECD-Ländern bleiben |
| Staatsschulden für Länder ohne Weltbank-Wert (z. B. Nigeria) | Weltbank GC.DOD.TOTL.GD.ZS, Lücken | Reihe der Zentralregierung fehlt für viele Länder | IMF Global Debt Database prüfen (Lizenz) |
| Monatswerte außerhalb Europas und der OECD | Jahreswerte der Weltbank | Keine gemeinsame freie Monatsquelle | Nationale Statistikämter einzeln anbinden |

## Börse & Finanzen

| Feld | Stand jetzt | Warum offen | Weg |
|---|---|---|---|
| Rendite zehnjähriger Staatsanleihen außerhalb der OECD | 47 Länder (OECD, monatlich) | Keine freie gemeinsame Quelle | Zentralbanken einzeln |
| Leitzinsen | 40 Zentralbanken (BIS) | BIS deckt nicht alle Länder ab | Zentralbanken einzeln |
| Goldpreis | fehlt | LBMA-Preise ohne Schlüssel nicht frei; FRED führt die Reihe nicht mehr | Quelle mit freier Lizenz suchen |
| Kursentwicklung je Unternehmen außerhalb des Terminals | nur Unternehmen mit Wochenkursen im Terminal (Stufe 3 farbig) | Kurse für die übrigen rund 30.000 Unternehmen fehlen | Kursabruf schrittweise erweitern |
| Banken mit Bilanzsumme und Kernkapitalquote außerhalb Deutschlands | nur deutsche Banken (Bankenvergleich) | Pillar-3-Daten anderer Länder nicht erhoben | EBA-Transparenzübung (EU) prüfen |
| Lage der Börsenplätze | Stadtmitte, von Hand (app/geo/boersenplaetze.csv) | Wikidata hat nicht für alle Börsen Koordinaten | Wikidata ergänzen |
| Kreditausfallprämien (CDS) | nicht vorgesehen | nur kostenpflichtig | entfällt |

## Unternehmen

| Feld | Stand jetzt | Warum offen | Weg |
|---|---|---|---|
| Koordinaten der Firmensitze | rund 9.200 Unternehmen mit Ort auf der Karte | Rund 22.600 Unternehmen nur mit Land (Entscheidung 03.11.2026: später) | Geokodierung über Wikidata bzw. OpenStreetMap Nominatim (frei, langsam) |
| Größenfilter (Umsatz, Mitarbeiter) | nur Filter „mit Kennzahlen“ | Umsatz nur für Unternehmen mit Kennzahlen im Terminal | Kennzahlen schrittweise erweitern |
| Börsenwert je Land | nur die 232 großen Unternehmen des Bereichs BÖR | Börsenwert der übrigen fehlt | mit dem Kursabruf erweitern |
| Lieferketten und Beteiligungen | Beispiel Volkswagen (stammdaten/beziehungen) | Keine freie strukturierte Quelle; Geschäftsberichte von Hand | Schrittweise je Unternehmen erfassen |

## Politik & Wahlen

| Feld | Stand jetzt | Warum offen | Weg |
|---|---|---|---|
| Ausrichtung der Regierung | Wikidata-Angabe der Partei (196 Staaten, 77 ohne Zuordnung) | Wikidata lückenhaft, Parteien ohne Angabe (z. B. PT Brasilien) | ParlGov (EU/OECD, CC BY-SA) oder V-Dem prüfen |
| Wahltermine | nationale Wahlen aus Wikipedia (42 Länder in 12 Monaten) | Landtags- und Regionalwahlen fehlen | Wikipedia-Listen je Land oder Wikidata, wenn die Abfrage schneller wird |
| Kabinettsmitglieder | fehlt (nur Regierungschef und Staatsoberhaupt) | Wikidata führt Kabinette uneinheitlich | Wikidata „Mitglied von“ Kabinett prüfen |
| Heutige Sitzverteilung nationaler Kammern | 187 von 281 Kammern aus der Wikipedia-Infobox, 47 nur mit dem Ergebnis der letzten Wahl (IPU Parline), 47 ohne Sitzverteilung (Stand Abruf 04.11.2026) | Infoboxen von UK, Kanada, Australien u. a. bestehen aus Vorlagen ({{… political groups}}), Irland aus Wikidata-Abfragen; ernannte Kammern (House of Lords, Bundesrat, Senat Kanada) und Staaten ohne gewähltes Parlament (Afghanistan, Militärregierungen in Westafrika) haben bei IPU kein Wahlergebnis | Vorlagen über die Wikipedia-API auflösen, wenn sie aus der Cloud nicht mehr drosselt (429); ernannte Kammern von Hand pflegen |
| Regierungslager je Kammer | nur, wo die Infobox Regierung/Opposition (oder Mehrheit/Minderheit) trennt, sonst Regierungsparteien laut IPU als Text | keine einheitliche Quelle | ParlGov (EU/OECD) prüfen |
| Stimmenanteile der letzten Wahl | 142 nationale Kammern, Gliedstaaten teilweise; nur die größten Parteien der Infobox | Infobox des Wahlartikels zeigt nur die Hauptparteien | amtliche Ergebnisse je Land (Wahlbehörden) schrittweise |
| Ergebnis kurz nach einer Wahl | IPU trägt Ergebnisse mit Tagen bis Wochen Verzug nach; Wikipedia vorläufig | Quellen hinken nach | Hinweis „gerade gewählt“ sagt, ob das Ergebnis schon in der Quelle steht (Schwelle 30 Tage) |
| Gliedstaaten | 499 Gliedstaaten in 26 Bundesstaaten; 439 von 683 Kammern (national und Gliedstaaten) mit heutiger Sitzverteilung | Ohne auswertbare Infobox: Brasilien (21 von 27), Kanada (7 von 13), Mexiko (24 von 28), Schweiz (14 von 21), Nigeria fast alle, Venezuela, Malaysia (14 von 16), Äthiopien, Irak, Nepal, Somalia, Sudan, Südsudan, Komoren, Mikronesien, VAE (keine Parlamentsartikel in Wikidata) | Wikidata P194 der Gliedstaaten ergänzen, Infoboxen in den Landessprachen (pt/es/de-Wikipedia) auswerten |
| Regierungschefs der Gliedstaaten | Amtsantritt jetzt ergänzt (USA 55 von 56, Kanada 12 von 13, Mexiko 15 von 32 mit Datum); fehlen u. a. für Schweiz (Kantone mit Kollegialregierung), Irak, Nepal, Somalia, Sudan | Wikidata P6 nicht gesetzt oder Kollegialorgan | von Hand oder über de-Wikipedia |
| Regionalstaaten (Frankreich, Italien, Spanien, Niederlande, Schweden, Norwegen, Dänemark, Finnland) | Neu 04.11.2026 im Reiter Gliedstaaten (F5): Frankreich 22 Regionen und Überseegebiete (20 mit Regierungschef, 17 mit Sitzverteilung), Italien 20 Regionen (19 / 20), Spanien 19 Autonome Gemeinschaften (18 / 17), Niederlande 12 Provinzen (12 / 7), Dänemark 5 Regionen plus Grönland und Färöer (7 / 2), Schweden 21 Läns (21 / 0), Norwegen 14 Fylker (14 / 0), Finnland nur Åland (1 / 0). Regierungschef mit Amtsantritt (Wikidata P6 + P580), Regierungslager aus der Wikipedia-Infobox, letzte und nächste Wahl | Frankreich: Départements fehlen (nur Regionen); ARA, Saint-Martin, Saint-Barthélemy ohne Regierungschef in Wikidata; Guadeloupe, Réunion, Mayotte, Neukaledonien ohne auswertbare Parlaments-Infobox. Niederlande: Friesland und Overijssel ohne Infobox. Schweden und Norwegen: Wikidata führt Landshövding (staatlich ernannt) bzw. Fylkesordfører, nicht die gewählte Regionsregierung; Regionsparlamente ohne Wikipedia-Infobox. Finnland: Wohlfahrtsgebiete und Landschaften haben keine gewählte Regierung (nur Åland). Island: keine Regionalebene mit Regierung, entfällt. Karte: Natural Earth hat für FR, IT, ES und NO Départements, Provinzen bzw. alte Kreise; diese werden in `geo()` (braucht einmalig `pip install shapely`) über Wikidata P131 zu den heutigen Regionen vereinigt (Norwegen von Hand, Stand der Kreisgrenzen vor 2020 mit Anpassung an die Aufteilung 2024). Ohne Fläche: Neukaledonien, Französisch-Polynesien, Saint-Pierre und Miquelon, Wallis und Futuna, Grönland, Färöer, Åland | Feinere Umrisse aus amtlichen Quellen (IGN ADMIN EXPRESS, ISTAT, IGN España, Kartverket); Regionsregierungen SE/NO von Hand oder über sv/no-Wikipedia; Départements als zweite Ebene ergänzen |
| Parteizuordnung der Regierungschefs | Wikidata P102 ohne Enddatum | Teils veraltet (z. B. Abruzzen: Marsilio bei „The People of Freedom“, Friaul: „Lega Nord“; Niederlande: Kommissare ohne Partei) | Parteiangabe aus Regierungslager der Infobox gegenprüfen |
| Wahlen in Regionalstaaten, Landtage Spanien/Italien/Frankreich | nächste Wahl nur, wo die Infobox sie nennt (Frankreich 2 von 22, Spanien 4 von 19, Niederlande 0 von 12) | Infoboxen pflegen das Feld nicht durchgängig | Wikipedia-Listen „regional elections“ je Land oder amtliche Wahlkalender
| Umfragen außerhalb Deutschlands | fehlt | Keine freie Quelle mit klarer Lizenz | je Land prüfen |
| Sanktionen, Konflikte (Variante 1C) | nicht gebaut | eigener Schritt laut Freigabe | EU-Sanktionsliste, OFAC, UCDP |

## Schon eingebunden (zum Vergleich)

- Weltbank World Development Indicators (CC BY 4.0): app/welt_daten.py -> app/data/welt.json
- Eurostat nrg_ti_eh / nrg_te_eh, bilateraler Strom (CC BY 4.0): app/welt_daten.py
- FRED (BEA-Zolleinnahmen, Census-Warenimporte, gemeinfrei): app/welt_daten.py
- Wirtschaftsräume von Hand mit Quelle je Raum: app/geo/wirtschaftsraeume.csv
- Seewege searoute/marnet (Apache-2.0), Flughäfen OurAirports (gemeinfrei): app/routen.py -> app/data/routen.json
- Meldungen zu Störungen (GDELT, sonst Google News RSS; nur Titel, Quelle, Datum, Link): app/news_routen.py -> app/data/news_routen.json
- Leitzinsen (BIS), 10-j. Renditen (OECD, CC BY 4.0), EZB-Kurse, Rohstoffe (FRED), Börsenplätze von Hand: app/boerse_welt.py -> app/data/boerse_welt.json
- Regierungen (Wikidata, CC0), Wahlkalender (Wikipedia, CC BY-SA 4.0), Bundestagswahl 2025 je Land (Bundeswahlleiterin, DL-DE 2.0), Umfragen (DAWUM, ODbL), Bundesländer (Natural Earth), Bündnisse von Hand: app/politik_daten.py -> app/data/politik.json
- Parlamente aller Staaten und Gliedstaaten: IPU Parline (CC BY-NC-SA 4.0, nicht kommerziell), Wikipedia-Infoboxen (CC BY-SA 4.0), Wikidata (CC0), Umrisse Natural Earth: app/parlamente_daten.py -> app/data/parlamente.json, app/geo/gliedstaaten.geojson

## Politik: Kommunen (neu 06.11.2026)

| Feld | Stand jetzt | Warum offen | Weg |
|---|---|---|---|
| Kommunen außerhalb Nordrhein-Westfalens | nur NRW: 54 Räte/Kreistage, 373 kreisangehörige Städte und Gemeinden (Heft 4), Vergleichswahlen aus Heft 1 (22 kreisfreie Städte, Stadt Aachen, 30 Kreise, Städteregion Aachen) und 141 Bezirksvertretungen aus Heft 3 der Kommunalwahlen 2025 (IT.NRW) | Quelle ist das Heft; andere Länder haben eigene Landesämter | Je Land ein Leser in app/kommunal_daten.py, Ablage unter kommunalwahlen/<land>_<jahr>/ |
| Vergleichsergebnisse Stadt Werne (Landtag/Europa/Bundestag) | fehlt | Im Textauszug von Heft 1 steht Werne in Tabelle 2 nicht | Seite im PDF prüfen |
| Koalitionen/Mehrheitsbündnisse in den Räten | fehlen | Amtliche Statistik enthält keine Bündnisse | Ratsinformationssysteme einzeln (aufwendig) |
| Kommunen als Flächen auf der Weltkugel | Punkte (Lage aus Wikidata, app/kommunal_lage.py → geo/kommunen_lage.json), Klick zeigt Sitzverteilung | Gebietsgrenzen der Gemeinden liegen nicht vor | Gebietsgrenzen (BKG VG250, Datenlizenz Deutschland) einbinden, Flächen nach stärkster Fraktion färben |
| Regionalverband Ruhr (Verbandsversammlung, Tabelle 5) | nicht eingelesen | Eigene Tabellenform | Reader ergänzen |
