"""Datenschicht des Bank-Terminals.

Liest die Auswertung (Excel, erzeugt von rohdaten/skripte/build.py) und baut
daraus einen Datensatz je Bank. Spalten werden über ihre Überschrift gesucht,
nicht über die Position: neue Spalten oder zusätzliche Banken (z. B. aus dem
EBA-Hub) kommen ohne Codeänderung mit. Fehlt eine Spalte, bleibt das Feld leer.
"""
import csv
import json
import re
import unicodedata
from pathlib import Path

import openpyxl

REPO = Path(__file__).resolve().parent.parent
import sys  # noqa: E402
sys.path.insert(0, str(REPO / "stammdaten"))
import ids as stamm  # noqa: E402  zentrale Unternehmens-IDs (stammdaten/)
STANDARD_EXCEL = REPO / "banken/bilanzvergleich-gj2025/auswertung/Bilanzvergleich_Banken_GJ2025.xlsx"

# Blatt -> {Feldname im Datensatz: Spaltenüberschrift in der Excel}
FELDER = {
    "Übersicht": {
        "sitz": "Sitz",
        "gj": "GJ",
        "rang": "Rang",
        "bs": "Bilanzsumme (Mio. €)",
        "ek": "Eigenkapital (Mio. €)",
        "ek_quote": "EK-Quote (EK/BS)",
        "fonds": "Fonds § 340g (Mio. €)",
        "fonds_bs": "Fonds § 340g in % BS",
        "ek_fonds_quote": "EK-Quote inkl. Fonds § 340g",
        "vj_bs": "VJ Bilanzsumme (Mio. €)",
        "vj_ek": "VJ Eigenkapital (Mio. €)",
        "vj_fonds": "VJ Fonds § 340g (Mio. €)",
        "d_fonds": "Veränderung Fonds § 340g (Mio. €)",
        "at1_posten": "AT1-Instrumente, eigener Passivposten (Mio. €)",
        "nachrang": "Nachrangige Verbindlichkeiten (Mio. €)",
        "cet1_naeh": "CET1-Näherung (Mio. €)",
        "cet1_naeh_bs": "CET1-Näherung in % BS",
        "quellenart": "Quellenart",
        "quelle": "Quelle (Link)",
    },
    "Offenlegung 31.12.2025": {
        "km1_ebene": "Ebene des Berichts",
        "cet1": "Hartes Kernkapital CET1 (Mio. €)",
        "t1": "Kernkapital T1 (Mio. €)",
        "eigenmittel": "Gesamtkapital (Mio. €)",
        "rwa": "Gesamtrisikobetrag RWA (Mio. €)",
        "cet1_quote": "CET1-Quote",
        "t1_quote": "Kernkapitalquote",
        "gk_quote": "Gesamtkapitalquote",
        "gk_anf": "Gesamtkapitalanforderung inkl. Puffer (EU 11a)",
        "gk_puffer_pp": "Gesamtkapitalquote über Anforderung (Pp.)",
        "lr": "Verschuldungsquote (Leverage Ratio)",
        "rwa_dichte": "RWA-Dichte (RWA / Bilanzsumme)",
        "km1_quelle": "Quelle",
    },
    "Eigenmittel CC1": {
        "cc1_instrumente": "Kapitalinstrumente inkl. Agio / Geschäftsguthaben (Mio. €)",
        "cc1_gewinnrl": "Gewinnrücklagen (Mio. €)",
        "cc1_oci": "Kumuliertes sonstiges Ergebnis u. a. Rücklagen (Mio. €)",
        "cc1_fonds": "Fonds für allgemeine Bankrisiken, aufsichtlich (EU-3a, Mio. €)",
        "cc1_vor_abz": "CET1 vor Abzügen (Mio. €)",
        "cc1_abzuege": "Abzüge vom CET1 gesamt (Mio. €, negativ)",
        "cc1_cet1": "Hartes Kernkapital CET1 (Mio. €)",
        "cc1_at1": "Zusätzliches Kernkapital AT1 (Mio. €)",
        "cc1_t2": "Ergänzungskapital T2 (Mio. €)",
        "cc1_kra": "Kreditrisikoanpassungen im T2 (Zeile 50, v. a. § 340f, Mio. €)",
        "cc1_rwa": "RWA (Mio. €)",
    },
    "RWA-Aufteilung OV1": {
        "ov1_kredit": "Kreditrisiko ohne CCR (Mio. €)",
        "ov1_ccr": "Gegenparteiausfallrisiko CCR (Mio. €)",
        "ov1_cva": "CVA-Risiko (Mio. €)",
        "ov1_verbr": "Verbriefungen im Anlagebuch (Mio. €)",
        "ov1_markt": "Marktrisiko (Mio. €)",
        "ov1_gross": "Großkredite (Mio. €)",
        "ov1_oprisk": "Operationelles Risiko (Mio. €)",
        "ov1_floor": "Aufschlag Output Floor nach Übergang (Mio. €)",
        "ov1_rwa": "RWA gesamt (Mio. €)",
    },
}

ZEITREIHE = "Zeitreihe 2021-2025"
# Langformat (zeitreihen/): HGB-Einzelreihen je Bank und Jahr, beliebig viele Jahre
ZEITREIHE_LANG = REPO / "zeitreihen/zeitreihe_lang.csv"
LANG_KENNZAHLEN = ("bilanzsumme", "eigenkapital", "fonds_340g", "jahresueberschuss")
# aufsichtliche Quartalsreihen (EBA-Hub, EU KM1): je Stichtag
QUARTAL_KENNZAHLEN = ("cet1_quote", "gk_quote", "leverage_ratio", "lcr", "nsfr")


GRUPPEN_LANG = REPO / "zeitreihen/gruppen_lang.csv"


def lade_gruppen(datei=GRUPPEN_LANG):
    """Bundesbank-Gruppenreihen: {kennzahl: {gruppe_id: {jahr: wert}}} (Jahresreihen, Stichtag 31.12.)."""
    out = {}
    if not Path(datei).exists():
        return out
    with open(datei, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            out.setdefault(r["kennzahl"], {}).setdefault(r["gruppe_id"], {})[r["stichtag"][:4]] = float(r["wert"])
    return out


def lade_lang(banken, datei=ZEITREIHE_LANG):
    """Legt je Bank `zr` = {kennzahl: {jahr: wert}} (HGB, Einzelabschluss) und `zq` = {kennzahl: {stichtag: wert}} (aufsichtlich) an."""
    if not Path(datei).exists():
        return
    nach_id = {b["id"]: b for b in banken if b.get("id")}
    with open(datei, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            b = nach_id.get(r["unternehmen_id"])
            if b is None:
                continue
            if r["kennzahl"] in LANG_KENNZAHLEN and r["rechnungslegung"] == "HGB":
                b.setdefault("zr", {}).setdefault(r["kennzahl"], {})[r["stichtag"][:4]] = float(r["wert"])
            elif r["kennzahl"] in QUARTAL_KENNZAHLEN and r["rechnungslegung"] == "aufsichtlich":
                b.setdefault("zq", {}).setdefault(r["kennzahl"], {})[r["stichtag"]] = float(r["wert"])
BILANZEN = "Bilanzen 31.12.2025"


def _zahl(v):
    """'n. v.', leere Zellen und Text -> None, sonst float."""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _wert(v):
    if isinstance(v, str):
        v = v.strip()
        return None if v in ("", "n. v.") else v
    return _zahl(v)


def _zeilen(ws):
    """Kopfzeile + Datenzeilen bis zur ersten Leerzeile (darunter folgen Gruppen-Tabellen)."""
    it = ws.iter_rows(values_only=True)
    kopf = [str(h).strip() if h is not None else "" for h in next(it)]
    for r in it:
        if r[0] is None:
            break
        yield dict(zip(kopf, r))


def _schluessel(z):
    return z.get("Bank")


def lade(excel=STANDARD_EXCEL):
    wb = openpyxl.load_workbook(excel, data_only=True, read_only=True)
    banken = {}

    for z in _zeilen(wb["Übersicht"]):
        banken[_schluessel(z)] = {"bank": z["Bank"], "gruppe": z["Gruppe"], "rolle": z["Rolle"]}

    for blatt, felder in FELDER.items():
        if blatt not in wb.sheetnames:
            continue
        for z in _zeilen(wb[blatt]):
            b = banken.setdefault(_schluessel(z), {"bank": z["Bank"], "gruppe": z["Gruppe"], "rolle": z["Rolle"]})
            for feld, spalte in felder.items():
                if spalte in z:
                    b[feld] = _wert(z[spalte])

    if ZEITREIHE in wb.sheetnames:
        for z in _zeilen(wb[ZEITREIHE]):
            b = banken.get(_schluessel(z))
            if b is None:
                continue
            zr = {}
            for spalte, v in z.items():
                m = re.match(r"(Bilanzsumme|Eigenkapital|Fonds § 340g|Jahresüberschuss) (\d{4}) \(Mio\. €\)", spalte)
                if m and _zahl(v) is not None:
                    zr.setdefault(m.group(1), {})[m.group(2)] = _zahl(v)
            b["zeitreihe"] = zr

    if BILANZEN in wb.sheetnames:
        for z in _zeilen(wb[BILANZEN]):
            b = banken.get(_schluessel(z))
            if b is None:
                continue
            seite, aktiva, passiva = "aktiva", {}, {}
            for spalte, v in z.items():
                if spalte in ("Gruppe", "Rolle", "Bank"):
                    continue
                if spalte == "Summe der Aktiva":
                    seite = "passiva"
                    continue
                if spalte == "Summe der Passiva":
                    break
                (aktiva if seite == "aktiva" else passiva)[spalte] = _zahl(v)
            if any(v for v in aktiva.values()):
                b["bilanz"] = {"aktiva": aktiva, "passiva": passiva}

    liste = list(banken.values())
    reg = stamm.lade()
    unbekannt = []
    for b in liste:   # Median- und Kopfzeilen der Gruppentabellen haben keine Gruppe und keine ID
        b["id"] = reg.aufloesen(b["bank"])
        if b["id"] is None and b.get("gruppe") not in (None, "Gruppe"):
            unbekannt.append(b["bank"])
    if unbekannt:
        raise SystemExit("Banken nicht in stammdaten/unternehmen_ids.csv: " + "; ".join(unbekannt))
    liste = [b for b in liste if b["id"]]
    lade_lang(liste)
    return liste


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--excel", default=STANDARD_EXCEL)
    p.add_argument("--out", default=Path(__file__).parent / "data/banken.json")
    a = p.parse_args()
    banken = lade(a.excel)
    meta = {"quelle": str(Path(a.excel).relative_to(REPO)) if Path(a.excel).is_relative_to(REPO) else str(a.excel),
            "stichtag": "2025-12-31", "anzahl": len(banken)}
    Path(a.out).write_text(json.dumps({"meta": meta, "banken": banken}, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(banken)} Banken -> {a.out}")


if __name__ == "__main__":
    main()
