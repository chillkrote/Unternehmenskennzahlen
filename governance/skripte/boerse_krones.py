from lib import *
U = 'U000349'
R = ('governance/dokumente/krones-ag/verguetungsbericht-2025.pdf', U)
uni('Krones AG', U)
# Vergütungsbericht 2025 (krones.com, HV 2026); Seiten = PDF-Seiten; Beträge in T€ (gewährte und geschuldete Vergütung, S. 13, ohne Versorgungsaufwand)
VS = [('Christoph Klenk','Vorsitzender des Vorstands (CEO)',1750),('Uta Anders','Finanzvorständin (CFO)',1126),('Thomas Ricker','Vorstand Vertrieb und Marketing and Services',1210),
 ('Markus Tischer','Vorstand International Operations',1121),('Ralf Goldbrunner','Vorstand Abfüll- und Verpackungstechnik',1081)]
for n,f,t in VS:
    M(R,'Vorstand',n,f,'','','',13,'','')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ohne Versorgungsaufwand)',13,'')
AR = [('Volker Kronseder','Aufsichtsratsvorsitzender',False,108.0),('Josef Weitzer','Stellvertretender Aufsichtsratsvorsitzender',True,73.0),('Norbert Broger','Mitglied',False,54.0),
 ('Nora Diepold','Mitglied',False,44.0),('Robert Friedmann','Mitglied',False,41.0),('Oliver Grober','Mitglied',True,44.0),('Thomas Hiltl','Mitglied',True,44.0),
 ('Markus Hüttner','Mitglied',True,55.5),('Prof. Dr. Susanne Nonnast','Mitglied',False,54.0),('Dr. Verena Di Pasquale','Mitglied',True,44.0),('Beate Eva Maria Pöpperl','Mitglied',True,44.0),
 ('Stefan Raith','Mitglied',True,44.0),('Olga Redda','Mitglied',True,54.0),('Petra Schadeberg-Herrmann','Mitglied',False,42.5),('Stephan Seifert','Mitglied',False,41.0),('Matthias Winkler','Mitglied',False,61.0)]
for n,f,an,t in AR:
    M(R,'Aufsichtsrat',n,f,'Arbeitnehmervertreter' if an else 'Anteilseignervertreter','','',16,'','Kennzeichnung * "Arbeitnehmervertreter"; Vergütung anteilig an Hans-Böckler-Stiftung abgeführt' if an else '')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Festvergütung, Ausschuss, Sitzungsgeld)',16,'')
K(R,'vorstand_mitglieder_zahl',5,'Personen',13,'fünf aktive Mitglieder')
K(R,'ar_mitglieder_zahl',16,'Personen',16,'acht Anteilseigner- und acht Arbeitnehmervertreter')
K(R,'ar_arbeitnehmervertreter_zahl',8,'Personen',16,'Fußnote * "Arbeitnehmervertreter"')
K(R,'pay_ratio','','',15,'Ø Vergütung Gesamtbelegschaft Krones AG 87,0 T€ (2024: 86,8 T€)')
