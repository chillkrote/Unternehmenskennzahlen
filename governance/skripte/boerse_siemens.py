from lib import *
U = 'U000535'
R = ('governance/dokumente/siemens-aktiengesellschaft/verguetungsbericht-2025.pdf', U)
uni('Siemens Aktiengesellschaft', U)
# Geschäftsjahr 1.10.2024-30.9.2025; Seiten = PDF-Seiten
VS = [('Dr. Roland Busch','Vorsitzender des Vorstands (Präsident und CEO seit 2.2021, Vorstand seit 4.2011)','2011-04',11495),
 ('Veronika Bienert','Mitglied','2024-10-01',2902),('Dr. Peter Koerte','Mitglied','2024-10-01',2905),
 ('Cedrik Neike','Mitglied','2017-04-01',6369),('Matthias Rebellius','Mitglied (zugleich CEO Siemens Schweiz AG)','2020-10-01',6971),
 ('Prof. Dr. Ralf P. Thomas','Mitglied','2013-09-18',7263),('Judith Wiese','Mitglied','2020-10-01',9128)]
# Die Zeile ohne Namen in der Tabelle (Thomas, 6.739 T€) ist die Vorjahreszeile (2024) von Thomas.
for n,f,s,t in VS:
    M(R,'Vorstand',n,f,'',s,'',32,'','Funktion/Zeiten lt. Tabelle B.6.1 (PDF S. 32)')
    V(R,'Vorstand',n,t,'Gesamtvergütung gem. § 162 AktG ohne Dienstzeitaufwand',32,'Rebellius: Teile durch Siemens Schweiz AG gezahlt; Wiese: inkl. 2.130 T€ Abgeltung Stock Awards' if n in ('Matthias Rebellius','Judith Wiese') else '')
V(R,'Vorstand','Gesamt (sieben Mitglieder)',sum(x[3] for x in VS),'Summe der Einzelwerte (gerechnet)',32,'')
AR = [('Jim Hagemann Snabe','Vorsitzender (seit 10.2013, Vors. seit 1.2018)','',612.0),('Birgit Steinborn','1. stellv. Vorsitzende','Arbeitnehmer',452.0),('Dr. Werner Brandt','2. stellv. Vorsitzender','',470.0),
 ('Tobias Bäumler','Mitglied','Arbeitnehmer',340.0),('Dr. Regina E. Dugan','Mitglied','',202.0),('Dr. Andrea Fehrmann','Mitglied','Arbeitnehmer',160.0),
 ('Oliver Hartmann','Mitglied','',160.0),('Keryn Lee James','Mitglied','',160.0),('Jürgen Kerner','Mitglied','Arbeitnehmer',292.0),
 ('Saskia Kraußer','Mitglied (seit 2.2025)','Arbeitnehmer',103.333),('Dr.-Ing. Christian Pfeiffer','Mitglied','Arbeitnehmer',206.0),('Benoît Potier','Mitglied','',172.0),
 ('Hagen Reimer','Mitglied','Arbeitnehmer',260.0),('Kasper Rørsted','Mitglied','',204.0),('Dr. Ulf Mark Schneider','Mitglied (seit 2.2025)','',181.333),
 ('Dr. Nathalie von Siemens','Mitglied','',174.0),('Dorothea Simon','Mitglied','Arbeitnehmer',160.0),('Mimon Uhamou','Mitglied','Arbeitnehmer',226.0),
 ('Grazia Vittadini','Mitglied','',246.0),('Matthias Zachert','Mitglied','',340.0)]
for n,f,v,t in AR:
    M(R,'Aufsichtsrat',n,f,v,'','',36,'','Fußnote 1 (Seite 36): Arbeitnehmer- und Gewerkschaftsvertreter, die ihre Vergütung abführen; übrige Zuordnung nicht ausgewiesen' if v else 'Seitenzuordnung im Vergütungsbericht nicht ausgewiesen')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Grund-, Ausschuss-, Sitzungsvergütung)',36,'Vergütung wird laut Fußnote 1 abgeführt' if v else '')
for n,b,t in [('Bettina Haller','2025-02',109.833),('Martina Merz','2025-02',107.833)]:
    M(R,'Aufsichtsrat',n,'Mitglied','','',b,36,'','bis 2.2025')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung',36,'zeitanteilig')
V(R,'Aufsichtsrat','Gesamt',5338.333,'Summe',36,'')
K(R,'vorstand_mitglieder_zahl',7,'Personen',32,'am 30.9.2025 im Amt')
K(R,'ar_mitglieder_zahl',20,'Personen',36,'20 am 30.9.2025 im Amt')
K(R,'ar_arbeitnehmervertreter_zahl','','Personen',36,'neun Mitglieder mit Abführungs-Fußnote (Arbeitnehmer- und Gewerkschaftsvertreter); Gesamtzahl im VB nicht ausgewiesen')
K(R,'pay_ratio','','',38,'Siemens weist kein Verhältnis aus; Ø-Vergütung Belegschaft Deutschland 116 T€ (FTE); Berechnung siehe berechnungen/pay_ratio.csv')
