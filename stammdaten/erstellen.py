"""Einmaliges Aufsetzen der Stammdaten aus dem Bestand (Banken-Zeitreihen-Stammdaten + Börsenuniversum).

Legt unternehmen_ids.csv, unternehmen_aliase.csv, isin_zuordnung.csv und stammdaten/dubletten.csv an und vergibt die IDs
(U000001 ... in der Reihenfolge des normierten Namens). Läuft nur, wenn unternehmen_ids.csv noch nicht existiert (--neu überschreibt;
dann ändern sich IDs, also nur vor dem ersten Einchecken benutzen).
Zusammengeführt werden Einträge, deren normierter Name (ids.schluessel) übereinstimmt; alles andere Ähnliche steht als Prüfliste in dubletten.csv.
"""
import csv
import difflib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ids

R = ids.REPO
UNI = R / "boersennotierte-unternehmen/universum"


def csv_lesen(p, d=","):
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=d))


RECHTSFORMEN = [r"SE & Co\. KGaA", r"AG & Co\. KGaA", r"AG & Co\. KG", r"GmbH & Co\. KGaA", r"GmbH & Co\. KG", r"SE & Co\. KG", r"KGaA",
                r"SE", r"AG", r"eG", r"GmbH", r"KG", r"SpA", r"S\.A\.", r"N\.V\.", r"PLC", r"Ltd\.?", r"Inc\.?", r"e\.V\.", r"AöR",
                r"Aktiengesellschaft", r"Societas Europaea", r"SCE mbH", r"mbH", r"Holding", r"S\.p\.A\."]


def rechtsform(name):
    n = name.strip()
    if re.search(r"Aktiengesellschaft$", n):
        return "AG"
    for rf in RECHTSFORMEN:
        if re.search(r"(?:^|[\s,])" + rf + r"$", n, re.I):
            m = re.search(r"((?:SE|AG|GmbH) & Co\. ?KGaA?|(?:SE|AG|GmbH) & Co\. ?KG|KGaA|SE|AG|eG|GmbH|KG|SpA|S\.A\.|N\.V\.|PLC|Ltd\.?|Inc\.?|mbH|AöR)$", n, re.I)
            return m.group(1) if m else ""
    if re.match(r"^(Kreis|Stadt|Bezirks|Verbands|Kreis- und Stadt)?[Ss]parkasse\b|^(Kreis|Stadt)sparkasse", n):
        return "Anstalt des öffentlichen Rechts (Sparkasse)"
    return ""


def git_ordner():
    r = subprocess.run(["git", "-C", str(R), "ls-tree", "-r", "-d", "--name-only", "HEAD"], capture_output=True, text=True, check=True)
    out = []
    for p in r.stdout.splitlines():
        t = p.split("/")
        if len(t) >= 2 and t[-2] == "dokumente" or (len(t) >= 3 and t[-3] == "dokumente"):
            out.append(p)
    return out


def main():
    if ids.UNTERNEHMEN.exists() and "--neu" not in sys.argv:
        sys.exit("unternehmen_ids.csv existiert schon; nichts getan (--neu überschreibt).")
    S = csv_lesen(R / "zeitreihen/stammdaten.csv")
    U = csv_lesen(UNI / "universum.csv", ";")
    INS = csv_lesen(UNI / "universum_instrumente.csv", ";")
    banken = json.loads((R / "app/data/banken.json").read_text(encoding="utf-8"))["banken"]
    bank_info = {b["bank"]: b for b in banken if b.get("bank")}
    hub = json.loads((R / "banken/bilanzvergleich-gj2025/rohdaten/eba_hub_neu_2025.json").read_text(encoding="utf-8"))
    gleif = json.loads((R / "banken/bilanzvergleich-gj2025/rohdaten/gleif_sitz.json").read_text(encoding="utf-8"))["items"]
    isins_je = defaultdict(list)
    for z in INS:
        if z["isin"] not in isins_je[z["unternehmen_id"]]:
            isins_je[z["unternehmen_id"]].append(z["isin"])

    # Entitäten bilden: gleicher normierter Name = dasselbe Unternehmen
    ent = {}
    for s in S:
        e = ent.setdefault(ids.schluessel(s["name"]), {"s": [], "u": []})
        e["s"].append(s)
    for u in U:
        e = ent.setdefault(ids.schluessel(u["name"]), {"s": [], "u": []})
        e["u"].append(u)
    # Umbenennungen: GLEIF führt unter derselben LEI einen anderen Rechtsnamen als der Bank-Stammsatz (z. B. Varengold Bank AG -> Ascory Bank AG)
    umbenannt = []
    for lei, g in gleif.items():
        k1, k2 = ids.schluessel(g["name"]), ids.schluessel(g.get("legal_name") or "")
        if k1 in ent and k2 in ent and k1 != k2 and ent[k1]["s"] and not ent[k1]["u"] and ent[k2]["u"] and not ent[k2]["s"]:
            ent[k2]["s"] = ent[k1]["s"]
            del ent[k1]
            umbenannt.append((ent[k2]["s"][0], ent[k2]["u"][0], lei))
    zusammen = [(e["s"][0], e["u"][0]) for e in ent.values() if e["s"] and e["u"]]

    zeilen, aliase, isinz = {}, [], []
    für_id = {}
    for key in sorted(ent, key=lambda k: (k)):
        pass
    namen = {}
    for key, e in ent.items():
        s = e["s"][0] if e["s"] else None
        u = e["u"][0] if e["u"] else None
        namen[key] = (s or u)["name"]
    reihenfolge = sorted(ent, key=lambda k: (ids.schluessel(namen[k]), k))
    for n, key in enumerate(reihenfolge, 1):
        e = ent[key]
        s = e["s"][0] if e["s"] else None
        u = e["u"][0] if e["u"] else None
        uid = f"U{n:06d}"
        b = bank_info.get(s["name"], {}) if s else {}
        name = (s or u)["name"] if not (s and u) else u["name"]
        if s and u:
            name = s["name"] if s["name"].endswith(" AG") and u["name"].endswith("Aktiengesellschaft") else u["name"]
        alle = isins_je.get(u["unternehmen_id"], []) if u else []
        haupt = u["isin_haupt"] if u else ""
        weitere = [i for i in dict.fromkeys(alle + [x for x in (u["weitere_isins"].split("|") if u and u["weitere_isins"] else [])]) if i and i != haupt]
        sitz = b.get("sitz") or ((u["sitz"].split(",")[0]) if u and u["sitz"] else "")
        r = {k: "" for k in ids.KOPF_U}
        r.update(unternehmen_id=uid, name=name, rechtsform=rechtsform(name), branche=u["branche"] if u else "banken",
                 gruppe=s["gruppe"] if s else "", rolle=s["rolle"] if s else "", sitz=sitz, land=(u["land"] if u else "Germany"),
                 status="börsennotiert" if u else "nicht börsennotiert", isin_haupt=haupt, weitere_isins="|".join(weitere),
                 ticker=u["yahoo"] if u else "", ordner=(u["unternehmen_id"] if u else s["unternehmen_id"]),
                 herkunft="Bank und Börse" if (s and u) else ("Bank" if s else "Börse"),
                 nachfolger_von=s["nachfolger_von"] if s else "")
        zeilen[uid] = r
        für_id[key] = uid
        for a, art in ([(s["unternehmen_id"], "id_alt")] if s else []) + ([(u["unternehmen_id"], "id_alt")] if u else []):
            aliase.append({"alias": a, "unternehmen_id": uid, "art": art})
        for x in (s, u):
            if x:
                aliase.append({"alias": x["name"], "unternehmen_id": uid, "art": "name"})
        for i in ([haupt] if haupt else []) + weitere:
            isinz.append({"isin": i, "unternehmen_id": uid, "art": "haupt" if i == haupt else "weitere"})
    # alte IDs aus ids.json (ISIN -> ID) und Hub-/GLEIF-Namen
    reg_name = {ids.schluessel(a["alias"]): a["unternehmen_id"] for a in aliase if a["art"] == "name"}
    for isin, alt in json.loads((UNI / "ids.json").read_text(encoding="utf-8")).items():
        aliase.append({"alias": alt, "unternehmen_id": next((i["unternehmen_id"] for i in isinz if i["isin"] == isin), reg_name.get(ids.schluessel(alt), "")), "art": "id_alt"})
    aliase = [a for a in aliase if a["unternehmen_id"]]
    lei_zu_uid = {}
    for k in ("neu", "bestehend"):
        for h in hub[k]:
            uid = reg_name.get(ids.schluessel(h["name"]))
            if not uid:
                continue
            lei_zu_uid[h["lei"]] = uid
            zeilen[uid]["lei"] = zeilen[uid]["lei"] or h["lei"]
            for alt in (h.get("hub_name"),):
                if alt and reg_name.get(ids.schluessel(alt), uid) == uid:  # Hub-Name einer anderen Gesellschaft (GRENKE AG) wird kein Alias
                    aliase.append({"alias": alt, "unternehmen_id": uid, "art": "name"})
    for lei, g in gleif.items():
        uid = lei_zu_uid.get(lei) or reg_name.get(ids.schluessel(g["name"]))
        if uid:
            zeilen[uid]["lei"] = zeilen[uid]["lei"] or lei
            if g.get("legal_name") and reg_name.get(ids.schluessel(g["legal_name"]), uid) == uid:
                aliase.append({"alias": g["legal_name"], "unternehmen_id": uid, "art": "name"})
    # Ordnernamen im Repo -> ID
    schl = defaultdict(set)
    for a in aliase:
        schl[ids.schluessel(a["alias"])].add(a["unternehmen_id"])
    ungeklaert = []
    HAND = {"bsk-1818-ag-ehem-landesbank-berlin-ag", "landesbank-berlin-ag-seit-15-07-2025-bsk-1818-ag-traegerin-d"}
    lbb = next(u for u, r in zeilen.items() if r["name"].startswith("Landesbank Berlin AG"))
    for ordner_name in sorted(HAND):
        aliase.append({"alias": ordner_name, "unternehmen_id": lbb, "art": "ordner"})
    for p in git_ordner():
        if p.split("/")[-1] in HAND or p.endswith("/_mehrere-banken"):
            continue
        t = p.split("/")
        name = t[-1]
        if name in ("dokumente",):
            continue
        treffer = schl.get(ids.schluessel(name), set())
        if len(treffer) == 1:
            aliase.append({"alias": name, "unternehmen_id": next(iter(treffer)), "art": "ordner"})
        elif t[-2] == "dokumente":
            ungeklaert.append(p)
    # eindeutig machen (gleicher Alias, gleiche ID nur einmal; die ersten Arten gewinnen)
    gesehen, sauber = set(), []
    for a in aliase:
        k = (a["alias"], a["unternehmen_id"])
        if k not in gesehen:
            gesehen.add(k)
            sauber.append(a)
    # Konflikte: derselbe Alias bei verschiedenen IDs
    je_alias = defaultdict(set)
    for a in sauber:
        je_alias[a["alias"]].add(a["unternehmen_id"])
    konflikte = {a: v for a, v in je_alias.items() if len(v) > 1}
    # Prüfliste ähnlicher Namen, die NICHT zusammengeführt wurden
    namenliste = [(uid, r["name"]) for uid, r in zeilen.items()]
    ähnlich = []
    for i in range(len(namenliste)):
        for j in range(i + 1, len(namenliste)):
            a, b = namenliste[i], namenliste[j]
            q = difflib.SequenceMatcher(None, ids.schluessel(a[1]), ids.schluessel(b[1])).ratio()
            if q >= 0.88:
                ähnlich.append((round(q, 3), a, b))
    ids._schreiben(ids.UNTERNEHMEN, ids.KOPF_U, list(zeilen.values()))
    ids._schreiben(ids.ALIASE, ids.KOPF_A, sorted(sauber, key=lambda r: (r["unternehmen_id"], r["art"], r["alias"])))
    ids._schreiben(ids.ISINS, ids.KOPF_I, sorted(isinz, key=lambda r: r["isin"]))
    with open(ids.DIR / "dubletten.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["entscheidung", "unternehmen_id", "name_bank_stammdaten", "id_alt_bank", "name_boerse", "id_alt_boerse", "begruendung"])
        for s, u in sorted(zusammen, key=lambda x: x[0]["name"]):
            if any(u is u2 for _, u2, _ in umbenannt):
                continue
            w.writerow(["zusammengeführt", für_id[ids.schluessel(u["name"])], s["name"], s["unternehmen_id"], u["name"], u["unternehmen_id"],
                        "gleicher normierter Name; Bank im Bilanzvergleich und notierte Gesellschaft sind dasselbe Rechtssubjekt (Ticker/ISIN bestätigen es)"])
        for s_, u_, lei in umbenannt:
            w.writerow(["zusammengeführt", für_id[ids.schluessel(u_["name"])], s_["name"], s_["unternehmen_id"], u_["name"], u_["unternehmen_id"],
                        f"Umbenennung: GLEIF führt LEI {lei} unter dem Rechtsnamen {u_['name']} (vorher {s_['name']}); dasselbe Rechtssubjekt"])
        w.writerow(["geprüft: getrennt gelassen", "GRENKE BANK AG / Grenke AG", "GRENKE BANK AG", "grenke-bank-ag", "Grenke AG", "grenke-ag",
                    "EBA-Hub führt den Bericht der Bank unter dem Namen GRENKE AG (Konzernbericht der Muttergesellschaft); Bank (Tochter) und notierte AG sind getrennte Rechtsträger"])
        for q, a, b in sorted(ähnlich, reverse=True):
            w.writerow(["geprüft: getrennt gelassen", f"{a[0]} / {b[0]}", a[1], "", b[1], "", f"Namensähnlichkeit {q}, eigene Rechtsträger (Prüfliste für Robin)"])
    print(len(zeilen), "Unternehmen,", len(umbenannt), "Umbenennungen,", len(sauber), "Aliase,", len(isinz), "ISINs;", len(zusammen), "Zusammenführungen;", len(ähnlich), "ähnliche Paare")
    print("Alias-Konflikte:", konflikte)
    print("Ordner ohne Zuordnung:", ungeklaert)


if __name__ == "__main__":
    main()
