from lib import *
G = ('governance/dokumente/adidas-ag/geschaeftsbericht-2025.pdf', 'adidas-ag')
R = ('governance/dokumente/adidas-ag/verguetungsbericht-2025.pdf', 'adidas-ag')
uni('SAP SE','sap-se'); uni('Merck KGaA','merck-kgaa'); uni('Lanxess AG','lanxess-aktiengesellschaft'); uni('Wacker Chemie AG','wacker-chemie-ag')
for n,f,t,sp in [('Bjørn Gulden','Vorsitzender (CEO)',6896.216,12),('Harm Ohlmeyer','Finanzen (CFO)',2866.084,12),
                 ('Michelle Robertson','Global Human Resources, People and Culture',2372.289,13),('Mathieu Sidokpohou','Vertrieb',2189.832,13)]:
    M(G,'Vorstand',n,f,'','','',sp,'','Funktion lt. Vergütungsbericht S. %d' % sp)
    V(R,'Vorstand',n,t,'Gesamtvergütung gem. § 162 AktG (gewährt und geschuldet, ohne Versorgungsaufwand)',sp,'in T€ (Quelle in EUR, exakt: %d EUR)' % round(t*1000))
AR=[('Thomas Rabe','Vorsitzender','Anteilseigner','Vorstandsvorsitzender, Bertelsmann Management SE','2019-05-09',21),
 ('Paul Francis Seline','stellv. Vorsitzender','Arbeitnehmer','Vorsitzender des Betriebsrats Herzogenaurach','2024-05-16',21),
 ('Nassef Sawiris','stellv. Vorsitzender','Anteilseigner','Executive Chairman OCI N.V.','2016-06-15',21),
 ('Birgit Biermann','Mitglied','Arbeitnehmer (Gewerkschaft)','Mitglied des geschäftsführenden Hauptvorstands IGBCE','2022-09-01',21),
 ('Linda Evenhuis','Mitglied','Arbeitnehmer','Senior Lead Program and Facilitation, adidas AG','2024-05-16',21),
 ('Ian Gallienne','Mitglied','Anteilseigner','','2016-06-15',22),
 ('Jackie Joyner-Kersee','Mitglied','Anteilseigner','CEO Jackie Joyner-Kersee Foundation','2021-05-12',22),
 ('Christian Klein','Mitglied','Anteilseigner','Vorstandssprecher (CEO) SAP SE','2020-08-11',22),
 ('Bastian Knobloch','Mitglied','Arbeitnehmer','Vorsitzender des Betriebsrats Campus North','2022-01-01',22),
 ('Oliver Mintzlaff','Mitglied','Anteilseigner','CEO Corporate Projects & Investments, Red Bull GmbH','2024-05-16',22),
 ('Petar Mitrovic','Mitglied','Arbeitnehmer','Senior Manager Program Facilitation, adidas AG','2024-05-16',23),
 ('Thomas Sapper','Mitglied','Arbeitnehmer','Senior Director Tech Project Management, adidas AG','2024-05-16',23),
 ('Harald Sikorski','Mitglied','Arbeitnehmer (Gewerkschaft)','Landesbezirksleiter Bayern IGBCE','2024-05-16',23),
 ('Bodo Uebber','Mitglied','Anteilseigner','Selbstständiger Unternehmensberater','2019-05-09',23),
 ('Jing Ulrich','Mitglied','Anteilseigner','Managing Director und Vice Chairman Investment Banking, JPMorgan Chase','2019-05-09',23),
 ('Günter Weigl','Mitglied','Arbeitnehmer','Senior Vice President Brand Partnerships, adidas AG','2019-05-09',23)]
for n,f,v,b,s,sp in AR:
    M(G,'Aufsichtsrat',n,f,v,s,'',sp,b)
X(G,'Birgit Biermann','a','Merck KGaA','Darmstadt','Mitglied des Aufsichtsrats','seit 2025-05-22',21)
X(G,'Birgit Biermann','a','Lanxess AG','Köln','Mitglied des Aufsichtsrats','seit 2025-05-22',21)
X(G,'Harald Sikorski','a','Wacker Chemie AG','München','Mitglied des Aufsichtsrats','',23)
X(G,'Bodo Uebber','a','Flix SE','München','Vorsitzender des Aufsichtsrats','',23)
X(G,'Christian Klein','a','SAP SE','Walldorf','Vorstandssprecher (CEO)','',22,'Vorstand, kein Kontrollgremium')
K(G,'vorstand_mitglieder_zahl',4,'Personen',43)
K(G,'vorstand_frauen_zahl',1,'Personen',43,'Michelle Robertson (Vorstandsmitglied), laut Diversitätsangabe mind. eine Frau')
K(G,'ar_mitglieder_zahl',16,'Personen',44,'8 Anteilseigner, 8 Arbeitnehmer')
K(G,'ar_frauen_zahl',4,'Personen',44,'je zwei Frauen auf Anteilseigner- und Arbeitnehmerseite')
K(G,'ar_arbeitnehmervertreter_zahl',8,'Personen',21,'mit * gekennzeichnet')
K(G,'ar_gewerkschaftsvertreter_zahl',2,'Personen',21,'Biermann (IGBCE-Hauptvorstand), Sikorski (IGBCE Landesbezirksleiter)')
K(G,'mitbestimmung_ar','paritätisch (MitbestG), 8 von 16 Arbeitnehmervertreter','',44)
K(R,'pay_ratio','','',4,'kein Verhältniswert; nur Vertikalvergleich (Entwicklung)')
