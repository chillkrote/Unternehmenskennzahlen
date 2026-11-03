"""Bilaterale Handelsströme (Warenhandel insgesamt, je Land die wichtigsten Partner) -> data/handel.json für die Weltkugel.

Quelle vorerst: UN Comtrade, öffentlicher Zugang ohne Schlüssel (comtradeapi.un.org/public/v1/preview, höchstens 500 Zeilen je Abruf).
Je meldendes Land zwei Abrufe (Exporte, Importe) für das jüngste gemeldete Jahr (Standard: 2024, sonst das Vorjahr), Warengruppe
TOTAL, alle Partner. Gespeichert werden Summe gegenüber der Welt und die 15 größten Partner je Richtung, Werte in US-Dollar laut
Meldeland (Exporte FOB, Importe meist CIF; Spiegeldaten des Partners weichen davon ab).

Geplant: WTO-Daten (data.wto.org / api.wto.org) als Quelle, sobald ein kostenloser API-Schlüssel vorliegt (Umgebungsvariable
WTO_API_KEY); die Weboberfläche data.wto.org lehnt automatische Abrufe ab (403), die API verlangt den Schlüssel.

    python3 app/handel_abruf.py [--jahr 2024] [--top 15]
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

HIER = Path(__file__).resolve().parent
ZIEL = HIER / "data/handel.json"
BASIS = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
REF = "https://comtradeapi.un.org/files/v1/app/reference/"
UA = {"User-Agent": "Unternehmenskennzahlen-Terminal/1.0 (Handelsstroeme)"}


def hole(url, versuche=5):
    for i in range(versuche):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            warte = 45 * (i + 1) if e.code == 429 else 5 * (i + 1)
            print(f"  HTTP {e.code}, warte {warte} s", file=sys.stderr)
            time.sleep(warte)
        except Exception as e:
            print(f"  Fehler {e}, neuer Versuch", file=sys.stderr)
            time.sleep(5 * (i + 1))
    return None


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--jahr", type=int, default=2024)
    p.add_argument("--top", type=int, default=15)
    a = p.parse_args()
    melder = [r for r in hole(REF + "Reporters.json")["results"] if not r.get("isGroup") and len(r.get("reporterCodeIsoAlpha2") or "") == 2]
    partner = {r["PartnerCode"]: r["PartnerCodeIsoAlpha2"] for r in hole(REF + "partnerAreas.json")["results"]
               if len(r.get("PartnerCodeIsoAlpha2") or "") == 2 and r["PartnerCodeIsoAlpha2"].isalpha() and not r.get("isGroup")}
    alt = json.loads(ZIEL.read_text()) if ZIEL.exists() else {"laender": {}}
    laender = {}
    for n, m in enumerate(melder, 1):
        iso = m["reporterCodeIsoAlpha2"]
        eintrag = None
        for jahr in (a.jahr, a.jahr - 1):
            e = {"jahr": jahr}
            for fluss, name in (("X", "export"), ("M", "import")):
                q = urllib.parse.urlencode({"reporterCode": m["reporterCode"], "period": jahr, "cmdCode": "TOTAL", "flowCode": fluss})
                d = hole(f"{BASIS}?{q}")
                time.sleep(2.0)
                zeilen = (d or {}).get("data") or []
                welt = next((z["primaryValue"] for z in zeilen if z["partnerCode"] == 0), None)
                paare = sorted(((partner[z["partnerCode"]], z["primaryValue"]) for z in zeilen
                                if z["partnerCode"] in partner and partner[z["partnerCode"]] != iso and z["primaryValue"]), key=lambda x: -x[1])
                if welt:
                    e[name + "_welt"] = round(welt)
                    e[name] = [[pi, round(v)] for pi, v in paare[:a.top]]
            if "export" in e or "import" in e:
                eintrag = e
                break
        if eintrag:
            laender[iso] = eintrag
        elif iso in alt["laender"]:
            laender[iso] = alt["laender"][iso]       # Abruf gescheitert: alten Stand behalten
        print(f"{n}/{len(melder)} {iso} {eintrag['jahr'] if eintrag else '-'}", file=sys.stderr)
    ZIEL.write_text(json.dumps({"quelle": "UN Comtrade (comtradeapi.un.org, öffentlicher Zugang), Warenhandel insgesamt (HS TOTAL), US-Dollar laut Meldeland",
                                "url": "https://comtradeplus.un.org/", "abruf": date.today().isoformat(), "top": a.top, "laender": laender},
                               ensure_ascii=False, separators=(",", ":")))
    print(f"{len(laender)} Länder -> {ZIEL} ({ZIEL.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
