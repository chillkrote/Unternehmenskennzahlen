"""Grenzüberschreitende physikalische Stromflüsse (ENTSO-E Transparency Platform, Artikel 12.1.G) je Monat: data/strom_entsoe.json.

Ergänzt den Reiter Handel (Stromhandel), der bisher nur Jahreswerte aus Eurostat zeigt, um die letzten zwölf vollen Monate.
Je Grenze und Richtung eine Abfrage (documentType A11, parallel), stündliche bzw. viertelstündliche Leistung in MW wird zu Energie in GWh
je Monat (UTC) aufsummiert. Lücken bleiben Lücken (kein Auffüllen).

Schlüssel: Umgebungsvariable entsoe_api (oder ENTSOE_API_KEY). Er wird nie ausgegeben oder gespeichert; Fehlermeldungen
nennen nur Grenze und HTTP-Status. Ohne Schlüssel bricht das Skript ab und lässt die alte Datei stehen.
Nutzung: Daten der Übertragungsnetzbetreiber; Bedingungen siehe docs/datenquellen.md (ENTSO-E).

    python3 app/entsoe_abruf.py                 # letzte zwölf volle Monate
    python3 app/entsoe_abruf.py --monate 24
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
ZIEL = HIER / "data/strom_entsoe.json"
API = "https://web-api.tp.entsoe.eu/api"
# Länder-Gebiete (EIC) der Transparenzplattform
EIC = {
    "AL": "10YAL-KESH-----5", "AT": "10YAT-APG------L", "BA": "10YBA-JPCC-----D", "BE": "10YBE----------2", "BG": "10YCA-BULGARIA-R",
    "CH": "10YCH-SWISSGRIDZ", "CZ": "10YCZ-CEPS-----N", "DE": "10Y1001A1001A83F", "DK": "10Y1001A1001A65H", "EE": "10Y1001A1001A39I",
    "ES": "10YES-REE------0", "FI": "10YFI-1--------U", "FR": "10YFR-RTE------C", "GB": "10YGB----------A", "GR": "10YGR-HTSO-----Y",
    "HR": "10YHR-HEP------M", "HU": "10YHU-MAVIR----U", "IE": "10YIE-1001A00010", "IT": "10YIT-GRTN-----B", "LT": "10YLT-1001A0008Q",
    "LU": "10YLU-CEGEDEL-NQ", "LV": "10YLV-1001A00074", "ME": "10YCS-CG-TSO---S", "MK": "10YMK-MEPSO----8", "NL": "10YNL----------L",
    "NO": "10YNO-0--------C", "PL": "10YPL-AREA-----S", "PT": "10YPT-REN------W", "RO": "10YRO-TEL------P", "RS": "10YCS-SERBIATSOV",
    "SE": "10YSE-1--------K", "SI": "10YSI-ELES-----O", "SK": "10YSK-SEPS-----K",
}
GRENZEN = """DE-AT DE-BE DE-CH DE-CZ DE-DK DE-FR DE-LU DE-NL DE-NO DE-PL DE-SE FR-BE FR-CH FR-ES FR-GB FR-IT ES-PT IT-AT IT-CH IT-GR
IT-SI IT-ME AT-CH AT-CZ AT-HU AT-SI CZ-PL CZ-SK PL-LT PL-SE PL-SK SK-HU HU-HR HU-RO HU-RS HU-SI HR-BA HR-RS HR-SI RO-BG RO-RS
BG-GR BG-MK BG-RS GR-AL GR-MK NL-BE NL-DK NL-GB NL-NO BE-GB BE-LU DK-GB DK-NO DK-SE NO-GB NO-SE NO-FI SE-FI SE-LT FI-EE EE-LV
LV-LT GB-IE ME-AL ME-BA ME-RS RS-AL RS-BA RS-MK""".split()
AUFLOESUNG = {"PT15M": 0.25, "PT30M": 0.5, "PT60M": 1.0}


def schluessel():
    k = os.environ.get("entsoe_api") or os.environ.get("ENTSOE_API_KEY")
    if not k:
        raise SystemExit("Kein ENTSO-E-Schlüssel (Umgebungsvariable entsoe_api bzw. ENTSOE_API_KEY); alte Datei bleibt unverändert")
    return k


def abfrage(token, von, nach, start, ende, versuche=4):
    """XML der physikalischen Flüsse von -> nach; None, wenn die Plattform keine Daten hat (Acknowledgement)."""
    p = {"securityToken": token, "documentType": "A11", "in_Domain": EIC[nach], "out_Domain": EIC[von],
         "periodStart": start.strftime("%Y%m%d%H%M"), "periodEnd": ende.strftime("%Y%m%d%H%M")}
    url = API + "?" + urllib.parse.urlencode(p)
    for i in range(versuche):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Unternehmenskennzahlen/1.0"}), timeout=120) as r:
                b = r.read()
            return None if b"Acknowledgement_MarketDocument" in b[:400] else b
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):                  # keine Daten für diese Grenze oder diesen Zeitraum
                return None
            fehler = f"HTTP {e.code}"
        except Exception as e:  # noqa: BLE001
            fehler = type(e).__name__
        if i == versuche - 1:
            raise RuntimeError(f"{von}>{nach}: {fehler}")   # ohne URL: sie enthält den Schlüssel
        print(f"  Wiederholung {von}>{nach}: {fehler}", file=sys.stderr)
        time.sleep(5 * (i + 1))


def monatswerte(xml_bytes):
    """{"JJJJ-MM": GWh} aus einem Publication_MarketDocument (Leistung in MW je Intervall, Zeit in UTC).

    Kurventyp A03 (Regelfall bei A11): ein Punkt gilt, bis der nächste Punkt kommt; fehlende Positionen wiederholen also den
    letzten Wert, bis zum Ende des Zeitintervalls der Periode. Bei A01 steht jede Position einzeln da (gleiche Rechnung).
    """
    wurzel = ET.fromstring(xml_bytes)
    ns = {"n": re.match(r"\{(.*)\}", wurzel.tag).group(1)} if wurzel.tag.startswith("{") else {"n": ""}
    zeit = lambda s: datetime.strptime(s, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
    out = {}
    for per in wurzel.iterfind(".//n:Period", ns):
        start = zeit(per.find("n:timeInterval/n:start", ns).text)
        ende = zeit(per.find("n:timeInterval/n:end", ns).text)
        h = AUFLOESUNG.get(per.find("n:resolution", ns).text)
        if h is None:
            continue
        anzahl = round((ende - start).total_seconds() / 3600 / h)
        pkte = sorted((int(pt.find("n:position", ns).text), float(pt.find("n:quantity", ns).text)) for pt in per.iterfind("n:Point", ns))
        for i, (pos, mw) in enumerate(pkte):
            bis = pkte[i + 1][0] if i + 1 < len(pkte) else anzahl + 1
            for q in range(pos, bis):
                m = (start + timedelta(hours=h * (q - 1))).strftime("%Y-%m")
                out[m] = out.get(m, 0.0) + mw * h / 1000
    return out


def zeitraum(monate, heute=None):
    heute = heute or date.today()
    ende = date(heute.year, heute.month, 1)
    j, m = ende.year, ende.month - monate
    while m <= 0:
        j, m = j - 1, m + 12
    return datetime(j, m, 1, tzinfo=timezone.utc), datetime(ende.year, ende.month, 1, tzinfo=timezone.utc)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--monate", type=int, default=12, help="so viele volle Monate bis zum Vormonat (höchstens 12 je Abfrage)")
    ap.add_argument("--parallel", type=int, default=6, help="gleichzeitige Abfragen (Standard 6)")
    a = ap.parse_args()
    token = schluessel()
    start, ende = zeitraum(min(a.monate, 12))
    monate = []
    t = start
    while t < ende:
        monate.append(t.strftime("%Y-%m"))
        t = (t.replace(day=28) + timedelta(days=4)).replace(day=1)
    richtungen = [r for g in GRENZEN for r in (tuple(g.split("-")), tuple(g.split("-")[::-1]))]

    def hole(r):
        von, nach = r
        b = abfrage(token, von, nach, start, ende)
        w = monatswerte(b) if b is not None else None
        print(f"  {von}>{nach}: {'keine Daten' if w is None else 'ok'}", file=sys.stderr)
        return r, w

    # eine Abfrage für zwölf Monate Viertelstundenwerte dauert rund zehn Sekunden; parallel, weit unter 400 Abfragen je Minute
    with ThreadPoolExecutor(max_workers=a.parallel) as ex:
        ergebnis = dict(ex.map(hole, richtungen))
    paare, fehlt = {}, []
    for von, nach in richtungen:
        w = ergebnis[(von, nach)]
        if w is None:
            fehlt.append(f"{von}>{nach}")
        else:
            paare[f"{von}>{nach}"] = [round(w[m], 1) if m in w else None for m in monate]
    out = {"quelle": "ENTSO-E Transparency Platform, Cross-Border Physical Flows (12.1.G)", "url": "https://transparency.entsoe.eu/",
           "abruf": date.today().isoformat(), "einheit": "GWh", "monate": monate, "paare": paare, "ohne_daten": fehlt,
           "hinweis": "Physikalische Flüsse je Grenze und Richtung, Summe der Leistung über die Zeit (UTC-Monate); keine Handelsgeschäfte."}
    ZIEL.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{ZIEL}: {len(paare)} Richtungen mit Daten, {len(fehlt)} ohne, Monate {monate[0]} bis {monate[-1]}", file=sys.stderr)


if __name__ == "__main__":
    main()
