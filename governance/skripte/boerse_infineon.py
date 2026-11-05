from lib import *
U = 'U000301'
R = ('governance/dokumente/infineon-technologies-ag/verguetungsbericht-2025.pdf', U)
uni('Infineon Technologies AG', U)
# Geschäftsjahr 2025 = 1.10.2024-30.9.2025; Seiten = PDF-Seiten; Beträge im Bericht in €, hier in T€
VS = [('Jochen Hanebeck','Vorstandsvorsitzender (seit 1.4.2022)','2016-07-01','',2577.471,22,''),
 ('Elke Reichart','Vorstandsmitglied','2023-11-01','',1193.214,22,''),
 ('Dr. Sven Schneider','Vorstandsmitglied','2019-05-01','',2028.369,22,''),
 ('Andreas Urschitz','Vorstandsmitglied','2022-06-01','',1189.604,23,''),
 ('Dr. Rutger Wijburg','Vorstandsmitglied','2022-04-01','2025-09-30',1197.324,23,'ausgeschieden 30.9.2025; Anstellungsvertrag läuft bis 31.3.2026 weiter (ca. 2 Mio. € Ansprüche, nicht in der Summe)')]
for n,f,s,b,t,p,bem in VS:
    M(R,'Vorstand',n,f,'',s,b,p,'','Funktion lt. Individualtabelle Vergütungsbericht')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung i. S. d. § 162 Abs. 1 Satz 1 AktG (ohne Versorgungsaufwand)',p,bem)
V(R,'Vorstand','Gesamt (alle Mitglieder)',8185.982,'Gesamtvergütung',22,'Summe der fünf Einzelwerte; keine Gesamtzeile im Bericht')
AR = [('Dr. Herbert Diess','Vorsitzender','','',305.0),('Johann Dechant','Mitglied','','',229.0),('Dr. Friedrich Eichiner','Mitglied','','',239.0),('Annette Engelfried','Mitglied','','',199.0),
 ('Prof. Dr. Hermann Eul','Mitglied','2024-02-23','',143.0),('Peter Gruber','Mitglied','','',145.0),('Klaus Helmrich','Mitglied','','',145.0),('Rico Irmischer','Mitglied','2025-02-20','',91.334),
 ('Dr. Susanne Lachenmann','Mitglied','','',145.0),('Melanie Riedl','Mitglied','','',145.0),('Jürgen Scholz','Mitglied','','2025-02-20',64.084),('Dr. Ulrich Spiesshofer','Mitglied','','',118.0),
 ('Margret Suckale','Mitglied','','',147.0),('Mirco Synde','Mitglied','','',114.0),('Diana Vitale','Mitglied','','',147.0),('Ute Wolf','Mitglied','','',168.0),('Xiaoqun Clever-Steg','Mitglied','','',145.0)]
for n,f,s,b,t in AR:
    M(R,'Aufsichtsrat',n,f,'',s,b,27,'','Anteilseigner-/Arbeitnehmerseite in der Vergütungstabelle nicht ausgewiesen')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Fest-, Funktionszuschlag, Sitzungsgeld)',27,'')
V(R,'Aufsichtsrat','Gesamt',2689.418,'Gesamtvergütung',27,'Ausweis im Bericht (Summen-Zeile)')
K(R,'vorstand_mitglieder_zahl',5,'Personen',22,'fünf Mitglieder mit Vergütung im GJ 2025')
K(R,'ar_mitglieder_zahl',17,'Personen',27,'17 Mitglieder mit Vergütung im GJ 2025 (zwei zeitanteilig)')
K(R,'pay_ratio','','',28,'Kein Verhältnis ausgewiesen; der Bericht nennt nur prozentuale Veränderungen der Ø-Mitarbeitervergütung (Deutschland, FTE), keinen Absolutwert. Variante A nicht berechenbar, Variante B aus Geschäftsbericht offen.')
