"""Pay Ratio und Gender Pay Gap im Vorstand nach Böckler-Methodik.

Liest verguetung.csv / gremien_mitglieder.csv, ergänzt die unten dokumentierten Eingangsdaten
und schreibt berechnungen/*.csv. Aufruf aus dem Repo-Root: python3 governance/skripte/berechnung.py
"""
import csv, os
from statistics import mean

D = 'governance'
rd = lambda f: list(csv.DictReader(open(f'{D}/{f}', encoding='utf-8-sig')))
VG, MB = rd('verguetung.csv'), rd('gremien_mitglieder.csv')
GB = lambda u: f'governance/dokumente/{u}/geschaeftsbericht-2025.pdf'
VB = lambda u: f'governance/dokumente/{u}/verguetungsbericht-2025.pdf'

# Variante A: Ø-Jahresvergütung der Beschäftigten in Deutschland (FTE) aus der vergleichenden Darstellung (§ 162 Abs. 1 Nr. 2 AktG)
# unternehmen_id: (T€, Beschäftigtenkreis, Dokument, Seite)
A = {
 'adidas-ag': (114.0, 'Beschäftigte Deutschland, Vollzeitäquivalente (Personalaufwand je FTE)', VB('adidas-ag'), 19),
 'mtu-aero-engines-ag': (101.662, 'aktive Stammbelegschaft Deutschland, auf Vollzeit normiert', VB('mtu-aero-engines-ag'), 20),
 'siemens-energy-ag': (120.0, 'Workforce Deutschland inkl. Siemens Gamesa Deutschland, FTE (GJ Okt 2024-Sep 2025)', VB('siemens-energy-ag'), 19),
}
# Variante B (Böckler 2018): (Konzern-Personalaufwand - Vorstandsvergütung) / Konzernbeschäftigte
# unternehmen_id: (Personalaufwand Mio. €, Beschäftigte, Basis, Seite Aufwand, Seite Beschäftigte)
B = {
 'adidas-ag': (3226, 61952, 'Mitarbeiter im Jahresdurchschnitt (Köpfe)', 436, 454),
 'basf-se': (12299, 110440, 'Ø Beschäftigte BASF-Gruppe; Aufwand inkl. 878 Mio. € nicht fortgeführter Coatings-Bereich', 412, 262),
 'beiersdorf-aktiengesellschaft': (1957, 22399, 'Headcount zum Stichtag (Bericht nutzt ab 2025 Headcount statt FTE)', 290, 134),
 'deutsche-telekom-ag': (19781, 199223, 'Ø Personalbestand Gesamtkonzern (inkl. Beamte und Auszubildende)', 305, 305),
 'mtu-aero-engines-ag': (1284, 13674, 'Gesamtbelegschaft zum 31.12. (Personen)', 283, 51),
 'rwe-aktiengesellschaft': (2948, 20120, 'Beschäftigte zum 31.12. in Vollzeitäquivalenten', 192, 3),
 'siemens-energy-ag': (10424, 101414, 'Ø Mitarbeitende GJ 2025', 192, 107),
}
# von den Unternehmen selbst ausgewiesene Quote (andere Definition als Variante A/B, nur zum Abgleich)
PUBLIZIERT = {
 'beiersdorf-aktiengesellschaft': (125.83, 'Verhältnis höchstbezahltes Vorstandsmitglied zu Median-Belegschaft, lt. Vergütungsbericht'),
 'rheinmetall-ag': (144.5, 'lt. Vergütungsbericht (Definition dort)'),
}
# Rheinmetall weist Personalaufwand je FTE direkt aus (GB S. 56): 97 T€
B_DIREKT = {'rheinmetall-ag': (97.0, 'Personalaufwand je Beschäftigtem (Kapazität FTE), Konzern', GB('rheinmetall-ag'), 56)}

# Geschlecht nur aus dokumentierten Angaben (nie aus Vornamen): person_id-Name, Unternehmen, Beleg, Seite
FRAUEN = [
 ('Michelle Robertson', 'adidas-ag', GB('adidas-ag'), 43, 'Erfüllung § 76 Abs. 3a AktG (mind. eine Frau) "mit Michelle Robertson"'),
 ('Dr. Katja Scharpwinkel', 'basf-se', GB('basf-se'), 134, '"With Dr. Katja Scharpwinkel, there was one female Board member"'),
 ('Astrid Hermann', 'beiersdorf-aktiengesellschaft', GB('beiersdorf-aktiengesellschaft'), 50, 'Vorstand zu 50 % weiblich, namentlich genannt'),
 ('Nicola D. Lafrentz', 'beiersdorf-aktiengesellschaft', GB('beiersdorf-aktiengesellschaft'), 50, 'namentlich genannt'),
 ('Grita Loebsack', 'beiersdorf-aktiengesellschaft', GB('beiersdorf-aktiengesellschaft'), 50, 'namentlich genannt'),
 ('Katja Garcia Vila', 'mtu-aero-engines-ag', VB('mtu-aero-engines-ag'), 3, 'Bezeichnung "Vorständin"'),
 ('Dr. Silke Maurer', 'mtu-aero-engines-ag', VB('mtu-aero-engines-ag'), 3, 'Bezeichnung "Vorständin"'),
 ('Dr. Vera Saal', 'rheinmetall-ag', GB('rheinmetall-ag'), 94, '"Personalvorständin"'),
 ('Dr. Ursula Biernert-Kloß', 'rheinmetall-ag', GB('rheinmetall-ag'), 163, '"Arbeitsdirektorin"'),
 ('Katja van Doren', 'rwe-aktiengesellschaft', GB('rwe-aktiengesellschaft'), 8, 'Lebenslauf im Bericht ("Personalvorständin ... Ihre Tätigkeit")'),
]
frauen = {(n, u) for n, u, *_ in FRAUEN}

def ganzjaehrig(m):
    """Mitglied war das ganze Berichtsjahr im Amt (aus seit/bis; leeres seit = vor dem GJ, nicht überall belegt)."""
    s, b = m['seit'], m['bis']
    if b:
        return False
    return not (s.startswith('2025'))
GJ_BEGINN_AUSNAHME = {'rheinmetall-ag': {'2025-01-01'}}  # 1.1.2025 gilt als volles Jahr

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
        zusatz = '; Vorstandsvergütung = gewährte/geschuldete Vergütung § 162 AktG lt. verguetung.csv'
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
                     quellen=VB(u) if u != 'beiersdorf-aktiengesellschaft' else GB(u), bemerkung='nur zum Abgleich, andere Definition'))

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
