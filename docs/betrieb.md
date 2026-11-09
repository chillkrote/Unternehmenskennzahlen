# Betrieb: Backup, Wiederherstellung, Überwachung, Fehlerdiagnose

## Backup

| Punkt | Festlegung |
|---|---|
| Was | Datenbank `sphaerae` (pg_dump Custom-Format, komprimiert). Code und Quelldaten liegen in GitHub; Dokumente zusätzlich im Repo |
| Wie | `docker compose -f server/docker-compose.yml --profile werkzeuge run --rm backup` (`server/deploy/backup.sh`) |
| Prüfung | jede Sicherung wird mit `pg_restore --list` geprüft (Kerntabellen müssen enthalten sein), erst dann umbenannt; SHA-256 daneben |
| Intervall | täglich 03:30 (systemd-Timer, unten) und vor jeder Schema-Migration |
| Aufbewahrung | 14 Tage lokal (`BACKUP_BEHALTEN_TAGE`), Offsite 30 Tage täglich + 12 Monatsstände |
| Speicherort | `server/backup/` auf dem Server; Offsite-Kopie außerhalb des Servers (unten) |
| RPO | 24 h (Datenbank lässt sich zusätzlich jederzeit aus den Repo-Dateien neu aufbauen: `etl`) |
| RTO | 1 h (neuer Server + Compose + Wiederherstellung: Datenbank heute 2,9 MB Sicherung, Import aus dem Repo rund 40 s) |

**Offsite (kostenlos):** `restic` mit `rclone`-Ziel Google Drive (Connector ist im Projekt vorhanden) oder ein zweiter Ort nach
Wahl. Das restic-Passwort und das rclone-Token liegen nur auf dem Server (`/root/.config`, Rechte 600) und in Robins
Passwortverwaltung, nie im Repo. Einrichtung, sobald der Server steht; bis dahin ist das Ziel offen (**blockiert: Server fehlt**).

## Wiederherstellung (getestet 09.11.2026)

```bash
# Probe in eine neue, leere Datenbank, die laufende bleibt unberührt
docker compose -f server/docker-compose.yml exec db psql -U postgres -c "CREATE DATABASE probe_restore"
docker compose -f server/docker-compose.yml --profile werkzeuge run --rm --entrypoint sh backup -c \
  'sh /deploy/restore.sh /backup/sphaerae_<STEMPEL>.dump postgresql://postgres:<PASSWORT>@db:5432/probe_restore'
# Ergebnis 09.11.2026: Prüfsumme OK, Unternehmen 32581, Kennzahlen 4802, Schema-Revision 0002
```

Ernstfall: API stoppen (`docker compose stop api`), Datenbank `sphaerae` umbenennen statt löschen, leere Datenbank anlegen,
wiederherstellen, API starten, `/api/v1/health` prüfen. Auf einem neuen Server legt `deploy/initdb/01-rollen.sh` die Rolle
`sphaerae_api` vor der Wiederherstellung an (die Sicherung enthält deren Leserechte).

## Zeitgesteuerte Aufgaben (systemd, auf dem Server)

```ini
# /etc/systemd/system/sphaerae@.service
[Unit]
Description=sphaerae %i
[Service]
Type=oneshot
WorkingDirectory=/srv/sphaerae/repo
ExecStart=/usr/bin/docker compose -f server/docker-compose.yml --profile werkzeuge run --rm %i

# /etc/systemd/system/sphaerae-backup.timer   (OnCalendar=*-*-* 03:30, Persistent=true, Unit=sphaerae@backup.service)
# /etc/systemd/system/sphaerae-etl.timer      (OnCalendar=*-*-* 05:00, Persistent=true, Unit=sphaerae@etl.service; vorher git pull)
```

Ein fehlgeschlagener Import rollt seine Transaktion zurück; der letzte gültige Stand bleibt, `ingestion_run` hält den Fehler fest und
`/api/v1/updates` zeigt `status = failed` mit dem letzten Erfolg.

## Überwachung

* `GET /api/v1/health`: 200 mit Schema-Revision oder 503 (Datenbank weg). Docker-Healthcheck der API nutzt denselben Endpunkt.
* `GET /api/v1/updates`: letzter Lauf und letzter Erfolg je Datenquelle (veraltete Quellen erkennen).
* Erreichbarkeit von außen: kostenloser externer Ping (z. B. healthchecks.io Free oder UptimeRobot Free) auf `/api/v1/health`; Auswahl
  mit Robin, sobald der Server läuft.
* Ressourcen: `docker stats`, `df -h`; PostgreSQL protokolliert Abfragen über 1 s (`log_min_duration_statement`).
* Protokolle: `docker compose logs api|web|db` (Caddy und Uvicorn auf stdout, Docker rotiert).

## Fehlerdiagnose

| Symptom | Ursache / Prüfung |
|---|---|
| Verzeichnis zeigt „Laden fehlgeschlagen … Erneut versuchen“ | API nicht erreichbar: `curl localhost/api/v1/health`, `docker compose logs api` |
| `/health` 503 | Datenbank startet nicht oder Passwort der Rolle `sphaerae_api` stimmt nicht mit `.env` überein |
| API-Antworten leer, `/health` ok | ETL noch nicht gelaufen: `--profile werkzeuge run --rm etl` |
| `permission denied for schema international` | Leserechte fehlen: ETL erneut laufen lassen (`rechte_vergeben`) |
| 504 `zeitlimit` | Abfrage zu breit (z. B. Suche mit einem Zeichen); Filter enger oder Index ergänzen |
| 429 | Ratenbegrenzung; `API_RATE_LIMIT_PER_MINUTE` anpassen |
| Build des API-Abbilds scheitert an SSL (Firmen-/Sandbox-Proxy) | `docker build --secret id=pip_ca,src=<ca.pem> -f server/Dockerfile -t sphaerae-api:lokal .` |

## Zugangsdaten

Nur in `server/.env` (Rechte 600, in `.gitignore`) und in Robins Passwortverwaltung. Schlüssel externer Quellen (z. B. `DART_API`,
Harvard Dataverse) kommen ebenfalls dorthin und werden nur an den ETL-Dienst übergeben, nie an API oder Browser.
