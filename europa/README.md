# Europäisches Tabellenuniversum und Jahresabschlüsse

Das Universum umfasst die 702 unterschiedlichen Unternehmen der Geschäftsberichte-Tabelle
vom 28.10.2026: die bisherigen DAX-/MDAX-/SDAX-/TecDAX-Namen einschließlich gekennzeichneter
Vorlagennamen und die 600 Unternehmen der dokumentierten STOXX-Europe-600-Liste.
70 Überschneidungen sind zusammengeführt. Jede Zeile verweist auf genau eine dauerhafte
ID in `stammdaten/unternehmen_ids.csv`; vorhandene IDs werden weiterverwendet.

`unternehmen.json` enthält Indexkennzeichen, Länderklassifikation, offizielle Archiv-/Fundstellen
und den ausdrücklich begrenzten Recherchestatus. STOXX-Land bedeutet Indexklassifikation,
nicht zwingend rechtlicher Sitz. Die 600er-Liste wurde aus der offiziellen Komponentenliste
und dem September-Review rekonstruiert; außerplanmäßige Tagesänderungen bis 28.10.2026 sind
nicht vollständig bestätigt. Quellen: https://stoxx.com/index/sxxp/?components=true und
https://www.iss-stoxx.com/press-releases/stoxx-europe-600-index-composition-changes-4/.

## Abschlussdaten

`abrufen.py` verwendet zuerst die bereits vorhandenen, ISIN-bezogenen Yahoo-Rohdaten im
Repository. `--fetch` ergänzt öffentliche Jahresabschlussdaten über den vorhandenen
Anbieter yfinance/Yahoo. Ticker aus der Bestandsregistrierung bzw. der ergänzenden
Wikipedia-Liste sind Suchkandidaten. Beim neuen Onlineabruf muss der Unternehmensname
zur Anbieteridentität passen; eine ungeklärte Zuordnung bleibt offen.

```sh
pip install 'yfinance>=0.2.65,<1'
python europa/abrufen.py --fetch
python -m unittest discover -s europa -p 'test_*.py'
python app/build.py
```

Gespeichert werden sämtliche gelieferten jährlichen Bilanz- und GuV-Posten, nicht nur
eine Auswahl von Standardkennzahlen. Abschlussstichtag, Originalbezeichnung, unskalierter
Wert, Berichtswährung, Anbieteridentität, Abrufzeit und Quellen-URL bleiben erhalten.
Jahre 2025 und 2024 haben Priorität; ältere verfügbare Jahre ab 2010 werden mitgeführt.
Bei abweichenden Geschäftsjahren entscheidet das Endjahr des Abschlussstichtags.
Keine TTM-, Quartals-, Prognose- oder zukünftigen Jahresdaten. Fehlende Werte werden
nicht als Null gespeichert; tatsächlich gemeldete Nullwerte bleiben erhalten.

**Die Daten sind eine Sekundärquelle und nicht vollständig am Originalabschluss geprüft.**
Die vollständige Lieferung des Anbieters ist kein Nachweis, dass jeder im Originalbericht
enthaltene Bilanz-/GuV-Posten abgedeckt ist. Fehler oder fehlende Anbieterabdeckung werden
je Unternehmen in `daten/status_*.json` erfasst. Neu gegründete oder abgespaltene Gesellschaften
können keine eigenständigen Abschlüsse für 2024/2025 haben.

Die Originalposten werden im Profil mit ihren Währungen angezeigt. Die bestehenden
Vergleichsfelder in Mio. EUR erhalten nur EUR-Werte und überschreiben keine vorhandene
Rechnungslegungsbasis. CHF/GBP/USD werden nicht stillschweigend in EUR umgerechnet.
EPS und Aktienanzahlen behalten ihre im Postennamen ausgewiesene Bedeutung.

`ergaenzungen/` enthält gezielte Übertragungen aus Geschäftsberichten für Lücken des
Anbieters, mit Quellen-URL, gedruckten Seiten und rechnerischer Kontrolle der Bilanzsummen.
Diese ersetzen nur die jeweilige Tabelle/Periode. Beispielsweise bleibt Smiths' GuV aus
der Anbieterquelle erhalten, während die fehlende Bilanz aus einer zugänglichen Berichtskopie
ergänzt wird. Quelle und Prüfstatus stehen **je Jahr und Tabelle** im Profil.
Zegonas Bericht 2025 umfasst 15 Monate (01.01.2024–31.03.2025); ein eigenständiger
Jahresabschluss 2024 wird nicht erfunden. Octaves 2024/2025-Daten sind kombinierte Abschlüsse
des damaligen Hexagon-Geschäfts, keine eigenständigen Abschlüsse des späteren Emittenten.

## Oberfläche und Aktualisierung

Der gemeinsame Länderfilter bleibt beim Reiterwechsel erhalten und filtert Unternehmen,
Branchen, Vergleiche, Bankansichten, Termine, Abschlussabdeckung und Korrelationsdaten.
VWL-Ansichten verwenden dieselbe geografische Auswahl; nicht vorhandene Länder liefern
keine Daten. „Alle Länder“ stellt das gesamte Universum wieder her.
Die Auswahl wird lokal im Browser gespeichert, ohne Serverübertragung.

Der Reiter **Bilanz & GuV** zeigt für jedes Tabellenunternehmen die Anzahl gelieferter
Posten 2025/2024, ältere Jahre und den Prüfstatus. Das Profil enthält die vollständigen
gelieferten Posten als Tabellen mit CSV-Export und Quellenlinks.

Der Workflow `europa.yml` führt den Abruf in vier Partitionen aus, mit höchstens zwei
gleichzeitigen Läufen, und speichert Rohdaten und offene Fälle auf dem Arbeitsbranch.
Er ist zusätzlich manuell ausführbar. Die Ergebnisse werden erst nach einem gesonderten
Terminal-Build in die eingebettete HTML-Fassung übernommen.
