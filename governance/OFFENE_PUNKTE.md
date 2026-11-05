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

## Block 3 (Vonovia, Heidelberg Materials, Fresenius)
- Vonovia (U000716): Ø 75,1 T€ ist Gesamtvergütung der Immobilienwirtschaft-Belegschaft konzernweit (FTE); Frauen im Vorstand/AR und Arbeitnehmerseite im AR nicht erhoben (Vergütungsbericht weist Geschlecht/Bank nicht aus).
- Heidelberg Materials (U000274): Vorstands-Gesamtvergütung enthält IAS-19-Dienstzeitaufwand, Ø-Vergütung (85 T€) nur Muttergesellschaft, Direktvergütung; Pay Ratio daher nur eingeschränkt vergleichbar. Frauenzahlen und AR-Zusammensetzung offen (Geschäftsbericht).
- Fresenius (U000234): Vergütungsbericht im Geschäftsbericht; Vorstand der Fresenius Management SE; AR-Gesamtvergütung gilt für KGaA und Management SE zusammen; Ø 53 T€ Konzern weltweit; Frauenzahlen/Mitbestimmung offen.
- Hannover Rück (U000264): Bericht per curl 403, PDF fehlt.

## Block 4 (Hannover Rück, E.ON, Infineon, Bayer, Mercedes-Benz) – Berichte von Robin bereitgestellt (05.11.2026)
- Hannover Rück (U000264): Ø 126,2 T€ nur Hannover Rück SE Deutschland. Der "Vorstandsvorsitzende" in der Pay Ratio ist Jungsthöfel (Vorsitz erst seit 1.4.2025, Henchoz bis 31.3. ausgeschieden). Frau Magee dokumentiert ("Eintritt von Frau Magee"); übrige Geschlechter offen. 3 Arbeitnehmervertreter (Fußnote), AR-Gesamtzahl 9.
- E.ON (U000195): Ø 84 T€ ist regelmäßige Zielvergütung (nicht gewährte Ist-Vergütung) der Arbeitnehmer in Deutschland. Frauenzahlen, Arbeitnehmerseite im AR offen (Geschäftsbericht liegt im Repo: boersennotierte-unternehmen/energie-versorger/dokumente/e-on-se/EON_GB25.pdf).
- Infineon (U000301): Geschäftsjahr Okt–Sep. Bericht nennt keine absolute Ø-Mitarbeitervergütung, nur Prozentänderungen -> Pay Ratio Variante A nicht berechenbar; Variante B aus Annual Report (liegt im Repo) offen. Geschlecht/Arbeitnehmerseite offen.
- Bayer (U000065): Ø 122 T€ Deutschland (Tarif- und Gesamtbelegschaft ausgewählter Gesellschaften). Heike Prinz/Hausfeld: Geschlecht nicht aus Vornamen abgeleitet. Arbeitnehmerseite im AR im Bericht nicht gekennzeichnet.
- Mercedes-Benz Group (U000395): Vergütungsbericht 2025 nachgeliefert und erfasst (12 Vorstände, 20 AR-Mitglieder; Seiten = PDF-Seiten). Er nennt keine absolute Ø-Mitarbeitervergütung -> Variante A nicht berechenbar, nur publizierte Pay Ratio 135:1 (Geschäftsbericht, Textfassung, Seiten ±1; anderes Konzept). Für vier ausgeschiedene Vorstände weichen Individualtabelle und vergleichende Darstellung ab (Individualtabelle verwendet). Geschäftsbericht als PDF wäre sauberer als Quelle.

## Block 5 (Porsche SE, GEA, Sartorius, Siemens Healthineers, Daimler Truck, DHL) – 05.11.2026
- Porsche SE (U000479), GEA (U000242), Sartorius (U000516): Berichte enthalten nur prozentuale Veränderungen/Index der Ø-Mitarbeitervergütung -> Variante A nicht berechenbar (GEA publiziert Verhältnis 85,2; Variante B aus Geschäftsbericht offen). GEA: AR-Seite und Frauenzahlen offen. Sartorius: Arbeitnehmervertreter nur für zwei Personen belegt.
- Siemens Healthineers (U000538): GJ Okt-Sep; Pay Ratio Variante A (113 T€ Belegschaft Deutschland). AR: neun Mitglieder mit Böckler-Fußnote als Arbeitnehmer-/Gewerkschaftsvertreter gekennzeichnet, Gesamtzahl der Arbeitnehmerseite nicht ausgewiesen. Frau Caron dokumentiert (Personalvorständin).
- Daimler Truck (U000133): Ø 89,3 T€ ist Personalaufwand je FTE (keine Ist-Vergütung). Frau Rådström dokumentiert (Vorsitzende). AR-Seiten (Anteilseigner/Arbeitnehmer) nicht in der Tabelle.
- DHL (U000165): Ø 50,5 T€ weltweit (Personalaufwand/Beschäftigte, nicht Deutschland). CEO Meyer 2025 gewährt 3.865 T€. Scharwath inkl. 3,4 Mio. € Abgeltung.
- Fresenius Medical Care (U000233): jetzt erfasst (Block 8, Tabellen als Bild gelesen). Pay Ratio 106:1 publiziert; Arbeitnehmerseite im AR nicht ausgewiesen.
- Scout24 (U000524, Block 6): alle sieben AR-Mitglieder von der Hauptversammlung gewählt, keine Arbeitnehmervertreter. Ø 99,6 T€ = Belegschaft der Scout24 SE (nicht Konzern). Weitz war erst ab 1.3.2025 CEO (Summe enthält CPTO-Zeit), daher Pay Ratio nur eingeschränkt vergleichbar. Frauenzahlen offen.
- Merck KGaA (U000396, Block 6): Bericht englisch; Ø 106,5 T€ ist weltweiter Personalaufwand ohne Pensionen je Beschäftigtem. Von Roeder als Frau belegt ("her"). Arbeitnehmerseite im AR nicht ausgewiesen.
- Brenntag (U000100) und Symrise (U000640): jetzt erfasst (Block 8). Brenntag: Ø 129 T€ nur Zentrale; keine Arbeitnehmerseite im AR ausgewiesen; Geschlecht keiner AR-Person dokumentiert. Symrise: nur prozentuale Veränderung der Ø-Vergütung, keine Pay Ratio; 6 Arbeitnehmervertreter belegt; Frau Coßmann (Arbeitsdirektorin) belegt. Qiagen (U000491, niederländisch), Airbus (U000026, niederländisch/§ 162 nicht anwendbar): Vergütungsberichte noch nicht beschafft.

## Block 7 (MDAX: Knorr-Bremse, Hugo Boss, Lufthansa, Rational, Aurubis) – 05.11.2026
- Knorr-Bremse (U000331): Ø 99 T€ Konzern Deutschland (gerundet); 6 Arbeitnehmervertreter belegt (Fußnote). Frauen offen.
- Hugo Boss (U000290): Bericht englisch; absolute Ø-Vergütung 2025 nicht ausgewiesen (nur +2 %), daher keine Pay Ratio. Arbeitnehmerseite im AR nicht ausgewiesen.
- Lufthansa (U000157): Ø 93,1 T€ Gesamtbelegschaft Deutschland; AR 10 Arbeitnehmervertreter laut Beschreibung, namentliche Zuordnung nicht in der Vergütungstabelle. ESRS-Kennzahlen (Gender Pay Gap, Ratio höchstbezahlte Person/Median) im Geschäftsbericht noch nicht übernommen.
- Rational (U000494): nur Veränderung der Ø-Vergütung ausgewiesen, keine Pay Ratio. Arbeitnehmerseite nicht ausgewiesen.
- Aurubis (U000053): GJ Okt-Sep; sechs Arbeitnehmervertreter; Ø-Vergütung Belegschaft in der Vergleichstabelle nicht sauber lesbar, Pay Ratio offen. Frau Hofkens (Vorständin) belegt.
- MDAX noch nicht erfasst, Vergütungsbericht liegt als eigenes Dokument vor (muss beschafft werden): Schaeffler, Hensoldt, Traton, Bilfinger, KION, Fuchs, Lanxess, Salzgitter, Wacker, Bechtle, IONOS, Nemetschek, Elmos, RTL, United Internet, AUTO1, PUMA, Fraport, Aroundtown, flatexDEGIRO, Aumovio, Hella, Jenoptik, thyssenkrupp, TKMS, Evonik, K+S, SUSS, CTS Eventim, freenet.
- MDAX mit Bericht im Geschäftsbericht, noch zu erfassen: Deutz, Renk, Nordex, Aixtron, TUI, DWS, Talanx, Delivery Hero, Siltronic, TAG Immobilien, Krones, Aumovio.

## Block 8 (Brenntag, Symrise, FME, Qiagen, Airbus) – 05.11.2026
- Qiagen (U000491): Bericht nach niederländischem Recht, Beträge in USD (Spalte betrag_tsd_eur bewusst leer, Beträge in Art/Bemerkung). Pay Ratio 87:1 publiziert (Dutch Corporate Governance Code, nicht ESRS/§ 162). Managing Board nur zwei Personen; LTI nur als Stückzahl.
- Airbus (U000026): nur Jahresabschluss (Note 33) vorhanden. CEO-Name steht nicht im Dokument, Eintrag anonym. Beträge sind IFRS-Aufwand, nicht gewährt/geschuldet. Report of the Board of Directors (Abschnitt 2.3.2/2.3.3, dort Pay Ratio) liegt auf airbus.com hinter Bot-Schutz: nicht abgerufen; Robin kann das PDF hochladen.
- Quellen gefunden: Schaeffler (schaeffler.com/.../2025_schaeffler_remuneration_report_de_20nyhn.pdf, aus der Umgebung 403) und Lanxess (lanxess.com/-/media/project/lanxess/corporate-internet/investors/reporting/2025/q4/2025-gb-vergutungsbericht-lxs-web.pdf) stehen für die MDAX-Runde bereit.

## Block 9 (Schaeffler, Lanxess, Deutz) – 05.11.2026
- Schaeffler (U000518, Bericht von Robin hochgeladen): 9 aktive Vorstände, 7 ehemalige plus 4 ehemalige Vitesco-Mitglieder; 27 AR-Mitglieder. Arbeitnehmerseite im AR nicht gekennzeichnet; keine absolute Ø-Vergütung (nur +4 %), keine Pay Ratio. Frau Fontaine (Arbeitsdirektorin) belegt.
- Lanxess (U000363): Ø 82 T€ Deutschland (ohne Vorstand). Sechs Arbeitnehmervertreter nur über den Wahltext belegt (2025 ausgeschiedene/neue), übrige Zuordnung offen. Frau van Baarle und Frau Biermann belegt (Frau/Arbeitsdirektorin).
- Deutz (U000163): nur Veränderung der Belegschaftsvergütung (+7,0 %), keine Pay Ratio. Acht AN-Kennzeichnungen im AR. Geschlecht Frau Dr. Mayer im Bericht nicht belegt, daher kein Eintrag.
- MDAX noch offen mit Bericht im Geschäftsbericht: Renk, Nordex, Aixtron, TUI, DWS, Talanx, Delivery Hero, Siltronic, TAG, Krones, Aumovio. Ohne Vergütungsbericht im Repo: Hensoldt, Traton, Bilfinger, KION, Fuchs, Salzgitter, Wacker, Bechtle, IONOS, Nemetschek, Elmos, RTL, United Internet, AUTO1, PUMA, Fraport, Aroundtown, flatexDEGIRO, Hella, Jenoptik, thyssenkrupp, TKMS, Evonik, K+S, SUSS, CTS Eventim, freenet.
- Renk Group (U000500) erledigt: 4 Vorstände, 12 AR-Mitglieder (6 Arbeitnehmervertreter belegt), Vergütung aus Geschäftsbericht S. 256–257; keine absolute Ø-Vergütung, keine Pay Ratio.
- Nordex (U000442): 2 Vorstände (Blanco, Hartmann) + ausgeschiedener Landa, 6 AR-Mitglieder ohne Arbeitnehmervertreter ausgewiesen. Veröffentlicht: Gender Pay Gap −12,3 % (Frauen verdienen mehr; Management +19,8 % für Männer) und ESRS-Verhältnis Höchstbezahlte/Median 41,6 (nicht Böckler-Methode, daher nicht in pay_ratio.csv). Keine absolute Ø-Vergütung. Geschlecht der AR-Mitglieder (Blanco, Cordón) im Bericht nicht belegt.
- Aixtron (U000028): 2 Vorstände, 6 AR-Mitglieder (+ Schindelhauer bis 15.5.2025), keine Arbeitnehmervertreter ausgewiesen; Frauen Florschütz und Weber belegt. Keine absolute Ø-Vergütung (nur +2 %).
- TUI (U000670, englischer Bericht): 5 Vorstände (Reiss als Frau belegt), 20 AR-Mitglieder inkl. 3 Ausgeschiedene, 10 Arbeitnehmervertreter belegt (Fußnote), Gewerkschaft: nur Thannisch (ver.di) belegt. Keine absolute Ø-Vergütung (nur +2 %). Frauenanteil AR 45 % (30.9.2025) nur als Quote, einzelne Frauen nicht belegt.
- Talanx (U000645): 7 aktive + Henchoz, 16 AR (8 AN belegt, Meister ver.di); Ø 108 T€ Deutschland → Pay Ratio berechnet (Methode A, Personalaufwand-Basis). Geschlecht der Vorstände nicht belegt.
- DWS (U000177): Geschäftsführung der DWS Management GmbH (7 aktiv, 10 ehemalige mit Zuflüssen 2025), AR 12; Pay Ratio mit Ø 146 T€ weltweit. Arbeitnehmervertreter im Bericht nicht gekennzeichnet (Anzahl leer); Geschlechter nicht belegt.
- Delivery Hero (U000143): 3 Vorstände 2025 (Popp als Frau belegt), Bruder erst ab 1.1.2026; AR 10 (4 AN belegt, Skogen Lund Vorsitzende = Frau). Vorstandsvergütung nur Grundgehalt (variabel 0), keine absolute Ø-Vergütung.
- Siltronic (U000539): 3 Vorstände, 12 AR; 5 Arbeitnehmer-/Gewerkschaftsvertreter laut Fußnote + 1 leitender Angestellter; Pay Ratio mit Ø 74 T€ Deutschland berechnet. Geschlechter nicht belegt.
- TAG Immobilien (U000643): 2 Co-CEOs, 6 AR ohne Arbeitnehmervertreter; veröffentlicht Gender Pay Gap 7,3 % und Höchstbezahlte/Median 25,2 (nur Kennzahlen). Keine Ø-Vergütung.
- Aumovio (U000052): Rumpfjahr nach Abspaltung (Vorstand ab 15.8./17.9.2025, AR ab 3.9.2025), Beträge anteilig; 8 AN + 8 Anteilseigner im AR, 6 Frauen im AR belegt; Ø 98 T€ Deutschland ausgewiesen, aber keine Pay Ratio (Vorstand nicht ganzjährig).
- Krones (U000349): Geschäftsbericht (englisch) enthält keinen Vergütungsbericht, nur Verweis → separat zu suchen (Block „ohne Vergütungsbericht“).
- Delivery Hero: Popp mit Jahresmarker „2025“ als Eintritt (Datum nicht genannt), damit kein Gender Gap im Vorstand gerechnet wird.
- MDAX mit Bericht im Geschäftsbericht damit abgearbeitet; offen bleiben die Unternehmen ohne Vergütungsbericht im Repo (Liste Block 9, plus Krones).
- KION (U000328): Vergütungsbericht 2025 direkt von kiongroup.com (Shareholders-Meeting/2026/2025-Q4_Vergütungsbericht_KION-Group.pdf) geladen: 6 Vorstände, 20 vergütete AR-Mitglieder; Arbeitnehmervertreter nicht gekennzeichnet; keine absolute Ø-Vergütung. Hensoldt: im Web nur Jahresabschluss-PDF gefunden, Geschäftsbericht mit Vergütungsbericht (S. 240) noch zu finden. Krones: Bericht unter krones.com/hauptversammlung2026 (Seite nicht per Suche direkt erreichbar).
- Bechtle (U000071): Vergütungsbericht direkt von bechtle.com; 4 Vorstände + Schäfer (ehem.), 16 AR (8 AN); Ø 66 T€ → Pay Ratio berechnet (CEO 89:1). Bilfinger: HV-Einladung (Bilfinger_TO26.pdf) enthält keinen Berichtstext, Bericht weiterhin zu suchen. Fuchs/Wacker: Berichte nur auf der HV-Seite der Unternehmen, per Suche nicht direkt erreichbar.
- Krones (U000349), Wacker (U000727), Fuchs (U000238): Vergütungsberichte 2025 direkt von den HV-/Vergütungssysteme-Seiten geladen. Krones: 5 Vorstände, 16 AR (8 AN), Ø 87 T€ → Pay Ratio. Wacker: 4 Vorstände, 16 AR, keine absolute Ø-Vergütung. Fuchs: 7 Vorstände (2 Wechsel), 7 AR, ESRS-Gender-Pay-Gap 11 % und Ratio 61 aus Geschäftsbericht S. 191.
- Bilfinger und Hensoldt weiterhin offen: Bilfinger-Seite nicht erreichbar, bei Hensoldt nur Jahresabschluss gefunden (Geschäftsbericht mit Vergütungsbericht ab S. 240 fehlt).
