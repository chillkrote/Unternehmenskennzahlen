from lib import *
U = 'U000727'
R = ('governance/dokumente/wacker-chemie-ag/verguetungsbericht-2025.pdf', U)
uni('Wacker Chemie AG', U)
# Compensation Report 2025 (englisch, wacker.com); Seiten = PDF-Seiten = Druckseiten; Beträge in T€ (granted and owed, ohne Pensionsaufwand, S. 12)
VS = [('Dr. Christian Hartel','Vorsitzender des Vorstands (President & CEO)','2021-05-01',1652.822),('Dr. Tobias Ohler','Mitglied des Vorstands (CFO)','2013-01-01',1341.494),
 ('Angela Wörl','Mitglied des Vorstands (Arbeitsdirektorin)','2021-05-01',1131.071),('Dr. Christian Kirsten','Mitglied des Vorstands','2023-05-01',1636.761)]
for n,f,s,t in VS:
    M(R,'Vorstand',n,f,'',s,'',12,'','Seit-Datum lt. Vergleichstabelle S. 18')
    V(R,'Vorstand',n,t,'Compensation granted and owed (ohne Pensionsaufwand: Hartel 274, Ohler 183, Wörl 185, Kirsten 195 T€)',12,'')
AR = [('Dr. Peter-Alexander Wacker','Vorsitzender',325),('Manfred Köppl','Stellvertretender Vorsitzender',225),('Prof. Andreas H. Biagosch','Mitglied',175),('Dr. Gregor Biebl','Mitglied',125),
 ('Matthias Biebl','Mitglied',175),('Dr. Patrick Cramer','Mitglied',125),('Stefan Entholzner','Mitglied',125),('Ingrid Heindl','Mitglied',125),('Barbara Kraller','Mitglied',175),
 ('Dr. Benedikt Postberg','Mitglied',125),('Harald Sikorski','Mitglied',125),('Reinhard Spateneder','Mitglied',125),('Ann-Sophie Wacker','Mitglied',125),
 ('Prof. Anna Weber','Mitglied (Vorsitzende Prüfungsausschuss)',225),('Dr. Susanne Weiss','Mitglied',125),('Günter Zellner','Mitglied',125)]
for n,f,t in AR:
    M(R,'Aufsichtsrat',n,f,'','','',16,'','Arbeitnehmer-/Anteilseignerseite im Bericht nicht gekennzeichnet')
    V(R,'Aufsichtsrat',n,t,'Compensation granted and owed (Festvergütung + Auslagenpauschale 25 T€)',16 if n!='Günter Zellner' else 17,'')
K(R,'vorstand_mitglieder_zahl',4,'Personen',12,'vier aktive Mitglieder')
K(R,'ar_mitglieder_zahl',16,'Personen',16,'sechzehn vergütete Mitglieder')
K(R,'ar_arbeitnehmervertreter_zahl','','',15,'Im Bericht nicht gekennzeichnet; Arbeitnehmervertreter führen Vergütung nach DGB-/VAA-Regeln ab (S. 15)')
K(R,'pay_ratio','','',18,'Keine absolute Ø-Vergütung ausgewiesen (nur Veränderung Wacker Chemie AG Deutschland −4 %)')
