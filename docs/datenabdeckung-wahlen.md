# Datenabdeckung Wahlen

Stand 10.11.2026. Grundlage ist das Wahlregister `app/data/wahlen.json` (976 Wahlen). Die vollständige, maschinenlesbare
Übersicht je Wahl steht in `wahlen/abdeckung.csv` (erzeugt von `app/wahlabdeckung.py`, wird mit dem Wahlregister im Workflow
`weltkugel.yml` erneuert). Dieses Dokument fasst sie zusammen und legt die Reihenfolge der Lücken fest.

## Stufen

| Stufe | Bedeutung | sichtbar auf der Weltkugel |
|---|---|---|
| A | amtliche Quelle mit Untereinheiten und Grenzen (Wahlkreise, Kreise, Gemeinden), absolute Stimmen | Karte je Einheit, Ergebniskarte, meist Vergleich zur Vorwahl |
| B | amtliche Quelle, nur Gesamtergebnis | Ergebniskarte |
| C | Wahlartikel (Wikipedia): Stimmenanteile der größeren Parteien | Fläche nach stärkster Partei, keine absoluten Stimmen, keine Untereinheiten |
| D | nur Sitzverteilung (IPU Parline oder heutige Zusammensetzung) | Sitzverteilung, keine Stimmen |

## Stand je Ebene

| Ebene | Wahlen | A | B | C | D |
|---|---|---|---|---|---|
| E0 Supranational (Europawahl 2024, nur Deutschland) | 1 | 1 | 0 | 0 | 0 |
| E1 Staat (178 Staaten, 219 Wahlen) | 219 | 26 | 0 | 103 | 90 |
| E2 Region (Länder, Bundesstaaten, Provinzen) | 306 | 2 | 0 | 219 | 85 |
| E3 Kreis/Stadt (Kommunalwahl NRW 2025) | 54 | 54 | 0 | 0 | 0 |
| E4 Gemeinde/Bezirk (Kommunalwahl NRW 2025) | 396 | 396 | 0 | 0 | 0 |

Stufe A auf E1: Bundestagswahl 2025, Unterhauswahlen in Österreich 2024, Australien 2025, Kanada 2025, Schweiz 2023, Spanien 2023,
Frankreich 2024, Vereinigtes Königreich 2024, Norwegen 2025; USA: Repräsentantenhaus 2020, 2022, 2024, Senat 2022, Präsident
1976 bis 2024.

## Deutsche Länder (E2)

| Land | letzte Wahl | Stufe | Quelle heute | amtliche Dateien |
|---|---|---|---|---|
| Sachsen-Anhalt | 06.09.2026 | **A** | Statistisches Landesamt, endgültiges Ergebnis: 41 Wahlkreise, 14 Kreise, Sitze, Vergleich 2021 | eingebunden (`app/landtagswahlen.py`) |
| Nordrhein-Westfalen | 15.05.2022 | **A** | Landeswahlleiterin: 128 Wahlkreise, Vergleich 2017 | eingebunden (`app/wahlen_daten.py`) |
| Baden-Württemberg | 08.03.2026 | C | Wahlartikel | gefunden: `wahlen.statistik-bw.de/ltw26/` (Ergebnisse und Gewählte als CSV, endgültig) |
| Rheinland-Pfalz | 22.03.2026 | C | Wahlartikel | gefunden: `wahlen.rlp.de` (endgültiges Ergebnis je Wahlkreis, Kreis, Verbandsgemeinde als XLSX, Stimmbezirke als CSV; Dateien ab 2001) |
| Mecklenburg-Vorpommern | 20.09.2026 | C | Wahlartikel | gefunden: `laiv-mv.de/Wahlen/Landtagswahlen/2026/` (endgültiges Ergebnis als Download) |
| Berlin | 20.09.2026 | C | Wahlartikel | gefunden: `wahlen-berlin.de` (`DL_BE_AGHBVV2026.xlsx`) |
| Brandenburg, Sachsen, Thüringen (2024), Hamburg (2025), Bayern, Hessen, Bremen (2023), Niedersachsen, Schleswig-Holstein, Saarland (2022) | | C | Wahlartikel | noch nicht gesucht |

Bei Stufe C fehlen einheitlich: absolute Stimmen, Vergleich zur Vorwahl, Wahlkreise auf der Karte, amtliche Quelle.

## Muster für eine Landtagswahl

Sachsen-Anhalt 2026 ist das Muster, nach dem die übrigen Länder folgen:

1. **Quelle:** amtliche Dateien unverändert nach `wahlen/quellen/<land>_ltw<jahr>_*.csv`; Vergleichswerte der Vorwahl, die nur
   auf der Ergebnisseite stehen, als Auszug `…_vergleich_<jahr>.json` mit Fundstelle.
2. **Import:** eine Lesefunktion je Land in `app/landtagswahlen.py`, Eintrag in `WAHLEN`, `LADEN`, `WAHL_GEO`. Sie liefert
   Land, Einheiten (Kreise, Wahlkreise), Sitze, Stimmarten, Wahlsystem, Vorwahl, Quelle mit Lizenz.
3. **Prüfung** vor der Übernahme, Abbruch bei Abweichung: nur endgültige Ergebnisse; Summe der Wahlkreise und der Kreise = Land
   in jeder Spalte; gültige Stimmen = Summe der Parteien; Wähler = gültige + ungültige; Urne + Brief = Gesamt; gewählter Bewerber
   hat die meisten Erststimmen; Direktmandate = Sitzverteilung; Sitze je Partei = Summe; Grenzen vollständig.
4. **Auslieferung:** `python3 app/wahlen_daten.py --ohne-abruf` schreibt das Wahlregister; die amtliche Datei ersetzt den
   Wahlartikel und hängt nicht an ihm. Grenzen als `app/geo/landtagswahlkreise_<land>.geojson`; die Server-Fassung lädt Werte
   und Grenzen als Dateien aus `wahlgeo/` nach.
5. **Weltkugel:** Politik & Wahlen, Ebene E2: Sitzverteilung mit Veränderung, Zweit- und Erststimmen mit Veränderung zur
   Vorwahl, Karte je Kreis und je Wahlkreis, Direktmandat im Wahlkreis.
6. **Tests:** `app/tests/test_landtagswahlen.py` (Prüfregeln, Sollwerte des Endergebnisses, Stand im Wahlregister),
   `app/tests/landtagswahl-smoke.js` (Ergebniskarte und Klick in einen Wahlkreis, Pages- und Server-Fassung).

Nicht umgesetzt: Wahlen liegen als Dateien vor, nicht in der Datenbank. Tabellen `election` und `election_result` mit einem
Endpunkt `/elections` sind erst nötig, wenn Wahlen mit Wirtschaftsdaten verknüpft oder über die API abgefragt werden sollen
(Paket P2.7 im Umsetzungsplan). Gemeindeergebnisse Sachsen-Anhalts (218 Gemeinden) liegen als Datei beim Landesamt, sind aber
noch nicht eingebunden.

## Lücken nach Priorität

| Nr. | Lücke | Umfang | Quelle | Stand |
|---|---|---|---|---|
| W1 | Landtagswahl Sachsen-Anhalt 2026 | 1 Wahl | Statistisches Landesamt | erledigt |
| W2 | Landtagswahlen 2026 in Baden-Württemberg, Rheinland-Pfalz, Mecklenburg-Vorpommern, Berlin | 4 Wahlen | Landeswahlleitungen, Dateien gefunden | als Nächstes |
| W3 | Landtagswahlen 2022 bis 2025 der übrigen zehn Länder | 10 Wahlen | Landeswahlleitungen | offen |
| W4 | USA 2026 (Repräsentantenhaus, Senat) | 2 Wahlen | amtliche Ergebnisse der Bundesstaaten bzw. Clerk of the House, sobald veröffentlicht | offen; im Register steht für 2026 nur die heutige Zusammensetzung (Stufe D) |
| W5 | Neuseeland 2026 | 1 Wahl | Electoral Commission (Seite mit Bot-Schutz, nicht umgehen) | offen, Quelle zu klären |
| W6 | Europawahl 2024 für alle 27 Staaten | 26 Staaten fehlen | Europäisches Parlament (Ergebnisdateien je Staat) | offen |
| W7 | E1 Stufe C und D: 193 nationale Wahlen ohne amtliche Quelle | 193 Wahlen | je Wahlbehörde; zuerst OECD-Staaten (Japan, Südkorea, Polen, Italien, Niederlande, Schweden …) | offen |
| W8 | E2 außerhalb Deutschlands (US-Bundesstaaten, Kanada, Österreich, Schweiz, Spanien …) | 290 Wahlen | je Region | später |
| W9 | Kommunalwahlen außerhalb NRW | alle | Landesämter | später |
| W10 | Wahlen in der Datenbank und über die API | alle | – | später (P2.7) |
