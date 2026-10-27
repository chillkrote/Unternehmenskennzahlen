# Terminal (Prototyp)

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

## Bankenansichten (über Branche Banken erreichbar, jetzt ohne F-Tasten)

| Kürzel | Inhalt |
|---|---|
| GRP | Gruppenvergleich: Passivstruktur, Kennzahlen-Mediane, CET1-Zusammensetzung (CC1), RWA-Aufteilung (OV1) |
| QUOT | Verteilung einer Quote je Gruppe (Punkte je Bank, Median, Quartilsband) und Streudiagramm Risikodichte gegen Kapital |
| CMP | Einzelbankvergleich: Kennzahlenmatrix mit Perzentil, Abweichung vom Gruppenmedian, Kapitalquoten gegen Anforderung, Passiv- und RWA-Struktur, Bilanzsumme im Zeitverlauf |
| RANK | sortierbare Liste aller Banken, filterbar nach Gruppe |
| MKT | Börsendaten: Kurs, 1T/1M/YTD/1J, 52-Wochen-Spanne, Börsenwert, Börsenwert / HGB-EK, indexierter Kursverlauf; Kennzahlenvergleich aus den Konzernabschlüssen (KGV, KBV, Kurs/mat. Buchwert, Dividendenrendite, Ausschüttungsquote, RoE, RoTE, RoA, Cost-Income-Ratio, Vorsteuermarge, Steuerquote, Zinsanteil, Zinsmarge, EK-Quote, Kreditanteil, Goodwill/EK, Wachstum), Rangfolge je Kennzahl und Bewertung gegen Rentabilität (Kurs/mat. Buchwert gegen RoTE) |

Oben läuft zusätzlich eine Kursleiste mit den letzten Schlusskursen; in CMP erscheinen Börsenwert, Börsenwert / HGB-EK und die Aktie, wo vorhanden.

## Branchen, Unternehmen und Profilseiten

Das Terminal kennt keinen Unterschied mehr zwischen Banken und anderen Unternehmen: Banken sind eine Branche unter allen.
Aufbau von oben nach unten: **Branche** → **Untergruppe** (z. B. Sparkassen, Genossenschaftsbanken; für andere Branchen die Spalte
„Gruppe“) → **Notierung** (börsennotiert / nicht börsennotiert, als Filter) → **Unternehmen**.

* F1 Branchen: Kacheln, Mediantabelle je Branche, Streudiagramm aller Unternehmen.
* F2 Branche: Filter für Branche, Untergruppe und Notierung; Tabelle, Rangfolge, Profil gegen die übrigen Branchen, Kurse, Kennzahlen gegeneinander.
  In der Branche Banken führt der Block „Spezialansichten Banken“ zu den bisherigen Ansichten GRP, QUOT, CMP, RANK, MKT und TS.
* F3 Vergleich: bis zu 6 Unternehmen aus beliebigen Branchen (Perzentile in der eigenen Branche, Abstand zum Branchenmedian, Kurse).
* F4 Verzeichnis: alle Unternehmen mit Suche und Filter.
* Profilseite je Unternehmen (`#firma-<id>`, auch über die Kommandozeile mit dem Namen): Kennzahlen mit Branchen- und Gruppenmedian,
  Zeitreihen, Kurse und alle Dokumente des Unternehmens aus dem Repo mit Download- und GitHub-Link, Quelle und Prüfsumme.

Nicht börsennotierte Unternehmen erscheinen mit Abschlusskennzahlen, ohne Kurs- und Bewertungswerte. Ob ein Unternehmen notiert ist,
steht in der Spalte „Börsennotiert“ der Branchentabelle bzw. in `zeitreihen/stammdaten.csv` (Spalte `notiert`); fehlt sie, gilt ein
Unternehmen mit Ticker oder ISIN als notiert. Neue Unternehmen kommen über `zeitreihen/stammdaten.csv` (Spalten `unternehmen_id`, `name`,
`branche`, `gruppe`, optional `notiert`, `isin`, `ticker`, `sitz`) oder über Branchen-Excel hinzu.

Datenschicht `unternehmen.py` (liest alles ohne Codeänderung):

* Branchen-Excel in beliebigen Ordnern des Repos (außer `banken/`, `zeitreihen/`, `app/`): Spalten über die Überschrift, Aliase in
  `unternehmen_katalog.json`; unbekannte Zahlenspalten werden als weitere Kennzahl übernommen. Neue Branchen erscheinen automatisch.
* Banken aus dem Bilanzvergleich (HGB-Einzelabschluss) plus Börsendaten der selbst notierten Institute.
* `zeitreihen/zeitreihe_lang.csv`: Reihen je Unternehmen (Profilseite); der letzte Wert füllt fehlende Kennzahlen.
* Dokumente: Dateien unter `…/dokumente/<unternehmen-id>/` (auch `webseiten/`, `berichte/`, `geschaeftsberichte/`), dazu jede `index.csv` in
  solchen Ordnern (Spalten u. a. `unternehmen_id` oder `unternehmen`/`bank`, `datei`, `titel`, `dokumentart`, `jahr`, `quelle_url`,
  `abruf`, `sha256`). Download-Links zeigen auf `https://github.com/<repo>/raw/main/<pfad>`; Repo über `TERMINAL_REPO` einstellbar.
* Solange außer den Banken keine Branche Daten hat, zeigt das Terminal Beispieldaten (`unternehmen_demo.py`, Yahoo Finance) und kennzeichnet sie.

## Täglicher Abruf

`.github/workflows/marktdaten.yml` läuft an Handelstagen um 18:30 UTC (nach Xetra-Schluss), holt die Kurse, baut das Terminal neu und committet `app/data/markt.json` und `app/dist/` nach main. Manuell startbar unter Actions → „Börsendaten Bank-Terminal“ → Run workflow. Yahoo Finance hat keine offizielle API; fällt ein Ticker aus, steht er unter `fehler` in `markt.json`, die übrigen werden trotzdem geschrieben.

Die Kommandozeile oben nimmt `GRP`, `QUOT`, `CMP`, `RANK` oder einen Banknamen (übernimmt die Bank in CMP). Klick auf einen Punkt in QUOT oder eine Zeile in RANK übernimmt die Bank ebenfalls.

Gruppenwerte ohne Zusatzeinträge (DZ BANK, DekaBank, DKB). KM1-Werte stammen teils von Gruppen- oder Konzernebene; die RWA-Dichte gegen die HGB-Bilanzsumme ist dort nur ein Richtwert.

## Startseite und Bereiche
Das Terminal öffnet mit einer Startseite (`#start`) und zwei Kacheln. **Unternehmen** führt in das Branchen-Terminal (F1 Branchen, F2 Branche, F3 Vergleich, F4 Verzeichnis, Profilseiten `#firma-<id>` mit Kennzahlen, Gremien, Vergütung und Dokumenten). **Volkswirtschaft** führt in das makroökonomische Terminal (F1 Überblick, F2 Zeitreihen, F3 Länder, F4 Berichte & Quellen). Die Daten dafür liegen in `volkswirtschaft/` und werden von `vwl.py` eingelesen; `build.py` bettet sie ein.

Gremien und Vergütung auf der Profilseite kommen aus `governance/*.csv` und hängen über `unternehmen_id` am Unternehmen; neue Zeilen erscheinen nach `python3 app/build.py` ohne Codeänderung.
