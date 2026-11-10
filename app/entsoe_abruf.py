"""Grenzüberschreitende physikalische Stromflüsse (ENTSO-E Transparency Platform, Artikel 12.1.G) je Monat: data/strom_entsoe.json.

Ergänzt den Reiter Handel (Stromhandel), der bisher nur Jahreswerte aus Eurostat zeigt, um volle Monate bis zum Vormonat.
Je Grenze und Richtung documentType A11 (parallel), stündliche bzw. viertelstündliche Leistung in MW wird zu Energie in GWh
je Monat (UTC) aufsummiert. Lücken bleiben Lücken (kein Auffüllen).

Zeitraum: Die Plattform erlaubt höchstens ein Jahr je Abfrage. Längere Zeiträume (--monate 24, 36 …) werden in aneinander
anschließende Fenster von höchstens zwölf Monaten geteilt (fenster) und je Richtung zusammengeführt. Die Fenster überlappen nicht, und
jeder Wert wird nur dem Fenster zugerechnet, in dem sein Zeitpunkt liegt (monatswerte: von/bis), es gibt also keine doppelten Monate.
Monatsgrenzen sind UTC (00:00 UTC am Monatsersten), nicht Ortszeit: ein Monat in MEZ beginnt eine Stunde früher.

Vollständigkeit: Zu jedem Monatswert wird gezählt, wie viele Stunden des Monats die Quelle geliefert hat. Monate mit weniger als
99,5 % der Stunden stehen unter "abdeckung" (Anteil 0 bis 1); ihr GWh-Wert ist dann eine Untergrenze, kein Monatswert. Monate ganz ohne
Daten sind null. Richtungen ganz ohne Daten stehen unter "ohne_daten".

Fehler: Schlägt eine Richtung nach allen Wiederholungen fehl, bleiben für sie die Werte der bisherigen Datei stehen ("uebernommen");
fällt mehr als ein Viertel der Richtungen aus, wird nichts geschrieben und die alte Datei bleibt, wie sie ist.

Schlüssel: Umgebungsvariable entsoe_api (oder ENTSOE_API_KEY). Er wird nie ausgegeben oder gespeichert; Fehlermeldungen
nennen nur Grenze und HTTP-Status. Ohne Schlüssel bricht das Skript ab und lässt die alte Datei stehen.
Nutzung: Daten der Übertragungsnetzbetreiber; Bedingungen siehe docs/datenquellen.md (ENTSO-E).

    python3 app/entsoe_abruf.py                 # letzte zwölf volle Monate
    python3 app/entsoe_abruf.py --monate 36     # drei Abfragefenster je Richtung
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
VOLL = 0.995                   # ab diesem Anteil der Stunden gilt ein Monat als vollständig (einzelne fehlende Stunden)
MAX_FENSTER = 12               # Monate je Abfrage (Grenze der Plattform: ein Jahr)
MAX_AUSFALL = 0.25             # höchstens dieser Anteil der Richtungen darf fehlschlagen, sonst bleibt die alte Datei


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


def monatsstunden(xml_bytes, von=None, bis=None):
    """{"JJJJ-MM": [GWh, Stunden mit Daten]} aus einem Publication_MarketDocument (Leistung in MW je Intervall, Zeit in UTC).

    Kurventyp A03 (Regelfall bei A11): ein Punkt gilt, bis der nächste Punkt kommt; fehlende Positionen wiederholen also den
    letzten Wert, bis zum Ende des Zeitintervalls der Periode. Bei A01 steht jede Position einzeln da (gleiche Rechnung).
    von/bis (UTC): nur Intervalle, die in [von, bis) beginnen, zählen; so kann ein Fenster nichts in das Nachbarfenster tragen.
    Liefert die Quelle denselben Zeitpunkt in zwei Perioden, zählt er einmal (der zuerst gelesene Wert).
    """
    wurzel = ET.fromstring(xml_bytes)
    ns = {"n": re.match(r"\{(.*)\}", wurzel.tag).group(1)} if wurzel.tag.startswith("{") else {"n": ""}
    zeit = lambda s: datetime.strptime(s, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
    out, gesehen = {}, set()
    for per in wurzel.iterfind(".//n:Period", ns):
        start = zeit(per.find("n:timeInterval/n:start", ns).text)
        ende = zeit(per.find("n:timeInterval/n:end", ns).text)
        h = AUFLOESUNG.get(per.find("n:resolution", ns).text)
        if h is None:
            continue
        anzahl = round((ende - start).total_seconds() / 3600 / h)
        pkte = sorted((int(pt.find("n:position", ns).text), float(pt.find("n:quantity", ns).text)) for pt in per.iterfind("n:Point", ns))
        for i, (pos, mw) in enumerate(pkte):
            bis_pos = pkte[i + 1][0] if i + 1 < len(pkte) else anzahl + 1
            for q in range(pos, bis_pos):
                t = start + timedelta(hours=h * (q - 1))
                if (von and t < von) or (bis and t >= bis) or t in gesehen:
                    continue
                gesehen.add(t)
                e = out.setdefault(t.strftime("%Y-%m"), [0.0, 0.0])
                e[0] += mw * h / 1000
                e[1] += h
    return out


def monatswerte(xml_bytes, von=None, bis=None):
    """{"JJJJ-MM": GWh}, siehe monatsstunden."""
    return {m: e[0] for m, e in monatsstunden(xml_bytes, von, bis).items()}


def zeitraum(monate, heute=None):
    """(Beginn, Ende) in UTC: `monate` volle Monate bis zum Vormonat von `heute`; Ende ist der Erste des laufenden Monats."""
    if monate < 1:
        raise ValueError("monate muss mindestens 1 sein")
    heute = heute or date.today()
    ende = date(heute.year, heute.month, 1)
    j, m = ende.year, ende.month - monate
    while m <= 0:
        j, m = j - 1, m + 12
    return datetime(j, m, 1, tzinfo=timezone.utc), datetime(ende.year, ende.month, 1, tzinfo=timezone.utc)


def _plus_monate(t, n):
    m = t.year * 12 + t.month - 1 + n
    return t.replace(year=m // 12, month=m % 12 + 1)


def monatsliste(start, ende):
    out, t = [], start
    while t < ende:
        out.append(t.strftime("%Y-%m"))
        t = _plus_monate(t, 1)
    return out


def fenster(start, ende, max_monate=MAX_FENSTER):
    """Teilt [start, ende) in aneinander anschließende Abfragefenster von höchstens max_monate Monaten (ältestes zuerst)."""
    out, t = [], start
    while t < ende:
        n = min(_plus_monate(t, max_monate), ende)
        out.append((t, n))
        t = n
    return out


def stunden_im_monat(m):
    a = datetime(int(m[:4]), int(m[5:7]), 1, tzinfo=timezone.utc)
    return (_plus_monate(a, 1) - a).total_seconds() / 3600


def richtung(token, von, nach, start, ende, hole=None):
    """Alle Fenster einer Richtung zusammengeführt: {"JJJJ-MM": [GWh, Stunden]} oder None, wenn kein Fenster Daten hat."""
    hole = hole or abfrage
    ges, etwas = {}, False
    for a, b in fenster(start, ende):
        x = hole(token, von, nach, a, b)
        if x is None:
            continue
        etwas = True
        for m, e in monatsstunden(x, a, b).items():
            if m in ges:                                # kann wegen von/bis nicht vorkommen; zur Sicherheit nie addieren
                raise RuntimeError(f"{von}>{nach}: Monat {m} in zwei Fenstern")
            ges[m] = e
    return ges if etwas else None


def zusammenstellen(monate, ergebnis, alt=None, heute=None):
    """Baut die Ausgabedatei. ergebnis: {(von, nach): {"JJJJ-MM": [GWh, h]} | None | Exception}; alt: bisherige Datei (für Ausfälle)."""
    paare, fehlt, abdeckung, uebernommen = {}, [], {}, []
    alt_m = {m: i for i, m in enumerate((alt or {}).get("monate") or [])}
    for (von, nach), w in ergebnis.items():
        k = f"{von}>{nach}"
        if isinstance(w, Exception):
            reihe = ((alt or {}).get("paare") or {}).get(k)
            if reihe is None:
                fehlt.append(k)
                continue
            paare[k] = [reihe[alt_m[m]] if m in alt_m else None for m in monate]
            ab = {m: a for m, a in (((alt or {}).get("abdeckung") or {}).get(k) or {}).items() if m in monate}
            if ab:
                abdeckung[k] = ab
            uebernommen.append(k)
        elif w is None:
            fehlt.append(k)
        else:
            paare[k] = [round(w[m][0], 1) if m in w else None for m in monate]
            ab = {m: round(w[m][1] / stunden_im_monat(m), 3) for m in monate if m in w and w[m][1] < VOLL * stunden_im_monat(m)}
            if ab:
                abdeckung[k] = ab
    luecken = sum(1 for l in paare.values() for v in l if v is None)
    return {"quelle": "ENTSO-E Transparency Platform, Cross-Border Physical Flows (12.1.G)", "url": "https://transparency.entsoe.eu/",
            "abruf": (heute or date.today()).isoformat(), "einheit": "GWh", "monate": monate, "paare": paare, "ohne_daten": fehlt,
            "abdeckung": abdeckung, "uebernommen": uebernommen,
            "vollstaendigkeit": {"richtungen": len(paare), "monate": len(monate), "monate_ohne_daten": luecken,
                                 "monate_teilweise": sum(len(v) for v in abdeckung.values())},
            "hinweis": "Physikalische Flüsse je Grenze und Richtung, Summe der Leistung über die Zeit (UTC-Monate); keine Handelsgeschäfte. "
                       "abdeckung: Monate, in denen die Quelle nicht alle Stunden geliefert hat (Anteil der Stunden); der Wert ist dann eine Untergrenze. "
                       "uebernommen: Richtungen, deren Abruf fehlschlug und die den Stand der vorherigen Datei behalten."}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--monate", type=int, default=12, help="so viele volle Monate bis zum Vormonat; mehr als 12 werden in mehrere Abfragen geteilt")
    ap.add_argument("--parallel", type=int, default=6, help="gleichzeitige Abfragen (Standard 6)")
    a = ap.parse_args(argv)
    token = schluessel()
    start, ende = zeitraum(a.monate)
    monate = monatsliste(start, ende)
    richtungen = [r for g in GRENZEN for r in (tuple(g.split("-")), tuple(g.split("-")[::-1]))]

    def hole(r):
        try:
            w = richtung(token, r[0], r[1], start, ende)
        except RuntimeError as e:                       # Meldung enthält nur Grenze und Status, nie die URL
            print(f"  {e}", file=sys.stderr)
            return r, e
        print(f"  {r[0]}>{r[1]}: {'keine Daten' if w is None else 'ok'}", file=sys.stderr)
        return r, w

    # eine Abfrage für zwölf Monate Viertelstundenwerte dauert rund zehn Sekunden; parallel, weit unter 400 Abfragen je Minute
    with ThreadPoolExecutor(max_workers=a.parallel) as ex:
        ergebnis = dict(ex.map(hole, richtungen))
    ausfall = sum(1 for w in ergebnis.values() if isinstance(w, Exception))
    if ausfall > MAX_AUSFALL * len(richtungen):
        raise SystemExit(f"{ausfall} von {len(richtungen)} Richtungen fehlgeschlagen; {ZIEL.name} bleibt unverändert")
    alt = json.loads(ZIEL.read_text(encoding="utf-8")) if ZIEL.exists() else None
    out = zusammenstellen(monate, ergebnis, alt)
    tmp = ZIEL.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(ZIEL)                                   # erst nach vollständigem Schreiben ersetzen
    v = out["vollstaendigkeit"]
    print(f"{ZIEL}: {len(out['paare'])} Richtungen mit Daten, {len(out['ohne_daten'])} ohne, {len(out['uebernommen'])} aus altem Stand, "
          f"Monate {monate[0]} bis {monate[-1]} ({len(monate)}), {v['monate_ohne_daten']} Monatswerte fehlen, {v['monate_teilweise']} unvollständig",
          file=sys.stderr)


if __name__ == "__main__":
    main()
