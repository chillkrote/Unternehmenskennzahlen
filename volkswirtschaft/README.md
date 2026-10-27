# Volkswirtschaftliche Kennzahlen

Zeitreihen für das Terminal-Modul „Volkswirtschaft“ (Deutschland, Euroraum, EU-27, FR, IT, ES, NL, AT), Quelle Eurostat (Dissemination-API, JSON-stat, ohne Schlüssel, kostenfrei).

| Datei | Inhalt |
|---|---|
| `serien.csv` | Katalog: je Reihe Thema, Name, Einheit, Format, Takt, Datensatz, Filter, Abruf-URL, Abrufdatum, erster/letzter Zeitraum, Hinweis |
| `zeitreihe_lang.csv` | `serie_id, geo, zeit, wert` (Monat `2026-09`, Quartal `2026-Q2`, Jahr `2025`) |
| `laender.csv`, `themen.csv` | Bezeichnungen |
| `berichte.csv` | regelmäßige Berichte mit Link (Bundesbank, Destatis, Sachverständigenrat, ifo, EZB, IWF) |
| `rohdaten/eurostat/*.json.gz` | unveränderte API-Antworten je Reihe |
| `skripte/abruf_eurostat.py` | Abruf; neue Reihe = ein weiterer Eintrag in `SERIEN` |

Reihen: BIP und Verwendung, HVPI nach Komponenten, Erzeugerpreise, Arbeitslosenquote, Arbeitskosten, Erwerbstätige, Einzelhandel, Produktion, Bau, Stimmungsindikatoren, Euribor, Schulden- und Defizitquote.

Abruf: `python3 -I volkswirtschaft/skripte/abruf_eurostat.py`, danach `python3 app/build.py`.

Grenzen: Der Euroraum ist bei Eurostat je Datensatz EA20 oder EA21 (Arbeitslosenquote); Arbeitskosten und Euribor liegen nicht für alle Länder vor. Bundesbank- und Destatis-Reihen (GENESIS braucht Anmeldung) sind nicht eingebunden; die Berichte sind als Links erfasst. Die Veröffentlichungsstände unterscheiden sich je Reihe (Stand je Zeile in der Übersicht).
