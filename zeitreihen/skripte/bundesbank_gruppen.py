"""Holt Gruppenreihen (Sparkassen, Kreditgenossenschaften, Landesbanken, Kreditbanken, Großbanken) von der Bundesbank.

Quelle: offene SDMX-Schnittstelle der Deutschen Bundesbank (api.statistiken.bundesbank.de, ohne Anmeldung),
Datenflüsse BBBP1 (Gewinn- und Verlustrechnung, jährlich) und BBBK4 (BISTA Gesamtinstitute, monatlich; hier nur Dezember).
Ergebnis: zeitreihen/gruppen_lang.csv. Aufruf: python3 -I bundesbank_gruppen.py
"""
import csv
import datetime
import io
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "gruppen_lang.csv"
API = "https://api.statistiken.bundesbank.de/rest/data/"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"

# Gruppenkürzel in BBBP1 -> (gruppe_id, Anzeigename)
GRUPPEN_P1 = {"SK": ("sparkassen", "Sparkassen"), "GN": ("kreditgenossenschaften", "Kreditgenossenschaften"),
              "LB": ("landesbanken", "Landesbanken"), "KR": ("kreditbanken", "Kreditbanken"), "GB": ("grossbanken", "Großbanken")}
# BBBP1-Kennzahlcode -> kennzahl (Beträge Mio. EUR, Renditen Prozent -> Anteil)
KZ_P1 = {"K120.X.X": "bilanzsumme", "G010.X.1": "jahresueberschuss", "K100.X.1": "jahresueberschuss_vor_steuern",
         "K010.X.1": "zinsueberschuss", "K080.X.1": "betriebsergebnis",
         "EK15.X.X": "ek_rentabilitaet_nach_steuern", "EK11.X.X": "ek_rentabilitaet_vor_steuern"}
# BBBK4 (Monatsreihen, Dezember): Bilanzsumme, Kapital insgesamt, Zahl der Institute
BBBK4 = {
    "sparkassen+landesbanken": ("Landesbanken und Sparkassen", {"bilanzsumme": "OUZ502", "kapital": "OUZ555", "anzahl_institute": "OUZ501"}),
    "kreditgenossenschaften": ("Kreditgenossenschaften", {"bilanzsumme": "OUZ515", "kapital": "OUZ558", "anzahl_institute": "OUZ514"}),
    "kreditbanken": ("Kreditbanken", {"bilanzsumme": "OUZ032", "kapital": "OUZ476", "anzahl_institute": "OUZ031"}),
    "grossbanken": ("Großbanken", {"bilanzsumme": "OUZ062", "kapital": "OUZ477", "anzahl_institute": "OUZ061"}),
}


def hole(pfad):
    r = subprocess.run(["curl", "-sS", "-m", "120", "-A", UA, API + pfad + "?format=sdmx_csv&detail=dataonly"], capture_output=True)
    t = r.stdout.decode("utf-8-sig", "replace")
    if t.startswith("{") or not t.strip():
        return []
    return list(csv.DictReader(io.StringIO(t), delimiter=";"))


def main():
    heute = datetime.date.today().isoformat()
    zeilen = []
    for kurz, (gid, name) in GRUPPEN_P1.items():
        for code, kz in KZ_P1.items():
            suffix = "Z5.0000.Z0Z.P0" if code.startswith("EK") else "Z5.0000.Z01.D"
            serie = f"A.DE.N.{kurz}.{code}.{suffix}"
            for r in hole(f"BBBP1/{serie}"):
                # bis 2001 steht der Wert in DM, BBK_EURO enthält die Euro-Umrechnung
                roh = r.get("BBK_EURO") or r["OBS_VALUE"]
                if roh in ("", "."):
                    continue
                einheit = "Anteil" if code.startswith("EK") else "Mio. EUR"
                v = float(roh) / (100 if code.startswith("EK") else 1)
                zeilen.append([gid, name, kz, r["TIME_PERIOD"] + "-12-31", round(v, 6), einheit, "BBBP1." + serie, heute])
    for gid, (name, serien) in BBBK4.items():
        for kz, nr in serien.items():
            for r in hole(f"BBBK4/M.{nr}"):
                # Dezember ab 2002 (davor DM/Euro gemischt); Beträge stehen in Mrd. EUR
                if not r["TIME_PERIOD"].endswith("-12") or int(r["TIME_PERIOD"][:4]) < 2002 or r["OBS_VALUE"] in ("", "."):
                    continue
                v = float(r["OBS_VALUE"])
                einheit = "Anzahl" if kz == "anzahl_institute" else "Mio. EUR"
                if kz != "anzahl_institute":
                    v *= 1000
                zeilen.append([gid, name, kz + "_bista", r["TIME_PERIOD"] + "-31", round(v, 3), einheit, "BBBK4.M." + nr, heute])
    zeilen.sort(key=lambda z: (z[0], z[2], z[3]))
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["gruppe_id", "gruppe", "kennzahl", "stichtag", "wert", "einheit", "bundesbank_serie", "abruf"])
        w.writerows(zeilen)
    print(len(zeilen), "Zeilen ->", OUT)


if __name__ == "__main__":
    main()
