from lib import *
G = ('governance/dokumente/deutsche-telekom-ag/geschaeftsbericht-2025.pdf', 'U000161')
R = ('governance/dokumente/deutsche-telekom-ag/verguetungsbericht-2025.pdf', 'U000161')
VS = [('Timotheus Höttges','Vorsitzender (CEO)','','',11176.445,23),('Dr. Ferri Abolhassan','Mitglied (T-Systems)','','',1904.509,23),('Birgit Bohle','Mitglied (Personal und Recht)','','',4732.989,23),
 ('Rodrigo Diehl','Mitglied (Deutschland)','2025-03-01','',1504.703,23),('Dr. Christian P. Illek','Mitglied (Finanzen, CFO)','','',4999.266,23),('Thorsten Langheim','Mitglied (USA und Unternehmensentwicklung)','','',5031.368,23),
 ('Dominique Leroy','Mitglied (Europa)','','',4239.794,23),('Dr. Abdurazak Mudesir','Mitglied (Produkt und Technologie)','2025-10-01','',471.850,24),
 ('Srinivasan Gopalan','Mitglied (Deutschland)','','2025-02-28',364.608,23),('Claudia Nemat','Mitglied (Technologie und Innovation)','','2025-09-30',4408.553,24)]
for n,f,s,b,e,sp in VS:
    M(G,'Vorstand',n,f,'',s,b,208)
    V(R,'Vorstand',n,e,'erdiente Gesamtvergütung 2025 (Vergütungsbericht § 162 AktG)',sp,'Betrag in T€ aus Euro-Angabe; "erdiente Vergütung" lt. Tabelle')
AR = [('Dr. Frank Appel','Vorsitzender',442000),('Odysseus D. Chatzidis','Mitglied',181000),('Eric Daum','Mitglied',152000),('Rachel Empey','Mitglied',130500),('Constantin Greve','Mitglied',152000),
 ('Lars Hinrichs','Mitglied',45333),('Dr. Helga Jung','Mitglied',56000),('Natalie Knight','Mitglied',85000),('Dagmar P. Kollmann','Mitglied',274500),('Petra Steffi Kreusel','Mitglied',176000),
 ('Harald Krüger','Mitglied',183000),('Kerstin Marx','Mitglied',247000),('Dr. Reinhard Ploss','Mitglied',163871),('Stefan Ramge','Mitglied',210500),('Frank Sauerland','Mitglied',234000),
 ('Christoph Schmitz-Dethlefsen','stellv. Vorsitzender',204000),('Susanne Schöttke','Mitglied',170000),('Nicole Seelemann-Wandtke','Mitglied',138873),('Karl-Heinz Streibich','Mitglied',176000),
 ('Margret Suckale','Mitglied',181000),('Karin Topel','Mitglied',176000),('Stefan B. Wintels','Mitglied',166648)]
for n,f,e in AR:
    M(G,'Aufsichtsrat',n,f,'','','',31,'','genannt in der AR-Vergütungstabelle (Vergütungsbericht S. 31, inkl. unterjährig Ausgeschiedener); Zuordnung Anteilseigner/Arbeitnehmer in den ausgewerteten Seiten nicht angegeben')
    V(R,'Aufsichtsrat',n,round(e/1000,3),'Gesamtvergütung 2025 (fest + Ausschuss + Sitzungsgeld)',31,'Auszahlung nach HV 2026')
V(R,'Aufsichtsrat','Gesamt (alle Mitglieder)',3945.226,'Gesamtvergütung 2025',31)
K(G,'vorstand_mitglieder_zahl',8,'Personen',208,'Stand 31.12.2025')
K(G,'ar_mitglieder_zahl',20,'Personen',208,'zehn Anteilseigner-, zehn Arbeitnehmervertreter')
K(G,'ar_arbeitnehmervertreter_zahl',10,'Personen',208)
K(G,'mitbestimmung_ar','paritätisch (MitbestG), 10 von 20 Arbeitnehmervertreter','',208,'§ 31 MitbestG und § 27 Abs. 3 MitbestG (Vermittlungsausschuss) im Dokument genannt')
K(G,'vorstand_frauen_zahl','','Personen',219,'Mindestbeteiligungsgebot (mind. 1 Frau) "übererfüllt"; Zahl nicht genannt')
K(G,'ar_frauen_zahl','','Personen',221,'Anteil nicht in den ausgewerteten Seiten beziffert')
K(G,'ar_gewerkschaftsvertreter_zahl','','Personen',31,'Hinweis: Gewerkschaftsmitglieder unter den Arbeitnehmervertretern führen Vergütung nach DGB-Richtlinien ab; Zahl nicht genannt')
K(R,'pay_ratio','','',23,'im Vergütungsbericht 2025 nicht ausgewiesen (nur gesetzlicher Vergleich der Entwicklung nach § 162 AktG)')
