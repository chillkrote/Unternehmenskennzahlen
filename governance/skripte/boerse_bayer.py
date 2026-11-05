from lib import *
U = 'U000065'
R = ('governance/dokumente/bayer-aktiengesellschaft/verguetungsbericht-2025.pdf', U)
uni('Bayer Aktiengesellschaft', U)
# Seiten = PDF-Seiten des Vergütungsberichts (gedruckte Seiten 411-423); Werte lt. vergleichender Darstellung (gewährte und geschuldete Vergütung)
VS = [('Bill Anderson','Vorsitzender des Vorstands',6062),('Wolfgang Nickl','Mitglied des Vorstands',2741),('Stefan Oelrich','Mitglied des Vorstands',2772),
 ('Heike Prinz','Mitglied des Vorstands',2606),('Rodrigo Santos','Mitglied des Vorstands',2978),('Julio Triana','Mitglied des Vorstands',2155)]
for n,f,t in VS:
    M(R,'Vorstand',n,f,'','','',45,'','Funktion/Zugehörigkeit lt. vergleichender Darstellung (in 2025 aktive Mitglieder)')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (vergleichende Darstellung)',45,'')
V(R,'Vorstand','Gesamt (aktive Mitglieder)',19314,'Gesamtvergütung',45,'Summe der sechs Einzelwerte; keine Gesamtzeile im Bericht')
AR = [('Prof. Dr. Norbert Winkeljohann','Vorsitzender','',518),('Heike Hausfeld','stellv. Vorsitzende','',350),('Dr. Paul Achleitner','Mitglied','',233),('Horst Baier','Mitglied','',336),
 ('André van Broich','Mitglied','',279),('Ertharin Cousin','Mitglied','',240),('Nadine Dietz','Mitglied','2025-01-01',244),('Yasmin Fahimi','Mitglied','',207),('Colleen A. Goggins','Mitglied','',233),
 ('Francesco Grioli','Mitglied','',198),('Frank Löllgen','Mitglied','',268),('Marianne Maehl','Mitglied','2024-09-01',172),('Kimberly Mathisen','Mitglied','',234),('Andrea Sacher','Mitglied','',244),
 ('Claudia Schade','Mitglied','',210),('Lori Schechter','Mitglied','2024-04-26',304),('Dr. Nancy Simonian','Mitglied','2024-04-26',208),('Jeffrey Ubben','Mitglied','2024-04-26',273),
 ('Alberto Weisser','Mitglied','',223),('Michael Westmeier','Mitglied','',241)]
for n,f,s,t in AR:
    M(R,'Aufsichtsrat',n,f,'',s,'',44,'','Anteilseigner-/Arbeitnehmerseite im Vergütungsbericht nicht ausgewiesen')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Fest-, Ausschussvergütung, Sitzungsgeld)',44,'')
V(R,'Aufsichtsrat','Gesamt',5210,'Gesamtvergütung',44,'Ausweis im Bericht (Summe der nicht gerundeten Werte)')
K(R,'vorstand_mitglieder_zahl',6,'Personen',45,'sechs in 2025 aktive Mitglieder')
K(R,'ar_mitglieder_zahl',20,'Personen',44,'20 zum 31.12.2025 amtierende Mitglieder')
K(R,'pay_ratio','','',46,'Kein Verhältnis ausgewiesen; Ø-Vergütung Beschäftigte in Deutschland (Tarif- und Gesamtbelegschaft, FTE) 2025: 122 T€; Berechnung siehe berechnungen/pay_ratio.csv')
