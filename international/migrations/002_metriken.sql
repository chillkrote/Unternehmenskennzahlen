-- Kennzahlenkatalog des MVP. Definitionen stehen in description; Abgrenzungen je Quelle in fact.provenance.
INSERT INTO international.metric (code, description, period_kind, unit_kind, regulatory) VALUES
 ('assets', 'Bilanzsumme / Vermögenswerte gesamt laut Abschluss (Stichtag)', 'instant', 'money', false),
 ('equity', 'Eigenkapital laut Bilanz; Abgrenzung (mit/ohne Minderheitsanteile) steht je Wert in provenance', 'instant', 'money', false),
 ('revenue', 'Umsatzerlöse (nur branchengeeignet, bei Banken nicht verwenden)', 'duration', 'money', false),
 ('net_income', 'Jahresüberschuss / Periodenergebnis laut GuV', 'duration', 'money', false),
 ('operating_cash_flow', 'Cashflow aus laufender Geschäftstätigkeit', 'duration', 'money', false),
 ('employees', 'Mitarbeiter (Stichtag oder Durchschnitt, siehe provenance)', 'instant', 'count', false),
 ('cet1_capital', 'Hartes Kernkapital (CET1) nach CRR, Art. 50', 'instant', 'money', true),
 ('t1_capital', 'Kernkapital (Tier 1) nach CRR, Art. 25', 'instant', 'money', true),
 ('own_funds', 'Eigenmittel gesamt nach CRR, Art. 72', 'instant', 'money', true),
 ('rwa', 'Gesamtrisikobetrag (risikogewichtete Positionen) nach CRR, Art. 92', 'instant', 'money', true),
 ('cet1_ratio', 'CET1-Quote = CET1 / RWA (Dezimalquote)', 'instant', 'ratio', true),
 ('t1_ratio', 'Kernkapitalquote = T1 / RWA (Dezimalquote)', 'instant', 'ratio', true),
 ('total_capital_ratio', 'Gesamtkapitalquote = Eigenmittel / RWA (Dezimalquote)', 'instant', 'ratio', true),
 ('leverage_ratio', 'Verschuldungsquote nach CRR, Art. 429 (Dezimalquote)', 'instant', 'ratio', true),
 ('lcr', 'Liquiditätsdeckungsquote nach Delegierter VO (EU) 2015/61 (Dezimalquote, 1.5 = 150 %)', 'instant', 'ratio', true),
 ('total_capital_requirement', 'Gesamtkapitalanforderung inkl. Puffer (EU KM1 Zeile EU 11a, Dezimalquote)', 'instant', 'ratio', true),
 ('leverage_exposure', 'Gesamtrisikopositionsmessgröße der Verschuldungsquote nach CRR, Art. 429', 'instant', 'money', true),
 ('nsfr', 'Strukturelle Liquiditätsquote (NSFR) nach CRR, Art. 428b (Dezimalquote)', 'instant', 'ratio', true),
 ('hqla', 'Liquiditätspuffer (HQLA) nach Delegierter VO (EU) 2015/61', 'instant', 'money', true),
 ('de_fonds_340g', 'Fonds für allgemeine Bankrisiken, § 340g HGB (nur Deutschland)', 'instant', 'money', false)
ON CONFLICT (code) DO NOTHING;
