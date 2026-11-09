#!/bin/sh
# Wiederherstellung einer Sicherung in eine Datenbank. Standard: in eine NEUE Datenbank (Probe-Wiederherstellung),
# die laufende bleibt unberührt. Ersetzen der Produktivdatenbank nur bewusst und nach Freigabe (docs/betrieb.md).
#   restore.sh <datei.dump> <ziel-url>
set -eu
DATEI="${1:?Sicherungsdatei angeben}"
ZIEL="${2:?Ziel-URL angeben (leere Datenbank)}"
[ -f "$DATEI.sha256" ] && sha256sum -c "$DATEI.sha256"
pg_restore --no-owner --exit-on-error --dbname="$ZIEL" "$DATEI"
psql "$ZIEL" -v ON_ERROR_STOP=1 -tAc "SELECT 'Unternehmen: ' || count(*) FROM international.company_register"
psql "$ZIEL" -v ON_ERROR_STOP=1 -tAc "SELECT 'Kennzahlen: ' || count(*) FROM international.fact"
psql "$ZIEL" -v ON_ERROR_STOP=1 -tAc "SELECT 'Schema-Revision: ' || version_num FROM public.alembic_version"
