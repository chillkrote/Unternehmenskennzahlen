from lib import *
U = 'U000716'
R = ('governance/dokumente/vonovia-se/verguetungsbericht-2025.pdf', U)
uni('Vonovia SE', U)
# Seiten = PDF-Seiten des Vergütungsberichts
VS = [('Rolf Buch','Vorsitzender des Vorstands (CEO)',4085.7,16,'seit 1.3.2013; zusätzlich bAV-Dienstzeitaufwand 770,4 T€ (nicht in § 162-Summe)'),
 ('Arnd Fittkau','Mitglied des Vorstands (CRO)',2163.3,16,'seit 16.5.2019'),
 ('Philip Grosse','Mitglied des Vorstands (CFO)',2410.2,16,'seit 1.1.2022'),
 ('Daniel Riedl','Mitglied des Vorstands (CDO)',2412.6,17,'seit 9.5.2018'),
 ('Ruth Werhahn','Mitglied des Vorstands (CHRO)',1967.7,17,'seit 1.10.2023')]
for n,f,t,p,b in VS:
    M(R,'Vorstand',n,f,'','','',p,'','Funktion lt. Individualtabelle Vergütungsbericht')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Gesamtvergütung)',p,b)
V(R,'Vorstand','Gesamt (alle Mitglieder)',13039.5,'Gesamtvergütung',32,'Summe der fünf Einzelwerte (vergleichende Darstellung); keine Gesamtzeile im Bericht')
AR = [('Clara-Christina Streit','Vorsitzende (seit Mai 2023)','2013-06','',395),('Vitus Eckert','stellv. Vorsitzender','2018-05','',240),
 ('Birgit M. Bohle','Mitglied','2024-05','',140),('Jürgen Fenk','Mitglied','2022-04','',200),('Dr. Florian Funck','Mitglied','2014-08','',230),
 ('Dr. Daniela Gerd tom Markotten','Mitglied','2023-05','',140),('Matthias Hünlein','Mitglied','2022-04','',155),('Dr. Ariane Reinhart','Mitglied','2016-05','',200),
 ('Michael Rüdiger','Mitglied','2025-05','',103),('Dr. Marcus Schenck','Mitglied','2025-05','',93),
 ('Dr. Ute Geipel-Faber','Mitglied (ausgeschieden)','','2025-05',65),('Hildegard Müller','Mitglied (ausgeschieden)','','2025-05',58)]
for n,f,s,b,t in AR:
    M(R,'Aufsichtsrat',n,f,'',s,b,30,'','Anteilseigner-/Arbeitnehmerseite im Vergütungsbericht nicht ausgewiesen')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Fest- und Ausschussvergütung)',30,'')
V(R,'Aufsichtsrat','Gesamt',2019,'Gesamtvergütung',30,'Summe der zwölf Einzelwerte (inkl. zwei ausgeschiedener Mitglieder); keine Gesamtzeile im Bericht')
K(R,'vorstand_mitglieder_zahl',5,'Personen',32,'fünf Mitglieder mit Vergütung 2025')
K(R,'pay_ratio','','',32,'Vonovia weist kein Verhältnis aus; Ø-Gesamtvergütung Gesamtbelegschaft Immobilienwirtschaft (FTE) 2025: 75,1 T€; Berechnung siehe berechnungen/pay_ratio.csv')
