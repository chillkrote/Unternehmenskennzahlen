# Website (GitHub Pages)

`terminal.yml` veröffentlicht nach jedem Build auf `main` (Datenänderung oder Code) automatisch `bankterminal.html`,
`weltkugel.html` und eine Startseite auf GitHub Pages. Es gibt keinen eigenen Server und keine Zusatzkosten.

## Einmalig einzustellen (Repo-Einstellungen)
1. Settings > Pages > Build and deployment > Source: **GitHub Actions**.
2. Sichtbarkeit beachten: Eine Pages-Seite ist öffentlich erreichbar, auch wenn das Repo privat ist
   (privates Repo plus Pages braucht einen bezahlten GitHub-Plan; nur Enterprise Cloud kann Pages auf Mitglieder beschränken).
   Die Seite enthält alle eingebetteten Daten. Dokumentlinks (`github.com/.../raw/main/...`) funktionieren nur für Personen mit Repo-Zugriff.
3. Danach einmal `Terminal bauen` von Hand starten (Actions > Terminal bauen > Run workflow).

URL: `https://chillkrote.github.io/unternehmenskennzahlen/`

## Größe
Weltkugel mit allen Unternehmen ca. 45 MB, Pages liefert sie gzip-komprimiert aus (deutlich kleiner). Grenze von Pages: 1 GB.
