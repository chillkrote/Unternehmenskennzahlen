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
from .common import DB, meta

router = APIRouter(tags=["Volkswirtschaft"])

MAX_REIHEN = 60
ZEITRAUM = r"^\d{4}(-(0[1-9]|1[0-2])|-Q[1-4])?$"
KATALOG = """
  SELECT s.id, s.topic, s.name, s.unit, s.fmt, s.kind, s.frequency, s.core, s.provider, s.dataset, s.filter, s.url, s.fetched,
         s.forecast_from, s.note, s.meta,
         COALESCE(a.geos, '{}') AS geos, a.first_period, a.last_period, COALESCE(a.n, 0) AS observations
    FROM international.series s
    LEFT JOIN (SELECT series_id, array_agg(DISTINCT geo ORDER BY geo) AS geos, min(period COLLATE "C") AS first_period,
                      max(period COLLATE "C") AS last_period, count(*) AS n
                 FROM international.observation WHERE valid_to IS NULL GROUP BY series_id) a ON a.series_id = s.id"""


def _stand(conn):
    return conn.execute(text("SELECT finished_at FROM international.ingestion_run WHERE adapter = 'vwl' AND status = 'ok' "
                             "ORDER BY id DESC LIMIT 1")).scalar()


def _liste(wert, muster, name, grenze):
    if not wert:
        return None
    l = [x.strip() for x in wert.split(",") if x.strip()]
    if len(l) > grenze or any(not re.match(muster, x) for x in l):
        raise HTTPException(422, detail={"code": name, "message": f"{name}: höchstens {grenze} kommagetrennte Werte im erlaubten Format"})
    return l


@router.get("/series", response_model=Antwort[list[Reihe]], summary="Katalog der volkswirtschaftlichen Reihen mit Abdeckung")
def series(request: Request, conn=DB, topic: Optional[str] = Query(None, max_length=40, description="nur dieses Thema (z. B. wachstum, preise)")):
    zeilen = conn.execute(text(KATALOG + " WHERE (CAST(:t AS text) IS NULL OR s.topic = :t) ORDER BY s.position"), {"t": topic}).mappings().all()
    m = meta(request, source="volkswirtschaft/serien.csv, zeitreihe_lang.csv", data_as_of=_stand(conn))
    return {"data": [dict(z) for z in zeilen], "meta": m}


@router.get("/series/{series_id}", response_model=Antwort[Reihe], summary="Eine Reihe mit Abdeckung")
def series_eine(request: Request, series_id: str, conn=DB):
    z = conn.execute(text(KATALOG + " WHERE s.id = :id"), {"id": series_id}).mappings().first()
    if not z:
        raise HTTPException(404, detail={"code": "nicht_gefunden", "message": f"Keine Reihe {series_id!r} (Katalog: /series)"})
    return {"data": dict(z), "meta": meta(request, source="volkswirtschaft/serien.csv", data_as_of=_stand(conn))}


@router.get("/observations", summary="Werte mehrerer Reihen je Gebiet (kompakt), optional zum Stand eines Tages")
def observations(request: Request, conn=DB,
                 series: str = Query(..., max_length=2000, description=f"kommagetrennte Reihen-IDs, höchstens {MAX_REIHEN}"),
                 geo: Optional[str] = Query(None, max_length=600, description="kommagetrennte Gebiete (DE, EA20, UK …); ohne: alle"),
                 from_: Optional[str] = Query(None, alias="from", pattern=ZEITRAUM, description="Zeitraum ab (JJJJ, JJJJ-MM, JJJJ-Qn)"),
                 to: Optional[str] = Query(None, pattern=ZEITRAUM, description="Zeitraum bis"),
                 as_of: Optional[Datum] = Query(None, description="Stand „bekannt zum“ Ende dieses Tages (UTC): frühere Fassungen revidierter Werte")):
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
    m = meta(request, source="volkswirtschaft/zeitreihe_lang.csv", data_as_of=_stand(conn))
    m["notes"] = ["Format {reihe: {gebiet: [[zeitraum, wert], …]}}; Werte in der Einheit der Reihe (/series)."] + \
        ([f"Stand bekannt zum {as_of.isoformat()} (Ende des Tages, UTC)"] if as_of else [])
    return {"data": daten, "meta": m}
