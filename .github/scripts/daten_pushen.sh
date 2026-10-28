#!/usr/bin/env bash
# Staged Dateien committen und nach main pushen; bei Wettlauf mit anderen Pushes Rebase und neuer Versuch.
# Aufruf: daten_pushen.sh "Commit-Text" pfad...   Ergebnis: geaendert=true|false in $GITHUB_OUTPUT
set -euo pipefail
msg="$1"; shift
# --sparse: neue PDFs liegen außerhalb der Sparse-Checkout-Definition (PDFs sind ausgeschlossen), sonst verweigert git add sie
git add --sparse -- "$@"
if git diff --cached --quiet; then
  echo "Keine Änderungen."
  echo "geaendert=false" >> "${GITHUB_OUTPUT:-/dev/null}"
  exit 0
fi
# Stammdaten prüfen, bevor etwas committet wird (vorher stand die Prüfung nur im späteren Terminal-Build, fehlerhafte Daten
# lagen dann schon auf main). Bei einem Verstoß wird nichts gepusht; die Änderungen bleiben nur im Runner.
if ! python3 stammdaten/pruefe_ids.py; then
  echo "::error::Stammdaten-Prüfung fehlgeschlagen, nichts gepusht"
  git reset -q
  exit 1
fi
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git commit -q -m "$msg"
for versuch in 1 2 3 4 5; do
  if git push origin "HEAD:${GITHUB_REF_NAME}"; then
    echo "geaendert=true" >> "${GITHUB_OUTPUT:-/dev/null}"
    exit 0
  fi
  echo "Push abgelehnt (Versuch $versuch), Rebase auf ${GITHUB_REF_NAME}"
  sleep $((versuch * 3))
  # Datendateien gewinnen: die frisch erzeugte Fassung ("theirs" im Rebase = unser Commit)
  git fetch -q --depth=50 origin "${GITHUB_REF_NAME}"
  git pull --rebase -X theirs origin "${GITHUB_REF_NAME}"
done
echo "::error::Push nach 5 Versuchen gescheitert"
exit 1
