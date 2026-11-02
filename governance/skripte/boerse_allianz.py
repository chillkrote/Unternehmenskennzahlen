from lib import *
U = 'U000036'
G = ('governance/dokumente/allianz-se/geschaeftsbericht-2025.pdf', U)
# Seitenangaben: PDF-Seiten (gedruckte Seitenzahl = PDF-Seite minus 2). Vergütungsbericht ist Teil des Annual Report.
uni('Allianz SE', U)
VB = [('Oliver Bäte','Vorsitzender (CEO seit 05/2015)','2008-01',10594,'Vorjahr 9.166'),
      ('Sirma Boshnakova','Mitglied','2022-01',2408,''),
      ('Claire-Marie Coste-Lepoutre','Mitglied','2024-01',2389,''),
      ('Dr. Barbara Karuth-Zelle','Mitglied','2021-01',2377,''),
      ('Dr. Klaus-Peter Röhler','Mitglied','2020-04',4881,'inkl. erstmaliger LTI-Auszahlung 2.489 T€'),
      ('Dr. Günther Thallinger','Mitglied','2017-01',5657,'inkl. LTI-Auszahlung 3.284 T€'),
      ('Christopher Townsend','Mitglied','2021-01',2392,''),
      ('Renate Wagner','Mitglied','2020-01',5662,'inkl. erstmaliger LTI-Auszahlung 3.284 T€'),
      ('Dr. Andreas Wimmer','Mitglied','2021-10',2380,'')]
for n,f,s,t,b in VB:
    M(G,'Vorstand',n,f,'',s,'',324,'','Funktion/Bestellung lt. Individualtabelle Vergütungsbericht (PDF S. 324)')
    V(G,'Vorstand',n,t,'Vergütung gewährt und geschuldet gem. § 162 AktG (ohne Pensionsaufwand)',324,b)
V(G,'Vorstand','Gesamt (aktive Mitglieder)',sum(x[3] for x in VB),'Summe der Einzelwerte (gerechnet)',324,'Summe aus den neun Einzelwerten, Rundungsabweichungen möglich')
# Aufsichtsrat 12: 6 Anteilseigner, 6 Arbeitnehmer (SEBG, Beteiligungsvereinbarung); Reihenfolge Qualifikationsmatrix PDF S. 20/122-Tabelle, Sitz-Zuordnung lt. Matrix-Reihenfolge
AR = [('Michael Diekmann','Vorsitzender','Anteilseigner','2017',758.0),('Sophie Boissard','Mitglied','Anteilseigner','2017',231.0),
      ('Stephanie Bruce','Mitglied','Anteilseigner','2024-05',231.0),('Rashmy Chatterjee','Mitglied','Anteilseigner','2022',205.0),
      ('Prof. Dr. Ralf P. Thomas','Mitglied','Anteilseigner','2025-05-08',153.0),('Dr. Jörg Schneider','stellv. Vorsitzender','Anteilseigner','2024',438.2),
      ('Prof. Dr. Nadine Brandl','Mitglied','Arbeitnehmer','2024-08',181.0),('Gabriele Burkhardt-Berg','stellv. Vorsitzende','Arbeitnehmer','2012',305.0),
      ('Jean-Claude Le Goaër','Mitglied','Arbeitnehmer','2018',259.0),('Frank Kirsch','Mitglied','Arbeitnehmer','2018',259.0),
      ('Jürgen Lawrenz','Mitglied','Arbeitnehmer','2015',206.0),('Primiano Di Paolo','Mitglied','Arbeitnehmer','2022',181.0)]
for n,f,v,s,t in AR:
    M(G,'Aufsichtsrat',n,f,v,s,'',336,'','Seitenzuordnung Anteilseigner/Arbeitnehmer aus Reihenfolge der Qualifikationsmatrix (PDF S. 20) und Bericht des AR (PDF S. 11); Eintrittsjahr lt. Matrix')
    V(G,'Aufsichtsrat',n,t,'Festvergütung, Ausschussvergütung, Sitzungsgelder gem. § 162 AktG',336,'')
M(G,'Aufsichtsrat','Dr. Friedrich Eichiner','Mitglied','Anteilseigner','', '2025-05-08',336,'','bis Ende der Hauptversammlung 8.5.2025 (AR-Bericht PDF S. 11)')
V(G,'Aufsichtsrat','Dr. Friedrich Eichiner',154.0,'Festvergütung, Ausschussvergütung, Sitzungsgelder gem. § 162 AktG',336,'zeitanteilig bis 05/2025')
V(G,'Aufsichtsrat','Gesamt',3561.2,'Summe Gesamtvergütung',336,'Ausweis im Bericht')
K(G,'vorstand_mitglieder_zahl',9,'Personen',121,'"Number of executive members: 9"')
K(G,'vorstand_frauen_zahl',4,'Personen',121,'"four female members, accounting for 44.4 %" (Corporate Governance Statement); nach § 16 Abs. 2 SEAG mindestens eine Frau')
K(G,'ar_mitglieder_zahl',12,'Personen',122,'sechs Anteilseigner-, sechs Arbeitnehmervertreter')
K(G,'ar_frauen_zahl',5,'Personen',121,'"five women (41.7 %) and seven men" zum 31.12.2025')
K(G,'ar_arbeitnehmervertreter_zahl',6,'Personen',122,'bestellt vom SE-Betriebsrat; vier aus Deutschland, je einer aus Frankreich und Italien')
K(G,'ar_gewerkschaftsvertreter_zahl',1,'Personen',122,'"including one trade union representative" (ver.di); Person im Dokument nicht namentlich ausgewiesen')
K(G,'mitbestimmung_ar','SE-Beteiligungsvereinbarung (SEBG), 6 von 12 Arbeitnehmervertreter','',122,'MitbestG gilt wegen der Rechtsform SE nicht; paritätische Besetzung lt. Vereinbarung')
K(G,'pay_ratio','','',333,'Allianz weist kein Verhältnis aus, nur Entwicklung Vorstand/Ø-Vergütung (95 T€ Deutschland, FTE); Berechnung siehe berechnungen/pay_ratio.csv')
