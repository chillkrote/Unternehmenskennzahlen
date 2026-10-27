"""Prüft die zentrale Unternehmens-ID im ganzen Repo. Exit-Code 1 bei jedem Verstoß (Build, Test, Workflow).

Regeln:
  1. IDs haben die Form U000123, sind eindeutig und haben einen Namen.
  2. Jede ISIN gehört zu genau einer ID (isin_zuordnung.csv, unternehmen_ids.csv und jede Datei im Repo mit ISIN und ID in einer Zeile).
  3. ISINs sind formal gültig (Format und Prüfziffer).
  4. Ein Alias (alte ID, Ordnername, Namensvariante) verweist auf höchstens eine ID.
  5. Jede ID-Spalte in CSV-Dateien (unternehmen_id, *_unternehmen_id) und jede id in app/data/*.json zeigt auf eine vorhandene ID (verwaiste Verweise = 0).
  6. Mit --gegen=<git-ref> (z. B. origin/main): keine ID des Referenzstands darf verschwinden, und keine ISIN darf von einer ID zu einer
     anderen wandern (IDs sind dauerhaft; Zusammenführungen werden als Alias auf die behaltene ID abgebildet, nicht durch Löschen).
Aufruf: python3 stammdaten/pruefe_ids.py [--json] [--gegen=origin/main]
"""
import csv
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ids

R = ids.REPO
ID_SPALTEN = ("unternehmen_id", "gesellschaft_unternehmen_id", "ueber_unternehmen_id")
ISIN_SPALTEN = ("isin", "isin_haupt")
AUSLASSEN = ("boersennotierte-unternehmen/rohdaten/yahoo/", "volkswirtschaft/", "stammdaten/", "desktop/")


def tracked(endung):
    r = subprocess.run(["git", "-C", str(R), "ls-files", "-z"], capture_output=True)
    dateien = [p for p in r.stdout.decode().split("\0") if p] if r.returncode == 0 else \
        [str(p.relative_to(R)) for p in R.rglob("*") if p.is_file() and ".git" not in p.parts]
    return [p for p in dateien if p.endswith(endung) and not p.startswith(AUSLASSEN) and (R / p).exists()]


def csv_zeilen(pfad):
    with open(R / pfad, encoding="utf-8-sig", newline="") as f:
        kopf = f.readline()
        f.seek(0)
        d = ";" if kopf.count(";") > kopf.count(",") else ","
        return list(csv.DictReader(f, delimiter=d))


def json_ids(pfad):
    """(id, isin) aus den App-Daten: Listen von Objekten mit Feld id."""
    j = json.loads((R / pfad).read_text(encoding="utf-8"))
    out = []

    def lauf(x):
        if isinstance(x, dict):
            if "id" in x and "name" in x and isinstance(x["id"], str) and (x.get("branche") or x.get("bank")):
                out.append((x["id"], x.get("isin") or ""))
            for v in x.values():
                lauf(v)
        elif isinstance(x, list):
            for v in x:
                lauf(v)
    lauf(j)
    return out


def pruefen():
    fehler, info = [], {}
    reg = ids.Register()
    ids_alle = set(reg.unternehmen)
    # 1 IDs
    zeilen = ids._lesen(ids.UNTERNEHMEN)
    if len(zeilen) != len(ids_alle):
        fehler.append("unternehmen_ids.csv: doppelte ID")
    for r in zeilen:
        if not ids.ID_MUSTER.match(r["unternehmen_id"]):
            fehler.append(f"ID mit falschem Format: {r['unternehmen_id']}")
        if not r["name"].strip():
            fehler.append(f"{r['unternehmen_id']}: Name fehlt")
    info["unternehmen"] = len(ids_alle)
    # 2 ISIN genau einer ID
    je_isin = defaultdict(set)
    for r in ids._lesen(ids.ISINS):
        je_isin[r["isin"]].add(r["unternehmen_id"])
        if r["unternehmen_id"] not in ids_alle:
            fehler.append(f"isin_zuordnung.csv: {r['isin']} -> unbekannte ID {r['unternehmen_id']}")
    for r in zeilen:
        for i in [r["isin_haupt"], *r["weitere_isins"].split("|")]:
            if i:
                je_isin[i].add(r["unternehmen_id"])
    quellen = 2
    for p in tracked(".csv"):
        z = csv_zeilen(p)
        if not z or not any(c in z[0] for c in ISIN_SPALTEN) or "unternehmen_id" not in z[0]:
            continue
        quellen += 1
        for r in z:
            for c in ISIN_SPALTEN:
                if r.get(c) and r.get("unternehmen_id"):
                    je_isin[r[c].strip()].add(r["unternehmen_id"])
    for p in tracked(".json"):
        if p.startswith("app/data/"):
            for uid, isin in json_ids(p):
                if isin:
                    je_isin[isin].add(uid)
    for isin, mehrere in sorted(je_isin.items()):
        if len(mehrere) > 1:
            fehler.append(f"ISIN {isin} bei mehreren IDs: {sorted(mehrere)}")
    info["isins"] = len(je_isin)
    # 3 ISIN formal
    for isin in sorted(je_isin):
        if not ids.isin_pruefsumme_ok(isin):
            fehler.append(f"ISIN {isin} formal ungültig (Format oder Prüfziffer)")
    # 4 Aliase
    je_alias = defaultdict(set)
    for a in reg.aliase:
        je_alias[a["alias"]].add(a["unternehmen_id"])
        if a["unternehmen_id"] not in ids_alle:
            fehler.append(f"Alias {a['alias']!r} -> unbekannte ID {a['unternehmen_id']}")
    for a, v in je_alias.items():
        if len(v) > 1:
            fehler.append(f"Alias {a!r} bei mehreren IDs: {sorted(v)}")
    info["aliase"] = len(reg.aliase)
    # 5 Verweise
    verweise = 0
    for p in tracked(".csv"):
        z = csv_zeilen(p)
        spalten = [c for c in ID_SPALTEN if z and c in z[0]]
        for r in z:
            for c in spalten:
                v = (r.get(c) or "").strip()
                if v:
                    verweise += 1
                    if v not in ids_alle:
                        fehler.append(f"{p}: {c}={v!r} ist keine Unternehmens-ID")
    for p in tracked(".json"):
        if p.startswith("app/data/"):
            for uid, _ in json_ids(p):
                verweise += 1
                if uid not in ids_alle:
                    fehler.append(f"{p}: id={uid!r} ist keine Unternehmens-ID")
    info["verweise"] = verweise
    info["isin_quellen"] = quellen
    return fehler, info


def gegen_referenz(ref):
    """Fehler, wenn gegenüber dem Git-Stand ref IDs fehlen oder ISINs die ID gewechselt haben."""
    fehler = []

    def lies(datei):
        r = subprocess.run(["git", "-C", str(R), "show", f"{ref}:stammdaten/{datei}"], capture_output=True)
        if r.returncode != 0:
            return None
        import io
        return list(csv.DictReader(io.StringIO(r.stdout.decode("utf-8-sig"))))
    alt_u, alt_i = lies("unternehmen_ids.csv"), lies("isin_zuordnung.csv")
    if alt_u is None:
        return fehler  # Referenz kennt die Stammdaten noch nicht
    jetzt = {r["unternehmen_id"] for r in ids._lesen(ids.UNTERNEHMEN)}
    for r in alt_u:
        if r["unternehmen_id"] not in jetzt:
            fehler.append(f"ID {r['unternehmen_id']} ({r['name']}) ist gegenüber {ref} verschwunden; IDs werden nie gelöscht oder neu vergeben")
    neu_isin = {r["isin"]: r["unternehmen_id"] for r in ids._lesen(ids.ISINS)}
    for r in alt_i or []:
        if neu_isin.get(r["isin"], r["unternehmen_id"]) != r["unternehmen_id"]:
            fehler.append(f"ISIN {r['isin']} wechselte gegenüber {ref} von {r['unternehmen_id']} zu {neu_isin[r['isin']]}")
    return fehler


def main():
    fehler, info = pruefen()
    for a in sys.argv[1:]:
        if a.startswith("--gegen="):
            fehler += gegen_referenz(a.split("=", 1)[1])
    if "--json" in sys.argv:
        print(json.dumps({"fehler": fehler, **info}, ensure_ascii=False))
    else:
        print(f"{info['unternehmen']} Unternehmen, {info['isins']} ISINs (je genau einer ID), {info['aliase']} Aliase, "
              f"{info['verweise']} geprüfte ID-Verweise")
        for f in fehler[:200]:
            print("FEHLER:", f)
    sys.exit(1 if fehler else 0)


if __name__ == "__main__":
    main()
