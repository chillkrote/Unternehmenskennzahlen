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
| Kabinett und Sitzverteilung außerhalb Deutschlands | fehlt | Keine freie gemeinsame Quelle | Wikidata (Mitglieder der Regierung) prüfen |
| Ergebnis der letzten Landtagswahl und Koalition je Bundesland | fehlt (Bundestagswahl 2025 je Land ist da) | Landeswahlleitungen ohne gemeinsames offenes Format | Landeswahlleitungen einzeln anbinden |
| Umfragen außerhalb Deutschlands | fehlt | Keine freie Quelle mit klarer Lizenz | je Land prüfen |
| Regionen außerhalb Deutschlands | fehlt | Regionalregierungen und -wahlen nicht gesammelt | nach Deutschland weitere Länder |
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
