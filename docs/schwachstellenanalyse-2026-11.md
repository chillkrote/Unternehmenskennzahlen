# Schwachstellenanalyse der Projektstruktur

Stand 11.11.2026, 20:00 Uhr MEZ. Grundlage: `main` bei `68ff623` (Merge von PR #188), die Projektübersicht aus PR #189, die Workflow-Läufe der letzten Tage (GitHub-API), die von außen sichtbaren Antworten von `neu.sphaerae.de` und GitHub Pages sowie öffentliche DNS-Abfragen.

Dieser Bericht schlägt nur vor. Umgesetzt wurde nichts. Er enthält keine Zugangsdaten. Rechtliche Einschätzungen sind eine fachliche Vorprüfung und keine Rechtsberatung.

## 1. Das Wichtigste in Kürze

Die Technik des neuen Servers ist ordentlich gebaut (nur lesende Datenbankrolle, Zeitlimits, kein offener Datenbankport, SSH nur mit Schlüssel, Lizenzprüfung im Build). Die größten Schwachstellen liegen woanders:

1. **Das Projekt ist bereits öffentlich, obwohl es als „noch nicht live“ behandelt wird.** Das Repo ist öffentlich und GitHub Pages liefert die volle Fassung aus. Alle Lizenz- und Datenschutzentscheidungen (E1 bis E6) wurden bisher nur für den neuen Server getroffen. Auf Pages stehen heute Yahoo-Daten, Personenprofile mit Vergütung und ein Impressum mit Platzhaltern (K1 bis K3).
2. **Wer auf `main` schreiben kann, kann den Server übernehmen**, sobald der tägliche Update-Timer läuft. `main` ist ungeschützt, fünf Workflows schreiben direkt darauf, und der Server führt den Stand mit Root-gleichen Rechten aus (K4).
3. **Es gibt nur eine Kopie von allem**, nämlich das GitHub-Konto. Keine belegte zweite Kopie des Repos (3,3 GB mit rund 1.000 Originaldokumenten), kein Offsite-Backup, kein aktiver Backup-Timer (K5, H2).
4. **Fehler bleiben unbemerkt.** Der Workflow „Live-Kurse“ ist in allen neun zuletzt sichtbaren Läufen gescheitert, drei weitere Zeitplan-Workflows sind seit ein bis zwei Tagen rot oder hängen, und niemand wurde benachrichtigt (H1).
5. **Der Änderungsweg hat keine Sicherung.** Kein Branch-Schutz, keine Pflichtprüfungen, rund 189 Pull Requests in 16 Tagen bei einem einzigen Prüfer (H3).

Empfohlene Reihenfolge in Abschnitt 6, offene Entscheidungen für Robin in Abschnitt 7.

## 2. Methode und Grenzen

| Geprüft | Wie |
|---|---|
| Repo-Inhalt | Checkout von `main` ohne PDFs; Lesen von `server/`, `.github/`, `app/`, `governance/`, `docs/` |
| Workflows | Dateien und die letzten rund 30 Läufe je Workflow samt Fehlerprotokollen |
| GitHub Pages | Abruf der Startseite und Auswertung des ausgelieferten HTML |
| Server | nur von außen: Antwortköpfe von `neu.sphaerae.de`, Health-Endpunkt, DNS |
| Einstellungen des Repos | Sichtbarkeit und `protected` über die API |

Nicht prüfbar und deshalb als **(unklar)** markiert: der innere Zustand des Servers (kein SSH-Zugang), ob der Backup-Timer inzwischen eingerichtet wurde, Zwei-Faktor-Anmeldung und Wiederherstellungscodes der Konten, Secret-Scanning-Einstellungen, die Git-Historie auf versehentlich eingecheckte Geheimnisse (nur flacher Klon; im aktuellen Stand fand eine Mustersuche nichts), eine vollständige XSS- und Barrierefreiheitsprüfung der Oberfläche.

Aufwand: **S** unter zwei Stunden, **M** ein halber bis ganzer Tag, **L** mehrere Tage. Gemeint ist die Arbeit in Claude-Sitzungen; wo Robin selbst etwas tun muss, steht es dabei.

## 3. Was gut gelöst ist

Damit die Liste unten nicht verzerrt: Die API verbindet sich mit einer Rolle, die nur lesen darf, jede Abfrage hat ein Zeitlimit, die Datenbank hat keinen veröffentlichten Port, der API-Container läuft mit schreibgeschütztem Dateisystem und ohne Root. SQL-Abfragen sind in der Stichprobe durchgehend parametrisiert, Sortier- und Feldnamen kommen aus festen Listen. Die Server-Pakete sind auf feste Versionen gesetzt. Der Build prüft die Lizenzstufe, bevor ausgeliefert wird. Die Einrichtungsskripte sperren Root- und Passwort-Login, schalten Firewall, fail2ban und automatische Sicherheitsupdates ein. Zeitreihen tragen Gültigkeitszeiträume (Vintage), Unternehmen haben feste IDs mit Prüfung vor jedem Daten-Commit. Das ist eine solide Basis.

## 4. Befunde nach Schweregrad

### Kritisch

#### K1 Lizenzentscheidungen gelten nur für den Server, veröffentlicht wird aber schon über Pages und das Repo

* **Beleg:** GitHub-API meldet `visibility: public`. Die Startseite `https://chillkrote.github.io/Unternehmenskennzahlen/` liefert 72,5 MB HTML (zuletzt geändert 11.11., 12:58 UTC). Darin stehen 13.146 Werte mit der Quellenangabe „Yahoo Finance (Sekundärquelle; Originalabgleich offen)“ sowie Tages- und Wochenkurse aus Yahoo. `docs/datenquellen.md` stuft Yahoo und UN Comtrade als „kritisch“ ein und sagt: „Bis zur Entscheidung läuft nichts davon öffentlich; GitHub Pages und der lokale Betrieb bleiben, wie sie sind.“ Der Satz stimmt nur, wenn Pages nicht öffentlich wäre. Im Repo liegen außerdem rund 1.000 Geschäftsberichte als PDF; `README.md` Zeile 37 begründet das mit „das Repository ist privat“. Der Zweig `daten-live` veröffentlicht Yahoo-Kurse zusätzlich über `raw.githubusercontent.com`.
* **Risiko:** Verstoß gegen Nutzungsbedingungen (Yahoo, Comtrade, IPU Parline nur nicht kommerziell mit gleicher Lizenz), Urheberrecht an gespiegelten Berichten. GitHub sperrt Repos nach Beschwerden; dann wäre auch die einzige Kopie betroffen (K5).
* **Vorschlag:**
  1. Pages sofort auf dieselbe Fassung umstellen, die der Server bekommt (`--oeffentlich`, Lizenzprüfung im Workflow), oder Pages bis zur Klärung abschalten. Aufwand S.
  2. Grundsatzentscheidung zur Sichtbarkeit (siehe E-A in Abschnitt 7). Meine Empfehlung: Repo teilen in ein öffentliches Code-Repo und ein privates Daten- und Dokumenten-Repo. Aufwand L.
  3. E2 bis E6 jetzt entscheiden, weil sie faktisch schon wirken. Aufwand für Robin: eine Stunde.
* **Nutzen:** beseitigt das größte rechtliche Risiko und schützt zugleich das Konto.

#### K2 Personenbezogene Daten sind weltweit abrufbar, ohne Rechtsgrundlage und ohne Datenschutzhinweise

* **Beleg:** `governance/` enthält 1.602 Personen (`gremien_mitglieder.csv`), 2.006 Vergütungszeilen mit Personenbezug (`verguetung.csv`), Werdegänge und externe Mandate. `berechnungen/geschlecht_schaetzung.csv` schätzt für 1.658 Personen das Geschlecht aus „Vorname/Recherche“, obwohl `governance/README.md` festlegt: „Das Geschlecht wird nicht aus Vornamen geschlossen“. 32 Zeilen kennzeichnen Personen als Gewerkschaftsvertreter; Gewerkschaftszugehörigkeit ist eine besondere Kategorie nach Art. 9 DSGVO. Die Daten liegen im öffentlichen Repo, in der Pages-Fassung (124 Unternehmen mit Mitgliederlisten, 90 mit Vergütung) und über `/companies/{id}/profile` in der Server-API. `.github/workflows/README.md` hält selbst fest: „Personenprofile (governance/) gehören in kein öffentliches Repo“.
* **Risiko:** Die Angaben stammen aus Pflichtveröffentlichungen, das macht die Weiterverarbeitung nicht automatisch zulässig. Es fehlen dokumentierte Interessenabwägung (Art. 6 Abs. 1 lit. f), Information der Betroffenen oder die begründete Ausnahme (Art. 14), ein Weg für Auskunft und Löschung, eine Datenschutzerklärung. Geschätzte Merkmale je Person sind zudem ein Richtigkeitsproblem (Art. 5).
* **Vorschlag:**
  1. Kurzfristig: `geschlecht_schaetzung.csv` nicht personenbezogen veröffentlichen (nur die Quote je Unternehmen), das Gewerkschaftsmerkmal je Person entfernen oder nur als Anzahl führen. Aufwand S.
  2. `governance/` aus dem öffentlichen Repo und aus der Pages-Fassung nehmen, bis die Abwägung steht. Aufwand S bis M.
  3. Die Dateien bleiben in der Git-Historie. Bereinigung nur per Umschreiben der Historie; das ist nicht umkehrbar und braucht Robins ausdrückliche Freigabe. Aufwand M.
  4. Abwägung, Datenschutzerklärung, Kontaktweg und Löschprozess schreiben; für Organmitglieder börsennotierter Unternehmen ist eine Veröffentlichung gut begründbar, für Arbeitnehmervertreter deutlich schwächer. Aufwand M, mit rechtlicher Prüfung.
* **Nutzen:** nimmt das größte Datenschutzrisiko heraus, ohne die Auswertungen zu verlieren.

#### K3 Öffentliche Seite ohne Impressum und Datenschutzerklärung, mit Google Fonts von Google-Servern

* **Beleg:** In der ausgelieferten Pages-Seite steht dreimal der Platzhalter „Vorname Nachname“ und zweimal „adresse@beispiel.de“ (`app/seiten/impressum.md` ist unausgefüllt). `app/src/terminal.html` Zeile 3 und 4 lädt die Schrift von `fonts.googleapis.com`; dabei geht die IP-Adresse jedes Besuchers an Google (dazu LG München I, 20.01.2022, 3 O 17493/20). Weitere Abrufe bei Dritten: Kartenkacheln von `tiles.openfreemap.org`, Live-Daten von `raw.githubusercontent.com`. Die IP-Abfrage bei geojs.io läuft bereits nur auf Knopfdruck, das ist gut gelöst.
* **Vorschlag:** Schriften ins Repo legen und selbst ausliefern (S). Impressum und Datenschutzerklärung ausfüllen, bevor irgendeine Fassung öffentlich bleibt; die Angaben muss Robin liefern (S). Drittabrufe in der Datenschutzerklärung nennen oder Kacheln später selbst hosten (M bis L, erst bei Bedarf).
* **Nutzen:** beseitigt ein verbreitetes Abmahnrisiko mit wenig Aufwand.

#### K4 Lieferkette: Schreibzugriff auf `main` bedeutet Root auf dem Server

* **Beleg:** `01-haerten.sh` gibt dem Benutzer `sphaerae` `NOPASSWD:ALL`, `02-docker.sh` nimmt ihn in die Docker-Gruppe. `04-timer.sh` startet täglich `aktualisieren.sh`; das Skript macht `git reset --hard origin/main` und führt danach Code aus dem Repo aus (`app/build.py`, Docker-Build, sich selbst). `main` hat keinen Schutz (`protected: false`). Neun Workflows haben `contents: write`, fünf davon pushen direkt nach `main` (`marktdaten`, `termine`, `prognosen`, `weltkugel`, `europa`). Alle Actions sind nur per Versionsmarke eingebunden (`actions/checkout@v5`), nicht per Commit-Hash; `live.yml` installiert `yfinance` ohne Version.
* **Risiko:** Ein kompromittiertes GitHub-Konto, eine manipulierte Action oder ein manipuliertes Python-Paket in einem Daten-Workflow genügt, um beliebigen Code auf dem Server als Root auszuführen. Heute läuft das Update noch von Hand, das Risiko wird mit dem Timer scharf.
* **Vorschlag, vor dem Einschalten von `04-timer.sh`:**
  1. Der Server zieht nicht `main`, sondern einen eigenen Zweig oder signierte Marken (`deploy`), den nur Robin setzt. Aufwand S.
  2. Daten-Workflows schreiben nicht mehr nach `main`, sondern in einen Datenzweig; der Server liest Daten von dort, Code von `deploy`. Aufwand M.
  3. `sudo` für `sphaerae` auf die wenigen nötigen Befehle begrenzen oder das Update als eigener Dienstbenutzer ohne `sudo` fahren. Aufwand S.
  4. Actions auf Commit-Hashes festlegen, Pakete in Workflows versionieren, Dependabot einschalten. Aufwand S.
* **Nutzen:** trennt „Daten ändern“ von „Code auf dem Server ausführen“. Das ist die wichtigste technische Sicherheitsmaßnahme.

#### K5 Einzige Kopie: Fällt das GitHub-Konto aus, ist alles weg

* **Beleg:** Die Datenbank wird aus Repo-Dateien neu aufgebaut, das Repo ist also das eigentliche Vermögen (API: 3,3 GB). Eine zweite Kopie ist nirgends dokumentiert **(unklar, ob lokal eine vollständige Kopie mit PDFs liegt)**. Server und Arbeitssitzungen halten nur Teil-Checkouts ohne PDFs.
* **Vorschlag:** wöchentlicher vollständiger Spiegel (`git clone --mirror`) auf Robins Rechner oder eine externe Platte, zusätzlich auf einen zweiten Git-Anbieter als privates Repo. Zwei-Faktor-Anmeldung und ausgedruckte Wiederherstellungscodes für GitHub prüfen (Robin, 15 Minuten). Aufwand S.
* **Nutzen:** macht aus einem Totalverlust eine Unannehmlichkeit.

### Hoch

#### H1 Keine Überwachung, keine Benachrichtigung

* **Beleg (Läufe auf `main`):**

  | Workflow | Befund | Ursache laut Protokoll |
  |---|---|---|
  | Live-Kurse | 9 von 9 Läufen gescheitert | `FileNotFoundError: app/data/live.json` |
  | Weltkugel-Daten | 10.11. und 11.11. nach 75 Minuten abgebrochen | hängt nach HTTP 429 und 504 der Quellen, kein Zeitlimit je Abruf |
  | Anreicherung Kennzahlen | 10.11. und 11.11. gescheitert | Push bricht nach 29 Minuten mit HTTP 500 ab |
  | Prognosen | 11.11. gescheitert | `apt-get install poppler-utils` |
  | Terminal bauen | letzter Lauf auf `main` rot | Browser-Test „Länderauswahl“; Pages wurde deshalb nicht aktualisiert |

  Auffällig auch: „Live-Kurse“ ist für alle 30 Minuten geplant, GitHub hat zuletzt etwa drei Läufe am Tag gestartet. In den Workflows steht neunmal `continue-on-error`, Teilausfälle färben den Lauf also nicht rot. Für den Server gibt es keinen externen Erreichbarkeitstest (in `docs/betrieb.md` nur als Idee), die systemd-Dienste haben kein `OnFailure`.
* **Vorschlag:**
  1. Ein täglicher Wächter-Workflow, der gescheiterte und überfällige Läufe sowie veraltete Datendateien in einem einzigen Issue zusammenfasst (GitHub schickt dann eine Mail). Aufwand S.
  2. Externer Ping auf `/api/v1/health` und ein „Totmannschalter“ für Backup und Update (kostenlose Stufe eines Ping-Dienstes). Aufwand S, Robin legt das Konto an.
  3. Die fünf konkreten Fehler oben beheben, jedem Abruf ein Zeitlimit geben. Aufwand M.
  4. `/data-quality` um eine Ampel erweitern, die der Wächter abfragt. Aufwand S.
* **Nutzen:** Ausfälle fallen nach Stunden auf statt nach Wochen.

#### H2 Sicherung und Wiederherstellung sind nicht belegt

* **Beleg:** Laut Stand vom 11.11. ist `04-timer.sh` nicht ausgeführt. Sicherungen liegen unverschlüsselt auf demselben Server (`server/backup/`, 14 Tage). Eine Offsite-Kopie fehlt. Eine Probe-Wiederherstellung auf dem Server ist nicht dokumentiert **(unklar)**. Die Caddy-Zertifikate und `server/.env` werden nicht gesichert.
* **Vorschlag:** Backup-Timer getrennt vom Update-Timer einschalten (der Update-Timer erst nach K4). Offsite verschlüsselt mit restic nach Google Drive oder einem zweiten Ort. Einmal im Quartal Wiederherstellung auf einem leeren System üben und die Dauer notieren. `.env` gehört in die Passwortverwaltung (ist laut Notiz der Fall). Aufwand M.
* **Nutzen:** Ein Serververlust kostet dann eine Stunde statt einen Tag. Da die Datenbank aus dem Repo neu entsteht, ist K5 wichtiger als dieser Punkt.

#### H3 Änderungsweg ohne Sicherungen

* **Beleg:** Kein Branch-Schutz auf `main`. `server.yml` läuft nur bei bestimmten Pfaden und nicht bei Pushes auf `main`. `main` war zeitweise rot und es wurde weiter gemergt. 174 Zweige liegen im Repo. Seit dem 26.10. sind rund 189 Pull Requests entstanden, alle von Claude-Sitzungen, einziger Prüfer ist Robin.
* **Risiko:** Bei diesem Tempo ist eine inhaltliche Prüfung nicht leistbar. Fehler in Daten und Code kommen ungeprüft durch; die Tests sind die einzige echte Kontrolle und sind nicht verpflichtend.
* **Vorschlag:** Regelwerk für `main`: nur per Pull Request, Pflichtprüfungen „Stammdaten“, „Server“, „Terminal“, gemergte Zweige automatisch löschen (Robin, 15 Minuten in den Einstellungen; setzt K4 Punkt 2 voraus, weil Workflows sonst nicht mehr nach `main` pushen können). Alte Zweige aufräumen. Für PRs eine kurze feste Prüfliste (Datenänderung mit Vorher-Nachher-Zahlen, betroffene Ansichten). Aufwand S bis M.
* **Nutzen:** rote Stände erreichen `main` nicht mehr; Robins Prüfung wird auf das Wesentliche gelenkt.

#### H4 Server-Update ohne vollständigen Rückweg

* **Beleg (`aktualisieren.sh`, `pruefen.sh`):** Zurückgestellt wird bei einem Fehler nur die Oberfläche. Der Code-Stand (`git reset --hard`), das neu gebaute API-Abbild und die Datenbank (jeder ETL-Lauf löscht und lädt Tabellen neu, Migrationen laufen vorwärts) bleiben auf dem neuen Stand. `pruefen.sh` wertet HTTP 401 als Erfolg; bei eingeschaltetem Seitenschutz wird also nur geprüft, dass Caddy antwortet. Das Skript überschreibt sich während des Laufs selbst. Alte Docker-Abbilder werden nie gelöscht **(Plattengröße unklar)**. Der ETL läuft als Datenbank-Superuser.
* **Vorschlag:** Abbild je Commit kennzeichnen und beim Fehlschlag das vorige starten. Prüfung von innen gegen die API (`docker compose exec`), mit inhaltlichen Erwartungen (Anzahl Unternehmen, jüngster Importlauf). ETL in eine Schattentabelle oder ein zweites Schema laden und erst nach Prüfung umschalten. `docker image prune` und eine Plattenwarnung. Eigene ETL-Rolle statt `postgres`. Aufwand M bis L.
* **Nutzen:** Ein fehlgeschlagenes nächtliches Update lässt die Seite auf dem alten, funktionierenden Stand.

#### H5 Datenqualität: großer Anteil ungeprüfter Sekundärdaten

* **Beleg:** 4.457 von 4.664 Abschlüssen in der Server-Datenbank stammen aus Yahoo (`docs/audit-2026-11.md`, E6 offen). 16 Reihen haben veraltete Gebiete (`oecd_inflation`: 27 Länder). Vor einem Daten-Commit läuft nur die ID-Prüfung; es gibt keine Formatprüfung der `app/data/*.json` und keine fachlichen Regeln (Aktiva gleich Passiva, Vorzeichen, Sprünge gegenüber dem Vorjahr, Einheiten). Im Repo liegt ein Ordner `undefined/` mit zwei Bildern, offenbar ein Skriptfehler.
* **Vorschlag:** Datenverträge je Datei (Pflichtfelder, Typen, Wertebereiche) als Prüfung in jedem Daten-Workflow. Plausibilitätsregeln mit Bericht statt stillem Übernehmen. Herkunft und Prüfstatus je Wert in der Oberfläche sichtbar halten. Originalquellen (ESEF, SEC, DART) zuerst für die meistgenutzten Unternehmen nachziehen. Aufwand M für die Prüfungen, L für die Originaldaten.
* **Nutzen:** Vertrauen in die Zahlen ist der Kern des Produkts.

#### H6 Keine Lizenz für das eigene Werk, keine Quellen- und Lizenzseite

* **Beleg:** Im Repo fehlt eine `LICENSE`. Rechtlich gilt damit „alle Rechte vorbehalten“, obwohl der Code öffentlich ist. Mehrere Quellen verlangen Namensnennung an der Ansicht (CC BY, dl-de/by-2-0, „© WTO“), DAWUM verlangt Weitergabe der Tabelle unter ODbL, IPU Parline unter CC BY-NC-SA.
* **Vorschlag:** Lizenz für Code und getrennt für eigene Daten festlegen (Entscheidung Robin). Eine Seite „Quellen und Lizenzen“ aus `server/katalog/datenquellen.csv` erzeugen und in der Fußleiste verlinken. Aufwand S bis M.

#### H7 Abhängigkeit von einer Person und je einem Konto

* **Beleg:** GitHub-Konto, netcup-Konto mit Domain, ein SSH-Schlüssel auf einem Rechner, eine Passwortverwaltung, persönliche API-Schlüssel (ENTSO-E, OpenDART, Harvard Dataverse) und das Claude-Projekt, dessen Notizen faktisch das Betriebshandbuch sind.
* **Vorschlag:** Ein Notfallblatt (wo liegt was, wie kommt man hinein, was kostet wann), getrennt von den Passwörtern aufbewahrt. Zweiter SSH-Schlüssel an sicherem Ort; die netcup-Konsole als Rückweg dokumentieren. Automatische Verlängerung der Domain prüfen. Liste der Schlüssel mit Ablaufdatum. Betriebswissen aus den Projektnotizen in `docs/betrieb.md` überführen. Aufwand S bis M, überwiegend Robin.

### Mittel

#### M1 Härtung der Website

* Keine Content-Security-Policy für die Website. `server/plattform/main.py` verweist darauf, dass Caddy sie setzt; im `Caddyfile` steht keine. Auch `frame-ancestors` fehlt für die Seiten.
* Die Oberfläche setzt an vielen Stellen HTML aus Daten zusammen (`innerHTML`: `globus.js` 25 Stellen, `unternehmen.js` 12). Ein Teil der Daten kommt aus fremden Quellen (Nachrichtenüberschriften, Wikipedia). Eine Maskierungsfunktion ist vorhanden; ob sie überall greift, habe ich nicht vollständig geprüft **(unklar)**. Eine CSP wäre die zweite Verteidigungslinie.
* `docker-compose.yml` und `Caddyfile` enthalten einen Standard-Passworthash für den Seitenschutz. Stünde `SEITENSCHUTZ=an` ohne eigenen Hash, gälte ein Hash, den jeder im öffentlichen Repo lesen kann. Besser: ohne eigenen Hash nicht starten.
* Die Passwortabfrage rechnet bcrypt mit Kostenfaktor 14. Ob Caddy das Ergebnis zwischenspeichert, sollte geprüft werden; sonst kostet jede Anfrage spürbar Rechenzeit und der kleine Server lässt sich leicht auslasten **(unklar)**.
* Der Kommentar „Caddy begrenzt zusätzlich“ zur Ratenbegrenzung stimmt nicht; statische Dateien sind unbegrenzt.
* `/api/v1/docs` lädt die Swagger-Oberfläche von einem fremden CDN.
* Für die Testadresse fehlt `X-Robots-Tag: noindex`, falls der Seitenschutz einmal aus ist.

Vorschlag: CSP und fehlende Köpfe im Caddyfile, Standard-Hash entfernen, Schutz gegen Dauerabfragen. Aufwand M (die CSP braucht Tests wegen der eingebetteten Skripte).

#### M2 Abhängigkeiten und Geheimnisse

Actions nur per Versionsmarke, Workflow-Pakete mit offenen Bereichen (`yfinance>=0.2.40`), Docker-Abbilder per Marke, `npm install playwright` ohne Version, kein Dependabot. Secret-Scanning mit Push-Schutz ist für öffentliche Repos kostenlos **(Einstellung unklar)**. Die vollständige Historie sollte einmal mit einem Werkzeug wie gitleaks durchsucht werden. Aufwand S.

#### M3 Größe und Aufbau des Repos

3,3 GB, davon der Großteil PDFs. `app/dist/` trägt zweimal 50 MB als „eingefrorenen Stand“. `app/data/` (52 MB, `unternehmen.json` allein 22 MB) wird von Workflows laufend neu geschrieben, jede Fassung bleibt in der Historie. Der gescheiterte Push der Anreicherung (HTTP 500 nach 29 Minuten) kann damit zusammenhängen **(unklar)**. Vorschlag: Dokumente aus Git herausnehmen (Ablage mit Prüfsumme in `index.csv`, wie schon in `.github/workflows/README.md` als Stufe 1 empfohlen), erzeugte Daten in einen eigenen Zweig oder nur noch in die Datenbank, `app/dist/` und `undefined/` entfernen. Aufwand M bis L, passt zur Trennung aus K1.

#### M4 Wartbarkeit

313 Python-Dateien, davon 25 Testdateien. Sehr große Einzeldateien (`globus.js` 2.445 Zeilen, `wahlen_daten.py` 2.114, `landtagswahlen.py` 1.091). Kein Linter, keine Formatierung, keine Typprüfung in der CI. Zwei Auslieferungswege (eingebettet für Pages, API für den Server) bedeuten doppelte Pfade in der Oberfläche. Die Daten fließen von Dateien über JSON-Pakete in die Datenbank; die Datenbank ist abgeleitet, nicht führend, was jede Korrektur an zwei Stellen erfordert. Vorschlag: ruff und ein JS-Linter als Pflichtprüfung (S), Zieldatum für das Ende der eingebetteten Fassung (Entscheidung), danach große Dateien schrittweise teilen (L).

#### M5 Widersprüche in der Dokumentation

* `README.md` und `docs/website.md` nennen das Repo privat; es ist öffentlich.
* `docs/website.md` und die Projektübersicht nennen `chillkrote.github.io/unternehmenskennzahlen`; diese Adresse liefert 404, erreichbar ist nur die Schreibweise mit großem U.
* `.github/workflows/README.md` rechnet mit dem Minutenkontingent eines privaten Repos und führt `terminal.yml` als „nur auf Anforderung“; der Workflow läuft bei jedem Push.
* Die Projektnotiz „AAAA fehlt noch“ ist überholt: `neu.sphaerae.de` hat inzwischen einen IPv6-Eintrag.

Vorschlag: mit PR #189 zusammen bereinigen; ein Abschnitt „Stand der Dinge“ an einer einzigen Stelle. Aufwand S.

#### M6 Leistung

Die Pages-Fassung überträgt 13,4 MB komprimiert und entpackt 72,5 MB in den Browser; auf Telefonen ist das kaum benutzbar. Der `<title>` steht im Körper statt im Kopf. Die Server-Fassung ist mit 1,7 und 5,2 MB deutlich besser. Auf dem Server teilen sich PostgreSQL, API und Caddy 2 GB Arbeitsspeicher, die API läuft als ein Prozess mit höchstens zehn Datenbankverbindungen; für den Start reicht das, eine Lastmessung fehlt. Der ETag spart Übertragung, nicht die Datenbankabfrage. Vorschlag: Lasttest vor dem Livegang (S), Zwischenspeicher in Caddy für Listenantworten (M), Pages-Fassung ablösen.

#### M7 Datenaktualisierung

GitHub-Zeitpläne starten unzuverlässig und teils Stunden später. Die Daten gelangen nur durch ein Update von Hand auf den Server. Yahoo und andere Quellen drosseln Rechenzentrumsadressen (429 im Protokoll). Bei öffentlichen Repos schaltet GitHub Zeitpläne nach 60 Tagen ohne Aktivität ab. Vorschlag: Abrufe wie in `docs/architektur.md` geplant auf den Server verlegen (systemd-Timer), je Quelle ein erwartetes Intervall hinterlegen und über H1 überwachen. Aufwand L, schrittweise.

#### M8 Stabilität der API

Der Pfad `/api/v1` ist gut gewählt. Es fehlen eine Zusage, was sich innerhalb von v1 ändern darf, ein Änderungsprotokoll, ein Test, der die OpenAPI-Beschreibung gegen ungewollte Änderungen sichert **(nicht gefunden)**, und ein Konzept für Vielnutzer (Schlüssel, Kontingente). Fehlercodes sind deutsch, Feldnamen englisch. Aufwand S für Zusage und Schnappschuss-Test.

#### M9 Domain und DNS

`sphaerae.de` zeigt auf eine andere Adresse als der Server (vermutlich die Platzhalterseite des Anbieters), `www.sphaerae.de` hat keinen Eintrag. Es gibt keinen CAA-Eintrag, kein DNSSEC und keine Mail-Einträge (MX, SPF, DMARC); ohne SPF und DMARC lässt sich die Domain leicht als Absender fälschen, und das Impressum braucht eine erreichbare Adresse. Vorschlag: CAA auf Let's Encrypt, SPF und DMARC auch ohne Mailbetrieb („sendet keine Mail“), `www` als Weiterleitung, HSTS erst nach dem Umzug auf Subdomains ausdehnen. Aufwand S, Robin im netcup-Kundenbereich.

#### M10 Tests und CI

Die API hat 115 Tests gegen eine echte Datenbank, das ist gut. Die Oberfläche hat nur Browser-Schnelltests, die zeitweise rot sind und dann die Veröffentlichung blockieren. Die Abrufskripte, also der fehleranfälligste Teil, sind kaum getestet (Tests gibt es für ENTSO-E, Handel, Landtagswahlen). Keine Abdeckungsmessung. Vorschlag: aufgezeichnete Antworten der Quellen als Testdaten für die Abrufskripte, instabile Browser-Tests reparieren oder als Warnung führen. Aufwand M bis L.

### Niedrig und Ausblick

| Nr. | Thema | Befund | Vorschlag | Aufwand |
|---|---|---|---|---|
| N1 | Barrierefreiheit | Karte und Diagramme ohne Textalternative, Bedienung stark mausorientiert; ARIA-Angaben sind teilweise vorhanden. Nicht systematisch geprüft. Das Barrierefreiheitsstärkungsgesetz dürfte für ein kostenloses Informationsangebot nicht greifen **(nicht geprüft)**. | automatische Prüfung (axe) in die Browser-Tests, Tabellenansicht als Alternative zur Karte, Tastaturbedienung | M |
| N2 | Mobil | Umbruchregeln sind vorhanden; die Pages-Fassung ist für Mobilgeräte zu groß. | nach Ablösung der eingebetteten Fassung mit echten Geräten testen | S |
| N3 | Suchmaschinen | Eine Seite mit Sprungmarken, keine Beschreibung im Kopf, keine `robots.txt`, keine Sitemap, keine eigenen Adressen je Unternehmen oder Land. | erst entscheiden, ob Auffindbarkeit gewollt ist; dann vom Server erzeugte Seiten je Unternehmen und Land | L |
| N4 | Nutzerverwaltung | Keine Konten; Merklisten liegen im Browser (18 Zugriffe auf lokalen Speicher). | so lange wie möglich ohne Konten bleiben (keine Passwörter, kaum DSGVO-Last); Export und Import der Merkliste als Datei | S |
| N5 | Kosten | Heute rund 4 € im Monat plus Domain. Risiken: Bei privatem Repo zählen Actions-Minuten (allein „Live-Kurse“ rund 1.000 von 2.000); Pages hat eine weiche Grenze von 100 GB Verkehr im Monat, das wären bei 13,4 MB je Aufruf rund 7.500 Aufrufe; die Claude-Nutzung ist der eigentliche laufende Aufwand. | Kostenblatt mit Schwellen in `docs/betrieb.md` | S |
| N6 | Skalierung | „Alles löschen und neu laden“ im ETL und 22 MB Profil-JSON skalieren nicht auf zehn Jahre Historie für 32.600 Unternehmen. | inkrementeller Import je Quelle, Profile als Tabellen statt JSON-Paket | L |
| N7 | Daten-Versionierung | Zeitreihen tragen Gültigkeitszeiträume. Ob Revisionen einen vollständigen Neuaufbau der Datenbank überstehen, ist **unklar**; Sicherungen reichen 14 Tage zurück. | benannte Datenstände (Marke plus Prüfsummenliste), monatliche Langzeitsicherung | M |
| N8 | Protokolle | Caddy schreibt Zugriffe mit IP-Adresse; Aufbewahrung ist durch Docker begrenzt. | in der Datenschutzerklärung nennen, IP kürzen | S |
| N9 | Desktop-App | Lädt den eingefrorenen Stand aus `app/dist/` und braucht ein GitHub-Token, obwohl das Repo öffentlich ist. Signatur der App **unklar**. | auf Pages oder Server umstellen oder einstellen | S |
| N10 | Weiteres Rechtliches | Hinweis „keine Anlageberatung“ steht in der Impressumsvorlage. Offen: Markenrecherche zum Namen, Umgang mit Löschwünschen von Unternehmen und Personen, Kontaktweg für Rechteinhaber. | kurze Seite „Hinweise für Rechteinhaber und Betroffene“ | S |

## 5. Über die bisherigen Aufgaben hinaus

Die Aufträge der letzten Wochen haben fast ausschließlich Inhalte und Funktionen erweitert. Drei Dinge wurden dabei nicht mitgezogen und sollten bewusst eingeplant werden:

1. **Betrieb als eigenes Arbeitspaket.** Überwachung, Sicherung, Wiederherstellung, Schlüsselpflege und ein Notfallblatt sind bisher Nebenprodukte. Vorschlag: ein fester Betriebstag im Monat mit Prüfliste (Wiederherstellung geprobt, Schlüssel geprüft, Kosten angesehen, rote Workflows auf null).
2. **Ein Ziel für die Öffentlichkeit.** Ob sphaerae ein privates Werkzeug, ein öffentliches nicht kommerzielles Angebot oder später ein Produkt sein soll, bestimmt Lizenzen (IPU, WTO, Yahoo), Datenschutzaufwand, Suchmaschinen und Nutzerkonten. Diese Entscheidung fehlt und macht viele Einzelfragen (E1 bis E6) erst beantwortbar.
3. **Weniger, dafür belastbare Daten.** Der Bestand wächst schneller als seine Prüfung. Ein Qualitätsstufenmodell je Datensatz (Original geprüft, Original ungeprüft, Sekundärquelle) mit sichtbarer Kennzeichnung und einem Ziel je Stufe wäre mehr wert als weitere Länder.

## 6. Empfohlene Reihenfolge

| Stufe | Wann | Inhalt | Aufwand gesamt |
|---|---|---|---|
| 0 | diese Woche | Entscheidungen E-A bis E-D treffen. Pages auf die öffentliche Fassung umstellen oder abschalten (K1). Personenschätzungen und Gewerkschaftsmerkmal herausnehmen (K2). Schriften selbst ausliefern, Impressum ausfüllen (K3). Vollständigen Spiegel des Repos anlegen, Zwei-Faktor prüfen (K5). | 1 bis 2 Tage, davon etwa 2 Stunden Robin |
| 1 | vor dem Update-Timer und vor dem Livegang | Deploy-Zweig und Datenzweig, `sudo` begrenzen, Actions festlegen (K4). Wächter und externer Ping, die fünf roten Workflows reparieren (H1). Backup-Timer, Offsite, Wiederherstellung proben (H2). Regelwerk für `main` (H3). Update mit echtem Rückweg (H4). CSP und Standard-Hash (M1). DNS-Einträge (M9). | 4 bis 6 Tage |
| 2 | danach | Datenverträge und Plausibilitätsregeln (H5). Lizenz und Quellenseite (H6). Notfallblatt (H7). Abhängigkeiten und Historienprüfung (M2). Repo teilen und verkleinern (M3). Dokumentation bereinigen (M5). | 5 bis 8 Tage |
| 3 | Ausbau | Abrufe auf den Server (M7), eingebettete Fassung ablösen (M4, M6), API-Zusage (M8), Tests der Abrufskripte (M10), Punkte N1 bis N10 nach Bedarf. | laufend |

## 7. Entscheidungen, die bei Robin liegen

| Nr. | Frage | Empfehlung |
|---|---|---|
| E-A | Sichtbarkeit: alles öffentlich lassen, alles privat stellen oder teilen? | Teilen: Code öffentlich, Daten, Dokumente und `governance/` privat. Bis dahin Pages auf die öffentliche Fassung. |
| E-B | Personenprofile: weiter veröffentlichen? | Nur Organmitglieder börsennotierter Unternehmen mit Vergütung laut Vergütungsbericht; keine geschätzten Merkmale je Person; Arbeitnehmervertreter nur als Anzahl. Vorher Abwägung und Datenschutzerklärung. |
| E-C | Git-Historie bereinigen (Personendaten, PDFs)? | Ja, zusammen mit der Teilung des Repos; nicht umkehrbar, deshalb erst nach vollständigem Spiegel. |
| E-D | Zielbild: privat, öffentlich nicht kommerziell oder Produkt? | Öffentlich nicht kommerziell festschreiben; das hält IPU, WTO und die meisten Quellen nutzbar. |
| E2 bis E6 | wie in `docs/datenquellen.md` | Vorschläge dort übernehmen; E6 sperren, weil die Daten über Pages schon öffentlich sind. |

## 8. Unklare Punkte zum Nachprüfen

1. Liegt irgendwo eine vollständige Kopie des Repos mit allen PDFs?
2. Sind Zwei-Faktor-Anmeldung und Wiederherstellungscodes für GitHub und netcup eingerichtet?
3. Ist `04-timer.sh` inzwischen gelaufen, und wie groß ist die Platte des Servers?
4. Sind Secret-Scanning und Push-Schutz im Repo eingeschaltet?
5. Wurde je ein Geheimnis eingecheckt? (Historie mit gitleaks prüfen.)
6. Speichert Caddy das Ergebnis der Passwortprüfung zwischen?
7. Greift die HTML-Maskierung an allen Stellen, an denen fremde Texte angezeigt werden?
