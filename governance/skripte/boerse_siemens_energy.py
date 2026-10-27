from lib import *
G = ('governance/dokumente/siemens-energy-ag/geschaeftsbericht-2025.pdf', 'U000537')
R = ('governance/dokumente/siemens-energy-ag/verguetungsbericht-2025.pdf', 'U000537')
uni('Daimler Truck Holding AG','U000133'); uni('Salzgitter AG','U000512'); uni('Covestro AG',''); uni('MTU Aero Engines AG','U000415')
uni('thyssenkrupp AG','U000655'); uni('ThyssenKrupp AG','U000655'); uni('Traton SE','U000668'); uni('Henkel AG & Co. KGaA','U000279'); uni('Vonovia SE','U000716')
uni('Siemens Healthineers AG','U000538'); uni('Deutsche Bank AG','U000148'); uni('Rheinmetall AG','U000502'); uni('Airbus SE','U000026')
uni('Frankfurter Allgemeine Zeitung GmbH','')
# Geschäftsjahr 2025 = 1.10.2024 - 30.9.2025
for n,f,t24,t25,sp in [('Dr.-Ing. Christian Bruch','Vorsitzender (CEO)',2121,6605,12),('Maria Ferraro','Mitglied',1154,3896,12),('Tim Holt','Mitglied',1161,3860,13),
                       ('Karim Amin','Mitglied',1082,3354,13),('Anne-Laure de Chammard','Mitglied',1000,2989,14),('Vinod Philip','Mitglied',942,2875,14)]:
    M(G,'Vorstand',n,f,'','','',4)
    V(R,'Vorstand',n,t25,'Gesamtvergütung GJ 2025 (Okt 2024 bis Sep 2025), § 162 AktG',sp,f'Vorjahr {t24}')
AR = [('Joe Kaeser','Vorsitzender','Anteilseigner','Vorsitzender des Aufsichtsrats Siemens Energy AG und Daimler Truck Holding AG','2020-09-25'),
 ('Robert Kensbock','1. stellv. Vorsitzender','Arbeitnehmer','Vorsitzender des Zentralbetriebsrats Siemens Energy Global GmbH & Co. KG','2020-11-10'),
 ('Dr. Hubert Lienhard','2. stellv. Vorsitzender','Anteilseigner','Aufsichtsratsmitglied verschiedener deutscher Unternehmen','2020-09-25'),
 ('Günter Augustat','Mitglied','Arbeitnehmer','Vorsitzender des Konzernbetriebsrats Siemens Energy AG','2020-11-10'),
 ('Manfred Bäreis','Mitglied','Arbeitnehmer','Betriebsratsvorsitzender Siemens Energy Global GmbH & Co. KG','2020-11-10'),
 ('Manuel Bloemers','Mitglied','Arbeitnehmer (Gewerkschaft)','Gewerkschaftssekretär im Vorstand der IG Metall, Verwaltungsstelle Düsseldorf','2022-09-01'),
 ('Dr. Christine Bortenlänger','Mitglied','Anteilseigner','Mitglied verschiedener Aufsichtsräte','2020-09-25'),
 ('Anja-Isabel Dotzenrath','Mitglied','Anteilseigner','Mitglied verschiedener Aufsichtsräte','2025-02-20'),
 ('Dr. Andrea Fehrmann','Mitglied','Arbeitnehmer (Gewerkschaft)','Gewerkschaftssekretärin IG Metall, Bezirksleitung Bayern','2020-11-10'),
 ('Dr. Andreas Feldmüller','Mitglied','Arbeitnehmer','Expert Community Manager; Vorsitzender des Zentralen Sprecherausschusses','2020-11-10'),
 ('Nadine Florian','Mitglied','Arbeitnehmer','Vorsitzende des Europäischen Betriebsrats Siemens Energy; Betriebsratsvorsitzende Duisburg','2020-11-10'),
 ('Prof. Sigmar Gabriel','Mitglied','Anteilseigner','Bundesminister a. D., Autor, Publizist','2020-09-25'),
 ('Prof. Dr. Veronika Grimm','Mitglied','Anteilseigner','Universitätsprofessorin','2024-02-26'),
 ('Jürgen Kerner','Mitglied','Arbeitnehmer (Gewerkschaft)','Zweiter Vorsitzender der IG Metall','2020-11-10'),
 ('Simone Menne','Mitglied','Anteilseigner','Mitglied verschiedener Aufsichtsräte','2024-02-26'),
 ('Hildegard Müller','Mitglied','Anteilseigner','Präsidentin des Verbands der Automobilindustrie (VDA) e.V.','2020-09-25'),
 ('Laurence Mulliez','Mitglied','Anteilseigner','Chair of the Board of Voltalia SA','2020-09-25'),
 ('Thomas Pfann','Mitglied','Arbeitnehmer','Betriebsratsvorsitzender Nürnberg K; stellv. Vorsitzender Konzernbetriebsrat','2022-09-01'),
 ('Matthias Rebellius','Mitglied','Anteilseigner','Mitglied des Vorstands Siemens AG, CEO Smart Infrastructure','2020-09-25'),
 ('Cornelia Schau','Mitglied','Arbeitnehmer','Stellv. Betriebsratsvorsitzende Erlangen, Siemens Energy Global GmbH & Co. KG','2024-02-26'),
 ('Geisha Jimenez Williams','Mitglied','Anteilseigner','Independent Board member verschiedener US-Unternehmen','2020-09-25'),
 ('Prof. Dr. Feiyu Xu','Mitglied','Anteilseigner','Universitätsprofessorin','2025-02-20')]
for n,f,art,beruf,seit in AR:
    bis='2025-02-20' if n in('Dr. Christine Bortenlänger','Hildegard Müller') else ''
    M(G,'Aufsichtsrat',n,f,art,seit,bis,241 if AR.index((n,f,art,beruf,seit))<9 else (242 if AR.index((n,f,art,beruf,seit))<16 else 243),beruf,'Arbeitnehmervertreter laut Sternchen (*) im Verzeichnis; Stand 30.9.2025; Seit = Mitglied seit lt. Tabelle')
    W(G,n,beruf,'','lt. Dokument','Beruf laut Organverzeichnis',241)
MND = [('Joe Kaeser','Daimler Truck Holding AG','Vorsitz Aufsichtsrat (börsennotiert)'),('Joe Kaeser','Linde plc.','Mitglied (Irland, börsennotiert)'),
 ('Dr. Hubert Lienhard','EnBW Energie Baden-Württemberg AG','Mitglied Aufsichtsrat'),('Dr. Hubert Lienhard','Heraeus Holding GmbH','Mitglied'),('Dr. Hubert Lienhard','Kaefer Management SE','Mitglied'),('Dr. Hubert Lienhard','TransnetBW GmbH','Mitglied'),
 ('Manuel Bloemers','Salzgitter AG','Mitglied Aufsichtsrat (börsennotiert)'),('Dr. Christine Bortenlänger','Covestro AG','Mitglied (börsennotiert)'),('Dr. Christine Bortenlänger','MTU Aero Engines AG','Mitglied (börsennotiert)'),('Dr. Christine Bortenlänger','TÜV Süd AG','Mitglied'),
 ('Anja-Isabel Dotzenrath','BayWa r.e. AG','stellv. Vorsitz seit 2025-05-20'),
 ('Dr. Andrea Fehrmann','Airbus Defence and Space GmbH','Mitglied (bis 2025-04-01)'),('Dr. Andrea Fehrmann','Siemens AG','Mitglied (börsennotiert)'),('Dr. Andrea Fehrmann','Siemens Healthineers AG','Mitglied (börsennotiert)'),
 ('Prof. Sigmar Gabriel','Deutsche Bank AG','Mitglied (börsennotiert)'),('Prof. Sigmar Gabriel','Heristo AG','stellv. Vorsitz'),('Prof. Sigmar Gabriel','Rheinmetall AG','Mitglied seit 2025-05-13'),
 ('Jürgen Kerner','Airbus GmbH','Mitglied (bis 2024-12-31)'),('Jürgen Kerner','MAN Truck & Bus SE','stellv. Vorsitz'),('Jürgen Kerner','Siemens AG','Mitglied (börsennotiert)'),('Jürgen Kerner','ThyssenKrupp AG','stellv. Vorsitz (börsennotiert)'),('Jürgen Kerner','Traton SE','stellv. Vorsitz (börsennotiert)'),
 ('Simone Menne','Henkel AG & Co. KGaA','Mitglied (börsennotiert)'),('Simone Menne','International Airlines Group S.A.','Mitglied seit 2025-06-19 (Spanien)'),('Simone Menne','Johnson Controls International plc','Mitglied bis 2025-03-31 (Irland)'),('Simone Menne','Russell Reynolds Associates Inc.','Mitglied (USA)'),
 ('Hildegard Müller','RAG-Stiftung','Mitglied'),('Hildegard Müller','Vonovia SE','Mitglied (börsennotiert)'),('Hildegard Müller','Atos SE','Mitglied seit 2025-01-31 (Frankreich)'),
 ('Laurence Mulliez','Voltalia SA','Vorsitz (Frankreich, börsennotiert)'),('Laurence Mulliez','Globeleq Ltd.','Vorsitz bis 2025-08-11'),
 ('Matthias Rebellius','Siemens Schweiz AG','Vorsitz (Konzernmandat Siemens AG)'),
 ('Geisha Jimenez Williams','Artera Services LLC','Mitglied (USA)'),('Geisha Jimenez Williams','Meritage Homes Corp.','Mitglied seit 2025-01-06 (USA)'),('Geisha Jimenez Williams','Osmose Utility Services, Inc.','Vorsitz (USA)'),
 ('Prof. Dr. Feiyu Xu','Frankfurter Allgemeine Zeitung GmbH','Mitglied seit 2025-07-01'),('Prof. Dr. Feiyu Xu','ZF Friedrichshafen AG','Mitglied'),('Prof. Dr. Feiyu Xu','Airbus SE','Mitglied (Niederlande, börsennotiert)'),('Prof. Dr. Feiyu Xu','Chain IQ Group AG','Mitglied (Schweiz)'),('Prof. Dr. Feiyu Xu','Zühlke Group AG','Mitglied (Schweiz)')]
for n,g,f in MND: X(G,n,'a',g,'',f,'',241)
K(G,'vorstand_mitglieder_zahl',6,'Personen',4,'laut Vergütungsbericht GJ 2025')
K(G,'vorstand_frauen_zahl','','Personen',234,'Mindestbeteiligungsgebot (mind. 1 Frau) erfüllt; Zahl nicht genannt')
K(G,'ar_mitglieder_zahl',20,'Personen',230,'zehn Anteilseigner-, zehn Arbeitnehmervertreter (Codetermination Act)')
K(G,'ar_frauen_zahl',9,'Personen',237,'neun Frauen: sechs Anteilseignervertreterinnen, drei Arbeitnehmervertreterinnen = 45 % (Stand 30.9.2025)')
K(G,'ar_arbeitnehmervertreter_zahl',10,'Personen',243,'mit * gekennzeichnet')
K(G,'ar_gewerkschaftsvertreter_zahl',3,'Personen',241,'Bloemers, Fehrmann (IG Metall-Sekretäre), Kerner (2. Vorsitzender IG Metall); Zuordnung aus Beruf')
K(G,'mitbestimmung_ar','paritätisch nach MitbestG, 10 von 20 Arbeitnehmervertreter','',230,'"German Codetermination Act"')
K(R,'pay_ratio','','',4,'kein Zahlenwert: vertikaler Vergleich wird vom Aufsichtsrat intern ermittelt (Vergütungsbericht S. 4)')
