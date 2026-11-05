from lib import *
U = 'U000516'
R = ('governance/dokumente/sartorius-aktiengesellschaft/geschaeftsbericht-2025.pdf', U)
uni('Sartorius Aktiengesellschaft', U)
# Vergütungsbericht im Geschäftsbericht (englisch); Seiten = PDF-Seiten
VS = [('Dr. Michael Grosse','Mitglied des Vorstands (seit 1.7.2025)','2025-07-01','',3852,253,'enthält 2.700 T€ gewährte Aktien (Antritts-/Ausgleichskomponente)'),
 ('Dr. René Fáber','Mitglied des Vorstands','','',1670,253,''),
 ('Dr. Alexandra Gatzemeyer','Mitglied des Vorstands (seit 1.5.2023)','2023-05-01','',1192,253,''),
 ('Dr. Florian Funck','Mitglied des Vorstands (seit 1.4.2024)','2024-04-01','',1422,253,''),
 ('Dr. Joachim Kreuzburg','Vorsitzender des Vorstands (bis 30.6.2025)','','2025-06-30',2341,254,'inkl. 524 T€ Vergütung aus Aufhebungsvereinbarung (Karenzentschädigung 223 T€, Phantom-Stock-Ausgleich 301 T€); beratend bis 10.11.2025')]
for n,f,s,b,t,p,bem in VS:
    M(R,'Vorstand',n,f,'',s,b,p,'','Funktion lt. Individualtabelle (Total remuneration granted and owed, § 162 AktG)')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Total remuneration)',p,bem)
V(R,'Vorstand (ehemalig)','Rainer Lehmann',179,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied, bis 31.10.2023)',254,'')
V(R,'Vorstand (ehemalig)','John Gerard Mackay',186,'Gewährte und geschuldete Vergütung gem. § 162 AktG (ehemaliges Mitglied, bis 15.6.2023)',254,'')
V(R,'Vorstand','Gesamt (aktive Tätigkeit aller Mitglieder)',9192,'Gesamtvergütung',253,'Ausweis im Bericht: "Total remuneration granted and owed for the active service of all Executive Board members" (Vorjahr 6.842)')
AR = [('Dr. Lothar Kappich','Vorsitzender','',290),('Dietmar Müller','stellv. Vorsitzender (seit 1.4.2025)','',170),('Annette Becker','Mitglied','',105),('Prof. David Raymond Ebsworth, Ph.D.','Mitglied','',79),
 ('Dr. Daniela Favoccia','Mitglied','',103),('Beatrix Henseler','Mitglied (seit 9.9.2025)','2025-09-09',26),('Dominik Langosch','Mitglied (seit 2.4.2025)','2025-04-02',87),('Ilke Hildegard Panzer','Mitglied','',79),
 ('Frank Riemensperger','Mitglied','2022-03-25',79),('Hermann Jens Ritzau','Mitglied','2021-03-01',79),('Prof. Dr. Klaus Rüdiger Trützschler','Mitglied','',195),('Sabrina Wirth','Mitglied','2022-03-25',75),
 ('Manfred Zaffke','stellv. Vorsitzender (bis 31.3.2025)','',49),('Petra Kirchhoff','Mitglied (bis 31.7.2025)','',47)]
for n,f,s,t in AR:
    M(R,'Aufsichtsrat',n,f,'Arbeitnehmervertreter' if n in ('Dietmar Müller','Manfred Zaffke') else '',s,'',262,'','Arbeitnehmervertreter nur dort gekennzeichnet, wo der Bericht die Spende der AR-Vergütung an eine Stiftung ausweist (S. 259/261)' if n in ('Dietmar Müller','Manfred Zaffke') else 'Anteilseigner-/Arbeitnehmerseite im Bericht nicht durchgängig ausgewiesen')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung (Total remuneration)',262,'')
K(R,'vorstand_mitglieder_zahl',5,'Personen',253,'vier aktive Mitglieder zum Jahresende plus Dr. Kreuzburg (bis 30.6.2025)')
K(R,'ar_mitglieder_zahl',14,'Personen',262,'14 Mitglieder mit Vergütung 2025 (inkl. unterjährig Ein-/Ausgetretener)')
K(R,'pay_ratio','','',262,'Bericht weist keine absolute Ø-Mitarbeitervergütung aus (nur Index 2025 = 100, Veränderung +3 %); Variante A nicht berechenbar, Variante B offen')
