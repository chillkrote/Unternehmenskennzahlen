import json, os, statistics
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

D = os.path.dirname(os.path.abspath(__file__)) + "/"
if os.path.isdir(D + "data"):
    D += "data/"
# im Repo liegt das Skript unter rohdaten/skripte/, die JSONs eine Ebene höher; Ausgabe dann nach auswertung/
IM_REPO = not os.path.exists(D + "private.json") and os.path.exists(D + "../private.json")
if IM_REPO:
    D = os.path.normpath(D + "..") + "/"
OUT = os.environ.get("OUT", D + "../auswertung/Bilanzvergleich_Banken_GJ2025.xlsx" if IM_REPO
                     else "/mnt/project-files/bilanzvergleich/Bilanzvergleich_Banken_GJ2025.xlsx")

def load(f):
    p = D + f
    return json.load(open(p)) if os.path.exists(p) else None

groups = [("Private Banken", load("private.json")),
          ("Genossenschaftsbanken", load("volksbanken.json")),
          ("Sparkassen", load("sparkassen.json")),
          ("Landesbanken", load("landesbanken.json"))]

gap_items = []
for f in ("gaps.json", "gaps_spk.json", "gaps_spk2a.json", "gaps_spk2b.json", "gaps_vb2.json", "gaps_priv2.json", "gaps_euler.json", "gaps_web.json", "gaps_k2.json"):
    g = load(f)
    if g:
        gap_items += [i for i in g["items"] if not (f == "gaps.json" and "TARGO" in i["name"].upper())]

FIELDS = ["bilanzsumme", "eigenkapital", "davon_at1", "fonds_340g", "davon_340e",
          "vj_bilanzsumme", "vj_eigenkapital", "vj_fonds_340g"]

def norm(s):
    return "".join(c for c in s.lower() if c.isalnum())

def key_of(name):
    n = norm(name)
    if "deutschekreditbank" in n or "dkb" in n:
        return "dkb"
    for k in ["bayernlb", "saarlb", "dekabank", "dkb", "helaba", "bsk1818", "dzbank", "frankfurtervolksbank",
              "aareal", "santander", "targobank", "hamburgcommercial", "traderepublic", "sparkassehannover",
              "frankfurtersparkasse", "pforzheim", "mittelbrandenburg", "kreissparkasseköln", "sparkassekölnbonn",
              "stadtsparkassemünchen", "hamburgersparkasse", "nassauische"]:
        if k in n:
            return k
    if "landesbankberlin" in n:
        return "bsk1818"
    if "hessenthüringen" in n:
        return "helaba"
    if "bayerische" in n and "landesbank" in n:
        return "bayernlb"
    return n

gaps = {}
for i in gap_items:
    k = key_of(i["name"])
    if k in gaps:  # mehrere Nacherhebungen: Felder zusammenführen, spätere Datei ergänzt
        old = gaps[k]
        for f in FIELDS:
            if i.get(f) is not None and (old.get(f) is None or i.get("_force") or (i.get("fiscal_year") or 0) > (old.get("fiscal_year") or 0)):
                old[f] = i[f]
        for fl in ("_force", "_full"):
            old[fl] = old.get(fl) or i.get(fl)
        old["notes"] = (old.get("notes") or "") + " | " + (i.get("notes") or "")
        if i.get("source_url") and (i.get("_full") or not old.get("_full")) and (i.get("fiscal_year") or 0) >= (old.get("fiscal_year") or 0):
            old["source_url"], old["source_doc"], old["source_type"] = i.get("source_url"), i.get("source_doc"), i.get("source_type")
        old["fiscal_year"] = max(old.get("fiscal_year") or 0, i.get("fiscal_year") or 0) or None
    else:
        gaps[k] = dict(i)

def find_gap(name):
    k = key_of(name)
    if k in gaps:
        return gaps[k]
    for gk, g in gaps.items():
        if len(gk) > 8 and (k.startswith(gk) or gk.startswith(k)):
            return g
    return None

def merge(b):
    g = find_gap(b["name"])
    if not g:
        return b
    if (g.get("fiscal_year") or 0) > (b.get("fiscal_year") or 0) and g.get("bilanzsumme") is not None:
        # neueres Geschäftsjahr gefunden: alle Werte ersetzen
        for f in FIELDS:
            b[f] = g.get(f)
        b["fiscal_year"] = g["fiscal_year"]
        b["source_url"], b["source_doc"], b["source_type"] = g.get("source_url"), g.get("source_doc"), g.get("source_type")
        b["notes"] = ((b.get("notes") or "") + " | Nacherhebung (neueres GJ): " + (g.get("notes") or "")).strip(" |")
        return b
    if g.get("_force"):
        # Nacherhebung aus der formalen HGB-Bilanz: belegte Werte ersetzen ältere/schwächere Angaben
        changed = [f for f in FIELDS if g.get(f) is not None and g.get(f) != b.get(f)]
        for f in changed:
            b[f] = g[f]
        if g.get("_full"):
            b["fiscal_year"] = g.get("fiscal_year") or b.get("fiscal_year")
            b["source_url"], b["source_doc"], b["source_type"] = g.get("source_url"), g.get("source_doc"), g.get("source_type")
        if changed:
            extra = f"Nacherhebung 24.10.2026 ({', '.join(changed)}): {g.get('source_doc') or ''} – {g.get('source_url') or ''}. {g.get('notes') or ''}"
            b["notes"] = ((b.get("notes") or "") + " | " + extra).strip(" |")
            b["_nach"] = True
        return b
    weak = (b.get("source_type") or "").startswith(("Rangliste", "Sekundär"))
    changed = [f for f in FIELDS if g.get(f) is not None and (b.get(f) is None or (weak and g.get(f) != b.get(f)))]
    if weak and "bilanzsumme" in changed and g.get("source_type"):
        b["source_type"] = g["source_type"]
    for f in changed:
        b[f] = g[f]
    if changed:
        extra = f"Nacherhebung ({', '.join(changed)}): {g.get('source_doc') or ''} – {g.get('source_url') or ''} [{g.get('source_type') or ''}]. {g.get('notes') or ''}"
        b["notes"] = ((b.get("notes") or "") + " | " + extra).strip(" |")
        if all(b.get(f) is None for f in ("bilanzsumme",)) or not b.get("source_url"):
            b["source_url"] = g.get("source_url")
        b["_nach"] = True
    elif g.get("notes"):
        b["notes"] = ((b.get("notes") or "") + " | Nacherhebung: " + g["notes"]).strip(" |")
    return b

OVR = {"bsk1818": "Lagebericht/Halbjahresbericht HGB",
       "kreissparkasseköln": "Lagebericht HGB (VJ-Fonds abgeleitet)",
       "dzbank": "Lagebericht HGB (Bilanzsumme gerundet)",
       "santander": "Lagebericht/Kennzahlen HGB",
       "saarlb": "Lagebericht HGB",
       }

# Posten für die CET1-/Kernkapital-Näherung (aus der HGB-Bilanz abgelesen, Mio. €)
KK = {norm(i["name"]): i for i in (load("kernkapital_posten.json") or {"items": []})["items"]}
KKF = ["at1_posten", "nachrang", "genussrechte", "bilanzgewinn", "immaterielle", "akt_lat_steuern"]

def kk_calc(b):
    """CET1- und Kernkapital-Näherung in Mio. €; None, wenn ein Baustein fehlt."""
    k = KK.get(norm(b["name"]))
    ek, fo = mio(b.get("eigenkapital")), mio(b.get("fonds_340g"))
    if not k or ek is None or fo is None or any(k.get(f) is None for f in ("bilanzgewinn", "immaterielle", "akt_lat_steuern")):
        return None, None
    stille = mio(b.get("davon_at1")) or 0
    cet1 = ek - stille + fo - max(k["bilanzgewinn"], 0) - k["immaterielle"] - k["akt_lat_steuern"]
    t1 = cet1 + stille + k["at1_posten"] if k.get("at1_posten") is not None else None
    return round(cet1, 3), (round(t1, 3) if t1 is not None else None)

rows = []  # (group, rolle, bank)
for gname, d in groups:
    if not d:
        continue
    for b in d["banks"]:
        b = merge(b); b["source_type"] = OVR.get(key_of(b["name"]), b.get("source_type"))
        rows.append((gname, "Top 40" if gname != "Landesbanken" else "Landesbank", b))
    for b in d.get("reference", []):
        b = merge(b); b["source_type"] = OVR.get(key_of(b["name"]), b.get("source_type"))
        rows.append((gname, "Zusatz", b))
EXT = {"Private Banken": ["private_11_40.json"],
       "Genossenschaftsbanken": ["vb_11_25.json", "vb_26_40.json"],
       "Sparkassen": ["spk_11_25.json", "spk_26_40.json"]}
ext_excluded = []
for gname, files in EXT.items():
    for f in files:
        d = load(f)
        if not d:
            continue
        ext_excluded += [(gname, e) for e in d.get("excluded", [])]
        for b in d["banks"]:
            k = key_of(b["name"])
            if any(g == gname and key_of(x["name"]) == k for g, _, x in rows if _ != "Zusatz"):
                continue  # schon in Top 10
            # Zusatzeintrag (z. B. Sparkasse Krefeld) wird Teil der Top 40
            rows[:] = [r for r in rows if not (r[0] == gname and r[1] == "Zusatz" and (key_of(r[2]["name"]).startswith(k) or k.startswith(key_of(r[2]["name"]))))]
            b = merge(b)
            b["source_type"] = OVR.get(k, b.get("source_type"))
            rows.append((gname, "Top 40", b))
# manuelle Ergänzung: State Street nur mit gerundeten Werten 2023 verfügbar
for g_, r_, b_ in rows:
    if b_["name"].startswith("State Street") and b_.get("bilanzsumme") is None:
        b_.update(fiscal_year=2023, stichtag="2023-12-31", bilanzsumme=46.2e9, eigenkapital=3.89e9, vj_bilanzsumme=None,
                  source_type="Sekundärquelle (Eulerpool, gerundet, GJ 2023)")
# ---------- Erweiterung: alle deutschen Einträge im EBA-Pillar-3-Datenhub ----------
# (eba_hub_neu_2025.json aus mk_hub_neu.py; neue Banken mit Rolle "EBA-Hub", bestehende Banken nur Lückenfüllung)
HN = load("eba_hub_neu_2025.json") or {"neu": [], "bestehend": []}
EXTRA_GROUP = "Förder- und Sonderinstitute"
HUB_URL = "https://edap-public.eba.europa.eu/Report/index/MTE2"
def e6(v):
    return None if v is None else v * 1e6
for h in HN["neu"]:
    c2 = h.get("cc2") or {}
    hgb = c2.get("hgb")
    st_ = "EBA-Hub CC2 (Bilanz laut Abschluss" + (", HGB)" if hgb else ", Summenzeilen; ggf. IFRS/Konzern)") if c2.get("bilanzsumme") else "EBA-Hub (keine Bilanz in CC2)"
    nt = [f"Ergänzt am 27.10.2026 aus dem EBA-Pillar-3-Datenhub (Hub-Eintrag: {h['hub_name']}, LEI {h['lei']}); Institutsart: {h['art']}."]
    if c2.get("notes"):
        nt.append("CC2: " + "; ".join(c2["notes"]) + ".")
    b = {"name": h["name"], "sitz": None, "fiscal_year": 2025 if c2.get("bilanzsumme") else None, "stichtag": "2025-12-31",
         "bilanzsumme": e6(c2.get("bilanzsumme")), "eigenkapital": e6(c2.get("eigenkapital")),
         "fonds_340g": e6(c2.get("fonds_340g")) if hgb or c2.get("fonds_340g") else None,
         "source_type": st_, "source_url": HUB_URL, "source_doc": "EU CC2/KM1/CC1/OV1 zum 31.12.2025, Data Points Report, Filter Country = Germany",
         "notes": " ".join(nt), "_hub": h}
    rows.append((h["gruppe"], "EBA-Hub", b))
# bestehende Banken: fehlende EK/Fonds aus CC2 (nur HGB-Einzelinstitute) ergänzen
HB = {}
for h in HN["bestehend"]:
    HB.setdefault(norm(h["name"]), []).append(h)
for g_, r_, b_ in rows:
    for h in HB.get(norm(b_["name"]), []):
        c2 = h.get("cc2") or {}
        if not c2.get("hgb") or not c2.get("bilanzsumme") or c2.get("fonds_340g") is None:
            continue
        filled = []
        for f, k in (("eigenkapital", "eigenkapital"), ("fonds_340g", "fonds_340g")):
            if b_.get(f) is None and c2.get(k) is not None:
                b_[f] = c2[k] * 1e6; filled.append(f)
        if filled:
            dev = ""
            if b_.get("bilanzsumme") and abs(b_["bilanzsumme"] / 1e6 - c2["bilanzsumme"]) > 0.005 * c2["bilanzsumme"]:
                dev = f" Bilanzsumme laut CC2 {c2['bilanzsumme']:,.1f} Mio. weicht von der Bilanzsumme dieser Zeile ab.".replace(",", "X").replace(".", ",").replace("X", ".")
            b_["notes"] = ((b_.get("notes") or "") + f" | Ergänzung 27.10.2026 ({', '.join(filled)}) aus EU CC2 im EBA-Datenhub (Hub-Eintrag {h['hub_name']}; Bilanz laut Jahresabschluss).{dev}").strip(" |")
            b_["_nach"] = True
# ---------- Lückenfüllung 27.10.2026 ----------
# Nacherhebung: Offenlegungsberichte (EU CC2) und Geschäftsberichte von den Websites der Banken (Quellen je Wert in der JSON)
NE = load("nacherhebung_2026-10-27.json") or {}
def ne_val(name, y, k):
    x = ((NE.get(name) or {}).get("jahre") or {}).get(str(y), {}).get(k)
    return x
# ---------- Website-Erhebung 27.10.2026 ----------
# Jahresabschlüsse 2025 von den Bankwebsites bzw. aus dem Lobbyregister des Bundestags, von Hand aus der Jahresbilanz abgelesen (Mio. €).
# Werte aus der Jahresbilanz ersetzen schwächere Angaben (Sekundärquelle, Rangliste, Lagebericht, EBA-Hub CC2);
# Einträge mit vj_only (nur Vorjahr, z. B. aus EU CC2 des Offenlegungsberichts 2024) füllen nur leere Zellen.
WS = {norm(i["bank"]): i for i in (load("websites_2026-10-27.json") or {"items": []})["items"]}
WSF = (("bilanzsumme", "bs"), ("eigenkapital", "ek"), ("fonds_340g", "fonds"), ("davon_340e", "f340e"),
       ("vj_bilanzsumme", "vj_bs"), ("vj_eigenkapital", "vj_ek"), ("vj_fonds_340g", "vj_fonds"))
def ws_fmt(v):
    return "n. v." if v is None else f"{v / 1e6:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
for g_, r_, b_ in rows:
    w = WS.get(norm(b_["name"]))
    if not w:
        continue
    changed, old = [], {f: b_.get(f) for f, _ in WSF}
    if not w.get("vj_only"):
        if (b_.get("fiscal_year") or 0) != w["gj"]:
            for f, _ in WSF:
                b_[f] = None  # anderes Geschäftsjahr: Altwerte verwerfen
            changed.append(f"GJ {b_.get('fiscal_year') or 'n. v.'} → {w['gj']}")
        b_["fiscal_year"], b_["stichtag"] = w["gj"], f"{w['gj']}-12-31"
        b_["source_type"], b_["source_url"], b_["source_doc"] = w["typ"], w["url"], w["doc"]
    for f, k in WSF:
        v = w.get(k)
        if v is None or (w.get("vj_only") and b_.get(f) is not None):
            continue
        v *= 1e6
        if old.get(f) is None or abs(old[f] - v) > 0.05e6:
            changed.append(f"{f} {ws_fmt(old.get(f))} → {ws_fmt(v)}")
        b_[f] = v
    for y, ks in ((w["gj"], ("ju", "bilgew")), (w["gj"] - 1, ("vj_ju", "vj_bilgew"))):
        for k in ks:
            if w.get(k) is not None:
                NE.setdefault(b_["name"], {"jahre": {}}).setdefault("jahre", {}).setdefault(str(y), {})[k.replace("vj_", "")] = \
                    {"wert": w[k], "quelle": w["url"], "dokument": w["doc"]}
    if w.get("vj_only"):
        b_["notes"] = ((b_.get("notes") or "") + f" | Website-Erhebung 27.10.2026 (Vorjahr): {w['doc']} – {w['url']}. {w.get('note') or ''}").strip(" |")
    else:
        b_["notes"] = ((b_.get("notes") or "") + f" | Website-Erhebung 27.10.2026: Werte aus {w['doc']}"
                       + (f"; geändert: {', '.join(changed)}" if changed else "; bisherige Werte bestätigt") + f". {w.get('note') or ''}").strip(" |")
    if changed:
        b_["_nach"] = True
# Sitz der Hub-Banken aus der GLEIF-LEI-Datenbank
GLEIF = (load("gleif_sitz.json") or {"items": {}})["items"]
def city(c):
    if not c:
        return None
    c = {"COLOGNE": "Köln"}.get(c.upper(), c)
    return c.title().replace(" Am ", " am ").replace(" Im ", " im ").replace(" An Der ", " an der ").replace(" Vor Der ", " vor der ") if c.isupper() or " Im " in c else c
for g_, r_, b_ in rows:
    if r_ == "EBA-Hub" and not b_.get("sitz"):
        b_["sitz"] = city((GLEIF.get(b_["_hub"]["lei"]) or {}).get("sitz"))
# Kernkapital-Posten aus der Bilanz (Blatt Bilanzen bzw. EU CC2 im EBA-Hub), wo die Jahresbilanz-Ablesung fehlt
BIL0 = {norm(k): v for k, v in (load("bilanzen_2025.json") or {}).items()}
for g_, r_, b_ in rows:
    n_ = norm(b_["name"])
    if n_ in KK:
        if KK[n_].get("bilanzgewinn") is None and ne_val(b_["name"], 2025, "bilgew"):
            KK[n_] = dict(KK[n_], bilanzgewinn=ne_val(b_["name"], 2025, "bilgew")["wert"],
                          notes=((KK[n_].get("notes") or "") + "; Bilanzgewinn aus Nacherhebung 27.10.2026").strip("; "))
        continue
    hs = [b_["_hub"]] if b_.get("_hub") else HB.get(n_, [])
    c2 = next((h["cc2"] for h in hs if (h.get("cc2") or {}).get("hgb") and h["cc2"].get("vollstaendig")), None)
    bl = BIL0.get(n_)
    src = None
    if bl and bl.get("aktiva"):
        a, p, src = bl["aktiva"], bl["passiva"], (bl.get("source_url") or "") + " (Blatt Bilanzen)"
    elif c2:
        a, p, src = c2["aktiva"], c2["passiva"], "EU CC2 im EBA-Datenhub (Bilanz laut Jahresabschluss)"
    if not src:
        continue
    bg = c2.get("bilanzgewinn") if c2 else None
    if bg is None and ne_val(b_["name"], 2025, "bilgew"):
        bg = ne_val(b_["name"], 2025, "bilgew")["wert"]
    ek_ = b_["eigenkapital"] / 1e6 if b_.get("eigenkapital") is not None else None
    if bg is not None and ek_ and abs(bg) > 0.15 * ek_:
        bg = None  # unplausibel (vermutlich Gewinnrücklage/Vortrag)
    KK[n_] = {"name": b_["name"], "source_url": src,
              "at1_posten": p.get("at1") or 0, "nachrang": p.get("nachrang") or 0, "genussrechte": p.get("genuss") or 0,
              "bilanzgewinn": None if bg is None else round(bg, 3), "immaterielle": a.get("immat") or 0, "akt_lat_steuern": a.get("akt_lat") or 0,
              "notes": "Posten am 27.10.2026 aus der Bilanz übernommen" + ("" if bg is not None else "; Bilanzgewinn nicht ausgewiesen bzw. n. v.")}
# Nacherhebung 27.10.2026: Offenlegungsberichte (EU CC2) und Geschäftsberichte von den Websites der Banken
for g_, r_, b_ in rows:
    e = NE.get(b_["name"])
    if not e:
        continue
    gj = b_.get("fiscal_year") or 2025
    filled, srcs = [], []
    for f, k, y in (("bilanzsumme", "bs", gj), ("eigenkapital", "ek", gj), ("fonds_340g", "fonds", gj),
                    ("vj_bilanzsumme", "bs", gj - 1), ("vj_eigenkapital", "ek", gj - 1), ("vj_fonds_340g", "fonds", gj - 1)):
        x = ne_val(b_["name"], y, k)
        if b_.get(f) is not None or x is None:
            continue
        v = x["wert"]
        cur = b_.get({"vj_bilanzsumme": "bilanzsumme", "vj_eigenkapital": "eigenkapital", "vj_fonds_340g": "fonds_340g"}.get(f, f))
        if f.startswith("vj_") and cur:
            q = v * 1e6 / cur
            if (k == "bs" and not 0.6 <= q <= 1.6) or (k == "ek" and not 0.7 <= q <= 1.3) or (k == "fonds" and q > 1.3 and v > 1):
                continue
        if k == "fonds" and v == 0 and (b_.get("vj_fonds_340g") or b_.get("fonds_340g")):
            continue
        b_[f] = v * 1e6; filled.append(f); srcs.append(f"{x['dokument']} ({x['quelle']})")
    if filled:
        if "bilanzsumme" in filled:
            b_["fiscal_year"] = 2025
        b_["notes"] = ((b_.get("notes") or "") + " | Nacherhebung 27.10.2026 (" + ", ".join(filled) + "): " + "; ".join(sorted(set(srcs)))).strip(" |")
        b_["_nach"] = True
# sort ranking inside group by Bilanzsumme
ALLG = [g for g, _ in groups] + [EXTRA_GROUP]
order = {g: i for i, g in enumerate(ALLG)}
ROLE_ORDER = {"Zusatz": 1, "EBA-Hub": 2}
CORE = lambda rolle: rolle not in ("Zusatz", "EBA-Hub")
def sk(r):
    g, rolle, b = r
    return (order[g], ROLE_ORDER.get(rolle, 0), -(b.get("bilanzsumme") or 0))
rows.sort(key=sk)
for _, _, b in rows:
    k = KK.get(norm(b["name"]))
    if k and k.get("stille_im_ek") and not b.get("davon_at1"):
        b["davon_at1"] = k["stille_im_ek"] * 1e6
        b["notes"] = ((b.get("notes") or "") + f" | Stille Einlagen im EK {k['stille_im_ek']:,.1f} Mio. laut Jahresbilanz (24.10.2026).".replace(",", "X").replace(".", ",").replace("X", ".")).strip(" |")

wb = Workbook()
HDR = Font(bold=True, color="FFFFFF")
HFILL = PatternFill("solid", fgColor="1F3864")
MISS = PatternFill("solid", fgColor="FCE4D6")
SEC = PatternFill("solid", fgColor="FFF2CC")
HUBF = PatternFill("solid", fgColor="E2EFDA")
thin = Side(style="thin", color="BFBFBF")

# ---------- Übersicht ----------
ws = wb.active
ws.title = "Übersicht"
cols = ["Gruppe", "Rolle", "Rang", "Bank", "Sitz", "GJ", "Bilanzsumme (Mio. €)", "Eigenkapital (Mio. €)",
        "davon AT1/stille Einlagen im EK (Mio. €)", "EK-Quote (EK/BS)", "Fonds § 340g (Mio. €)",
        "Fonds § 340g in % BS", "EK-Quote inkl. Fonds § 340g", "davon § 340e Abs. 4 (Mio. €)",
        "VJ Bilanzsumme (Mio. €)", "VJ Eigenkapital (Mio. €)", "VJ Fonds § 340g (Mio. €)",
        "VJ EK-Quote", "VJ EK-Quote inkl. Fonds", "Veränderung Fonds § 340g (Mio. €)",
        "AT1-Instrumente, eigener Passivposten (Mio. €)", "Nachrangige Verbindlichkeiten (Mio. €)",
        "Genussrechtskapital (Mio. €)", "Bilanzgewinn (Mio. €)", "Immaterielle Anlagewerte (Mio. €)",
        "Aktive latente Steuern (Mio. €)", "CET1-Näherung (Mio. €)", "CET1-Näherung in % BS",
        "Kernkapital-Näherung (CET1 + AT1, Mio. €)", "Kernkapital-Näherung in % BS",
        "Quellenart", "Quelle (Link)", "Fundstelle", "Anmerkungen", "Hinweis Kernkapital-Posten"]
ws.append(cols)
for c in range(1, len(cols) + 1):
    cell = ws.cell(1, c)
    cell.font = HDR; cell.fill = HFILL
    cell.alignment = Alignment(wrap_text=True, vertical="top")
ws.row_dimensions[1].height = 48

def mio(v):
    return None if v is None else round(v / 1e6, 3)

rank_ctr = {}
for gname, rolle, b in rows:
    r = ws.max_row + 1
    if rolle == "Zusatz":
        rank = b.get("rank") if gname == "Sparkassen" else None
    elif rolle == "EBA-Hub":
        rank = None
    else:
        rank_ctr[gname] = rank_ctr.get(gname, 0) + 1
        rank = rank_ctr[gname]
    vals = [gname, rolle, rank, b["name"], b.get("sitz"), b.get("fiscal_year"),
            mio(b.get("bilanzsumme")), mio(b.get("eigenkapital")), mio(b.get("davon_at1")), None,
            mio(b.get("fonds_340g")), None, None, mio(b.get("davon_340e")),
            mio(b.get("vj_bilanzsumme")), mio(b.get("vj_eigenkapital")), mio(b.get("vj_fonds_340g")),
            None, None, None]
    k = KK.get(norm(b["name"]))
    cet1, t1 = kk_calc(b)
    vals += [k.get(f) if k else None for f in KKF]
    vals += [cet1, cet1 / mio(bs) if cet1 is not None and (bs := b.get("bilanzsumme")) else None,
             t1, t1 / mio(b["bilanzsumme"]) if t1 is not None and b.get("bilanzsumme") else None]
    b["_cet1"], b["_t1"] = cet1, t1
    kk_note = None
    if k:
        kk_note = "Jahresbilanz: " + (k.get("source_url") or "") + (" – " + k["notes"] if k.get("notes") else "")
    vals += [b.get("source_type"), b.get("source_url"), b.get("source_doc"), b.get("notes"), kk_note]
    ws.append(vals)
    G, H, K, O, P, Q = (f"{x}{r}" for x in "GHKOPQ")
    def q(a, b):
        return a / b if a is not None and b else "n. v."
    def qs(a, c, b):
        return (a + c) / b if a is not None and c is not None and b else "n. v."
    bs_, ek_, fo_ = b.get("bilanzsumme"), b.get("eigenkapital"), b.get("fonds_340g")
    vbs, vek, vfo = b.get("vj_bilanzsumme"), b.get("vj_eigenkapital"), b.get("vj_fonds_340g")
    ws[f"J{r}"] = q(ek_, bs_)
    ws[f"L{r}"] = q(fo_, bs_)
    ws[f"M{r}"] = qs(ek_, fo_, bs_)
    ws[f"R{r}"] = q(vek, vbs)
    ws[f"S{r}"] = qs(vek, vfo, vbs)
    ws[f"T{r}"] = round((fo_ - vfo) / 1e6, 3) if fo_ is not None and vfo is not None else "n. v."
    for c in range(21, 31):
        cell = ws.cell(r, c)
        if c in (28, 30):
            cell.number_format = '0.00%'
        else:
            cell.number_format = '#,##0.0'
        if cell.value is None:
            cell.value = "n. v."
            cell.fill = MISS
            cell.alignment = Alignment(horizontal="right")
    for c in (7, 8, 9, 11, 14, 15, 16, 17, 20):
        cell = ws.cell(r, c)
        cell.number_format = '#,##0.0'
        if cell.value is None and c in (7, 8, 11, 15, 16, 17):
            cell.value = "n. v."
            cell.fill = MISS
            cell.alignment = Alignment(horizontal="right")
    for c in (10, 12, 13, 18, 19):
        ws.cell(r, c).number_format = '0.00%'
    if b.get("source_url"):
        ws.cell(r, 32).hyperlink = b["source_url"]
        ws.cell(r, 32).style = "Hyperlink"
    if rolle == "Zusatz":
        for c in range(1, 7):
            ws.cell(r, c).fill = SEC
    elif rolle == "EBA-Hub":
        for c in range(1, 7):
            ws.cell(r, c).fill = HUBF
    for c in (33, 34, 35):
        ws.cell(r, c).alignment = Alignment(wrap_text=False, vertical="top")

last = ws.max_row
widths = [18, 11, 6, 46, 16, 6, 14, 14, 13, 10, 13, 10, 11, 12, 14, 14, 13, 10, 11, 12,
          13, 13, 12, 12, 12, 12, 13, 11, 14, 11, 20, 40, 45, 80, 60]
for i, w in enumerate(widths, 1):
    ws.column_dimensions[get_column_letter(i)].width = w
ws.freeze_panes = "E2"
tab = Table(displayName="Banken", ref=f"A1:{get_column_letter(len(cols))}{last}")
tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
ws.add_table(tab)

# ---------- Gruppenauswertung (Werte in Python berechnet) ----------
ga = wb.create_sheet("Gruppenauswertung")
ga.append(["Gruppe", "Banken in Liste", "mit vollst. Werten (BS, EK, Fonds)",
           "Summe Bilanzsumme (Mio. €)", "EK-Quote gewichtet", "EK-Quote Median",
           "Fonds § 340g in % BS gewichtet", "Fonds § 340g in % BS Median",
           "EK-Quote inkl. Fonds gewichtet", "EK-Quote inkl. Fonds Median",
           "Anteil Fonds an (EK + Fonds) gewichtet"])
for c in range(1, 12):
    cell = ga.cell(1, c); cell.font = HDR; cell.fill = HFILL
    cell.alignment = Alignment(wrap_text=True, vertical="top")
ga.row_dimensions[1].height = 48
summary = {}
for gname, sel_all in [(g, [b for gg, rolle, b in rows if gg == g and CORE(rolle)]) for g, _ in groups]:
  for label, sel in ([("Top 10", sel_all[:10]), ("Top 40", sel_all)] if gname != "Landesbanken" else [("alle", sel_all)]):
      full = [b for b in sel if all(b.get(f) is not None for f in ("bilanzsumme", "eigenkapital", "fonds_340g"))]
      if not full:
          continue
      bs = sum(b["bilanzsumme"] for b in full); ek = sum(b["eigenkapital"] for b in full); fo = sum(b["fonds_340g"] for b in full)
      eq = [b["eigenkapital"] / b["bilanzsumme"] for b in full]
      fq = [b["fonds_340g"] / b["bilanzsumme"] for b in full]
      tq = [(b["eigenkapital"] + b["fonds_340g"]) / b["bilanzsumme"] for b in full]
      s = dict(n=len(sel), nf=len(full), bs=bs, ekw=ek / bs, ekm=statistics.median(eq), fw=fo / bs,
               fm=statistics.median(fq), tw=(ek + fo) / bs, tm=statistics.median(tq), share=fo / (ek + fo))
      summary[gname + " " + label] = s
      ga.append([gname + " – " + label, s["n"], s["nf"], round(bs / 1e6, 1), s["ekw"], s["ekm"], s["fw"], s["fm"], s["tw"], s["tm"], s["share"]])
      r = ga.max_row
      ga.cell(r, 4).number_format = '#,##0'
      for c in range(5, 12):
          ga.cell(r, c).number_format = '0.00%'
ga.append([])
ga.append(["Gruppe", "Banken in Liste", "mit CET1-Näherung", "Summe Bilanzsumme dieser Banken (Mio. €)",
           "CET1-Näherung in % BS gewichtet", "CET1-Näherung in % BS Median",
           "Kernkapital-Näherung in % BS gewichtet", "Kernkapital-Näherung in % BS Median",
           "Abzüge (Bilanzgewinn, Immaterielle, akt. lat. Steuern) in % von (EK + Fonds)"])
hr = ga.max_row
for c in range(1, 10):
    cell = ga.cell(hr, c); cell.font = HDR; cell.fill = HFILL
    cell.alignment = Alignment(wrap_text=True, vertical="top")
ga.row_dimensions[hr].height = 48
for gname, sel_all in [(g, [b for gg, rolle, b in rows if gg == g and CORE(rolle)]) for g, _ in groups]:
  for label, sel in ([("Top 10", sel_all[:10]), ("Top 40", sel_all)] if gname != "Landesbanken" else [("alle", sel_all)]):
      kb = [b for b in sel if b.get("_cet1") is not None]
      if not kb:
          continue
      bsk = sum(b["bilanzsumme"] for b in kb) / 1e6
      tb = [b for b in kb if b.get("_t1") is not None]
      base = sum(mio(b["eigenkapital"]) + mio(b["fonds_340g"]) for b in kb)
      ded = sum(mio(b["eigenkapital"]) - (mio(b.get("davon_at1")) or 0) + mio(b["fonds_340g"]) - b["_cet1"] for b in kb)
      s = dict(n=len(kb), cw=sum(b["_cet1"] for b in kb) / bsk,
               cm=statistics.median(b["_cet1"] / mio(b["bilanzsumme"]) for b in kb),
               tw=sum(b["_t1"] for b in tb) / (sum(b["bilanzsumme"] for b in tb) / 1e6) if tb else None,
               tm=statistics.median(b["_t1"] / mio(b["bilanzsumme"]) for b in tb) if tb else None)
      summary[gname + " " + label].update(kk=s)
      ga.append([gname + " – " + label, len(sel), len(kb), round(bsk, 1), s["cw"], s["cm"], s["tw"], s["tm"], ded / base])
      r = ga.max_row
      ga.cell(r, 4).number_format = '#,##0'
      for c in range(5, 10):
          ga.cell(r, c).number_format = '0.00%'
ga.append([])
ga.append(["CET1-Näherung = EK − stille Einlagen/AT1 im EK + Fonds § 340g − Bilanzgewinn − immaterielle Anlagewerte − aktive latente Steuern; Kernkapital-Näherung = CET1-Näherung + stille Einlagen/AT1 im EK + AT1-Instrumente (eigener Posten). Bilanzielle Näherung, nicht die gemeldete Kapitalquote (die bezieht sich auf risikogewichtete Aktiva). Siehe Blatt 'Methodik'."])
ga.append(["Gewichtet = Summe EK (bzw. Fonds) / Summe Bilanzsumme der Banken mit vollständigen Werten; Median = mittlerer Wert der Einzelquoten. Ohne Zusatzeinträge (DZ BANK, DekaBank, DKB). Ränge 11–40 stützen sich teils auf Ranglisten-Bilanzsummen (Quellenart 'Rangliste')."])
for i, w in enumerate([22, 10, 14, 16, 12, 12, 14, 14, 14, 14, 16], 1):
    ga.column_dimensions[get_column_letter(i)].width = w

# ---------- Weitere / ausgeschlossen ----------
ex = wb.create_sheet("Nicht aufgenommen")
ex.append(["Gruppe", "Institut", "Grund / Hinweis", "Bilanzsumme (Mio. €)", "Quelle"])
for c in range(1, 6):
    cell = ex.cell(1, c); cell.font = HDR; cell.fill = HFILL
for gname, d in groups:
    if not d:
        continue
    for e in d.get("excluded", []):
        ex.append([gname, e["name"], e.get("reason") or e.get("notes"), mio(e.get("bilanzsumme")), e.get("source_url")])
        ex.cell(ex.max_row, 4).number_format = '#,##0.0'
for gname, e in ext_excluded:
    ex.append([gname, e["name"], e.get("reason") or e.get("notes"), mio(e.get("bilanzsumme")), e.get("source_url")])
for i, w in enumerate([20, 45, 110, 14, 60], 1):
    ex.column_dimensions[get_column_letter(i)].width = w

# ---------- Methodik ----------
me = wb.create_sheet("Methodik")
lines = [
    "Bilanzvergleich deutscher Banken – Geschäftsjahr 2025 (Stichtag 31.12.2025), Stand der Erhebung: 17.10.2026, Nacherhebung aus Original-Jahresabschlüssen: 24.10.2026",
    "",
    "Grundlage: HGB-Einzelabschlüsse (Jahresabschluss nach §§ 340 ff. HGB), nicht IFRS-Konzernabschlüsse.",
    "Größe: Bilanzsumme laut HGB-Einzelabschluss.",
    "Eigenkapital: Passivposten 'Eigenkapital' (gezeichnetes Kapital inkl. stiller Einlagen, Rücklagen, Bilanzgewinn). AT1-Anleihen, die als eigener Passivposten außerhalb des Eigenkapitals stehen, sind NICHT enthalten (siehe Anmerkungen).",
    "EK-Quote = Eigenkapital / Bilanzsumme (bilanzielle Quote, keine aufsichtsrechtliche Kapitalquote).",
    "EK-Quote inkl. Fonds = (Eigenkapital + Fonds für allgemeine Bankrisiken nach § 340g HGB) / Bilanzsumme.",
    "Der Fonds § 340g wird in der Bilanz als eigener Posten vor dem Eigenkapital ausgewiesen und zählt aufsichtsrechtlich zum harten Kernkapital (CET1). Er enthält ggf. den Sonderposten nach § 340e Abs. 4 HGB (Handelsbestand), soweit angegeben in eigener Spalte.",
    "",
    "Gruppen:",
    "Private Banken: Kreditbanken mit Sitz in Deutschland; ohne Post-Brexit-Hubs ausländischer Investmentbanken, Marktinfrastruktur und Trade Republic (Bilanz fast vollständig Treuhandvermögen) – siehe Blatt 'Nicht aufgenommen'.",
    "Genossenschaftsbanken: Kreditgenossenschaften (Volks-, Raiffeisen-, Sparda-, PSD-Banken u. a.) ohne Zentralinstitute; MünchenerHyp und apoBank sind genossenschaftliche Spezialinstitute und als solche gekennzeichnet. DZ BANK AG als Zusatzeintrag.",
    "Sparkassen: ohne Landesbanken; Berliner Sparkasse ist Teil der BSK 1818 AG (ehem. Landesbank Berlin AG) ohne eigenen Abschluss und steht deshalb bei den Landesbanken. Sparkasse Krefeld ist Teil der Top 40.",
    "Landesbanken: alle Landesbanken; DekaBank und DKB als Zusatzeinträge.",
    "",
    "Quellen: Jahresabschlüsse/Geschäftsberichte der Institute; wo die formale Bilanz nicht lesbar war, Lageberichte, Offenlegungsberichte (EU CC2), HGB-Halbjahresberichte (Vorjahresspalte) oder Sekundärquellen – die Quellenart steht je Zeile in Spalte 'Quellenart', Details in 'Fundstelle' und 'Anmerkungen'.",
    "Nacherhebung 24.10.2026: Für Landesbanken, große Sparkassen, Genossenschaftsbanken und Privatbanken wurden die Jahresabschlüsse direkt von den Bankwebsites geladen und EK/Fonds/Bilanzsumme aus der formalen HGB-Bilanz (Passivseite) übernommen; diese Werte ersetzen Ranglisten-, Presse- und Sekundärwerte (Kennzeichnung in Spalte 'Anmerkungen'). Viele Sparkassen veröffentlichen ihren Abschluss nur im Unternehmensregister; dort ist der Abruf durch eine Sicherheitsabfrage geschützt und wurde nicht automatisiert.",
    "",
    "Kernkapital-Bausteine (Ergänzung 24.10.2026): Aus der HGB-Jahresbilanz abgelesen: AT1-Instrumente als eigener Passivposten ('Instrumente des zusätzlichen aufsichtsrechtlichen Kernkapitals'), nachrangige Verbindlichkeiten, Genussrechtskapital, Bilanzgewinn (Passiva) sowie immaterielle Anlagewerte und aktive latente Steuern (Aktiva). 0 = Posten in der vollständigen Bilanz nicht ausgewiesen; 'n. v.' = keine vollständige Bilanz verfügbar (nur verkürzte Bilanz, Offenlegungsbericht oder gar keine Quelle). Quelle je Zeile in Spalte 'Hinweis Kernkapital-Posten'.",
    "CET1-Näherung = Eigenkapital − stille Einlagen/AT1 im EK + Fonds § 340g − Bilanzgewinn (soweit positiv) − immaterielle Anlagewerte − aktive latente Steuern.",
    "Kernkapital-Näherung (Tier 1) = CET1-Näherung + stille Einlagen/AT1 im EK + AT1-Instrumente (eigener Posten). Nachrangige Verbindlichkeiten und Genussrechte sind Ergänzungskapital (Tier 2) bzw. ggf. AT1 und fließen nicht ein; sie stehen nur zur Information in der Tabelle.",
    "Grenzen der Näherung: (1) Der Bilanzgewinn wird vollständig abgezogen; bei Sparkassen und Genossenschaftsbanken wird er oft größtenteils thesauriert und zählt nach Feststellung des Abschlusses zum CET1. (2) Aktive latente Steuern sind vollständig abgezogen; aufsichtsrechtlich wird nur der Teil aus Verlustvorträgen voll abgezogen, temporäre Differenzen bis zum Schwellenwert nach Art. 48 CRR werden mit 250 % gewichtet. (3) Weitere CET1-Abzüge (z. B. Beteiligungen an Finanzinstituten, Pensionsfondsvermögen, Prudent Valuation, NPL-Backstop, Unterdeckung bei IRB-Wertberichtigungen) und die stillen Vorsorgereserven nach § 340f HGB (Tier 2) sind aus der Bilanz nicht ablesbar. (4) Ob stille Einlagen heute als AT1 oder nur als Tier 2 anrechenbar sind, ist nicht geprüft. Die Werte sind daher eine bilanzielle Orientierung und nicht mit der gemeldeten CET1- oder Kernkapitalquote (Bezug: risikogewichtete Aktiva) vergleichbar; '% BS' ist eher mit der Leverage Ratio verwandt.",
    "Blatt 'Zeitreihe 2021-2025' (Stand 24.10.2026): Bilanzsumme, Eigenkapital, Fonds § 340g und Jahresüberschuss je Bank und Jahr (Mio. €) mit jährlichem Wachstum und durchschnittlichem Wachstum p. a. (Formeln). 2025 und 2024 stammen aus dem GJ2025-Bericht (Vorjahresspalte), der Jahresüberschuss aus der GuV. Ältere Jahre wurden nur dort eingetragen, wo der Jahresabschluss bzw. Geschäftsbericht des Instituts frei abrufbar war (Download von der Bankwebsite, automatisiert ausgelesen, Folgejahre gegeneinander geprüft). Viele Sparkassen und Genossenschaftsbanken veröffentlichen ältere Abschlüsse nur im Unternehmensregister/Bundesanzeiger; dort ist der Abruf durch eine Sicherheitsabfrage geschützt, die nicht umgangen wurde. 'n. v.' = nicht erhoben. Der Jahresüberschuss ist das Ergebnis nach Steuern UND nach Zuführung zum Fonds § 340g; bei Banken mit Gewinnabführung steht 0.",
    "Blatt 'Offenlegung 31.12.2025' (Stand 26.10.2026): Gemeldete Kapitalkennzahlen aus Tabelle EU KM1 der Offenlegungsberichte nach Teil 8 CRR (hartes Kernkapital, Kernkapital, Eigenmittel, RWA, Quoten, Gesamtkapitalanforderung EU 11a, Leverage Ratio). Erhoben für 95 von 129 Banken: 32 aus Berichten auf den Bankwebsites, 63 aus dem Pillar-3-Datenhub der EBA (Data Points Report, Template EU KM1, Spalte T, Export über die Weboberfläche am 26.10.2026). Für die 27 Banken mit beiden Quellen stimmten die Werte überein. Der Hub zeigt jeweils die höchste Konsolidierungsebene im EWR; bei Privatbanken und Landesbanken ist das oft eine Gruppe ('Ebene des Berichts'). 34 Banken sind in keiner der beiden Quellen ('n. v.'). AT1 = Kernkapital − CET1, Tier 2 = Eigenmittel − Kernkapital, RWA-Dichte = RWA / HGB-Bilanzsumme (Formeln). Bei Gruppenberichten ist die RWA-Dichte nur ein Richtwert und geht nicht in den Gruppenmedian ein.",
    "Blätter 'Eigenmittel CC1' und 'RWA-Aufteilung OV1' (Stand 26.10.2026): Tabellen EU CC1 (Zusammensetzung der Eigenmittel) und EU OV1 (Aufteilung der Gesamtrisikobeträge) zum 31.12.2025 aus dem Pillar-3-Datenhub der EBA, Export über die Weboberfläche (Rohdateien eba_hub_cc1_20251231.csv, eba_hub_ov1_20251231.csv, aufbereitet in eba_cc1_ov1_2025.json). Verfügbar für 89 der 129 Banken. Kennzahlen als Formeln. Kreditrisikoanpassungen im T2 (CC1 Zeile 50) enthalten bei HGB-Instituten vor allem die Vorsorgereserven nach § 340f. Der Vergleich 'Fonds HGB über aufsichtlichem Fonds' zeigt den Teil des Fonds § 340g, der zum Stichtag noch nicht als CET1 angerechnet war (meist die Zuführung des Geschäftsjahres).",
    "Erweiterung 27.10.2026 (Rolle 'EBA-Hub', grün hinterlegt): Alle Institute, die im Pillar-3-Datenhub der EBA (edap-public.eba.europa.eu, Data Points Report) mit dem Filter Country = Germany erscheinen, sind in jeder Tabelle ergänzt. "
    f"Dazu wurden über die normale Weboberfläche exportiert: KM1 für alle Stichtage (170 deutsche Einträge), CC1 und OV1 zum 31.12.2025 (vorhanden) sowie EU CC2 zum 31.12.2025 (159 Einträge). Zusammen sind das {len(HN['neu']) + len(HN['bestehend'])} deutsche Hub-Einträge; {len(HN['bestehend'])} davon gehören zu bereits erfassten Banken (teils mehrere Ebenen je Bank, z. B. HASPA Finanzholding und Hamburger Sparkasse AG), {sum(1 for x in rows if x[1] == 'EBA-Hub')} Institute sind neu und der passenden Gruppe zugeordnet "
    "(Sparkassen inkl. Landesbausparkassen, Genossenschaftsbanken inkl. Bausparkasse Schwäbisch Hall und BFS SozialFinanz, Private Banken inkl. privater Bausparkassen und EU-Töchtern ausländischer Bankengruppen, die Holding der DekaBank bei den Landesbanken, KfW IPEX-Bank und KfW Beteiligungsholding als neue Gruppe 'Förder- und Sonderinstitute'). "
    "Neu aufgenommen sind damit auch Häuser, die in der ursprünglichen Auswahl bewusst fehlten (z. B. Post-Brexit-Hubs, Trade Republic, AKA, Standard Chartered); sie zählen weder zu den Top-40-Rängen noch zur 'Gruppenauswertung', die unverändert die bisherige Auswahl zeigt.",
    "Bilanzsumme, Eigenkapital und Fonds § 340g der neuen Institute stammen aus EU CC2 Spalte a (Bilanz laut Jahresabschluss; bei HGB-Instituten die HGB-Einzelbilanz, bei Konzernen/Holdings IFRS-Summenzeilen, Quellenart je Zeile). Der Hub-Export ('Summarized data') liefert für Positionen ohne Schlüssel keinen Einzelwert; betroffen ist meist 'Verbindlichkeiten gegenüber Kunden'. Dieser Posten ist dann als Differenz Bilanzsumme − übrige Passiva berechnet (Hinweis je Zeile). "
    "Prüfung: Für 55 bereits erfasste HGB-Institute stimmten Bilanzsumme, Eigenkapital und Fonds aus CC2 mit den Original-Jahresabschlüssen überein. Für 7 bestehende Sparkassen ohne EK/Fonds-Angabe (u. a. KSK Esslingen-Nürtingen, Ludwigsburg, München Starnberg Ebersberg, Waiblingen, Sparkasse Aachen, Mainfranken, Schwaben-Bodensee) wurden EK und Fonds aus CC2 ergänzt. "
    "KM1 fehlt im Hub bei BSK 1818 AG, Hamburger Sparkasse AG und KfW IPEX-Bank; dort sind CET1, Kernkapital, Eigenmittel, RWA und Quoten aus CC1 übernommen. Aareal Bank (30.06.2026), Siemens Bank und Trade Republic (30.09.2025) haben im Hub kein KM1 zum 31.12.2025; ihr KM1 zum jeweils verfügbaren Stichtag ist mit Hinweis eingetragen. Kein CC2 im Hub: BHW Bausparkasse, Sparkasse Duisburg, Sparkasse Südpfalz, SWK Bank, Trade Republic.",
    "Nacherhebung 27.10.2026 (Lückenfüllung): Leere Zellen wurden aus frei abrufbaren Originalberichten nachgetragen, ohne Captcha- oder Bot-Schutz zu umgehen. Quellen: (1) Offenlegungsberichte der Bankwebsites 2021–2025, Tabelle EU CC2 (vollständige HGB-Bilanz inkl. Bilanzgewinn zum Berichtsstichtag), (2) Geschäftsberichte/Jahresabschlüsse (Formblatt 1 und GuV, jeweils auch die Vorjahresspalte), (3) GLEIF-LEI-Register für den Sitz der neuen Hub-Institute. Ein Wert wird nur übernommen, wenn die Zelle leer war und er plausibel zum Bestand passt (Vorjahres-Bilanzsumme 60–160 %, Vorjahres-EK 70–130 % des Berichtsjahres); Quelle je Wert in nacherhebung_2026-10-27.json und in den Anmerkungen. Bei Sparkassen ist der Jahresüberschuss gleich dem Bilanzgewinn (kein Gewinnvortrag; an 11 Sparkassen mit beiden Angaben geprüft), daher ist der Jahresüberschuss dort ggf. aus dem Bilanzgewinn übernommen; für Genossenschaftsbanken gilt das nicht. Kernkapital-Posten neuer Institute stammen aus der Bilanz (CC2). Korrektur: Jahresüberschuss MünchenerHyp 2025/2024 aus dem Geschäftsbericht 2025 (bisher Halbjahreswert). Die Ranglisten von DSGV und BVR für 2021–2024 sind nicht mehr online und konnten nicht genutzt werden.",
    "Fehlende Werte sind mit 'n. v.' (nicht verifiziert) gekennzeichnet und orange hinterlegt. Es wurden keine Werte geschätzt.",
    "Beträge in Mio. € (aus Originalangaben in €, T€ oder Mio. € umgerechnet; Genauigkeit je nach Quelle, siehe Anmerkungen).",
    "Hinweis: Rang bezieht sich auf die Reihenfolge innerhalb der Gruppe nach Bilanzsumme laut dieser Erhebung (Top 40 je Gruppe; Landesbanken vollständig).",
    "Ranglisten-Vorauswahl: DSGV 'Sparkassenrangliste 2025', BVR 'Liste aller Genossenschaftsbanken 2025' (vorläufige Werte); private Banken eigene Zusammenstellung. Wo nur der Ranglistenwert vorlag, steht Quellenart 'Rangliste'.",
    "Abweichende Stichtage/GJ: Spalte 'GJ' (z. B. TARGOBANK, Toyota Kreditbank, mehrere kleinere Privatbanken mit GJ 2024; State Street mit gerundeten Werten 2023). Konzernwerte statt Einzelabschluss sind in den Anmerkungen gekennzeichnet (z. B. Hamburg Commercial Bank, N26, Metzler, National-Bank).",
]
for l in lines:
    me.append([l])
me["A1"].font = Font(bold=True, size=13)
me.column_dimensions["A"].width = 160

au = wb.create_sheet("Auswertung")
def pc(x, d=1):
    return f"{x * 100:.{d}f} %".replace(".", ",")
def short(n):
    for a, b_ in (("Sparkasse ", ""), ("Stadtsparkasse ", ""), ("Kreissparkasse ", "KSK "), ("Volksbank ", "VB "), (" eG", "")):
        n = n.replace(a, b_)
    return n.split(" (")[0]
S40 = {g: summary.get(g + (" alle" if g == "Landesbanken" else " Top 40")) for g, _ in groups}
NAMES = {"Private Banken": "Private", "Genossenschaftsbanken": "Genossenschaftsbanken", "Sparkassen": "Sparkassen", "Landesbanken": "Landesbanken"}
def line(key, order):
    return ", ".join(f"{NAMES[g]} {pc(S40[g][key[0]])} / {pc(S40[g][key[1]])}" for g in order)
by = lambda k: sorted(S40, key=lambda g: -S40[g][k])
full = {g: [b for gg, rolle, b in rows if gg == g and CORE(rolle) and all(b.get(f) is not None for f in ("bilanzsumme", "eigenkapital", "fonds_340g"))] for g, _ in groups}
fge = {g: sorted([b for b in full[g] if b["fonds_340g"] > b["eigenkapital"]], key=lambda b: -(b["fonds_340g"] - b["eigenkapital"]) / b["bilanzsumme"]) for g in full}
def ex(g, k):
    return ", ".join(f"{short(b['name'])} {pc(b['fonds_340g'] / b['bilanzsumme'])} vs. {pc(b['eigenkapital'] / b['bilanzsumme'])}" for b in fge[g][:k])
none_ = [NAMES[g].replace("Private", "privaten Bank").replace("Landesbanken", "Landesbank") for g in ("Private Banken", "Landesbanken") if not fge[g]]
kref = [(i + 1, b) for g in ("Sparkassen",) for i, b in enumerate([b for gg, rolle, b in rows if gg == g and CORE(rolle)]) if "Krefeld" in b["name"]]
lines_au = [
    "Kurzauswertung Top 40 (Basis: Blatt 'Übersicht'; gewichtete Werte und Mediane nur für Banken mit vollständigen Angaben, siehe 'Gruppenauswertung')",
    "",
    "Vollständige Werte (Bilanzsumme, Eigenkapital, Fonds): " + ", ".join(f"{g} {S40[g]['nf']} von {S40[g]['n']}" for g, _ in groups) + ". Nacherhebung vom 24.10.2026 aus den Original-Jahresabschlüssen eingearbeitet.",
    "",
    "1. Bilanzielle EK-Quote (gewichtet / Median): " + line(("ekw", "ekm"), [g for g, _ in groups]) + ".",
    "2. Fonds § 340g in % der Bilanzsumme (gewichtet / Median): " + line(("fw", "fm"), by("fw")) + ".",
    "3. EK-Quote inkl. Fonds (gewichtet / Median): " + line(("tw", "tm"), by("tw")) + ".",
    "4. Anteil des Fonds an (EK + Fonds): " + ", ".join(f"{NAMES[g]} {pc(S40[g]['share'], 0)}" for g in by("share")) + ".",
    f"5. Fonds größer als Eigenkapital: bei {len(fge['Sparkassen'])} von {len(full['Sparkassen'])} Sparkassen mit vollständigen Werten (z. B. {ex('Sparkassen', 3)}), "
    f"{len(fge['Genossenschaftsbanken'])} von {len(full['Genossenschaftsbanken'])} Genossenschaftsbanken (z. B. {ex('Genossenschaftsbanken', 2)})"
    + "".join(f", {len(fge[g])} von {len(full[g])} {NAMES[g]} (z. B. {ex(g, 2)})" for g in ("Landesbanken", "Private Banken") if fge[g])
    + (f"; bei keiner {' und keiner '.join(none_)}." if none_ else "."),
    f"6. Top 10 vs. Top 40 (Median EK-Quote inkl. Fonds): Sparkassen {pc(summary['Sparkassen Top 10']['tm'])} vs. {pc(summary['Sparkassen Top 40']['tm'])}, Genossenschaftsbanken {pc(summary['Genossenschaftsbanken Top 10']['tm'])} vs. {pc(summary['Genossenschaftsbanken Top 40']['tm'])}, Private {pc(summary['Private Banken Top 10']['tm'])} vs. {pc(summary['Private Banken Top 40']['tm'])}.",
    "7. Private Banken sind heterogen: Auto- und Konsumentenbanken (VW Bank, Toyota, Mercedes-Benz, Hyundai, Isbank) zeigen rund 12–22 % EK-Quote; Großbanken und Direktbanken liegen bei 2–4 % (Commerzbank 3,2 %, ING-DiBa 1,8 %, Raisin 0,8 %). Einzelne Privatbanken nutzen den Fonds stark (BMW Bank 5,2 %, TARGOBANK 3,1 %). Die Hamburg Commercial Bank hat ihren Fonds 2025 fast vollständig aufgelöst (777 → 27 Mio. €).",
    "8. Landesbanken: Die DekaBank hält mit 5,4 Mrd. € (6,1 % der Bilanzsumme) einen Fonds, der mehr als fünfmal so groß ist wie ihr bilanzielles Eigenkapital (1,0 Mrd. €); BayernLB 0,8 %, Helaba 0,3 % Fonds-Anteil.",
    "9. CET1-Näherung in % der Bilanzsumme (gewichtet / Median; nur Banken mit vollständigen Kernkapital-Posten, Anzahl in Klammern): "
    + ", ".join(f"{NAMES[g]} {pc(S40[g]['kk']['cw'])} / {pc(S40[g]['kk']['cm'])} ({S40[g]['kk']['n']})" for g in sorted(S40, key=lambda g: -S40[g]['kk']['cw']))
    + ". Mit AT1 (Kernkapital-Näherung, gewichtet): " + ", ".join(f"{NAMES[g]} {pc(S40[g]['kk']['tw'])}" for g in sorted(S40, key=lambda g: -S40[g]['kk']['tw']))
    + ". AT1 als eigener Passivposten haben vor allem Großbanken und Landesbanken (z. B. Deutsche Bank, Commerzbank, ING-DiBa, HVB, Helaba, LBBW, DKB); bei Sparkassen und Genossenschaftsbanken ist der Abstand zwischen CET1 und Kernkapital nahezu null.",
] + ([f"10. Sparkasse Krefeld (Rang {kref[0][0]}): EK-Quote {pc(kref[0][1]['eigenkapital'] / kref[0][1]['bilanzsumme'])}, inkl. Fonds {pc((kref[0][1]['eigenkapital'] + kref[0][1]['fonds_340g']) / kref[0][1]['bilanzsumme'])} (Median Top-40-Sparkassen: {pc(S40['Sparkassen']['tm'])})"
      + ("; Fonds größer als das Eigenkapital." if kref[0][1]['fonds_340g'] > kref[0][1]['eigenkapital'] else ".")] if kref and kref[0][1].get("fonds_340g") is not None else []) + [
    "",
    "Einschränkungen: Bilanzielle Quoten sind keine aufsichtsrechtlichen Kapitalquoten. Bei den privaten Banken ab Rang 11 stammen viele Werte aus Sekundärquellen (Eulerpool, Auszüge aus Bundesanzeiger-Veröffentlichungen) und teils aus dem GJ 2024; bei Sparkassen und Genossenschaftsbanken ist für einige Häuser nur der Ranglistenwert (DSGV/BVR, meist 1–2 % über der HGB-Bilanzsumme) verfügbar. Die Rangfolge kann sich dadurch an den Rändern verschieben. Siehe Spalte 'Quellenart'.",
]
for l in lines_au:
    au.append([l])
au["A1"].font = Font(bold=True, size=12)
au.column_dimensions["A"].width = 170


# ---------- Zeitreihe 2021-2025 ----------
ZR = {norm(i["name"]): i for i in (load("zeitreihe.json") or {"items": []})["items"]}
zs = wb.create_sheet("Zeitreihe 2021-2025")
YEARS = [2021, 2022, 2023, 2024, 2025]
METR = [("Bilanzsumme", "bs"), ("Eigenkapital", "ek"), ("Fonds § 340g", "fonds"), ("Jahresüberschuss", "ju")]
zh = ["Gruppe", "Rolle", "Rang", "Bank", "letztes GJ"]
for mname, _ in METR:
    zh += [f"{mname} {y} (Mio. €)" for y in YEARS] + [f"{mname} Wachstum {y}" for y in YEARS[1:]] + [f"{mname} Ø Wachstum p. a. (CAGR)"]
zh += ["Quelle / Hinweis Zeitreihe"]
zs.append(zh)
for c in range(1, len(zh) + 1):
    cell = zs.cell(1, c)
    cell.font = HDR; cell.fill = HFILL
    cell.alignment = Alignment(wrap_text=True, vertical="top")
zs.row_dimensions[1].height = 62
rk = {}
ZR_ROWS = []
for gname, rolle, b in rows:
    r = zs.max_row + 1
    if rolle == "Zusatz":
        rank = b.get("rank") if gname == "Sparkassen" else None
    elif rolle == "EBA-Hub":
        rank = None
    else:
        rk[gname] = rk.get(gname, 0) + 1
        rank = rk[gname]
    gj = b.get("fiscal_year") or 2025
    z = ZR.get(norm(b["name"])) or {}
    ser = {
        "bs": {gj: mio(b.get("bilanzsumme")), gj - 1: mio(b.get("vj_bilanzsumme"))},
        "ek": {gj: mio(b.get("eigenkapital")), gj - 1: mio(b.get("vj_eigenkapital"))},
        "fonds": {gj: mio(b.get("fonds_340g")), gj - 1: mio(b.get("vj_fonds_340g"))},
        "ju": {},
    }
    for m in ser:
        for y, v in ((z.get("cal") or {}).get(m) or {}).items():
            if v is not None and ser[m].get(int(y)) is None:
                ser[m][int(y)] = v
    ne_note = []
    # Plausibilität gegen den nächstgelegenen schon belegten Wert (BS 50–160 %, EK 65–125 %, Fonds 30–130 %)
    ref0 = {m: {y_: v_ for y_, v_ in ser[m].items() if isinstance(v_, (int, float))} for m in ser}
    def ne_ok(m, y, v):
        rf = ref0.get(m) or {}
        if m == "ju" or not rf or not isinstance(v, (int, float)):
            return True
        yr = min(rf, key=lambda q: abs(q - y)); r0 = rf[yr]
        if not r0 or r0 <= 0:
            return True
        q = v / r0
        return {"bs": 0.5 <= q <= 1.6, "ek": 0.65 <= q <= 1.25, "fonds": 0.3 <= q <= 1.3}[m]
    for y, dd in ((NE.get(b["name"]) or {}).get("jahre") or {}).items():
        if not 2021 <= int(y) <= 2025:
            continue
        for m in ("bs", "ek", "fonds", "ju"):
            if m in dd and ser[m].get(int(y)) is None:
                if m == "fonds" and dd[m]["wert"] == 0 and any(ser["fonds"].get(x) for x in ser["fonds"]):
                    continue
                if not ne_ok(m, int(y), dd[m]["wert"]):
                    continue
                ser[m][int(y)] = dd[m]["wert"]; ne_note.append(f"{m} {y}")
    if gname == "Sparkassen":
        for y in YEARS:
            if ser["ju"].get(y) is None:
                bg = ((NE.get(b["name"]) or {}).get("jahre") or {}).get(str(y), {}).get("bilgew")
                bgv = bg["wert"] if bg else ((KK.get(norm(b["name"])) or {}).get("bilanzgewinn") if y == gj else None)
                if bgv:
                    ser["ju"][y] = bgv; ne_note.append(f"ju {y} = Bilanzgewinn")
    ZR_ROWS.append((r, gname, rolle, b, ser))
    row = [gname, rolle, rank, b["name"], gj]
    for _, m in METR:
        row += [ser[m].get(y) for y in YEARS] + [None] * 5
    note = z.get("note") or ""
    if ne_note:
        note = (note + " | " if note else "") + "Nacherhebung 27.10.2026 (" + ", ".join(ne_note) + ") aus Offenlegungsberichten (EU CC2) und Geschäftsberichten, Quellen in nacherhebung_2026-10-27.json" + ("; bei Sparkassen entspricht der Jahresüberschuss dem Bilanzgewinn (kein Gewinnvortrag, an 11 Sparkassen geprüft)" if any("Bilanzgewinn" in x for x in ne_note) else "")
    row += [(z.get("src") or "") + ((" | " + note) if note else "")]
    zs.append(row)
    for mi, (_, m) in enumerate(METR):
        base = 6 + mi * 10
        for k in range(5):
            cell = zs.cell(r, base + k)
            cell.number_format = '#,##0.0'
            if cell.value is None:
                cell.value = "n. v."; cell.fill = MISS
                cell.alignment = Alignment(horizontal="right")
        for k in range(1, 5):
            a, p_ = get_column_letter(base + k), get_column_letter(base + k - 1)
            c = zs.cell(r, base + 4 + k)
            c.value = f'=IF(AND(ISNUMBER({a}{r}),ISNUMBER({p_}{r})),IF({p_}{r}>0,{a}{r}/{p_}{r}-1,"n. v."),"n. v.")'
            c.number_format = '0.0%'
            c.alignment = Alignment(horizontal="right")
        f_, l_ = get_column_letter(base), get_column_letter(base + 4)
        c = zs.cell(r, base + 9)
        c.value = f'=IF(AND(ISNUMBER({f_}{r}),ISNUMBER({l_}{r})),IF(AND({f_}{r}>0,{l_}{r}>0),({l_}{r}/{f_}{r})^(1/4)-1,"n. v."),"n. v.")'
        c.number_format = '0.0%'
        c.alignment = Alignment(horizontal="right")
    if rolle == "Zusatz":
        for c in range(1, 6):
            zs.cell(r, c).fill = SEC
    elif rolle == "EBA-Hub":
        for c in range(1, 6):
            zs.cell(r, c).fill = HUBF
zs.freeze_panes = "F2"
zs.column_dimensions["D"].width = 46
for c in range(6, len(zh)):
    zs.column_dimensions[get_column_letter(c)].width = 12
zs.column_dimensions[get_column_letter(len(zh))].width = 70
zs.auto_filter.ref = f"A1:{get_column_letter(len(zh))}{zs.max_row}"


# ---------- Entwicklung ab 2022 ----------
en = wb.create_sheet("Entwicklung ab 2022")
eh = ["Gruppe", "Bank", "Bilanzsumme 2022", "EK 2022", "EK 2025", "EK Δ Mio.", "EK Δ %", "Fonds 2022", "Fonds 2025", "Fonds Δ Mio.", "Fonds Δ %",
      "EK + Fonds 2022 (Kernkapital-Basis)", "EK + Fonds 2025", "EK + Fonds Δ Mio.", "EK + Fonds Δ %", "EK + Fonds Ø p. a.",
      "Bilanzsumme Δ %", "EK + Fonds in % BS 2022", "EK + Fonds in % BS 2025", "CET1-Näherung 2025 (Mio.)", "Anmerkung"]
en.append(eh)
for c in range(1, len(eh) + 1):
    cell = en.cell(1, c); cell.font = HDR; cell.fill = HFILL
    cell.alignment = Alignment(wrap_text=True, vertical="top")
en.row_dimensions[1].height = 60
only_fonds = []
def zc(m, y):
    base = {"bs": 6, "ek": 16, "fonds": 26, "ju": 36}[m]
    return get_column_letter(base + (y - 2021))
Z = "'Zeitreihe 2021-2025'!"
for r, gname, rolle, b, ser in ZR_ROWS:
    gj = b.get("fiscal_year") or 2025
    if gj != 2025:
        continue
    ek22, ek25 = ser["ek"].get(2022), ser["ek"].get(2025)
    f22, f25 = ser["fonds"].get(2022), ser["fonds"].get(2025)
    bs22, bs25 = ser["bs"].get(2022), ser["bs"].get(2025)
    if None not in (ek22, ek25, f22, f25):
        rr = en.max_row + 1
        en.append([gname, b["name"]] + [None] * 18 + [None])
        ref = lambda m, y: f"{Z}{zc(m, y)}{r}"
        f = {3: f"={ref('bs', 2022)}", 4: f"={ref('ek', 2022)}", 5: f"={ref('ek', 2025)}", 6: f"=E{rr}-D{rr}", 7: f"=IF(D{rr}>0,E{rr}/D{rr}-1,\"n. v.\")",
             8: f"={ref('fonds', 2022)}", 9: f"={ref('fonds', 2025)}", 10: f"=I{rr}-H{rr}", 11: f"=IF(H{rr}>0,I{rr}/H{rr}-1,\"n. v.\")",
             12: f"=D{rr}+H{rr}", 13: f"=E{rr}+I{rr}", 14: f"=M{rr}-L{rr}", 15: f"=IF(L{rr}>0,M{rr}/L{rr}-1,\"n. v.\")",
             16: f"=IF(L{rr}>0,(M{rr}/L{rr})^(1/3)-1,\"n. v.\")", 17: f"=IF(AND(ISNUMBER({ref('bs', 2022)}),{ref('bs', 2022)}>0),{ref('bs', 2025)}/{ref('bs', 2022)}-1,\"n. v.\")",
             18: f"=IF(AND(ISNUMBER(C{rr}),C{rr}>0),L{rr}/C{rr},\"n. v.\")", 19: f"=IF(ISNUMBER({ref('bs', 2025)}),M{rr}/{ref('bs', 2025)},\"n. v.\")"}
        for c, v in f.items():
            en.cell(rr, c).value = v
        en.cell(rr, 20).value = b.get("_cet1") if b.get("_cet1") is not None else "n. v."
        for c in (3, 4, 5, 6, 8, 9, 10, 12, 13, 14, 20):
            en.cell(rr, c).number_format = '#,##0.0'
        for c in (7, 11, 15, 16, 17, 18, 19):
            en.cell(rr, c).number_format = '0.0%'
    elif f22 is not None and f25 is not None:
        only_fonds.append((gname, b["name"], f22, f25, bs22, bs25))
en.freeze_panes = "C2"
en.column_dimensions["B"].width = 44
for c in range(3, len(eh)):
    en.column_dimensions[get_column_letter(c)].width = 13
en.auto_filter.ref = f"A1:{get_column_letter(len(eh))}{en.max_row}"
n0 = en.max_row + 2
en.cell(n0, 1).value = "Nur Fonds § 340g ab 2022 vorhanden (Eigenkapital 2022 fehlt):"
en.cell(n0, 1).font = Font(bold=True)
for k, h in enumerate(["Gruppe", "Bank", "Fonds 2022", "Fonds 2025", "Fonds Δ Mio.", "Fonds Δ %", "Bilanzsumme 2022", "Bilanzsumme 2025"]):
    c = en.cell(n0 + 1, 1 + k); c.value = h; c.font = HDR; c.fill = HFILL
rr = n0 + 2
for gname_, n_, a_, c_, bs22_, bs25_ in only_fonds:
    en.cell(rr, 1).value = gname_; en.cell(rr, 2).value = n_
    en.cell(rr, 3).value = a_; en.cell(rr, 4).value = c_
    en.cell(rr, 5).value = f"=D{rr}-C{rr}"; en.cell(rr, 6).value = f'=IF(C{rr}>0,D{rr}/C{rr}-1,"n. v.")'
    en.cell(rr, 7).value = bs22_ if bs22_ is not None else "n. v."; en.cell(rr, 8).value = bs25_ if bs25_ is not None else "n. v."
    for c in (3, 4, 5, 7, 8): en.cell(rr, c).number_format = '#,##0.0'
    en.cell(rr, 6).number_format = '0.0%'
    rr += 1
n0 = rr - 1
en.cell(n0 + 1, 1).value = "Hinweis: 'Kernkapital-Basis' = Eigenkapital + Fonds § 340g (Bilanzposten). Die vollständige CET1-Näherung (abzüglich Bilanzgewinn, immaterielle Werte, aktive latente Steuern) liegt nur für 2025 vor, weil diese Posten für ältere Jahre nicht erhoben wurden."
# ---------- Offenlegung 31.12.2025 (EU KM1) ----------
OL = {norm(i["name"]): i for i in (load("offenlegung_2025.json") or {"items": []})["items"]}
def hub_ol(h, ebene):
    k = h.get("km1")
    if not k or k.get("cet1") is None:
        return None
    st = h.get("km1_stichtag") or "2025-12-31"
    hint = "EBA-Hub-Eintrag: " + h["hub_name"] + (f"; {h['km1_hinweis']}" if h.get("km1_hinweis") else "")
    return {"name": h["name"], "ebene": ebene, "stichtag": st, "cet1": k.get("cet1"), "t1": k.get("t1"), "tc": k.get("tc"), "rwa": k.get("rwa"),
            "cet1_q": k.get("cet1_q"), "t1_q": k.get("t1_q"), "tc_q": k.get("tc_q"), "gesamt_anf": k.get("gesamt_anf"),
            "lr_exp": k.get("lr_exp"), "lr": k.get("lr"),
            "quelle": f"EBA Pillar-3-Datenhub, Data Points Report, Template EU KM1, Stichtag {st[8:10]}.{st[5:7]}.{st[:4]}, Filter Country = Germany (Export 27.10.2026, Datei eba_hub_km1_de_alle_stichtage.xlsx)",
            "hinweis": hint}
for h in HN["neu"]:
    x = hub_ol(h, h["ebene"])
    if x:
        OL[norm(h["name"])] = x
for h in HN["bestehend"]:
    if norm(h["name"]) not in OL:
        x = hub_ol(h, f"laut EBA-Hub: {h['hub_name']} (höchste Ebene im EWR, ggf. Gruppe)")
        if x:
            OL[norm(h["name"])] = x
ol = wb.create_sheet("Offenlegung 31.12.2025")
oh = ["Gruppe", "Rolle", "Bank", "Ebene des Berichts", "Bilanzsumme HGB (Mio. €)", "Hartes Kernkapital CET1 (Mio. €)", "Kernkapital T1 (Mio. €)",
      "Gesamtkapital (Mio. €)", "Gesamtrisikobetrag RWA (Mio. €)", "CET1-Quote", "Kernkapitalquote", "Gesamtkapitalquote",
      "Gesamtkapitalanforderung inkl. Puffer (EU 11a)", "Gesamtkapitalquote über Anforderung (Pp.)", "Verschuldungsquote (Leverage Ratio)", "Gesamtrisikopositionsmessgröße LR (Mio. €)",
      "AT1 = T1 − CET1 (Mio. €)", "Ergänzungskapital T2 = Gesamt − T1 (Mio. €)", "RWA-Dichte (RWA / Bilanzsumme)", "CET1 in % Bilanzsumme", "CET1-Näherung (bilanziell) in % BS", "Quelle", "Hinweis"]
ol.append(oh)
for c in range(1, len(oh) + 1):
    cell = ol.cell(1, c); cell.font = HDR; cell.fill = HFILL
    cell.alignment = Alignment(wrap_text=True, vertical="top")
ol.row_dimensions[1].height = 62
OL_ROWS = []
for gname, rolle, b in rows:
    i = OL.get(norm(b["name"]))
    r = ol.max_row + 1
    bs = mio(b.get("bilanzsumme"))
    row = [gname, rolle, b["name"], i["ebene"] if i else None, bs]
    if i:
        row += [i["cet1"], i["t1"], i["tc"], i["rwa"], i["cet1_q"], i["t1_q"], i["tc_q"], i.get("gesamt_anf"), None, i.get("lr"), i.get("lr_exp"), None, None, None, None,
                b.get("_cet1") / bs if b.get("_cet1") is not None and bs else None, i["quelle"], i.get("hinweis")]
    else:
        row += [None] * 15 + [b.get("_cet1") / bs if b.get("_cet1") is not None and bs else None, None, "weder auf der Website noch im EBA-Datenhub (Stand 26.10.2026) ein KM1 zum 31.12.2025 gefunden"]
    ol.append(row)
    OL_ROWS.append((r, gname, bool(i), i))
    if i:
        if i.get("gesamt_anf") is not None:
            ol.cell(r, 14).value = f"=(L{r}-M{r})*100"
        ol.cell(r, 17).value = f"=G{r}-F{r}"
        ol.cell(r, 18).value = f"=H{r}-G{r}"
        if bs:
            ol.cell(r, 19).value = f"=I{r}/E{r}"
            ol.cell(r, 20).value = f"=F{r}/E{r}"
    for c in (5, 6, 7, 8, 9, 16, 17, 18):
        ol.cell(r, c).number_format = '#,##0.0'
    for c in (10, 11, 12, 13, 15, 19, 20, 21):
        ol.cell(r, c).number_format = '0.0%'
    ol.cell(r, 14).number_format = '0.0'
    for c in range(4, 22):
        if ol.cell(r, c).value is None:
            ol.cell(r, c).value = "n. v."; ol.cell(r, c).fill = MISS
            ol.cell(r, c).alignment = Alignment(horizontal="right")
    if rolle == "Zusatz":
        for c in range(1, 4):
            ol.cell(r, c).fill = SEC
    elif rolle == "EBA-Hub":
        for c in range(1, 4):
            ol.cell(r, c).fill = HUBF
    OL_ROWS[-1] = OL_ROWS[-1] + (rolle,)
ol.freeze_panes = "D2"
ol.column_dimensions["C"].width = 44
ol.column_dimensions["D"].width = 22
for c in range(5, 22):
    ol.column_dimensions[get_column_letter(c)].width = 13
ol.column_dimensions["V"].width = 60
ol.column_dimensions["W"].width = 40
ol.auto_filter.ref = f"A1:{get_column_letter(len(oh))}{ol.max_row}"
# Gruppenübersicht (Median, nur Banken mit Bericht; RWA-Dichte nur Einzelinstitute)
g0 = ol.max_row + 2
ol.cell(g0, 1).value = "Gruppenübersicht (Median der Banken mit KM1-Werten zum 31.12.2025; Werte als Formeln)"
ol.cell(g0, 1).font = Font(bold=True)
gh = ["Gruppe", "Banken mit Bericht", "CET1-Quote (Median)", "Gesamtkapitalquote (Median)", "Leverage Ratio (Median)", "RWA-Dichte (Median, nur Einzelinstitute)", "CET1 in % BS (Median)", "CET1-Näherung bilanziell in % BS (Median, dieselben Banken)"]
for k, h in enumerate(gh):
    c = ol.cell(g0 + 1, 1 + k); c.value = h; c.font = HDR; c.fill = HFILL; c.alignment = Alignment(wrap_text=True, vertical="top")
ol.row_dimensions[g0 + 1].height = 48
MED_VARIANTS = [("bisherige Auswahl", lambda ro: ro != "EBA-Hub"), ("alle inkl. EBA-Hub-Ergänzung", lambda ro: True)]
GROUPS5 = ["Sparkassen", "Genossenschaftsbanken", "Landesbanken", "Private Banken", EXTRA_GROUP]
for n_, (vn, vf, g) in enumerate([(vn, vf, g) for vn, vf in MED_VARIANTS for g in GROUPS5]):
    rr = g0 + 2 + n_
    rs = [r for r, gn, ok, i, ro in OL_ROWS if gn == g and ok and vf(ro)]
    re_ = [r for r, gn, ok, i, ro in OL_ROWS if gn == g and ok and vf(ro) and i["ebene"] == "Einzelinstitut"]
    if g == EXTRA_GROUP and vn == "bisherige Auswahl":
        continue
    ol.cell(rr, 1).value = f"{g} – {vn}"
    ol.cell(rr, 2).value = len(rs)
    def med(col, rr_list):
        return '=IFERROR(MEDIAN(' + ",".join(f"{col}{x}" for x in rr_list) + '),"n. v.")' if rr_list else "n. v."
    ol.cell(rr, 3).value = med("J", rs); ol.cell(rr, 4).value = med("L", rs); ol.cell(rr, 5).value = med("O", rs)
    ol.cell(rr, 6).value = med("S", re_); ol.cell(rr, 7).value = med("T", rs)
    rn = [x for x in rs if isinstance(ol.cell(x, 21).value, float)]
    ol.cell(rr, 8).value = med("U", rn)
    for c in range(3, 9):
        ol.cell(rr, c).number_format = '0.0%'
ol.cell(g0 + 2 + 2 * len(GROUPS5), 1).value = ("Quelle: EU KM1 nach CRR zum 31.12.2025, aus den Offenlegungsberichten auf den Websites der Institute und aus dem Pillar-3-Datenhub der EBA (Data Points Report, Export 26.10.2026, Rohdatei eba_hub_km1_20251231.xlsx; Quelle je Zeile). "
                            "Wo beide vorlagen, stimmten die Werte überein. 'n. v.' = weder auf der Website noch im Hub gefunden (meist kleine, nicht komplexe Institute oder Töchter ausländischer Gruppen). "
                            "'Ebene des Berichts' zeigt, ob der Bericht das Einzelinstitut oder eine Gruppe abdeckt; bei Gruppen ist die RWA-Dichte gegen die HGB-Bilanzsumme des Einzelinstituts nur ein Richtwert. "
                            "Rolle 'EBA-Hub' (grün): am 27.10.2026 ergänzte Institute, die im Hub mit Land Deutschland geführt werden; ihre Bilanzsumme stammt aus EU CC2 im Hub. "
                            "Die Gruppenübersicht zeigt die Mediane für die bisherige Auswahl (Top 40, Landesbanken, Zusatzeinträge) und für alle Banken einschließlich der Hub-Ergänzung (darin auch Bausparkassen, Holdings und EU-Töchter ausländischer Banken).")
# Eigenmittel (CC1) und RWA-Aufteilung (OV1) aus dem EBA-Datenhub
HUB = load("eba_cc1_ov1_2025.json") or {"cc1": {}, "ov1": {}}
HCC = {norm(k): v for k, v in HUB["cc1"].items()}
HOV = {norm(k): v for k, v in HUB["ov1"].items()}
for h in HN["neu"] + HN["bestehend"]:
    for D_, key in ((HCC, "cc1"), (HOV, "ov1")):
        if h.get(key) and norm(h["name"]) not in D_:
            D_[norm(h["name"])] = h[key]
GROUPS4 = GROUPS5


def hub_sheet(title, cols, fill_row, ratios, footnote, median_title):
    """cols: [(Header, key|callable, fmt)], ratios: [(Header, formula-template mit {r} und Spaltenbuchstaben, nur_einzel)]"""
    ws = wb.create_sheet(title)
    head = ["Gruppe", "Rolle", "Bank", "Ebene / Eintrag im EBA-Hub"] + [c[0] for c in cols] + [x[0] for x in ratios] + ["Hinweis"]
    ws.append(head)
    for c in range(1, len(head) + 1):
        cell = ws.cell(1, c); cell.font = HDR; cell.fill = HFILL
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[1].height = 75
    L = {(c[1] if isinstance(c[1], str) else c[3]): get_column_letter(5 + k) for k, c in enumerate(cols)}
    r0 = 5 + len(cols)
    out = []
    for gname, rolle, b in rows:
        r = ws.max_row + 1
        d, hint = fill_row(b)
        oli = OL.get(norm(b["name"]))
        ebene = oli["ebene"] if (oli and d) else ((b.get("_hub") or {}).get("ebene") if d else None)
        vals = []
        for h, key, fmt, *_ in cols:
            v = key(b, d) if callable(key) else (d.get(key) if d else None)
            vals.append(v)
        ws.append([gname, rolle, b["name"], ebene] + vals + [None] * len(ratios) + [hint])
        if d:
            for k, (h, f, _) in enumerate(ratios):
                ws.cell(r, r0 + k).value = "=" + f.format(r=r, **L)
        for k, (h, key, fmt, *_) in enumerate(cols):
            ws.cell(r, 5 + k).number_format = fmt
        for k in range(len(ratios)):
            ws.cell(r, r0 + k).number_format = '0.0%'
        for c in range(4, r0 + len(ratios)):
            if ws.cell(r, c).value is None:
                ws.cell(r, c).value = "n. v."; ws.cell(r, c).fill = MISS
                ws.cell(r, c).alignment = Alignment(horizontal="right")
        if rolle == "Zusatz":
            for c in range(1, 4):
                ws.cell(r, c).fill = SEC
        elif rolle == "EBA-Hub":
            for c in range(1, 4):
                ws.cell(r, c).fill = HUBF
        out.append((r, gname, bool(d), ebene == "Einzelinstitut", rolle))
    ws.freeze_panes = "D2"
    ws.column_dimensions["C"].width = 44; ws.column_dimensions["D"].width = 30
    for c in range(5, r0 + len(ratios)):
        ws.column_dimensions[get_column_letter(c)].width = 13
    ws.column_dimensions[get_column_letter(r0 + len(ratios))].width = 50
    ws.auto_filter.ref = f"A1:{get_column_letter(len(head))}{ws.max_row}"
    g0 = ws.max_row + 2
    ws.cell(g0, 1).value = median_title; ws.cell(g0, 1).font = Font(bold=True)
    gh = ["Gruppe", "Banken mit Daten"] + [x[0] + " (Median)" for x in ratios]
    for k, h in enumerate(gh):
        c = ws.cell(g0 + 1, 1 + k); c.value = h; c.font = HDR; c.fill = HFILL; c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[g0 + 1].height = 75
    for n_, (vn, vf, g) in enumerate([(vn, vf, g) for vn, vf in MED_VARIANTS for g in GROUPS5]):
        rr = g0 + 2 + n_
        if g == EXTRA_GROUP and vn == "bisherige Auswahl":
            continue
        rs = [r for r, gn, ok, ei, ro in out if gn == g and ok and vf(ro)]
        ws.cell(rr, 1).value = f"{g} – {vn}"; ws.cell(rr, 2).value = len(rs)
        for k, (h, f, only_einzel) in enumerate(ratios):
            sel = [r for r, gn, ok, ei, ro in out if gn == g and ok and vf(ro) and (ei or not only_einzel)]
            col = get_column_letter(r0 + k)
            c = ws.cell(rr, 3 + k)
            c.value = '=IFERROR(MEDIAN(' + ",".join(f"{col}{x}" for x in sel) + '),"n. v.")' if sel else "n. v."
            c.number_format = '0.0%'
    ws.cell(g0 + 2 + 2 * len(GROUPS5), 1).value = footnote + (" Rolle 'EBA-Hub' (grün): am 27.10.2026 ergänzte Institute mit Land Deutschland im Hub; Mediane für die bisherige Auswahl und für alle Banken inkl. Ergänzung.")
    return ws


def cc1_row(b):
    d = HCC.get(norm(b["name"]))
    if not d:
        return None, "nicht im EBA-Hub (CC1 zum 31.12.2025)"
    d = dict(d)
    hint = "EBA-Hub: " + d["hub_name"]
    if d.get("cet1") is None and d.get("cet1_vor_abzuegen") is not None:
        d["cet1"] = round(d["cet1_vor_abzuegen"] + (d.get("abzuege_cet1") or 0), 1)
        hint += "; CET1 (Zeile 29) fehlt, berechnet als Zeile 6 + Zeile 28"
    if d.get("rwa") is None:
        oli = OL.get(norm(b["name"]))
        if oli and oli.get("rwa"):
            d["rwa"] = oli["rwa"]; hint += "; RWA aus KM1"
    return d, hint


hub_sheet(
    "Eigenmittel CC1",
    [("Kapitalinstrumente inkl. Agio / Geschäftsguthaben (Mio. €)", "instrumente", '#,##0.0'),
     ("Gewinnrücklagen (Mio. €)", "gewinnruecklagen", '#,##0.0'),
     ("Kumuliertes sonstiges Ergebnis u. a. Rücklagen (Mio. €)", "kum_ergebnis", '#,##0.0'),
     ("Fonds für allgemeine Bankrisiken, aufsichtlich (EU-3a, Mio. €)", "fonds_340g", '#,##0.0'),
     ("Fonds § 340g laut HGB-Bilanz 31.12.2025 (Mio. €)", lambda b, d: mio(b.get("fonds_340g")) if d else None, '#,##0.0', "fonds_hgb"),
     ("CET1 vor Abzügen (Mio. €)", "cet1_vor_abzuegen", '#,##0.0'),
     ("Abzüge vom CET1 gesamt (Mio. €, negativ)", "abzuege_cet1", '#,##0.0'),
     ("Hartes Kernkapital CET1 (Mio. €)", "cet1", '#,##0.0'),
     ("Zusätzliches Kernkapital AT1 (Mio. €)", "at1", '#,##0.0'),
     ("T2-Instrumente / Nachrang (Mio. €)", "t2_instrumente", '#,##0.0'),
     ("Kreditrisikoanpassungen im T2 (Zeile 50, v. a. § 340f, Mio. €)", "kreditrisikoanpassungen", '#,##0.0'),
     ("Ergänzungskapital T2 (Mio. €)", "t2", '#,##0.0'),
     ("Eigenmittel gesamt (Mio. €)", "eigenmittel", '#,##0.0'),
     ("RWA (Mio. €)", "rwa", '#,##0.0')],
    lambda b: cc1_row(b),
    [("Fonds § 340g in % CET1", 'IF(N({cet1}{r})>0,N({fonds_340g}{r})/{cet1}{r},"n. v.")', False),
     ("Kapitalinstrumente in % CET1", 'IF(N({cet1}{r})>0,N({instrumente}{r})/{cet1}{r},"n. v.")', False),
     ("Gewinnrücklagen in % CET1", 'IF(N({cet1}{r})>0,N({gewinnruecklagen}{r})/{cet1}{r},"n. v.")', False),
     ("Abzüge in % CET1 vor Abzügen", 'IF(N({cet1_vor_abzuegen}{r})>0,-N({abzuege_cet1}{r})/{cet1_vor_abzuegen}{r},"n. v.")', False),
     ("AT1 in % RWA", 'IF(N({rwa}{r})>0,N({at1}{r})/{rwa}{r},"n. v.")', False),
     ("T2 in % RWA", 'IF(N({rwa}{r})>0,N({t2}{r})/{rwa}{r},"n. v.")', False),
     ("Kreditrisikoanpassungen (§ 340f) in % RWA", 'IF(N({rwa}{r})>0,N({kreditrisikoanpassungen}{r})/{rwa}{r},"n. v.")', False),
     ("Kreditrisikoanpassungen in % T2", 'IF(N({t2}{r})>0,N({kreditrisikoanpassungen}{r})/{t2}{r},"n. v.")', False),
     ("Fonds HGB über aufsichtlichem Fonds, in % HGB-Fonds (nur Einzelinstitute)", 'IF(AND(ISNUMBER({fonds_hgb}{r}),N({fonds_hgb}{r})>0,$D{r}="Einzelinstitut"),({fonds_hgb}{r}-N({fonds_340g}{r}))/{fonds_hgb}{r},"n. v.")', True)],
    "Quelle: Tabelle EU CC1 (Zusammensetzung der aufsichtsrechtlichen Eigenmittel) zum 31.12.2025 aus dem Pillar-3-Datenhub der EBA (Data Points Report, Spalte a, Export über die Weboberfläche am 26.10.2026; Rohdatei eba_hub_cc1_20251231.csv). "
    "Der Hub zeigt die höchste Konsolidierungsebene im EWR; Konzerne melden nach IFRS und weisen dort keinen Fonds § 340g (EU-3a) aus. Kreditrisikoanpassungen (Zeile 50) enthalten bei HGB-Instituten vor allem die Vorsorgereserven nach § 340f und Pauschalwertberichtigungen. "
    "Die letzte Kennzahl vergleicht den Fonds laut HGB-Bilanz mit dem aufsichtlich angerechneten Fonds; die Differenz ist meist die Zuführung 2025, die erst nach Feststellung des Jahresabschlusses zum CET1 zählt.",
    "Gruppenübersicht CC1 (Median der Banken mit CC1-Daten; Werte als Formeln)")


def ov1_row(b):
    d = HOV.get(norm(b["name"]))
    if not d:
        return None, "nicht im EBA-Hub (OV1 zum 31.12.2025)"
    d = dict(d); hint = "EBA-Hub: " + d["hub_name"]
    oli = OL.get(norm(b["name"]))
    if oli and oli.get("rwa") and d.get("gesamt") and abs(d["gesamt"] - oli["rwa"]) > 1:
        hint += f"; OV1-Gesamt weicht von KM1-RWA ({oli['rwa']:,.1f}) ab"
    return d, hint


hub_sheet(
    "RWA-Aufteilung OV1",
    [("Bilanzsumme HGB (Mio. €)", lambda b, d: mio(b.get("bilanzsumme")) if d else None, '#,##0.0', "bs"),
     ("Kreditrisiko ohne CCR (Mio. €)", "kreditrisiko", '#,##0.0'),
     ("Gegenparteiausfallrisiko CCR (Mio. €)", "gegenparteirisiko", '#,##0.0'),
     ("CVA-Risiko (Mio. €)", "cva", '#,##0.0'),
     ("Verbriefungen im Anlagebuch (Mio. €)", "verbriefung", '#,##0.0'),
     ("Marktrisiko (Mio. €)", "marktrisiko", '#,##0.0'),
     ("Großkredite (Mio. €)", "grosskredite", '#,##0.0'),
     ("Operationelles Risiko (Mio. €)", "oprisk", '#,##0.0'),
     ("Aufschlag Output Floor nach Übergang (Mio. €)", "floor_aufschlag", '#,##0.0'),
     ("RWA gesamt (Mio. €)", "gesamt", '#,##0.0'),
     ("Output Floor angewandt (Anteil)", "output_floor_pct", '0.0%')],
    lambda b: ov1_row(b),
    [("Kreditrisiko in % RWA", 'IF(N({gesamt}{r})>0,N({kreditrisiko}{r})/{gesamt}{r},"n. v.")', False),
     ("Markt-, CCR- und CVA-Risiko in % RWA", 'IF(N({gesamt}{r})>0,(N({gegenparteirisiko}{r})+N({cva}{r})+N({marktrisiko}{r}))/{gesamt}{r},"n. v.")', False),
     ("Verbriefungen in % RWA", 'IF(N({gesamt}{r})>0,N({verbriefung}{r})/{gesamt}{r},"n. v.")', False),
     ("Operationelles Risiko in % RWA", 'IF(N({gesamt}{r})>0,N({oprisk}{r})/{gesamt}{r},"n. v.")', False),
     ("Output-Floor-Aufschlag in % RWA", 'IF(N({gesamt}{r})>0,N({floor_aufschlag}{r})/{gesamt}{r},"n. v.")', False),
     ("Kreditrisiko-RWA in % Bilanzsumme (nur Einzelinstitute)", 'IF(AND(N({bs}{r})>0,$D{r}="Einzelinstitut"),N({kreditrisiko}{r})/{bs}{r},"n. v.")', True)],
    "Quelle: Tabelle EU OV1 (Übersicht über die Gesamtrisikobeträge) zum 31.12.2025 aus dem Pillar-3-Datenhub der EBA (Data Points Report, Spalte a = RWA zum Stichtag, Export über die Weboberfläche am 26.10.2026; Rohdatei eba_hub_ov1_20251231.csv). "
    "Der Hub zeigt die höchste Konsolidierungsebene im EWR; bei Gruppen ist der Bezug auf die HGB-Bilanzsumme des Einzelinstituts nicht sinnvoll und bleibt leer. In wenigen Fällen weicht die OV1-Summe leicht vom RWA-Wert in KM1 ab (Hinweisspalte).",
    "Gruppenübersicht OV1 (Median der Banken mit OV1-Daten; Werte als Formeln)")


# ---------- Bilanzen 31.12.2025 (Formblatt 1 RechKredV, Mio. €) ----------
BIL = {norm(k): v for k, v in (load("bilanzen_2025.json") or {}).items()}
BIL_HUB = set()
for h in HN["neu"] + HN["bestehend"]:
    c2 = h.get("cc2") or {}
    if c2.get("fuer_bilanzblatt") and norm(h["name"]) not in BIL:
        pa = dict(c2["passiva"])
        BIL[norm(h["name"])] = {"aktiva": c2["aktiva"], "passiva": pa, "page": None,
                                "source_url": "EBA-Pillar-3-Datenhub, EU CC2 Spalte a (Bilanz laut Jahresabschluss), Hub-Eintrag " + h["hub_name"],
                                "note": "; ".join(c2.get("notes") or [])}
        BIL_HUB.add(norm(h["name"]))
for n_, e in NE.items():
    bl = e.get("bilanz2025")
    if bl and norm(n_) not in BIL:
        pa = dict(bl["passiva"]); pa["ek"] = bl["ek"]
        BIL[norm(n_)] = {"aktiva": bl["aktiva"], "passiva": pa, "page": None, "source_url": bl["src"]["url"],
                         "note": "Nacherhebung 27.10.2026: " + bl["src"]["doc"]}
AKT = [("barreserve", "1. Barreserve"), ("schuldtitel_oeff", "2. Schuldtitel öffentlicher Stellen und Wechsel"),
       ("ford_ki", "3. Forderungen an Kreditinstitute"), ("ford_kunden", "4. Forderungen an Kunden"),
       ("schuldverschr", "5. Schuldverschreibungen und andere festverzinsliche Wertpapiere"),
       ("aktien", "6. Aktien und andere nicht festverzinsliche Wertpapiere"), ("handel_a", "6a. Handelsbestand"),
       ("beteiligungen", "7. Beteiligungen"), ("verb_unt", "8. Anteile an verbundenen Unternehmen"),
       ("treuhand_a", "9. Treuhandvermögen"), ("ausgleich", "10. Ausgleichsforderungen gegen die öffentliche Hand"),
       ("leasing", "Leasingvermögen"), ("immat", "11. Immaterielle Anlagewerte"), ("sachanlagen", "12. Sachanlagen"),
       ("ausst_einl", "13. Ausstehende Einlagen auf das gezeichnete Kapital"), ("sonst_vg", "14. Sonstige Vermögensgegenstände"),
       ("rap_a", "15. Rechnungsabgrenzungsposten (Aktiva)"), ("akt_lat", "16. Aktive latente Steuern"),
       ("aktiv_ub", "17. Aktiver Unterschiedsbetrag aus der Vermögensverrechnung"), ("fehlbetrag", "Nicht durch Eigenkapital gedeckter Fehlbetrag")]
PAS = [("verb_ki", "1. Verbindlichkeiten gegenüber Kreditinstituten"), ("verb_kunden", "2. Verbindlichkeiten gegenüber Kunden"),
       ("verbrieft", "3. Verbriefte Verbindlichkeiten"), ("handel_p", "3a. Handelsbestand"), ("treuhand_p", "4. Treuhandverbindlichkeiten"),
       ("sonst_verb", "5. Sonstige Verbindlichkeiten"), ("rap_p", "6. Rechnungsabgrenzungsposten (Passiva)"),
       ("pas_lat", "6a. Passive latente Steuern"), ("rueckst", "7. Rückstellungen"),
       ("sonderposten", "Sonderposten / Fonds zur bauspartechnischen Absicherung"), ("nachrang", "9. Nachrangige Verbindlichkeiten"),
       ("genuss", "10. Genussrechtskapital"), ("at1", "Instrumente des zusätzlichen aufsichtsrechtlichen Kernkapitals"),
       ("fonds", "11. Fonds für allgemeine Bankrisiken"), ("ek", "12. Eigenkapital")]
used = {k for v in BIL.values() for k in list(v["aktiva"]) + list(v["passiva"])}
AKT = [x for x in AKT if x[0] in used]; PAS = [x for x in PAS if x[0] in used]
wsb = wb.create_sheet("Bilanzen 31.12.2025")
hb = ["Gruppe", "Rolle", "Bank"] + [h for _, h in AKT] + ["Summe der Aktiva"] + [h for _, h in PAS] + ["Summe der Passiva",
      "Bilanzsumme laut Übersicht", "Prüfung: Aktiva − Passiva", "Prüfung: Aktiva − Bilanzsumme Übersicht", "Quelle / Hinweis"]
wsb.append(hb)
for c in range(1, len(hb) + 1):
    cell = wsb.cell(1, c); cell.font = HDR; cell.fill = HFILL
    cell.alignment = Alignment(wrap_text=True, vertical="top")
wsb.row_dimensions[1].height = 90
cA0 = 4; cSA = cA0 + len(AKT); cP0 = cSA + 1; cSP = cP0 + len(PAS); cBS = cSP + 1; cC1 = cBS + 1; cC2 = cBS + 2; cH = cBS + 3
L_ = get_column_letter
bil_rows = []
for gname, rolle, b in rows:
    r = wsb.max_row + 1
    d = BIL.get(norm(b["name"]))
    vals = [gname, rolle, b["name"]]
    if d:
        vals += [d["aktiva"].get(k, 0) for k, _ in AKT] + [f"=SUM({L_(cA0)}{r}:{L_(cSA - 1)}{r})"]
        vals += [d["passiva"].get(k, 0) for k, _ in PAS] + [f"=SUM({L_(cP0)}{r}:{L_(cSP - 1)}{r})"]
        vals += [mio(b.get("bilanzsumme")), f"={L_(cSA)}{r}-{L_(cSP)}{r}", f"=IF(ISNUMBER({L_(cBS)}{r}),{L_(cSA)}{r}-{L_(cBS)}{r},\"n. v.\")"]
        pg = f", S. {d['page']}" if d.get("page") is not None else ""
        vals += [d["source_url"] + pg + ("; " + d["note"] if d.get("note") else "")]
    else:
        vals += [None] * (cC2 - 3) + ["keine vollständige HGB-Bilanz frei verfügbar (Abschluss nur im Unternehmensregister, nur verkürzte Bilanz, Gruppenabschluss oder kein Original-PDF)"]
        vals[cBS - 1] = mio(b.get("bilanzsumme"))
    wsb.append(vals)
    for c in range(4, cH):
        cell = wsb.cell(r, c)
        cell.number_format = '#,##0.0'
        if cell.value is None:
            cell.value = "n. v."; cell.fill = MISS; cell.alignment = Alignment(horizontal="right")
    for c in (cSA, cSP):
        wsb.cell(r, c).font = Font(bold=True)
    if rolle == "Zusatz":
        for c in range(1, 4):
            wsb.cell(r, c).fill = SEC
    elif rolle == "EBA-Hub":
        for c in range(1, 4):
            wsb.cell(r, c).fill = HUBF
    bil_rows.append((r, gname, bool(d), rolle))
last_b = wsb.max_row
wsb.freeze_panes = "D2"
wsb.column_dimensions["C"].width = 44
for c in range(4, cH):
    wsb.column_dimensions[L_(c)].width = 13
wsb.column_dimensions[L_(cH)].width = 70
wsb.auto_filter.ref = f"A1:{L_(cH)}{last_b}"
g0 = last_b + 2
wsb.cell(g0, 1).value = "Aggregierte Bilanzstruktur je Gruppe (Summe der Posten in % der Summe der Aktiva bzw. Passiva; nur Banken mit ausgelesener Bilanz, ohne Zusatzeinträge wie DZ BANK, DekaBank und DKB; Formeln)"
wsb.cell(g0, 1).font = Font(bold=True)
for k, h in enumerate(["Gruppe", "Banken mit Bilanz"] + [h for _, h in AKT] + ["Summe der Aktiva (Mio. €)"] + [h for _, h in PAS] + ["Summe der Passiva (Mio. €)"]):
    c = wsb.cell(g0 + 1, 1 + k if k < 2 else 2 + k); c.value = h; c.font = HDR; c.fill = HFILL
    c.alignment = Alignment(wrap_text=True, vertical="top")
wsb.row_dimensions[g0 + 1].height = 90
rngA = f"$A$2:$A${last_b}"; rngR = f"$B$2:$B${last_b}"
BV = [("bisherige Auswahl", f',{rngR},"<>EBA-Hub"', lambda ro: ro not in ("Zusatz", "EBA-Hub")),
      ("alle inkl. EBA-Hub-Ergänzung", "", lambda ro: ro != "Zusatz")]
for n_, (vn, crit, vf, g) in enumerate([(vn, crit, vf, g) for vn, crit, vf in BV for g in GROUPS5]):
    rr = g0 + 2 + n_
    if g == EXTRA_GROUP and vn == "bisherige Auswahl":
        continue
    wsb.cell(rr, 1).value = g
    wsb.cell(rr, 2).value = sum(1 for _, gn, ok, ro in bil_rows if gn == g and ok and vf(ro))
    wsb.cell(rr, 3).value = vn
    for c in range(cA0, cSP + 1):
        col = L_(c); tot = L_(cSA) if c <= cSA else L_(cSP)
        cell = wsb.cell(rr, c)
        if c in (cSA, cSP):
            cell.value = f"=SUMIFS({col}$2:{col}${last_b},{rngA},$A{rr},{rngR},\"<>Zusatz\"{crit})"; cell.number_format = '#,##0'
        else:
            cell.value = (f"=IFERROR(SUMIFS({col}$2:{col}${last_b},{rngA},$A{rr},{rngR},\"<>Zusatz\"{crit})"
                          f"/SUMIFS({tot}$2:{tot}${last_b},{rngA},$A{rr},{rngR},\"<>Zusatz\"{crit}),\"n. v.\")")
            cell.number_format = '0.0%'
wsb.cell(g0 + 2 + 2 * len(GROUPS5), 1).value = ("Quelle: formale HGB-Jahresbilanz (Formblatt 1 RechKredV) aus den Jahresabschlüssen auf den Bankwebsites, ergänzt um Tabelle EU CC2 der Offenlegungsberichte, hauptversammlung.de und das Lobbyregister; ausgelesen am 26.10.2026; "
                             "Rohdaten in bilanzen_2025.json. Hauptposten ohne Unterposten, umgerechnet in Mio. €. 0 = Posten in der Bilanz nicht ausgewiesen. "
                             "Die Prüfspalten zeigen Rundungsdifferenzen der Quelle; größere Abweichungen sind in der Hinweisspalte erläutert. "
                             "Ergänzung 27.10.2026: Bilanzen aus Tabelle EU CC2 (Spalte a, Bilanz laut Jahresabschluss) im EBA-Pillar-3-Datenhub für Banken ohne frei verfügbaren Abschluss; "
                             "im Hub-Export fehlen bei vielen Instituten einzelne Positionswerte (meist 'Verbindlichkeiten gegenüber Kunden'), diese sind als Differenz zur Bilanzsumme berechnet und in der Hinweisspalte genannt.")
me.append([f"Blatt 'Bilanzen 31.12.2025' (Stand 26.10.2026, Ergänzung 27.10.2026 um {len(BIL_HUB)} Bilanzen aus EU CC2 im EBA-Datenhub): Vollständige HGB-Bilanz (Hauptposten nach Formblatt 1 RechKredV, Mio. €) für {len(BIL) - len(BIL_HUB)} der 129 Banken der bisherigen Auswahl, ausgelesen aus den Original-Jahresabschlüssen auf den Bankwebsites (bei MünchenerHyp und Haspa aus der Vorjahresspalte des HGB-Halbjahresberichts 30.06.2026). Nacherhebung 26.10.2026: weitere Banken aus Tabelle EU CC2 der Offenlegungsberichte (Bilanz laut Jahresabschluss, Hauptposten), aus Jahresabschlüssen auf hauptversammlung.de und im Lobbyregister des Bundestags; die Quelle steht je Zeile in der Hinweisspalte. "
           "Jede Bilanz wurde gegen die gedruckte Summe der Aktiva und Passiva sowie gegen die Bilanzsumme, das Eigenkapital und den Fonds § 340g im Blatt 'Übersicht' geprüft. Summen und Prüfdifferenzen sind Formeln. "
           "Banken, deren Abschluss nur im Unternehmensregister steht oder die nur eine verkürzte Bilanz veröffentlichen, sind 'n. v.'. Unten im Blatt: aggregierte Bilanzstruktur je Gruppe."])

ORDER = ["Auswertung", "Übersicht", "Gruppenauswertung", "Nicht aufgenommen", "Zeitreihe 2021-2025", "Entwicklung ab 2022",
         "Offenlegung 31.12.2025", "Eigenmittel CC1", "RWA-Aufteilung OV1", "Bilanzen 31.12.2025", "Methodik"]
wb._sheets.sort(key=lambda w: ORDER.index(w.title) if w.title in ORDER else len(ORDER))
wb.active = 1
wb.save(OUT)
# Formeln mit LibreOffice durchrechnen, damit die Datei gespeicherte Ergebnisse enthält
# (openpyxl schreibt nur Formeln; Vorschauen ohne Rechenkern zeigen sonst leere Zellen bzw. 0,00 %)
import subprocess, tempfile, shutil
with tempfile.TemporaryDirectory() as td:
    subprocess.run(["soffice", "--headless", "--calc", "--convert-to", "xlsx:Calc MS Excel 2007 XML", "--outdir", td, OUT],
                   check=True, capture_output=True, timeout=300)
    shutil.copyfile(os.path.join(td, os.path.basename(OUT)), OUT)
json.dump({k: v for k, v in summary.items()}, open(D + "summary.json", "w"), indent=1, ensure_ascii=False)
print("saved", OUT, last - 1, "rows")
for k, v in summary.items():
    print(k, {a: (round(b, 4) if isinstance(b, float) else b) for a, b in v.items()})
