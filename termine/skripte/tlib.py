"""Gemeinsame Hilfen für die Berichtstermine: Pfade, Unternehmensliste, termine.csv lesen/schreiben, Periode ableiten."""
import calendar
import csv
import json
import re
import unicodedata
from datetime import date, timedelta
import sys
from pathlib import Path

TERMINE = Path(__file__).resolve().parent.parent
REPO = TERMINE.parent
sys.path.insert(0, str(REPO / "stammdaten"))
import ids  # noqa: E402  zentrale Unternehmens-IDs (stammdaten/)

UNIVERSUM = REPO / "boersennotierte-unternehmen" / "universum" / "universum.csv"
YAHOO_ROH = REPO / "boersennotierte-unternehmen" / "rohdaten" / "yahoo"
TICKER_BANKEN = REPO / "app" / "boersen_ticker.json"
BANKEN_JSON = REPO / "app" / "data" / "banken.json"
CSV_PFAD = TERMINE / "termine.csv"
MANUELL = TERMINE / "termine_manuell.csv"
QUELLEN_FK = TERMINE / "finanzkalender_quellen.csv"

KOPF = ["unternehmen_id", "name", "branche", "ticker", "berichtsart", "periode_ende", "termin", "quelle", "quelle_url",
        "status", "stand", "abruf_status", "versuche", "datei", "sha256", "hinweis"]
# Rangfolge der Quellen: bei gleichem Bericht gewinnt die höhere
RANG = {"yahoo": 1, "finanzkalender": 2, "manuell": 3}
BERICHTSARTEN = {0: "Jahresbericht", 1: "Q1-Bericht", 2: "Halbjahresbericht", 3: "Q3-Bericht"}


def lese_csv(pfad):
    if not Path(pfad).exists():
        return []
    with open(pfad, encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "").strip() for k, v in r.items() if k} for r in csv.DictReader(f, delimiter=";")]


def schreibe_termine(zeilen):
    zeilen = sorted(zeilen, key=lambda z: (z["termin"], z["unternehmen_id"], z["periode_ende"]))
    with open(CSV_PFAD, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, KOPF, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(zeilen)


def unternehmen():
    """{id: {name, branche, ticker, ordner}}: Börsenunternehmen (Yahoo-Ticker) und selbst notierte Banken."""
    out = {}
    for u in lese_csv(UNIVERSUM):
        if u.get("yahoo"):
            out[u["unternehmen_id"]] = {"name": u["name"], "branche": u["branche"], "ticker": u["yahoo"], "isin": u["isin_haupt"],
                                        "website": u.get("website", ""), "ordner": f"boersennotierte-unternehmen/{u['branche']}/dokumente",
                                        "ordner_name": ids.lade().ordner(u["unternehmen_id"])}
    if TICKER_BANKEN.exists() and BANKEN_JSON.exists():
        namen = [(b["id"], b["bank"]) for b in json.loads(BANKEN_JSON.read_text(encoding="utf-8"))["banken"] if b.get("bank") and b.get("id")]
        for t in json.loads(TICKER_BANKEN.read_text(encoding="utf-8"))["ticker"]:
            if t.get("ebene") != "Institut":
                continue
            if any(v["ticker"].split(".")[0] == t["ticker"].split(".")[0] for v in out.values()):
                continue  # schon als Börsenunternehmen im Universum; das Terminal überträgt die Termine über den Ticker auf die Bankseite
            for uid, n in namen:
                if re.search(t["muster"], n):
                    out[uid] = {"name": n, "branche": "banken", "ticker": t["ticker"], "isin": "", "website": "",
                                "ordner": "banken/unterjahr/dokumente", "ordner_name": ids.lade().ordner(uid)}
    return out


def geschaeftsjahresende_monat(uid, isin):
    """Monat des Geschäftsjahresendes aus den Yahoo-Rohdaten (lastFiscalYearEnd); sonst 12."""
    p = YAHOO_ROH / f"{isin}.json"
    try:
        ts = json.loads(p.read_text(encoding="utf-8"))["info"]["lastFiscalYearEnd"]
        return date.fromtimestamp(ts).month if ts else 12
    except Exception:
        return 12


def periode(termin, fye_monat):
    """Welche Periode wird an diesem Termin berichtet? Das jüngste Quartalsende, das mindestens 14 Tage zurückliegt.
    Rückgabe (Periodenende, Berichtsart)."""
    for rueck in range(0, 12):
        m = (termin.month - 1 - rueck) % 12 + 1
        j = termin.year - ((rueck - termin.month + 1 + 11) // 12 if rueck >= termin.month else 0)
        if (m - fye_monat) % 3:
            continue
        ende = date(j, m, calendar.monthrange(j, m)[1])
        if (termin - ende).days >= 14:
            return ende, BERICHTSARTEN[((m - fye_monat) % 12) // 3]
    return None, "Bericht"
