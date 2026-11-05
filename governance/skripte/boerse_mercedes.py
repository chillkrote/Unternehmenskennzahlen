from lib import *
U = 'U000395'
G = ('governance/dokumente/mercedes-benz-group-ag/geschaeftsbericht-2025.txt', U)
uni('Mercedes-Benz Group AG', U)
# Quelle: Textfassung des Geschäftsberichts 2025 (keine PDF-Seiten); Seite = gedruckte Seitenzahl lt. Kopfzeile, +-1 möglich.
# Der Vergütungsbericht 2025 (§ 162 AktG) liegt nicht im Repo -> keine Einzelvergütung erfasst (siehe OFFENE_PUNKTE.md).
VS = [('Ola Källenius','Vorsitzender des Vorstands','Bestellung bis Mai 2029'),('Dr. Jörg Burzer','Chief Technology Officer, Entwicklung & Einkauf','Bestellung bis November 2029'),
 ('Mathias Geisen','Vertrieb & Kunde','Bestellung bis Januar 2028'),('Olaf Schick','Integrität, Governance & Nachhaltigkeit','Bestellung bis Oktober 2028'),
 ('Michael Schiebe','Produktion, Qualität & Supply Chain Management','Bestellung bis Dezember 2028'),('Britta Seeger','Personal & Arbeitsdirektorin','Bestellung bis Dezember 2029'),
 ('Oliver Thöne','Greater China','Bestellung bis Januar 2028'),('Harald Wilhelm','Finanzen & Controlling','Bestellung bis März 2027')]
for n,f,b in VS:
    M(G,'Vorstand',n,f,'','','',8,'',b)
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
