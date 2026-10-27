# GitHub-Workflows

| Datei | Zweck | Takt (UTC) | Laufzeit |
|---|---|---|---|
| `marktdaten.yml` „Börsendaten Terminal“ | Tageskurse der Banken (`app/data/markt.json`); samstags Wochenkurse (`kurse_woche.json`) | Mo–Fr 18:30, Sa 05:00 | ca. 3 min (Sa ca. 2 min) |
| `termine.yml` „Berichtstermine“ | Termine erfassen, fällige Berichte laden, montags Finanzkalender lesen | täglich 05:20, Mo–Fr 16:20 | ca. 3–4 min, montags +6 min |
| `terminal.yml` „Terminal bauen“ | baut `bankterminal.html` und legt sie als Artifact und auf den Branch `terminal-dist` | nur auf Anforderung | ca. 0,5 min |
| `desktop-macos.yml` | macOS-App (.dmg) | von Hand, Tag `desktop-v*`, PR an `desktop/` | ca. 2 min, macOS zählt zehnfach |

## Aufbau

* **Daten-Updates und Terminal-Bau sind getrennt.** `marktdaten.yml` und `termine.yml` committen nur kleine Datendateien nach main und nur, wenn sich etwas geändert hat. Danach lösen sie `terminal.yml` aus. Das Terminal (8,6 MB) steht nicht mehr in main, sondern in einem einzigen Commit auf dem Branch `terminal-dist` (Force-Push, keine Historie) und als Workflow-Artifact (14 Tage). `app/dist/` in main ist ein eingefrorener Stand.
* **Schlanker Checkout.** `filter: blob:none` und Sparse-Checkout ohne `*.pdf` und `*.gz` (2,9 GB): rund 100 MB statt 3 GB, Checkout in 5 Sekunden. Der Terminal-Bau legt für die fehlenden PDFs leere Dateien in Originalgröße an (`.github/scripts/pdf_platzhalter.py`), damit die Dokumentlisten stimmen.
* **Gemeinsame Sperre.** `marktdaten.yml` und `termine.yml` teilen die Gruppe `daten-schreiben`, laufen also nie gleichzeitig. Ein dritter wartender Lauf ersetzt den zweiten (GitHub hält nur einen wartenden Lauf je Gruppe).
* **Push mit Wiederholung.** `.github/scripts/daten_pushen.sh` commitet nur die Datendateien, bei abgelehntem Push folgt Rebase und neuer Versuch (bis zu fünf).
* **Teilausfälle.** Bricht bei Yahoo mehr als ein Drittel der Banken (bzw. mehr als zehn Prozent der Ticker bei den Wochenkursen) weg, bleibt die alte Datei liegen und der Lauf zeigt eine Warnung. Einzelne fehlende Ticker stehen unter `fehler` in den Dateien. Jeder Lauf schreibt eine Zusammenfassung (Seite des Laufs).
* **pip-Cache** über `setup-python`.

* **Schreiben nur auf main.** Daten-Commit, Push und Auslösen von `terminal.yml` laufen nur auf main. Von einem anderen Branch gestartet, sind `marktdaten.yml` und `termine.yml` Trockenläufe (Abruf und Zusammenfassung, kein Commit); `terminal.yml` baut dort nur das Artifact und veröffentlicht `terminal-dist` nicht.

## Minutenschätzung je Monat (Free-Plan: 2000 Linux-Minuten für private Repos)

Gemessen am Testlauf vom 27.10.2026 (Abruf inkl. Start je Job ca. 1 min aufgerundet).

| Workflow | Läufe/Monat | min je Lauf | Summe |
|---|---|---|---|
| Börsendaten Mo–Fr | 22 | 3 | 66 |
| Wochenkurse Sa | 4 | 3 | 12 |
| Berichtstermine 05:20 | 30 | 4 | 120 |
| Berichtstermine 16:20 Mo–Fr | 22 | 4 | 88 |
| Finanzkalender-Scan Mo | 4 | 6 | 24 |
| Terminal bauen (nach Datenänderung, ca. 2 je Tag) | 60 | 1 | 60 |
| **Summe** | | | **ca. 370** |

Das sind etwa 19 Prozent des Kontingents. Vorher wären es bei vollem 3-GB-Checkout und zweimal täglichem Terminal-Commit deutlich mehr gewesen, und main wüchse um bis zu 17 MB pro Tag. Die macOS-App zählt zehnfach: ein Lauf ca. 20 Kontingentminuten, nur bei Änderungen unter `desktop/`.

## Offen

* Die Desktop-App holt das Terminal weiter aus `app/dist/` in main (`desktop/main.js`, `DATEI_IM_REPO`). Umstellen auf `?ref=terminal-dist`, sobald alle Geräte die neue App haben; `desktop-macos.yml` könnte die Datei vor dem Bau von dort holen.
