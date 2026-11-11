# Umzug auf netcup

Stand 11.11.2026. **Server (nano, Domain sphaerae.de) ist bestellt.** Die Einsteiger-Anleitung steht in [server-einrichtung.md](server-einrichtung.md),
die Skripte in `server/deploy/einrichtung/`. DNS-Änderungen und das Umschalten der öffentlichen Website nur nach ausdrücklicher Freigabe.
Alles unten ist lokal mit Docker Compose getestet (gleiche Abbilder, gleiche Konfiguration).

## Annahmen (bis der Server da ist)

| Punkt | Annahme | prüfen am Server |
|---|---|---|
| Tarif | VPS nano G11.5s: 2 vCore, 2 GB RAM, 60 GB SSD, IPv4 + IPv6 (Entscheidungsvorlage vom 08.11.2026) | `nproc`, `free -h`, `df -h` |
| Betriebssystem | Debian 12 oder Ubuntu 24.04 aus dem netcup-Image | `cat /etc/os-release` |
| Zugang | root per SSH-Schlüssel, danach eigener Benutzer `sphaerae` mit sudo | — |
| Domain | sphaerae.de bei netcup, A- und AAAA-Eintrag auf den Server | `dig sphaerae.de` |
| Vorhandene Dienste | keine (frischer Server) | `ss -tlnp` |
| Backup-Ziel außerhalb | siehe `betrieb.md` (kostenfrei: Google Drive über rclone/restic, oder netcup-Snapshots) | — |

Ressourcen: PostgreSQL (256 MB shared_buffers), API (rund 80 MB), Caddy (rund 30 MB) laufen in 2 GB; Swap 2 GB als Reserve anlegen.

## Einrichtung (Reihenfolge)

1. **Härten:** Updates (`apt full-upgrade`), Benutzer `sphaerae`, SSH nur mit Schlüssel und ohne root-Passwort, `ufw allow 22,80,443/tcp`,
   `unattended-upgrades` für Sicherheitsupdates, Swap-Datei.
2. **Docker:** Docker Engine und Compose-Plugin aus dem offiziellen Debian-/Ubuntu-Repository.
3. **Code:** `git clone --filter=blob:none --sparse https://github.com/chillkrote/Unternehmenskennzahlen /srv/sphaerae/repo` und
   Sparse-Checkout ohne PDFs (wie in den Workflows); Dokumente später getrennt nach `/srv/sphaerae/daten`.
4. **Konfiguration:** `cp server/.env.example server/.env`, Passwörter erzeugen (`openssl rand -base64 30`),
   `SITE_ADDRESS=sphaerae.de`, `PLATTFORM_UMGEBUNG=produktion`, `API_CORS_ORIGINS` leer (gleiche Domain).
5. **Oberfläche bauen:** `python3 app/build.py --nur-seite --api /api/v1 --ziel dist-api` (oder als Workflow-Artifact herunterladen). Die API-Fassung enthält keine Yahoo-Daten (Entscheidung E1); die Datenbank übernimmt sie ebenfalls nicht.
   Danach Pflicht: `cd server && python3 -m plattform.lizenz ../app/dist-api` (Lizenzprüfung der Ausgabe; bei einem Fund nicht
   ausliefern). In `server/.env` `PLATTFORM_UMGEBUNG=produktion` setzen, dann lassen sich Yahoo-Daten nicht versehentlich laden.
   Die Migrationen 0007 und 0008 fügen nur Spalten und Tabellen hinzu (`alembic upgrade head`).
6. **Start:** `docker compose -f server/docker-compose.yml up -d --build`, dann
   `docker compose -f server/docker-compose.yml --profile werkzeuge run --rm etl`.
7. **Prüfen (Smoke-Test nach Deployment):** `curl -fsS https://sphaerae.de/api/v1/health`, `node app/tests/api-smoke.js https://sphaerae.de/bankterminal.html`.
8. **Timer:** systemd-Timer für `etl` (täglich nach dem Datenstand) und `backup` (täglich), siehe `betrieb.md`.
9. **Umschalten:** erst nach Robins Freigabe A/AAAA-Eintrag von sphaerae.de setzen. Bis dahin Test über `/etc/hosts` oder eine
   Subdomain (`neu.sphaerae.de`).

## Rückweg

* Die GitHub-Pages-Fassung läuft unverändert weiter (`terminal.yml`). Zurück = DNS-Eintrag wieder entfernen bzw. auf GitHub Pages
  zeigen lassen; die TTL vorher auf 300 s senken.
* Datenbank: Wiederherstellung aus der letzten Sicherung (`server/deploy/restore.sh`), Schema-Revisionen sind additiv.
* Neue Fassung der Oberfläche fehlerhaft: vorherigen Stand von `app/dist-api` wieder einspielen (Caddy liefert nur Dateien aus).

## Umgebungen

* Entwicklung: lokal, `docker-compose.dev.yml` (Datenbank auf 127.0.0.1:5433, API auf 127.0.0.1:8000).
* Produktion: netcup, `server/.env` mit `PLATTFORM_UMGEBUNG=produktion`.
* Staging: bei 2 GB RAM nicht dauerhaft; bei Bedarf zweites Compose-Projekt (`docker compose -p sphaerae-staging`) mit eigener
  Datenbank unter `neu.sphaerae.de`, nur für die Dauer einer Abnahme.

## Was Robin tun muss

1. netcup-Account freischalten lassen und Bescheid geben (dann bestelle ich nicht selbst, sondern nenne den genauen Tarif zur Bestellung).
2. SSH-Zugang für die Einrichtung bereitstellen (öffentlicher Schlüssel auf dem Server), oder die Schritte 1–7 mit dieser Anleitung selbst ausführen.
3. Freigabe für den DNS-Eintrag geben, sobald die Abnahme (Funktionsmatrix in `umsetzungsstand.md`) erfüllt ist.
