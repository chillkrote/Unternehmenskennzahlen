from lib import *
U = 'U000812'
R = ('governance/dokumente/associated-british-foods-plc/annual-report-2025.pdf', U)
uni('Associated British Foods plc', U)
# Annual Report 2025 (52 Wochen bis 13.09.2025; financialreports.eu-Kopie); UK Directors' Remuneration Report; Seiten = PDF-Seiten; Beträge in GBP (T£), NICHT umgerechnet
GBP = ' (Betrag nur in GBP, Spalte betrag_tsd_eur leer, keine Umrechnung)'
for n, f, t, s in [('George Weston', 'Chief Executive (Vorsitz)', 3662, 129), ('Eoin Tonge', 'Finance Director (ab 04/2025 interim CEO Primark)', 3645, 129)]:
    M(R, 'Vorstand', n, f, '', '', '', 129, '', 'Executive Director')
    V(R, 'Vorstand', n, '', 'Single total figure of remuneration (Fixed + STIP + RSP/LTIP + Other)' + GBP, s, '%d T£' % t)
AR = [('Michael McLintock', 'Chairman', 472), ('Richard Reid', 'Non-Executive Director (ausgeschieden im Jahr)', 98), ('Emma Adamo', 'Non-Executive Director', 85), ('Graham Allan', 'Non-Executive Director (Chair Remuneration Committee)', 111),
      ('Heather Rabbatts', 'Senior Independent Director', 109), ('Annie Murphy', 'Non-Executive Director', 94), ('Kumsal Bayazit Besson', 'Non-Executive Director', 85), ('Loraine Woodhouse', 'Non-Executive Director', 92)]
for n, f, t in AR:
    M(R, 'Aufsichtsrat', n, f, '', '', '', 139, '', 'Board (monistisch): Non-Executive Directors')
    V(R, 'Aufsichtsrat', n, '', 'Non-executive directors’ remuneration (Fees)' + GBP, 139, '%d T£' % t)
K(R, 'vorstand_mitglieder_zahl', 2, 'Personen', 129, 'zwei Executive Directors')
K(R, 'pay_ratio', 126, 'Verhältnis', 135, 'CEO pay ratio Median 126:1 (Option B; Q1 137:1, Q3 104:1; 2024: 218:1); GB-Belegschaft, nicht § 162 AktG')
K(R, 'gender_pay_gap_gesamt', '', '', 136, 'UK Gender Pay Gap (Stand 5.4.2025): mean/median getrennt nach Food bzw. Primark ausgewiesen (Primark Median Frauen 17,8 % unter Männern bzw. 7,3 % darüber in zweiter Spalte) – kein Konzernwert')
