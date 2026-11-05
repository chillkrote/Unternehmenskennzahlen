from lib import *
U = 'U000518'
R = ('governance/dokumente/schaeffler-ag/verguetungsbericht-2025.pdf', U)
uni('Schaeffler AG', U)
# Vergütungsbericht 2025 (Upload Robin 05.11.2026); Seiten = PDF-Seiten; Beträge in T€ (Gesamtvergütung gem. § 162 AktG ohne Pensionsaufwand)
VS = [('Klaus Rosenfeld','Vorsitzender des Vorstands','2014-10-24','',5731,26,''),('Dr. Astrid Fontaine','Vorstand Personal und Arbeitsdirektorin','2024-01-01','',2208,26,''),
 ('Christophe Hannequin','Vorstand Finanzen und IT','2025-09-01','',882,26,'zeitanteilig ab 1.9.2025; Nebenleistungen enthalten Ausgleich 153 T€'),
 ('Andreas Schick','Vorstand Produktion, Supply Chain Management und Einkauf','2018-04-01','',2879,26,''),('Jens Schüler','Vorstand Vehicle Lifetime Solutions','2022-01-01','',2697,26,''),
 ('Thomas Stierle','Vorstand E-Mobility','2024-10-01','',1977,26,''),('Uwe Wagner','Vorstand Forschung und Entwicklung','2019-10-01','',2874,26,''),
 ('Sascha Zaps','Vorstand Bearings & Industrial Solutions','2024-05-01','',2105,26,''),('Matthias Zink','Vorstand Powertrain & Chassis','2017-01-01','',2665,26,'')]
for n,f,s,b,t,p,bem in VS:
    M(R,'Vorstand',n,f,'',s,b,p,'','Funktion/Eintritt lt. Vergütungstabelle 1.8')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ohne Pensionsaufwendungen)',p,bem)
V(R,'Vorstand','Gesamt (aktive Mitglieder)',24017,'Gesamtvergütung',26,'Summenzeile (ohne Pensionen 1.820 T€)')
for n,t,bem in [('Claus Bauer',2084,'ehemaliges Mitglied; zusätzlich Karenzentschädigung 208 T€'),('Prof. Dr.-Ing. Peter Gutzmer',159,'Pensionszahlungen'),('Norbert Indlekofer',298,'Pensionszahlungen'),('Prof. Dr. Peter Pleus',298,'Pensionszahlungen'),
 ('Corinna Schittenhelm',334,'LTB; zusätzlich Karenzentschädigung 755 T€'),('Dr. Stefan Spindler',823,'LTB; zusätzlich Karenzentschädigung 809 T€'),('Dietmar Heinrich',0,'Karenzentschädigung 277 T€ (nicht in Gesamtvergütung § 162)')]:
    V(R,'Vorstand (ehemalig)',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied)',27,bem)
for n,t,bem in [('Andreas Wolf',0,'ehemaliges Vitesco-Mitglied; Karenzentschädigung 1.933 T€'),('Klaus Hau',0,'ehemaliges Vitesco-Mitglied; Karenzentschädigung 877 T€'),('Stephan Rölleke',2020,'ehemaliges Vitesco-Mitglied; Abfindung 2.020 T€'),('Werner Volz',25,'ehemaliges Vitesco-Mitglied; Pensionszahlungen')]:
    V(R,'Vorstand (ehemalig)',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Vitesco-Vorstandsmitglied)',28,bem)
AR = [('Georg F. W. Schaeffler','Vorsitzender',179,33,''),('Horst Ott','Stellvertretender Vorsitzender',122,33,''),('Sabine Bendiek','Mitglied',91,32,''),
 ('Grigore Beutura','Mitglied (seit 24.4.2025)',53,32,''),('Prof. Dr. Hans-Jörg Bullinger','Mitglied (bis 24.4.2025)',28,32,''),('Manfred Eibeck','Mitglied (seit 24.4.2025)',51,32,''),
 ('Dr. Holger Engelmann','Mitglied',90,32,''),('Prof. Dr. Bernd Gottschalk','Mitglied (bis 24.4.2025)',20,32,''),('Ulrike Hasbargen','Mitglied',60,32,''),
 ('Susanne Heckelsberger','Mitglied (seit 24.4.2025)',42,32,''),('Lisa Hinrichsen','Mitglied (seit 24.4.2025)',63,32,''),('Joachim Hirsch','Mitglied (seit 24.4.2025)',45,32,''),
 ('Thomas Höhn','Mitglied',115,32,''),('Michael Kicker','Mitglied (seit 24.4.2025)',53,32,''),('Hanna Köhler','Mitglied (bis 24.4.2025)',20,32,''),('Susanne Lau','Mitglied (bis 24.4.2025)',26,32,''),
 ('Antje Mütherig','Mitglied (seit 24.4.2025)',45,32,''),('Dr. Alexander Putz','Mitglied',64,33,''),('Katherina Reiche','Mitglied (bis 28.4.2025)',22,33,''),('Maja Reusch','Mitglied (seit 8.1.2025)',82,33,''),
 ('Volker Robl','Mitglied (seit 24.4.2025)',53,33,''),('Jürgen Schenk','Mitglied (bis 24.4.2025)',25,33,''),('Helga Schönhoff','Mitglied (bis 24.4.2025)',20,33,''),('Ulrich Schöpplein','Mitglied',99,33,''),
 ('Robin Stalker','Mitglied',108,33,''),('Prof. Siegfried Wolf','Mitglied',108,33,''),('Prof. Dr.-Ing. Tong Zhang','Mitglied',78,33,''),('Markus Zirkel','Mitglied (bis 24.4.2025)',25,33,'')]
for n,f,t,p,bem in AR:
    M(R,'Aufsichtsrat',n,f,'','','',p,'','Arbeitnehmer-/Anteilseignerseite in der Tabelle nicht ausgewiesen')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Grundvergütung, Ausschuss, Sitzungsgeld)',p,'')
V(R,'Aufsichtsrat','Gesamt',1787,'Gesamtvergütung',33,'Summenzeile (2024: 1.546 T€)')
K(R,'vorstand_mitglieder_zahl',9,'Personen',26,'neun aktive Mitglieder in der Tabelle 1.8')
K(R,'pay_ratio','','',34,'Kein Verhältnis und keine absolute Ø-Vergütung ausgewiesen (Gesamtbelegschaft weltweit, nur Veränderung +4 % ggü. Vorjahr)')
