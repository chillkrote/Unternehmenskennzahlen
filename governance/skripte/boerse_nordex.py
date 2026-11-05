from lib import *
U = 'U000442'
R = ('governance/dokumente/nordex-se/geschaeftsbericht-2025.pdf', U)
uni('Nordex SE', U)
# Integrierter Geschäftsbericht 2025, Vergütungsbericht; Seiten = PDF-Seiten; Beträge in T€ (gewährte und geschuldete Vergütung, S. 248)
for n,f,t in [('José Luis Blanco','Vorsitzender des Vorstands (CEO)',1843.072),('Dr. Ilya Hartmann','Finanzvorstand (CFO)',2084.116)]:
    M(R,'Vorstand',n,f,'','','',230,'','Ressort lt. Bericht des Aufsichtsrats / Vergütungsbericht')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Gesamtvergütung)',248,'')
M(R,'Vorstand','Patxi Landa','Chief Sales Officer (CSO)','','','2024-12-31',249,'','Anstellungsvertrag zum 31.12.2024 beendet; Abfindung 720 T€ im Feb. 2025 gezahlt')
V(R,'Vorstand','Patxi Landa',720,'Abfindung (gezahlt Februar 2025)',249,'Zur Abgeltung entgehender Vergütungsansprüche; keine Vergütung für 2025')
AR = [('Dr.-Ing. Wolfgang Ziebart','Vorsitzender',118.764),('Juan Muro-Lara','Stellvertretender Vorsitzender',86.359),('Jan Klatten','Mitglied',75.669),
 ('Maria Isabel Blanco','Mitglied',53.953),('Martin Rey','Mitglied',64.811),('María Cordón','Mitglied',53.953)]
for n,f,t in AR:
    M(R,'Aufsichtsrat',n,f,'Anteilseignervertreter','','',250,'','Ausschussmitgliedschaft lt. Tabelle S. 250')
    V(R,'Aufsichtsrat',n,t,'Gewährte/geschuldete Vergütung (Festvergütung + Ausschusstätigkeit)',251,'')
K(R,'vorstand_mitglieder_zahl',2,'Personen',248,'zwei aktive Mitglieder zum 31.12.2025')
K(R,'ar_mitglieder_zahl',6,'Personen',251,'sechs vergütete Mitglieder')
K(R,'ar_arbeitnehmervertreter_zahl',0,'Personen',251,'Im Bericht keine Arbeitnehmervertreter im Aufsichtsrat ausgewiesen (SE, nur sechs Mitglieder)')
K(R,'gender_pay_gap_gesamt',-12.3,'Prozent',203,'Unbereinigt, alle Arbeitnehmenden (ESRS S1-16); negativ = Frauen verdienen im Mittel mehr. Management +19,8 %, White-Collar +7,2 %, Blue-Collar +3,2 % zugunsten der Männer')
K(R,'pay_ratio_hoechstbezahlte_median',41.6,'Verhältnis',204,'ESRS S1-16: höchstbezahlte Einzelperson zum Median aller Arbeitnehmenden (ohne diese Person), 2024: 37,0 — nicht Böckler-/CEO-Methode')
K(R,'pay_ratio','','',251,'Keine absolute Ø-Vergütung ausgewiesen (nur Veränderung +9,4 % für Deutschland); kein CEO-Verhältnis nach § 162 AktG')
