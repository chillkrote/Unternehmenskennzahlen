#!/bin/sh
# Sicherung der Datenbank im Custom-Format (komprimiert, einzeln wiederherstellbar) mit Prüfung und Aufbewahrung.
#   DATABASE_URL  Verbindung (Rolle mit Leserecht auf alles, z. B. postgres)
#   BACKUP_DIR    Zielordner (Standard ./backup); Offsite-Kopie siehe docs/betrieb.md (restic/rclone)
#   BACKUP_BEHALTEN_TAGE  ältere Sicherungen werden gelöscht (Standard 14)
set -eu
: "${DATABASE_URL:?DATABASE_URL setzen}"
DIR="${BACKUP_DIR:-./backup}"
TAGE="${BACKUP_BEHALTEN_TAGE:-14}"
mkdir -p "$DIR"
STEMPEL=$(date -u +%Y%m%dT%H%M%SZ)
ZIEL="$DIR/sphaerae_$STEMPEL.dump"
pg_dump --format=custom --compress=6 --no-owner --file="$ZIEL.teil" "$DATABASE_URL"
# Prüfen, dass die Datei lesbar ist und die Kerntabellen enthält, erst dann umbenennen (keine halben Sicherungen)
pg_restore --list "$ZIEL.teil" > "$ZIEL.liste"
for t in company_register entity fact; do
  grep -q "TABLE DATA international $t" "$ZIEL.liste" || { echo "Sicherung unvollständig: $t fehlt" >&2; rm -f "$ZIEL.teil" "$ZIEL.liste"; exit 1; }
done
rm -f "$ZIEL.liste"
mv "$ZIEL.teil" "$ZIEL"
sha256sum "$ZIEL" > "$ZIEL.sha256"
find "$DIR" -name 'sphaerae_*.dump*' -mtime +"$TAGE" -delete
echo "Sicherung: $ZIEL ($(du -h "$ZIEL" | cut -f1))"
