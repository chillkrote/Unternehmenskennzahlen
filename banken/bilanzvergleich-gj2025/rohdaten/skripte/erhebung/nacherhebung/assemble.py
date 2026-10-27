import json, re, os, sys, urllib.parse, collections
BS = json.load(open("bs2025.json"))
ALIAS = {"Erwerbsgesellschaft der S-Finanzgruppe mbH & Co. KG": "Erwerbsgesellschaft der S-Finanzgruppe mbH & Co. KG (Holding der DekaBank)"}
cc2_docs, ja_docs = [], []
for f in ("crawl/spk_parsed.json", "crawl/geno_parsed.json", "crawl/priv_parsed.json", "crawl/r2_parsed.json"):
    for r in json.load(open(f)):
        if r.get("cc2") and r["cc2"].get("bilanzsumme"):
            cc2_docs.append(r)
for r in json.load(open("crawl/ja_parsed.json")):
    ja_docs.append(r)
# Repo-Dokumente: Bank über den Ordner (Name in index.csv) zuordnen
import csv
idx = list(csv.DictReader(open("/home/user/unternehmenskennzahlen/banken/bilanzvergleich-gj2025/dokumente/index.csv", encoding="utf-8-sig"), delimiter=";"))
folder_bank = {}
for i in idx:
    fo = i["datei"].split("/")[1] if i["datei"].count("/") >= 2 else None
    if fo and i["bank"] in BS: folder_bank.setdefault(fo, i["bank"])
for r in json.load(open("crawl/repo_ja.json")):
    fo = r["file"].split("dokumente/")[1].split("/")[0]
    b = folder_bank.get(fo)
    if not b: continue
    u = next((i["quelle_url"] for i in idx if i["datei"].endswith(r["file"].split("dokumente/")[1])), None)
    ja_docs.append({"bank": b, "url": u or ("repo:" + r["file"].split("bilanzvergleich-gj2025/")[1]), "fn": os.path.basename(r["file"]), "ja": r["ja"], "repo": r["file"].split("bilanzvergleich-gj2025/")[1]})
def near(a, b, tol=0.004):
    return a is not None and b is not None and b != 0 and abs(a - b) <= tol * abs(b)
out = collections.defaultdict(lambda: {"years": collections.defaultdict(dict), "docs": []})
def put(bank, y, k, v, src, prio):
    if v is None: return
    d = out[bank]["years"][y]
    if k in d and d[k]["prio"] >= prio: return
    d[k] = {"v": round(v, 3), "src": src, "prio": prio}
# 1) CC2-Tabellen (Offenlegungsberichte): Jahr aus dem Text, Einheit über Bilanzsumme 2025
for r in cc2_docs:
    bank = ALIAS.get(r["bank"], r["bank"]); c = r["cc2"]; y = r["year"]
    if not y or y < 2021 or y > 2025: continue
    if re.search(r"20(26)", r["fn"]) and y == 2025: continue  # Zwischenberichte 2026
    ys = [int(x) for x in re.findall(r"20[12]\d", urllib.parse.unquote(r["fn"]))]
    if ys and y not in ys and not any(str(y) in s for s in re.findall(r"\d{8}", r["fn"])) and max(ys) != y: continue
    bs = abs(c["bilanzsumme"]); ref = BS.get(bank)
    sc = 1.0
    if ref:
        for s in (1.0, 1e-3, 1e-6):
            if 0.55 <= bs * s / ref <= 1.6: sc = s; break
        else: continue
    elif bs > 1e6: sc = 1e-6 if bs > 1e8 else 1e-3
    bs *= sc
    if y == 2025 and ref and not near(bs, ref, 0.006): continue
    if re.search(r"konzern|halbjahr", r["fn"], re.I): continue
    ek = abs(c["eigenkapital"]) * sc if c.get("eigenkapital") is not None else None
    eqs = sum(abs(v) for v in (c.get("eq") or {}).values()) * sc
    fo = abs(c["fonds"]) * sc if c.get("fonds") is not None else None
    chk_a = (c["chk_a"] or 0) * sc; chk_p = (c["chk_p"] or 0) * sc
    if ek is not None and fo and (abs(chk_p - fo) <= 0.006 * bs or (eqs and abs(ek - eqs - fo) <= 0.003 * bs)): ek -= fo; chk_p -= fo
    ok_a = abs(chk_a) <= 0.006 * bs; ok_p = abs(chk_p) <= 0.006 * bs
    src = {"url": r["url"], "doc": f"Offenlegungsbericht {y}, Tabelle EU CC2 (Bilanz laut Jahresabschluss)", "fn": r["fn"]}
    put(bank, y, "bs", bs, src, 3)
    if ok_a or ok_p:
        if ek and 0.01 <= ek / bs <= 0.3: put(bank, y, "ek", ek, src, 3)
        if fo is not None and fo / bs <= 0.2: put(bank, y, "fonds", fo, src, 3)
        if c.get("bilanzgewinn") is not None and abs(c["bilanzgewinn"] * sc) <= 0.02 * bs: put(bank, y, "bilgew", c["bilanzgewinn"] * sc, src, 3)
        if y == 2025 and ok_a and ok_p:
            out[bank]["bilanz2025"] = {"aktiva": {k: round(abs(v) * sc, 3) for k, v in c["aktiva"].items()},
                                       "passiva": {k: round(abs(v) * sc, 3) for k, v in c["passiva"].items()},
                                       "ek": round(ek, 3) if ek else None, "bs": round(bs, 3), "src": src}
# 2) Jahresabschlüsse: Kette ausgehend von der Bilanzsumme 2025 (Übersicht) bzw. den CC2-Jahren
def known_bs(bank, y):
    if y == 2025 and BS.get(bank): return BS[bank]
    d = out[bank]["years"].get(y, {})
    return d.get("bs", {}).get("v")
for it in range(4):
    for r in ja_docs:
        bank = ALIAS.get(r["bank"], r["bank"]); p = r["ja"]
        if not p or not p.get("bilanzsumme"): continue
        if re.search(r"halbjahr|konzern|offenleg|zwischen", r["fn"] + (r.get("url") or ""), re.I): continue
        cur = p["bilanzsumme"]
        Y = None
        for y in range(2025, 2020, -1):
            if near(cur, known_bs(bank, y), 0.003): Y = y; break
        if Y is None and not BS.get(bank):
            ys = [int(x) for x in re.findall(r"20[12]\d", r["fn"])]
            if ys and max(ys) == 2025 and cur > 100: Y = 2025
        if Y is None: continue
        src = {"url": r["url"], "doc": f"Jahresabschluss/Geschäftsbericht {Y} (Bilanz und GuV)", "fn": r["fn"]}
        put(bank, Y, "bs", cur, src, 2)
        ek = p.get("eigenkapital")
        if ek and 0.01 <= ek / cur <= 0.3: put(bank, Y, "ek", ek, src, 2)
        if p.get("fonds") is not None and p["fonds"] / cur <= 0.2 and p.get("fonds") != ek: put(bank, Y, "fonds", p["fonds"], src, 2)
        if p.get("ju") is not None and abs(p["ju"]) <= 0.03 * cur: put(bank, Y, "ju", p["ju"], src, 2)
        if p.get("bilgew") is not None and abs(p["bilgew"]) <= 0.03 * cur: put(bank, Y, "bilgew", p["bilgew"], src, 2)
        vj = p.get("vj_bilanzsumme")
        if vj and 0.6 <= vj / cur <= 1.6:
            srcv = dict(src, doc=src["doc"] + ", Vorjahresspalte")
            put(bank, Y - 1, "bs", vj, srcv, 1)
            vf = p.get("vj_fonds")
            if vf is not None and vf / vj <= 0.2 and p.get("fonds") is not None and vf <= p["fonds"] * 1.6 + 1: put(bank, Y - 1, "fonds", vf, srcv, 1)
            vek = p.get("vj_eigenkapital_summe_unterposten")
            if vek and ek and 0.8 <= vek / ek <= 1.1: put(bank, Y - 1, "ek", vek, srcv, 1)
            if p.get("vj_ju") is not None and abs(p["vj_ju"]) <= 0.03 * vj: put(bank, Y - 1, "ju", p["vj_ju"], srcv, 1)
            if p.get("vj_bilgew") is not None and abs(p["vj_bilgew"]) <= 0.03 * vj: put(bank, Y - 1, "bilgew", p["vj_bilgew"], srcv, 1)
res = {}
for b, d in out.items():
    yrs = {str(y): {k: {"wert": v["v"], "quelle": v["src"]["url"], "dokument": v["src"]["doc"]} for k, v in sorted(dd.items())} for y, dd in sorted(d["years"].items())}
    res[b] = {"jahre": yrs}
    if d.get("bilanz2025"): res[b]["bilanz2025"] = d["bilanz2025"]
json.dump(res, open("nacherhebung.json", "w"), ensure_ascii=False, indent=1)
for b, d in sorted(res.items()):
    print(b[:40], {y: {k: v["wert"] for k, v in dd.items()} for y, dd in d["jahre"].items()})
