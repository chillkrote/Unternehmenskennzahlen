"""Gemeinsamer Schreibpfad der Adapter: Quelle registrieren, Fakten idempotent einfügen, Lauf mit Wasserzeichen.

Ablauf eines Laufs: Fakten in EINER Transaktion einfügen und committen, erst danach Lauf als 'ok' markieren und das Wasserzeichen setzen.
Bricht der Lauf ab, wird nichts veröffentlicht und das Wasserzeichen bleibt unverändert; ein erneuter Lauf ist durch die
Eindeutigkeit (source_id, source_fact_key, mapping_version) und den SHA-256 der Quelle idempotent.
"""
import json
from contextlib import contextmanager


def quelle_registrieren(conn, provider, external_id, url, sha256, object_key, published_at=None, rights_status="unverified"):
    return conn.execute(
        "INSERT INTO international.source_document (provider, external_id, url, sha256, object_key, published_at, rights_status) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (provider, external_id, sha256) DO UPDATE SET url = EXCLUDED.url RETURNING id",
        (provider, external_id, url, sha256, object_key, published_at, rights_status)).fetchone()[0]


FAKT_SQL = (
    "INSERT INTO international.fact (entity_id, metric_code, period_start, period_end, value, unit, accounting_standard, consolidation, "
    "dimensions, source_id, source_fact_key, mapping_version, quality, reported_at, provenance) "
    "VALUES (%(entity_id)s,%(metric_code)s,%(period_start)s,%(period_end)s,%(value)s,%(unit)s,%(accounting_standard)s,%(consolidation)s,"
    "%(dimensions)s::jsonb,%(source_id)s,%(source_fact_key)s,%(mapping_version)s,%(quality)s,%(reported_at)s,%(provenance)s::jsonb) "
    "ON CONFLICT (source_id, source_fact_key, mapping_version) DO NOTHING")


def fakt_einfuegen(conn, f):
    """Gibt True zurück, wenn neu eingefügt, False bei bereits vorhandenem Fakt."""
    p = dict(f)
    p["dimensions"] = json.dumps(p.get("dimensions") or {}, sort_keys=True)
    p["provenance"] = json.dumps(p.get("provenance") or {}, sort_keys=True, default=str)
    p.setdefault("reported_at", None)
    return conn.execute(FAKT_SQL, p).rowcount == 1


class Lauf:
    def __init__(self, run_id):
        self.run_id = run_id
        self.anzahl = 0
        self.wasserzeichen = None


@contextmanager
def ingestion_lauf(conn, adapter, dry_run=False):
    """with ingestion_lauf(conn, 'sec') as lauf: ... fakt_einfuegen(conn, ...); lauf.anzahl += 1
    dry_run=True führt alles aus und rollt am Ende zurück (inklusive Laufprotokoll)."""
    if dry_run:
        try:
            with conn.transaction():
                run_id = conn.execute("INSERT INTO international.ingestion_run (adapter, status) VALUES (%s,'running') RETURNING id", (adapter,)).fetchone()[0]
                lauf = Lauf(run_id)
                yield lauf
                raise _Rollback()          # alles verwerfen, auch das Laufprotokoll
        except _Rollback:
            return
    run_id = conn.execute("INSERT INTO international.ingestion_run (adapter, status) VALUES (%s,'running') RETURNING id", (adapter,)).fetchone()[0]
    lauf = Lauf(run_id)
    try:
        with conn.transaction():
            yield lauf
    except BaseException as e:
        conn.execute("UPDATE international.ingestion_run SET status='failed', finished_at=now(), error_details=%s::jsonb WHERE id=%s",
                     (json.dumps({"fehler": repr(e)[:2000]}), run_id))
        raise
    conn.execute("UPDATE international.ingestion_run SET status='ok', finished_at=now(), imported_count=%s, watermark=%s::jsonb WHERE id=%s",
                 (lauf.anzahl, json.dumps(lauf.wasserzeichen) if lauf.wasserzeichen is not None else None, run_id))


class _Rollback(Exception):
    pass
