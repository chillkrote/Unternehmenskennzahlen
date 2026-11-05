from lib import *
U = 'U000195'
R = ('governance/dokumente/e-on-se/verguetungsbericht-2025.pdf', U)
uni('E.ON SE', U)
# Seiten = PDF-Seiten des Vergütungsberichts
VS = [('Leonhard Birnbaum','Vorsitzender des Vorstands (seit 1.4.2021)','2013-07-01',8746,'Mitglied seit 1.7.2013'),
 ('Nadia Jakobi','Vorstand Finanzen','2024-06-01',2006,''),
 ('Thomas König','Vorstand Netzgeschäft','2018-06-01',4618,''),
 ('Victoria Ossadnik','Vorstand Digitalisierung','2021-04-01',4595,''),
 ('Marc Spieker','Vorstand Vertrieb und Kundenlösungen','2017-01-01',4607,'')]
for n,f,s,t,b in VS:
    M(R,'Vorstand',n,f,'',s,'',30,'','Funktion lt. Zielvergütungstabelle (S. 26)')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Gesamtvergütung, vergleichende Darstellung)',30,b)
V(R,'Vorstand','Gesamt (aktive Mitglieder)',24572,'Gesamtvergütung',30,'Summe der fünf Einzelwerte; keine Gesamtzeile im Bericht')
AR = [('Erich Clementi','Vorsitzender (seit 17.5.2023)','',451),('Ulrich Grillo','stellv. Vorsitzender (seit 17.5.2023)','',331),('Frank Werneke','stellv. Vorsitzender','2024-01-01',329),
 ('Katja Bauer','Mitglied','2022-04-01',265),('Klaus Fröhlich','Mitglied','',287),('Anke Groth','Mitglied','2022-07-01',259),('Eugen-Gheorge Luha','Mitglied','',145),
 ('Stefan May','Mitglied','',232),('Nadège Petit','Mitglied','2023-05-17',217),('Szilvia Pinczésné Márton','Mitglied','',145),('René Pöhls','Mitglied','',288),
 ('Andreas Schmitz','Mitglied','',331),('Rolf Martin Schmitz','Mitglied','',219),('Elisabeth Wallbaum','Mitglied','',259),('Deborah Wilkens','Mitglied','',260),('Axel Winterwerber','Mitglied','2023-01-01',244)]
for n,f,s,t in AR:
    M(R,'Aufsichtsrat',n,f,'',s,'',29,'','Anteilseigner-/Arbeitnehmerseite im Vergütungsbericht nicht ausgewiesen')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Fest-, Ausschussvergütung, Sitzungsgeld, Tochtergesellschaften)',29,'')
V(R,'Aufsichtsrat','Gesamt',4262,'Gesamtvergütung',29,'Summe der 16 Einzelwerte; keine Gesamtzeile im Bericht')
K(R,'vorstand_mitglieder_zahl',5,'Personen',30,'fünf aktive Mitglieder')
K(R,'ar_mitglieder_zahl',16,'Personen',29,'16 Mitglieder mit Vergütung 2025')
K(R,'pay_ratio','','',30,'Kein Verhältnis ausgewiesen; Ø-Vergütung Arbeitnehmer in Deutschland (regelmäßige Zielvergütung zum Jahresende, auf 100 % hochgerechnet) 2025: 84 T€ (40.513 Arbeitnehmer); Berechnung siehe berechnungen/pay_ratio.csv')
