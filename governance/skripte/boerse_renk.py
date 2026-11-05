from lib import *
U = 'U000500'
R = ('governance/dokumente/renk-group-ag/geschaeftsbericht-2025.pdf', U)
uni('RENK Group AG', U)
# Geschäftsbericht 2025, Vergütungsbericht (Abschnitt C); Seiten = PDF-Seiten; Beträge in T€ (gewährt und geschuldet, S. 257)
VS = [('Dr. Alexander Sagel','Vorsitzender des Vorstands (CEO, seit 1.2.2025)','2025-02-01','',1306,'zuvor 2024 Vorstandsmitglied'),('Anja Mänz-Siebje','CFO','','',903,''),
 ('Dr. Emmerich Schiller','COO (seit 1.3.2025)','2025-03-01','',653,'zeitanteilig'),('Susanne Wiegand','Vorsitzende des Vorstands (CEO, bis 31.1.2025)','','2025-01-31',143,'zeitanteilig')]
for n,f,s,b,t,bem in VS:
    M(R,'Vorstand',n,f,'',s,b,257,'','Funktion lt. Abschnitt 1.1.2 Ziel-Gesamtvergütung')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Gesamt)',257,bem)
AR = [('Claus von Hermann','Vorsitzender',False,147),('Karin Sonnenmoser','Mitglied',False,91),('Doreen Nowotne','Mitglied',False,107),('Florian Hohenwarter','Mitglied',False,64),
 ('Johannes Meier','Mitglied',False,87),('Klaus Stahlmann','Mitglied',False,64),('Klaus Refle','Stellvertretender Vorsitzender',True,117),('Sascha Dudzik','Mitglied',True,76),
 ('Lothar Evers','Mitglied',True,64),('Adela Lieb','Mitglied',True,64),('Ferdije Rracaj','Mitglied',True,75),('Mario Sommer','Mitglied',True,64)]
for n,f,an,t in AR:
    M(R,'Aufsichtsrat',n,f,'Arbeitnehmervertreter' if an else 'Anteilseignervertreter','','',256,'','Gliederung "Arbeitnehmervertreter" in der Vergütungstabelle' if an else 'Gliederung "Anteilseigenervertreter" in der Vergütungstabelle')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Festvergütung, Ausschuss, Sitzungsgeld)',256,'')
K(R,'vorstand_mitglieder_zahl',4,'Personen',257,'vier im GJ 2025 tätige Mitglieder (Wechsel Wiegand/Sagel)')
K(R,'ar_mitglieder_zahl',12,'Personen',256,'sechs Anteilseigner- und sechs Arbeitnehmervertreter')
K(R,'ar_arbeitnehmervertreter_zahl',6,'Personen',256,'Tabelle "Arbeitnehmervertreter"; fünf davon führen Vergütung teilweise an die Hans-Böckler-Stiftung ab (IG Metall)')
K(R,'pay_ratio','','',257,'Kein Verhältnis und keine absolute Ø-Vergütung ausgewiesen (Belegschaft nur Veränderungen: 2024/2025 nicht angegeben)')
