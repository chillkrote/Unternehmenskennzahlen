"""Weltkugel, Darstellungsformen Handel und Volkswirtschaft: erzeugt data/welt.json.

Inhalt (alles kostenlos und ohne Schlüssel abrufbar):
 - laender: je Land (ISO2) die jüngsten Jahreswerte aus den World Development Indicators der Weltbank (CC BY 4.0):
   BIP-Wachstum, Inflation, BIP, BIP je Einwohner (KKP), Arbeitslosenquote, Leistungsbilanz, Staatsschulden, Exporte/Importe
   in % des BIP, Direktinvestitionen, Einwohner und die angewandten Zollsätze (einfacher und handelsgewichteter Durchschnitt
   über alle Waren). Dazu je Reihe die letzten zehn Jahre für die Verlaufslinie.
 - strom: bilateraler Stromhandel (GWh) der europäischen Meldeländer nach Partnerland aus Eurostat nrg_ti_eh / nrg_te_eh
   (Einfuhren und Ausfuhren, CC BY 4.0). Für andere Weltregionen gibt es keine freie bilaterale Quelle ohne Schlüssel
   (offene Punkte in app/OFFENE_DATENFELDER.md).
 - raeume: Wirtschaftsräume aus app/geo/wirtschaftsraeume.csv (von Hand gepflegt, Quelle je Raum).

    python3 app/welt_daten.py            # alles neu abrufen
    python3 app/welt_daten.py --ohne-netz   # nur Wirtschaftsräume neu einlesen, Länder- und Stromdaten aus der alten Datei
"""
import argparse
import csv
import json
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

HIER = Path(__file__).resolve().parent
ZIEL = HIER / "data/welt.json"
RAEUME = HIER / "geo/wirtschaftsraeume.csv"
WB = "https://api.worldbank.org/v2/country/all/indicator/{}?format=json&date={}:{}&per_page=20000"
# Kürzel -> (Indikator, Bezeichnung, Einheit)
REIHEN = {
    "bip_wachstum": ("NY.GDP.MKTP.KD.ZG", "BIP real, Veränderung ggü. Vorjahr", "%"),
    "inflation": ("FP.CPI.TOTL.ZG", "Inflation (Verbraucherpreise)", "%"),
    "bip_usd": ("NY.GDP.MKTP.CD", "BIP nominal", "USD"),
    "bip_pk_kkp": ("NY.GDP.PCAP.PP.CD", "BIP je Einwohner, Kaufkraftparitäten", "USD KKP"),
    "arbeitslos": ("SL.UEM.TOTL.ZS", "Arbeitslosenquote (ILO-Schätzung)", "%"),
    "leistungsbilanz": ("BN.CAB.XOKA.GD.ZS", "Leistungsbilanzsaldo", "% BIP"),
    "schulden": ("GC.DOD.TOTL.GD.ZS", "Schulden der Zentralregierung", "% BIP"),
    "exporte_bip": ("NE.EXP.GNFS.ZS", "Exporte von Waren und Dienstleistungen", "% BIP"),
    "importe_bip": ("NE.IMP.GNFS.ZS", "Importe von Waren und Dienstleistungen", "% BIP"),
    "fdi": ("BX.KLT.DINV.WD.GD.ZS", "Direktinvestitionen, Nettozufluss", "% BIP"),
    "einwohner": ("SP.POP.TOTL", "Einwohner", "Personen"),
    "zoll_einfach": ("TM.TAX.MRCH.SM.AR.ZS", "Angewandter Zollsatz, einfacher Durchschnitt aller Waren", "%"),
    "zoll_gewichtet": ("TM.TAX.MRCH.WM.AR.ZS", "Angewandter Zollsatz, handelsgewichteter Durchschnitt aller Waren", "%"),
}
EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{}?format=JSON&lang=en&siec=E7000&unit=GWH&lastTimePeriod=1"
# Eurostat-Kürzel, die von ISO2 abweichen
EU_ISO = {"EL": "GR", "UK": "GB", "XK": "XK"}


def holen(url, versuche=4):
    for i in range(versuche):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Unternehmenskennzahlen/1.0"}), timeout=90) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            if i == versuche - 1:
                raise
            print("  Wiederholung", url[:90], e, file=sys.stderr)
            time.sleep(3 * (i + 1))


def weltbank(isos):
    jahr = date.today().year
    out, meta = {}, {}
    for kurz, (ind, name, einheit) in REIHEN.items():
        d = holen(WB.format(ind, jahr - 11, jahr))
        stand = d[0].get("lastupdated")
        n = 0
        for z in d[1] or []:
            iso = z["country"]["id"]
            if iso not in isos or z["value"] is None:
                continue
            l = out.setdefault(iso, {}).setdefault(kurz, [])
            l.append([int(z["date"]), round(z["value"], 3 if abs(z["value"]) < 1000 else 0)])
            n += 1
        meta[kurz] = {"indikator": ind, "name": name, "einheit": einheit, "stand": stand,
                      "url": f"https://data.worldbank.org/indicator/{ind}"}
        print(f"  {ind}: {n} Werte", file=sys.stderr)
        time.sleep(.5)
    for iso in out:
        for kurz in out[iso]:
            out[iso][kurz].sort()
    return out, meta


def eurostat_strom():
    """{"MELDER>PARTNER": GWh} als Einfuhren (Partner -> Melder) und Ausfuhren (Melder -> Partner); Jahr dazu."""
    paare, jahre = {}, set()
    for tab, richtung in (("nrg_ti_eh", "import"), ("nrg_te_eh", "export")):
        d = holen(EUROSTAT.format(tab))
        dims = d["id"]
        groesse = d["size"]
        idx = {k: {v: i for v, i in d["dimension"][k]["category"]["index"].items()} for k in dims}
        rueck = {k: {i: v for v, i in idx[k].items()} for k in dims}
        partner_dim = "partner"
        jahre.update(idx["time"].keys())
        for pos, wert in d["value"].items():
            pos = int(pos)
            koord = {}
            for k, g in zip(reversed(dims), reversed(groesse)):
                koord[k] = rueck[k][pos % g]
                pos //= g
            geo, part = koord["geo"], koord[partner_dim]
            if not wert or round(wert) == 0 or len(geo) != 2 or len(part) != 2 or geo == part:
                continue
            geo, part = EU_ISO.get(geo, geo), EU_ISO.get(part, part)
            von, nach = (part, geo) if richtung == "import" else (geo, part)
            schl = von + ">" + nach
            # Ausfuhrmeldung des Herkunftslandes hat Vorrang, sonst die Einfuhrmeldung des Ziellandes (Spiegel)
            if richtung == "export" or schl not in paare:
                paare[schl] = [round(wert), "export" if richtung == "export" else "spiegel"]
    return {"jahr": max(jahre) if jahre else None, "einheit": "GWh", "paare": paare,
            "quelle": "Eurostat nrg_ti_eh und nrg_te_eh (Stromeinfuhren und -ausfuhren nach Partnerland), CC BY 4.0",
            "url": "https://ec.europa.eu/eurostat/databrowser/view/nrg_ti_eh/default/table"}


FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"


def us_zoll_effektiv():
    """Effektive Zollbelastung der USA je Quartal: Zolleinnahmen des Bundes (BEA, B235RC1Q027SBEA, Mrd. USD, Jahresrate)
    geteilt durch die Warenimporte (Census/BEA, BOPGIMP, Mio. USD je Monat, aufs Jahr hochgerechnet). Abgeleitet, nicht
    amtlich veröffentlicht; beide Reihen gemeinfrei (US-Bundesbehörden), abgerufen über FRED ohne Schlüssel."""
    def reihe(sid):
        txt = urllib.request.urlopen(urllib.request.Request(FRED.format(sid), headers={"User-Agent": "Unternehmenskennzahlen/1.0"}), timeout=60).read().decode()
        out = {}
        for z in txt.strip().splitlines()[1:]:
            d, v = z.split(",")
            if v not in ("", "."):
                out[d] = float(v)
        return out
    zoll, imp = reihe("B235RC1Q027SBEA"), reihe("BOPGIMP")
    werte = []
    for d, z in sorted(zoll.items()):
        j, m = int(d[:4]), int(d[5:7])
        monate = [f"{j}-{m + i:02d}-01" for i in range(3)]
        if all(x in imp for x in monate) and j >= 2015:
            werte.append([f"{j}-Q{(m - 1) // 3 + 1}", round(z / (sum(imp[x] for x in monate) * 4 / 1000) * 100, 2)])
    return {"werte": werte, "name": "Effektive Zollbelastung der USA (Zolleinnahmen ÷ Warenimporte)", "einheit": "%",
            "quelle": "abgeleitet aus BEA (Zolleinnahmen, B235RC1Q027SBEA) und Census/BEA (Warenimporte, BOPGIMP) über FRED",
            "url": "https://fred.stlouisfed.org/series/B235RC1Q027SBEA"}


def raeume():
    out = []
    for r in csv.DictReader(open(RAEUME, encoding="utf-8")):
        out.append({"id": r["id"], "name": r["name"], "kurz": r["kurz"], "art": r["art"], "farbe": r["farbe"],
                    "mitglieder": r["mitglieder"].split(), "stand": r["stand"], "quelle": r["quelle"], "hinweis": r["hinweis"]})
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ohne-netz", action="store_true")
    a = p.parse_args()
    feat = json.loads((HIER / "geo/laender.geojson").read_text())["features"]
    isos = {f["properties"]["iso"] for f in feat}
    kont = {}
    for f in feat:
        kont.setdefault(f["properties"]["iso"], f["properties"]["kontinent"])
    alt = json.loads(ZIEL.read_text()) if ZIEL.exists() else {}
    if a.ohne_netz:
        laender, meta, strom, uszoll = alt.get("laender", {}), alt.get("reihen", {}), alt.get("strom", {}), alt.get("us_zoll_effektiv")
    else:
        laender, meta = weltbank(isos)
        try:
            strom = eurostat_strom()
        except Exception as e:  # noqa: BLE001
            print("Eurostat-Strom nicht abrufbar, alter Stand bleibt:", e, file=sys.stderr)
            strom = alt.get("strom", {})
        try:
            uszoll = us_zoll_effektiv()
        except Exception as e:  # noqa: BLE001
            print("FRED nicht abrufbar, alter Stand bleibt:", e, file=sys.stderr)
            uszoll = alt.get("us_zoll_effektiv")
    out = {"abruf": date.today().isoformat() if not a.ohne_netz else alt.get("abruf"),
           "quelle": "Weltbank, World Development Indicators (CC BY 4.0)", "url": "https://databank.worldbank.org/source/world-development-indicators",
           "reihen": meta, "laender": laender, "strom": strom, "us_zoll_effektiv": uszoll, "raeume": raeume(), "kontinente": kont}
    ZIEL.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"{ZIEL}: {len(laender)} Länder, {len(strom.get('paare', {}))} Strompaare, {len(out['raeume'])} Wirtschaftsräume", file=sys.stderr)


if __name__ == "__main__":
    main()
