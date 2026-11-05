from lib import *
U = 'U000234'
R = ('governance/dokumente/fresenius-se-und-co-kgaa/geschaeftsbericht-2025.pdf', U)
uni('Fresenius SE & Co. KGaA', U)
# Vergütungsbericht ist Teil des Geschäftsberichts; Seiten = PDF-Seiten. Vorstand der Fresenius Management SE (persönlich haftende Gesellschafterin)
VS = [('Michael Sen','Vorsitzender des Vorstands (seit 1.10.2022)','2021-04-12',4431,73),
 ('Pierluigi Antonelli','Vorstand Unternehmensbereich Fresenius Kabi','2023-03-01',2056,73),
 ('Sara Hennicken','Vorstand Finanzen','2022-09-01',1946,74),
 ('Robert Möller','Vorstand Unternehmensbereich Fresenius Helios','2023-09-08',2113,74),
 ('Dr. Michael Moser','Vorstand Recht, Compliance, Risikomanagement','2023-07-01',2173,74)]
for n,f,s,t,p in VS:
    M(R,'Vorstand',n,f,'',s,'',p,'','Vorstand der Fresenius Management SE (persönlich haftende Gesellschafterin); Funktion lt. Individualtabelle')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Summe i. S. d. § 162 Abs. 1 S. 2 Nr. 1)',p,'ohne Versorgungsaufwand (Sen inkl. Versorgungsaufwand 5.123)' if n=='Michael Sen' else 'ohne Versorgungsaufwand')
V(R,'Vorstand','Gesamt (alle Mitglieder)',12719,'Gesamtvergütung',78,'Summe der fünf Einzelwerte; keine Gesamtzeile im Bericht')
# Aufsichtsrat (Gesamtvergütung für Fresenius SE & Co. KGaA und Fresenius Management SE zusammen)
AR = [('Wolfgang Kirsch','Vorsitzender','','',570),('Michael Diekmann','Mitglied','','',320),('Grit Genster','Mitglied','','',320),('Dr. Dieter Schenk','Mitglied (Aufsichtsrat Fresenius Management SE)','','',320),
 ('Prof. Dr. med. D. Michael Albrecht','Mitglied','','2025-05-23',71),('Dr. Frank Appel','Mitglied (Aufsichtsrat Fresenius Management SE)','','',210),('Bernd Behlert','Mitglied','','',230),
 ('Alberto Fuentelsaz Franganillo','Mitglied','2025-02-01','2025-05-23',56),('Carsten Georg','Mitglied','2025-05-23','',109),('Dr. Heinrich Hiesinger','Mitglied (Aufsichtsrat Fresenius Management SE)','','',210),
 ('Prof. Dr. med. Ralf Kiesslich','Mitglied','2025-05-23','',109),('Tania Lara Campaña','Mitglied','2025-05-23','',109),('Frauke Lehmann','Mitglied','','2025-05-23',71),
 ('Prof. Dr. med. Iris Löw-Friedrich','Mitglied','','',180),('Holger Michel','Mitglied','','',180),('Oscar Romero De Paco','Mitglied','','',180),
 ('Harald Steer','Mitglied','','2025-01-31',15),('Susanne Zeidler','Mitglied','','',335),('Dr. Christoph Zindel','Mitglied','','',230)]
for n,f,s,b,t in AR:
    M(R,'Aufsichtsrat',n,f,'',s,b,77,'','Anteilseigner-/Arbeitnehmerseite in der Vergütungstabelle nicht ausgewiesen')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Fest- und Ausschussvergütung, KGaA und Management SE zusammen)',77,'')
V(R,'Aufsichtsrat','Gesamt',3825,'Gesamtvergütung',77,'Ausweis im Bericht (Summen-Zeile)')
K(R,'vorstand_mitglieder_zahl',5,'Personen',74,'fünf Mitglieder mit Vergütung 2025')
K(R,'pay_ratio','','',78,'Kein Verhältnis ausgewiesen; durchschnittliche Arbeitnehmervergütung Konzern (FTE, Löhne und Gehälter) 2025: 53 T€; Berechnung siehe berechnungen/pay_ratio.csv')
