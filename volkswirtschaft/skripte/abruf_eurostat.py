"""Ruft volkswirtschaftliche Zeitreihen aus der frei zugänglichen Eurostat-API ab (JSON-stat, kein Schlüssel nötig).

Schreibt in volkswirtschaft/:
  serien.csv            eine Zeile je Serie (Name, Einheit, Datensatz, Filter, Stand der Quelle, Abrufdatum)
  zeitreihe_lang.csv    serie_id, geo, zeit, wert   (zeit: 2025-Q3 | 2025-09 | 2025)
  rohdaten/eurostat/    unveränderte API-Antworten als .json.gz (Beleg)

Neue Kennzahl: Eintrag in SERIEN ergänzen und das Skript neu laufen lassen; das Terminal liest die CSV ohne Codeänderung.
Aufruf: python3 -I abruf_eurostat.py
"""
import csv
import gzip
import json
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

AUS = Path(__file__).resolve().parents[1]
API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
SEIT = {"M": "2005-01", "Q": "2005-Q1", "A": "1995"}
LAENDER = ["DE", "EA20", "EU27_2020", "FR", "IT", "ES", "NL", "AT"]
GEO_NAMEN = {"DE": "Deutschland", "EA20": "Euroraum", "EU27_2020": "EU-27", "FR": "Frankreich", "IT": "Italien",
             "ES": "Spanien", "NL": "Niederlande", "AT": "Österreich"}


def s(id, thema, name, einheit, fmt, art, freq, dataset, filt, kern=False, hinweis="", geo_map=None, laender=None):
    return dict(id=id, thema=thema, name=name, einheit=einheit, fmt=fmt, art=art, freq=freq, dataset=dataset, filter=filt,
                kern=kern, hinweis=hinweis, geo_map=geo_map or {}, laender=laender or LAENDER)


BIP = dict(s_adj="SCA", na_item="B1GQ")
SERIEN = [
    # Wachstum und Nachfrage
    s("bip_qoq", "wachstum", "BIP real, ggü. Vorquartal", "%", "pct1", "rate", "Q", "namq_10_gdp", dict(unit="CLV_PCH_PRE", **BIP), True, "preis-, saison- und kalenderbereinigt"),
    s("bip_yoy", "wachstum", "BIP real, ggü. Vorjahresquartal", "%", "pct1", "rate", "Q", "namq_10_gdp", dict(unit="CLV_PCH_SM", **BIP), True, "preis-, saison- und kalenderbereinigt"),
    s("bip_niveau", "wachstum", "BIP real (verkettet, 2010)", "Mio. €", "zahl0", "niveau", "Q", "namq_10_gdp", dict(unit="CLV10_MEUR", **BIP), False, "preis-, saison- und kalenderbereinigt"),
    s("konsum_privat", "wachstum", "Privater Konsum real, ggü. Vorquartal", "%", "pct1", "rate", "Q", "namq_10_gdp", dict(unit="CLV_PCH_PRE", s_adj="SCA", na_item="P31_S14_S15")),
    s("konsum_staat", "wachstum", "Staatskonsum real, ggü. Vorquartal", "%", "pct1", "rate", "Q", "namq_10_gdp", dict(unit="CLV_PCH_PRE", s_adj="SCA", na_item="P3_S13")),
    s("investitionen", "wachstum", "Bruttoanlageinvestitionen real, ggü. Vorquartal", "%", "pct1", "rate", "Q", "namq_10_gdp", dict(unit="CLV_PCH_PRE", s_adj="SCA", na_item="P51G")),
    s("exporte", "wachstum", "Exporte real, ggü. Vorquartal", "%", "pct1", "rate", "Q", "namq_10_gdp", dict(unit="CLV_PCH_PRE", s_adj="SCA", na_item="P6")),
    s("importe", "wachstum", "Importe real, ggü. Vorquartal", "%", "pct1", "rate", "Q", "namq_10_gdp", dict(unit="CLV_PCH_PRE", s_adj="SCA", na_item="P7")),
    # Preise
    s("hicp_gesamt", "preise", "Inflationsrate (HVPI)", "%", "pct1", "rate", "M", "prc_hicp_minr", dict(unit="RCH_A", coicop18="TOTAL"), True, "Harmonisierter Verbraucherpreisindex, ggü. Vorjahresmonat"),
    s("hicp_kern", "preise", "Kerninflation (ohne Energie, Nahrung, Alkohol, Tabak)", "%", "pct1", "rate", "M", "prc_hicp_minr", dict(unit="RCH_A", coicop18="TOT_X_NRG_FOOD"), True, "ggü. Vorjahresmonat"),
    s("hicp_energie", "preise", "Inflation Energie", "%", "pct1", "rate", "M", "prc_hicp_minr", dict(unit="RCH_A", coicop18="NRG"), False, "ggü. Vorjahresmonat"),
    s("hicp_nahrung", "preise", "Inflation Nahrungsmittel, Alkohol, Tabak", "%", "pct1", "rate", "M", "prc_hicp_minr", dict(unit="RCH_A", coicop18="FOOD"), False, "ggü. Vorjahresmonat"),
    s("hicp_dienste", "preise", "Inflation Dienstleistungen", "%", "pct1", "rate", "M", "prc_hicp_minr", dict(unit="RCH_A", coicop18="SERV"), False, "ggü. Vorjahresmonat"),
    s("hicp_industrie", "preise", "Inflation Industriegüter ohne Energie", "%", "pct1", "rate", "M", "prc_hicp_minr", dict(unit="RCH_A", coicop18="IGD_NNRG"), False, "ggü. Vorjahresmonat"),
    s("erzeugerpreise", "preise", "Erzeugerpreise Industrie, ggü. Vorjahresmonat", "%", "pct1", "rate", "M", "sts_inpp_m", dict(nace_r2="B-E36", indic_bt="PRC_PRR", s_adj="NSA", unit="PCH_SM"), False, "Industrie ohne Bau, Inlandsabsatz plus Export"),
    # Arbeit und Löhne
    s("arbeitslosenquote", "arbeit", "Arbeitslosenquote (ILO)", "%", "pct1", "rate", "M", "une_rt_m", dict(s_adj="SA", age="TOTAL", unit="PC_ACT", sex="T"), True, "saisonbereinigt, in % der Erwerbspersonen; Euroraum = EA21", {"EA20": "EA21"}),
    s("arbeitskosten", "arbeit", "Arbeitskosten je Stunde, ggü. Vorjahresquartal", "%", "pct1", "rate", "Q", "lc_lci_r2_q", dict(nace_r2="B-S", lcstruct="D1_D4_MD5", unit="PCH_SM", s_adj="NSA"), True, "Löhne und Gehälter plus Sozialbeiträge, gewerbliche Wirtschaft"),
    s("erwerbstaetige", "arbeit", "Erwerbstätige (Inland)", "Tsd.", "zahl0", "niveau", "Q", "namq_10_pe", dict(unit="THS_PER", s_adj="SCA", na_item="EMP_DC"), False, "saison- und kalenderbereinigt"),
    # Nachfrage, Produktion und Stimmung
    s("einzelhandel", "nachfrage", "Einzelhandelsumsatz (Volumen)", "Index 2021 = 100", "zahl1", "index", "M", "sts_trtu_m", dict(nace_r2="G47", indic_bt="VOL_SLS", s_adj="SCA", unit="I21"), True, "preis-, saison- und kalenderbereinigt"),
    s("produktion", "nachfrage", "Produktion im produzierenden Gewerbe", "Index 2021 = 100", "zahl1", "index", "M", "sts_inpr_m", dict(nace_r2="B-D", indic_bt="PRD", s_adj="SCA", unit="I21"), True, "ohne Bau; saison- und kalenderbereinigt"),
    s("bau", "nachfrage", "Produktion im Bauhauptgewerbe", "Index 2021 = 100", "zahl1", "index", "M", "sts_copr_m", dict(nace_r2="F", indic_bt="PRD", s_adj="SCA", unit="I21"), False, "saison- und kalenderbereinigt"),
    s("wirtschaftsstimmung", "nachfrage", "Wirtschaftsstimmung (ESI)", "Index (Langfristmittel 100)", "zahl1", "index", "M", "ei_bssi_m_r2", dict(indic="BS-ESI-I", s_adj="SA"), True, "Economic Sentiment Indicator der EU-Kommission"),
    s("verbrauchervertrauen", "nachfrage", "Verbrauchervertrauen", "Saldo", "zahl1", "saldo", "M", "ei_bsco_m", dict(indic="BS-CSMCI", s_adj="SA", unit="BAL"), False, "Saldo der Umfrageantworten, saisonbereinigt"),
    s("industrievertrauen", "nachfrage", "Industrievertrauen", "Saldo", "zahl1", "saldo", "M", "ei_bsin_m_r2", dict(indic="BS-ICI", s_adj="SA", unit="BAL"), False, "Saldo der Umfrageantworten, saisonbereinigt"),
    # Zinsen und Staatsfinanzen
    s("euribor_3m", "finanzen", "Zinssatz Dreimonatsgeld (EURIBOR)", "%", "pct2", "rate", "M", "irt_st_m", dict(int_rt="IRT_M3"), True, "Monatsdurchschnitt, nur Euroraum", {"EA20": "EA"}, ["EA20"]),
    s("schuldenquote", "finanzen", "Staatsschuldenquote (Maastricht)", "% des BIP", "pct1", "rate", "A", "gov_10dd_edpt1", dict(unit="PC_GDP", sector="S13", na_item="GD"), False, "Bruttoschuld des Staates"),
    s("defizitquote", "finanzen", "Finanzierungssaldo des Staates", "% des BIP", "pct1", "rate", "A", "gov_10dd_edpt1", dict(unit="PC_GDP", sector="S13", na_item="B9"), False, "negativ = Defizit"),
]
THEMEN = {"wachstum": "Wachstum & Nachfrage", "preise": "Preise & Inflation", "arbeit": "Arbeit & Löhne",
          "nachfrage": "Produktion & Stimmung", "finanzen": "Zinsen & Staatsfinanzen"}


def abruf(sp):
    geos = [sp["geo_map"].get(g, g) for g in sp["laender"]]
    rück = {v: k for k, v in sp["geo_map"].items()}
    q = [("geo", g) for g in geos] + list(sp["filter"].items()) + [("sinceTimePeriod", SEIT[sp["freq"]]), ("format", "JSON"), ("lang", "EN")]
    url = API + sp["dataset"] + "?" + urllib.parse.urlencode(q)
    roh = urllib.request.urlopen(url, timeout=90).read()
    d = json.loads(roh)
    ids, groesse = d["id"], d["size"]
    kat = {i: {pos: code for code, pos in d["dimension"][i]["category"]["index"].items()} for i in ids}
    zeilen = []
    for flach, wert in d["value"].items():
        rest, pos = int(flach), {}
        for i, n in zip(reversed(ids), reversed(groesse)):
            pos[i] = rest % n
            rest //= n
        if wert is None:
            continue
        geo = kat["geo"][pos["geo"]]
        zeilen.append((rück.get(geo, geo), kat["time"][pos["time"]], wert))
    return url, roh, d.get("updated", ""), sorted(zeilen)


def main():
    (AUS / "rohdaten/eurostat").mkdir(parents=True, exist_ok=True)
    lang, meta, heute = [], [], date.today().isoformat()
    for sp in SERIEN:
        try:
            url, roh, stand, zeilen = abruf(sp)
        except Exception as e:  # eine fehlende Serie darf den Abruf nicht stoppen
            print(f"  FEHLER {sp['id']}: {e}")
            continue
        (AUS / f"rohdaten/eurostat/{sp['id']}.json.gz").write_bytes(gzip.compress(roh, 9, mtime=0))
        lang += [(sp["id"], g, t, w) for g, t, w in zeilen]
        meta.append({"serie_id": sp["id"], "thema": sp["thema"], "name": sp["name"], "einheit": sp["einheit"], "format": sp["fmt"],
                     "art": sp["art"], "frequenz": sp["freq"], "kern": int(sp["kern"]), "quelle": "Eurostat", "datensatz": sp["dataset"],
                     "filter": ";".join(f"{k}={v}" for k, v in sp["filter"].items()), "url": url, "stand_quelle": stand[:10], "abruf": heute,
                     "erster_zeitraum": min((t for _, t, _ in zeilen), default=""), "letzter_zeitraum": max((t for _, t, _ in zeilen), default=""),
                     "anzahl": len(zeilen), "hinweis": sp["hinweis"]})
        print(f"{sp['id']}: {len(zeilen)} Werte, bis {meta[-1]['letzter_zeitraum']}")
        time.sleep(0.3)
    with open(AUS / "serien.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(meta[0]))
        w.writeheader()
        w.writerows(meta)
    with open(AUS / "zeitreihe_lang.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["serie_id", "geo", "zeit", "wert"])
        w.writerows(lang)
    with open(AUS / "laender.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["geo", "name"])
        w.writerows(GEO_NAMEN.items())
    with open(AUS / "themen.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["thema", "name"])
        w.writerows(THEMEN.items())
    print(f"{len(meta)} Serien, {len(lang)} Werte")


if __name__ == "__main__":
    main()
