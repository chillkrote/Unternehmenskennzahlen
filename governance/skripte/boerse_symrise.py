from lib import *
U = 'U000640'
R = ('governance/dokumente/symrise-ag/verguetungsbericht-2025.pdf', U)
uni('Symrise AG', U)
# Vergütungsbericht 2025 (Download von symrise.com/de/verguetungsbericht/); Seiten = PDF-Seiten; Beträge in T€
VS = [('Dr. Jean-Yves Parisot','Vorsitzender des Vorstands','2016-10-01','',2034.986,8,'Vorstand seit 1.10.2016, Vorsitzender seit 1.4.2024'),
 ('Olaf Klinger','Vorstand Finanzen','2016-01-01','',1316.056,8,''),
 ('Dr. Stephanie Coßmann','Vorstand und Arbeitsdirektorin','2023-02-01','',1049.762,8,''),
 ('Walter Ribeiro','Vorstand Taste, Nutrition & Health','2024-09-15','',1040.948,9,''),
 ('Michael Friede','Vorstand Scent & Care','2025-12-01','',1147.785,9,'seit 1.12.2025; enthält Sign-on-Bonus 550 T€, Ausgleich entgangener Pensionsleistungen 480 T€, Umzugskosten 30 T€ (Posten "Sonstiges")')]
for n,f,s,b,t,p,bem in VS:
    M(R,'Vorstand',n,f,'',s,b,p,'','Funktion lt. Vergütungstabelle/Abschnitt 3')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Summe)',p,bem)
V(R,'Vorstand (ehemalig)','Dr. Heinz-Jürgen Bertram',618.481,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied)',19,'Pension 164,1 T€ und LTIP 2022 454,3 T€; Ruhestand seit 31.3.2024')
AR = [('Michael König','Vorsitzender',False,213.0),('Harald Feist','Stellvertretender Vorsitzender',True,163.0),('Ursula Buck','Mitglied',False,112.0),
 ('Jan Zijderveld','Mitglied',False,109.0),('Jeannette Chiarlitti','Mitglied (bis 31.7.2025, zeitweise Mutterschutz)',True,52.0),('Bernd Hirsch','Mitglied',False,162.0),
 ('André Kirchhoff','Mitglied',True,108.0),('Dr. Jakob Ley','Mitglied',True,109.0),('Prof. Dr. Andrea Pfeifer','Mitglied',False,106.5),
 ('Andrea Püttcher','Mitglied',True,112.0),('Peter Vanacker','Mitglied',False,107.0),('Malte Lückert','Mitglied',True,112.0)]
for n,f,an,t in AR:
    M(R,'Aufsichtsrat',n,f,'Arbeitnehmervertreter' if an else 'Anteilseignervertreter','','',4,'','Kennzeichnung ** bzw. * in Abschnitt 4 des Berichts')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Festvergütung und Sitzungsgelder)',21,'')
K(R,'vorstand_mitglieder_zahl',5,'Personen',4,'fünf Mitglieder im GJ 2025 (Friede seit 1.12.2025)')
K(R,'ar_mitglieder_zahl',12,'Personen',4,'sechs Anteilseigner- und sechs Arbeitnehmervertreter')
K(R,'ar_arbeitnehmervertreter_zahl',6,'Personen',4,'Feist, Chiarlitti, Kirchhoff, Ley, Püttcher, Lückert (mit ** gekennzeichnet)')
K(R,'pay_ratio','','',22,'Kein Verhältnis und keine absolute Ø-Vergütung ausgewiesen (Belegschaft Symrise AG Deutschland, 2.713 FTE, 2025 +4,1 % ggü. Vorjahr)')
