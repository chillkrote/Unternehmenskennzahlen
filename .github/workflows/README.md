# GitHub-Workflows

| Datei | Zweck | Takt (UTC) | Laufzeit |
|---|---|---|---|
| `marktdaten.yml` „Börsendaten Terminal“ | Tageskurse der Banken (`app/data/markt.json`); samstags Wochenkurse (`kurse_woche.json`); Bereich BÖR: Aktienindizes weltweit und große Unternehmen (`boerse.json`) | Mo–Fr 18:37, Sa 05:11, Mo–Fr 22:43 (UTC; GitHub startet Zeitpläne oft Stunden später) | ca. 3 min (Sa ca. 2 min, BÖR ca. 2 min) |
| `termine.yml` „Berichtstermine“ | Termine erfassen, fällige Berichte laden, montags Finanzkalender lesen | täglich 05:17, Mo–Fr 16:47 (UTC; GitHub startet Zeitpläne oft Stunden später) | ca. 3–4 min, montags +6 min |
| `prognosen.yml` „Prognosen“ | Konjunkturprognosen aller Prognosegeber (`volkswirtschaft/prognosen_international.csv`); montags zusätzlich OECD Economic Outlook, Istwerte, Prognosefehler | Mo–Fr 06:43 | ca. 5 min (Mo ca. 8 min) |
| `terminal.yml` „Terminal bauen“ | baut `bankterminal.html` und legt sie als Artifact und auf den Branch `terminal-dist` | nur auf Anforderung | ca. 0,5 min |
| `desktop-macos.yml` | macOS-App (.dmg) | von Hand, Tag `desktop-v*`, PR an `desktop/` | ca. 2 min, macOS zählt zehnfach |

## Aufbau

* **Daten-Updates und Terminal-Bau sind getrennt.** `marktdaten.yml` und `termine.yml` committen nur kleine Datendateien nach main und nur, wenn sich etwas geändert hat. Danach lösen sie `terminal.yml` aus. Das Terminal (8,6 MB) steht nicht mehr in main, sondern in einem einzigen Commit auf dem Branch `terminal-dist` (Force-Push, keine Historie) und als Workflow-Artifact (14 Tage). `app/dist/` in main ist ein eingefrorener Stand.
* **Schlanker Checkout.** `filter: blob:none` und Sparse-Checkout ohne `*.pdf` und `*.gz` (2,9 GB): rund 100 MB statt 3 GB, Checkout in 5 Sekunden. Der Terminal-Bau legt für die fehlenden PDFs leere Dateien in Originalgröße an (`.github/scripts/pdf_platzhalter.py`), damit die Dokumentlisten stimmen.
* **Gemeinsame Sperre.** `marktdaten.yml` und `termine.yml` teilen die Gruppe `daten-schreiben`, laufen also nie gleichzeitig. Ein dritter wartender Lauf ersetzt den zweiten (GitHub hält nur einen wartenden Lauf je Gruppe).
* **Push mit Wiederholung.** `.github/scripts/daten_pushen.sh` commitet nur die Datendateien, bei abgelehntem Push folgt Rebase und neuer Versuch (bis zu fünf); bei einem Konflikt mit zwischenzeitlichen Änderungen bricht das Skript ab (kein `-X theirs`), der nächste Lauf erzeugt die Daten neu. Vor dem Commit läuft `stammdaten/pruefe_ids.py`.
* **Teilausfälle.** Bricht bei Yahoo mehr als ein Drittel der Banken (bzw. mehr als zehn Prozent der Ticker bei den Wochenkursen) weg, bleibt die alte Datei liegen und der Lauf zeigt eine Warnung. Einzelne fehlende Ticker stehen unter `fehler` in den Dateien. Jeder Lauf schreibt eine Zusammenfassung (Seite des Laufs).
* **pip-Cache** über `setup-python`.

* **Schreiben nur auf main.** Daten-Commit, Push und Auslösen von `terminal.yml` laufen nur auf main. Von einem anderen Branch gestartet, sind `marktdaten.yml` und `termine.yml` Trockenläufe (Abruf und Zusammenfassung, kein Commit); `terminal.yml` baut dort nur das Artifact und veröffentlicht `terminal-dist` nicht.

## Minutenschätzung je Monat (Free-Plan: 2000 Linux-Minuten für private Repos)

Gemessen am Testlauf vom 27.10.2026 (Abruf inkl. Start je Job ca. 1 min aufgerundet).

| Workflow | Läufe/Monat | min je Lauf | Summe |
|---|---|---|---|
| Börsendaten Mo–Fr | 22 | 3 | 66 |
| Wochenkurse Sa | 4 | 3 | 12 |
| Berichtstermine 05:17 | 30 | 4 | 120 |
| Berichtstermine 16:47 Mo–Fr | 22 | 4 | 88 |
| Finanzkalender-Scan Mo | 4 | 6 | 24 |
| Terminal bauen (nach Datenänderung, ca. 2 je Tag) | 60 | 1 | 60 |
| **Summe** | | | **ca. 370** |

Das sind etwa 19 Prozent des Kontingents. Vorher wären es bei vollem 3-GB-Checkout und zweimal täglichem Terminal-Commit deutlich mehr gewesen, und main wüchse um bis zu 17 MB pro Tag. Die macOS-App zählt zehnfach: ein Lauf ca. 20 Kontingentminuten, nur bei Änderungen unter `desktop/`.

## Offen

* Die Desktop-App holt das Terminal weiter aus `app/dist/` in main (`desktop/main.js`, `DATEI_IM_REPO`). Umstellen auf `?ref=terminal-dist`, sobald alle Geräte die neue App haben; `desktop-macos.yml` könnte die Datei vor dem Bau von dort holen.

## Analyse: Erhebungen von GitHub Actions auslagern? (27.10.2026)

**Kurzfassung:** Die Minuten sind nicht der Engpass, der Speicherplatz im Repo ist es. Nach dem Umbau liegen die Workflows bei rund 370 von 2000 freien Minuten im Monat (Annahme: GitHub Free, privates Repo; unter Settings → Billing prüfbar). Das Repo ist 2,4 GB groß, davon 2,9 GB PDF-Inhalt (821 Dateien, im Schnitt 3,5 MB). Die Abrufliste für das Unternehmensregister umfasst 753 weitere Berichte; kämen sie alle ins Repo, wüchse es um etwa 2,6 GB und läge dann bei rund 5 GB, der Größe, ab der GitHub Verkleinern empfiehlt. Auslagern lohnt sich deshalb zuerst für die Dokumente, nicht für die Abrufe.

### Was belastet was

| Erhebung | Minuten/Monat | Repo-Wachstum | Bemerkung |
|---|---|---|---|
| Tageskurse Banken | ca. 66 | `markt.json` 1,4 MB je Änderung | Yahoo kann Rechenzentrums-IPs mit 429 drosseln; Schutz gegen Teilausfall ist eingebaut |
| Wochenkurse | ca. 12 | `kurse_woche.json` 1,5 MB | wöchentlich, unkritisch |
| Berichtstermine | ca. 208 | klein (CSV) | größter Posten bei den Minuten, vor allem wegen Yahoo je Ticker |
| Finanzkalender-Scan | ca. 24 | klein | montags, 6 min |
| Berichtsabruf | wenige | **groß: 1 bis 5 MB je PDF** | der eigentliche Wachstumstreiber; Unternehmenswebsites sperren Rechenzentrums-IPs teils (Bot-Schutz) |
| Terminal-Bau | ca. 60 | keines mehr (Branch `terminal-dist`) | erledigt |
| Hub-Exporte (EBA), Crawler, Lückenfüllung | nicht in Actions | große Rohdaten (CSV bis 12 MB) | laufen bisher einmalig in Claude-Sitzungen, Captcha-Fälle von Hand |

### Alternativen (alle ohne Bezahldienst)

| Option | Für | Gegen |
|---|---|---|
| **A. Actions im privaten Repo (jetzt)** | läuft, kein Secret nötig, ein Ort für Code und Daten | 2000 Min Deckel, Repo-Größe, Runner-IPs sind Azure-Rechenzentrum (Bot-Schutz) |
| **B. Öffentliches Daten-Repo mit Actions** | unbegrenzte Minuten für Standard-Runner; die Desktop-App bräuchte kein Token mehr | alles ist öffentlich: nur für Kurse, Termine, Terminal geeignet. **Nicht** für `governance/` (Personenprofile, DSGVO) und fraglich für gespiegelte Geschäftsberichte (Urheberrecht, auch wenn die Firmen sie frei anbieten) |
| **C. GitLab CI** | ähnlich A | Freikontingent kleiner (400 Min), Rechenzentrums-IPs, zweites System; keine Verbesserung |
| **D. Cloudflare Workers/Pages Cron** | zuverlässiger Takt, großzügig frei | Skripte sind Python (yfinance, pypdf), Workers sind JavaScript mit knappen Limits (u. a. 50 Unterabrufe je Lauf, wenig CPU-Zeit); Speicher (KV/R2) zusätzlich, R2 verlangt eine hinterlegte Zahlungsart; großer Umbau für wenig Gewinn |
| **E. Oracle Always-Free-VM oder Google e2-micro** | eigener Linux-Rechner, beliebige Laufzeit, Python wie bisher | Anmeldung mit Zahlungskarte, Konten ohne Last werden teils zurückgenommen, Wartung (Updates, Cron, Schlüssel), weiterhin Rechenzentrums-IP |
| **F. Robins Rechner / Mac-App im Hintergrund** | Wohnort-IP (am wenigsten Bot-Schutz und 429), Daten bleiben lokal, keine Minuten | läuft nur bei eingeschaltetem Gerät, Schlaf, kein Zeitplan-Garant; die App ist bewusst offline |
| **G. Claude-Routinen / Sitzungen** | gut für Unscharfes: Termine finden, Kalender lesen, PDFs prüfen, Captcha-Fälle begleiten | zählt gegen Robins Claude-Nutzung, nicht gegen Actions; für reines Herunterladen zu teuer und nicht deterministisch |

**Datenschutz und Secrets:** Personenprofile (`governance/`) gehören in kein öffentliches Repo und in keinen Fremddienst; sie bleiben im privaten Repo. Kurse, Termine und Terminal enthalten nichts Personenbezogenes. Jede Auslagerung außerhalb von GitHub braucht Schreib-Token für das Repo (Secret im Dienst); das ist bei A nicht nötig, bei D bis F schon.

### Empfehlung mit Stufenplan

1. **Jetzt (Stufe 0):** bei A bleiben. 19 % Auslastung braucht keine Auslagerung. Einmal pro Monat Billing-Seite ansehen.
2. **Stufe 1, vor dem Abruf der 753 Berichte:** Wachstum der PDFs bremsen. Neue Originale nicht mehr automatisch ins Repo committen, sondern das Skript ablegen lassen (Datei und SHA-256 bleiben in `index.csv`, die Datei selbst z. B. im angebundenen Google Drive, 15 GB frei) oder die Abrufliste nach Stufe A/B/C priorisieren und Obergrenze setzen (Repo unter 4 GB). Das ist die einzige Maßnahme, die wirklich Kapazität schafft.
3. **Stufe 2, nur wenn die Minuten über 60 % steigen:** Kurse, Termine und Terminal in ein **öffentliches** Daten-Repo (Variante B) verlegen, `governance/` und Dokumente bleiben privat. Vorher entscheidet Robin, ob öffentliche Daten gewollt sind.
4. **Stufe 3, optional:** Quellen, die Actions-IPs sperren (einzelne IR-Seiten, Yahoo bei 429), vom eigenen Rechner oder einer Oracle-VM abrufen (Variante E/F). Erst bei konkretem Bedarf.
5. **Nicht empfohlen:** GitLab CI (C) und Cloudflare Workers (D): zusätzlicher Pflegeaufwand ohne Nutzen gegenüber dem Ist-Zustand.
6. **Einmalige und unscharfe Erhebungen** (Hub-Exporte, Crawler, Lückenfüllung, Captcha-Berichte) weiter in Claude-Sitzungen, nicht in Actions.
