"""Gemeinsame Helfer der Governance-Erhebung. Seitenangaben = PDF-Seite."""
import csv, re, os, sys, unicodedata
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'stammdaten'))
import ids  # zentrale Unternehmens-IDs (stammdaten/)
OUT = os.path.join(os.path.dirname(__file__), '..')
TRANSLIT = str.maketrans({'ø': 'o', 'Ø': 'O', 'æ': 'ae', 'Æ': 'Ae', 'œ': 'oe', 'Œ': 'Oe', 'ß': 'ss', 'ł': 'l', 'Ł': 'L', 'đ': 'd', 'Đ': 'D', 'ð': 'd', 'þ': 'th'})
def slug(n):
    n = re.sub(r'\b(Prof\.|Dr\.|Professor|Dipl\.-\w+\.?|h\.c\.|Ing\.)\s*', '', n)
    n = n.translate(TRANSLIT)       # Buchstaben, die NFKD nicht zerlegt (Bjørn -> bjorn statt bjrn)
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', n).strip('-')

# bekannte IDs aus dem Universum (Mandate in Unternehmen, die selbst im Repo stehen)
UNI = {'Münchener Rückversicherungs-Gesellschaft AG': 'U000420',
       'JENOPTIK AG': 'U000317', 'TUI AG': 'U000670', 'Rheinmetall AG': 'U000502',
       'Siemens Energy AG': 'U000537', 'Bayer AG': 'U000065', 'Traton SE': 'U000668',
       'Knorr Bremse AG': 'U000331', 'Commerz Real AG': '', 'Bertelsmann SE & Co.KGaA': ''}

mitglieder, mandate, werdegang, verg, kenn = [], [], [], [], []

def M(src, organ, name, funktion='Mitglied', vertreter='', seit='', bis='', seite='', beruf='', bemerkung=''):
    mitglieder.append(dict(unternehmen_id=src[1], gj=2025, organ=organ, person_id=slug(name), name=name, funktion=funktion,
        vertreter_art=vertreter, seit=seit, bis=bis, beruf_laut_dokument=beruf, quelle_dokument=src[0], seite=seite, bemerkung=bemerkung))

def X(src, name, typ, ges, sitz='', funktion='', gueltig='', seite='', bem=''):
    mandate.append(dict(person_id=slug(name), name=name, typ=typ, gesellschaft=ges, gesellschaft_unternehmen_id=UNI.get(ges, ''),
        sitz=sitz, funktion=funktion, gueltig=gueltig, ueber_unternehmen_id=src[1], gj=2025, quelle_dokument=src[0], seite=seite, bemerkung=bem))

def K(src, feld, wert, einheit='', seite='', bem='', gj=2025):
    kenn.append(dict(unternehmen_id=src[1], gj=gj, feld=feld, wert=wert, einheit=einheit, quelle_dokument=src[0], seite=seite, bemerkung=bem))


def V(src, gremium, name, betrag, art, seite, bem='', gj=2025):
    verg.append(dict(unternehmen_id=src[1], gj=gj, gremium=gremium, person_id=slug(name) if not name.startswith(('Gesamt', 'Barwert', 'Zahlungen')) else '',
        name=name, betrag_tsd_eur=betrag, art=art, quelle_dokument=src[0], seite=seite, bemerkung=bem))

def W(src, name, station, organisation='', zeitraum='', art='', seite=''):
    werdegang.append(dict(person_id=slug(name), name=name, station=station, organisation=organisation, zeitraum=zeitraum, art=art, quelle_dokument=src[0], seite=seite))


_ORIG = [
    (re.compile(r'Originalbetrag:?\s*(GBP|USD|EUR|CHF)\s*([\d.,]+)\s*\((Tausend|Einheiten)'), None),
    (re.compile(r'[Oo]riginal(?:betrag)?:?\s*(USD|GBP|CHF)\s*([\d.,]+)'), 'voll'),
    (re.compile(r'[Oo]riginal(?:betrag)?:?\s*([\d.,]+)\s*(USD|GBP|CHF)'), 'voll_nw'),
    (re.compile(r'^([\d.,]+)\s*T£'), 'T£'),
    (re.compile(r'([\d.,]+)\s*T USD'), 'T$'),
]
def _num(x):
    x = x.rstrip('.,').replace(',', '')
    try: return float(x)
    except ValueError: return None

def original_aus_text(bem):
    """(Betrag in Tausend der Originalwährung, Währung) aus der Bemerkung; leer, wenn nicht erkennbar. Keine Umrechnung."""
    for rx, mode in _ORIG:
        m = rx.search(bem or '')
        if not m: continue
        if mode is None: v, w, einh = _num(m.group(2)), m.group(1), m.group(3)
        elif mode == 'voll': v, w, einh = _num(m.group(2)), m.group(1), 'Einheiten'
        elif mode == 'voll_nw': v, w, einh = _num(m.group(1)), m.group(2), 'Einheiten'
        elif mode == 'T£': v, w, einh = _num(m.group(1)), 'GBP', 'Tausend'
        else: v, w, einh = _num(m.group(1)), 'USD', 'Tausend'
        if v is None: continue
        return (round(v / 1000 if einh == 'Einheiten' else v, 3), w)
    return ('', '')

def uni(name, uid): UNI[name] = uid

def w(name, rows, cols):
    with open(os.path.join(OUT, name), 'w', newline='', encoding='utf-8-sig') as f:
        wr = csv.DictWriter(f, fieldnames=cols); wr.writeheader()
        for r in rows: wr.writerow({c: r.get(c, '') for c in cols})

def lade_handeingabe():
    """Zeilen aus governance/handeingabe/*.json (Import der Excel-Vorlage, governance/vorlage/importieren.py) übernehmen."""
    import json, glob
    for f in sorted(glob.glob(os.path.join(OUT, 'handeingabe', '*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        mitglieder.extend(d.get('mitglieder', [])); mandate.extend(d.get('mandate', []))
        werdegang.extend(d.get('werdegang', [])); verg.extend(d.get('verguetung', [])); kenn.extend(d.get('kennzahlen', []))

def write_all():
    lade_handeingabe()
    reg = ids.lade(neu=True)
    unbekannt = set()
    for rows in (mitglieder, mandate, verg, kenn):
        for r in rows:
            for c in ('unternehmen_id', 'gesellschaft_unternehmen_id', 'ueber_unternehmen_id'):
                v = r.get(c)
                if v and v not in reg.unternehmen:       # alte Schreibweise (Slug) oder Name -> zentrale ID
                    r[c] = reg.aufloesen(v) or v
                    if r[c] not in reg.unternehmen: unbekannt.add(v)
    if unbekannt: raise SystemExit('Keine Unternehmens-ID in stammdaten/ für: %s' % sorted(unbekannt))
    pers = {}
    for r in mitglieder + [dict(person_id=m['person_id'], name=m['name']) for m in mandate]:
        pers.setdefault(r['person_id'], r['name'])
    w('personen.csv', [dict(person_id=k, name=v) for k, v in sorted(pers.items())], ['person_id', 'name'])
    w('gremien_mitglieder.csv', mitglieder, ['unternehmen_id','gj','organ','person_id','name','funktion','vertreter_art','seit','bis','beruf_laut_dokument','quelle_dokument','seite','bemerkung'])
    w('mandate_extern.csv', mandate, ['person_id','name','typ','gesellschaft','gesellschaft_unternehmen_id','sitz','funktion','gueltig','ueber_unternehmen_id','gj','quelle_dokument','seite','bemerkung'])
    w('werdegang.csv', werdegang, ['person_id','name','station','organisation','zeitraum','art','quelle_dokument','seite'])
    for r in verg:   # Fremdwährung: Originalbetrag (Tausend) und Währung aus dem Bemerkungstext, keine Umrechnung
        if not r.get('betrag_tsd_eur') and not r.get('betrag_original_tsd'):
            r['betrag_original_tsd'], r['waehrung'] = original_aus_text(r.get('bemerkung', ''))
        r.setdefault('betrag_original_tsd', ''); r.setdefault('waehrung', '')
    w('verguetung.csv', verg, ['unternehmen_id','gj','gremium','person_id','name','betrag_tsd_eur','betrag_original_tsd','waehrung','art','quelle_dokument','seite','bemerkung'])
    w('kennzahlen_gremien.csv', kenn, ['unternehmen_id','gj','feld','wert','einheit','quelle_dokument','seite','bemerkung'])
    print({k: len(v) for k, v in dict(personen=pers, mitglieder=mitglieder, mandate=mandate, werdegang=werdegang, verguetung=verg, kennzahlen=kenn).items()})
