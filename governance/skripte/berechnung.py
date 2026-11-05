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
VG, MB = [r for r in VG if r['gj'] == '2025'], [r for r in MB if r['gj'] == '2025']  # Berechnung nur GJ 2025 (andere Jahre aus Handeingaben nicht einmischen)
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
 'U000716': (75.1, 'Gesamtbelegschaft Immobilienwirtschaft konzernweit, Vollzeitäquivalente (Ø-Gesamtvergütung lt. vergleichender Darstellung)', VB('U000716'), 32),
 'U000274': (85.0, 'Gesamtbelegschaft Heidelberg Materials AG (nur Muttergesellschaft) inkl. Top-/Senior-Management ohne Vorstand, Vollzeitbasis, Direktvergütung', VB('U000274'), 32),
 'U000234': (53.0, 'Konzern weltweit, Ø Löhne und Gehälter je FTE (nicht nur Deutschland)', GB('U000234'), 78),
 'U000264': (126.2, 'Mitarbeiter Hannover Rück SE in Deutschland, Vollzeitäquivalente (Ø-Vergütung lt. vergleichender Darstellung)', VB('U000264'), 21),
 'U000195': (84.0, 'Arbeitnehmer in Deutschland, regelmäßige Zielvergütung zum Jahresende auf 100 % Beschäftigungsgrad hochgerechnet (keine gewährte Ist-Vergütung)', VB('U000195'), 30),
 'U000065': (122.0, 'Beschäftigte Deutschland (Tarif- und Gesamtbelegschaft ausgewählter Gesellschaften), Vollzeitäquivalente', VB('U000065'), 46),
 'U000538': (113.0, 'Belegschaft Siemens Healthineers Gruppe in Deutschland, Vollzeitäquivalente (GJ Okt 2024-Sep 2025)', VB('U000538'), 34),
 'U000133': (89.3, 'Beschäftigte Konzern: Personalaufwand lt. GuV je Vollzeitäquivalent (keine Ist-Vergütung der Belegschaft)', VB('U000133'), 21),
 'U000524': (99.6, 'Arbeitnehmervergleichsgruppe 2 = Belegschaft der Scout24 SE (ohne oberen Führungskreis), Ø-Gesamtvergütung', VB('U000524'), 34),
 'U000396': (106.5, 'Konzern weltweit: Ø Personalaufwand ohne Pensionsaufwand je Vollzeitbeschäftigtem (Ø 62.636 Beschäftigte), keine Ist-Vergütung Deutschland', VB('U000396'), 36),
 'U000331': (99.0, 'Belegschaft Knorr-Bremse Konzern in Deutschland, Vollzeitäquivalente (Zufluss), gerundet lt. Bericht', 'governance/dokumente/knorr-bremse-ag/geschaeftsbericht-2025.pdf', 305),
 'U000157': (93.114, 'Gesamtbelegschaft Deutschland (Lufthansa-Tarifkreis ohne CityLine), Vollzeitäquivalente, T220', 'governance/dokumente/deutsche-lufthansa-ag/geschaeftsbericht-2025.pdf', 386),
 'U000100': (129.0, 'Beschäftigte der Brenntag SE (Konzernzentrale, FTE; ohne Konzerngesellschaften), Tab. 4.23', VB('U000100'), 24),
 'U000233': (60.7, 'Alle Beschäftigten Fresenius Medical Care weltweit, FTE (Tab. 3.36)', 'governance/dokumente/fresenius-medical-care-ag/geschaeftsbericht-2025.pdf', 238),
 'U000280': (101.077, 'Belegschaft HENSOLDT AG und deutsche Tochtergesellschaften (Steuerbrutto auf VZÄ-Basis, ohne Azubis/Trainees)', VB('U000280'), 15),
 'U000349': (87.0, 'Gesamtbelegschaft der Krones AG (tarifliche und außertarifliche Beschäftigte), tatsächlich gezahltes Brutto plus Rückstellung variable Vergütung', VB('U000349'), 15),
 'U000071': (66.0, 'Arbeitnehmer der Bechtle-Konzernunternehmen in Deutschland, Personalaufwand je Vollzeitäquivalent, Vergleichstabelle', VB('U000071'), 22),
 'U000539': (74.0, 'Arbeitnehmer der Siltronic AG in Deutschland (Vollzeitäquivalent, inkl. variabler Bestandteile), Mehrjahresübersicht', GB('U000539'), 172),
 'U000177': (146.0, 'Arbeitnehmer des DWS-Konzerns weltweit, Vollzeitbasis, Vergleichstabelle (inkl. variabler Vergütung)', GB('U000177'), 263),
 'U000645': (108.0, 'Belegschaft Talanx Konzern in Deutschland (Personalaufwand ohne Vorstand je Arbeitnehmer), Vergleichstabelle', GB('U000645'), 46),
 'U000363': (82.0, 'Beschäftigte in Deutschland ohne Vorstand, Vollzeitäquivalente (inkl. oberer Führungsebene), Vergleichstabelle', VB('U000363'), 20),
 'U000165': (50.539, 'Gesamtbelegschaft DHL Group weltweit: Personalaufwand geteilt durch Beschäftigte (Ø-Gesamtvergütung lt. Bericht)', VB('U000165'), 37),
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
 'U000242': (85.2, 'CEO-Vergütung zur Ø-Vergütung aller Mitarbeitenden des GEA-Konzerns in Deutschland (lt. Vergütungsbericht, Geschäftsbericht S. 302)'),
 'U000491': (87.0, 'CEO pay ratio lt. Remuneration Report (Dutch Corporate Governance Code; Beträge in USD, Ø aller Beschäftigten weltweit 111 T USD)'),
 'U000233': (106.1, 'CEO pay ratio lt. Vergütungsbericht (Tab. 3.36, CEO im Amt zum Jahresende zu Ø aller Beschäftigten weltweit)'),
 'U000395': (135.0, 'ESRS: höchstbezahlte Einzelperson zu Median-Gesamtvergütung aller Beschäftigten (Geschäftsbericht S. 184)'),
}
# Rheinmetall weist Personalaufwand je FTE direkt aus (GB S. 56): 97 T€
B_DIREKT = {'U000502': (97.0, 'Personalaufwand je Beschäftigtem (Kapazität FTE), Konzern', GB('U000502'), 56)}

DOK_B = {}  # Quelle der Variante-B-Eingaben aus Handeingaben (sonst Geschäftsbericht im Repo)

# Geschlecht nur aus dokumentierten Angaben (nie aus Vornamen): person_id-Name, Unternehmen, Beleg, Seite
FRAUEN = [
 ('Helene von Roeder', 'U000396', VB('U000396'), 9, 'Bericht: "her move to the Executive Board of Merck KGaA"'),
 ('Inge Hofkens', 'U000053', GB('U000053'), 102, 'Bezeichnung "Vorständin"'),
 ('Dr. Stephanie Coßmann', 'U000640', VB('U000640'), 8, 'Bezeichnung "Arbeitsdirektorin"'),
 ('Dr. Astrid Fontaine', 'U000518', VB('U000518'), 26, 'Bezeichnung "Arbeitsdirektorin"'),
 ('Sybille Reiss', 'U000670', GB('U000670'), 220, 'Bericht: "Mrs Reiss" / "Ms Reiss"'),
 ('Marie-Anne Popp', 'U000143', GB('U000143'), 69, 'Bericht: "Finanzvorständin (CFO)"'),
 ('Kristin Skogen Lund', 'U000143', GB('U000143'), 69, 'Bericht: "Vorsitzende des Aufsichtsrats"'),
 ('Prof. Dr. Sabina Jeschke', 'U000052', GB('U000052'), 34, 'Bericht: "Frau Prof. Dr. Sabina Jeschke" (Aufsichtsrat, sechs Frauen)'),
 ('Dr. Petra Mayer', 'U000052', GB('U000052'), 34, 'Bericht: "Frau Dr. Petra Mayer" (Aufsichtsrat, sechs Frauen)'),
 ('Prof. Dr. Katja Windt', 'U000052', GB('U000052'), 34, 'Bericht: "Frau Prof. Dr. Katja Windt" (Aufsichtsrat, sechs Frauen)'),
 ('Christiane Benner', 'U000052', GB('U000052'), 34, 'Bericht: "Frau Christiane Benner" (Aufsichtsrat, sechs Frauen)'),
 ('Carmen Löffler', 'U000052', GB('U000052'), 34, 'Bericht: "Frau Carmen Löffler" (Aufsichtsrat, sechs Frauen)'),
 ('Clarissa Bader', 'U000052', GB('U000052'), 34, 'Bericht: "Frau Clarissa Bader" (Aufsichtsrat, sechs Frauen)'),
 ('Uta Anders', 'U000349', VB('U000349'), 13, 'Bericht: "CFO, Finanzvorständin"'),
 ('Ayten Barisik', 'U000238', VB('U000238'), 22, 'Bericht: "Frau Ayten Barisik"'),
 ('Cornelia Stahlschmidt', 'U000238', VB('U000238'), 22, 'Bericht: "Frau Cornelia Stahlschmidt"'),
 ('Karen Florschütz', 'U000028', GB('U000028'), 33, 'Bericht: "zwei von sechs Aufsichtsratsmitgliedern Frauen, nämlich Karen Florschütz und Prof. Dr. Anna Weber"'),
 ('Prof. Dr. Anna Weber', 'U000028', GB('U000028'), 33, 'Bericht: "zwei von sechs Aufsichtsratsmitgliedern Frauen, nämlich Karen Florschütz und Prof. Dr. Anna Weber"'),
 ('Frederique van Baarle', 'U000363', VB('U000363'), 15, 'Bericht: "Arbeitsdirektorin Frau Frederique van Baarle"'),
 ('Karin Rådström', 'U000133', VB('U000133'), 16, 'Bezeichnung "Vorstandsvorsitzende"'),
 ('Darleen Caron', 'U000538', VB('U000538'), 28, 'Bezeichnung "Personalvorständin"'),
 ('Britta Seeger', 'U000395', 'governance/dokumente/mercedes-benz-group-ag/geschaeftsbericht-2025.txt', 236, 'Bezeichnung "Arbeitsdirektorin"; "Zum 31. Dezember 2025 ist dies Britta Seeger" (Frau im Vorstand)'),
 ('Brona Magee', 'U000264', VB('U000264'), 18, 'Fußnote: "Eintritt von Frau Magee als Vorstandsmitglied"'),
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

# Handeingaben aus der Excel-Importvorlage (governance/vorlage/importieren.py --schreiben): gleiche Struktur, nur GJ 2025
import glob, json
PUB_Q = {'U000491': 'governance/dokumente/qiagen-n-v/verguetungsbericht-2025.pdf S. 15', 'U000233': 'governance/dokumente/fresenius-medical-care-ag/geschaeftsbericht-2025.pdf S. 238', 'U000242': 'governance/dokumente/gea-group-aktiengesellschaft/geschaeftsbericht-2025.pdf S. 302', 'U000395': 'governance/dokumente/mercedes-benz-group-ag/geschaeftsbericht-2025.txt S. 184'}
GESCHLECHT_SONST = []
for _f in sorted(glob.glob(f'{D}/handeingabe/*.json')):
    _d = json.load(open(_f, encoding='utf-8'))
    for g in _d.get('geschlecht', []):
        if g['geschlecht'] == 'weiblich':
            FRAUEN.append((g['name'], g['unternehmen_id'], g['quelle_dokument'], g['seite'], g['beleg']))
        else:
            GESCHLECHT_SONST.append(g)
    for r in _d.get('pay_ratio_eingang', []):
        if int(r['gj']) != 2025:
            continue
        u, q, sp = r['unternehmen_id'], r['quelle_dokument'], r['seite']
        if r['variante'] == 'A':
            A[u] = (r['durchschnittsverguetung_teur'], r['basis'], q, sp)
        elif r['variante'] == 'B':
            B[u] = (r['personalaufwand_mio'], int(r['beschaeftigte']), r['basis'], sp, sp)
            DOK_B[u] = q
        elif r['variante'] == 'Bericht':
            PUBLIZIERT[u] = (r['pay_ratio'], f"{r['bezug']}; {r['basis']}")
            PUB_Q[u] = f'{q} S. {sp}'
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
        nenner.append(('B', t, basis, [f'{DOK_B.get(u) or GB(u)} S. {s1} (Personalaufwand {pa:,} Mio. €)', f'{DOK_B.get(u) or GB(u)} S. {s2} (Beschäftigte {n:,})'.replace(',', '.')],
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
                     quellen=PUB_Q.get(u) or (GB(u) if u in ('U000073', 'U000151') else VB(u)), bemerkung='nur zum Abgleich, andere Definition'))

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
w('geschlecht_belege.csv', [dict(name=n, unternehmen_id=u, geschlecht='weiblich', quelle_dokument=q, seite=s, beleg=b) for n, u, q, s, b in FRAUEN]
  + [dict(name=g['name'], unternehmen_id=g['unternehmen_id'], geschlecht=g['geschlecht'], quelle_dokument=g['quelle_dokument'], seite=g['seite'], beleg=g['beleg']) for g in GESCHLECHT_SONST])
print(len(rows), 'Pay-Ratio-Zeilen;', len(gap), 'Gap-Zeilen')
