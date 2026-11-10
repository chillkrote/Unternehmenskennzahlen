# Implementierungsplan

Stand 09.11.2026. Kleine, einzeln testbare Pakete; jedes endet mit Tests, aktualisierter Funktionsmatrix und einem eigenen PR.
Aufwand in Arbeitssitzungen (eine Sitzung ≈ ein Thread-Arbeitstag mit Tests). Reihenfolge folgt den Phasen des Auftrags, angepasst
an die Abhängigkeiten aus der Bestandsaufnahme.

| Nr. | Paket | hängt ab von | Ergebnis / Test | Aufwand | Stand |
|---|---|---|---|---|---|
| P0 | Bestandsaufnahme, Zielarchitektur, Plan, Funktionsmatrix | – | `docs/` | 0,5 | erledigt |
| P1.1 | Backend-Grundlage: FastAPI, Alembic über dem Kernmodell, Docker Compose, Caddy, Leserolle | P0 | 44 pytest, Compose-Lauf | 1 | erledigt |
| P1.2 | Import Register + Zeitreihen in die Datenbank (`etl.laden`), IDs unverändert | P1.1 | IDs-Test gegen CSV | 0,5 | erledigt |
| P1.3 | Backup/Restore-Skripte, Probe-Wiederherstellung | P1.1 | Restore-Zählung | 0,25 | erledigt |
| P2.1 | Verzeichnis F4 und Registerprofile über die API, Datenadapter `api.js`, Build `--api` | P1.2 | `api-smoke.js` | 0,5 | erledigt |
| P2.2 | CI: pytest gegen PostgreSQL, Build der API-Fassung, API-Smoke gegen Compose im Workflow | P2.1 | Workflow grün | 0,5 | erledigt: `server.yml` Job `test` (pytest) und Job `compose` (Stack bauen, ETL, api-/globus-/wahlen-smoke über http) |
| P2.3 | **Kennzahlen aller Unternehmen (`unternehmen.json`, 22,5 MB) in die Datenbank**: Import der Werte mit Quelle, `/companies/{id}` liefert Profilwerte, Branchenmediane serverseitig; Profilseite lädt per API | P1.2 | Abgleich jeder Kennzahl mit `unternehmen.json` (Referenztest) | 2 | erledigt (Abschlüsse, Gremien, Dokumente ausgelagert; Kennzahlen bleiben für F1–F3 bis P2.4 eingebettet) |
| P2.4 | Branchenansichten F1–F3 serverseitig (Listen, Mediane, Filter), danach `unternehmen`-Block nicht mehr einbetten | P2.3 | Smoke F1–F3, Werte gleich alt/neu | 1,5 | zurückgestellt: nach P2.3 ist der Block nur noch 1,4 MB, wird aber von Weltkugel, Korrelation, Terminen und Vergleich genutzt; Mediane liefert die API schon (`/sectors/{id}/statistics`). Erst nach P2.6 |
| P2.5a | Weltkugel: Stammdaten-Details (Beschreibung, Quelle, Website, LEI, Handelsregister, Rechtsform, Börse) nicht einbetten, Fenster lädt sie über `/companies/{id}` | P2.1 | `globus-smoke.js` über http | 0,25 | erledigt (−7,1 MB) |
| P2.5 | Weltkugel-Unternehmenspunkte (`geo-tabelle`, 3,1 MB): API-Fassung lädt die schlanke Tabelle nach dem Start als `geodaten/unternehmen.json` (gzip 0,7 MB) und baut Punkte, Ringe „ohne Ort“ und Dichte je Land neu auf; Viewport-Abfrage bzw. PMTiles erst bei deutlich mehr Punkten | P1.2 | `globus-smoke.js` über den Server | 1,5 | erledigt (−3,1 MB) |
| P2.6 | VWL-Reihen (`vwl`, 5,3 MB) als `series`/`observation` mit Vintage, VWL-Ansichten laden je Land/Reihe | P1.1 | Abgleich mit CSV | 2 | erledigt (Reihenwerte 4,4 MB über `/observations`; Prognosen und Abgleich 1,4 MB als Datei `data/vwl_prognosen.json`, geladen mit der Ansicht Prognosen) |
| P2.7a | Wahlen und Geometrien nachladen: Grenzen der Kommunen, Bundestagswahlkreise und Kreise sowie Wahlwerte ab 10 Werten je Einheit als vorberechnete Dateien (`wahlgeo/`), geladen sobald eine Wahl auf der Karte ist | P2.1 | `wahlen-smoke.js` über den Server | 0,5 | erledigt (−5,5 MB) |
| P2.8 | Große Datenblöcke als Dateien: allgemeiner Lader `BLOCK` (api.js, Platzhalter `{"_nach": …}`, Ereignis `sphaerae:block`); Parlamente und Kommunalwahlen (2,5 MB, mit der Ansicht) sowie `markt`, `kurse`, `boerse` (4,2 MB, beim Start parallel über `BLOCK.warte`); P2.8c: Güterexporte (`gueter-daten` 0,6 MB) und Gliedstaaten-Grenzen (`gliedstaaten-geo` 1,0 MB) beim Start nachgeladen; offen: `unternehmen` 1,4 (P2.4), `daten` 0,7 MB | P2.1 | `api-smoke.js` (Politik, Börse), `handel-gueter-smoke.js` über http, Ansichtstext gleich Pages | 1 | erledigt bis auf Unternehmen, Banken |
| P2.7 | Wahlen und Geometrien: PostGIS, vereinfachte Geometrien je Zoomstufe, Wahldaten je Wahl über die API | P2.5 | `wahlen-smoke.js` | 2 | geplant; erst nötig, wenn Abfragen über Geometrien gebraucht werden (Dateien reichen für die Anzeige) |
| P3.1 | Datenkatalog `data_source` + `/data-catalog` aus vorhandenen Quellenangaben (`volkswirtschaft/serien.csv`, `PROGNOSEGEBER.md`, Adapter) | P2.6 | Katalog vollständig für importierte Reihen | 1 | geplant |
| P3.2 | Datenqualität: `/data-quality` (Prüfmarken, veraltete Quellen, Sprünge), Abdeckungsmatrix mit festem Nenner | P3.1 | Prüfbericht reproduzierbar | 1,5 | geplant |
| P3.3 | Universelle Suche in der Oberfläche (Befehlszeile + Weltkugel-Suchfeld über `/search`, Gruppen, Tastatur) | P2.1 | Smoke | 1 | API fertig, Oberfläche geplant |
| P4 | Analyse-Arbeitsbereich (Korrelation erweitern: Reihen aus allen Bereichen, Transformationen, Referenzwerte), teilbare URLs, Export CSV/JSON | P2.6, P3.1 | Mathematik gegen Referenzwerte | 3 | geplant |
| P5 | Handelsabhängigkeit (HHI, Weltmarktanteile, Alternativlieferländer), belegte vs. abgeleitete Beziehungen | P2.6 | Referenzrechnungen | 3 | geplant |
| P6 | Revisionen/Vintages für VWL und Prognosen, Änderungsfeed + Atom, regelbasierte Berichte | P2.6, P3.2 | Feed-Test | 3 | geplant |
| P7 | Szenariorechner | P4, P5 | — | später | geplant |
| B1 | Server bei netcup einrichten, HTTPS, Timer, Offsite-Backup | Robins Freigabe | Smoke nach Deployment | 1 | **blockiert** (Account) |
| B2 | Lizenzprüfung je Quelle vor öffentlicher Weiterverbreitung (Kurse, Nachrichten) | – | `datenquellen.md` | 1 | geplant |

Kritischer Pfad bis zur Abnahme „erste HTML-Antwort ohne vollständigen Datenbestand“, nach Größe der eingebetteten Blöcke geordnet:
P2.3 → P2.5a → P2.6 (VWL 5,3 MB) → P2.7 (Wahlen und Geometrien, zusammen rund 8 MB) → P2.5 → P2.4.
Danach ist die Seite voraussichtlich unter 5 MB (nach P2.8c: 8,5 MB Weltkugel bzw. 3,8 MB Terminal in der API-Fassung; die Weltkugel trägt noch Ländergrenzen 1,5 MB und Wahlen 1,2 MB, 69,1 MB in der Pages-Fassung).
