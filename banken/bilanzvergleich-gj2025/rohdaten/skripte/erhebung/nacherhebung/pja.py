"""Formblatt-1-Bilanz und GuV aus pdftotext -layout: Bilanzsumme, Fonds, EK, Jahresüberschuss, Bilanzgewinn je GJ und VJ (Mio. €)."""
import re, sys, json
NUMRX = re.compile(r"(?<![\d.,])(-?\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|-?\d+,\d{1,2}|-?\d{1,3})(?![\d.,])")
def nums(l):
    out = []
    for m in NUMRX.finditer(l):
        s = m.group(1)
        # Postennummern am Zeilenanfang (z. B. "11.") ausschließen
        if m.start() < 12 and re.match(r"^\s*\d{1,2}\.?\s*$", l[:m.end() + 1]): continue
        if "," not in s and "." not in s and len(s) <= 2: continue
        v = float(s.replace(".", "").replace(",", "."))
        out.append((v, m.end()))
    return out
def find_pairs(L, rx, start=0, stop=None):
    res = []
    for i in range(start, stop or len(L)):
        if re.search(rx, L[i]):
            n = nums(L[i])
            if len(n) >= 2: res.append((i, n))
    return res
def parse(t, bs_hint=None):
    L = [l.replace("\t", "    ") for l in t.splitlines()]
    sa = find_pairs(L, r"^\s*Summe der Aktiva|^\s*Summe Aktiva|^\s*Aktivsumme")
    sp = find_pairs(L, r"^\s*Summe der Passiva|^\s*Summe Passiva|^\s*Passivsumme")
    if not sa: return None
    cands = []
    for i, n in sa:
        cur, vj = n[-2][0], n[-1][0]
        cands.append((i, cur, vj, n[-2][1], n[-1][1]))
    # bevorzugt die Bilanz, deren Summe zu bs_hint passt
    def mio(v):  # Rohwert mit Komma = EUR, sonst unbekannt
        return v
    best = None
    for c in cands:
        i, cur, vj, ce, ve = c
        for sc in (1e-6, 1e-3, 1.0):
            cm = cur * sc
            if bs_hint and abs(cm - bs_hint) <= 0.006 * bs_hint:
                best = (c, sc); break
        if best: break
    if not best:
        if bs_hint: return {"fehler": "Bilanzsumme passt nicht", "kand": [(c[1], c[2]) for c in cands[:3]]}
        c = cands[0]; best = (c, 1e-6 if c[1] > 1e7 else (1e-3 if c[1] > 1e4 else 1.0))
    (ia, cur, vj, ce, ve), sc = best
    cm = cur * sc
    vsc = None
    for s2 in (1e-6, 1e-3, 1.0):
        if 0.6 <= vj * s2 / cm <= 1.6: vsc = s2; break
    r = {"bilanzsumme": round(cm, 3), "vj_bilanzsumme": round(vj * vsc, 3) if vsc else None, "zeile_aktiva": ia}
    ip = next((i for i, n in sp if i > ia), None)
    r["zeile_passiva"] = ip
    pce, pve = ce, ve
    if ip is not None:
        npp = nums(L[ip]); pce, pve = npp[-2][1], npp[-1][1]
    ipa = next((i for i in range(ia + 1, ip or ia + 1) if re.match(r"^\s*Passiva", L[i])), ia + 1)
    def cur_vj(i):
        ce_, ve_ = (pce, pve) if i >= ipa else (ce, ve)
        n = nums(L[i])
        c = v = None
        for val, e in n:
            if abs(e - ve_) <= 3 and vsc: v = val * vsc
            elif abs(e - ce_) <= 3: c = val * sc
        return c, v
    blk = range(ia, ip) if ip else range(ia, min(len(L), ia + 120))
    for k, rx in (("fonds", r"Fonds f.r allgemeine Bank"), ("nachrang", r"Nachrangige Verbindlichkeit"), ("genuss", r"Genussrechtskapital"),
                  ("immat", r"Immaterielle Anlagewerte"), ("akt_lat", r"Aktive latente Steuern")):
        hit = None
        rng = list(range(ipa, ip or ipa + 80)) if k in ("fonds", "nachrang", "genuss") else list(range(max(0, ia - 120), ia))
        for i in rng:
            if 0 <= i < len(L) and re.search(rx, L[i]):
                c, v = cur_vj(i)
                # Wert kann auf Folgezeilen stehen (Unterposten)
                j = i
                while (c is None or (c == 0 and k == "fonds")) and j < i + 4 and j + 1 < len(L):
                    j += 1
                    if re.match(r"^\s*\d{1,2}\.\s", L[j]) or re.search(r"Summe", L[j]): break
                    c2, v2 = cur_vj(j)
                    if c2 is not None: c = c2
                if c is not None or v is not None:
                    hit = (c, v); break
        if hit: r[k] = round(hit[0], 3) if hit[0] is not None else 0.0; r["vj_" + k] = round(hit[1], 3) if hit[1] is not None else None
    # Eigenkapital-Block: von "12. Eigenkapital" bis Summe der Passiva
    ie = next((i for i in blk if re.search(r"^\s*1[2-4]\.\s*Eigenkapital|^\s*Eigenkapital\s*$", L[i])), None)
    if ie is not None:
        cs, vs = [], []
        for i in range(ie, ip or ie + 25):
            if re.search(r"darunter|davon", L[i]): continue
            if re.search(r"Summe", L[i]): break
            c, v = cur_vj(i)
            if c is not None: cs.append(c)
            if v is not None: vs.append(v)
        if cs: r["eigenkapital"] = round(max(cs), 3)
        if vs: r["vj_eigenkapital_summe_unterposten"] = round(sum(vs), 3)
    # GuV
    for k, rx in (("ju", r"^\s*\d{0,2}\.?\s*Jahres.berschuss\s*/?\s*(Jahresfehlbetrag)?\s{2,}|^\s*\d{0,2}\.?\s*Jahres.berschuss\s*$|^\s*\d{1,2}\.\s*Jahres(überschuss|fehlbetrag)"),
                  ("bilgew", r"^\s*\d{0,2}\.?\s*Bilanzgewinn\s{2,}")):
        for i in range(ia, min(len(L), ia + 400)):
            if re.search(rx, L[i]):
                n = nums(L[i])
                if len(n) >= 2:
                    c, v = n[-2][0], n[-1][0]
                    r[k] = round(c * sc, 3); r["vj_" + k] = round(v * vsc, 3) if vsc else None
                    break
    return r
if __name__ == "__main__":
    t = open(sys.argv[1], errors="replace").read()
    print(json.dumps(parse(t, float(sys.argv[2]) if len(sys.argv) > 2 else None), ensure_ascii=False))
