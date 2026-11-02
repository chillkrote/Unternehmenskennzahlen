# Mappingkatalog

Version `de-zeitreihe-v1` (Deutschland) und `sec-v2` (USA). Neue Kennzahlen erst nach fachlichem Fixture und Stichprobe gegen den Originalbericht aufnehmen; Änderungen am Mapping bekommen eine neue Versionsnummer, alte Fakten bleiben erhalten.

| metric.code | Bedeutung | Deutschland (Spalte kennzahl in zeitreihe_lang.csv) | USA (Companyfacts) | Status USA |
|---|---|---|---|---|
| assets | Bilanzsumme | bilanzsumme (HGB, Einzel) | us-gaap:Assets, USD | geprüft (10 Unternehmen) |
| equity | Eigenkapital der Muttergesellschafter | eigenkapital | us-gaap:StockholdersEquity | geprüft; fehlt bei Caterpillar und Johnson & Johnson, ADTRAN nur bis 2021 (diese Unternehmen nutzen den Tag mit Minderheitsanteilen) |
| equity_incl_nci | Eigenkapital inkl. Minderheitsanteilen | – | us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest | geprüft |
| revenue | Umsatz (nicht für Banken) | – | erster vorhandener Tag je Filing: RevenueFromContractWithCustomerExcludingAssessedTax, Revenues, SalesRevenueNet, SalesRevenueGoodsNet | geprüft; Umsatz ist je Unternehmen der ausgewiesene Umsatz (z. B. Walmart: Net sales, nicht Total revenues) |
| net_income | Jahresüberschuss (Anteil der Muttergesellschafter) | jahresueberschuss (Beginn 1.1. nur bei Stichtag 31.12.) | us-gaap:NetIncomeLoss | geprüft; Caterpillar nur bis 2010 (dort ProfitLoss) |
| net_income_incl_nci | Periodenergebnis inkl. Minderheitsanteilen | – | us-gaap:ProfitLoss | geprüft; bei JPMorgan/J&J nur teilweise vorhanden |
| operating_cash_flow | operativer Cashflow | – | us-gaap:NetCashProvidedByUsedInOperatingActivities (Fallback …ContinuingOperations) | geprüft |
| employees | Mitarbeiter | – | in Companyfacts uneinheitlich (kein verlässliches Tag) | offen |
| cet1_capital, t1_capital, own_funds, rwa | aufsichtliche Kapitalgrößen | cet1, t1, eigenmittel, rwa (aufsichtlich) | nicht in Companyfacts | andere Quelle nötig |
| cet1_ratio, t1_ratio, total_capital_ratio, total_capital_requirement | Quoten (Dezimalquote) | cet1_quote, t1_quote, gk_quote, gk_anforderung | – | – |
| leverage_ratio, leverage_exposure, lcr, nsfr, hqla | Verschuldung/Liquidität | gleichnamig | – | – |
| de_fonds_340g | Fonds für allgemeine Bankrisiken, § 340g HGB | fonds_340g | – | nur Deutschland |

Regeln: Konsolidierung `regulatory` für Pillar-3-/EBA-Werte, `solo` für HGB-Einzel, `unknown` solange nicht belegt. Prüfstatus der Zeitreihe: `geparst` → `raw`, alle übrigen (`verankert`, `plausibilisiert`, `manuell bestätigt`) → `validated`; der Originalstatus steht in `provenance`.

## ESEF (Frankreich, Niederlande, Italien, Spanien), Version `esef-v1`

Quelle: xBRL-JSON der ESEF-Einreichung, nur Fakten ohne zusätzliche Dimensionen, nur Währungseinheiten. Rangfolge der Konzepte je Einreichung und Periode (nie gemischt):

| metric.code | IFRS-Konzept |
|---|---|
| assets | ifrs-full:Assets |
| equity | ifrs-full:EquityAttributableToOwnersOfParent |
| equity_incl_nci | ifrs-full:Equity |
| revenue | ifrs-full:Revenue, sonst ifrs-full:RevenueFromContractsWithCustomers (für Banken nicht geladen; Sanofi nutzt ein Erweiterungskonzept und bleibt leer) |
| net_income | ifrs-full:ProfitLossAttributableToOwnersOfParent |
| net_income_incl_nci | ifrs-full:ProfitLoss |
| operating_cash_flow | ifrs-full:CashFlowsFromUsedInOperatingActivities |

Mitarbeiter und aufsichtliche Kennzahlen: nicht in den Primärrechnungen getaggt, bleiben leer.
