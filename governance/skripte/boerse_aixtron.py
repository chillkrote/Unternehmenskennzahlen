from lib import *
U = 'U000028'
R = ('governance/dokumente/aixtron-se/geschaeftsbericht-2025.pdf', U)
uni('AIXTRON SE', U)
# Geschäftsbericht 2025, Corporate Governance / Vergütungsbericht; Seiten = PDF-Seiten = Seitenzahl; Beträge in T€
M(R,'Vorstand','Dr. Felix Grawert','Vorsitzender des Vorstands (CEO)','','2017-08-14','',58,'','Vorstand seit 14.8.2017')
V(R,'Vorstand','Dr. Felix Grawert',4250,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Wert gewährter Aktien zum Bilanzstichtagskurs)',58,'Aufwand nach IFRS 4.144 T€; Zufluss 2025: 2.044 T€')
M(R,'Vorstand','Dr. Christian Danninger','Vorstandsmitglied (CFO)','','2021-05-01','',59,'','Vorstand seit 1.5.2021')
V(R,'Vorstand','Dr. Christian Danninger',2405,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Wert gewährter Aktien zum Bilanzstichtagskurs)',59,'Aufwand nach IFRS 2.347 T€; Zufluss 2025: 1.214 T€')
AR = [('Alexander Everke','Vorsitzender',210,'ab 15.5.2025 Vorsitzender'),('Frits van Hout','Stellvertretender Vorsitzender',120,''),('Ingo Bank','Mitglied',63,''),
 ('Karen Florschütz','Mitglied',80,''),('Dr. Stefan Traeger','Mitglied',80,''),('Prof. Dr. Anna Weber','Mitglied',100,'Vorsitzende des Prüfungsausschusses, unabhängige Finanzexpertin'),
 ('Kim Schindelhauer','Vorsitzender (bis 15.5.2025)',83,'Ehemaliges Vorstandsmitglied')]
for n,f,t,b in AR:
    M(R,'Aufsichtsrat',n,f,'Anteilseignervertreter','','2025-05-15' if 'Schindelhauer' in n else '',69,'',b)
    V(R,'Aufsichtsrat',n,t,'Gesamtvergütung Aufsichtsrat (Festvergütung + Ausschussvergütung)',69,b)
K(R,'vorstand_mitglieder_zahl',2,'Personen',32,'Vorstand zweiköpfig, Frauenanteil 0 %')
K(R,'ar_mitglieder_zahl',6,'Personen',32,'sechs Mitglieder zum 31.12.2025, davon zwei Frauen (33 %)')
K(R,'ar_arbeitnehmervertreter_zahl',0,'Personen',69,'SE ohne Arbeitnehmervertreter im Aufsichtsrat ausgewiesen')
K(R,'ar_frauen_zahl',2,'Personen',33,'Karen Florschütz und Prof. Dr. Anna Weber (33 %); Zielgröße 33 % bis 2030')
K(R,'vorstand_frauen_zahl',0,'Personen',32,'Frauenanteil Vorstand 0 %, Zielgröße 0 %')
K(R,'pay_ratio','','',65,'Keine absolute Ø-Vergütung ausgewiesen (nur Veränderung Mitarbeiter AIXTRON SE +2 %, FTE)')
