# Universum: in Deutschland notierte Aktiengesellschaften

Stand der Quellen: Deutsche Börse 01.10.2026, alle übrigen Abrufe 27.10.2026.

## Abgrenzung

Aufgenommen sind Aktien, die an einer deutschen Börse **mit Zutun des Emittenten** notiert bzw. in ein Qualitätssegment einbezogen sind:

| Segment | Börse | Marktart | Quelle |
|---|---|---|---|
| Prime Standard | Frankfurt | regulierter Markt | Deutsche Börse, `Listed-companies` |
| General Standard | Frankfurt | regulierter Markt | Deutsche Börse, `Listed-companies` |
| Scale | Frankfurt | Freiverkehr (KMU-Wachstumsmarkt) | Deutsche Börse, `Listed-companies` |
| Basic Board | Frankfurt | Freiverkehr | Deutsche Börse, `Listed-companies` |
| m:access | München | Freiverkehr, Qualitätssegment | Börse München, Liste gelisteter Unternehmen |
| Primärmarkt | Düsseldorf | Freiverkehr, Qualitätssegment | Börse Düsseldorf, Aktien Primärmarkt |
| Freiverkehr/Regionalbörse | Xetra bzw. Börse Frankfurt | weitere Aktien **deutscher** Emittenten (DE-ISIN), die dort handelbar sind; darunter Werte, die nur an Regionalbörsen (Hamburg, Hannover, Berlin, Stuttgart) im regulierten Markt notieren | T7 `allTradableInstruments` (Xetra, Börse Frankfurt) |

**Ausländische Emittenten** sind enthalten, wenn sie selbst eine Notierung in einem der Segmente oben haben (z. B. Airbus, Qiagen, Aroundtown, BB Biotech, Befesa). **Nicht** enthalten sind die mehreren tausend ausländischen Aktien, die ohne Antrag des Emittenten in den Freiverkehr einbezogen sind (z. B. Apple, Nestlé im Open Market), ADRs/GDRs sowie vorübergehende Handelslinien (junge Aktien, Umtausch- und Verkaufslinien).

Banken stehen in der Branche `banken` nur mit Kapitalmarktdaten; die eigentliche Erhebung liegt unter [`banken/bilanzvergleich-gj2025`](../../banken/bilanzvergleich-gj2025/).

## Bekannte Lücken

- Aktien, die ausschließlich an einer Regionalbörse notieren und weder auf Xetra noch an der Börse Frankfurt handelbar sind, fehlen (die Regionalbörsen veröffentlichen keine maschinenlesbare Gesamtliste; Börse Stuttgart sperrt automatisierte Abrufe).
- Die Deutsche-Börse-Liste hat den Stand 01.10.2026; Notierungsaufnahmen danach sind nur über die T7-Instrumentenliste (Stand 27.10.2026) erfasst (z. B. Pfisterer, TK Accelis), Delistings nach dem 01.10. sind noch enthalten.

## Dateien

| Datei | Inhalt |
|---|---|
| `universum.csv` | eine Zeile je Unternehmen: ID, Name, Branche, Segment, Index, Land, Sitz, Haupt-ISIN, Kürzel, Yahoo-Ticker, weitere Gattungen, Sektor laut Börse und Yahoo, Website |
| `universum_instrumente.csv` | eine Zeile je Aktiengattung (Stamm-/Vorzugsaktien getrennt) |
| `rohdaten_instrumente_roh.csv` | Rohliste aus den Börsenquellen vor Zusammenführung |
| `korrekturen.json` | Hand-Zuordnungen (Branche, Name, Website, Zusammenführung) für Werte ohne Börsensektor |
| *(entfällt)* `ids.json` | ersetzt durch das zentrale Register `stammdaten/` (ID `U000123`, ISIN → ID in `stammdaten/isin_zuordnung.csv`) |
| `quellen/` | Originalabrufe der Börsenlisten (XLSX, HTML, CSV; Frankfurt-Liste gzip-komprimiert) |
| `skripte/universum.py` | liest die Quellen, schreibt `rohdaten_instrumente_roh.csv` |
| `skripte/unternehmen.py` | fasst Gattungen zu Unternehmen zusammen und ordnet Branchen zu |

## Branchenzuordnung

Grundlage ist der Sektor/Subsektor der Deutschen Börse; Werte ohne Börsensektor bekommen die Branche aus Sektor/Industrie laut Yahoo, der Rest ist in `korrekturen.json` von Hand zugeordnet. Immobilien (Subsektor „Real Estate“) und erneuerbare Energien (Subsektor „Renewable Energies“) sind eigene Branchen, unabhängig vom Obersektor.
