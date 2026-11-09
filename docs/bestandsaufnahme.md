# Technische Bestandsaufnahme (Phase 0)

Stand 09.11.2026, Branch `claude/plattform-api-postgres`, Ausgangscommit `05dc3e0`. Grundlage ist der Code im Repo, nicht ältere
Projektnotizen. Größen wurden mit `python3 app/build.py --nur-seite` gemessen.

## Kurzfassung

* Die Website ist eine einzige generierte HTML-Datei je Oberfläche. **97 % der Weltkugel-Seite sind eingebettete JSON-Daten**
  (67,1 von 69,1 MB, gzip 12,0 MB; Terminal 51,5 MB, gzip 8,8 MB). Jeder Aufruf lädt alle Unternehmen, VWL-Reihen, Wahlen und Geometrien.
* Ein **PostgreSQL-Kernmodell existiert bereits** (`international/`, Schema `international`): Entitäten mit den Repo-IDs, Kennungen,
  Wertpapiere, Kennzahlen mit Quelle, Vintage (`reported_at`, `fact_as_of`), Importläufe mit Wasserzeichen, Unternehmensregister mit
  Aliasen und Prüfmarken. Es wurde bisher nur von Importskripten und Tests genutzt, nicht von der Website. Dieser Bestand ist die
  Grundlage des Backends; es wird nichts doppelt gebaut.
* Die Frontend-Module lesen ihre Daten über `JSON.parse(document.getElementById(…).textContent)` und haben teils schon einen
  Rückfall auf `fetch("../data/…json")`. Das macht eine schrittweise Umstellung je Datenblock möglich.
* Unternehmens-IDs sind zentral und sauber: 32.663 IDs in `stammdaten/unternehmen_ids.csv`, alle 32.581 Zeilen der
  Unternehmenstabelle tragen eine ID, `stammdaten/pruefe_ids.py` sichert „eine ISIN nur bei einer ID“ (0 Fehler).

## 1. Datenformate im Repo

| Bereich | Dateien | Format |
|---|---|---|
| Unternehmensregister | `unternehmen-tabelle/Unternehmen_Tabelle.csv` (32.581 Zeilen), `.xlsx`, Bereinigungsprotokolle | CSV (`;`), Excel |
| Stammdaten / IDs | `stammdaten/unternehmen_ids.csv`, `isin_zuordnung.csv`, `unternehmen_aliase.csv`, `geo/sitz_geo.csv`, `geo/tabelle_geo.csv`, `beziehungen/` | CSV, JSON |
| Kennzahlen deutscher Unternehmen | `zeitreihen/zeitreihe_lang.csv`, `stammdaten.csv`, Bankenexcel `banken/…/Bilanzvergleich_Banken_GJ2025.xlsx` | CSV, Excel |
| Branchen-Excel, Abschlüsse | `boersennotierte-unternehmen/`, `abschluesse-nichtbanken/`, `europa/`, `segmente/`, `esg/` | Excel, CSV, JSON |
| Internationale Abschlüsse | `international/*_pilot.csv`, Rohdaten der Adapter (SEC, ESEF, DART) | CSV, JSON, PostgreSQL |
| Volkswirtschaft | `volkswirtschaft/*.csv` (Prognosen, Ist-Werte, Indikatoren) | CSV |
| Handel, Börse, Politik, Wahlen | `app/data/*.json` (von den Abrufskripten erzeugt), `wahlen/quellen/`, `app/geo/*.geojson` | JSON, GeoJSON |
| Dokumente | rund 2,9 GB PDF/HTML unter `banken/`, `zeitreihen/dokumente/`, `historie…` mit `index.csv` (SHA-256) | PDF, HTML |

## 2. Bei jedem Build neu erzeugt

`app/build.py` erzeugt `data/banken.json`, `data/unternehmen.json` (22,5 MB) und `data/register.json` (10,5 MB) aus Excel/CSV
und bettet danach **alle** `app/data/*.json` sowie mehrere GeoJSON-Dateien in `src/terminal.html` ein; `globus.py` ergänzt Karte,
Firmensitze und Wahldaten. Die übrigen JSON-Dateien schreiben die Abrufskripte der Workflows (siehe Abschnitt 8).

## 3. Unmittelbar ins HTML eingebettet (Weltkugel-Seite, MB unkomprimiert)

| Script-Tag | MB | lesendes Modul | Quelle |
|---|---|---|---|
| `unternehmen` | 22,52 | `unternehmen.js`, `korrelation.js`, `globus.js` | `unternehmen.py` |
| `register` | 10,47 | `unternehmen.js` (Verzeichnis, Registerprofile, Befehlszeile, Branchen-Stubs) | `register.py` |
| `geo-tabelle` | 10,32 | `globus.js` (Unternehmenspunkte, Stammdatenfenster) | `globus.py` |
| `vwl` | 5,34 | `vwl.js`, `korrelation.js` | `vwl.py` |
| `wahlen-daten` | 3,06 | `wahlen.js` | `wahlen_daten.py` |
| `kurse` | 1,57 | Terminal, `korrelation.js` | `kurse_historie.py` |
| `geo-laender` | 1,53 | `globus.js` | Natural Earth |
| `markt` | 1,42 | Terminal (MKT) | `marktdaten.py` |
| `wahlkreise-bund`, `kommunen-geo`, `gliedstaaten-geo`, `kreise-de-geo`, `de-laender-geo` | 4,43 | `handel.js`, `wahlen.js`, `globus.js` | `geo/` |
| `parlamente-daten`, `kommunal-daten`, `politik-daten` | 2,60 | `handel.js` (POL), `globus.js` | `parlamente_daten.py`, `kommunal_daten.py`, `politik_daten.py` |
| `boerse`, `boerse-welt-daten`, `finanz-daten`, `finanz-makro-daten` | 1,60 | `boerse.js`, `finanz.js` | Abrufskripte BÖR |
| `daten` (Banken), `gueter-daten`, `welt-daten`, `handel-daten`, `routen-daten`, `verkehr-daten`, `news-daten`, `geo-netze`, `geo-sitze`, `geo-glyphen`, `geo-stufen`, `seiten-daten` | 2,30 | Terminal, `handel.js`, `globus.js`, `netz.js`, `seiten.js` | diverse |

Dazu MapLibre GL (rund 0,8 MB) und Schriften inline.

## 4. Bereits dynamisch nachgeladen

* Wahlkreisgrenzen einzelner Länder und Gemeindewerte ab 800 Einheiten: `dist/wahlgeo/*.json` (18 MB), `wahlen.js` lädt sie per `fetch` beim Öffnen.
* Live-Kurse: `finanz.js` lädt `live.json` vom Branch `daten-live` alle zwei Minuten (nur auf github.io).
* Kartenkacheln: OpenFreeMap (`tiles.openfreemap.org`, ohne Schlüssel), wahlweise „einfache“ Karte ohne Netz.
* Rückfall-`fetch` auf `../data/*.json` im Terminal, falls ein Script-Tag fehlt (nur lokal sinnvoll).

## 5. Module mit direkter Abhängigkeit von eingebetteten Script-Tags

`terminal.html` (daten, markt, kurse, unternehmen, register, vwl, boerse), `finanz.js` (finanz-daten, finanz-makro-daten,
boerse-welt-daten), `handel.js` (politik-, parlamente-, kommunal-, boerse-welt-daten), `wahlen.js` (wahlen-daten,
wa-geo-nachladen), `netz.js` (geo-netze), `globus.js` (geo-laender, geo-sitze, geo-tabelle, geo-glyphen, geo-stufen).
`vwl.js`, `boerse.js`, `korrelation.js` und `unternehmen.js` bekommen ihre Daten über `init(...)` aus dem Hauptskript.

## 6. Schnittstellen zwischen den Modulen

Globale Objekte (IIFE-Module): `UNT`, `VWL`, `BOE`, `FNZ`, `HDL`, `KOR`, `GLOBUS`, `WAHL`, `NETZ`. Das Hauptskript in
`terminal.html` hält das Routing (`location.hash`, `VIEWS`, `render()`, `gehe()`), ruft je Modul `init` und `nachRender` auf und
stellt Hilfsfunktionen (`panel`, `esc`, `fmt`, …) global bereit. Die Weltkugel hängt sich über `GLOBUS.ebene` und Ereignisse
(`globus:firma`) ein und nutzt `UNT.nachId`, `UNT.auswahl`. Neuer gemeinsamer Baustein: `src/api.js` (`API`).

## 7. Identifikatoren

* Unternehmen: `U000123` aus `stammdaten/` (nie aus ISIN/LEI abgeleitet), alte Slugs über `alt_ids` umgeleitet;
  Deep Link `#firma-<ID>`. Zeilen ohne ID bekamen früher einen Hash-Schlüssel (`register.schluessel`), heute haben alle eine ID.
* Länder: ISO-3166-Alpha-2 (`laender.geojson`, `ZZ` = unbekannt); die Unternehmenstabelle führt englische Landesnamen, die Zuordnung
  steht in `register.land_codes()` (wird jetzt auch vom Server-Import benutzt).
* Branchen: feste IDs (`banken`, `automobil`, …) aus `register.BRANCHEN`.
* Wahlen: `wahlen.json` mit Wahl-ID, Einheiten-ID und `geo`-Schlüssel; Handel: ISO-Ländercodes und BACI-Gütergruppen.

## 8. Zeitgesteuerte Abrufe (`.github/workflows/`)

`marktdaten.yml` (Kurse, Mo–Fr 18:37/22:43, Sa), `termine.yml` (täglich 05:17, Mo–Fr 16:47), `prognosen.yml` (Mo–Fr 06:43),
`live.yml` (alle 30 min), `weltkugel.yml` (täglich 06:17, Mo 04:23), `anreicherung.yml` (täglich 03:23); dazu
`terminal.yml` (Build und Pages), `international.yml` und `stammdaten.yml` (Tests), `europa.yml`, `desktop-macos.yml`.
Details: `.github/workflows/README.md`.

## 9. Vorhandene Tests

* Python `unittest`: `international/tests` (Kernmodell, Adapter, Unternehmenstabelle, gegen echtes PostgreSQL 16 in CI),
  `stammdaten/test_ids.py`, `europa/test_*.py`, `stammdaten/pruefe_ids.py` als Prüfung im Build.
* Playwright-Smoke-Tests unter `app/tests/` (Terminal, Länderauswahl, Weltkugel, Wahlen, Finanz, Netze, Seiten), in `terminal.yml`.
* Neu: `server/tests` (pytest, 44 Tests) und `app/tests/api-smoke.js` (API-Fassung im Browser).

## 10. Unverändert weiter betreibbar

Alle Abrufskripte und Workflows, die Datenhaltung in CSV/Excel als Arbeitsstand, das Kernmodell `international/` mit seinen
Importen, die Frontend-Module (Vanilla-JS, MapLibre), die GitHub-Pages-Fassung als Referenz und Rückfall.

## 11. Anzupassen oder zu ersetzen

* `build.py`/`globus.py`: Einbettung je Datenblock abschaltbar machen (begonnen mit `--api`, Register).
* `unternehmen.js`, `globus.js`, `vwl.js`, `wahlen.js`, `handel.js`: Datenzugriff über `API` statt Script-Tag, Bereich für Bereich.
* Zeitgesteuerte Workflows mit Commit nach main: auf dem Server durch systemd-Timer ersetzen, die direkt in die Datenbank importieren.
* Browser-Abruf `get.geojs.io` (IP-Geolokalisierung beim Start der Weltkugel, `globus.js`) und Live-Kurse von raw.githubusercontent.com:
  auf dem eigenen Server entbehrlich bzw. selbst ausliefern (Datenschutz, Drittanbieter).

## 12. Was bei der Migration kaputtgehen kann (Risiken)

| Risiko | Wo | Gegenmaßnahme |
|---|---|---|
| Branchenansichten F1–F3 zeigen ohne eingebettetes Register nur Unternehmen mit Kennzahlen | `UNT.initRegister` erzeugt Stubs | in der API-Fassung bekannt und dokumentiert (Funktionsmatrix); nächstes Paket: Branchenlisten serverseitig |
| Weltkugel-Länderauswahl und Unternehmenspunkte hängen an `register` bzw. `geo-tabelle` | `terminal.html`, `globus.js` | `geo-tabelle` bleibt vorerst eingebettet; Umstellung auf Kachel-/Viewport-Abfragen als eigenes Paket |
| Merkliste speichert IDs nur im Browser | `localStorage` | IDs bleiben gleich; API-Filter `ids=` |
| Deep Links `#firma-<alte-id>` | `alt_ids` | Profil mit Kennzahlen weiter aus eingebetteten Daten, Register über `/companies/{id}` |
| Unterschiedliche Bedeutung „mit Kennzahlen“ (eingebettet: Werte aus `unternehmen.json`; Datenbank: `fact`) | Verzeichnis | Spalte zeigt beides, Filter benennt „(Datenbank)“; Ausgleich, sobald `unternehmen.json` in die Datenbank übernommen ist |
| Doppelte Migrationssysteme | `international/db.py` und Alembic | Alembic-Revision 0001 führt dieselben Dateien mit derselben Buchführung aus; getestet in beide Richtungen |
| Lizenz bei öffentlicher Weiterverbreitung (Yahoo-Kurse, Nachrichten, Wahlstatistiken) | Abrufskripte | vor dem öffentlichen Umschalten je Quelle prüfen (`docs/datenquellen.md`) |

## Ressourcenbedarf (geschätzt, gemessen wo angegeben)

* Datenbank heute: Register, Aliase, Prüfmarken, 4.802 Kennzahlen: Sicherung 2,9 MB (gemessen), Datenbank unter 200 MB.
  Mit allen Kennzahlen aus `unternehmen.json`, VWL- und Handelsreihen voraussichtlich 1–3 GB.
* Arbeitsspeicher: PostgreSQL mit `shared_buffers=256MB`, API ein Prozess (rund 80 MB), Caddy rund 30 MB: passt auf 2 GB (netcup VPS nano),
  Importe mit großen Dateien (BACI) gegebenenfalls nachts, wenn wenig Last ist.
* Plattenplatz: Docker-Abbilder rund 1,2 GB, Oberfläche rund 120 MB je Fassung, PDFs 2,9 GB (wachsend), Sicherungen.
