# Konzept: Welthandelsrouten (Schiff, Bahn, Straße, Luft) auf der Weltkugel

Stand 03.11.2026, Entwurf zur Abstimmung. Baut auf den drei Zoomstufen der Weltkugel auf (Stufe 1 Kontinente, Stufe 2 Länder, Stufe 3 Unternehmen und Nachbarn). Die Routen kommen als neue Ebenengruppe „Verkehrswege“ in das bestehende Ebenen-Register (`GLOBUS.ebene(...)`), je Verkehrsträger ein eigener Schalter.

Alle genannten Quellen sind ohne Bezahlung und ohne Vertrag nutzbar (Projektregel: keine kostenpflichtigen Dienste). Wo die Lizenz vor der Übernahme zu prüfen ist, steht „Lizenz prüfen“.

## 1. Was auf die Karte soll

| Objekt | Beispiele | Darstellung |
|---|---|---|
| **Routen** (Linien) | Seewege Asien–Europa über Suez bzw. Kap, Transpazifik, Nordatlantik; Bahn China–Europa (Nord-, Mittel-, Südkorridor); Fernstraßen-Korridore; Luftfracht-Hauptachsen | Linienbreite = Menge, Farbe = Verkehrsträger |
| **Knotenpunkte** | Seehäfen (Shanghai, Singapur, Rotterdam …), Umschlagbahnhöfe und Trockenhäfen, Grenzübergänge (Małaszewicze, Brest, Alashankou/Khorgos), Frachtflughäfen (Memphis, Hongkong, Anchorage …) | Punkte, Größe = Umschlag |
| **Engstellen** | Suez, Bab al-Mandab, Hormus, Malakka, Panama, Bosporus, Gibraltar, Dänische Meerengen, Ärmelkanal, Taiwanstraße, Kap der Guten Hoffnung; Landengpässe (Brest, Khorgos, Darién) | Markierung mit Durchfahrten pro Tag, Anteil am Welthandel, Störungs-Hinweis |
| **Umschlagstellen** zwischen Verkehrsträgern | Hafen–Bahn, Bahn–Straße | Verbindungsknoten, Stufe 3 |

## 2. Darstellung je Zoomstufe

**Stufe 1 (Kontinente).** Nur die 10 bis 12 Hauptkorridore als breite, geglättete Bänder zwischen den Kontinentmitten, Verkehrsträger als Farbanteil im Band (Schiff überwiegt fast überall, Bahn und Luft sieht man nur als dünne Zusatzlinien Eurasien und Transpazifik). Die Engstellen erscheinen als etwa acht große Marker mit Tageszahl. Klick auf ein Band öffnet in der Seitenleiste die Aufteilung nach Verkehrsträger und die genutzten Engstellen. Das passt zur vorhandenen Kontinentmatrix.

**Stufe 2 (Länder).** Routen werden zu Länderpaaren zugeordnet: Die drei größten Handelsströme je Land (wie heute) laufen entlang der tatsächlichen Wege (Seeweg über Hafen und Engstelle, Bahn über Grenzübergang) statt als Großkreis. Sichtbar sind die rund 60 größten Häfen, 40 Frachtflughäfen und die großen Grenz- und Umschlagpunkte; die Verkehrsträger lassen sich einzeln ein- und ausblenden. Engstellen mit Namen, Durchfahrten und Anteil.

**Stufe 3 (Unternehmen, Nachbarn).** Infrastruktur im Detail: einzelne Häfen mit Terminals, Bahnnetz (OSM), Fernstraßen und Grenzübergänge zu jedem Nachbarland (zusammen mit den Nachbarströmen aus Stufe 3 der Länderebene), Flughäfen. Hier kommen die Unternehmen ins Spiel: Werke und Sitze mit Anbindung an den nächsten Hafen, Bahnhof und Flughafen; später echte Lieferketten (Ebene „Lieferketten“) entlang dieser Wege.

Die Überblendung geschieht wie jetzt über die Deckkraft nach Zoom; Linien werden pro Stufe in einer eigenen Vereinfachungsstufe vorgehalten (siehe 5).

## 3. Quellen

**Schiff**
- IMF PortWatch (portwatch.imf.org, Open Data über ArcGIS-Dienste): tägliche Durchfahrten und geschätztes Handelsvolumen für 28 Engstellen und über 1.600 Häfen, aus Satelliten-AIS. Kernquelle für Engstellen und Häfen. Lizenz prüfen (IMF-Nutzungsbedingungen, bei Veröffentlichung Quellenangabe).
- NGA World Port Index (gemeinfrei): Lage und Eigenschaften von rund 3.800 Häfen.
- World Bank Container Port Performance Index und UNCTAD-Containerumschlag (jährlich, frei): Rangfolge und Umschlag der Containerhäfen.
- Seewege: freies Seewegenetz (Python-Paket `searoute`, MIT, Netz aus offenen Daten) zum Verlegen der Routen; ergänzend die Weltbank-Verkehrsdichte aus AIS („Global Shipping Traffic Density“, offen) zur Kontrolle der Hauptachsen. EMODnet Human Activities (Schiffsdichte EU-Gewässer, CC BY).
- Lücke: Echtzeit-AIS einzelner Schiffe gibt es frei nur eingeschränkt (AISHub verlangt eigene Daten, Global Fishing Watch nur Fischerei). Für ein Verkehrsbild einzelner Schiffe wäre ein Bezahldienst nötig; das ist nicht geplant, die tägliche Auswertung aus PortWatch reicht für Stufe 1 und 2.

**Bahn**
- OpenStreetMap, Schienennetz und Güterbahnhöfe (ODbL; Auszug über Overpass bzw. Geofabrik, vereinfacht).
- UNECE-Listen der wichtigsten Güterverkehrslinien und Umschlagterminals (AGC/AGTC) und die Korridore der EU (TEN-T, offene Geodaten).
- Mengen: Eurostat (rail_go_*) für Europa, US BTS Freight Analysis Framework 5 (frei) für die USA und Nordamerika. Für China–Europa nur Berichte und Jahreszahlen der Betreiber (Anzahl Züge und Container je Jahr, zitierbar, aber nicht einheitlich erhoben).
- Lücke: weltweit keine einheitlichen Bahnfrachtmengen je Korridor.

**Straße**
- OpenStreetMap, Fernstraßen (trunk/motorway, ODbL), TEN-T-Netz, Asian-Highway- und Trans-African-Highway-Listen (UNESCAP bzw. AU, öffentlich).
- Grenzübergänge: US BTS Border Crossing Data (Lkw je Übergang USA–Kanada/Mexiko, frei), für Europa kein einheitlicher Datensatz (Eurostat nur national).
- Mengen: Eurostat road_go, BTS FAF5, IRU-Berichte.
- Lücke: Lkw-Ströme sind außerhalb von EU und USA kaum frei zugänglich.

**Luft**
- OurAirports (gemeinfrei) und OpenFlights (ODbL, Streckendaten nur bis etwa 2017, deshalb höchstens für die Lage): Flughäfen.
- Mengen: Eurostat avia_gooc (Fracht je Flughafenpaar, EU), US BTS T-100, OpenSky Network (Flugbewegungen, frei für Forschung, Lizenz prüfen). Weltweite Frachtranglisten (ACI) sind kostenpflichtig; Ersatz: Wikipedia-Tabellen mit Quellenangabe und Eurostat/BTS.
- Lücke: Luftfracht je Länderpaar weltweit frei nicht verfügbar.

**Welche Mengen laufen über welchen Verkehrsträger**
- US Census (USA Trade Online) und Eurostat Comext weisen Außenhandel nach Verkehrsträger aus (Wert und Gewicht je Partnerland). Das ist die einzige freie Quelle für den Anteil Schiff, Bahn, Straße, Luft nach Länderpaar; sie deckt nur USA und EU ab. Für den Rest: Näherung über Gütertyp (Rohstoffe See, Elektronik und Pharma Luft) aus UN Comtrade nach Warengruppe (HS), als Modell gekennzeichnet.
- UN Comtrade selbst hat keinen Verkehrsträger (die Spalte ist leer), deshalb sind Routen aus Länderströmen immer modelliert und nicht gemessen.

## 4. Datenmodell

Neue Dateien unter `app/data/`, per Skript erzeugt (wie `handel_stufen.py`):

- `knoten.json`: Hafen, Flughafen, Bahnterminal, Grenzübergang mit ID, Art, Land, Koordinate, Umschlag, Quelle, Jahr.
- `engstellen.json`: Name, Geometrie, Durchfahrten pro Tag (PortWatch), Anteil am Welthandel, Quelle.
- `routen.json`: Korridore als Linien mit Verkehrsträger, Knoten-IDs, Engstellen-IDs und je Stufe vereinfachter Geometrie.
- `routen_zuordnung.json`: je Länderpaar der Anteil je Verkehrsträger und die genutzten Routen (modelliert, mit Kennzeichnung „gemessen“ bzw. „geschätzt“ und Quelle).

Aus Länderströmen werden Routenmengen berechnet: Strom je Länderpaar × Verkehrsträgeranteil → kürzester Weg im Netz (mit Zuschlag für Engstellen, damit z. B. Suez und Kap als Alternativen auftauchen) → Summe je Strecke. Rechenmodell und Annahmen stehen im Panel der Ebene.

## 5. Technik

- Geometrien im GeoJSON, pro Stufe vereinfacht (Douglas-Peucker, 1° / 0,1° / ungekürzt), OSM-Netz nur für Stufe 3 und nur für Fernverbindungen. Ziel: unter 15 MB zusätzlich in der Seite.
- Liniendicke und -deckkraft nach Zoom wie bei den Handelsbögen; Engstellen und Häfen als Symbol- und Kreisschichten mit Mengenradius.
- Ein Klick öffnet im Seitenfenster Menge, Quelle, Berichtsjahr, Abweichung der Zuordnung.
- Aktualisierung: PortWatch täglich (GitHub-Workflow), alles andere jährlich.

## 6. Vorschlag zur Reihenfolge

1. **Engstellen und Häfen** (PortWatch, World Port Index): kleinster Aufwand, größte Wirkung, Stufe 1 und 2.
2. **Seerouten** aus Seewegenetz, Zuordnung der Containerströme (Länderpaare × Seeanteil).
3. **Luft**: Flughäfen und die zwanzig größten Frachtachsen.
4. **Bahn**: Eurasien-Korridore als kuratierte Liste, Rest aus OSM in Stufe 3.
5. **Straße** und Grenzübergänge (zuerst USA und EU, wo Daten vorhanden sind).
6. Verknüpfung mit Unternehmen (Werke, Lieferketten) in Stufe 3.

## 7. Offene Fragen und Grenzen

- Mengen je Route sind außer bei Engstellen und Häfen **modelliert**, nicht gemessen; das muss in der Oberfläche sichtbar bleiben.
- Quellenlizenzen von PortWatch und OpenSky vor dem Einbau prüfen.
- Soll es auch Pipelines, Stromtrassen und Datenkabel geben? Die Stromseite hängt an derselben Netzlogik (bilaterale Stromflüsse nur für Europa über ENTSO-E mit kostenlosem Token möglich).
- Zeitverlauf (Sperrungen, Umleitung um das Kap): PortWatch liefert Tagesreihen seit 2019, damit wären Störungen wie Rotes Meer oder Panama-Dürre darstellbar.
