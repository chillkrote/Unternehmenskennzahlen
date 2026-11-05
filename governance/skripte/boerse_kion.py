from lib import *
U = 'U000328'
R = ('governance/dokumente/kion-group-ag/verguetungsbericht-2025.pdf', U)
uni('KION GROUP AG', U)
# Vergütungsbericht 2025 (kiongroup.com, HV 2026); Seiten = PDF-Seiten = Druckseiten; Beträge in T€ (gewährt und geschuldet)
VS = [('Dr. Richard Robinson Smith','Vorsitzender des Vorstands (CEO)','2022-01-01','',5248,23),('Valeria Jimena Gargiulo','Mitglied des Vorstands (CPSO)','2023-05-01','',3043,24),
 ('Christian Harm','Finanzvorstand (CFO)','2023-07-06','',3079,24),('Andreas Krinninger','Mitglied des Vorstands (President KION ITS EMEA)','2021-01-01','',3466,25),
 ('Michael Larsson','Mitglied des Vorstands','2024-01-01','',1774,25),('Ching Pong Quek','Mitglied des Vorstands (CTO & President KION ITS Asia Pacific)','2013-06-04','',4493,26)]
for n,f,s,b,t,p in VS:
    M(R,'Vorstand',n,f,'',s,b,p,'','')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Gesamtvergütung)',p,'Pauschaler Hypotax-Zuschlag im LTI' if 'Quek' in n else '')
AR = [('Dr. Mohsen Sohi','Vorsitzender (seit 27.5.2025)',181.833,''),('Hans Peter Ring','Vorsitzender (bis 27.5.2025)',90.667,'bis 27.5.2025'),('Özcan Pancarci','Stellvertretender Vorsitzender',167.917,''),
 ('Sherry A. Aaholm','Mitglied (seit 27.5.2025)',55.917,''),('Birgit Behrendt','Mitglied',87.5,''),('Jan Bergemann','Mitglied',78.75,''),('Dr. Alexander Dibelius','Mitglied',104.083,''),
 ('Martin Fahrendorf','Mitglied',78.75,''),('Kui Jiang','Mitglied',115.917,''),('Peter Kameritsch','Mitglied (seit 27.5.2025)',120.417,''),('Dominique Lembke','Mitglied',77.25,''),
 ('Thomas Mainka','Mitglied',77.25,''),('Jörg Milla','Mitglied',122.167,''),('Dr. Nicolas Peter','Mitglied (bis 27.5.2025)',52.5,''),('Dr. Christina Reuter','Mitglied (bis 27.5.2025)',27.417,''),
 ('Alexandra Schädler','Mitglied',138.583,''),('Dr. Shaojun Sun','Mitglied',78.75,''),('Claudia Wenzel','Mitglied',96.833,''),('Ping Xu','Mitglied (bis 27.5.2025)',25.917,''),('Xiaomei Zhang','Mitglied (seit 27.5.2025)',57.417,'')]
for n,f,t,b in AR:
    M(R,'Aufsichtsrat',n,f,'','2025-05-27' if 'seit 27.5' in f else '','2025-05-27' if 'bis 27.5' in f else '',31,'','')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (netto: Festvergütung, Ausschuss, Sitzungsgeld)',31,'')
K(R,'vorstand_mitglieder_zahl',6,'Personen',23,'sechs aktive Mitglieder')
K(R,'ar_arbeitnehmervertreter_zahl','','',30,'Nicht einzeln gekennzeichnet; Arbeitnehmervertreter führen Vergütung teils an Hans-Böckler-Stiftung ab (S. 30)')
K(R,'pay_ratio','','',35,'Keine absolute Ø-Vergütung ausgewiesen (nur Veränderung Mitarbeiter Deutschland +3,4 %, FTE)')
