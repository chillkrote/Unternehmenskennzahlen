"""Sitz mit Koordinate für jede Zeile der Unternehmenstabelle (unternehmen-tabelle/Unternehmen_Tabelle.csv) -> tabelle_geo.csv.

Für die Weltkugel, die alle Unternehmen der Tabelle zeigt, nicht nur die des Terminals.
1. Ort aus der Spalte Sitz der Tabelle.
2. Fehlt er: GLEIF. Die ISIN wird über die GLEIF-Zuordnungsdatei ISIN -> LEI (mapping.gleif.org, täglich, frei) aufgelöst, die
   Anschrift (Hauptverwaltung, sonst rechtlicher Sitz) über die GLEIF-API in Blöcken zu 100 LEI. Antworten im gemeinsamen
   Zwischenspeicher gleif_cache.json (wie sitz_geo.py).
3. Fehlt beides: Wikidata (Abfragedienst query.wikidata.org, frei). Über die ISIN (P946) oder den Börsenkürzel (P249 als Qualifikator
   der Börsennotierung P414) wird der Hauptsitz (P159) mit Koordinate (P625) gesucht. Wikidata drosselt den Dienst zeitweise auf eine
   Abfrage je Minute, darum große Blöcke, Pausen und der Zwischenspeicher wikidata_cache.json; mit --ohne-wikidata nur der Speicher.
   Ein Kürzel gilt nur, wenn es an genau dieser Börse genau ein Unternehmen trifft.
4. Ort -> Koordinate über GeoNames wie in sitz_geo.py (Orte ab 500 Einwohnern, sonst Postleitzahl).
5. Sonst Landesmitte (Beschriftungspunkt von Natural Earth) mit genauigkeit = land, damit das Unternehmen im richtigen Land
   erscheint; die Oberfläche kennzeichnet diese Punkte als ungenau.

Schlüssel je Zeile: Unternehmens-ID, sonst ISIN, sonst Land und Name (so bleibt er stabil, wenn sich die Reihenfolge der Tabelle ändert).

    python3 stammdaten/geo/tabelle_geo.py [--offline]
"""
import argparse
import csv
import json
import sys
import zipfile
import io
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
import sitz_geo as sg  # noqa: E402

REPO = HIER.parent.parent
TABELLE = REPO / "unternehmen-tabelle/Unternehmen_Tabelle.csv"
ZIEL = HIER / "tabelle_geo.csv"
LAENDER = REPO / "app/geo/laender.geojson"
SPALTEN = ["schluessel", "unternehmen_id", "name", "land_code", "ort", "lat", "lon", "genauigkeit", "quelle"]
LAND = {**sg.LAND, "China": "CN", "India": "IN", "Japan": "JP", "Hong Kong": "HK", "Taiwan": "TW", "Brazil": "BR", "United Arab Emirates": "AE",
        "Saudi Arabia": "SA", "South Africa": "ZA", "Singapore": "SG", "Jordan": "JO"}


WD_CACHE = HIER / "wikidata_cache.json"
WD_URL = "https://query.wikidata.org/sparql"
WD_AGENT = "Unternehmenskennzahlen-Terminal/1.0 (Sitz-Geokodierung; github.com/chillkrote/Unternehmenskennzahlen)"
# Börse laut Tabelle -> Bezeichnung der Börse in Wikidata (englisches Label oder Alias)
BOERSE_WD = {
    "Tokyo Stock Exchange": "Tokyo Stock Exchange", "Shenzhen Stock Exchange": "Shenzhen Stock Exchange",
    "Shanghai Stock Exchange": "Shanghai Stock Exchange", "Australian Securities Exchange": "Australian Securities Exchange",
    "Taipei Exchange (TPEx)": "Taipei Exchange", "Taiwan Stock Exchange (TWSE)": "Taiwan Stock Exchange",
    "Taiwan Stock Exchange": "Taiwan Stock Exchange", "New York Stock Exchange Inc.": "New York Stock Exchange",
    "XBSP": "B3", "Saudi Stock Exchange": "Saudi Exchange", "Bursa Malaysia": "Bursa Malaysia",
}


def wd_frage(abfrage, versuche=6):
    daten = urllib.parse.urlencode({"query": abfrage, "format": "json"}).encode()
    for i in range(versuche):
        req = urllib.request.Request(WD_URL, data=daten, headers={"User-Agent": WD_AGENT, "Accept": "application/sparql-results+json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)["results"]["bindings"]
        except urllib.error.HTTPError as f:
            if f.code not in (429, 500, 502, 503, 504):
                raise
            warte = int(f.headers.get("Retry-After") or 0) or 65 * (i + 1)
            print(f"  Wikidata HTTP {f.code}, warte {warte} s", file=sys.stderr)
            time.sleep(warte)
        except (TimeoutError, urllib.error.URLError) as f:
            print(f"  Wikidata {f}, neuer Versuch", file=sys.stderr)
            time.sleep(65)
    raise RuntimeError("Wikidata antwortet nicht")


def wd_punkt(b):
    lon, lat = b["koord"]["value"].removeprefix("Point(").rstrip(")").split()[:2]
    return {"lat": round(float(lat), 4), "lon": round(float(lon), 4), "ort": b.get("ortLabel", {}).get("value", ""),
            "wd": b["u"]["value"].rsplit("/", 1)[-1]}


SITZ = "?u wdt:P159 ?ort. ?ort wdt:P625 ?koord. SERVICE wikibase:label { bd:serviceParam wikibase:language \"de,en\". }"


def wikidata(isins, ticker, offline):
    """isins: Menge; ticker: {Börse der Tabelle: Menge Kürzel}. Ergebnis im Zwischenspeicher: isin:X / ticker:Börse:K -> Punkt oder None."""
    cache = json.load(open(WD_CACHE)) if WD_CACHE.exists() else {}
    if offline:
        return cache
    offen = sorted(i for i in isins if "isin:" + i not in cache)
    for n in range(0, len(offen), 800):
        teil = offen[n:n + 800]
        print(f"  Wikidata ISIN {n + 1}-{n + len(teil)} von {len(offen)}", file=sys.stderr)
        werte = " ".join(f'"{i}"' for i in teil)
        treffer = {}
        for b in wd_frage(f"SELECT ?isin ?u ?ortLabel ?koord WHERE {{ VALUES ?isin {{ {werte} }} ?u wdt:P946 ?isin. {SITZ} }}"):
            treffer.setdefault(b["isin"]["value"], wd_punkt(b))
        for i in teil:
            cache["isin:" + i] = treffer.get(i)
        json.dump(cache, open(WD_CACHE, "w"), ensure_ascii=False, sort_keys=True, indent=0)
        time.sleep(62)
    for boerse, kuerzel in sorted(ticker.items()):
        wd = BOERSE_WD.get(boerse)
        if not wd or all(f"ticker:{boerse}:{k}" in cache for k in kuerzel):
            continue
        print(f"  Wikidata Börse {boerse} ({len(kuerzel)} Kürzel)", file=sys.stderr)
        abfrage = (f'SELECT ?t ?u ?ortLabel ?koord WHERE {{ ?b rdfs:label|skos:altLabel "{wd}"@en. ?u p:P414 ?s. ?s ps:P414 ?b; pq:P249 ?t. '
                   f'{SITZ} }}')
        je = {}
        for b in wd_frage(abfrage):
            je.setdefault(b["t"]["value"].strip().upper(), {})[b["u"]["value"]] = b
        for k in kuerzel:
            t = je.get(k.upper(), {})
            cache[f"ticker:{boerse}:{k}"] = wd_punkt(next(iter(t.values()))) if len(t) == 1 else None
        json.dump(cache, open(WD_CACHE, "w"), ensure_ascii=False, sort_keys=True, indent=0)
        time.sleep(62)
    return cache


def schluessel(r, cc):
    return r["unternehmen_id"] or (r["ISIN"].strip() and "ISIN:" + r["ISIN"].strip()) or f"N:{cc}:{r['Name *'].strip()}"


def isin_lei(isins, ordner):
    """ISIN -> LEI aus der GLEIF-Zuordnungsdatei (rund 30 MB gepackt), nur für die gesuchten ISINs."""
    ordner.mkdir(parents=True, exist_ok=True)
    z = ordner / "isin-lei.zip"
    if not z.exists():
        meta = json.load(urllib.request.urlopen("https://mapping.gleif.org/api/v2/isin-lei/latest"))
        urllib.request.urlretrieve(meta["data"]["attributes"]["downloadLink"], z)
    erg = {}
    with zipfile.ZipFile(z) as zf, zf.open(zf.namelist()[0]) as fh:
        for zeile in io.TextIOWrapper(fh, encoding="utf-8"):
            lei, isin = zeile.strip().split(",")[:2]
            if isin in isins:
                erg[isin] = lei
    return erg


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--offline", action="store_true")
    p.add_argument("--ohne-wikidata", action="store_true", help="Wikidata nur aus dem Zwischenspeicher")
    p.add_argument("--geonames-dir", default=str(Path.home() / ".cache/geonames"))
    p.add_argument("--gleif-dir", default=str(Path.home() / ".cache/gleif"))
    a = p.parse_args()
    zeilen = list(csv.DictReader(open(TABELLE, encoding="utf-8-sig"), delimiter=";"))
    mitte = {f["properties"]["iso"]: (f["properties"]["ly"], f["properties"]["lx"]) for f in json.load(open(LAENDER))["features"]}
    gl = sg.Gleif(a.offline)
    ohne = [r for r in zeilen if not r["Sitz"].strip()]
    isins = {r["ISIN"].strip() for r in ohne if r["ISIN"].strip() and not r["LEI"].strip()}
    zuord = isin_lei(isins, Path(a.gleif_dir).expanduser()) if isins else {}
    leis = sorted({r["LEI"].strip() for r in ohne if r["LEI"].strip()} | set(zuord.values()))
    print(f"{len(ohne)} Zeilen ohne Sitz, {len(isins)} ISINs davon {len(zuord)} mit LEI, {len(leis)} LEI abzufragen", file=sys.stderr)
    gl.leis(leis)
    gl.speichern()
    ohne_ort = [r for r in ohne if not gl.cache.get("lei:" + (r["LEI"].strip() or zuord.get(r["ISIN"].strip(), "")), {}).get("ort")]
    wd_isin = {r["ISIN"].strip() for r in ohne_ort if r["ISIN"].strip()}
    wd_ticker = {}
    for r in ohne_ort:
        if not r["ISIN"].strip() and r["Ticker"].strip():
            wd_ticker.setdefault(r["Börse"].strip(), set()).add(r["Ticker"].strip())
    wdc = wikidata(wd_isin, wd_ticker, a.offline or a.ohne_wikidata)
    idx = sg.geonames_laden(Path(a.geonames_dir).expanduser())
    erg, gesehen = [], set()
    for r in zeilen:
        cc = LAND.get(r["Land *"].strip(), "")
        k = schluessel(r, cc)
        if k in gesehen:
            continue
        gesehen.add(k)
        ort, plz, quelle = r["Sitz"].split(",")[0].strip(), "", "tabelle"
        if not ort:
            lei = r["LEI"].strip() or zuord.get(r["ISIN"].strip(), "")
            g = gl.cache.get("lei:" + lei) if lei else None
            if g and g.get("ort"):
                ort, plz, quelle = g["ort"], g.get("plz") or "", "gleif"
                cc = g.get("land") or cc
            else:
                quelle = ""
                w = wdc.get("isin:" + r["ISIN"].strip()) if r["ISIN"].strip() else wdc.get(f"ticker:{r['Börse'].strip()}:{r['Ticker'].strip()}")
                if w:
                    ort, quelle = w["ort"], "wikidata"
        e = {"schluessel": k, "unternehmen_id": r["unternehmen_id"], "name": r["Name *"].strip(), "land_code": cc, "ort": ort,
             "lat": "", "lon": "", "genauigkeit": "", "quelle": quelle}
        if quelle == "wikidata":
            w = wdc.get("isin:" + r["ISIN"].strip()) if r["ISIN"].strip() else wdc.get(f"ticker:{r['Börse'].strip()}:{r['Ticker'].strip()}")
            e.update(lat=f"{w['lat']:.4f}", lon=f"{w['lon']:.4f}", genauigkeit="ort")
        elif ort and cc:
            t = next((idx[cc][v] for v in sg.varianten(ort) if v in idx.get(cc, {})), None)
            if t:
                e.update(lat=f"{t[1]:.4f}", lon=f"{t[2]:.4f}", genauigkeit="ort")
            else:
                pz = sg.plz_laden(Path(a.geonames_dir).expanduser(), cc)
                q = plz.replace(" ", "").upper()
                t = pz.get(q) or next((pz["ort:" + v] for v in sg.varianten(ort) if "ort:" + v in pz), None)
                if t:
                    e.update(lat=f"{t[0]:.4f}", lon=f"{t[1]:.4f}", genauigkeit="ort")
        if not e["lat"] and cc in mitte:
            e.update(lat=f"{mitte[cc][0]:.4f}", lon=f"{mitte[cc][1]:.4f}", genauigkeit="land")
        erg.append(e)
    with open(ZIEL, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SPALTEN, lineterminator="\n")
        w.writeheader()
        w.writerows(erg)
    c = Counter(e["genauigkeit"] or "ohne" for e in erg)
    print(f"{len(erg)} Unternehmen: {dict(c)}; Ort aus {dict(Counter(e['quelle'] or '-' for e in erg))}")


if __name__ == "__main__":
    main()
