# Konzept: Welthandelsrouten auf der Weltkugel

Stand: 03.11.2026 · Entwurf zur Abstimmung mit Robin · reines Konzept, kein Code

Bezug: Weltkugel-Oberfläche (`app/globus.py`, `app/src/globus.js`), Ebenen-Register `GLOBUS.ebene(...)`, Handelsströme-Ebene (PR #95) und `handel.json` aus UN Comtrade (PR #100, 167 Länder).

Standingregel des Projekts: **nur frei verfügbare Quellen, keine kostenpflichtigen APIs oder Dienste.** Alle Quellen unten erfüllen das. Lizenzangaben stammen aus meinem Kenntnisstand und sind **vor dem Einbau je Quelle zu prüfen** (Spalte „Prüfen“).

---

## 1. Ziel in einem Absatz

Zu den Handelsströmen (wer handelt wie viel mit wem) kommt die Frage dazu, **wie die Ware reist**: per Schiff, Bahn, Lkw oder Flugzeug, über welche Knotenpunkte (Häfen, Flughäfen, Bahnterminals, Grenzübergänge) und durch welche Engstellen (Suez, Panama, Malakka, Hormus, Bosporus, Bab-el-Mandeb …). Die Weltkugel soll dazu je Zoomstufe das Passende zeigen: ganz groß wenige dicke Hauptachsen, mittel die Routen der größten Länderpaare, nah die einzelnen Knoten samt Unternehmen.

## 2. Kernidee: Gerüst messen, Flüsse modellieren

Es gibt **keine freie Weltdatenbank**, die sagt, wie viele Tonnen von Land A nach Land B per Bahn oder Lkw fahren. Frei verfügbar sind dagegen:

- **Geometrie und Knoten** (wo liegen Häfen, Flughäfen, Gleise, Grenzübergänge) – gut und vollständig,
- **gemessene Teilzahlen** (Schiffsdurchfahrten je Engstelle, Containerumschlag je Land/Hafen, Grenzübergänge USA–Kanada/Mexiko, Verkehrsstatistik der EU),
- **bilaterale Handelswerte** (Comtrade, schon im Projekt).

Deshalb arbeitet das Konzept in drei Schichten:

1. **Netz (Gerüst):** Knoten und Kanten je Verkehrsträger mit Geometrie. Vollständig aus offenen Daten.
2. **Zuordnung (Modell):** Bilaterale Handelsströme aus `handel.json` werden auf Verkehrsträger aufgeteilt (Modal-Split) und über das Netz geroutet.
3. **Kalibrierung (Messung):** Wo es echte Zahlen gibt (Engstellen-Durchfahrten, EU-Statistik, US-Grenzverkehr), wird das Modell daran abgeglichen und die Strecke als „gemessen“ markiert.

Jeder Wert an einer Kante trägt ein **Vertrauensfeld**: `gemessen`, `abgeleitet` (aus Messung hochgerechnet) oder `modelliert`. Die Oberfläche zeigt das sichtbar an (durchgezogen / gestrichelt, Legende). So entsteht kein falscher Eindruck von Genauigkeit; das passt zur bisherigen Linie des Projekts, nichts zu erfinden.

## 3. Verkehrsträger, Knoten, Engstellen

### 3.1 Schiff (wichtigster Träger: rund 80 % der Welthandelsmenge in Tonnen, rund die Hälfte bis 60 % des Werts, Näherungswerte)

**Hauptachsen:** Asien–Europa (über Malakka, Bab-el-Mandeb, Suez oder um das Kap der Guten Hoffnung), Transpazifik (Ostasien–Westküste Nordamerika), Transatlantik, Asien–Ostküste Nordamerika über Panama oder Suez, Golf–Ostasien (Öl/Gas über Hormus), Südamerika–Asien (Erz, Soja), Australien–China (Erz, Kohle), Intra-Asien.

**Knoten (Häfen):** Weltweit rund 3.700 Häfen in der World Port Index, davon für die Darstellung relevant: ca. 100 Großhäfen (Stufe 2) und ca. 1.500 Häfen mit nennenswertem Verkehr (Stufe 3). Beispiele: Shanghai, Singapur, Ningbo-Zhoushan, Shenzhen, Qingdao, Busan, Rotterdam, Antwerpen-Brügge, Hamburg, Jebel Ali, Port Klang, Los Angeles/Long Beach, New York/New Jersey, Santos, Durban, Tanger Med.

**Engstellen (Chokepoints):**

| Engstelle | Rolle | Besonderheit für die Darstellung |
|---|---|---|
| Suezkanal | Asien–Europa | Durchfahrten brachen ab Ende 2023 wegen Rotem Meer ein, Umleitung um Afrika: gutes Beispiel für Jahresvergleich |
| Bab-el-Mandeb | Zugang Rotes Meer | gleiche Ereignisreihe wie Suez |
| Panamakanal | Atlantik–Pazifik | Wasserstand/Schleusen begrenzen Kapazität (Dürre 2023/24) |
| Straße von Malakka | Indischer Ozean–Südchinesisches Meer | größte Engstelle nach Menge, Alternativen Lombok/Sunda |
| Straße von Hormus | Golf-Öl und -Gas | Energie, kaum Alternativrouten |
| Bosporus / Dardanellen | Schwarzes Meer | Getreide, Öl; Türkische Meerengen |
| Gibraltar | Atlantik–Mittelmeer | |
| Ärmelkanal / Straße von Dover | Nordeuropa | dichtester Verkehr, Verkehrstrennungsgebiet |
| Dänische Meerengen (Großer Belt, Öresund), Kieler Kanal | Ostsee-Zugang | |
| Kap der Guten Hoffnung | Umleitung statt Suez | als „Engstelle“ nur Verkehrsmenge, kein Nadelöhr |
| Taiwanstraße, Koreastraße, Luzonstraße | Ostasien | |
| Lombok, Sunda | Malakka-Alternativen | |
| Straße von Kertsch, Magellanstraße, Kap Hoorn, Mosambikkanal, Yucatán | Nebenengstellen | nur ab Stufe 2/3 |

IMF PortWatch führt dafür 28 Engstellen mit täglichen Durchfahrten (am 03.11.2026 abgefragt): Suezkanal, Panamakanal, Bosporus, Bab-el-Mandeb, Malakka, Hormus, Kap der Guten Hoffnung, Gibraltar, Dover, Öresund, Taiwanstraße, Koreastraße, Tsugaru, Luzon, Lombok, Ombai, Bohai, Torres, Sunda, Makassar, Magellan, Yucatán, Windward-Passage, Mona-Passage, Balabac, Beringstraße, Mindoro, Kertsch. Nicht enthalten sind Dardanellen, Großer Belt und Kieler Kanal; die müssten selbst ergänzt werden.

### 3.2 Bahn

**Hauptachsen:**

- **Eurasische Landbrücke (China–Europa):** Nordroute (China–Kasachstan–Russland–Belarus–Polen–Duisburg/Deutschland), **Mittlerer Korridor** (Kasachstan–Kaspisches Meer per Fähre–Aserbaidschan–Georgien–Türkei), Südroute (Iran–Türkei). Transsibirische Eisenbahn als Binnenachse Russland.
- **Nordamerika:** Class-I-Netze (Union Pacific, BNSF, CN, CPKC) mit Hafen-Hinterlandverkehr (Westküste → Chicago, Kansas City) und Nord-Süd-Achse USA–Mexiko.
- **Europa:** TEN-T-Korridore (Rhein–Alpen/Rotterdam–Genua, Skandinavien–Mittelmeer, Nordsee–Ostsee, Orient/Ost-Med).
- **Afrika/Südamerika/Australien:** einzelne Erzbahnen und Korridore (Dar es Salaam–Sambia/TAZARA, Benguela, Dschibuti–Addis Abeba, Mombasa–Nairobi; Pilbara-Erzbahnen, Inland Rail).

**Knoten:** Containerterminals und **Umspurstellen** (Brest/Małaszewicze, Dostyk/Alashankou, Khorgos/Altynkol, Manzhouli/Zabaikalsk), Binnenhäfen und Hinterland-Hubs (Duisburg, Łódź, Chongqing, Xi’an, Chicago, Kansas City). Die Umspurstellen sind zugleich Engstellen der Landbrücke (Kapazität, Wartezeit, Sanktionslage) und bekommen dasselbe Symbol wie Seeengstellen.

### 3.3 Straße (Lkw, Auto)

**Hauptachsen:** USA–Mexiko und USA–Kanada (USMCA-Handel), EU-Binnenmarkt (Nord–Süd über die Alpen: Brenner, Gotthard, Fréjus; Ost–West über Polen/Deutschland), Türkei–Europa (Kapıkule/Kapitan Andreevo), China–Zentralasien/Südostasien, afrikanische Korridore (Northern Corridor Mombasa–Uganda, Beitbridge, Walvis Bay).

**Knoten:** **Grenzübergänge** (Laredo, Detroit–Windsor, Otay Mesa, Brenner, Kapıkule, Torkham, Beitbridge …), Logistikzentren. Engstellen sind hier Grenzübergänge, Alpenpässe und Brücken, nicht Kanäle.

Personenautos (Neuwagen als Handelsgut) laufen als Fracht mit: per Schiff (Ro-Ro) und Bahn. Eine eigene Pkw-Ebene gibt es nicht; wer Fahrzeugexporte sehen will, filtert nach HS-Kapitel 87.

### 3.4 Flugzeug

In Tonnen klein (rund 1 % der Menge), im Wert groß (Größenordnung ein Drittel des Welthandelswerts, Näherung, Quelle beim Einbau belegen): Elektronik, Pharma, Luxusgüter, Eilfracht.

**Hauptachsen:** Transpazifik, Nordatlantik, Asien–Europa, Golf-Drehkreuze als Brücke (Dubai, Doha, Istanbul). **Knoten:** große Frachtflughäfen (Hongkong, Memphis, Anchorage, Shanghai-Pudong, Incheon, Louisville, Dubai, Doha, Frankfurt, Leipzig/Halle, Lüttich, Miami, Ezhou-Huahu). Engstellen im engeren Sinn gibt es nicht; die Analogie sind **gesperrte oder gemiedene Lufträume** (Russland/Ukraine/Naher Osten) als Zusatzebene, falls gewünscht.

## 4. Quellen (nur frei verfügbar)

Legende „Nutzen“: G = Geometrie/Knoten, M = Messwert, K = Kontext/Kalibrierung. Lizenz und Aktualität nach meinem Kenntnisstand, „Prüfen“ = vor Einbau verifizieren.

### 4.1 Schiff

| Quelle | Inhalt | Nutzen | Format | Lizenz (Kenntnisstand) | Aktualität | Prüfen |
|---|---|---|---|---|---|---|
| IMF PortWatch | tägliche Schiffsdurchfahrten und geschätztes Handelsvolumen je Engstelle; Hafenanläufe und geschätzte Im-/Exporte je Hafen, aus AIS abgeleitet | M, G | ArcGIS-Feature-Service (JSON/CSV), kostenlos, ohne Schlüssel | **IMF-Sonderbedingungen, nicht CC BY** (geprüft 03.11.2026, siehe 4.6) | täglich, Stand 25.10.2026 | Genehmigung der IMF für automatisierten Abruf einholen |
| World Port Index (NGA, Pub. 150) | rund 3.700 Häfen: Position, Größe, Tiefgang, Kai-Einrichtungen | G | CSV/Shapefile | US-Behördenwerk, gemeinfrei | unregelmäßig (jährliche Überarbeitung) | Download-URL |
| World Bank Container Port Performance Index (CPPI) | Rang/Effizienz von rund 400 Containerhäfen | K | PDF/Excel | **CC BY-NC 3.0 IGO** (Ausgabe 2020–2024), frühere Ausgaben CC BY 3.0 IGO (geprüft 03.11.2026) | jährlich, mit Verzug von 1–2 Jahren | nicht-kommerzielle Nutzung klären |
| UNCTADstat | Containerumschlag (TEU) je Land, Liner-Shipping-Connectivity-Index (LSCI/PLSCI), Seehandel in Tonnen | M, K | CSV | CC BY 3.0 IGO (geprüft 03.11.2026) | jährlich | – |
| Natural Earth | Häfen, Küsten, Meeresflächen | G | GeoJSON/Shapefile | gemeinfrei | statisch | – |
| Marine Regions (VLIZ) | Namen und Polygone von Meerengen/Seegebieten | G | Shapefile/GeoJSON | CC BY 4.0 (Teil CC BY-NC, prüfen) | gelegentlich | Lizenz je Datensatz |
| Seeverkehrsgraph | Gerüst aus Fahrwegen zwischen Häfen und Engstellen; Optionen: Open-Source-Bibliothek `searoute` (MIT) bzw. eigener Graph aus PortWatch-Engstellen plus Küstenabstand | G | Graph | Bibliothek MIT, Datenherkunft prüfen | statisch | Herkunft des Graphen |
| Eurostat Seeverkehr (`mar_go_*`) | Güterumschlag der EU-Häfen nach Partnerregion | M | TSV/JSON | CC BY 4.0 | jährlich/vierteljährlich | Tabellencodes |
| Global Shipping Traffic Density (IMF/Weltbank, 2020) | Verkehrsdichteraster aus AIS | K | Raster | CC BY 4.0 | einmalig, 2015–2019 | nur als Plausibilisierung |
| Nicht verwenden | Global Fishing Watch (nicht kommerziell), kommerzielle AIS-Dienste (kostenpflichtig) | – | – | – | – | – |

### 4.2 Bahn

| Quelle | Inhalt | Nutzen | Format | Lizenz | Aktualität | Prüfen |
|---|---|---|---|---|---|---|
| OpenStreetMap (Geofabrik-Auszüge, Overpass) | `railway=rail`, Terminals, Umspurstellen | G | PBF/GeoJSON | ODbL (Quellenangabe, Share-Alike für Datenbank-Ableitungen) | täglich | ODbL-Pflichten für abgeleitete Datenbank |
| OpenRailwayMap | OSM-Aufbereitung, nur als Anschauung | K | Kacheln | ODbL | – | nicht als Datenquelle |
| Natural Earth Railroads | grobes Weltnetz | G | Shapefile | gemeinfrei | statisch | reicht für Stufe 1 |
| Eurostat Schienengüterverkehr (`rail_go_*`) | Tonnen nach Land/Partner, TEN-T-Korridore | M | TSV | CC BY 4.0 | jährlich | Tabellencodes |
| EU TEN-T / GISCO | Korridore, Terminals Europa | G | GeoJSON | CC BY 4.0 | gelegentlich | Download |
| US DOT NTAD (Bahnnetz), BTS TransBorder Freight | USA-Netz, Grenzverkehr nach Verkehrsträger | G, M | CSV/Shapefile | US-Behörde, gemeinfrei | monatlich/jährlich | – |
| Kuratierte Landbrücken | China–Europa-Routen, Mittlerer Korridor, Transsib, Umspurstellen | G, K | eigene CSV mit Belegen (Behörden- und Betreiberseiten, Wikipedia) | je Beleg | von Hand | **größte manuelle Position** |

Freie Zugzahlen/Tonnen je Landbrücke gibt es nur verstreut (Presse, Betreiberangaben). Werte dort als `abgeleitet` oder `modelliert` markieren, nie als gemessen.

### 4.3 Straße und Grenzübergänge

| Quelle | Inhalt | Nutzen | Format | Lizenz | Aktualität | Prüfen |
|---|---|---|---|---|---|---|
| OSM | Fernstraßen (motorway/trunk), `barrier=border_control`, Grenzübergänge | G | PBF/GeoJSON | ODbL | täglich | Vollständigkeit der Grenzübergänge je Region |
| Natural Earth Roads | grobes Weltnetz | G | Shapefile | gemeinfrei | statisch | Stufe 1/2 |
| BTS Border Crossing / TransBorder Freight | Lkw-Übertritte und Handelswert je Übergang USA–Kanada/Mexiko | M | CSV | gemeinfrei | monatlich | – |
| Eurostat Straßengüterverkehr (`road_go_*`) | Tonnen nach Land/Partner | M | TSV | CC BY 4.0 | jährlich | – |
| UNESCAP Asian Highway, AfDB Trans-African Highway | Korridornetze | G | PDF/Karten, teils GIS | frei zugänglich, Lizenz prüfen | selten | Digitalisierung nötig |

### 4.4 Luft

| Quelle | Inhalt | Nutzen | Format | Lizenz | Aktualität | Prüfen |
|---|---|---|---|---|---|---|
| OurAirports | rund 70.000 Flugplätze, Typ (large/medium/…), Position | G | CSV | gemeinfrei | laufend | – |
| OpenFlights | Flughäfen und Routen | G | CSV | ODbL; **Routen veraltet (Stand 2014)** | statisch | nur als Ergänzung |
| Natural Earth Airports | rund 900 Flughäfen | G | Shapefile | gemeinfrei | statisch | Stufe 1/2 |
| Eurostat Luftverkehr (`avia_tf_*`, `avia_gooc_*`) | Fracht und Passagiere je Flughafen/Partnerland EU | M | TSV | CC BY 4.0 | monatlich/jährlich | – |
| BTS T-100 | Fracht je US-Flughafen und Route | M | CSV | gemeinfrei | monatlich | – |
| Rangfolgen großer Frachtflughäfen (Flughafenbetreiber, Wikipedia mit Quellen) | Tonnen je Flughafen | M | von Hand | Fakten, Quelle zitieren | jährlich | Top-50 manuell |
| OpenSky Network | Flugbewegungen | K | – | nur Forschung/nicht kommerziell | – | **nicht verwenden**, wenn Veröffentlichung kommerziell werden könnte |

### 4.5 Handelswerte und Modal-Split

| Quelle | Inhalt | Format | Lizenz |
|---|---|---|---|
| UN Comtrade (schon im Projekt, `handel.json`) | bilaterale Werte nach HS-Kapitel; teils Feld Verkehrsträger | JSON/CSV | frei, Quellenangabe |
| Eurostat Comext | EU-Außenhandel **nach Verkehrsträger** und Partner | TSV | CC BY 4.0 |
| BTS TransBorder Freight | USA nach Verkehrsträger und Partner (Kanada/Mexiko) | CSV | gemeinfrei |
| WTO (schon im Projekt, `app/handel_wto.py`) | ergänzende Handelsstatistik | JSON | frei |

Global fehlt der Modal-Split je Länderpaar. Er wird aus Eurostat/BTS für die EU und die USA übernommen und für den Rest nach Warengruppe und Entfernung **modelliert** (z. B. Rohstoffe/Energie fast nur See, Pharma/Elektronik mit hohem Luftanteil, Nachbarländer mit Landanschluss mit Bahn/Lkw). Diese Regeln stehen in einer offenen Tabelle, nicht im Code versteckt.

### 4.6 Ergebnis der Quellenprüfung (Phase 0, 03.11.2026)

Abgerufen und gelesen am 03.11.2026; „erreichbar“ heißt nur, dass die Adresse antwortet.

| Quelle | Ergebnis |
|---|---|
| IMF PortWatch | Dienste erreichbar ohne Schlüssel (ArcGIS-Feature-Services): 28 Engstellen, 2.065 Häfen, Tagesdaten (Engstellen: Durchfahrten und Kapazität je Schiffstyp; Häfen: Anläufe, Importe und Exporte je Schiffstyp), letzter Tag 25.10.2026. **Lizenz ist nicht CC BY**, sondern die IMF-Nutzungsbedingungen: Herunterladen, Kopieren, abgeleitete Werke und Veröffentlichen sind erlaubt mit Quellenangabe („Source: International Monetary Fund, Datenbankname, Link“) und mit Hinweis auf wesentliche Veränderungen. **Automatisierter Massenabruf ist ohne ausdrückliche Erlaubnis untersagt, kommerzielle Weiterverwendung braucht Erlaubnis** (copyright@imf.org), Nutzung zum Training von Sprachmodellen ist ausgeschlossen. Folge: Vor dem automatischen Abruf in der Pipeline die Erlaubnis der IMF einholen; bis dahin nur manuelle Downloads. |
| World Bank CPPI | Ausgabe 2020–2024 unter CC BY-NC 3.0 IGO (nicht-kommerziell), frühere unter CC BY 3.0 IGO. Für ein nicht-kommerzielles Projekt nutzbar, bei kommerzieller Absicht klären. |
| UNCTADstat | CC BY 3.0 IGO, Quelle nennen. |
| OurAirports | Adresse erreichbar (12,8 MB CSV); laut OpenFlights gemeinfrei. |
| OpenFlights | ODbL; Streckendaten enden 2014 und sind „nur von historischem Wert“. Nur für Lage von Flughäfen, nicht für Routen. |
| Natural Earth | Hafen-Datei (`ne_10m_ports`) erreichbar; gemeinfrei. |
| NGA World Port Index | Seite erreichbar, Download-Adresse und Lizenzaussage nicht bestätigt. Offen. |
| Marine Regions | Seite lieferte beim Abruf einen Zugriffsfehler (403). Lizenz offen. |
| Eurostat | Lizenz in dieser Prüfung nicht erneut gelesen; Annahme CC BY 4.0 bleibt offen. |
| Global Energy Monitor | CC BY 4.0 bestätigt; Download über ein Formular, Adresse der Pipeline-Seite hat sich geändert. |
| Ember | CC BY 4.0 bestätigt; Format der Downloads wurde im Juli 2026 geändert, vor dem Skript prüfen. |
| ENTSO-E | Token wie beschrieben: Konto anlegen, E-Mail an transparency@entsoe.eu mit Betreff „Restful API access“ und registrierter Adresse im Text, Freischaltung laut Hilfeseite binnen drei Werktagen, danach Token unter „My Account“ erzeugen. Freie Weiterverwendung gilt für eine Liste von Daten (TSO-Daten), diese Liste vor dem Einbau prüfen. |

Wichtigste Folge: Der Schiffsteil hängt an der IMF-Erlaubnis für den automatisierten Abruf. Der Entwurf einer Anfrage liegt dem Thread bei.

Hinweis: Im Repo liegt bereits `app/KONZEPT_Handelsrouten.md` (gleicher Tag, aus der Umsetzung der Zoomstufen). Beide Dokumente sind inhaltlich verwandt; dieses hier ist ausführlicher bei Quellen, Datenmodell und Aufwand, das App-Dokument näher an der Oberfläche. Es gilt dort noch „PortWatch über 1.600 Häfen“, richtig sind 2.065.

## 5. Datenmodell

Passend zum bestehenden PostgreSQL-Kernmodell (`international/`) und zur Unternehmens-ID `U000123`. Alle Tabellen als CSV im Repo (wie `stammdaten/`), Auswertung für die Oberfläche zu einer kompakten JSON gebaut.

```
verkehr_knoten
  knoten_id        K00001 (opak, wie bei Unternehmen)
  typ              hafen | flughafen | bahnterminal | umspurstelle | grenzuebergang | binnenhafen
  name, land_iso, kontinent, lat, lon
  groessenklasse   1 (Stufe 1/2 sichtbar) | 2 | 3   -> steuert Zoomstufe
  quelle, quelle_id, lizenz

verkehr_engstelle
  engstelle_id     E001
  name, typ        meerenge | kanal | umspurstelle | pass | grenzuebergang
  modus            see | bahn | strasse | luft
  knoten_id        optional (Verweis auf Knoten)
  geometrie        Linie/Polygon (vereinfacht)
  alternative      verweist auf Ausweichroute (z. B. Suez -> Kap)
  portwatch_id     optional

verkehr_kante
  kante_id, modus, von_knoten, nach_knoten
  geometrie        vereinfachte Linie (entlang echter Route; Luft: Großkreis)
  korridor_id      z. B. "Asien-Europa-See", "Nordroute-Bahn"
  engstelle_ids    durchlaufene Engstellen
  laenge_km, kapazitaetshinweis

verkehr_korridor
  korridor_id, name, modus, kontinent_von, kontinent_nach, beschreibung

verkehr_fluss                      (Jahr x Kante)
  kante_id, jahr, richtung
  tonnen, wert_usd
  methode          gemessen | abgeleitet | modelliert
  quelle, stand

verkehr_fluss_paar                 (Zuordnung Länderpaar -> Modus -> Weg)
  jahr, exp_land, imp_land, hs_kapitel
  modus, anteil, wert_usd
  weg_kanten[]     Liste kante_id der Standardroute
  methode

verkehr_engstelle_durchfahrt       (Zeitreihe, aus PortWatch)
  engstelle_id, datum, schiffe_gesamt, schiffe_nach_typ, tonnen_geschaetzt

unternehmen_knoten                 (nur Stufe 3)
  id (U000…), knoten_id, abstand_km, verfahren   (naechster Hafen/Flughafen, nur Hinweis)
```

Wichtig: `verkehr_fluss_paar` hängt an den vorhandenen Comtrade-Zeilen. Kontinentströme (Stufe 1) und Top-3-Ströme (Stufe 2) sind **Aggregate derselben Tabelle**, es gibt keine zweite Wahrheit.

## 6. Darstellung in den drei Zoomstufen

Prinzip: Ein flüssiger Zoom ohne Sprünge. Technisch heißt das: jede Ebene hat Mindest- und Höchstzoom mit weichem Ein-/Ausblenden (Deckkraft-Übergang über ca. eine Zoomstufe) und Linienbreiten, die mit dem Zoom skalieren. Die Daten je Stufe sind vorab aggregiert, damit nichts im Browser neu gerechnet werden muss. Die Schwellen entsprechen den bestehenden Kerndaten-Stufen der Kugel.

### Stufe 1 – Kontinentströme (ganz groß)

- **Linien:** ein gebündeltes Band je Kontinentpaar und Richtung (Europa, Asien, Afrika, Nordamerika, Südamerika, Ozeanien = 6×6 inkl. Binnenverkehr), Breite nach Wert. Der Kontinent aus der IP-Adresse ist vorgewählt (siehe Hinweis unten); Klick auf einen anderen Kontinent wechselt die Auswahl, Klick auf ein Band öffnet die Zahlen.
- **Verkehrsträger:** Umschalter See / Bahn / Straße / Luft / Alle. Auf dieser Stufe laufen Seebänder **entlang der echten Hauptseewege** (Kap- und Suezroute, Panama, Transpazifik), nicht als gerade Linie. Bahn nur als drei dicke Eurasien-Achsen, Luft als Großkreisbögen zwischen den Hubs-Regionen, Straße praktisch nur Nordamerika.
- **Knoten:** keine einzelnen Häfen. Nur die **großen Engstellen** (Suez, Panama, Malakka, Hormus, Bosporus, Bab-el-Mandeb, Gibraltar, Dover) als große Symbole mit Mini-Anzeige (Durchfahrten pro Tag bzw. Index) und Schaltfläche „Umleitung zeigen“.
- **Zahl der Objekte:** unter 100 Linien/Symbole.

### Stufe 2 – Länder (mittel)

- **Linien:** je Land die **Top 3 Importströme und Top 3 Exportströme** (wie vom Auftrag vorgegeben), gezeichnet auf der Standardroute, die `verkehr_fluss_paar` vorgibt. Farbe = Verkehrsträger, Breite = Wert, gestrichelt = modelliert.
- **Knoten:** die **Großhäfen** (Klasse 1: ca. 100), große Frachtflughäfen (ca. 50), die wichtigen Bahnterminals/Umspurstellen und die Hauptgrenzübergänge. Beschriftung erst ab einer Mindestgröße.
- **Engstellen:** alle Seeengstellen mit Namen, dazu Umspurstellen und Alpenpässe. Hover/Klick zeigt Zeitreihe (PortWatch) und Alternativroute.
- **Zahl der Objekte:** rund 1.000.

### Stufe 3 – Unternehmen und Nachbarn (nah)

- **Unternehmen** erscheinen erst hier (wie bisher als Cluster/Punkte). Neu: Klick auf ein Unternehmen markiert den **nächstgelegenen Hafen/Flughafen** (`unternehmen_knoten`) als Hinweis, nicht als Behauptung, dass die Ware dort läuft.
- **Nachbarländer:** Im- und Exporte je Landgrenze mit Verkehrsträger, am Grenzübergang verankert (Lkw/Bahn). Dazu Klick auf ein Land → Tabelle „Nachbarn“.
- **Strom:** grenzüberschreitende Stromflüsse (Importe/Exporte) als eigene Ebene mit Leitungen; Quellen dafür (ENTSO-E Transparency Platform für Europa, frei mit Registrierung; Eurostat; Ember) sind **nicht Teil dieses Konzepts** und werden in einem eigenen Konzept beschrieben. Schnittstelle: dieselben Tabellen `verkehr_knoten/kante`, `modus = strom`.
- **Knoten:** alle Häfen/Flughäfen/Terminals/Grenzübergänge der Klasse 2 und 3, mit Detailkarte (Kapazität, Umschlag, Land, Quelle).
- **Zahl der Objekte:** je Bildausschnitt wenige tausend, per Kachelung/Ausschnitt geladen.

### Hinweis zur Vorauswahl nach IP

Die Kontinentwahl nach IP ist **nicht ohne Weiteres umsetzbar**, wenn die Seite als Artifact oder statische Datei läuft: Eine Abfrage an einen IP-Dienst ist durch die Inhaltsrichtlinie gesperrt oder kostet (Dienste mit Gratisquote). Konzeptvorschlag: Erst Browsersprache und Zeitzone (`Intl.DateTimeFormat().resolvedOptions().timeZone`, z. B. „Europe/Berlin“ → Europa) nutzen, das funktioniert ohne Fremddienst und ohne Datenschutzproblem; die genaue IP-Abfrage nur optional (freier Dienst ohne Schlüssel), mit Rückfall auf Zeitzone. Entscheidung offen.

## 7. Technische Umsetzung (grob)

- **Rechenschritt (Python, Ablauf wie bei `app/globus.py`):** Quellen laden → Netz/Graph bauen → Standardrouten je Länderpaar berechnen → Modal-Split → Flüsse je Kante summieren → Kalibrierung gegen PortWatch/Eurostat/BTS → vereinfachte JSON für die Oberfläche (`app/geo/verkehr_*.json`).
- **Geometrie-Budget:** Seewege ca. 1–2 MB (vereinfacht), Häfen/Flughäfen/Terminals ca. 1 MB, Bahn- und Straßengeometrie nur für Korridore (nicht das ganze OSM-Netz) ca. 2–4 MB. Ziel: Gesamtzuwachs unter 10 MB, damit die Einzeldatei-Vorschau (Artifact, komprimiert) noch funktioniert. Detaildaten für Stufe 3 optional als getrennte Dateien, bei Bedarf nachgeladen.
- **Oberfläche:** neue Ebenen im bestehenden Register (`GLOBUS.ebene('verkehr_see', …)` usw.), pro Stufe eine Datei. Umschalter Verkehrsträger, Jahr (für Suez-/Panama-Vergleich), Legende mit Vertrauensstufe.
- **Aktualisierung:** PortWatch-Zeitreihen täglich/wöchentlich im vorhandenen Workflow-Rhythmus; alles andere jährlich.

## 8. Reihenfolge und Aufwand (grob, in Arbeitstagen für die Umsetzung)

| Phase | Inhalt | Aufwand | Ergebnis |
|---|---|---|---|
| 0 | Quellen verifizieren (Lizenzen, URLs, Abfragegrenzen), Kontinentzuordnung der 167 Länder, Entscheidung IP/Zeitzone | 1 | Quellenliste final |
| 1 | **Schiff:** Häfen (WPI, PortWatch), Engstellen, Seegraph, Routing der Top-Länderpaare, Kalibrierung an PortWatch | 6–8 | Seeebene Stufe 1+2, Engstellen mit Zeitreihe |
| 2 | **Luft:** Flughäfen (OurAirports), Top-50-Fracht, Großkreise, Eurostat/BTS | 3–4 | Luftebene |
| 3 | **Bahn:** kuratierte Landbrücken, Terminals, Umspurstellen, Eurostat/BTS-Bahn | 5–7 | Bahnebene (viel Handarbeit) |
| 4 | **Straße:** Grenzübergänge (OSM, BTS), Korridore, Eurostat-Straße | 5–7 | Straßenebene, Nachbarländer Stufe 3 |
| 5 | Modal-Split-Modell Rest der Welt, Vertrauensstufen, Validierung | 3–4 | alle Träger einheitlich |
| 6 | Stufe 3: Unternehmen ↔ Knoten, Detailkarten | 3–4 | vollständige Darstellung |

Summe etwa 26–35 Arbeitstage, schrittweise auslieferbar; **Empfehlung: Phase 0 und 1 zuerst**, weil Schiff den größten Teil des Handels trägt, die beste Messbasis hat (PortWatch) und Suez/Panama/Hormus die sichtbarsten Engstellen sind. Danach Luft (günstig), dann Bahn und Straße.

## 9. Grenzen und Risiken

- **Modellierte Flüsse sind Schätzungen.** Ohne Betreiber- oder Zolldaten ist die Bahn- und Lkw-Aufteilung außerhalb EU/USA nur grob. Deshalb Vertrauensfeld und Legende.
- **Spiegelwerte:** Comtrade-Meldungen von Export- und Importland weichen voneinander ab; Wert-USD, nicht Tonnen. Tonnen nur dort, wo Quellen sie liefern.
- **Lizenz OSM (ODbL):** Quellenangabe in der Fußzeile und Share-Alike für abgeleitete Datenbanken beachten; CC-BY-Quellen ebenfalls namentlich nennen. Nicht-kommerzielle Quellen (Global Fishing Watch, OpenSky) bleiben draußen.
- **Ereignisse:** Rotes Meer, Panama-Dürre, Sanktionen auf Bahnrouten über Russland ändern Routen kurzfristig. Das Modell braucht ein Jahr-Feld und bekannte Sperrungen als Regeln (z. B. Suez gesperrt ab 2024 → Kap).
- **Umfang des Hafenverzeichnisses:** PortWatch deckt nur Häfen mit AIS-Meldungen ab; kleine oder militärische Häfen fehlen. WPI schließt Lücken, aber ohne Verkehrsmengen.
- **Datenmenge:** OSM weltweit ist zu groß; nur Korridorgeometrie und Knoten übernehmen.
- **Bezug zu Unternehmen:** Die Nähe eines Firmensitzes zu einem Hafen sagt nichts über dessen Warenwege; die Oberfläche kennzeichnet das als Hinweis.

## 10. Entscheidungen (Robin, 03.11.2026)

1. **Modell vs. Messung:** Ja. Bahn- und Straßenflüsse außerhalb EU/USA werden modelliert und als solche gekennzeichnet.
2. **IP-Vorauswahl:** Vorschlag angenommen. Zeitzone/Browsersprache als Standard, IP-Abfrage nur optional mit Rückfall auf die Zeitzone.
3. **Strom und Pipelines:** Eigenes Konzept gewünscht, siehe [weltkugel_strom_pipelines_konzept.md](weltkugel_strom_pipelines_konzept.md).
4. **Reihenfolge:** Mit Phase 0 und 1 (Schiff und Engstellen) beginnen, sobald Robin die Umsetzung freigibt.
5. **Pkw/Neuwagen:** Noch offen; bis dahin gilt der HS-87-Filter.
