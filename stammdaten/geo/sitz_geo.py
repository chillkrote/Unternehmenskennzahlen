"""Firmensitz je Unternehmens-ID als Koordinate (für die Weltkugel im Terminal).

Ablauf:
1. Ort und Land kommen aus stammdaten/unternehmen_ids.csv (Spalten sitz, land).
2. Fehlt der Sitz, fragt das Skript die GLEIF-LEI-Datenbank (kostenlos, ohne Schlüssel): erst über die LEI, dann über die ISIN
   (isin_haupt und isin_zuordnung.csv), zuletzt über den Namen im Land (nur eindeutige Präfix-Treffer, als "unsicher" markiert).
   Genommen wird die Anschrift der Hauptverwaltung (headquartersAddress), sonst die rechtliche Anschrift.
3. Ort -> Koordinate über GeoNames cities500 (CC BY 4.0, Orte ab 500 Einwohnern, Namen und Alternativnamen); trifft der Name nicht,
   über die Postleitzahl (GeoNames-Postleitzahlen je Land).

Ergebnis: stammdaten/geo/sitz_geo.csv (eine Zeile je ID, auch ohne Treffer, damit Lücken sichtbar bleiben).
Zeilen mit quelle_ort = "manuell" bleiben beim nächsten Lauf unverändert stehen: so lassen sich falsche Treffer von Hand korrigieren.
GLEIF-Antworten liegen in gleif_cache.json, damit ein erneuter Lauf ohne Netz dasselbe Ergebnis liefert (--offline).

    python3 stammdaten/geo/sitz_geo.py [--offline] [--geonames-dir ~/.cache/geonames]
"""
import argparse
import csv
import io
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

HIER = Path(__file__).resolve().parent
STAMM = HIER.parent
ZIEL = HIER / "sitz_geo.csv"
CACHE = HIER / "gleif_cache.json"
GLEIF = "https://api.gleif.org/api/v1/lei-records"
UA = "Unternehmenskennzahlen-Terminal/1.0 (Sitz-Geokodierung)"
SPALTEN = ["unternehmen_id", "name", "ort", "plz", "land_code", "lat", "lon", "quelle_ort", "quelle_koordinate", "geonames_id", "hinweis"]

# Ländernamen aus stammdaten (englisch) -> ISO 3166-1 alpha-2
LAND = {
    "Germany": "DE", "UK": "GB", "United Kingdom": "GB", "France": "FR", "Switzerland": "CH", "Sweden": "SE", "Italy": "IT", "Netherlands": "NL",
    "Spain": "ES", "Luxembourg": "LU", "Denmark": "DK", "Norway": "NO", "Poland": "PL", "Austria": "AT", "Belgium": "BE", "Finland": "FI",
    "Greece": "GR", "Portugal": "PT", "United States": "US", "USA": "US", "Canada": "CA", "Iceland": "IS", "Hungary": "HU", "Ireland": "IE",
    "Lithuania": "LT", "Estonia": "EE", "Mexico": "MX", "Israel": "IL", "Slovenia": "SI", "Slovakia": "SK", "Czech Republic": "CZ",
    "Czechia": "CZ", "Latvia": "LV", "Japan": "JP", "South Korea": "KR", "Korea": "KR", "Australia": "AU", "New Zealand": "NZ", "Chile": "CL",
    "Colombia": "CO", "Costa Rica": "CR", "Turkey": "TR", "Türkiye": "TR", "Bulgaria": "BG", "China": "CN", "Cyprus": "CY", "Malta": "MT",
    "Romania": "RO", "Croatia": "HR", "Liechtenstein": "LI", "Jersey": "JE", "Guernsey": "GG", "Isle of Man": "IM", "Bermuda": "BM",
    "Deutschland": "DE",
}


def norm(s):
    s = "".join(c for c in unicodedata.normalize("NFKD", (s or "").replace("ß", "ss")) if not unicodedata.combining(c)).casefold()
    return re.sub(r"[\W_]+", " ", s).strip()


RECHTSFORM = re.compile(r"\b(plc|ltd|limited|ag|se|sa|s a|nv|n v|asa|ab|a s|as|oyj|oy|spa|s p a|sas|sarl|gmbh|kgaa|co|group|grp|holding|holdings|"
                        r"inc|corp|corporation|company|the|publ|b|a)\b")


def kern(name):
    """Name ohne Rechtsform und Aktiengattung, zum Abgleich mit GLEIF-Rechtsnamen."""
    return re.sub(r"\s+", " ", RECHTSFORM.sub(" ", norm(name).replace("&", " "))).strip()


def varianten(ort):
    """Schreibweisen eines Ortsnamens, von genau nach grob."""
    o = ort.strip()
    v = [o, re.sub(r"\s*\(.*?\)", "", o), o.split("/")[0], o.split(",")[0], re.sub(r"\s+(i\.|im|in|an der|am|ob der|bei)\s.*$", "", o),
         re.sub(r"\s+\d+$", "", o), re.sub(r"\s+[A-Z]{1,2}$", "", o), re.sub(r"^(Bad|St\.?|Sankt)\s+", "", o)]
    if o.lower().startswith("st. "):
        v.append("Sankt " + o[4:])
    out = []
    for x in v:
        n = norm(x)
        if n and n not in out:
            out.append(n)
    return out


def geonames_laden(ordner):
    ordner.mkdir(parents=True, exist_ok=True)
    zipd = ordner / "cities500.zip"
    if not zipd.exists():
        print("lade GeoNames cities500 …", file=sys.stderr)
        urllib.request.urlretrieve("https://download.geonames.org/export/dump/cities500.zip", zipd)
    idx = defaultdict(dict)        # (land) -> norm(name) -> (einwohner, lat, lon, id); "*" = alle Länder (nur Hauptname)
    with zipfile.ZipFile(zipd) as z, z.open("cities500.txt") as fh:
        for zeile in io.TextIOWrapper(fh, encoding="utf-8"):
            t = zeile.rstrip("\n").split("\t")
            gid, name, ascii_, alt, lat, lon, cc, pop = t[0], t[1], t[2], t[3], t[4], t[5], t[8], int(t[14] or 0)
            for n in {norm(name), norm(ascii_), *(norm(a) for a in alt.split(",") if a)}:
                if not n:
                    continue
                alt_e = idx[cc].get(n)
                if alt_e is None or pop > alt_e[0]:
                    idx[cc][n] = (pop, float(lat), float(lon), gid)
                g = idx["*"].get(n)
                if pop >= 50000 and (g is None or pop > g[0]):
                    idx["*"][n] = (pop, float(lat), float(lon), gid)
    return idx


_plz = {}


def plz_laden(ordner, cc):
    if cc in _plz:
        return _plz[cc]
    d = {}
    zipd = ordner / f"plz_{cc}.zip"
    try:
        if not zipd.exists():
            urllib.request.urlretrieve(f"https://download.geonames.org/export/zip/{cc}.zip", zipd)
        with zipfile.ZipFile(zipd) as z, z.open(f"{cc}.txt") as fh:
            for zeile in io.TextIOWrapper(fh, encoding="utf-8"):
                t = zeile.split("\t")
                if t[9] and t[10]:
                    d.setdefault(t[1].replace(" ", "").upper(), (float(t[9]), float(t[10]), t[2]))
                    d.setdefault("ort:" + norm(t[2]), (float(t[9]), float(t[10]), t[2]))
    except Exception as e:  # Land ohne Postleitzahl-Datei
        print(f"  keine Postleitzahlen für {cc}: {e}", file=sys.stderr)
    _plz[cc] = d
    return d


class Gleif:
    def __init__(self, offline):
        self.offline = offline
        self.cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
        self.letzter = 0.0

    def _hole(self, params):
        if self.offline:
            return None
        warte = 1.05 - (time.time() - self.letzter)      # GLEIF erlaubt 60 Abrufe je Minute
        if warte > 0:
            time.sleep(warte)
        url = GLEIF + "?" + urllib.parse.urlencode(params)
        for versuch in range(4):
            try:
                self.letzter = time.time()
                req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/vnd.api+json"})
                with urllib.request.urlopen(req, timeout=40) as r:
                    return json.load(r).get("data", [])
            except Exception as e:
                print(f"  GLEIF-Fehler ({e}), neuer Versuch", file=sys.stderr)
                time.sleep(3 * (versuch + 1))
        return None

    @staticmethod
    def _adresse(rec):
        e = rec["attributes"]["entity"]
        a = e.get("headquartersAddress") or e.get("legalAddress") or {}
        if not a.get("city"):
            a = e.get("legalAddress") or {}
        return {"lei": rec["attributes"]["lei"], "name": e["legalName"]["name"], "status": e.get("status"), "ort": a.get("city"),
                "plz": a.get("postalCode"), "land": a.get("country")}

    def leis(self, leis):
        offen = [l for l in leis if "lei:" + l not in self.cache]
        for i in range(0, len(offen), 100):
            teil = offen[i:i + 100]
            daten = self._hole({"filter[lei]": ",".join(teil), "page[size]": 100})
            if daten is None:
                continue
            gef = {r["attributes"]["lei"]: self._adresse(r) for r in daten}
            for l in teil:
                self.cache["lei:" + l] = gef.get(l)

    def isin(self, isin):
        k = "isin:" + isin
        if k not in self.cache:
            d = self._hole({"filter[isin]": isin, "page[size]": 5})
            if d is None:
                return None
            self.cache[k] = self._adresse(d[0]) if d else None
        return self.cache[k]

    def name(self, name, cc):
        k = f"name:{cc}:{name}"
        if k not in self.cache:
            q = re.sub(r"\b(PLC|AG|SE|SA|S\.A\.|NV|N\.V\.|ASA|AB|A/S|OYJ|SPA|S\.P\.A\.|GRP|GROUP|HOLDING|B|A)\b\.?", " ", name, flags=re.I)
            q = re.sub(r"\s+", " ", q).strip() or name
            d = self._hole({"filter[fulltext]": q, "filter[entity.legalAddress.country]": cc, "filter[entity.status]": "ACTIVE", "page[size]": 10})
            if d is None:
                return None
            self.cache[k] = {"anfrage": q, "treffer": [self._adresse(r) for r in d]}
        return self.cache[k]

    def speichern(self):
        CACHE.write_text(json.dumps(self.cache, ensure_ascii=False, indent=0, sort_keys=True) + "\n")


def name_treffer(antwort, name):
    """Namenssuche: nur Treffer, deren Rechtsname ohne Rechtsform genau dem gesuchten Namen entspricht (ABIVAX = ABIVAX SA,
    ALCON = ALCON AG), alle im selben Ort. Töchter, Fonds und Namensähnlichkeiten (ABB Schweiz AG) zählen nicht."""
    if not antwort:
        return None
    q = kern(name)
    t = [x for x in antwort["treffer"] if x.get("ort") and q and kern(x["name"]) == q]
    if not t or len({norm(x["ort"]) for x in t}) > 1:
        return None
    return t[0]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--offline", action="store_true", help="nur den GLEIF-Cache nutzen")
    p.add_argument("--geonames-dir", default=str(Path.home() / ".cache/geonames"))
    a = p.parse_args()
    gdir = Path(a.geonames_dir).expanduser()

    zeilen = list(csv.DictReader(open(STAMM / "unternehmen_ids.csv", encoding="utf-8-sig")))
    weitere = defaultdict(list)
    for r in csv.DictReader(open(STAMM / "isin_zuordnung.csv", encoding="utf-8-sig")):
        weitere[r["unternehmen_id"]].append(r["isin"])
    alt = {r["unternehmen_id"]: r for r in csv.DictReader(open(ZIEL, encoding="utf-8"))} if ZIEL.exists() else {}

    gl = Gleif(a.offline)
    gl.leis(sorted({r["lei"] for r in zeilen if r["lei"] and not r["sitz"]}))
    gl.speichern()

    erg = []
    for r in zeilen:
        uid = r["unternehmen_id"]
        if uid in alt and alt[uid]["quelle_ort"] == "manuell":
            erg.append(alt[uid])
            continue
        cc = LAND.get(r["land"].strip(), r["land"].strip() if len(r["land"].strip()) == 2 else "")
        ort = r["sitz"].split(",")[0].strip() if r["sitz"] else ""
        plz, quelle, hinweis = "", "stammdaten" if ort else "", ""
        if not ort:
            g = None
            if r["lei"]:
                g, quelle = gl.cache.get("lei:" + r["lei"]), "gleif-lei"
            if not g:
                for isin in [r["isin_haupt"]] + weitere.get(uid, []):
                    if isin and (g := gl.isin(isin)):
                        quelle = "gleif-isin"
                        break
            if not g and cc:
                g = name_treffer(gl.name(r["name"], cc), r["name"])
                quelle, hinweis = "gleif-name", f"über den Namen gefunden (GLEIF {g['lei']}: {g['name']})" if g else ""
            if g and g.get("ort"):
                ort, plz = g["ort"], g.get("plz") or ""
                cc = g.get("land") or cc
                if quelle != "gleif-name":
                    hinweis = f"GLEIF {g['lei']}"
            else:
                quelle = ""
        erg.append({"unternehmen_id": uid, "name": r["name"], "ort": ort, "plz": plz, "land_code": cc, "lat": "", "lon": "",
                    "quelle_ort": quelle, "quelle_koordinate": "", "geonames_id": "", "hinweis": hinweis})
        if len(erg) % 50 == 0:
            gl.speichern()
    gl.speichern()

    idx = geonames_laden(gdir)
    for e in erg:
        if e["quelle_ort"] == "manuell" or not e["ort"] or not e["land_code"]:
            continue
        treffer = None
        for v in varianten(e["ort"]):
            if v in idx.get(e["land_code"], {}):
                treffer = idx[e["land_code"]][v]
                break
        if treffer:
            e["lat"], e["lon"], e["geonames_id"], e["quelle_koordinate"] = f"{treffer[1]:.4f}", f"{treffer[2]:.4f}", treffer[3], "geonames-ort"
            continue
        pz = plz_laden(gdir, e["land_code"])
        plz = e["plz"].replace(" ", "").upper()
        t = pz.get(plz) or (pz.get(plz[:4]) if plz[:4].isdigit() else None) or next((pz["ort:" + v] for v in varianten(e["ort"]) if "ort:" + v in pz), None)
        if t:
            e["lat"], e["lon"], e["quelle_koordinate"] = f"{t[0]:.4f}", f"{t[1]:.4f}", "geonames-plz"
            continue
        # Sitz in einem anderen Land als dem Registerland (ad pepper: N.V., Sitz Nürnberg): nur große, eindeutige Orte
        g = next((idx["*"][v] for v in varianten(e["ort"]) if v in idx["*"]), None)
        if g:
            e["lat"], e["lon"], e["geonames_id"], e["quelle_koordinate"] = f"{g[1]:.4f}", f"{g[2]:.4f}", g[3], "geonames-ort-ausland"
            e["hinweis"] = (e["hinweis"] + "; " if e["hinweis"] else "") + "Sitz außerhalb des Registerlands"
            continue
        e["hinweis"] = (e["hinweis"] + "; " if e["hinweis"] else "") + "Ort nicht in GeoNames gefunden"

    with open(ZIEL, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SPALTEN, lineterminator="\n")
        w.writeheader()
        w.writerows(erg)
    n = len(erg)
    mit = sum(1 for e in erg if e["lat"])
    print(f"{n} Unternehmen, {mit} mit Koordinate, {sum(1 for e in erg if e['ort'] and not e['lat'])} Ort ohne Koordinate, "
          f"{sum(1 for e in erg if not e['ort'])} ohne Ort")
    print("Herkunft Ort:", dict(Counter(e["quelle_ort"] or "-" for e in erg)))


if __name__ == "__main__":
    main()
