from lib import *
U = 'U000539'
R = ('governance/dokumente/siltronic-ag/geschaeftsbericht-2025.pdf', U)
uni('Siltronic AG', U)
# Geschäftsbericht 2025, Vergütungsbericht; Seiten = PDF-Seiten = Druckseiten; Beträge in T€ (gewährt und geschuldet, S. 169)
VS = [('Dr. Michael Heckmeier','Vorstandsvorsitzender (CEO)','',1554.518),('Claudia Schmitt','Finanzvorständin (CFO)','',1028.249),('Klaus Buchwald','Chief Operating Officer (COO)','2024-06-01',1014.848)]
for n,f,s,t in VS:
    M(R,'Vorstand',n,f,'',s,'',169,'','')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Festgehalt, Nebenleistungen, STI, LTI-Tranche 2025–2028)',169,'')
AR = [('Dr. Tobias Ohler','Vorsitzender','Anteilseignervertreter',160.0,''),('Michael Hankel','Stellvertretender Vorsitzender','Anteilseignervertreter',110.0,''),
 ('Jos Benschop','Mitglied','Anteilseignervertreter',60.0,''),('Sieglinde Feist','Mitglied','Anteilseignervertreter',60.0,''),('Mariella Röhm-Kottmann','Mitglied','Anteilseignervertreter',110.0,''),
 ('Andreas Pecher','Mitglied (seit 12.5.2025)','Anteilseignervertreter',40.0,''),('Dr. Hermann Gerlinger','Mitglied (bis 12.5.2025)','Anteilseignervertreter',25.0,''),
 ('Mandy Breyer','Mitglied','Arbeitnehmervertreter',60.0,'Fußnote 2: Arbeitnehmer-/Gewerkschaftsvertreter, Vergütung an gemeinnützige Einrichtungen abgeführt'),
 ('Günter Zellner','Mitglied','Arbeitnehmervertreter',60.0,'Fußnote 2: Arbeitnehmer-/Gewerkschaftsvertreter, Vergütung abgeführt'),
 ('Daniela Berer','Mitglied','Arbeitnehmervertreter',110.0,'Fußnote 2: Arbeitnehmer-/Gewerkschaftsvertreterin, Vergütung abgeführt'),
 ('Lina Ohltmann','Mitglied','Arbeitnehmervertreter',60.0,'Fußnote 2: Arbeitnehmer-/Gewerkschaftsvertreter, Vergütung abgeführt'),
 ('Volker Stapfer','Mitglied','Arbeitnehmervertreter',85.0,'Fußnote 2: Arbeitnehmer-/Gewerkschaftsvertreter, Vergütung abgeführt'),
 ('Klaus-Peter Estermaier','Mitglied','Vertreter der leitenden Angestellten',60.0,'Fußnote 1: Vertreter der Leitenden Angestellten (VAA-Abführungsregeln)')]
for n,f,seite,t,b in AR:
    M(R,'Aufsichtsrat',n,f,seite,'2025-05-12' if 'Pecher' in n else '','2025-05-12' if 'Gerlinger' in n else '',171,'',b)
    V(R,'Aufsichtsrat',n,t,'Aufsichtsratsvergütung 2025 inkl. Auslagenpauschale 10 T€ (anteilig bei Gerlinger/Pecher)',171,'')
K(R,'vorstand_mitglieder_zahl',3,'Personen',169,'drei aktive Mitglieder')
K(R,'ar_mitglieder_zahl',12,'Personen',171,'zwölf Mitglieder zum 31.12.2025 (Gerlinger bis 12.5., Pecher ab 12.5.2025)')
K(R,'ar_arbeitnehmervertreter_zahl',5,'Personen',171,'Fußnote 2 "Vertreter der Arbeitnehmer ... sowie Gewerkschaften": Breyer, Zellner, Berer, Ohltmann, Stapfer; zusätzlich ein Vertreter der leitenden Angestellten (Estermaier)')
K(R,'pay_ratio','','',172,'Ø Vergütung Arbeitnehmer Deutschland 74 T€ (2024: 79), Konzern 63 T€; keine ausgewiesene Pay Ratio')
