from lib import *
U = 'U000151'
G = ('governance/dokumente/deutsche-boerse-ag/geschaeftsbericht-2025.pdf', U)   # englischer Annual Report 2025
R = ('governance/dokumente/deutsche-boerse-ag/verguetungsbericht-2025.pdf', U)  # deutscher Vergütungsbericht (Auszug aus dem Geschäftsbericht)
for n,f,s,b,sp,t in [('Dr. Stephan Leithner','Vorsitzender','','',41,7024),('Dr. Christoph Böhm','CIO/COO','','',41,3800),('Dr. Thomas Book','Mitglied','','',41,3249),
  ('Dr. Stephanie Eckermann','Mitglied','','',41,3005),('Heike Eckert','People, Risk & Compliance, Arbeitsdirektorin','','',42,3752),('Christian Kromann','Investment Management Solutions','2025-01-01','',42,3021),
  ('Dr. Jens Schulte','Finanzvorstand (seit 22.9.2025)','2025-06-01','',42,2926),('Gregor Pottmeyer','Finanzvorstand (bis 30.9.2025)','','2025-09-30',42,2854)]:
    M(R,'Vorstand',n,f,'',s,b,sp,'','Funktion und Zeiten lt. Vergütungsbericht S. %d' % sp)
    V(R,'Vorstand',n,t,'Gesamtvergütung i. S. d. § 162 AktG (ohne bAV-Dienstzeitaufwand)',sp,'zeitanteilig bei unterjährigem Eintritt/Austritt' if (s or b) else '')
# Aufsichtsrat 16 Mitglieder (8 Anteilseigner, 8 Arbeitnehmer, MitbestG); Zuordnung zu den Seiten und Frauen nicht aus der Vergütungstabelle ablesbar
for n,f,s,b in [('Clara-Christina Streit','Vorsitzende (seit 14.5.2025)','',''),('Martin Jetter','Vorsitzender (bis 14.5.2025)','','2025-05-14'),('Dr. Markus Beck','stellv. Vorsitzender','2021-12-08',''),
  ('Prof. Dr. Nadine Brandl','Mitglied','',''),('Dr. Andreas Gottschling','Mitglied','',''),('Dr. Anja Greenwood','Mitglied','2021-11-17',''),('Oliver Greie','Mitglied','2022-04-29',''),
  ('Shannon A. Johnston','Mitglied','2022-05-18',''),('Achim Karle','Mitglied','',''),('Sigrid Kozmiensky','Mitglied','2024-05-14',''),('Barbara Lambert','Mitglied','',''),
  ('Rainer Müller','Mitglied','2024-05-14',''),('Jean Pierre Mustier','Mitglied','2025-05-14',''),('Dr. Carsten Schäfer','Mitglied','2024-05-14',''),
  ('Charles G. T. Stonehill','Mitglied','',''),('Chong Lee Tan','Mitglied','2021-05-19',''),('Maria-Regina Wohak','Mitglied','2024-05-14','')]:
    M(R,'Aufsichtsrat',n,f,'',s,b,48,'','Liste lt. Vergütungsbericht S. 48; Anteilseigner/Arbeitnehmer-Zuordnung nicht angegeben, nachzutragen' )
    # Vergütung AR GJ 2025 (T€) aus S. 46 siehe unten
for n,t in [('Clara-Christina Streit',348),('Martin Jetter',182),('Dr. Markus Beck',256),('Prof. Dr. Nadine Brandl',156),('Dr. Andreas Gottschling',238),('Dr. Anja Greenwood',214),('Oliver Greie',174),
  ('Shannon A. Johnston',182),('Achim Karle',212),('Sigrid Kozmiensky',174),('Barbara Lambert',266),('Rainer Müller',193),('Jean Pierre Mustier',105),('Dr. Carsten Schäfer',193),
  ('Charles G. T. Stonehill',204),('Chong Lee Tan',156),('Maria-Regina Wohak',191)]:
    V(R,'Aufsichtsrat',n,t,'Gesamtvergütung Aufsichtsrat gemäß § 162 AktG (Fest, Ausschuss, Sitzungsgeld)',46)
K(G,'vorstand_mitglieder_zahl',8,'Personen',41,'im GJ 2025 aktive Mitglieder lt. Vergütungsbericht; zum Jahresende 7 (Pottmeyer ausgeschieden 30.9.2025)')
K(G,'vorstand_frauen_zahl',2,'Personen',142,'"The Executive Board of Deutsche Börse AG consists of two female members"; namentlich belegt nur Heike Eckert (Arbeitsdirektorin)')
K(G,'ar_mitglieder_zahl',16,'Personen',142,'acht Anteilseigner- und acht Arbeitnehmervertreter')
K(G,'ar_frauen_zahl','','Personen',142,'Anteilseignerseite 50 % Frauen (4); Arbeitnehmerseite nicht in den ausgewerteten Seiten beziffert')
K(G,'ar_arbeitnehmervertreter_zahl',8,'Personen',142)
K(G,'ar_gewerkschaftsvertreter_zahl','','Personen',142,'nicht ausgewertet')
K(G,'mitbestimmung_ar','paritätisch (MitbestG), 8 von 16 Arbeitnehmervertreter','',142)
K(G,'pay_ratio',97.0,'x',111,'ESRS S1-16: höchstbezahlte Person (CEO) zu Median-Gesamtvergütung aller Beschäftigten, 2024: 94,7')
K(G,'gender_pay_gap_belegschaft_pct',28.2,'%',111,'ESRS S1-16, unbereinigt, Konzern-Belegschaft (2024: 29,1 %)')
