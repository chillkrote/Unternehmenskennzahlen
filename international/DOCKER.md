# Datenbank lokal mit Docker testen (macOS)

Ungetestet in der Cloud-Umgebung (dort gibt es keinen Docker-Daemon); die SQL-Dateien und Tests liefen gegen PostgreSQL 16.15. Die Schritte sind so gewählt, dass ein Fehler schnell sichtbar wird.

1. **Docker Desktop** installieren und starten (https://www.docker.com/products/docker-desktop/), im Terminal `docker version` prüfen (Client und Server müssen antworten).
2. **Repo und Abhängigkeiten:**
   ```bash
   cd Unternehmenskennzahlen && git pull
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r international/requirements.txt
   ```
3. **Datenbank starten** (Passwort frei wählen, nur lokal, Port 5433 nur auf deinem Rechner):
   ```bash
   export INTERNATIONAL_DB_PASSWORD='dein-lokales-passwort'
   docker compose -f international/docker-compose.yml up -d
   docker compose -f international/docker-compose.yml ps        # Status "healthy" abwarten (ca. 10 s)
   ```
4. **Verbindung setzen und Schema anlegen:**
   ```bash
   export INTERNATIONAL_DATABASE_URL="postgresql://postgres:$INTERNATIONAL_DB_PASSWORD@127.0.0.1:5433/international"
   python3 international/db.py                       # Migrationen + 38 OECD-Länder
   python3 international/import_de.py                # 743 Unternehmen, 4.802 Fakten
   ```
5. **Tests** (legen je Test eine Wegwerf-Datenbank an und löschen sie wieder):
   ```bash
   INTERNATIONAL_TEST_DATABASE_URL="postgresql://postgres:$INTERNATIONAL_DB_PASSWORD@127.0.0.1:5433/postgres" \
     python3 -m unittest discover -s international/tests -v
   ```
   Erwartet: alle Tests `ok`, keine `skipped`. Übersprungene DB-Tests heißen: die Variable ist nicht gesetzt.
6. **Stichprobe in der Datenbank:**
   ```bash
   docker compose -f international/docker-compose.yml exec db psql -U postgres international -c "select count(*) from international.fact_current"
   ```
7. **Aufräumen:** `docker compose -f international/docker-compose.yml down` (Daten bleiben im Volume) oder `down -v` (alles löschen).

Typische Fehler: `Connection refused` = Container noch nicht „healthy“ oder Port 5433 belegt; `password authentication failed` = beim ersten Start war ein anderes Passwort gesetzt, dann `down -v` und neu starten; `INTERNATIONAL_DB_PASSWORD setzen` = Variable in dieser Shell nicht exportiert.

Backup und Rückspielen:
```bash
docker compose -f international/docker-compose.yml exec -T db pg_dump -U postgres -Fc international > international.dump
docker compose -f international/docker-compose.yml exec -T db pg_restore -U postgres --no-owner -d international --clean --if-exists < international.dump
```
