from lib import *
U = 'U000363'
R = ('governance/dokumente/lanxess-aktiengesellschaft/verguetungsbericht-2025.pdf', U)
uni('LANXESS Aktiengesellschaft', U)
# Vergütungsbericht 2025; Seiten = PDF-Seiten; Vorstandsbeträge in T€ lt. vergleichender Darstellung (S. 20), AR-Beträge in € lt. Tabelle S. 19 (hier in T€)
VS = [('Matthias Zachert','Vorsitzender des Vorstands','2014-04-01','',3395),('Frederique van Baarle','Mitglied des Vorstands und Arbeitsdirektorin','2023-04-01','',1047),
 ('Dr. Hubert Fink','Mitglied des Vorstands','2015-10-01','',1511),('Oliver Stratmann','Mitglied des Vorstands','2023-09-01','',950)]
for n,f,s,b,t in VS:
    M(R,'Vorstand',n,f,'',s,b,20,'','Funktion/Eintritt lt. Vergleichstabelle')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Gesamt)',20,'')
V(R,'Vorstand (ehemalig)','Dr. Anno Borkowsky',140,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied, Pensionszahlungen)',20,'Vorstand bis 31.12.2023')
V(R,'Vorstand (ehemalig)','Dr. Rainier van Roessel',155,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied, Pensionszahlungen)',20,'Vorstand bis 31.12.2019; heute Aufsichtsratsvorsitzender')
AN = {'Birgit Biermann','Ralf Sikorski','Sadik Emiroglu','Dr. Hans-Dieter Gerriets','Cem Güner','Dr. Carsten Hesse'}
AR = [('Dr. Rainier van Roessel','Vorsitzender (seit 24.5.2024)','','',267.500),('Birgit Biermann','Stellvertretende Vorsitzende (seit 22.5.2025)','2025-05-22','',113.260),
 ('Ralf Sikorski','Stellvertretender Vorsitzender (bis 22.5.2025)','','2025-05-22',70.191),('Hans van Bylen','Mitglied','','',187.5),('Armando Dente','Mitglied','','',141.5),
 ('Sadik Emiroglu','Mitglied (1.6.2024 bis 22.5.2025)','2024-06-01','2025-05-22',54.630),('Dr. Hans-Dieter Gerriets','Mitglied (bis 22.5.2025)','','2025-05-22',54.630),
 ('Cem Güner','Mitglied (seit 22.5.2025)','2025-05-22','',59.664),('Dr. Heike Hanagarth','Mitglied','','',99.390),('Dr. Carsten Hesse','Mitglied (seit 22.5.2025)','2025-05-22','',59.664),
 ('Pamela Knapp','Mitglied','','',181.5),('Hans Joachim Müller','Mitglied (seit 24.5.2024)','2024-05-24','',153.637),('Lawrence A. Rosen','Mitglied','','',151.5),
 ('Iris Schmitz','Mitglied','','',170.548),('Manuela Strauch','Mitglied','','',170.548)]
for n,f,s,b,t in AR:
    M(R,'Aufsichtsrat',n,f,'Arbeitnehmervertreter' if n in AN else '',s,b,19,'','Als Arbeitnehmervertreter im Text (Wahl der Arbeitnehmervertreter 2025, S. 18) genannt' if n in AN else 'Zuordnung zur Arbeitnehmerseite im Bericht nicht ausgewiesen')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Fest, Ausschuss, Sitzungsgeld, Tochter-AR)',19,'')
V(R,'Aufsichtsrat','Gesamt',1935.662,'Gesamtvergütung',19,'Summenzeile (2024: 1.990,6 T€)')
K(R,'vorstand_mitglieder_zahl',4,'Personen',20,'vier aktive Mitglieder')
K(R,'pay_ratio','','',20,'Kein Verhältnis ausgewiesen; Ø-Vergütung Beschäftigte in Deutschland ohne Vorstand 82 T€ (2024: 84 T€)')
