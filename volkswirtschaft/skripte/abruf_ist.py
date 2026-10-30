"""Ruft die tatsächlichen Jahreswerte für Deutschland ab (Eurostat-API, ohne Schlüssel) und schreibt sie nach prognosen_ist.csv.

Die Datei prognosen_ist.csv enthält zwei Arten von Zeilen:
  quelle = Eurostat            vom Skript geschrieben (vintage `aktuell` = heutiger, revidierter Stand)
  alle anderen Quellen         handgepflegt aus der Gemeinschaftsdiagnose (vintage `erst` = Stand im Frühjahr nach dem Jahr, also die ersten
                               Jahresergebnisse des Statistischen Bundesamts; Verbraucherpreise und Arbeitslosenquote nach BA stehen auch als `aktuell`)
Das Skript ersetzt nur die Eurostat-Zeilen. Danach `python3 -I abgleich_prognosen.py` ausführen.
Aufruf: python3 -I abruf_ist.py
"""
import csv
import json
import urllib.request
from datetime import date
from pathlib import Path

AUS = Path(__file__).resolve().parents[1]
API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
SEIT, BIS = 2014, 2025
FELDER = ["groesse", "jahr", "vintage", "wert", "einheit", "quelle", "beleg", "url", "abruf", "hinweis"]
# groesse, Datensatz, Filter, Einheit, Hinweis
REIHEN = [
    ("bip_wachstum", "nama_10_gdp", "geo=DE&unit=CLV_PCH_PRE&na_item=B1GQ", "%", "BIP real, Veränderung ggü. Vorjahr (preisbereinigt, unbereinigt)"),
    ("inflation_hvpi", "prc_hicp_aind", "geo=DE&unit=RCH_A_AVG&coicop=CP00", "%", "Harmonisierter Verbraucherpreisindex, Jahresdurchschnitt"),
    ("arbeitslosenquote_ilo", "une_rt_a", "geo=DE&unit=PC_ACT&sex=T&age=Y15-74", "%", "Erwerbslosenquote nach ILO (nicht die Quote der Bundesagentur)"),
    ("finanzierungssaldo", "gov_10dd_edpt1", "geo=DE&unit=PC_GDP&sector=S13&na_item=B9", "% des BIP", "Finanzierungssaldo des Staates in % des BIP (ESVG), + = Überschuss"),
]


def hole(ds, filt):
    url = f"{API}{ds}?{filt}&sinceTimePeriod={SEIT}&format=JSON&lang=EN"
    d = json.loads(urllib.request.urlopen(url, timeout=90).read())
    zeit = d["dimension"]["time"]["category"]["index"]
    return url, {int(t): d["value"][str(i)] for t, i in zeit.items() if str(i) in d["value"]}


def main():
    p = AUS / "prognosen_ist.csv"
    alt = list(csv.DictReader(open(p, encoding="utf-8"))) if p.exists() else []
    neu, heute = [], date.today().isoformat()
    for gr, ds, filt, einh, hint in REIHEN:
        url, w = hole(ds, filt)
        for j, v in sorted(w.items()):
            if j <= BIS:
                neu.append(dict(groesse=gr, jahr=j, vintage="aktuell", wert=v, einheit=einh, quelle="Eurostat", beleg="Eurostat-API", url=url, abruf=heute, hinweis=hint))
        print(gr, len(w), "Jahre")
    zeilen = [r for r in alt if r["quelle"] != "Eurostat"] + neu
    zeilen.sort(key=lambda r: (r["groesse"], int(r["jahr"]), r["vintage"]))
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, FELDER)
        w.writeheader()
        w.writerows({k: r.get(k, "") for k in FELDER} for r in zeilen)


if __name__ == "__main__":
    main()
