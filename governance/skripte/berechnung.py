"""Pay Ratio und Gender Pay Gap im Vorstand nach Böckler-Methodik.

Liest verguetung.csv / gremien_mitglieder.csv, ergänzt die unten dokumentierten Eingangsdaten
und schreibt berechnungen/*.csv. Aufruf aus dem Repo-Root: python3 governance/skripte/berechnung.py
"""
import csv, os, sys
sys.path.insert(0, 'stammdaten')
import ids  # zentrale Unternehmens-IDs; Ordner der Dokumente unter governance/dokumente/ tragen die alte Schreibweise
from statistics import mean

D = 'governance'
rd = lambda f: list(csv.DictReader(open(f'{D}/{f}', encoding='utf-8-sig')))
VG, MB = rd('verguetung.csv'), rd('gremien_mitglieder.csv')
GB = lambda u: f'governance/dokumente/{ids.lade().ordner(u)}/geschaeftsbericht-2025.pdf'
VB = lambda u: f'governance/dokumente/{ids.lade().ordner(u)}/verguetungsbericht-2025.pdf'

# Variante A: Ø-Jahresvergütung der Beschäftigten in Deutschland (FTE) aus der vergleichenden Darstellung (§ 162 Abs. 1 Nr. 2 AktG)
# unternehmen_id: (T€, Beschäftigtenkreis, Dokument, Seite)
A = {
 'U000151': (121.0, 'Gesamtbelegschaft (Ø-Vergütung, Konzern lt. vergleichender Darstellung)', VB('U000151'), 48),
 'U000279': (105.283, 'Gesamtbelegschaft Deutschland (Ø-Vergütung, Vollzeitkraft ohne Altersversorgung)', VB('U000279'), 56),
 'U000017': (114.0, 'Beschäftigte Deutschland, Vollzeitäquivalente (Personalaufwand je FTE)', VB('U000017'), 19),
 'U000415': (101.662, 'aktive Stammbelegschaft Deutschland, auf Vollzeit normiert', VB('U000415'), 20),
 'U000036': (95.0, 'Beschäftigte Deutschland, Vollzeitäquivalente (Ø-Vergütung lt. vergleichender Darstellung)', GB('U000036'), 333),
 'U000067': (101.227, 'Beschäftigte BMW AG, Vollzeitäquivalente (Ø-Vergütung lt. vergleichender Darstellung)', VB('U000067'), 40),
 'U000535': (116.0, 'Belegschaft Deutschland (ohne Siemens Healthineers), FTE', VB('U000535'), 38),
 'U000515': (146.0, 'Mitarbeitende des SAP-Konzerns, Vollzeitkräfte (Konzern, nicht nur Deutschland)', VB('U000515'), 35),
 'U000124': (108.0, 'Arbeitnehmer Commerzbank AG auf VZK-Basis (Brutto-Personalaufwand)', VB('U000124'), 50),
 'U000148': (120.974, 'Beschäftigte Deutsche Bank Konzern weltweit auf Vollzeitbasis (nicht nur Deutschland)', GB('U000148'), 755),
 'U000537': (120.0, 'Workforce Deutschland inkl. Siemens Gamesa Deutschland, FTE (GJ Okt 2024-Sep 2025)', VB('U000537'), 19),
}
# Variante B (Böckler 2018): (Konzern-Personalaufwand - Vorstandsvergütung) / Konzernbeschäftigte
# unternehmen_id: (Personalaufwand Mio. €, Beschäftigte, Basis, Seite Aufwand, Seite Beschäftigte)
B = {
 'U000125': (5922, 92653, 'Mitarbeitende zum 31.12. (fortgeführte Aktivitäten), Personalaufwand fortgeführte Aktivitäten', 260, 2),
 'U000742': (693.8, 16582, 'Ø Mitarbeiter*innen (ohne Werkstudierende, Praktikant*innen, Auszubildende)', 128, 2),
 'U000279': (3790, 47300, 'Ø Mitarbeiter:innen Konzern', 109, 109),
 'U000017': (3226, 61952, 'Mitarbeiter im Jahresdurchschnitt (Köpfe)', 436, 454),
 'U000061': (12299, 110440, 'Ø Beschäftigte BASF-Gruppe; Aufwand inkl. 878 Mio. € nicht fortgeführter Coatings-Bereich', 412, 262),
 'U000073': (1957, 22399, 'Headcount zum Stichtag (Bericht nutzt ab 2025 Headcount statt FTE)', 290, 134),
 'U000161': (19781, 199223, 'Ø Personalbestand Gesamtkonzern (inkl. Beamte und Auszubildende)', 305, 305),
 'U000415': (1284, 13674, 'Gesamtbelegschaft zum 31.12. (Personen)', 283, 51),
 'U000510': (2948, 20120, 'Beschäftigte zum 31.12. in Vollzeitäquivalenten', 192, 3),
 'U000537': (10424, 101414, 'Ø Mitarbeitende GJ 2025', 192, 107),
}
# von den Unternehmen selbst ausgewiesene Quote (andere Definition als Variante A/B, nur zum Abgleich)
BEM = {'U000125': '; CEO-Wert enthält Abfindung 4.788 T€ (Ausscheiden 31.12.2025); Vorstandsvergütung: nicht aller 2025 aktiven Mitglieder ganzjährig'}
PUBLIZIERT = {
 'U000151': (97.0, 'ESRS S1-16: höchstbezahlte Person (CEO) zu Median-Gesamtvergütung aller Beschäftigten (Geschäftsbericht S. 111)'),
 'U000073': (125.83, 'Verhältnis höchstbezahltes Vorstandsmitglied zu Median-Belegschaft, lt. Vergütungsbericht'),
 'U000502': (144.5, 'lt. Vergütungsbericht (Definition dort)'),
}
# Rheinmetall weist Personalaufwand je FTE direkt aus (GB S. 56): 97 T€
B_DIREKT = {'U000502': (97.0, 'Personalaufwand je Beschäftigtem (Kapazität FTE), Konzern', GB('U000502'), 56)}

# Geschlecht nur aus dokumentierten Angaben (nie aus Vornamen): person_id-Name, Unternehmen, Beleg, Seite
FRAUEN = [
 ('Ilka Horstmeier', 'U000067', VB('U000067'), 28, 'Bezeichnung "Arbeitsdirektorin"'),
 ('Dr. Bettina Orlopp', 'U000124', VB('U000124'), 24, 'Bezeichnung "Vorstandsvorsitzende"'),
 ('Hauke Stars', 'U000712', GB('U000712'), 53, 'Anrede "Frau Stars" im Vergütungsbericht; Frauenquote Vorstand 12,5 % (S. 226)'),
 ('Dr. Astrid Arndt', 'U000742', VB('U000742'), 32, 'Possessivpronomen "ihrem Anstellungsvertrag"; Frauenanteil Vorstand 40 % im Vorjahr (Arndt, Dembeck)'),
 ('Dr. Sandra Dembeck', 'U000742', VB('U000742'), 32, 'Possessivpronomen "ihr Anstellungsvertrag"; Frauenanteil Vorstand GB S. 108'),
 ('Sylvie Nicol', 'U000279', VB('U000279'), 15, 'Geschlechtsangabe (w) in der Vergütungstabelle'),
 ('Michelle Robertson', 'U000017', GB('U000017'), 43, 'Erfüllung § 76 Abs. 3a AktG (mind. eine Frau) "mit Michelle Robertson"'),
 ('Dr. Katja Scharpwinkel', 'U000061', GB('U000061'), 134, '"With Dr. Katja Scharpwinkel, there was one female Board member"'),
 ('Astrid Hermann', 'U000073', GB('U000073'), 50, 'Vorstand zu 50 % weiblich, namentlich genannt'),
 ('Nicola D. Lafrentz', 'U000073', GB('U000073'), 50, 'namentlich genannt'),
 ('Grita Loebsack', 'U000073', GB('U000073'), 50, 'namentlich genannt'),
 ('Katja Garcia Vila', 'U000415', VB('U000415'), 3, 'Bezeichnung "Vorständin"'),
 ('Dr. Silke Maurer', 'U000415', VB('U000415'), 3, 'Bezeichnung "Vorständin"'),
 ('Dr. Vera Saal', 'U000502', GB('U000502'), 94, '"Personalvorständin"'),
 ('Dr. Ursula Biernert-Kloß', 'U000502', GB('U000502'), 163, '"Arbeitsdirektorin"'),
 ('Katja van Doren', 'U000510', GB('U000510'), 8, 'Lebenslauf im Bericht ("Personalvorständin ... Ihre Tätigkeit")'),
]
frauen = {(n, u) for n, u, *_ in FRAUEN}

def ganzjaehrig(m):
    """Mitglied war das ganze Berichtsjahr im Amt (aus seit/bis; leeres seit = vor dem GJ, nicht überall belegt)."""
    s, b = m['seit'], m['bis']
    if b:
        return False
    return not (s.startswith('2025'))
GJ_BEGINN_AUSNAHME = {'U000502': {'2025-01-01'}}  # 1.1.2025 gilt als volles Jahr

def vorstand(u):
    out = []
    for m in MB:
        if m['unternehmen_id'] != u or m['organ'] != 'Vorstand':
            continue
        v = next((x for x in VG if x['unternehmen_id'] == u and x['gremium'] == 'Vorstand' and x['name'] == m['name']), None)
        if not v:
            continue
        voll = ganzjaehrig(m) or m['seit'] in GJ_BEGINN_AUSNAHME.get(u, ())
        out.append(dict(name=m['name'], funktion=m['funktion'], t=float(v['betrag_tsd_eur']), voll=voll, quelle=v['quelle_dokument'], seite=v['seite']))
    return out

rows = []
def add(u, variante, bezug, zaehler, nenner, basis, quellen, bem=''):
    rows.append(dict(unternehmen_id=u, gj=2025, variante=variante, bezug=bezug, zaehler_teur=round(zaehler, 1), nenner_teur=round(nenner, 1),
                     pay_ratio=round(zaehler / nenner, 1), nenner_basis=basis, quellen=' | '.join(quellen), bemerkung=bem))

for u in sorted(set(A) | set(B) | set(B_DIREKT)):
    vs = vorstand(u)
    if not vs:
        continue
    ceo = [x for x in vs if 'Vorsitz' in x['funktion'] and x['voll']]
    voll = [x for x in vs if x['voll']]
    vorst_sum = sum(x['t'] for x in vs)
    nenner = []
    if u in A:
        t, basis, doc, s = A[u]
        nenner.append(('A', t, basis, [f'{doc} S. {s}'], ''))
    if u in B:
        pa, n, basis, s1, s2 = B[u]
        t = (pa * 1000 - vorst_sum) / n
        nenner.append(('B', t, basis, [f'{GB(u)} S. {s1} (Personalaufwand {pa:,} Mio. €)', f'{GB(u)} S. {s2} (Beschäftigte {n:,})'.replace(',', '.')],
                       'Personalaufwand abzüglich Summe Vorstandsvergütung (alle Mitglieder des Jahres)'))
    if u in B_DIREKT:
        t, basis, doc, s = B_DIREKT[u]
        nenner.append(('B', t, basis, [f'{doc} S. {s}'], 'Personalaufwand je FTE direkt ausgewiesen, nicht um Vorstandsvergütung bereinigt'))
    for var, t, basis, q, bem in nenner:
        zusatz = BEM.get(u, '') + '; Vorstandsvergütung = gewährte/geschuldete Vergütung § 162 AktG lt. verguetung.csv'
        if ceo:
            c = ceo[0]
            add(u, var, 'Vorstandsvorsitzender', c['t'], t, basis, q + [f"{c['quelle']} S. {c['seite']}"], bem + zusatz)
        else:
            rows.append(dict(unternehmen_id=u, gj=2025, variante=var, bezug='Vorstandsvorsitzender', zaehler_teur='', nenner_teur=round(t, 1), pay_ratio='',
                             nenner_basis=basis, quellen=' | '.join(q), bemerkung='kein ganzjähriger Vorsitzender (Wechsel im Jahr)'))
        if voll:
            add(u, var, f'Ø ganzjährige Vorstandsmitglieder (n={len(voll)})', mean(x['t'] for x in voll), t, basis, q + [f"{voll[0]['quelle']} S. {voll[0]['seite']}"], bem + zusatz)
for u, (r, b) in PUBLIZIERT.items():
    rows.append(dict(unternehmen_id=u, gj=2025, variante='Unternehmen', bezug='ausgewiesen', zaehler_teur='', nenner_teur='', pay_ratio=r, nenner_basis=b,
                     quellen=GB(u) if u in ('U000073', 'U000151') else VB(u), bemerkung='nur zum Abgleich, andere Definition'))

# Gender Pay Gap im Vorstand (unbereinigt) = (Ø Männer - Ø Frauen) / Ø Männer; nur ganzjährige Mitglieder
gap = []
for u in sorted({x[1] for x in FRAUEN}):
    vs = [x for x in vorstand(u) if x['voll']]
    f = [x for x in vs if (x['name'], u) in frauen]
    m = [x for x in vs if (x['name'], u) not in frauen]
    nonvoll = [x['name'] for x in vorstand(u) if not x['voll']]
    if f and m:
        mf, mm = mean(x['t'] for x in f), mean(x['t'] for x in m)
        g = (mm - mf) / mm * 100
        gap.append(dict(unternehmen_id=u, gj=2025, n_frauen=len(f), n_maenner=len(m), ø_frauen_teur=round(mf, 1), ø_maenner_teur=round(mm, 1),
                        gender_pay_gap_pct=round(g, 1), nicht_einbezogen=', '.join(nonvoll),
                        bemerkung='unbereinigt, sehr kleine Fallzahl; Funktionen und Ressorts nicht kontrolliert; Geschlecht nur aus dokumentierten Angaben'))
    else:
        gap.append(dict(unternehmen_id=u, gj=2025, n_frauen=len(f), n_maenner=len(m), ø_frauen_teur='', ø_maenner_teur='', gender_pay_gap_pct='',
                        nicht_einbezogen=', '.join(nonvoll), bemerkung='nicht berechenbar: keine ganzjährige Frau bzw. kein ganzjähriger Mann im Vorstand'))

def w(f, rs):
    with open(f'{D}/berechnungen/{f}', 'w', newline='', encoding='utf-8-sig') as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rs[0].keys())); wr.writeheader(); wr.writerows(rs)
w('pay_ratio.csv', rows); w('gender_pay_gap_vorstand.csv', gap)
w('geschlecht_belege.csv', [dict(name=n, unternehmen_id=u, geschlecht='weiblich', quelle_dokument=q, seite=s, beleg=b) for n, u, q, s, b in FRAUEN])
print(len(rows), 'Pay-Ratio-Zeilen;', len(gap), 'Gap-Zeilen')
