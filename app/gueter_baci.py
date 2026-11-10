"""Weltkugel, Reiter Handel: Exporte je Gut und Land aus CEPII BACI -> data/gueter.json.

Quelle: CEPII BACI (http://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37), Lizenz Etalab 2.0 (freie Nutzung mit
Quellenangabe), harmonisierte bilaterale Handelsströme auf HS6-Ebene aus UN Comtrade. Die Datei BACI_HS12_V202601.zip
(rund 1,3 GB, Jahre 2012 bis 2024) wird einmal geladen und hier auf Land x Gutgruppe x Jahr verdichtet; ins Repo kommt nur das Ergebnis.

Wertangaben in tausend US-Dollar (Rohwert), im Ergebnis in Millionen US-Dollar. Je Land und Gut stehen zehn Jahre Exportwert
und, für das jüngste Jahr, die fünf größten Abnehmerländer sowie Zahl und Konzentration (HHI) aller Abnehmer.

Zweite Ausgabe data/gueter_importe.json (Audit 2026-11, 4.3): die Importseite aus derselben vollständigen bilateralen Matrix.
Je Importland und Gut: Importwert je Jahr, Zahl der Lieferländer, HHI über ALLE Lieferländer je Jahr, größtes Lieferland je Jahr und
die zehn größten Lieferländer des jüngsten Jahres. Die Matrix selbst (rund 150 000 Zeilen je Jahr) kommt nicht ins Repo und nicht
auf den Server: gespeichert wird nur diese Verdichtung.

Methodik: BACI gleicht die Meldungen von Export- und Importland ab (ein Wert je Strom, FOB), ist also bereits eine abgeglichene
Spiegelstatistik und weicht von den nationalen Importstatistiken (CIF, Ursprungs- statt Versendungsland) ab. Ströme mit Partnern ohne
ISO-Code (z. B. „Areas, nes“) lassen sich keinem Lieferland zuordnen: Sie zählen zum Importwert, stehen als „unbekannt“ in der Datei
und gehen nicht in den HHI ein (der HHI ist dann eine Untergrenze). Kleinstströme unter der BACI-Meldeschwelle fehlen.

    python3 app/gueter_baci.py --zip /pfad/BACI_HS12_V202601.zip [--jahre 2015-2024]
"""
import argparse
import json
import time
import zipfile
from pathlib import Path

import pandas as pd

HIER = Path(__file__).resolve().parent
ZIEL = HIER / "data/gueter.json"
ZIEL_IMPORTE = HIER / "data/gueter_importe.json"
TOP_LIEFERLAENDER = 10

# Gutgruppen: id -> (Name, Einheit/Kurztext, HS-Präfixe auf 2 bis 6 Stellen). Die Positionen sind in HS2012 und HS2022 gleich.
GRUPPEN = [
    ("oel", "Rohöl", ["2709"], "Energie"),
    ("oelprodukte", "Mineralölprodukte (Benzin, Diesel …)", ["2710"], "Energie"),
    ("gas", "Erdgas und Flüssiggas (LNG)", ["2711"], "Energie"),
    ("kohle", "Kohle", ["2701"], "Energie"),
    ("weizen", "Weizen", ["1001"], "Landwirtschaft"),
    ("mais", "Mais", ["1005"], "Landwirtschaft"),
    ("reis", "Reis", ["1006"], "Landwirtschaft"),
    ("soja", "Sojabohnen", ["1201"], "Landwirtschaft"),
    ("kaffee", "Kaffee", ["0901"], "Landwirtschaft"),
    ("duenger", "Düngemittel", ["31"], "Landwirtschaft"),
    ("eisenerz", "Eisenerz", ["2601"], "Metalle"),
    ("kupfer", "Kupfer (Erze und Metall)", ["2603", "7402", "7403"], "Metalle"),
    ("aluminium", "Aluminium (roh)", ["7601"], "Metalle"),
    ("gold", "Gold", ["7108"], "Metalle"),
    ("stahl", "Eisen und Stahl", ["72"], "Metalle"),
    ("pkw", "Personenkraftwagen", ["8703"], "Industrie"),
    ("maschinen", "Maschinen", ["84"], "Industrie"),
    ("chips", "Halbleiter und Chips", ["8541", "8542"], "Industrie"),
    ("flugzeuge", "Flugzeuge und Raumfahrzeuge", ["8802"], "Industrie"),
    ("pharma", "Arzneimittel", ["3002", "3004"], "Industrie"),
    ("kunststoffe", "Kunststoffe", ["39"], "Industrie"),
    ("kleidung", "Bekleidung", ["61", "62"], "Industrie"),
]
PRAEFIX = {p: g[0] for g in GRUPPEN for p in g[2]}
LAENGEN = sorted({len(p) for p in PRAEFIX})


def gruppe_von(k):
    # k als sechsstelliger Text; längster passender Präfix
    for n in sorted(LAENGEN, reverse=True):
        g = PRAEFIX.get(k[:n])
        if g:
            return g
    return None


def hhi(werte):
    """Herfindahl-Hirschman-Index in Punkten (0 bis 10 000) über positive Werte; wie server/plattform/handel.py: hhi."""
    w = [float(v) for v in werte if v and v > 0]
    s = sum(w)
    return round(sum((v / s * 100) ** 2 for v in w), 1) if s > 0 else 0.0


def importseite(d, roh, jahre, letzt):
    """Verdichtung der bilateralen Matrix aus Sicht der Importländer.

    d: Ströme mit ISO-Code auf beiden Seiten (t, iso_i Exportland, iso_j Importland, g, v in Tsd. USD); roh: alle Ströme, auch
    mit Exportländern ohne ISO-Code. Ergebnis je Importland und Gut:
      v     Importwert je Jahr (Mio. USD, einschließlich nicht zuordenbarer Lieferländer)
      u     nicht zuordenbarer Teil je Jahr (Mio. USD; fehlt, wenn überall 0)
      n     Zahl der Lieferländer je Jahr
      hhi   HHI über alle zuordenbaren Lieferländer je Jahr
      t1    größtes Lieferland je Jahr als [ISO, Anteil am Importwert]
      top   die zehn größten Lieferländer im jüngsten Jahr als [ISO, Mio. USD]
    """
    roh = roh.dropna(subset=["iso_j"])
    ges = roh.groupby(["iso_j", "g", "t"])["v"].sum()
    bil = d.groupby(["iso_j", "g", "t", "iso_i"], as_index=False)["v"].sum()
    bil = bil[(bil["v"] > 0) & (bil["iso_i"] != bil["iso_j"])]
    laender = {}
    for (land, g), teil in bil.groupby(["iso_j", "g"]):
        je_jahr = {int(t): x for t, x in teil.groupby("t")}
        v, u, n, h, t1 = [], [], [], [], []
        for t in jahre:
            x = je_jahr.get(int(t))
            summe = float(ges.get((land, g, t), 0.0))
            if x is None or summe <= 0:
                v.append(None); u.append(None); n.append(0); h.append(None); t1.append(None)
                continue
            bekannt = float(x["v"].sum())
            v.append(round(summe / 1000, 1))
            u.append(round(max(summe - bekannt, 0.0) / 1000, 1))
            n.append(int(len(x)))
            h.append(hhi(x["v"]))
            gr = x.loc[x["v"].idxmax()]
            t1.append([gr["iso_i"], round(float(gr["v"]) / summe, 4)])
        e = {"v": v, "n": n, "hhi": h, "t1": t1}
        if any(x for x in u if x):
            e["u"] = u
        x = je_jahr.get(int(letzt))
        if x is not None:
            e["top"] = [[r.iso_i, round(float(r.v) / 1000, 1)] for r in x.nlargest(TOP_LIEFERLAENDER, "v").itertuples()]
        laender.setdefault(land, {})[g] = e
    return {"jahre": [int(t) for t in jahre], "jahr": int(letzt), "gruppen": [g[0] for g in GRUPPEN], "top_n": TOP_LIEFERLAENDER, "laender": laender,
            "hinweis": "Importwert je Importland und Gut aus der vollständigen bilateralen Matrix (CEPII BACI, abgeglichene Spiegelstatistik, FOB). "
                       "hhi über alle zuordenbaren Lieferländer; u = Lieferland nicht zuordenbar (zählt zum Importwert, nicht zum HHI). "
                       "Abweichungen zu nationalen Importstatistiken (CIF, Ursprungsland) sind methodisch bedingt."}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True)
    ap.add_argument("--jahre", default="2015-2024")
    a = ap.parse_args()
    j0, j1 = [int(x) for x in a.jahre.split("-")]
    z = zipfile.ZipFile(a.zip)
    laender = pd.read_csv(z.open(next(n for n in z.namelist() if n.startswith("country_codes"))), keep_default_na=False)   # "NA" (Namibia) ist kein Leerwert
    # Zwei-Buchstaben-Codes wie in der Weltkugel. Namibia fehlt in der Datei, "Other Asia, nes" (490) ist im Kern Taiwan.
    iso = {c: i for c, i in zip(laender.country_code, laender.country_iso2) if i}
    iso.update({516: "NA", 490: "TW"})
    teile = []
    for n in sorted(x for x in z.namelist() if x.startswith("BACI_") and x.endswith(".csv")):
        jahr = int(n.split("_Y")[1][:4])
        if not j0 <= jahr <= j1:
            continue
        t0 = time.time()
        sub = []
        for ch in pd.read_csv(z.open(n), dtype={"k": str, "i": int, "j": int}, usecols=["t", "i", "j", "k", "v"], chunksize=2_000_000):
            ch["k"] = ch["k"].str.zfill(6)
            m = ch["k"].str[:2].isin({p[:2] for p in PRAEFIX})
            ch = ch[m]
            ch = ch.assign(g=[gruppe_von(k) for k in ch["k"]])
            ch = ch[ch["g"].notna()]
            sub.append(ch.groupby(["t", "i", "j", "g"], as_index=False)["v"].sum())
        teil = pd.concat(sub).groupby(["t", "i", "j", "g"], as_index=False)["v"].sum()
        teile.append(teil)
        print(n, len(teil), "Zeilen,", round(time.time() - t0), "s", flush=True)
    d = pd.concat(teile)
    d["iso_i"] = d["i"].map(iso)
    d["iso_j"] = d["j"].map(iso)
    roh = d                                              # mit Partnern ohne ISO-Code, für den nicht zuordenbaren Teil der Importe
    d = d.dropna(subset=["iso_i", "iso_j"])
    jahre = sorted(d["t"].unique().tolist())
    letzt = jahre[-1]
    # Welt je Gut und Jahr (Mio. USD)
    welt = d.groupby(["g", "t"])["v"].sum() / 1000
    ausgabe = {"quelle": "CEPII BACI, Version 202601 (Etalab 2.0), Daten aus UN Comtrade", "url": "http://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37",
               "abruf": time.strftime("%Y-%m-%d"), "einheit": "Mio. US-Dollar", "jahre": jahre, "jahr": int(letzt),
               "gruppen": [{"id": g[0], "name": g[1], "hs": g[2], "bereich": g[3]} for g in GRUPPEN],
               "welt": {g: {int(t): round(float(welt[(g, t)]), 1) for t in jahre if (g, t) in welt.index} for g in [x[0] for x in GRUPPEN]},
               "laender": {}}
    exp = d.groupby(["iso_i", "g", "t"])["v"].sum() / 1000
    top = d[d["t"] == letzt].groupby(["iso_i", "g", "iso_j"])["v"].sum().reset_index()
    for (land, g), teil in exp.groupby(level=[0, 1]):
        e = ausgabe["laender"].setdefault(land, {})
        reihe = {int(t): round(float(v), 1) for (_, _, t), v in teil.items()}
        e[g] = {"v": [reihe.get(int(t)) for t in jahre]}
    for (land, g), teil in top.groupby(["iso_i", "g"]):
        t5 = teil.nlargest(5, "v")
        e = ausgabe["laender"][land][g]
        e["partner"] = [[r.iso_j, round(float(r.v) / 1000, 1)] for r in t5.itertuples()]
        # alle Abnehmer: Zahl und HHI (Exportabhängigkeit nach Absatzmarkt), nicht nur die fünf größten
        pos = teil[teil["v"] > 0]["v"]
        e["pn"], e["phhi"] = int(len(pos)), hhi(pos)
    ZIEL.write_text(json.dumps(ausgabe, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("geschrieben", ZIEL, ZIEL.stat().st_size // 1024, "KB,", len(ausgabe["laender"]), "Länder")
    importe = importseite(d, roh, jahre, letzt)
    importe.update({"quelle": ausgabe["quelle"], "url": ausgabe["url"], "abruf": ausgabe["abruf"], "einheit": ausgabe["einheit"]})
    ZIEL_IMPORTE.write_text(json.dumps(importe, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("geschrieben", ZIEL_IMPORTE, ZIEL_IMPORTE.stat().st_size // 1024, "KB,", len(importe["laender"]), "Importländer")


if __name__ == "__main__":
    main()
