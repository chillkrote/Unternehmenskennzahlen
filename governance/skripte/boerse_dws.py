from lib import *
U = 'U000177'
R = ('governance/dokumente/dws-group-gmbh-und-co-kgaa/geschaeftsbericht-2025.pdf', U)
uni('DWS Group GmbH & Co. KGaA', U)
# Geschäftsbericht 2025, Vergütungsbericht; Seiten = PDF-Seiten; Beträge in T€ (gewährte und geschuldete Vergütung, Vergleichstabelle S. 263).
# Geschäftsführung der DWS Management GmbH (persönlich haftende Gesellschafterin) = Vorstand-Äquivalent
VS = [('Dr. Stefan Hoops','Vorsitzender der Geschäftsführung (CEO)','2022-06-10','',4604,253),('Manfred Bauer','Mitglied der Geschäftsführung','','',1910,253),
 ('Dirk Görgen','Mitglied der Geschäftsführung','','',3466,254),('Dr. Markus Kobler','Mitglied der Geschäftsführung','2023-11-01','',2095,254),
 ('Dr. Karen Kuder','Mitglied der Geschäftsführung','2022-11-01','',1276,255),('Rafael Otero','Mitglied der Geschäftsführung','2024-10-01','',999,255),
 ('Vincenzo Vedda','Mitglied der Geschäftsführung','2025-08-01','',397,256)]
for n,f,s,b,t,p in VS:
    M(R,'Vorstand',n,f,'',s,b,263,'','Geschäftsführung der DWS Management GmbH')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Zufluss, Gesamt inkl. weiterer Anstellungsverträge)',p,'')
EX = [('Angela Maragkopoulou','2023-12-31',1128),('Mark Cullen','2022-12-31',1988),('Stefan Kreuzkamp','2022-12-31',2055),('Dr. Asoka Wöhrmann','2022-06-09',5304),
 ('Pierre Cherki','2020-06-09',1257),('Robert Kendall','2020-06-09',1041),('Nikolaus von Tippelskirch','2020-06-09',766),('Jonathan Eilbeck','2018-11-30',81),
 ('Thorsten Michalik','2018-11-30',98),('Nicolas Moreau','2018-10-25',5328)]
for n,b,t in EX:
    M(R,'Vorstand',n,'Ehemaliges Mitglied der Geschäftsführung','','',b,263,'','')
    V(R,'Vorstand',n,t,'Zuflüsse 2025 aus früherer Tätigkeit (§ 162 AktG), überwiegend aufgeschobene Vergütung',257 if n in ('Angela Maragkopoulou','Mark Cullen','Stefan Kreuzkamp','Dr. Asoka Wöhrmann') else 258,'')
AR = [('Oliver Behrens','Vorsitzender','2024-06-06',373.25),('Ute Wolf','Stellvertretende Vorsitzende','',263.0),('Stephan Accorsini','Mitglied','',143.5),
 ('Prof. Dr. Christina E. Bannier','Mitglied','2023-06-15',135.5),('Aldo Cardoso','Mitglied','',170.0),('Christine Metzler','Mitglied','2023-06-21',100.0),
 ('Angela Meurer','Mitglied','',142.25),('Richard I. Morris, Jr.','Mitglied','',207.75),('Karl von Rohr','Mitglied','',137.75),('Erwin Stengele','Mitglied','',150.75),
 ('Margret Suckale','Mitglied','',193.75),('Tomohiro Yao','Mitglied','2025-06-13',None)]
for n,f,s,t in AR:
    M(R,'Aufsichtsrat',n,f,'',s,'',261,'','')
    V(R,'Aufsichtsrat',n,t if t is not None else '','Aufsichtsratsvergütung insgesamt (Grundvergütung + Ausschüsse)',261,'Verzicht auf Vergütung (Konzern-/unabhängiger Anteilseignervertreter)' if t is None else '')
M(R,'Aufsichtsrat','Kazuhide Toda','Mitglied (bis 13.6.2025)','','2023-06-15','2025-06-13',261,'','Verzicht auf Vergütung')
K(R,'vorstand_mitglieder_zahl',7,'Personen',263,'sieben aktive Mitglieder der Geschäftsführung (Vedda seit 1.8.2025)')
K(R,'ar_mitglieder_zahl',12,'Personen',261,'zwölf aktive Mitglieder lt. Vergütungstabelle; Arbeitnehmervertreter im Bericht nicht einzeln gekennzeichnet (Mitbestimmung lt. S. 274 vorhanden)')
K(R,'ar_arbeitnehmervertreter_zahl','','',261,'Nicht belegt: Kennzeichnung im Vergütungsbericht fehlt (Metzler und Stengele mit reiner Grundvergütung 100 T€, aber ohne Beleg)')
K(R,'pay_ratio','','',263,'Ø Vergütung Arbeitnehmer weltweit (Vollzeit) 146 T€ (2024: 157 T€); Berechnung als Methode A mit weltweiter Basis')
