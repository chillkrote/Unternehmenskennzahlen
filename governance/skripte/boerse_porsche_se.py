from lib import *
U = 'U000479'
R = ('governance/dokumente/porsche-automobil-holding-se/geschaeftsbericht-2025.pdf', U)
uni('Porsche Automobil Holding SE', U)
# Vergütungsbericht im Geschäftsbericht 2025; Seiten = PDF-Seiten
VS = [('Hans Dieter Pötsch','Vorsitzender des Vorstands (seit 1.11.2015)','2015-11-01','',1527,55,''),
 ('Dr. Manfred Döss','Vorstand für Recht und Compliance','2016-01-01','',1194,55,''),
 ('Dr. Johannes Lattwein','Vorstand für Finanzen und IT','2022-02-01','',1347,56,''),
 ('Lutz Meschke','Vorstand für Beteiligungsmanagement','2020-07-01','2025-12-09',1023,56,'Amt endete 9.12.2025; Leistungszusagen zur Beendigung gesondert im Bericht (III. 8)')]
for n,f,s,b,t,p,bem in VS:
    M(R,'Vorstand',n,f,'',s,b,p,'','Funktion lt. Individualtabelle Vergütungsbericht')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 Abs. 1 AktG (Gesamtvergütung)',p,bem)
V(R,'Vorstand','Gesamt (alle Mitglieder)',5091,'Gesamtvergütung',56,'Summe der vier Einzelwerte; keine Gesamtzeile im Bericht')
AR = [('Dr. Wolfgang Porsche','Vorsitzender',200),('Dr. Hans Michel Piëch','Mitglied',175),('Prof. Dr. Ulrich Lehner','Mitglied',175),('Dr. Ferdinand Oliver Porsche','Mitglied',150),
 ('Mag. Josef Michael Ahorner','Mitglied',75),('Mag. Marianne Heiß','Mitglied',75),('Dr. Günther Horvath','Mitglied',75),('Dr. Sophie Piëch','Mitglied',75),
 ('Peter Daniell Porsche','Mitglied',75),('Prof. KR Ing. Siegfried Wolf','Mitglied',75)]
for n,f,t in AR:
    M(R,'Aufsichtsrat',n,f,'','','',68,'','')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Fest- und Ausschussvergütung)',68,'')
V(R,'Aufsichtsrat','Gesamt',1150,'Gesamtvergütung',68,'Ausweis im Bericht')
K(R,'vorstand_mitglieder_zahl',4,'Personen',56,'vier im GJ 2025 aktive Mitglieder')
K(R,'ar_mitglieder_zahl',10,'Personen',68,'zehn Mitglieder (Porsche SE ist nicht mitbestimmt)')
K(R,'pay_ratio','','',69,'Kein Verhältnis und keine absolute Ø-Vergütung ausgewiesen (nur prozentuale Veränderung der Ø-Vergütung der Arbeitnehmer); Variante A nicht berechenbar')
