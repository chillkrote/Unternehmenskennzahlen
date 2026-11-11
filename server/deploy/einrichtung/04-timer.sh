#!/bin/bash
# Schritt 4: tägliche Sicherung (03:30) und tägliche Aktualisierung (05:00) als systemd-Timer. Als root. Wiederholbar.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Bitte als root ausführen (sudo)." >&2; exit 1; }
cat > /etc/systemd/system/sphaerae-backup.service <<'KONF'
[Unit]
Description=sphaerae Datenbanksicherung
[Service]
Type=oneshot
User=sphaerae
WorkingDirectory=/srv/sphaerae/repo
ExecStart=/usr/bin/docker compose -f server/docker-compose.yml --profile werkzeuge run --rm backup
KONF
cat > /etc/systemd/system/sphaerae-backup.timer <<'KONF'
[Unit]
Description=sphaerae Sicherung täglich
[Timer]
OnCalendar=*-*-* 03:30:00
Persistent=true
[Install]
WantedBy=timers.target
KONF
cat > /etc/systemd/system/sphaerae-update.service <<'KONF'
[Unit]
Description=sphaerae Aktualisierung (Code, Oberfläche, Daten)
[Service]
Type=oneshot
User=sphaerae
TimeoutStartSec=1800
ExecStart=/bin/bash /srv/sphaerae/repo/server/deploy/einrichtung/aktualisieren.sh
KONF
cat > /etc/systemd/system/sphaerae-update.timer <<'KONF'
[Unit]
Description=sphaerae Aktualisierung täglich
[Timer]
OnCalendar=*-*-* 05:00:00
Persistent=true
[Install]
WantedBy=timers.target
KONF
systemctl daemon-reload
systemctl enable --now sphaerae-backup.timer sphaerae-update.timer
systemctl list-timers 'sphaerae-*' --no-pager
