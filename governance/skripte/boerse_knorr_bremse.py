from lib import *
U = 'U000331'
R = ('governance/dokumente/knorr-bremse-ag/geschaeftsbericht-2025.pdf', U)
uni('Knorr-Bremse AG', U)
# Vergütungsbericht im Geschäftsbericht 2025 (Seiten = PDF-Seiten); Beträge in T€
VS = [('Marc Llistosella','Vorsitzender des Vorstands','2023-01-01','',5479,299),('Frank Markus Weber','Finanzvorstand (CFO)','2020-07-01','',3706,299),
 ('Dr. Claudia Mayfeld','Vorstand People & Integrity','2021-05-01','',3335,299),('Bernd Spies','Vorstand Division Systeme für Nutzfahrzeuge','2022-03-12','',3172,299),
 ('Dr. Nicolas Lange','Vorstand Division Systeme für Schienenfahrzeuge','2023-10-01','',3372,299)]
for n,f,s,b,t,p in VS:
    M(R,'Vorstand',n,f,'',s,b,p,'','Funktion/Eintritt lt. Vergütungstabelle 4.10')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Gesamt)',p,'')
for n,t,bem in [('Dr. Jürgen Wilder',342,'Vorstand bis 30.9.2023'),('Dr. Jan Mrosik',214,'Vorstand bis 30.4.2022'),('Klaus Deller',195,'Vorstand bis 30.4.2019'),('Dr. Dieter Wilhelm',262,'Vorstand bis 30.6.2016'),('Vor dem 31.12.2015 ausgeschiedene Mitglieder',295,'Sammelposten')]:
    V(R,'Vorstand (ehemalig)',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied)',300,bem)
# Aufsichtsrat Tab. 4.13; Fußnote 2: von den Mitarbeitenden gewählt
AR = [('Dr. Reinhard Ploss','Vorsitzender',False,486,'',''),('Franz-Josef Birkeneder','Stellvertretender Vorsitzender',True,276,'',''),
 ('Stephan Sturm','Stellvertretender Vorsitzender (seit 31.7.2025)',False,106,'2025-04-30',''),('Dr. Theodor Weimer','Stellvertretender Vorsitzender (bis 30.4.2025)',False,63,'','2025-04-30'),
 ('Kathrin Dahnke','Mitglied',False,235,'',''),('Manuela Deseive','Mitglied',True,108,'2025-01-01',''),('Thomas Mittmann','Mitglied',True,108,'2024-07-01',''),
 ('Dr. Sigrid Evelyn Nikutta','Mitglied',False,151,'',''),('Wolfgang Nirschl','Mitglied',True,154,'',''),('Werner Ratzisberger','Mitglied',True,181,'',''),
 ('Annemarie Sedlmair','Mitglied',True,108,'',''),('Dr. Stefan Sommer','Mitglied',False,229,'',''),('Julia Thiele-Schürhoff','Mitglied',False,151,'','')]
for n,f,an,t,s,b in AR:
    M(R,'Aufsichtsrat',n,f,'Arbeitnehmervertreter' if an else '',s,b,303,'','Fußnote 2 der Tabelle 4.13: von den Mitarbeitenden gewählt' if an else '')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Grund-, Ausschussvergütung, Sitzungsgeld)',303,'')
K(R,'vorstand_mitglieder_zahl',5,'Personen',299,'fünf aktive Mitglieder')
K(R,'ar_mitglieder_zahl',13,'Personen',303,'13 Mitglieder mit Vergütung 2025 (Weimer bis 30.4., Sturm ab 30.4.2025)')
K(R,'ar_arbeitnehmervertreter_zahl',6,'Personen',303,'Fußnote 2: Birkeneder, Deseive, Mittmann, Nirschl, Ratzisberger, Sedlmair von den Mitarbeitenden gewählt')
K(R,'pay_ratio','','',305,'Kein Verhältnis ausgewiesen; Ø-Gesamtvergütung Belegschaft Konzern Deutschland (FTE, Zufluss) 99 T€')
