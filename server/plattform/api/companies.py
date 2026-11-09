"""Unternehmen: Liste mit serverseitiger Filterung und Pagination, Einzelprofil, Kennzahlen (Zeitreihen mit Vintage)."""
import re
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import text

from ..schemas import Antwort, Beobachtung, Unternehmen, UnternehmenKurz, UnternehmenZeile
from .common import BRANCHEN, DB, meta, register_stand, seite, seitengroesse

router = APIRouter(tags=["Unternehmen"])

ID_MUSTER = r"^U\d{6}$"
FELDER_KURZ = list(UnternehmenKurz.model_fields)
SORTIERUNG = {
    # Standard wie im Terminal-Verzeichnis: Unternehmen mit Kennzahlen zuerst, dann Name
    "default": "(fakten > 0) DESC, lower(name), id",
    "name": "lower(name), id",
    "-name": "lower(name) DESC, id",
    "id": "id",
    "country": "country NULLS LAST, lower(name), id",
}

BASIS = """
  SELECT r.entity_id AS id, r.name, r.domicile AS country, r.country_name, r.seat, r.sector, r.listed, r.is_bank,
         r.isin, r.ticker, r.exchange, r.lei,
         (SELECT count(*) FROM international.fact x WHERE x.entity_id = r.entity_id)
         + (SELECT count(*) FROM international.company_profile_value x WHERE x.entity_id = r.entity_id) AS fakten
    FROM international.company_register r
   WHERE r.active AND r.entity_id IS NOT NULL
"""


def _filter(q, country, sector, listed, has_metrics, ids):
    bed, par = [], {}
    if q:
        q = q.strip().lower()
        par["q"] = q
        par["qlike"] = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        # wie die bisherige Suche im Terminal: Name, Ticker, ISIN, LEI, Sitz (Teilzeichenfolge), dazu ID und Aliase
        bed.append("(lower(r.name) LIKE :qlike OR lower(COALESCE(r.ticker,'')) LIKE :qlike OR lower(COALESCE(r.isin,'')) LIKE :qlike"
                   " OR lower(COALESCE(r.lei,'')) LIKE :qlike OR lower(COALESCE(r.seat,'')) LIKE :qlike OR lower(r.entity_id) = :q"
                   " OR EXISTS (SELECT 1 FROM international.company_alias a WHERE a.row_key = r.row_key AND lower(a.alias) LIKE :qlike))")
    if country:
        if country == "ZZ":
            bed.append("r.domicile IS NULL")
        else:
            bed.append("r.domicile = :country")
            par["country"] = country
    if sector:
        bed.append("r.sector = :sector")
        par["sector"] = sector
    if listed is not None:
        bed.append("r.listed = :listed")
        par["listed"] = listed
    if has_metrics is not None:
        bed.append(("" if has_metrics else "NOT ") + "(EXISTS (SELECT 1 FROM international.fact x WHERE x.entity_id = r.entity_id)"
                   " OR EXISTS (SELECT 1 FROM international.company_profile_value x WHERE x.entity_id = r.entity_id))")
    if ids:
        bed.append("r.entity_id = ANY(:ids)")
        par["ids"] = ids
    return bed, par


@router.get("/companies", response_model=Antwort[list[UnternehmenZeile]], response_model_exclude_unset=True,
            summary="Unternehmen suchen und filtern")
def companies(request: Request, conn=DB,
              q: Optional[str] = Query(None, max_length=100, description="Teilzeichenfolge in Name, Alias, Ticker, ISIN, LEI, Sitz oder exakte ID"),
              country: Optional[str] = Query(None, pattern=r"^[A-Za-z]{2}$", description="Sitzland ISO-Alpha-2; ZZ = unbekannt"),
              sector: Optional[str] = Query(None, max_length=40, description="Branchen-ID, siehe /sectors"),
              listed: Optional[bool] = Query(None, description="nur börsennotierte (true) bzw. nicht notierte (false)"),
              has_metrics: Optional[bool] = Query(None, description="nur mit (true) bzw. ohne (false) Kennzahlen in der Datenbank"),
              ids: Optional[str] = Query(None, max_length=8000, description="kommagetrennte Unternehmens-IDs (z. B. Merkliste), höchstens 500"),
              sort: str = Query("default", description="default | name | -name | id | country"),
              page: int = Query(1, ge=1, le=10000),
              page_size: int = Query(100, ge=1),
              fields: Optional[str] = Query(None, max_length=300, description="kommagetrennte Feldauswahl, z. B. id,name,country")):
    page_size = seitengroesse(request, page_size)
    if sort not in SORTIERUNG:
        raise HTTPException(422, detail={"code": "sortierung", "message": f"sort muss eines von {sorted(SORTIERUNG)} sein"})
    if sector and sector not in BRANCHEN:
        raise HTTPException(422, detail={"code": "branche", "message": f"unbekannte Branche {sector!r}", "details": sorted(BRANCHEN)})
    id_liste = None
    if ids is not None:
        id_liste = [x.strip().upper() for x in ids.split(",") if x.strip()]
        if len(id_liste) > 500 or any(not re.match(ID_MUSTER, x) for x in id_liste):
            raise HTTPException(422, detail={"code": "ids", "message": "ids: höchstens 500 IDs im Format U000123"})
    auswahl = None
    if fields:
        auswahl = [f.strip() for f in fields.split(",") if f.strip()]
        falsch = [f for f in auswahl if f not in FELDER_KURZ]
        if falsch:
            raise HTTPException(422, detail={"code": "felder", "message": f"unbekannte Felder {falsch}", "details": FELDER_KURZ})
        if "id" not in auswahl:
            auswahl.insert(0, "id")
    bed, par = _filter(q, country.upper() if country else None, sector, listed, has_metrics, id_liste)
    wo = (" AND " + " AND ".join(bed)) if bed else ""
    total = conn.execute(text(f"SELECT count(*) FROM international.company_register r WHERE r.active AND r.entity_id IS NOT NULL{wo}"), par).scalar_one()
    par.update(lim=page_size, off=(page - 1) * page_size)
    zeilen = conn.execute(text(f"SELECT * FROM ({BASIS}{wo}) t ORDER BY {SORTIERUNG[sort]} LIMIT :lim OFFSET :off"), par).mappings().all()
    daten = []
    for z in zeilen:
        d = dict(z)
        d["facts"] = d.pop("fakten")
        daten.append({k: d[k] for k in auswahl} if auswahl else d)
    datei, stand = register_stand(conn)
    return {"data": daten, "meta": meta(request, pagination=seite(total, page, page_size), source=datei, data_as_of=stand)}


@router.get("/companies/{company_id}", response_model=Antwort[Unternehmen], summary="Profil eines Unternehmens")
def company(request: Request, company_id: str, conn=DB):
    cid = company_id.upper()
    if not re.match(ID_MUSTER, cid):
        raise HTTPException(422, detail={"code": "id_format", "message": "Unternehmens-ID im Format U000123 erwartet"})
    r = conn.execute(text("""
        SELECT r.*, (SELECT count(*) FROM international.fact x WHERE x.entity_id = r.entity_id)
                    + (SELECT count(*) FROM international.company_profile_value x WHERE x.entity_id = r.entity_id) AS fakten,
               EXISTS (SELECT 1 FROM international.company_profile x WHERE x.entity_id = r.entity_id) AS hat_profil
          FROM international.company_register r WHERE r.entity_id = :id"""), {"id": cid}).mappings().first()
    if not r:
        raise HTTPException(404, detail={"code": "nicht_gefunden", "message": f"Kein Unternehmen mit der ID {cid}"})
    kennungen = [{"scheme": s, "value": v} for s, v in (("ISIN", r["isin"]), ("LEI", r["lei"]), ("TICKER", r["ticker"]),
                                                        ("REGISTER_NO", r["register_no"])) if v]
    kennungen += [{"scheme": s, "value": v} for s, v in conn.execute(text(
        "SELECT scheme, value FROM international.identifier WHERE entity_id = :id ORDER BY scheme, value"), {"id": cid})
        if not any(k["scheme"] == s and k["value"] == v for k in kennungen)]
    aliase = [a for (a,) in conn.execute(text("SELECT DISTINCT alias FROM international.company_alias WHERE row_key = :k ORDER BY alias"), {"k": r["row_key"]})]
    marken = [dict(m) for m in conn.execute(text(
        "SELECT code, detail, decision, reason FROM international.review_flag WHERE row_key = :k ORDER BY code"), {"k": r["row_key"]}).mappings()]
    kz = [c for (c,) in conn.execute(text("SELECT DISTINCT metric_code FROM international.fact WHERE entity_id = :id ORDER BY 1"), {"id": cid})]
    d = {"id": cid, "name": r["name"], "country": r["domicile"], "country_name": r["country_name"], "seat": r["seat"], "sector": r["sector"],
         "listed": r["listed"], "is_bank": r["is_bank"], "isin": r["isin"], "ticker": r["ticker"], "exchange": r["exchange"], "lei": r["lei"],
         "facts": r["fakten"], "legal_form": r["legal_form"], "nace": r["nace"], "register_no": r["register_no"], "website": r["website"],
         "indices": r["indices"], "description": r["description"], "source_url": r["source_url"], "identifiers": kennungen, "aliases": aliase,
         "review_flags": marken, "metrics": kz,
         "links": {"self": f"/api/v1/companies/{cid}", "metrics": f"/api/v1/companies/{cid}/metrics", "terminal": f"#firma-{cid}",
                   **({"profile": f"/api/v1/companies/{cid}/profile"} if r["hat_profil"] else {})}}
    datei, stand = register_stand(conn)
    notes = [] if r["active"] else ["Zeile ist in der zuletzt importierten Unternehmenstabelle nicht mehr enthalten (active=false)"]
    m = meta(request, source=datei, data_as_of=stand)
    m["notes"] = notes
    return {"data": d, "meta": m}


@router.get("/companies/{company_id}/metrics", response_model=Antwort[list[Beobachtung]], summary="Kennzahlenwerte eines Unternehmens")
def company_metrics(request: Request, company_id: str, conn=DB,
                    metric: Optional[str] = Query(None, max_length=60, description="nur diese Kennzahl (Code, siehe /indicators)"),
                    as_of: Optional[date] = Query(None, description="Stand „bekannt zum“: nur Werte, die an diesem Tag veröffentlicht waren"),
                    from_: Optional[date] = Query(None, alias="from", description="Periodenende ab"),
                    to: Optional[date] = Query(None, description="Periodenende bis")):
    cid = company_id.upper()
    if not re.match(ID_MUSTER, cid):
        raise HTTPException(422, detail={"code": "id_format", "message": "Unternehmens-ID im Format U000123 erwartet"})
    if not conn.execute(text("SELECT 1 FROM international.entity WHERE id = :id"), {"id": cid}).first():
        raise HTTPException(404, detail={"code": "nicht_gefunden", "message": f"Kein Unternehmen mit der ID {cid}"})
    bed, par = ["f.entity_id = :id"], {"id": cid, "as_of": as_of}
    if metric:
        bed.append("f.metric_code = :metric"); par["metric"] = metric
    if from_:
        bed.append("f.period_end >= :von"); par["von"] = from_
    if to:
        bed.append("f.period_end <= :bis"); par["bis"] = to
    zeilen = conn.execute(text(f"""
        SELECT f.metric_code AS metric, f.period_start, f.period_end, f.value, f.unit, f.accounting_standard, f.consolidation, f.quality,
               f.reported_at, f.recorded_at, f.provenance, s.provider, s.url, s.object_key, s.fetched_at, s.rights_status
          FROM international.fact_as_of(CAST(:as_of AS date)) f JOIN international.source_document s ON s.id = f.source_id
         WHERE {' AND '.join(bed)} ORDER BY f.metric_code, f.period_end"""), par).mappings().all()
    daten = [{"metric": z["metric"], "period_start": z["period_start"], "period_end": z["period_end"], "value": float(z["value"]), "unit": z["unit"],
              "accounting_standard": z["accounting_standard"], "consolidation": z["consolidation"], "quality": z["quality"],
              "reported_at": z["reported_at"], "recorded_at": z["recorded_at"], "provenance": z["provenance"] or {},
              "source": {"provider": z["provider"], "url": z["url"], "object_key": z["object_key"], "fetched_at": z["fetched_at"].isoformat(),
                         "rights_status": z["rights_status"]}} for z in zeilen]
    m = meta(request)
    m["notes"] = ["Werte unskaliert in der angegebenen Einheit; Quoten als Dezimalzahl (0.15 = 15 %).",
                  "Fehlende Perioden sind nicht vorhanden, nicht null."] + ([f"Stand bekannt zum {as_of.isoformat()}"] if as_of else [])
    return {"data": daten, "meta": m}
