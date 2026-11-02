from lib import *
U = 'U000420'
D = 'governance/dokumente/muenchener-rueckversicherungs-gesellschaft-aktiengesellschaf/'
G = (D + 'geschaeftsbericht-2025.pdf', U)
R = (D + 'verguetungsbericht-2025.pdf', U)
# Seiten = PDF-Seiten der jeweiligen Datei
uni('Münchener Rückversicherungs-Gesellschaft AG', U)
VS = [('Dr. Joachim Wenning','Vorsitzender des Vorstands','',7088.819,25,''),
 ('Dr. Thomas Blunck','Vorsitzender des Rückversicherungsausschusses','',4295.095,25,''),
 ('Nicholas Gartside','Chief Investment Officer','',4289.981,25,''),
 ('Stefan Golling','Mitglied','',4299.196,25,''),
 ('Robin Johnson','Chief Technology Officer','2025-08-01',1028.627,25,'seit 1.8.2025; Gesamtbetrag inkl. Bezüge ERGO Group AG und ET&SM AG; davon Munich Re 346,526 T€'),
 ('Dr. Christoph Jurecka','Chief Financial Officer','',4937.800,26,''),
 ('Dr. Achim Kassow','Arbeitsdirektor (Labour Relations Director)','',4308.512,26,''),
 ('Michael Kerner','Mitglied','',2767.545,26,'Gesamtbetrag inkl. Bezüge Munich-American Holding Corp.; davon Munich Re 555,642 T€'),
 ('Clarisse Kopff','Mitglied','',4511.149,26,''),
 ('Mari-Lizette Malherbe','Mitglied','',2476.618,26,''),
 ('Dr. Markus Rieß','Erstversicherung/ERGO','',4221.643,26,'Gesamtbetrag inkl. Bezüge ERGO Group; davon Munich Re 1.430,710 T€')]
for n,f,s,t,p,b in VS:
    M(G,'Vorstand',n,f,'',s,'',71,'','Funktionen lt. Konzerngeschäftsbericht (PDF S. 71) – Erklärung zur Unternehmensführung')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Summe, ohne Pensionsaufwand)',p,b)
V(R,'Vorstand','Gesamt (aktive Mitglieder, "gesamt"-Spalten)',round(sum(x[3] for x in VS),3),'Summe der Einzelwerte (gerechnet)',26,'Summe aus elf Einzelwerten; enthält konzerninterne Bezüge außerhalb der Münchener Rück AG')
AR = [('Dr. Nikolaus von Bomhard','Vorsitzender','Anteilseigner','2019-04-30',414.000),('Dr. Anne Horstmann','stellv. Vorsitzende','Arbeitnehmer','2014-04-30',180.250),
 ('Matthias Beier','Mitglied','Arbeitnehmer','2024-04-25',82.750+35.000),('Clement B. Booth','Mitglied','Anteilseigner','2016-04-27',111.000),
 ('Dr. Roland Busch','Mitglied','Anteilseigner','2024-04-25',93.563),('Grzegorz Czlowiekowski','Mitglied','Arbeitnehmer','2024-04-25',82.750),
 ('Martina Grundler','Mitglied','Arbeitnehmer','2024-04-25',82.750),('Julia Jäkel','Mitglied','Anteilseigner','2024-04-25',82.750),
 ('Renata Jungo Brüngger','Mitglied','Anteilseigner','2017-01-03',169.125),('Stefan Kaindl','Mitglied','Arbeitnehmer','2019-04-30',180.000),
 ('Dr. Carinne Knoche-Brouillon','Mitglied','Anteilseigner','2021-04-28',111.000),('Gabriele Mücke','Mitglied','Arbeitnehmer','2019-04-30',111.000),
 ('Dr. Victoria E. Ossadnik','Mitglied','Anteilseigner','2024-04-25',135.000),('Ulrich Plottke','Mitglied','Arbeitnehmer','2014-04-30',180.000),
 ('Carsten Spohr','Mitglied','Anteilseigner','2020-04-29',111.000),('Anita Stocker-Napravnik','Mitglied','Arbeitnehmer','2024-04-25',119.188),
 ('Susanne Terhoeven','Mitglied','Arbeitnehmer','2024-04-25',82.750),('Jens-Jürgen Vogel','Mitglied','Arbeitnehmer','2024-04-25',82.750),
 ('Prof. Dr. Jens Weidmann','Mitglied','Anteilseigner','2024-04-25',107.375),('Dr. Maximilian Zimmerer','Mitglied','Anteilseigner','2017-07-04',259.750)]
for n,f,v,s,t in AR:
    M(G,'Aufsichtsrat',n,f,v,s,'',206,'','Arbeitnehmervertreter lt. Fußnote 2 der Mitgliederliste (PDF S. 206-207); Beruf/Funktion dort')
    extra = 'inkl. Tochterunternehmen (35,000 € bis 12.3.2025 ERGO)' if n=='Matthias Beier' else ''
    V(R,'Aufsichtsrat',n,t,'Gewährte Vergütung 2025 (Grundvergütung, Ausschussgelder, Sitzungsgelder)',37,extra)
K(G,'vorstand_mitglieder_zahl',11,'Personen',70,'"elf Mitgliedern, davon zwei Frauen" zum 31.12.2025')
K(G,'vorstand_frauen_zahl',2,'Personen',71,'Frauenanteil 18,18 %; Personen im Dokument nicht namentlich als Frauen ausgewiesen')
K(G,'ar_mitglieder_zahl',20,'Personen',73,'')
K(G,'ar_frauen_zahl',9,'Personen',73,'"neun weiblichen und elf männlichen Mitgliedern" = 45 %')
K(G,'ar_arbeitnehmervertreter_zahl',10,'Personen',206,'Fußnote "Vertreter der Arbeitnehmer" bei zehn Mitgliedern; paritätisch lt. MitbestG')
K(G,'ar_gewerkschaftsvertreter_zahl',3,'Personen',206,'Beier und Grundler (ver.di), Mücke (Vorsitzende Neue Assekuranz Gewerkschaft) lt. Berufsangabe; weitere Gewerkschaftszugehörigkeit nicht ausgewiesen')
K(G,'mitbestimmung_ar','paritätisch (MitbestG), 10 von 20 Arbeitnehmervertreter','',206,'')
K(R,'pay_ratio','','',39,'Kein Verhältnis ausgewiesen; Vergleich nur als Veränderung (Ø-Vergütung Deutschland FTE 2025: -0,2 %), keine Absolutwerte -> Berechnung nach Böckler Variante A nicht möglich')
