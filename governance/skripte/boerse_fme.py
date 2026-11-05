from lib import *
U = 'U000233'
R = ('governance/dokumente/fresenius-medical-care-ag/geschaeftsbericht-2025.pdf', U)
uni('Fresenius Medical Care AG', U)
# Annual Report 2025 (englisch), Compensation Report; Seiten = PDF-Seiten; Beträge in T€ (Total compensation according to Section 162(1) Sent. 2 No. 1 AktG)
VS = [('Helen Giza','Chief Executive Officer, Vorsitz des Vorstands (Chair of the Management Board)','2019-11-01','',6457,226,'enthält 3.236 T€ Barauszahlung wegen rückwirkender Aufhebung der Pensionszusage (Fußnote 2); mit Pension Cancellation 3.858 T€'),
 ('Craig Cordola, EdD','Chief Executive Officer for Care Delivery','2024-01-01','',3247,226,''),
 ('Martin Fischer','Chief Financial Officer','2023-10-01','',2180,226,''),
 ('Dr. Jörg Häring','Legal, Compliance and Human Resources','2024-06-01','',1649,227,''),
 ('Franklin W. Maddux, MD','Global Chief Medical Officer','2020-01-01','2025-12-31',4165,227,'enthält 2.151 T€ Barauszahlung wegen Aufhebung der Pensionszusage; Ausscheiden Ende GJ 2025'),
 ('Dr. Katarzyna Mazur-Hofsäß','Chief Executive Officer for Care Enablement','2018-09-01','2025-12-31',1835,227,'Ausscheiden Ende GJ 2025')]
for n,f,s,b,t,p,bem in VS:
    M(R,'Vorstand',n,f,'',s,b,p,'','Funktion/Eintritt lt. Tabelle 3.28')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Total compensation Sec. 162 (1) S. 2 Nr. 1)',p,bem)
for n,t,bem in [('Michael Brosnan',382,'Vorstand bis 31.10.2019; Pension'),('Roberto Fusté',337,'Vorstand bis 31.3.2016; Pension'),('Ronald Kuerbitz',130,'Vorstand bis 17.2.2017; Pension'),
 ('Rice Powell',837,'Vorstand bis 31.12.2022; Pension und LTI'),('William Valle',167,'Vorstand bis 31.12.2023'),('Kent Wanzek',278,'Vorstand bis 31.12.2021; Pension')]:
    V(R,'Vorstand (ehemalig)',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied, Tab. 3.34)',235,bem)
AR = [('Michael Sen','Vorsitzender',530),('Stefanie Balling','Stellvertretende Vorsitzende (seit 14.3.2024)',365),('Ralf Erkens','Mitglied',225),('Beate Haßdenteufel','Mitglied',170),
 ('Sara Hennicken','Mitglied',210),('Regina Karsch','Mitglied',210),('Shervin J. Korangy','Mitglied',250),('Dr. Marcus Kuhnert','Mitglied (Vorsitzender Prüfungsausschuss)',335),
 ('Frank Michael Prescher','Mitglied',225),('Gregory Sorensen, MD','Mitglied',225),('Dr. Manuela Stauss-Grabo','Mitglied',210),('Pascale Witz','Mitglied',290)]
for n,f,t in AR:
    M(R,'Aufsichtsrat',n,f,'','','',236,'','Arbeitnehmerseite im Bericht nicht ausgewiesen')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Aufsichtsrat und Ausschüsse, Tab. 3.35)',236,'')
V(R,'Aufsichtsrat','Gesamt',3245,'Gesamtvergütung',236,'Summenzeile Tabelle 3.35')
K(R,'vorstand_mitglieder_zahl',6,'Personen',226,'sechs Mitglieder im GJ 2025')
K(R,'ar_mitglieder_zahl',12,'Personen',236,'zwölf vergütete Mitglieder')
K(R,'pay_ratio',106.1,'Verhältnis',238,'CEO pay ratio (CEO im Amt zum Jahresende zu Ø-Vergütung aller Beschäftigten, FTE, weltweit) 106:1 (2024: 61:1); Anstieg wegen Barauszahlung für aufgehobene Pensionszusage; Ø-Vergütung 60,7 T€')
