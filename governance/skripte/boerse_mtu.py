from lib import *
G = ('governance/dokumente/mtu-aero-engines-ag/geschaeftsbericht-2025.pdf', 'mtu-aero-engines-ag')
R = ('governance/dokumente/mtu-aero-engines-ag/verguetungsbericht-2025.pdf', 'mtu-aero-engines-ag')
for n,f,s,b,t in [('Lars Wagner','Vorsitzender (bis 31.8.2025)','','2025-08-31',2221.838),('Dr. Johannes Bussmann','Vorsitzender (seit 1.9.2025)','2025-07-15','',1724.664),
 ('Peter Kameritsch','Finanzen und IT','','2025-06-30',877.217),('Katja Garcia Vila','Finanzen und IT','2025-04-01','',1482.402),('Dr. Silke Maurer','OEM / Operations','','',1956.312),('Michael Schreyögg','Programme','','',1778.143)]:
    M(G,'Vorstand',n,f,'',s,b,18,'','Funktion lt. Vergütungsbericht S. 18')
    V(R,'Vorstand',n,t,'Summe gewährte und geschuldete Vergütung § 162 AktG (ohne Versorgungsaufwand)',18,'zeitanteilig bei unterjährigem Eintritt/Austritt')
V(R,'Vorstand','Gesamt (alle Mitglieder)',10040.575,'Summe gewährte und geschuldete Vergütung',18)
for n in ['Gordon Riske','Josef Mailer','Kai Eisenblätter','Dr. Christine Bortenlänger','Daniele Frijia','Dr.-Ing. Marc Haltrich','Anita Heimerl','Dr. Detlef Kayser','Dr. Rainer Martens','Claudia Sowa-Frank','Dr. Peter Weckesser','Ute Wolf']:
    M(G,'Aufsichtsrat',n,'Mitglied','','','',238,'','Qualifikationsmatrix S. 238; Zuordnung Anteilseigner/Arbeitnehmer und Funktionen (Vorsitz) aus den ausgewerteten Seiten nicht eindeutig, nachzutragen')
uni('MTU Aero Engines AG','mtu-aero-engines-ag')
K(G,'vorstand_mitglieder_zahl',4,'Personen',3,'Stand nach Wechseln 2025: Bussmann, Garcia Vila, Maurer, Schreyögg (Pfänder ab 1.1.2026) - Zahl aus Namen im Vergütungsbericht, nicht ausdrücklich genannt')
K(G,'ar_mitglieder_zahl',12,'Personen',236,'je sechs Vertreter der Anteilseigner und der Arbeitnehmer')
K(G,'ar_frauen_zahl',4,'Personen',239,'Bortenlänger, Heimerl, Sowa-Frank, Wolf = 33,3 %; zwei Arbeitnehmerseite, zwei Anteilseignerseite')
K(G,'ar_arbeitnehmervertreter_zahl',6,'Personen',236)
K(G,'mitbestimmung_ar','paritätisch (MitbestG), 6 von 12 Arbeitnehmervertreter','',236,'"gesetzlichen Bestimmungen ... je sechs Vertreter:innen der Anteilseigner und der Arbeitnehmer:innen"')
K(G,'ar_gewerkschaftsvertreter_zahl','','Personen',238,'nicht ausgewertet')
K(G,'vorstand_frauen_zahl','','Personen',3,'Katja Garcia Vila und Dr. Silke Maurer lt. Bezeichnung "Vorständin"; Gesamtzahl im Vergütungsbericht nicht beziffert')
K(R,'pay_ratio','','',20,'Vertikalvergleich zeigt nur Entwicklung der Gesamtvergütung gegenüber Belegschaft in Deutschland, kein Verhältnis')
