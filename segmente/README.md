# Segmentdaten (Umsatz und Segmentergebnis je Berichtssegment)

`segmente_lang.csv` (Semikolon, UTF-8 mit BOM) enthält die Segmentzahlen der DAX- und MDAX-Unternehmen, **von Hand aus der Segmentberichterstattung des jeweiligen Konzernabschlusses gelesen** (Bericht für Bericht).

Spalten: `unternehmen_id` (zentrale ID `U000123`), `gj`, `segment` (Name wie im Bericht), `kennzahl`, `wert_mio` (Millionen in `waehrung`), `waehrung`, `quelle_dokument` (Pfad der PDF im Repo), `pdf_seite` (Seite in der PDF, nicht die gedruckte Seitenzahl), `pruefstatus`, `bemerkung`.

Hinweise:
- Segmentnamen und -abgrenzung sind je Unternehmen verschieden und ändern sich zwischen Jahren; Vorjahre stehen in der angepassten Struktur des jüngsten Berichts, soweit dieser sie ausweist.
- Zeilen wie „Überleitung“ oder „Konzern“ gehören zur Summenprobe (Segmente + Überleitung = Konzern).
- Lücken: Unternehmen ohne Geschäftsbericht im Repo stehen in `fehlend.md`.
- Anfügen: `python3 segmente/anfuegen.py eingabe.json`.
