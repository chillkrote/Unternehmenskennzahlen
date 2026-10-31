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
