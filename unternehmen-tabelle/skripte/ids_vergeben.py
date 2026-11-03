"""Vergibt Unternehmens-IDs für alle Tabellenzeilen ohne ID (03.11.2026, Robin: "Ja").

Weg (nur über stammdaten/ids.py, nie erstellen.py --neu):
  1. Zeile findet ein bestehendes Unternehmen über den Namensschlüssel (ids.schluessel) und teilt keine ISIN mit einer anderen ID
     -> übernimmt dessen ID (Abgleich "Name"), keine neue Zeile im Register.
  2. sonst neue ID (fortlaufend, in Tabellenreihenfolge) mit Name, Rechtsform, Branche, Land, Sitz, Status, LEI und der ISIN,
     sofern diese formal gültig und noch frei ist. Ungültige ISINs (häufig aus CUSIP-Umrechnung) bleiben nur in der Tabelle.
  Ticker bleiben bewusst nur in der Tabelle: app/boersen_abruf.py ordnet über den Ticker zu, und Tickers sind börsenübergreifend nicht eindeutig.
Schreibt stammdaten/unternehmen_ids.csv und isin_zuordnung.csv (einmal am Ende), die Spalte unternehmen_id der CSV und id_zuordnung.csv.
Idempotent: Zeilen mit ID bleiben unberührt. Aufruf: python3 unternehmen-tabelle/skripte/ids_vergeben.py [--trocken]
"""
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "stammdaten"))
import ids  # noqa: E402

TABELLE = REPO / "unternehmen-tabelle/Unternehmen_Tabelle.csv"
ZUORDNUNG = REPO / "unternehmen-tabelle/id_zuordnung.csv"


def main():
    trocken = "--trocken" in sys.argv
    reg = ids.lade(neu=True)
    with open(TABELLE, encoding="utf-8-sig", newline="") as f:
        kopf = f.readline()
        f.seek(0)
        lies = csv.DictReader(f, delimiter=";")
        felder = lies.fieldnames
        zeilen = list(lies)
    vergeben = {}                     # uid -> Zeile (jede bestehende ID höchstens einmal übernehmen)
    for z in zeilen:
        if z["unternehmen_id"]:
            vergeben[z["unternehmen_id"]] = z
    neu = abgleich = isin_ungueltig = isin_belegt = 0
    naechste = int(reg._naechste_id()[1:])
    neue_zuordnung = []
    for z in zeilen:
        if z["unternehmen_id"]:
            continue
        name, isin = z["Name *"].strip(), z["ISIN"].strip().upper()
        uid = None
        kandidaten = reg.nach_schluessel.get(ids.schluessel(name), set())
        if len(kandidaten) == 1:
            k = next(iter(kandidaten))
            fremde = reg.unternehmen[k]["isin_haupt"]
            if k not in vergeben and (not isin or not fremde or isin == fremde) and reg.nach_isin.get(isin, k) == k:
                uid = k
                abgleich += 1
                art, weg = "bestehend", "Name"
        if uid is None:
            uid = f"U{naechste:06d}"
            naechste += 1
            r = {k: "" for k in ids.KOPF_U}
            gueltig = bool(isin) and ids.isin_pruefsumme_ok(isin)
            if isin and not gueltig:
                isin_ungueltig += 1
            if gueltig and isin in reg.nach_isin:
                isin_belegt += 1
                gueltig = False
            r.update(unternehmen_id=uid, name=name, rechtsform=z["Rechtsform"], branche=z["Branche *"], sitz=z["Sitz"], land=z["Land *"],
                     status="börsennotiert" if z["Börsennotiert *"].strip().lower() == "ja" else "nicht börsennotiert",
                     isin_haupt=isin if gueltig else "", lei=z["LEI"], herkunft="Unternehmenstabelle",
                     hinweis="ID am 03.11.2026 für alle Tabellenzeilen ohne ID vergeben" + ("" if gueltig or not isin else f"; ISIN {isin} formal ungültig oder vergeben, nur in der Tabelle"))
            reg.unternehmen[uid] = r
            if gueltig:
                reg.isins.append({"isin": isin, "unternehmen_id": uid, "art": "haupt"})
                reg.nach_isin[isin] = uid
            neu += 1
            art, weg = "neu", "Tabellenzeile"
        vergeben[uid] = z
        z["unternehmen_id"] = uid
        neue_zuordnung.append([uid, name, z["Land *"], art, weg])
    print(f"{neu} neue IDs, {abgleich} Zeilen auf bestehende ID gelegt, {isin_ungueltig} ungültige ISINs und {isin_belegt} belegte ISINs nur in der Tabelle")
    if trocken:
        return
    reg.speichern()
    with open(TABELLE, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, felder, delimiter=";", lineterminator="\r\n")
        w.writeheader()
        w.writerows(zeilen)
    with open(ZUORDNUNG, encoding="utf-8", newline="") as f:
        alt = list(csv.reader(f))
    with open(ZUORDNUNG, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerows(alt)
        w.writerows(neue_zuordnung)


if __name__ == "__main__":
    main()
