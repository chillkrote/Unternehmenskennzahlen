from lib import *
U = 'U000238'
R = ('governance/dokumente/fuchs-se/verguetungsbericht-2025.pdf', U)
G = ('governance/dokumente/fuchs-se/geschaeftsbericht-2025.pdf', U)
uni('FUCHS SE', U)
# Vergütungsbericht 2025 (fuchs.com); Seiten = PDF-Seiten = Druckseiten; Beträge in T€ (Gesamtvergütung ohne Dienstzeitaufwand IAS gem. § 162 AktG, S. 13–15)
# Stefan Fuchs und Rheinboldt: Gesamtvergütung ohne Dienstzeitaufwand; übrige: Gesamtvergütung (identisch)
VS = [('Stefan Fuchs','Vorsitzender des Vorstands','',2885,13,''),('Dr. Timo Reister','Stellvertretender Vorsitzender des Vorstands','',2537,13,''),
 ('Mathieu Boulandet','Mitglied des Vorstands','2025',756,14,'Eintritt im Geschäftsjahr 2025 (Datum im Bericht nicht genannt; Jahresangabe als Marker für Nicht-Ganzjährigkeit)'),
 ('Dr. Ralph Rheinboldt','Mitglied des Vorstands','',1565,14,''),
 ('Esma Saglik','Mitglied des Vorstands','2025',1208,14,'Eintritt im Geschäftsjahr 2025 (Datum nicht genannt; Jahresmarker)'),('Dr. Sebastian Heiner','Mitglied des Vorstands','',1805,14,''),
 ('Isabelle Wege','Mitglied des Vorstands (ausgeschieden 2025)','','2025',915,15)]
for n,f,s,t,p,*b in [(v[0],v[1],v[2],v[3],v[4],v[5] if len(v)>5 else '') for v in VS if v[0]!='Isabelle Wege']:
    M(R,'Vorstand',n,f,'',s,'',13,'',b[0] if b else '')
    V(R,'Vorstand',n,t,'Gesamtvergütung gem. § 162 AktG (ohne Dienstzeitaufwand IAS)',p,'')
M(R,'Vorstand','Isabelle Wege','Mitglied des Vorstands','','','2025',15,'','Ausgeschieden im Geschäftsjahr 2025 (Gesamtvergütung für sechs Monate, S. 17); Austrittsdatum nicht genannt')
V(R,'Vorstand','Isabelle Wege',915,'Gesamtvergütung gem. § 162 AktG (sechs Monate)',15,'')
AR = [('Dr. Christoph Loos','Vorsitzender',False,288,''),('Dr. Susanne Fuchs','Stellvertretende Vorsitzende',False,193,''),('Ayten Barisik','Mitglied (seit 7.5.2025)',True,62,'seit 7.5.2025 Arbeitnehmervertreterin'),
 ('Jens Lehfeldt','Mitglied',False,95,''),('Ingeborg Neumann','Mitglied',False,190,''),('Cornelia Stahlschmidt','Mitglied (bis 7.5.2025)',True,33,'Arbeitnehmervertreterin, ausgeschieden 7.5.2025'),
 ('Dr. Markus Steilemann','Mitglied',False,145,'')]
for n,f,an,t,b in AR:
    M(R,'Aufsichtsrat',n,f,'Arbeitnehmervertreter' if an else '', '2025-05-07' if 'seit 7.5' in f else '','2025-05-07' if 'bis 7.5' in f else '',22,'',b)
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Fest- + Ausschussvergütung)',22,'')
K(R,'vorstand_mitglieder_zahl',6,'Personen',13,'sechs zum Jahresende (Wege ausgeschieden); sieben im Berichtsjahr')
K(R,'ar_arbeitnehmervertreter_zahl','','',22,'Nur Stahlschmidt und Barisik im Bericht als Arbeitnehmervertreterinnen genannt; Gesamtzahl nicht ausgewiesen')
K(G,'gender_pay_gap_gesamt',11,'Prozent',191,'ESRS S1-16, Konzern; Definition: Differenz Durchschnittseinkommen Frauen/Männer in % der Männer')
K(G,'pay_ratio_hoechstbezahlte_median',61,'Verhältnis',191,'ESRS S1-16: höchstbezahlte Einzelperson zum gewichteten Median aller Arbeitnehmer — nicht Böckler-/CEO-Methode')
K(R,'pay_ratio','','',20,'Keine absolute Ø-Vergütung ausgewiesen (nur Veränderung Mitarbeitende Konzern)')
