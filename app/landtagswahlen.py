#!/usr/bin/env python3
"""Landtagswahlen aus den amtlichen Dateien der Landeswahlleitungen: Lesen, Prüfen, Aufbereiten für das Wahlregister.

Je Land eine Lesefunktion, die dieselbe Struktur liefert (siehe `wahl()`); `wahlen_daten.regional()` ersetzt damit den
Eintrag aus dem Wahlartikel. Jede Lesefunktion prüft die Quelle gegen sich selbst (Summen der Wahlkreise = Land, gültige
Stimmen = Summe der Parteien, Sitze, Direktmandate) und bricht bei einer Abweichung ab: lieber keine Wahl als eine falsche.

Aufruf (lädt fehlende Quelldateien und Grenzen, prüft, druckt eine Übersicht):
    python3 app/landtagswahlen.py [--ohne-abruf]

Sachsen-Anhalt 06.09.2026: Statistisches Landesamt Sachsen-Anhalt, endgültiges Ergebnis
(https://wahlergebnisse.sachsen-anhalt.de/wahlen/lt26/). Grenzen der Wahlkreise: © GeoBasis-DE / LVermGeo ST, dl-de/by-2-0.
"""
import argparse
import csv
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
QUELLEN = HIER.parent / "wahlen" / "quellen"
GEO = HIER / "geo"


class Pruefehler(ValueError):
    """Die amtliche Datei widerspricht sich selbst oder passt nicht zur erwarteten Struktur."""


def r1(x):
    return None if x is None else round(x, 1)


def _hole(url, versuche=4):
    for i in range(versuche):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Unternehmenskennzahlen/1.0"}), timeout=120) as r:
                return r.read()
        except Exception:  # noqa: BLE001
            if i == versuche - 1:
                raise
            time.sleep(5 * 2 ** i)


def _widgets(seite):
    """JSON der eingebetteten Tabellen und Karten einer Ergebnisseite (htmlwidgets)."""
    return [json.loads(m) for m in re.findall(r'<script type="application/json" data-for="[^"]+"[^>]*>(.*?)</script>', seite, re.S)]


def _tabellen(seite):
    return [t for t in (((w.get("x") or {}).get("tag") or {}).get("attribs", {}).get("data") for w in _widgets(seite)) if t]


def _text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(s).replace("&shy;", "")))).strip()


def _zahl(x):
    return x if isinstance(x, (int, float)) else None


# ---------------------------------------------------------------- Sachsen-Anhalt 2026
ST = "https://wahlergebnisse.sachsen-anhalt.de/wahlen/lt26/"
ST_DATEIEN = {"downloads/Ergebnisse_Land_RKR_WKR_LT_2026.csv": "st_ltw26_land_kreise_wahlkreise.csv",
              "downloads/Sitzverteilung_LT_2026.csv": "st_ltw26_sitzverteilung.csv"}
ST_VERGLEICH = QUELLEN / "st_ltw26_vergleich_2021.json"
ST_GEO = GEO / "landtagswahlkreise_st.geojson"
ST_GEO_QUELLE = "Statistisches Landesamt Sachsen-Anhalt, Wahlkreiskarte Landtagswahl 2026; © GeoBasis-DE / LVermGeo ST, dl-de/by-2-0"


def st_vergleich(land, sitze, gv):
    """Vergleichswerte der Landtagswahl 2021 aus den Tabellen der Ergebnisseiten (erg_land, sitze, gewinn_verlust_wkr)."""
    t = _tabellen(land)[0]
    zeile = {_text(m): i for i, m in enumerate(t["merkmal"])}
    fest = {"Wähler/innen, Wahlbeteiligung", "Briefwähler/innen, Briefwahlbeteiligung", "Ungültig", "Gültig"}
    out = {"quelle": ST + "erg_land.html, sitze.html, gewinn_verlust_wkr.html", "wahl": "2021-06-06",
           "land": {"bet": t["prozent.vj.x"][zeile["Wähler/innen, Wahlbeteiligung"]], "z": {}, "e": {}}, "sitze": {}, "wahlkreise": {}}
    for name, i in zeile.items():
        if name in fest or name.startswith("Wahlberechtigte"):
            continue
        for st, sp in (("z", "prozent.vj.x"), ("e", "prozent.vj.y")):
            if _zahl(t[sp][i]) is not None:
                out["land"][st][re.sub(r"\s*\d$", "", name)] = t[sp][i]
    s = next(x for x in _tabellen(sitze) if "anzahl_sitze_vj" in x)
    for p, n in zip(s["partei_kurzname"], s["anzahl_sitze_vj"]):
        if p != "Insgesamt":
            out["sitze"][p] = n
    out["sitze_n"] = s["anzahl_sitze_vj"][s["partei_kurzname"].index("Insgesamt")]
    g = next(x for x in _tabellen(gv) if "partei_stimmen.y" in x)
    for wk, p, n, ges in zip(g["wkr"], g["partei_kurzname"], g["partei_stimmen.y"], g["zst_insgesamt.y"]):
        w = out["wahlkreise"].setdefault(str(int(wk)), {"gueltig": ges, "z": {}})
        if _zahl(n) is not None:
            w["z"][p] = n
    return out


def st_flaechen(karte):
    """Wahlkreisflächen aus der Wahlkreiskarte (Leaflet-Daten der Seite karten_wkr.html) -> GeoJSON, properties.id = Wahlkreisnummer."""
    ruf = next(c for w in _widgets(karte) for c in (w.get("x") or {}).get("calls", []) if c["method"] == "addPolygons")
    feats = []
    for poly, label in zip(ruf["args"][0], ruf["args"][6]):
        m = re.match(r"(\d+)\s+(.*)", _text(label).split(" Wahlbeteiligung")[0].strip())
        teile = [[[[round(x, 4), round(y, 4)] for x, y in zip(ring["lng"], ring["lat"])] for ring in teil] for teil in poly]
        for t in teile:
            for ring in t:
                if ring[0] != ring[-1]:
                    ring.append(ring[0])
        geom = {"type": "Polygon", "coordinates": teile[0]} if len(teile) == 1 else {"type": "MultiPolygon", "coordinates": teile}
        feats.append({"type": "Feature", "properties": {"id": str(int(m.group(1))), "name": m.group(2).strip()}, "geometry": geom})
    feats.sort(key=lambda f: int(f["properties"]["id"]))
    return {"type": "FeatureCollection", "quelle": ST_GEO_QUELLE, "features": feats}


def st_laden(abruf=True):
    """Fehlende Quelldateien und Grenzen holen. Vorhandene Dateien bleiben unverändert (der Stand im Repository ist die Quelle des Builds)."""
    for quelle, ziel in ST_DATEIEN.items():
        p = QUELLEN / ziel
        if not p.exists() and abruf:
            p.write_bytes(_hole(ST + quelle))
    if not ST_VERGLEICH.exists() and abruf:
        seiten = [_hole(ST + s).decode("utf-8") for s in ("erg_land.html", "sitze.html", "gewinn_verlust_wkr.html")]
        ST_VERGLEICH.write_text(json.dumps(st_vergleich(*seiten), ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if not ST_GEO.exists() and abruf:
        ST_GEO.write_text(json.dumps(st_flaechen(_hole(ST + "karten_wkr.html").decode("utf-8")), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def _st_zeilen(pfad):
    """{(satzart, schlüssel, wahllokal): {spalte: wert}}; Zahlen als int, leere Felder als None."""
    out = {}
    with open(pfad, encoding="utf-8-sig", newline="") as f:
        for z in csv.DictReader(f, delimiter=";"):
            if z["Ergebnisart"] != "E":
                raise Pruefehler(f"{pfad.name}: Ergebnisart {z['Ergebnisart']!r} statt E (endgültig)")
            d = {k: (int(v) if re.fullmatch(r"-?\d+", v or "") else (v or None)) for k, v in z.items()}
            out[(z["Satzart"], z["Schlüsselnummer"], z["Wahllokal"])] = d
    return out


def _st_parteien(d, buchstabe):
    """[(partei, stimmen)] der Spalten F01… (Zweitstimmen) bzw. D01… (Erststimmen), ohne Parteien ohne Wahlvorschlag im Gebiet."""
    return [(k.split(".", 1)[1], v) for k, v in d.items() if re.match(rf"{buchstabe}\d\d\.", k) and v is not None]


def st_pruefe(zeilen, sitze, geo=None):
    """Widersprüche der amtlichen Dateien als Liste von Sätzen (leer = stimmig)."""
    f = []
    land = zeilen[("LAN", "15", "")]
    spalten = [k for k, v in land.items() if isinstance(v, int) and re.match(r"[A-F](\d\d)?\.", k)]
    for art, n in (("WKR", 41), ("KRS", 14)):
        teile = [d for (a, _, lokal), d in zeilen.items() if a == art and lokal == ""]
        if len(teile) != n:
            f.append(f"{art}: {len(teile)} statt {n} Gebiete")
        for k in spalten:
            s = sum(d[k] or 0 for d in teile)
            if s != land[k]:
                f.append(f"{art}: Summe {k} = {s}, Land = {land[k]}")
    for (art, nr, lokal), d in zeilen.items():
        if lokal:
            continue
        for b, gueltig in (("F", "F.Gültige.Zweitstimmen"), ("D", "D.Gültige.Erststimmen")):
            s = sum(n for _, n in _st_parteien(d, b))
            if s != d[gueltig]:
                f.append(f"{art} {nr}: Summe der Parteien {b} = {s}, gültig = {d[gueltig]}")
        if d["B.Wähler"] != d["F.Gültige.Zweitstimmen"] + d["E.Ungültige.Zweitstimmen"]:
            f.append(f"{art} {nr}: Wähler ungleich gültige + ungültige Zweitstimmen")
        u, b = zeilen.get((art, nr, "U")), zeilen.get((art, nr, "B"))
        if u and b:
            for k in spalten:
                if k != "A.Wahlberechtigte" and (u[k] or 0) + (b[k] or 0) != (d[k] or 0):
                    f.append(f"{art} {nr}: Urne + Brief ungleich Gesamt bei {k}")
    direkt = {}
    for (art, nr, lokal), d in zeilen.items():
        if art != "WKR" or lokal:
            continue
        m = re.search(r"\(([^()]+)\)\s*$", d["Gewählt.im.Wahlkreis"] or "")
        if not m:
            f.append(f"WKR {nr}: kein gewählter Bewerber")
            continue
        direkt[m.group(1)] = direkt.get(m.group(1), 0) + 1
        erst = max(_st_parteien(d, "D"), key=lambda x: x[1])[0]
        if erst != m.group(1):
            f.append(f"WKR {nr}: gewählt {m.group(1)}, meiste Erststimmen {erst}")
    for z in sitze:
        if z["Partei"] == "Insgesamt":
            if z["Sitze.insgesamt"] != sum(x["Sitze.insgesamt"] for x in sitze if x["Partei"] != "Insgesamt"):
                f.append("Sitze: Summe der Parteien ungleich Insgesamt")
            continue
        if z["Sitze.insgesamt"] != z["Kreiswahlvorschlaege"] + z["Landeswahlvorschlaege"]:
            f.append(f"Sitze {z['Partei']}: Direkt + Liste ungleich Gesamt")
        if z["Kreiswahlvorschlaege"] != direkt.get(z["Partei"], 0):
            f.append(f"Sitze {z['Partei']}: {z['Kreiswahlvorschlaege']} Direktmandate laut Sitzverteilung, {direkt.get(z['Partei'], 0)} gewählte Bewerber")
    if geo is not None:
        ids = sorted(int(x["properties"]["id"]) for x in geo["features"])
        if ids != list(range(1, 42)):
            f.append(f"Grenzen: Wahlkreise {ids[:3]}…{ids[-3:]} ({len(ids)}) statt 1 bis 41")
    return f


def _st_sitze():
    with open(QUELLEN / ST_DATEIEN["downloads/Sitzverteilung_LT_2026.csv"], encoding="utf-8-sig", newline="") as f:
        return [{k: (int(v) if re.fullmatch(r"\d+", v or "") else v) for k, v in z.items()} for z in csv.DictReader(f, delimiter=";")]


def st_ltw26(kurz=lambda p: p):
    """Landtagswahl Sachsen-Anhalt 06.09.2026: Land, 41 Wahlkreise (Erst- und Zweitstimmen, Direktmandat), 14 Kreise, Sitze, Vergleich 2021."""
    pfad = QUELLEN / ST_DATEIEN["downloads/Ergebnisse_Land_RKR_WKR_LT_2026.csv"]
    if not pfad.exists() or not (QUELLEN / ST_DATEIEN["downloads/Sitzverteilung_LT_2026.csv"]).exists():
        return None
    zeilen, sitze = _st_zeilen(pfad), _st_sitze()
    geo = json.loads(ST_GEO.read_text(encoding="utf-8")) if ST_GEO.exists() else None
    fehler = st_pruefe(zeilen, sitze, geo)
    if fehler:
        raise Pruefehler("Landtagswahl Sachsen-Anhalt 2026: " + "; ".join(fehler[:8]))
    vgl = json.loads(ST_VERGLEICH.read_text(encoding="utf-8")) if ST_VERGLEICH.exists() else {}

    def stimmen(d, vor):
        out = {}
        for st, b, gueltig in (("z", "F", "F.Gültige.Zweitstimmen"), ("e", "D", "D.Gültige.Erststimmen")):
            v = (vor or {}).get(st) or {}
            out[st] = [[kurz(p), n, r1(n / d[gueltig] * 100), r1(v.get(p))] for p, n in sorted(_st_parteien(d, b), key=lambda x: -x[1]) if n]
        return out

    def gebiet(d, vor=None):
        return {"s": stimmen(d, vor), "wb": d["A.Wahlberechtigte"], "w": d["B.Wähler"], "bet": r1(d["B.Wähler"] / d["A.Wahlberechtigte"] * 100),
                "bet_vor": r1((vor or {}).get("bet"))}

    land = zeilen[("LAN", "15", "")]
    g = gebiet(land, vgl.get("land"))
    g["brief"] = zeilen[("LAN", "15", "B")]["B.Wähler"]
    vs = vgl.get("sitze") or {}
    g["sitze"] = [[kurz(z["Partei"]), z["Sitze.insgesamt"], vs.get(z["Partei"])] for z in sitze if z["Partei"] != "Insgesamt" and z["Sitze.insgesamt"]]
    g["sitze_n"] = next(z["Sitze.insgesamt"] for z in sitze if z["Partei"] == "Insgesamt")
    g["sitze_direkt"] = [[kurz(z["Partei"]), z["Kreiswahlvorschlaege"]] for z in sitze if z["Partei"] != "Insgesamt" and z["Kreiswahlvorschlaege"]]
    g["sitze_hinweis"] = (f"Endgültige Sitzverteilung laut Statistischem Landesamt: {g['sitze_n']} Sitze, davon 41 Direktmandate"
                          + (f"; Vergleich: {vgl['sitze_n']} Sitze nach der Wahl 2021" if vgl.get("sitze_n") else ""))
    wk, kreise = {}, {}
    for (art, nr, lokal), d in sorted(zeilen.items()):
        if lokal:
            continue
        if art == "WKR":
            v = (vgl.get("wahlkreise") or {}).get(str(int(nr)))
            vor = {"z": {p: n / v["gueltig"] * 100 for p, n in v["z"].items()}} if v and v.get("gueltig") else None
            e = gebiet(d, vor)
            m = re.match(r"(.*?)\s*\(([^()]+)\)\s*$", d["Gewählt.im.Wahlkreis"])
            nach, _, vorname = m.group(1).partition(",")
            wk[str(int(nr))] = {"n": f"{int(nr)} {d['Name']}", **e, "direkt": {"name": f"{vorname.strip()} {nach.strip()}".strip(), "partei": kurz(m.group(2))}}
        elif art == "KRS":
            kreise[nr] = {"n": d["Name"], **gebiet(d)}
    quelle = {"name": "Statistisches Landesamt Sachsen-Anhalt, endgültiges Ergebnis der Landtagswahl 2026; Grenzen: © GeoBasis-DE / LVermGeo ST",
              "url": ST + "erg_land.html", "lizenz": "dl-de/by-2-0"}
    einheiten = [{"id": "kreis", "name": "Landkreise und kreisfreie Städte", "einzahl": "Kreis/Stadt", "art": "zaehlgebiet", "geo": "kreise-de", "werte": kreise}]
    if geo:
        einheiten.append({"id": "lwk", "name": "Landtagswahlkreise", "einzahl": "Landtagswahlkreis", "art": "wahlkreis", "geo": "landtagswahlkreise-st", "werte": wk})
    return {"g": g, "einheiten": einheiten, "quelle": quelle, "status": "endgültig", "stimmarten": [["z", "Zweitstimmen"], ["e", "Erststimmen"]],
            "system": ("Personalisierte Verhältniswahl mit Erst- und Zweitstimme, 41 Landtagswahlkreise; die Zweitstimmen bestimmen die Sitzverteilung "
                       "(mindestens 83 Sitze, Überhang- und Ausgleichsmandate möglich), Sperrklausel 5 %."),
            "vor": {"datum": "2021-06-06", "titel": "Landtagswahl 2021", "hinweis": "Vergleichswerte laut Statistischem Landesamt"}}


# ---------------------------------------------------------------- Register
# Je Land die amtlich eingelesenen Wahlen (Wahltag, Lesefunktion). Grenzen: (Schlüssel "geo" der Einheit, Datei unter app/geo) für globus.WAHL_GEO.
WAHLEN = {"DE-ST": [("2026-09-06", st_ltw26)]}
LADEN = [st_laden]
WAHL_GEO = [("landtagswahlkreise-st", "geo/landtagswahlkreise_st.geojson")]


def wahl(code, datum=None, kurz=lambda p: p):
    """(Wahltag, amtliches Ergebnis) für das Land `code` oder None. Mit `datum` (Wahltag laut Wahlartikel) die Wahl dieses Jahres,
    sonst oder wenn der Wahlartikel älter ist die jüngste amtlich eingelesene Wahl: die amtliche Datei hängt nicht am Wahlartikel."""
    liste = sorted(WAHLEN.get(code, []), reverse=True)
    for tag, f in liste:
        if not datum or tag[:4] == datum[:4] or tag > datum:
            w = f(kurz)
            return (tag, w) if w else None
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ohne-abruf", action="store_true")
    a = ap.parse_args(argv)
    for f in LADEN:
        f(not a.ohne_abruf)
    for code, jahr, f in sorted((c, tag[:4], f) for c, l in WAHLEN.items() for tag, f in l):
        w = f()
        if not w:
            print(f"{code} {jahr}: Quelldateien fehlen")
            continue
        g = w["g"]
        print(f"{code} {jahr}: geprüft, Beteiligung {g['bet']} % (vorher {g['bet_vor']}), "
              + ", ".join(f"{p} {x} %" for p, _, x, _ in g["s"]["z"][:6]) + f"; {g['sitze_n']} Sitze; "
              + ", ".join(f"{len(e['werte'])} {e['name']}" for e in w["einheiten"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
