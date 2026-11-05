from lib import *
U = 'U000242'
R = ('governance/dokumente/gea-group-aktiengesellschaft/geschaeftsbericht-2025.pdf', U)
uni('GEA Group Aktiengesellschaft', U)
# Vergütungsbericht im Geschäftsbericht 2025; Seiten = PDF-Seiten; Beträge im Bericht in EUR, hier in T€
VS = [('Stefan Klebert','Vorsitzender des Vorstands (CEO)','','',6285.687,292,'bestellt bis 31.12.2028'),
 ('Alexander Kocherscheidt','Mitglied des Vorstands (CFO)','2025-11-01','',421.662,292,'zeitanteilig ab 1.11.2025 (Festgehalt 120 T€ im GJ); bestellt bis 31.10.2028'),
 ('Johannes Giloth','Mitglied des Vorstands (COO)','','',3142.042,292,'bestellt bis 30.6.2026'),
 ('Bernd Brinker','Mitglied des Vorstands (ausgeschieden 31.10.2025)','','2025-10-31',3635.130,293,'fixe Bezüge enthalten Abfindungsleistungen zur vorzeitigen Beendigung (Fußnote 4)')]
for n,f,s,b,t,p,bem in VS:
    M(R,'Vorstand',n,f,'',s,b,p,'','Funktion lt. Vergütungstabelle')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Summe)',p,bem)
V(R,'Vorstand (ehemalig)','Dr. Helmut Schmale',247.575,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied, Versorgungsbezüge)',293,'Mitglied 22.4.2009-17.5.2019')
V(R,'Vorstand','Gesamt (gegenwärtige Mitglieder)',9849.391,'Gesamtvergütung',292,'Summenzeile der gegenwärtigen Mitglieder (Klebert, Kocherscheidt, Giloth)')
AR = [('Prof. Dieter Kempf','Vorsitzender',331.0),('Nancy Böhning','Mitglied (unterjährig ausgeschieden)',39.671),('Claudia Claas','Mitglied',128.0),('Roger Falk','Mitglied',169.0),
 ('Prof. Dr. Jürgen Fleischer','Mitglied',152.0),('Rainer Gröbel','Mitglied',167.0),('Michael Kämpfert','Mitglied',80.0),('Prof. Dr. Annette Köhler','Mitglied',174.0),
 ('Brigitte Krönchen','Mitglied',166.0),('Holly Lei','Mitglied',78.0),('Christian van Remmen','Mitglied (unterjährig eingetreten)',26.63),('Andreas Renschler','Mitglied',114.0),('Prof. Dr.-Ing. Axel Stepken','Mitglied',131.0)]
for n,f,t in AR:
    M(R,'Aufsichtsrat',n,f,'','','',305,'','Anteilseigner-/Arbeitnehmerseite in der Vergütungstabelle nicht ausgewiesen')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Fest-, Ausschussvergütung, Sitzungsgelder)',305,'')
V(R,'Aufsichtsrat','Gesamt',1756.301,'Gesamtvergütung',306,'Ausweis im Bericht (Summenzeile, inkl. 2025 ausgeschiedener Mitglieder)')
K(R,'vorstand_mitglieder_zahl',4,'Personen',292,'vier im GJ 2025 aktive Mitglieder (Klebert, Kocherscheidt, Giloth, Brinker)')
K(R,'pay_ratio',85.2,'Verhältnis',302,'Vergütung des CEO im Verhältnis zur durchschnittlichen Vergütung aller Mitarbeitenden des GEA-Konzerns in Deutschland (2024: 68,6); Ø der Vorstandsmitglieder 42,6 (2024: 33,3). Absolute Ø-Vergütung nicht ausgewiesen')
