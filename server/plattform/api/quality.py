"""Datenqualität (P3.2): ein reproduzierbarer Prüfbericht über den aktuellen Datenbestand.

Gleicher Datenstand (letzter Importlauf) und gleicher Stichtag ergeben denselben Bericht; Rechenregeln in plattform/qualitaet.py.
Abschnitte: Prüfmarken der Unternehmenstabelle und Qualitätsstufen der Fakten, veraltete VWL-Reihen, auffällige Sprünge,
Abdeckung mit festem Nenner (VWL: Gebiete; Profile: Unternehmen mit Profil), nicht freigegebene Quellen mit Daten.
"""
import threading
from collections import OrderedDict
from datetime import date as Datum
from typing import Optional

from fastapi import APIRouter, Query, Request
from sqlalchemy import text

from .. import qualitaet as q
from ..schemas import Antwort
from .common import DB, jetzt, meta

router = APIRouter(tags=["Datenqualität"])
_CACHE: "OrderedDict[tuple, dict]" = OrderedDict()
_SPERRE = threading.Lock()


def _bericht(conn, stichtag):
    flags = [dict(r) for r in conn.execute(text(
        "SELECT code, count(*) AS total, count(decision) AS decided, count(*) - count(decision) AS open "
        "FROM international.review_flag GROUP BY code ORDER BY count(*) DESC, code")).mappings()]
    fakten = {r[0]: r[1] for r in conn.execute(text("SELECT quality, count(*) FROM international.fact GROUP BY quality ORDER BY quality"))}

    reihen = conn.execute(text("SELECT id, name, frequency, forecast_from FROM international.series ORDER BY position")).mappings().all()
    werte = {}
    for sid, geo, per, val in conn.execute(text(
            "SELECT series_id, geo, period, value FROM international.observation WHERE valid_to IS NULL "
            "ORDER BY series_id, geo, period COLLATE \"C\"")):
        werte.setdefault(sid, {}).setdefault(geo, []).append((per, val))
    alle_geos = sorted({g for gs in werte.values() for g in gs})

    veraltet, spruenge, abdeckung_vwl = [], [], []
    for r in reihen:
        gs = werte.get(r["id"], {})
        prog = r["forecast_from"]
        beob = {g: [p for p in pts if not prog or p[0] < prog] for g, pts in gs.items()}
        letzte = max((pts[-1][0] for pts in beob.values() if pts), default=None)
        if letzte:
            v = q.verzug(letzte, r["frequency"], stichtag)
            if v["stale"]:
                veraltet.append({"series_id": r["id"], "name": r["name"], "frequency": r["frequency"], "last_period": letzte, **v})
        for g, pts in sorted(beob.items()):
            for s in q.spruenge(pts):
                spruenge.append({"series_id": r["id"], "geo": g, **s})
        abdeckung_vwl.append({"series_id": r["id"], "covered": len(gs), "share": q.anteil(len(gs), len(alle_geos))})

    n_prof = conn.execute(text("SELECT count(*) FROM international.company_profile")).scalar()
    abdeckung_prof = [{"metric": c, "name": n, "covered": k, "share": q.anteil(k, n_prof)} for c, n, k in conn.execute(text(
        "SELECT m.code, m.name, count(v.entity_id) FROM international.profile_metric m "
        "LEFT JOIN international.company_profile_value v ON v.metric_code = m.code GROUP BY m.code, m.name, m.position ORDER BY m.position"))]

    quellen = [dict(r) for r in conn.execute(text(
        "SELECT d.id, d.status, d.decision, "
        "  (SELECT count(*) FROM international.series s WHERE s.provider = ANY(d.aliases)) AS series, "
        "  (SELECT count(*) FROM international.source_document sd WHERE sd.provider = ANY(d.aliases)) AS documents "
        "FROM international.data_source d WHERE d.status NOT IN ('geeignet', 'namensnennung', 'erledigt') ORDER BY d.position")).mappings()]
    quellen = [x for x in quellen if x["series"] or x["documents"]]

    return {
        "reference_date": stichtag.isoformat(),
        "rules": {"allowed_lag_months": q.ERLAUBT_MONATE, "jump_threshold": q.SPRUNG_SCHWELLE, "jump_min_history": q.SPRUNG_MIN_HISTORIE,
                  "jump_checked_latest": q.SPRUNG_LETZTE},
        "summary": {"open_flags": sum(f["open"] for f in flags), "stale_series": len(veraltet), "jumps": len(spruenge),
                    "uncleared_sources_with_data": len(quellen)},
        "flags": flags,
        "fact_quality": fakten,
        "stale_series": veraltet,
        "jumps": spruenge,
        "coverage": {
            "series": {"denominator": len(alle_geos), "denominator_basis": "alle Gebiete mit mindestens einem aktuellen VWL-Wert",
                       "geos": alle_geos, "rows": abdeckung_vwl},
            "profile_metrics": {"denominator": n_prof, "denominator_basis": "alle Unternehmen mit Profil", "rows": abdeckung_prof},
        },
        "uncleared_sources_with_data": quellen,
    }


@router.get("/data-quality", response_model=Antwort[dict], summary="Prüfbericht: Prüfmarken, veraltete Reihen, Sprünge, Abdeckung")
def data_quality(request: Request, conn=DB,
                 as_of: Optional[Datum] = Query(None, description="Stichtag für den Verzug (Standard: heute, UTC); gleicher Stichtag und "
                                                                  "gleicher Datenstand ergeben denselben Bericht")):
    stichtag = as_of or jetzt().date()
    lauf = conn.execute(text("SELECT max(id), max(finished_at) FROM international.ingestion_run WHERE status = 'ok'")).first()
    schluessel = (stichtag, lauf[0])
    with _SPERRE:
        d = _CACHE.get(schluessel)
    if d is None:
        d = _bericht(conn, stichtag)
        with _SPERRE:
            _CACHE[schluessel] = d
            while len(_CACHE) > 8:
                _CACHE.popitem(last=False)
    m = meta(request, source="Datenbank (review_flag, fact, series, observation, company_profile, data_source)", data_as_of=lauf[1])
    m["notes"] = ["Regeln und Schwellen: plattform/qualitaet.py; Sprünge sind Hinweise zur Prüfung, keine Fehlerbefunde."]
    return {"data": d, "meta": m}
