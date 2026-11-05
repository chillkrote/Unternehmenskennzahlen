from lib import *
U = 'U000524'
R = ('governance/dokumente/scout24-se/verguetungsbericht-2025.pdf', U)
uni('Scout24 SE', U)
# Vergütungsbericht 2025; Seiten = PDF-Seiten; Beträge in T€ lt. Bericht
VS = [('Ralf Weitz','Vorsitzender des Vorstands (CEO, ehem. CPTO)','2018-12-01','',4290.5,'CEO ab 1.3.2025; Vorstand seit 12/2018'),
 ('Dr. Dirk Schmelzer','Mitglied des Vorstands (CFO)','2019-06-01','2026-02-28',2195.8,'ausgeschieden zum 28.2.2026 (nach Berichtsjahr)'),
 ('Dr. Gesa Crockford','Mitglied des Vorstands (CCO)','2024-04-01','',1005.2,''),
 ('Tobias Hartmann','Vorstandsmitglied (ehem. CEO)','2018-11-01','2025-02-28',5902.5,'Amt beendet 28.2.2025, Dienstverhältnis bis 31.5.2025; Summe inkl. Auszahlungen aus anteilsbasierter Vergütung'),
 ('Dr. Thomas Schroeter','ehemaliges Vorstandsmitglied (CPO)','2018-12-01','2023-06-30',2497.6,'Auszahlung aus früherer anteilsbasierter Vergütung (Vorjahre)')]
for n,f,s,b,t,bem in VS:
    M(R,'Vorstand',n,f,'',s,b,34,'','Funktion lt. Vergleichstabelle')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Gesamtvergütung)',34,bem)
AR = [('Dr. Hans-Holger Albrecht','Vorsitzender','2018-06-01','',260.0,31),('Frank H. Lutz','Stellvertretender Vorsitzender','2019-08-01','',221.7,31),
 ('Maya Miteva','Mitglied','2023-06-01','',95.0,31),('Andrea Euenheim','Mitglied','2024-06-05','',110.0,31),
 ('André Schwämmlein','Mitglied','2019-08-01','',90.0,31),('Lutz Finger','Mitglied','2025-06-05','',55.4,31),
 ('Sohaila Ouffata','Mitglied (ausgeschieden)','2023-06-01','2025-06-05',45.0,31)]
for n,f,s,b,t,p in AR:
    M(R,'Aufsichtsrat',n,f,'',s,b,p,'','Alle Mitglieder von der Hauptversammlung gewählt (keine Arbeitnehmervertreter ausgewiesen)')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Grund- und Ausschussvergütung, ohne Auslagen)',p,'')
V(R,'Aufsichtsrat','Gesamt',877.1,'Gesamtvergütung',31,'Summenzeile der Tabelle')
K(R,'vorstand_mitglieder_zahl',4,'Personen',34,'im GJ 2025 aktiv: Weitz, Schmelzer, Crockford, Hartmann (bis 2/2025)')
