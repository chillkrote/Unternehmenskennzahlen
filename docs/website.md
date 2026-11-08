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

## Live-Kurse
Auf der Website (nicht im Artifact, nicht als lokale Datei) lädt `finanz.js` alle zwei Minuten
`https://raw.githubusercontent.com/chillkrote/Unternehmenskennzahlen/daten-live/live.json` nach. Die Datei erzeugt der Workflow
`live.yml` alle 30 Minuten (Mo-Fr 00-22 Uhr UTC, am Wochenende stündlich) aus Yahoo Finance, ca. 15 Minuten verzögert; sie liegt als einziger
überschriebener Commit auf dem Zweig `daten-live`, nicht in main. Aktualisiert werden die Marktpuls-Kacheln (Terminal und Weltkugel) und die Kurse
der Leitindizes; die Seite nennt den Abrufzeitpunkt. Zum Testen: `...index.html?live=<Adresse einer live.json>`.
Grenzen: kein echter Echtzeitkurs (kostenlos nicht zu haben), GitHub-Zeitpläne kommen mit Verspätung, raw.githubusercontent.com hält Antworten bis zu 5 Minuten im Cache.
