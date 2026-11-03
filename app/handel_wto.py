#!/usr/bin/env python3
"""Handelsdaten der WTO (Timeseries-API, api.wto.org) für die Weltkugel: app/data/handel_wto.json

Wichtig zur Datenlage (geprüft 03.11.2026): Die WTO-Zeitreihen-API liefert Warenhandel NUR gegen "Welt"
(Indikatoren ITS_MTV_AX/AM haben 3 Partner: Welt, EU, Extra-EU). Bilaterale Werte nach Partnerland gibt es dort
nur für DIENSTLEISTUNGEN (ITS_CS_AX6/AM6, EBOPS 2010, Summe "S"); davon melden nur rund 45 Berichtsländer (EU, USA, GB, JP, CN u. a.)
Partnerwerte, alle anderen nur gegen Welt.
Bilateraler Warenhandel steht nicht in dieser API; dafür bleibt UN Comtrade (app/handel_abruf.py).

Schlüssel: Umgebungsvariable WTO_API_KEY (Header Ocp-Apim-Subscription-Key). Er wird nie ausgegeben oder gespeichert.
Aufruf: python3 app/handel_wto.py   (ohne Netz-Zugriff auf die WTO bricht das Skript ab, die Datei bleibt unverändert)

Format (je Land, ISO2 wie in app/geo/laender.geojson):
  "DE": { "jahr": 2025, "export_welt": Mio. USD Waren, "import_welt": ...,           # Warenhandel gesamt, Partner Welt
          "dl_jahr": 2024, "dl_export_welt": Mio. USD Dienstleistungen, "dl_import_welt": ...,
          "dl_export": [[ISO2, Mio. USD], ...], "dl_import": [...] }                 # bilateral, absteigend, Top 40
Werte in Mio. US-Dollar (WTO-Einheit USM), nicht in USD. Die Comtrade-Quelle schreibt USD; Umrechnung beim Zusammenführen beachten.
"""
import json
import os
import sys
import urllib.request
from datetime import date
from pathlib import Path

HIER = Path(__file__).resolve().parent
BASIS = "https://api.wto.org/timeseries/v1"
UA = "Mozilla/5.0 (compatible; Kennzahlen-Terminal/1.0)"
JAHRE = "2025,2024,2023,2022"   # neuester verfügbarer Wert je Land wird genommen
TOP = 40


def holen(pfad, **p):
    key = os.environ.get("WTO_API_KEY")
    if not key:
        sys.exit("WTO_API_KEY fehlt (Umgebungsvariable mit dem Subscription-Key der WTO).")
    q = "&".join(f"{k}={v}" for k, v in p.items())
    req = urllib.request.Request(f"{BASIS}/{pfad}?{q}", headers={"Ocp-Apim-Subscription-Key": key, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("cp1252", errors="replace"))


def daten(indikator, **p):
    return holen("data", i=indikator, ps=JAHRE, fmt="json", mode="full", meta="false", max=500000, **p)["Dataset"]


def neueste(zeilen):
    """je (Berichtsland, Partner) der Wert des jüngsten Jahres; None-Werte übersprungen"""
    out = {}
    for z in zeilen:
        if z["Value"] is None:
            continue
        k = (z["ReportingEconomyCode"], z["PartnerEconomyCode"])
        if k not in out or z["Year"] > out[k][0]:
            out[k] = (z["Year"], z["Value"])
    return out


def main():
    geo = json.loads((HIER / "geo/laender.geojson").read_text())
    iso3_zu_2 = {f["properties"]["a3"]: f["properties"]["iso"] for f in geo["features"] if f["properties"].get("a3")}
    code_zu_iso2 = {}
    for e in holen("partners", lang=1):
        if e.get("iso3A") in iso3_zu_2:
            code_zu_iso2[e["code"]] = iso3_zu_2[e["iso3A"]]

    waren_x = neueste(daten("ITS_MTV_AX", r="all", p="000", pc="TO"))
    waren_m = neueste(daten("ITS_MTV_AM", r="all", p="000", pc="TO"))
    dl_x = neueste(daten("ITS_CS_AX6", r="all", p="all", pc="S"))
    dl_m = neueste(daten("ITS_CS_AM6", r="all", p="all", pc="S"))

    laender = {}
    def land(code):
        iso = code_zu_iso2.get(code)
        return laender.setdefault(iso, {}) if iso else None

    for (r, p), (j, v) in waren_x.items():
        if (l := land(r)) is not None:
            l["jahr"] = max(l.get("jahr", 0), j); l["export_welt"] = v
    for (r, p), (j, v) in waren_m.items():
        if (l := land(r)) is not None:
            l["jahr"] = max(l.get("jahr", 0), j); l["import_welt"] = v

    for name, quelle in (("export", dl_x), ("import", dl_m)):
        paare = {}
        for (r, p), (j, v) in quelle.items():
            l = land(r)
            if l is None:
                continue
            l["dl_jahr"] = max(l.get("dl_jahr", 0), j)
            if p == "000":
                l[f"dl_{name}_welt"] = v
            elif p in code_zu_iso2 and v > 0:
                paare.setdefault(code_zu_iso2[r], []).append([code_zu_iso2[p], v])
        for iso, liste in paare.items():
            liste.sort(key=lambda x: -x[1])
            laender[iso][f"dl_{name}"] = liste[:TOP]

    out = {"quelle": "WTO Timeseries API (api.wto.org), ITS_MTV_AX/AM, ITS_CS_AX6/AM6", "einheit": "Mio. USD",
           "abgerufen": date.today().isoformat(),
           "hinweis": "Warenhandel nur gegen Welt; bilaterale Werte nur für Dienstleistungen.", "laender": laender}
    ziel = HIER / "data/handel_wto.json"
    ziel.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(laender)} Länder, mit Dienstleistungs-Partnern: {sum(1 for l in laender.values() if 'dl_export' in l)} -> {ziel}")


if __name__ == "__main__":
    main()
