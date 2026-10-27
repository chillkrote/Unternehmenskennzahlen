from lib import *
G = ('governance/dokumente/basf-se/geschaeftsbericht-2025.pdf', 'basf-se')
R = ('governance/dokumente/basf-se/verguetungsbericht-2025.pdf', 'basf-se')
uni('BMW AG',''); uni('Henkel AG & Co. KGaA','henkel-ag-und-co-kgaa'); uni('RWE AG','rwe-aktiengesellschaft')
VS=[('Dr. Markus Kamieth','Vorsitzender','2024-04-25',6001,'Erstbestellung 2017; Geschäftsbereiche: Corporate Development, Legal/Compliance, HR, Communications, IR','24'),
 ('Dr. Dirk Elvermann','Mitglied (CFO)','2023-04-27',1766,'','24'),('Michael Heinz','Mitglied','2011-05-06',2770,'Mandat endet planmäßig mit der HV am 30.4.2026','24'),
 ('Anup Kothari','Mitglied','2024-03-01',2137,'','24'),('Dr. Stephan Kothrade','Mitglied','2023',2001,'','25'),('Dr. Katja Scharpwinkel','Mitglied','2024',1925,'','25')]
for n,f,s,t,b,sp in VS:
    M(G,'Vorstand',n,f,'',s,'',140,'',b)
    V(R,'Vorstand',n,t,'gewährte und geschuldete Vergütung § 162 AktG (ohne freiwillig angegebene Pensionsbeiträge)',int(sp),'Zahlen aus Vergütungsbericht 2025, T€')
AR=[('Dr. Kurt Bock','Vorsitzender','Anteilseigner','Ehemaliger Vorsitzender des Vorstands der BASF SE (bis Mai 2018)','2020-06-18'),
 ('Prof. Dr. Stefan Asenkerschbaumer','stellv. Vorsitzender','Anteilseigner','Geschäftsführender Gesellschafter Robert Bosch Industrietreuhand KG; Vorsitzender des Aufsichtsrats der Robert Bosch GmbH','2022-04-29'),
 ('Sinischa Horvat','stellv. Vorsitzender','Arbeitnehmer','Betriebsratsvorsitzender BASF SE Ludwigshafen, BASF-Konzernbetriebsrat und BASF Europa Betriebsrat','2017-05-12'),
 ('Prof. Dr. Thomas Carell','Mitglied','Anteilseigner','Professor für Organische Chemie, LMU München','2019-05-03'),
 ('Liming Chen','Mitglied','Anteilseigner','Nonexecutive independent Board member, ACWA Power Company SJSC','2020-10-08'),
 ('Tatjana Diether','Mitglied','Arbeitnehmer','Stellv. Betriebsratsvorsitzende BASF SE Ludwigshafen; Mitglied Konzernbetriebsrat','2018-05-04'),
 ('Alessandra Genco','Mitglied','Anteilseigner','Ehemalige CFO der Leonardo SpA (bis November 2025)','2022-04-29'),
 ('André Matta','Mitglied','Arbeitnehmer','Mitglied des Betriebsrats BASF SE Ludwigshafen','2022-04-29'),
 ('Natalie Mühlenfeld','Mitglied','Arbeitnehmer (Gewerkschaft)','Bezirksleiterin IGBCE Köln/Bonn','2022-04-29'),
 ('Michael Vassiliadis','Mitglied','Arbeitnehmer (Gewerkschaft)','Vorsitzender der IGBCE','2004-08-01'),
 ('Tamara Weinert','Mitglied','Anteilseigner','Ehemals President und CEO Business Area Americas, Mitglied des Leadership Teams der Outokumpu Corporation (bis Oktober 2025)','2024-04-25'),
 ('Peter Zaman','Mitglied','Arbeitnehmer','Sekretär des Betriebsrats BASF Antwerpen N.V.','2022-04-29')]
for n,f,art,beruf,seit in AR:
    M(G,'Aufsichtsrat',n,f,art,seit,'',141 if AR.index((n,f,art,beruf,seit))<6 else 142,beruf,'Stand 23.2.2026; Arbeitnehmervertreter/Anteilseigner laut Fußnoten b/c')
    W(G,n,beruf,'','lt. Dokument','Beruf laut Organverzeichnis',141)
for n,t,g,f,gl,sp in [('Dr. Dirk Elvermann','b','Harbour Energy plc','Non-executive Director (börsennotiert)','',140),('Dr. Katja Scharpwinkel','b','BASF Antwerpen N.V.','Vorsitz Aufsichtsrat (Konzern)','',140),
 ('Dr. Kurt Bock','a','Bayerische Motoren Werke Aktiengesellschaft','stellv. Vorsitz, Vorsitz Prüfungsausschuss','',141),('Prof. Dr. Stefan Asenkerschbaumer','a','Robert Bosch GmbH','Vorsitz','',141),('Prof. Dr. Stefan Asenkerschbaumer','b','Stadler Rail AG','Mitglied Verwaltungsrat (börsennotiert)','',141),
 ('Liming Chen','b','ACWA Power Company SJSC','Mitglied (börsennotiert)','seit 2025-01-05',141),('Alessandra Genco','b','Elettronica SpA','Mitglied (Leonardo-Konzern)','bis 2025-05-21',141),('Alessandra Genco','b','Leonardo Global Solutions SpA','Mitglied (Leonardo-Konzern)','2025-05-20 bis 2025-11-30',141),
 ('Natalie Mühlenfeld','a','3M Deutschland GmbH','Mitglied','bis 2025-08-31',142),('Natalie Mühlenfeld','a','Solventum Germany GmbH','Mitglied','',142),('Natalie Mühlenfeld','a','Henkel AG & Co. KGaA','Mitglied (börsennotiert)','seit 2025-01-31',142),
 ('Michael Vassiliadis','a','Steag GmbH','stellv. Vorsitz','',142),('Michael Vassiliadis','a','RAG Aktiengesellschaft','stellv. Vorsitz','',142),('Michael Vassiliadis','a','RWE AG','stellv. Vorsitz (börsennotiert)','seit 2025-04-30',142),('Michael Vassiliadis','a','Henkel AG & Co. KGaA','Mitglied (börsennotiert)','',142),('Michael Vassiliadis','a','Vivawest GmbH','Mitglied','',142)]:
    X(G,n,t,g,'',f,gl,sp)
K(G,'vorstand_mitglieder_zahl',6,'Personen',140,'Stand 31.12.2025; Kurian und Tedeschi folgen ab 1.5.2026')
K(G,'vorstand_frauen_zahl',1,'Personen',118,'Frauenanteil 16,7 %')
K(G,'ar_mitglieder_zahl',12,'Personen',141)
K(G,'ar_frauen_zahl',8,'Personen',124,'Frauenanteil 66,7 % von 12')
K(G,'ar_arbeitnehmervertreter_zahl',6,'Personen',141,'sechs Arbeitnehmervertreter, gewählt vom BASF Europa Betriebsrat (SE)')
K(G,'ar_gewerkschaftsvertreter_zahl',2,'Personen',142,'Vassiliadis (Vorsitzender IGBCE), Mühlenfeld (Bezirksleiterin IGBCE); Zuordnung aus Beruf')
K(G,'mitbestimmung_ar','paritätisch, 6 von 12 Arbeitnehmervertreter','',141,'Größe lt. Satzung; Rechtsgrundlage (SE-Beteiligungsvereinbarung statt MitbestG) aus der Rechtsform SE abgeleitet, im Dokument nicht ausdrücklich genannt')
K(G,'pay_ratio','','',299,'"Excessive CEO pay ratio" laut ESRS-Index als nicht wesentlich eingestuft; kein Wert')
