"""Unternehmensprofile aus app/data/unternehmen.json in die Datenbank (Revision 0003).

unternehmen.json entsteht im Build (app/unternehmen.py: Branchenmappen, Bilanzvergleich, Börsendaten, Governance, Dokumente,
Termine) und liegt im Repo. Der Import übernimmt diesen Stand unverändert:

* Kennzahlenwerte (werte)            -> company_profile_value (ein Wert je Unternehmen und Kennzahl)
* Abschlussposten (abschluesse)      -> financial_statement + financial_statement_line (Reihenfolge wie geliefert)
* Kopfangaben, Zeitreihen, Gremien, Dokumente, Termine -> company_profile (jsonb, Felder wie im Terminal)

Ein Lauf ersetzt den vorigen Stand vollständig in einer Transaktion (ingestion_run „profile“). Schlägt er fehl, bleibt der alte
Stand. Ist die Datei unverändert (gleiche SHA-256 wie der aktuelle Stand), passiert nichts. IDs werden nicht vergeben: Unternehmen,
deren ID nicht als Entität existiert, werden gezählt und übersprungen.
"""
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATEI = REPO / "app" / "data" / "unternehmen.json"
BLOB = "https://github.com/chillkrote/Unternehmenskennzahlen/blob/main/"

# Felder, die eigene Spalten oder Tabellen haben; alles Übrige eines Unternehmens landet in attributes
from plattform.lizenz import YAHOO_WERTE, firma_ohne_yahoo_abschluesse, mit_yahoo, ohne_yahoo_abschluesse  # noqa: E402

EIGENE = {"id", "name", "branche", "gruppe", "notiert", "werte", "abschluesse", "reihen", "gov", "dokumente", "termine"}
TEILE = ("bilanz", "guv")


def _zahl(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None


def lesen(pfad=DATEI):
    roh = Path(pfad).read_bytes()
    return json.loads(roh), hashlib.sha256(roh).hexdigest()


def importieren(conn, dry_run=False, pfad=DATEI, erzwingen=False):
    import ingest
    bericht = Counter()
    d, sha = lesen(pfad)
    alt = conn.execute("SELECT file_sha256 FROM international.profile_snapshot WHERE is_current").fetchone()
    if alt and alt[0] == sha and not erzwingen:
        bericht["unveraendert"] = 1
        return bericht
    try:
        rel = str(Path(pfad).resolve().relative_to(REPO))
    except ValueError:
        rel = str(pfad)
    with ingest.ingestion_lauf(conn, "profile", dry_run=dry_run) as lauf:
        sid = ingest.quelle_registrieren(conn, "repo-unternehmen", rel + "@" + sha[:12], BLOB + rel, sha, rel,
                                         rights_status="Build-Stand aus den Quellen in quellen[] (Lizenz je Quelle: docs/datenquellen.md)")
        # alter Stand weg (Werte, Abschlüsse und Posten hängen mit ON DELETE CASCADE am Profil)
        conn.execute("DELETE FROM international.company_profile")
        conn.execute("DELETE FROM international.profile_metric")
        conn.execute("UPDATE international.profile_snapshot SET is_current = false WHERE is_current")
        snap = conn.execute(
            "INSERT INTO international.profile_snapshot (source_id, run_id, file_sha256, sources, sectors, groups, alt_ids, demo, is_current) "
            "VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s::jsonb,%s,true) RETURNING id",
            (sid, lauf.run_id, sha, d.get("quellen") or [], json.dumps(d.get("branchen") or [], ensure_ascii=False),
             d.get("gruppen") or [], json.dumps(d.get("alt_ids") or {}), bool(d.get("demo")))).fetchone()[0]
        # E1: Kurse und kursabhängige Kennzahlen aus Yahoo nicht in die Server-Datenbank (plattform/lizenz.py)
        gesperrt = set() if mit_yahoo() else set(YAHOO_WERTE)
        # E6 (offen): mit SPHAERAE_OHNE_YAHOO_ABSCHLUESSE=1 auch keine Yahoo-Abschlüsse, daraus abgeleitete Kennzahlen und Yahoo-Termine
        streng = ohne_yahoo_abschluesse() and not mit_yahoo()
        for i, k in enumerate(k for k in d.get("kennzahlen") or [] if k["key"] not in gesperrt):
            conn.execute(
                "INSERT INTO international.profile_metric (code, name, unit, fmt, metric_group, higher_is_better, help, aliases, position) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (k["key"], k.get("name") or k["key"], k.get("einheit"), k.get("fmt"), k.get("gruppe"), k.get("hoch"), k.get("hilfe"),
                 k.get("aliase") or [], i))
        katalog = {k["key"] for k in d.get("kennzahlen") or []}
        vorhanden = {r[0] for r in conn.execute("SELECT id FROM international.entity")}
        zeilen = []
        for pos, f in enumerate(d.get("unternehmen") or []):
            if f["id"] not in vorhanden:
                bericht["ohne_entitaet"] += 1
                continue
            if streng:
                vorher = (len(f.get("abschluesse") or []), len(f.get("werte") or {}), len(f.get("termine") or []))
                f = firma_ohne_yahoo_abschluesse(f)
                bericht["abschluesse_gesperrt"] += vorher[0] - len(f.get("abschluesse") or [])
                bericht["werte_gesperrt"] += vorher[1] - len(f.get("werte") or {})
                bericht["termine_gesperrt"] += vorher[2] - len(f.get("termine") or [])
            attrs = {k: v for k, v in f.items() if k not in EIGENE}
            conn.execute(
                "INSERT INTO international.company_profile (entity_id, snapshot_id, name, sector, peer_group, listed, position, attributes, "
                "series, governance, documents, report_dates) VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb)",
                (f["id"], snap, f["name"], f["branche"], f.get("gruppe"), bool(f.get("notiert")), pos, json.dumps(attrs, ensure_ascii=False),
                 json.dumps(f.get("reihen") or {}, ensure_ascii=False), json.dumps(f["gov"], ensure_ascii=False) if f.get("gov") else None,
                 json.dumps(f.get("dokumente") or [], ensure_ascii=False), json.dumps(f.get("termine") or [], ensure_ascii=False)))
            bericht["profile"] += 1
            for k, v in (f.get("werte") or {}).items():
                z = _zahl(v)
                if z is None:
                    bericht["werte_ohne_zahl"] += 1
                    continue
                if k in gesperrt:
                    bericht["werte_gesperrt"] += 1
                    continue
                if k not in katalog:
                    bericht["werte_ohne_katalog"] += 1
                    continue
                zeilen.append((f["id"], k, z))
            for apos, a in enumerate(f.get("abschluesse") or []):
                st = conn.execute(
                    "INSERT INTO international.financial_statement (entity_id, position, period_end, fiscal_year, currency, source, source_url, "
                    "fetched, status, part_sources) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb) RETURNING id",
                    (f["id"], apos, a["ende"], a["jahr"], a.get("waehrung") or "", a.get("quelle"), a.get("quelle_url"), a.get("abruf"),
                     a.get("status"), json.dumps(a.get("quellen") or {}, ensure_ascii=False))).fetchone()[0]
                bericht["abschluesse"] += 1
                with conn.cursor().copy("COPY international.financial_statement_line (statement_id, part, position, label, value) FROM STDIN") as cp:
                    for teil in TEILE:
                        for lpos, (label, v) in enumerate((a.get(teil) or {}).items()):
                            cp.write_row((st, teil, lpos, label, _zahl(v)))
                            bericht["posten"] += 1
        with conn.cursor().copy("COPY international.company_profile_value (entity_id, metric_code, value) FROM STDIN") as cp:
            for z in zeilen:
                cp.write_row(z)
        bericht["werte"] = len(zeilen)
        lauf.anzahl = len(zeilen) + bericht["posten"]
        lauf.wasserzeichen = {"unternehmen_sha256": sha, "profile": bericht["profile"]}
    for t in ("company_profile", "company_profile_value", "financial_statement", "financial_statement_line"):
        conn.execute(f"ANALYZE international.{t}")
    return bericht
