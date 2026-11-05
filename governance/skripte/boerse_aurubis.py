from lib import *
U = 'U000053'
R = ('governance/dokumente/aurubis-ag/geschaeftsbericht-2025.pdf', U)
uni('Aurubis AG', U)
# Geschäftsbericht 2024/25 (GJ 1.10.2024-30.9.2025), Vergütungsbericht; Seiten = PDF-Seiten; Beträge in EUR im Bericht, hier in T€
VS = [('Dr. Toralf Haag','Chief Executive Officer (Vorsitzender des Vorstands)','2024-09-01','',1296.603),('Steffen Alexander Hoffmann','Chief Financial Officer','2024-10-01','',1166.984),
 ('Inge Hofkens','COO Multimetal Recycling','2023-01-01','',1009.395),('Tim Kurth','COO Custom Smelting & Products','2024-09-01','',884.645)]
for n,f,s,t in [(a,b,c,e) for a,b,c,d,e in VS]:
    M(R,'Vorstand',n,f,'',s,'',102,'','Funktion/Eintritt lt. Vergütungstabelle')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Gesamtvergütung)',102,'Haag/Hoffmann/Kurth im GJ 2024/25 nur zeitanteilig/Vorjahr unvollständig' if n!='Inge Hofkens' else '')
for n,f,s,b,t,bem in [('Roland Harings','Chief Executive Officer (Vorsitzender des Vorstands)','2019-05-20','2024-09-30',873.033,'inkl. Aktien-Deferral/Performance Cash Plan aus Vorjahren; Einmalzahlung 4.110 T€ nur im Vorjahr'),
 ('Dr. Heiko Arnold','COO Custom Smelting & Products','2020-08-15','2024-04-30',587.313,'Auszahlung aus früheren Plänen'),('Rainer Verhoeven','Chief Financial Officer','2018-01-01','2024-06-30',587.313,'Auszahlung aus früheren Plänen')]:
    V(R,'Vorstand (ehemalig)',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied)',103,bem)
AN = False
AR = [('Prof. Dr. Fritz Vahrenholt','Vorsitzender','2018-03-01',283.0,False),('Kathrin Dahnke','Mitglied','2023-02-16',116.0,False),('Gunnar Groebler','Mitglied','2021-10-01',111.0,False),
 ('Prof. Dr. Markus Kramer','Mitglied','2023-02-16',121.5,False),('Dr. Stephan Krümmer','Mitglied','2018-03-01',135.0,False),('Dr. Sandra Reich','Mitglied','2013-02-28',114.0,False),
 ('Jan Koltze','Stellvertretender Vorsitzender','2011-03-03',185.0,True),('Deniz Filiz Acar','Mitglied','2019-05-03',114.0,True),('Christian Ehrentraut','Mitglied','2019-05-03',110.5,True),
 ('Dr. Elke Lossin','Mitglied','2018-03-01',108.5,True),('Daniel Mrosek','Mitglied','2023-02-16',92.5,True),('Stefan Schmidt','Mitglied','2018-03-01',110.5,True)]
for n,f,s,t,an in AR:
    M(R,'Aufsichtsrat',n,f,'Arbeitnehmervertreter' if an else '',s,'',106,'','Tabelle gliedert "Vertreter der Arbeitnehmer"' if an else 'Tabelle gliedert "Vertreter der Anteilseigner"')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (fest, Ausschuss, Sitzungsgeld)',106,'')
K(R,'vorstand_mitglieder_zahl',4,'Personen',102,'vier aktive Mitglieder im GJ 2024/25')
K(R,'ar_mitglieder_zahl',12,'Personen',106,'sechs Anteilseigner- und sechs Arbeitnehmervertreter')
K(R,'ar_arbeitnehmervertreter_zahl',6,'Personen',106,'Tabelle "Vertreter der Arbeitnehmer"')
K(R,'pay_ratio','','',108,'Kein Verhältnis ausgewiesen; Ø-Vergütung Belegschaft der Aurubis AG (FTE) in der Vergleichstabelle nicht eindeutig maschinell lesbar')
