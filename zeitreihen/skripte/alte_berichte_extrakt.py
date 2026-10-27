"""Liest Bilanzsumme, Eigenkapital, Jahresüberschuss und Fonds § 340g aus älteren Berichten (zwei Spalten je Zeile).

Verankerung statt Raten: Eine Zeile mit zwei Zahlen zählt nur, wenn eine der beiden Zahlen (nach Einheit EUR, TEUR
oder Mio.) einen bereits bekannten Wert der Bank auf 0,3 % genau trifft. Das legt Jahr, Einheit und Ebene (Einzel-
gegen Konzernabschluss) fest. Die andere Spalte ist dann das Nachbarjahr: Liegt das Folgejahr schon vor und die
Zeile bestätigt es nicht, ist es das Vorjahr. Neue Werte dienen in der nächsten Runde als Anker, so läuft die Kette
von 2024 rückwärts. Widersprechen sich Berichte für dasselbe Jahr, wird es verworfen.
Aufruf: python3 -I alte_berichte_extrakt.py PDFORDNER INDEX.csv AUS.csv [--cache DIR] [--ab JAHR]
"""
import argparse
import concurrent.futures as cf
import csv
import re
import subprocess
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mehrjahres_extrakt import ZEILEN, zahlen  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
LANG = REPO / "zeitreihen/zeitreihe_lang.csv"
SKALEN = (1e-6, 1e-3, 1.0, 1e3)   # EUR, TEUR, Mio. EUR, Mrd. EUR -> Mio. EUR


def slug(n):
    s = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def pdftext(pdf, cache):
    t = cache / (pdf.parent.name + "__" + pdf.name + ".txt")
    if not t.exists():
        subprocess.run(["pdftotext", "-layout", str(pdf), str(t)], timeout=180, check=False, capture_output=True)
    return t.read_text(errors="ignore") if t.exists() else ""


def einheit(v, bekannt):
    """Skalierter Wert, der dem nächstliegenden bekannten Wert am nächsten kommt (Faktor 0,3 bis 3,3), sonst None."""
    if v == 0:
        return 0.0
    ref = [w for w in bekannt.values() if w]
    best = None
    for s in SKALEN:
        for w in ref:
            q = abs(v * s / w) if w else 0
            if 0.3 <= q <= 3.3 and (best is None or abs(q - 1) < best[0]):
                best = (abs(q - 1), v * s)
    return best[1] if best else None


def plausibel(kz, v, nachbar):
    if nachbar == 0 or v == 0:
        return kz in ("jahresueberschuss", "fonds_340g")
    q = abs(v / nachbar)
    return 0.4 <= q <= 2.5 if kz in ("bilanzsumme", "eigenkapital") else 0.05 <= q <= 20


def auswerten(z, b, kz):
    """{jahr: wert} für noch unbekannte Jahre einer Zeile, verankert an bekannten Werten; sonst {}."""
    z = z[:10]
    gefunden = {}
    for s in SKALEN:
        w = [x * s for x in z]
        for i, v in enumerate(w):
            for y, ref in b.items():
                if not ref or not nahe(v, ref):
                    continue
                zulaessig = []
                for h in (1, -1):                     # 1: Spalten laufen rückwärts in der Zeit, -1: vorwärts
                    jahr = lambda k: y - h * (k - i)
                    block = {i: y}
                    for richtung in (1, -1):          # vom Anker nach außen, solange die Zeile plausibel bleibt
                        k = i + richtung
                        while 0 <= k < len(w) and 2010 <= jahr(k) <= 2025 and plausibel(kz, w[k], w[k - richtung]):
                            block[k] = jahr(k)
                            k += richtung
                    treffer = [k for k, j in block.items() if k != i and j in b and nahe(w[k], b[j])]
                    falsch = [k for k, j in block.items() if k != i and j in b and b[j] and not nahe(w[k], b[j], 0.01)]
                    if treffer and not falsch:
                        zulaessig.append((len(treffer), block))
                    elif len(z) == 2 and not treffer and not falsch and len(block) == 2:
                        k = 1 - i                       # Zeile mit zwei Zahlen: Folgejahr bekannt, aber nicht bestätigt = Vorjahr
                        if h == 1 and y + 1 in b and y - 1 not in b:
                            zulaessig.append((0, block))
                if len(zulaessig) == 1 or (len(zulaessig) == 2 and zulaessig[0][0] != zulaessig[1][0]):
                    block = max(zulaessig, key=lambda t: t[0])[1]
                    for k, j in block.items():
                        if j not in b:
                            gefunden[j] = w[k]
                    if gefunden:
                        return gefunden
    return gefunden


def nahe(a, b, tol=0.003):
    return b != 0 and abs(a - b) <= tol * abs(b)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("pdfordner")
    p.add_argument("index")
    p.add_argument("aus")
    p.add_argument("--cache", default="/tmp/alte_cache")
    p.add_argument("--ab", type=int, default=2024, help="nur bekannte Werte ab diesem Jahr als Anker (Test gegen die übrigen)")
    a = p.parse_args()
    cache, wurzel = Path(a.cache), Path(a.pdfordner)
    cache.mkdir(parents=True, exist_ok=True)
    ids = {}
    with open(REPO / "zeitreihen/stammdaten.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            ids[slug(r["name"])] = r["unternehmen_id"]
    bekannt, ankerfrei = defaultdict(dict), defaultdict(dict)
    with open(LANG, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["rechnungslegung"] == "HGB":
                j = int(r["stichtag"][:4])
                (bekannt if j >= a.ab else ankerfrei)[(r["unternehmen_id"], r["kennzahl"])][j] = float(r["wert"])
    berichte = []
    with open(a.index, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            uid = ids.get(slug(r["bank"]))
            if uid:
                berichte.append((uid, wurzel / r["datei"], r["datei"]))
    with cf.ThreadPoolExecutor(8) as ex:
        texte = list(ex.map(lambda b: pdftext(b[1], cache), berichte))
    zeilen = []                      # (uid, kz, [z1, z2], dokument, seite)
    for (uid, pdf, rel), text in zip(berichte, texte):
        for seite, blatt in enumerate(text.split("\f"), 1):
            for zeile in blatt.splitlines():
                for kz, muster in ZEILEN.items():
                    if muster.match(zeile):
                        z = zahlen(zeile)
                        if len(z) >= 2:
                            zeilen.append((uid, kz, z[:10], rel, seite))
    neu = {}
    for runde in range(20):
        kand = defaultdict(list)
        for uid, kz, z, rel, seite in zeilen:
            b = bekannt.get((uid, kz))
            if not b:
                continue
            erg = auswerten(z, b, kz) or auswerten(z[:2], b, kz)
            for jahr, wert in erg.items():
                kand[(uid, kz, jahr)].append((wert, rel, seite, 0))
        neue = 0
        for (uid, kz, ziel), liste in kand.items():
            if any(not nahe(l[0], liste[0][0]) for l in liste):
                continue                                     # widersprüchlich
            bekannt[(uid, kz)][ziel] = liste[0][0]
            neu[(uid, kz, ziel)] = (liste[0][0], liste[0][1], liste[0][2], len({l[1] for l in liste}))
            neue += 1
        print("Runde", runde + 1, neue, "neue Werte", file=sys.stderr)
        if not neue:
            break
    # Test gegen die zurückgehaltenen älteren Werte (nur bei --ab > früheste Jahre)
    ok = nein = 0
    for (uid, kz, j), (w, rel, seite, n) in neu.items():
        k = ankerfrei.get((uid, kz), {}).get(j)
        if k is not None:
            ok, nein = (ok + 1, nein) if nahe(w, k, 0.005) else (ok, nein + 1)
            if not nahe(w, k, 0.005):
                print("X", uid, kz, j, "bekannt", k, "gelesen", w, rel, seite, file=sys.stderr)
    if ok + nein:
        print("Test gegen zurückgehaltene Werte: passt", ok, "passt nicht", nein, file=sys.stderr)
    with open(a.aus, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["unternehmen_id", "kennzahl", "jahr", "wert_mio_eur", "dokument", "seite", "berichte"])
        for (uid, kz, j), (v, rel, seite, n) in sorted(neu.items()):
            w.writerow([uid, kz, j, v, rel, seite, n])
    print(len(neu), "verankerte Werte ->", a.aus)


if __name__ == "__main__":
    main()
