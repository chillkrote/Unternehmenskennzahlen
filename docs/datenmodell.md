# Datenmodell

Schema `international` in PostgreSQL 16. Grundschema aus `international/migrations/001–004` (siehe `international/README.md`,
`international/UNTERNEHMENSTABELLE_SQL.md`), Erweiterungen als Alembic-Revisionen in `server/alembic/versions/`.

## Heute vorhanden

| Tabelle / Funktion | Inhalt | Schlüssel |
|---|---|---|
| `country` | Länder (38 OECD mit Beitrittsdatum, dazu alle Länder der Weltkugel), `name_de`, `region` (Revision 0002) | `iso2` |
| `entity` | Unternehmen (juristische Einheit), eine Zeile je Repo-ID | `id` = `U000123` |
| `identifier` | weitere Kennungen je Unternehmen (ISIN, LEI, CIK, Ticker …), eine Kennung gehört genau einem Unternehmen | (`scheme`, `value`) |
| `instrument`, `listing` | Wertpapiere je Unternehmen und Börsennotierungen mit Gültigkeitszeitraum (keine Überlappung gleicher Ticker) | `isin`; (`mic`, `ticker`, Zeitraum) |
| `company_register` | Zeilen der Unternehmenstabelle (Stammdaten, Land, Branche, Notierung, Quelle), `active` statt Löschen | `row_key`, `entity_id` |
| `company_alias` | Aliase und zusammengelegte Namen mit Herkunft | (`row_key`, `alias`, `kind`) |
| `review_flag` | Prüfmarken (automatisch ergänzt, notiert ohne ISIN, Branchen-Platzhalter, Prüfliste) mit Entscheidung | (`row_key`, `code`, `detail`) |
| `metric` | Kennzahlendefinitionen: Periodenart (Stichtag/Zeitraum), Einheitenart, aufsichtsrechtlich | `code` |
| `fact` | Beobachtungen: Wert, Einheit, Periode, Rechnungslegung, Konsolidierungskreis, Dimensionen, Qualität, `reported_at` (Veröffentlichung), `recorded_at` (Erfassung), `provenance` (Originalwert, Skalierung, Formular …) | `id`; eindeutig je (`source_id`, `source_fact_key`, `mapping_version`) |
| `source_document` | Quelle je Datensatz: Anbieter, URL, SHA-256, Ablageort, Abrufzeit, Rechtsstatus | `id` |
| `fx_rate` | Wechselkurse mit Quelle | (`base`, `quote`, `rate_date`, `source_id`) |
| `ingestion_run` | Importläufe: Adapter, Status, Anzahl, Wasserzeichen, Fehler | `id` |
| `register_import` | welcher Stand der Unternehmenstabelle (SHA-256) wann importiert wurde | `id` |
| `fact_as_of(datum)`, Sicht `fact_current` | je Kennzahl/Periode/Abgrenzung die zum Datum zuletzt veröffentlichte, nicht verworfene Fassung | — |

Regeln im Schema: Stichtagswerte ohne `period_start`, Zeitraumwerte mit; Geldwerte nur mit ISO-Währung, Quoten nur `ratio`;
aufsichtsrechtliche Kennzahlen nur mit `consolidation = 'regulatory'`; eine ISIN nie bei zwei Unternehmen (Trigger).
Eigenkapitalquote nach HGB und IFRS bleiben über `accounting_standard` getrennt, Eigenkapital mit und ohne Minderheiten sind
eigene Kennzahlen (`equity`, `equity_incl_nci`).

## Zeitreihen und Revisionen

Getrennt gespeichert: Beobachtungszeitraum (`period_start`, `period_end`), Veröffentlichung (`reported_at`), Abruf
(`source_document.fetched_at`), Erfassung (`recorded_at`), Fassung (`mapping_version`, neue Quelle = neue Zeile). Revisionen
bleiben als eigene Zeilen erhalten; `fact_as_of` liefert den damals bekannten Stand. Noch offen (geplant, Phase 6):
Kennzeichen für Prognose/Schätzung/Modell als eigenes Feld (`value_kind`), Gültigkeitszeitraum je Fassung, Archivierungsregel für
Zwischenstände.

## Geplante Erweiterungen (Reihenfolge laut `umsetzungsplan.md`)

| Objekt | Zweck | Paket |
|---|---|---|
| `fact.value_kind` (`observed`, `preliminary`, `forecast`, `estimate`, `modelled`) und `fact.status`-Flags (revidiert, veraltet, Prüfung fehlgeschlagen) | Status nicht gegenseitig ausschließend abbilden | P3 |
| `series` (Zeitreihen ohne Unternehmen: Land/Region × Indikator × Frequenz × Einheit × Quelle) und `observation` | VWL, Prognosen, Handel, Börsenindizes | P2/P4 |
| `data_source` (Katalog: Lizenz, Weiterverbreitung, Abrufart, Takt, Grenzen) | Datenkatalog, `/data-catalog` | P3 |
| `entity_relation` (Beteiligungen, Tochter, Fusion, Nachfolger mit Gültigkeit und Beleg) | Konzerne, Namenswechsel | P5 |
| `trade_flow` (Berichtsland, Partner, HS-Code mit Version, Jahr, Wert, Menge, Quelle) | Handelsabhängigkeit | P5 |
| `election`, `election_result`, Verwaltungseinheiten mit PostGIS-Geometrie | Wahlen, Karten | P4 |
| `change_event` | Änderungsfeed, Atom | P6 |

Partitionierung ist nicht vorgesehen, solange `fact` unter etwa 50 Mio. Zeilen bleibt; Indizes reichen.
