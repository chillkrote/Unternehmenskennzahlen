# Offene Datenfelder der Weltkugel

Stand 04.11.2026. Hier steht, welche Daten die fünf Darstellungsformen der Weltkugel (Handel, Volkswirtschaft, Börse & Finanzen, Unternehmen, Politik & Wahlen) noch nicht haben und warum. Regel des Projekts: nur kostenlose Quellen ohne Bezahlschranke. Ein Feld bleibt offen, solange es keine solche Quelle gibt oder die Quelle einen (kostenlosen) Schlüssel braucht, den wir noch nicht eingerichtet haben.

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

## Börse & Finanzen (Entwurf zur Freigabe)

| Feld | Stand jetzt | Warum offen | Weg |
|---|---|---|---|
| Rendite zehnjähriger Staatsanleihen außerhalb der OECD | OECD-Länder | Keine freie gemeinsame Quelle | Zentralbanken einzeln |
| Leitzinsen aller Länder | noch nicht eingebunden | BIS-Statistik (Leitzinsen) ist frei, Nutzung noch zu prüfen | BIS Data Portal anbinden |
| Kreditausfallprämien (CDS) | nicht vorgesehen | nur kostenpflichtig | entfällt |

## Unternehmen (Entwurf zur Freigabe)

| Feld | Stand jetzt | Warum offen | Weg |
|---|---|---|---|
| Koordinaten der Firmensitze | 1.230 Unternehmen mit Sitz auf der Karte | Rund 31.000 Unternehmen ohne Koordinaten (Entscheidung 03.11.2026: später) | Geokodierung über Wikidata bzw. OpenStreetMap Nominatim (frei, langsam) |
| Lieferketten und Beteiligungen | Beispiel Volkswagen (stammdaten/beziehungen) | Keine freie strukturierte Quelle; Geschäftsberichte von Hand | Schrittweise je Unternehmen erfassen |

## Politik & Wahlen (Entwurf zur Freigabe)

| Feld | Stand jetzt | Warum offen | Weg |
|---|---|---|---|
| Wahltermine weltweit | Deutschland | Keine freie maschinenlesbare Gesamtliste | Wikidata-Abfrage (Wahlen mit Datum) prüfen |
| Umfragen | Deutschland | Außerhalb Deutschlands keine freie Quelle mit klarer Lizenz | je Land prüfen |
| Ausrichtung der Regierungsparteien | EU und OECD (ParlGov) | Außerhalb nicht abgedeckt | V-Dem bzw. Manifesto Project prüfen (Lizenz) |

## Schon eingebunden (zum Vergleich)

- Weltbank World Development Indicators (CC BY 4.0): app/welt_daten.py -> app/data/welt.json
- Eurostat nrg_ti_eh / nrg_te_eh, bilateraler Strom (CC BY 4.0): app/welt_daten.py
- FRED (BEA-Zolleinnahmen, Census-Warenimporte, gemeinfrei): app/welt_daten.py
- Wirtschaftsräume von Hand mit Quelle je Raum: app/geo/wirtschaftsraeume.csv
- Seewege searoute/marnet (Apache-2.0), Flughäfen OurAirports (gemeinfrei): app/routen.py -> app/data/routen.json
- Meldungen zu Störungen (GDELT, sonst Google News RSS; nur Titel, Quelle, Datum, Link): app/news_routen.py -> app/data/news_routen.json
