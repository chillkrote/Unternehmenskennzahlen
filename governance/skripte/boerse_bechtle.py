from lib import *
U = 'U000071'
R = ('governance/dokumente/bechtle-ag/verguetungsbericht-2025.pdf', U)
uni('Bechtle AG', U)
# Vergütungsbericht 2025 (bechtle.com); Seiten = PDF-Seiten = Druckseiten; Beträge in T€ (gewährt und geschuldet, S. 18)
VS = [('Dr. Thomas Olemotz','Vorsitzender des Vorstands (CEO)','2007-03-01',5873.7),('Michael Guschlbauer','Vorstand Ländermärkte Deutschland, Österreich & Spezialisten','2009-01-01',2765.1),
 ('Antje Leminsky','Vorstand für Logistik, Financial Services & Nachhaltigkeitsmanagement','2024-02-01',1440.88),('Konstantin Ebert','Vorstand für Ländermärkte International','2024-01-01',1382.4)]
for n,f,s,t in VS:
    M(R,'Vorstand',n,f,'',s,'',18,'','')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Gesamtvergütung)',18,'')
M(R,'Vorstand','Jürgen Schäfer','Vorstand für IT-E-Commerce (ehemals)','','2009-01-01','2023-12-31',18,'','Vorstand bis 31.12.2023')
V(R,'Vorstand','Jürgen Schäfer',422.1,'Gewährte Vergütung aus langfristiger variabler Vergütung (ehemaliges Mitglied)',18,'')
AR = [('Klaus Winkler','Vorsitzender',False,426),('Kurt Dobitsch','Mitglied',False,118),('Dr. Lars Grünert','Mitglied',False,82),('Prof. Dr. Thomas Hess','Mitglied',False,142),
 ('Stephanie Holdt','Mitglied',False,84),('Elmar König','Mitglied',False,112),('Sandra Stegmann','Mitglied',False,120),('Klaus Straub','Mitglied',False,110),
 ('Uli Drautz','Stellvertretender Vorsitzender',True,213),('Jonas Berhe','Mitglied',True,78),('Julia Böttcher','Mitglied',True,84),('Christian Döngi','Mitglied',True,82),
 ('Daniela Eberle','Mitglied',True,120),('Christine Muhr','Mitglied',True,82),('Julia Randelshofer','Mitglied',True,84),('Anton Samija','Mitglied',True,84)]
for n,f,an,t in AR:
    M(R,'Aufsichtsrat',n,f,'Arbeitnehmervertreter' if an else 'Anteilseignervertreter','','',20,'','Zuordnung "Vertreter der Arbeitnehmer" in der Vergütungstabelle' if an else 'Zuordnung "Vertreter der Anteilseigner"')
    V(R,'Aufsichtsrat',n,t,'Gesamtvergütung Aufsichtsrat (Grund-, Ausschussvergütung, Sitzungsgeld)',20,'')
K(R,'vorstand_mitglieder_zahl',4,'Personen',18,'vier aktive Mitglieder; Schäfer ausgeschieden')
K(R,'ar_mitglieder_zahl',16,'Personen',20,'acht Anteilseigner- und acht Arbeitnehmervertreter')
K(R,'ar_arbeitnehmervertreter_zahl',8,'Personen',20,'Tabelle "Vertreter der Arbeitnehmer"')
K(R,'pay_ratio','','',22,'Ø Vergütung Arbeitnehmer (Konzernunternehmen Deutschland, Personalaufwand je FTE) 66,0 T€')
