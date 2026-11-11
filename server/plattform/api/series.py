"""VWL-Reihen (Revision 0004): Katalog und Werte je Reihe und Gebiet, mit Stand „bekannt zum“ (Vintage).

Werte im selben kompakten Format wie bisher eingebettet: {reihe: {gebiet: [[zeitraum, wert], …]}}, Zeiträume aufsteigend.
"""
import re
from datetime import datetime, time, timezone
from datetime import date as Datum
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import text

from ..schemas import Antwort, Reihe
from .common import DB, meta, seite

router = APIRouter(tags=["Volkswirtschaft"])

MAX_REIHEN = 60
ZEITRAUM = r"^\d{4}(-(0[1-9]|1[0-2])|-Q[1-4])?$"
KATALOG = """
  SELECT s.id, s.topic, s.name, s.unit, s.fmt, s.kind, s.frequency, s.core, s.provider, s.dataset, s.filter, s.url, s.fetched,
         s.forecast_from, s.note, s.meta, COALESCE(s.meta->>'ebene', 'country') AS level,
         COALESCE(a.geos, '{}') AS geos, a.first_period, a.last_period, COALESCE(a.n, 0) AS observations,
         s.meta->>'stand_quelle' AS source_updated, h.history_start, COALESCE(h.superseded, 0) AS superseded_versions
    FROM international.series s
    LEFT JOIN (SELECT series_id, min(valid_from) AS history_start, count(*) FILTER (WHERE valid_to IS NOT NULL) AS superseded
                 FROM international.observation GROUP BY series_id) h ON h.series_id = s.id
    LEFT JOIN (SELECT series_id, array_agg(DISTINCT geo ORDER BY geo) AS geos, min(period COLLATE "C") AS first_period,
                      max(period COLLATE "C") AS last_period, count(*) AS n
                 FROM international.observation WHERE valid_to IS NULL GROUP BY series_id) a ON a.series_id = s.id"""


def _stand(conn):
    return conn.execute(text("SELECT finished_at FROM international.ingestion_run WHERE adapter = 'vwl' AND status = 'ok' "
                             "ORDER BY id DESC LIMIT 1")).scalar()


# Begriffe der Versionierung (Audit 2026-11, 4.4); stehen in meta.vintage von /observations und /series/{id}/revisions
VINTAGE = {
    "basis": "recorded_from/recorded_to bzw. as_of beziehen sich auf den Erfassungszeitpunkt des Imports in diese Datenbank (Datenbankstand), "
             "nicht auf das Veröffentlichungsdatum der Quelle",
    "reconstruction": False,
    "terms": {
        "period": "Beobachtungszeitraum, auf den sich der Wert bezieht",
        "recorded_from": "Erfassungszeitpunkt: seit wann diese Fassung in der Datenbank gilt",
        "recorded_to": "bis wann sie galt (leer = aktuelle Fassung); danach revidiert oder aus der Quelle entfallen",
        "source_updated": "Stand der Quelle laut Abruf (Quellenversion), soweit festgehalten",
        "fetched": "Datum des Abrufs bei der Quelle, soweit festgehalten",
        "status": "observation = Beobachtung, forecast = Projektion (Zeitraum ab forecast_from der Reihe)",
    },
    "limits": ["Die Historie beginnt mit dem ersten Import (history_start); frühere öffentlich verfügbare Stände sind nicht rekonstruiert.",
               "Zwischen zwei Importen mehrfach revidierte Werte erscheinen als eine Revision.",
               "Vorläufige oder geschätzte Werte der Quellen (Kennzeichen p, e) werden bisher nicht übernommen; status unterscheidet nur "
               "Beobachtung und Projektion."],
}


def _historie(conn, ids=None):
    return conn.execute(text("SELECT min(valid_from) FROM international.observation WHERE (CAST(:ids AS text[]) IS NULL OR series_id = ANY(:ids))"),
                        {"ids": ids}).scalar()


def _liste(wert, muster, name, grenze):
    if not wert:
        return None
    l = [x.strip() for x in wert.split(",") if x.strip()]
    if len(l) > grenze or any(not re.match(muster, x) for x in l):
        raise HTTPException(422, detail={"code": name, "message": f"{name}: höchstens {grenze} kommagetrennte Werte im erlaubten Format"})
    return l


@router.get("/series", response_model=Antwort[list[Reihe]], summary="Katalog der volkswirtschaftlichen Reihen mit Abdeckung")
def series(request: Request, conn=DB, topic: Optional[str] = Query(None, max_length=40, description="nur dieses Thema (z. B. wachstum, preise)"),
           level: Optional[str] = Query(None, pattern="^(country|nuts3)$", description="nur Länderreihen (country) oder Regionalreihen (nuts3)")):
    zeilen = conn.execute(text(KATALOG + " WHERE (CAST(:t AS text) IS NULL OR s.topic = :t) AND (CAST(:l AS text) IS NULL OR "
                                         "COALESCE(s.meta->>'ebene', 'country') = :l) ORDER BY s.position"), {"t": topic, "l": level}).mappings().all()
    m = meta(request, source="volkswirtschaft/serien.csv, zeitreihe_lang.csv", data_as_of=_stand(conn))
    return {"data": [dict(z) for z in zeilen], "meta": m}


@router.get("/series/{series_id}", response_model=Antwort[Reihe], summary="Eine Reihe mit Abdeckung")
def series_eine(request: Request, series_id: str, conn=DB):
    z = conn.execute(text(KATALOG + " WHERE s.id = :id"), {"id": series_id}).mappings().first()
    if not z:
        raise HTTPException(404, detail={"code": "nicht_gefunden", "message": f"Keine Reihe {series_id!r} (Katalog: /series)"})
    return {"data": dict(z), "meta": meta(request, source="volkswirtschaft/serien.csv", data_as_of=_stand(conn))}


@router.get("/series/{series_id}/revisions", response_model=Antwort[list[dict]],
            summary="Alle gespeicherten Fassungen der Werte einer Reihe (Revisionen), mit Erfassungszeitpunkt und Quellenstand")
def revisions(request: Request, series_id: str, conn=DB,
              geo: Optional[str] = Query(None, max_length=600, description="kommagetrennte Gebiete; ohne: alle"),
              period: Optional[str] = Query(None, pattern=ZEITRAUM, description="nur dieser Beobachtungszeitraum"),
              only_revised: bool = Query(True, description="nur Zeiträume mit mehr als einer Fassung (false: auch nie revidierte Werte)"),
              page: int = Query(1, ge=1), page_size: int = Query(200, ge=1, le=1000)):
    r = conn.execute(text("SELECT id, forecast_from FROM international.series WHERE id = :id"), {"id": series_id}).first()
    if not r:
        raise HTTPException(404, detail={"code": "nicht_gefunden", "message": f"Keine Reihe {series_id!r} (Katalog: /series)"})
    geos = _liste(geo, r"^[A-Z0-9_]{2,12}$", "geo", 80)
    bed, par = ["o.series_id = :id"], {"id": series_id, "lim": page_size, "off": (page - 1) * page_size}
    if geos:
        bed.append("o.geo = ANY(:geos)"); par["geos"] = geos
    if period:
        bed.append("o.period = :p"); par["p"] = period
    if only_revised:
        bed.append("EXISTS (SELECT 1 FROM international.observation x WHERE x.series_id = o.series_id AND x.geo = o.geo AND x.period = o.period "
                   "AND x.valid_to IS NOT NULL)")
    wo = " AND ".join(bed)
    total = conn.execute(text(f"SELECT count(*) FROM international.observation o WHERE {wo}"), par).scalar()
    zeilen = [{"geo": z.geo, "period": z.period, "value": z.value, "status": "forecast" if r.forecast_from and z.period >= r.forecast_from else "observation",
               "recorded_from": z.valid_from, "recorded_to": z.valid_to, "current": z.valid_to is None, "source_updated": z.source_updated,
               "fetched": z.fetched, "run_id": z.run_id}
              for z in conn.execute(text(f"SELECT o.geo, o.period, o.value, o.valid_from, o.valid_to, o.source_updated, o.fetched, o.run_id "
                                         f"FROM international.observation o WHERE {wo} "
                                         f"ORDER BY o.geo, o.period COLLATE \"C\", o.valid_from LIMIT :lim OFFSET :off"), par)]
    m = meta(request, source="international.observation (alle Fassungen)", data_as_of=_stand(conn))
    m["vintage"] = {**VINTAGE, "history_start": _historie(conn, [series_id])}
    m["pagination"] = seite(total, page, page_size)
    return {"data": zeilen, "meta": m}


@router.get("/observations", summary="Werte mehrerer Reihen je Gebiet (kompakt), optional zum Stand eines Tages")
def observations(request: Request, conn=DB,
                 series: str = Query(..., max_length=2000, description=f"kommagetrennte Reihen-IDs, höchstens {MAX_REIHEN}"),
                 geo: Optional[str] = Query(None, max_length=600, description="kommagetrennte Gebiete (DE, EA20, UK …); ohne: alle"),
                 from_: Optional[str] = Query(None, alias="from", pattern=ZEITRAUM, description="Zeitraum ab (JJJJ, JJJJ-MM, JJJJ-Qn)"),
                 to: Optional[str] = Query(None, pattern=ZEITRAUM, description="Zeitraum bis"),
                 as_of: Optional[Datum] = Query(None, description="Stand „bekannt zum“ Ende dieses Tages (UTC): frühere Fassungen revidierter Werte"),
                 format: str = Query("json", pattern="^(json|csv)$", description="csv: eine Zeile je Wert (reihe;gebiet;zeitraum;wert), Semikolon, UTF-8")):
    ids = _liste(series, r"^[a-z0-9_]{1,60}$", "series", MAX_REIHEN)
    geos = _liste(geo, r"^[A-Z0-9_]{2,12}$", "geo", 80)
    bekannt = {r[0] for r in conn.execute(text("SELECT id FROM international.series WHERE id = ANY(:ids)"), {"ids": ids})}
    fehlt = [i for i in ids if i not in bekannt]
    if fehlt:
        raise HTTPException(404, detail={"code": "nicht_gefunden", "message": f"unbekannte Reihen {fehlt}", "details": fehlt})
    bed, par = ["o.series_id = ANY(:ids)"], {"ids": ids}
    if as_of:
        par["t"] = datetime.combine(as_of, time.max, tzinfo=timezone.utc)
        bed.append("o.valid_from <= :t AND (o.valid_to IS NULL OR o.valid_to > :t)")
    else:
        bed.append("o.valid_to IS NULL")
    if geos:
        bed.append("o.geo = ANY(:geos)"); par["geos"] = geos
    if from_:
        bed.append("o.period COLLATE \"C\" >= :von"); par["von"] = from_
    if to:
        bed.append("o.period COLLATE \"C\" <= :bis"); par["bis"] = to
    daten = {i: {} for i in ids}
    for s, g, p, v in conn.execute(text(f"SELECT o.series_id, o.geo, o.period, o.value FROM international.observation o "
                                        f"WHERE {' AND '.join(bed)} ORDER BY o.series_id, o.geo, o.period COLLATE \"C\""), par):
        daten[s].setdefault(g, []).append([p, v])
    if format == "csv":
        from .analysis import _csv
        return _csv([[s, g, p, v] for s, gs in daten.items() for g, pts in gs.items() for p, v in pts], ["reihe", "gebiet", "zeitraum", "wert"])
    m = meta(request, source="volkswirtschaft/zeitreihe_lang.csv", data_as_of=_stand(conn))
    m["notes"] = ["Format {reihe: {gebiet: [[zeitraum, wert], …]}}; Werte in der Einheit der Reihe (/series)."]
    if as_of:
        beginn = _historie(conn, ids)
        m["vintage"] = {**VINTAGE, "history_start": beginn, "as_of": as_of.isoformat()}
        m["notes"].append(f"Datenbankstand zum {as_of.isoformat()} (Ende des Tages, UTC): Fassungen, die zu diesem Zeitpunkt in dieser Datenbank "
                          f"galten. Keine Rekonstruktion früherer Veröffentlichungen der Quelle.")
        if beginn is None or par["t"] < beginn:
            m["notes"].append(f"as_of liegt vor dem Beginn der Historie ({beginn.date().isoformat() if beginn else 'kein Import'}); "
                              "für diesen Tag ist kein Stand gespeichert, die Antwort ist deshalb leer.")
    return {"data": daten, "meta": m}
