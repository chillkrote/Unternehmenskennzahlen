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

## Erhebungen

| Ordner | Inhalt | Stand |
|---|---|---|
| [banken/bilanzvergleich-gj2025](banken/bilanzvergleich-gj2025/) | 129 deutsche Banken (Sparkassen, Genossenschaftsbanken, Landesbanken, Privatbanken): HGB-Bilanzen, Eigenkapital, Kernkapital, Pillar-3-Offenlegung (KM1, CC1, OV1) zum 31.12.2025 | 26.10.2026 |
| [boersennotierte-unternehmen](boersennotierte-unternehmen/) | alle in Deutschland notierten Aktiengesellschaften (rund 540), je Branche eine Excel mit Bilanz-, GuV-, Cashflow-, Aktionärs- und Kapitalmarktdaten | 27.10.2026 |

Neue Erhebungen (andere Branchen, weitere Geschäftsjahre) bekommen einen neuen Ordner nach demselben Schema.

## Hinweise

- Die Dokumente sind öffentlich zugängliche Veröffentlichungen der jeweiligen Unternehmen bzw. des EBA-Pillar-3-Datenhubs. Urheberrechte liegen bei den Herausgebern; das Repository ist privat und dient der Nachvollziehbarkeit der Auswertung.
- Dateien über ca. 50 MB sollten künftig per Git LFS abgelegt werden. Die Geschäftsberichte unter `boersennotierte-unternehmen/` liegen als normale Git-Dateien im Repo (je unter 100 MB).
