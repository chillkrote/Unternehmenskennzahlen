from lib import *
U = 'U000157'
R = ('governance/dokumente/deutsche-lufthansa-ag/geschaeftsbericht-2025.pdf', U)
uni('Deutsche Lufthansa AG', U)
# Annual Report 2025 (englisch), Vergütungsbericht Tabellen T217-T220; Seiten = PDF-Seiten; Beträge in T€ (Total remuneration as defined in Section 162 AktG, ohne Versorgungsaufwand)
VS = [('Carsten Spohr','Vorsitzender des Vorstands (Chairman of the Executive Board)','2011-01-01','',8259,381,'Vorstandsmitglied seit 1.1.2011, Vorsitzender seit 1.5.2014'),
 ('Michael Niggemann','Mitglied des Vorstands (Human Resources & Legal, Labour)','2020-01-01','',4030,381,''),
 ('Till Streichert','Mitglied des Vorstands (Finanzen)','2024-09-15','',3341,381,'enthält Ausgleichszahlung 563 T€ für verfallene Leistungen des früheren Arbeitgebers (Fußnote 2)'),
 ('Grazia Vittadini','Mitglied des Vorstands (Chief Technology Officer)','2024-07-01','',2104,382,''),
 ('Dieter Vranckx','Mitglied des Vorstands (Chief Commercial Officer)','2024-07-01','',2129,382,'')]
for n,f,s,b,t,p,bem in VS:
    M(R,'Vorstand',n,f,'',s,b,p,'','Funktion lt. Qualifikationsmatrix T048 und Tabelle T217')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Total remuneration as defined in Section 162 AktG)',p,bem)
for n,t,bem in [('Christina Foerster',1955,'Vorstand bis 30.6.2024; LTI 2022'),('Karl Ulrich Garnadt',133,'Vorstand bis 30.4.2017'),('Harry Hohmeister',2171,'Vorstand bis 30.6.2024'),('Detlef Kayser',5280,'Vorstand bis 30.6.2024; inkl. Pauschalabfindung Altersversorgung 3.322 T€'),('Simone Menne',2846,'Vorstand bis 31.8.2016; Pauschalzahlung Altersversorgung')]:
    V(R,'Vorstand (ehemalig)',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied, T218)',382,bem)
AR = [('Karl-Ludwig Kley','Vorsitzender',375,'',''),('Christine Behle','Stellvertretende Vorsitzende',175,'',''),('Tim Busse','Mitglied',100,'',''),('Erich Clementi','Mitglied',150,'',''),
 ('Thomas Enders','Mitglied (bis 6.5.2025)',60,'','2025-05-06'),('Karl Gernandt','Mitglied',166,'',''),('Sara Grubisic','Mitglied',125,'',''),('Sara Hennicken','Mitglied',133,'2024-05-07',''),
 ('Christian Hirsch','Mitglied',150,'',''),('Alexis von Hoensbroech','Mitglied (seit 6.5.2025)',66,'2025-05-06',''),('Jamila Jadran','Mitglied',100,'',''),('Arne Christian Karstens','Mitglied',150,'',''),
 ('Carsten Knobel','Mitglied',150,'',''),('Holger Benjamin Koch','Mitglied',150,'',''),('Harald Krüger','Mitglied',225,'',''),('Marvin Reschinsky','Mitglied',125,'',''),
 ('Birgit Rohleder','Mitglied',100,'',''),('Britta Seeger','Mitglied',100,'',''),('Astrid Stange','Mitglied',100,'',''),('Angela Titzrath','Mitglied',125,'',''),('Klaus Winkler','Mitglied',150,'','')]
for n,f,t,s,b in AR:
    M(R,'Aufsichtsrat',n,f,'',s,b,384,'','Zuordnung Anteilseigner-/Arbeitnehmerseite in der Vergütungstabelle nicht ausgewiesen')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Festvergütung und Ausschussvergütung, T219)',384,'')
V(R,'Aufsichtsrat','Gesamt',2975,'Gesamtvergütung',384,'Summenzeile T219')
K(R,'vorstand_mitglieder_zahl',5,'Personen',381,'fünf aktive Mitglieder 2025')
K(R,'ar_mitglieder_zahl',20,'Personen',114,'Aufsichtsrat aus 20 Personen: zehn Anteilseignervertreter und zehn Arbeitnehmervertreter (mitbestimmt)')
K(R,'ar_arbeitnehmervertreter_zahl',10,'Personen',114,'lt. Aufsichtsratsbeschreibung im Geschäftsbericht')
K(R,'pay_ratio','','',386,'Kein Verhältnis ausgewiesen; Ø-Vergütung Gesamtbelegschaft Deutschland (FTE, Lufthansa-Tarifkreis ohne CityLine) 93.114 EUR')
