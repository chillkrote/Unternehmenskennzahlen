"""Überführt die Zeitreihen der Bankenerhebung ins lange Format.

Quelle ist die Auswertungs-Excel (Blätter "Zeitreihe 2021-2025" und
"Offenlegung 31.12.2025"). Ergebnis: zeitreihen/zeitreihe_lang.csv und
zeitreihen/stammdaten.csv. Aufruf: python3 -I migriere_banken.py
"""
import csv
import re
import unicodedata
from pathlib import Path

import openpyxl

REPO = Path(__file__).resolve().parents[2]
EXCEL = REPO / "banken/bilanzvergleich-gj2025/auswertung/Bilanzvergleich_Banken_GJ2025.xlsx"
AUS = REPO / "zeitreihen"

# Spaltenpräfix im Blatt -> (kennzahl, einheit)
ZR_KENNZAHLEN = {
    "Bilanzsumme": ("bilanzsumme", "Mio. EUR"),
    "Eigenkapital": ("eigenkapital", "Mio. EUR"),
    "Fonds § 340g": ("fonds_340g", "Mio. EUR"),
    "Jahresüberschuss": ("jahresueberschuss", "Mio. EUR"),
}
# Spaltenüberschrift im Blatt Offenlegung -> (kennzahl, einheit)
OFF_KENNZAHLEN = {
    "Hartes Kernkapital CET1 (Mio. €)": ("cet1", "Mio. EUR"),
    "Kernkapital T1 (Mio. €)": ("t1", "Mio. EUR"),
    "Gesamtrisikobetrag RWA (Mio. €)": ("rwa", "Mio. EUR"),
    "CET1-Quote": ("cet1_quote", "Anteil"),
    "Kernkapitalquote": ("t1_quote", "Anteil"),
    "Gesamtkapitalquote": ("gk_quote", "Anteil"),
    "Verschuldungsquote (Leverage Ratio)": ("leverage_ratio", "Anteil"),
}
FELDER = ["unternehmen_id", "kennzahl", "stichtag", "wert", "einheit", "waehrung",
          "rechnungslegung", "ebene", "quelle", "pruefstatus"]


def slug(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def zahl(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def tabelle(ws):
    zeilen = ws.iter_rows(values_only=True)
    kopf = [str(c).strip() if c is not None else "" for c in next(zeilen)]
    for z in zeilen:
        # Median- und Kopfzeilen der Gruppentabellen unter den Banken überspringen
        if z and isinstance(z[kopf.index("Bank")], str) and z[kopf.index("Gruppe")] != "Gruppe" and "(Median)" not in z[kopf.index("Bank")]:
            yield kopf, z


def main():
    wb = openpyxl.load_workbook(EXCEL, data_only=True)
    lang, stamm = [], {}
    # Bankenreihen 2021-2025, Einzelabschluss HGB (Konzernwerte nur dort, wo die Quelle es vermerkt)
    for kopf, z in tabelle(wb["Zeitreihe 2021-2025"]):
        name = z[kopf.index("Bank")]
        uid = slug(name)
        stamm[uid] = {"unternehmen_id": uid, "name": name, "branche": "banken",
                      "gruppe": z[kopf.index("Gruppe")], "rolle": z[kopf.index("Rolle")],
                      "nachfolger_von": "", "nachfolge_datum": ""}
        hinweis = z[kopf.index("Quelle / Hinweis Zeitreihe")] or ""
        for i, spalte in enumerate(kopf):
            m = re.fullmatch(r"(.+?) (20\d\d) \(Mio\. €\)", spalte)
            if not m or m.group(1) not in ZR_KENNZAHLEN or zahl(z[i]) is None:
                continue
            kz, einheit = ZR_KENNZAHLEN[m.group(1)]
            lang.append({"unternehmen_id": uid, "kennzahl": kz, "stichtag": f"{m.group(2)}-12-31",
                         "wert": z[i], "einheit": einheit, "waehrung": "EUR",
                         "rechnungslegung": "HGB", "ebene": "Einzel",
                         "quelle": hinweis, "pruefstatus": "geparst"})
    # Aufsichtsrechtliche Kennzahlen zum 31.12.2025 aus der Offenlegung (Ebene steht im Blatt)
    for kopf, z in tabelle(wb["Offenlegung 31.12.2025"]):
        uid = slug(z[kopf.index("Bank")])
        for spalte, (kz, einheit) in OFF_KENNZAHLEN.items():
            if spalte in kopf and zahl(z[kopf.index(spalte)]) is not None:
                lang.append({"unternehmen_id": uid, "kennzahl": kz, "stichtag": "2025-12-31",
                             "wert": z[kopf.index(spalte)], "einheit": einheit, "waehrung": "EUR",
                             "rechnungslegung": "aufsichtlich", "ebene": z[kopf.index("Ebene des Berichts")] or "",
                             "quelle": z[kopf.index("Quelle")] or "", "pruefstatus": "geparst"})
        stamm.setdefault(uid, {"unternehmen_id": uid, "name": z[kopf.index("Bank")], "branche": "banken",
                               "gruppe": z[kopf.index("Gruppe")], "rolle": z[kopf.index("Rolle")],
                               "nachfolger_von": "", "nachfolge_datum": ""})
    lang.sort(key=lambda r: (r["unternehmen_id"], r["kennzahl"], r["stichtag"]))
    with open(AUS / "zeitreihe_lang.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, FELDER)
        w.writeheader()
        w.writerows(lang)
    with open(AUS / "stammdaten.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(next(iter(stamm.values()))))
        w.writeheader()
        w.writerows(sorted(stamm.values(), key=lambda r: r["unternehmen_id"]))
    print(len(lang), "Werte,", len(stamm), "Unternehmen")


if __name__ == "__main__":
    main()
