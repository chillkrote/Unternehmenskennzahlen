import re, sys, json, collections
sys.path.insert(0, "/mnt/project-files/bilanzvergleich/rohdaten")
import importlib.util
spec = importlib.util.spec_from_file_location("mh", "/mnt/project-files/bilanzvergleich/rohdaten/mk_hub_neu.py")
src = open("/mnt/project-files/bilanzvergleich/rohdaten/mk_hub_neu.py").read()
src = "A_RULES" + src.split("A_RULES", 1)[1].split("def side_of")[0]
ns = {"re": re}; exec(src, ns)
classify = ns["classify"]
NUM = r"(?:-?\(?\d{1,3}(?:\.\d{3})*(?:,\d+)?\)?|-?\d+(?:,\d+)?|k\.\s?A\.?|n\.\s?a\.?|–|-|—)"
LINE = re.compile(r"^\s*(?:EU-?\s*)?(\d{1,2}[a-z]?\.?)?\s*(.*?)\s{2,}(" + NUM + r")(?:\s{2,}.*)?\s*$")
def val(s):
    s = s.strip()
    if re.match(r"^(k\.\s?A\.?|n\.\s?a\.?|–|-|—)$", s): return 0.0
    neg = s.startswith("(") or s.startswith("-")
    s = s.strip("()-")
    v = float(s.replace(".", "").replace(",", "."))
    return -v if neg else v
def year_of(t):
    c = collections.Counter(re.findall(r"31\.\s?12\.\s?(20[12]\d)|31\.\s?Dezember\s?(20[12]\d)", t[:20000]))
    ys = collections.Counter()
    for a, b in c.elements(): ys[a or b] += 1
    return int(ys.most_common(1)[0][0]) if ys else None
TOT_A = re.compile(r"(aktiva|summe der aktiva|aktiva) (insgesamt|gesamt)|^summe (der )?aktiva|^gesamtaktiva|^bilanzsumme|summe aktiva", re.I)
TOT_P = re.compile(r"passiva (insgesamt|gesamt)|^summe (der )?passiva|^gesamtpassiva|summe passiva", re.I)
TOT_E = re.compile(r"eigenkapital (insgesamt|gesamt)|^summe eigenkapital|^eigenkapital gesamt", re.I)
def parse(t):
    L = t.splitlines()
    heads = [i for i, l in enumerate(L) if re.search(r"EU\s*CC2|CC2\s*[–-]", l)]
    best = None
    for h in heads:
        seg = L[h:h + 260]
        j = next((k for k, l in enumerate(seg) if TOT_P.search(l.strip()) and re.search(NUM + r"\s*$", l)), None)
        if j is not None:
            best = (h, h + j + 1)
    if not best:
        return None
    seg = L[best[0]:best[1]]
    unit = 1.0
    hdr = " ".join(seg[:40])
    if re.search(r"TEUR|Tsd\.|in Tausend|T€", hdr, re.I): unit = 1e-3
    if re.search(r"in EUR\b|in Euro\b", hdr) and not re.search(r"Mio", hdr): unit = 1e-6
    side = "assets"; A = {}; P = {}; tot = {}; pend = ""
    for l in seg:
        s = l.strip()
        if re.match(r"^Passiva\b", s) or "Passiva-Klassen" in s or re.match(r"^Passiv", s) and len(s) < 60:
            side = "liab"; pend = ""
            if not re.search(NUM + r"\s*$", s) or "Klassen" in s: continue
        if re.search(r"Seite\s*:?\s*\d+|^\s*s\s+\S", l) or not s:
            continue
        m = LINE.match(l)
        if not m or not re.search(r"[A-Za-zÄÖÜäöü]", (m.group(2) or "") + pend):
            if s and not re.search(r"^(a\)|b\)|c\)|In Mio|Zum Ende|Bilanz im|und im|rungskreis|Verweis)", s) and len(s) < 90:
                pend = (pend + " " + s).strip()
            continue
        lbl = ((pend + " " + m.group(2)).strip() if pend and not m.group(1) else m.group(2)).strip()
        if pend and m.group(1) is None: pass
        pend = ""
        try: v = val(m.group(3)) * unit
        except: continue
        if TOT_A.search(lbl): tot["aktiva"] = v; side = "liab"; continue
        if TOT_P.search(lbl): tot["passiva"] = v; continue
        if TOT_E.search(lbl): tot["ek"] = v; continue
        if re.search(r"verbindlichkeiten (insgesamt|gesamt)", lbl, re.I): continue
        k, davon = classify("assets" if side == "assets" else "liab", lbl)
        if k in (None, "?"): continue
        D = A if side == "assets" else P
        if davon and k in ("gez", "kaprl", "gewrl", "bilgew"):
            P.setdefault("_eq", {})[k] = P.get("_eq", {}).get(k, 0) + v; continue
        if davon: continue
        if k in ("gez", "kaprl", "gewrl", "bilgew"):
            P.setdefault("_eq", {})[k] = P.get("_eq", {}).get(k, 0) + v; continue
        if k == "ek_total": tot.setdefault("ek", v); continue
        D[k] = round(D.get(k, 0) + v, 3)
    eq = P.pop("_eq", {})
    ek = tot.get("ek") or (sum(eq.values()) if eq else None)
    r = {"aktiva": A, "passiva": P, "eq": eq, "bilanzsumme": tot.get("aktiva") or tot.get("passiva"), "summe_passiva": tot.get("passiva"),
         "eigenkapital": ek, "fonds": P.get("fonds"), "bilanzgewinn": eq.get("bilgew"), "unit": unit}
    sa = sum(A.values()); sp = sum(P.values()) + (ek or 0)
    r["chk_a"] = None if not r["bilanzsumme"] else round(sa - r["bilanzsumme"], 2)
    r["chk_p"] = None if not r["bilanzsumme"] else round(sp - r["bilanzsumme"], 2)
    return r
if __name__ == "__main__":
    t = open(sys.argv[1], errors="replace").read()
    print(year_of(t), json.dumps(parse(t), ensure_ascii=False))
