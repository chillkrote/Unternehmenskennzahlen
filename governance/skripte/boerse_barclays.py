from lib import *
U = 'U000832'
R = ('governance/dokumente/barclays-plc/annual-report-2025.pdf', U)
uni('Barclays PLC', U)
# Annual Report 2025 (home.barclays); Seiten = PDF-Seiten; Beträge in GBP (T£), NICHT umgerechnet
GBP = ' (Betrag nur in GBP, Spalte betrag_tsd_eur leer, keine Umrechnung)'
for n, f, t in [('C.S. Venkatakrishnan', 'Group Chief Executive', 15045), ('Anna Cross', 'Group Finance Director', 8970)]:
    M(R, 'Vorstand', n, f, '', '', '', 177, '', 'Executive Director')
    V(R, 'Vorstand', n, '', 'Single total figure for 2025 remuneration (Fixed, Bonus, LTIP)' + GBP, 177, '%d T£' % t)
AR = [('Nigel Higgins', 'Chairman', 937, '', ''), ('Robert Berry', 'Non-Executive Director', 328, '', ''), ('Tim Breedon', 'Non-Executive Director', 136, '', '2025-04-30'), ('Dawn Fitzpatrick', 'Non-Executive Director', 263, '', ''),
      ('Mary Francis', 'Non-Executive Director', 222, '', ''), ('Brian Gilvary', 'Non-Executive Director', 246, '', ''), ('Sir John Kingman', 'Non-Executive Director', 601, '', ''),
      ('Diony Lebot', 'Non-Executive Director', 103, '2025-03-17', ''), ('Mary Mack', 'Non-Executive Director', 76, '2025-06-01', ''), ('Marc Moses', 'Non-Executive Director', 253, '', ''),
      ('Diane Schueneman', 'Non-Executive Director', 37, '', '2025-01-31'), ('Brian Shea', 'Non-Executive Director', 211, '', ''), ('Julia Wilson', 'Non-Executive Director', 366, '', '')]
for n, f, t, s, b in AR:
    M(R, 'Aufsichtsrat', n, f, '', s, b, 195, '', 'Board (monistisch): Chairman und Non-Executive Directors')
    V(R, 'Aufsichtsrat', n, '', 'Single total figure 2025 (Fees + Benefits)' + GBP, 195, '%d T£' % t)
K(R, 'vorstand_mitglieder_zahl', 2, 'Personen', 177, 'zwei Executive Directors')
K(R, 'pay_ratio', 248, 'Verhältnis', 192, 'Group-CEO-Pay-Ratio Median 248:1 (25. Perzentil 360:1, 75. Perzentil 148:1; Option A; 2024: 201:1); UK-Beschäftigte; nicht § 162 AktG')
