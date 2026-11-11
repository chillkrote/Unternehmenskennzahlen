#!/bin/bash
# Schritt 1: frischen Server absichern. Als root ausführen. Wiederholbar.
#   SSH_PUBKEY_DATEI  Datei mit Robins ÖFFENTLICHEM Schlüssel (Standard: /root/.ssh/authorized_keys, also der, mit dem du dich gerade angemeldet hast)
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Bitte als root ausführen." >&2; exit 1; }
BENUTZER=sphaerae
SCHLUESSEL="${SSH_PUBKEY_DATEI:-/root/.ssh/authorized_keys}"
[ -s "$SCHLUESSEL" ] || { echo "Kein SSH-Schlüssel in $SCHLUESSEL – ohne Schlüssel sperre ich dich nicht aus. Abbruch." >&2; exit 1; }

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get full-upgrade -y
apt-get install -y ufw unattended-upgrades ca-certificates curl git sudo python3 python3-venv openssl fail2ban

# Benutzer ohne Passwort, nur per Schlüssel; darf sudo (ohne Passwortabfrage, weil es kein Passwort gibt)
id "$BENUTZER" >/dev/null 2>&1 || adduser --disabled-password --gecos "" "$BENUTZER"
usermod -aG sudo "$BENUTZER"
echo "$BENUTZER ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-$BENUTZER
chmod 440 /etc/sudoers.d/90-$BENUTZER
install -d -m 700 -o "$BENUTZER" -g "$BENUTZER" /home/$BENUTZER/.ssh
cat "$SCHLUESSEL" >> /home/$BENUTZER/.ssh/authorized_keys
sort -u -o /home/$BENUTZER/.ssh/authorized_keys /home/$BENUTZER/.ssh/authorized_keys
chown "$BENUTZER:$BENUTZER" /home/$BENUTZER/.ssh/authorized_keys
chmod 600 /home/$BENUTZER/.ssh/authorized_keys

# SSH: kein Passwort-Login, kein root-Login. Wirkt erst nach dem Neuladen unten.
cat > /etc/ssh/sshd_config.d/10-sphaerae.conf <<'KONF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
PubkeyAuthentication yes
MaxAuthTries 3
KONF
sshd -t
systemctl reload ssh || systemctl reload sshd

# Firewall: nur SSH, HTTP, HTTPS (HTTP braucht Caddy für das Zertifikat)
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# automatische Sicherheitsupdates
dpkg-reconfigure -f noninteractive unattended-upgrades
systemctl enable --now fail2ban

# Swap 2 GB als Reserve (der Server hat 2 GB RAM)
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo
echo "Fertig. WICHTIG: Öffne jetzt ein ZWEITES Terminal und prüfe, dass 'ssh $BENUTZER@<server-ip>' funktioniert,"
echo "bevor du dieses Fenster schließt. Danach ist root-Login gesperrt."
