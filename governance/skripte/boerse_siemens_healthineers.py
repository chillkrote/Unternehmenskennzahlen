from lib import *
U = 'U000538'
R = ('governance/dokumente/siemens-healthineers-ag/verguetungsbericht-2025.pdf', U)
uni('Siemens Healthineers AG', U)
# Geschäftsjahr 2025 = 1.10.2024-30.9.2025; Seiten = PDF-Seiten des Vergütungsberichts
VS = [('Dr. Bernhard Montag','Vorsitzender des Vorstands','2018-03-01',6788,28,'zusätzlich Versorgungsaufwand 564 T€'),
 ('Dr. Jochen Schmitz','Finanzvorstand','2018-03-01',3943,28,'zusätzlich Versorgungsaufwand 353 T€'),
 ('Darleen Caron','Personalvorständin','2021-02-01',3161,28,''),
 ('Elisabeth Staudinger-Leibrecht','Mitglied des Vorstands','2021-12-01',1451,28,'zusätzlich Versorgungsaufwand 268 T€')]
for n,f,s,t,p,b in VS:
    M(R,'Vorstand',n,f,'',s,'',p,'','Funktion lt. Individualtabelle Vergütungsbericht')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Gesamtvergütung ohne Versorgungsaufwand)',p,b)
V(R,'Vorstand','Gesamt (aktive Mitglieder)',15343,'Gesamtvergütung',28,'Summe der vier Einzelwerte; keine Gesamtzeile im Bericht')
V(R,'Vorstand (ehemalig)','Dr. Christoph Zindel',1994,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied, bis 31.3.2022)',29,'Stock Awards')
V(R,'Vorstand (ehemalig)','Gesamt (alle ehemaligen Mitglieder)',2010,'Gesamtvergütung',29,'Ausweis im Bericht')
AN = 'Arbeitnehmer-/Gewerkschaftsvertreter (Fußnote 2: Abführung an Hans-Böckler-Stiftung)'
AR = [('Prof. Dr. Ralf P. Thomas','Vorsitzender',0,0,'','','Verzicht auf Vergütung (Siemens-Vorstand)'),('Dorothea Simon','stellv. Vorsitzende',275.5,1,'','',''),('Karl-Heinz Streibich','weiterer stellv. Vorsitzender',204.5,0,'','',''),
 ('Vanessa Barth','Mitglied',206.5,1,'','',''),('Harry Blunk','Mitglied (bis 30.6.2025)',166.5,1,'','2025-06-30',''),('Stephan Büttner','Mitglied',211.5,1,'','',''),
 ('Dr. Roland Busch','Mitglied',0,0,'','','Verzicht auf Vergütung (Siemens-Vorstand)'),('Lars-Christian Dinglinger','Mitglied',149.25,1,'','',''),('Dr. Andrea Fehrmann','Mitglied',260.5,1,'','',''),
 ('Nick Heindl','Mitglied',139.0,1,'','',''),('Dr. Marion Helmes','Mitglied',276.5,0,'','',''),('Dr. Peter Körte','Mitglied',0,0,'','','Verzicht auf Vergütung (Siemens-Vorstand)'),
 ('Volker Lang','Mitglied (seit 1.7.2025)',44.25,0,'2025-07-01','',''),('Sarena Lin','Mitglied',183.0,0,'','',''),('Axel Patze','Mitglied',144.0,1,'','',''),('Astrid Ploß','Mitglied',139.0,0,'','',''),
 ('Peer M. Schatz','Mitglied',259.0,0,'','',''),('Dr. Nathalie von Siemens','Mitglied',155.5,0,'','',''),('Harald Tretter','Mitglied',247.5,1,'','',''),('Dow R. Wilson','Mitglied',196.5,0,'','','')]
for n,f,t,an,s,b,bem in AR:
    pg = 31 if AR.index((n,f,t,an,s,b,bem))<10 else 32
    M(R,'Aufsichtsrat',n,f,AN if an else '',s,b,pg,'',bem)
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Grund-, Ausschussvergütung, Sitzungsgeld)',pg,bem)
K(R,'vorstand_mitglieder_zahl',4,'Personen',28,'vier im GJ 2025 amtierende Mitglieder')
K(R,'pay_ratio','','',34,'Kein Verhältnis ausgewiesen; Ø-Vergütung Belegschaft der Siemens Healthineers Gruppe in Deutschland (FTE) GJ 2025: 113 T€; Berechnung siehe berechnungen/pay_ratio.csv')
