from lib import *
U = 'U000395'
G = ('governance/dokumente/mercedes-benz-group-ag/geschaeftsbericht-2025.txt', U)
uni('Mercedes-Benz Group AG', U)
# Quelle: Textfassung des Geschäftsberichts 2025 (keine PDF-Seiten); Seite = gedruckte Seitenzahl lt. Kopfzeile, +-1 möglich.
# Einzelvergütung aus dem Vergütungsbericht 2025 (PDF, englisch; Seiten = PDF-Seiten), Quelle R.
R = ('governance/dokumente/mercedes-benz-group-ag/verguetungsbericht-2025.pdf', U)
VS = [('Ola Källenius','Vorsitzender des Vorstands','Bestellung bis Mai 2029'),('Dr. Jörg Burzer','Chief Technology Officer, Entwicklung & Einkauf','Bestellung bis November 2029'),
 ('Mathias Geisen','Vertrieb & Kunde','Bestellung bis Januar 2028'),('Olaf Schick','Integrität, Governance & Nachhaltigkeit','Bestellung bis Oktober 2028'),
 ('Michael Schiebe','Produktion, Qualität & Supply Chain Management','Bestellung bis Dezember 2028'),('Britta Seeger','Personal & Arbeitsdirektorin','Bestellung bis Dezember 2029'),
 ('Oliver Thöne','Greater China','Bestellung bis Januar 2028'),('Harald Wilhelm','Finanzen & Controlling','Bestellung bis März 2027')]
for n,f,b in VS:
    M(G,'Vorstand',n,f,'',{'Mathias Geisen':'2025-02-01','Oliver Thöne':'2025-02-01','Olaf Schick':'2025-10-01','Michael Schiebe':'2025-12-01'}.get(n,''),'',8,'',b)
AR = [('Dr. Martin Brudermüller','Vorsitzender','Anteilseigner','Gewählt bis 2028'),('Ergun Lümali','stellv. Vorsitzender','Arbeitnehmer','Vorsitzender Konzernbetriebsrat; gewählt bis 2028'),
 ('Michael Bettag','Mitglied','Arbeitnehmer','Betriebsratsvorsitzender Niederlassung Nürnberg'),('Ben van Beurden','Mitglied','Anteilseigner','ehem. Vorstandsvorsitzender Shell plc'),
 ('Nadine Boguslawski','Mitglied','Arbeitnehmer (Gewerkschaft)','Hauptkassiererin der IG Metall'),('Liz Centoni','Mitglied','Anteilseigner','EVP und Chief Customer Experience Officer, Cisco'),
 ('Dame Veronica Anne (»Polly«) Courtice','Mitglied','Anteilseigner','ehem. Direktorin Univ. Cambridge Institute for Sustainability Leadership'),
 ('Sebastian Fay','Mitglied','Arbeitnehmer (Gewerkschaft)','Leiter Funktionsbereich Tarifpolitik und Handwerk, IG Metall Vorstand'),
 ('Marco Gobbetti','Mitglied','Anteilseigner','Executive Administrator Aeffe S.p.A.'),('Michael Häberle','Mitglied','Arbeitnehmer','stellv. Vorsitzender Konzernbetriebsrat'),
 ('Dr. Doris Höpke','Mitglied','Anteilseigner','Senior Advisor und Mediatorin'),('Timotheus Höttges','Mitglied','Anteilseigner','Vorsitzender des Vorstands Deutsche Telekom AG'),
 ('Olaf Koch','Mitglied','Anteilseigner','Partner und Managing Director Zintinus GmbH'),('Gabriela Neher-Merkel','Mitglied','Arbeitnehmer','Betriebsrätin Werk Rastatt'),
 ('Michael Peters','Mitglied','Arbeitnehmer','Betriebsratsvorsitzender Werk Bremen'),('Stefan Pierer','Mitglied','Anteilseigner','Vorsitzender des Vorstands Pierer Industrie AG'),
 ('Barbara Resch','Mitglied','Arbeitnehmer (Gewerkschaft)','IG Metall Bezirksleiterin Baden-Württemberg; seit 1.1.2025'),
 ('Pia Simon','Mitglied','Arbeitnehmer','Bereichsleiterin Corporate Audit; Vorsitzende Konzernsprecherausschuss'),
 ('Prof. Dr. Helene Svahn','Mitglied','Anteilseigner','Professorin Royal Institute of Technology, Schweden'),('Monika Tielsch','Mitglied','Arbeitnehmer','Betriebsrätin Werk Sindelfingen')]
for n,f,v,b in AR:
    M(G,'Aufsichtsrat',n,f,v,'2025-01-01' if 'Resch' in n else '','',18,b.split(';')[0],'Kennzeichnung Arbeitnehmervertreter (*) lt. Mitgliederliste; Gewerkschaft nach Funktion' if 'Arbeitnehmer' in v else '')
K(G,'vorstand_mitglieder_zahl',8,'Personen',8,'acht Mitglieder zum 31.12.2025')
K(G,'ar_mitglieder_zahl',20,'Personen',18,'MitbestG: 20 Mitglieder, je zur Hälfte Anteilseigner/Arbeitnehmer')
K(G,'ar_arbeitnehmervertreter_zahl',10,'Personen',385,'sieben Arbeitnehmer des Unternehmens und drei Gewerkschaftsvertreter')
K(G,'ar_gewerkschaftsvertreter_zahl',3,'Personen',385,'drei Vertreter von Gewerkschaften (IG Metall: Boguslawski, Fay, Resch)')
K(G,'ar_frauen_zahl',9,'Personen',184,'45 % Frauen im Aufsichtsrat zum 31.12.2025; Namen lt. Erklärung zur Unternehmensführung (S. 236 ff.): Centoni, Courtice, Höpke, Svahn (Anteilseigner), Boguslawski, Neher-Merkel, Simon, Tielsch, Resch (Arbeitnehmer)')
K(G,'ar_frauen_quote',45,'%',184,'Frauenanteil Aufsichtsrat 2025 (2024: 40 %)')
K(G,'vorstand_frauen_zahl',1,'Personen',236,'Britta Seeger zum 31.12.2025; Frauenanteil 12,5 % (2024: 37,5 %)')
K(G,'vorstand_frauen_quote',12.5,'%',184,'Frauenanteil Vorstand 2025 (2024: 37,5 %)')
K(G,'pay_ratio',135,'Verhältnis',184,'Vergütung der höchstbezahlten Einzelperson zum Median der jährlichen Gesamtvergütung aller Beschäftigten (x:1), 2025; 2024: 175')
K(G,'gender_pay_gap_konzern',3.9,'%',184,'unbereinigter Verdienstunterschied weiblich/männlich konzernweit, 2025 (2024: 4,8)')

# Einzelvergütung 2025 lt. Vergütungsbericht (Total remuneration in terms of Sect. 162 AktG, T€; ohne Dienstzeitaufwand)
VB = [('Ola Källenius',8214,32,'ganzjährig; inkl. Dienstzeitaufwand 8.782'),('Dr. Jörg Burzer',2424,32,'ganzjährig'),('Mathias Geisen',1730,33,'seit 1.2.2025'),
 ('Renata Jungo Brüngger',3792,33,'1.1.-30.11.2025; in vergleichender Darstellung (S. 44) 3.962'),('Sabine Kohleisen',695,34,'1.1.-30.4.2025; in vergleichender Darstellung (S. 44) 1.931'),
 ('Markus Schäfer',4057,34,'1.1.-30.11.2025; in vergleichender Darstellung (S. 44) 4.554'),('Olaf Schick',445,35,'seit 1.10.2025'),('Michael Schiebe',154,35,'seit 1.12.2025'),
 ('Britta Seeger',4149,36,'ganzjährig'),('Oliver Thöne',2104,36,'seit 1.2.2025'),('Hubertus Troska',3646,37,'1.1.-31.7.2025; in vergleichender Darstellung (S. 44) 4.097'),('Harald Wilhelm',4083,37,'ganzjährig')]
AUS = {'Renata Jungo Brüngger':('Personal & Arbeitsdirektorin (bis 30.11.2025)','2025-11-30'),'Sabine Kohleisen':('Human Relations & Labour Director (bis 30.4.2025)','2025-04-30'),
 'Markus Schäfer':('Chief Technology Officer, Development & Procurement (bis 30.11.2025)','2025-11-30'),'Hubertus Troska':('Greater China (bis 31.7.2025)','2025-07-31')}
for n,t,p,b in VB:
    if n in AUS:
        M(R,'Vorstand',n,AUS[n][0],'','',AUS[n][1],p,'','ausgeschieden 2025; nicht im Vorstand zum 31.12.2025')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Total remuneration in terms of Sect. 162 AktG)',p,b)
V(R,'Vorstand','Gesamt (alle 2025 aktiven Mitglieder)',35493,'Gesamtvergütung',44,'Summe der zwölf Einzelwerte aus den Individualtabellen; keine Gesamtzeile im Bericht')
ARV = [('Dr. Martin Brudermüller',600),('Ergun Lümali',475),('Michael Bettag',200),('Ben van Beurden',300),('Nadine Boguslawski',200),('Liz Centoni',400),('Dame Veronica Anne (»Polly«) Courtice',300),
 ('Sebastian Fay',400),('Marco Gobbetti',200),('Michael Häberle',300),('Dr. Doris Höpke',300),('Timotheus Höttges',400),('Olaf Koch',450),('Gabriela Neher-Merkel',200),('Michael Peters',200),
 ('Stefan Pierer',200),('Barbara Resch',293),('Pia Simon',200),('Prof. Dr. Helene Svahn',200),('Monika Tielsch',200)]
for n,t in ARV:
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Total remuneration)',42,'inkl. rückwirkend gezahlter Ausschussvergütung 2024' if 'Centoni' in n else '')
V(R,'Aufsichtsrat','Gesamt',6018,'Gesamtvergütung',42,'Summe der 20 Einzelwerte; keine Gesamtzeile im Bericht')
K(R,'pay_ratio_hinweis','','',44,'Vergütungsbericht nennt keine absolute Ø-Mitarbeitervergütung (nur relative Veränderung); Variante A nicht berechenbar, publizierte Pay Ratio 135 aus Geschäftsbericht')
