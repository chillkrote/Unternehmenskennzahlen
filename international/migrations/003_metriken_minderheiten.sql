-- Eigenkapital und Ergebnis einschließlich Minderheitsanteilen als eigene Kennzahlen, damit die Abgrenzung nie vermischt wird
-- (equity / net_income = Anteil der Muttergesellschafter, *_incl_nci = Gesamtgrößen laut Bilanz bzw. GuV).
INSERT INTO international.metric (code, description, period_kind, unit_kind, regulatory) VALUES
 ('equity_incl_nci', 'Eigenkapital einschließlich Minderheitsanteilen laut Bilanz', 'instant', 'money', false),
 ('net_income_incl_nci', 'Periodenergebnis einschließlich Minderheitsanteilen laut GuV', 'duration', 'money', false)
ON CONFLICT (code) DO NOTHING;
