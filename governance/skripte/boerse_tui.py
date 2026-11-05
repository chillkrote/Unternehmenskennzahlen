from lib import *
U = 'U000670'
R = ('governance/dokumente/tui-ag/geschaeftsbericht-2025.pdf', U)
uni('TUI AG', U)
# Annual Report 2025 (englisch), Corporate Governance; Seiten = PDF-Seiten; Beträge in T€ (Total remuneration, S. 219–220)
VS = [('Sebastian Ebel','Vorsitzender des Vorstands (CEO)','2022-10-01',2704.6,219,'Pensionsaufwand IAS 19 in "granted and owed" nicht enthalten'),
 ('Mathias Kiep','Finanzvorstand (CFO)','2022-10-01',1401.7,219,''),('Peter Krueger','Vorstandsmitglied','2021-01-01',1585.1,219,''),
 ('Sybille Reiss','Vorstandsmitglied','2021-07-01',1585.1,220,''),('David Schelp','Vorstandsmitglied (CEO Markets + Airline)','2024-01-01',1401.7,220,'')]
for n,f,s,t,p,bem in VS:
    M(R,'Vorstand',n,f,'',s,'',219,'','Funktion lt. Tabelle "Granted and owed remuneration"')
    V(R,'Vorstand',n,t,'Total remuneration granted and owed gem. § 162 AktG (inkl. Pensionsbeitrag)',p,bem)
AR = [('Dr. Dieter Zetsche','Vorsitzender',False,376.0),('Frank Jakobi','Stellvertretender Vorsitzender',True,284.0),('Ingrid-Helen Arnold','Mitglied',False,97.0),
 ('Sonja Austermühle','Mitglied',True,130.5),('Christian Baier','Mitglied',False,146.0),('Andreas Barczewski','Mitglied',True,124.8),
 ('Dr. Jutta Dönges','Mitglied',False,249.7),('Wolfgang Flintermann','Mitglied',True,97.0),('María Garaña Corces','Mitglied',False,96.0),
 ('Stefan Heinemann','Mitglied',True,146.0),('Janina Kugel','Mitglied',False,97.0),('Johan Lundgren','Mitglied (seit 24.6.2025)',False,25.3),
 ('Coline McConville','Mitglied',False,127.8),('Helena Murano','Mitglied',False,97.0),('Mark Muratovic','Mitglied',True,160.9),
 ('Anette Strempel','Mitglied',True,145.0),('Rainald Thannisch','Mitglied (seit 6.1.2025)',True,71.3),('Joan Trían Riu','Mitglied',False,126.8),
 ('Tanja Viehl','Mitglied',True,97.0),('Stefan Weinhofer','Mitglied',True,146.0),
 ('Peter Bremme','Mitglied (bis 31.12.2024)',True,38.0),('Prof. Dr. Edgar Ernst','Mitglied (bis 11.2.2025)',False,104.9),('Pepijn Rijvers','Mitglied (11.2.–5.6.2025)',False,30.8)]
for n,f,an,t in AR:
    M(R,'Aufsichtsrat',n,f,'Arbeitnehmervertreter' if an else 'Anteilseignervertreter','','',225,'','Kennzeichnung "Employee representatives" (Fußnote 1)' if an else '')
    V(R,'Aufsichtsrat',n,t,'Granted and owed remuneration (Festvergütung, Ausschüsse, Sitzungsgeld, Konzernmandate)',228,'' if n!='Peter Bremme' else 'Vergütung zeitanteilig bis 31.12.2024 gezahlt')
K(R,'vorstand_mitglieder_zahl',5,'Personen',219,'fünf aktive Mitglieder')
K(R,'ar_mitglieder_zahl',20,'Personen',186,'paritätisch: zehn Anteilseigner-, zehn Arbeitnehmervertreter')
K(R,'ar_arbeitnehmervertreter_zahl',10,'Personen',225,'Fußnote "Employee representatives": Jakobi, Austermühle, Barczewski, Flintermann, Heinemann, Muratovic, Strempel, Thannisch, Viehl, Weinhofer')
K(R,'ar_gewerkschaftsvertreter_zahl',1,'Personen',183,'Rainald Thannisch (ver.di-Bundesverwaltung); weitere Gewerkschaftsvertreter im Bericht nicht gekennzeichnet')
K(R,'pay_ratio','','',221,'Keine absolute Ø-Vergütung ausgewiesen (nur Veränderung Belegschaft TUI AG +2 % ggü. Vorjahr, FTE)')
