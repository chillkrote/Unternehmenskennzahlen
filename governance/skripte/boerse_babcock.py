from lib import *
U = 'U000826'
R = ('governance/dokumente/babcock-international-group-plc/annual-report-2026.pdf', U)
uni('Babcock International Group PLC', U)
# Annual Report and Financial Statements FY26 (Geschäftsjahr bis 31.03.2026, babcockinternational.com); Seiten = PDF-Seiten; Beträge in GBP (T£), NICHT umgerechnet
GBP = ' (Betrag nur in GBP, Spalte betrag_tsd_eur leer, keine Umrechnung)'
EX = [('David Lockwood', 'Chief Executive (CEO)', '', 8880, ''), ('David Mellors', 'Chief Financial Officer', '', 5293, ''), ('Harry Holt', 'Executive Director (Teiljahr lt. Tabelle)', '2025', 233, 'Teiljahr lt. Single-figure-Tabelle (Eintrittsdatum nicht geprüft)')]
for n, f, s, t, b in EX:
    M(R, 'Vorstand', n, f, '', s, '', 169, '', b)
    V(R, 'Vorstand', n, '', 'Single total figure of remuneration FY26 (Fixed + Bonus + PSP + Dividenden)' + GBP, 169, '%d T£; Geschäftsjahr bis 31.03.2026' % t)
AR = [('Dame Ruth Cairnie', 'Chair', 368, ''), ('Carl-Peter Forster', 'Senior Independent Director, Chair Remuneration Committee', 108, ''), ('Lord Parker', 'Non-Executive Director', 89, ''),
      ('John Ramsay', 'Non-Executive Director, Chair Audit Committee', 100, ''), ('Jane Moriarty', 'Non-Executive Director', 82, ''), ('Sir Kevin Smith', 'Non-Executive Director', 74, ''),
      ('Claudia Natanson', 'Non-Executive Director', 82, ''), ('Aedamar Comiskey', 'Non-Executive Director', 47, '2025-09-01'), ('Lucy Dimes', 'Non-Executive Director', 33, '')]
for n, f, t, s in AR:
    M(R, 'Aufsichtsrat', n, f, '', s, '2025-09-25' if n == 'Lucy Dimes' else '', 173, '', 'Board (monistisch): Non-Executive Directors')
    V(R, 'Aufsichtsrat', n, '', 'Single total figure Non-Executive Directors FY26 (Fees)' + GBP, 173, '%d T£' % t)
K(R, 'vorstand_mitglieder_zahl', 3, 'Personen', 169, 'drei Executive Directors in der Single-figure-Tabelle')
K(R, 'pay_ratio', 178, 'Verhältnis', 177, 'Median CEO pay ratio FY26 178:1 (FY25: 163:1); UK-Belegschaft; nicht § 162 AktG')
K(R, 'gender_pay_gap_gesamt', 6.2, '%', 86, 'Median Gender Pay Gap 2025 lt. Annual Report 6,2 % (Mean nicht erfasst)')
