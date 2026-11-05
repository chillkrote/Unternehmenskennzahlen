from lib import *
U = 'U000086'
R = ('governance/dokumente/bilfinger-se/verguetungsbericht-2025.pdf', U)
uni('Bilfinger SE', U)
# Vergütungsbericht 2025 (Robin-Upload); Seiten = PDF-Seiten = Druckseiten; Beträge in T€ (S. 8, ohne Versorgungsaufwand)
M(R,'Vorstand','Dr. Thomas Schulz','Vorsitzender des Vorstands (CEO)','','2022-03-01','',7,'','')
M(R,'Vorstand','Matti Jäkel','Mitglied des Vorstands (CFO)','','2022-07-01','',7,'','')
V(R,'Vorstand','Dr. Thomas Schulz',2899.0,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Grundgehalt, Nebenleistungen, Versorgungsentgelt, STI 2025)',8,'')
V(R,'Vorstand','Matti Jäkel',1541.0,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ohne Versorgungsaufwand 230 T€)',8,'')
# Aufsichtsrat S. 23 (Gesamtvergütung netto)
AR = [('Dr. Eckhard Cordes','Vorsitzender',240,'2014-11-05'),('Stephan Brückner','Stellvertretender Vorsitzender',195,'2008-05-21'),('Vanessa Barth','Mitglied',145,'2021-04-15'),
 ('Dr. Roland Busch','Mitglied',145,'2021-04-15'),('Evert Doornbos','Mitglied',146,'2025-01-01'),('Rainer Knerler','Mitglied',150,'1996-07-18'),('Frank Lutz','Mitglied',195,'2018-05-15'),
 ('Dr. Silke Maurer','Mitglied',96,'2021-04-15'),('Agnieszka Othman','Mitglied',96,'2016-09-07'),('Robert Schuchna','Mitglied',146,'2020-06-24'),('Jörg Sommer','Mitglied',145,'2016-05-11'),
 ('Dr. Bettina Volkens','Mitglied',145,'2020-06-24')]
for n,f,t,s in AR:
    M(R,'Aufsichtsrat',n,f,'',s,'',23 if s!='x' else 24,'','Mitglied seit lt. S. 24; Arbeitnehmer-/Anteilseignerseite im Bericht nicht gekennzeichnet')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Festvergütung, Ausschussvergütung, Sitzungsgeld; netto ohne USt)',23,'')
K(R,'vorstand_mitglieder_zahl',2,'Personen',7,'zwei Mitglieder')
K(R,'ar_mitglieder_zahl',12,'Personen',23,'zwölf Mitglieder')
K(R,'pay_ratio','','',21,'Keine absolute Ø-Vergütung ausgewiesen (nur Veränderung Arbeitnehmer Deutschland +4,5 %)')
