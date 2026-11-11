# Server-Einrichtung (netcup) – Skripte

Die Schritt-für-Schritt-Anleitung für Einsteiger steht in [docs/server-einrichtung.md](../../../docs/server-einrichtung.md).
Diese Skripte sind absichtlich klein, lesbar und wiederholbar (ein zweiter Lauf richtet keinen Schaden an). Sie enthalten
**keine Geheimnisse**; Passwörter erzeugt das Skript auf dem Server selbst und legt sie nur dort ab (`server/.env`, Rechte 600).

| Reihenfolge | Skript | Läuft als | Zweck |
|---|---|---|---|
| 1 | `01-haerten.sh` | root | Updates, Benutzer `sphaerae`, SSH nur mit Schlüssel, Firewall, Auto-Sicherheitsupdates, Swap |
| 2 | `02-docker.sh` | root | Docker Engine + Compose aus dem offiziellen Docker-Repository |
| 3 | `03-installieren.sh` | sphaerae | Code holen, `.env` erzeugen, Oberfläche bauen, Lizenzprüfung, Stack starten, Daten laden |
| 4 | `04-timer.sh` | root | tägliche Sicherung und tägliche Aktualisierung (systemd-Timer) |
| – | `aktualisieren.sh` | sphaerae | neuen Stand holen und ausrollen (von Hand oder durch den Timer), mit Rückfallpunkt |
| – | `pruefen.sh` | beliebig | Gesundheitsprüfung des laufenden Servers (Smoke-Test ohne Browser) |
