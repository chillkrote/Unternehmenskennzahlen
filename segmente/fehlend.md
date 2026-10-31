# Unternehmen ohne Segmentdaten (Stand 31.10.2026)

## DAX

34 von 40 DAX-Unternehmen sind erfasst (siehe `segmente_lang.csv`). Es fehlen:

| Unternehmen | Grund |
|---|---|
| Mercedes-Benz Group | Download der Berichts-PDF auf group.mercedes-benz.com liefert HTTP 403 (Bot-Schutz); wird nicht umgangen |
| Bayer | bayer.com liefert HTTP 403; wird nicht umgangen |
| SAP | robots.txt von sap.com untersagt den Abruf der Investor-Dokumente |
| Commerzbank | kein frei auffindbarer Direktlink zum Konzern-Geschäftsbericht 2025 (nur Einzelabschluss im Repo) |
| HOCHTIEF | Berichtsseite lädt Links dynamisch, kein Direktlink gefunden |
| Qiagen | nur Form 20-F; Abruf über SEC EDGAR noch nicht eingerichtet (verlangt Kontaktangabe in der Kennung) |

Die Einzelberichte werden ergänzt, sobald ein erlaubter Weg bekannt ist (z. B. manueller Download durch Robin in `dokumente/<unternehmen>/`).

## MDAX

42 von 49 MDAX-Werten sind erfasst, Berichte jeweils selbst geladen und unter `dokumente/<unternehmen>/` abgelegt. Die übrigen sieben haben nach IFRS 8 nur ein berichtspflichtiges Segment und damit keine Segmentzahlen:

| Unternehmen | Hinweis im Bericht |
|---|---|
| AIXTRON | „nur ein berichtspflichtiges Segment" |
| DWS Group | einziges Geschäftssegment (Asset Management) |
| Elmos Semiconductor | „nur ein einziges Segment" (Halbleitergeschäft) |
| IONOS Group | einheitliche Steuerungsebene; AdTech als aufgegebener Geschäftsbereich ausgewiesen |
| K+S | „einziges Geschäftssegment"; Kundensegmente sind laut Bericht keine Segmente nach IFRS 8 |
| LEG Immobilien | seit 2016 nur ein Segment |
| Siltronic | „nur ein berichtspflichtiges Segment" |

Besonderheiten bei einzelnen Quellen:
- TKMS: Quelle ist der freiwillige verkürzte Geschäftsbericht 2024/25 (kombinierter Abschluss, Geschäftsjahr bis 30.9.); die zuvor abgelegte `TKMS_GB25.pdf` (27 Seiten) enthält keine Segmentnote.
- Aumovio, Hugo Boss, thyssenkrupp u. a. mit abweichendem Geschäftsjahr: `gj` ist das Jahr, in dem das Geschäftsjahr endet.
- Porsche SE: Segmente sind Beteiligungsarten (Kern- und Portfoliobeteiligungen), keine Umsatzsegmente.

## SDAX

55 von 70 SDAX-Werten sind erfasst, Berichte jeweils selbst geladen und unter `dokumente/<unternehmen>/` abgelegt. Die übrigen 15:

| Unternehmen | Grund |
|---|---|
| ASTA Energy Solutions | einziges Segment „Energy" |
| ATOSS Software | per Textsuche keine Segmentnote gefunden (vermutlich ein Segment) |
| Basler | per Textsuche keine Segmentnote gefunden (vermutlich ein Segment) |
| Grand City Properties | per Textsuche keine Segmentnote gefunden (Portfolio nach Regionen, Einsegment-Unternehmen vermutet) |
| Hamborner REIT | per Textsuche keine Segmentnote gefunden (vermutlich ein Segment) |
| Nagarro | per Textsuche keine Segmentnote gefunden |
| Shelly Group | per Textsuche keine Segmentnote gefunden (vermutlich ein Segment) |
| Stratec | „single-segment entity" |
| TeamViewer | „einziges Segment" |
| init | 2025 keine Segmentnote; neue Segmente erst ab 2026 angekündigt |
| Friedrich Vorwerk | Bericht 2025 nicht frei abrufbar gefunden (Zahlen nur indirekt über MBB-Segment sichtbar) |
| Deutsche Beteiligungs AG | Rumpfgeschäftsjahr 2024 (1 Quartal), nicht vergleichbar; Segmente Private Equity / Fund Investment Services nicht gelesen |
| Deutsche Pfandbriefbank | abgelegte Datei enthält nur den Lagebericht, kein Konzernanhang mit Segmentnote |
| Adtran Networks, Vincorion | kein Bericht frei gefunden |

Besonderheiten:
- Abweichende Geschäftsjahre: `gj` ist das Jahr, in dem das Geschäftsjahr endet. Südzucker, HORNBACH, KWS, Verbio und Heidelberger Druck stehen mit 2026 (GJ 2025/26) und 2025 (GJ 2024/25); Carl Zeiss Meditec und Douglas mit 2025 und 2024. Im Dokumentenindex steht dagegen das Startjahr (2025).
- Vorjahreswerte sind teils vom Unternehmen angepasst (neue Segmentstruktur): Dürr, Kontron, 1&1, Mutares, JOST, Heidelberger Druck, PNE, DERMAPHARM.
- Die Berichte von Mutares (Hauptversammlung-Kopie), HelloFresh (Lobbyregister, englisch) und Redcare (72 MB) sind Kopien aus erlaubten Quellen.
