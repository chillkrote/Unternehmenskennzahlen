"""Universum der in Deutschland notierten Aktiengesellschaften.

Quellen (in ../quellen/, Abruf 27.10.2026):
  Listed-companies_<datum>.xlsx            Deutsche Börse, Frankfurter Wertpapierbörse:
                                           Prime Standard, General Standard, Scale, Basic Board
  maccess_gelistete-unternehmen.html       Börse München, Segment m:access
  duesseldorf_aktien-primaermarkt.html     Börse Düsseldorf, Segment Primärmarkt
  t7-xetr-allTradableInstruments.csv       Xetra, alle handelbaren Instrumente
  t7-xfra-BF-allTradableInstruments.csv.gz Börse Frankfurt, alle handelbaren Instrumente

Schreibt ../universum_instrumente.csv (eine Zeile je Aktiengattung) und
../universum.csv (eine Zeile je Unternehmen, Branche zugeordnet).
"""
import csv
import gzip
import html
import io
import json
import re
from collections import OrderedDict
from pathlib import Path

import openpyxl

HIER = Path(__file__).resolve().parent
Q = HIER.parent / "quellen"
OUT = HIER.parent

SEGMENTE_FWB = ["Prime Standard", "General Standard", "Scale", "Basic Board"]
REGULIERT = {"Prime Standard", "General Standard"}

# Branchen der Erhebung (Ordnername, Anzeigename)
BRANCHEN = OrderedDict([
    ("automobil", "Automobil und Zulieferer"),
    ("industrie", "Industrie, Maschinenbau und Bau"),
    ("chemie-rohstoffe", "Chemie und Rohstoffe"),
    ("energie-versorger", "Versorger und erneuerbare Energien"),
    ("pharma-gesundheit", "Pharma, Biotech und Gesundheit"),
    ("software-it", "Software und IT-Dienstleistungen"),
    ("technologie", "Technologie, Halbleiter und Elektronik"),
    ("telekom-medien", "Telekommunikation und Medien"),
    ("handel-konsum", "Handel, Konsum und Lebensmittel"),
    ("transport-logistik", "Transport und Logistik"),
    ("immobilien", "Immobilien"),
    ("finanzdienstleister", "Finanzdienstleister und Beteiligungsgesellschaften"),
    ("versicherungen", "Versicherungen"),
    ("banken", "Banken (siehe banken/bilanzvergleich-gj2025)"),
])


def branche_db(sektor, subsektor):
    """Branche aus Sektor/Subsektor der Deutschen Börse."""
    s = (sektor or "").strip().lower()
    u = (subsektor or "").strip().lower()
    if "real estate" in u:
        return "immobilien"
    if "renewable" in u:
        return "energie-versorger"
    if s.startswith("automobile") or s == "consumer cyclical":
        return "automobil"
    if s.startswith("industrial") or s.startswith("construction"):
        return "industrie"
    if s.startswith("chemicals") or s.startswith("basic resources"):
        return "chemie-rohstoffe"
    if s.startswith("utilities"):
        return "energie-versorger"
    if s.startswith("pharma"):
        return "pharma-gesundheit"
    if s.startswith("software"):
        return "software-it"
    if s.startswith("technology"):
        return "software-it" if "software" in u else "technologie"
    if s.startswith("telecommunication") or s.startswith("media"):
        return "telekom-medien"
    if s.startswith(("retail", "consumer", "food")):
        return "handel-konsum"
    if s.startswith("transportation"):
        return "transport-logistik"
    if s.startswith("insurance"):
        return "versicherungen"
    if s.startswith("banks"):
        return "banken"
    if s.startswith("financial"):
        return "finanzdienstleister"
    return None


def lies_fwb():
    wb = openpyxl.load_workbook(Q / "Listed-companies_2026-10-01.xlsx", read_only=True)
    zeilen = []
    for seg in SEGMENTE_FWB:
        kopf = None
        for r in wb[seg].iter_rows(values_only=True):
            if r and r[0] == "ISIN":
                kopf = [str(c).strip() if c else "" for c in r]
                continue
            if kopf and r[0]:
                d = dict(zip(kopf, r))
                zeilen.append({
                    "isin": str(d["ISIN"]).strip(),
                    "kuerzel": str(d.get("Trading Symbol") or "").strip(),
                    "name_boerse": " ".join(str(d["Company"]).split()),
                    "segment": seg,
                    "boerse": "Frankfurt",
                    "reguliert": seg in REGULIERT,
                    "land": (d.get("Country") or "").strip().replace("Luxemburg", "Luxembourg"),
                    "handelsplatz": (d.get("Instrument Exchange") or "").strip(),
                    "index": (d.get("Index") or "").strip().strip("-"),
                    "sektor_db": (d.get("Sector") or "").strip(),
                    "subsektor_db": (d.get("Subsector") or "").strip(),
                    "quelle": "Deutsche Börse, Listed companies (Stand 01.10.2026)",
                })
    return zeilen


def lies_maccess():
    t = (Q / "maccess_gelistete-unternehmen.html").read_text(encoding="utf8")
    out = []
    for tr in re.findall(r"<tr>(.*?)</tr>", t, re.S):
        m = re.search(r'href="/aktie/([A-Z]{2}[0-9A-Z]{9}\d)/"', tr)
        if not m:
            continue
        tds = [html.unescape(re.sub(r"<[^>]+>", " ", x)).split() for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        web = re.search(r'<td>\s*<a target="_blank" href="([^"]+)"', tr)
        out.append({
            "isin": m.group(1), "name_boerse": " ".join(tds[0]), "sektor_maccess": " ".join(tds[2]) if len(tds) > 2 else "",
            "website": web.group(1) if web else "",
        })
    return out


def lies_duesseldorf():
    t = html.unescape(re.sub(r"<[^>]+>", " ", (Q / "duesseldorf_aktien-primaermarkt.html").read_text(encoding="utf8")))
    t = " ".join(t.split())
    out = []
    for m in re.finditer(r"([^\d%]{3,80}?)\s+([A-Z]{2}[0-9A-Z]{9}\d)\b", t):
        name = re.sub(r"^.*(Uhr|%|[-+]?\d+,\d+)\s+", "", m.group(1)).strip()
        out.append({"isin": m.group(2), "name_boerse": name})
    seen, res = set(), []
    for o in out:
        if o["isin"] not in seen:
            seen.add(o["isin"])
            res.append(o)
    return res


def lies_t7(datei, gz=False):
    roh = gzip.open(datei, "rt", encoding="latin-1") if gz else open(datei, encoding="latin-1")
    r = list(csv.reader(roh, delimiter=";"))
    kopf = r[2]
    return [dict(zip(kopf, x)) for x in r[3:] if len(x) > 5]


# Zeilen im Freiverkehr, die nur vorübergehend handelbar sind (junge Aktien, Umtausch-/Verkaufslinien)
TEMP = re.compile(r"Z\.?\s?VERK|Z\.VK|\bVERK\.|\bJGE\b|\bKONV\.|\bN\.NA\b|BEZUGS", re.I)


def main():
    fwb = lies_fwb()
    isins = {z["isin"] for z in fwb}
    xetr = {x["ISIN"]: x for x in lies_t7(Q / "t7-xetr-allTradableInstruments.csv") if x.get("Instrument Type") == "CS"}
    xfra = {x["ISIN"]: x for x in lies_t7(Q / "t7-xfra-BF-allTradableInstruments.csv.gz", gz=True) if x.get("Instrument Type") == "CS"}

    zeilen = list(fwb)
    for m in lies_maccess():
        if m["isin"] in isins:
            for z in zeilen:
                if z["isin"] == m["isin"]:
                    z["weitere_segmente"] = "m:access (München)"
            continue
        isins.add(m["isin"])
        x = xetr.get(m["isin"]) or xfra.get(m["isin"]) or {}
        zeilen.append({"isin": m["isin"], "kuerzel": x.get("Mnemonic", ""), "name_boerse": m["name_boerse"],
                       "segment": "m:access", "boerse": "München", "reguliert": None, "land": "",
                       "website": m["website"], "sektor_maccess": m["sektor_maccess"],
                       "quelle": "Börse München, m:access gelistete Unternehmen (Abruf 27.10.2026)"})
    for d in lies_duesseldorf():
        if d["isin"] in isins:
            for z in zeilen:
                if z["isin"] == d["isin"]:
                    z["weitere_segmente"] = ", ".join(filter(None, [z.get("weitere_segmente"), "Primärmarkt (Düsseldorf)"]))
            continue
        isins.add(d["isin"])
        x = xetr.get(d["isin"]) or xfra.get(d["isin"]) or {}
        zeilen.append({"isin": d["isin"], "kuerzel": x.get("Mnemonic", ""), "name_boerse": d["name_boerse"],
                       "segment": "Primärmarkt", "boerse": "Düsseldorf", "reguliert": None, "land": "",
                       "quelle": "Börse Düsseldorf, Aktien Primärmarkt (Abruf 27.10.2026)"})
    # weitere Aktien deutscher Emittenten (DE-ISIN), die auf Xetra oder Börse Frankfurt handelbar sind
    for quelle, tab in (("Xetra", xetr), ("Börse Frankfurt", xfra)):
        for isin, x in tab.items():
            if not isin.startswith("DE") or isin in isins or TEMP.search(x["Instrument"]):
                continue
            isins.add(isin)
            zeilen.append({"isin": isin, "kuerzel": x.get("Mnemonic", ""), "name_boerse": " ".join(x["Instrument"].split()),
                           "segment": "Freiverkehr/Regionalbörse", "boerse": quelle, "reguliert": None, "land": "Germany",
                           "quelle": f"Deutsche Börse, T7 allTradableInstruments {quelle} (Stand 27.10.2026)"})
    for z in zeilen:
        x = xetr.get(z["isin"]) or xfra.get(z["isin"]) or {}
        z["wkn"] = (x.get("WKN") or "")[-6:]
        z["xetra"] = z["isin"] in xetr
        if not z.get("kuerzel"):
            z["kuerzel"] = x.get("Mnemonic", "")
        if not z.get("land"):
            z["land"] = {"DE": "Germany", "AT": "Austria", "CH": "Switzerland", "IT": "Italy", "GB": "United Kingdom",
                         "MT": "Malta", "PL": "Poland", "LU": "Luxembourg", "NL": "Netherlands"}.get(z["isin"][:2], z["isin"][:2])
        z["branche"] = branche_db(z.get("sektor_db"), z.get("subsektor_db")) or ""
    felder = ["isin", "wkn", "kuerzel", "xetra", "name_boerse", "segment", "weitere_segmente", "boerse", "reguliert", "land",
              "handelsplatz", "index", "sektor_db", "subsektor_db", "sektor_maccess", "website", "branche", "quelle"]
    with open(OUT / "rohdaten_instrumente_roh.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, felder, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(zeilen)
    print(len(zeilen), "Instrumente")


if __name__ == "__main__":
    main()
