# Mappingkatalog

Version `de-zeitreihe-v1` (Deutschland) und `sec-v1` (USA). Neue Kennzahlen erst nach fachlichem Fixture und Stichprobe gegen den Originalbericht aufnehmen; Änderungen am Mapping bekommen eine neue Versionsnummer, alte Fakten bleiben erhalten.

| metric.code | Bedeutung | Deutschland (Spalte kennzahl in zeitreihe_lang.csv) | USA (Companyfacts) | Status USA |
|---|---|---|---|---|
| assets | Bilanzsumme | bilanzsumme (HGB, Einzel) | us-gaap:Assets, USD | geprüft (ADTRAN, 3 Werte) |
| equity | Eigenkapital | eigenkapital | us-gaap:StockholdersEquity (Abgrenzung mit/ohne Minderheiten noch klären) | geplant |
| revenue | Umsatz (nicht für Banken) | – | us-gaap:Revenues bzw. RevenueFromContractWithCustomerExcludingAssessedTax (mehrere Tags, Fixture nötig) | geplant |
| net_income | Jahresüberschuss | jahresueberschuss (Beginn 1.1. nur bei Stichtag 31.12.) | us-gaap:NetIncomeLoss | geplant |
| operating_cash_flow | operativer Cashflow | – | us-gaap:NetCashProvidedByUsedInOperatingActivities | geplant |
| employees | Mitarbeiter | – | dei/us-gaap-Tag uneinheitlich, oft nur Text | offen |
| cet1_capital, t1_capital, own_funds, rwa | aufsichtliche Kapitalgrößen | cet1, t1, eigenmittel, rwa (aufsichtlich) | nicht in Companyfacts | andere Quelle nötig |
| cet1_ratio, t1_ratio, total_capital_ratio, total_capital_requirement | Quoten (Dezimalquote) | cet1_quote, t1_quote, gk_quote, gk_anforderung | – | – |
| leverage_ratio, leverage_exposure, lcr, nsfr, hqla | Verschuldung/Liquidität | gleichnamig | – | – |
| de_fonds_340g | Fonds für allgemeine Bankrisiken, § 340g HGB | fonds_340g | – | nur Deutschland |

Regeln: Konsolidierung `regulatory` für Pillar-3-/EBA-Werte, `solo` für HGB-Einzel, `unknown` solange nicht belegt. Prüfstatus der Zeitreihe: `geparst` → `raw`, alle übrigen (`verankert`, `plausibilisiert`, `manuell bestätigt`) → `validated`; der Originalstatus steht in `provenance`.
