"""Gesamtregister für das Terminal: alle Zeilen der Unternehmenstabelle (unternehmen-tabelle/Unternehmen_Tabelle.csv) als kompakte,
spaltenweise Tabelle -> data/register.json. Nur Stammdaten (Name, Land, Sitz, Branche, ISIN, Ticker, Börse, Notierung, Index, LEI, Website,
Quelle); Kennzahlen kommen weiter aus unternehmen.py. Zeilen mit ID tragen sie mit und verweisen im Terminal auf das Profil mit Kennzahlen.
Zeilen ohne ID bleiben ohne ID (Neuvergabe nur über stammdaten/ids.py); sie werden über einen stabilen Schlüssel angesprochen
(ISIN, sonst LEI, sonst Land+Name, wie international/import_unternehmen.py), im Terminal als #reg-<Schlüssel>."""
import csv
import hashlib
import json
import re
from pathlib import Path

HIER = Path(__file__).resolve().parent
TABELLE = HIER.parent / "unternehmen-tabelle/Unternehmen_Tabelle.csv"
GEO = HIER / "geo/laender.geojson"

# Namen der Tabelle, die nicht wörtlich in Natural Earth (name_en) stehen
LAND_EXTRA = {"usa": "US", "uk": "GB", "south korea": "KR", "czechia": "CZ", "turkey": "TR", "hong kong": "HK", "taiwan": "TW",
              "russia": "RU", "vietnam": "VN", "iran": "IR", "united arab emirates": "AE", "sonstige": "ZZ"}
BRANCHEN = {"banken": "Banken", "versicherungen": "Versicherungen", "finanzdienstleister": "Finanzdienstleister", "immobilien": "Immobilien",
            "industrie": "Industrie", "automobil": "Automobil", "technologie": "Technologie", "software-it": "Software & IT",
            "telekom-medien": "Telekom & Medien", "pharma-gesundheit": "Pharma & Gesundheit", "chemie-rohstoffe": "Chemie & Rohstoffe",
            "energie": "Energie", "energie-versorger": "Energie & Versorger", "handel-konsum": "Handel & Konsum",
            "transport-logistik": "Transport & Logistik", "sonstige": "Sonstige / nicht zugeordnet"}
SPALTEN = ["k", "id", "name", "land", "sitz", "br", "isin", "ticker", "boerse", "n", "bank", "index", "lei", "web", "quelle", "form", "hinweis"]


def land_codes():
    m = {}
    for f in json.load(open(GEO, encoding="utf-8"))["features"]:
        p = f["properties"]
        for k in ("name_en", "name"):
            if p.get(k):
                m.setdefault(p[k].lower(), p["iso"])
    m.update(LAND_EXTRA)
    return m


def schluessel(z):
    """Stabiler Zeilenschlüssel wie row_key der SQL-Tabelle (ISIN, sonst LEI, sonst Land+Name), als kurzer Hash für die Adresszeile."""
    roh = z["ISIN"].strip().upper() or z["LEI"].strip().upper() or (z["Land *"].strip().lower() + "|" + re.sub(r"\s+", " ", z["Name *"].strip().lower()))
    return hashlib.sha1(roh.encode()).hexdigest()[:8]


def lade(pfad=TABELLE):
    codes = land_codes()
    zeilen, sicht, unbekannt = [], {}, {}
    for z in csv.DictReader(open(pfad, encoding="utf-8-sig"), delimiter=";"):
        k = schluessel(z)
        n = sicht.get(k, 0)
        sicht[k] = n + 1
        if n:                       # gleicher Schlüssel (z. B. Aktiengattungen mit gleicher ISIN): Zähler anhängen
            k = f"{k}{n}"
        land = z["Land *"].strip()
        code = codes.get(land.lower())
        if code is None:
            unbekannt[land] = unbekannt.get(land, 0) + 1
            code = "ZZ"
        hinweis = z["Beschreibung"].strip()
        zeilen.append([k, z["unternehmen_id"], z["Name *"].strip(), code, z["Sitz"].strip(), z["Branche *"].strip(), z["ISIN"].strip(),
                       z["Ticker"].strip(), z["Börse"].strip(), 1 if z["Börsennotiert *"].strip().lower() == "ja" else 0,
                       1 if z["Bank *"].strip().lower() == "ja" else 0, z["Index-Zugehörigkeit"].strip(), z["LEI"].strip(), z["Website"].strip(),
                       z["Quelle Stammdaten (URL) *"].strip(), z["Rechtsform"].strip(), hinweis])
    return {"spalten": SPALTEN, "branchen": BRANCHEN, "laender_namen": {}, "zeilen": zeilen}, unbekannt


if __name__ == "__main__":
    d, u = lade()
    s = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
    (HIER / "data/register.json").write_text(s)
    print(len(d["zeilen"]), "Zeilen,", len(s) // 1000, "kB; Länder ohne Code:", u)
