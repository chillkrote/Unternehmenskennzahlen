"""Weltkugel, Darstellungsform Politik & Wahlen: erzeugt data/politik.json (und mit --geo app/geo/de_laender.geojson).

Inhalt (alles kostenlos und ohne Schlüssel):
 - regierungen: je Land Regierungschef, Staatsoberhaupt und deren Partei samt politischer Ausrichtung der Partei
   (Wikidata, CC0). Die Ausrichtung ist der Mittelwert der Wikidata-Angaben "politische Ausrichtung" (P1387) der Partei
   des Regierungschefs (ohne Partei: des Staatsoberhaupts), eingeteilt in links, Mitte-links, Mitte, Mitte-rechts, rechts.
   Ohne Partei oder ohne Angabe: keine Zuordnung. Wikidata wird von Freiwilligen gepflegt; Stand steht in "abruf".
 - wahlen: nationale Wahlen der nächsten zwölf Monate aus den Wikipedia-Listen "national electoral calendar" (CC BY-SA 4.0).
 - buendnisse: aus app/geo/buendnisse.csv (von Hand gepflegt, Quelle je Bündnis).
 - deutschland: Bundestagswahl 2025 je Land (Zweitstimmen, Bundeswahlleiterin, Datenlizenz Deutschland 2.0), Sitzverteilung,
   Ministerpräsidentinnen und -präsidenten (Wikidata) und die jüngste Umfrage je Parlament (DAWUM, ODbL).

    python3 app/politik_daten.py           # Daten abrufen
    python3 app/politik_daten.py --geo     # zusätzlich Bundesländer-Umrisse aus Natural Earth (gemeinfrei) neu erzeugen
"""
import argparse
import csv
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

HIER = Path(__file__).resolve().parent
ZIEL = HIER / "data/politik.json"
GEO_DE = HIER / "geo/de_laender.geojson"
UA = {"User-Agent": "Unternehmenskennzahlen/1.0 (https://github.com/chillkrote/Unternehmenskennzahlen)"}
SPARQL = "https://query.wikidata.org/sparql?"
WIKI = "https://en.wikipedia.org/w/index.php?title={}_national_electoral_calendar&action=raw"
KERG = "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/ergebnisse/opendata/btw25/csv/kerg2.csv"
DAWUM = "https://api.dawum.de/"
NE_A1 = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_1_states_provinces.geojson"
# Bundestag nach der Wahl vom 23.02.2025, endgültiges Ergebnis (Bundeswahlleiterin)
BUNDESTAG = {"stand": "Wahl 23.02.2025, endgültiges Ergebnis", "quelle": "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/ergebnisse/bund-99.html",
             "sitze": [["CDU", 164, "#1a1a1a"], ["CSU", 44, "#2f6db5"], ["AfD", 152, "#00a2de"], ["SPD", 120, "#e3000f"],
                       ["Grüne", 85, "#46962b"], ["Die Linke", 64, "#be3075"], ["SSW", 1, "#003c8f"]],
             "regierung": ["CDU", "CSU", "SPD"]}
# Ausrichtung (englische Wikidata-Bezeichnung) -> Wert von -3 (ganz links) bis +3 (ganz rechts)
SKALA = {"far-left politics": -3, "far-left": -3, "left-wing politics": -2, "left-wing": -2, "centre-left politics": -1, "centre-left": -1,
         "center-left politics": -1, "centre politics": 0, "centrism": 0, "center": 0, "radical centrism": 0, "big tent": 0,
         "centre-right politics": 1, "centre-right": 1, "center-right politics": 1, "right-wing politics": 2, "right-wing": 2,
         "far-right politics": 3, "far-right": 3, "alt-right": 3, "right-libertarianism": 2, "left-libertarianism": -2,
         "syncretic politics": 0, "fiscal conservatism": 1}
STUFEN = [(-1.5, "links"), (-.5, "mitte-links"), (.5, "mitte"), (1.5, "mitte-rechts"), (99, "rechts")]


def holen(url, versuche=4, roh=False):
    for i in range(versuche):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=150) as r:
                b = r.read()
            return b if roh else b.decode("utf-8-sig")
        except Exception as e:  # noqa: BLE001
            if i == versuche - 1:
                raise
            print("  Wiederholung", url[:90], e, file=sys.stderr)
            time.sleep(10 * (i + 1))


def sparql(q):
    return json.loads(holen(SPARQL + urllib.parse.urlencode({"query": q, "format": "json"})))["results"]["bindings"]


def wert(x, k):
    return x.get(k, {}).get("value", "")


def qid(x, k):
    return wert(x, k).rsplit("/", 1)[-1]


REG = """SELECT ?iso ?hog ?hogLabel ?hos ?hosLabel ?partei ?parteiLabel ?pkurz ?ausrEn ?hosPartei ?hosParteiLabel ?hkurz ?hosAusrEn WHERE {
  ?land wdt:P31 wd:Q3624078 ; wdt:P297 ?iso .
  OPTIONAL { ?land wdt:P6 ?hog .
    OPTIONAL { ?hog p:P102 ?ps . ?ps ps:P102 ?partei . FILTER NOT EXISTS { ?ps pq:P582 [] }
      OPTIONAL { ?partei wdt:P1813 ?pkurz . FILTER(LANG(?pkurz) IN ("de", "en", "mul")) }
      OPTIONAL { ?partei wdt:P1387 ?ausr . ?ausr rdfs:label ?ausrEn . FILTER(LANG(?ausrEn) = "en") } } }
  OPTIONAL { ?land wdt:P35 ?hos .
    OPTIONAL { ?hos p:P102 ?ps2 . ?ps2 ps:P102 ?hosPartei . FILTER NOT EXISTS { ?ps2 pq:P582 [] }
      OPTIONAL { ?hosPartei wdt:P1813 ?hkurz . FILTER(LANG(?hkurz) IN ("de", "en", "mul")) }
      OPTIONAL { ?hosPartei wdt:P1387 ?ha . ?ha rdfs:label ?hosAusrEn . FILTER(LANG(?hosAusrEn) = "en") } } }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "de,en,mul". }
}"""


def regierungen():
    roh = {}
    for x in sparql(REG):
        iso = wert(x, "iso")
        r = roh.setdefault(iso, {"hog": {}, "hos": {}})
        for rolle, p, pa, au, ku in (("hog", "hog", "partei", "ausrEn", "pkurz"), ("hos", "hos", "hosPartei", "hosAusrEn", "hkurz")):
            if not wert(x, p):
                continue
            person = r[rolle].setdefault(qid(x, p), {"name": wert(x, p + "Label"), "parteien": {}})
            if wert(x, pa):
                partei = person["parteien"].setdefault(qid(x, pa), {"name": wert(x, pa + "Label"), "ausr": set(), "kurz": set()})
                if wert(x, ku) and len(wert(x, ku)) <= 14:
                    partei["kurz"].add(wert(x, ku))
                if wert(x, au):
                    partei["ausr"].add(wert(x, au).lower())
    out = {}
    for iso, r in roh.items():
        def person(rolle):
            if not r[rolle]:
                return None
            q, p = sorted(r[rolle].items())[0] if len(r[rolle]) > 1 else next(iter(r[rolle].items()))
            # bei mehreren aktuellen Parteien (z. B. Bündnis und europäische Partei): die mit Ausrichtung zuerst
            parteien = sorted(p["parteien"].items(), key=lambda kv: (not kv[1]["ausr"], kv[1]["name"]))
            werte = [SKALA[a] for _, pa in parteien for a in pa["ausr"] if a in SKALA]
            return {"name": p["name"] if not re.fullmatch(r"Q\d+", p["name"]) else "", "wikidata": q,
                    "partei": parteien[0][1]["name"] if parteien else "", "partei_wd": parteien[0][0] if parteien else "",
                    "partei_kurz": sorted(parteien[0][1]["kurz"], key=lambda k: (len(k) < 2, not k.isascii(), len(k)))[0] if parteien and parteien[0][1]["kurz"] else "",
                    "ausrichtung_angaben": sorted({a for _, pa in parteien for a in pa["ausr"]}),
                    "wert": round(sum(werte) / len(werte), 2) if werte else None}
        hog, hos = person("hog"), person("hos")
        basis = hog if hog and hog["wert"] is not None else hos if hos and hos["wert"] is not None else None
        stufe = next(s for g, s in STUFEN if basis["wert"] <= g) if basis else None
        out[iso] = {"regierungschef": hog, "staatsoberhaupt": hos, "ausrichtung": stufe,
                    "ausrichtung_nach": ("regierungschef" if basis is hog else "staatsoberhaupt") if basis else None}
    return out


MONATE = {m: i + 1 for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August", "September",
                                           "October", "November", "December"])}


def wahlen(name_iso, juengst=None):
    """Nationale Wahlen der nächsten zwölf Monate; mit `juengst` (dict) zusätzlich die Wahlen der letzten 30 Tage."""
    heute = date.today()
    ende = heute + timedelta(days=366)
    out = {}
    for jahr in sorted({heute.year, ende.year, (heute - timedelta(days=30)).year}):
        try:
            t = holen(WIKI.format(jahr))
        except Exception as e:  # noqa: BLE001
            print("  Wikipedia", jahr, e, file=sys.stderr)
            continue
        monat = None
        for z in t.splitlines():
            m = re.match(r"^==\s*([A-Za-z ]+?)\s*==\s*$", z)
            if m:
                monat = MONATE.get(m.group(1).strip())     # "Date unknown"/"Expected" -> None
                continue
            m = re.match(r"^\*+\s*(?:(\d{1,2})(?:[–-]\d{1,2})? ([A-Z][a-z]+)\s*:\s*)?(.*)$", z)
            if not m or "[[" not in z:
                continue
            tag, mname, rest = m.groups()
            mon = MONATE.get(mname) if mname else monat
            land = re.search(r"\[\[(?:Elections in )?([^|\]]+)\|([^\]]+)\]\]", rest)
            if not land:
                continue
            lname = land.group(2).strip()
            iso = name_iso.get(lname) or name_iso.get(land.group(1).replace("Elections in ", "").strip())
            if not iso:
                continue
            was = re.sub(r"<ref.*?(</ref>|/>)", "", rest[land.end():])
            was = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", was).strip(" ,:")
            was = re.sub(r"\{\{.*?\}\}", "", was).strip(" ,").replace("''", "")
            artikel = re.search(r"\[\[(\d{4} [^|\]]*)", rest[land.end():])
            if mon:
                d = date(jahr, mon, int(tag)) if tag else date(jahr, mon, 1)
                if juengst is not None and tag and heute - timedelta(days=30) <= d < heute:
                    juengst.setdefault(iso, []).append({"datum": d.isoformat(), "was": was[:140],
                                                        "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(artikel.group(1).replace(" ", "_")) if artikel else ""})
                if d < heute.replace(day=1) or d > ende or (tag and d < heute):
                    continue
                datum = d.isoformat() if tag else f"{jahr}-{mon:02d}"
            else:
                if jahr != ende.year and jahr != heute.year:
                    continue
                datum = str(jahr)
            out.setdefault(iso, []).append({"datum": datum, "was": was[:140],
                                            "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(artikel.group(1).replace(" ", "_")) if artikel else ""})
        time.sleep(2)
    for v in out.values():
        v.sort(key=lambda x: x["datum"])
    return out


def btw_laender():
    t = holen(KERG)
    z = list(csv.reader(io.StringIO(t), delimiter=";"))
    kopf = next(i for i, r in enumerate(z) if r and r[0] == "Wahlart")
    sp = {k: i for i, k in enumerate(z[kopf])}
    out = {}
    for r in z[kopf + 1:]:
        if len(r) < len(sp) or r[sp["Gebietsart"]] != "Land" or r[sp["Gruppenart"]] != "Partei" or r[sp["Stimme"]] != "2":
            continue
        p = r[sp["Prozent"]].replace(",", ".")
        if p:
            out.setdefault(r[sp["Gebietsname"]], {})[r[sp["Gruppenname"]]] = round(float(p), 1)
    return {k: dict(sorted(v.items(), key=lambda kv: -kv[1])[:8]) for k, v in out.items()}


MP = """SELECT ?q ?code ?mp ?mpLabel ?parteiLabel WHERE {
  VALUES ?q { %s }
  ?q wdt:P300 ?code .
  OPTIONAL { ?q wdt:P6 ?mp . OPTIONAL { ?mp p:P102 ?ps . ?ps ps:P102 ?partei . FILTER NOT EXISTS { ?ps pq:P582 [] } } }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "de,mul". }
}"""


def landesregierungen(qids):
    out = {}
    for x in sparql(MP % " ".join("wd:" + q for q in qids)):
        c = wert(x, "code")
        if not c.startswith("DE-"):
            continue
        e = out.setdefault(c, {"regierungschef": wert(x, "mpLabel"), "parteien": []})
        if wert(x, "parteiLabel") and wert(x, "parteiLabel") not in e["parteien"]:
            e["parteien"].append(wert(x, "parteiLabel"))
    return out


def umfragen():
    d = json.loads(holen(DAWUM))
    parteien, inst = d["Parties"], d["Institutes"]
    neu = {}
    for sid, s in d["Surveys"].items():
        p = s["Parliament_ID"]
        if p not in neu or s["Date"] > neu[p][1]["Date"]:
            neu[p] = (sid, s)
    out = {}
    for p, (sid, s) in neu.items():
        out[d["Parliaments"][p]["Shortcut"]] = {
            "datum": s["Date"], "institut": inst.get(s["Institute_ID"], {}).get("Name", ""), "befragte": s.get("Surveyed_Persons"),
            "werte": sorted([[parteien.get(k, {}).get("Shortcut", k), v] for k, v in s["Results"].items()], key=lambda x: -x[1]),
            "url": f"https://dawum.de/{urllib.parse.quote(d['Parliaments'][p]['Shortcut'])}/"}
    return {"lizenz": d["Database"]["License"]["Shortcut"], "stand": d["Database"]["Last_Update"], "parlamente": out}


def vereinfachen(pkte, tol):
    """Douglas-Peucker für einen Ring."""
    if len(pkte) < 5:
        return pkte
    def abst(p, a, b):
        (x, y), (x1, y1), (x2, y2) = p, a, b
        dx, dy = x2 - x1, y2 - y1
        if dx == dy == 0:
            return ((x - x1) ** 2 + (y - y1) ** 2) ** .5
        t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        return ((x - x1 - t * dx) ** 2 + (y - y1 - t * dy) ** 2) ** .5
    stapel, behalten = [(0, len(pkte) - 1)], {0, len(pkte) - 1}
    while stapel:
        a, b = stapel.pop()
        best, idx = 0, None
        for i in range(a + 1, b):
            d = abst(pkte[i], pkte[a], pkte[b])
            if d > best:
                best, idx = d, i
        if idx is not None and best > tol:
            behalten.add(idx)
            stapel += [(a, idx), (idx, b)]
    return [[round(x, 3), round(y, 3)] for i, (x, y) in enumerate(pkte) if i in behalten]


def geo_de():
    d = json.loads(holen(NE_A1, roh=True))
    feats = []
    for f in d["features"]:
        p = f["properties"]
        if p.get("iso_a2") != "DE":
            continue
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        neu = [[vereinfachen(r, .008) for r in poly] for poly in polys]
        neu = [poly for poly in neu if len(poly[0]) >= 4]
        feats.append({"type": "Feature", "properties": {"code": p["iso_3166_2"], "name": p.get("name_de") or p["name"], "wikidata": p.get("wikidataid")},
                      "geometry": {"type": "MultiPolygon", "coordinates": neu}})
    GEO_DE.write_text(json.dumps({"type": "FeatureCollection", "quelle": "Natural Earth 1:10 Mio., Admin 1 (gemeinfrei), vereinfacht",
                                  "features": sorted(feats, key=lambda f: f["properties"]["code"])}, ensure_ascii=False, separators=(",", ":")))
    print(f"{GEO_DE}: {len(feats)} Länder", file=sys.stderr)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--geo", action="store_true")
    a = p.parse_args()
    if a.geo or not GEO_DE.exists():
        geo_de()
    feat = json.loads((HIER / "geo/laender.geojson").read_text())["features"]
    name_iso = {}
    for f in feat:
        pr = f["properties"]
        for n in (pr.get("name_en"), pr.get("name")):
            if n:
                name_iso.setdefault(n, pr["iso"])
    # Schreibweisen der Wikipedia-Listen, die von Natural Earth abweichen
    name_iso.update({"United States": "US", "United Kingdom": "GB", "Czech Republic": "CZ", "Czechia": "CZ", "Ivory Coast": "CI",
                     "Republic of the Congo": "CG", "Democratic Republic of the Congo": "CD", "DR Congo": "CD", "South Korea": "KR",
                     "North Korea": "KP", "Russia": "RU", "Eswatini": "SZ", "East Timor": "TL", "Timor-Leste": "TL", "Cape Verde": "CV",
                     "The Gambia": "GM", "Gambia": "GM", "The Bahamas": "BS", "Bahamas": "BS", "Micronesia": "FM", "Federated States of Micronesia": "FM",
                     "North Macedonia": "MK", "Bosnia and Herzegovina": "BA", "Vietnam": "VN", "Laos": "LA", "Syria": "SY", "Iran": "IR",
                     "Taiwan": "TW", "Palestine": "PS", "State of Palestine": "PS", "Moldova": "MD", "Bolivia": "BO", "Venezuela": "VE",
                     "Tanzania": "TZ", "São Tomé and Príncipe": "ST", "Sao Tome and Principe": "ST", "Brunei": "BN", "Kosovo": "XK",
                     "Netherlands": "NL", "Philippines": "PH", "Comoros": "KM", "Maldives": "MV", "Solomon Islands": "SB"})
    alt = json.loads(ZIEL.read_text()) if ZIEL.exists() else {}
    de_geo = json.loads(GEO_DE.read_text())["features"]
    out = {"abruf": date.today().isoformat(),
           "buendnisse": [{**r, "mitglieder": r["mitglieder"].split()} for r in csv.DictReader(open(HIER / "geo/buendnisse.csv", encoding="utf-8"))],
           "quellen": {"regierungen": {"name": "Wikidata (CC0): Regierungschef P6, Staatsoberhaupt P35, Partei P102, politische Ausrichtung P1387",
                                       "url": "https://www.wikidata.org/"},
                       "wahlen": {"name": "Wikipedia, national electoral calendar (CC BY-SA 4.0)",
                                  "url": "https://en.wikipedia.org/wiki/2027_national_electoral_calendar"},
                       "btw": {"name": "Die Bundeswahlleiterin, Bundestagswahl 2025, Zweitstimmen je Land (Datenlizenz Deutschland 2.0)",
                               "url": "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/ergebnisse/opendata.html"},
                       "umfragen": {"name": "DAWUM (ODbL), jüngste Umfrage je Parlament", "url": "https://dawum.de/"}}}
    juengst = {}
    schritte = [("regierungen", regierungen), ("wahlen", lambda: wahlen(name_iso, juengst)), ("wahlen_juengst", lambda: juengst)]
    for kurz, f in schritte:
        try:
            out[kurz] = f()
            print(f"  {kurz}: {len(out[kurz])}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"{kurz} nicht abrufbar, alter Stand bleibt:", e, file=sys.stderr)
            out[kurz] = alt.get(kurz, {})
    de = dict(alt.get("deutschland", {}))
    de["bundestag"] = BUNDESTAG
    for kurz, f in (("btw25", btw_laender), ("landesregierungen", lambda: landesregierungen([x["properties"]["wikidata"] for x in de_geo])),
                    ("umfragen", umfragen)):
        try:
            de[kurz] = f()
            print(f"  {kurz}: {len(de[kurz])}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"{kurz} nicht abrufbar, alter Stand bleibt:", e, file=sys.stderr)
    out["deutschland"] = de
    ZIEL.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"{ZIEL}: {len(out.get('regierungen', {}))} Regierungen, Wahlen in {len(out.get('wahlen', {}))} Ländern", file=sys.stderr)


if __name__ == "__main__":
    main()
