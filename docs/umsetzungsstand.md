# Umsetzungsstand

Stand 09.11.2026. Status: **Geplant**, **In Bearbeitung**, **Implementiert** (Code vorhanden), **Getestet** (automatische Tests
grün), **Produktiv** (auf dem öffentlichen Server), **Blockiert**. Produktiv ist noch nichts aus diesem Umbau: es gibt noch keinen Server.

## Bausteine

| Baustein | Status | Nachweis |
|---|---|---|
| Bestandsaufnahme, Architektur, Plan | Implementiert | `docs/bestandsaufnahme.md`, `architektur.md`, `umsetzungsplan.md` |
| Alembic über dem Kernmodell (0001), Suche/Indizes/Ländernamen (0002), Unternehmensprofile (0003) | Getestet | `server/tests/test_migrationen.py` (beide Reihenfolgen, Wiederholung, Downgrade 0002 und 0003) |
| Import Register + Zeitreihen (`server/etl/laden.py`) | Getestet | 32.581 Zeilen, 32.663 Entitäten, 4.802 Werte; IDs = CSV (`test_alle_ids_unveraendert_uebernommen`) |
| API `/api/v1` (10 Endpunkte, OpenAPI) | Getestet | `server/tests/test_api.py`, `test_einheiten.py` (44 Tests) |
| Sicherheit: nur lesend, Leserolle, Ratenbegrenzung, CORS, Header | Getestet | Tests `nur_lesend`, `read-only`, `cors`, `ratenbegrenzung`; Compose mit Rolle `sphaerae_api` |
| Docker Compose (db, api, web/Caddy, etl, backup) | Getestet (lokal) | Compose-Lauf 09.11.2026, `curl /api/v1/health` über Caddy |
| Backup und Wiederherstellung | Getestet (lokal) | Probe-Wiederherstellung 09.11.2026: 32.581 / 4.802 / Revision 0002 |
| Unternehmensprofile in der Datenbank (Revision 0003, `server/etl/profile.py`) | Getestet | 1.284 Profile, 23.280 Werte, 4.664 Abschlüsse mit 412.107 Posten; `test_profile.py` vergleicht jeden Wert und jeden Posten mit `unternehmen.json`, Mediane und Rang für alle 1.284 Profile ohne Abweichung |
| API `/companies/{id}/profile`, `/sectors/{id}/statistics`, `/profile-metrics` | Getestet | `test_profile.py` (Rechenregeln wie `unternehmen.js`, Länderauswahl, Fehlerfälle) |
| VWL-Reihen in der Datenbank (Revision 0004, `server/etl/vwl.py`) mit Vintage | Getestet | 56 Reihen, 210.160 Werte; `test_vwl.py`: jede Zahl gleich der eingebetteten Seite, Revision und Wegfall mit Stand „bekannt zum“ |
| API `/series`, `/series/{id}`, `/observations` | Getestet | `test_vwl.py` (Filter, Eingabeprüfung, `as_of`) |
| Datenadapter `app/src/api.js` (Zeitlimit, Wiederholung, Cache, Fehler) | Getestet | `app/tests/api-smoke.js` (Ausfall + „Erneut versuchen“) |
| Build-Schalter `--api`, `--ziel` | Getestet | Pages-Fassung unverändert (Smoke-Tests), API-Fassung ohne Register |
| CI-Workflow `server.yml`: pytest gegen PostgreSQL 16 (Job `test`) und ganzer Compose-Stack mit ETL und Browser-Smoke-Tests über http (Job `compose`) | Implementiert | läuft im PR |
| netcup-Server, HTTPS unter sphaerae.de, Timer, Offsite-Backup | **Blockiert** | wartet auf Freischaltung des netcup-Accounts und Robins Freigabe |
| Lizenzprüfung je Quelle | Geplant | `docs/datenquellen.md` |

## Funktionsmatrix (bestehende Kernfunktionen)

„Pages“ = bisherige Fassung (`app/dist`, GitHub Pages), „Server“ = API-Fassung (`app/dist-api`).

| Funktion | Pages | Server | Anmerkung |
|---|---|---|---|
| Weltkugel (fünf Formen, Länder, Fenster) | unverändert | unverändert; Stammdaten-Fenster lädt Beschreibung, Quelle, Website, LEI, Handelsregister über `/companies/{id}` (Ladehinweis, „Erneut versuchen“) | `globus-smoke.js` auf beiden Fassungen grün, API-Fassung auch über http |
| Länderansichten | unverändert | unverändert | eingebettet |
| Universelle Suche (Befehlszeile, Suchfeld der Weltkugel) | unverändert (lokale Suche) | **neu**: Vorschläge über `/search` nach Unternehmen, Ländern, Branchen und „Branche · Land“, Pfeiltasten, Enter, Escape; Enter ohne Vorschlag bleibt Befehl | `suche-smoke.js` |
| Unternehmensverzeichnis (F4) | unverändert | **verbessert**: Suche, Filter, Seiten auf dem Server, auch Aliase und IDs | `api-smoke.js`; „Nur mit Kennzahlen“ zählt Zeitreihen und Profilkennzahlen der Datenbank |
| Unternehmensprofile mit Kennzahlen | unverändert | **verbessert**: Kennzahlen, Mediane, Zeitreihen sofort; Bilanz/GuV, Gremien, Vergütung und Dokumente laden über `/companies/{id}/profile` (Ladehinweis, „Erneut versuchen“) | `api-smoke.js`; Kennzahlen bleiben für F1–F3 eingebettet bis P2.4 |
| Bilanz- und GuV-Abdeckung (F7) | unverändert | unverändert, Postenzahlen aus eingebetteter Kurzfassung | `api-smoke.js` |
| Registerprofile (Unternehmen ohne Kennzahlen) | unverändert | **verbessert**: Daten über `/companies/{id}`, zusätzlich Aliase, Prüfhinweise | Deep Link `#firma-U…` funktioniert |
| Branchenvergleiche (F1–F3) | unverändert | **bekannte Einschränkung**: nur Unternehmen mit Kennzahlen, keine Register-Stubs | P2.4 |
| Unternehmensvergleiche | unverändert | unverändert | |
| Börsenansichten (BÖR, MKT) | unverändert | unverändert | eingebettet |
| Volkswirtschaftliche Daten (VWL) | unverändert | **verbessert**: Reihenwerte laden bei Bedarf über `/observations` (Ladehinweis, „Erneut versuchen“); Texte aller VWL-Ansichten gleich der Pages-Fassung | `api-smoke.js`; Prognosen und Abgleich (1,4 MB) noch eingebettet |
| Korrelationsanalysen (KOR) | unverändert | unverändert, VWL-Reihen über die API | `api-smoke.js` (Ansicht gleich der Pages-Fassung) |
| Handelsdaten, Handelsrouten | unverändert | unverändert | eingebettet |
| Politik und Wahlen | unverändert | unverändert; Grenzen (Kommunen, Bundestagswahlkreise, Kreise) und Wahlwerte laden als Dateien, sobald eine Wahl auf der Karte ist | `wahlen-smoke.js` auf beiden Fassungen, API-Fassung über den Server |
| Dokumentenlinks | unverändert | unverändert | Links auf github.com/raw |
| Merkliste | unverändert | unverändert, Filter „Nur Merkliste“ über `ids=` | |
| CSV-Export | unverändert | unverändert | |
| Befehlszeile | unverändert | Name ohne lokalen Treffer öffnet das Verzeichnis mit Serversuche | |
| Deep Links (`#globus`, `#firma-…`, Ansichten) | unverändert | unverändert | `index.html` = Weltkugel |
| Länderauswahl oben | unverändert | Liste enthält nur Länder mit Kennzahlen bzw. VWL-Daten (ohne Register) | bekannte Einschränkung bis P2.4 |

## Abnahmekriterien der Grundmigration (Auftrag Abschnitt 30)

| Kriterium | Stand |
|---|---|
| Erste HTML-Antwort ohne vollständigen Unternehmens-, VWL-, Handels- und Wahlbestand | teilweise: Register (10,5 MB), Abschlussposten/Gremien/Dokumente (21 MB), Weltkugel-Stammdatendetails (7 MB) und VWL-Reihenwerte (4,4 MB) ausgelagert; Profilkennzahlen (für F1–F3), Wahlen und Handel noch eingebettet; VWL-Prognosen (1,4 MB), Parlamente und Kommunalwahlen (2,5 MB) mit der Ansicht und Markt-, Kurs- und Börsendaten (4,2 MB), Güterexporte (0,6 MB), Gliedstaaten-Grenzen (1,0 MB) und das Wahlregister der Weltkugel (1,2 MB) beim Start als Dateien nachgeladen. Wahlgrenzen und Wahlwerte (5,5 MB) sowie die Unternehmenspunkte der Weltkugel (3,1 MB) als Dateien nachgeladen. Weltkugel der API-Fassung 7,3 MB (vorher 58,6 MB), Terminal 3,8 MB (Ziel unter 5 MB erreicht) |
| Daten nach Bedarf geladen | für Verzeichnis und Registerprofile ja |
| Öffentliche Endpunkte dokumentiert und begrenzt | ja (`docs/api.md`, OpenAPI, Grenzen) |
| Unternehmens-IDs erhalten | ja, getestet |
| Migrationen reproduzierbar | ja, getestet |
| Keine API-Schlüssel im Browser | ja (API ohne Schlüssel, Quellschlüssel nur im ETL) |
| Fehlgeschlagene Importe überschreiben nicht den letzten Stand | ja (Transaktion je Import, `ingestion_run`), im Kernmodell getestet |
| Wichtigste Anwendungswege über Regressionstests abgesichert | Smoke-Tests beider Fassungen; weitere Wege mit jedem Paket |
| Backup/Wiederherstellung dokumentiert und getestet | lokal ja; Offsite blockiert (Server) |
| Umschaltung umkehrbar | dokumentiert (`migration-netcup.md`), noch nicht ausgeführt |
