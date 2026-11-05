from lib import *
U = 'U000494'
R = ('governance/dokumente/rational-aktiengesellschaft/geschaeftsbericht-2025.pdf', U)
uni('RATIONAL Aktiengesellschaft', U)
# Annual Report 2025 (englisch), Remuneration Report; Seiten = PDF-Seiten; Beträge in T€
VS = [('Dr. Peter Stadelmann','CEO (Vorsitzender des Vorstands)','2012-12-01',2276),('Dr. Martin Hermann','CTO','2022-09-01',1585),('Markus Paschmann','CSMO','2013-12-01',1709),('Jörg Walter','CFO','2021-03-01',1187)]
for n,f,s,t in VS:
    M(R,'Vorstand',n,f,'',s,'',177,'','Funktion/Eintritt lt. Tabelle "Executive Board members of RATIONAL AG in 2025"')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung (Total remuneration granted and owed)',177,'')
V(R,'Vorstand (ehemalig)','Peter Wiedemann',726,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied)',180,'Vorstand bis 31.12.2024 (25 Jahre); davon 714 T€ vertragliche Ausgleichszahlung')
AR = [('Walter Kurtz','Vorsitzender',275),('Erich Baumgärtner','Stellvertretender Vorsitzender (seit 5/2024)',210),('Clarissa Käfer','Mitglied (Vorsitzende Prüfungsausschuss)',175),
 ('Moritz Graser','Mitglied',150),('Dr. Christoph Lintz','Mitglied',150),('Werner Schwind','Mitglied',150),('Dr. Johannes Würbser','Mitglied',150)]
for n,f,t in AR:
    M(R,'Aufsichtsrat',n,f,'','','',180,'','Arbeitnehmerseite im Bericht nicht ausgewiesen')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Festvergütung, Ausschuss, Sachleistung)',180,'')
V(R,'Aufsichtsrat','Gesamt',1260,'Gesamtvergütung',180,'Summenzeile')
K(R,'vorstand_mitglieder_zahl',4,'Personen',177,'vier aktive Mitglieder 2025')
K(R,'pay_ratio','','',181,'Kein Verhältnis und keine absolute Ø-Vergütung ausgewiesen (Veränderung Ø je FTE 2025 -2 %)')
