"""VWL-Reihen aus volkswirtschaft/ in die Datenbank (Revision 0004), mit Vintage.

Liest mit derselben Funktion wie der Build (app/vwl.py: lade), damit Datenbank und Seite dieselben Werte haben:
serien.csv -> series, zeitreihe_lang.csv -> observation.

Vintage: Ein Wert, der sich gegenüber dem aktuellen Stand ändert, bekommt eine neue Zeile; die alte endet mit valid_to = Zeitpunkt
des Imports. Ein Wert, der in der Quelldatei fehlt, endet ebenso (wird nicht gelöscht). Unveränderte Werte bleiben unberührt.
Alles in einer Transaktion (ingestion_run „vwl“); ist die Datei unverändert, passiert nichts.

Was die Fassungen bedeuten (Audit 2026-11, 4.4): valid_from/valid_to sind Erfassungszeitpunkte dieses Imports (Datenbankstand).
Die Historie beginnt mit dem ersten Import; frühere Veröffentlichungsstände der Quelle werden nicht rekonstruiert. Je neuer
Fassung werden zusätzlich der Stand der Quelle (source_updated = stand_quelle) und das Abrufdatum (fetched) festgehalten.
"""
import hashlib
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ORDNER = REPO / "volkswirtschaft"
BLOB = "https://github.com/chillkrote/Unternehmenskennzahlen/blob/main/"
SPALTEN = {"thema": "topic", "name": "name", "einheit": "unit", "format": "fmt", "art": "kind", "frequenz": "frequency",
           "quelle": "provider", "datensatz": "dataset", "filter": "filter", "url": "url", "abruf": "fetched", "prognose_ab": "forecast_from",
           "hinweis": "note"}


def _sha(*pfade):
    h = hashlib.sha256()
    for p in pfade:
        h.update(Path(p).read_bytes())
    return h.hexdigest()


def importieren(conn, dry_run=False, erzwingen=False, ordner=ORDNER):
    import json

    import ingest
    import vwl as vwl_build                       # app/vwl.py (sys.path wie in etl.laden)
    bericht = Counter()
    ordner = Path(ordner)
    csv_s, csv_z = ordner / "serien.csv", ordner / "zeitreihe_lang.csv"
    if not csv_s.exists() or not csv_z.exists():
        bericht["keine_dateien"] = 1
        return bericht
    sha = _sha(csv_s, csv_z)
    alt = conn.execute("SELECT watermark->>'sha256' FROM international.ingestion_run WHERE adapter = 'vwl' AND status = 'ok' "
                       "ORDER BY id DESC LIMIT 1").fetchone()
    if alt and alt[0] == sha and not erzwingen:
        bericht["unveraendert"] = 1
        return bericht
    vorher, vwl_build.ORDNER = vwl_build.ORDNER, ordner
    try:
        d = vwl_build.lade()
    finally:
        vwl_build.ORDNER = vorher
    try:
        rel = str(csv_z.resolve().relative_to(REPO))
    except ValueError:
        rel = str(csv_z)
    import csv
    with open(csv_s, newline="", encoding="utf-8-sig") as f:
        stand_quelle = {z["serie_id"]: z.get("stand_quelle") for z in csv.DictReader(f)}
    with ingest.ingestion_lauf(conn, "vwl", dry_run=dry_run) as lauf:
        sid = ingest.quelle_registrieren(conn, "repo-vwl", rel + "@" + sha[:12], BLOB + rel, sha, rel,
                                         rights_status="je Reihe laut Spalte quelle (Eurostat, OECD …), siehe docs/datenquellen.md")
        for pos, s in enumerate(d["serien"]):
            werte = {neu: (s.get(alt) or None) for alt, neu in SPALTEN.items()}
            meta = {k: v for k, v in s.items() if k not in SPALTEN and k not in ("serie_id", "kern")}
            if stand_quelle.get(s["serie_id"]):
                meta["stand_quelle"] = stand_quelle[s["serie_id"]]      # Stand der Quelle laut Abruf (app/vwl.py reicht ihn nicht durch)
            conn.execute(
                "INSERT INTO international.series (id, topic, name, unit, fmt, kind, frequency, core, provider, dataset, filter, url, fetched, "
                "forecast_from, note, position, meta, run_id) VALUES (%(id)s,%(topic)s,%(name)s,%(unit)s,%(fmt)s,%(kind)s,%(frequency)s,%(core)s,"
                "%(provider)s,%(dataset)s,%(filter)s,%(url)s,%(fetched)s,%(forecast_from)s,%(note)s,%(position)s,%(meta)s::jsonb,%(run)s) "
                "ON CONFLICT (id) DO UPDATE SET topic=EXCLUDED.topic, name=EXCLUDED.name, unit=EXCLUDED.unit, fmt=EXCLUDED.fmt, kind=EXCLUDED.kind, "
                "frequency=EXCLUDED.frequency, core=EXCLUDED.core, provider=EXCLUDED.provider, dataset=EXCLUDED.dataset, filter=EXCLUDED.filter, "
                "url=EXCLUDED.url, fetched=EXCLUDED.fetched, forecast_from=EXCLUDED.forecast_from, note=EXCLUDED.note, position=EXCLUDED.position, "
                "meta=EXCLUDED.meta, run_id=EXCLUDED.run_id",
                {**werte, "id": s["serie_id"], "core": bool(s.get("kern")), "position": pos, "meta": json.dumps(meta, ensure_ascii=False),
                 "run": lauf.run_id})
            bericht["reihen"] += 1
        conn.execute("CREATE TEMP TABLE vwl_neu (series_id text, geo text, period text, value double precision) ON COMMIT DROP")
        with conn.cursor().copy("COPY vwl_neu (series_id, geo, period, value) FROM STDIN") as cp:
            for sid_, geos in d["daten"].items():
                for geo, pts in geos.items():
                    for zeit, wert in pts:
                        cp.write_row((sid_, geo, zeit, wert))
                        bericht["werte_datei"] += 1
        conn.execute("CREATE INDEX ON vwl_neu (series_id, geo, period)")
        bericht["revidiert"] = conn.execute("""
            UPDATE international.observation o SET valid_to = now() FROM vwl_neu n
             WHERE o.valid_to IS NULL AND o.series_id = n.series_id AND o.geo = n.geo AND o.period = n.period AND o.value <> n.value""").rowcount
        bericht["entfallen"] = conn.execute("""
            UPDATE international.observation o SET valid_to = now()
             WHERE o.valid_to IS NULL AND o.series_id IN (SELECT DISTINCT series_id FROM vwl_neu)
               AND NOT EXISTS (SELECT 1 FROM vwl_neu n WHERE n.series_id = o.series_id AND n.geo = o.geo AND n.period = o.period)""").rowcount
        bericht["neu"] = conn.execute("""
            INSERT INTO international.observation (series_id, geo, period, value, run_id, source_id, source_updated, fetched)
            SELECT n.series_id, n.geo, n.period, n.value, %s, %s, s.meta->>'stand_quelle', s.fetched
              FROM vwl_neu n JOIN international.series s ON s.id = n.series_id
             WHERE NOT EXISTS (SELECT 1 FROM international.observation o WHERE o.valid_to IS NULL AND o.series_id = n.series_id
                                 AND o.geo = n.geo AND o.period = n.period)""", (lauf.run_id, sid)).rowcount
        lauf.anzahl = bericht["neu"]
        lauf.wasserzeichen = {"sha256": sha, "stand": d.get("stand")}
    conn.execute("ANALYZE international.observation")
    return bericht
