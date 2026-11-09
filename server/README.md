# server/: Backend der Plattform

Lesende API (FastAPI) über PostgreSQL, Importe aus den Repo-Dateien, Betrieb mit Docker Compose (lokal und auf netcup).
Architektur: [`docs/architektur.md`](../docs/architektur.md), API: [`docs/api.md`](../docs/api.md), Betrieb und Backup:
[`docs/betrieb.md`](../docs/betrieb.md), Umzug: [`docs/migration-netcup.md`](../docs/migration-netcup.md).

| Pfad | Inhalt |
|---|---|
| `plattform/` | API: `main.py` (App, Middleware, Fehler), `api/companies.py`, `api/profiles.py`, `api/series.py`, `api/search.py`, `api/misc.py`, `schemas.py`, `db.py`, `config.py` |
| `alembic/` | Migrationen; `0001` übernimmt `international/migrations/001–004`, `0002` Suche und Ländernamen, `0003` Unternehmensprofile, `0004` VWL-Reihen |
| `etl/laden.py` | Schema migrieren, Länder, Unternehmenstabelle, Zeitreihen, Profile, Leserechte (nutzt `international/import_*.py`) |
| `etl/vwl.py` | VWL-Reihen aus `volkswirtschaft/` mit Vintage (`series`, `observation`) |
| `etl/profile.py` | Unternehmensprofile aus `app/data/unternehmen.json` (Kennzahlen, Abschlussposten, Gremien, Dokumente, Termine) |
| `deploy/` | `Caddyfile`, `backup.sh`, `restore.sh`, `initdb/01-rollen.sh` |
| `docker-compose.yml`, `docker-compose.dev.yml`, `Dockerfile`, `.env.example` | Betrieb |
| `tests/` | pytest: Einheiten ohne Datenbank, Migrationen, API gegen die echten Repo-Daten |

## Schnellstart mit Docker (empfohlen)

```bash
cp server/.env.example server/.env                          # Passwörter setzen
python3 app/build.py --nur-seite --api /api/v1 --ziel dist-api   # Oberfläche im API-Modus
docker compose -f server/docker-compose.yml up -d --build
docker compose -f server/docker-compose.yml --profile werkzeuge run --rm etl      # Daten laden (rund 40 s)
open http://localhost/                                       # Weltkugel; Verzeichnis: http://localhost/bankterminal.html#u-verzeichnis
open http://localhost/api/v1/docs                            # API ausprobieren
docker compose -f server/docker-compose.yml --profile werkzeuge run --rm backup   # Sicherung nach server/backup/
```

Ports 80/443 belegt? `WEB_PORT_HTTP=8080` und `WEB_PORT_HTTPS=8443` in `server/.env`.

## Ohne Docker (Entwicklung)

```bash
pip install -r server/requirements-dev.txt
export DATABASE_URL=postgresql://postgres:PASSWORT@127.0.0.1:5433/sphaerae   # z. B. db aus docker-compose.dev.yml
cd server
python3 -m etl.laden                       # migriert und lädt
uvicorn plattform.main:app --reload        # http://127.0.0.1:8000/api/v1/docs
# Oberfläche gegen diese API: app/dist-api/bankterminal.html?api=http://127.0.0.1:8000/api/v1 über einen lokalen Webserver,
# dazu API_CORS_ORIGINS=http://localhost:8080 setzen
```

## Tests

```bash
cd server
TEST_DATABASE_URL=postgresql://postgres:PASSWORT@127.0.0.1:5433/postgres python3 -m pytest -q   # Rolle mit CREATEDB-Recht
node ../app/tests/api-smoke.js http://localhost/bankterminal.html                                # Browser, gegen laufenden Compose-Stack
```

Ohne `TEST_DATABASE_URL` laufen nur die Tests ohne Datenbank. Jeder Datenbanktest legt eine eigene Wegwerf-Datenbank an.

## Regeln

* Neue Schemaänderungen nur als neue Alembic-Revision; `international/migrations/*.sql` werden nicht mehr geändert.
* Die API schreibt nie. Importe laufen nur über `etl/` bzw. die Skripte in `international/`.
* Unternehmens-IDs vergibt weiterhin nur `stammdaten/ids.py`; der Import übernimmt sie unverändert.
* Zugangsdaten nur in `server/.env` (nicht im Repo).
