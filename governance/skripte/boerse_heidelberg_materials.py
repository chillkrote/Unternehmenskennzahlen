from lib import *
U = 'U000274'
R = ('governance/dokumente/heidelberg-materials-ag/verguetungsbericht-2025.pdf', U)
uni('Heidelberg Materials AG', U)
# Seiten = PDF-Seiten des Vergütungsberichts; Gesamtvergütung enthält den IAS-19-Dienstzeitaufwand der bAV
BEM = 'Gesamtvergütung inkl. bAV-Dienstzeitaufwand (IAS 19) lt. Individualtabelle'
VS = [('Dr. Dominik von Achten','Vorsitzender des Vorstands',8697,27,'',''),
 ('René Aldach','Mitglied des Vorstands',3337,27,'2021-09-01',''),
 ('Dr. Katharina Beumelburg','Mitglied des Vorstands',1939,27,'2024-10-01',''),
 ('Roberto Callieri','Mitglied des Vorstands',2595,27,'2024-01-01',''),
 ('Axel Conrads','Mitglied des Vorstands',1455,27,'2024-02-01',''),
 ('Hakan Gurdal','Mitglied des Vorstands',4032,28,'',''),
 ('Dennis Lentz','Mitglied des Vorstands',3671,28,'2021-09-01',''),
 ('Jon Morrish','Mitglied des Vorstands',4370,28,'',''),
 ('Chris Ward','Mitglied des Vorstands',4388,28,'','')]
for n,f,t,p,s,b in VS:
    M(R,'Vorstand',n,f,'',s,b,p,'','Funktion lt. Individualtabelle Vergütungsbericht; Eintritt lt. Fußnoten vergleichende Darstellung (S. 33)')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Gesamtvergütung)',p,BEM)
V(R,'Vorstand','Gesamt (alle Mitglieder)',34484,'Gesamtvergütung',28,'Summe der neun Einzelwerte; keine Gesamtzeile im Bericht')
AR = [('Dr. Bernd Scheifele','Vorsitzender',332),('Werner Schraeder','stellv. Vorsitzender (seit 16.5.2024)',216),('Barbara Breuninger','Mitglied',165),
 ('Gunnar Groebler','Mitglied (seit 16.5.2024)',129),('Katja Karcher','Mitglied (seit 16.5.2024)',157),('Ludwig Merckle','Mitglied',229),('Luka Mucic','Mitglied',211),
 ('Markus Oleynik','Mitglied (seit 16.5.2024)',157),('Peter Riedel','Mitglied',166),('Margret Suckale','Mitglied',166),('Dr. Sopna Sury','Mitglied',195),('Anna Toborek-Kacar','Mitglied (seit 1.11.2024)',132)]
for n,f,t in AR:
    M(R,'Aufsichtsrat',n,f,'','','',31,'','Anteilseigner-/Arbeitnehmerseite im Vergütungsbericht nicht ausgewiesen (Hinweis auf Abgabe von AR-Vergütung durch Arbeitnehmervertreter)')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Feste Vergütung, Ausschüsse, Sitzungsgelder)',31,'')
V(R,'Aufsichtsrat','Gesamt',2254,'Gesamtvergütung',31,'Ausweis im Bericht')
K(R,'vorstand_mitglieder_zahl',9,'Personen',27,'neun aktive Mitglieder mit Vergütung 2025')
K(R,'ar_mitglieder_zahl',12,'Personen',31,'zwölf Mitglieder mit Vergütung 2025')
K(R,'pay_ratio','','',32,'Kein Verhältnis ausgewiesen; Ø-Direktvergütung Gesamtbelegschaft Heidelberg Materials AG (ohne Vorstand, FTE) 2025: 85 T€; Berechnung siehe berechnungen/pay_ratio.csv')
