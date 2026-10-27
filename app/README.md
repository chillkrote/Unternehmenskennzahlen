# Bank-Terminal (Prototyp)

Grafische Auswertung des Bilanzvergleichs GJ 2025 im Stil eines Finanzterminals. Erste Beispielansichten, noch kein fertiges Programm.

## Starten

```bash
pip install openpyxl
python3 app/build.py            # liest die Excel, schreibt data/banken.json und dist/bankterminal.html
open app/dist/bankterminal.html # bzw. im Browser öffnen
```

Andere Excel-Datei: `python3 app/build.py --excel pfad/zur/datei.xlsx`.

## Aufbau

| Datei | Aufgabe |
|---|---|
| `datenschicht.py` | liest `banken/bilanzvergleich-gj2025/auswertung/Bilanzvergleich_Banken_GJ2025.xlsx` (Blätter Übersicht, Offenlegung, CC1, OV1, Bilanzen, Zeitreihe) und baut einen Datensatz je Bank. Spalten werden über ihre Überschrift gefunden, neue Banken und Spalten kommen ohne Codeänderung mit. |
| `build.py` | ruft die Datenschicht auf und bettet die Daten in die Oberfläche ein |
| `src/terminal.html` | Oberfläche (HTML/CSS/JS ohne Bibliotheken, Diagramme als SVG) |
| `data/banken.json` | erzeugter Datensatz |
| `dist/bankterminal.html` | erzeugte, eigenständige Seite (lokal öffnen); `bankterminal.fragment.html` ist die Fassung ohne Dokumentgerüst für das Artifact |

Nach jeder Änderung an der Excel (z. B. durch `rohdaten/skripte/build.py`) einfach `app/build.py` neu laufen lassen.

## Ansichten

| Taste | Kürzel | Inhalt |
|---|---|---|
| F1 | GRP | Gruppenvergleich: Passivstruktur, Kennzahlen-Mediane, CET1-Zusammensetzung (CC1), RWA-Aufteilung (OV1) |
| F2 | QUOT | Verteilung einer Quote je Gruppe (Punkte je Bank, Median, Quartilsband) und Streudiagramm Risikodichte gegen Kapital |
| F3 | CMP | Einzelbankvergleich: Kennzahlenmatrix mit Perzentil, Abweichung vom Gruppenmedian, Kapitalquoten gegen Anforderung, Passiv- und RWA-Struktur, Bilanzsumme im Zeitverlauf |
| F4 | RANK | sortierbare Liste aller Banken, filterbar nach Gruppe |

Die Kommandozeile oben nimmt `GRP`, `QUOT`, `CMP`, `RANK` oder einen Banknamen (übernimmt die Bank in CMP). Klick auf einen Punkt in QUOT oder eine Zeile in RANK übernimmt die Bank ebenfalls.

Gruppenwerte ohne Zusatzeinträge (DZ BANK, DekaBank, DKB). KM1-Werte stammen teils von Gruppen- oder Konzernebene; die RWA-Dichte gegen die HGB-Bilanzsumme ist dort nur ein Richtwert.
