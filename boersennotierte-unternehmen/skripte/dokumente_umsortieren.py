"""Verschiebt Dokumente in den Branchenordner laut aktuellem universum.csv (nach Änderungen der Branchenzuordnung)
und schreibt die index.csv der betroffenen Branchen neu."""
import csv
import shutil
from pathlib import Path

BASIS = Path(__file__).resolve().parent.parent


def main():
    uni = {u["unternehmen_id"]: u for u in csv.DictReader(open(BASIS / "universum" / "universum.csv", encoding="utf-8-sig"), delimiter=";")}
    alle, kopf = {}, None
    indizes = list(BASIS.glob("*/dokumente/index.csv")) + ([BASIS / "dokumente" / "index.csv"] if (BASIS / "dokumente" / "index.csv").exists() else [])
    for p in indizes:
        alt_branche = p.parent.parent
        for z in csv.DictReader(open(p, encoding="utf-8-sig"), delimiter=";"):
            kopf = kopf or list(z)
            u = uni.get(z["unternehmen_id"])
            ziel_branche = BASIS / u["branche"] if u and u["branche"] else alt_branche
            quelle, ziel = alt_branche / z["datei"], ziel_branche / z["datei"]
            if quelle != ziel and quelle.exists():
                ziel.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(quelle), str(ziel))
                print("verschoben:", z["unternehmen_id"], alt_branche.name, "->", ziel_branche.name)
            if u:
                z["unternehmen"] = u["name"]
            alle.setdefault(ziel_branche, []).append(z)
        p.unlink()
    for branche, zeilen in alle.items():
        p = branche / "dokumente" / "index.csv"
        p.parent.mkdir(parents=True, exist_ok=True)
        zeilen.sort(key=lambda z: (z["unternehmen_id"], z["geschaeftsjahr"], z["datei"]))
        with open(p, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, kopf, delimiter=";")
            w.writeheader()
            w.writerows(zeilen)
    for d in sorted(BASIS.glob("**/dokumente/*"), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    if (BASIS / "dokumente").exists() and not any((BASIS / "dokumente").iterdir()):
        (BASIS / "dokumente").rmdir()


if __name__ == "__main__":
    main()
