"""Weltkugel, Haupthandelsrouten: erzeugt data/routen.json aus den von Hand gepflegten Listen in app/geo/routen/.

 - knoten.csv: Engstellen (See, Binnenschiff, Bahn, Straße) und Drehkreuze (Häfen, Bahnknoten) mit Koordinate, Rolle und
   Suchbegriffen für die Störungsmeldungen (news_routen.py). Koordinaten genähert (Lage, keine Vermessung).
 - flughaefen.txt: Frachtflughäfen (IATA); Lage aus OurAirports (gemeinfrei, https://ourairports.com/data/).
 - korridore.csv: Hauptachsen je Verkehrsträger. Seewege werden über das Seewegenetz "marnet" berechnet (kürzester Weg, mit
   Sperren für Passagen wie Suez), das aus dem Paket searoute stammt (Apache-2.0, beruht auf Eurostat SeaRoute und dem
   Netz des Oak Ridge National Laboratory; Lizenz in app/geo/routen/LICENCE-searoute-Apache-2.0.txt). Bahn, Straße und Luft
   sind schematisch: Stationen verbunden (Bahn/Straße) bzw. Großkreis (Luft), nicht der tatsächliche Gleis- oder Flugweg.

Mengen je Route gibt es frei nicht (IMF PortWatch nur mit Erlaubnis für den automatischen Abruf), daher keine Breite nach Menge.

    python3 app/routen.py [--flughaefen pfad/zu/airports.csv]
"""
import argparse
import csv
import heapq
import io
import json
import math
import sys
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
QUELL = HIER / "geo/routen"
ZIEL = HIER / "data/routen.json"
OURAIRPORTS = "https://davidmegginson.github.io/ourairports-data/airports.csv"


def km(a, b):
    r = math.pi / 180
    d = math.sin((b[1] - a[1]) * r / 2) ** 2 + math.cos(a[1] * r) * math.cos(b[1] * r) * math.sin((b[0] - a[0]) * r / 2) ** 2
    return 12742 * math.asin(min(1, math.sqrt(d)))


def schluessel(p):
    lon = round(p[0], 4)
    if lon == -180:
        lon = 180.0    # Datumsgrenze: beide Seiten sind derselbe Knoten
    return (lon, round(p[1], 4))


class Netz:
    def __init__(self, pfad):
        d = json.loads(pfad.read_text())
        self.kanten = {}       # Knoten -> {Nachbar: (km, passage)}
        for f in d["features"]:
            g = f["geometry"]
            linien = [g["coordinates"]] if g["type"] == "LineString" else g["coordinates"]
            pas = f["properties"].get("passage")
            for lin in linien:
                for a, b in zip(lin, lin[1:]):
                    ka, kb = schluessel(a), schluessel(b)
                    if ka == kb:
                        continue
                    w = km(ka, kb)
                    self.kanten.setdefault(ka, {})[kb] = (w, pas)
                    self.kanten.setdefault(kb, {})[ka] = (w, pas)
        self.knoten = list(self.kanten)

    def naechster(self, p):
        return min(self.knoten, key=lambda k: km(k, p))

    def weg(self, a, b, meiden=()):
        start, ziel = self.naechster(a), self.naechster(b)
        dist, vor, offen = {start: 0}, {}, [(0, start)]
        while offen:
            d, k = heapq.heappop(offen)
            if k == ziel:
                break
            if d > dist.get(k, 1e18):
                continue
            for n, (w, pas) in self.kanten[k].items():
                if pas and pas in meiden:
                    continue
                nd = d + w
                if nd < dist.get(n, 1e18):
                    dist[n], vor[n] = nd, k
                    heapq.heappush(offen, (nd, n))
        if ziel not in dist:
            raise ValueError(f"kein Seeweg {a} -> {b} ohne {meiden}")
        pfad, k = [ziel], ziel
        while k != start:
            k = vor[k]
            pfad.append(k)
        return [list(a)] + [list(p) for p in reversed(pfad)] + [list(b)], dist[ziel]


def fortlaufend(pkt):
    """Längengrade fortlaufend (kein Sprung über die Datumsgrenze), auf 2 Nachkommastellen."""
    out, vorher = [], None
    for lon, lat in pkt:
        if vorher is not None:
            while lon - vorher > 180:
                lon -= 360
            while vorher - lon > 180:
                lon += 360
        vorher = lon
        out.append([round(lon, 2), round(lat, 2)])
    return out


def grosskreis(a, b, n=48):
    r = math.pi / 180
    v = lambda p: (math.cos(p[1] * r) * math.cos(p[0] * r), math.cos(p[1] * r) * math.sin(p[0] * r), math.sin(p[1] * r))  # noqa: E731
    A, B = v(a), v(b)
    w = math.acos(max(-1, min(1, sum(x * y for x, y in zip(A, B)))))
    if w < 1e-6:
        return [list(a), list(b)]
    out = []
    for i in range(n + 1):
        t = i / n
        k1, k2 = math.sin((1 - t) * w) / math.sin(w), math.sin(t * w) / math.sin(w)
        x, y, z = (k1 * p + k2 * q for p, q in zip(A, B))
        out.append([math.atan2(y, x) / r, math.atan2(z, math.hypot(x, y)) / r])
    return out


def flughaefen(pfad):
    want = set((QUELL / "flughaefen.txt").read_text().split("\n", 1)[1].split())
    text = Path(pfad).read_text(encoding="utf-8") if pfad else urllib.request.urlopen(OURAIRPORTS, timeout=120).read().decode("utf-8")
    out = {}
    for r in csv.DictReader(io.StringIO(text)):
        if r["iata_code"] in want and r["type"] in ("large_airport", "medium_airport"):
            out[r["iata_code"]] = {"id": r["iata_code"], "name": r["municipality"].split(" (")[0] + f" ({r['iata_code']})", "art": "flughafen", "traeger": "luft",
                                   "stufe": 2, "lon": round(float(r["longitude_deg"]), 3), "lat": round(float(r["latitude_deg"]), 3),
                                   "rolle": "Frachtflughafen", "suche": ""}
    fehlt = want - set(out)
    if fehlt:
        print("Flughäfen ohne Treffer:", sorted(fehlt), file=sys.stderr)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--flughaefen", help="lokale Kopie von OurAirports airports.csv")
    a = p.parse_args()
    knoten = {}
    for r in csv.DictReader(open(QUELL / "knoten.csv", encoding="utf-8")):
        knoten[r["id"]] = {"id": r["id"], "name": r["name"], "art": r["art"], "traeger": r["traeger"], "stufe": int(r["stufe"]),
                           "lon": float(r["lon"]), "lat": float(r["lat"]), "rolle": r["rolle"], "suche": r["suche"]}
    knoten.update(flughaefen(a.flughaefen))
    netz = Netz(QUELL / "marnet.geojson")
    engstellen = [k for k in knoten.values() if k["art"] == "engstelle"]
    korridore = []
    for r in csv.DictReader(open(QUELL / "korridore.csv", encoding="utf-8")):
        punkte = []
        for t in r["punkte"].split():
            if t.startswith("@"):
                lon, lat = t[1:].split("/")
                punkte.append((float(lon), float(lat)))
            else:
                punkte.append((knoten[t]["lon"], knoten[t]["lat"]))
        if r["traeger"] == "see":
            pkt, laenge = [], 0
            for x, y in zip(punkte, punkte[1:]):
                # Nordwest- und Nordostpassage (Beringstraße) nur, wenn ausdrücklich gewünscht
                w, l = netz.weg(x, y, set(r["meiden"].split()) | {"northwest", "bering"})
                pkt += w if not pkt else w[1:]
                laenge += l
        elif r["traeger"] == "luft":
            pkt, laenge = [], 0
            for x, y in zip(punkte, punkte[1:]):
                g = grosskreis(x, y)
                pkt += g if not pkt else g[1:]
                laenge += km(x, y)
        else:
            pkt, laenge = [list(x) for x in punkte], sum(km(x, y) for x, y in zip(punkte, punkte[1:]))
        # Engstellen am Weg (bis 80 km Abstand zu einem Wegpunkt; schematische Wege prüfen nur die Stationen)
        passt = {"see": {"see"}, "bahn": {"bahn", "strasse"}, "strasse": {"strasse", "bahn"}}.get(r["traeger"], set())
        am_weg = [e["id"] for e in engstellen if e["traeger"] in passt and any(km(e2, (e["lon"], e["lat"])) < (300 if e["id"] == "kap" else 80) for e2 in pkt)]
        korridore.append({"id": r["id"], "name": r["name"], "traeger": r["traeger"], "stufe": int(r["stufe"]), "hinweis": r["hinweis"],
                          "km": round(laenge), "engstellen": am_weg, "schematisch": r["traeger"] != "see", "linie": fortlaufend(pkt)})
        print(f"  {r['id']}: {round(laenge):,} km, {len(pkt)} Punkte, Engstellen {am_weg}", file=sys.stderr)
    out = {"knoten": list(knoten.values()), "korridore": korridore, "quellen": {
        "seewege": "Seewegenetz marnet aus dem Paket searoute (Apache-2.0), beruhend auf Eurostat SeaRoute / Oak Ridge National Laboratory",
        "seewege_url": "https://github.com/genthalili/searoute-py",
        "flughaefen": "OurAirports (gemeinfrei)", "flughaefen_url": "https://ourairports.com/data/",
        "knoten": "Auswahl und Lage von Hand (app/geo/routen/knoten.csv), Koordinaten genähert"}}
    ZIEL.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"{ZIEL}: {len(knoten)} Knoten, {len(korridore)} Korridore", file=sys.stderr)


if __name__ == "__main__":
    main()
