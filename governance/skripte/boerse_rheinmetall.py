from lib import *
G = ('governance/dokumente/rheinmetall-ag/geschaeftsbericht-2025.pdf', 'U000502')
uni('E.ON SE','U000195'); uni('Deutsche Bank AG','U000148'); uni('freenet AG','U000231'); uni('Nemetschek SE','U000433')
for n,f,s,b in [('Armin Papperger','Vorsitzender (CEO)','2012-01-01',''),('Klaus Neumann','Mitglied (CFO)','',''),('Dr. Vera Saal','Mitglied (Personal)','2025',''),
                ('René Gansauge','Mitglied (COO)','2025-01-01',''),('Dr. Ursula Biernert-Kloß','Mitglied','2024-10-01','2025-08-31')]:
    M(G,'Vorstand',n,f,'',s,b,94 if n!='Dr. Ursula Biernert-Kloß' else 192)
for n,t,sp in [('Armin Papperger',8399,192),('Klaus Neumann',1813,192),('Dr. Vera Saal',543,192),('René Gansauge',2022,192),('Dr. Ursula Biernert-Kloß',1339,192)]:
    V(G,'Vorstand',n,t,'gewährte und geschuldete Vergütung § 162 AktG (ohne Dienstzeitaufwand)',sp,'Gesamtvergütung inkl. Dienstzeitaufwand: Papperger 10.161, Neumann 1.907; Saal zeitanteilig' if n in('Armin Papperger','Klaus Neumann','Dr. Vera Saal') else '')
AR = [('Dipl.-Kfm. Ulrich Grillo','Vorsitzender','Anteilseigner','CEO der Grillo-Werke AG','2016-05-10'),('Dr.-Ing. Klaus Draeger','Mitglied','Anteilseigner','Executive Advisor','2017-05-09'),
 ('Saori Dubourg','Mitglied','Anteilseigner','Vorsitzende des Vorstands der Greiner AG','2024-05-14'),('Prof. Sigmar Gabriel','Mitglied','Anteilseigner','Berater und Publizist, Bundesminister a. D.','2025-05-13'),
 ('Prof. Dr. Andreas Georgi','Mitglied','Anteilseigner','Executive Advisor','2002-06-10'),('Prof. Dr. Sabina Jeschke','Mitglied','Anteilseigner','Vorstandsvorsitzende des KI Park e. V.','2025-05-13'),
 ('Louise Öfverström','Mitglied','Anteilseigner','CFO der Nemetschek SE','2022-05-10'),('Marc Tüngler','Mitglied','Anteilseigner','Hauptgeschäftsführer DSW – Deutsche Schutzvereinigung für Wertpapierbesitz e. V.','2024-05-14'),
 ('Dr. Daniel Hay','stellv. Vorsitzender','Arbeitnehmer (Gewerkschaft)','Wissenschaftlicher Direktor des Instituts für Mitbestimmung und Unternehmensführung (I.M.U.) der Hans-Böckler-Stiftung','2014-05-07'),
 ('Dagmar Muth','stellv. Vorsitzende','Arbeitnehmer','Vorsitzende des Betriebsrats Bremen, Rheinmetall Electronics GmbH; stellv. Vorsitzende des Konzernbetriebsrats','2015-07-01'),
 ('Ralf Bolm','Mitglied','Arbeitnehmer','Vorsitzender des Betriebsrats der Rheinmetall Waffe Munition GmbH, Niederlassung Trittau; Vorsitzender des Gesamtbetriebsrats; stellv. Vorsitzender des Konzernbetriebsrats','2020-07-01'),
 ('Martin Wolfgang Hoffmann','Mitglied','Arbeitnehmer','Vorsitzender des Europäischen Betriebsrats der Rheinmetall AG; stellv. Vorsitzender des Betriebsrats Waffe Munition, Niederlassung Berlin','2025-01-01'),
 ('Murat Küplemez','Mitglied','Arbeitnehmer','Betriebsratsvorsitzender Pierburg GmbH / Pierburg Pump Technology, Standort Neuss','2022-05-10'),
 ('Dr. Michael Mielke','Mitglied','Arbeitnehmer (leitende Angestellte)','Leiter des Bereichs Wasserstoff, Sensor and Actuators, Pierburg GmbH','2010-09-01'),
 ('Yvonne Möller','Mitglied','Arbeitnehmer (Gewerkschaft)','Tarifsekretärin IG Metall Baden-Württemberg','2025-08-07'),
 ('Sven Schmidt','Mitglied','Arbeitnehmer','Vorsitzender des Betriebsrats und Gesamtbetriebsrats der KS Gleitlager GmbH; Vorsitzender des Konzernbetriebsrats der Rheinmetall AG','2014-07-01')]
for n,f,art,beruf,seit in AR:
    M(G,'Aufsichtsrat',n,f,art,seit,'',12 if art=='Anteilseigner' else 13,beruf,'Seit = erstmalige Bestellung lt. Tabelle; Gewerkschaftszuordnung Hay/Möller aus Funktion abgeleitet (GB S. 165: zwei Gewerkschaftsvertreter, fünf Arbeitnehmervertreter, ein leitender Angestellter)' if 'Gewerkschaft' in art else 'Seit = erstmalige Bestellung lt. Tabelle')
    W(G,n,beruf,'','lt. Dokument','Beruf laut Organverzeichnis',12 if art=='Anteilseigner' else 13)
for n,g,f,sp in [('Dipl.-Kfm. Ulrich Grillo','E.ON SE','Mitglied Aufsichtsrat (börsennotiert)',12),('Prof. Sigmar Gabriel','Deutsche Bank AG','Mitglied Aufsichtsrat',12),('Prof. Sigmar Gabriel','Siemens Energy AG','Mitglied Aufsichtsrat',12),
 ('Prof. Sigmar Gabriel','Siemens Energy Management GmbH','Mitglied Aufsichtsrat (Konzern, nicht börsennotiert)',12),('Prof. Sigmar Gabriel','Heristo AG','Mitglied Aufsichtsrat (nicht börsennotiert)',12),
 ('Prof. Dr. Andreas Georgi','Felix Schoeller Holding GmbH & Co. KG','Mitglied Aufsichtsgremium',12),('Louise Öfverström','Bluebeam Holding Inc.','Mitglied (Konzern Nemetschek, USA)',12),
 ('Marc Tüngler','freenet AG','Vorsitzender Aufsichtsrat',12),('Marc Tüngler','InnoTec TSS AG','Mitglied Aufsichtsrat',12),('Yvonne Möller','IVECO Magirus AG','Mitglied Aufsichtsrat',13),('Yvonne Möller','AUDI AG','Mitglied Aufsichtsrat',13)]:
    X(G,n,'a',g,'',f,'',sp)
K(G,'vorstand_mitglieder_zahl',4,'Personen',94,'Stand Jahresende 2025 (Vorjahr 3)')
K(G,'vorstand_frauen_zahl',1,'Personen',94,'"drei Männern und einer Frau" = 25 % (Vorjahr 66,7 %)')
K(G,'ar_mitglieder_zahl',16,'Personen',165,'je acht Anteilseigner- und Arbeitnehmervertreter (§ 7 Abs. 1 Nr. 2 MitbestG)')
K(G,'ar_frauen_zahl',5,'Personen',168,'drei weibliche Mitglieder Anteilseignerseite, zwei Arbeitnehmerseite (Text S. 168 zweiteilig)')
K(G,'ar_arbeitnehmervertreter_zahl',8,'Personen',165)
K(G,'ar_gewerkschaftsvertreter_zahl',2,'Personen',165,'"zwei Gewerkschaftsvertreter, fünf Arbeitnehmervertreter und einen Vertreter der leitenden Angestellten"')
K(G,'mitbestimmung_ar','paritätisch nach MitbestG, 8 von 16 Arbeitnehmervertreter','',165,'§ 7 Abs. 1 Nr. 2 MitbestG; Arbeitsdirektor gem. § 33 MitbestG (S. 164)')
K(G,'pay_ratio',144.5,'Verhältnis',140,'jährliche Gesamtvergütung der am höchsten bezahlten Einzelperson zum Median der Arbeitnehmer (ohne diese Person); Vorjahr 59,8; Anstieg wegen LTI-Tranche 2022')
