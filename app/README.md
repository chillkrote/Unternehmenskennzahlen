# Bank-Terminal (Prototyp)

Grafische Auswertung des Bilanzvergleichs GJ 2025 im Stil eines Finanzterminals. Erste Beispielansichten, noch kein fertiges Programm.

## Starten

```bash
pip install -r app/requirements.txt
python3 app/marktdaten.py       # optional: Börsenkurse über yfinance -> data/markt.json
python3 app/build.py            # liest die Excel, schreibt data/banken.json und dist/bankterminal.html
open app/dist/bankterminal.html # bzw. im Browser öffnen
```

Andere Excel-Datei: `python3 app/build.py --excel pfad/zur/datei.xlsx`.

## Aufbau

| Datei | Aufgabe |
|---|---|
| `datenschicht.py` | liest `banken/bilanzvergleich-gj2025/auswertung/Bilanzvergleich_Banken_GJ2025.xlsx` (Blätter Übersicht, Offenlegung, CC1, OV1, Bilanzen, Zeitreihe) und baut einen Datensatz je Bank. Spalten werden über ihre Überschrift gefunden, neue Banken und Spalten kommen ohne Codeänderung mit. |
| `build.py` | ruft die Datenschicht auf und bettet die Daten in die Oberfläche ein |
| `marktdaten.py` | holt Schlusskurse (12 Monate), Renditen, Börsenwert und die letzten Konzernabschlüsse (GuV, Bilanz) über yfinance, rechnet daraus die Kennzahlen und schreibt `data/markt.json`, getrennt von den GJ-Bilanzdaten |
| `boersen_ticker.json` | Zuordnung Bank -> Ticker. `Institut` = Bank selbst notiert (Deutsche Bank, Commerzbank, pbb, UmweltBank, Merkur, Baader), `Mutter` = nur die Bank- oder Finanzgruppe darüber ist notiert (UniCredit, ING, Santander, State Street, flatexDEGIRO, GRENKE, MLP, Akbank, İşbank, JPMorgan, Goldman Sachs, Morgan Stanley, Citigroup, UBS, Standard Chartered, W&W; norisbank und BHW über Deutsche Bank). ProCredit ist selbst notiert. `bilanzwaehrung` angeben, wenn der Konzern in anderer Währung bilanziert als die Aktie notiert. Neue Ticker hier eintragen. |
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
| F5 | MKT | Börsendaten: Kurs, 1T/1M/YTD/1J, 52-Wochen-Spanne, Börsenwert, Börsenwert / HGB-EK, indexierter Kursverlauf; Kennzahlenvergleich aus den Konzernabschlüssen (KGV, KBV, Kurs/mat. Buchwert, Dividendenrendite, Ausschüttungsquote, RoE, RoTE, RoA, Cost-Income-Ratio, Vorsteuermarge, Steuerquote, Zinsanteil, Zinsmarge, EK-Quote, Kreditanteil, Goodwill/EK, Wachstum), Rangfolge je Kennzahl und Bewertung gegen Rentabilität (Kurs/mat. Buchwert gegen RoTE) |

Oben läuft zusätzlich eine Kursleiste mit den letzten Schlusskursen; in CMP erscheinen Börsenwert, Börsenwert / HGB-EK und die Aktie, wo vorhanden.

## Branchen (Unternehmen außerhalb des Bankensektors)

Oben rechts schaltet der Schalter „Banken / Branchen“ um. Im Bereich Branchen gibt es drei Ansichten:
F1 Branchenübersicht (Kacheln, Mediantabelle je Branche, Streudiagramm aller Unternehmen),
F2 Branche (Ranglisten, Profil gegen die übrigen Branchen, Kursverlauf, Bewertung gegen Rentabilität),
F3 Unternehmen (bis zu 6 Unternehmen aus allen Branchen: Kennzahlenmatrix mit Perzentilen, Abstand zum Branchenmedian, indexierte Kurse).
Befehlszeile: `BRA`, `UCMP`, `UEB` oder ein Firmenname.

Datenschicht: `unternehmen.py` liest alle Excel-Tabellen unter `unternehmen*/` (bzw. Branchen-Ordnern) im Repo über die
Spaltenüberschriften. Welche Überschrift welche Kennzahl ist, steht samt Aliasen in `unternehmen_katalog.json`; neue Branchen
und Spalten erscheinen ohne Codeänderung. Fehlen die Tabellen, zeigt das Terminal Beispieldaten
(`unternehmen_demo.py`, Yahoo Finance, ca. 43 deutsche Werte) und kennzeichnet sie als solche.
`build.py` bettet das Ergebnis ein (`data/unternehmen.json`).

## Täglicher Abruf

`.github/workflows/marktdaten.yml` läuft an Handelstagen um 18:30 UTC (nach Xetra-Schluss), holt die Kurse, baut das Terminal neu und committet `app/data/markt.json` und `app/dist/` nach main. Manuell startbar unter Actions → „Börsendaten Bank-Terminal“ → Run workflow. Yahoo Finance hat keine offizielle API; fällt ein Ticker aus, steht er unter `fehler` in `markt.json`, die übrigen werden trotzdem geschrieben.

Die Kommandozeile oben nimmt `GRP`, `QUOT`, `CMP`, `RANK` oder einen Banknamen (übernimmt die Bank in CMP). Klick auf einen Punkt in QUOT oder eine Zeile in RANK übernimmt die Bank ebenfalls.

Gruppenwerte ohne Zusatzeinträge (DZ BANK, DekaBank, DKB). KM1-Werte stammen teils von Gruppen- oder Konzernebene; die RWA-Dichte gegen die HGB-Bilanzsumme ist dort nur ein Richtwert.
