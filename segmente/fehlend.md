# DAX-Unternehmen ohne Segmentdaten (Stand 28.10.2026)

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
