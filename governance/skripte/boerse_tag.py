from lib import *
U = 'U000643'
R = ('governance/dokumente/tag-immobilien-ag/geschaeftsbericht-2025.pdf', U)
uni('TAG Immobilien AG', U)
# Geschäftsbericht 2025, Vergütungsbericht (S. 194–210) und ESRS S1-16 (S. 161); Seiten = PDF-Seiten; Beträge in T€
for n,f,t in [('Claudia Hoyer','COO, Co-CEO',916),('Martin Thiel','CFO, Co-CEO',908)]:
    M(R,'Vorstand',n,f,'','','',210,'','Co-CEO lt. Vergütungstabelle')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Gesamtvergütung)',210,'')
AR = [('Olaf Borkers','Vorsitzender',175,''),('Eckhard Schultz','Stellvertretender Vorsitzender',135,'60 Aufsichtsrat + 75 Ausschuss (Vorsitz Prüfungsausschuss)'),
 ('Gabriela Gryger','Mitglied',41,'40 + 1 Ausschuss'),('Beate Schulz','Mitglied',40,''),('Björn Eifler','Mitglied',40,''),('Prof. Dr. Kristin Wellner','Mitglied',50,'40 + 10 Ausschuss')]
for n,f,t,b in AR:
    M(R,'Aufsichtsrat',n,f,'Anteilseignervertreter','','',196,'','')
    V(R,'Aufsichtsrat',n,t,'Gewährte Vergütung Aufsichtsrats- und Ausschusstätigkeit',196,b)
K(R,'vorstand_mitglieder_zahl',2,'Personen',210,'zwei Co-CEOs')
K(R,'ar_mitglieder_zahl',6,'Personen',196,'sechs vergütete Mitglieder; keine Arbeitnehmervertreter (nicht mitbestimmt)')
K(R,'ar_arbeitnehmervertreter_zahl',0,'Personen',196,'Im Bericht keine Arbeitnehmervertreter ausgewiesen')
K(R,'gender_pay_gap_gesamt',7.3,'Prozent',161,'ESRS S1-16: Bruttostundenverdienst Männer um 7,3 % über Frauen (Vorjahr 7,4 %), ohne Vorstand')
K(R,'pay_ratio_hoechstbezahlte_median',25.2,'Verhältnis',161,'ESRS S1-16: höchstbezahlte Einzelperson zum Median aller weiteren Beschäftigten (Vorjahr 25,2) — nicht Böckler-/CEO-Methode')
K(R,'pay_ratio','','',161,'Keine absolute Ø-Vergütung ausgewiesen; kein CEO-Verhältnis nach § 162 AktG')
