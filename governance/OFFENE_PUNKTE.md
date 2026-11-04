# Offene Punkte und Probleme der Governance-Erhebung

Stand 02.11.2026. Diese Liste wird bei jedem Block fortgeschrieben. Sie ist so geordnet, dass oben steht, was die Aussagekraft der Daten am stärksten einschränkt.

## 1. Datenlücken in bereits erfassten Unternehmen

| Unternehmen | Was fehlt | Weg zur Lösung |
|---|---|---|
| Volkswagen | Namensliste des Aufsichtsrats (20 Personen, Zuordnung Arbeitnehmer/Gewerkschaft); im Vergütungsbericht stehen nur die Mitglieder mit Veränderungsraten | Abschnitt Gremien im Geschäftsbericht auswerten |
| Continental | Aufsichtsrat nur als Namens- und Vergütungsliste (25 Namen inkl. Ausgeschiedene); Vertreterart, Frauen, Zahl der Gewerkschaftsvertreter fehlen. Vorstand: Zahl der Frauen nicht erfasst | englischen Geschäftsbericht (Corporate Governance) auswerten |
| Deutsche Börse | Aufsichtsrat: Zuordnung Anteilseigner/Arbeitnehmer und Frauenzahl der Arbeitnehmerseite; zweite Frau im Vorstand nicht namentlich belegt | Gremienübersicht im Geschäftsbericht |
| Zalando | Arbeitnehmervertreter aus Bildunterschrift abgeleitet (Östberg, Sloan, Laskowski, Reynolds); Gewerkschaftsvertreter nicht ausgewertet; Pay Ratio nur Veränderungsraten | Gremienübersicht prüfen |
| MTU | Aufsichtsrat: Rollen (Vorsitz, Anteilseigner/Arbeitnehmer) nicht eindeutig | Gremienübersicht prüfen |
| Telekom | Zahl der Frauen im Vorstand nicht genannt, Aufsichtsrat Zuordnungen teilweise offen | Geschäftsbericht S. 219 ff. |
| Siemens Energy | Zahl der Frauen im Vorstand nicht genannt | Geschäftsbericht S. 234 ff. |
| Rheinmetall, RWE, BASF, adidas, Beiersdorf, Henkel | Lebensläufe und Mandatslisten nur, soweit im Bericht; Gewerkschaftsvertreter teils aus Berufsangabe abgeleitet | Prüfung gegen Websites der Unternehmen |
| alle | `werdegang` (Lebenslauf) nur für wenige Personen befüllt (130 Zeilen bei 377 Personen) | je Person Unternehmenswebsite und Lebenslaufseite im Bericht |

## 2. Methodische Probleme

* **Pay Ratio nicht vergleichbar:** Variante A (Beschäftigte Deutschland) und Variante B (Konzern) haben unterschiedliche Nenner. Beschäftigtenzahlen sind teils Köpfe, teils FTE, teils Durchschnitt, teils Stichtag. Nur Werte gleicher Variante vergleichen.
* **Zähler uneinheitlich:** § 162-Vergütung „gewährt und geschuldet“ bei fast allen, „erdient“ bei der Telekom. Bei Continental enthält der CEO-Wert eine Abfindung von 4,8 Mio. €, bei Zalando LTI-Auszahlungen, bei VW 50 % der Vorstandsvorsitzenden-Vergütung zusätzlich über Porsche.
* **Ganzjährige Mitglieder:** Fehlt das Eintrittsdatum, gilt ein Mitglied als ganzjährig. Das ist nicht überall belegt (Beiersdorf: niedrige Werte bei Barckhahn und Lafrentz ungeprüft, Kapitalbausteine/Umwandlungen).
* **Gender Pay Gap im Vorstand:** Gruppen von 1 bis 7 Personen, Ressorts und Aktienkomponenten nicht kontrolliert. Geschlecht nur aus Dokumenten (Anrede, Geschlechtsangabe in Tabellen, Possessivpronomen). Bei Rheinmetall, Telekom, Siemens Energy, Continental, Deutsche Börse nicht berechenbar.
* **Keine Median-Pay-Ratio:** Mediane sind nur selten veröffentlicht (Deutsche Börse 97,0, Beiersdorf 125,83, Rheinmetall 144,5, jeweils andere Definition).
* **Geschäftsjahre:** Siemens Energy (Okt–Sep) und adidas/andere mit abweichenden Stichtagen sind als GJ 2025 geführt.
* **Zehn Jahre Historie fehlen vollständig:** Es liegt nur GJ 2025 vor. Für Zeitreihen und Karriereverläufe braucht es Berichte 2016–2024 (Vergütungsberichte erst ab 2021 mit vergleichender Darstellung).

## 3. Technische Punkte

* **Dokumente im Repo:** Berichte liegen als PDF direkt im Repo (pro Unternehmen 5–20 MB); das Repo wächst um rund 10–20 MB je Unternehmen. Bei mehreren Hundert Unternehmen Speicherbedarf und Klonzeit prüfen (Git LFS wurde auf Wunsch nicht genutzt).
* **Sparse Checkout:** Die Sitzungen klonen ohne PDFs; Dokumente müssen mit `git show origin/main:<pfad>` gelesen werden.
* **Tabellenerkennung:** Mehrspaltige Vergütungstabellen werden per Text-Extraktion gelesen; Zuordnung Name zu Spalte läuft über Reihenfolge und Eintrittsdaten und ist stichprobenartig geprüft, aber nicht doppelt kontrolliert.
* **Quellen für Dokumente:** SAP-Website blockt automatische Abrufe (Bot-Schutz, nicht umgangen); Vergütungsberichte liegen bei manchen Unternehmen separat, bei anderen im Geschäftsbericht.
* **Skripte:** `build.py` erzeugt alle CSV neu; Änderungen an `lib.py` (z. B. `slug`) erfordern Neuaufbau statt Merge der CSV. Personenverweise werden geprüft, Dubletten bei abweichenden Namensschreibweisen nicht automatisch erkannt.
* **Terminal-Anbindung:** Die Spalten (Vorstand, Aufsichtsrat, Pay Ratio, Frauenquote, Mitbestimmung) sind noch nicht in die Profilseiten des Bank-Terminals eingebunden (Abstimmung mit dem Terminal-Thread steht aus).

## 4. Umfang, der noch fehlt

* Übrige DAX-Unternehmen (ca. 25), MDAX und SDAX.
* Große Banken außer Commerzbank, Deutsche Bank, HypoVereinsbank (Aareal, apoBank, Hamburg Commercial Bank, Münchener Hyp, VW Bank, pbb, Haspa u. a.). Bei kleinen Banken ohne Veröffentlichungspflicht (z. B. Sparkassen): leer lassen oder kennzeichnen.
* Nicht-deutsche Unternehmen des Terminals (OECD-Erweiterung): andere Berichtspflichten, andere Quellen.

## 5. Rechtliches und Datenschutz

* Erfasst werden nur beruflich relevante, veröffentlichte Angaben (Name, Funktion, Vergütung nach § 162 AktG, Mandate). Kein Wohnort, keine Familie. In einigen Berichten stehen Geburtsdatum und Wohnort; sie werden bewusst nicht übernommen.
* Personenprofile über die Zeit verknüpfen mehrere Unternehmen; vor einer Veröffentlichung außerhalb des Repos klären, ob eine Prüfung nach DSGVO nötig ist.

## Block 2 (Stand 02.11.2026)
- Erfasst: Allianz SE (U000036), Munich Re (U000420). Allianz: Pay Ratio nach Variante A gerechnet; Frauen im Vorstand (4 von 9) nur als Zahl, Namen im Bericht nicht ausdrücklich als Frauen ausgewiesen, daher keine Gender-Gap-Rechnung.
- Munich Re: Vergütungsbericht liegt separat auf munichre.com (Download per curl möglich), enthält keine Absolutwerte der Ø-Belegschaftsvergütung, daher keine Pay Ratio nach Variante A.
- Nicht erfasst (Vergütungsbericht nur auf Seiten mit Bot-Schutz oder gesperrten Hosts, nicht umgangen): E.ON (eon.com 403), Infineon (infineon.com/eqs 202/503), Mercedes-Benz (403), Bayer (403).
- Block 2b (03.11.2026): BMW (U000067) und Siemens (U000535) aus den Vergütungsberichten (Download per curl, bmwgroup.com bzw. assets.new.siemens.com) erfasst, beide mit Pay Ratio Variante A. BMW: Arbeitnehmervertreter nur teilweise erkennbar (Böckler-Fußnote), Frauenzahlen im Vorstand/AR nicht im Vergütungsbericht (Geschäftsbericht fehlt noch); Gender Gap BMW nur mit Horstmeier als einziger dokumentierter Frau. Siemens: Geschlecht der Vorstände nicht belegt, daher kein Gap; Geschäftsjahr endet 30.9.
- Block 2c (04.11.2026): SAP (U000515) und Commerzbank (U000124) aus den Vergütungsberichten (Download ir-api.eqs.com per curl) erfasst. SAP: Ø-Vergütung ist Konzernwert (nicht nur Deutschland), Arbeitnehmerseite im Aufsichtsrat nicht ausgewiesen, Geschlechter der Vorstände nicht belegt. Commerzbank: Vorstand/Aufsichtsrat-Stammdaten kommen aus dem Jahresabschluss-Pilot (Schreibweisen Bernhard Spalt, Christiane Vorspel-Rüter beibehalten), nur Vergütung neu; Frauenzahlen noch aus der Corporate-Governance-Erklärung nachzutragen.
- Deutsche Bank (U000148), 04.11.2026: Vergütung aus dem Geschäftsbericht 2025 (Link von Robin: investor-relations.db.com, Download per curl möglich) erfasst; Ø-Vergütung ist Konzernwert weltweit (120.974 €), Pay Ratio daher nicht mit Deutschland-Werten vergleichbar. Namen der zwei Vorständinnen nicht belegt.
