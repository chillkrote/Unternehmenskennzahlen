"""Erzeugt zeitreihe.json (Kalenderjahr-Schlüssel, Mio. €) aus:
 - ju_gj25.json:   Jahresüberschuss GJ/GJ-1 aus den GJ2025-Berichten (Offset 0/-1)
 - zr_old_extract.json: automatisch gelesene Werte aus älteren Berichten (Kalenderjahre)
 - ZR_MANUAL unten: von Hand geprüfte Werte/Hinweise"""
import json, os
D = os.path.dirname(os.path.abspath(__file__)) + "/"
import openpyxl
wb = openpyxl.load_workbook(D + "../Bilanzvergleich_Banken_GJ2025.xlsx", data_only=True)
GJ = {r[3]: r[5] for r in wb["Übersicht"].iter_rows(min_row=2, values_only=True) if r[3]}
ju = json.load(open(D + "ju_gj25.json"))
old = json.load(open(D + "zr_old_extract.json"))
DROP_OLD = {"Joh. Berenberg, Gossler & Co. KG", "Norddeutsche Landesbank Girozentrale"}
ZR_MANUAL = {
 "Commerzbank AG": {"ju": {"2025": 2374, "2024": 2294}},
 "Sparda-Bank Südwest eG": {"ju": {"2025": 15.254, "2024": 15.476}},
 "Aareal Bank AG": {"ju": {"2025": -81.1, "2024": 1988.1}},
 "Landesbank Baden-Württemberg": {"ju": {"2025": 350, "2024": 330}},
 "Joh. Berenberg, Gossler & Co. KG": {"ju": {"2025": 20.217, "2024": 81.613, "2023": 55, "2022": 55, "2021": 170},
     "note": "Jahresüberschuss 2021–2023 aus der 10-Jahres-Übersicht im Lagebericht (Mio. € gerundet)"},
 "Volksbank BRAWO eG": {"ju": {"2025": 0.187, "2024": 26.531, "2023": 25.925, "2022": 31.683, "2021": 26.631},
     "note": "Fünfjahresübersicht im Lagebericht; 2025 Fonds-Auflösung 136 Mio."},
 "Volkswagen Bank GmbH": {"fonds": {"2021": 25.565, "2022": 25.565, "2023": 25.565}, "note": "Jahresüberschuss 0: Gewinnabführung"},
 "Hamburger Sparkasse AG (Haspa)": {"note": "Jahresüberschuss 0: Gewinnabführung"},
}
SKIP_JU = {"Baader Bank AG"}
out = {}
for n, v in ju.items():
    if n in SKIP_JU or n.startswith("Deutsche Kreditbank") or n.startswith("TOYOTA"): continue
    g = GJ.get(n) or 2025
    out.setdefault(n, {"cal": {}})["cal"].setdefault("ju", {}).update({str(g + int(k)): x for k, x in
        {"0": v["0"], "-1": v["-1"]}.items()})
for n, v in old.items():
    if n in DROP_OLD: continue
    for m, d in v.items():
        out.setdefault(n, {"cal": {}})["cal"].setdefault(m, {}).update({y: x for y, x in d.items()})
        out[n]["old"] = True
for n, v in ZR_MANUAL.items():
    e = out.setdefault(n, {"cal": {}})
    for m, d in v.items():
        if m == "note": e["note"] = d
        else: e["cal"].setdefault(m, {}).update(d)

# Zweite Welle: Berichte von den Bank-Websites (Crawl), nur von Hand freigegebene Dateien/Kennzahlen
dl2 = json.load(open(D + "zr_dl2_extract.json"))
import json as _j
_banks = None
ACCEPT = {
 "110_1.txt": "bs ek fonds ju", "110_2.txt": "bs ek fonds ju",
 "005_0.txt": "bs ju", "005_2.txt": "bs ju", "005_4.txt": "bs ju",
 "081_1.txt": "bs fonds ju",
 "006_13.txt": "bs ek fonds ju", "006_18.txt": "bs ek fonds ju", "006_24.txt": "bs ek fonds ju",
 "026_0.txt": "bs fonds ju", "011_1.txt": "bs ju",
 "128_11.txt": "bs fonds ju", "128_0.txt": "bs fonds ju", "128_7.txt": "bs fonds ju",
 "082_2024.txt": "bs fonds ju", "086_2024.txt": "bs ek fonds ju", "101_2024.txt": "bs fonds ju",
 "090_6.txt": "bs", "090_2.txt": "bs", "090_4.txt": "bs",
 "037_8.txt": "bs fonds", "037_10.txt": "bs fonds", "037_11.txt": "bs fonds", "037_9.txt": "bs fonds",
}
IDX_NAME = json.load(open(D + "zr_idx_names.json"))
import re as _re
for fn, ms in ACCEPT.items():
    i, c, r = dl2[fn]
    name = IDX_NAME[str(i)]
    Y = int(c[0][0])
    # Berichtsjahr: häufigstes Datum; bei Mehrdeutigkeit (Folgejahr im Text) das kleinere der beiden Top-Jahre, die Bilanzsumme prüft die Ordnung
    for m in ms.split():
        if m not in r: continue
        a, b = r[m]
        e = out.setdefault(name, {"cal": {}})
        e.setdefault("old", True)
        e["cal"].setdefault(m, {})
        e["cal"][m].setdefault(str(Y), a)
        e["cal"][m].setdefault(str(Y - 1), b)

for n, e in out.items():
    s = "Jahresüberschuss 2025/2024: GuV der GJ2025-Berichte."
    if e.get("old"): s += " Ältere Jahre: automatisch aus Jahresabschlüssen/Geschäftsberichten GJ2021–2023 gelesen (Stichproben geprüft)."
    e["src"] = s
json.dump({"items": [{"name": n, **e} for n, e in out.items()]}, open(D + "zeitreihe.json", "w"), ensure_ascii=False, indent=1)
print(len(out))
