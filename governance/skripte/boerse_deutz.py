from lib import *
U = 'U000163'
R = ('governance/dokumente/deutz-aktiengesellschaft/geschaeftsbericht-2025.pdf', U)
uni('DEUTZ Aktiengesellschaft', U)
# Geschäftsbericht 2025, Vergütungsbericht; Seiten = PDF-Seiten; Beträge in T€ (Gesamtvergütung gem. § 162 AktG ohne Altersversorgungsaufwand)
VS = [('Dr. Sebastian C. Schulte','Vorsitzender des Vorstands','',2399,''),('Dr.-Ing. Petra Mayer','Ordentliches Vorstandsmitglied','',1077,''),
 ('Dr.-Ing. Markus Müller','Ordentliches Vorstandsmitglied','2025-01-31',672,'Vorstandsvertrag endete 31.1.2025; Gesamt enthält LTI-Auszahlung 579 T€'),('Oliver Neu','Ordentliches Vorstandsmitglied','',955,'')]
for n,f,b,t,bem in VS:
    M(R,'Vorstand',n,f,'','',b,180,'','Funktion lt. Vergütungstabelle')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Gesamtvergütung)',180,bem)
V(R,'Vorstand (ehemalig)','Dr. Margarete Haase',49,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied)',182,'Vorstand bis 30.4.2018')
V(R,'Vorstand (ehemalig)','Dr.-Ing. Helmut Leube',67,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied)',182,'Vorstand bis 31.12.2016')
AR = [('Dr. Dietmar Voggenreiter','Vorsitzender',False,251.5,'',''),('Sabine Beutert','Stellvertretende Vorsitzende',True,182.0,'',''),('Dr. Fabian Dietrich','Mitglied (bis 30.11.2025)',True,63.2,'','2025-11-30'),
 ('Silvia Eidt','Mitglied (seit 9.12.2025)',True,4.8,'2025-12-09',''),('Helmut Ernst','Mitglied',False,69.0,'',''),('Melanie Freytag','Mitglied',True,74.0,'',''),
 ('Patricia Geibel-Conrad','Mitglied',False,146.0,'',''),('Ismail-Hilmi Kocer','Mitglied',True,69.0,'',''),('Gottfried Laengert','Mitglied',True,74.0,'',''),
 ('Dr.-Ing. Rudolf Maier','Mitglied',False,109.0,'',''),('Bernd Maierhofer','Mitglied',False,69.0,'',''),('Katja Olligschläger','Mitglied',True,104.0,'',''),('Hans-Jörg Schaller','Mitglied',True,69.0,'','')]
for n,f,an,t,s,b in AR:
    M(R,'Aufsichtsrat',n,f,'Arbeitnehmervertreter' if an else '',s,b,184,'','Kennzeichnung "AN" in der Vergütungstabelle' if an else '')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Grund-, Ausschussvergütung, Sitzungsgeld)',184,'')
V(R,'Aufsichtsrat','Gesamt',1284.5,'Gesamtvergütung',184,'Summenzeile')
K(R,'vorstand_mitglieder_zahl',4,'Personen',180,'vier Mitglieder im GJ 2025 (Müller bis 31.1.2025)')
K(R,'ar_arbeitnehmervertreter_zahl',8,'Personen',184,'acht Personen mit Kennzeichnung AN (inkl. unterjähriger Wechsel Dietrich/Eidt)')
K(R,'pay_ratio','','',182,'Kein Verhältnis und keine absolute Ø-Vergütung ausgewiesen (Belegschaft DEUTZ AG nur +7,0 % ggü. Vorjahr)')
