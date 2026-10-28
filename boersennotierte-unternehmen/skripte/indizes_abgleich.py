"""Indexzugehörigkeit (DAX, MDAX, SDAX, TecDAX) aus den Zusammensetzungs-Tabellen der deutschen Wikipedia
-> universum/indexzugehoerigkeit.csv (je Unternehmen und Index eine Zeile) und Abweichungsbericht gegen universum.csv.
Wikipedia ist frei zugänglich; die Tabellen werden von der Redaktion nach der Deutschen Börse gepflegt, Stand steht im Seitentext.
Aufruf: python3 boersennotierte-unternehmen/skripte/indizes_abgleich.py [--anwenden]   (--anwenden schreibt die Spalte index in universum.csv um)"""
import csv
import html
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
UNI = WURZEL / "universum/universum.csv"
AUS = WURZEL / "universum/indexzugehoerigkeit.csv"
INDIZES = ["DAX", "MDAX", "SDAX", "TecDAX"]
UA = "Unternehmenskennzahlen-Erhebung (privates Projekt, chillkrote)"


def norm(s):
    s = html.unescape(s).lower().replace("&", "und")
    s = re.sub(r"\b(ag|se|kgaa|aktiengesellschaft|n\.v\.|s\.a\.|plc|holding|group|gruppe|& co\.?|co\.|gmbh)\b", " ", s)
    return re.sub(r"[^a-z0-9äöüß]", "", s)


def tabelle(name):
    req = urllib.request.Request(f"https://de.wikipedia.org/wiki/{name}", headers={"User-Agent": UA})
    t = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    for m in re.finditer(r"<table[^>]*wikitable[^>]*>(.*?)</table>", t, re.S):
        zeilen = [[html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S)]
                  for r in re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(1), re.S)]
        if zeilen and "Name" in zeilen[0] and any(h.startswith("Index") for h in zeilen[0]):
            kopf = zeilen[0]
            i_n, i_s = kopf.index("Name"), next((i for i, h in enumerate(kopf) if h.startswith("Symbol")), None)
            return [(z[i_n], re.sub(r"\[.*?\]", "", z[i_s]).strip() if i_s is not None else "") for z in zeilen[1:] if len(z) > i_n and z[i_n]]
    raise SystemExit(f"{name}: keine Zusammensetzungstabelle gefunden")


def main():
    uni = list(csv.DictReader(open(UNI, encoding="utf-8-sig"), delimiter=";"))
    nach_k = {u["kuerzel"]: u for u in uni if u["kuerzel"]}
    nach_n = {norm(u["name"]): u for u in uni}
    ausgabe, offen = [], []
    for idx in INDIZES:
        mitglieder = tabelle(idx)
        for name, sym in mitglieder:
            u = nach_k.get(sym) or nach_n.get(norm(name))
            if not u:
                u = next((v for k, v in nach_n.items() if norm(name) and (k.startswith(norm(name)) or norm(name).startswith(k)) and len(k) > 4), None)
            if u:
                ausgabe.append({"unternehmen_id": u["unternehmen_id"], "name": u["name"], "index": idx, "quelle": f"https://de.wikipedia.org/wiki/{idx}", "abruf": date.today().isoformat()})
            else:
                offen.append((idx, name, sym))
        print(f"{idx}: {len(mitglieder)} Mitglieder laut Wikipedia, {sum(1 for a in ausgabe if a['index'] == idx)} im Universum zugeordnet")
    with open(AUS, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, ["unternehmen_id", "name", "index", "quelle", "abruf"], delimiter=";")
        w.writeheader(); w.writerows(sorted(ausgabe, key=lambda a: (a["index"], a["name"])))
    for o in offen:
        print("nicht zugeordnet:", *o)
    # Abweichung gegen universum.csv (Spalte index kennt nur den höchsten Index)
    rang = {"DAX": 0, "MDAX": 1, "SDAX": 2, "TecDAX": 3}
    soll = {}
    for a in ausgabe:
        if a["index"] != "TecDAX":
            soll[a["unternehmen_id"]] = min(soll.get(a["unternehmen_id"], a["index"]), a["index"], key=rang.get)
    for u in uni:
        if soll.get(u["unternehmen_id"], "") != u["index"]:
            print(f"Abweichung {u['unternehmen_id']} {u['name']}: universum={u['index'] or '-'} Wikipedia={soll.get(u['unternehmen_id'], '-')}")
            if "--anwenden" in sys.argv:
                u["index"] = soll.get(u["unternehmen_id"], "")
    if "--anwenden" in sys.argv:
        with open(UNI, newline="", encoding="utf-8-sig") as f:
            kopf = next(csv.reader(f, delimiter=";"))
        with open(UNI, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, kopf, delimiter=";", lineterminator="\r\n")
            w.writeheader(); w.writerows(uni)
        print("universum.csv: Spalte index übernommen")


if __name__ == "__main__":
    main()
