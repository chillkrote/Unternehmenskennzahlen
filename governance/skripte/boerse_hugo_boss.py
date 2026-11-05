from lib import *
U = 'U000290'
R = ('governance/dokumente/hugo-boss-ag/geschaeftsbericht-2025.pdf', U)
uni('HUGO BOSS AG', U)
# Annual Report 2025 (englisch), Vergütungsbericht; Seiten = PDF-Seiten (gedruckte Seitenzahl + 1); Beträge in T€
for n,f,s,t in [('Daniel Grieder','Chairman of the Managing Board and CEO (Vorsitzender des Vorstands)','2021-06-01',5274),('Oliver Timm','CSO and Deputy CEO','2021-01-01',2926),('Yves Müller','CFO/COO','2017-12-01',2521)]:
    M(R,'Vorstand',n,f,'',s,'',204,'','Funktion lt. Vergütungstabelle')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Total compensation)',204,'')
for n,t,bem in [('Dr. Heiko Schäfer',158,'Vorstand 03/2020-05/2022; LTI-Auszahlung'),('Ingo Wilts',255,'Vorstand 08/2016-02/2022; LTI-Auszahlung')]:
    V(R,'Vorstand (ehemalig)',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied)',205,bem)
AR = [('Stephan Sturm','Chairman (seit 15.5.2025)','2025-05-15','',221),('Sinan Piskin','Deputy Chairman','','',230),('Iris Epple-Righi','Mitglied','','',110),
 ('Katharina Herzog','Mitglied','','',110),('Dr. Claudia Hülsken','Mitglied (seit 15.5.2025)','2025-05-15','',69),('Andreas Kurali','Mitglied (seit 15.5.2025)','2025-05-15','',88),
 ('Daniela Liburdi','Mitglied','','',129),('Luca Marzotto','Mitglied','','',153),('Laura Micati','Mitglied (seit 15.5.2025)','2025-05-15','',69),
 ('Michael Murray','Mitglied (seit 15.5.2025)','2025-05-15','',82),('Tanja Silvana Nitschke','Mitglied','','',110),('Christina Rosenberg','Mitglied','','',110),
 ('Andreas Flach','Mitglied (bis 15.5.2025)','','2025-05-15',41),('Gaetano Marzotto','Mitglied (bis 15.5.2025)','','2025-05-15',48),('Bernd Simbeck','Mitglied (bis 15.5.2025)','','2025-05-15',52),
 ('Robin J. Stalker','Mitglied (bis 15.5.2025)','','2025-05-15',52),('Hermann Waldemer','Vorsitzender (bis 15.5.2025)','','2025-05-15',129)]
for n,f,s,b,t in AR:
    M(R,'Aufsichtsrat',n,f,'',s,b,209,'','Anteilseigner-/Arbeitnehmerseite in der Tabelle nicht ausgewiesen')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Grundvergütung und Ausschussarbeit)',209,'')
K(R,'vorstand_mitglieder_zahl',3,'Personen',204,'drei aktive Mitglieder zum 31.12.2025')
K(R,'pay_ratio','','',210,'Kein Verhältnis und keine absolute Ø-Vergütung 2025 ausgewiesen (nur +2 % ggü. Vorjahr; Ø 2024: 53 T€, konzernweit, FTE)')
