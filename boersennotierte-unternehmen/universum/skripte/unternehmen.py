"""Fasst die Aktiengattungen zu Unternehmen zusammen und ordnet jedem Unternehmen eine Branche zu.

Eingaben:  ../rohdaten_instrumente_roh.csv (aus universum.py), ../../rohdaten/yahoo/<ISIN>.json,
           ../korrekturen.json (Hand-Zuordnungen: Branche, Ausschluss, Zusammenfassung, Ticker)
Ausgaben:  ../universum_instrumente.csv  eine Zeile je Aktiengattung, mit Unternehmens-ID und Yahoo-Ticker
           ../universum.csv              eine Zeile je Unternehmen (Hauptgattung = liquideste bzw. Stammaktie)
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HIER = Path(__file__).resolve().parent
U = HIER.parent
YAHOO = U.parent / "rohdaten" / "yahoo"
sys.path.insert(0, str(HIER))
from universum import BRANCHEN  # noqa: E402
sys.path.insert(0, str(U.parents[1] / "stammdaten"))
import ids  # noqa: E402

RECHTSFORM = re.compile(r"\b(aktiengesellschaft|ag|se|kgaa|gmbh|co|kg|n\.?v|s\.?a|plc|inc|ltd|limited|holding|holdings|group|gruppe|"
                        r"spolka akcyjna|s\.?p\.?a|corp|corporation|& co|und)\b\.?", re.I)
GATTUNG = re.compile(r"\b(st|vz|vzo|o\.?n|inh|na|vna|nam|vink|i\.?a|on|z\.?vk|konv)\b\.?", re.I)


def schluessel(name):
    n = name.lower().replace("&", " ")
    n = GATTUNG.sub(" ", n)
    n = RECHTSFORM.sub(" ", n)
    n = re.sub(r"[^a-z0-9äöüß]+", " ", n)
    return " ".join(n.split())


def boersenname_bereinigen(n):
    """Kurzname der Börse ohne Gattungszusätze (O.N., INH, NA, VZO, EO 1 ...)."""
    n = re.sub(r"\b(INH\.?|NA\.?|VNA|VZO|VZ|ST|O\.N\.?|ON|EO\s?[\d,]+|SF-?,?\d*|AKT\.?|NAM\.?|I\.A\.)(?=\s|$)", " ", n)
    return " ".join(n.split()).strip(" .,")


def slug(name):
    n = name.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("&", "und")):
        n = n.replace(a, b)
    n = re.sub(r"[^a-z0-9]+", "-", n).strip("-")
    return n[:60].strip("-")


def branche_yahoo(sektor, industrie):
    s, i = (sektor or "").lower(), (industrie or "").lower()
    if "auto" in i and ("parts" in i or "manufacturers" in i):
        return "automobil"
    if s == "technology":
        return "software-it" if ("software" in i or "information technology" in i) else "technologie"
    if s == "industrials":
        if re.search(r"airline|freight|logistic|marine|railroad|trucking|airport|shipping", i):
            return "transport-logistik"
        if "solar" in i or "renewable" in i:
            return "energie-versorger"
        return "industrie"
    if s == "healthcare":
        return "pharma-gesundheit"
    if s in ("consumer cyclical", "consumer defensive"):
        return "handel-konsum"
    if s == "financial services":
        if i.startswith("banks"):
            return "banken"
        if i.startswith("insurance"):
            return "versicherungen"
        return "finanzdienstleister"
    if s == "real estate":
        return "immobilien"
    if s in ("utilities", "energy"):
        return "energie-versorger"
    if s == "basic materials":
        return "chemie-rohstoffe"
    if s == "communication services":
        return "telekom-medien"
    return ""


def main():
    korr = json.loads((U / "korrekturen.json").read_text(encoding="utf-8")) if (U / "korrekturen.json").exists() else {}
    zeilen = list(csv.DictReader(open(U / "rohdaten_instrumente_roh.csv", encoding="utf-8-sig"), delimiter=";"))
    for z in zeilen:
        p = YAHOO / f"{z['isin']}.json"
        y = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        info = y.get("info", {})
        z["yahoo"] = y.get("ticker", "")
        z["name"] = info.get("longName") or info.get("shortName") or boersenname_bereinigen(z["name_boerse"])
        z["sektor_yahoo"], z["industrie_yahoo"] = info.get("sector", ""), info.get("industry", "")
        z["website"] = z.get("website") or info.get("website", "")
        z["sitz"] = ", ".join(filter(None, [info.get("city"), info.get("country")]))
        z["boersenwert_yahoo"] = info.get("marketCap") or ""
        k = korr.get("instrumente", {}).get(z["isin"], {})
        z.update({a: b for a, b in k.items() if not a.startswith("_")})
        if not z["branche"]:
            z["branche"] = branche_yahoo(z["sektor_yahoo"], z["industrie_yahoo"])
        z["ordner"] = z.get("unternehmen_id") or slug(z["name"])  # alte Schreibweise: bleibt Ordnername der Dokumente (Alias im Register)
    # Unternehmens-ID aus dem zentralen Register (stammdaten/): ISIN zuerst, dann Ordnername/Name; nur wirklich Neues bekommt eine neue ID.
    # Aktiengattungen desselben Unternehmens (gleicher normierter Name) teilen sich eine ID.
    reg = ids.lade(neu=True)
    nach_schl = defaultdict(list)
    for z in zeilen:
        nach_schl[schluessel(z["name"]) if not z.get("ausschluss") else z["isin"]].append(z)
    for gruppe in nach_schl.values():
        bekannt = sorted({u for u in (reg.nach_isin.get(z["isin"]) or reg.aufloesen(z["ordner"]) for z in gruppe) if u})
        h = gruppe[0]
        uid = bekannt[0] if bekannt else reg.registrieren(
            name=h["name"], branche=h["branche"], isin=h["isin"], weitere_isins=[z["isin"] for z in gruppe[1:]], ordner=h["ordner"],
            sitz=(h["sitz"] or "").split(",")[0].strip(), land=h["land"], ticker=h["yahoo"], herkunft="Börse")
        for z in gruppe:
            z["unternehmen_id"] = uid
    felder = ["unternehmen_id", "isin", "wkn", "kuerzel", "yahoo", "xetra", "name", "name_boerse", "segment", "weitere_segmente",
              "boerse", "reguliert", "land", "sitz", "index", "sektor_db", "subsektor_db", "sektor_maccess", "sektor_yahoo",
              "industrie_yahoo", "branche", "website", "ausschluss", "quelle"]
    with open(U / "universum_instrumente.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, felder, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(zeilen, key=lambda z: (z["unternehmen_id"], z["isin"])))
    # ein Eintrag je Unternehmen
    rang = {"Prime Standard": 0, "General Standard": 1, "Scale": 2, "m:access": 3, "Primärmarkt": 4, "Basic Board": 5,
            "Freiverkehr/Regionalbörse": 6}
    unternehmen = defaultdict(list)
    for z in zeilen:
        if not z.get("ausschluss"):
            unternehmen[z["unternehmen_id"]].append(z)
    out = []
    for uid, gr in unternehmen.items():
        gr.sort(key=lambda z: (rang.get(z["segment"], 9), bool(re.search(r"\bvz", z["name_boerse"], re.I)) if len(gr) > 1 else 0,
                               -float(z["boersenwert_yahoo"] or 0)))
        h = gr[0]
        out.append({
            "unternehmen_id": uid, "name": h["name"], "branche": h["branche"],
            "branche_name": BRANCHEN.get(h["branche"], ""), "segment": h["segment"],
            "weitere_segmente": h.get("weitere_segmente", ""), "reguliert": h["reguliert"], "index": h.get("index", ""),
            "land": h["land"], "sitz": h["sitz"], "isin_haupt": h["isin"], "kuerzel": h["kuerzel"], "yahoo": h["yahoo"],
            "weitere_isins": ", ".join(z["isin"] for z in gr[1:]), "sektor_db": h.get("sektor_db", ""),
            "subsektor_db": h.get("subsektor_db", ""), "industrie_yahoo": h["industrie_yahoo"], "website": h["website"],
        })
    out.sort(key=lambda u: (list(BRANCHEN).index(u["branche"]) if u["branche"] in BRANCHEN else 99, u["name"].lower()))
    with open(U / "universum.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, list(out[0]), delimiter=";")
        w.writeheader()
        w.writerows(out)
    for u in out:  # Stammdaten (Ticker, Sitz, Branche, ISINs) im Register nachziehen; IDs und Namen bleiben unverändert
        r = reg.unternehmen[u["unternehmen_id"]]
        reg.aktualisieren(u["unternehmen_id"], isin_haupt=u["isin_haupt"], weitere_isins=u["weitere_isins"], ticker=u["yahoo"],
                          branche=u["branche"] if r["herkunft"] == "Börse" else "", land=u["land"],
                          sitz=(u["sitz"] or "").split(",")[0].strip() if not r["sitz"] else "")
    reg.speichern()
    print(len(out), "Unternehmen,", sum(1 for z in zeilen if z.get("ausschluss")), "Gattungen ausgeschlossen")
    print(Counter(u["branche"] or "OHNE" for u in out).most_common())


if __name__ == "__main__":
    main()
