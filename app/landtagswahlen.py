#!/usr/bin/env python3
"""Landtagswahlen aus den amtlichen Dateien der Landeswahlleitungen: Lesen, Prüfen, Aufbereiten für das Wahlregister.

Je Land eine Lesefunktion, die dieselbe Struktur liefert (siehe `wahl()`); `wahlen_daten.regional()` ersetzt damit den
Eintrag aus dem Wahlartikel. Jede Lesefunktion prüft die Quelle gegen sich selbst (Summen der Wahlkreise = Land, gültige
Stimmen = Summe der Parteien, Sitze, Direktmandate) und bricht bei einer Abweichung ab: lieber keine Wahl als eine falsche.

Aufruf (lädt fehlende Quelldateien und Grenzen, prüft, druckt eine Übersicht):
    python3 app/landtagswahlen.py [--ohne-abruf]

Sachsen-Anhalt 06.09.2026: Statistisches Landesamt Sachsen-Anhalt, endgültiges Ergebnis
(https://wahlergebnisse.sachsen-anhalt.de/wahlen/lt26/). Grenzen der Wahlkreise: © GeoBasis-DE / LVermGeo ST, dl-de/by-2-0.
Baden-Württemberg 08.03.2026 und Berlin 20.09.2026: Ergebnispräsentation des Statistischen Landesamts bzw. der Landeswahlleitung
(gemeinsamer Leser `praes_*`); Baden-Württemberg zusätzlich gegen die amtliche Downloaddatei abgeglichen.
Rheinland-Pfalz 22.03.2026 und Mecklenburg-Vorpommern 20.09.2026: Tabellen und Shape-Dateien der Landeswahlleiter (gemeinsame Form
`tab_*`). Neue Auszüge aus XLSX und Shape brauchen openpyxl, pyshp, pyproj, shapely; der Build liest nur die abgelegten Dateien.
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


# ---------------------------------------------------------------- Ergebnispräsentation (Baden-Württemberg, Berlin)
# Beide Länder veröffentlichen mit derselben Software: eine Seite je Gebiet mit der „Ergebnistabelle“ (Erst- und Zweitstimmen,
# Anzahl, Anteil, Gewinn und Verlust in Prozentpunkten), Tabellen der Gewählten und eine Kartendatei m_….json mit den Wahlkreisen.
# Der Auszug (Tabellen unverändert als Text) liegt je Wahl in wahlen/quellen/<kürzel>_praesentation.json.
PRAES = {
    "DE-BW": {"kuerzel": "bw_ltw26", "basis": "https://wahlen.statistik-bw.de/ltw26/", "start": "ergebnispraesentation.html",
              "wk": r"ergebnispraesentation_wahlkreis_(\d+)\.html", "wahltag": "2026-03-08", "wahlkreise": 70, "geo": "landtagswahlkreise-bw",
              "herausgeber": "Statistisches Landesamt Baden-Württemberg", "einzahl": "Landtagswahlkreis", "einheit": "Landtagswahlkreise",
              "lizenz": "Vervielfältigung und Verbreitung mit Quellenangabe gestattet (Impressum der Wahlpräsentation)",
              "system": ("Personalisierte Verhältniswahl mit Erst- und Zweitstimme (erstmals 2026), 70 Landtagswahlkreise; die Zweitstimmen bestimmen "
                         "die Sitzverteilung (mindestens 120 Sitze, Überhang- und Ausgleichsmandate möglich), Sperrklausel 5 %."),
              "vor": {"datum": "2021-03-14", "titel": "Landtagswahl 2021", "hinweis": "2021 gab es nur eine Stimme; Veränderung laut Statistischem Landesamt"}},
    "DE-BE": {"kuerzel": "be_agh26", "basis": "https://www.wahlen-berlin.de/wahlen/BE2026/AFSPRAES/agh/", "start": "ergebnisse.html",
              "zwischen": r"ergebnisse_bezirk_(\d+)\.html", "wk": r"ergebnisse_wahlkreis_(\d+)\.html", "wahltag": "2026-09-20", "wahlkreise": 78, "gewaehlte": "gewaehlte.html",
              "geo": "landtagswahlkreise-be", "herausgeber": "Landeswahlleitung Berlin / Amt für Statistik Berlin-Brandenburg",
              "einzahl": "Wahlkreis", "einheit": "Abgeordnetenhauswahlkreise", "name_ohne_nummer": True, "lizenz": "Vervielfältigung und Verbreitung mit Quellenangabe gestattet (Impressum wahlen-berlin.de)",
              "system": ("Personalisierte Verhältniswahl mit Erst- und Zweitstimme, 78 Wahlkreise in 12 Bezirken; die Zweitstimmen bestimmen die "
                         "Sitzverteilung (mindestens 130 Sitze, Überhang- und Ausgleichsmandate möglich), Sperrklausel 5 %."),
              "vor": {"datum": "2023-02-12", "titel": "Wiederholungswahl 2023", "hinweis": "Veränderung laut Landeswahlleitung"}},
}
PRAES_FEST = ("Wahlberechtigte", "Wählende", "Ungültige Stimmen", "Gültige Stimmen")


def praes_tabellen(seite):
    """[(Überschrift, [[Zelle, …], …])] aller Tabellen einer Seite, Zellen als Text."""
    out = []
    for t in re.findall(r"<table.*?</table>", seite, re.S):
        cap = re.search(r"<caption.*?</caption>", t, re.S)
        zeilen = [[_text(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", z, re.S)] for z in re.findall(r"<tr.*?</tr>", t, re.S)]
        out.append((_text(cap.group(0)) if cap else "", zeilen))
    return out


def praes_ergebnistabelle(seite):
    """(Überschrift, Zeilen [Merkmal, Bewerber, E Anzahl, E Anteil, E Veränderung, Z Anzahl, Z Anteil, Z Veränderung]) der Ergebnistabelle."""
    cap, zeilen = next((c, z) for c, z in praes_tabellen(seite) if c.startswith("Ergebnistabelle"))
    out = []
    for z in zeilen[2:]:
        if len(z) == 7:
            z = [z[0], ""] + z[1:]
        if len(z) != 8:
            raise Pruefehler(f"Ergebnistabelle: Zeile mit {len(z)} Zellen ({z[:2]})")
        out.append(z)
    return cap, out


def _de_zahl(t):
    """'7.764.858' -> 7764858, '+5,8' -> 5.8, '-' -> None."""
    t = (t or "").replace("%", "").replace("−", "-").strip()
    if t in ("", "-"):
        return None
    if re.fullmatch(r"[+-]?\d{1,3}(\.\d{3})*", t) or re.fullmatch(r"\d+", t):
        return int(t.replace(".", ""))
    return float(t.replace(".", "").replace(",", "."))


def praes_abrufen(spec, hole=None):
    """Auszug der Ergebnispräsentation: Land, alle Wahlkreise, Gewählte; dazu die Wahlkreisflächen als GeoJSON."""
    hole = hole or (lambda u: _hole(u).decode("utf-8"))
    b = spec["basis"]
    start = hole(b + spec["start"])
    seiten = [start] + [hole(b + m.group(0)) for m in sorted(set(re.finditer(spec["zwischen"], start)), key=lambda m: m.group(0))] if spec.get("zwischen") else [start]
    links = sorted({m.group(0): m.group(1) for s in seiten for m in re.finditer(spec["wk"], s)}.items(), key=lambda x: x[1])
    cap, land = praes_ergebnistabelle(start)
    out = {"quelle": b + spec["start"], "titel": cap, "land": land, "wahlkreise": {}, "gewaehlt": {}}
    for link, nr in links:
        c, z = praes_ergebnistabelle(hole(b + link))
        out["wahlkreise"][nr] = {"titel": c, "zeilen": z}
    gew = hole(b + spec["gewaehlte"]) if spec.get("gewaehlte") else start
    for c, z in praes_tabellen(gew):
        if c.startswith(("Gewählte in Wahlkreisen", "Gewählt im Wahlkreis")):
            out["gewaehlt"]["direkt"] = z[1:]
        elif c.startswith("Auf Listen Gewählte"):
            out["gewaehlt"]["liste"] = z[1:]
    karte = re.search(r"m_[0-9_]+\.json", start)
    feats = []
    for f in (json.loads(hole(b + karte.group(0)))["geoJSON"]["features"] if karte else []):
        rund = lambda c: [rund(x) for x in c] if isinstance(c[0], list) else [round(c[0], 4), round(c[1], 4)]
        feats.append({"type": "Feature", "properties": {"id": f["properties"]["gebietNr"], "name": f["properties"]["name"]},
                      "geometry": {"type": f["geometry"]["type"], "coordinates": rund(f["geometry"]["coordinates"])}})
    feats.sort(key=lambda f: f["properties"]["id"].zfill(6))
    geo = {"type": "FeatureCollection", "quelle": f"{spec['herausgeber']}, Wahlkreiskarte der Ergebnispräsentation ({b})", "features": feats}
    return out, geo


def _praes_gebiet(zeilen):
    """Tabelle -> {'wb', 'w', 'gueltig': {e, z}, 'ungueltig': {e, z}, 'bet_gv', 'p': [(Partei, Bewerber, eAnz, eGv, zAnz, zGv)]}."""
    d = {z[0]: z for z in zeilen}
    g = {"wb": _de_zahl(d["Wahlberechtigte"][5]), "w": _de_zahl(d["Wählende"][5]), "bet_gv": _de_zahl(d["Wählende"][7]),
         "gueltig": {"e": _de_zahl(d["Gültige Stimmen"][2]), "z": _de_zahl(d["Gültige Stimmen"][5])},
         "ungueltig": {"e": _de_zahl(d["Ungültige Stimmen"][2]), "z": _de_zahl(d["Ungültige Stimmen"][5])}, "p": []}
    for z in zeilen:
        if z[0] not in PRAES_FEST:
            g["p"].append((z[0], z[1], _de_zahl(z[2]), _de_zahl(z[4]), _de_zahl(z[5]), _de_zahl(z[7])))
    return g


def praes_pruefe(d, spec, geo=None):
    """Widersprüche des Auszugs als Liste von Sätzen (leer = stimmig)."""
    f = []
    for titel in [d["titel"]] + [w["titel"] for w in d["wahlkreise"].values()]:
        if not re.search(r"Endgültiges Ergebnis|Endergebnis", titel):
            f.append(f"kein endgültiges Ergebnis: {titel[-60:]}")
            break
    if len(d["wahlkreise"]) != spec["wahlkreise"]:
        f.append(f"{len(d['wahlkreise'])} statt {spec['wahlkreise']} Wahlkreise")
    land = _praes_gebiet(d["land"])
    gebiete = {nr: _praes_gebiet(w["zeilen"]) for nr, w in d["wahlkreise"].items()}
    for name, g in [("Land", land)] + sorted(gebiete.items()):
        for st, i in (("e", 2), ("z", 4)):
            s = sum(p[i] or 0 for p in g["p"])
            if s != g["gueltig"][st]:
                f.append(f"{name}: Summe der Parteien ({st}) = {s}, gültig = {g['gueltig'][st]}")
            if g["w"] != g["gueltig"][st] + g["ungueltig"][st]:
                f.append(f"{name}: Wählende ungleich gültige + ungültige Stimmen ({st})")
    for was, hol in (("Wahlberechtigte", lambda g: g["wb"]), ("Wählende", lambda g: g["w"]), ("gültige Erststimmen", lambda g: g["gueltig"]["e"]),
                     ("gültige Zweitstimmen", lambda g: g["gueltig"]["z"])):
        s = sum(hol(g) for g in gebiete.values())
        if s != hol(land):
            f.append(f"Summe der Wahlkreise {was} = {s}, Land = {hol(land)}")
    for p in land["p"]:
        if p[4] is not None:
            s = sum(q[4] or 0 for g in gebiete.values() for q in g["p"] if q[0] == p[0])
            if s != p[4]:
                f.append(f"Summe der Wahlkreise Zweitstimmen {p[0]} = {s}, Land = {p[4]}")
    direkt = {re.match(r"0*(\d+)", z[0]).group(1): z for z in d["gewaehlt"].get("direkt", [])}
    if len(direkt) != spec["wahlkreise"]:
        f.append(f"{len(direkt)} statt {spec['wahlkreise']} direkt Gewählte")
    for nr, g in gebiete.items():
        z = direkt.get(str(int(nr)))
        if not z:
            continue
        erst = max((p for p in g["p"] if p[2] is not None and p[1]), key=lambda p: p[2])
        if erst[0] != z[2] or erst[1] != z[1]:
            f.append(f"Wahlkreis {nr}: gewählt {z[1]} ({z[2]}), meiste Erststimmen {erst[1]} ({erst[0]})")
    if geo is not None and sorted(x["properties"]["id"] for x in geo["features"]) != sorted(d["wahlkreise"]):
        f.append("Grenzen: Wahlkreise der Karte passen nicht zu den Ergebnissen")
    return f


def praes_laden(code, abruf=True):
    spec = PRAES[code]
    p, g = QUELLEN / f"{spec['kuerzel']}_praesentation.json", GEO / (spec["geo"].replace("-", "_") + ".geojson")
    if (p.exists() and g.exists()) or not abruf:
        return
    d, geo = praes_abrufen(spec)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=0, sort_keys=True) + "\n", encoding="utf-8")
    g.write_text(json.dumps(geo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def praes_sitze(code, d):
    """[(Partei, Sitze, Direktmandate)] aus den Tabellen der Gewählten bzw. der amtlichen Datei der Gewählten."""
    spec, n, direkt = PRAES[code], {}, {}
    datei = QUELLEN / f"{spec['kuerzel']}_gewaehlte.csv"
    if datei.exists():                              # Baden-Württemberg: ltw26-gewaehlte.csv (Gebietsart WAHLKREIS = Direktmandat, LAND = Landesliste)
        with open(datei, encoding="utf-8", newline="") as f:
            for z in csv.DictReader(f, delimiter=";"):
                n[z["Wahlvorschlag-Kurzname"]] = n.get(z["Wahlvorschlag-Kurzname"], 0) + 1
                if z["Gebietsart"] == "WAHLKREIS":
                    direkt[z["Wahlvorschlag-Kurzname"]] = direkt.get(z["Wahlvorschlag-Kurzname"], 0) + 1
    else:
        for z in d["gewaehlt"].get("direkt", []):
            n[z[2]] = n.get(z[2], 0) + 1
            direkt[z[2]] = direkt.get(z[2], 0) + 1
        for z in d["gewaehlt"].get("liste", []):
            n[z[2]] = n.get(z[2], 0) + 1
    return sorted(((p, k, direkt.get(p, 0)) for p, k in n.items()), key=lambda x: -x[1])


def praes_wahl(code, kurz=lambda p: p):
    """Wahl aus dem Auszug der Ergebnispräsentation in der Struktur des Wahlregisters (wie st_ltw26)."""
    spec = PRAES[code]
    p, gp = QUELLEN / f"{spec['kuerzel']}_praesentation.json", GEO / (spec["geo"].replace("-", "_") + ".geojson")
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    geo = json.loads(gp.read_text(encoding="utf-8")) if gp.exists() else None
    fehler = praes_pruefe(d, spec, geo)
    sitze = praes_sitze(code, d)
    if sum(x[2] for x in sitze) != spec["wahlkreise"]:
        fehler.append(f"{sum(x[2] for x in sitze)} Direktmandate in der Liste der Gewählten statt {spec['wahlkreise']}")
    if fehler:
        raise Pruefehler(f"{code} {spec['wahltag'][:4]}: " + "; ".join(fehler[:8]))

    def gebiet(zeilen):
        g = _praes_gebiet(zeilen)
        s = {}
        for st, i in (("z", 4), ("e", 2)):
            l = []
            for q in sorted((q for q in g["p"] if q[i]), key=lambda q: -q[i]):
                anteil = q[i] / g["gueltig"][st] * 100
                l.append([kurz("Sonstige" if q[0] == "Übrige" else q[0]), q[i], r1(anteil), r1(anteil - q[i + 1]) if q[i + 1] is not None else None])
            s[st] = l
        bet = g["w"] / g["wb"] * 100
        return {"s": s, "wb": g["wb"], "w": g["w"], "bet": r1(bet), "bet_vor": r1(bet - g["bet_gv"]) if g["bet_gv"] is not None else None}

    g = gebiet(d["land"])
    g["sitze"] = [[kurz(x[0]), x[1], None] for x in sitze]
    g["sitze_n"] = sum(x[1] for x in sitze)
    g["sitze_direkt"] = [[kurz(x[0]), x[2]] for x in sitze if x[2]]
    g["sitze_hinweis"] = f"Sitze nach der Liste der Gewählten ({spec['herausgeber']}): {g['sitze_n']} Sitze, davon {spec['wahlkreise']} Direktmandate"
    direkt = {re.match(r"0*(\d+)", z[0]).group(1): z for z in d["gewaehlt"]["direkt"]}
    wk = {}
    for nr, w in sorted(d["wahlkreise"].items()):
        z = direkt[str(int(nr))]
        nach, _, vorname = z[1].partition(",")
        name = re.match(r"Ergebnistabelle .*?, (\d.*?) (?:Endgültiges Ergebnis|Amtliches Endergebnis)", w["titel"]).group(1)
        wk[nr] = {"n": re.sub(r"^0*(\d+) - ", "" if spec.get("name_ohne_nummer") else r"\1 ", name), **gebiet(w["zeilen"]), "direkt": {"name": f"{vorname.strip()} {nach.strip()}".strip(), "partei": kurz(z[2])}}
    quelle = {"name": f"{spec['herausgeber']}, endgültiges Ergebnis (Ergebnispräsentation); Grenzen: Wahlkreiskarte der Ergebnispräsentation",
              "url": spec["basis"] + spec["start"], "lizenz": spec["lizenz"]}
    einheiten = [{"id": "lwk", "name": spec["einheit"], "einzahl": spec["einzahl"], "art": "wahlkreis", "geo": spec["geo"], "werte": wk}] if geo else []
    return {"g": g, "einheiten": einheiten, "quelle": quelle, "status": "endgültig", "stimmarten": [["z", "Zweitstimmen"], ["e", "Erststimmen"]],
            "system": spec["system"], "vor": spec["vor"]}


# Baden-Württemberg: amtliche Downloaddateien als zweite Quelle (Zeilen LAND und WAHLKREIS der Ergebnisdatei, Liste der Gewählten)
BW_PARTEIEN = {1: "GRÜNE", 2: "CDU", 3: "SPD", 4: "FDP", 5: "AfD", 6: "Die Linke", 7: "FREIE WÄHLER", 8: "Die PARTEI", 9: "dieBasis", 10: "KlimalisteBW",
               11: "ÖDP", 12: "Volt", 13: "Bündnis C", 14: "PdH", 15: "Verjüngungsforschung", 16: "BSW", 17: "Die Gerechtigkeitspartei", 18: "PDR",
               19: "PdF", 20: "Tierschutzpartei", 21: "WerteUnion", 22: "Übrige"}       # Hinweise-Datensatzbeschreibung.pdf; D22 = anderer Kreiswahlvorschlag
BW_ERGEBNISSE, BW_GEWAEHLTE = QUELLEN / "bw_ltw26_land_wahlkreise.csv", QUELLEN / "bw_ltw26_gewaehlte.csv"


def bw_laden(abruf=True):
    praes_laden("DE-BW", abruf)
    b = PRAES["DE-BW"]["basis"]
    if not BW_ERGEBNISSE.exists() and abruf:        # 12.740 Zeilen bis zum Wahlbezirk; im Repository nur Kopf, Land und Wahlkreise
        zeilen = _hole(b + "ltw26-ergebnisse.csv").decode("utf-8-sig").splitlines()
        BW_ERGEBNISSE.write_text("\n".join([zeilen[0]] + [z for z in zeilen[1:] if z.split(";")[5] in ("LAND", "WAHLKREIS")]) + "\n", encoding="utf-8")
    if not BW_GEWAEHLTE.exists() and abruf:
        BW_GEWAEHLTE.write_text(_hole(b + "ltw26-gewaehlte.csv").decode("cp1252").replace("\r\n", "\n"), encoding="utf-8")


def bw_abgleich(d):
    """Vergleich der Ergebnispräsentation mit der amtlichen Downloaddatei: Liste der Abweichungen (leer = deckungsgleich)."""
    f = []
    with open(BW_ERGEBNISSE, encoding="utf-8", newline="") as fh:
        zeilen = list(csv.DictReader(fh, delimiter=";"))
    bekannt, uebrige = set(BW_PARTEIEN.values()) - {"Übrige"}, 0
    for z in zeilen:
        if z["gemeldete Wahlbezirke"] != z["Anzahl Wahlbezirke"]:
            f.append(f"{z['Gebietsname']}: {z['gemeldete Wahlbezirke']} von {z['Anzahl Wahlbezirke']} Wahlbezirken gemeldet")
        g = _praes_gebiet(d["land"] if z["Gebietsart"] == "LAND" else d["wahlkreise"][z["Gebietsnummer"]]["zeilen"])
        tab = {(p[0], "D"): p[2] for p in g["p"]} | {(p[0], "F"): p[4] for p in g["p"]}
        soll = [("Wahlberechtigte", int(z["Wahlberechtigte gesamt (A)"]), g["wb"]), ("Wählende", int(z["Waehler gesamt (B)"]), g["w"]),
                ("gültige Erststimmen", int(z["Erststimmen gueltige (D)"]), g["gueltig"]["e"]), ("gültige Zweitstimmen", int(z["Zweitstimmen gueltige (F)"]), g["gueltig"]["z"])]
        for b in "DF":
            for nr, partei in BW_PARTEIEN.items():
                v = z.get(f"{b}{nr}")
                if not v or (z["Gebietsart"] == "LAND" and nr == 22):
                    continue
                if nr == 22 and z["Gebietsart"] != "LAND":
                    # D22 = übrige Kreiswahlvorschläge: die Wahlkreisseite nennt sie mit eigenem Namen statt als „Übrige“
                    ist = sum(p[2] or 0 for p in g["p"] if p[0] not in bekannt)
                    uebrige += int(v)
                else:
                    ist = tab.get((partei, b)) or 0
                soll.append((f"{b}{nr} {partei}", int(v), ist))
        f += [f"{z['Gebietsname']}: {was} Datei {a}, Präsentation {b}" for was, a, b in soll if a != b]
    land = {p[0]: p[2] for p in _praes_gebiet(d["land"])["p"]}.get("Übrige") or 0
    if land != uebrige:
        f.append(f"Land: Übrige Erststimmen {land}, Summe D22 der Wahlkreise {uebrige}")
    return f


def bw_ltw26(kurz=lambda p: p):
    """Landtagswahl Baden-Württemberg 08.03.2026: Land, 70 Wahlkreise, Sitze; Ergebnispräsentation gegen die amtliche Downloaddatei geprüft."""
    p = QUELLEN / "bw_ltw26_praesentation.json"
    if p.exists() and BW_ERGEBNISSE.exists():
        f = bw_abgleich(json.loads(p.read_text(encoding="utf-8")))
        if f:
            raise Pruefehler("Landtagswahl Baden-Württemberg 2026, Abgleich mit ltw26-ergebnisse.csv: " + "; ".join(f[:8]))
    return praes_wahl("DE-BW", kurz)


def be_agh26(kurz=lambda p: p):
    """Wahl zum Abgeordnetenhaus von Berlin 20.09.2026: Land, 78 Wahlkreise, Sitze."""
    return praes_wahl("DE-BE", kurz)


# ---------------------------------------------------------------- Tabellen der Landeswahlleitungen (Rheinland-Pfalz, Mecklenburg-Vorpommern)
# Beide Länder liefern Tabellen je Wahlkreis und amtliche Grenzen als Shape. Die Lesefunktionen (rp_lesen, mv_lesen) bringen sie in
# eine gemeinsame Form; Prüfung (tab_pruefe) und Aufbereitung (tab_wahl) sind für beide gleich.
#   {"land": G, "wahlkreise": {nr: G + {"name"}}, "direkt": {nr: [Name, Partei]}, "sitze": [[Partei, Sitze, Direktmandate, Sitze Vorwahl]]}
#   G = {"wb", "w", "e": {"ungueltig", "gueltig", "p": {Partei: Stimmen}}, "z": {…}, "vor": {"bet", "e": {Partei: %}, "z": {Partei: %}}}
TAB = {
    "DE-RP": {"kuerzel": "rp_ltw26", "wahltag": "2026-03-22", "wahlkreise": 52, "geo": "landtagswahlkreise-rp", "e": "Wahlkreisstimmen", "z": "Landesstimmen",
              "herausgeber": "Landeswahlleiter Rheinland-Pfalz", "url": "https://www.wahlen.rlp.de/landtagswahl/ergebnisse",
              "lizenz": "amtliches Endergebnis des Landeswahlleiters; Grenzen aus BKG VG250 (dl-de/by-2-0) und Stadtbezirken Trier (dl-de/by-2-0)",
              "system": ("Personalisierte Verhältniswahl mit Wahlkreis- und Landesstimme, 52 Wahlkreise; die Landesstimmen bestimmen die Sitzverteilung "
                         "(mindestens 101 Sitze, Überhang- und Ausgleichsmandate möglich), Sperrklausel 5 %."),
              "vor": {"datum": "2021-03-14", "titel": "Landtagswahl 2021",
                      "hinweis": "Vergleich nur für das Land; die Wahlkreise wurden zur Wahl 2026 teils neu zugeschnitten"}},
    "DE-MV": {"kuerzel": "mv_ltw26", "wahltag": "2026-09-20", "wahlkreise": 36, "geo": "landtagswahlkreise-mv", "e": "Erststimmen", "z": "Zweitstimmen",
              "herausgeber": "Landeswahlleiter Mecklenburg-Vorpommern", "url": "https://www.laiv-mv.de/Wahlen/Landtagswahlen/2026/Ergebnisse/",
              "lizenz": "amtliches Endergebnis, © Der Landeswahlleiter Mecklenburg-Vorpommern; Grenzen aus BKG VG250 (dl-de/by-2-0) und statistischen Bezirken Rostock (CC0 1.0)",
              "system": ("Personalisierte Verhältniswahl mit Erst- und Zweitstimme, 36 Wahlkreise; die Zweitstimmen bestimmen die Sitzverteilung "
                         "(71 Sitze, Überhang- und Ausgleichsmandate möglich), Sperrklausel 5 %."),
              "vor": {"datum": "2021-09-26", "titel": "Landtagswahl 2021", "hinweis": "Vergleichswerte laut Statistischem Amt Mecklenburg-Vorpommern"}},
}


def shape_geojson(zip_bytes, stamm, eigenschaften, toleranz=80):
    """Amtliche Shape-Datei (ETRS89/UTM) -> GeoJSON in WGS84, vereinfacht (Toleranz in Metern) und auf 4 Stellen gerundet.

    Braucht pyshp, pyproj und shapely (nur beim Abruf der Grenzen; der Build liest das abgelegte GeoJSON)."""
    import io
    import zipfile
    import shapefile
    from pyproj import CRS, Transformer
    from shapely.geometry import mapping, shape
    from shapely.ops import transform
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    pre = next(n[:-4] for n in z.namelist() if n.endswith(stamm + ".shp"))
    r = shapefile.Reader(shp=io.BytesIO(z.read(pre + ".shp")), dbf=io.BytesIO(z.read(pre + ".dbf")), shx=io.BytesIO(z.read(pre + ".shx")), encoding="cp1252")
    nach = Transformer.from_crs(CRS.from_wkt(z.read(pre + ".prj").decode("utf-8")), "EPSG:4326", always_xy=True).transform
    out = []
    for sr in r.iterShapeRecords():
        g = transform(nach, shape(sr.shape.__geo_interface__).buffer(0).simplify(toleranz, preserve_topology=True))
        m = mapping(g)
        polys = [m["coordinates"]] if m["type"] == "Polygon" else m["coordinates"]
        koord = [[[[round(x, 4), round(y, 4)] for x, y in ring] for ring in p] for p in polys]
        out.append({"type": "Feature", "properties": eigenschaften(sr.record.as_dict()), "geometry": {"type": "MultiPolygon", "coordinates": koord}})
    return {"type": "FeatureCollection", "features": sorted(out, key=lambda f: int(f["properties"]["id"]))}


# ---------------------------------------------------------------- Wahlkreisgrenzen aus offenen Geodaten (E7, Rheinland-Pfalz und Mecklenburg-Vorpommern)
# Die Landeswahlleitungen geben ihre Wahlkreis-Shapes ohne Lizenz heraus. Die Wahlkreise bestehen aber aus ganzen Gemeinden; nur
# einige Städte sind auf mehrere Wahlkreise geteilt. Deshalb werden die Grenzen aus den Gemeinden der BKG-Verwaltungsgebiete
# (VG250, dl-de/by-2-0) zusammengesetzt, geteilte Städte aus offenen Stadtteilgrenzen der Städte. Fehlen solche, steht die Stadt als
# ein Gebiet auf der Karte (Schlüssel "S" + Gemeindeschlüssel) mit dem amtlichen Ergebnis der Stadt.
# Zuordnungen: wahlen/quellen/<land>_ltw26_gemeinden_wahlkreise.csv (ags; gemeinde; wahlkreis, bei geteilten Städten "27|28|29")
# und <land>_ltw26_stadtteile_wahlkreise.csv (ags; stadtteil; wahlkreis; anteil). Beide wurden am 11.11.2026 durch Verschneiden mit
# der amtlichen Wahlkreiseinteilung ermittelt; "anteil" ist der Flächenanteil des Stadtteils im zugeordneten Wahlkreis.
BKG_VG250 = "https://daten.gdz.bkg.bund.de/produkte/vg/vg250_ebenen_0101/aktuell/vg250_01-01.utm32s.shape.ebenen.zip"
BKG_QUELLE = "© BKG (2026) dl-de/by-2-0 (Verwaltungsgebiete 1:250 000, Stand 01.01.2026)"
STADTTEILE = {
    "07211000": {"url": "https://www.geoportal.rlp.de/spatial-objects/470/collections/ms:grenze_stadtbezirke/items?f=json&limit=500",
                 "name": "STADTBEZI1", "quelle": "Stadt Trier, Stadtbezirke (dl-de/by-2-0)"},
    "13003000": {"url": "https://geo.sv.rostock.de/download/opendata/statistische_bezirke/statistische_bezirke.json",
                 "name": "bezeichnung", "quelle": "Hanse- und Universitätsstadt Rostock, statistische Bezirke (CC0 1.0)"},
}


def _vg250_gemeinden(praefix):
    """{AGS: [Name, Geometrie in ETRS89/UTM32]} der Gemeinden eines Landes aus VG250 (Zwischenspeicher ~/.cache/sphaerae)."""
    import io
    import os
    import zipfile
    import shapefile
    from shapely.geometry import shape
    cache = Path(os.environ.get("SPHAERAE_CACHE", Path.home() / ".cache" / "sphaerae")) / "vg250_ebenen_0101.zip"
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(_hole(BKG_VG250))
    z = zipfile.ZipFile(cache)
    pre = next(n[:-4] for n in z.namelist() if n.endswith("VG250_GEM.shp"))
    r = shapefile.Reader(shp=io.BytesIO(z.read(pre + ".shp")), dbf=io.BytesIO(z.read(pre + ".dbf")), shx=io.BytesIO(z.read(pre + ".shx")), encoding="utf-8")
    return {sr.record["AGS"]: [sr.record["GEN"], shape(sr.shape.__geo_interface__).buffer(0)] for sr in r.iterShapeRecords()
            if sr.record["GF"] == 4 and sr.record["AGS"].startswith(praefix)}


def wk_zuordnung(kurz):
    """Zuordnungen aus wahlen/quellen: ({AGS: [Name, [Wahlkreise]]}, {AGS: {Stadtteil: Wahlkreis}})."""
    with open(QUELLEN / f"{kurz}_ltw26_gemeinden_wahlkreise.csv", encoding="utf-8", newline="") as f:
        gem = {z["ags"]: [z["gemeinde"], z["wahlkreis"].split("|")] for z in csv.DictReader(f, delimiter=";")}
    teile = {}
    with open(QUELLEN / f"{kurz}_ltw26_stadtteile_wahlkreise.csv", encoding="utf-8", newline="") as f:
        for z in csv.DictReader(f, delimiter=";"):
            teile.setdefault(z["ags"], {})[z["stadtteil"]] = z["wahlkreis"]
    return gem, teile


def wk_staedte(kurz):
    """Geteilte Städte ohne offene Stadtteilgrenzen: {"S" + AGS: [Name, [Wahlkreise]]} (auf der Karte ein Gebiet)."""
    gem, teile = wk_zuordnung(kurz)
    return {"S" + a: [n, wks] for a, (n, wks) in sorted(gem.items()) if len(wks) > 1 and a not in teile}


def wk_aus_gemeinden(kurz, praefix, namen, toleranz=80):
    """Wahlkreisgrenzen als GeoJSON: Gemeinden (VG250) je Wahlkreis vereinigt, geteilte Städte nach Stadtteilen oder als ein Gebiet.

    `namen` = {Wahlkreis: Name}. Braucht pyshp, pyproj und shapely (nur beim Abruf der Grenzen)."""
    from pyproj import Transformer
    from shapely.geometry import mapping, shape
    from shapely.ops import transform, unary_union
    gem, teile = wk_zuordnung(kurz)
    vg = _vg250_gemeinden(praefix)
    if set(vg) != set(gem):
        raise Pruefehler(f"{kurz}: Gemeinden der Zuordnung ({len(gem)}) und VG250 ({len(vg)}) weichen ab: {sorted(set(vg) ^ set(gem))[:5]}")
    nach_utm = Transformer.from_crs("EPSG:4326", "EPSG:25832", always_xy=True).transform
    flaechen, staedte = {}, {}
    for ags, (name, wks) in gem.items():
        g = vg[ags][1]
        if len(wks) == 1:
            flaechen.setdefault(wks[0], []).append(g)
        elif ags in teile:
            st = STADTTEILE[ags]
            fc = json.loads(_hole(st["url"]))
            gefunden = set()
            for f in fc["features"]:
                n = f["properties"][st["name"]]
                if n not in teile[ags]:
                    raise Pruefehler(f"{kurz}: Stadtteil {n} ({ags}) ohne Wahlkreis in der Zuordnung")
                gefunden.add(n)
                flaechen.setdefault(teile[ags][n], []).append(transform(nach_utm, shape(f["geometry"]).buffer(0)).intersection(g))
            if gefunden != set(teile[ags]):
                raise Pruefehler(f"{kurz}: Stadtteile {sorted(set(teile[ags]) - gefunden)} ({ags}) fehlen in der Quelle")
        else:
            staedte["S" + ags] = [name, wks, g]
    zu_wgs = Transformer.from_crs("EPSG:25832", "EPSG:4326", always_xy=True).transform

    def feature(eig, g):
        g = transform(zu_wgs, g.buffer(0).simplify(toleranz, preserve_topology=True))
        m = mapping(g)
        polys = [m["coordinates"]] if m["type"] == "Polygon" else m["coordinates"]
        return {"type": "Feature", "properties": eig,
                "geometry": {"type": "MultiPolygon", "coordinates": [[[[round(x, 4), round(y, 4)] for x, y in ring] for ring in p] for p in polys]}}
    out = [feature({"id": nr, "name": namen.get(nr, nr)}, unary_union(gs)) for nr, gs in sorted(flaechen.items(), key=lambda x: int(x[0]))]
    out += [feature({"id": sid, "name": name, "teil": wks}, g) for sid, (name, wks, g) in sorted(staedte.items())]
    return {"type": "FeatureCollection", "quelle": BKG_QUELLE + "; " + "; ".join(STADTTEILE[a]["quelle"] for a in sorted(teile)), "features": out}


def tab_pruefe(d, spec, geo=None):
    """Widersprüche der Tabellen als Liste von Sätzen (leer = stimmig)."""
    f = []
    if len(d["wahlkreise"]) != spec["wahlkreise"]:
        f.append(f"{len(d['wahlkreise'])} statt {spec['wahlkreise']} Wahlkreise")
    for name, g in [("Land", d["land"])] + sorted(d["wahlkreise"].items(), key=lambda x: int(x[0])):
        for st in "ez":
            s = sum(g[st]["p"].values())
            if s != g[st]["gueltig"]:
                f.append(f"{name}: Summe der Parteien ({st}) = {s}, gültig = {g[st]['gueltig']}")
            if g["w"] != g[st]["gueltig"] + g[st]["ungueltig"]:
                f.append(f"{name}: Wählende ungleich gültige + ungültige Stimmen ({st})")
        if not 0 < g["w"] <= g["wb"]:
            f.append(f"{name}: Wählende {g['w']} bei {g['wb']} Wahlberechtigten")
    wk = d["wahlkreise"].values()
    for was, hol in (("Wahlberechtigte", lambda g: g["wb"]), ("Wählende", lambda g: g["w"])):
        if sum(hol(g) for g in wk) != hol(d["land"]):
            f.append(f"Summe der Wahlkreise {was} = {sum(hol(g) for g in wk)}, Land = {hol(d['land'])}")
    for st in "ez":
        for p, n in d["land"][st]["p"].items():
            s = sum(g[st]["p"].get(p, 0) for g in wk)
            if s != n:
                f.append(f"Summe der Wahlkreise {p} ({st}) = {s}, Land = {n}")
    if set(d["direkt"]) != set(d["wahlkreise"]):
        f.append(f"{len(d['direkt'])} direkt Gewählte für {len(d['wahlkreise'])} Wahlkreise")
    direkt = {}
    for nr, (name, partei) in d["direkt"].items():
        direkt[partei] = direkt.get(partei, 0) + 1
        e = d["wahlkreise"].get(nr, {}).get("e", {}).get("p") or {}
        if e and max(e, key=e.get) != partei:
            f.append(f"Wahlkreis {nr}: gewählt {name} ({partei}), meiste Stimmen {max(e, key=e.get)}")
    for p, n, dm, _ in d["sitze"]:
        if dm != direkt.get(p, 0):
            f.append(f"Sitze {p}: {dm} Direktmandate, in den Wahlkreisen gewählt {direkt.get(p, 0)}")
        if dm > n:
            f.append(f"Sitze {p}: {dm} Direktmandate bei {n} Sitzen")
    staedte = d.get("staedte") or {}
    for sid, g in staedte.items():
        if set(g["teil"]) - set(d["wahlkreise"]):
            f.append(f"{g['name']}: Wahlkreise {g['teil']} nicht in den Ergebnissen")
        for st in "ez":
            if sum(g[st]["p"].values()) != g[st]["gueltig"] or g["w"] != g[st]["gueltig"] + g[st]["ungueltig"]:
                f.append(f"{g['name']}: Stimmen ({st}) nicht stimmig")
    if geo is not None:
        ids = {x["properties"]["id"] for x in geo["features"]}
        flaeche = ids - set(staedte)
        if flaeche - set(d["wahlkreise"]) or {i for i in ids if i.startswith("S")} != set(staedte):
            f.append("Grenzen: Wahlkreise der Karte passen nicht zu den Ergebnissen")
        ohne = set(d["wahlkreise"]) - flaeche - {nr for g in staedte.values() for nr in g["teil"]}
        if ohne:
            f.append(f"Grenzen: Wahlkreise {sorted(ohne, key=int)} ohne Fläche auf der Karte")
    return f


def tab_wahl(code, d, kurz=lambda p: p):
    """Wahl aus der gemeinsamen Tabellenform in der Struktur des Wahlregisters (wie st_ltw26)."""
    spec = TAB[code]
    gp = GEO / (spec["geo"].replace("-", "_") + ".geojson")
    geo = json.loads(gp.read_text(encoding="utf-8")) if gp.exists() else None
    fehler = tab_pruefe(d, spec, geo)
    if fehler:
        raise Pruefehler(f"{code} {spec['wahltag'][:4]}: " + "; ".join(fehler[:8]))

    def gebiet(g):
        vor = g.get("vor") or {}
        s = {st: [[kurz(p), n, r1(n / g[st]["gueltig"] * 100), r1((vor.get(st) or {}).get(p))] for p, n in sorted(g[st]["p"].items(), key=lambda x: -x[1]) if n]
             for st in "ze"}
        return {"s": s, "wb": g["wb"], "w": g["w"], "bet": r1(g["w"] / g["wb"] * 100), "bet_vor": r1(vor.get("bet"))}

    g = gebiet(d["land"])
    g["sitze"] = [[kurz(p), n, v] for p, n, _, v in d["sitze"] if n]
    g["sitze_n"] = sum(n for _, n, _, _ in d["sitze"])
    g["sitze_direkt"] = [[kurz(p), dm] for p, _, dm, _ in d["sitze"] if dm]
    vor_n = sum(v or 0 for _, _, _, v in d["sitze"])
    g["sitze_hinweis"] = (f"Sitze laut {spec['herausgeber']}: {g['sitze_n']} Sitze, davon {spec['wahlkreise']} Direktmandate"
                          + (f"; Vergleich: {vor_n} Sitze nach der Wahl {spec['vor']['datum'][:4]}" if vor_n else ""))
    wk = {nr: {"n": f"{nr} {w['name']}", **gebiet(w), "direkt": {"name": d["direkt"][nr][0], "partei": kurz(d["direkt"][nr][1])}}
          for nr, w in sorted(d["wahlkreise"].items(), key=lambda x: int(x[0]))}
    for sid, s in sorted((d.get("staedte") or {}).items()):
        t = [str(x) for x in sorted(map(int, s["teil"]))]
        wk[sid] = {"n": f"{s['name']} (Wahlkreise {', '.join(t[:-1])} und {t[-1]})", **gebiet(s), "stadt": True, "teil": t}
    grenzen = (geo or {}).get("quelle") or "amtliche Wahlkreisgeometrie"
    quelle = {"name": f"{spec['herausgeber']}, endgültiges Ergebnis; Grenzen: {grenzen}", "url": spec["url"], "lizenz": spec["lizenz"]}
    einheiten = [{"id": "lwk", "name": "Landtagswahlkreise", "einzahl": "Landtagswahlkreis", "art": "wahlkreis", "geo": spec["geo"], "anzahl": len(d["wahlkreise"]), "werte": wk}] if geo else []
    return {"g": g, "einheiten": einheiten, "quelle": quelle, "status": "endgültig", "stimmarten": [["z", spec["z"]], ["e", spec["e"]]],
            "system": spec["system"], "vor": spec["vor"]}


def _xlsx_zeilen(daten, blatt=None):
    """Zeilen eines Tabellenblatts (Werte, ohne Formeln)."""
    import io
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(daten), read_only=True, data_only=True)
    ws = wb[blatt] if blatt else wb.worksheets[0]
    ws.reset_dimensions()
    return [list(z) for z in ws.iter_rows(values_only=True)]


# Rheinland-Pfalz: Ergebnisdateien des Landeswahlleiters (XLSX je Ebene), Gewählte von der Ergebnisseite, Shape der Wahlkreise
RP = "https://www.wahlen.rlp.de/"
RP_DATEIEN = RP + "fileadmin/wahlen.rlp.de/dokumente-wahlen/ltw/"
RP_EINZEL = {"Bastian Ruhl", "Yunus Emre"}          # Einzelbewerber stehen mit ihrem Namen in der Kopfzeile
RP_NAMEN_2021 = {"AFD": "AfD", "DIE LINKE": "Die Linke", "VOLT": "Volt"}


def rp_tabelle(zeilen):
    """Blatt LW_2026_WK bzw. LW_2026_LK_KS -> (Kopf, Datenzeilen) als flache Tabelle: Schlüssel, Name, A, B, C, D, D:<Partei>…, E, F, F:<Partei>…"""
    kz = next(i for i, z in enumerate(zeilen) if z and "A1" in z and "D1" in z)
    namen = zeilen[kz - 2]
    kopf, spalten = ["Schluessel", "Name"], []
    for i, k in enumerate(zeilen[kz]):
        if isinstance(k, str) and re.fullmatch(r"[A-F]\d*", k) and k not in ("A1", "A2", "A3", "B1"):
            partei = re.sub(r"\s+", " ", str(namen[i])).strip() if re.fullmatch(r"[DF]\d+", k) else None
            kopf.append(f"{k[0]}:{partei}" if partei else k)
            spalten.append(i)
    daten = [[re.sub(r"\s+", " ", str(z[0])).strip(), re.sub(r",? ?WK$", "", str(z[2]).strip())] + [z[i] if z[i] is not None else "" for i in spalten]
             for z in zeilen[kz + 1:] if z and z[1] == "G" and z[2]]
    return kopf, daten


def rp_vergleich(zeilen_wk21):
    """Landesergebnis 2021 aus dem Blatt Wahlkreisergebnisse der amtlichen Datei: Anteile der Wahlkreis- und Landesstimmen, Beteiligung."""
    namen = zeilen_wk21[next(i for i, z in enumerate(zeilen_wk21) if z and "Wahlkreisstimmenergebnis" in z) + 1]
    land = next(z for z in zeilen_wk21 if z and z[2] == "Landesergebnis Rheinland-Pfalz")
    e0, z0 = [i for i, n in enumerate(namen) if n == "ungültig"]        # je Stimmart: ungültig, gültig, dann die Parteien
    out = {"wahl": "2021-03-14", "bet": round(land[7] / land[3] * 100, 2), "e": {}, "z": {}}
    for st, von, bis in (("e", e0, z0), ("z", z0, len(namen))):
        gueltig = land[next(i for i in range(von, bis) if namen[i] == "gültig")]
        for i in range(von, bis):
            n = namen[i]
            if isinstance(n, str) and n.strip() and n not in ("ungültig", "gültig") and isinstance(land[i], (int, float)) and land[i]:
                n = re.sub(r"\s+", " ", n).strip()
                out[st][RP_NAMEN_2021.get(n, n)] = round(land[i] / gueltig * 100, 2)
    return out


def rp_gewaehlte(seite):
    """{"direkt": {Wahlkreis: [Name, Partei]}, "liste": [[Name, Partei]]} aus den beiden Tabellen der Seite der Gewählten."""
    out = {"direkt": {}, "liste": []}
    for tb in re.findall(r"(?s)<table.*?</table>", seite):
        zeilen = [[_text(c) for c in re.findall(r"(?s)<t[dh][^>]*>(.*?)</t[dh]>", z)] for z in re.findall(r"(?s)<tr[^>]*>(.*?)</tr>", tb)]
        if not zeilen or len(zeilen[0]) != 3:
            continue
        for z in zeilen[1:]:
            if zeilen[0][0] == "Wahlkreis":
                out["direkt"][str(int(z[0]))] = [z[1], z[2]]
            elif zeilen[0][0] == "Listenplatz":
                out["liste"].append([z[1], z[2]])
    return out


def rp_laden(abruf=True):
    """Fehlende Quelldateien und Grenzen holen (Tabellen als CSV-Auszug der amtlichen XLSX-Dateien)."""
    q = {x: QUELLEN / f"rp_ltw26_{x}" for x in ("wahlkreise.csv", "land.csv", "gewaehlte.json", "vergleich_2021.json")}
    for ziel, datei in ((q["wahlkreise.csv"], "Endgueltiges_Ergebnis_LW_2026_Wahlkreise.xlsx"), (q["land.csv"], "Endgueltiges_Ergebnis_LW_2026_LK_KS.xlsx")):
        if not ziel.exists() and abruf:
            kopf, daten = rp_tabelle(_xlsx_zeilen(_hole(RP_DATEIEN + "Ergebnisdateien/2026/" + datei)))
            if ziel == q["land.csv"]:
                daten = [z for z in daten if z[1] == "RLP"]
            with open(ziel, "w", encoding="utf-8", newline="") as f:
                csv.writer(f, delimiter=";", lineterminator="\n").writerows([kopf] + daten)
    if not q["gewaehlte.json"].exists() and abruf:
        q["gewaehlte.json"].write_text(json.dumps(rp_gewaehlte(_hole(RP + "landtagswahl/ergebnisse/gewaehlte").decode("utf-8")), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if not q["vergleich_2021.json"].exists() and abruf:
        v = rp_vergleich(_xlsx_zeilen(_hole(RP_DATEIEN + "Ergebnisdateien/2021/LW2021_Endgueltiges_Ergebnis.xlsx"), "Wahlkreisergebnisse"))
        q["vergleich_2021.json"].write_text(json.dumps(v, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    st = QUELLEN / "rp_ltw26_staedte.csv"
    if not st.exists() and abruf:
        kreise = {sid[3:6] for sid in wk_staedte("rp")}           # kreisfreie Städte: Kreisschlüssel 07xxx -> "xxx"
        kopf, daten = rp_tabelle(_xlsx_zeilen(_hole(RP_DATEIEN + "Ergebnisdateien/2026/Endgueltiges_Ergebnis_LW_2026_LK_KS.xlsx")))
        with open(st, "w", encoding="utf-8", newline="") as f:
            csv.writer(f, delimiter=";", lineterminator="\n").writerows([kopf] + [z for z in daten if z[0] in kreise])
    gp = GEO / "landtagswahlkreise_rp.geojson"
    if not gp.exists() and abruf and q["wahlkreise.csv"].exists():
        with open(q["wahlkreise.csv"], encoding="utf-8", newline="") as f:
            namen = {str(int(z["Schluessel"].split()[1])): re.sub(r",? ?WK$", "", z["Name"]) for z in csv.DictReader(f, delimiter=";")}
        gp.write_text(json.dumps(wk_aus_gemeinden("rp", "07", namen), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def _rp_gebiet(z):
    def stimmen(b, ung):
        p = {}
        for k, v in z.items():
            if k.startswith(b + ":") and v != "":
                name = k[2:]
                name = "Einzelbewerber" if name in RP_EINZEL else name
                p[name] = p.get(name, 0) + int(v)
        return {"ungueltig": int(z[ung]), "gueltig": int(z[b]), "p": {k: v for k, v in p.items() if v}}
    return {"wb": int(z["A"]), "w": int(z["B"]), "e": stimmen("D", "C"), "z": stimmen("F", "E")}


def rp_lesen():
    """Auszüge der amtlichen Dateien -> gemeinsame Tabellenform. Das Land kommt aus der Datei der Landkreise (zweite Quelle für die Summenprobe)."""
    q = {x: QUELLEN / f"rp_ltw26_{x}" for x in ("wahlkreise.csv", "land.csv", "gewaehlte.json", "vergleich_2021.json")}
    if not all(p.exists() for p in list(q.values())[:3]):
        return None
    with open(q["wahlkreise.csv"], encoding="utf-8", newline="") as f:
        wk = {str(int(z["Schluessel"].split()[1])): {"name": z["Name"], **_rp_gebiet(z)} for z in csv.DictReader(f, delimiter=";")}
    with open(q["land.csv"], encoding="utf-8", newline="") as f:
        land = _rp_gebiet(next(csv.DictReader(f, delimiter=";")))
    land["vor"] = json.loads(q["vergleich_2021.json"].read_text(encoding="utf-8")) if q["vergleich_2021.json"].exists() else {}
    gew = json.loads(q["gewaehlte.json"].read_text(encoding="utf-8"))
    n, dm = {}, {}
    for _, partei in list(gew["direkt"].values()) + gew["liste"]:
        n[partei] = n.get(partei, 0) + 1
    for _, partei in gew["direkt"].values():
        dm[partei] = dm.get(partei, 0) + 1
    staedte = {}
    sp = QUELLEN / "rp_ltw26_staedte.csv"
    if sp.exists():
        namen = wk_staedte("rp")
        with open(sp, encoding="utf-8", newline="") as f:
            for z in csv.DictReader(f, delimiter=";"):
                sid = "S07" + z["Schluessel"] + "000"
                staedte[sid] = {"name": namen[sid][0], "teil": namen[sid][1], **_rp_gebiet(z)}
    return {"land": land, "wahlkreise": wk, "direkt": gew["direkt"], "sitze": sorted(([p, k, dm.get(p, 0), None] for p, k in n.items()), key=lambda x: -x[1]),
            "staedte": staedte}


def rp_ltw26(kurz=lambda p: p):
    """Landtagswahl Rheinland-Pfalz 22.03.2026: Land, 52 Wahlkreise (Wahlkreis- und Landesstimmen, Direktmandat), Sitze, Landesvergleich 2021."""
    d = rp_lesen()
    return tab_wahl("DE-RP", d, kurz) if d else None


# Mecklenburg-Vorpommern: CSV des Landeswahlleiters (Wahlkreise, Mandate), Gewählte von der Ergebnisseite, Vergleich 2021 aus dem
# Kurzbericht des Statistischen Amtes (XLSX), Shape der Wahlkreise vom Amt für Geoinformation
MV = "https://www.laiv-mv.de/"
MV_SEITEN = "https://wahlen.mvnet.de/dateien/ergebnisse.2026/landtagswahl/html/"
MV_KURZBERICHT = MV + "serviceassistent/download?id=1693020"


def mv_gewaehlte(seite):
    """{Wahlkreis: [Name, Partei]} aus der Seite der gewählten Wahlkreisbewerber (Zellen sind einzeln positioniert: Zeilen über die Höhe bilden)."""
    zellen = sorted((int(m.group(1)), int(m.group(2)), _text(m.group(3)).replace("\xa0", " ").strip())
                    for m in re.finditer(r'<div style="top: (\d+)px; left: (\d+)px; width:\s*\d+px; " class="S\d+">(.*?)</div>', seite))
    zeilen, oben = [], None
    for top, links, text in zellen:
        if oben is None or top - oben > 3:
            zeilen.append([])
        oben = top
        zeilen[-1].append((links, text))
    out = {}
    for z in zeilen:
        t = [x for _, x in sorted(z)]
        if len(t) == 4 and t[0].isdigit() and re.fullmatch(r"\d+,\d", t[2]):
            nach, _, vor = t[3].partition(",")
            out[t[0]] = [f"{vor.strip()} {nach.strip()}".strip(), t[1]]
    return out


def mv_vergleich(blaetter):
    """Vergleichswerte 2021 aus dem Kurzbericht: Anteile je Partei und Wahlkreis, Beteiligung, Sitze. `blaetter` = {Blattname: Zeilen}."""
    out = {"wahl": "2021-09-26", "land": {"e": {}, "z": {}}, "wahlkreise": {}, "sitze": {}}
    for z in blaetter["Wahlbeteiligung MV"]:
        if z and z[0] == "Mecklenburg-Vorpommern":
            out["land"]["bet"] = round(z[4], 2)
        elif z and isinstance(z[0], int) and isinstance(z[4], (int, float)):
            out["wahlkreise"].setdefault(str(z[0]), {"e": {}, "z": {}})["bet"] = round(z[4], 2)
    for partei, zeilen in blaetter.items():
        if not (zeilen and len(zeilen) > 1 and zeilen[1] and str(zeilen[1][0]).startswith("Stimmenanteile der ")):
            continue
        for z in zeilen:
            ziel = out["land"] if z and z[0] == "Mecklenburg-Vorpommern" else out["wahlkreise"].get(str(z[0])) if z and isinstance(z[0], int) else None
            if ziel is not None:
                for st, i in (("e", 3), ("z", 6)):
                    if isinstance(z[i], (int, float)):
                        ziel[st][partei] = round(z[i], 2)
    for z in blaetter["Endgültiges Ergebnis"]:
        if z and isinstance(z[0], str) and len(z) > 4 and isinstance(z[4], int) and z[0] != "Insgesamt":
            out["sitze"][re.sub(r"\s*\d\)$", "", z[0].replace("\xa0", " "))] = z[4]
    return out


def mv_laden(abruf=True):
    q = {x: QUELLEN / f"mv_ltw26_{x}" for x in ("wahlkreise.csv", "mandate.csv", "gewaehlte.json", "vergleich_2021.json")}
    for ziel, datei in ((q["wahlkreise.csv"], "l_wahlkreise.csv"), (q["mandate.csv"], "l_mandate.csv")):
        if not ziel.exists() and abruf:
            roh = _hole(MV + "static/LAIV/Wahlen/2-Landtagswahlen/2026/Ergebnisse/" + datei).decode("cp1252")
            ziel.write_text(roh.replace("\r\n", "\n"), encoding="utf-8")
    if not q["gewaehlte.json"].exists() and abruf:
        g = mv_gewaehlte(_hole(MV_SEITEN + "l_gewbewerberwk.html").decode("latin-1"))
        q["gewaehlte.json"].write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if not q["vergleich_2021.json"].exists() and abruf:
        import io
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(_hole(MV_KURZBERICHT)), read_only=True, data_only=True)
        blaetter = {}
        for ws in wb.worksheets:
            ws.reset_dimensions()
            blaetter[ws.title] = [list(z) for z in ws.iter_rows(values_only=True)]
        q["vergleich_2021.json"].write_text(json.dumps(mv_vergleich(blaetter), ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    st = QUELLEN / "mv_ltw26_staedte.csv"
    if not st.exists() and abruf:
        roh = _hole(MV + "static/LAIV/Wahlen/2-Landtagswahlen/2026/Ergebnisse/l_gemeinden.csv").decode("cp1252").replace("\r\n", "\n")
        vorspann, _, rest = roh.partition("\n\n")
        kopf, *zeilen = rest.splitlines()
        i, gem = kopf.split(";").index("Gemeinde"), {sid[1:] for sid in wk_staedte("mv")}
        st.write_text(vorspann + "\n\n" + "\n".join([kopf] + [z for z in zeilen if z.split(";")[i] in gem and z.split(";")[1] == "A"]) + "\n", encoding="utf-8")
    gp = GEO / "landtagswahlkreise_mv.geojson"
    if not gp.exists() and abruf and q["wahlkreise.csv"].exists():
        namen = {z["Wahlkreis"]: z["Wahlkreisname/Land"] for z in _mv_csv(q["wahlkreise.csv"]) if z["Ausgabe"] == "A"}
        gp.write_text(json.dumps(wk_aus_gemeinden("mv", "13", namen), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def _mv_csv(pfad):
    """Datenzeilen einer CSV des Landeswahlleiters (vier Kopfzeilen Text, Leerzeile, Spaltenkopf); nur endgültige Ergebnisse."""
    text = pfad.read_text(encoding="utf-8")
    vorspann, _, rest = text.partition("\n\n")
    if "Endgültiges Ergebnis" not in vorspann:
        raise Pruefehler(f"{pfad.name}: kein endgültiges Ergebnis ({vorspann.splitlines()[1] if vorspann.count(chr(10)) else vorspann[:60]})")
    return list(csv.DictReader(rest.splitlines(), delimiter=";"))


def mv_lesen():
    q = {x: QUELLEN / f"mv_ltw26_{x}" for x in ("wahlkreise.csv", "mandate.csv", "gewaehlte.json", "vergleich_2021.json")}
    if not all(p.exists() for p in list(q.values())[:3]):
        return None
    fest = {"Berechnungsdatum", "Ausgabe", "Wahlkreis", "Wahlkreisname/Land", "Wahlbezirke insg.", "Erf. Wahlbezirke", "Wahlberechtigte", "Wähler",
            "Wahlbeteiligung", "Erst-/Zweitstimme", "Ungültige Stimmen", "Gültige Stimmen", "Sort", "Mandatstyp"}
    fest |= {"Kreis", "Kreisname", "Amt", "Amtsname", "Gemeinde", "Gemeindename"}
    vgl = json.loads(q["vergleich_2021.json"].read_text(encoding="utf-8")) if q["vergleich_2021.json"].exists() else {}

    def lesen(pfad, schluessel, name):
        out = {}
        for z in _mv_csv(pfad):
            if z["Ausgabe"] != "A":
                continue
            if z["Wahlbezirke insg."] != z["Erf. Wahlbezirke"]:
                raise Pruefehler(f"Mecklenburg-Vorpommern 2026, {z[name]}: {z['Erf. Wahlbezirke']} von {z['Wahlbezirke insg.']} Wahlbezirken erfasst")
            g = out.setdefault(z[schluessel], {"name": z[name], "wb": int(z["Wahlberechtigte"]), "w": int(z["Wähler"])})
            g["e" if z["Erst-/Zweitstimme"] == "1" else "z"] = {
                "ungueltig": int(z["Ungültige Stimmen"]), "gueltig": int(z["Gültige Stimmen"]),
                "p": {k: int(v) for k, v in z.items() if k not in fest and v not in ("x", "", None) and int(v)}}
        return out
    gebiete = lesen(q["wahlkreise.csv"], "Wahlkreis", "Wahlkreisname/Land")
    staedte = {}
    if (QUELLEN / "mv_ltw26_staedte.csv").exists():
        namen = wk_staedte("mv")
        staedte = {"S" + k: {**g, "name": namen["S" + k][0], "teil": namen["S" + k][1]}
                   for k, g in lesen(QUELLEN / "mv_ltw26_staedte.csv", "Gemeinde", "Gemeindename").items()}
    land = gebiete.pop("99")
    land["vor"] = vgl.get("land") or {}
    for nr, g in gebiete.items():
        g["vor"] = (vgl.get("wahlkreise") or {}).get(nr) or {}
    mandate = {z["Mandatstyp"]: z for z in _mv_csv(q["mandate.csv"]) if z["Wahlkreis"] == "99"}
    vs = vgl.get("sitze") or {}
    sitze = []
    for p, n in mandate["Insgesamt"].items():
        if p not in fest and n not in ("x", "") and (int(n) or vs.get(p)):
            dm = mandate["Direktmandate"][p]
            sitze.append([p, int(n), int(dm) if dm not in ("x", "") else 0, vs.get(p)])
    return {"land": land, "wahlkreise": gebiete, "direkt": json.loads(q["gewaehlte.json"].read_text(encoding="utf-8")),
            "sitze": sorted(sitze, key=lambda x: -x[1]), "staedte": staedte}


def mv_ltw26(kurz=lambda p: p):
    """Landtagswahl Mecklenburg-Vorpommern 20.09.2026: Land, 36 Wahlkreise (Erst- und Zweitstimmen, Direktmandat), Sitze, Vergleich 2021."""
    d = mv_lesen()
    return tab_wahl("DE-MV", d, kurz) if d else None


# ---------------------------------------------------------------- Register
# Je Land die amtlich eingelesenen Wahlen (Wahltag, Lesefunktion). Grenzen: (Schlüssel "geo" der Einheit, Datei unter app/geo) für globus.WAHL_GEO.
WAHLEN = {"DE-ST": [("2026-09-06", st_ltw26)], "DE-BW": [("2026-03-08", bw_ltw26)], "DE-BE": [("2026-09-20", be_agh26)],
          "DE-RP": [("2026-03-22", rp_ltw26)], "DE-MV": [("2026-09-20", mv_ltw26)]}
LADEN = [st_laden, bw_laden, lambda abruf=True: praes_laden("DE-BE", abruf), rp_laden, mv_laden]
WAHL_GEO = [("landtagswahlkreise-st", "geo/landtagswahlkreise_st.geojson"), ("landtagswahlkreise-bw", "geo/landtagswahlkreise_bw.geojson"),
            ("landtagswahlkreise-be", "geo/landtagswahlkreise_be.geojson"),
            ("landtagswahlkreise-rp", "geo/landtagswahlkreise_rp.geojson"), ("landtagswahlkreise-mv", "geo/landtagswahlkreise_mv.geojson")]


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
