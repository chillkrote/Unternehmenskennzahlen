# Projektreview Unternehmenskennzahlen (Stand 27.10.2026)

Prüfung des gesamten Repos auf Stand `main` @ `d738978` (nach PR #27): Daten, Skripte, Terminal (`app/`), Desktop-App (`desktop/`), Workflows, Excel-Dateien, Governance, Termine, Volkswirtschaft und Zeitreihen. Es wurde nichts am Produktivstand geändert außer den unter „Direkt behoben“ genannten Kleinstfehlern.

Schweregrade: **Hoch** = falsche Zahlen im Terminal oder ein Ablauf, der absehbar bricht. **Mittel** = Inkonsistenz oder Risiko, das Auswertungen verfälschen kann. **Niedrig** = Pflege, Lesbarkeit, Komfort.

## Kurzfassung

1. **Die Datenbasis ist solide.** Alle 821 PDFs sind gültige PDFs, alle 15 `index.csv` verweisen auf vorhandene Dateien, jede SHA-256-Prüfsumme stimmt, und die Bankenauswertung lässt sich aus den Rohdaten-JSONs zellgenau neu erzeugen. 21 Stichproben gegen die Originaldokumente (14 Banken GJ 2025, 7 Zeitreihenwerte 2017 bis 2022) waren alle korrekt.
2. **Das größte strukturelle Problem sind die Unternehmens-IDs.** Es gibt mindestens 12 eigene `slug()`-Funktionen mit zwei unverträglichen Schemata (Umlaut als `ae` bzw. Umlaut weggelassen, teils auf 60 Zeichen gekürzt). Das Terminal rettet sich mit Heuristiken; dabei entstehen Dubletten (Deutsche Bank, Baader Bank je zweimal) und tote Querverweise.
3. **Ein Fehler im Terminal zeigt falsche KGV.** Die Spalte „KGV (12M, Yahoo)“ überschrieb „KGV (GJ)“; bei 53 Unternehmen weicht der angezeigte Wert um mehr als 50 % vom GJ-Wert ab (Hapag-Lloyd 384 statt 25). In diesem PR behoben.
4. **Die Workflows sind ungetestet und teuer.** `marktdaten.yml` und `termine.yml` sind noch nie gelaufen, checken das ganze 3-GB-Repo aus und committen täglich bis zu dreimal ein 8,6-MB-Terminal doppelt. Im privaten Repo zählt das gegen die freien Actions-Minuten; ist das Kontingent aufgebraucht, bleiben die Abläufe einfach stehen.
5. **Der veröffentlichte Terminal-Stand ist veraltet.** `app/dist` und `app/data/unternehmen.json` passen nicht zum Repo: Ein Neubau ergänzt Dokumente bei 277 und Termine bei 199 Unternehmen.

## Befunde

### Hoch

| # | Befund | Fundstelle | Empfehlung |
|---|---|---|---|
| H1 | **KGV im Terminal falsch (behoben).** Zwei Excel-Spalten haben den Alias `kgv`; die spätere („KGV (12M, Yahoo)“, Yahoo `trailingPE`) überschrieb den GJ-Wert. Betroffen sind 53 von rund 300 Unternehmen mit mehr als 50 % Abweichung, z. B. Hapag-Lloyd 384 statt 25, Porsche SE 79 statt 6, Camerit 667 statt 3.433. | `app/unternehmen.py:114`, Spalten in `boersennotierte-unternehmen/skripte/build.py:307-308` | Behoben: Die erste Spalte gilt, die zweite erscheint als eigene Kennzahl „KGV (12M, Yahoo)“. Das Terminal muss danach neu gebaut werden (macht der nächste Workflow-Lauf). |
| H2 | **Unternehmens-IDs uneinheitlich.** `universum/skripte/unternehmen.py:40` schreibt `ä→ae`, `&→und` und kürzt auf 60 Zeichen. `app/unternehmen.py:46`, `app/datenschicht.py:91`, `termine/skripte/tlib.py:27` und `zeitreihen` lassen Umlaute weg. Ergebnis: 62 von 543 Universum-IDs existieren im Terminal nicht als ID (z. B. `duerr-aktiengesellschaft` vs. `durr-aktiengesellschaft`), Dokumentordner derselben Bank liegen unter zwei Namen (`banken/.../sparkasse-osnabrueck/` und `zeitreihen/dokumente/sparkasse-osnabruck/`). Das Terminal gleicht das über `_finder` (`app/unternehmen.py:259`) heuristisch aus. | siehe links; Liste aller `slug`-Definitionen: governance/skripte/lib.py, app/unternehmen.py, app/datenschicht.py, universum/skripte/unternehmen.py, termine/skripte/tlib.py, 4× zeitreihen/skripte, 3× banken/.../erhebung | Eine zentrale Stammdatentabelle `stammdaten/unternehmen.csv` mit fester `unternehmen_id` (einmal vergeben, nie neu berechnet), ISIN, LEI, Ticker, Branche, Namensvarianten. Ein gemeinsames Modul `lib/ids.py`, das alle Skripte importieren. Branchen-Excel bekommen eine Spalte „ID“ (wird von `unternehmen.py` schon erkannt). |
| H3 | **Dubletten im Terminal.** Deutsche Bank (`deutsche-bank-ag` aus dem Bilanzvergleich, `deutsche-bank-aktiengesellschaft` aus der Börsenmappe) und Baader Bank erscheinen je zweimal in der Branche Banken, weil die Zusammenführung nur über den Namens-Slug läuft und Bankeinträge keine ISIN tragen. Commerzbank wird zufällig richtig zusammengeführt. | `app/unternehmen.py:356` (Abgleich `ids.get(f["id"])`) | Zusammenführung über ISIN/LEI aus H2; kurzfristig `boersen_ticker.json` um die ISIN ergänzen und darüber abgleichen. |
| H4 | **Workflows noch nie gelaufen, Checkout des ganzen Repos.** Laut Actions-Verlauf gab es nur zwei Läufe (Desktop-Build). `marktdaten.yml:17` und `termine.yml:26` checken alle 3 GB aus, zusammen rund 80 Läufe im Monat. Dazu zählen macOS-Minuten zehnfach (`desktop-macos.yml` läuft bei jedem PR mit Änderungen unter `desktop/`). Das private Repo hat ein festes Freikontingent; danach stoppen die Abläufe. | `.github/workflows/*.yml` | Einmal von Hand starten und Laufzeit messen. Checkout mit `filter: blob:none` und `sparse-checkout` (nur `app`, `termine`, `zeitreihen`, `governance`, `volkswirtschaft`, `boersennotierte-unternehmen/*/auswertung`, `banken/*/auswertung`, `index.csv`-Dateien). `unternehmen.py` müsste dann Dateigrößen über `git ls-tree -l` statt vom Datenträger lesen (`_groesse`, `app/unternehmen.py`). |
| H5 | **Terminal-Stand veraltet.** Ein Neubau aus `main` ändert `app/data/unternehmen.json` bei 277 Unternehmen (Dokumente), 199 (Termine), 68 (Werte), 9 (Governance). Das Artifact und die Desktop-App zeigen also weniger als im Repo liegt. | `app/dist/`, `app/data/unternehmen.json` | Nach dem Merge einmal `Börsendaten Terminal` von Hand starten. Langfristig siehe M1. |

### Mittel

| # | Befund | Fundstelle | Empfehlung |
|---|---|---|---|
| M1 | **Build-Ergebnis im Git.** `app/dist/bankterminal.html` und `.fragment.html` (je 8,6 MB, gezippt je 2 MB) werden von zwei Workflows bis zu dreimal täglich neu committet, dazu `markt.json` (1,4 MB). Git komprimiert Versionen gegeneinander, Klone und Actions-Checkouts wachsen trotzdem stetig. | `marktdaten.yml:26`, `termine.yml:41` | `dist/` aus Git nehmen und als Asset eines festen Releases (`terminal-latest`) hochladen; die Desktop-App lädt von dort (`desktop/main.js` `DATEI_IM_REPO`). Mindestens die Fragment-Fassung nicht committen, sie entsteht beim Veröffentlichen. |
| M2 | **Zwei Workflows schreiben ohne gemeinsame Sperre nach `main`.** `marktdaten.yml` macht vor `git push` kein `pull --rebase` und nutzt eine andere `concurrency`-Gruppe als `termine.yml`. Jeder Merge zwischen Checkout und Push lässt den Lauf scheitern. Außerdem committet `marktdaten.yml` `app/data/unternehmen.json` und `banken.json` nicht, obwohl `build.py` sie neu schreibt. | `marktdaten.yml:23-33`, `termine.yml:20-22` | Gleiche `concurrency: group: main-schreiben` in beiden, `git pull --rebase` vor dem Push, `git add app/data app/dist`. |
| M3 | **Übersicht und Bilanzblatt widersprechen sich bei sechs Sparkassen.** Die Übersicht nutzt DSGV-Rangliste oder Zeitungsmeldung, das Blatt „Bilanzen 31.12.2025“ die HGB-Bilanz aus EBA-CC2: Schwaben-Bodensee 12.304 vs. 11.944 Mio. € (−360), Esslingen-Nürtingen 13.228 vs. 13.108, Mainfranken 11.201 vs. 11.112, Ludwigsburg 13.300 (gerundet) vs. 13.331, KSK München 13.462 vs. 13.470, Wuppertal 8.295 vs. 8.312. Rang, EK-Quote und Gruppenauswertung rechnen mit dem ungenaueren Wert. Der README nennt nur Wuppertal und Hanseatic. | Excel, Blätter Übersicht und Bilanzen; Logik in `banken/.../rohdaten/skripte/build.py` | In `build.py` die Bilanzsumme aus der formalen Bilanz bevorzugen, wenn vorhanden (wie `_force` bei der Nacherhebung). Quellenart bei KSK München korrigieren: dort steht „Offenlegungsbericht“, Quelle ist die DSGV-Rangliste. |
| M4 | **Bilanzen gehen nicht auf.** LBS NordWest: Aktiva 21.482,3, Passiva 21.463,3 (−19 Mio., Bilanzgewinn fehlt in CC2). LBS NordOst: −5 Mio. Volksbank Stuttgart: +0,5 Mio. Rundungsdifferenzen von 1 Mio. bei Großbanken sind unkritisch. | Blatt Bilanzen 31.12.2025, Spalte „Prüfung: Aktiva − Passiva“ | Fehlenden Bilanzgewinn als eigenen Posten ergänzen bzw. Differenz als „nicht zugeordnet“ ausweisen, damit die Prüfspalte 0 zeigt. |
| M5 | **Bankenauswertung im Repo nicht ausführbar (behoben).** `rohdaten/skripte/build.py` sucht die JSONs im eigenen Ordner, im Repo liegen sie eine Ebene höher; Aufruf brach mit `TypeError` ab. Ausgabe ging fest nach `/mnt/project-files/...`. | `banken/.../rohdaten/skripte/build.py:11` | Behoben: erkennt das Repo-Layout und schreibt dann nach `auswertung/`. Geprüft: Neubau im Repo ergibt 0 abweichende Zellen. |
| M6 | **„Bestätigt“ im Yahoo-Abgleich bedeutet nicht „GJ 2025 bestätigt“.** Ein Treffer gegen irgendeines der letzten vier Jahre zählt. 163 der rund 1.000 Bestätigungen betreffen ein älteres Jahr (EBIT: 68 von 129). Beispiel 1&1: EBIT 2025 laut Bericht 208,2, laut Yahoo 223,6, trotzdem „bestätigt“. | `boersennotierte-unternehmen/skripte/berichte_abgleich.py:145-150` | Nur das letzte GJ als „bestätigt“ werten, ältere Treffer als „Vorjahr gefunden“ ausweisen. |
| M7 | **Yahoo-Felder mit offensichtlichen Fehlern im Terminal.** Ausschüttungsquote (Yahoo) DMG Mori 11.359 %, Hapag-Lloyd 882 %; Dividendenrendite SMAG 250 % (60 € Dividende bei 24 € Kurs); EBIT-Marge Eisen- und Hüttenwerke 65.383 % (Holding mit 0,14 Mio. Umsatz). | `boersennotierte-unternehmen/skripte/build.py:315`, Terminal | Plausibilitätsgrenzen in `build.py` (z. B. Quoten außerhalb −100 % bis +300 % leeren und markieren); Margen bei Umsatz unter 1 Mio. € nicht berechnen. |
| M8 | **Branchen-Taxonomie doppelt.** Die Ordner haben 14 Branchen (u. a. `software-it`, `technologie`, `chemie-rohstoffe`, `pharma-gesundheit`), das Terminal 12 (`technologie`, `chemie-pharma`, `auto`, `konsum`, `logistik`), Zuordnung über Aliase im Katalog. Branchenmediane im Terminal mischen dadurch z. B. Software mit Halbleitern. | `app/unternehmen_katalog.json:41-50`, `boersennotierte-unternehmen/README.md` | Eine Taxonomie festlegen (Ordner = Terminal-Branche) oder Ordnerbranche als Untergruppe ins Terminal übernehmen. |
| M9 | **Governance-Querverweise tot.** `mandate_extern.csv` verweist auf `muenchener-rueckversicherungs-gesellschaft-aktiengesellschaf` und `henkel-ag-und-co-kgaa`; das Terminal kennt diese IDs nicht. `person_id` verliert Sonderzeichen (`bjrn-gulden` für Bjørn Gulden) und hängt nur am Namen. | `governance/skripte/lib.py:4,10` | Mit H2 lösen; `person_id` einmal vergeben und in `personen.csv` festschreiben statt bei jedem Lauf neu zu berechnen. |
| M10 | **Einmal-Skripte mit festen Sitzungspfaden.** 12 Skripte unter `banken/.../erhebung/` lesen aus `/mnt/project-files/...`, `/tmp/claude-0/<sitzung>/` oder `/home/user/...`. `zeitreihen/skripte/migriere_banken.py:90` überschreibt `zeitreihe_lang.csv` komplett und würde spätere Ergänzungen (z. B. die 90 „verankerten“ Altwerte) löschen. | z. B. `erhebung/organize.py:2-3`, `erhebung/add.py:3-5`, `migriere_banken.py:90` | In `erhebung/` und bei `migriere_banken.py` eine Kopfzeile „Archiv, einmalig ausgeführt, nicht erneut starten“ ergänzen; Skripte, die weiter laufen sollen, auf Repo-relative Pfade umstellen. |
| M11 | **Zwei Ablagen der Bankenauswertung.** `/mnt/project-files/bilanzvergleich/` (Projektdateien) und `banken/bilanzvergleich-gj2025/` (Repo) enthalten dieselbe Excel und dieselben JSONs; `summary.json` weicht bereits ab. | Projektdateien, Repo | Repo als einzige Quelle festlegen; Projektdateien nur noch als Kopie zum Herunterladen. |
| M12 | **Desktop-App mit Electron 33.2.1.** Diese Hauptversion bekommt keine Sicherheitsupdates mehr; die App lädt HTML aus dem Netz nach. | `desktop/package.json:20` | Auf eine aktuelle Electron-Version heben (Build läuft ohnehin in Actions). |

### Niedrig

| # | Befund | Fundstelle | Empfehlung |
|---|---|---|---|
| N1 | Auswertungszeile `cet1-quote-median` stand als Unternehmen in den Stammdaten (behoben, Ursache im Migrationsskript ebenfalls). | `zeitreihen/stammdaten.csv`, `zeitreihen/skripte/migriere_banken.py:51` | Behoben. |
| N2 | Root-README war veraltet: nannte nur zwei Erhebungen und empfahl noch Git LFS ab 50 MB, entgegen der Entscheidung vom 27.10.2026 (behoben). `governance/README.md:30` und Stand-Angabe „Pilot mit drei Banken“ sind ebenfalls überholt (jetzt 8 DAX-Werte). | `README.md`, `governance/README.md` | Root behoben; Governance-README beim nächsten Ausbau nachziehen. |
| N3 | `pruefstatus` „verankert“ (90 Zeilen) ist im Zeitreihen-README nicht dokumentiert; 4.687 von 4.802 Werten sind nur „geparst“. | `zeitreihen/README.md:27` | Status ergänzen; Stichprobenprüfung (wie in diesem Review) als Skript, das `plausibilisiert` setzt. |
| N4 | Prozent-Heuristik: Spalten mit „%“ werden nur bei Beträgen über 1,5 durch 100 geteilt. Eine Spalte, die Prozentpunkte unter 1,5 enthält, würde als 100-fach gelesen. | `app/unternehmen.py:138` | Einheit je Spalte festlegen (Excel-Kopf „in %“ oder Katalog), nicht am Wert raten. |
| N5 | Identische PDFs mehrfach abgelegt: sechs Geschäftsberichte in `governance/dokumente/` und `boersennotierte-unternehmen/*/dokumente/` (zusammen 85 MB im Checkout), DekaBank-Abschluss dreifach, DKB, Kreissparkasse Köln, KölnBonn, SaarLB je doppelt, apoBank-Altberichte in `banken/` und `zeitreihen/`. Git speichert gleiche Inhalte nur einmal, der Checkout aber mehrfach. | siehe links | Governance auf die Dokumente der Börsenerhebung verweisen lassen (Pfad in `quelle_dokument`) statt zu kopieren. |
| N6 | Alle Crawler senden einen Chrome-User-Agent und prüfen `robots.txt` nicht. Das ist kein Umgehen von Bot-Schutz, wirkt bei automatischen Abrufen aus Actions aber wie Tarnung. | 7 Skripte, z. B. `termine/skripte/finanzkalender_scan.py:25` | Ein ehrlicher User-Agent mit Projektname und `robots.txt`-Prüfung im täglichen Abruf. |
| N7 | `berichte_abrufen.py` lädt jede Datei vollständig in den Speicher, bevor die 95-MB-Grenze greift. | `termine/skripte/berichte_abrufen.py:162-169` | `stream=True` und `Content-Length` vorab prüfen. |
| N8 | Abhängigkeiten nur nach unten begrenzt (`yfinance>=0.2.40`); ein yfinance-Update kann den täglichen Lauf brechen. Actions nicht auf Commit-SHA gepinnt. | `app/requirements.txt`, `termine/requirements.txt` | Versionen pinnen (`==`), Update bewusst per PR. |
| N9 | Terminal kennt nur vier Bankengruppen; „Förder- und Sonderinstitute“ (KfW IPEX, KfW Beteiligungsholding) erscheinen in den Bankenansichten ohne Farbe und Gruppe. Kein JS-Fehler (Smoke-Test über 24 Ansichten ohne Fehler). | `app/src/terminal.html:260` | Fünfte Gruppe ergänzen. |
| N10 | `termine/` liest `app/data/banken.json`, `app/` liest `termine/termine.csv`: gegenseitige Abhängigkeit über ein Build-Ergebnis. | `termine/skripte/tlib.py:18` | Termine aus `zeitreihen/stammdaten.csv` bzw. der zentralen Stammdatentabelle speisen. |
| N11 | Links im Terminal werden mit `esc()` maskiert, aber nicht auf `https:` geprüft. Quellen-URLs aus Crawlern könnten `javascript:` enthalten. Risiko gering, da nur eigene Daten. | `app/src/unternehmen.js:452,546`, `app/src/vwl.js:235` | In `esc`-Aufrufen für `href` nur `http(s):` zulassen. |
| N12 | Doppelte Zeile in `.gitignore` (behoben). `app/README.md` nannte den Workflow „Börsendaten Bank-Terminal“ (behoben). | | Behoben. |

## Was geprüft wurde und in Ordnung ist

- **Dokumente:** 821 PDFs, alle mit gültigem PDF-Kopf und von `pdfinfo` lesbar; keine HTML-Fehlerseiten unter `.pdf`. Größte Datei 55,6 MB (AMG), keine über 100 MB.
- **Index-Dateien:** 15 `index.csv` mit zusammen 869 Einträgen, keine fehlende Datei, keine Datei ohne Eintrag, alle SHA-256 stimmen.
- **Reproduzierbarkeit:** `rohdaten/skripte/build.py` erzeugt die Bankenexcel zellgenau (0 Abweichungen in 11 Blättern). `governance/skripte/build.py` erzeugt die Governance-CSVs unverändert. `app/build.py` läuft in 5 Sekunden durch.
- **Stichproben gegen Quelldokumente (21, alle korrekt):** Bilanzsumme, Eigenkapital und Fonds § 340g für Donner & Reuschel, ING-DiBa (223.151 / 4.077 / 2.890), Sparkasse Paderborn-Detmold-Höxter, Gestalterbank, Frankfurter Volksbank (19.331.861 T€, Fonds 1.341,9 Mio.), apoBank, Isbank, Berenberg, DKB, VR TeilhaberBank, Bank11, Stadtsparkasse Düsseldorf, Stadtsparkasse München; Eigenkapital jeweils inkl. Bilanzgewinn, wie in der Methodik beschrieben. Zeitreihe: Sparkasse Essen 2022, Sparkasse Osnabrück 2017 und 2021, apoBank 2019 und 2022, Volksbank Darmstadt-Mainz 2022, Volksbank BraWo 2020.
- **Plausibilität Banken:** keine doppelten Banken, Ränge je Gruppe absteigend, EK-Quote und Fonds-Quote rechnerisch konsistent. Große Bilanzsprünge (Raisin +87 %, C24 +78 %, Pax-Bank +82 % nach Fusion) sind erklärbar.
- **VWL:** 209.954 Werte, jede Reihe im Katalog, keine Dubletten.
- **Zeitreihen:** keine doppelten Schlüssel, alle IDs im Terminal bekannt.
- **Sicherheit:** keine Zugangsdaten im Repo. Desktop-App mit `contextIsolation` und `sandbox`, Token im Schlüsselbund (`safeStorage`), externe Links nur im Browser.
- **Terminal:** Smoke-Test mit Playwright über 24 Ansichten (Start, Bankenansichten, Branchen, Verzeichnis, Termine, VWL, Korrelation, Profilseiten) ohne JavaScript-Fehler.

## Verkomplizierte Strukturen

1. **Zwölf ID-Funktionen statt einer Stammdatentabelle** (H2). Daraus folgen `_finder` mit Umlaut-Heuristik und Präfixsuche, die Ticker-Brücke in `berichtstermine()`, die Name-Zusammenführung der Banken und die toten Governance-Links.
2. **Governance-Daten als Python-Code.** Jeder Wert steht als Funktionsaufruf in `governance/skripte/boerse_<firma>.py`; `build.py` führt sie aus und schreibt CSVs. Erfassung direkt in CSV (oder YAML je Unternehmen) mit einem Prüfskript wäre einfacher zu pflegen, zu prüfen und zu diffen.
3. **Bankenexcel aus 20 JSON-Schichten.** `build.py` (1.200 Zeilen) führt `private.json`, `private_11_40.json`, `gaps*.json` (7 Dateien, zwei davon `gaps_vb2.json` und `gaps_priv2.json` fehlen und werden still übergangen), `nacherhebung`, `websites` usw. mit Vorrangregeln (`_force`, `_full`, `key_of`-Sonderfälle) zusammen. Ergebnis stimmt, aber jede Korrektur braucht Wissen über die Reihenfolge. Empfehlung: einmal in eine Tabelle „ein Wert je Bank, Feld, Stichtag mit Quelle“ (wie `zeitreihe_lang.csv`) überführen; `build.py` liest dann nur noch diese.
4. **Drei Langformate mit unterschiedlichen Spalten** (`zeitreihen/zeitreihe_lang.csv`, `volkswirtschaft/zeitreihe_lang.csv`, `governance/kennzahlen_gremien.csv`), dazu Kennzahlen der Börsenunternehmen nur in Excel. Ein gemeinsames Schema `objekt_id, kennzahl, stichtag, wert, einheit, basis, quelle, seite, pruefstatus` würde Korrelation, Profilseiten und Excel-Exporte vereinfachen.
5. **Zwei Ablagen der Bankenerhebung** (M11) und **zwei Taxonomien** (M8).

## Bessere Verknüpfung

- **Zentrale Stammdaten** `stammdaten/unternehmen.csv`: `unternehmen_id`, Name, Namensvarianten, Rechtsform, ISIN(s), LEI, Yahoo-Ticker, Branche, Untergruppe, notiert, Sitz, Website, Mutter (`mutter_id`), Nachfolge. Die LEIs liegen schon vor (`gleif_sitz.json`, EBA-Hub-Exporte), die ISINs in `universum.csv`. Alle Erhebungen, Termine, Governance, Kurse und das Terminal hängen sich daran.
- **Konzern–Tochter:** HypoVereinsbank ↔ UniCredit, DKB ↔ BayernLB, norisbank ↔ Deutsche Bank stehen heute nur als Text bzw. in `boersen_ticker.json` (`Mutter`). Eine Spalte `mutter_id` macht daraus echte Verweise (Profilseite „gehört zu“, Konzernsicht).
- **Personen:** `person_id` als feste ID mit eigener Profilseite im Terminal (Mandate über alle Unternehmen, Vergütung über Jahre).
- **Dokumente:** ein gemeinsamer Dokumentkatalog (`dokumente.csv` mit `unternehmen_id`, Jahr, Art, Pfad, SHA-256) statt 15 `index.csv` mit zwei Spaltenschemata (`bank;...` vs. `unternehmen;unternehmen_id;...`). Dubletten (N5) fallen dann über die Prüfsumme auf.
- **VWL ↔ Unternehmen:** Branchenzuordnung zu VWL-Reihen (z. B. Bau ↔ Bauproduktion, Banken ↔ Euribor) als kleine Mappingtabelle, damit die Korrelationsansicht sinnvolle Paare vorschlagen kann.

## Ausbaumöglichkeiten

1. **Datenprüfung als Workflow** (kostenlos, schnell): ein Skript `pruefung/pruefe.py`, das die hier gemachten Checks bei jedem PR ausführt: Bilanz geht auf, Übersicht = Bilanz, IDs eindeutig und bekannt, `index.csv` vollständig, SHA-256, Plausibilitätsgrenzen. Läuft mit sparse Checkout in unter einer Minute.
2. **Einheitliche Ladeschicht** `lib/` (IDs, CSV lesen/schreiben, HTTP mit User-Agent und `robots.txt`, SHA-256, PDF-Text) statt Kopien in jedem Ordner.
3. **Historie der Börsenunternehmen:** die Excel hat bis zu fünf GJ, das Terminal nutzt nur das letzte. Die Mehrjahreswerte ins Langformat übernehmen; dann funktioniert die Korrelation auch für Nicht-Banken.
4. **VWL-Abruf als Workflow** (monatlich, Eurostat und OECD ohne Schlüssel), heute nur von Hand.
5. **Wochenkurse** (`kurse_historie.py`) in `marktdaten.yml` aufnehmen (wöchentlich).
6. **Release statt Commit** für Terminal und Desktop-App (M1), dazu ein `terminal-latest`-Release, das das Artifact und die App speisen.
7. **Excel-Exporte für alle Bereiche** aus dem Langformat (wie `zeitreihen/skripte/excel_export.py`), damit jede Excel aus derselben Quelle entsteht.

## Datenschutz und Lizenz

- **Personenprofile** (`governance/`): 266 Personen mit Mandaten, Werdegang und Einzelvergütung. Die Angaben sind Pflichtveröffentlichungen (§ 285 HGB, § 162 AktG, Organverzeichnis), und die README regelt sauber, dass nichts Privates erhoben und das Geschlecht nicht aus Vornamen geschlossen wird. Trotzdem ist es eine Sammlung personenbezogener Daten nach DSGVO. Empfehlung: im Governance-README Zweck, Rechtsgrundlage (berechtigtes Interesse, Art. 6 Abs. 1 lit. f) und eine Löschregel (z. B. Personen ohne Mandat seit mehr als 10 Jahren) festhalten; Personenprofile nicht in öffentlich geteilte Artifacts aufnehmen. Das Artifact des Terminals ist privat, solange es nicht geteilt wird; beim Teilen sind die Profile mit dabei.
- **Dokumente:** Geschäftsberichte sind urheberrechtlich geschützt; die Ablage im privaten Repo zur Nachvollziehbarkeit ist im README benannt. Das Repo sollte daher privat bleiben; ein öffentliches Daten-Repo (Idee aus dem Desktop-Thread, Update ohne Token) dürfte nur Kennzahlen und Links enthalten, keine PDFs.
- **Yahoo Finance:** Die Nutzungsbedingungen erlauben nur persönliche Nutzung. Für den privaten Gebrauch passt das; eine Weitergabe der Kurse (z. B. öffentliches Artifact) wäre davon nicht gedeckt.

## Direkt behoben in diesem PR

| Datei | Änderung |
|---|---|
| `app/unternehmen.py` | H1: Bei zwei Spalten mit demselben Alias gilt die erste; die zweite wird eigene Kennzahl mit vollem Spaltennamen. |
| `banken/bilanzvergleich-gj2025/rohdaten/skripte/build.py` | M5: erkennt das Repo-Layout (JSONs eine Ebene höher) und schreibt dann nach `auswertung/`; außerhalb des Repos unverändert. |
| `zeitreihen/stammdaten.csv`, `zeitreihen/skripte/migriere_banken.py` | N1: Medianzeile entfernt, Migrationsskript überspringt Median- und Kopfzeilen. |
| `README.md` | N2: alle Bereiche aufgeführt, LFS-Hinweis an die Entscheidung vom 27.10.2026 angepasst. |
| `app/README.md`, `.gitignore` | N12: Workflow-Name, doppelte Zeile. |

Build-Ergebnisse (`app/dist`, `app/data`, Excel) sind bewusst nicht neu committet; der nächste Lauf von „Börsendaten Terminal“ baut sie mit dem KGV-Fix neu.

## Vorgeschlagene Reihenfolge

1. Diesen PR mergen, dann „Börsendaten Terminal“ von Hand starten (H1, H5, H4 testen).
2. Workflows absichern: sparse Checkout, gemeinsame Sperre, `pull --rebase` (H4, M2).
3. Zentrale Stammdaten mit fester ID, ISIN, LEI (H2, H3, M9, N10).
4. Prüfskript als PR-Check (Ausbau 1), danach M3, M4, M6, M7 als Regeln darin.
5. `dist/` als Release statt Commit (M1), Electron aktualisieren (M12).
