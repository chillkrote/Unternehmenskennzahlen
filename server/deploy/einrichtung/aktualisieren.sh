#!/bin/bash
# Neuen Stand aus GitHub holen und ausrollen. Als sphaerae. Bricht bei Fehlern ab, die laufende Fassung bleibt dann erhalten.
set -euo pipefail
cd /srv/sphaerae/repo
C="docker compose -f server/docker-compose.yml"
SITE=$(grep '^SITE_ADDRESS=' server/.env | cut -d= -f2)

# Rückfallpunkt: Datenbanksicherung und bisherige Oberfläche merken
$C --profile werkzeuge run --rm backup
rm -rf app/dist-api.vorher && [ -d app/dist-api ] && cp -a app/dist-api app/dist-api.vorher || true

git fetch --depth 1 origin main
git reset --hard origin/main   # der Server hat keine eigenen Änderungen; .env ist nicht im Repo und bleibt
/srv/sphaerae/venv/bin/pip install --quiet "openpyxl>=3.1,<4"   # der Server-Build braucht nur openpyxl (kein Yahoo)
/srv/sphaerae/venv/bin/python app/build.py --nur-seite --api /api/v1 --ziel dist-api.neu
( cd server && /srv/sphaerae/venv/bin/python -m plattform.lizenz ../app/dist-api.neu )
rm -rf app/dist-api && mv app/dist-api.neu app/dist-api

$C build api
$C up -d --wait db
$C --profile werkzeuge run --rm etl
$C up -d --wait api web
$C restart web   # Caddy neu einlesen

if ! bash server/deploy/einrichtung/pruefen.sh "${SITE#:}" ; then
  echo "Prüfung fehlgeschlagen: alte Oberfläche wird zurückgestellt." >&2
  [ -d app/dist-api.vorher ] && { rm -rf app/dist-api && mv app/dist-api.vorher app/dist-api && $C restart web; }
  exit 1
fi
echo "Aktualisiert: $(git rev-parse --short HEAD)"
