#!/bin/bash
# Passwortabfrage vor der ganzen Website ein- oder ausschalten. Als Benutzer sphaerae auf dem Server.
#   bash seitenschutz.sh an     fragt nach Benutzername und Passwort, schaltet den Schutz ein
#   bash seitenschutz.sh aus    schaltet den Schutz aus
# Das Passwort wird nur hier eingetippt (unsichtbar), nie gespeichert und nie angezeigt. In server/.env landet nur sein Hash.
# Ausgenommen von der Abfrage bleibt /api/v1/health (Überwachung, liefert nur "ok").
set -euo pipefail
ENV=/srv/sphaerae/repo/server/.env
C="docker compose -f /srv/sphaerae/repo/server/docker-compose.yml"
[ -f "$ENV" ] || { echo "$ENV fehlt – zuerst 03-installieren.sh ausführen." >&2; exit 1; }

setze() {  # setze NAME 'wert'  (ersetzt oder hängt an, Wert in einfachen Anführungszeichen wegen der $-Zeichen im Hash)
  grep -v "^$1=" "$ENV" > "$ENV.neu" || true
  printf "%s='%s'\n" "$1" "$2" >> "$ENV.neu"
  chmod 600 "$ENV.neu" && mv "$ENV.neu" "$ENV"
}

case "${1:-}" in
  an)
    read -rp "Benutzername für die Abfrage [besucher]: " U; U=${U:-besucher}
    read -rsp "Passwort (wird nicht angezeigt, mindestens 12 Zeichen): " P1; echo
    read -rsp "Passwort wiederholen: " P2; echo
    [ "$P1" = "$P2" ] || { echo "Die beiden Eingaben sind verschieden. Abbruch, nichts geändert." >&2; exit 1; }
    [ "${#P1}" -ge 12 ] || { echo "Zu kurz (mindestens 12 Zeichen). Abbruch, nichts geändert." >&2; exit 1; }
    HASH=$(printf '%s\n' "$P1" | docker run --rm -i caddy:2.10-alpine caddy hash-password 2>/dev/null)
    unset P1 P2
    case "$HASH" in '$2a$'*) ;; *) echo "Hash konnte nicht erzeugt werden. Abbruch, nichts geändert." >&2; exit 1;; esac
    setze SCHUTZ_USER "$U"; setze SCHUTZ_HASH "$HASH"; setze SEITENSCHUTZ an
    ;;
  aus) setze SEITENSCHUTZ aus ;;
  *) echo "Aufruf: bash seitenschutz.sh an|aus" >&2; exit 1;;
esac

$C up -d --force-recreate web
sleep 3
echo "Prüfung (ohne Passwort muss 401 kommen, wenn der Schutz an ist):"
SITE=$(grep '^SITE_ADDRESS=' "$ENV" | cut -d= -f2 | tr -d "'")
curl -s -o /dev/null -w "  Startseite: HTTP %{http_code}\n" "https://${SITE}/bankterminal.html" || true
curl -s -o /dev/null -w "  Health:     HTTP %{http_code}\n" "https://${SITE}/api/v1/health" || true
