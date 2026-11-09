# Umsetzungsstand

Stand 09.11.2026. Status: **Geplant**, **In Bearbeitung**, **Implementiert** (Code vorhanden), **Getestet** (automatische Tests
grün), **Produktiv** (auf dem öffentlichen Server), **Blockiert**. Produktiv ist noch nichts aus diesem Umbau: es gibt noch keinen Server.

## Bausteine

| Baustein | Status | Nachweis |
|---|---|---|
| Bestandsaufnahme, Architektur, Plan | Implementiert | `docs/bestandsaufnahme.md`, `architektur.md`, `umsetzungsplan.md` |
| Alembic über dem Kernmodell (0001), Suche/Indizes/Ländernamen (0002) | Getestet | `server/tests/test_migrationen.py` (beide Reihenfolgen, Wiederholung, Downgrade 0002) |
| Import Register + Zeitreihen (`server/etl/laden.py`) | Getestet | 32.581 Zeilen, 32.663 Entitäten, 4.802 Werte; IDs = CSV (`test_alle_ids_unveraendert_uebernommen`) |
| API `/api/v1` (10 Endpunkte, OpenAPI) | Getestet | `server/tests/test_api.py`, `test_einheiten.py` (44 Tests) |
| Sicherheit: nur lesend, Leserolle, Ratenbegrenzung, CORS, Header | Getestet | Tests `nur_lesend`, `read-only`, `cors`, `ratenbegrenzung`; Compose mit Rolle `sphaerae_api` |
| Docker Compose (db, api, web/Caddy, etl, backup) | Getestet (lokal) | Compose-Lauf 09.11.2026, `curl /api/v1/health` über Caddy |
| Backup und Wiederherstellung | Getestet (lokal) | Probe-Wiederherstellung 09.11.2026: 32.581 / 4.802 / Revision 0002 |
| Datenadapter `app/src/api.js` (Zeitlimit, Wiederholung, Cache, Fehler) | Getestet | `app/tests/api-smoke.js` (Ausfall + „Erneut versuchen“) |
| Build-Schalter `--api`, `--ziel` | Getestet | Pages-Fassung unverändert (Smoke-Tests), API-Fassung ohne Register |
| CI-Workflow `server.yml` (pytest gegen PostgreSQL 16) | Implementiert | läuft im PR |
| netcup-Server, HTTPS unter sphaerae.de, Timer, Offsite-Backup | **Blockiert** | wartet auf Freischaltung des netcup-Accounts und Robins Freigabe |
| Lizenzprüfung je Quelle | Geplant | `docs/datenquellen.md` |

## Funktionsmatrix (bestehende Kernfunktionen)

„Pages“ = bisherige Fassung (`app/dist`, GitHub Pages), „Server“ = API-Fassung (`app/dist-api`).

| Funktion | Pages | Server | Anmerkung |
|---|---|---|---|
| Weltkugel (fünf Formen, Länder, Fenster) | unverändert | unverändert | `globus-smoke.js` auf beiden Fassungen grün |
| Länderansichten | unverändert | unverändert | eingebettet |
| Unternehmensverzeichnis (F4) | unverändert | **verbessert**: Suche, Filter, Seiten auf dem Server, auch Aliase und IDs | `api-smoke.js`; „Nur mit Kennzahlen“ zählt Datenbankwerte (bekannte Einschränkung bis P2.3) |
| Unternehmensprofile mit Kennzahlen | unverändert | unverändert | noch eingebettet (`unternehmen`), P2.3 |
| Registerprofile (Unternehmen ohne Kennzahlen) | unverändert | **verbessert**: Daten über `/companies/{id}`, zusätzlich Aliase, Prüfhinweise | Deep Link `#firma-U…` funktioniert |
| Branchenvergleiche (F1–F3) | unverändert | **bekannte Einschränkung**: nur Unternehmen mit Kennzahlen, keine Register-Stubs | P2.4 |
| Unternehmensvergleiche | unverändert | unverändert | |
| Börsenansichten (BÖR, MKT) | unverändert | unverändert | eingebettet |
| Volkswirtschaftliche Daten (VWL) | unverändert | unverändert | eingebettet, P2.6 |
| Korrelationsanalysen (KOR) | unverändert | unverändert | eingebettet |
| Handelsdaten, Handelsrouten | unverändert | unverändert | eingebettet |
| Politik und Wahlen | unverändert | unverändert | `wahlen-smoke.js` |
| Dokumentenlinks | unverändert | unverändert | Links auf github.com/raw |
| Merkliste | unverändert | unverändert, Filter „Nur Merkliste“ über `ids=` | |
| CSV-Export | unverändert | unverändert | |
| Befehlszeile | unverändert | Name ohne lokalen Treffer öffnet das Verzeichnis mit Serversuche | |
| Deep Links (`#globus`, `#firma-…`, Ansichten) | unverändert | unverändert | `index.html` = Weltkugel |
| Länderauswahl oben | unverändert | Liste enthält nur Länder mit Kennzahlen bzw. VWL-Daten (ohne Register) | bekannte Einschränkung bis P2.4 |

## Abnahmekriterien der Grundmigration (Auftrag Abschnitt 30)

| Kriterium | Stand |
|---|---|
| Erste HTML-Antwort ohne vollständigen Unternehmens-, VWL-, Handels- und Wahlbestand | teilweise: Register (10,5 MB) ausgelagert; Kennzahlen, VWL, Wahlen, Handel noch eingebettet |
| Daten nach Bedarf geladen | für Verzeichnis und Registerprofile ja |
| Öffentliche Endpunkte dokumentiert und begrenzt | ja (`docs/api.md`, OpenAPI, Grenzen) |
| Unternehmens-IDs erhalten | ja, getestet |
| Migrationen reproduzierbar | ja, getestet |
| Keine API-Schlüssel im Browser | ja (API ohne Schlüssel, Quellschlüssel nur im ETL) |
| Fehlgeschlagene Importe überschreiben nicht den letzten Stand | ja (Transaktion je Import, `ingestion_run`), im Kernmodell getestet |
| Wichtigste Anwendungswege über Regressionstests abgesichert | Smoke-Tests beider Fassungen; weitere Wege mit jedem Paket |
| Backup/Wiederherstellung dokumentiert und getestet | lokal ja; Offsite blockiert (Server) |
| Umschaltung umkehrbar | dokumentiert (`migration-netcup.md`), noch nicht ausgeführt |
