"""Länder, Branchen, Kennzahlenkatalog, Aktualisierungen und Gesundheitsprüfung."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .. import __version__
from ..db import engine
from ..schemas import Antwort, Branche, Gesundheit, Kennzahl, Land, Lauf
from .common import BRANCHEN, DB, meta, register_stand

router = APIRouter()


@router.get("/countries", response_model=Antwort[list[Land]], tags=["Länder"], summary="Alle Länder mit Zahl der Unternehmen")
def countries(request: Request, conn=DB):
    rows = conn.execute(text("""
        SELECT c.iso2 AS code, c.iso3, c.name, c.name_de, c.region, c.oecd_from IS NOT NULL AND c.oecd_until IS NULL AS oecd_member,
               COALESCE(n.n, 0) AS companies
          FROM international.country c
          LEFT JOIN (SELECT domicile, count(*) n FROM international.company_register WHERE active GROUP BY 1) n ON n.domicile = c.iso2
         ORDER BY COALESCE(c.name_de, c.name)""")).mappings().all()
    return {"data": [dict(r) for r in rows], "meta": meta(request)}


@router.get("/countries/{code}", response_model=Antwort[dict], tags=["Länder"], summary="Ein Land: Stammdaten und Unternehmen nach Branche")
def country(request: Request, code: str, conn=DB):
    code = code.upper()
    r = conn.execute(text("""SELECT iso2 AS code, iso3, name, name_de, region, oecd_from, oecd_until FROM international.country WHERE iso2 = :c"""),
                     {"c": code}).mappings().first()
    if not r:
        raise HTTPException(404, detail={"code": "nicht_gefunden", "message": f"Kein Land mit dem Code {code}"})
    br = conn.execute(text("""SELECT sector, count(*) n, count(*) FILTER (WHERE listed) notiert FROM international.company_register
                               WHERE active AND domicile = :c GROUP BY 1 ORDER BY 2 DESC"""), {"c": code}).mappings().all()
    d = dict(r)
    d["sectors"] = [{"id": b["sector"], "name": BRANCHEN.get(b["sector"], b["sector"]), "companies": b["n"], "listed": b["notiert"]} for b in br]
    d["companies"] = sum(b["n"] for b in br)
    d["links"] = {"companies": f"/api/v1/companies?country={code}"}
    return {"data": d, "meta": meta(request)}


@router.get("/sectors", response_model=Antwort[list[Branche]], tags=["Unternehmen"], summary="Branchen mit Zahl der Unternehmen")
def sectors(request: Request, conn=DB):
    n = dict(conn.execute(text("SELECT sector, count(*) FROM international.company_register WHERE active GROUP BY 1")).all())
    return {"data": [{"id": b, "name": name, "companies": n.get(b, 0)} for b, name in BRANCHEN.items()], "meta": meta(request)}


@router.get("/indicators", response_model=Antwort[list[Kennzahl]], tags=["Kennzahlen"], summary="Kennzahlenkatalog mit Abdeckung")
def indicators(request: Request, conn=DB):
    rows = conn.execute(text("""
        SELECT m.code, m.description, m.period_kind, m.unit_kind, m.regulatory, count(f.id) AS observations, count(DISTINCT f.entity_id) AS companies
          FROM international.metric m LEFT JOIN international.fact f ON f.metric_code = m.code AND f.quality <> 'rejected'
         GROUP BY 1,2,3,4,5 ORDER BY 1""")).mappings().all()
    m = meta(request)
    m["notes"] = ["observations zählt alle gespeicherten Fassungen (auch revidierte); companies = Unternehmen mit mindestens einem Wert"]
    return {"data": [dict(r) for r in rows], "meta": m}


@router.get("/updates", response_model=Antwort[list[Lauf]], tags=["Betrieb"], summary="Letzte Importläufe je Datenquelle")
def updates(request: Request, conn=DB):
    rows = conn.execute(text("""
        SELECT DISTINCT ON (adapter) adapter, status, started_at, finished_at, imported_count,
               (SELECT max(finished_at) FROM international.ingestion_run x WHERE x.adapter = r.adapter AND x.status = 'ok') AS last_success_at
          FROM international.ingestion_run r ORDER BY adapter, started_at DESC""")).mappings().all()
    datei, stand = register_stand(conn)
    return {"data": [dict(r) for r in rows], "meta": meta(request, source=datei, data_as_of=stand)}


@router.get("/health", response_model=Gesundheit, tags=["Betrieb"], summary="Erreichbarkeit von API und Datenbank")
def health(request: Request):
    try:
        with engine(request.app.state.einstellungen).connect() as conn:
            rev = conn.execute(text("SELECT version_num FROM public.alembic_version")).scalar()
        return {"status": "ok", "database": "ok", "schema_revision": rev, "version": __version__}
    except Exception:            # keine Interna nach außen
        return JSONResponse(status_code=503, content={"status": "fehler", "database": "nicht erreichbar", "schema_revision": None, "version": __version__})
