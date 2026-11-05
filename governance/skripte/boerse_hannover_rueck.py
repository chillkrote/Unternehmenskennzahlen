from lib import *
U = 'U000264'
R = ('governance/dokumente/hannover-rueck-se/verguetungsbericht-2025.pdf', U)
uni('Hannover Rück SE', U)
# Seiten = PDF-Seiten des Vergütungsberichts
VS = [('Jean-Jacques Henchoz','Vorsitzender des Vorstands','','2025-03-31',1020.4,17,'ausgeschieden 31.3.2025, Vergütung zeitanteilig'),
 ('Clemens Jungsthöfel','Vorsitzender des Vorstands (seit 1.4.2025; zuvor Finanzvorstand)','2020-09-01','',1892.3,17,'Vorsitzender seit 1.4.2025'),
 ('Sven Althoff','Geschäftsbereichsvorstand (Koordinator Schaden-Rückversicherung)','2014-08-01','',1517.0,17,''),
 ('Claude Chèvre','Geschäftsbereichsvorstand','2011-11-01','',1534.6,17,''),
 ('Dr. Christian Hermelingmeier','Finanzvorstand (seit 1.4.2025)','2025-04-01','',919.8,17,'zeitanteilig ab 1.4.2025'),
 ('Brona Magee','Geschäftsbereichsvorstand','2025-01-01','',1236.9,17,''),
 ('Sharon Ooi','Geschäftsbereichsvorstand','2023-01-11','',1185.7,17,'inkl. 60 TEUR Ausgleichszahlung für Verfall von Leistungen beim vorherigen Arbeitgeber'),
 ('Silke Sehm','Geschäftsbereichsvorstand','2019-03-06','',1439.0,17,''),
 ('Thorsten Steinmann','Geschäftsbereichsvorstand','2024-09-01','',1223.3,17,'')]
for n,f,s,b,t,p,bem in VS:
    M(R,'Vorstand',n,f,'',s,b,p,'','Funktion lt. Individualtabelle Vergütungsbericht')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Gesamtvergütung, ohne Versorgungsaufwand)',p,bem)
for n,b,t,bem in [('Dr. Klaus Miller','2024-12-31',1141.5,'Mandat zum 31.12.2024 niedergelegt, beratend bis 31.8.2025'),('Dr. Michael Pickel','2024-12-31',378.0,''),('Roland Vogel','2020-09-30',565.1,'inkl. Ruhegeld'),('Ulrich Wallin','2019-05-05',318.5,'')]:
    V(R,'Vorstand (ehemalig)',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied)',18,bem)
V(R,'Vorstand','Gesamt (aktive Mitglieder)',11969.0,'Gesamtvergütung',17,'Summe der neun Einzelwerte; keine Gesamtzeile im Bericht')
AR = [('Torsten Leue','Vorsitzender','',459.0,''),('Herbert K. Haas','stellv. Vorsitzender','',224.0,''),('Ilka Hundeshagen','Mitglied','',132.0,'AN'),
 ('Timo Kaufmann','Mitglied','2024-05-06',104.0,'AN'),('Harald Kayser','Mitglied','2024-05-06',104.0,''),('Sibylle Kempff','Mitglied','2024-05-06',104.0,'AN'),
 ('Dr. Alena Kouba','Mitglied','2024-05-06',104.0,''),('Dr. Ursula Lipowsky','Mitglied (Vorsitzende Finanz- und Prüfungsausschuss)','',187.0,''),('Dr. Michael Ollmann','Mitglied','2024-05-06',132.0,'')]
for n,f,s,t,an in AR:
    M(R,'Aufsichtsrat',n,f,'Arbeitnehmervertreter' if an else '',s,'',20,'','Fußnote 1 der Vergütungstabelle: Arbeitnehmervertreter' if an else '')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Fest-, Ausschussvergütung, Sitzungsgelder, inkl. Konzerngesellschaften)',20,'inkl. 110 TEUR Aufsichtsratsbezüge von Konzerngesellschaften' if n=='Torsten Leue' else '')
V(R,'Aufsichtsrat','Gesamt',1550.0,'Gesamtvergütung',20,'Ausweis im Bericht (Summen-Zeile)')
K(R,'vorstand_mitglieder_zahl',9,'Personen',17,'neun aktive Mitglieder mit Vergütung 2025')
K(R,'ar_mitglieder_zahl',9,'Personen',20,'neun Mitglieder mit Vergütung 2025')
K(R,'ar_arbeitnehmervertreter_zahl',3,'Personen',20,'Fußnote 1 kennzeichnet drei aktive Arbeitnehmervertreter (Hundeshagen, Kaufmann, Kempff)')
K(R,'pay_ratio','','',21,'Kein Verhältnis ausgewiesen; Ø-Vergütung Mitarbeiter Hannover Rück SE Deutschland (FTE) 2025: 126,2 T€; Berechnung siehe berechnungen/pay_ratio.csv')
