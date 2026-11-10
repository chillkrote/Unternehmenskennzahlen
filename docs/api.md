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
| `GET /companies/{id}/profile` | vollständiges Profil eines Unternehmens mit Kennzahlen: Werte mit Branchen- und Gruppenmedian und Rang (Rechenregeln wie im Terminal), Zeitreihen, Abschlussposten je Stichtag mit Quelle, Gremien, Vergütung, Dokumente, Berichtstermine | `country` (Vergleichsmenge nur dieses Sitzland) |
| `GET /sectors/{id}/statistics` | Branchenkennzahlen: Anzahl, Median, Quartile, Minimum, Maximum je Kennzahl | `group` (z. B. `Sparkassen`), `country` |
| `GET /profile-metrics` | Kennzahlenkatalog der Profile (Name, Einheit, Format, Gruppe, „höher ist besser“, Hilfe) | — |
| `GET /series` | Katalog der VWL-Reihen (Thema, Einheit, Format, Art, Frequenz, Quelle, Datensatz, Abruf, Projektion ab) mit Gebieten, erstem/letztem Zeitraum, Anzahl | `topic` |
| `GET /series/{id}` | eine VWL-Reihe mit Abdeckung | — |
| `GET /series/{id}/revisions` | alle Fassungen der Werte einer Reihe mit `valid_from`, `valid_to`, Stand der Quelle (`source_updated`) und Abruf (`fetched`) | `geo`, `period`, `only_revised`, `page`, `page_size` |
| `GET /data-catalog` | Datenkatalog: alle Quellen mit Lizenz, Bewertung, Status, `cleared` (öffentlich freigegeben), offener Entscheidung, Pflichtangabe, Zahl der Reihen und Werte, Jahresspanne, letztem Abruf und Importlauf, Zahl der Prognosegeber | `area`, `status`, `cleared`, `decision` |
| `GET /data-catalog/{id}` | eine Quelle mit ihren VWL-Reihen (`series_list`) | — |
| `GET /data-quality` | Prüfbericht: offene Prüfmarken der Unternehmenstabelle, Qualitätsstufen der Fakten, veraltete VWL-Reihen (Verzug je Frequenz), auffällige Sprünge der jüngsten Werte (robuste Abweichung, Schwelle 6), Abdeckung mit festem Nenner (VWL: alle Gebiete mit Werten; Profile: alle Unternehmen mit Profil), nicht freigegebene Quellen mit Daten. Gleicher Stichtag und Datenstand ergeben denselben Bericht; Regeln in `plattform/qualitaet.py` | `as_of` (Stichtag) |
| `GET /analysis/correlation` | Korrelation zweier VWL-Reihen mit denselben Regeln wie die Korrelationsansicht (KOR): gemeinsame Frequenz, Transformation je Reihe, Verzögerung, Pearson, Spearman, p-Werte, Konfidenzintervall, Regressionsgerade, Durbin-Watson, effektive Stichprobe (`n_eff`, `p_eff`), Kreuzkorrelation; Projektionen ausgeschlossen; `format=csv` liefert die gepaarten Werte | `a`, `b` (`reihe:gebiet`), `freq`, `ta`, `tb` (niveau, diff, pct, log, yoy), `agg`, `lag`, `from`, `to`, `method`, `format` |
| `GET /trade/goods` | Gütergruppen (CEPII BACI) mit Weltexportwert, Zahl der Exportländer, HHI und Einstufung (gering < 1 000, mäßig bis 1 800, hoch), CR3, größtem Exportland | `year` |
| `GET /trade/goods/{id}` | ein Gut: Weltmarktanteile der Exportländer, HHI und CR3 je Jahr | `year`, `top` |
| `GET /trade/goods/{id}/alternatives` | Alternativlieferländer ohne die genannten Exportländer (vorhandene Exportkapazität, keine freie Kapazität) | `exclude` (z. B. `CN,TW`), `n`, `year` |
| `GET /trade/countries/{geo}` | ein Exportland: je Gut Wert, Weltmarktanteil, Rang, Zahl aller Abnehmer (`partner_count`), HHI über alle Abnehmer (`partner_hhi`, `partner_hhi_complete`), sonst Untergrenze (`partner_hhi_lower_bound`), die fünf größten Abnehmer | `year` |
| `GET /trade/import-dependencies` | Importseite eines Landes: je Gut Importwert, Zahl der Lieferländer, HHI über alle Lieferländer, Anteil des größten Lieferlands je Jahr, die zehn größten Lieferländer; mit `supplier` der Anteil eines bestimmten Lieferlands | `geo` (Pflicht), `supplier`, `good`, `year` |
| `GET /forecasters` | Prognosegeber je Land (Recherche, Werte noch nicht eingebunden) | `geo`, `priority` (höchstens) |
| `GET /observations` | Werte mehrerer Reihen kompakt `{reihe: {gebiet: [[zeitraum, wert], …]}}`, mit `format=csv` als Tabelle (reihe;gebiet;zeitraum;wert) | `series` (bis 60), `geo`, `from`, `to`, `as_of` (Stand „bekannt zum“, frühere Fassungen revidierter Werte) |
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
GET /api/v1/companies/U000148/profile              (Deutsche Bank: 60 Kennzahlen mit Branchenmedian, Abschlüsse, Gremien)
GET /api/v1/sectors/banken/statistics?group=Sparkassen
GET /api/v1/data-catalog?decision=true   (Quellen mit offener Lizenzentscheidung)
GET /api/v1/forecasters?geo=FR&priority=1
GET /api/v1/trade/goods/chips/alternatives?exclude=CN,TW
GET /api/v1/trade/import-dependencies?geo=DE&supplier=CN
GET /api/v1/series/bip_qoq/revisions?geo=DE&only_revised=true
GET /api/v1/analysis/correlation?a=konsum_privat:DE&b=bip_yoy:DE&lag=1&from=2010
GET /api/v1/observations?series=bip_yoy&geo=DE,FR&format=csv
GET /api/v1/observations?series=bip_qoq,hicp_gesamt&geo=DE,FR&from=2020-Q1
GET /api/v1/observations?series=bip_qoq&geo=DE&as_of=2026-10-01   (Werte, wie sie am 1.10.2026 bekannt waren)
GET /api/v1/search?q=Deutschland%20Automobile
  -> interpreted: {countries: ["DE"], sectors: ["automobil"]}, Gruppen country, sector, company
GET /api/v1/search?q=Siemns              (fehlertolerant -> Siemens AG)
```

## Aktualität je Gebiet (`/data-quality`, Abschnitt `freshness`)

Je Reihe: letzter Zeitraum der Quelle, Verzug, Stand der Quelle, Abruf, Vergleichsfenster (12 Monate, 8 Quartale, 5 Jahre) und
die Gebiete, die nicht aktuell sind oder Lücken haben. Status je Gebiet: `current`, `stale` (hinter dem Stand der Quelle),
`source_stale` (Quelle insgesamt im Verzug), `dormant` (lange nichts mehr), `not_published` (bekannt eingestellt), `missing`
(erwartet, ohne Wert). Die Abdeckung nennt `covered`, `expected`, `share`, `basis`, `missing`, `unexpected`; erwartet sind die
Gebiete, die der Abruf der Reihe anfordert. Regeln: `server/plattform/qualitaet.py`.

## Stand „bekannt zum“ (`as_of`)

`valid_from` ist der Zeitpunkt, zu dem ein Wert in **diese** Datenbank kam, nicht die Veröffentlichung der Quelle. `as_of` vor
dem Beginn der Historie liefert nichts; `meta.vintage` nennt den Beginn (`history_start`) und die Hinweise sagen das im Klartext.
Frühere Stände werden nicht rekonstruiert.

## Handel: welche Frage beantwortet welche Zahl

| Frage | Zahl | Endpunkt |
|---|---|---|
| Wie konzentriert ist das weltweite Angebot eines Guts? | HHI der Weltexporte, CR3 | `/trade/goods` |
| Von wem kauft ein Land? | Anteile der Lieferländer, HHI über alle Lieferländer | `/trade/import-dependencies` |
| Wie stark hängt ein Land an einem Lieferland? | Anteil am Importwert des Guts | `/trade/import-dependencies?supplier=` |
| An wen verkauft ein Land? | Abnehmer, HHI über alle Abnehmer | `/trade/countries/{geo}` |
| Wer könnte ersatzweise liefern? | vorhandene Exporte ohne die ausgeschlossenen Länder (keine freie Kapazität) | `/trade/goods/{id}/alternatives` |

Die Bänder 1.000 und 1.800 stammen aus der Fusionskontrolle und sind nur Lesehilfe, keine Schwelle der Versorgungssicherheit.
Quelle ist CEPII BACI (abgeglichene Spiegelstatistik, FOB); Umschlagplätze erscheinen als Lieferland, inländische Produktion fehlt.

## Geänderte Felder (10.11.2026)

`partner_hhi_top5` in `/trade/countries/{geo}` entfällt, weil ein HHI aus fünf Partnern keine belastbare Zahl ist; Ersatz
`partner_hhi` mit `partner_hhi_complete` bzw. `partner_hhi_lower_bound`. `coverage.series.denominator` in `/data-quality` entfällt
zugunsten von `expected` und `basis`. Die Oberfläche nutzte beide Felder nicht; die API ist noch nicht öffentlich.

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
