from lib import *
U = 'U000143'
R = ('governance/dokumente/delivery-hero-se/geschaeftsbericht-2025.pdf', U)
uni('Delivery Hero SE', U)
# Geschäftsbericht 2025, Vergütungsbericht; Seiten = PDF-Seiten; Beträge in T€ (gewährt und geschuldet, S. 65)
VS = [('Niklas Östberg','Vorstandsvorsitzender (CEO), Mitgründer',525.6),('Pieter-Jan Vandepitte','Chief Operating Officer (COO)',576.0),('Marie-Anne Popp','Finanzvorständin (CFO)',498.4)]
for n,f,t in VS:
    M(R,'Vorstand',n,f,'','2025' if 'Popp' in n else '','',65,'','Eintritt im Geschäftsjahr 2025 (genaues Datum im Bericht nicht genannt; Jahresangabe als Marker für Nicht-Ganzjährigkeit, Grundvergütung 441 T€ anteilig)' if 'Popp' in n else '')
    V(R,'Vorstand',n,t,'Gesamtvergütung gewährt und geschuldet gem. § 162 AktG (nur Grundvergütung und Nebenleistungen)',65 if n!='Marie-Anne Popp' else 65,'seit 2025 im Vorstand (Vorjahr n/a)' if 'Popp' in n else '')
M(R,'Vorstand','Dr. Johannes Bruder','Chief Product Officer (CPO)','','2026-01-01','',14,'','Bestellung zum 1.1.2026 als viertes Vorstandsmitglied; keine Vergütung für 2025')
AR = [('Kristin Skogen Lund','Vorsitzende',False,440.0),('Roger Rabalais','Mitglied',False,161.7),('Dr. Martin Enderle','Mitglied',False,111.1),('Scott Ferguson','Mitglied',False,90.0),
 ('Isabel Poscherstnikov','Mitglied',True,80.7),('Warren Jenson','Mitglied',False,76.7),('Judith Jungmann','Mitglied',False,70.2),('Gabriella Ardbo','Mitglied',True,70.0),
 ('Nils Engvall','Mitglied',True,70.0),('Dimitrios Tsaousis','Mitglied',True,50.0)]
for n,f,an,t in AR:
    M(R,'Aufsichtsrat',n,f,'Arbeitnehmervertreter' if an else 'Anteilseignervertreter','','',68,'','Fußnote 1 "Arbeitnehmervertreter"' if an else '')
    V(R,'Aufsichtsrat',n,t,'Gesamtvergütung Aufsichtsrat (Festvergütung + Ausschussvergütung)',68,'Mitgliedschaft teilweise unterjährig' if n in ('Warren Jenson','Judith Jungmann','Dr. Martin Enderle') else '')
K(R,'vorstand_mitglieder_zahl',3,'Personen',65,'drei vergütete Mitglieder 2025; vierter (Bruder) ab 1.1.2026')
K(R,'ar_mitglieder_zahl',10,'Personen',68,'zehn vergütete Mitglieder 2025 (inkl. unterjährig Ausgeschiedener/Neuer)')
K(R,'ar_arbeitnehmervertreter_zahl',4,'Personen',68,'Poscherstnikov, Ardbo, Engvall, Tsaousis (Fußnote)')
K(R,'pay_ratio','','',69,'Keine absolute Ø-Vergütung ausgewiesen (nur Änderung Belegschaft Deutschland +8 %)')
