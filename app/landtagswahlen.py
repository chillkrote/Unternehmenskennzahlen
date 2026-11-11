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


# ---------------------------------------------------------------- Register
# Je Land die amtlich eingelesenen Wahlen (Wahltag, Lesefunktion). Grenzen: (Schlüssel "geo" der Einheit, Datei unter app/geo) für globus.WAHL_GEO.
WAHLEN = {"DE-ST": [("2026-09-06", st_ltw26)], "DE-BW": [("2026-03-08", bw_ltw26)], "DE-BE": [("2026-09-20", be_agh26)]}
LADEN = [st_laden, bw_laden, lambda abruf=True: praes_laden("DE-BE", abruf)]
WAHL_GEO = [("landtagswahlkreise-st", "geo/landtagswahlkreise_st.geojson"), ("landtagswahlkreise-bw", "geo/landtagswahlkreise_bw.geojson"),
            ("landtagswahlkreise-be", "geo/landtagswahlkreise_be.geojson")]


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
