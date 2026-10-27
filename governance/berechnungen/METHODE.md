# Pay Ratio und Gender Pay Gap im Vorstand: Methode

Stand 27.10.2026, Geschäftsjahr 2025. Skript: `governance/skripte/berechnung.py`, Ergebnisse: `pay_ratio.csv`, `gender_pay_gap_vorstand.csv`, `geschlecht_belege.csv` in diesem Ordner.

## Grundlage: Studien der Hans-Böckler-Stiftung

* Marion Weckes (I.M.U.): *Manager to Worker Pay Ratio 2017. Das Verhältnis der Vorstandsvergütung zur Mitarbeitervergütung im DAX 30*, Mitbestimmungsreport Nr. 44, Juli 2018 (https://www.econstor.eu/bitstream/10419/180399/1/1026665167.pdf). Pay Ratio = Vorstandsvergütung ÷ (Konzernpersonalaufwand, bereinigt um die Vorstandsvergütung, je Konzernbeschäftigtem). Getrennt für den Vorsitzenden (CEO) und den Durchschnitt der übrigen ordentlichen Vorstandsmitglieder; unterjährige Ein- und Austritte werden über Beschäftigungsmonate gewichtet. Ergebnis 2017: Ø 71, CEO Ø 97, Median 68.
* Armeli/Schmid: *Pay ratio in DAX und MDAX*, Mitbestimmungsreport Nr. 85, Oktober 2025 (https://www.econstor.eu/bitstream/10419/331229/1/1939895847.pdf). Seit 2021 liefert die vergleichende Darstellung nach § 162 Abs. 1 Satz 2 Nr. 2 AktG die Ø-Vergütung der Beschäftigten (Vollzeitäquivalente); die Studie empfiehlt absolute Beträge, Ausweis für Deutschland und Gesamtbelegschaft sowie den Median. Ergebnis GJ 2023 DAX: CEO 17- bis 102-fach (Median 55), Vorstands-Ø 12- bis 71-fach (Median 28).

## Zwei Varianten der Pay Ratio

* **Variante A (bevorzugt, wo verfügbar):** Zähler = gewährte und geschuldete Vergütung nach § 162 AktG; Nenner = Ø-Jahresvergütung der Beschäftigten in Deutschland (FTE) aus der vergleichenden Darstellung. Das ist die Logik des Reports Nr. 85.
* **Variante B (Konzern, Methode Report Nr. 44):** Nenner = (Konzernpersonalaufwand − Summe Vorstandsvergütung) ÷ Konzernbeschäftigte. Wird für alle Unternehmen gerechnet, bei denen Personalaufwand und Beschäftigtenzahl im Geschäftsbericht stehen. Diese Quote ist durch Auslandsbelegschaften meist niedriger im Nenner und damit höher als Variante A.
* Beide Varianten stehen nebeneinander, weil die Nenner nicht vergleichbar sind. Nur Varianten gleicher Art zwischen Unternehmen vergleichen.
* Unternehmensselbst ausgewiesene Quoten (Beiersdorf 125,83; Rheinmetall 144,5) stehen als Abgleich in der Datei, sie sind anders definiert.

## Abweichungen von der Böckler-Methode (bewusst)

* Zähler ist die **gewährte und geschuldete Vergütung nach § 162 AktG**, Böckler 2018 nutzte die Zuflusstabelle des DCGK 2017 (nicht mehr verfügbar). Telekom weist die „erdiente“ Vergütung aus, die nicht vollständig deckungsgleich ist.
* Statt Gewichtung nach Beschäftigungsmonaten gehen nur **ganzjährig amtierende Mitglieder** in den Vorstands-Durchschnitt ein (Mitglied ohne `bis` und ohne Eintritt 2025). Ein Eintritt vor dem Berichtsjahr gilt auch dann als ganzjährig, wenn das Eintrittsdatum in den Daten fehlt; das ist nicht überall belegt. Ist der Vorsitzende im Jahr gewechselt (MTU), wird keine CEO-Quote berechnet.
* Beschäftigtenzahlen sind uneinheitlich (Ø-Köpfe, Stichtags-Köpfe, FTE; Basis steht je Zeile in `nenner_basis`). Beiersdorf weist ab 2025 nur noch Headcount aus.
* Die Quoten werden nicht auf den Median umgestellt, weil Medianwerte nur selten veröffentlicht sind.

## Gender Pay Gap im Vorstand

Zu Vorstandsvergütung nach Geschlecht fand sich **keine Böckler-Studie**; die HBS/WSI-Veröffentlichungen zum Gender Pay Gap betreffen die Gesamtwirtschaft. Es wird daher die dort und bei Destatis/Eurostat verwendete **unbereinigte Definition** auf den Vorstand übertragen: `(Ø Männer − Ø Frauen) ÷ Ø Männer`, jeweils auf Basis der gewährten und geschuldeten Vergütung ganzjährig amtierender Mitglieder. Positive Werte bedeuten, dass Frauen im Schnitt weniger erhalten.

Grenzen: Fallzahlen von 1 bis 5 Personen je Gruppe, Ressortunterschiede (CEO, CFO, Personal), Sonderzahlungen und Aktienkomponenten werden nicht kontrolliert, daher keine Aussage über Ungleichbehandlung. Das Geschlecht wird **nie aus dem Vornamen abgeleitet**, sondern nur aus einer im Dokument genannten Angabe (siehe `geschlecht_belege.csv` mit Seite). Unternehmen ohne dokumentierte Frau mit Vollzeitjahr sind nicht berechenbar (z. B. Rheinmetall, Telekom, Siemens Energy).

## Offene Punkte

* Weitere DAX/MDAX-Unternehmen und Banken folgen, sobald deren Berichte erfasst sind.
* Mehrjahresreihen (10 Jahre) sind noch nicht gerechnet; dafür fehlen die Altberichte.
