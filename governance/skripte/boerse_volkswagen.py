from lib import *
U = 'U000712'
G = ('governance/dokumente/volkswagen-ag/geschaeftsbericht-2025.pdf', U)   # Vergütungsbericht ist Teil des Geschäftsberichts (PDF S. 47-72)
# Vorstand: gewährte und geschuldete Vergütung 2025 (EUR -> T€), PDF S. 48-53; Reihenfolge lt. Aktienplan-Tabelle S. 57; Geschlecht lt. Anrede im Bericht (Herr/Frau)
for n,f,s,b,sp,t,bem in [
  ('Oliver Blume','Vorsitzender','','',48,6306.45867,'Volkswagen AG zahlt 50 % der Vorstandsvorsitzenden-Vergütung, übrige 50 % Porsche AG; Tabelle zeigt beide Anteile; Herr (S. 47)'),
  ('Arno Antlitz','Mitglied','','',49,5075.33919,'Herr (S. 56)'),
  ('Ralf Brandstätter','Mitglied (CEO Volkswagen (China) Investment Company)','2022-01-01','',50,3837.923,'Herr (S. 50); zusätzliche Vergütung der Volkswagen (China) Investment Company, 90/75 % angerechnet'),
  ('Gernot Döllner','Mitglied (Markengruppe Progressive, Vorsitzender des Vorstands der AUDI AG)','2023-09-01','',51,3404.523,'Herr (S. 51)'),
  ('Manfred Döss','Mitglied','2022-02-01','',51,2545.518,'Herr (S. 51); Vergütung 75 % eines ordentlichen Vorstandsmitglieds'),
  ('Gunnar Kilian','Mitglied (bis 4.7.2025)','','2025-07-04',52,1791.9597,'Herr (S. 52); Vergütung bis 4.7.2025'),
  ('Thomas Schäfer','Mitglied (Markengruppe Core, Vorsitzender des Vorstands der Marke Volkswagen Pkw)','2022-07-01','',52,3401.649,'Herr (S. 52)'),
  ('Thomas Schmall-von Westerholt','Mitglied (Vorsitzender des Vorstands der Volkswagen Group Components)','','',53,5630.3013,'Herr (S. 56)'),
  ('Hauke Stars','Mitglied','2022-02-01','',53,3401.076,'Frau (S. 53)')]:
    M(G,'Vorstand',n,f,'',s,b,sp,'','Funktion lt. Überschrift der Vergütungstabelle S. %d; Ressorts nicht vollständig ausgewertet' % sp)
    V(G,'Vorstand',n,round(t,3),'Summe gewährte und geschuldete Vergütung § 162 AktG (ohne Versorgungsaufwendungen)',sp,bem)
K(G,'vorstand_mitglieder_zahl',8,'Personen',226,'Frauenquote im Vorstand 12,5 % = 1 von 8 (nach Ausscheiden Kilian)')
K(G,'vorstand_frauen_zahl',1,'Personen',226,'12,5 %; Hauke Stars (Frau lt. Bericht S. 53)')
K(G,'ar_mitglieder_zahl',20,'Personen',226,'zehn Anteilseigner-, zehn Arbeitnehmervertreter; Land Niedersachsen entsendet zwei Anteilseignervertreter')
K(G,'ar_frauen_zahl',9,'Personen',227,'45 %')
K(G,'ar_arbeitnehmervertreter_zahl',10,'Personen',226)
K(G,'ar_gewerkschaftsvertreter_zahl',7,'Personen',226,'"sieben dieser Arbeitnehmervertreter sind von Gewerkschaften gewählte Gewerkschaftsvertreter"')
K(G,'mitbestimmung_ar','paritätisch (MitbestG), 10 von 20 Arbeitnehmervertreter, davon 7 Gewerkschaftsvertreter','',226)
K(G,'pay_ratio','','',72,'kein Verhältniswert; Vergleich der Veränderung mit bereinigtem Personalaufwand je FTE der Volkswagen AG, absolute Beträge nicht ausgewiesen')
