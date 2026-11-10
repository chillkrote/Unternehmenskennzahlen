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
| `boersen_abruf.py` | Bereich BÖR: Wochenkurse über zehn Jahre und Kennzahlen (Stand, 1 T. bis 10 J., 52-Wochen-Spanne, Börsenwert) für Aktienindizes und große Unternehmen laut `boersen_katalog.json` über yfinance -> `data/boerse.json`; Workflow „Börsendaten Terminal“ werktags 22:00 UTC |
| `boersen_katalog.json` | Katalog: `indizes` (Name, Land, Gruppe Welt/OECD/Nicht-OECD, Region, Yahoo-Symbole als Kandidaten, `etf` wo nur ein ETF als Stellvertreter frei verfügbar ist) und `unternehmen` (Name, Symbol, Land, Sektor). Neue Einträge nur hier ergänzen |
| `vwl.py` (Prognosen) | liest `prognosen_institute.csv` (Deutschland), `prognosen_oecd.csv` und `prognosen_international.csv` (Konsensumfragen und Zentralbanken, 21 Länder und Euroraum) in dieselbe Liste; fehlt bei einer Zeile das Datum, gilt der Monat der Runde. Im Terminal (F5) wählt eine Länderliste das Land, Basis und Abgrenzung stehen im Hinweis je Zeile |
| `src/boerse.js` | Oberfläche des Bereichs BÖR |
| `finanz_abruf.py` | Marktpuls (VIX, VXN, OVX, GVZ, MOVE, Gold, Silber, Brent, Dollar-Index, Bitcoin, Ether über Yahoo; EZB-Stressindex CISS), Zinsstrukturkurven Euroraum (EZB) und USA (US-Finanzministerium) für heute, vor einem Monat und vor einem Jahr, alle EZB-Währungen über zehn Jahre -> `data/finanz.json`; Workflow „Börsendaten Terminal“ (Lauf `boerse`). Fällt eine Quelle aus, bleibt ihr alter Stand |
| `finanz_makro.py` | Welle 2: Inflation (OECD), Realzins und Realrendite (gerechnet aus BIS-Leitzins, OECD-Rendite und Inflation), Schuldenquote, Finanzierungssaldo und Börsenwert/BIP (Weltbank, Werte über sieben Jahre alt fehlen), Renditeaufschläge auf Bundesanleihen als CDS-Ersatz (OECD), Bankensektor je Euro-Land (EZB Supervisory Banking Statistics: CET1, RoE, CIR, NPL, LCR, Leverage) -> `data/finanz_makro.json`; läuft im Workflow „Weltkugel-Daten“ (täglicher Lauf, nach `boerse_welt.py`) |
| `live_abruf.py` | Live-Kurse: Marktpuls-Größen, zwölf Leitindizes, Rohstoffe, Bitcoin und Ether von Yahoo Finance (ca. 15 Minuten verzögert) -> `data/live.json` (nicht in main, in `.gitignore`); Workflow „Live-Kurse“ (`live.yml`) legt die Datei alle 30 Minuten als einzigen Commit auf den Zweig `daten-live`. `finanz.js` lädt sie auf der Website (github.io) alle zwei Minuten nach und aktualisiert Kacheln und Indexkurse an Ort und Stelle; im Artifact oder lokal bleibt der Build-Stand |
| `src/finanz.js` | Reiter BÖR F8 Marktpuls (Ampel, realisierte Volatilität der Indizes), F9 Zinskurven, F10 Währungen (Kreuzkurse), F11 Sektoren, Makro und Bankensektor (Welle 2; auf der Weltkugel färben Chips „Karte einfärben nach“ die Länder nach Inflation, Realzins, Schulden usw.) (Sektoren aus dem Feld `sektor` der Großunternehmen, nach Börsenwert gewichtet); die Marktpuls-Leiste steht auch auf der Weltkugel (Börse) |
| `src/terminal.html` | Oberfläche (HTML/CSS/JS ohne Bibliotheken, Diagramme als SVG) |
| `data/banken.json` | erzeugter Datensatz |
| `dist/bankterminal.html` | erzeugte, eigenständige Seite (lokal öffnen); `bankterminal.fragment.html` ist die Fassung ohne Dokumentgerüst für das Artifact |

Nach jeder Änderung an der Excel (z. B. durch `rohdaten/skripte/build.py`) einfach `app/build.py` neu laufen lassen.

## Server-Fassung (API-Modus)

`python3 app/build.py --nur-seite --api /api/v1 --ziel dist-api` baut dieselbe Oberfläche für den eigenen Server (`server/`,
Docker Compose): das Gesamtregister (rund 10 MB) wird nicht eingebettet, Verzeichnis (F4), Registerprofile (`#firma-U…` ohne
Kennzahlen) und die Befehlszeile fragen die Plattform-API ab (`src/api.js`: Zeitlimit, begrenzte Wiederholung, Zwischenspeicher,
Lade- und Fehlerzustände). Abschlussposten, Gremien, Vergütung und Dokumente (rund 21 MB) fehlen ebenfalls im eingebetteten
Unternehmensblock (`build.py: firmen_fuer_api`); das Profil lädt sie über `/companies/{id}/profile` nach, die Kennzahlen bleiben
für die Branchenansichten eingebettet. Auf der Weltkugel fehlen Beschreibung, Quelle, Website, LEI, Handelsregister, Rechtsform und Börse in der eingebetteten
Unternehmenstabelle (`globus.py: tabelle_schlank`); das Stammdaten-Fenster lädt sie über `/companies/{id}`. Die VWL-Reihenwerte (4,4 MB) sind ebenfalls nicht
eingebettet, nur die Abdeckung je Reihe; `src/vwl.js` (`bedarf`) lädt sie gesammelt über `/observations` nach, VWL-Ansichten, Korrelation und Weltkugel
zeichnen danach neu (Ereignis `sphaerae:vwl`). Grenzen der Kommunen, Bundestagswahlkreise und Kreise sowie Wahlwerte ab 10 Werten je
Einheit liegen als Dateien unter `wahlgeo/` (`globus.py: GEO_NACH_API`, `WERTE_NACHLADEN_AB_API`) und kommen erst, wenn eine Wahl sie braucht. Die Unternehmenstabelle der Weltkugel (Punkte, Ringe „ohne Ort“) steht als `geodaten/unternehmen.json` daneben (`globus.tabelle_schreiben`) und wird gleich nach dem Start geladen; VWL-Prognosen und Abgleich stehen in `data/vwl_prognosen.json` und kommen mit der Ansicht Prognosen (`vwl.js: progBedarf`); Parlamente, Kommunalwahlen, Güterexporte und Gliedstaaten-Grenzen stehen als `data/parlamente.json`, `data/kommunal.json`, `data/gueter.json` und `data/gliedstaaten.json` daneben, das Wahlregister der Weltkugel als `data/wahlen.json` (`globus.py: WAHLEN_DATEI`, geschrieben von `wahlgeo_schreiben`) (`build.py: BLOCK_NACHLADEN`, Lader `BLOCK` in `src/api.js`); `data/banken.json`, `data/unternehmen.json`, `data/markt.json`, `data/kurse_woche.json` und `data/boerse.json` lädt `start()` parallel (`BLOCK.warte`). Nach einer Änderung an `data/unternehmen.json` oder `volkswirtschaft/` den Server-ETL laufen lassen.
Ohne `--api` entsteht die bisherige Fassung unverändert (GitHub Pages, Artifact, Desktop-App).
Die Befehlszeile des Terminals und das Suchfeld der Weltkugel zeigen in der API-Fassung beim Tippen Vorschläge über `/search` (`src/suche.js`: Unternehmen, Länder, Branchen und die Kombination „Branche · Land“, die das gefilterte Verzeichnis öffnet; Pfeiltasten, Enter, Escape). Enter ohne markierten Vorschlag verhält sich wie bisher (Befehle, lokale Suche); test: `node app/tests/suche-smoke.js http://localhost:8080`.
Öffentliche Fassung ohne Yahoo-Daten (Lizenzentscheidung E1 in `docs/datenquellen.md`, noch offen): `--oeffentlich` (gedacht für die Server-Fassung mit `--api`) lässt Marktdaten, Wochenkurse, Börsenbereich und alle Yahoo-Werte der Unternehmen (`build.py: YAHOO_WERTE`, `ohne_yahoo_firmen`) sowie Yahoo-Einträge im Finanzpuls weg. Standard ist aus; der Server baut bis zur Entscheidung unverändert.
Die API-Adresse lässt sich zum Testen mit `?api=<url>` überschreiben. Test: `node app/tests/api-smoke.js http://localhost/bankterminal.html`.
Stand und Funktionsmatrix: [`docs/umsetzungsstand.md`](../docs/umsetzungsstand.md).

## Fußleiste: Impressum, Kontakt, About Sphaerae

Unten mittig (Terminal und Weltkugel) stehen drei Schaltflächen, die ein Textfenster öffnen. Die Texte liegen als Markdown in `app/seiten/` (`impressum.md`, `kontakt.md`, `about.md`) und werden beim Bau über `seiten.py` eingebettet; Oberfläche in `src/seiten.js`/`seiten.css`. Platzhalter `[[…]]` erscheinen gelb markiert. Anleitung: `app/seiten/README.md`. Test: `app/tests/seiten-smoke.js`.

## Bankenansichten (über Branche Banken erreichbar, jetzt ohne F-Tasten)

| Kürzel | Inhalt |
|---|---|
| GRP | Gruppenvergleich: Passivstruktur, Kennzahlen-Mediane, CET1-Zusammensetzung (CC1), RWA-Aufteilung (OV1) |
| QUOT | Verteilung einer Quote je Gruppe (Punkte je Bank, Median, Quartilsband) und Streudiagramm Risikodichte gegen Kapital |
| CMP | Einzelbankvergleich: Kennzahlenmatrix mit Perzentil, Abweichung vom Gruppenmedian, Kapitalquoten gegen Anforderung, Passiv- und RWA-Struktur, Bilanzsumme im Zeitverlauf |
| RANK | sortierbare Liste aller Banken, filterbar nach Gruppe |
| MKT | Börsendaten: Kurs, 1T/1M/YTD/1J, 52-Wochen-Spanne, Börsenwert, Börsenwert / HGB-EK, indexierter Kursverlauf; Kennzahlenvergleich aus den Konzernabschlüssen (KGV, KBV, Kurs/mat. Buchwert, Dividendenrendite, Ausschüttungsquote, RoE, RoTE, RoA, Cost-Income-Ratio, Vorsteuermarge, Steuerquote, Zinsanteil, Zinsmarge, EK-Quote, Kreditanteil, Goodwill/EK, Wachstum), Rangfolge je Kennzahl und Bewertung gegen Rentabilität (Kurs/mat. Buchwert gegen RoTE) |

Oben läuft zusätzlich eine Kursleiste mit den letzten Schlusskursen; in CMP erscheinen Börsenwert, Börsenwert / HGB-EK und die Aktie, wo vorhanden.

## Gesamtregister (alle Unternehmen der Unternehmenstabelle)

`app/register.py` liest `unternehmen-tabelle/Unternehmen_Tabelle.csv` (rund 32.600 Zeilen) und schreibt `data/register.json`: eine kompakte, spaltenweise Tabelle nur mit Stammdaten (Name, Land als ISO-Code, Sitz, Branche, ISIN, Ticker, Börse, Notierung, Index, LEI, Website, Quelle, Herkunftshinweis; rund 10 MB, gzip 1,3 MB). `build.py` bettet sie als `<script id="register">` ein, dieselbe Seite speist auch die Weltkugel.

* F4 Verzeichnis zeigt alle Zeilen mit Suche (Name, Ticker, ISIN, LEI), Filter Land, Branche, Notierung und „mit/ohne Kennzahlen“, 100 Zeilen je Seite. Unternehmen mit Kennzahlen stehen zuerst und öffnen das bisherige Profil.
* Jede Zeile hat eine Unternehmens-ID (seit 03.11.2026 für alle Tabellenzeilen vergeben, `unternehmen-tabelle/skripte/ids_vergeben.py`, über `stammdaten/ids.py`). Zeilen ohne Kennzahlen öffnen unter `#firma-<ID>` ein Registerprofil: Stammdaten, Quelle, Hinweis „noch keine Kennzahlen“. Nur wenn eine Zeile noch keine ID hat, steht ersatzweise ein Hash aus ISIN, sonst LEI, sonst Land+Name im Link. Neue Tabellenzeilen: `ids_vergeben.py` erneut laufen lassen.
* Die Befehlszeile findet auch Registereinträge (Name, Ticker, ISIN). Die Länderauswahl oben schränkt das Verzeichnis ein.
* Korrelation (F6, `src/korrelation.js`): Die Paar-Auswertung steht in der Adresse (`#korr?a=vwl~bip_yoy~DE&b=…&f=Q&ta=yoy&lag=1&von=2010&m=spearman`), lässt sich also als Link teilen; Reihen eines anderen Landes erscheinen nur, wenn die Länderauswahl oben dieses Land oder „Alle Länder“ zeigt. Die Server-API rechnet dieselbe Auswertung für VWL-Reihen unter `/api/v1/analysis/correlation` (Test: `server/tests/test_analyse.py` vergleicht mit dem Browser-Code). Test der Adresse: `node app/tests/korrelation-url-smoke.js app/dist/bankterminal.html`.
* Die Länderauswahl oben steht standardmäßig auf Deutschland (alle Länder des Registers wählbar, „Alle Länder“ bleibt eine Option). F1 bis F3 enthalten alle Registerunternehmen des Landes als schlanke Einträge ohne Werte (kein Ticker, keine Mediane); Korrelation, Kursabruf und Karte arbeiten weiter nur mit den Unternehmen mit Kennzahlen bzw. bekanntem Sitz. Das Artifact-Paket (`artifact_packen.py`) komprimiert das Register mit (gepackt rund 9 bis 10 MB).

## Branchen, Unternehmen und Profilseiten

Das Terminal kennt keinen Unterschied mehr zwischen Banken und anderen Unternehmen: Banken sind eine Branche unter allen.
Aufbau von oben nach unten: **Branche** → **Untergruppe** (z. B. Sparkassen, Genossenschaftsbanken; für andere Branchen die Spalte
„Gruppe“) → **Notierung** (börsennotiert / nicht börsennotiert, als Filter) → **Unternehmen**.

* F1 Branchenvergleich: Kacheln, Mediantabelle je Branche, Streudiagramm aller Unternehmen.
* F2 Einzelbranche: eine Branche im Detail (früher beide Reiter „Branche“). Alle Unternehmen des Registers erscheinen, zuerst die mit Kennzahlen (200 Zeilen, „+ 500 weitere“). Filter für Branche, Untergruppe und Notierung; Tabelle, Rangfolge, Profil gegen die übrigen Branchen, Kurse, Kennzahlen gegeneinander.
  In der Branche Banken führt der Block „Spezialansichten Banken“ zu den bisherigen Ansichten GRP, QUOT, CMP, RANK, MKT und TS.
* F3 Vergleich: bis zu 6 Unternehmen aus beliebigen Branchen (Perzentile in der eigenen Branche, Abstand zum Branchenmedian, Kurse).
* F4 Verzeichnis: alle Unternehmen mit Suche und Filter.
* Profilseite je Unternehmen (`#firma-<id>`, auch über die Kommandozeile mit dem Namen): Kennzahlen mit Branchen- und Gruppenmedian,
  Zeitreihen, Kurse und alle Dokumente des Unternehmens aus dem Repo mit Download- und GitHub-Link, Quelle und Prüfsumme.

Nicht börsennotierte Unternehmen erscheinen mit Abschlusskennzahlen, ohne Kurs- und Bewertungswerte. Ob ein Unternehmen notiert ist,
steht in der Spalte „Börsennotiert“ der Branchentabelle bzw. in `zeitreihen/stammdaten.csv` (Spalte `notiert`); fehlt sie, gilt ein
Unternehmen mit Ticker oder ISIN als notiert. Die Unternehmens-ID kommt ausschließlich aus `stammdaten/` (`U000123`, siehe [stammdaten/README.md](../stammdaten/README.md)); der Build bricht ab, wenn ein Unternehmen dort fehlt oder eine ISIN bei mehreren IDs steht. Alte Lesezeichen `#firma-<alte-id>` werden umgeleitet. Neue Unternehmen kommen über `zeitreihen/stammdaten.csv` (Spalten `unternehmen_id`, `name`,
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

## Weltkugel (alternative Oberfläche)

`dist/weltkugel.html` ist dieselbe Seite wie das Terminal, mit einer Weltkugel als Startansicht (`#globus`). `build.py` baut sie mit;
für reine Änderungen an der Oberfläche reicht `python3 app/build.py --nur-seite` (bettet die vorhandenen `data/*.json` ein, auch im
teilweisen Checkout ohne Dokumentordner). Wie `bankterminal.html` wird die Datei nicht nach main committet, sondern vom Workflow
„Terminal bauen“ auf den Branch `terminal-dist` und als Workflow-Artifact abgelegt.

* **Darstellungsformen:** Reiter oben auf der Karte, je mit eigenem Reiter im Terminal (HDL, VWL, BÖR, UNT, POL; dazu KOR):
  * **Handel:** Stufe 1 die 15 größten Volkswirtschaften (oder Kontinente) mit ihren Strömen, Haupthandelsrouten aller Verkehrsträger
    mit Engstellen und Knoten, „!“ bei aktuellen Störungsmeldungen. Stufe 2 die fünf größten Export- (grün, durchgezogen) und
    Importpartner (rot, gestrichelt) der gewählten Länder (Shift+Klick wählt mehrere; Kacheln rechts und links), unter jedem Land
    Zollsatz und Handelssaldo, Strom zwischen Wirtschaftsräumen, Vorschauen echter Meldungen. Stufe 3 Handel mit allen Nachbarn und
    fünf weiteren größten Partnern, Strom je Nachbar.
  * **Volkswirtschaft:** Stufe 1 Wirtschaftsräume (`geo/wirtschaftsraeume.csv`) mit BIP-Wachstum und Inflation auf der Karte, übrige
    Werte rechts. Stufe 2 dieselben Werte je Land, Klick zeigt alles, Shift+Klick vergleicht. Stufe 3 Land im Detail (Volkswirtschaft,
    Handel, Strom, Unternehmen, Börse).
  * **Börse & Finanzen:** Stufe 1 Börsenplätze mit Leitindex seit Jahresbeginn (grün/rot), Wirtschaftsraum wählbar, Kacheln mit
    Indizes nach Region, Rohstoffen, Leitwährungen, Leitzinsen und Renditen. Stufe 2 je Land Leitindex und 10-jährige Rendite.
    Stufe 3 Finanzplatz: börsennotierte Unternehmen nach Kursentwicklung gefärbt, Indexmitglieder, Banken (Deutschland).
  * **Unternehmen:** Stufe 1 Kreis je Land nach Zahl oder Börsenwert, Branchenmix je Wirtschaftsraum. Stufe 2 Sitze mit Filtern
    (Branche, Index, börsennotiert, Kennzahlen); Shift+Klick nimmt Unternehmen in den Vergleich. Stufe 3 Netz, Profil, Nachbarländer.
  * **Politik & Wahlen:** Stufe 1 Länder nach Ausrichtung der Regierung, W = Wahl in den nächsten zwölf Monaten, N = gerade gewählt
    (letzte 30 Tage), Bündnisse wählbar. Stufe 2 Regierungschef, Partei und nächste Wahl je Land; Land anklicken zeigt jede
    Parlamentskammer (Einkammer, Unterhaus, Oberhaus) mit Sitzverteilung als Halbkreis, Regierungslager, Stimmenanteilen der letzten
    Wahl und Wahlterminen. Stufe 3 Gliedstaaten der 26 Bundesstaaten (USA, Kanada, Australien, Indien, Brasilien, Schweiz, Österreich,
    Deutschland …) mit Regierungschef und Parlament, dazu Handel und Unternehmen; in Deutschland zusätzlich Bundestagswahl je Land und
    Landtagsumfrage. Im Terminal Reiter POL (F1 Regierungen, F2 Wahlkalender, F3 Deutschland, F4 Parlamente, F5 Gliedstaaten) und BÖR F7.
  Daten: `welt_daten.py` (Weltbank, Eurostat-Strom, US-Zollbelastung, Wirtschaftsräume -> `data/welt.json`), `routen.py`
  (`data/routen.json`), `news_routen.py` (`data/news_routen.json`), `boerse_welt.py` (`data/boerse_welt.json`), `politik_daten.py`
  (`data/politik.json`, `geo/de_laender.geojson`), `parlamente_daten.py` (IPU Parline, Wikipedia, Wikidata -> `data/parlamente.json`,
  `geo/gliedstaaten.geojson`), `entsoe_abruf.py` (ENTSO-E, physikalische Stromflüsse je Grenze und Monat der letzten zwölf Monate
  -> `data/strom_entsoe.json`, Reiter HDL F4 Tafel STM; braucht den Schlüssel in der Umgebungsvariable `entsoe_api`, der nie ins Repo,
  in Logs oder Fehlermeldungen gelangt; dauert rund fünf Minuten); Abruf im Workflow „Weltkugel-Daten“. Was noch fehlt:
  `OFFENE_DATENFELDER.md`.
* **Politik & Wahlen, Ansicht „Wahlen“ (neu 06.11.2026, Konzept „Wahlergebnisse auf allen Ebenen“):** Die Karte zeigt immer genau eine
  Wahl je Gebiet. Links die Ebenenleiter E0 Supranational, E1 Staat, E2 Region, E3 Kommune, E4 Gemeinde (Namen je Land, in Deutschland
  Europa, Bund, Land, Kreis/Stadt, Gemeinde/Bezirk); die Ebene wechselt nur per Klick. Oben die Satzleiste („E1 · Bund · Bundestagswahl
  2025 · Zweitstimmen · je Wahlkreis · gefärbt nach stärkster Partei“), jedes Wort ist ein Auswahlfeld. Zoomen ändert nur die
  Auszählungseinheit derselben Wahl (Gesamt › Länder › Wahlkreise), mit Überblendung; das Feld „festgehalten“ hält sie fest. Rechts die
  Ergebniskarte, für jede Wahl und jede Einheit gleich gebaut: Ebene und Pfad, gewählte Person, Sitzverteilung, Stimmen mit Veränderung,
  Kennzahlen, sortierbare Liste der Einheiten, Sprung zur selben Stelle auf anderen Ebenen, Quelle. Durchgezogene Grenze = Wahlkreis
  (Mandat), gestrichelt = nur Zählgebiet, schraffiert = keine Daten auf dieser Ebene. Die Ansicht „Regierungen“ enthält alles Bisherige
  (Ausrichtung, Bündnisse, Regierungschefs, Gliedstaaten).
  Daten: `wahlen_daten.py` fasst parlamente.json, die Bundestagswahlkreise, die Europawahl 2024 nach Kreisen
  (`wahlen/quellen/ew24_kerg2.csv`, Bundeswahlleiterin), die Landtagswahl NRW 2022 je Landtagswahlkreis (`wahlen/quellen/nw_ltw22_*.csv`,
  Grenzen `geo/landtagswahlkreise_nw.geojson`, Landeswahlleiterin NRW), die Unterhauswahl 2024 (UK Parliament, `geo/wahlkreise_gb.geojson`), die
  Wahl zur Assemblée nationale 2024 (Innenministerium, `geo/wahlkreise_fr.geojson`), die Unterhauswahl Kanada 2025 (Elections Canada,
  `geo/wahlkreise_ca.geojson`), die Wahl zum Repräsentantenhaus Australien 2025 (AEC, Erstpräferenzen und Ergebnis nach Präferenzen; Grenzen
  ABS, `geo/wahlkreise_au.geojson`), die Nationalratswahl Schweiz 2023 je Kanton (BFS, `wahlen/quellen/ch_nrw23_*.json`), die Nationalratswahl
  Österreich 2024 je Bundesland und Gemeinde (BMI, `wahlen/quellen/at_nrw*.csv`; Gemeindegrenzen Statistik Austria, `geo/gemeinden_at.geojson`)
  das Repräsentantenhaus USA 2024 je Kongresswahlkreis (Statistik des Clerk of the House, PDF; Grenzen Census CD119), den Congreso Spanien 2023
  je Provinz (Junta Electoral Central im BOE, PDF), das Storting Norwegen 2025 je Wahlkreis (Valgdirektoratet; Grenzen Spanien und Norwegen aus
  Natural Earth), die Gemeinden der Schweiz (BFS; Grenzen swisstopo swissBOUNDARIES3D)
  und kommunal.json in einem einheitlichen Format zusammen (`data/wahlen.json`; Kreisgrenzen `geo/kreise_de.geojson` aus BKG VG1000,
  dl-de/by-2-0). Neue Wahldaten nur als Leser in dieser Datei.
  Grenzen nachladen: die Wahlkreisgrenzen aus `WAHL_GEO` in `globus.py` stecken nicht in der Seite, sondern liegen als `dist/wahlgeo/<art>.json`
  daneben (`build.py` schreibt sie) und werden erst geladen, wenn eine Wahl sie braucht; so bleibt die Vorschau unter 16 MB. Beim Artifact
  die Dateien `wahlgeo/*.json` mitveröffentlichen. Einheiten mit 800 und mehr Werten (Gemeinden AT, CH) stehen ebenfalls nicht in der Seite:
  `globus.wahlen_aufteilen()` lagert ihre Werte nach `wahlgeo/werte-<wahl>-<einheit>.json` aus (Feld `nach`), `wahlen.js` lädt sie mit der Wahl; der Test liefert die Seite über einen kleinen HTTP-Server aus (fetch geht nicht über file://).
  Test: `tests/wahlen-smoke.js`.
* **Länder:** anklicken oder suchen; das Land wird markiert, rechts stehen die Kerndaten (BIP, Inflation, Kerninflation, Arbeitslosenquote,
  Staatsschulden, Finanzierungssaldo, Leistungsbilanz, Zinsen, BIP je Einwohner, OECD-Frühindikator) mit Verlauf, die OECD-Projektion,
  die Unternehmen des Landes und die Börsenindizes aus dem Bereich BÖR. Quelle wie im VWL-Bereich: Eurostat, wo vorhanden, sonst OECD.
  Länder ohne VWL-Reihen zeigen nur Grundangaben aus Natural Earth.
* **Unternehmen:** erscheinen beim Hineinzoomen am Sitz, als Gruppen (Zahl = Unternehmen), die beim Zoomen zerfallen. Gruppen in einer
  Stadt zerfallen nicht weiter; ein Klick zeigt dann die Liste. Gelb = börsennotiert, blau = nicht notiert.
* **Fenster:** ein Klick auf ein Unternehmen öffnet dessen Profil (dieselbe Ansicht wie `#firma-<id>`) als verschiebbares Fenster;
  mehrere Fenster gleichzeitig, „Nebeneinander“ ordnet sie an, „+ Vergleich“ sammelt bis zu sechs Unternehmen für das Vergleichsfenster
  (dieselbe Ansicht wie F3 Vergleich). Links auf andere Ansichten führen ins klassische Terminal, „◉ Weltkugel“ zurück.
* **Grundkarte:** OpenStreetMap-Daten als Vektorkacheln über [OpenFreeMap](https://openfreemap.org) (kostenlos, ohne Schlüssel und
  Anmeldung; Namensnennung OpenFreeMap, OpenMapTiles, OpenStreetMap ist eingeblendet). Ohne Netz oder wenn der Kachelserver nicht
  erreichbar ist, schaltet die Seite auf eine eingebettete einfache Karte aus Natural Earth um. Umschalter unter „Ebenen“.
* **Ebenen:** Jede Darstellung ist eine Ebene in `EBENEN` (`src/globus.js`). Handelsströme und Lieferketten sind als Ebenen vorgesehen
  (noch ohne Daten; erwartetes Format im Kommentar über den beiden Einträgen). Neue Ebenen: `GLOBUS.ebene({ id, name, gruppe, quellen(map),
  schichten(map, vor), klick? })`; sie werden nach jedem Wechsel der Grundkarte neu angelegt.

| Datei | Aufgabe |
|---|---|
| `globus.py` | baut `dist/weltkugel.html` aus der Terminal-Seite, Karte, Ländern, Sitzen und Schriften |
| `src/globus.js`, `src/globus.css` | Oberfläche der Weltkugel |
| `vendor/maplibre-gl/` | MapLibre GL JS 5.24.0 (BSD-3-Clause, `LICENSE.txt`), eingebettet, damit die Seite ohne CDN läuft |
| `geo/laender.geojson` | Ländergrenzen Natural Earth 1:50 Mio. (gemeinfrei), erzeugt mit `geo/laender_bauen.py` |
| `geo/glyphs/` | Schrift Noto Sans (SIL OFL) für Kartenbeschriftungen, Zeichen 0–255 |
| `../stammdaten/geo/sitz_geo.csv` | Sitz je Unternehmens-ID mit Koordinate, erzeugt mit `stammdaten/geo/sitz_geo.py` (siehe dort) |
| `artifact_packen.py` | packt eine `dist/*.fragment.html` für die Artifact-Vorschau unter 16 MB (gzip im Browser entpackt) |

Firmensitze: Ort aus `stammdaten/unternehmen_ids.csv`, sonst aus der GLEIF-LEI-Datenbank (über LEI, ISIN oder, als unsicher markiert,
über den exakten Namen im Land), Koordinate aus GeoNames (Orte ab 500 Einwohnern, sonst Postleitzahl). Stand 03.11.2026: 1.230 von 1.409
Unternehmen mit Koordinate (im Terminal 1.099 von 1.274). Falsche Treffer in `sitz_geo.csv` von Hand korrigieren und `quelle_ort` auf
`manuell` setzen; solche Zeilen überschreibt das Skript nicht. Neu abrufen: `python3 stammdaten/geo/sitz_geo.py` (GLEIF-Antworten
liegen in `gleif_cache.json`, `--offline` nutzt nur diesen Zwischenspeicher).

## Täglicher Abruf

`.github/workflows/marktdaten.yml` läuft an Handelstagen um 18:30 UTC (nach Xetra-Schluss) und holt die Kurse (`app/data/markt.json`, samstags die Wochenkurse); nur bei Änderungen committet er nach main und stößt `terminal.yml` an, das das Terminal baut und als Artifact sowie auf den Branch `terminal-dist` legt (nicht mehr nach main). Aufbau, Takt und Minutenschätzung: `.github/workflows/README.md`. Manuell startbar unter Actions → „Börsendaten Terminal“ → Run workflow. Yahoo Finance hat keine offizielle API; fällt ein Ticker aus, steht er unter `fehler` in `markt.json`, die übrigen werden trotzdem geschrieben.

Die Kommandozeile oben nimmt `GRP`, `QUOT`, `CMP`, `RANK` oder einen Banknamen (übernimmt die Bank in CMP). Klick auf einen Punkt in QUOT oder eine Zeile in RANK übernimmt die Bank ebenfalls.

Gruppenwerte ohne Zusatzeinträge (DZ BANK, DekaBank, DKB). KM1-Werte stammen teils von Gruppen- oder Konzernebene; die RWA-Dichte gegen die HGB-Bilanzsumme ist dort nur ein Richtwert.

## Startseite und Bereiche
Das Terminal öffnet mit einer Startseite (`#start`) und zwei Kacheln. **Unternehmen** führt in das Branchen-Terminal (F1 Branchenvergleich, F2 Einzelbranche, F3 Vergleich, F4 Verzeichnis, Profilseiten `#firma-<id>` mit Kennzahlen, Gremien, Vergütung und Dokumenten). **Volkswirtschaft** führt in das makroökonomische Terminal (F1 Überblick, F2 Zeitreihen, F3 Länder, F4 Berichte & Quellen). Die Daten dafür liegen in `volkswirtschaft/` und werden von `vwl.py` eingelesen; `build.py` bettet sie ein.

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

## Bereich BÖR (Börsendaten, vierte Kachel der Startseite)

Eigener Bereich mit F1 Überblick (Leitindizes, Länderkacheln nach Veränderung seit Jahresbeginn, Gewinner und Verlierer), F2 Indizes (Welt, OECD, Nicht-OECD; Filter nach Gruppe und Region), F3 Unternehmen (große Unternehmen weltweit nach Börsenwert; Filter Land, Sektor, Suche), F4 Verlauf (bis zu zehn Auswahlen aus Indizes und Unternehmen, auf 100 indexiert, Fenster 1 bis 10 Jahre, logarithmisch wählbar) und F5 Quellen.
Kommandozeile im Bereich: Name eines Index oder Unternehmens übernimmt ihn in den Verlauf.
Frei verfügbar über Yahoo Finance sind 80 Indizes (15 davon nur als ETF-Stellvertreter, im Namen gekennzeichnet) und 232 Unternehmen aus 29 Ländern. Nicht frei verfügbar sind u. a. WIG20, PX, BUX, Colcap, EGX 30, MOEX, Tadawul-Index und kleinere Börsen Afrikas, Südasiens und Osteuropas. Unternehmen aus `stammdaten/` (Ticker-Treffer) verlinken auf die Profilseite; neue IDs vergibt der Abruf nie.
