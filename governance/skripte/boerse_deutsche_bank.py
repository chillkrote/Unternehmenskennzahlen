from lib import *
U = 'U000148'
G = ('governance/dokumente/deutsche-bank-aktiengesellschaft/geschaeftsbericht-2025.pdf', U)
# Vergütungsbericht ist Teil des Geschäftsberichts; Seiten = PDF-Seiten. Mitglieder/Seiten (Anteilseigner/Arbeitnehmer) stammen aus pilot_banken (Jahresabschluss).
VS = [('Christian Sewing',15556,745),('James von Moltke',11217,745),('Fabrizio Campelli',6998,746),('Dr. Marcus Chromik',1903,746),
 ('Bernd Leukert',5264,746),('Alexander von zur Mühlen',6746,746),('Laura Padovani',2787,747),('Claudio de Sanctis',4540,747),('Rebecca Short',4720,747),
 ('Prof. Dr. Stefan Simon',5873,747),('Olivier Vigneron',2541,748)]
bem = {'Dr. Marcus Chromik':'Mitglied seit 1.5.2025, zeitanteilig','Laura Padovani':'Mitglied seit 1.7.2024','Prof. Dr. Stefan Simon':'Mitglied bis 30.4.2025; Zufluss aus Restricted Equity Award 2018/Cliff-Vesting','Olivier Vigneron':'Mitglied bis 19.5.2025; inkl. Beendigungsleistung 620 T€',
       'Christian Sewing':'Zufluss inkl. Restricted Equity Award für 2018 (7.205 T€, Cliff-Vesting)'}
for n,t,p in VS:
    V(G,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Gesamtvergütung)',p,bem.get(n,''))
V(G,'Vorstand','Gesamt (aktive Mitglieder)',sum(x[1] for x in VS),'Summe der Einzelwerte (gerechnet)',749,'')
AR = [('Alexander Wynaendts',950),('Frank Schulze',475),('Prof. Dr. Norbert Winkeljohann',575),('Susanne Bleidt',300),('Mayree Clark',450),('Jan Duscheck',300),('Manja Eifert',300),
 ('Claudia Fieber',300),('Sigmar Gabriel',300),('Florian Haggenmiller',300),('Timo Heider',300),('Dr. Klaus Moosmayer',175),('Kirsty Roth',175),('Gerlinde M. Siebert',300),
 ('Yngve Slyngstad',300),('Stephan Szukalski',300),('John Alexander Thain',400),('Jürgen Tögel',300),('Michele Trogni',450),('Dr. Dagmar Valcárcel',187.5),('Dr. Theodor Weimer',125),('Frank Witter',450)]
for n,t in AR:
    V(G,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (Festvergütung + Ausschussvergütung)',753,'Mitglied ab 22.5.2025' if n in('Dr. Klaus Moosmayer','Kirsty Roth') else ('Mitglied bis 22.5.2025' if n in ('Dr. Dagmar Valcárcel','Dr. Theodor Weimer') else ''))
V(G,'Aufsichtsrat','Gesamt',7712.5,'Summe',753,'Ausweis im Bericht')
K(G,'ar_frauen_zahl',7,'Personen',418,'"sieben von zwanzig Mitgliedern beziehungsweise 35 %"; Arbeitnehmerseite 4 Frauen/6 Männer, Anteilseignerseite 3 Frauen/7 Männer (PDF S. 797)')
K(G,'vorstand_frauen_zahl',2,'Personen',418,'"zwei von neun Mitgliedern beziehungsweise 22 %" zum Jahresende 2025; Personen im Dokument nicht namentlich ausgewiesen')
K(G,'ar_arbeitnehmervertreter_zahl',10,'Personen',797,'Arbeitnehmerseite 4 Frauen und 6 Männer = 10 von 20')
K(G,'mitbestimmung_ar','paritätisch (10 von 20 Arbeitnehmervertreter)','',797,'Anteilseignerseite 10, Arbeitnehmerseite 10 lt. Besetzungsangabe; MitbestG nicht ausdrücklich zitiert')
K(G,'pay_ratio','','',755,'Deutsche Bank weist kein Verhältnis aus; Ø-Vergütung weltweit auf Vollzeitbasis 2025: 120.974 €; Berechnung siehe berechnungen/pay_ratio.csv')
