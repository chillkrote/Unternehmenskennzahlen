from lib import *
U = 'U000133'
R = ('governance/dokumente/daimler-truck-holding-ag/verguetungsbericht-2025.pdf', U)
uni('Daimler Truck Holding AG', U)
# Seiten = PDF-Seiten des Vergütungsberichts 2025
VS = [('Karin Rådström','Vorsitzende des Vorstands','',2939.3,16,''),('Eva Scherer','Chief Financial Officer','',1547.8,16,''),('Jürgen Hartwig','Personal','',1417.4,16,''),
 ('Achim Puchert','Mercedes-Benz Trucks und BharatBenz','2024-12-01',1271.8,16,'Vorstandsmitglied seit 1.12.2024'),('John O’Leary','Daimler Truck North America','',2004.1,17,''),
 ('Karl Deppen','FUSO und RIZON','',1682.8,17,''),('Andreas Gorbach','Truck Technology','',1639.8,17,'')]
for n,f,s,t,p,b in VS:
    M(R,'Vorstand',n,f,'',s,'',p,'','Funktion lt. Individualtabelle (Abbildung 18)')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Gesamtvergütung i. S. d. § 162, ohne Versorgungsaufwand)',p,b)
V(R,'Vorstand (ehemalig)','Stephan Unger',151.598,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied, Dividendenäquivalent PPSP-Tranchen 2022-2024)',16,'')
V(R,'Vorstand','Gesamt (aktive Mitglieder)',12502.2,'Gesamtvergütung',16,'Summe der sieben Einzelwerte; keine Gesamtzeile im Bericht')
AR = [('Joe Kaeser','Vorsitzender','',448.3,''),('Michael Brecht','stellv. Vorsitzender','',364.3,''),('Michael Brosnan','Mitglied','',253.2,''),('Bruno Buschbacher','Mitglied','',128.8,''),
 ('Jacques Esculier','Mitglied (bis 30.9.2025)','2025-09-30',94.4,'bis'),('Jan Gurander','Mitglied (seit 1.10.2025)','2025-10-01',32.2,'seit'),('Akihiro Eto','Mitglied','',193.2,''),('Laura Ipsen','Mitglied','',126.6,''),
 ('Renata Jungo Brüngger','Mitglied','',153.9,''),('Carmen Klitzsch-Müller','Mitglied','',128.8,''),('Jörg Köhlinger','Mitglied','',192.1,''),('John Krafcik','Mitglied (bis 27.5.2025)','2025-05-27',49.8,'bis'),
 ('Kurt Sievers','Mitglied (seit 27.5.2025)','2025-05-27',77.1,'seit'),('Jörg Lorz','Mitglied','',128.8,''),('Andrea Reith','Mitglied (bis 30.6.2025)','2025-06-30',64.4,'bis'),('Barbara Resch','Mitglied','',182.1,''),
 ('Martin Richenhagen','Mitglied','',127.7,''),('Udo Roth','Mitglied (seit 1.7.2025)','2025-07-01',64.4,'seit'),('Andrea Seidel','Mitglied','',128.8,''),('Shintaro Suzuki','Mitglied','',128.8,''),
 ('Marie L. Wieck','Mitglied','',208.3,''),('Harald Wilhelm','Mitglied','',193.2,''),('Thomas Zwick','Mitglied','',193.2,'')]
for n,f,d,t,k in AR:
    M(R,'Aufsichtsrat',n,f,'',d if k=='seit' else '',d if k=='bis' else '',19,'','Anteilseigner-/Arbeitnehmerseite in der Tabelle nicht ausgewiesen')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Fest-, Ausschussvergütung, Sitzungsgeld)',19,'')
K(R,'vorstand_mitglieder_zahl',7,'Personen',16,'sieben Mitglieder mit Vergütung 2025')
K(R,'ar_mitglieder_zahl',23,'Personen',19,'23 Mitglieder mit Vergütung 2025 (inkl. fünf unterjährige Wechsel)')
K(R,'pay_ratio','','',21,'Kein Verhältnis ausgewiesen; Ø-Vergütung Beschäftigte (Personalaufwand lt. GuV je FTE) 2025: 89,3 T€; Berechnung siehe berechnungen/pay_ratio.csv')
