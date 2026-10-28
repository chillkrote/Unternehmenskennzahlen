# ESG-Kennzahlen aus Berichten (Pilot)

Langformat `esg_lang.csv` (Semikolon, UTF-8): `unternehmen_id`, `gj`, `kennzahl`, `wert`, `einheit`, `quelle_dokument`, `seite`, `pruefstatus`, `bemerkung`.
`unternehmen_id` ist die zentrale ID aus `stammdaten/`. `seite` ist die PDF-Seite. Einheiten stehen so, wie der Bericht sie nennt (t oder Mio. t CO2e); Umrechnung erst bei der Anzeige.

Kennzahlen (Stand): `thg_scope1`, `thg_scope2_marktbasiert`, `thg_scope3_gesamt` (Brutto, ESRS E1-6, GJ 2025 und 2024).

Stand 28.10.2026: Pilot mit Deutsche Telekom und RWE. Warum nur zwei: Die Tabellen unterscheiden sich je Bericht stark (Spaltenaufbau, Basisjahre, Konzern- oder Teilmengen, Mio. t oder t); ein automatischer Auszug lieferte falsche Spalten. Jeder Wert wurde deshalb von Hand aus der Tabelle gelesen. Die Berichte von BASF, Beiersdorf, MTU, Rheinmetall und adidas liegen im Repo und sind die nächsten Kandidaten; BASF hat mehrere Zahlenspalten pro Jahr und braucht Klärung, welche gilt.

Regeln: nur Werte, die der Bericht selbst ausweist (keine Schätzung, keine Summenbildung aus Teilen, die der Bericht nicht summiert); fehlende Werte bleiben leer.
