#!/usr/bin/env bash
# Staged Dateien committen und nach main pushen; bei Wettlauf mit anderen Pushes Rebase (ohne Konfliktauflösung zugunsten der eigenen Daten) und neuer Versuch.
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
  # Kein "-X theirs": bei einem echten Konflikt (Datei zwischenzeitlich auch auf dem Server geändert, z. B. von Hand) darf die ältere,
  # hier erzeugte Fassung die neuere nicht überschreiben. Dann abbrechen; der nächste Lauf erzeugt die Daten auf dem neuen Stand neu.
  git fetch -q --depth=50 origin "${GITHUB_REF_NAME}"
  if ! git rebase "origin/${GITHUB_REF_NAME}"; then
    git rebase --abort || true
    echo "::error::Konflikt mit zwischenzeitlichen Änderungen auf ${GITHUB_REF_NAME}; nichts gepusht, der nächste Lauf erzeugt die Daten neu"
    exit 1
  fi
  # Nach dem Rebase stimmt der Datenstand evtl. nicht mehr: Stammdaten erneut prüfen
  if ! python3 stammdaten/pruefe_ids.py; then
    echo "::error::Stammdaten-Prüfung nach dem Rebase fehlgeschlagen, nichts gepusht"
    exit 1
  fi
done
echo "::error::Push nach 5 Versuchen gescheitert"
exit 1
