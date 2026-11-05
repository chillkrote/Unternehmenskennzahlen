from lib import *
U = 'U000491'
R = ('governance/dokumente/qiagen-n-v/verguetungsbericht-2025.pdf', U)
uni('QIAGEN N.V.', U)
# Remuneration Report 2025 nach niederländischem Recht und Dutch Corporate Governance Code (kein § 162 AktG); Beträge in USD (T USD), NICHT in Euro umgerechnet; Seiten = PDF-Seiten
USD = ' (Betrag nur in USD, Spalte betrag_tsd_eur leer, keine Umrechnung)'
for n,f,fix,bon,oth,tot,ben,psu in [('Thierry Bernard','Chief Executive Officer (Vorsitz Managing Board)',1008.834,1183.698,31.650,2224.182,205.767,143229),('Roland Sackers','Chief Financial Officer (Managing Board)',633.220,506.580,65.770,1205.570,123.480,80098)]:
    M(R,'Vorstand',n,f,'','','',8,'','Managing Board (monistisch/zweistufig nach NL-Recht)')
    V(R,'Vorstand',n,'','Annual compensation gesamt (Festgehalt, variabler Cash-Bonus, Sonstiges)'+USD,8,'%.3f T USD; zusätzlich Beiträge Altersvorsorge %.3f T USD und %d gewährte PSUs' % (tot,ben,psu))
for n,f,t,rsu,bem in [('Stephen H. Rusckowski','Chair',132.750,5990,''),('Dr. Metin Colpan','Mitglied',86.500,5990,''),('Dr. Toralf Haag','Mitglied',82.500,5990,''),('Dr. Ross L. Levine','Mitglied',68.500,5990,''),
 ('Bert van Meurs','Mitglied',68.500,5990,''),('Eva van Pelt','Mitglied',72.500,5990,''),('Dr. Eva Pisa','Mitglied',75.500,5990,''),('Elizabeth E. Tallett','Mitglied',94.500,5990,''),
 ('Lawrence A. Rosen','Mitglied (nicht wiedergewählt, Hauptversammlung Juni 2025)',88.000,5990,''),('Prof. Dr. Elaine Mardis','Mitglied (nicht wiedergewählt, Hauptversammlung Juni 2025)',39.750,5990,'')]:
    M(R,'Aufsichtsrat',n,f,'','','2025-06-30' if 'nicht wiedergewählt' in f else '',18,'','Supervisory Board; Arbeitnehmervertretung nicht vorgesehen')
    V(R,'Aufsichtsrat',n,'','Barvergütung (Fix, Ausschuss) gesamt'+USD,18,'%.3f T USD; zusätzlich 5.990 Restricted Stock Units (Wert 230 T USD bei Gewährung)' % t)
K(R,'vorstand_mitglieder_zahl',2,'Personen',8,'Managing Board mit zwei Mitgliedern')
K(R,'pay_ratio',87,'Verhältnis',15,'CEO pay ratio (Gesamtjahresvergütung CEO zur Ø-Vergütung aller Beschäftigten weltweit) nach Dutch Corporate Governance Code, 87:1 (2024: 90:1); Ø Beschäftigte 111 T USD. Nicht nach § 162 AktG, keine Währungsumrechnung')
