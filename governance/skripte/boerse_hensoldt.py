from lib import *
U = 'U000280'
R = ('governance/dokumente/hensoldt-ag/verguetungsbericht-2025.pdf', U)
uni('Hensoldt AG', U)
# Vergütungsbericht 2025 (Robin-Upload, HV 22.05.2026); Seiten = PDF-Seiten = Druckseiten; Beträge in T€ (gewährte und geschuldete Vergütung, S. 9/10, ohne Dienstzeitaufwand)
VS = [('Oliver Dörre','Vorsitzender des Vorstands (CEO)','',1484.185,9,''),('Christian Ladurner','Mitglied des Vorstands (CFO)','',1098.651,9,''),
 ('Dr. Lars Immisch','Mitglied des Vorstands (CHRO)','',982.248,9,'Bestellung zum 31.12.2025 beendet; verstorben 30.01.2026 (S. 10-11); zusätzlich Einmalzahlung 1.528,8 T€ in 2026')]
for n,f,s,t,p,b in VS:
    M(R,'Vorstand',n,f,'',s,'',p,'',b)
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Gesamtvergütung gem. § 162 AktG (Grundgehalt, Nebenleistungen, STI 2025, LTI-Tranche 2022-2025; ohne Dienstzeitaufwand)',p,'')
EX = [('Thomas Müller','Vorsitzender des Vorstands (bis 31.03.2024)','2024-03-31',1300.0),('Celia Pelaz Perez','Mitglied des Vorstands (bis 31.08.2024)','2024-08-31',680.0),
 ('Axel Salzmann','Mitglied des Vorstands (bis 30.06.2022)','2022-06-30',600.0),('Peter Fieser','Mitglied des Vorstands (bis 30.09.2022)','2022-09-30',800.0)]
for n,f,bis,t in EX:
    M(R,'Vorstand',n,f,'','',bis,10,'','Ausgeschieden; 2025 nur LTI-Auszahlung Tranche 2022-2025')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung 2025 ehemaliges Mitglied (LTI-Bonus Tranche 2022-2025)',10,'')
# Aufsichtsrat S. 13; Fußnote 1 = Arbeitnehmervertreter
AR = [('Reiner Winkler','Vorsitzender',False,165),('Armin Maier-Junker','Stellvertretender Vorsitzender',True,85),('Dr. Jürgen Bestle','Mitglied',True,80),('Jürgen Bühl','Mitglied',True,65),
 ('Marco R. Fuchs','Mitglied',False,60),('Achim Gruber','Mitglied',True,65),('Ingrid Jägering','Mitglied',False,85),('Marion Koch','Mitglied',True,65),('Raffaella Luglini','Mitglied',False,65),
 ('Giuseppe Panizzardi','Mitglied',False,90),('Julia Wahl','Mitglied',True,65),('Hiltrud D. Werner','Mitglied',False,90)]
for n,f,an,t in AR:
    M(R,'Aufsichtsrat',n,f,'Arbeitnehmervertreter' if an else 'Anteilseignervertreter','','',13,'','Fußnote 1 "Arbeitnehmervertreter"' if an else '')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Grundvergütung + Ausschusszulagen)',13,'')
K(R,'vorstand_mitglieder_zahl',3,'Personen',9,'drei zum 31.12.2025 amtierende Mitglieder')
K(R,'ar_mitglieder_zahl',12,'Personen',13,'zwölf Mitglieder')
K(R,'ar_arbeitnehmervertreter_zahl',5,'Personen',13,'Fußnote 1; davon vier zugleich Angestellte des Konzerns (Fußnote 2)')
K(R,'pay_ratio','','',15,'Ø Belegschaftsvergütung 101.077 € (HENSOLDT AG und dt. Töchter, Steuerbrutto VZÄ), 2024: 96.724 €')
