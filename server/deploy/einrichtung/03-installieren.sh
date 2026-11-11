#!/bin/bash
# Schritt 3: Plattform installieren und starten. Als Benutzer sphaerae (nicht root). Wiederholbar.
#   SITE_ADDRESS  Adresse der Website (Standard: neu.sphaerae.de zum Testen; später sphaerae.de)
#   REPO          Git-Adresse (Standard: das öffentliche Repository)
set -euo pipefail
[ "$(id -u)" != 0 ] || { echo "Bitte als Benutzer sphaerae ausführen, nicht als root." >&2; exit 1; }
SITE_ADDRESS="${SITE_ADDRESS:-neu.sphaerae.de}"
REPO="${REPO:-https://github.com/chillkrote/unternehmenskennzahlen}"
ZIEL=/srv/sphaerae/repo

sudo install -d -o "$USER" -g "$USER" /srv/sphaerae
if [ ! -d "$ZIEL/.git" ]; then
  git clone --depth 1 --filter=blob:none --no-checkout "$REPO" "$ZIEL"
  git -C "$ZIEL" sparse-checkout init --no-cone
  # ohne die großen PDF-/HTML-Dokumente (die liegen für den Betrieb nicht auf dem Server)
  printf '%s\n' '/*' '!*.pdf' '!*.gz' '!*.html' '!*.htm' '/app/src/*.html' | git -C "$ZIEL" sparse-checkout set --no-cone --stdin
  git -C "$ZIEL" checkout main
fi
cd "$ZIEL"

# Zugangsdaten: werden hier erzeugt und bleiben auf dem Server (Rechte 600), nie im Repository
if [ ! -f server/.env ]; then
  umask 077
  {
    echo "POSTGRES_PASSWORD=$(openssl rand -hex 24)"
    echo "SPHAERAE_API_PASSWORD=$(openssl rand -hex 24)"
    echo "SITE_ADDRESS=$SITE_ADDRESS"
    echo "API_CORS_ORIGINS="
    echo "API_RATE_LIMIT_PER_MINUTE=240"
    echo "PLATTFORM_UMGEBUNG=produktion"
  } > server/.env
  echo "server/.env angelegt (Passwörter erzeugt). Sichere sie in deiner Passwortverwaltung: cat /srv/sphaerae/repo/server/.env"
else
  sed -i "s|^SITE_ADDRESS=.*|SITE_ADDRESS=$SITE_ADDRESS|" server/.env
fi
chmod 600 server/.env

# Oberfläche im API-Modus bauen (ohne Yahoo-Daten, Entscheidung E1) und prüfen
[ -d /srv/sphaerae/venv ] || python3 -m venv /srv/sphaerae/venv
/srv/sphaerae/venv/bin/pip install --quiet "openpyxl>=3.1,<4"   # der Server-Build braucht nur openpyxl (kein Yahoo)
/srv/sphaerae/venv/bin/python app/build.py --nur-seite --api /api/v1 --ziel dist-api
( cd server && /srv/sphaerae/venv/bin/python -m plattform.lizenz ../app/dist-api )

# Stack starten, dann Daten in die Datenbank laden
C="docker compose -f server/docker-compose.yml"
$C build api
$C up -d --wait db
$C --profile werkzeuge run --rm etl
$C up -d --wait api web

sleep 3
bash server/deploy/einrichtung/pruefen.sh "$SITE_ADDRESS" || true
echo "Fertig. Teste im Browser: https://$SITE_ADDRESS (das Zertifikat braucht beim ersten Mal bis zu einer Minute)."
