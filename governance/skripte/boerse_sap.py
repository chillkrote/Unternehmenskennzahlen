from lib import *
U = 'U000515'
R = ('governance/dokumente/sap-se/verguetungsbericht-2025.pdf', U)
uni('SAP SE', U)
# Seiten = PDF-Seiten des Vergütungsberichts
VS = [('Christian Klein','Vorsitzender des Vorstands (Vorstandsvorsitzender)',16244,21,'inkl. LTI-Auszahlung Tranche 2022 (10.982 T€); Vorjahr 18.983'),
 ('Muhammad Alam','Mitglied des Vorstands',2246,21,''),
 ('Dominik Asam','Mitglied des Vorstands',2531,22,''),
 ('Thomas Saueressig','Mitglied des Vorstands',7044,22,'Vorjahr 8.241'),
 ('Sebastian Steinhäuser','Mitglied des Vorstands (seit 1.2.2025)',2131,23,'zeitanteilig ab 1.2.2025'),
 ('Gina Vargiu-Breuer','Mitglied des Vorstands',2524,23,'')]
for n,f,t,p,b in VS:
    M(R,'Vorstand',n,f,'','2025-02-01' if 'Steinhäuser' in n else '','',p,'','Funktion lt. Individualtabelle Vergütungsbericht')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Gesamtvergütung)',p,b)
V(R,'Vorstand','Gesamt (alle Mitglieder)',32720,'Gesamtvergütung',24,'Ausweis im Bericht')
AR = [('Dr. h. c. mult. Pekka Ala-Pietilä','Vorsitzender (seit 15.5.2024)',600),('Lars Lamadé','stellv. Vorsitzender',290),('Jakub Černý','Mitglied (seit 15.5.2024)',235),
 ('Pascal Demat','Mitglied (seit 15.5.2024)',235),('Aicha Evans','Mitglied',285),('Andreas Hahn','Mitglied (seit 15.5.2024)',235),('Prof. Dr. Ralf Herbrich','Mitglied (seit 15.5.2024)',235),
 ('Margret Klein-Magar','Mitglied',250),('Jennifer Xin-Zhe Li','Mitglied',295),('Dr. Qi Lu','Mitglied',200),('César Martin','Mitglied (seit 15.5.2024)',250),('Gerhard Oswald','Mitglied',285),
 ('Dr. Friederike Rotsch','Mitglied',385),('Nicolas Sabatier','Mitglied (seit 15.5.2024)',235),('Dr. Eberhard Schick','Mitglied (seit 15.5.2024)',250),
 ('Nina Straßner','Mitglied (seit 15.5.2024)',285),('Dr. Rouven Westphal','Mitglied',285),('Dr. Gunnar Wiedenfels','Mitglied',296)]
for n,f,t in AR:
    M(R,'Aufsichtsrat',n,f,'','','',32 if t!=285 or n in('Aicha Evans','Gerhard Oswald') else 33,'','Anteilseigner-/Arbeitnehmerseite im Vergütungsbericht nicht ausgewiesen')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Grund- und Ausschussvergütung)',32,'')
V(R,'Aufsichtsrat','Gesamt',5131,'Gesamtvergütung',33,'')
K(R,'vorstand_mitglieder_zahl',6,'Personen',24,'sechs Mitglieder mit Vergütung 2025 (Summe 32.720 T€)')
K(R,'ar_mitglieder_zahl',18,'Personen',32,'18 Mitglieder mit Vergütung für das ganze Jahr 2025 im Bericht; Arbeitnehmerseite/MitbestG-Besetzung nicht ausgewiesen')
K(R,'pay_ratio','','',35,'SAP weist kein Verhältnis aus; Ø-Jahresvergütung der Mitarbeitenden des SAP-Konzerns 2025: 146 T€ (VZK); Berechnung siehe berechnungen/pay_ratio.csv')
