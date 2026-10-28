"""Vergleichsexport: versionierter JSON-Export im bisherigen deutschen Schema (zeitreihe_lang.csv) plus Sitzland, Rechnungslegungsstandard,
Währung, Konsolidierungskreis und Vergleichsgruppe. Datenquelle ist die Sicht international.fact_as_of (aktueller Stand oder 'bekannt zum').

Vergleichsregel: Werte dürfen nur innerhalb derselben vergleichsgruppe (Kennzahl|Währung|Rechnungslegung|Kreis) in Mediane oder Ränge eingehen.
Geldwerte stehen in Mio. der Originalwährung; es gibt keine Umrechnung ohne dokumentierten Kurs (siehe international_core.stichtagskurs).
Aufruf: INTERNATIONAL_DATABASE_URL=... python3 international/export_vergleich.py [--as-of 2026-10-28] [--out pfad.json]
"""
import argparse
import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
import db  # noqa: E402
from import_de import KENNZAHL  # noqa: E402

SCHEMA_VERSION = "vergleich-v1"
DEUTSCH = {v: k for k, v in KENNZAHL.items()}
DEUTSCH.update({"revenue": "umsatz", "operating_cash_flow": "operativer_cashflow", "employees": "mitarbeiter"})
KREIS = {"solo": "Einzel", "group": "Konzern", "regulatory": "aufsichtlich", "unknown": "unbekannt"}

SQL = """
SELECT f.entity_id, e.legal_name, e.domicile, f.metric_code, f.period_start, f.period_end, f.value, f.unit,
       f.accounting_standard, f.consolidation, f.dimensions, f.quality, f.reported_at, f.provenance, s.url
  FROM international.fact_as_of(%s) f
  JOIN international.entity e ON e.id = f.entity_id
  JOIN international.source_document s ON s.id = f.source_id
 ORDER BY f.entity_id, f.metric_code, f.period_end, f.accounting_standard, f.consolidation
"""


def zeile(r):
    (uid, name, sitz, metric, start, end, wert, unit, std, kreis, dim, qual, gemeldet, prov, url) = r
    geld = unit not in ("ratio", "count")
    anzeige = float(Decimal(wert) / Decimal(1_000_000)) if geld else float(wert)
    kz = DEUTSCH.get(metric, metric)
    waehrung = unit if geld else None
    ebene = (dim or {}).get("ebene_laut_quelle") or KREIS[kreis]
    return {
        "unternehmen_id": uid, "name": name, "sitzland": sitz, "boersenland": None,
        "kennzahl": kz, "stichtag": end.isoformat(), "periode_beginn": start.isoformat() if start else None,
        "wert": anzeige, "einheit": f"Mio. {unit}" if geld else ("Anteil" if unit == "ratio" else "Anzahl"), "waehrung": waehrung,
        "rechnungslegung": (prov or {}).get("rechnungslegung") or std, "standard": std,
        "ebene": ebene, "kreis": kreis, "pruefstatus": (prov or {}).get("pruefstatus") or qual, "qualitaet": qual,
        "bekannt_seit": gemeldet.isoformat() if gemeldet else None, "quelle": url,
        "vergleichsgruppe": f"{kz}|{waehrung or '-'}|{(prov or {}).get('rechnungslegung') or std}|{kreis}",
    }


def exportieren(conn, as_of: date | None = None):
    zeilen = [zeile(r) for r in conn.execute(SQL, (as_of,)).fetchall()]
    return {
        "schema_version": SCHEMA_VERSION,
        "erzeugt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bekannt_zum": as_of.isoformat() if as_of else None,
        "anzahl": len(zeilen),
        "vergleichsregel": "Mediane und Ränge nur innerhalb derselben vergleichsgruppe; keine stille Währungsumrechnung",
        "zeilen": zeilen,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", type=date.fromisoformat)
    ap.add_argument("--out", default=str(HIER / "export" / f"{SCHEMA_VERSION}.json"))
    a = ap.parse_args()
    with db.verbinden() as c:
        daten = exportieren(c, a.as_of)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".teil")
    tmp.write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(out)
    print(f"{daten['anzahl']} Zeilen -> {out}")
