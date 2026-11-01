"""Gleicht die importierten ESEF-Werte mit dem veröffentlichten Berichtsdokument (iXBRL/XHTML der Einreichung) ab.

Je Unternehmen, Kennzahl und jüngster Periode der jüngsten Einreichung wird die im Dokument sichtbar ausgewiesene Zahl (ix:nonFraction mit
Skalierung und Vorzeichen) für dasselbe Konzept und denselben Zeitraum gelesen und mit dem Datenbankwert verglichen. Nur 'gleich' zählt als bestätigt.
Aufruf: INTERNATIONAL_USER_AGENT=... INTERNATIONAL_DATABASE_URL=... python3 international/verify_fr.py
"""
import csv
import sys
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
import db  # noqa: E402
import esef  # noqa: E402
from httpsafe import SichererClient, atomar_speichern  # noqa: E402

IX = "{http://www.xbrl.org/2013/inlineXBRL}"
XBRLI = "{http://www.xbrl.org/2003/instance}"
XBRLDI = "{http://xbrl.org/2006/xbrldi}"


def anzeige_zahl(text, fmt):
    """Sichtbare Zahl -> Decimal (None, wenn nicht eindeutig lesbar). Unterstützt die gebräuchlichen ixt-Formate."""
    t = (text or "").strip().replace("\xa0", " ")
    fmt = (fmt or "").split(":")[-1].lower()
    if fmt in ("zerodash", "fixed-zero", "zerodash"):
        return Decimal(0)
    if "comma" in fmt:              # 1.234,56 / 1 234,56
        t = t.replace(".", "").replace(" ", "").replace(",", ".")
    else:                           # 1,234.56 / 1 234.56
        t = t.replace(",", "").replace(" ", "")
    try:
        return Decimal(t)
    except Exception:
        return None


def lies_dokument(daten: bytes):
    """-> {(konzept, beginn, ende): set(werte)} nur für dimensionslose Kontexte."""
    kontexte, fakten = {}, []
    for ereignis, el in ET.iterparse(BytesIO(daten), events=("end",)):
        if el.tag == XBRLI + "context":
            if el.find(f".//{XBRLDI}explicitMember") is not None or el.find(f".//{XBRLI}segment") is not None or el.find(f".//{XBRLI}scenario") is not None:
                kontexte[el.get("id")] = None
            else:
                inst, a, b = el.find(f".//{XBRLI}instant"), el.find(f".//{XBRLI}startDate"), el.find(f".//{XBRLI}endDate")
                if inst is not None:
                    kontexte[el.get("id")] = (None, date.fromisoformat(inst.text.strip()[:10]))
                elif a is not None and b is not None:
                    kontexte[el.get("id")] = (date.fromisoformat(a.text.strip()[:10]), date.fromisoformat(b.text.strip()[:10]))
        elif el.tag == IX + "nonFraction":
            fakten.append((el.get("name"), el.get("contextRef"), el.get("scale"), el.get("sign"), el.get("format"), "".join(el.itertext()), el.get("{http://www.w3.org/2001/XMLSchema-instance}nil")))
    ergebnis = {}
    for name, ctx, scale, sign, fmt, text, nil in fakten:
        per = kontexte.get(ctx)
        if per is None or nil == "true":
            continue
        z = anzeige_zahl(text, fmt)
        if z is None:
            continue
        z = z * (Decimal(10) ** int(scale or 0))
        if sign == "-":
            z = -z
        ergebnis.setdefault((name, per[0], per[1]), set()).add(z)
    return ergebnis


def main():
    client = SichererClient(esef.HOSTS | {"filings.xbrl.org"}, max_bytes=80_000_000, timeout=180)
    ausgabe = []
    with db.verbinden() as conn:
        ents = conn.execute("SELECT e.id, e.legal_name, e.lei FROM international.entity e WHERE e.lei IS NOT NULL AND EXISTS "
                            "(SELECT 1 FROM international.fact f WHERE f.entity_id=e.id AND f.provenance ? 'fxo_id') ORDER BY e.id").fetchall()
        for uid, name, lei in ents:
            fxo = conn.execute("SELECT provenance->>'fxo_id' FROM international.fact WHERE entity_id=%s AND provenance ? 'fxo_id' "
                               "GROUP BY 1 ORDER BY max(period_end) DESC, 1 DESC LIMIT 1", (uid,)).fetchone()[0]
            einr = next(e for e in esef.einreichungen(client, lei) if e["attributes"]["fxo_id"] == fxo)
            url = esef.INDEX + einr["attributes"]["report_url"]
            pfad = HIER / "objektspeicher" / "esef" / "berichte" / (fxo.replace("/", "_") + ".xhtml")
            if not pfad.exists():
                atomar_speichern(pfad.parent, pfad.name, client.holen(url))
            dok = lies_dokument(pfad.read_bytes())
            for metric, m in esef.MAPPING.items():
                z = conn.execute("SELECT value, period_start, period_end, provenance->>'concept' FROM international.fact WHERE entity_id=%s AND metric_code=%s "
                                 "AND provenance->>'fxo_id'=%s ORDER BY period_end DESC LIMIT 1", (uid, metric, fxo)).fetchone()
                if not z:
                    continue
                wert, beginn, ende, konzept = z
                gefunden = dok.get((konzept, beginn, ende))
                status = "nicht_gefunden" if not gefunden else ("gleich" if wert in gefunden else "abweichung")
                ausgabe.append([uid, name, metric, konzept, f"{beginn or ''}..{ende}", wert, ";".join(str(x) for x in sorted(gefunden or [])), fxo, status, date.today().isoformat()])
            print(uid, name, "geprüft", flush=True)
    with open(HIER / "pruefung_fr.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["unternehmen_id", "name", "kennzahl", "ifrs_konzept", "periode", "wert_datenbank", "wert_dokument", "einreichung", "status", "geprueft_am"])
        w.writerows(ausgabe)
    from collections import Counter
    print(Counter(a[8] for a in ausgabe))


if __name__ == "__main__":
    main()
