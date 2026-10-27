from lib import *
B = ('governance/dokumente/beiersdorf-aktiengesellschaft/geschaeftsbericht-2025.pdf', 'beiersdorf-aktiengesellschaft')
uni('Aurubis AG', 'aurubis-ag')
VS = [('Vincent Warnery','Vorsitzender (CEO)','Corporate Development & Strategy, Internal Audit, Supply Chain & Quality, R&D, Derma, Health Care, Communication, Sustainability, Japan','',''),
 ('Oswald Barckhahn','Mitglied','Europe, USA & Canada, Luxury','',''),
 ('Astrid Hermann','Mitglied (CFO)','Finance, Legal & Compliance, IT, tesa SE','',''),
 ('Nicola D. Lafrentz','Mitglied (CHRO, Arbeitsdirektorin)','Human Resources, General Services','',''),
 ('Grita Loebsack','Mitglied','NIVEA: Brand Management, Digital Marketing, Greater China/South Korea','',''),
 ('Ramon A. Mirt','Mitglied','Emerging Markets (Latin America, Africa, Asia ohne Greater China, Russia)','',''),
 ('Patrick Rasquinet','Mitglied','','','2025-06-30')]
for n,f,r,s,b in VS: M(B,'Vorstand',n,f,'',s,b,300,r)
X(B,'Astrid Hermann','a','tesa SE','Hamburg','stellv. Vorsitz (Konzern)','',300); X(B,'Astrid Hermann','b','Stora Enso Oyj','Finnland','Mitglied Aufsichtsrat (börsennotiert)','',300)
X(B,'Patrick Rasquinet','b','Silhouette International Schmied AG','Österreich','Mitglied Aufsichtsrat','',300)
AR = [('Prof. Dr. Reinhard Pöllath','Vorsitzender','Anteilseigner','Rechtsanwalt, P+P Pöllath + Partners'),
 ('Frédéric Pflanz','stellv. Vorsitzender','Anteilseigner','Managing Director/CFO, maxingvest GmbH & Co. KGaA'),
 ('Barbara Wentzel','stellv. Vorsitzende','Arbeitnehmer','Mitglied des Betriebsrats, Beiersdorf AG'),
 ('Donya-Florence Amer','Mitglied','Anteilseigner','Vorstand/CIO und CHRO, Hapag-Lloyd AG'),
 ('Hilde Cambier','Mitglied','Arbeitnehmer','Vice President Marketing New Product and Business Development, tesa Management Unit Consumer'),
 ('Hong Chow','Mitglied','Anteilseigner','Executive Vice President, Head of Product and Portfolio Strategy, Novo Nordisk A/S'),
 ('Wolfgang Herz','Mitglied','Anteilseigner','General Manager, Participia Holding GmbH'),
 ('Uta Kemmerich-Keil','Mitglied','Anteilseigner','Mitglied in Aufsichts-/Beiräten/Verwaltungsräten verschiedener Unternehmen'),
 ('Jan Koltze','Mitglied','Arbeitnehmer (Gewerkschaft)','Regional Head, Industriegewerkschaft Bergbau, Chemie, Energie (IG BCE)'),
 ('Olaf Papier','Mitglied','Arbeitnehmer','Vorsitzender des Betriebsrats, Beiersdorf AG'),
 ('Doris Robben','Mitglied','Arbeitnehmer','Stellv. Vorsitzende des Betriebsrats, tesa SE'),
 ('Kirstin Weiland','Mitglied','Arbeitnehmer','Process Engineer Converting, tesa Manufacturing Hamburg GmbH')]
for n,f,art,beruf in AR:
    M(B,'Aufsichtsrat',n,f,art,'','',298,beruf,'Arbeitnehmer-/Anteilseignerseite aus der Beschreibung der Funktion (Betriebsrat, Beschäftigte, Gewerkschaft) bzw. Angabe "sechs Arbeitnehmervertreter" S. 50')
    W(B,n,beruf,'','lt. Dokument','Beruf laut Organverzeichnis',298)
for n,t,g,s,f,gl in [('Wolfgang Herz','a','Blume2000 SE','','Vorsitz',''),('Wolfgang Herz','a','TOPP Holding AG','','Vorsitz',''),('Wolfgang Herz','a','maxingvest GmbH & Co. KGaA','','Mitglied',''),('Wolfgang Herz','a','TCHIBO GmbH','','Mitglied',''),
 ('Uta Kemmerich-Keil','a','Schott AG','','Mitglied',''),('Uta Kemmerich-Keil','a','Karo Healthcare AB','Schweden','Mitglied','bis 2025-08-27'),('Uta Kemmerich-Keil','b','Klosterfrau Zürich AG','Schweiz','Mitglied Verwaltungsrat',''),('Uta Kemmerich-Keil','b','British American Tobacco p.l.c.','Vereinigtes Königreich','Mitglied Board of Directors (börsennotiert)','seit 2025-02-17'),
 ('Jan Koltze','a','Aurubis AG','','Mitglied (börsennotiert)',''),('Jan Koltze','a','ExxonMobil Central Europe Holding GmbH','','Mitglied',''),('Jan Koltze','a','maxingvest GmbH & Co. KGaA','','Mitglied',''),
 ('Frédéric Pflanz','a','Mast-Jägermeister SE','','stellv. Vorsitz','seit 2025-04-02'),
 ('Prof. Dr. Reinhard Pöllath','a','Elektrobau Mulfingen GmbH & Co. KGaA','','Vorsitz',''),('Prof. Dr. Reinhard Pöllath','a','Wanzl GmbH & Co. KGaA','','Vorsitz','bis 2025-06-04'),('Prof. Dr. Reinhard Pöllath','a','Wanzl GmbH & Co. Holding KG','','Vorsitz','seit 2025-06-04'),
 ('Kirstin Weiland','a','tesa SE','Hamburg','Mitglied (Konzern)','')]:
    X(B,n,t,g,s,f,gl,298)
K(B,'vorstand_mitglieder_zahl',6,'Personen',50,'"The Beiersdorf Group Executive Board has six members" (2025); Rasquinet schied zum 30.6.2025 aus')
K(B,'vorstand_frauen_zahl',3,'Personen',50,'50 %: Astrid Hermann, Nicola D. Lafrentz, Grita Loebsack')
K(B,'ar_mitglieder_zahl',12,'Personen',50)
K(B,'ar_frauen_zahl',7,'Personen',50,'58 % von 12 laut Dokument ("58% were female")')
K(B,'ar_arbeitnehmervertreter_zahl',6,'Personen',50,'six members were employee representatives')
K(B,'ar_gewerkschaftsvertreter_zahl',1,'Personen',298,'Jan Koltze, Regional Head IG BCE')
K(B,'mitbestimmung_ar','paritätisch (6 von 12 Arbeitnehmervertreter)','',50,'Rechtsgrundlage (MitbestG) nicht wörtlich im Dokument; aus Besetzung abgeleitet')
K(B,'pay_ratio',125.83,'Verhältnis',137,'Jahreszielvergütung der höchstbezahlten Person zum Median aller Beschäftigten (nicht CEO-Bezug); Segmente: Consumer 132,54, tesa 108,55')
for n,t in [('Vincent Warnery',2411),('Oswald Barckhahn',855),('Astrid Hermann',1502),('Nicola D. Lafrentz',881),('Grita Loebsack',4193),('Ramon A. Mirt',1390),('Patrick Rasquinet',799)]:
    V(B,'Vorstand',n,t,'gewährte und geschuldete Vergütung § 162 Abs. 1 AktG',{'Vincent Warnery':338,'Oswald Barckhahn':338,'Astrid Hermann':339,'Nicola D. Lafrentz':339,'Grita Loebsack':340,'Ramon A. Mirt':341,'Patrick Rasquinet':342}[n],'Vorjahr 2024 siehe Dokument; Warnery 2024: 13.192')
