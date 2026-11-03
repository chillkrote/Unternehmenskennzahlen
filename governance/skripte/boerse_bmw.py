from lib import *
U = 'U000067'
R = ('governance/dokumente/bayerische-motoren-werke-aktiengesellschaft/verguetungsbericht-2025.pdf', U)
uni('Bayerische Motoren Werke Aktiengesellschaft', U)
# Seiten = PDF-Seiten des Vergütungsberichts (gedruckte Seite = PDF-Seite + 375)
VS = [('Oliver Zipse','Vorsitzender des Vorstands (seit 16.8.2019)','2015-05-13','',5784.538,26),
 ('Jochen Goller','Kunde, Marken, Vertrieb','2023-11-01','',2643.824,27),
 ('Ilka Horstmeier','Personal und Immobilien, Arbeitsdirektorin','2019-11-01','',3205.763,28),
 ('Nicolai Martin','Einkauf und Lieferantennetzwerk','2025-06-01','',1637.046,29),
 ('Walter Mertl','Finanzen','2023-05-12','',2608.564,30),
 ('Milan Nedeljković','Produktion','2019-10-01','',3162.897,31),
 ('Joachim Post','Entwicklung (seit 1.6.2025)','2022-01-01','',3100.552,32),
 ('Frank Weber','Entwicklung (bis 31.5.2025)','2020-07-01','2025-05-31',3048.831,33)]
for n,f,s,b,t,p in VS:
    M(R,'Vorstand',n,f,'',s,b,p,'','Funktion/Zeiten lt. Vergütungsbericht (PDF S. 26-33, 35-36)')
    V(R,'Vorstand',n,t,'Gesamtvergütung gem. § 162 AktG (gewährt und geschuldet, ohne Dienstzeitaufwand)',p,'zeitanteilig bei unterjährigem Ein-/Austritt; Dienstvertrag Weber bis 30.6.2026' if (s>='2025' or b) else '')
V(R,'Vorstand','Gesamt (acht Mitglieder)',round(sum(x[4] for x in VS),3),'Summe der Einzelwerte (gerechnet)',40,'')
AR = [('Nicolas Peter','Vorsitzender (seit 14.5.2025)',387.545,''),('Martin Kimmich','stellv. Vorsitzender',410.0,'Böckler'),('Stefan Quandt','stellv. Vorsitzender',410.0,''),
 ('Stefan Schmid','stellv. Vorsitzender',410.0,'Böckler'),('Kurt Bock','stellv. Vorsitzender, Vors. Prüfungsausschuss',460.0,''),('Ulrich Bauer','Mitglied',210.0,''),
 ('Marc Bitzer','Mitglied',210.0,''),('Rachel Empey','Mitglied, Prüfungsausschuss',410.0,''),('Heinrich Hiesinger','Mitglied',210.0,''),('Susanne Klatten','Mitglied',210.0,''),
 ('Jens Köhler','Mitglied',210.0,'Böckler'),('André Mandl','Mitglied',210.0,'Böckler'),('Dominique Mohabeer','Mitglied, Prüfungsausschuss',410.0,'Böckler'),
 ('Michael Nikolaides','Mitglied',210.0,''),('Horst Ott','Mitglied',208.0,'Böckler'),('Anke Schäferkordt','Mitglied, Vergütungsausschuss',310.0,''),
 ('Christoph M. Schmidt','Mitglied',210.0,''),('Vishal Sikka','Mitglied',210.0,''),('Sibylle Wankel','Mitglied',210.0,'Böckler'),('Johanna Wenckebach','Mitglied',210.0,'Böckler')]
for n,f,t,bk in AR:
    M(R,'Aufsichtsrat',n,f,'Arbeitnehmer' if bk else '','','',38,'','Fußnote 2: Arbeitnehmervertreter, die ihre Vergütung an die Hans-Böckler-Stiftung abführen (Seitenzuordnung der übrigen Arbeitnehmervertreter nicht ausgewiesen)' if bk else 'Seitenzuordnung im Vergütungsbericht nicht ausgewiesen')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Festvergütung + Sitzungsgeld)',38,'Vergütung wird laut Fußnote an die Hans-Böckler-Stiftung abgeführt' if bk else '')
M(R,'Aufsichtsrat','Norbert Reithofer','Vorsitzender (bis 14.5.2025)','','','2025-05-14',39,'','')
V(R,'Aufsichtsrat','Norbert Reithofer',224.727,'Gewährte und geschuldete Vergütung',39,'ausgeschieden 14.5.2025')
V(R,'Aufsichtsrat','Gesamt (amtierende und ehemalige)',5950.272,'Summe',39,'')
K(R,'vorstand_mitglieder_zahl',7,'Personen',26,'sieben im Dezember 2025 amtierende Mitglieder (Zipse, Goller, Horstmeier, Martin, Mertl, Nedeljković, Post); Weber bis 31.5.2025')
K(R,'ar_mitglieder_zahl',20,'Personen',38,'20 zum 31.12.2025 amtierende Mitglieder lt. Vergütungstabelle')
K(R,'ar_arbeitnehmervertreter_zahl','','Personen',38,'im Vergütungsbericht nicht gesamt ausgewiesen; acht Mitglieder mit Böckler-Abführung (nur Teilmenge der Arbeitnehmervertreter); Mitbestimmung nach MitbestG nicht im VB belegt')
K(R,'pay_ratio','','',40,'BMW weist kein Verhältnis aus; Ø-Vergütung BMW AG 101.227 € (FTE); Berechnung siehe berechnungen/pay_ratio.csv')
