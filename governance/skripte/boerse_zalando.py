from lib import *
U = 'U000742'
G = ('governance/dokumente/zalando-se/geschaeftsbericht-2025.pdf', U)
R = ('governance/dokumente/zalando-se/verguetungsbericht-2025.pdf', U)
for n,f,s,b,sp,t in [('Robert Gentz','Co-CEO','','',30,1094.635),('David Schröder','Co-CEO (bis 31.12.2025 auch Interims-CFO)','','',30,4670.468),
   ('Dr. Sandra Dembeck','CFO','','2025-02-28',30,455.257),('David Schneider','Mitglied des Vorstands (Mitgründer)','2025','',31,647.370),('Dr. Astrid Arndt','CPO','','',31,1303.439)]:
    M(R,'Vorstand',n,f,'',s,b,sp,'','Funktion und Zeiten lt. Vergütungsbericht (PDF S. 18-32)')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gemäß § 162 Abs. 1 Satz 1 AktG',sp,'in T€ umgerechnet aus EUR; zeitanteilig bei unterjährigem Eintritt/Austritt' if (s or b) else 'in T€ umgerechnet aus EUR; Schröder: einschließlich Auszahlung LTI 2019 (3.308.506 EUR)')
M(G,'Vorstand','Anna Dimitrova','CFO','','2026-01-01','',108,'','bestellt bis 31.12.2028, zum 31.12.2025 noch kein Mitglied')
# Aufsichtsrat 9 Mitglieder: 6 Anteilseigner, 3 Arbeitnehmer (SE-Beteiligungsvereinbarung); Zuordnung GB S. 11 (Bild) und VB S. 36
for n,f,v,s in [('Kelly Bennett','Vorsitzender','Anteilseigner','2019-05-22'),('Mariella Röhm-Kottmann','stellv. Vorsitzende','Anteilseigner','2019-05-22'),
   ('Anders Holch Povlsen','Mitglied','Anteilseigner','2013-12-09'),('Niklas Östberg','Mitglied','Anteilseigner','2021-05-19'),('Susanne Schröter-Crossan','Mitglied','Anteilseigner','2023-05-24'),
   ('Alice Delahunt','Mitglied','Anteilseigner','2025-05-27'),('Zbigniew Laskowski','Mitglied','Arbeitnehmer','2025-05-27'),('Rose Reynolds','Mitglied','Arbeitnehmer','2025-05-27'),('Maggie Ratay Sloan','Mitglied','Arbeitnehmer','2025-05-27')]:
    M(R,'Aufsichtsrat',n,f,v,s,'',36,'','Vergütungsbericht S. 36; Vertreterart lt. Geschäftsbericht S. 11 (Bildunterschrift nennt Östberg als Anteilseigner, Sloan, Laskowski, Reynolds als Arbeitnehmervertreter); die übrigen sind bei 6 Anteilseigner- und 3 Arbeitnehmervertretern (S. 110) Anteilseigner' )
for n,s,b in [('Jennifer Hyman','','2025-05-27'),('Matti Ahtiainen','','2025-05-27'),('Jade Buddenberg','','2025-05-27'),('Anika Mangelmann','','2025-05-27')]:
    M(R,'Aufsichtsrat',n,'ehemaliges Mitglied','',s,b,36,'','bis HV 27.5.2025')
for n,t in [('Kelly Bennett',220),('Mariella Röhm-Kottmann',200),('Anders Holch Povlsen',90),('Niklas Östberg',90),('Alice Delahunt',54),('Susanne Schröter-Crossan',110),('Zbigniew Laskowski',54),('Rose Reynolds',66),('Maggie Ratay Sloan',54)]:
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung gemäß § 162 Abs. 1 Satz 1 AktG',36,'in T€ umgerechnet aus EUR')
K(G,'vorstand_mitglieder_zahl',4,'Personen',108,'zum 31.12.2025 (ohne Dembeck); ab 1.1.2026 fünf mit Dimitrova')
K(G,'vorstand_frauen_zahl',1,'Personen',108,'Frauenanteil 25 % zum 31.12.2025 (Vorjahr 40 %); ab 1.1.2026 wieder 40 %')
K(G,'ar_mitglieder_zahl',9,'Personen',110,'sechs Anteilseigner-, drei Arbeitnehmervertreter')
K(G,'ar_frauen_zahl',5,'Personen',137,'Frauenanteil 55,6 %')
K(G,'ar_arbeitnehmervertreter_zahl',3,'Personen',110)
K(G,'ar_gewerkschaftsvertreter_zahl','','Personen',110,'nicht ausgewertet')
K(G,'mitbestimmung_ar','Drittelparität nach SE-Beteiligungsvereinbarung (SEBG), 3 von 9 Arbeitnehmervertreter','',110,'"in Einklang mit den Bestimmungen des SE-Beteiligungsgesetzes (SEBG) getroffenen Beteiligungsvereinbarung"')
K(R,'pay_ratio','','',37,'kein Verhältniswert; vergleichende Darstellung nur mit Veränderungsraten (S. 37-38)')
