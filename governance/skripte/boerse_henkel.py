from lib import *
U = 'U000279'
G = ('governance/dokumente/henkel-ag-und-co-kgaa/geschaeftsbericht-2025.pdf', U)
R = ('governance/dokumente/henkel-ag-und-co-kgaa/verguetungsbericht-2025.pdf', U)
uni('BASF SE','U000061'); uni('RWE AG','U000510'); uni('Siemens Energy','U000537'); uni('Orange S.A.','')
# Vorstand (Mitglieder des Vorstands der Henkel Management AG, persönlich haftende Gesellschafterin); Geschlecht lt. Vergütungsbericht-Tabelle
for n,f,s,sp,t in [('Carsten Knobel','Vorsitzender','2012-07-01',14,5099.283),('Mark Dorn','Mitglied (Adhesive Technologies)','2023-02-01',14,2953.686),
                   ('Wolfgang König','Mitglied (Consumer Brands)','2021-06-01',14,3524.202),('Sylvie Nicol','Mitglied','2019-04-09',15,3454.378),
                   ('Marco Swoboda','Mitglied','2020-01-01',15,2995.990)]:
    M(G,'Vorstand',n,f,'',s,'',sp if False else 61,'','Mitglied des Vorstands der Henkel Management AG; Seit-Datum lt. Vergütungsbericht S. %d' % sp)
    V(R,'Vorstand',n,t,'Summe gewährte und geschuldete Vergütung § 162 AktG (Komponenten 1-5, ohne Kapitalbausteine)',sp,'Kapitalbausteine (Altersversorgung) nicht enthalten: Knobel 750, Swoboda 450 T€')
V(R,'Vorstand','Gesamt (alle Mitglieder)',18027.539,'Summe gewährte und geschuldete Vergütung § 162 AktG',15)
# Aufsichtsrat der Henkel AG & Co. KGaA (16 Mitglieder, MitbestG 1976); * = Arbeitnehmervertreter; GB S. 461-463 (PDF)
AR=[('Dr. Simone Bagel-Trah','Vorsitzende','Anteilseigner','Unternehmerin','2008-04-14',461),
 ('Birgit Helten-Kindlein','stellv. Vorsitzende','Arbeitnehmer','Vorsitzende des Gesamtbetriebsrats und des Betriebsrats der Henkel AG & Co. KGaA, Standort Düsseldorf','2008-04-14',461),
 ('Michael Baumscheiper','Mitglied','Arbeitnehmer','Stellv. Vorsitzender des Gesamtbetriebsrats, Vorsitzender des Betriebsrats Standort Hamburg','2020-12-11',461),
 ('Dr. Konstantin Benda','Mitglied','Arbeitnehmer (leitende Angestellte)','Chemiker, Transaction Manager, Vorsitzender des Sprecherausschusses','2023-04-24',461),
 ('Lutz Bunnenberg','Mitglied','Anteilseigner','Unternehmer','2020-06-17',461),
 ('Sabine Friedrich','Mitglied','Arbeitnehmer','Assistenz und Produktmanagement Produktentwicklung Industrials EIMEA, Mitglied des Betriebsrats','2023-09-23',461),
 ('Vinzenz Peter Gruber','Mitglied','Anteilseigner','Ehemals Executive Vice President & President Mondelez Europe','2024-04-22',461),
 ('Barbara Kux','Mitglied','Anteilseigner','Unternehmerin','2013-07-03',462),
 ('Laurent Martinez','Mitglied','Anteilseigner','Finanzvorstand Orange S.A.','2023-04-24',462),
 ('Dr. Anja Langenbucher','Mitglied','Anteilseigner','Direktorin für Europa, Bill & Melinda Gates Stiftung','2024-04-22',462),
 ('Simone Menne','Mitglied','Anteilseigner','Unternehmerin','2020-06-17',462),
 ('Benedikt-Richard Freiherr von Herman','Mitglied','Anteilseigner','Unternehmer','2016-04-11',462),
 ('Natalie Mühlenfeld','Mitglied','Arbeitnehmer (Gewerkschaft)','Bezirksleiterin IGBCE, Bezirk Köln-Bonn','2025-01-31',462),
 ('Dirk Thiede','Mitglied','Arbeitnehmer','Mitglied des Betriebsrats, Standort Düsseldorf','2018-04-09',462),
 ('Edgar Topsch','Mitglied','Arbeitnehmer','Mitglied des Gesamtbetriebsrats, stellv. Vorsitzender des Betriebsrats Düsseldorf','2010-08-01',462),
 ('Michael Vassiliadis','Mitglied','Arbeitnehmer (Gewerkschaft)','Vorsitzender der IG BCE','2018-04-09',462)]
for n,f,v,b,s,sp in AR: M(G,'Aufsichtsrat',n,f,v,s,'',sp,b)
# Gesellschafterausschuss (10 Mitglieder, GB S. 56-57 und 461)
for n,f in [('Dr. Simone Bagel-Trah','Vorsitzende'),('Dr. Paul Achleitner','Mitglied'),('Sabrina Soussan','Mitglied'),('Poul Weihrauch','Mitglied'),
            ('Konstantin von Unger','Mitglied (Vorsitz Finanzausschuss)'),('Dr. Christoph Kneip','Mitglied (stellv. Vorsitz Finanzausschuss)'),
            ('Dr. Kaspar von Braun','Mitglied (stellv. Vorsitz Personalausschuss)'),('Alexander Birken','Mitglied'),('Dr. h.c. Thomas Manchot','Mitglied'),('Jean-François van Boxmeer','Mitglied')]:
    M(G,'Gesellschafterausschuss',n,f,'Anteilseigner','','',56,'','Namen aus Beschreibung der Ausschüsse; Gesellschafterausschuss hat 10 Mitglieder (GB S. 56)')
# externe Mandate laut Gremienübersicht GB S. 461-462 (a = gesetzlich zu bildende inländische AR, b = vergleichbare Kontrollgremien)
for n,t,g,fk,sp in [('Dr. Simone Bagel-Trah','a','Henkel Management AG','Vorsitz',461),('Dr. Simone Bagel-Trah','a','Heraeus Holding GmbH','',461),('Dr. Simone Bagel-Trah','b','Chanel Ltd., Großbritannien','',461),
    ('Laurent Martinez','b','BuyIn S.A., Belgien','',462),('Laurent Martinez','b','MasOrange S.L., Spanien','',462),('Laurent Martinez','b','Orange MEA S.A., Frankreich','',462),('Laurent Martinez','b','Orange Polska S.A., Polen','',462),
    ('Dr. Anja Langenbucher','b','Sofina SA, Belgien','',462),('Simone Menne','b','Johnson Controls International plc., Irland','',462),('Simone Menne','b','Russell Reynolds Associates Inc., USA','',462),('Simone Menne','a','Siemens Energy','',462),
    ('Natalie Mühlenfeld','a','BASF SE','',462),('Natalie Mühlenfeld','a','Solventum Germany GmbH','',462),
    ('Michael Vassiliadis','a','BASF SE','',462),('Michael Vassiliadis','a','RAG AG','stellv. Vorsitz',462),('Michael Vassiliadis','a','RWE AG','stellv. Vorsitz',462),('Michael Vassiliadis','a','STEAG GmbH','',462),('Michael Vassiliadis','a','Vivawest GmbH','',462)]:
    X(G,n,t,g,'',fk,'',sp)
K(G,'vorstand_mitglieder_zahl',5,'Personen',61,'Vorstand der Henkel Management AG, 4 Männer und 1 Frau')
K(G,'vorstand_frauen_zahl',1,'Personen',61,'20 %; Sylvie Nicol (w) lt. Vergütungsbericht S. 15')
K(G,'ar_mitglieder_zahl',16,'Personen',61,'8 Anteilseigner, 8 Arbeitnehmer')
K(G,'ar_frauen_zahl',7,'Personen',61,'44 %; je 4 Frauen Anteilseigner, 3 Frauen Arbeitnehmer')
K(G,'ar_arbeitnehmervertreter_zahl',8,'Personen',461)
K(G,'ar_gewerkschaftsvertreter_zahl',2,'Personen',462,'Mühlenfeld (IGBCE Bezirksleiterin), Vassiliadis (Vorsitzender IGBCE)')
K(G,'mitbestimmung_ar','paritätisch (MitbestG 1976), 8 von 16 Arbeitnehmervertreter','',61)
K(G,'gesellschafterausschuss_mitglieder_zahl',10,'Personen',56,'Henkel AG & Co. KGaA: Gesellschafterausschuss ersetzt teilweise Hauptversammlungsrechte')
K(R,'pay_ratio','','',56,'kein Verhältniswert; Ø-Vergütung Gesamtbelegschaft Deutschland 105.283 € (2025) in vergleichender Darstellung')
