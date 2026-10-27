"""Erweiterung um alle deutschen Einträge im Pillar-3-Datenhub der EBA (Filter Country = Germany).

Liest die Hub-Exporte (Data Points Report, Export über die Weboberfläche) und schreibt
eba_hub_neu_2025.json: KM1, CC1, OV1 und die Bilanz aus EU CC2 (Spalte a) je Hub-Eintrag,
für neue Banken mit Gruppe/Institutsart und für bestehende Banken als Lückenfüllung.
"""
import csv, json, os, re, collections, datetime
import openpyxl

D = os.path.dirname(os.path.abspath(__file__)) + "/"

def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def load_csv(f):
    return [r for r in list(csv.reader(open(D + f)))[3:] if len(r) > 14]

def load_xlsx(f):
    ws = openpyxl.load_workbook(D + f).active
    return [list(r) for r in ws.iter_rows(min_row=4, values_only=True)]

def ref(v):
    return v.strftime("%Y-%m-%d") if isinstance(v, datetime.datetime) else "-".join(reversed(str(v).split("/")))

CC1 = {"instrumente": "0010", "gewinnruecklagen": "0050", "kum_ergebnis": "0060", "fonds_340g": "0070",
       "cet1_vor_abzuegen": "0110", "immaterielle": "0130", "dta": "0140", "abzuege_cet1": "0360", "cet1": "0370",
       "at1": "0540", "t1": "0550", "t2_instrumente": "0560", "kreditrisikoanpassungen": "0620", "t2": "0710",
       "eigenmittel": "0720", "rwa": "0730", "cet1_q": "0740", "t1_q": "0750", "tc_q": "0760"}
OV1 = {"kreditrisiko": "0010", "gegenparteirisiko": "0070", "cva": "0120", "verbriefung": "0210", "marktrisiko": "0260",
       "grosskredite": "0300", "oprisk": "0320", "floor_aufschlag": "0370", "gesamt": "0380", "output_floor_pct": "0350"}
KM1 = {"cet1": "0010", "t1": "0020", "tc": "0030", "rwa": "0040", "cet1_q": "0050", "t1_q": "0060", "tc_q": "0070",
       "gesamt_anf": "0190", "lr_exp": "0210", "lr": "0220", "lcr": "0320", "nsfr": "0350"}
PCT = {"cet1_q", "t1_q", "tc_q", "gesamt_anf", "lr", "lcr", "nsfr", "output_floor_pct"}

def build(rows, mapping, cc1=False):
    """{(lei, stichtag): {hub_name, werte}} für Spalte 0010 (bei CC1 nur Teil a)."""
    out = {}
    for r in rows:
        if r[2] != "Germany" or r[10] != "0010" or (cc1 and "K_66.01.b," in (r[5] or "")):
            continue
        out.setdefault((r[0], ref(r[13])), {"hub_name": r[1], "_raw": {}})["_raw"][r[8]] = num(r[14])
    res = {}
    for key, d in out.items():
        x = {"hub_name": d["hub_name"]}
        for k, row in mapping.items():
            v = d["_raw"].get(row)
            if v is not None:
                x[k] = round(v, 6) if k in PCT else round(v / 1e6, 1)
        res[key] = x
    return res

# ---------- EU CC2: Bilanz laut Abschluss (Spalte a) ----------
A_RULES = [("barreserve", r"barreserve|kassenbestand"), ("schuldtitel_oeff", r"schuldtitel"),
           ("ford_ki", r"forderungen an kreditinst"), ("ford_kunden", r"forderungen an kunden|baudarlehen"),
           ("ausgleich", r"ausgleichsforderung"),
           ("schuldverschr", r"schuldverschreibungen|anleihen"), ("aktien", r"aktien"), ("handel_a", r"handelsbestand"),
           ("beteiligungen", r"beteiligungen"), ("verb_unt", r"verbundenen unternehmen"), ("treuhand_a", r"treuhand"),
           ("leasing", r"leasing"), ("immat", r"immateriell"), ("sachanlagen", r"sachanlage"),
           ("ausst_einl", r"ausstehende einlage|eingefordert"), ("sonst_vg", r"sonstige verm"), ("rap_a", r"abgrenzung"),
           ("akt_lat", r"latente steuer"), ("aktiv_ub", r"unterschiedsbetrag"), ("fehlbetrag", r"fehlbetrag")]
P_RULES = [("verb_ki", r"verbindlichkeiten gegen.ber kreditinst"), ("verb_kunden", r"verbindlichkeiten gegen.ber kunden"),
           ("verbrieft", r"verbriefte"), ("handel_p", r"handelsbestand"), ("treuhand_p", r"treuhand"),
           ("sonst_verb", r"sonstige verbindlichkeit"), ("rap_p", r"abgrenzung"), ("pas_lat", r"latente steuer"),
           ("rueckst", r"r.ckstellung"), ("sonderposten", r"bauspartechnisch|sonderposten mit r.cklage"),
           ("nachrang", r"nachrang"), ("genuss", r"genussrecht"), ("at1", r"zus.tzlichen? (aufsichtsrechtlichen )?kernkapital|zus.tzlichen aufsichtsrechtlichen kapital"),
           ("fonds", r"fonds f.r allgemeine bank.{0,2}risiken|340g"),
           ("ek_total", r"^eigenkapital$"),
           ("gez", r"gezeichnetes kapital|eingefordertes kapital|gesch.ftsguthaben|grundkapital|stammkapital|kommanditkapital"),
           ("kaprl", r"kapitalr.cklage"), ("gewrl", r"g.?winnr.cklage|ergebnisr.cklage|sicherheitsr.cklage|andere r.cklagen|gesetzliche r.cklage|^r.cklagen"),
           ("bilgew", r"bilanzgewinn|bilanzverlust|gewinnvortrag")]
EQ = ("gez", "kaprl", "gewrl", "bilgew")

def classify(side, lbl):
    s = re.sub(r"\s+", " ", lbl).strip().lower()
    s = re.sub(r"^(aktiva|passiva)\s+", "", s)
    s = re.sub(r"^[ap]?\d+[a-z]*\.?(\d+\.?)?\s*[\.\-–)]*\s*", "", s)
    s = s.replace("gegenueber", "gegenüber").replace("rueck", "rück").replace("keitengegen", "keiten gegen")
    s = re.sub(r"(?<=[a-zäöüß])- ?(?=[a-zäöüß])", "", s).replace("kredit inst", "kreditinst").replace("werpapier", "wertpapier")
    davon = bool(re.match(r"^\.*\s*(davon|darunter)", s))
    s = re.sub(r"^\.*\s*(davon|darunter)\s*:?\s*", "", s)
    if "gestrichen" in s or "weggefallen" in s or re.match(r"^(gesamtaktiva|gesamtpassiva|summe|verbindlichkeiten insgesamt|total|eigenkapital (gesamt|insgesamt))", s):
        return None, davon
    for k, rx in (A_RULES if side == "assets" else P_RULES):
        if re.search(rx, s):
            return k, davon
    return "?", davon

LABEL = {"verb_kunden": "Verbindlichkeiten gegenüber Kunden", "verb_ki": "Verbindlichkeiten gegenüber Kreditinstituten",
         "schuldtitel_oeff": "Schuldtitel öffentlicher Stellen", "schuldverschr": "Schuldverschreibungen", "handel_a": "Handelsbestand (Aktiva)",
         "sachanlagen": "Sachanlagen", "rap_a": "Rechnungsabgrenzungsposten (Aktiva)", "akt_lat": "Aktive latente Steuern", "immat": "Immaterielle Anlagewerte",
         "aktiv_ub": "Aktiver Unterschiedsbetrag", "fonds": "Fonds für allgemeine Bankrisiken", "kaprl": "Kapitalrücklage", "aktien": "Aktien"}
lab = lambda k: LABEL.get(k, k)

def side_of(t):
    return "assets" if "assets" in t else ("equity" if "equity" in t else "liab")

def cc2_entities():
    E = collections.defaultdict(lambda: {"items": [], "blank": [], "name": None, "total": {}})
    for r in load_csv("eba_hub_cc2_20251231.csv"):
        if r[2] != "Germany":
            continue
        e = E[r[0]]; e["name"] = r[1]
        if r[8]:  # Summenzeilen Total assets / Total liabilities / Total shareholders' equity
            if r[10] == "0010":
                e["total"][r[9].strip()] = float(r[14]) / 1e6
            continue
        if r[10] == "0005" and not r[6]:
            e["blank"].append((side_of(r[11]), r[14]))
        elif r[10] == "0010" and r[6]:
            t, lbl = r[6].split("=", 1)
            e["items"].append((side_of(t), lbl.strip(), float(r[14]) / 1e6))
    return E

def cc2_bilanz(e, cc1_gewrl=None, lr_exp=None):
    """Hauptposten Formblatt 1 (Mio. €) aus EU CC2 Spalte a; Summenzeilen des Hubs als Kontrolle."""
    akt, pas, eq, unk, notes = {}, {}, {}, [], []
    a = [v for s, l, v in e["items"] if s == "assets"]
    p = [v for s, l, v in e["items"] if s != "assets"]
    asign = -1 if a and sum(a) < 0 else 1  # manche Institute melden Aktiva bzw. Passiva mit negativem Vorzeichen
    psign = -1 if p and sum(p) < 0 else 1
    fonds_im_ek = False
    for s, l, v in e["items"]:
        k, davon = classify("assets" if s == "assets" else "liab", l)
        if k is None:
            continue
        if k == "?":
            if not davon:
                unk.append(l)
            continue
        if s == "assets":
            if not davon:
                akt[k] = akt.get(k, 0) + v * asign
            continue
        v *= psign
        if k in EQ:
            eq[k] = eq.get(k, 0) + v
        elif k == "ek_total":
            if not davon:
                eq["total"] = eq.get("total", 0) + v
        elif not davon:
            pas[k] = pas.get(k, 0) + v
            if k == "fonds" and s == "equity":
                fonds_im_ek = True
    blank = []
    for s, l in e["blank"]:
        k, davon = classify("assets" if s == "assets" else "liab", l)
        if k in EQ or k == "ek_total":
            blank.append(("eq", k))
        elif k and k != "?" and not davon:
            blank.append((s if s == "assets" else "liab", k))
    t = e["total"]
    ta = abs(t["Total assets"]) if t.get("Total assets") else None
    te = abs(t["Total shareholders' equity"]) if t.get("Total shareholders' equity") else None
    # Einheit: einzelne Institute melden in Tausend €; Abgleich mit der Leverage-Gesamtrisikoposition (KM1)
    scale = 1
    ref_bs = ta or sum(akt.values())
    if lr_exp and ref_bs and 0.0003 < ref_bs / lr_exp < 0.003:
        scale = 1000; notes.append("Werte im Hub offenbar in Tausend € gemeldet, mit 1.000 multipliziert")
    akt = {k: v * scale for k, v in akt.items()}; pas = {k: v * scale for k, v in pas.items()}
    eq = {k: v * scale for k, v in eq.items()}
    ta = ta * scale if ta else None; te = te * scale if te else None
    if unk or not akt:
        # keine Bilanz nach Formblatt 1 (IFRS/Konzern, englische Positionen o. Ä.): nur Summenzeilen übernehmen
        ek = te if te is not None else eq.get("total")
        return dict(aktiva={}, passiva={}, bilanzsumme=round(ta, 3) if ta else None, bilanzsumme_aus_summenzeile=bool(ta),
                    eigenkapital=None if ek is None else round(ek, 3), fonds_340g=None, bilanzgewinn=None, hgb=False,
                    unbekannt=unk, differenz_aktiva_passiva=None, differenz_aktiva_bilanzsumme=None, residual=None,
                    notes=["keine Bilanz nach HGB-Formblatt (IFRS/Konzern o. Ä.); Bilanzsumme und Eigenkapital aus den Summenzeilen 'Total assets' und 'Total shareholders’ equity'"
                           if ta else "keine verwertbaren Bilanzwerte in CC2"],
                    vollstaendig=False, fuer_bilanzblatt=False)
    # Eigenkapital (Posten 12): Bestandteile, sonst Gesamtposten, sonst Summenzeile 'Total shareholders' equity'
    ek = None
    if "gewrl" not in eq and any(k == "gewrl" for _, k in blank) and cc1_gewrl is not None and "total" not in eq:
        eq["gewrl"] = cc1_gewrl
        notes.append("Gewinnrücklage im Hub-Export ohne Wert, aus CC1 Zeile 2 übernommen")
    if "gewrl" in eq:
        ek = sum(eq.get(k, 0) for k in EQ)
        if "bilgew" not in eq:
            notes.append("ohne Bilanzgewinn (in CC2 nicht ausgewiesen)")
    elif "total" in eq:
        ek = eq["total"]
    elif te is not None:
        ek = te - (pas.get("fonds", 0) if fonds_im_ek else 0)
        notes.append("Eigenkapital aus der Summenzeile 'Total shareholders’ equity'" + (" abzüglich Fonds § 340g" if fonds_im_ek else ""))
    if ek is not None:
        pas["ek"] = ek
    blank_a = [k for s, k in blank if s == "assets"]
    blank_p = [k for s, k in blank if s == "liab"]
    if ta and not blank_a and akt and abs(sum(akt.values()) - ta) > 0.02 * ta:
        notes.append(f"Summenzeile 'Total assets' im Hub ({ta:,.1f}) passt nicht zu den Aktivposten, Summe der Posten verwendet")
        ta = None
    bs = ta if ta else sum(akt.values())
    resid = None
    if not ta and blank_a == ["schuldtitel_oeff"] and blank_p:
        # Muster wie bei bekannten Banken (BBBank, GLS, Sparda West …): Schuldtitel dort jeweils 0
        akt["schuldtitel_oeff"] = 0.0; blank_a = []
        notes.append("Posten 'Schuldtitel öffentlicher Stellen' im Hub-Export ohne Wert, als 0 angenommen")
    if not blank_p and "verb_kunden" not in pas and bs - sum(pas.values()) > 0.05 * bs:
        blank_p = ["verb_kunden"]
    if ta and len(blank_a) == 1:
        resid = blank_a[0]; akt[resid] = round(ta - sum(akt.values()), 3)
        notes.append(f"Aktivposten '{lab(resid)}' im Hub-Export ohne Wert, als Differenz zur Bilanzsumme berechnet")
        blank_a = []
    elif ta and blank_a == [] and abs(ta - sum(akt.values())) > max(1.0, 0.0005 * ta):
        notes.append(f"Summe der Aktivposten weicht um {sum(akt.values()) - ta:,.1f} Mio. von der Bilanzsumme ab")
    if not blank_a and len(blank_p) == 1 and ek is not None:
        r_ = blank_p[0]; val = round(bs - sum(v for k, v in pas.items() if k != r_), 3)
        if val >= 0:
            pas[r_] = val
            notes.append(f"Passivposten '{lab(r_)}' im Hub-Export ohne Wert, als Differenz Bilanzsumme − übrige Passiva berechnet")
            resid = (resid + ", " if resid else "") + r_
    elif not ta and blank_a and not blank_p and ek is not None:
        r_ = blank_a[0]; akt[r_] = round(sum(pas.values()) - sum(akt.values()), 3); bs = sum(akt.values())
        notes.append(f"Aktivposten '{lab(r_)}' im Hub-Export ohne Wert, als Differenz Passiva − übrige Aktiva berechnet")
        resid = r_
    elif blank_a:
        notes.append("Aktivposten " + ", ".join(map(lab, blank_a)) + " im Hub-Export ohne Wert; Bilanzsumme ggf. zu niedrig")
    fonds = pas.get("fonds")
    if fonds is None:
        notes.append("kein Posten 'Fonds für allgemeine Bankrisiken' in CC2")
    diff_a = round(sum(akt.values()) - bs, 1)
    diff = round(sum(akt.values()) - sum(pas.values()), 1)
    hgb = not unk and bool(akt)
    return dict(aktiva={k: round(v, 3) for k, v in akt.items()}, passiva={k: round(v, 3) for k, v in pas.items()},
                bilanzsumme=round(bs, 3) if bs else None, bilanzsumme_aus_summenzeile=bool(ta),
                eigenkapital=None if ek is None else round(ek, 3),
                fonds_340g=None if fonds is None else round(fonds, 3), bilanzgewinn=eq.get("bilgew"),
                hgb=hgb, unbekannt=unk, differenz_aktiva_passiva=diff, differenz_aktiva_bilanzsumme=diff_a,
                residual=resid, notes=notes,
                vollstaendig=hgb and abs(diff) < max(1.0, 0.0005 * bs) and abs(diff_a) < max(1.0, 0.0005 * bs) and not blank_a,
                fuer_bilanzblatt=hgb and bool(bs) and not blank_a and abs(diff_a) < max(1.0, 0.0005 * bs) and abs(diff) < 0.01 * bs)

# ---------- Zuordnung der neuen Hub-Einträge ----------
# LEI -> (Anzeigename, Gruppe, Institutsart, Ebene)
S, G, L, P, F = "Sparkassen", "Genossenschaftsbanken", "Landesbanken", "Private Banken", "Förder- und Sonderinstitute"
NEU = {
    "529900DSIVJWCUQUMP41": ("AKA Ausfuhrkredit-Gesellschaft mbH", P, "Spezialinstitut (Exportfinanzierung, Bankenkonsortium)", "Einzelinstitut"),
    "529900EM0ZU25V87GD50": ("ALTE LEIPZIGER Bauspar AG", P, "Bausparkasse", "Einzelinstitut"),
    "5299000R7WZOVIFHLN21": ("BFS SozialFinanz AG (SozialBank)", G, "Spezialinstitut (AG, BVR-Mitglied)", "Einzelinstitut"),
    "7D9EHZL14BBPJWTN6S08": ("BHW Bausparkasse AG", P, "Bausparkasse", "Einzelinstitut"),
    "529900JZXXU699FCKK89": ("Bausparkasse Schwäbisch Hall AG", G, "Bausparkasse", "Einzelinstitut"),
    "6TJCK1B7E7UTXP528Y04": ("Citigroup Global Markets Europe AG", P, "EU-Tochter ausländischer Bankengruppe", "Einzelinstitut"),
    "529900FMPYJ0QVTBSD95": ("Debeka Bausparkasse AG", P, "Bausparkasse", "Einzelinstitut"),
    "39120001JPAYYPDRNN92": ("Deutsche Bausparkasse Badenia AG", P, "Bausparkasse", "Einzelinstitut"),
    "391200EEGLNXBBCVKC73": ("Erwerbsgesellschaft der S-Finanzgruppe mbH & Co. KG (Holding der DekaBank)", L, "Finanzholding", "Gruppe (Holding)"),
    "529900LXGM7KMLJE5H80": ("Erzgebirgssparkasse", S, "Sparkasse", "Einzelinstitut"),
    "549300ISU0OO19LLYT70": ("FIL Holdings (Germany) GmbH (Fidelity)", P, "Finanzholding (Fondsplattform)", "Gruppe (Holding)"),
    "549300BZZFFS0SOWR325": ("Ford Bank GmbH", P, "Autobank", "Einzelinstitut"),
    "8IBZUGJ7JPLH368JE346": ("Goldman Sachs Bank Europe SE", P, "EU-Tochter ausländischer Bankengruppe", "Einzelinstitut"),
    "549300ZK53CNGEEI6A29": ("J.P. Morgan SE", P, "EU-Tochter ausländischer Bankengruppe", "Einzelinstitut"),
    "5299006OWDQGU3FEDK86": ("Kasseler Sparkasse", S, "Sparkasse", "Einzelinstitut"),
    "5299002GPCR602QYJC04": ("KfW Beteiligungsholding GmbH", F, "Finanzholding (KfW-Gruppe)", "Gruppe (Holding)"),
    "529900Q1M1F4M8KMTM64": ("KfW IPEX-Bank GmbH", F, "Spezialinstitut (Export- und Projektfinanzierung, KfW-Gruppe)", "Einzelinstitut"),
    "529900FPOU897IEWGV26": ("Kreissparkasse Biberach", S, "Sparkasse", "Einzelinstitut"),
    "529900CDFH7GJ76LXH43": ("Kreissparkasse Halle-Wiedenbrück", S, "Sparkasse", "Einzelinstitut"),
    "52990008SP9ETV9I7047": ("Kreissparkasse Ostalb", S, "Sparkasse", "Einzelinstitut"),
    "5299002GZMVW234JRW43": ("Kreissparkasse Ravensburg", S, "Sparkasse", "Einzelinstitut"),
    "529900WZ5UJMQE5EXE26": ("Kreissparkasse Reutlingen", S, "Sparkasse", "Einzelinstitut"),
    "5299001SSGO8MMQN8E03": ("Kreissparkasse Steinfurt", S, "Sparkasse", "Einzelinstitut"),
    "529900VZSHKAB0ZU6Z09": ("Kreissparkasse Tübingen", S, "Sparkasse", "Einzelinstitut"),
    "5299004SI3IL8FGDV034": ("LBS Landesbausparkasse NordOst AG", S, "Bausparkasse (Sparkassen-Finanzgruppe)", "Einzelinstitut"),
    "529900HC4LDSGK0NCJ85": ("LBS Landesbausparkasse NordWest", S, "Bausparkasse (Sparkassen-Finanzgruppe)", "Einzelinstitut"),
    "529900FU4WJ2XT7BVE31": ("LBS Landesbausparkasse Süd", S, "Bausparkasse (Sparkassen-Finanzgruppe)", "Einzelinstitut"),
    "54930056FHWP7GIWYY08": ("Morgan Stanley Europe SE", P, "EU-Tochter ausländischer Bankengruppe", "Einzelinstitut"),
    "529900AT73S3UKIMP047": ("OstseeSparkasse Rostock", S, "Sparkasse", "Einzelinstitut"),
    "529900KNPI1D0Y1DGK92": ("PSD Bank München eG", G, "Kreditgenossenschaft", "Einzelinstitut"),
    "529900LIN8L1K9MLTR09": ("ProCredit Holding AG", P, "Finanzholding (Bankengruppe mit Töchtern in Südosteuropa)", "Gruppe (Holding)"),
    "5299007CKOPKK8KX5129": ("Rheinhessen Sparkasse", S, "Sparkasse", "Einzelinstitut"),
    "529900YI7GR9R4L1UI63": ("SECB Swiss Euro Clearing Bank GmbH", P, "Spezialinstitut (Zahlungsverkehr)", "Einzelinstitut"),
    "5299008I9KIOJRP9OZ42": ("Sparda-Bank Nürnberg eG", G, "Kreditgenossenschaft", "Einzelinstitut"),
    "529900R5ERJA9VIZHJ29": ("Sparkasse Hanau", S, "Sparkasse", "Einzelinstitut"),
    "5299008PIM61AXE4C673": ("Sparkasse Allgäu", S, "Sparkasse", "Einzelinstitut"),
    "529900LUBMIN39VO2E71": ("Sparkasse Ansbach", S, "Sparkasse", "Einzelinstitut"),
    "529900BR2N56KWNZOM37": ("Sparkasse Aschaffenburg Miltenberg", S, "Sparkasse", "Einzelinstitut"),
    "529900D0GBT27T9NB551": ("Sparkasse Bielefeld", S, "Sparkasse", "Einzelinstitut"),
    "5299002GDXM6JRUY4311": ("Sparkasse Celle-Gifhorn-Wolfsburg", S, "Sparkasse", "Einzelinstitut"),
    "529900X1RCYC7HPDGT34": ("Sparkasse Chemnitz", S, "Sparkasse", "Einzelinstitut"),
    "529900C2A9G3SP7VPK94": ("Sparkasse Duisburg", S, "Sparkasse", "Einzelinstitut"),
    "529900BXR8FHQ0546E89": ("Sparkasse Düren", S, "Sparkasse", "Einzelinstitut"),
    "529900XQUKY370MSCE53": ("Sparkasse Hellweg-Lippe", S, "Sparkasse", "Einzelinstitut"),
    "5299005GLFOIV7898E14": ("Sparkasse Ingolstadt Eichstätt", S, "Sparkasse", "Einzelinstitut"),
    "529900YHNJHJ6HCOV883": ("Sparkasse Koblenz", S, "Sparkasse", "Einzelinstitut"),
    "529900GS01MWP4QSH807": ("Sparkasse Landshut", S, "Sparkasse", "Einzelinstitut"),
    "529900VJ7CMGXPGH3278": ("Sparkasse Mittelfranken-Süd", S, "Sparkasse", "Einzelinstitut"),
    "529900M7DRA4N1J81L72": ("Sparkasse Mittelthüringen", S, "Sparkasse", "Einzelinstitut"),
    "529900OC0J2AGDDP1J56": ("Sparkasse Niederbayern-Mitte", S, "Sparkasse", "Einzelinstitut"),
    "529900JFTHKPTK4YNL22": ("Sparkasse Offenburg/Ortenau", S, "Sparkasse", "Einzelinstitut"),
    "5299007M83GBOCBBUP36": ("Sparkasse Regensburg", S, "Sparkasse", "Einzelinstitut"),
    "5299003MY56ID5EB4A55": ("Sparkasse Rhein Neckar Nord", S, "Sparkasse", "Einzelinstitut"),
    "529900UZ4WGK38RQ1M84": ("Sparkasse Rhein-Nahe", S, "Sparkasse", "Einzelinstitut"),
    "529900Q34WY4SPLWUU02": ("Sparkasse Rosenheim-Bad Aibling", S, "Sparkasse", "Einzelinstitut"),
    "5299002GPM9IXQLHUC77": ("Sparkasse Saarbrücken", S, "Sparkasse", "Einzelinstitut"),
    "52990078RM4B6ZUC6648": ("Sparkasse Südholstein", S, "Sparkasse", "Einzelinstitut"),
    "529900U59PV6VXIQ9K43": ("Sparkasse Südpfalz", S, "Sparkasse", "Einzelinstitut"),
    "5299002ER8OE93VD2R07": ("Sparkasse Trier", S, "Sparkasse", "Einzelinstitut"),
    "52990086IBNN51AGC442": ("Sparkasse Ulm", S, "Sparkasse", "Einzelinstitut"),
    "529900FR6NK5ZQR5EP29": ("Sparkasse Vest Recklinghausen", S, "Sparkasse", "Einzelinstitut"),
    "529900B6FH6DMERJCI37": ("Sparkasse Vorpommern", S, "Sparkasse", "Einzelinstitut"),
    "529900D06C9IHN6BR131": ("Sparkasse im Kreis Herford", S, "Sparkasse", "Einzelinstitut"),
    "529900UELOQV2KQ0VP31": ("Stadt- und Kreis-Sparkasse Darmstadt", S, "Sparkasse", "Einzelinstitut"),
    "529900YFF1OOLDFE8X31": ("Stadt- und Kreissparkasse Erlangen Höchstadt Herzogenaurach", S, "Sparkasse", "Einzelinstitut"),
    "549300WDT1HWUMTUW770": ("Standard Chartered Bank AG", P, "EU-Tochter ausländischer Bankengruppe", "Einzelinstitut"),
    "529900CLVK38HUKPKF71": ("Süd-West-Kreditbank Finanzierung GmbH (SWK Bank)", P, "Konsumentenkreditbank", "Einzelinstitut"),
    "52990055VN3I202R2809": ("Taunus-Sparkasse", S, "Sparkasse", "Einzelinstitut"),
    "5299007QVIQ7IO64NX37": ("UBS Europe SE", P, "EU-Tochter ausländischer Bankengruppe", "Einzelinstitut"),
    "529900JRKG8AEYL65326": ("VR Bank Heilbronn Schwäbisch Hall eG", G, "Kreditgenossenschaft", "Einzelinstitut"),
    "52990089LBIKLBM8YB23": ("VR Bank Nord eG", G, "Kreditgenossenschaft", "Einzelinstitut"),
    "529900E0WY09Z3H21393": ("VR Bank Rhein-Neckar eG", G, "Kreditgenossenschaft", "Einzelinstitut"),
    "529900JXM2IQSPJHMK02": ("VR Bank Starnberg-Zugspitze eG", G, "Kreditgenossenschaft", "Einzelinstitut"),
    "529900ZMDTSQYEYCKL45": ("VR TeilhaberBank Metropolregion Nürnberg eG", G, "Kreditgenossenschaft", "Einzelinstitut"),
    "529900BIK4WRWS06MR52": ("Varengold Bank AG", P, "Spezialinstitut (Handelsfinanzierung)", "Einzelinstitut"),
    "5299008F7LLV7TEYIT04": ("Volksbank Düsseldorf Neuss eG", G, "Kreditgenossenschaft", "Einzelinstitut"),
    "529900SSGT49ZZSWYE62": ("Volkswagen Financial Services AG", P, "Finanzdienstleistungsgruppe (Leasing, Autobank-Schwester)", "Gruppe (Holding)"),
    "529900S1KHKOEQL5CK20": ("Wüstenrot Bausparkasse AG", P, "Bausparkasse", "Einzelinstitut"),
    "5299009IFX1XTKDY4568": ("Trade Republic Bank GmbH", P, "Neobank/Wertpapierhandelsbank", "Einzelinstitut"),
}
# Hub-Einträge, die zu bereits erfassten Banken gehören, bisher aber nicht zugeordnet waren
BESTEHEND = {
    "GTQYZJON3I7SXRNJTT73": "Landesbank Berlin AG (seit 15.07.2025 BSK 1818 AG; Trägerin der Berliner Sparkasse)",
    "EZKODONU5TYHW4PP1R34": "Aareal Bank AG",
    "529900UY9ICRQLT2PN79": "Siemens Bank GmbH",
}
# nur zur Lückenfüllung (Übersicht/Bilanzen) aus CC2, KM1/CC1/OV1 sind dort schon zugeordnet
HUB_TO_BANK_EXTRA = {"529900F5KTT6ZUPA8N40": "Hamburger Sparkasse AG (Haspa)"}

if __name__ == "__main__":
    km1 = build(load_xlsx("eba_hub_km1_de_alle_stichtage.xlsx"), KM1)
    cc1 = build(load_csv("eba_hub_cc1_20251231.csv"), CC1, cc1=True)
    ov1 = build(load_csv("eba_hub_ov1_20251231.csv"), OV1)
    E = cc2_entities()
    # bisherige Zuordnung Hub-Name -> Bank aus den vorhandenen Rohdaten
    old = json.load(open(D + "eba_cc1_ov1_2025.json"))
    hub2bank = {}
    for t in ("cc1", "ov1"):
        for k, v in old[t].items():
            hub2bank[v["hub_name"]] = k
    for i in json.load(open(D + "offenlegung_2025.json"))["items"]:
        m = re.search(r"EBA-Hub-Eintrag: (.*)", i.get("hinweis") or "")
        if m:
            hub2bank[m.group(1).strip()] = i["name"]
    leis = {k[0] for k in km1} | {k[0] for k in cc1} | {k[0] for k in ov1} | set(E)
    names = {}
    for src in (km1, cc1, ov1):
        for (lei, _), v in src.items():
            names.setdefault(lei, v["hub_name"])
    for lei, e in E.items():
        names.setdefault(lei, e["name"])
    out = {"stand": "2026-10-27", "einheit": "Mio. € (Quoten als Anteil)",
           "quelle": "EBA Pillar-3-Datenhub, Data Points Report, Filter Country = Germany, Export über die Weboberfläche am 26./27.10.2026",
           "neu": [], "bestehend": [], "nicht_zugeordnet": []}
    for lei in sorted(leis, key=lambda x: names[x]):
        hn = names[lei]
        alln = {v["hub_name"] for src in (km1, cc1, ov1) for (l, _), v in src.items() if l == lei}
        bank = next((hub2bank[x] for x in alln if x in hub2bank), None) or BESTEHEND.get(lei) or HUB_TO_BANK_EXTRA.get(lei)
        if lei not in NEU and not bank:
            out["nicht_zugeordnet"].append({"lei": lei, "hub_name": hn}); continue
        dates = sorted({d for (l, d) in km1 if l == lei})
        st = "2025-12-31" if "2025-12-31" in dates else (dates[-1] if dates else None)
        k = dict(km1.get((lei, st), {}))
        c = cc1.get((lei, "2025-12-31"))
        o = ov1.get((lei, "2025-12-31"))
        c = c if c and len(c) > 1 else None  # Einträge ohne Werte (nur Name) verwerfen
        o = o if o and len(o) > 1 else None
        km1_note = None
        if k and k.get("cet1") is None and c and c.get("cet1") is not None:
            k = {}  # KM1-Eintrag ohne Werte
        if not k and c and c.get("cet1") is not None:
            k = {"hub_name": hn, **{f: c.get(f) for f in ("cet1", "t1", "rwa", "cet1_q", "t1_q", "tc_q")}, "tc": c.get("eigenmittel")}
            st = "2025-12-31"; km1_note = "kein KM1 im Hub; Werte aus CC1 (Zeilen 29, 45, 59, 60–63)"
        elif k and st != "2025-12-31":
            km1_note = f"kein KM1 zum 31.12.2025 im Hub; Stichtag {st[8:10]}.{st[5:7]}.{st[:4]}"
        b = cc2_bilanz(E[lei], c.get("gewinnruecklagen") if c else None, (k or {}).get("lr_exp")) if lei in E else None
        rec = {"lei": lei, "hub_name": hn, "km1": k or None, "km1_stichtag": st if k else None, "km1_hinweis": km1_note,
               "cc1": c, "ov1": o, "cc2": b, "km1_stichtage_im_hub": dates}
        if lei in NEU:
            n, g, art, eb = NEU[lei]
            rec.update(name=n, gruppe=g, art=art, ebene=eb)
            out["neu"].append(rec)
        else:
            rec.update(name=bank)
            out["bestehend"].append(rec)
    json.dump(out, open(D + "eba_hub_neu_2025.json", "w"), indent=1, ensure_ascii=False)
    print("neu", len(out["neu"]), "bestehend", len(out["bestehend"]), "nicht zugeordnet", out["nicht_zugeordnet"])
    for r in out["neu"]:
        b = r["cc2"] or {}
        print(f"{r['name'][:45]:45} {r['gruppe'][:5]} km1={'j' if r['km1'] else '-'} cc1={'j' if r['cc1'] else '-'} ov1={'j' if r['ov1'] else '-'} "
              f"bs={b.get('bilanzsumme')} ek={b.get('eigenkapital')} fo={b.get('fonds_340g')} hgb={b.get('hgb')} voll={b.get('vollstaendig')} diff={b.get('differenz_aktiva_passiva')}/{b.get('differenz_aktiva_bilanzsumme')} {b.get('notes')}")
