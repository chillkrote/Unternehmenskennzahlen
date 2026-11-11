# Server einrichten und umziehen – Anleitung für Einsteiger

Stand 11.11.2026. Für Robin geschrieben, der so etwas noch nie gemacht hat. Jeder Fachbegriff wird beim ersten Mal erklärt.
Das technische Gegenstück für Fachleute ist [migration-netcup.md](migration-netcup.md), der Betrieb steht in [betrieb.md](betrieb.md).

## Das Bild im Kopf

Bisher liegt die Website bei GitHub (GitHub Pages): ein riesiger fertiger Dateiberg von 69 MB. Künftig läuft bei netcup ein
eigener kleiner Computer rund um die Uhr, der drei Dinge tut:

1. **Webserver (Caddy)** liefert die Seite aus und besorgt sich selbst das Schloss-Symbol (HTTPS-Zertifikat).
2. **Datenbank (PostgreSQL)** hält die Zahlen. Die Seite lädt nur, was sie gerade braucht.
3. **API** ist der Kellner zwischen Seite und Datenbank.

Alles läuft in **Docker**: das sind verschlossene Kisten, in denen jedes Programm für sich läuft. Darum muss auf dem Server
nichts von Hand zusammengebaut werden; ein Befehl startet alle Kisten.

## Wörterbuch

| Begriff | Bedeutung |
|---|---|
| **Server / VPS** | gemieteter Computer in einem Rechenzentrum, ohne Bildschirm. Du steuerst ihn über Text. |
| **Terminal** | das Programm auf deinem Mac (Programme → Dienstprogramme → Terminal), in dem du Befehle tippst. |
| **SSH** | der sichere Telefonanruf vom Terminal zum Server. `ssh benutzer@adresse` ruft an. |
| **SSH-Schlüssel** | ein Schlüsselpaar: der *private* Teil bleibt auf deinem Mac (nie weitergeben), der *öffentliche* Teil (ein Schloss) kommt auf den Server. Nur wer den passenden Schlüssel hat, kommt hinein. Sicherer als ein Passwort. |
| **root** | der Allmächtige auf dem Server. Wir sperren ihn nach der Einrichtung für Anmeldungen und arbeiten als normaler Benutzer `sphaerae`. |
| **Firewall (ufw)** | Türsteher: lässt nur Anrufe auf den drei Nummern 22 (SSH), 80 (HTTP) und 443 (HTTPS) durch. |
| **IP-Adresse** | die „Telefonnummer“ des Servers, z. B. `203.0.113.7`. |
| **DNS / A-Eintrag** | das Telefonbuch: „sphaerae.de gehört zur IP-Adresse …“. A = IPv4, AAAA = IPv6 (die lange Form). |
| **TTL** | wie lange sich andere Computer einen Telefonbucheintrag merken. Vor dem Umschalten klein (300 s), damit Änderungen schnell wirken und ein Rückzieher schnell geht. |
| **HTTPS / Zertifikat** | das Schloss im Browser. Caddy holt es kostenlos bei Let's Encrypt, sobald der DNS-Eintrag stimmt. |
| **Subdomain** | Zusatzname vor der Domain, z. B. `neu.sphaerae.de`. Damit testen wir, bevor `sphaerae.de` selbst umschaltet. |
| **Repository (Repo)** | der Ordner mit allem Code und allen Daten bei GitHub. |
| **Timer (systemd)** | Wecker auf dem Server: „täglich 03:30 Sicherung machen“. |
| **Backup** | Sicherungskopie der Datenbank. Eine Kopie nur auf dem Server zählt nicht, deshalb später zusätzlich außerhalb. |

## Wer macht was

* **Du** (nur du kannst das): netcup-Konto, Server-Image wählen, SSH-Schlüssel erzeugen, Domain/DNS einstellen, die Skripte
  ausführen (ich gebe dir fertige Befehle zum Kopieren), Passwörter in deine Passwortverwaltung legen, Freigaben erteilen.
* **Ich** (Claude): alle Skripte, Konfiguration, Sicherung, tägliche Aktualisierung, Datenimport, Tests, Fehlersuche, Rückfallplan.
  Ich habe **keinen Zugang zu deinem Server** und brauche auch keinen. Du kopierst mir bei Problemen nur die Ausgabe ins Gespräch.
* **Nie in den Chat oder ins Repo**: Passwörter, den privaten SSH-Schlüssel (Datei ohne `.pub`), netcup-Zugangsdaten, Inhalte
  von `server/.env`. Die IP-Adresse und der öffentliche Schlüssel (`.pub`) sind unkritisch.

## Phase A – im netcup-Kundenbereich (ca. 20 Minuten)

1. Im netcup **Server Control Panel (SCP)** deinen Server öffnen und die **IP-Adresse** (IPv4 und IPv6) notieren.
2. **Betriebssystem installieren** (im SCP unter „Medien“/„Images“): Empfehlung **Ubuntu 24.04 LTS** (wird bis 2029 mit
   Sicherheitsupdates versorgt); Debian 12 geht ebenso, die Skripte können beides. Wähle das Standard-/Minimal-Image ohne
   Zusatzpakete (kein Plesk o. Ä.). Falls das SCP die Auswahl eines SSH-Schlüssels anbietet, nimm den aus Phase B Schritt 1
   (dann zuerst Phase B). Sonst wird ein Root-Passwort vergeben; das brauchst du nur für die allererste Anmeldung.
3. **Snapshot-Möglichkeit** im SCP anschauen (Schnappschuss des ganzen Servers). Nach Phase C einen ersten anlegen: kostet bei
   netcup meist nichts oder wenig und ist die Notbremse.
4. Rechnungs-/Laufzeitdaten: nichts zu tun, nur im Kopf: der Tarif läuft 6 Monate.

## Phase B – SSH-Schlüssel und erste Anmeldung (ca. 15 Minuten)

1. Terminal auf dem Mac öffnen, Schlüsselpaar erzeugen (bei Fragen einfach Enter; eine Passphrase ist empfehlenswert):
   ```
   ssh-keygen -t ed25519 -C "sphaerae-server"
   cat ~/.ssh/id_ed25519.pub
   ```
   Die zweite Zeile zeigt den **öffentlichen** Schlüssel (beginnt mit `ssh-ed25519`). Der ist harmlos.
2. Zum Server verbinden (IP einsetzen; beim ersten Mal „yes“ tippen):
   ```
   ssh root@DEINE-IP
   ```
   Falls der Schlüssel noch nicht auf dem Server ist, gibt es die Anmeldung per Root-Passwort; dann einmalig auf dem Server:
   ```
   mkdir -p ~/.ssh && echo "EINGEFÜGTER ÖFFENTLICHER SCHLÜSSEL" >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys
   ```
   Dann `exit`, neu anmelden, und es muss ohne Passwort klappen. **Erst dann weiter.**

## Phase C – Server absichern und Docker installieren (ca. 20 Minuten, alles auf dem Server)

Sobald dieser Stand im Repo auf GitHub (Branch `main`) liegt, holst du die Skripte so (als root):
```
apt-get update && apt-get install -y curl
B=https://raw.githubusercontent.com/chillkrote/unternehmenskennzahlen/main/server/deploy/einrichtung
for f in 01-haerten.sh 02-docker.sh; do curl -fsSLO $B/$f; done
bash 01-haerten.sh
```
Das Skript: spielt Updates ein, legt den Benutzer `sphaerae` an, kopiert deinen öffentlichen Schlüssel dorthin, sperrt Passwort-
und root-Anmeldung, schaltet die Firewall auf 22/80/443, aktiviert automatische Sicherheitsupdates und legt 2 GB Reserve-Speicher an.
Es bricht ab, wenn kein Schlüssel hinterlegt ist, damit du dich nie aussperrst.

**Wichtig:** Öffne vor dem Schließen ein zweites Terminal und teste `ssh sphaerae@DEINE-IP`. Klappt es, geht es weiter:
```
bash 02-docker.sh
```
Danach als `sphaerae` anmelden (`exit`, dann `ssh sphaerae@DEINE-IP`). Jetzt einen Server-Schnappschuss im SCP anlegen („frisch gehärtet“).

## Phase D – Domain (DNS) für den Test (ca. 10 Minuten, im netcup-Kundenbereich)

Zuerst nur der Test-Name, nicht die echte Adresse:

| Name | Typ | Wert |
|---|---|---|
| `neu.sphaerae.de` | A | deine IPv4-Adresse |
| `neu.sphaerae.de` | AAAA | deine IPv6-Adresse (falls im SCP angezeigt) |

TTL 300 setzen, falls einstellbar. Prüfen (nach wenigen Minuten, auf dem Mac): `dig +short neu.sphaerae.de` muss deine IP zeigen.
Hinweis: Solange `sphaerae.de` selbst noch nicht auf den Server zeigt, bleibt die heutige GitHub-Fassung unberührt.

## Phase E – Plattform installieren (ca. 30 Minuten, als `sphaerae`)

```
B=https://raw.githubusercontent.com/chillkrote/unternehmenskennzahlen/main/server/deploy/einrichtung
curl -fsSLO $B/03-installieren.sh
SITE_ADDRESS=neu.sphaerae.de bash 03-installieren.sh
```
Das Skript holt den Code (ohne die großen PDFs), erzeugt die Passwörter selbst und legt sie in `server/.env`, baut die Seite,
prüft sie auf unzulässige Quellen (Yahoo-Kurse bleiben draußen, Entscheidung E1), startet Datenbank/API/Webserver, lädt die Daten
und prüft zum Schluss vier Adressen. **Sichere danach die Passwörter** (`cat /srv/sphaerae/repo/server/.env`, in die
Passwortverwaltung kopieren, nicht in den Chat).

Test: im Browser `https://neu.sphaerae.de` öffnen: Bank-Terminal, Weltkugel, Suche. Bei Fehlern kopierst du mir die Ausgabe
des Skripts (nicht die `.env`) in den Chat.

## Phase F – Automatik und Sicherung (ca. 15 Minuten)

```
curl -fsSLO $B/04-timer.sh && sudo bash 04-timer.sh
```
Das stellt zwei Wecker: täglich 03:30 Datenbanksicherung (14 Tage lokal), täglich 05:00 Aktualisierung (neuer Stand aus GitHub,
Seite neu bauen, Daten neu laden, Prüfung; bei Fehlschlag wird die alte Seite zurückgestellt).

**Sicherung außerhalb des Servers:** Eine Kopie nur auf dem Server schützt nicht vor dessen Verlust. Vorgesehen sind `restic`
und `rclone` mit Google Drive (kostenlos). Das braucht einmal deine Google-Anmeldung im Browser; dazu gebe ich dir dann
eine eigene kurze Anleitung (Phase F2).

## Phase G – Abnahme und Umschalten (erst nach deiner Freigabe)

Vor dem Umschalten von `sphaerae.de` sind drei Dinge zu klären, weil die Seite dann öffentlich unter deiner Domain steht:

* **Lizenzfragen offen (E2–E5):** Comtrade durch BACI ersetzen (ist technisch schon so), IPU Parline nur nicht kommerziell,
  Nachrichten nur verlinken, PDFs verlinken statt ausliefern. Und E6 (Yahoo-Abschlüsse) „später entscheiden“, jetzt wird es fällig.
* **Das GitHub-Repo ist öffentlich** und enthält u. a. `governance/` mit Personenprofilen. Eine Entscheidung ist offen.
* Impressum/Datenschutzangaben für eine öffentliche deutsche Website (Pflicht, ich entwerfe die Texte, du prüfst sie).

Umschalten (nur wenn du „los“ sagst):
1. In `server/.env` `SITE_ADDRESS=sphaerae.de` (oder `sphaerae.de, www.sphaerae.de`) setzen, `docker compose -f server/docker-compose.yml up -d`.
2. Im netcup-DNS die A/AAAA-Einträge für `sphaerae.de` und `www` auf den Server setzen (TTL vorher 24 h im Voraus auf 300 s).
3. `bash server/deploy/einrichtung/pruefen.sh sphaerae.de`.

**Rückfallweg:** Die GitHub-Pages-Fassung wird nicht abgeschaltet und läuft weiter (Workflow `terminal.yml`). Geht etwas schief:
DNS-Einträge zurücknehmen (wegen TTL 300 s binnen Minuten wirksam). Der Server selbst hat zusätzlich den Snapshot aus dem SCP
und die Datenbanksicherungen (`server/deploy/restore.sh`).

## Zeitplan in einem Blick

| Wann | Was | Wer |
|---|---|---|
| Heute | A, B: Image, Schlüssel, Anmeldung | Robin |
| Heute | C: Absichern, Docker | Robin (Befehle von mir) |
| Heute/morgen | D, E: Test-Domain, Plattform läuft unter `neu.sphaerae.de` | Robin + Claude (Fehlersuche) |
| danach | F: Timer, Backup außerhalb | Robin + Claude |
| vor Livegang | Lizenzentscheidungen, Repo-Sichtbarkeit, Impressum | Robin entscheidet, Claude bereitet vor |
| Livegang | G: Domain umschalten, Rückfall bereit | Robin auf Freigabe |

## Was ich von dir brauche

1. Welches Betriebssystem du installiert hast (Ubuntu 24.04 oder Debian).
2. Die **IPv4-Adresse** (und IPv6), kein Passwort.
3. Ob `sphaerae.de` bei netcup selbst registriert ist (dann im SCP unter „Domains/DNS“ einstellbar).
4. Danach nur noch: das Ergebnis jedes Schritts, bei Fehlern die Ausgabe.
