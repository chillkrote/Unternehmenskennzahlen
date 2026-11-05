from lib import *
U = 'U000645'
R = ('governance/dokumente/talanx-ag/geschaeftsbericht-2025.pdf', U)
uni('Talanx AG', U)
# Geschäftsbericht 2025, Vergütungsbericht; Seiten = PDF-Seiten (Druckseite +4); Beträge in T€ (gewährte und geschuldete Vergütung)
VS = [('Torsten Leue','Vorsitzender des Vorstands','2010-09-01','',3382,42,'Vorsitzender seit 8.5.2018; Aufsichtsratsbezüge von Konzerngesellschaften 362 T€ enthalten'),
 ('Jean-Jacques Henchoz','Geschäftsbereichsvorstand','2019-04-01','2025-03-31',1271,42,'inkl. Hannover Rück SE 2.528 T€'),
 ('Clemens Jungsthöfel','Geschäftsbereichsvorstand','2025-04-01','',1717,42,'inkl. Hannover Rück SE'),
 ('Dr. Wilm Langenbach','Geschäftsbereichsvorstand','2020-12-01','',1527,43,''),('Dr. Edgar Puls','Geschäftsbereichsvorstand','2019-05-09','',1539,43,''),
 ('Caroline Schlienkamp','Mitglied des Vorstands','2022-05-01','',1279,43,''),('Jens Warkentin','Geschäftsbereichsvorstand','2023-01-01','',1290,43,''),
 ('Dr. Jan Wicke','Finanzvorstand (CFO)','2014-05-01','',2103,43,'Finanzvorstand seit 1.9.2020')]
for n,f,s,b,t,p,bem in VS:
    M(R,'Vorstand',n,f,'',s,b,p,'','')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Gesamtvergütung, ohne Versorgungsaufwand)',45,bem)
AR = [('Herbert K. Haas','Vorsitzender',False,559,'2018-05-08'),('Jutta Hammer','Stellvertretende Vorsitzende',True,193,'2011-02-01'),('Angela Titzrath','Stellvertretende Vorsitzende',False,207,'2018-05-08'),
 ('Natalie Bani Ardalan','Mitglied',True,133,'2024-05-07'),('Rainer-Karl Bock-Wehr','Mitglied',True,104,'2019-05-09'),('Dr. Joachim Brenk','Mitglied',False,115,'2023-05-04'),
 ('Sebastian L. Gascard','Mitglied',True,131,'2019-05-09'),('Dr. Christof Günther','Mitglied',False,133,'2023-05-04'),('Dr. Hermann Jung','Mitglied',False,158,'2013-05-06'),
 ('Dirk Lohmann','Mitglied',False,104,'2013-05-06'),('Christoph Meister','Mitglied',True,104,'2014-05-08'),('Dr. Sandra Reich','Mitglied',False,104,'2023-05-04'),
 ('Matthias Rickel','Mitglied',True,104,'2024-05-07'),('Prof. Dr. Jens Schubert','Mitglied',True,114,'2014-05-08'),('Patrick Seidel','Mitglied',True,144,'2024-05-07'),('Norbert Steiner','Mitglied',False,131,'2013-05-06')]
for n,f,an,t,s in AR:
    M(R,'Aufsichtsrat',n,f,'Arbeitnehmervertreter' if an else 'Anteilseignervertreter',s,'',12,'Mitglied im ver.di-Bundesvorstand' if 'Meister' in n else '','Kennzeichnung "Arbeitnehmervertreter" (Fußnote 1)' if an else '')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Festvergütung, Ausschuss, Sitzungsgeld, Konzerngesellschaften)',44,'')
K(R,'vorstand_mitglieder_zahl',7,'Personen',42,'sieben aktive Mitglieder zum 31.12.2025 (zusätzlich Henchoz bis 31.3.2025)')
K(R,'ar_mitglieder_zahl',16,'Personen',12,'acht Anteilseigner- und acht Arbeitnehmervertreter')
K(R,'ar_arbeitnehmervertreter_zahl',8,'Personen',12,'Fußnote "Arbeitnehmervertreter": Hammer, Bani Ardalan, Bock-Wehr, Gascard, Meister, Rickel, Schubert, Seidel')
K(R,'ar_gewerkschaftsvertreter_zahl',1,'Personen',13,'Christoph Meister (Mitglied im ver.di-Bundesvorstand); weitere nicht gekennzeichnet')
K(R,'pay_ratio','','',46,'Kein Verhältnis ausgewiesen; Ø Arbeitnehmer Deutschland 108 T€ (2024: 102 T€) in Vergleichstabelle')
