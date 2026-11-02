from lib import *
U = 'U000125'
G = ('governance/dokumente/continental-aktiengesellschaft/geschaeftsbericht-2025.pdf', U)   # englischer Annual Report
R = ('governance/dokumente/continental-aktiengesellschaft/verguetungsbericht-2025.pdf', U)
# Vorstand lt. Vergütungsbericht S. 23-25 (PDF); Namen aus der vergleichenden Darstellung S. 28, Zuordnung zu den Tabellen über Eintritts-/Austrittsdaten
for n,f,s,b,sp,t,bem in [
  ('Nikolai Setzer','Vorsitzender (1.12.2020 bis 31.12.2025; im Vorstand seit 12.8.2009)','','',24,7980,'Gesamtvergütung enthält Abfindung 4.788 T€ wegen Ausscheidens zum 31.12.2025 (Vollzeitjahr 2025)'),
  ('Ulrike Hintze','Mitglied','2025-07-01','',24,415,'zeitanteilig'),
  ('Philipp von Hirschheydt','Mitglied (1.5.2023 bis 16.9.2025)','2023-05-01','2025-09-16',25,1537,'zeitanteilig; einschl. Spin-off Bonus'),
  ('Christian Kötz','Mitglied','2019-04-01','',25,1739,''),
  ('Philip Nelles','Mitglied','2021-06-01','',25,1467,''),
  ('Dr. Ariane Reinhart','Mitglied (1.10.2014 bis 30.6.2025)','2014-10-01','2025-06-30',26,1186,'zeitanteilig'),
  ('Olaf Schick','Mitglied (1.5.2023 bis 30.9.2025)','2023-05-01','2025-09-30',26,1542,'zeitanteilig'),
  ('Roland Welzbacher','Mitglied','2025-08-01','',26,346,'zeitanteilig')]:
    M(R,'Vorstand',n,f,'',s,b,sp,'','Funktion und Zeiten lt. Vergütungsbericht; Tabellenzuordnung über Eintritts-/Austrittsdaten und Reihenfolge der vergleichenden Darstellung S. 28')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung i. S. v. § 162 Abs. 1 Satz 1 AktG',sp,bem)
# Aufsichtsrat: Vergütung S. 30 (Fix+Sitzungsgeld, T€); Vertreterart in den ausgewerteten Seiten nicht angegeben
for n,f,s,b,t in [('Prof. Dr.-Ing. Wolfgang Reitzle','Vorsitzender','','',541),('Hasan Allak','stellv. Vorsitzender (seit 30.9.2025)','','',278),('Christiane Benner','stellv. Vorsitzende (bis 17.9.2025)','','2025-09-17',198),
  ('Dr. Kevin Borck','Mitglied','','',187),('Dorothea von Boxberg','Mitglied','','',180),('Stefan Erwin Buchner','Mitglied','','2025-09-04',125),('Dr. Gunter Dunkel','Mitglied','','2025-09-17',132),
  ('Matthias Ebenau','Mitglied','','2025-09-17',134),('Francesco Grioli','Mitglied','','',280),('Petra Hartwig','Mitglied','2025-09-22','',51),('Michael Iglhaut','Mitglied','','',200),
  ('Satish Khatu','Mitglied','','',186),('Isabel Corinna Knauf','Mitglied','','',276),('Sabine Kühn','Mitglied','2025-09-22','',51),('Michael Linnartz','Mitglied','2025-09-22','',77),
  ('Carmen Löffler','Mitglied','','2025-09-17',134),('Sabine Neuß','Mitglied','','',180),('Prof. Dr. Rolf Nonnenmacher','Mitglied','','',456),('Anne Nothing','Mitglied','','2025-09-17',133),
  ('Klaus Rosenfeld','Mitglied','','',274),('Sabrina Soussan','Mitglied','2025-09-22','',51),('Georg F. W. Schaeffler','Mitglied','','',274),('Jörg Schönfelder','Mitglied','','',185),
  ('Matthias Tote','Mitglied','','',278),('Nicole Werner','Mitglied','2025-09-22','',51)]:
    M(R,'Aufsichtsrat',n,f,'',s,b,30,'','Liste lt. Vergütungsbericht S. 30; Anteilseigner/Arbeitnehmer-Zuordnung nicht angegeben, nachzutragen')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Fix + Sitzungsgeld)',30)
K(G,'vorstand_mitglieder_zahl','','Personen','','nicht ausgewertet; 8 Personen im Berichtsjahr tätig (Wechsel durch Aumovio-Abspaltung)')
K(G,'vorstand_frauen_zahl','','Personen','','nicht ausgewertet')
K(G,'ar_mitglieder_zahl','','Personen','','Mitgliederzahl nicht ausgewertet')
K(G,'ar_frauen_zahl','','Personen','','nicht ausgewertet')
K(G,'ar_arbeitnehmervertreter_zahl','','Personen','','nicht ausgewertet')
K(G,'ar_gewerkschaftsvertreter_zahl','','Personen','','nicht ausgewertet')
K(G,'mitbestimmung_ar','paritätisch (MitbestG)','',71,'Verweis auf Mitbestimmungsgesetz im Abschnitt Aufsichtsrat; Zahl der Arbeitnehmervertreter nicht ausgewertet')
K(R,'pay_ratio','','',31,'kein Verhältniswert; vergleichende Darstellung nur mit Veränderungsraten (S. 28 und 31)')
