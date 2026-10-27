from lib import *
G = ('governance/dokumente/rwe-aktiengesellschaft/geschaeftsbericht-2025.pdf', 'U000510')
R = ('governance/dokumente/rwe-aktiengesellschaft/verguetungsbericht-2025.pdf', 'U000510')
uni('Deutsche Telekom AG','U000161'); uni('Henkel AG & Co.KGaA','U000279'); uni('BASF SE','U000061'); uni('Lanxess AG','U000363')
uni('Siemens AG','U000535'); uni('Dr. Ing. h. c. F. Porsche AG','U000175'); uni('Fraport AG','U000230')
for n,f,t,sp,bis in [('Dr. Markus Krebber','Vorsitzender (CEO)',7001,25,''),('Dr. Michael Müller','Mitglied',3538,25,''),('Katja van Doren','Mitglied',1768,25,''),('Zvezdana Seeger','ehemaliges Mitglied (Arbeitsdirektorin)',1467,26,'2023-10'),('Dr. Rolf Martin Schmitz','ehemaliges Mitglied',639,26,'2021-06')]:
    M(G,'Vorstand',n,f,'','',bis,91 if not bis else 31,'','Bezüge 2025 an ehemaliges Mitglied (Vergütungsbericht S. 31, Tabelle Veränderung)' if bis else '')
    V(R,'Vorstand',n,t,'Gesamtvergütung (TR) gewährt und geschuldet § 162 AktG',sp,'ehemaliges Mitglied' if bis else '')
AR=[('Dr. Frank Appel','Vorsitzender','Anteilseigner','Vorsitzender des Aufsichtsrats der Deutsche Telekom AG','2024-05-03',320),
 ('Michael Vassiliadis','stellv. Vorsitzender','Arbeitnehmer (Gewerkschaft)','Vorsitzender der IGBCE','2025-04-30',320),
 ('Michael Bochinsky','Mitglied','Arbeitnehmer','Stellv. Gesamtbetriebsratsvorsitzender der RWE Power AG','2018-08-01',321),
 ('Sandra Bossemeyer','Mitglied','Arbeitnehmer','Betriebsratsvorsitzende der RWE AG, Schwerbehindertenvertreterin','2016-04-20',321),
 ('Dr. Hans Friedrich Bünting','Mitglied','Anteilseigner','Selbstständiger Unternehmensberater','2021-04-28',321),
 ('Matthias Dürbaum','Mitglied','Arbeitnehmer','Betriebsratsvorsitzender Tagebau Hambach, RWE Power AG','2019-09-30',321),
 ('Ute Gerbaulet','Mitglied','Anteilseigner','Persönlich haftende Gesellschafterin der Dr. August Oetker KG','2017-04-27',321),
 ('Mag. Dr. h. c. Monika Kircher','Mitglied','Anteilseigner','Selbstständige Unternehmensberaterin','2016-10-15',322),
 ('Thomas Kufen','Mitglied','Anteilseigner','Oberbürgermeister der Stadt Essen','2021-10-18',322),
 ('Reiner van Limbeck','Mitglied','Arbeitnehmer','Betriebsratsvorsitzender der Zentrale Essen, RWE Generation SE und RWE Technology International GmbH','2021-09-15',322),
 ('Harald Louis','Mitglied','Arbeitnehmer','Gesamtbetriebsratsvorsitzender der RWE Power AG','2016-04-20',322),
 ('Dagmar Paasch','Mitglied','Arbeitnehmer (Gewerkschaft)','Landesfachbereichsleiterin ver.di NRW (Finanzdienste, Kommunikation, Technologie, Kultur, Ver- und Entsorgung)','2021-09-15',323),
 ('Dirk Schumacher','Mitglied','Arbeitnehmer','Betriebsratsvorsitzender Standort Hauptwerkstatt Grefrath/Werkstätten, RWE Power AG','2021-09-15',323),
 ('Prof. Jörg Rocholl, PhD','Mitglied','Anteilseigner','Präsident der European School of Management and Technology (ESMT Berlin)','2024-05-03',323),
 ('Dr. Stefan Schulte','Mitglied','Anteilseigner','Vorsitzender des Vorstands der Fraport AG','2025-04-30',323),
 ('Hauke Stars','Mitglied','Anteilseigner','Mitglied des Vorstands der Volkswagen AG','2021-04-28',323),
 ('Helle Valentin','Mitglied','Anteilseigner','Managing Partner IBM Consulting EMEA, IBM Corporation','2021-04-28',323),
 ('Dr. Andreas Wagner','Mitglied','Arbeitnehmer','Mitarbeiter Bohr- und Wasserwirtschaft der RWE Power AG','2021-09-15',324),
 ('Marion Weckes','Mitglied','Arbeitnehmer','Assistentin des Senior Vizepräsidenten Corporate Legal der GEA Group AG','2016-04-20',324),
 ('Thomas Westphal','Mitglied','Anteilseigner','Oberbürgermeister a. D. der Stadt Dortmund','2024-05-03',324),
 ('Ralf Sikorski','Mitglied (ausgeschieden)','Arbeitnehmer (Gewerkschaft)','Ehem. stellv. Vorsitzender der IGBCE','2014-07-01',320),
 ('Dr. Werner Brandt','Vorsitzender (ausgeschieden)','Anteilseigner','Mitglied des Aufsichtsrats der Siemens AG','2013-04-18',320)]
for n,f,art,beruf,seit,sp in AR:
    bis='2025-04-30' if 'ausgeschieden' in f else ''
    M(G,'Aufsichtsrat',n,f,art,seit,bis,sp,beruf,'Stand 26.2.2026; Arbeitnehmervertreter laut Fußnote 2 im Verzeichnis')
    W(G,n,beruf,'','lt. Dokument','Beruf laut Organverzeichnis',sp)
for n,g,f,sp,gl in [('Dr. Frank Appel','Deutsche Telekom AG','Vorsitz Aufsichtsrat',320,''),('Dr. Frank Appel','Fresenius Management SE','Mitglied',320,''),('Dr. Frank Appel','Henkel AG & Co.KGaA','Mitglied',320,''),
 ('Michael Vassiliadis','BASF SE','Mitglied (börsennotiert)',320,''),('Michael Vassiliadis','RAG AG','stellv. Vorsitz',320,''),('Michael Vassiliadis','Steag GmbH','stellv. Vorsitz',320,''),('Michael Vassiliadis','Vivawest GmbH','Mitglied',320,''),('Michael Vassiliadis','Henkel AG & Co.KGaA','Mitglied',320,''),
 ('Ralf Sikorski','Lanxess AG','Mitglied (börsennotiert)',320,''),('Dr. Werner Brandt','Siemens AG','Mitglied (börsennotiert)',320,''),
 ('Dr. Stefan Schulte','Fraport AG','Vorstandsvorsitzender; Vorsitz mehrerer Konzerngesellschaften',323,''),
 ('Hauke Stars','Dr. Ing. h. c. F. Porsche AG','Mitglied (börsennotiert, VW-Konzern)',323,''),('Hauke Stars','AUDI AG','Mitglied (VW-Konzern)',323,''),('Hauke Stars','Kühne + Nagel International AG','Mitglied (börsennotiert)',323,''),
 ('Helle Valentin','Danske Bank A/S','Mitglied (börsennotiert)',323,''),('Thomas Westphal','Dortmunder Stadtwerke AG','Vorsitz (bis 2025-12-12)',324,''),('Ute Gerbaulet','Dr. August Oetker Nahrungsmittel KG','Vorsitz',321,'')]:
    X(G,n,'a',g,'',f,gl,sp)
K(G,'vorstand_mitglieder_zahl',3,'Personen',91)
K(G,'vorstand_frauen_zahl',1,'Personen',91,'33,3 %')
K(G,'ar_mitglieder_zahl',20,'Personen',91)
K(G,'ar_frauen_zahl',7,'Personen',91,'35,0 %')
K(G,'ar_arbeitnehmervertreter_zahl',10,'Personen',320,'Fußnote 2 "Vertreter der Arbeitnehmer"; Stand 26.2.2026')
K(G,'ar_gewerkschaftsvertreter_zahl',2,'Personen',320,'Vassiliadis (IGBCE), Paasch (ver.di); Zuordnung aus Beruf')
K(G,'mitbestimmung_ar','paritätisch (MitbestG), 10 von 20 Arbeitnehmervertreter','',91,'"Committee pursuant to Section 27, Paragraph 3 of the German Co-determination Act" im Vergütungsbericht S. 27; Parität aus 20 Mitgliedern und zehn Arbeitnehmervertretern abgeleitet')
K(R,'pay_ratio','','',30,'kein Verhältniswert; nur vergleichende Darstellung der jährlichen Veränderung (Abschnitt E)')
