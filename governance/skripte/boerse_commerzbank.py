from lib import *
U = 'U000124'
R = ('governance/dokumente/commerzbank-ag/verguetungsbericht-2025.pdf', U)
uni('Commerzbank AG', U)
# Seiten = PDF-Seiten des Vergütungsberichts (gedruckte Seite = PDF-Seite - 2)
VS = [('Dr. Bettina Orlopp','Vorsitzende (seit 1.10.2024; Vorstand seit 1.11.2017)','2017-11-01','',2964,24),
 ('Michael Kotzbauer','Stellv. Vorsitzender, Segment Firmenkunden','2021-01-14','',2028,24),
 ('Sabine Mlnarsky','Group Human Resources & Group Organisation and Security','2023-01-01','',1563,25),
 ('Thomas Schaufler','Segment Privat- und Unternehmerkunden','2021-12-01','',1577,25),
 ('Carsten Schmitt','Chief Financial Officer','2025-02-19','',1006,26),
 ('Bernd Spalt','Chief Risk Officer','2024-01-01','',1183,26),
 ('Christiane Vorspel','Chief Operating Officer','2024-09-01','',1304,27)]
for n,f,s,b,t,p in VS:
    n={'Bernd Spalt':'Bernhard Spalt','Christiane Vorspel':'Christiane Vorspel-Rüter'}.get(n,n)  # Schreibweise wie im Jahresabschluss (pilot_banken)
    V(R,'Vorstand',n,t,'Gesamtvergütung i. S. d. § 162 AktG (ohne Versorgungsaufwand)',p,'zeitanteilig ab Eintritt' if s>='2025' else '')
V(R,'Vorstand','Gesamt (amtierende Mitglieder)',sum(x[4] for x in VS),'Summe der Einzelwerte (gerechnet)',27,'')
AR = [('Prof. Dr. Jens Weidmann','Vorsitzender',465),('Sascha Uebel','Mitglied',282),('Heike Anscheit','Mitglied',128),('Gunnar de Buhr','Mitglied',167),('Harald Christ','Mitglied',200),
 ('Dr. Frank Czichowski','Mitglied',215),('Sabine Ursula Dietrich','Mitglied',193),('Dr. Michael Gorriz','Mitglied (seit 15.5.2025)',101),('Burkhard Keese','Mitglied',239),
 ('Thomas Kühnl','Mitglied (seit 1.1.2025)',128),('Sabine Lautenschläger-Peiter','Mitglied (seit 15.5.2025)',129),('Maxi Leuchters','Mitglied',170),('Daniela Mattheus','Mitglied',183),
 ('Nina Olderdissen','Mitglied',197),('Sandra Persiehl','Mitglied',166),('Michael Schramm','Mitglied',206),('Caroline Seifert','Mitglied',150),('Kevin Voß','Mitglied (seit 1.1.2025)',131),
 ('Frederik Werning','Mitglied (seit 30.4.2024)',150),('Frank Westhoff','Mitglied',244)]
for n,f,t in AR:
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (netto, Grund-, Ausschuss-, Sitzungsvergütung)',46,'')
for n,t in [('Dr. Jutta A. Dönges',77),('Dr. Gertrude Tumpel-Gugerell',74)]:
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (netto)',47,'zeitanteilig bis 15.5.2025')
V(R,'Aufsichtsrat','Gesamt',3993,'Gesamt (netto)',47,'Ausweis im Bericht')
K(R,'pay_ratio','','',50,'Commerzbank weist kein Verhältnis aus; Ø-Arbeitnehmervergütung auf VZK-Basis 2025: 108 T€; Berechnung siehe berechnungen/pay_ratio.csv')
