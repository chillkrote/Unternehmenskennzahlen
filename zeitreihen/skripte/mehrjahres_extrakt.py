"""Liest Mehrjahresübersichten aus bereits abgelegten Geschäftsberichten (PDF) und ergänzt ältere Jahre.

Verfahren: In den Textzeilen zu Bilanzsumme, Eigenkapital, Jahresüberschuss und Fonds § 340g werden alle Zahlen
gelesen. Eine Zeile zählt nur, wenn mindestens zwei bereits bekannte Jahreswerte der Bank (aus zeitreihe_lang.csv)
in aufeinanderfolgenden Spalten stehen (so ergeben sich Richtung, Einheit und Jahreszuordnung). Nur dann werden die
übrigen Spalten als frühere Jahre übernommen, solange Nachbarjahre plausibel bleiben (Faktor 0,5 bis 2).
Ergebnis: zeitreihen/rohdaten/mehrjahres_extrakt.csv. Aufruf: python3 -I mehrjahres_extrakt.py [--cache DIR]
"""
import argparse
import csv
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOK = REPO / "banken/bilanzvergleich-gj2025/dokumente"
LANG = REPO / "zeitreihen/zeitreihe_lang.csv"
AUS = REPO / "zeitreihen/rohdaten/mehrjahres_extrakt.csv"

ZEILEN = {
    "bilanzsumme": re.compile(r"^\s*Bilanzsumme\b(?!\s*(?:in\s*%|-?wachstum))", re.I),
    "eigenkapital": re.compile(r"^\s*(?:Bilanzielles\s+|Wirtschaftliches\s+)?Eigenkapital\b(?!\s*(?:zum|-?quote|-?rendite|-?ausstattung|\d{1,2}\.))", re.I),
    "jahresueberschuss": re.compile(r"^\s*Jahres(?:über|ueber)schuss\b(?!\s*(?:vor|nach))", re.I),
    "fonds_340g": re.compile(r"^\s*Fonds\s+für\s+allgemeine\s+Bankrisiken", re.I),
}
ZAHL = re.compile(r"(?<![\w.,])-?\d{1,3}(?:[. ]\d{3})*(?:,\d+)?(?![\w])|(?<![\w.,])-?\d+(?:,\d+)?(?![\w])")
SKALEN = (1e-6, 1e-3, 1.0)


def zahlen(zeile):
    out = []
    for m in ZAHL.finditer(zeile):
        t = m.group(0).replace(" ", "").replace(".", "").replace(",", ".")
        try:
            out.append(float(t))
        except ValueError:
            pass
    return out


def bank_id(ordner, ids):
    if ordner in ids:
        return ordner
    k = [i for i in ids if i.startswith(ordner) or ordner.startswith(i)]
    return k[0] if len(k) == 1 else None


def text(pdf, cache):
    t = cache / (pdf.parent.name + "__" + pdf.name + ".txt")
    if not t.exists():
        subprocess.run(["pdftotext", "-layout", str(pdf), str(t)], timeout=120, check=False, capture_output=True)
    return t.read_text(errors="ignore") if t.exists() else ""


def auswerten(zahlenreihe, bekannt):
    """Gibt {jahr: wert} der Zeile zurück oder {} (mindestens 2 passende Nachbarspalten)."""
    best = {}
    for s in SKALEN:
        for richtung in (1, -1):
            for i, v in enumerate(zahlenreihe):
                for y, w in bekannt.items():
                    if w == 0 or abs(v * s - w) > abs(w) * 0.003:
                        continue
                    j = i + richtung                      # Nachbarspalte: Jahr y-1
                    if not (0 <= j < len(zahlenreihe)):
                        continue
                    w2 = bekannt.get(y - 1)
                    if w2 is None or w2 == 0 or abs(zahlenreihe[j] * s - w2) > abs(w2) * 0.003:
                        continue
                    jahre = {i + richtung * k: y - k for k in range(-len(zahlenreihe), len(zahlenreihe))}
                    erg = {}
                    for pos in sorted(range(len(zahlenreihe)), key=lambda p: abs(p - i)):
                        jahr = jahre.get(pos)
                        if jahr is None or not 2010 <= jahr <= 2025:
                            continue
                        wert = zahlenreihe[pos] * s
                        nachbar = erg.get(jahr + (1 if richtung == 1 else -1) * (1 if pos > i else -1) * -1) if False else None
                        erg[jahr] = wert
                    # Plausibilität: benachbarte Jahre Faktor 0,5..2 (Vorzeichen bei Jahresüberschuss tolerant)
                    ok = {}
                    for jahr in sorted(erg):
                        if jahr in bekannt:
                            ok[jahr] = erg[jahr]
                    ys = sorted(erg)
                    # von den bekannten Jahren nach außen laufen
                    anker = min(bekannt.keys() & erg.keys())
                    for step in (-1, 1):
                        prev = erg[anker]
                        jahr = anker + step
                        while jahr in erg:
                            cur = erg[jahr]
                            if prev != 0 and 0.5 <= abs(cur / prev) <= 2.0 or prev == 0:
                                ok[jahr] = cur
                                prev = cur
                                jahr += step
                            else:
                                break
                    if len(ok) > len(best):
                        best = ok
    return best


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cache", default="/tmp/mehrjahres_cache")
    a = p.parse_args()
    cache = Path(a.cache)
    cache.mkdir(parents=True, exist_ok=True)
    bekannt = {}
    with open(LANG, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["rechnungslegung"] == "HGB":
                bekannt.setdefault((r["unternehmen_id"], r["kennzahl"]), {})[int(r["stichtag"][:4])] = float(r["wert"])
    ids = {i for i, _ in bekannt}
    neu = {}
    for ordner in sorted(p for p in DOK.iterdir() if p.is_dir() and not p.name.startswith("_")):
        uid = bank_id(ordner.name, ids)
        if uid is None:
            continue
        for pdf in sorted(ordner.glob("*.pdf")):
            for seite, blatt in enumerate(text(pdf, cache).split("\f"), 1):
                for zeile in blatt.splitlines():
                    for kz, muster in ZEILEN.items():
                        b = bekannt.get((uid, kz))
                        if not b or not muster.match(zeile):
                            continue
                        for jahr, wert in auswerten(zahlen(zeile), b).items():
                            if jahr not in b:
                                neu.setdefault((uid, kz, jahr), []).append((wert, f"{ordner.name}/{pdf.name}", seite))
    AUS.parent.mkdir(exist_ok=True)
    with open(AUS, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["unternehmen_id", "kennzahl", "jahr", "wert_mio_eur", "dokument", "seite", "treffer"])
        for (uid, kz, jahr), liste in sorted(neu.items()):
            werte = {round(x[0], 1) for x in liste}
            if len(werte) > 1:                          # widersprüchliche Treffer: nicht übernehmen
                continue
            x = liste[0]
            w.writerow([uid, kz, jahr, x[0], x[1], x[2], len(liste)])
    print(len(neu), "Kandidaten ->", AUS)


if __name__ == "__main__":
    main()
