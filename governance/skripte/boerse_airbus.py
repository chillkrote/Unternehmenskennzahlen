from lib import *
U = 'U000026'
R = ('governance/dokumente/airbus-se/jahresabschluss-2025.pdf', U)
uni('Airbus SE', U)
# Airbus Financial Statements 2025, Note 33 (Remuneration); niederländisches Recht, kein § 162 AktG; Beträge sind IFRS-Aufwand des Jahres (nicht "gewährt und geschuldet"); Seiten = PDF-Seiten
M(R,'Vorstand','CEO Airbus SE (Name im Dokument nicht genannt)','Chief Executive Officer (einziges geschäftsführendes Mitglied des Board)','','','',51,'','Name des CEO steht nicht in diesem Dokument; Report of the Board of Directors (Abschnitt 2.3.2) wegen Bot-Schutz der Airbus-Website nicht abgerufen')
V(R,'Vorstand','CEO Airbus SE (Name im Dokument nicht genannt)',10122.430,'CEO-Vergütung als IFRS-Aufwand 2025 (Grundgehalt, variable Vergütung, Altersvorsorge, LTI, Sonstiges, Sozialabgaben); keine gewährte und geschuldete Vergütung nach § 162 AktG',51,'Grundgehalt 1.560 T€, Jahresbonus 2.737,8 T€, Altersvorsorge 1.077,0 T€, LTI 3.152,2 T€, Sonstiges 34,0 T€, Sozialabgaben 1.561,5 T€; 2024 insgesamt 7.998 T€ (Summe der Einzelposten)')
V(R,'Vorstand','Gesamt (Executive Committee inkl. CEO)',56700,'Gesamtaufwand Key Management Personnel 2025 inkl. Non-Executive Board Members (56,7 Mio. €)',49,'Executive Committee: kurzfristig 18,9, Altersvorsorge 5,3, LTI 13,0, Abfindungen 9,7, Sonstiges 0,2, Sozialabgaben 6,1 Mio. €; Non-Executive 3,5 Mio. €')
AR = [('René Obermann','Chair',662.5),('Victor Chu','Non-Executive Director',228.0),('Jean-Pierre Clamadieu','Non-Executive Director',337.0),('Mark Dunkerley','Non-Executive Director',316.0),
 ('Stephan Gemkow','Non-Executive Director (Vorsitz Audit Committee seit 15.4.2025)',311.845),('Catherine Guillouard','Non-Executive Director (Vorsitz Audit Committee bis 15.4.2025)',309.784),
 ('Dr. Doris Höpke','Non-Executive Director (seit 15.4.2025)',216.287),('Amparo Moraleda','Non-Executive Director',331.0),('Claudia Nemat','Non-Executive Director (bis 15.4.2025)',53.509),
 ('Irene Rummelhoff','Non-Executive Director',229.5),('Antony Wood','Non-Executive Director',269.0),('Dr Fei Yu Xu','Non-Executive Director',203.702)]
for n,f,t in AR:
    M(R,'Aufsichtsrat',n,f,'','','',53,'','Board of Directors (Non-Executive Directors); keine Arbeitnehmervertreter im Board ausgewiesen')
    V(R,'Aufsichtsrat',n,t,'Vergütung gesamt (Fixum und Sitzungsgelder), Anhang Note 33',53,'')
V(R,'Aufsichtsrat','Gesamt',3468.127,'Gesamtvergütung Non-Executive Directors',53,'inkl. 2024 ausgeschiedenem Ralph D. Crosby, Jr. nur im Vorjahr')
K(R,'vorstand_mitglieder_zahl',1,'Personen',51,'CEO ist einziges geschäftsführendes Board-Mitglied; Executive Committee getrennt')
K(R,'pay_ratio','','',51,'Im Jahresabschluss nicht enthalten; Report of the Board of Directors (Abschnitt 2.3.2) nicht abgerufen (Airbus-Website mit Bot-Schutz)')
