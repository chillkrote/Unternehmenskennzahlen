"""Gemeinsame Bausteine der Abrufskripte (Eurostat, OECD, ...): Länderliste und Schreiben der Ergebnisdateien.

Jedes Abrufskript besitzt seine Reihen (Spalte `quelle` in serien.csv). `schreibe()` ersetzt nur die Reihen der eigenen Quelle
und lässt alle anderen unverändert, damit die Skripte einzeln und in beliebiger Reihenfolge laufen können."""
import csv
from pathlib import Path

AUS = Path(__file__).resolve().parents[1]
FELDER = ["serie_id", "thema", "name", "einheit", "format", "art", "frequenz", "kern", "quelle", "datensatz", "filter", "url",
          "stand_quelle", "abruf", "erster_zeitraum", "letzter_zeitraum", "anzahl", "prognose_ab", "hinweis"]

# geo -> (Name, OECD-Mitglied). Schlüssel sind ISO-2-Codes (Eurostat-Schreibweise: Griechenland GR, Vereinigtes Königreich UK).
LAENDER = {
    "DE": ("Deutschland", 1), "EA20": ("Euroraum", 0), "EU27_2020": ("EU-27", 0), "OECD": ("OECD gesamt", 0), "G7": ("G7", 0),
    "AU": ("Australien", 1), "AT": ("Österreich", 1), "BE": ("Belgien", 1), "CA": ("Kanada", 1), "CL": ("Chile", 1),
    "CO": ("Kolumbien", 1), "CR": ("Costa Rica", 1), "CZ": ("Tschechien", 1), "DK": ("Dänemark", 1), "EE": ("Estland", 1),
    "FI": ("Finnland", 1), "FR": ("Frankreich", 1), "EL": ("Griechenland", 1), "HU": ("Ungarn", 1), "IS": ("Island", 1),
    "IE": ("Irland", 1), "IL": ("Israel", 1), "IT": ("Italien", 1), "JP": ("Japan", 1), "KR": ("Südkorea", 1),
    "LV": ("Lettland", 1), "LT": ("Litauen", 1), "LU": ("Luxemburg", 1), "MX": ("Mexiko", 1), "NL": ("Niederlande", 1),
    "NZ": ("Neuseeland", 1), "NO": ("Norwegen", 1), "PL": ("Polen", 1), "PT": ("Portugal", 1), "SK": ("Slowakei", 1),
    "SI": ("Slowenien", 1), "ES": ("Spanien", 1), "SE": ("Schweden", 1), "CH": ("Schweiz", 1), "TR": ("Türkei", 1),
    "UK": ("Vereinigtes Königreich", 1), "US": ("USA", 1),
}
OECD_ISO3 = {  # OECD-Ländercode -> geo
    "DEU": "DE", "EA20": "EA20", "EU27_2020": "EU27_2020", "OECD": "OECD", "G7": "G7", "AUS": "AU", "AUT": "AT", "BEL": "BE",
    "CAN": "CA", "CHL": "CL", "COL": "CO", "CRI": "CR", "CZE": "CZ", "DNK": "DK", "EST": "EE", "FIN": "FI", "FRA": "FR",
    "GRC": "EL", "HUN": "HU", "ISL": "IS", "IRL": "IE", "ISR": "IL", "ITA": "IT", "JPN": "JP", "KOR": "KR", "LVA": "LV",
    "LTU": "LT", "LUX": "LU", "MEX": "MX", "NLD": "NL", "NZL": "NZ", "NOR": "NO", "POL": "PL", "PRT": "PT", "SVK": "SK",
    "SVN": "SI", "ESP": "ES", "SWE": "SE", "CHE": "CH", "TUR": "TR", "GBR": "UK", "USA": "US",
}
THEMEN = {"wachstum": "Wachstum & Nachfrage", "preise": "Preise & Inflation", "arbeit": "Arbeit & Löhne",
          "nachfrage": "Produktion & Stimmung", "finanzen": "Zinsen & Staatsfinanzen", "prognose": "OECD-Projektionen (jährlich)"}


def lies(name):
    p = AUS / name
    if not p.exists():
        return []
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def schreibe(quelle, meta, lang):
    """meta: Zeilen für serien.csv (dicts), lang: (serie_id, geo, zeit, wert)-Tupel. Ersetzt alle Reihen dieser Quelle."""
    alt = lies("serien.csv")
    fremd = {r["serie_id"] for r in alt if r["quelle"] != quelle}
    serien = [r for r in alt if r["quelle"] != quelle] + [{k: m.get(k, "") for k in FELDER} for m in meta]
    reihen = [r for r in lies("zeitreihe_lang.csv") if r["serie_id"] in fremd]
    with open(AUS / "serien.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, FELDER)
        w.writeheader()
        w.writerows({k: r.get(k, "") for k in FELDER} for r in serien)
    with open(AUS / "zeitreihe_lang.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["serie_id", "geo", "zeit", "wert"])
        w.writerows((r["serie_id"], r["geo"], r["zeit"], r["wert"]) for r in reihen)
        w.writerows(lang)
    with open(AUS / "laender.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["geo", "name", "oecd"])
        w.writerows((g, n, o) for g, (n, o) in LAENDER.items())
    with open(AUS / "themen.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["thema", "name"])
        w.writerows(THEMEN.items())
