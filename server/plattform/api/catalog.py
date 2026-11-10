"""Datenkatalog (P3.1): Quellen mit Lizenzstand, Abdeckung und Importstand; Prognosegeber je Land.

Texte aus docs/datenquellen.md, maschinenlesbare Felder aus server/katalog/datenquellen.csv (ETL: etl/katalog.py).
Abdeckung und Stand werden über die Aliase der Quelle aus series, observation, source_document und ingestion_run ermittelt.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import text

from ..schemas import Antwort, Datenquelle, Prognosegeber
from .common import DB, meta

router = APIRouter(tags=["Datenkatalog"])

FREI = ("geeignet", "namensnennung", "erledigt")
STATUS = "^(geeignet|namensnennung|voraussichtlich|pruefen|eingeschraenkt|kritisch|erledigt)$"
QUELLEN = """
  SELECT d.id, d.name, d.area, d.used_for, d.access, d.credentials, d.license, d.assessment, d.status,
         d.status IN ('geeignet', 'namensnennung', 'erledigt') AS cleared, d.decision, d.attribution, d.links, d.aliases,
         COALESCE(r.n, 0) AS series, COALESCE(r.datasets, '{}') AS datasets, COALESCE(r.obs, 0) AS observations,
         r.first_year, r.last_year, r.fetched,
         (SELECT count(*) FROM international.source_document sd WHERE sd.provider = ANY(d.aliases)) AS documents,
         (SELECT max(finished_at) FROM international.ingestion_run ir WHERE ir.adapter = ANY(d.aliases) AND ir.status = 'ok') AS last_run,
         (SELECT count(*) FROM international.forecaster f WHERE f.source_id = d.id) AS forecasters
    FROM international.data_source d
    LEFT JOIN LATERAL (
      SELECT count(*) AS n, array_agg(DISTINCT s.dataset ORDER BY s.dataset) FILTER (WHERE s.dataset IS NOT NULL) AS datasets,
             max(s.fetched) AS fetched, sum(a.n) AS obs, min(a.first_year) AS first_year, max(a.last_year) AS last_year
        FROM international.series s
        LEFT JOIN (SELECT series_id, count(*) AS n, min(left(period, 4)::int) AS first_year, max(left(period, 4)::int) AS last_year
                     FROM international.observation WHERE valid_to IS NULL GROUP BY series_id) a ON a.series_id = s.id
       WHERE s.provider = ANY(d.aliases)) r ON true"""


def _stand(conn):
    return conn.execute(text("SELECT finished_at FROM international.ingestion_run WHERE adapter = 'katalog' AND status = 'ok' "
                             "ORDER BY id DESC LIMIT 1")).scalar()


@router.get("/data-catalog", response_model=Antwort[list[Datenquelle]], summary="Alle Datenquellen mit Lizenzstand, Abdeckung und Importstand")
def data_catalog(request: Request, conn=DB,
                 area: Optional[str] = Query(None, pattern="^[a-z]{2,20}$", description="nur dieser Bereich (z. B. volkswirtschaft, politik)"),
                 status: Optional[str] = Query(None, pattern=STATUS, description="nur dieser Lizenzstatus"),
                 cleared: Optional[bool] = Query(None, description="true: nur für den öffentlichen Server freigegebene Quellen"),
                 decision: Optional[bool] = Query(None, description="true: nur Quellen mit offener Entscheidung (E1 …)")):
    bed, par = [], {}
    if area:
        bed.append("d.area = :area"); par["area"] = area
    if status:
        bed.append("d.status = :status"); par["status"] = status
    if cleared is not None:
        bed.append(("" if cleared else "NOT ") + "d.status = ANY(:frei)"); par["frei"] = list(FREI)
    if decision is not None:
        bed.append("d.decision IS " + ("NOT NULL" if decision else "NULL"))
    wo = (" WHERE " + " AND ".join(bed)) if bed else ""
    zeilen = conn.execute(text(QUELLEN + wo + " ORDER BY d.position"), par).mappings().all()
    m = meta(request, source="docs/datenquellen.md, server/katalog/datenquellen.csv", data_as_of=_stand(conn))
    m["notes"] = ["Lizenzangaben sind eine fachliche Vorprüfung, keine Rechtsberatung; offene Entscheidungen: docs/datenquellen.md."]
    return {"data": [dict(z) for z in zeilen], "meta": m}


@router.get("/data-catalog/{source_id}", response_model=Antwort[dict], summary="Eine Datenquelle mit ihren Reihen")
def data_catalog_eine(request: Request, source_id: str, conn=DB):
    z = conn.execute(text(QUELLEN + " WHERE d.id = :id"), {"id": source_id}).mappings().first()
    if not z:
        raise HTTPException(404, detail={"code": "nicht_gefunden", "message": f"Keine Datenquelle {source_id!r} (Katalog: /data-catalog)"})
    reihen = conn.execute(text("SELECT id, name, topic, dataset, frequency, unit, fetched FROM international.series "
                               "WHERE provider = ANY(:a) ORDER BY position"), {"a": z["aliases"]}).mappings().all()
    d = Datenquelle(**z).model_dump()
    d["series_list"] = [dict(r) for r in reihen]
    return {"data": d, "meta": meta(request, source="docs/datenquellen.md, server/katalog/datenquellen.csv", data_as_of=_stand(conn))}


@router.get("/forecasters", response_model=Antwort[list[Prognosegeber]], summary="Prognosegeber je Land (Recherche, ohne eingebundene Werte)")
def forecasters(request: Request, conn=DB,
                geo: Optional[str] = Query(None, pattern="^[A-Z0-9_]{2,12}$", description="Land bzw. Gebiet (DE, FR, EA20, OECD …)"),
                priority: Optional[int] = Query(None, ge=1, le=3, description="höchstens diese Priorität (1 = nur die wichtigsten)")):
    zeilen = conn.execute(text(
        "SELECT id, geo, country, publisher, type, publication, variables, horizon, rhythm, url, access, data_url, priority, note, "
        "http_status_url, http_status_data, checked FROM international.forecaster "
        "WHERE (CAST(:geo AS text) IS NULL OR geo = :geo) AND (CAST(:p AS int) IS NULL OR priority <= :p) ORDER BY geo, priority NULLS LAST, id"),
        {"geo": geo, "p": priority}).mappings().all()
    m = meta(request, source="volkswirtschaft/prognosegeber_oecd.csv", data_as_of=_stand(conn))
    m["notes"] = ["Geprüft ist nur die Erreichbarkeit der Adressen (HTTP-Status); Horizont, Rhythmus und Größen siehe volkswirtschaft/PROGNOSEGEBER.md."]
    return {"data": [dict(z) for z in zeilen], "meta": m}
