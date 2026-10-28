"""SEC-EDGAR-Adapter (Companyfacts, XBRL). Erst Rohantwort sichern, dann extrahieren, dann normalisieren, dann in einer Transaktion schreiben.

Quelle: https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json (Dokumentation: https://www.sec.gov/edgar/sec-api-documentation).
Je Filing (accession) und Periodenende entsteht eine eigene Fassung; berichtigte Abschlüsse (10-K/A) bleiben neben dem Original erhalten.
Companyfacts enthält nicht jede unternehmensspezifische Erweiterung der Taxonomie: fehlende Werte werden nicht ergänzt.
"""
import json
import re
from datetime import date
from decimal import Decimal

import ingest
from httpsafe import AbrufFehler, SichererClient, atomar_speichern
from international_core import periode_klasse

HOST = "data.sec.gov"
ANBIETER = "sec-companyfacts"
MAPPING_VERSION = "sec-v1"
JAHRESFORMULARE = {"10-K", "10-K/A", "10-KT", "10-KT/A", "20-F", "20-F/A", "40-F", "40-F/A"}

# metric_code -> Taxonomie-Tag. Weitere Kennzahlen erst nach fachlichem Fixture und Abgleich mit dem Originalbericht aufnehmen.
MAPPING = {
    "assets": {"taxonomy": "us-gaap", "tag": "Assets", "period": "instant", "unit": "USD"},
}


def cik_normalisieren(cik) -> str:
    s = str(cik).strip()
    if not re.fullmatch(r"\d{1,10}", s):
        raise ValueError(f"CIK muss numerisch mit höchstens 10 Stellen sein: {cik!r}")
    return s.zfill(10)


def companyfacts_url(cik) -> str:
    return f"https://{HOST}/api/xbrl/companyfacts/CIK{cik_normalisieren(cik)}.json"


def abrufen(client: SichererClient, cik, speicher_verzeichnis):
    """Lädt die Rohantwort, prüft sie als JSON und speichert sie atomar. Gibt (pfad, sha256, bytes) zurück."""
    url = companyfacts_url(cik)
    daten = client.holen(url)
    try:
        j = json.loads(daten)
    except ValueError as e:
        raise AbrufFehler("Antwort ist kein JSON") from e
    if str(j.get("cik")).zfill(10) != cik_normalisieren(cik):
        raise AbrufFehler("CIK in der Antwort passt nicht zur Anfrage")
    # Dateiname enthält den Hash, damit jede abweichende Antwort als eigener Beleg erhalten bleibt
    import hashlib
    h = hashlib.sha256(daten).hexdigest()
    pfad, h2 = atomar_speichern(speicher_verzeichnis, f"CIK{cik_normalisieren(cik)}_{h[:16]}.json", daten)
    return pfad, h2, len(daten)


def extrahieren(rohdaten: dict, mapping=MAPPING):
    """Alle Einträge der gemappten Tags aus Jahresformularen, unverändert und mit allen Kontextangaben."""
    ausgabe = []
    for metric, m in mapping.items():
        knoten = rohdaten.get("facts", {}).get(m["taxonomy"], {}).get(m["tag"])
        if not knoten:
            continue
        for einheit, eintraege in knoten.get("units", {}).items():
            if einheit != m["unit"]:
                continue   # andere Einheiten (z. B. Aktien) bleiben im Rohbeleg, werden nicht gemappt
            for e in eintraege:
                if e.get("form") in JAHRESFORMULARE:
                    ausgabe.append({"metric": metric, "taxonomy": m["taxonomy"], "tag": m["tag"], "unit": einheit, **e})
    return ausgabe


def normalisieren(eintraege, entity_id, source_id):
    """Fakt-Zeilen für international.fact. Duplikate innerhalb desselben Filings und Periodenendes werden einmal geführt;
    widersprüchliche Werte im selben Filing ergeben einen Fehler statt stiller Auswahl."""
    zeilen, gesehen = [], {}
    for e in eintraege:
        end = date.fromisoformat(e["end"])
        start = date.fromisoformat(e["start"]) if e.get("start") else None
        m = MAPPING[e["metric"]]
        if (m["period"] == "instant") != (start is None):
            continue                   # Periodentyp passt nicht zum Tag (z. B. Dauer statt Stichtag): nicht mappen
        if start is not None and periode_klasse(start, end) != "annual":
            continue                   # nur Jahresperioden
        wert = Decimal(str(e["val"]))
        schluessel = f"{e['taxonomy']}:{e['tag']}|{e['unit']}|{e['accn']}|{e.get('start') or ''}|{e['end']}"
        if schluessel in gesehen:
            if gesehen[schluessel] != wert:
                raise ValueError(f"Widerspruch im selben Filing: {schluessel}")
            continue
        gesehen[schluessel] = wert
        zeilen.append({
            "entity_id": entity_id, "metric_code": e["metric"],
            "period_start": start, "period_end": end,
            "value": wert, "unit": e["unit"],
            "accounting_standard": "US-GAAP" if e["taxonomy"] == "us-gaap" else e["taxonomy"],
            "consolidation": "unknown",    # Companyfacts nennt den Konsolidierungskreis nicht; Konzernabschluss ist bei 10-K üblich, aber nicht belegt
            "dimensions": {},
            "source_id": source_id, "source_fact_key": schluessel, "mapping_version": MAPPING_VERSION,
            "quality": "raw",
            "reported_at": date.fromisoformat(e["filed"]) if e.get("filed") else None,
            "provenance": {"form": e.get("form"), "accn": e["accn"], "fy": e.get("fy"), "fp": e.get("fp"), "frame": e.get("frame"),
                           "filed": e.get("filed"), "tag": f"{e['taxonomy']}:{e['tag']}", "originalwert": e["val"], "skalierung": 1},
        })
    return zeilen


def importieren(conn, rohdatei, sha256, entity_id, cik, dry_run=False, object_key=None):
    """Schreibt die Companyfacts einer Rohdatei in die Datenbank. Gibt (neu, vorhanden) zurück."""
    with open(rohdatei, "rb") as f:
        roh = json.loads(f.read())
    if str(roh.get("cik")).zfill(10) != cik_normalisieren(cik):
        raise ValueError("CIK der Rohdatei passt nicht")
    neu = alt = 0
    with ingest.ingestion_lauf(conn, "sec-companyfacts", dry_run=dry_run) as lauf:
        conn.execute("INSERT INTO international.identifier (scheme, value, entity_id) VALUES ('CIK', %s, %s) ON CONFLICT DO NOTHING",
                     (cik_normalisieren(cik), entity_id))
        sid = ingest.quelle_registrieren(conn, ANBIETER, cik_normalisieren(cik), companyfacts_url(cik), sha256,
                                         object_key or str(rohdatei))
        for z in normalisieren(extrahieren(roh), entity_id, sid):
            if ingest.fakt_einfuegen(conn, z):
                neu += 1
            else:
                alt += 1
        lauf.anzahl = neu
        lauf.wasserzeichen = {"cik": cik_normalisieren(cik), "sha256": sha256}
    return neu, alt


if __name__ == "__main__":
    import argparse
    import db
    ap = argparse.ArgumentParser(description="SEC-Companyfacts einer Gesellschaft laden und importieren (Live-Abruf, rate-limitiert)")
    ap.add_argument("--cik", required=True)
    ap.add_argument("--entity", required=True, help="zentrale Unternehmens-ID, z. B. U000021 (muss in international.entity vorhanden sein)")
    ap.add_argument("--speicher", default=str(db.HIER / "objektspeicher" / "sec"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    pfad, h, n = abrufen(SichererClient({HOST}), a.cik, a.speicher)
    print(f"Rohantwort: {pfad} ({n} Bytes, sha256 {h})")
    with db.verbinden() as c:
        db.migrieren(c)
        neu, alt = importieren(c, pfad, h, a.entity, a.cik, dry_run=a.dry_run)
        print(f"neu: {neu}, schon vorhanden: {alt}" + (" (Dry-Run, zurückgerollt)" if a.dry_run else ""))
