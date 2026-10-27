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
| `marktdaten.py` | holt Schlusskurse (letztes Jahr für die Ansichten, bis zu zehn Jahre als `kurse_hist` für die Korrelation), Renditen, Börsenwert und die letzten Konzernabschlüsse (GuV, Bilanz) über yfinance, rechnet daraus die Kennzahlen und schreibt `data/markt.json`, getrennt von den GJ-Bilanzdaten |
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

## Wochenkurse aller Notierten

`python3 app/kurse_historie.py` holt über yfinance (kostenlos) zehn Jahre Wochenschlusskurse für alle Ticker aus `data/unternehmen.json` und `data/markt.json` und schreibt `data/kurse_woche.json` (gemeinsame Datumsachse, je Ticker ein Array, null = keine Notiz; rund 1,5 MB, tägliche Kurse wären etwa 20 MB). Ticker ohne Börsenendung werden nacheinander an .DE, .F, .MU, .DU, .SG, .HM, .BE gesucht, nie ohne Endung (Verwechslung mit US-Tickern). `build.py` bettet die Datei ein. Stand 27.10.2026: 510 von 551 Tickern mit Kursen, 41 ohne Treffer (Liste unter `fehler`). Kurse in Börsenwährung, Londoner Kurse in Pence; Korrelationen auf Renditebasis sind davon unberührt.

## Täglicher Abruf

`.github/workflows/marktdaten.yml` läuft an Handelstagen um 18:30 UTC (nach Xetra-Schluss), holt die Kurse, baut das Terminal neu und committet `app/data/markt.json` und `app/dist/` nach main. Manuell startbar unter Actions → „Börsendaten Bank-Terminal“ → Run workflow. Yahoo Finance hat keine offizielle API; fällt ein Ticker aus, steht er unter `fehler` in `markt.json`, die übrigen werden trotzdem geschrieben.

Die Kommandozeile oben nimmt `GRP`, `QUOT`, `CMP`, `RANK` oder einen Banknamen (übernimmt die Bank in CMP). Klick auf einen Punkt in QUOT oder eine Zeile in RANK übernimmt die Bank ebenfalls.

Gruppenwerte ohne Zusatzeinträge (DZ BANK, DekaBank, DKB). KM1-Werte stammen teils von Gruppen- oder Konzernebene; die RWA-Dichte gegen die HGB-Bilanzsumme ist dort nur ein Richtwert.

## Startseite und Bereiche
Das Terminal öffnet mit einer Startseite (`#start`) und zwei Kacheln. **Unternehmen** führt in das Branchen-Terminal (F1 Branchen, F2 Branche, F3 Vergleich, F4 Verzeichnis, Profilseiten `#firma-<id>` mit Kennzahlen, Gremien, Vergütung und Dokumenten). **Volkswirtschaft** führt in das makroökonomische Terminal (F1 Überblick, F2 Zeitreihen, F3 Länder, F4 Berichte & Quellen). Die Daten dafür liegen in `volkswirtschaft/` und werden von `vwl.py` eingelesen; `build.py` bettet sie ein.

Gremien und Vergütung auf der Profilseite kommen aus `governance/*.csv` und hängen über `unternehmen_id` am Unternehmen; neue Zeilen erscheinen nach `python3 app/build.py` ohne Codeänderung.

## Korrelation (KOR, F6)

Statistische Korrelationsauswertung, vollständig im Browser gerechnet (`src/korrelation.js`, keine Bibliotheken, läuft daher auch im Artifact und in einer Desktop-App). Erreichbar über F6 in beiden Bereichen, die Startseite oder die Kommandozeile (`KORR`).

| Modus | Inhalt |
|---|---|
| Zeitreihen A ↔ B | zwei frei gewählte Reihen: VWL-Reihe und Land, Jahreskennzahl eines Unternehmens, Aktienkurs, Median einer Kennzahl je Branche, gleichgewichteter Kursindex einer Branche. Wahl von Zeitraum (Jahre), Frequenz (Jahr, Quartal, Monat, Tag), Transformation je Reihe (Niveau, Differenz, Veränderung zur Vorperiode, Log-Rendite, Veränderung zum Vorjahr), Verzögerung (Kreuzkorrelation), Pearson oder Spearman. Ausgabe: r, ρ, p-Wert, p-Wert mit effektiver Stichprobe, 95-%-Intervall (Fisher-z), R², Regressionsgerade, Streudiagramm, Kreuzkorrelation, Verlauf, automatische Hinweise |
| Matrix | bis 14 Reihen, alle Paare als Heatmap; Klick auf eine Zelle öffnet das Paar. Voreinstellungen: VWL-Kernreihen, Kurse großer Werte, Branchen-Kursindizes |
| Querschnitt | zwei Kennzahlen über alle Unternehmen (Filter Branche, Notierung, optional log₁₀), Streudiagramm mit Klick ins Profil, Kennzahlenmatrix |

Regeln: Perioden ohne Wert in einer der beiden Reihen fallen heraus, es wird nichts interpoliert. Projektionen (`prognose_ab`) sind ausgeschlossen. Bei Umrechnung auf gröbere Frequenz gilt der Mittelwert für Raten und Salden, sonst der letzte Wert. Hinweise erscheinen bei n < 10 und n < 30, bei Niveaureihen mit Trend (Scheinkorrelation), hoher Autokorrelation (n_eff nach Bartlett), überlappenden Vorjahresraten, Durbin-Watson < 1, starker Abweichung zwischen Pearson und Spearman und beim besten von mehreren Lags (nicht multipel getestet). Der Datenbestand bestimmt, was auswertbar ist: Jahreskennzahlen mit Zeitreihe gibt es derzeit nur für Banken, Kurse: Banken mit Börsennotierung täglich bis zu zehn Jahre (`kurse_hist` in `markt.json`), alle übrigen Notierten als Wochenschlusskurse über zehn Jahre (`data/kurse_woche.json`); die Ansichten zeigen weiter das letzte Jahr. Branchen-Kursindizes (gleichgewichtet, Wochenbasis) gibt es damit für alle Branchen. Neue Reihen im Repo erscheinen automatisch.

Die Statistik wurde gegen SciPy geprüft (Pearson, Spearman, p-Werte, Regression stimmen auf mindestens 10 Stellen überein).

## Bedienung der Diagramme

* **UEB 2 / BRA 5 (Streudiagramme):** Der Punkt unter der Maus (Umkreis von ca. 14 px) wird vergrößert und beschriftet, die übrigen treten zurück; Tooltip mit Branche und Kennzahlen; Klick öffnet das Profil. Legende schaltet Branchen aus (Doppelklick: nur diese), Hover auf die Legende oder eine Branchenzeile in UEB 1 hebt die Branche hervor. Mausrad zoomt, Ziehen verschiebt, Doppelklick setzt zurück; die Suche markiert ein Unternehmen (Enter öffnet das Profil). Das Diagramm passt sich der Fensterbreite an.
* **BRA:** Hover über eine Tabellenzeile oder einen Balken markiert dasselbe Unternehmen im Streudiagramm und umgekehrt; in Tabellen leuchtet zusätzlich die Spalte unter der Maus. Spaltenköpfe sind per Tab erreichbar und per Enter sortierbar.
* **MKT 2 und TS:** Fadenkreuz mit Wertetabelle aller Reihen am nächsten Messpunkt.
* **KOR (Matrix):** Zeile und Spalte der Zelle unter der Maus werden hervorgehoben.
