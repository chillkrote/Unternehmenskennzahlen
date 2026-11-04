# Anreicherung in Zehnerblöcken

`skripte/batch_anreichern.py` arbeitet die Tabelle in der Reihenfolge der Tabellenzeilen ab, je Aufruf 10 Unternehmen. `stand.csv` hält je Unternehmen fest, was passiert ist (Block, ergänzte Stammdaten, Zahl der Kennzahlen, Quelle, Notizen). Unternehmen ohne Daten stehen mit Grund im Stand und werden übersprungen.

* Stammdaten (nur leere Felder, Vermerk "bitte prüfen" in der Beschreibung): LEI, Sitz, Handelsregisternummer aus GLEIF, Rechtsform aus dem Namen.
* Kennzahlen nach `import/daten/<ID>.json` (Format der Importvorlage, 10 Jahre sind bei Yahoo nicht abrufbar, es kommen 4 bis 5 Berichtsjahre): Bilanz, GuV, Cashflow, je Aktie. Quelle ist Yahoo Finance (fundamentals-timeseries, frei, Sekundärquelle). Die Rechnungslegung gibt Yahoo nicht an, sie steht als "Sonstige".
* Geschäftsbericht: Wird ein Bericht gefunden (Quellen-Dokumente oder PDF-Link auf der IR-Seite), wird geprüft, ob die Werte des letzten Jahres dort stehen. Treffer bekommen Quelle = Bericht und die Seite. Nicht abgeglichen heißt: Yahoo.
* Nicht automatisch belegbar und deshalb leer: WZ/NACE-Code, Branche (bleibt Platzhalter), Website.
