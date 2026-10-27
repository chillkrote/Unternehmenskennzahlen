"""Datenprüfung für das ganze Repo (die Prüfungen des Projektreviews vom 27.10.2026 als Skript).

Fehler (Exit-Code 1): verletzte ID-Regeln, falsche SHA-256 in einer index.csv.
Warnungen (Exit-Code 0): Bank ohne Bilanzsumme, Bilanz geht nicht auf, Übersicht und Bilanzblatt widersprechen sich, auffällige Quoten.
Dateien, die im (sparse) Checkout fehlen, werden übersprungen und gezählt; mit --voll gilt das als Fehler.
Aufruf: python3 pruefung/pruefe.py [--voll]"""
import csv
import hashlib
import subprocess
import sys
from pathlib import Path

import openpyxl

WURZEL = Path(__file__).resolve().parent.parent
XLSX = WURZEL / "banken/bilanzvergleich-gj2025/auswertung/Bilanzvergleich_Banken_GJ2025.xlsx"
fehler, warnungen = [], []


def ids():
    r = subprocess.run([sys.executable, str(WURZEL / "stammdaten/pruefe_ids.py")], capture_output=True, text=True)
    if r.returncode:
        fehler.append("ID-Prüfung (stammdaten/pruefe_ids.py): " + (r.stdout + r.stderr).strip()[-400:])


def index_dateien(voll):
    fehlt = geprueft = 0
    for idx in WURZEL.rglob("index.csv"):
        if ".git" in idx.parts:
            continue
        with open(idx, encoding="utf-8-sig") as f:
            kopf = f.readline()
            f.seek(0)
            zeilen = list(csv.DictReader(f, delimiter=";" if kopf.count(";") >= kopf.count(",") else ","))
        for z in zeilen:
            pfad, soll = z.get("datei") or z.get("pfad"), (z.get("sha256") or "").strip()
            if not pfad or not soll:
                continue
            p = idx.parent.parent / pfad if not (idx.parent / pfad).exists() and (idx.parent.parent / pfad).exists() else idx.parent / pfad
            if not p.exists():
                fehlt += 1
                continue
            geprueft += 1
            if hashlib.sha256(p.read_bytes()).hexdigest() != soll:
                fehler.append(f"SHA-256 stimmt nicht: {p.relative_to(WURZEL)}")
    if fehlt:
        (fehler if voll else warnungen).append(f"{fehlt} Dateien aus index.csv nicht im Checkout (übersprungen), {geprueft} geprüft")
    print(f"index.csv: {geprueft} Dateien geprüft")


def banken():
    if not XLSX.exists():
        warnungen.append("Bankenexcel fehlt")
        return
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)

    def tab(name):
        zl = list(wb[name].iter_rows(values_only=True))
        return [dict(zip(zl[0], z)) for z in zl[1:] if z[0]]
    uebers = {z["Bank"]: z for z in tab("Übersicht")}
    for b, z in uebers.items():
        if not isinstance(z["Bilanzsumme (Mio. €)"], (int, float)) or z["Bilanzsumme (Mio. €)"] <= 0:
            warnungen.append(f"{b}: keine Bilanzsumme (Bank ohne Abschluss)")
    for z in tab("Bilanzen 31.12.2025"):
        a, p = z["Summe der Aktiva"], z["Summe der Passiva"]
        if isinstance(a, (int, float)) and isinstance(p, (int, float)) and abs(a - p) > max(2, 0.0002 * a):
            warnungen.append(f"Bilanz geht nicht auf: {z['Bank']} Aktiva {a:,.0f} − Passiva {p:,.0f} = {a - p:,.1f}")
        bs = uebers.get(z["Bank"], {}).get("Bilanzsumme (Mio. €)")
        if isinstance(a, (int, float)) and isinstance(bs, (int, float)) and abs(a - bs) > max(2, 0.002 * bs):
            warnungen.append(f"Übersicht ≠ Bilanzblatt: {z['Bank']} Übersicht {bs:,.0f} vs. Bilanz {a:,.0f}")
    for b, z in uebers.items():
        q, bs, ek = z["EK-Quote (EK/BS)"], z["Bilanzsumme (Mio. €)"], z["Eigenkapital (Mio. €)"]
        if all(isinstance(x, (int, float)) for x in (q, bs, ek)) and bs and abs(q - ek / bs) > 0.0005:
            warnungen.append(f"EK-Quote passt nicht zu EK/BS: {b}")
    print(f"Banken: {len(uebers)} Zeilen geprüft")


def main():
    voll = "--voll" in sys.argv
    ids(); index_dateien(voll); banken()
    for w in warnungen:
        print("WARNUNG", w)
    for f in fehler:
        print("FEHLER", f)
    print(f"{len(fehler)} Fehler, {len(warnungen)} Warnungen")
    sys.exit(1 if fehler else 0)


if __name__ == "__main__":
    main()
