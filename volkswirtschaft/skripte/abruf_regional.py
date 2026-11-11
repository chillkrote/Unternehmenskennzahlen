"""Regionale Wirtschaftsdaten der 400 Kreise und kreisfreien Städte (NUTS-3).

Primärquelle für Deutschland ist der Arbeitskreis „Volkswirtschaftliche Gesamtrechnungen der Länder“ (VGRdL, Statistische Ämter
des Bundes und der Länder): „Bruttoinlandsprodukt, Bruttowertschöpfung in den kreisfreien Städten und Landkreisen“, Reihe 2,
Kreisergebnisse Band 1 (Excel von statistikportal.de). Sie ist aktueller als die Kreiswerte bei Eurostat (Revision 2024, ein Jahr
länger) und weicht für einzelne Kreise deutlich von ihnen ab (abgleich_eurostat.csv). Eurostat liefert zusätzlich das BIP je
Einwohner in Kaufkraftstandards (EU-27 = 100) für den europäischen Vergleich.

Schreibt in volkswirtschaft/regional/:
  serien.csv            eine Zeile je Reihe, Spalten wie volkswirtschaft/serien.csv plus `ebene` und `erwartet`
  zeitreihe_lang.csv    serie_id, geo, zeit, wert   (geo = NUTS-3-Code wie DE111, zeit = Jahr)
  abgleich_eurostat.csv BIP je Kreis und Jahr bei VGRdL und Eurostat mit Abweichung (nur Abweichungen über 1 %)
  rohdaten/             unveränderte Quelldateien (Excel der VGRdL, Eurostat-Antworten als .json.gz)
regionen.csv (nuts3, ags, name, name_eurostat, land) ist die amtliche Zuordnung NUTS-3 <-> Kreisschlüssel aus der LAU-NUTS-Korrespondenz
von Eurostat; neu erzeugen mit --zuordnung EU-27-LAU-2024-NUTS-2024.xlsx (https://ec.europa.eu/eurostat/documents/345175/501971/
EU-27-LAU-2024-NUTS-2024.xlsx, 19 MB, nicht im Repo). Die VGRdL-Datei nennt dieselben NUTS-3-Codes; das Skript prüft die Übereinstimmung.

Nutzungsbedingungen VGRdL (Impressum der Datei): „Vervielfältigung und Verbreitung, auch auszugsweise, mit Quellenangabe gestattet.“
Erwerbstätige und Einwohner dürfen nur mit einer Nachkommastelle (in Tausend) weitergegeben werden; das Skript rundet sie so.
Eurostat: CC BY 4.0.

Aufruf: python3 -I volkswirtschaft/skripte/abruf_regional.py [--vgrdl <xlsx>] [--zuordnung <xlsx>]
Schlägt ein Abruf fehl, bleibt der bisherige Stand unverändert (es wird nichts teilweise geschrieben).
"""
import argparse
import csv
import gzip
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

HIER = Path(__file__).resolve().parent
AUS = HIER.parent / "regional"
SEIT = 2000
FELDER = ["serie_id", "thema", "name", "einheit", "format", "art", "frequenz", "kern", "quelle", "datensatz", "filter", "url",
          "stand_quelle", "abruf", "erster_zeitraum", "letzter_zeitraum", "anzahl", "prognose_ab", "hinweis", "ebene", "erwartet"]
LAND = {"01": "SH", "02": "HH", "03": "NI", "04": "HB", "05": "NW", "06": "HE", "07": "RP", "08": "BW", "09": "BY", "10": "SL",
        "11": "BE", "12": "BB", "13": "MV", "14": "SN", "15": "ST", "16": "TH"}
UA = {"User-Agent": "Mozilla/5.0 (sphaerae Datenabruf)"}

VGRDL_SEITE = "https://www.statistikportal.de/de/vgrdl/ergebnisse-kreisebene/bruttoinlandsprodukt-bruttowertschoepfung-kreise"
VGRDL_NAME = "VGR der Länder (Statistische Ämter des Bundes und der Länder)"
# id, Blatt, name, einheit, format, art, kern, Nachkommastellen (None = wie geliefert), hinweis
VGRDL = [
    ("r3_bip", "1.1", "BIP (nominal)", "Mio. €", "zahl0", "niveau", False, 3, "Bruttoinlandsprodukt in jeweiligen Preisen"),
    ("r3_bip_wachstum", "1.2", "BIP-Wachstum (nominal), ggü. Vorjahr", "%", "pct1", "rate", False, 3,
     "jeweilige Preise, enthält Preisänderungen (preisbereinigte Kreiswerte gibt es nicht)"),
    ("r3_bip_je_einwohner", "6", "BIP je Einwohner", "€", "zahl0", "niveau", True, 0,
     "jeweilige Preise; Städte mit vielen Einpendlern liegen hoch, weil Pendler mitproduzieren, aber nicht als Einwohner zählen"),
    ("r3_bip_je_erwerbstaetigen", "4", "BIP je Erwerbstätigen", "€", "zahl0", "niveau", False, 0, "Arbeitsproduktivität, jeweilige Preise"),
    ("r3_bip_je_arbeitsstunde", "8", "BIP je Arbeitsstunde", "€", "zahl1", "niveau", False, 2, "Stundenproduktivität, jeweilige Preise"),
    ("r3_bevoelkerung", "5", "Einwohner (Jahresdurchschnitt)", "Tsd.", "zahl1", "niveau", False, 1, "Durchschnittsbevölkerung der VGR"),
    ("r3_erwerbstaetige", "3.1", "Erwerbstätige (Arbeitsort)", "Tsd.", "zahl1", "niveau", False, 1, "Inlandskonzept, alle Wirtschaftsbereiche"),
    ("r3_bws", "2.1", "Bruttowertschöpfung", "Mio. €", "zahl0", "niveau", False, 3, "alle Wirtschaftsbereiche (A–T), jeweilige Preise"),
    ("r3_bws_industrie", "2.3.1", "Bruttowertschöpfung Produzierendes Gewerbe ohne Bau", "Mio. €", "zahl0", "niveau", False, 3,
     "Wirtschaftsabschnitte B bis E (Bergbau, Verarbeitendes Gewerbe, Energie, Wasser)"),
    ("r3_bws_dienstleistung", "2.4", "Bruttowertschöpfung Dienstleistungsbereiche", "Mio. €", "zahl0", "niveau", False, 3, "Wirtschaftsabschnitte G bis T"),
]
# id, name, einheit, format, art, Formel (Werte derselben Region und desselben Jahres), Hinweis
ABGELEITET = [
    ("r3_anteil_industrie", "Industrieanteil an der Bruttowertschöpfung", "%", "pct1", "rate",
     lambda w: w["r3_bws_industrie"] / w["r3_bws"] * 100 if w.get("r3_bws") and w.get("r3_bws_industrie") is not None else None,
     "abgeleitet: Bruttowertschöpfung B–E / Bruttowertschöpfung gesamt"),
    ("r3_anteil_dienstleistung", "Dienstleistungsanteil an der Bruttowertschöpfung", "%", "pct1", "rate",
     lambda w: w["r3_bws_dienstleistung"] / w["r3_bws"] * 100 if w.get("r3_bws") and w.get("r3_bws_dienstleistung") is not None else None,
     "abgeleitet: Bruttowertschöpfung G–T / Bruttowertschöpfung gesamt"),
]
EUROSTAT_API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
EUROSTAT = [  # id, name, einheit, format, art, datensatz, filter, hinweis
    ("r3_bip_kks_index", "BIP je Einwohner in KKS (EU-27 = 100)", "Index EU-27 = 100", "zahl0", "index", "nama_10r_3gdp", {"unit": "PPS_HAB_EU27_2020"},
     "Kaufkraftstandards, EU-Durchschnitt = 100 (Eurostat; Stand der Kreisdaten kann hinter VGRdL zurückliegen)"),
]
ABGLEICH = ("nama_10r_3gdp", {"unit": "MIO_EUR"})     # Eurostat-BIP je Kreis, nur zum Abgleich mit VGRdL


def holen(url, versuche=3):
    """GET mit begrenzter Wiederholung. Eurostat leitet bei zu vielen Abrufen auf sorry.ec.europa.eu um (Drosselung): dann warten."""
    import time
    for i in range(versuche):
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120)
        if "sorry.ec.europa.eu" not in r.geturl():
            return r.read()
        if i < versuche - 1:
            time.sleep(30 * (i + 1))
    raise SystemExit(f"Abruf gedrosselt (sorry.ec.europa.eu), später erneut versuchen: {url}")


def vgrdl_url(seite_html, basis=VGRDL_SEITE):
    """Link der Excel-Datei auf der Ergebnisseite (Pfad wechselt mit jeder Ausgabe, z. B. /sites/default/files/2026-09/vgrdl_r2b1_bs2025_4.xlsx)."""
    m = re.findall(r'href="([^"]*vgrdl_r2b1[^"]*\.xlsx)"', seite_html)
    if not m:
        raise SystemExit("VGRdL: kein Link auf vgrdl_r2b1_*.xlsx auf " + basis)
    return urllib.parse.urljoin(basis, m[0])


def vgrdl_lesen(pfad, ags_nuts):
    """Excel der VGRdL -> ({serie: {(nuts3, jahr): wert}}, Stand). Nur Zeilen der NUTS-3-Ebene; Berlin und Hamburg tragen den
    Regionalschlüssel 11 bzw. 02 (wird auf fünf Stellen ergänzt). Der NUTS-Code der Datei muss zu regionen.csv passen."""
    import openpyxl
    wb = openpyxl.load_workbook(pfad, read_only=True)
    stand = ""
    for z in wb["Impressum"].iter_rows(values_only=True):
        t = " ".join(str(c) for c in z if c)
        if t.startswith("Berechnungsstand"):
            stand = t
    werte = {}
    for sid, blatt, *_r, stellen, _h in VGRDL:
        zeilen = list(wb[blatt].iter_rows(values_only=True))
        kopf = next(z for z in zeilen if z and z[0] == "Lfd. Nr.")
        r = {}
        for z in zeilen:
            if not z or z[6] != "3" or not z[2]:
                continue
            ags = str(z[2]).ljust(5, "0")
            nuts = ags_nuts.get(ags)
            if not nuts:
                raise SystemExit(f"VGRdL {blatt}: Kreisschlüssel {ags} ({z[7]}) fehlt in regionen.csv")
            code = str(z[1]).rstrip("x")      # Berlin/Hamburg als NUTS-1 (DE3, DE6); Thüringer Kreise nach Gebietsreform mit „x“
            if not (code == nuts or (code[:3] == nuts[:3] and (len(code) == 3 or code.endswith("x") or str(z[1]).endswith("x")))):
                raise SystemExit(f"VGRdL {blatt}: {ags} hat NUTS {z[1]}, regionen.csv {nuts}")
            for j, v in zip(kopf[8:], z[8:]):
                if isinstance(j, int) and j >= SEIT and isinstance(v, (int, float)):
                    r[(nuts, str(j))] = round(float(v), stellen) if stellen is not None else float(v)
        werte[sid] = r
    return werte, stand


def jsonstat_zeilen(d):
    """JSON-stat 2.0 (Eurostat) -> [(geo, zeit, wert)] ohne fehlende Werte."""
    ids, groesse = d["id"], d["size"]
    kat = {i: {pos: code for code, pos in d["dimension"][i]["category"]["index"].items()} for i in ids}
    aus = []
    for flach, wert in d.get("value", {}).items():
        if wert is None:
            continue
        rest, pos = int(flach), {}
        for i, n in zip(reversed(ids), reversed(groesse)):
            pos[i] = rest % n
            rest //= n
        aus.append((kat["geo"][pos["geo"]], kat["time"][pos["time"]], float(wert)))
    return sorted(aus)


def eurostat_url(datensatz, filt):
    q = [("geoLevel", "nuts3")] + list(filt.items()) + [("sinceTimePeriod", str(SEIT)), ("format", "JSON"), ("lang", "EN")]
    return EUROSTAT_API + datensatz + "?" + urllib.parse.urlencode(q)


def lies_regionen(pfad=None):
    pfad = Path(pfad or AUS / "regionen.csv")
    if not pfad.exists():
        return []
    with open(pfad, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def zuordnung_aus_lau(xlsx, labels, namen_ags):
    """LAU-NUTS-Korrespondenz (Blatt DE) -> Zeilen für regionen.csv. Jeder Kreis (erste fünf Stellen des Gemeindeschlüssels)
    muss genau einer NUTS-3-Region angehören; sonst Abbruch. Gebiete ohne Kreis (DEXXX, gemeindefreies Küstengewässer) entfallen."""
    import openpyxl
    ws = openpyxl.load_workbook(xlsx, read_only=True)["DE"]
    m = {}
    for z in list(ws.iter_rows(values_only=True))[1:]:
        if z[0] and z[1] and not str(z[0]).endswith("XXX"):
            m.setdefault(str(z[1])[:5], set()).add(str(z[0]))
    mehrdeutig = {a: n for a, n in m.items() if len(n) > 1}
    if mehrdeutig:
        raise SystemExit(f"Kreise in mehreren NUTS-3-Regionen: {sorted(mehrdeutig)[:5]}")
    return [{"nuts3": next(iter(n)), "ags": a, "name": namen_ags.get(a, labels.get(next(iter(n)), a)), "name_eurostat": labels.get(next(iter(n)), ""),
             "land": "DE-" + LAND[a[:2]]} for a, n in sorted(m.items())]


def ableiten(werte):
    """werte: {serie: {(geo, zeit): wert}} -> {serie: {(geo, zeit): wert}} der abgeleiteten Reihen (nur aus Werten derselben Region
    und desselben Jahres)."""
    aus = {}
    schluessel = set().union(*(set(v) for v in werte.values())) if werte else set()
    for sid, *_, formel, _h in ABGELEITET:
        r = {}
        for k in schluessel:
            try:
                v = formel({s: werte[s].get(k) for s in werte})
            except (ZeroDivisionError, TypeError):
                v = None
            if v is not None:
                r[k] = round(v, 3)
        aus[sid] = r
    return aus


def abgleich(vg, eu):
    """[(nuts3, jahr, vgrdl, eurostat, abweichung %)] für Abweichungen über 1 %, sortiert nach Größe."""
    z = [(g, t, v, eu[(g, t)], round((eu[(g, t)] / v - 1) * 100, 2)) for (g, t), v in vg.items() if (g, t) in eu and v]
    return sorted((x for x in z if abs(x[4]) > 1), key=lambda x: -abs(x[4]))


def zahl(v):
    return ("%.3f" % v).rstrip("0").rstrip(".")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vgrdl", help="VGRdL-Excel lokal statt Download")
    ap.add_argument("--zuordnung", help="LAU-NUTS-Korrespondenz (xlsx) -> regionen.csv neu schreiben")
    a = ap.parse_args(argv)
    heute = date.today().isoformat()
    roh, labels = {}, {}
    eu = {}
    for sid, *_r, ds, filt, _h in EUROSTAT + [("_abgleich", None, None, None, None) + ABGLEICH + ("",)]:
        url, datei = eurostat_url(ds, filt), f"eurostat_{sid.strip('_')}.json.gz"
        try:
            b = holen(url)
            roh[datei] = gzip.compress(b, 9, mtime=0)
        except (SystemExit, OSError) as e:
            # Eurostat gedrosselt oder nicht erreichbar: letzter gültiger Stand aus rohdaten/ (Audit: Stand bei Fehlern erhalten);
            # gibt es keinen, fehlen die Eurostat-Teile (KKS-Index, Abgleich) bis zum nächsten Abruf, die VGRdL-Reihen kommen trotzdem
            if not (AUS / "rohdaten" / datei).exists():
                print(f"  Eurostat nicht erreichbar ({e}); {sid} ohne Stand, wird übersprungen")
                continue
            print(f"  Eurostat nicht erreichbar ({e}); {sid} aus rohdaten/{datei}")
            b = gzip.decompress((AUS / "rohdaten" / datei).read_bytes())
        d = json.loads(b)
        labels.update(d["dimension"]["geo"]["category"].get("label", {}))
        eu[sid] = ({(g, t): v for g, t, v in jsonstat_zeilen(d) if g.startswith("DE") and not g.endswith("XXX")}, url, (d.get("updated") or "")[:10])
    if a.zuordnung:
        g = json.loads((HIER.parents[1] / "app/geo/kreise_de.geojson").read_text())
        reg = zuordnung_aus_lau(a.zuordnung, labels, {f["properties"]["id"]: f["properties"]["name"] for f in g["features"]})
    else:
        reg = lies_regionen()
    if len(reg) != 400:
        raise SystemExit(f"regionen.csv: {len(reg)} statt 400 Kreise")
    ags_nuts = {r["ags"]: r["nuts3"] for r in reg}
    if a.vgrdl:
        xlsx_url, xlsx = Path(a.vgrdl).name, Path(a.vgrdl).read_bytes()
    else:
        xlsx_url = vgrdl_url(holen(VGRDL_SEITE).decode("utf-8", "replace"))
        xlsx = holen(xlsx_url)
    tmp = AUS / ".vgrdl.xlsx"
    AUS.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(xlsx)
    try:
        werte, stand = vgrdl_lesen(tmp, ags_nuts)
    finally:
        tmp.unlink()
    xlsx_name = "vgrdl_" + Path(urllib.parse.urlsplit(xlsx_url).path).name.removeprefix("vgrdl_")
    roh[xlsx_name] = xlsx
    for sid, r in werte.items():
        if len({g for g, _ in r}) != 400:
            raise SystemExit(f"{sid}: {len({g for g, _ in r})} statt 400 Kreise")
    meta = []
    for sid, blatt, name, einheit, fmt, art, kern, _s, hinweis in VGRDL:
        meta.append({"serie_id": sid, "thema": "regional", "name": name, "einheit": einheit, "format": fmt, "art": art, "frequenz": "A", "kern": int(kern),
                     "quelle": VGRDL_NAME, "datensatz": "Reihe 2 Band 1, Tabelle " + blatt, "filter": "", "url": xlsx_url, "stand_quelle": stand,
                     "abruf": heute, "hinweis": hinweis})
    for sid, r in ableiten(werte).items():
        d = next(x for x in ABGELEITET if x[0] == sid)
        meta.append({**meta[-1], "serie_id": sid, "name": d[1], "einheit": d[2], "format": d[3], "art": d[4], "kern": 0, "hinweis": d[6],
                     "datensatz": "Reihe 2 Band 1, Tabellen 2.1, 2.3.1, 2.4"})
        werte[sid] = r
    for sid, name, einheit, fmt, art, ds, filt, hinweis in EUROSTAT:
        if sid not in eu:
            continue
        w, url, st = eu[sid]
        w = {(g, t): v for (g, t), v in w.items() if g in set(ags_nuts.values())}
        meta.append({"serie_id": sid, "thema": "regional", "name": name, "einheit": einheit, "format": fmt, "art": art, "frequenz": "A", "kern": 0,
                     "quelle": "Eurostat", "datensatz": ds, "filter": ";".join(f"{k}={v}" for k, v in filt.items()), "url": url, "stand_quelle": st,
                     "abruf": heute, "hinweis": hinweis})
        werte[sid] = w
    erwartet = ",".join(sorted(ags_nuts.values()))
    lang = []
    for m in meta:
        w = werte[m["serie_id"]]
        zeiten = sorted({t for _, t in w})
        m.update(erster_zeitraum=zeiten[0] if zeiten else "", letzter_zeitraum=zeiten[-1] if zeiten else "", anzahl=len(w), ebene="nuts3", erwartet=erwartet)
        lang += [(m["serie_id"], g, t, zahl(v)) for (g, t), v in sorted(w.items())]
    ab = abgleich(werte["r3_bip"], eu["_abgleich"][0]) if "_abgleich" in eu else None
    # alles berechnet: jetzt schreiben
    (AUS / "rohdaten").mkdir(exist_ok=True)
    for alt in (AUS / "rohdaten").glob("vgrdl_*.xlsx"):
        alt.unlink()
    for name, b in roh.items():
        (AUS / "rohdaten" / name).write_bytes(b)
    if a.zuordnung:
        with open(AUS / "regionen.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, ["nuts3", "ags", "name", "name_eurostat", "land"])
            w.writeheader()
            w.writerows(reg)
    with open(AUS / "serien.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, FELDER)
        w.writeheader()
        w.writerows({k: m.get(k, "") for k in FELDER} for m in meta)
    with open(AUS / "zeitreihe_lang.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["serie_id", "geo", "zeit", "wert"])
        w.writerows(lang)
    if ab is not None:
        with open(AUS / "abgleich_eurostat.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["nuts3", "jahr", "bip_vgrdl_mio_eur", "bip_eurostat_mio_eur", "abweichung_pct"])
            w.writerows(ab)
    for m in meta:
        print(f"{m['serie_id']}: {m['anzahl']} Werte, {m['erster_zeitraum']}–{m['letzter_zeitraum']} ({m['quelle']})")
    print(f"{len(meta)} Reihen, {len(lang)} Werte; Abgleich Eurostat: {len(ab) if ab is not None else 'nicht erneuert'} Kreisjahre mit über 1 % Abweichung -> {AUS}")


if __name__ == "__main__":
    sys.exit(main())
