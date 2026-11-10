# Zielarchitektur

Stand 09.11.2026. Ziel: Die Website lädt nur die Oberfläche und holt Daten gezielt über eine API aus PostgreSQL. Betrieb auf
einem netcup-Server (Domain sphaerae.de), GitHub bleibt Versionsverwaltung, CI und Rückfall-Hosting (GitHub Pages).

```
Browser ──HTTPS──> Caddy (TLS, gzip/zstd, Sicherheitsheader, statische Oberfläche)
                    ├── /            app/dist-api/ (Weltkugel + Terminal, Vanilla-JS, MapLibre)
                    ├── /wahlgeo/*, /geodaten/*   nachzuladende Geometrien und Unternehmenspunkte (später Vektorkacheln)
                    └── /api/*  ──> FastAPI (ein Prozess, lesend, Rolle sphaerae_api)
                                     └── PostgreSQL 16 + PostGIS (Schema international)
systemd-Timer ──> Importe (etl.laden, international/*.py, Abrufskripte) ──> PostgreSQL (Rolle postgres/ETL)
                                     └── Rohdaten und Dokumente: /srv/sphaerae/daten (Dateisystem)
Backup (pg_dump, täglich) ──> lokaler Ordner ──> Offsite-Kopie (restic, siehe betrieb.md)
```

## Komponenten

| Komponente | Umsetzung | Stand |
|---|---|---|
| Web-Frontend | bestehende Module (`app/src/*.js`), gebaut mit `app/build.py --api /api/v1 --ziel dist-api`; gemeinsamer Datenadapter `src/api.js` | Verzeichnis und Registerprofile über die API, Rest eingebettet |
| Backend-API | `server/plattform` (FastAPI, Pydantic, SQLAlchemy Core), versioniert unter `/api/v1`, OpenAPI unter `/api/v1/docs` | implementiert, getestet |
| Datenbank | PostgreSQL 16 mit PostGIS-Abbild; Schema `international` (bestehendes Kernmodell) | implementiert |
| Migrationen | Alembic (`server/alembic`); Revision 0001 übernimmt die SQL-Dateien `international/migrations/001–004` | implementiert, getestet |
| Import/ETL | `server/etl/laden.py` ruft die bestehenden Importe (`import_unternehmen`, `import_de`) auf; Laufprotokoll `ingestion_run` | implementiert für Register und Zeitreihen |
| Geodaten | API-Fassung: Wahlgrenzen und Wahlwerte als statische Dateien unter `wahlgeo/` (P2.7a), Unternehmenspunkte unter `geodaten/unternehmen.json` (P2.5), Länder und Firmensitze des Terminals noch eingebettet; Ziel: PostGIS + vereinfachte Geometrien bzw. Vektorkacheln (PMTiles) | teilweise |
| Datenqualität | Prüfmarken `review_flag`, `stammdaten/pruefe_ids.py`, Plausibilitätsregeln der Adapter; Ziel: Endpunkt `/data-quality` | teilweise |
| Historische Stände | `fact.reported_at`, `recorded_at`, `fact_as_of(datum)`; API-Parameter `as_of` | implementiert für Kennzahlen |
| Dokumente | weiter im Repo; Ziel: Dateisystem des Servers, ausgeliefert durch Caddy, Index in der Datenbank (`source_document`) | geplant |
| Aktualisierung | heute GitHub Actions; Ziel: systemd-Timer auf dem Server, Workflows nur noch für Tests/Build | geplant |
| Monitoring | `/api/v1/health`, Docker-Healthchecks, `/api/v1/updates` (letzter Erfolg je Quelle); Ziel: externer kostenloser Ping | teilweise |
| Backup | `server/deploy/backup.sh` (pg_dump, Prüfung, Aufbewahrung), `restore.sh` (Probe-Wiederherstellung) | implementiert, Wiederherstellung getestet |
| Deployment | Docker Compose (`server/docker-compose.yml`), Anleitung `docs/migration-netcup.md` | lokal getestet, Server noch nicht bestellt |

## Technologieentscheidungen

| Entscheidung | Begründung | Verworfen |
|---|---|---|
| **FastAPI + Pydantic + SQLAlchemy Core** statt der im Konzept vom 08.11. erwogenen PostgREST-API | Python ist bereits die Sprache aller Importe; Validierung, einheitliche Antworten, Suche über mehrere Bereiche und Rechenlogik (Korrelation, Handelskennzahlen) lassen sich in Python sauber kapseln; PostgREST würde Tabellen 1:1 freilegen und Logik in SQL-Funktionen zwingen | PostgREST (zusätzliche Sprache für Logik), Django (zu schwer) |
| **SQLAlchemy Core mit handgeschriebenem SQL**, keine ORM-Modelle | das Kernmodell nutzt Trigger, Ausschluss-Constraints und SQL-Funktionen (`fact_as_of`); handgeschriebene Migrationen bilden das genau ab | Alembic-Autogenerate |
| **Alembic über den bestehenden SQL-Migrationen** | vorhandene Dateien und Buchführung (`public.international_migrations`) bleiben gültig; beide Wege getestet | Neuschreiben des Schemas |
| **PostgreSQL-Suche (pg_trgm)** statt Suchserver | 32.600 Unternehmen, Aliase und Länder: Ähnlichkeitssuche mit Index antwortet lokal in Millisekunden; kein weiterer Dienst | Meilisearch/Elasticsearch (erst bei nachgewiesenem Bedarf) |
| **Caddy** statt Nginx | automatisches Let's-Encrypt-HTTPS ohne Zusatzskripte, kurze Konfiguration | Nginx + certbot |
| **Kein Redis, keine Queue** | Ratenbegrenzung prozesslokal (ein API-Prozess), Caching über ETag/`Cache-Control`; Importe als einfache Timer | — |
| **PostGIS-Abbild von Anfang an** | gleiche Kollation lokal und auf dem Server, spätere Geodaten ohne Abbildwechsel | Alpine-Abbild (andere Kollation) |
| **Kein Frontend-Framework-Wechsel** | die vorhandenen Module funktionieren; der Adapter `api.js` reicht für dynamisches Laden | React/Next.js-Neubau |

## Sicherheit (umgesetzt)

* API nur lesend: Middleware lehnt alle schreibenden Methoden ab, jede Datenbankverbindung ist `read only`, eigene Rolle `sphaerae_api`
  mit reinen Leserechten; Zeitlimit je Anweisung (5 s API, 10 s Rolle).
* Eingaben serverseitig geprüft (Pydantic, Muster für IDs/Ländercodes, Obergrenzen für Seitengröße und Listen), alle SQL-Werte als
  gebundene Parameter; Sortierungen und Felder nur aus festen Listen.
* Ratenbegrenzung je IP (Standard 240/min), CORS nur für konfigurierte Ursprünge, Sicherheitsheader (CSP für API-Antworten,
  `nosniff`, `no-referrer`, HSTS über Caddy), keine Interna in Fehlermeldungen.
* Zugangsdaten nur in `server/.env` auf dem Server (in `.gitignore`), keine Schlüssel im Browser.
* Datenbank ohne veröffentlichten Port; API-Container `read_only`, unprivilegierter Benutzer.

## Migrationsweg

Neue API-Funktionen entstehen neben den bisherigen Komponenten. Dieselben Quelldateien bauen zwei Fassungen: die bisherige
(`app/dist`, GitHub Pages, alles eingebettet) und die Server-Fassung (`app/dist-api`). Ein Bereich nach dem anderen wird umgestellt;
die Pages-Fassung bleibt bis zur Abnahme Referenz und Rückfall. Umschalten der Domain erst nach Robins Freigabe
(`docs/migration-netcup.md`), rückgängig durch Zurücksetzen des DNS-Eintrags.
