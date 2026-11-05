from lib import *
U = 'U000165'
R = ('governance/dokumente/dhl-ag/verguetungsbericht-2025.pdf', U)
uni('DHL AG', U)
# Seiten = PDF-Seiten des Vergütungsberichts 2025; Beträge im Bericht in EUR, hier in T€
VS = [('Dr. Tobias Meyer','Vorsitzender des Vorstands','','',3865.310,28,''),('Oscar de Bok','Vorstand Global Forwarding, Freight','','',1785.854,28,''),
 ('Pablo Ciano','Vorstand eCommerce','','',1523.561,28,''),('Nikola Hagleitner','Vorstand Post & Paket Deutschland','','',1490.343,29,''),
 ('Melanie Kreis','Vorstand Finanzen','','',1923.023,29,''),('Dr. Thomas Ogilvie','Vorstand Personal','','',2572.618,29,''),('John Pearson','Vorstand','','',2276.169,29,''),
 ('Hendrik Venter','Vorstand Supply Chain (ab 16.8.2025)','2025-08-16','',431.546,29,'zeitanteilig ab 16.8.2025'),
 ('Tim Scharwath','Vorstand Global Forwarding, Freight (bis 15.8.2025)','','2025-08-15',5588.614,36,'enthält 3.401,464 T€ Abgeltung vertraglicher Ansprüche (Sonstige Zahlungen); laufende Vergütung 2.187,150 T€ (S. 30)')]
for n,f,s,b,t,p,bem in VS:
    M(R,'Vorstand',n,f,'',s,b,p,'','Funktion lt. Individualtabelle Vergütungsbericht')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Gesamtvergütung, ohne Versorgungsaufwand)',p,bem)
V(R,'Vorstand (ehemalig)','Ken Allen',275.871,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied, Deferral 2022)',32,'')
V(R,'Vorstand (ehemalig)','Dr. Frank Appel',1016.518,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied, Deferral 2022)',32,'')
V(R,'Vorstand (ehemalig)','John Gilbert',13.273,'Pensionszahlungen an ehemaliges Mitglied',32,'')
V(R,'Vorstand','Gesamt (aktive Mitglieder ohne Scharwath)',15868.424,'Gesamtvergütung',36,'Summe der acht Einzelwerte ohne Scharwath; keine Gesamtzeile im Bericht')
AR = [('Dr. Katrin Suder','Vorsitzende (ab 2.5.2025)',320.549,'',''),('Dr. Nikolaus von Bomhard','Vorsitzender (bis 2.5.2025)',156.412,'','2025-05-02'),('Andrea Kocsis','stellv. Vorsitzende',374.0,'',''),
 ('Prof. Dr. Dr. Ann-Kristin Achleitner','Mitglied',164.0,'',''),('Dr. Rolf Bösinger','Mitglied (ab 2.7.2025)',101.714,'2025-07-02',''),('Silke Busch','Mitglied',107.0,'',''),('Dr. Mario Daberkow','Mitglied',107.0,'',''),
 ('Ingrid Deltenre','Mitglied',217.0,'',''),('Jörg von Dosky','Mitglied',164.0,'',''),('Dr. Hans Ulrich Engel','Mitglied',214.0,'',''),('Thomas Held','Mitglied',220.0,'',''),('Dr. Heinrich Hiesinger','Mitglied',198.425,'',''),
 ('Prof. Dr. Luise Hölscher','Mitglied (bis 25.6.2025)',105.44,'','2025-06-25'),('Mario Jacubasch','Mitglied (bis 17.12.2025)',155.248,'','2025-12-17'),('Thorsten Kühn','Mitglied',162.0,'',''),
 ('Ulrike Lennartz-Pipenbacher','Mitglied',107.0,'',''),('Yusuf Özdemir','Mitglied',164.0,'',''),('Prof. Dr. Georg A. Pölzl','Mitglied (ab 2.5.2025)',72.849,'2025-05-02',''),('Lawrence Rosen','Mitglied',163.0,'',''),
 ('Stephan Teuscher','Mitglied',221.0,'',''),('Stefanie Weckesser','Mitglied',163.0,'',''),('Stefan B. Wintels','Mitglied',165.0,'','')]
for n,f,t,s,b in AR:
    M(R,'Aufsichtsrat',n,f,'',s,b,35,'','Anteilseigner-/Arbeitnehmerseite in der Tabelle nicht ausgewiesen')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Grund-, Ausschussvergütung, Sitzungsgeld)',35,'')
K(R,'vorstand_mitglieder_zahl',9,'Personen',36,'neun Mitglieder mit Vergütung 2025 (zwei unterjährige Wechsel)')
K(R,'ar_mitglieder_zahl',22,'Personen',35,'22 Mitglieder mit Vergütung 2025')
K(R,'pay_ratio','','',37,'Kein Verhältnis ausgewiesen; Ø-Gesamtvergütung Gesamtbelegschaft DHL Group (Personalaufwand / Beschäftigte) 2025: 50,539 T€; Berechnung siehe berechnungen/pay_ratio.csv')
