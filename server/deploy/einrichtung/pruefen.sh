#!/bin/bash
# Gesundheitsprüfung. Aufruf: pruefen.sh [adresse]  (ohne Adresse: lokal über http://localhost)
set -u
A="${1:-}"
if [ -n "$A" ]; then BASIS="https://$A"; else BASIS="http://localhost"; fi
ok=0
for pfad in /api/v1/health /api/v1/updates /bankterminal.html /weltkugel.html; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$BASIS$pfad")
  [ "$code" = 200 ] && s=OK || { s=FEHLER; ok=1; }
  printf '%-8s %s%s (HTTP %s)\n' "$s" "$BASIS" "$pfad" "$code"
done
exit $ok
