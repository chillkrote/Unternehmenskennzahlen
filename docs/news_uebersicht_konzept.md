# Konzept: News-Übersicht (Meldungen) im Terminal und auf der Weltkugel

Stand 08.11.2026 · Entscheidungsvorlage, noch nichts umgesetzt · Keine kostenpflichtigen Dienste

## 1. Ist-Stand (aus dem Repo gelesen)

- **Erzeugung:** `app/news_routen.py` fragt je Engstelle (`app/geo/routen/knoten.csv`) GDELT, bei Drosselung Google News RSS ab (letzte 14 Tage, Englisch/Deutsch). Ein Titel zählt, wenn er den Ort und ein Störungswort nennt. Höchstens 5 Titel je Engstelle. Ergebnis: `app/data/news_routen.json` (Stand 06.11.2026, 11 Engstellen mit Meldungen).
- **Rhythmus:** Workflow `weltkugel.yml` täglich 06:17 UTC; danach baut `terminal.yml` nur, wenn sich Daten geändert haben.
- **Darstellung an vier Stellen, jeweils eigener Code:**
  1. Karte: Engstelle als Raute (bernstein bei Meldung) plus Kreis mit „!“ (`rt-news`) plus Vorschaukarten „⚠ Name“ (`vorschauen()`, bis zu 4).
  2. Seitenleiste der Weltkugel: Block „Störungen an Engstellen“ mit „⚠“ (`stoerungBlock`, 6 Einträge).
  3. Terminal HDL, Panel „STÖ“: Liste ohne Symbol, mit Datum `TT.MM.JJJJ`.
  4. Terminal HDL, Panel „ENG“: Tabelle mit „⚠ “ vor dem Namen.
- Es gibt nur **einen** Meldungstyp (Störung an Engstellen). Andere „Neuigkeiten“ (z. B. „gerade gewählt“-Chip bei Wahlen, neue Berichte/Termine) laufen separat und mit eigenem Symbol.

## 2. Ursachen

### 2.1 Veraltete Meldungen
1. **Alter Stand bleibt ohne Altersprüfung.** Fällt eine Abfrage aus, übernimmt das Skript die alte Liste der Engstelle (`alt["meldungen"]`) unverändert und ohne Kennzeichnung. Dann stehen bis zu beliebig alte Titel weiter als „aktuell“ da; das Feld `fehler` wird in der Oberfläche nicht gezeigt.
2. **Kein Ablaufdatum in der Anzeige.** Die 14-Tage-Grenze gilt nur bei der Abfrage. Was im JSON steht, wird immer angezeigt, auch am 14. Tag oder später; die Oberfläche prüft das Datum nicht. Der Gotthard-Eintrag ist z. B. schon 12–14 Tage alt und hat dieselbe Rolle wie der von heute.
3. **Sortierung nach neuester Meldung, nicht nach Relevanz/Alter sichtbar.** Das Datum erscheint nur als `TT.MM.` (ohne Jahr, ohne „vor x Tagen“). Ein 12 Tage alter Titel sieht aus wie ein frischer.
4. **Momentaufnahme.** Die Artifact-Vorschau und die gebauten Dateien zeigen den Stand ihres letzten Baus; das Datum „Abruf“ steht nur klein im Fuß. Wer die Vorschau nach Tagen öffnet, sieht alte Meldungen ohne Warnung. Der Tageslauf holt zudem nur, wenn GitHub-Actions läuft; ein ausgefallener Lauf ist nirgends sichtbar.
5. **Datum der Quelle ist ungenau.** Bei Google News kommt nur das Veröffentlichungsdatum der Suchtreffer; Nachrichtenseiten schieben alte Artikel erneut nach vorn. Titel wie „Maersk reroutes via Suez“ bleiben Tage auf der Liste, obwohl der Vorgang erledigt ist.
6. **Zu weiter Treffer-Filter.** Wörter wie „threat“, „queue“, „restrictions“ oder „halt“ lassen auch Meldungen durch, die keine akute Störung sind.

### 2.2 Uneinheitliche Symbole
1. Dasselbe Ereignis hat vier Zeichen: bernsteinfarbene Raute, Kreis mit „!“, Textzeichen „⚠“ und in der Terminalliste gar keines.
2. „⚠“ ist ein Schriftzeichen und sieht je Betriebssystem/Schrift anders aus; auf der Karte ist es ein gezeichneter Kreis.
3. Es gibt keine Zuordnung nach Meldungstyp (Angriff, Sperrung, Wetter/Niedrigwasser, Streik, Stau). Alles wird als „Störung“ gezeigt; „Kuwait urges end to attacks“ und „Maersk reroutes“ sehen gleich aus.
4. Andere Neuigkeiten (Wahl „neu“-Chip, Termine, neue Berichte) benutzen eigene Marken, sodass keine gemeinsame „News“-Sprache entsteht.

## 3. Vorschlag

### 3.1 Datenmodell (eine Quelle für alle Anzeigen)
Eine Datei `app/data/meldungen.json` (Nachfolger von `news_routen.json`, Ablösung schrittweise) mit einheitlichen Einträgen:

| Feld | Inhalt |
|---|---|
| `id` | Hash aus URL |
| `typ` | `angriff`, `sperrung`, `wetter`, `streik`, `stau`, `sonst` (aus Störungswörtern, feste Tabelle) |
| `bereich` | `route` (jetzt), später `wahl`, `bericht`, `termin` |
| `ort_id` | Engstelle bzw. Bezugsobjekt |
| `titel`, `url`, `quelle`, `sprache` | wie bisher, Originaltitel unverändert |
| `veroeffentlicht` | Datum der Quelle |
| `erstmals_gesehen`, `zuletzt_gesehen` | vom Skript gesetzt (Tageslauf) |
| `stand` | `neu` (≤ 2 Tage), `aktuell` (≤ 7), `aelter` (≤ 14), danach `abgelaufen` |

Wichtig: `zuletzt_gesehen` wird nur gesetzt, wenn die Abfrage den Artikel erneut liefert. Bei Ausfall der Quelle bleibt der Eintrag stehen, wird aber als „Stand unsicher“ markiert (nicht still als aktuell).

### 3.2 Aktualität und Ablauf
- **Harte Obergrenze 14 Tage** nach `veroeffentlicht`, sowohl im Skript als auch in der Oberfläche (Prüfung beim Laden gegen das heutige Datum, damit auch eine alte Vorschau alte Einträge selbst ausblendet).
- **Kein Fallback auf alten Stand ohne Kennzeichnung:** Bei Ausfall bleiben nur Einträge mit `zuletzt_gesehen` ≤ 3 Tage; Kopfzeile zeigt „Abruf fehlgeschlagen, Stand dd.mm. hh:mm“.
- **Stempel „Stand“ gut sichtbar** in jeder Übersicht („Abruf vor 6 Std.“); ist er älter als 48 Std., gelbes Banner „Daten veraltet“.
- **Strengerer Filter:** Doppel-Treffer-Regel (Ort + Störungswort im Titel, Wörter wie `threat`, `queue`, `restrictions` nur zusammen mit Ort-Nähe), außerdem Titel-Duplikate über Quellen hinweg zusammenfassen (Ähnlichkeit, nicht nur die ersten 80 Zeichen).
- Weiter ohne Kosten: GDELT und Google News RSS, optional kostenlose RSS-Feeds der Seewarten/Verkehrsämter als dritte Quelle (später).

### 3.3 Einheitliche Symbole
Ein Symbolsatz, als SVG auf der Karte und im Terminal gleich (nicht als Schriftzeichen), Farbe nach Alter, Form nach Typ:

| Typ | Symbol | Wort |
|---|---|---|
| Angriff / Sicherheitslage | Dreieck mit „!“ | Angriff |
| Sperrung / Blockade | Kreis mit Balken | Sperrung |
| Wetter / Niedrigwasser | Tropfen | Wetter/Pegel |
| Streik | Faust bzw. gekreuzte Balken | Streik |
| Stau / Verzögerung | Uhr | Stau |
| Sonstiges | Kreis mit „i“ | Hinweis |

Farbe nur für Alter: neu = Bernstein voll, aktuell = Bernstein gedämpft, älter = grau. Eine Legende (Typ + Alter) steht einmal in der Seitenleiste. Die Hilfsfunktion `meldungSymbol(typ, stand)` liefert SVG für Karte (als Kartenbild), Seitenleiste, STÖ und ENG; keine eigenen ⚠-Zeichen mehr.

### 3.4 Struktur der Übersicht
- **Ein Panel „Meldungen“** statt vier verschiedener Listen, mit denselben Zeilen überall: `Symbol · Engstelle · Titel (Link) · Quelle · „vor 2 Tagen“ (Tooltip: 05.11.2026)`.
- **Gruppierung** standardmäßig nach Alter: „Heute/gestern“, „Diese Woche“, „Älter (bis 14 Tage)“; wählbar nach Engstelle oder Typ.
- **Ausblenden alter Meldungen:** Standard „bis 7 Tage“, Schalter „bis 14 Tage“. Ältere erscheinen nie. Leerer Zustand: „Keine aktuellen Meldungen. Letzter Abruf …“.
- **Karte:** Symbol nur bei Meldungen ≤ 7 Tage; ältere nur bei aktiviertem Schalter. Vorschaukarten zeigen höchstens drei, nur „neu“.
- **Tabelle ENG:** Spalte „Meldung“ mit Symbol, Alter und Titel der jüngsten Meldung statt „⚠“.

## 4. Umsetzungsschritte (jeweils ein kleiner PR)

1. **Datenmodell + Skript:** `news_routen.py` erweitern (Typ-Zuordnung, `zuletzt_gesehen`, Altersstufen, Ablauf, kein stiller Fallback, strengerer Filter); Tests mit Beispiel-Titeln (Reststand, Ausfall, Duplikate). `news_routen.json` bleibt als kompatible Ausgabe, damit nichts bricht.
2. **Anzeigelogik zentral:** eine Funktion `meldungen()` (Alter, Ausblenden, Gruppen, Symbol) in einer gemeinsamen Datei, von `globus.js` und `handel.js` genutzt.
3. **Symbole:** SVG-Satz, Legende, Ersatz aller „⚠“ und der „!“-Kreise.
4. **Übersicht:** Panel „Meldungen“ (Terminal + Seitenleiste) mit Gruppierung, „vor x Tagen“, Alters-Schalter, Banner „veraltet“.
5. **Betrieb:** Workflow zeigt bei Fehlern eine Zusammenfassung; optional Zweitlauf am Nachmittag (kostenlos in GitHub-Actions).
6. **Später (separat entscheiden):** weitere Bereiche (Wahlen, Berichtstermine) in dieselbe Übersicht aufnehmen.

## 5. Offene Entscheidungen für Robin

1. Reicht „nur Störungen an Engstellen“ als Inhalt, oder soll die Übersicht gleich andere Neuigkeiten (Wahlen, Berichte, Termine) bündeln?
2. Ablauf: Standard 7 Tage sichtbar, 14 Tage per Schalter. Passt das?
3. Symbolsatz wie in 3.3 (fünf Typen + „Hinweis“), oder lieber einheitlich ein Symbol mit Typ nur im Text?
4. Ältere Vorschau ohne Neubau: Hinweisbanner bei Daten über 48 Std. genügt, oder soll die Vorschau automatisch nach jedem Tageslauf neu veröffentlicht werden?
