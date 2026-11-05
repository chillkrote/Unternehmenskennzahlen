from lib import *
U = 'U000052'
R = ('governance/dokumente/aumovio-se/geschaeftsbericht-2025.pdf', U)
uni('AUMOVIO SE', U)
# Geschäftsbericht 2025, Vergütungsbericht; Seiten = PDF-Seiten; Beträge in T€ — nur anteilig ab Abspaltung (Vorstand ab 17.9.2025/15.8.2025, AR ab 3.9.2025), S. 64
VS = [('Philipp von Hirschheydt','Vorsitzender des Vorstands (CEO)','2025-03-12',705,'Vorstandsvorsitzender seit 12.3.2025; Vergütung nur für Zeitraum ab Abspaltung 17.9.2025'),
 ('Dr. Jutta A. Dönges','Mitglied des Vorstands','2025-11-01',513,'inkl. Sign-On-Bonus 273 T€; Vergütung ab 1.11.2025'),
 ('Ingo Holstein','Mitglied des Vorstands','2025-06-02',374,'Vergütung nur ab Abspaltung'),('Dr. Boris Mergell','Mitglied des Vorstands','2025-08-15',374,'Vergütung nur ab Abspaltung'),
 ('Dr. Ismail Dagli','Mitglied des Vorstands','2025-08-15',378,'Vergütung nur ab Abspaltung'),('Jean-François Tarabbia','Mitglied des Vorstands','2025-08-15',374,'Vergütung nur ab Abspaltung')]
for n,f,s,t,b in VS:
    M(R,'Vorstand',n,f,'',s,'',64,'','')
    V(R,'Vorstand',n,t,'Gewährte und geschuldete Vergütung gem. § 162 AktG (anteilig ab Abspaltung)',64,b)
AR = [('Stefan E. Buchner','Vorsitzender (seit 5.9.2025)',False,118),('Christiane Benner','Stellvertretende Vorsitzende (seit 5.9.2025)',True,69),('Clarissa Bader','Mitglied',True,53),
 ('Claus Thomas Bauer','Mitglied',False,53),('Râdu-Ioan Câtânet','Mitglied',True,52),('Joachim Dratwa','Mitglied',True,35),('Gábor Guzslován','Mitglied',True,36),
 ('Michael Iglhaut','Mitglied',True,70),('Ionut-Sergiu Istrati','Mitglied',True,36),('Prof. Dr. Sabina Jeschke','Mitglied',False,36),('Carmen Löffler','Mitglied',True,53),
 ('Dr. Petra Mayer','Mitglied',False,52),('Klaus Rosenfeld','Mitglied',False,36),('Georg F. W. Schaeffler','Mitglied',False,70),('Robin J. Stalker','Mitglied',False,70),('Prof. Dr. Katja Windt','Mitglied',False,35)]
for n,f,an,t in AR:
    M(R,'Aufsichtsrat',n,f,'Arbeitnehmervertreter' if an else 'Anteilseignervertreter','2025-09-03','',27,'','Bestellung als Arbeitnehmervertreter am 3.9.2025 lt. S. 27' if an else '')
    V(R,'Aufsichtsrat',n,t,'Gewährte und geschuldete Vergütung, anteilig ab 3.9.2025',64,'')
K(R,'vorstand_mitglieder_zahl',6,'Personen',64,'sechs Mitglieder (Eintritte 2025 im Zuge der Abspaltung)')
K(R,'ar_mitglieder_zahl',16,'Personen',27,'acht Anteilseigner- und acht Arbeitnehmervertreter')
K(R,'ar_arbeitnehmervertreter_zahl',8,'Personen',27,'Namentlich benannt S. 27')
K(R,'ar_frauen_zahl',6,'Personen',34,'Jeschke, Mayer, Windt, Benner, Löffler, Bader (37,5 %)')
K(R,'pay_ratio','','',64,'Ø Arbeitnehmer Deutschland (Vollzeit) 98 T€; Vorstandsvergütung nur anteilig ab Abspaltung, daher keine Pay Ratio gerechnet')
