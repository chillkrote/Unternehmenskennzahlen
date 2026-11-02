# Unternehmenstabelle in der SQL-Datenbank

Die zusammengeführte Tabelle (`unternehmen-tabelle/Unternehmen_Tabelle.csv`, Stand PR #76: 26.130 Zeilen) liegt zusätzlich im PostgreSQL-Kernmodell (Schema `international`). Excel und CSV bleiben Ausgabeformate und Quelle der Wahrheit, bis die Datenbank der Arbeitsstand wird; der Export aus der Datenbank ist byteweise gleich der CSV (Test `test_export_ist_byteweise_die_tabelle`).

## Warum SQL zusätzlich zu Excel

Excel ist für die Ansicht und für Handarbeit gut. Für 26.000 Unternehmen mit späteren Zeitreihen, Aliasen und Prüfmarken fehlen ihm Schlüssel- und Eindeutigkeitsprüfung (eine ISIN kann nicht bei zwei Unternehmen stehen, das erzwingt jetzt die Datenbank), Abfragen über mehrere Tabellen (Unternehmen × Kennzahlen × Zeit) und wiederholbare Importe ohne Handarbeit.

## Tabellen (Migration `004_unternehmenstabelle.sql`)

| Tabelle | Inhalt |
|---|---|
| `company_register` | eine Zeile je Tabellenzeile; `entity_id` (`U000123`) nur bei Unternehmen mit Repo-ID (1.284), sonst leer; `row_key` ist ein stabiler Zeilenschlüssel (ISIN, sonst LEI, sonst Land+Name) |
| `company_alias` | 2.475 Aliase: `stammdaten/unternehmen_aliase.csv` und die in den Bereinigungsprotokollen zusammengelegten Namen |
| `review_flag` | Prüfmarkierungen: `automatisch_ergaenzt` ("bitte prüfen" in der Beschreibung), `boersennotiert_ohne_isin`, `branche_platzhalter`, `pruefliste_getrennt` / `pruefliste_zusammengelegt` (mit Entscheidung und Begründung aus `bereinigung_pruefliste.csv`) |
| `register_import` | welcher Dateistand (SHA-256) zuletzt importiert wurde |
| Sicht `company_overview` | Zeile, ID, offene Prüfmarken und Anzahl Kennzahlen (`fact`) je Unternehmen |

Regeln: Zeilen ohne ID bekommen keine neue ID (die vergibt nur `stammdaten/ids.py`); ISIN und LEI sind in `company_register` eindeutig, ein Trigger weist eine ISIN ab, die in `instrument` einem anderen Unternehmen gehört; der Import bricht vor dem ersten Schreiben ab, wenn die Tabelle doppelte IDs/ISINs/LEIs hat oder eine ISIN zu einer anderen Repo-ID gehört. Nichts wird gelöscht: fehlt eine Zeile in einer neueren Tabelle, wird sie `active = false`.

## Anleitung

```bash
pip install -r international/requirements.txt              # psycopg; openpyxl nur für --xlsx
export INTERNATIONAL_DATABASE_URL="postgresql://postgres:PASSWORT@127.0.0.1:5433/international"   # Start der Datenbank: DOCKER.md
python3 international/import_unternehmen.py --dry-run     # Probelauf, rollt zurück (ca. 10 s)
python3 international/import_unternehmen.py               # Migrationen, Entitäten, Zeilen, Aliase, Prüfmarken
python3 international/import_de.py                        # (wie bisher) Zeitreihen für die Unternehmen mit ID
python3 international/export_unternehmen.py out.csv [--xlsx out.xlsx] [--mit-pruefmarken]
```

Beispiele: `SELECT * FROM international.company_overview WHERE offene_pruefmarken > 0 AND unternehmen_id IS NOT NULL;`, `SELECT r.* FROM international.company_alias a JOIN international.company_register r USING (row_key) WHERE lower(a.alias) = lower('Deutsche Post');`.

Neue Tabellenstände: erst die CSV/XLSX wie bisher aktualisieren (`unternehmen-tabelle/`), dann `import_unternehmen.py` erneut laufen lassen (Upsert, wiederholbar). Aliase und Prüfmarken werden dabei komplett aus den Dateien neu aufgebaut; von Hand in der Datenbank gesetzte Marken würden überschrieben, sie gehören also in die Dateien.

## Nicht Teil dieses Schritts

* Die Datenbank wird noch nicht zur Quelle der Wahrheit; dafür müsste Handarbeit (Prüfliste, Zusammenlegungen) in der Datenbank statt in den Skripten laufen.
* Ein Name→ID-Abgleich für die 24.853 Zeilen ohne ID (neue IDs über `stammdaten/ids.py`) ist offen; `sitzland_unbekannt` (255 Registerfirmen) und Länder wie "Sonstige" haben noch kein ISO-Land (`domicile` bleibt leer).
* Das Terminal liest weiter die CSV/Excel-Dateien.
