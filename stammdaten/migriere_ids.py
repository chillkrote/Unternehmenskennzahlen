"""Stellt alle CSV-Dateien im Repo von den alten Schreibweisen (Slug aus dem Namen, zwei Schemata) auf die zentrale Unternehmens-ID um.

Betroffen sind Spalten unternehmen_id, gesellschaft_unternehmen_id und ueber_unternehmen_id. Alte Werte werden über
stammdaten/unternehmen_aliase.csv (Art id_alt) aufgelöst; Werte, die schon eine neue ID sind, bleiben stehen (idempotent).
Format der Dateien (BOM, Trennzeichen, Zeilenende) bleibt erhalten. Dateien unter Dokumentordnern behalten ihre Ordnernamen.
Aufruf: python3 stammdaten/migriere_ids.py [--trocken]
"""
import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ids
import pruefe_ids as pr

R = ids.REPO


def umschreiben(pfad, reg, trocken):
    roh = (R / pfad).read_bytes()
    bom = roh.startswith(b"\xef\xbb\xbf")
    text = roh.decode("utf-8-sig")
    kopf = text.split("\n", 1)[0]
    delim = ";" if kopf.count(";") > kopf.count(",") else ","
    ende = "\r\n" if "\r\n" in text[:5000] else "\n"
    zeilen = list(csv.reader(io.StringIO(text, newline=""), delimiter=delim))
    if not zeilen:
        return 0, 0, []
    spalten = [i for i, c in enumerate(zeilen[0]) if c in pr.ID_SPALTEN]
    if not spalten:
        return 0, 0, []
    geaendert, offen = 0, []
    for z in zeilen[1:]:
        for i in spalten:
            if i < len(z) and z[i].strip():
                alt = z[i]
                if ids.ID_MUSTER.match(alt) and alt in reg.unternehmen:
                    continue
                neu = reg.exakt.get(alt)
                if neu and ids.ID_MUSTER.match(neu):
                    z[i] = neu
                    geaendert += 1
                else:
                    offen.append((pfad, zeilen[0][i], alt))
    if geaendert and not trocken:
        out = io.StringIO(newline="")
        csv.writer(out, delimiter=delim, lineterminator=ende).writerows(zeilen)
        (R / pfad).write_bytes((b"\xef\xbb\xbf" if bom else b"") + out.getvalue().encode("utf-8"))
    return geaendert, len(zeilen) - 1, offen


JSON_DATEIEN = ["boersennotierte-unternehmen/rohdaten/berichte_abgleich.json", "boersennotierte-unternehmen/rohdaten/berichte_status.json",
                "termine/rohdaten/finanzkalender_status.json", "boersennotierte-unternehmen/universum/korrekturen.json"]


def json_umschreiben(pfad, reg, trocken):
    """Ersetzt in Schlüsseln und Werten jede exakt zitierte alte ID durch die neue; Formatierung bleibt (reiner Textersatz)."""
    import json
    import re
    text = (R / pfad).read_text(encoding="utf-8")
    alt = {a["alias"]: a["unternehmen_id"] for a in reg.aliase if a["art"] == "id_alt"}
    n = 0

    def ersatz(m):
        nonlocal n
        neu = alt.get(m.group(1))
        if neu:
            n += 1
            return '"' + neu + '"'
        return m.group(0)
    neu_text = re.sub(r'"([a-z0-9][a-z0-9-]*)"', ersatz, text)
    vorher, nachher = json.loads(text), json.loads(neu_text)
    if isinstance(vorher, dict) and len(vorher) != len(nachher):
        raise SystemExit(f"{pfad}: Schlüssel würden zusammenfallen ({len(vorher)} -> {len(nachher)}); von Hand klären")
    if n and not trocken:
        (R / pfad).write_text(neu_text, encoding="utf-8")
    return n


def main():
    trocken = "--trocken" in sys.argv
    reg = ids.Register()
    gesamt, offen, dateien = 0, [], []
    for p in pr.tracked(".csv"):
        g, n, o = umschreiben(p, reg, trocken)
        if n or o:
            dateien.append((p, n, g))
        gesamt += g
        offen += o
    for p, n, g in dateien:
        print(f"{p}: {g} von {n} Zeilen umgestellt")
    for p in JSON_DATEIEN:
        n = json_umschreiben(p, reg, trocken)
        print(f"{p}: {n} Stellen umgestellt")
        gesamt += n
    print("Verweise umgestellt:", gesamt, "| nicht auflösbar:", len(offen))
    for o in sorted(set(offen))[:50]:
        print("  OFFEN", o)
    sys.exit(1 if offen else 0)


if __name__ == "__main__":
    main()
