#!/bin/bash
# Gesundheitsprüfung. Aufruf: pruefen.sh [adresse]  (ohne Adresse: lokal über http://localhost)
set -u
A="${1:-}"
if [ -n "$A" ]; then BASIS="https://$A"; else BASIS="http://localhost"; fi
ok=0
for pfad in /api/v1/health /api/v1/updates /bankterminal.html /weltkugel.html; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$BASIS$pfad")
  # bei eingeschaltetem Seitenschutz (seitenschutz.sh) ist 401 auf allen Seiten außer /api/v1/health richtig
  if [ "$code" = 200 ]; then s=OK
  elif [ "$code" = 401 ] && [ "$pfad" != /api/v1/health ]; then s="OK (geschützt)"
  else s=FEHLER; ok=1; fi
  printf '%-15s %s%s (HTTP %s)\n' "$s" "$BASIS" "$pfad" "$code"
done
exit $ok
