"""Datenqualität (P3.2): ein reproduzierbarer Prüfbericht über den aktuellen Datenbestand.

Gleicher Datenstand (letzter Importlauf) und gleicher Stichtag ergeben denselben Bericht; Rechenregeln in plattform/qualitaet.py.
Abschnitte: Prüfmarken der Unternehmenstabelle und Qualitätsstufen der Fakten, veraltete VWL-Reihen (ganze Quelle), Aktualität
je Reihe und Gebiet mit Lücken, Vergleichszeitraum und Abrufalter (freshness), auffällige Sprünge, Abdeckung mit festem Nenner
(VWL: angefragte Gebiete je Reihe; Profile: Unternehmen mit Profil), nicht freigegebene Quellen mit Daten.
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

    reihen = conn.execute(text("SELECT id, name, frequency, forecast_from, provider, url, fetched, meta FROM international.series ORDER BY position")).mappings().all()
    werte = {}
    for sid, geo, per, val in conn.execute(text(
            "SELECT series_id, geo, period, value FROM international.observation WHERE valid_to IS NULL "
            "ORDER BY series_id, geo, period COLLATE \"C\"")):
        werte.setdefault(sid, {}).setdefault(geo, []).append((per, val))
    alle_geos = sorted({g for gs in werte.values() for g in gs})

    veraltet, spruenge, abdeckung_vwl, frische, je_quelle = [], [], [], [], {}
    for r in reihen:
        gs = werte.get(r["id"], {})
        prog = r["forecast_from"]
        beob = {g: [p for p in pts if not prog or p[0] < prog] for g, pts in gs.items()}
        erwartet = q.erwartete_gebiete(r["url"])
        akt = q.aktualitaet({g: pts[-1][0] for g, pts in beob.items() if pts}, r["frequency"], stichtag, erwartet, r["provider"])
        letzte = akt["source_last"]
        if letzte:
            v = akt["source"]
            if v["stale"]:
                veraltet.append({"series_id": r["id"], "name": r["name"], "frequency": r["frequency"], "last_period": letzte, **v})
        for g, pts in sorted(beob.items()):
            for s in q.spruenge(pts):
                spruenge.append({"series_id": r["id"], "geo": g, **s})
        # Abdeckung: Nenner sind die bei der Quelle angefragten Gebiete; ohne Gebietsliste in der Abruf-URL die Gebiete mit Werten (Anteil 1, so benannt)
        nenner = erwartet if erwartet is not None else sorted(gs)
        gedeckt = [g for g in nenner if g in gs]
        abdeckung_vwl.append({"series_id": r["id"], "covered": len(gedeckt), "expected": len(nenner), "share": q.anteil(len(gedeckt), len(nenner)),
                              "basis": "angefragte Gebiete (Abruf-URL)" if erwartet is not None else "Gebiete mit Werten (keine Gebietsliste im Abruf)",
                              "missing": [g for g in nenner if g not in gs], "unexpected": [g for g in sorted(gs) if g not in nenner]})
        # Aktualität je Gebiet, Lücken und Verfügbarkeit im Vergleichszeitraum
        fen = q.fenster(letzte, r["frequency"]) if letzte else []
        zahl, auffaellig, fenster_ist = {}, [], 0
        for g, e in akt["geos"].items():
            zahl[e["status"]] = zahl.get(e["status"], 0) + 1
            per = [p[0] for p in beob.get(g, [])]
            lue = q.luecken(per, r["frequency"])
            im_fenster = sum(1 for p in fen if p in set(per))
            fenster_ist += im_fenster
            if e["status"] != "current" or lue:
                auffaellig.append({"geo": g, **e, "gaps": len(lue), "gap_periods": lue[:12],
                                   "window_available": im_fenster, "window_share": q.anteil(im_fenster, len(fen))})
        abruf = q.abruf_alter(r["fetched"], r["frequency"], stichtag)
        frische.append({"series_id": r["id"], "name": r["name"], "provider": r["provider"], "frequency": r["frequency"],
                        "expected_rhythm": q.RHYTHMUS.get(r["frequency"]), "source_last_period": letzte,
                        "source_lag_months": akt["source"]["lag_months"] if akt["source"] else None,
                        "source_stale": bool(akt["source"] and akt["source"]["stale"]),
                        "source_updated": (r["meta"] or {}).get("stand_quelle"), "fetch": abruf,
                        "window": {"periods": len(fen), "from": fen[0] if fen else None, "to": fen[-1] if fen else None,
                                   "share": q.anteil(fenster_ist, len(fen) * len(akt["geos"]))},
                        "status_counts": dict(sorted(zahl.items())), "geos": auffaellig})
        jq = je_quelle.setdefault(r["provider"] or "unbekannt", {"provider": r["provider"] or "unbekannt", "series": 0, "last_fetch": None,
                                                                   "overdue_series": 0, "stale_series": 0, "stale_geo_series": 0})
        jq["series"] += 1
        if abruf:
            jq["last_fetch"] = max(jq["last_fetch"] or "", abruf["fetched"])
            jq["overdue_series"] += abruf["overdue"]
        jq["stale_series"] += bool(akt["source"] and akt["source"]["stale"])
        jq["stale_geo_series"] += any(x["status"] in ("stale", "dormant") for x in auffaellig)
    laeufe = [dict(x) for x in conn.execute(text(
        "SELECT adapter, max(finished_at) FILTER (WHERE status = 'ok') AS last_ok, max(started_at) FILTER (WHERE status <> 'ok') AS last_failed, "
        "count(*) FILTER (WHERE status <> 'ok') AS failed FROM international.ingestion_run GROUP BY adapter ORDER BY adapter")).mappings()]
    for x in laeufe:
        for k in ("last_ok", "last_failed"):
            x[k] = x[k].isoformat() if x[k] else None
    geo_zahl = {}
    for f in frische:
        for k, n in f["status_counts"].items():
            geo_zahl[k] = geo_zahl.get(k, 0) + n

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
                  "jump_checked_latest": q.SPRUNG_LETZTE, "dormant_after_months": q.RUHEND_MONATE, "window_periods": q.FENSTER,
                  "expected_rhythm": q.RHYTHMUS, "fetch_max_age_days": q.ABRUF_MAX_TAGE,
                  "known_not_published": [{"provider": k[0], "geo": k[1], "reason": v} for k, v in q.BEKANNT.items()]},
        "summary": {"open_flags": sum(f["open"] for f in flags), "stale_series": len(veraltet), "jumps": len(spruenge),
                    "uncleared_sources_with_data": len(quellen),
                    "series_with_stale_geos": sum(1 for f in frische if any(x["status"] in ("stale", "dormant") for x in f["geos"])),
                    "geo_series_by_status": dict(sorted(geo_zahl.items())),
                    "fetch_overdue_series": sum(1 for f in frische if f["fetch"] and f["fetch"]["overdue"])},
        "flags": flags,
        "fact_quality": fakten,
        "stale_series": veraltet,
        "freshness": {"basis": "je Reihe und Gebiet der letzte beobachtete Zeitraum (ohne Projektionen), gemessen am Stichtag; "
                               "geos nennt nur Gebiete, die nicht aktuell sind oder Lücken haben; window.share ist der Anteil vorhandener Werte "
                               "im Vergleichszeitraum über alle erwarteten Gebiete",
                      "by_provider": sorted(je_quelle.values(), key=lambda x: x["provider"]), "import_runs": laeufe, "rows": frische},
        "jumps": spruenge,
        "coverage": {
            "series": {"denominator_basis": "je Reihe die bei der Quelle angefragten Gebiete (rows[].expected), nicht die Vereinigung "
                                            "aller Gebiete irgendeiner Reihe",
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
