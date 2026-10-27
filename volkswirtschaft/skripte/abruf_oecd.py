"""Ruft Zeitreihen aller OECD-Länder aus der frei zugänglichen OECD-Data-API ab (SDMX-REST, CSV, kein Schlüssel nötig).

Schreibt (über gemeinsam.schreibe, nur die OECD-Reihen) nach volkswirtschaft/:
  serien.csv, zeitreihe_lang.csv   wie beim Eurostat-Abruf; Reihen mit Prognosewerten tragen in `prognose_ab` den ersten Prognosezeitraum
  prognosen_oecd.csv               Projektionen aller Economic-Outlook-Ausgaben 114 bis 119 (Ausgabe, Land, Größe, Jahr) für den Vergleich älterer Prognosen
  rohdaten/oecd/                   unveränderte API-Antworten (CSV, gzip)

Neue Reihe: Eintrag in SERIEN (ein Aufruf von s(...)); `schluessel` ist der SDMX-Schlüssel mit {A} als Platzhalter für die
Länderliste. Aufruf: python3 -I abruf_oecd.py [--ohne-eo-ausgaben]
Hinweis: Die OECD begrenzt Abrufe (etwa 60 pro Stunde); das Skript braucht rund 25 Abrufe.
"""
import csv
import gzip
import io
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import AUS, OECD_ISO3, schreibe  # noqa: E402

API = "https://sdmx.oecd.org/public/rest/data/"
LAENDER = "+".join(OECD_ISO3)  # alle 38 Mitglieder plus EA20, EU27_2020, OECD, G7 (nicht überall vorhanden)
SEIT = {"A": "2000", "Q": "2005-Q1", "M": "2005-01"}
EO = "OECD.ECO.MAD,DSD_EO@DF_EO,"
EO_PROGNOSE_AB = "2026"  # Economic Outlook 119 (Juni 2026): bis 2025 Ist/Schätzung, ab 2026 Projektion


def s(id, thema, name, einheit, fmt, art, freq, flow, schluessel, kern=False, hinweis="", prognose_ab="", wert="OBS_VALUE"):
    return dict(id=id, thema=thema, name=name, einheit=einheit, fmt=fmt, art=art, freq=freq, flow=flow, schluessel=schluessel,
                kern=kern, hinweis=hinweis, prognose_ab=prognose_ab)


def eo(id, name, einheit, fmt, art, mass, hinweis="", thema="prognose", kern=False):
    return s(id, thema, name, einheit, fmt, art, "A", EO, "{A}.%s.A" % mass, kern, hinweis, EO_PROGNOSE_AB)


EOH = "OECD Economic Outlook 119 (Juni 2026); ab 2026 Projektion"
CPIK = "{A}.M.N.CPI.PA.%s.N.GY"
SERIEN = [
    # Quartals- und Monatsreihen für alle Mitglieder
    s("oecd_bip_qoq", "wachstum", "BIP real, ggü. Vorquartal (OECD)", "%", "pct1", "rate", "Q", "OECD.SDD.NAD,DSD_NAMAIN1@DF_QNA,",
      "Q.Y.{A}.S1.S1.B1GQ._Z._Z._Z.PC.L.G1.T0102", True, "preis- und saisonbereinigt; Volkswirtschaftliche Gesamtrechnungen der OECD"),
    s("oecd_bip_yoy", "wachstum", "BIP real, ggü. Vorjahresquartal (OECD)", "%", "pct1", "rate", "Q", "OECD.SDD.NAD,DSD_NAMAIN1@DF_QNA,",
      "Q.Y.{A}.S1.S1.B1GQ._Z._Z._Z.PC.L.GY.T0102", True, "preis- und saisonbereinigt"),
    s("oecd_inflation", "preise", "Inflationsrate, Verbraucherpreise (OECD)", "%", "pct1", "rate", "M", "OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,",
      CPIK % "_T", True, "Verbraucherpreisindex, ggü. Vorjahresmonat; nationale Abgrenzung (CPI)"),
    s("oecd_kerninflation", "preise", "Kerninflation ohne Nahrung und Energie (OECD)", "%", "pct1", "rate", "M", "OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,",
      CPIK % "_TXCP01_NRG", False, "ggü. Vorjahresmonat"),
    s("oecd_arbeitslosenquote", "arbeit", "Arbeitslosenquote, 15 Jahre und älter (OECD)", "%", "pct1", "rate", "M", "OECD.SDD.TPS,DSD_LFS@DF_IALFS_UNE_M,",
      "{A}.UNE_LF_M.PT_LF_SUB._Z.Y._T.Y_GE15._Z.M", True, "saisonbereinigt, in % der Erwerbspersonen; Arbeitskräfteerhebungen"),
    s("oecd_jugendarbeitslosigkeit", "arbeit", "Jugendarbeitslosenquote, 15–24 Jahre (OECD)", "%", "pct1", "rate", "M", "OECD.SDD.TPS,DSD_LFS@DF_IALFS_UNE_M,",
      "{A}.UNE_LF_M.PT_LF_SUB._Z.Y._T.Y15T24._Z.M", False, "saisonbereinigt"),
    s("oecd_fruehindikator", "nachfrage", "Frühindikator CLI (OECD)", "Index (Langfristmittel 100)", "zahl1", "index", "M", "OECD.SDD.STES,DSD_STES@DF_CLI,",
      "{A}.M.LI.IX._Z.AA.IX._Z.H", False, "Composite Leading Indicator, amplitudenbereinigt; Werte über 100 = Expansion"),
    s("oecd_unternehmensvertrauen", "nachfrage", "Geschäftsklima (OECD, BCI)", "Index (Langfristmittel 100)", "zahl1", "index", "M", "OECD.SDD.STES,DSD_STES@DF_CLI,",
      "{A}.M.BCICP.IX._Z.AA.IX._Z.H", True, "Business Confidence Indicator, amplitudenbereinigt; für Deutschland aus dem ifo-Konjunkturtest"),
    s("oecd_verbrauchervertrauen", "nachfrage", "Verbrauchervertrauen (OECD, CCI)", "Index (Langfristmittel 100)", "zahl1", "index", "M", "OECD.SDD.STES,DSD_STES@DF_CLI,",
      "{A}.M.CCICP.IX._Z.AA.IX._Z.H", False, "Consumer Confidence Indicator, amplitudenbereinigt"),
    # Jahreswerte und Projektionen aus dem Economic Outlook
    eo("oecd_eo_bip", "BIP real, Wachstum (OECD-Projektion)", "%", "pct1", "rate", "GDPV_ANNPCT", EOH, kern=True),
    eo("oecd_eo_inflation", "Inflationsrate, Verbraucherpreise (OECD-Projektion)", "%", "pct1", "rate", "CPI_YTYPCT", EOH),
    eo("oecd_eo_inflation_hvpi", "Inflationsrate, HVPI (OECD-Projektion)", "%", "pct1", "rate", "CPIH_YTYPCT", EOH + "; Harmonisierter Verbraucherpreisindex (Euroraum-Länder, Deutschland)"),
    eo("oecd_eo_kerninflation", "Kerninflation (OECD-Projektion)", "%", "pct1", "rate", "PCORE_YTYPCT", EOH),
    eo("oecd_eo_arbeitslosenquote", "Arbeitslosenquote (OECD-Projektion)", "%", "pct1", "rate", "UNR", EOH),
    eo("oecd_eo_finanzierungssaldo", "Finanzierungssaldo des Staates (OECD-Projektion)", "% des BIP", "pct1", "rate", "NLGQ", EOH),
    eo("oecd_eo_primaersaldo", "Primärsaldo des Staates (OECD-Projektion)", "% des BIP", "pct1", "rate", "NLGXQ", EOH),
    eo("oecd_eo_schuldenquote", "Bruttoverschuldung des Staates (OECD-Projektion)", "% des BIP", "pct1", "rate", "GGFLQ", EOH + "; Bruttofinanzverbindlichkeiten (SNA-Abgrenzung)"),
    eo("oecd_eo_leistungsbilanz", "Leistungsbilanzsaldo (OECD-Projektion)", "% des BIP", "pct1", "rate", "CBGDPR", EOH),
    eo("oecd_eo_investitionen", "Bruttoanlageinvestitionen real, Wachstum (OECD-Projektion)", "%", "pct1", "rate", "ITV_ANNPCT", EOH),
    eo("oecd_eo_konsum", "Privater Konsum real, Wachstum (OECD-Projektion)", "%", "pct1", "rate", "CPV_ANNPCT", EOH),
    eo("oecd_eo_deflator", "BIP-Deflator, Wachstum (OECD-Projektion)", "%", "pct1", "rate", "PGDP_ANNPCT", EOH),
    eo("oecd_eo_potenzial", "Produktionspotenzial, Wachstum (OECD-Projektion)", "%", "pct1", "rate", "GDPVTR_ANNPCT", EOH),
    eo("oecd_eo_langfristzins", "Rendite zehnjähriger Staatsanleihen (OECD-Projektion)", "%", "pct2", "rate", "IRL", EOH),
    eo("oecd_eo_kurzfristzins", "Kurzfristiger Zins (OECD-Projektion)", "%", "pct2", "rate", "IRS", EOH),
    eo("oecd_eo_sparquote", "Sparquote der privaten Haushalte, netto (OECD-Projektion)", "% des verfügbaren Einkommens", "pct1", "rate", "SRATIO", EOH),
    eo("oecd_eo_produktivitaet", "Arbeitsproduktivität, Gesamtwirtschaft (OECD-Projektion)", "Index", "zahl1", "index", "PDTY", EOH),
    eo("oecd_eo_lohnstueckkosten", "Lohnstückkosten, Gesamtwirtschaft (OECD-Projektion)", "Index", "zahl1", "index", "ULC", EOH),
    eo("oecd_eo_bip_je_einwohner", "BIP je Einwohner, real (OECD-Projektion)", "USD, KKP", "zahl0", "niveau", "GDPVD_CAP", EOH + "; konstante Preise und Kaufkraftparitäten"),
]


def hole(flow, schluessel, seit, name):
    """Ein Abruf der OECD-API als CSV; Rückgabe (url, Rohtext). Zwei Wiederholungen bei Netzwerkfehlern, 429 wartet länger."""
    url = f"{API}{flow}/{schluessel}?startPeriod={seit}"
    for versuch in range(4):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/vnd.sdmx.data+csv; charset=utf-8", "User-Agent": "Mozilla/5.0 (Unternehmenskennzahlen-Abruf)"})
            return url, urllib.request.urlopen(req, timeout=180).read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(60 * (versuch + 1))
                continue
            raise
        except OSError:
            time.sleep(5 * (versuch + 1))
    raise RuntimeError("Abruf gescheitert: " + url)


def lese(roh):
    return [r for r in csv.DictReader(io.StringIO(roh)) if r.get("OBS_VALUE") not in (None, "")]


def reihen(sp):
    schluessel = sp["schluessel"].replace("{A}", LAENDER)
    url, roh = hole(sp["flow"], schluessel, SEIT[sp["freq"]], sp["id"])
    zeilen = []
    for r in lese(roh):
        geo = OECD_ISO3.get(r["REF_AREA"])
        if geo:
            zeilen.append((geo, r["TIME_PERIOD"], float(r["OBS_VALUE"])))
    # Die Quelle liefert vereinzelt doppelte Zeilen (verschiedene Revisionsstände): je (Land, Zeit) gilt der zuletzt gelieferte Wert.
    return url, roh, sorted(dict(((g, t), (g, t, w)) for g, t, w in zeilen).values())


# Ausgaben des Economic Outlook: (Name, Datenfluss, Veröffentlichung). Neue Ausgabe = eine Zeile oben einfügen.
EO_AUSGABEN = [
    ("Economic Outlook 119", EO, "2026-06-03"),
    ("Economic Outlook 118", "OECD.ECO.MAD,DSD_EO_118@DF_EO_118,", "2025-12-02"),
    ("Economic Outlook 117", "OECD.ECO.MAD,DSD_EO_117@DF_EO_117,", "2025-06-03"),
    ("Economic Outlook 116", "OECD.ECO.MAD,DSD_EO_116@DF_EO_116,", "2024-12-04"),
    ("Economic Outlook 115", "OECD.ECO.MAD,DSD_EO_115@DF_EO_115,", "2024-05-02"),
    ("Economic Outlook 114", "OECD.ECO.MAD,DSD_EO_114@DF_EO_114,", "2023-11-29"),
]
EO_GROESSEN = {"GDPV_ANNPCT": ("bip_wachstum", "%"), "CPI_YTYPCT": ("inflation_vpi", "%"), "CPIH_YTYPCT": ("inflation_hvpi", "%"),
               "UNR": ("arbeitslosenquote", "%"), "NLGQ": ("finanzierungssaldo", "% des BIP")}


def eo_ausgaben():
    """Alle Ausgaben des Economic Outlook für BIP, Inflation, Arbeitslosenquote und Finanzierungssaldo -> prognosen_oecd.csv."""
    heute, zeilen = date.today().isoformat(), []
    for name, flow, datum in EO_AUSGABEN:
        try:
            url, roh = hole(flow, "%s.%s.A" % (LAENDER, "+".join(EO_GROESSEN)), "2022", name)
            url = API + flow.strip(",")  # Quelle des Datenflusses; der volle Schlüssel steht in EO_GROESSEN
        except Exception as e:
            print(f"  FEHLER {name}: {e}")
            continue
        n = 0
        for r in lese(roh):
            geo, g = OECD_ISO3.get(r["REF_AREA"]), EO_GROESSEN.get(r["MEASURE"])
            if geo and g:
                zeilen.append((geo, "OECD", name, datum, g[0], r["TIME_PERIOD"], round(float(r["OBS_VALUE"]), 3), g[1], "OECD-API", url, heute))
                n += 1
        print(f"{name}: {n} Werte")
        time.sleep(2)
    with open(AUS / "prognosen_oecd.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["geo", "herausgeber", "ausgabe", "veroeffentlicht", "groesse", "jahr", "wert", "einheit", "beleg", "url", "abruf"])
        w.writerows(sorted(zeilen))


def main():
    (AUS / "rohdaten/oecd").mkdir(parents=True, exist_ok=True)
    lang, meta, heute = [], [], date.today().isoformat()
    for sp in SERIEN:
        try:
            url, roh, zeilen = reihen(sp)
        except Exception as e:  # eine fehlende Serie darf den Abruf nicht stoppen
            print(f"  FEHLER {sp['id']}: {e}")
            continue
        if not zeilen:
            print(f"  LEER {sp['id']}")
            continue
        (AUS / f"rohdaten/oecd/{sp['id']}.csv.gz").write_bytes(gzip.compress(roh.encode("utf-8"), 9, mtime=0))
        lang += [(sp["id"], g, t, w) for g, t, w in zeilen]
        meta.append({"serie_id": sp["id"], "thema": sp["thema"], "name": sp["name"], "einheit": sp["einheit"], "format": sp["fmt"],
                     "art": sp["art"], "frequenz": sp["freq"], "kern": int(sp["kern"]), "quelle": "OECD", "datensatz": sp["flow"].strip(",").split(",")[-1],
                     "filter": sp["schluessel"].replace("{A}", "Länder"), "url": url, "stand_quelle": heute, "abruf": heute,
                     "erster_zeitraum": min(t for _, t, _ in zeilen), "letzter_zeitraum": max(t for _, t, _ in zeilen),
                     "anzahl": len(zeilen), "prognose_ab": sp["prognose_ab"], "hinweis": sp["hinweis"]})
        print(f"{sp['id']}: {len(zeilen)} Werte, {len({g for g, _, _ in zeilen})} Länder, bis {meta[-1]['letzter_zeitraum']}")
        time.sleep(2)
    schreibe("OECD", meta, lang)
    print(f"{len(meta)} Serien, {len(lang)} Werte")
    if "--ohne-eo-ausgaben" not in sys.argv:
        eo_ausgaben()


if __name__ == "__main__":
    main()
