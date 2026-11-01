# Segmentdaten (Umsatz und Segmentergebnis je Berichtssegment)

`segmente_lang.csv` (Semikolon, UTF-8 mit BOM) enthält die Segmentzahlen der DAX-, MDAX- und SDAX-Unternehmen, **von Hand aus der Segmentberichterstattung des jeweiligen Konzernabschlusses gelesen** (Bericht für Bericht).

Spalten: `unternehmen_id` (zentrale ID `U000123`), `gj`, `segment` (Name wie im Bericht), `kennzahl`, `wert_mio` (Millionen in `waehrung`), `waehrung`, `quelle_dokument` (Pfad der PDF im Repo), `pdf_seite` (Seite in der PDF, nicht die gedruckte Seitenzahl), `pruefstatus`, `bemerkung`.

Hinweise:
- Segmentnamen und -abgrenzung sind je Unternehmen verschieden und ändern sich zwischen Jahren; Vorjahre stehen in der angepassten Struktur des jüngsten Berichts, soweit dieser sie ausweist.
- Zeilen wie „Überleitung“ oder „Konzern“ gehören zur Summenprobe (Segmente + Überleitung = Konzern).
- Lücken: Unternehmen ohne Geschäftsbericht im Repo stehen in `fehlend.md`.
- Weitere Kennzahlen (Stand 31.10.2026, 45 Unternehmen): Segmentvermögen, Segmentschulden, Investitionen/Zugänge, Abschreibungen, Capital Employed bzw. operatives Vermögen – nur dort erfasst, wo der Bericht sie je Segment tabelliert. Abschreibungen stehen als positiver Betrag; Bezeichnungen folgen dem Bericht (z. B. „Gross operating capital“ bei Beiersdorf). Ausstehend sind die übrigen DAX-/MDAX-/SDAX-Unternehmen (Liste: Unternehmen ohne diese Kennzahlen in `segmente_lang.csv`).
- Anfügen: `python3 segmente/anfuegen.py eingabe.json`.
