# Unternehmenskennzahlen

Sammlung von Rohdaten, Quellen und Originaldokumenten (Jahresabschlüsse, Geschäfts- und Offenlegungsberichte) für Kennzahlenvergleiche von Unternehmen.

Jede Erhebung liegt in einem eigenen Ordner, gruppiert nach Branche:

```
<branche>/<erhebung>/
  README.md      Umfang, Quellen, Methodik, Lücken
  dokumente/     Originaldokumente je Unternehmen (+ index.csv mit Quelle, Abrufdatum, SHA-256)
  webseiten/     HTML-Schnappschüsse, wo die Quelle keine Datei war
  rohdaten/      extrahierte Werte (JSON/CSV), Exporte, Skripte
  auswertung/    fertige Auswertungen (Excel, Listen), archiv/ für ältere Stände
```

## Stammdaten

Jedes Unternehmen hat genau eine zentrale ID (`U000123`, [stammdaten/](stammdaten/)), unabhängig von ISIN und Namensschreibweise. Eine Prüfung (`stammdaten/pruefe_ids.py`, im Build und im Workflow) stellt sicher, dass jede ISIN nur bei einer ID steht und keine ID-Verweise ins Leere zeigen.

## Erhebungen

| Ordner | Inhalt | Stand |
|---|---|---|
| [banken/bilanzvergleich-gj2025](banken/bilanzvergleich-gj2025/) | 129 deutsche Banken (Sparkassen, Genossenschaftsbanken, Landesbanken, Privatbanken): HGB-Bilanzen, Eigenkapital, Kernkapital, Pillar-3-Offenlegung (KM1, CC1, OV1) zum 31.12.2025 | 26.10.2026 |
| [boersennotierte-unternehmen](boersennotierte-unternehmen/) | alle in Deutschland notierten Aktiengesellschaften (rund 540), je Branche eine Excel mit Bilanz-, GuV-, Cashflow-, Aktionärs- und Kapitalmarktdaten | 27.10.2026 |
| [zeitreihen](zeitreihen/) | Zeitreihen im Langformat (Banken, Bundesbank-Gruppenreihen), Stammdaten der Banken | 27.10.2026 |
| [governance](governance/) | Vorstand, Aufsichtsrat, Vergütung und Mandate (Pilot: Banken, DAX-Werte) | 27.10.2026 |
| [volkswirtschaft](volkswirtschaft/) | VWL-Reihen (Eurostat, OECD, ifo), Prognosen, Konjunkturindikatoren | 27.10.2026 |
| [termine](termine/) | Berichtstermine und automatischer Abruf neuer Berichte | 27.10.2026 |

Werkzeuge: [app](app/) (Terminal, eine HTML-Datei mit eingebetteten Daten), [desktop](desktop/) (macOS-App des Terminals), [review](review/) (Prüfberichte zum Gesamtprojekt). Automatische Abläufe stehen unter `.github/workflows/`.

Neue Erhebungen (andere Branchen, weitere Geschäftsjahre) bekommen einen neuen Ordner nach demselben Schema.

## Hinweise

- Die Dokumente sind öffentlich zugängliche Veröffentlichungen der jeweiligen Unternehmen bzw. des EBA-Pillar-3-Datenhubs. Urheberrechte liegen bei den Herausgebern; das Repository ist privat und dient der Nachvollziehbarkeit der Auswertung.
- Dokumente werden ohne Git LFS als normale Git-Dateien abgelegt (Entscheidung 27.10.2026). GitHub lehnt Dateien über 100 MB ab; solche Dateien werden nicht gespeichert, sondern gemeldet.
