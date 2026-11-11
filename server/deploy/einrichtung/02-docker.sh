#!/bin/bash
# Schritt 2: Docker Engine und Compose-Plugin aus dem offiziellen Repository von Docker. Als root. Wiederholbar.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Bitte als root ausführen (sudo)." >&2; exit 1; }
. /etc/os-release
case "$ID" in debian|ubuntu) ;; *) echo "Nur Debian/Ubuntu vorgesehen, gefunden: $ID" >&2; exit 1;; esac
export DEBIAN_FRONTEND=noninteractive
install -m 0755 -d /etc/apt/keyrings
curl -fsSL "https://download.docker.com/linux/$ID/gpg" -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/$ID ${VERSION_CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
# Docker-Protokolle begrenzen, sonst füllt sich die Platte langsam
cat > /etc/docker/daemon.json <<'KONF'
{ "log-driver": "json-file", "log-opts": { "max-size": "10m", "max-file": "3" } }
KONF
systemctl restart docker
usermod -aG docker sphaerae
docker --version && docker compose version
echo "Fertig. Der Benutzer sphaerae muss sich einmal ab- und wieder anmelden, damit die Docker-Gruppe gilt."
