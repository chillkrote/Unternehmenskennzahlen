# API v1

Lesende, öffentliche API unter `/api/v1`. Maschinenlesbare Beschreibung: `/api/v1/openapi.json`, Oberfläche zum Ausprobieren:
`/api/v1/docs`. Code: `server/plattform/`. Tests: `server/tests/test_api.py`.

## Grundregeln

* Antwort: `{"data": …, "meta": {"api_version": "1", "generated_at", "pagination"?, "source"?, "data_as_of"?, "notes": []}}`.
* Fehler: `{"error": {"code", "message", "details"}}` mit passendem Status (404 `nicht_gefunden`, 422 `ungueltige_eingabe` bzw.
  fachlicher Code, 429 `zu_viele_anfragen` mit `Retry-After`, 503 `datenbank`, 504 `zeitlimit`, 405 `nur_lesend`).
* IDs: Unternehmen `U000123` (dauerhaft), Länder ISO-3166-Alpha-2 (`ZZ` = unbekannt), Branchen-IDs wie in `/sectors`.
* Datum ISO 8601; Zahlen unskaliert in der angegebenen Einheit (`EUR`, `ratio` = Dezimalquote, `count`). Fehlende Werte fehlen,
  sie werden nie als 0 geliefert.
* Pagination: `page` (ab 1), `page_size` (Standard 100, höchstens 200); `meta.pagination.total` ist die Trefferzahl insgesamt.
* Caching: `ETag` (ohne Zeitstempel) und `Cache-Control: public, max-age=300`; `If-None-Match` liefert 304. Antworten ab 1 KB gzip.
* Begrenzung: 240 Anfragen je Minute und IP (`API_RATE_LIMIT_PER_MINUTE`), Zeitlimit 5 s je Datenbankabfrage.

## Endpunkte

| Pfad | Zweck | Wichtige Parameter |
|---|---|---|
| `GET /companies` | Unternehmensliste mit Suche, Filtern, Seiten | `q`, `country`, `sector`, `listed`, `has_metrics`, `ids` (bis 500), `sort` (`default` = mit Kennzahlen zuerst, `name`, `-name`, `id`, `country`), `page`, `page_size`, `fields` |
| `GET /companies/{id}` | Profil: Stammdaten, Kennungen, Aliase, Prüfmarken, vorhandene Kennzahlen, Links | — |
| `GET /companies/{id}/metrics` | Kennzahlenwerte mit Einheit, Rechnungslegung, Konsolidierung, Quelle, Herkunft, Veröffentlichungs- und Erfassungszeit | `metric`, `as_of` (Stand „bekannt zum“), `from`, `to` |
| `GET /search` | eine Suche über Unternehmen, Länder, Branchen, Kennzahlen; erkennt Länder und Branchen in den Suchwörtern | `q`, `types`, `limit` |
| `GET /countries` | alle Länder mit deutschem Namen, Region, OECD-Mitgliedschaft, Zahl der Unternehmen | — |
| `GET /countries/{code}` | ein Land mit Unternehmen je Branche | — |
| `GET /sectors` | Branchen mit Zahl der Unternehmen | — |
| `GET /indicators` | Kennzahlenkatalog (Definition, Periodenart, Einheitenart, aufsichtsrechtlich) mit Abdeckung | — |
| `GET /updates` | letzter Importlauf je Datenquelle mit Status und letztem Erfolg | — |
| `GET /health` | API und Datenbank erreichbar, Schema-Revision (503 bei Ausfall, nie gecacht) | — |

## Beispiele

```
GET /api/v1/companies?country=DE&sector=automobil&listed=true&fields=id,name,isin
GET /api/v1/companies?q=AT0000BAWAG2
GET /api/v1/companies/U000148/metrics?metric=assets&as_of=2026-06-30
GET /api/v1/search?q=Deutschland%20Automobile
  -> interpreted: {countries: ["DE"], sectors: ["automobil"]}, Gruppen country, sector, company
GET /api/v1/search?q=Siemns              (fehlertolerant -> Siemens AG)
```

## Suche

PostgreSQL `pg_trgm` (Trigramm-Ähnlichkeit mit GIN-Index auf Namen und Aliasen). Reihenfolge: exakte Kennung (ID, ISIN, LEI,
Ticker) vor Namensanfang vor Ähnlichkeit. Länder über ISO-Codes, englische und deutsche Namen und Synonyme (`UK`, `USA`,
`Schweiz` …), Branchen über Namen und Synonyme (`Auto`, `Pharma`, `Bank` …, `server/plattform/api/common.py`). Zweibuchstabige
Wörter wie „in“ oder „de“ gelten nur in Großschrift als Ländercode.

## Versionierung

Neue Felder kommen ohne Versionswechsel hinzu. Entfernen oder Umdeuten von Feldern erfordert `/api/v2`; `/api/v1` bleibt dann
mindestens bis zur Umstellung der Oberfläche bestehen. Jede Antwort trägt `X-API-Version`.

## Nicht öffentlich

Es gibt keine schreibenden oder administrativen Endpunkte. Importe laufen ausschließlich auf dem Server (`server/etl`).
