from lib import *
U = 'U000396'
R = ('governance/dokumente/merck-kgaa/verguetungsbericht-2025.pdf', U)
uni('Merck KGaA', U)
# Compensation Report 2025 (englisch); Seiten = PDF-Seiten; Beträge in T€; Vergleichstabelle § 162 Abs. 1 Nr. 2 AktG S. 36
VS = [('Belén Garijo','Chair of the Executive Board (Vorsitzende des Vorstands)','2021-05-01','',7690,''),
 ('Kai Beckmann','Mitglied des Vorstands (Deputy Chair seit 25.9.2025)','2011-04-01','',5766,''),
 ('Peter Guenter','Mitglied des Vorstands','2021-01-01','2025-05-31',11594,'Ausscheiden 31.5.2025; Summe enthält Abfindungs-/Beendigungsleistungen'),
 ('Matthias Heinzel','Mitglied des Vorstands','2021-04-01','2025-05-31',7608,'Ausscheiden 31.5.2025; Summe enthält Leistungen zur Beendigung (Karenz, Abfindung)'),
 ('Helene von Roeder','Mitglied des Vorstands','2023-07-01','',4301,'enthält Ausgleichszahlungen für verfallene variable Vergütung bei Vonovia'),
 ('Khadija Ben Hammada','Mitglied des Vorstands','2025-03-01','',1010,'zeitanteilig'),
 ('Jean-Charles Wirth','Mitglied des Vorstands','2025-06-01','',708,'zeitanteilig'),
 ('Dan Pinhas Bar Zohar','Mitglied des Vorstands','2025-06-01','',725,'zeitanteilig')]
for n,f,s,b,t,bem in VS:
    M(R,'Vorstand',n,f,'',s,b,36,'','Funktion/Eintritt lt. Vergleichstabelle')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Gesamt)',36,bem)
for n,t,bem in [('Marcus Kuhnert',2829,'Vorstand bis 30.6.2023'),('Stefan Oschmann',1215,'Vorstand bis 30.4.2021'),('Karl-Ludwig Kley',768,'Vorstand bis 31.8.2016'),('Bernd Reckmann',521,'Vorstand bis 29.4.2016'),('Weitere ehemalige Mitglieder (gesamt)',5482,'Sammelposten')]:
    V(R,'Vorstand (ehemalig)',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied)',36,bem)
AR = [('Michael Kleinemeier','Vorsitzender','2024-02-13','',242.5),('Sascha Held','Stellvertretender Vorsitzender bis 30.6.2025','','2025-06-30',84.3),
 ('Anne Lange','Stellvertretende Vorsitzende seit 1.7.2025','','',98.8),('Birgit Biermann','Mitglied','2022-07-14','',80.0),
 ('Katja Garcia Vila','Mitglied','2024-04-26','',130.0),('Carla Kriwet','Mitglied','2024-04-26','',80.0),('Barbara Lambert','Mitglied','2023-08-11','',180.0),
 ('Dietmar Oeter','Mitglied','','',80.0),('Stefan Palzer','Mitglied','2024-04-26','',79.0),('Alexander Putz','Mitglied','','',80.0),
 ('Christian Raabe','Mitglied','','',130.0),('Michael Reinhart','Mitglied','2024-04-26','',130.0),('Susanne Schaffert','Mitglied','2024-04-26','',79.0),
 ('Sandra Schwebke','Mitglied','2024-04-26','',80.0),('Daniel Thelen','Mitglied','','',80.0),('Simon Thelen','Mitglied','','',80.0),('Sven Vollrath','Mitglied','2025-07-01','',64.5)]
for n,f,s,b,t in AR:
    M(R,'Aufsichtsrat',n,f,'',s,b,36,'','Anteilseigner-/Arbeitnehmerseite im Bericht nicht ausgewiesen')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG',36,'')
K(R,'vorstand_mitglieder_zahl',8,'Personen',36,'im GJ 2025 aktiv lt. Vergleichstabelle (inkl. Guenter und Heinzel bis 31.5.2025)')
K(R,'aufsichtsrat_mitglieder_zahl',17,'Personen',36,'in der Vergleichstabelle aufgeführt (inkl. unterjährig ausgeschiedener/eingetretener)')
