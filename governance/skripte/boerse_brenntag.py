from lib import *
U = 'U000100'
R = ('governance/dokumente/brenntag-se/verguetungsbericht-2025.pdf', U)
uni('Brenntag SE', U)
# Remuneration Report 2025 (Kapitel des Annual Report, englisch); Seiten = PDF-Seiten dieses Berichts; Beträge in T€, "awarded and due" gem. § 162 AktG
VS = [('Jens Birgersson','CEO Brenntag Group (seit 1.9.2025)','2025-09-01','',996,19,'zeitanteilig; enthält Sign-on-Bonus 433 T€ (fällig 2026)'),
 ('Thomas Reisten','CFO Brenntag Group','2025-09-09','',706,19,'zeitanteilig'),
 ('Dr. Christian Kohlpaintner','Vorstandsmitglied (CEO bis 31.8.2025)','','2025-08-31',938,19,'als aktives Mitglied bis 31.8.2025; zusätzlich 469 T€ als ehemaliges Mitglied (Seite 20), Gesamt 1.407 T€'),
 ('Dr. Kristin Neumann','Vorstandsmitglied','','2025-03-31',175,19,'bis 31.3.2025; zusätzlich 84 T€ Karenzentschädigung als ehemaliges Mitglied'),
 ('Michael Friede','Vorstandsmitglied','','2025-11-30',649,19,'bis 30.11.2025'),
 ('Ewout van Jarwaarde','Vorstandsmitglied','','2026-03-31',488,19,'als aktives Mitglied bis 8.9.2025; zusätzlich 2.814 T€ als ehemaliges Mitglied (Gehalt, Abfindung, Bonus 2026), Gesamt 3.302 T€')]
for n,f,s,b,t,p,bem in VS:
    M(R,'Vorstand',n,f,'',s,b,p,'','Funktion/Laufzeit lt. Tabelle 4.17 und Text')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Total remuneration, Tabelle 4.17)',p,bem)
V(R,'Vorstand (ehemalig)','Dr. Christian Kohlpaintner',469,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied, Grundgehalt ab 1.9.2025)',20,'')
V(R,'Vorstand (ehemalig)','Ewout van Jarwaarde',2814,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied)',20,'Gehalt 220 T€, Abfindung 2.496 T€, Bonus 2026 98 T€')
V(R,'Vorstand (ehemalig)','Dr. Kristin Neumann',84,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Karenzentschädigung)',20,'1.4.-17.6.2025')
V(R,'Vorstand (ehemalig)','Henri Nejade',8,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Pensionszahlung)',20,'')
AR = [('Richard Ridinger','Vorsitzender','','',425),('Stefanie Berlinger','Stellvertretende Vorsitzende (seit 22.5.2025)','2025-05-22','',200),
 ('Dr. Andreas Rittstieg','Stellvertretender Vorsitzender (bis 22.5.2025)','','2025-05-22',113),('Sujatha Chandrasekaran','Mitglied','','',180),
 ('Wijnand P. Donkers','Mitglied','','',275),('Ulrich M. Harnacke','Mitglied','','',275),('Dominik de Daniel','Mitglied (seit 22.5.2025)','2025-05-22','',109),
 ('Karl von Rohr','Mitglied (seit 9.7.2025)','2025-07-09','',122),('Susanne Wiegand','Mitglied (seit 9.7.2025)','2025-07-09','',86)]
for n,f,s,b,t in AR:
    M(R,'Aufsichtsrat',n,f,'',s,b,23,'','Arbeitnehmerseite im Bericht nicht ausgewiesen')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (reine Festvergütung inkl. Ausschussarbeit, Tabelle 4.22)',23,'')
V(R,'Aufsichtsrat','Gesamt',1784,'Gesamtvergütung',23,'Summenzeile Tabelle 4.22')
K(R,'vorstand_mitglieder_zahl',6,'Personen',19,'sechs im GJ 2025 tätige Mitglieder (Wechsel im Jahresverlauf)')
K(R,'pay_ratio','','',24,'Kein Verhältnis ausgewiesen; Ø-Vergütung Beschäftigte Brenntag SE (Zentrale, FTE) 129 T€')
