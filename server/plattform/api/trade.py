"""Handel (P5a): Konzentration je Gut, Länderprofil und Alternativlieferländer aus CEPII BACI (Regeln: plattform/handel.py).

Belegt: Exportwerte je Land und die fünf größten Abnehmer je Exportland (BACI). Abgeleitet: Weltmarktanteile, HHI, CR3,
Alternativen – Rechnungen auf den belegten Werten, keine eigenen Erhebungen.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import text

from .. import handel as h
from ..schemas import Antwort
from .common import DB, meta

router = APIRouter(tags=["Handel"])
QUELLE = "CEPII BACI (Etalab 2.0), app/data/gueter.json"
HINWEIS = "Weltmarktanteile, HHI, CR3 und Alternativen sind abgeleitet; belegt sind Exportwerte und die fünf größten Abnehmer je Exportland."


def _stand(conn):
    return conn.execute(text("SELECT finished_at, watermark->>'jahr' FROM international.ingestion_run WHERE adapter = 'handel' AND status = 'ok' "
                             "ORDER BY id DESC LIMIT 1")).first() or (None, None)


def _jahr(conn, year):
    j = conn.execute(text("SELECT max(year) FROM international.trade_export")).scalar()
    if j is None:
        raise HTTPException(404, detail={"code": "keine_daten", "message": "Keine Handelsdaten geladen"})
    return year or j


def _werte(conn, good, year):
    return {g: v for g, v in conn.execute(text("SELECT geo, value FROM international.trade_export WHERE good_id = :g AND year = :y"),
                                          {"g": good, "y": year})}


def _gut(conn, good):
    g = conn.execute(text("SELECT id, name, area, hs FROM international.trade_good WHERE id = :g"), {"g": good}).mappings().first()
    if not g:
        raise HTTPException(404, detail={"code": "nicht_gefunden", "message": f"Kein Gut {good!r} (Liste: /trade/goods)"})
    return dict(g)


def _meta(request, conn, year):
    st = _stand(conn)
    m = meta(request, source=QUELLE, data_as_of=st[0])
    m["notes"] = [HINWEIS, f"Jahr {year}; Werte in Mio. US-Dollar."]
    return m


@router.get("/trade/goods", response_model=Antwort[list[dict]], summary="Gütergruppen mit Weltwert, Konzentration (HHI) und größtem Exportland")
def goods(request: Request, conn=DB, year: Optional[int] = Query(None, ge=1995, le=2100, description="Jahr (Standard: letztes)")):
    y = _jahr(conn, year)
    out = []
    for g in conn.execute(text("SELECT id, name, area, hs FROM international.trade_good ORDER BY position")).mappings():
        w = _werte(conn, g["id"], y)
        a = h.anteile(w)
        top = max(a.items(), key=lambda x: x[1]) if a else (None, 0)
        hh = h.hhi(w)
        out.append({**dict(g), "year": y, "world_value": round(sum(w.values()), 1), "exporters": len(a), "hhi": hh, "concentration": h.einstufung(hh),
                    "cr3": h.cr(w), "top_exporter": top[0], "top_share": round(top[1], 4)})
    return {"data": out, "meta": _meta(request, conn, y)}


@router.get("/trade/goods/{good}", response_model=Antwort[dict], summary="Ein Gut: Weltmarktanteile aller Exportländer, HHI im Zeitverlauf")
def good(request: Request, good: str, conn=DB, year: Optional[int] = Query(None, ge=1995, le=2100),
         top: int = Query(20, ge=1, le=250, description="so viele Exportländer in der Liste")):
    g, y = _gut(conn, good), _jahr(conn, year)
    w = _werte(conn, good, y)
    a = h.anteile(w)
    liste = sorted(a.items(), key=lambda x: (-x[1], x[0]))
    verlauf = []
    for (j,) in conn.execute(text("SELECT DISTINCT year FROM international.trade_export WHERE good_id = :g ORDER BY year"), {"g": good}):
        wj = _werte(conn, good, j)
        verlauf.append({"year": j, "world_value": round(sum(wj.values()), 1), "hhi": h.hhi(wj), "cr3": h.cr(wj)})
    hh = h.hhi(w)
    d = {**g, "year": y, "world_value": round(sum(w.values()), 1), "hhi": hh, "concentration": h.einstufung(hh), "cr3": h.cr(w),
         "exporters": [{"rank": i + 1, "geo": k, "value": w[k], "world_share": round(s, 4)} for i, (k, s) in enumerate(liste[:top])],
         "exporters_total": len(liste), "history": verlauf}
    return {"data": d, "meta": _meta(request, conn, y)}


@router.get("/trade/goods/{good}/alternatives", response_model=Antwort[dict], summary="Alternativlieferländer ohne die genannten Exportländer")
def alternatives(request: Request, good: str, conn=DB, exclude: str = Query(..., pattern=r"^[A-Z]{2}(,[A-Z]{2}){0,9}$", description="z. B. CN oder CN,RU"),
                 year: Optional[int] = Query(None, ge=1995, le=2100), n: int = Query(5, ge=1, le=30)):
    g, y = _gut(conn, good), _jahr(conn, year)
    w, ohne = _werte(conn, good, y), exclude.split(",")
    a = h.anteile(w)
    d = {**g, "year": y, "excluded": [{"geo": k, "world_share": round(a.get(k, 0.0), 4)} for k in ohne],
         "excluded_share": round(sum(a.get(k, 0.0) for k in ohne), 4), "alternatives": h.alternativen(w, ohne, n),
         "hhi_without_excluded": h.hhi({k: v for k, v in w.items() if k not in ohne})}
    m = _meta(request, conn, y)
    m["notes"].append("Alternativen zeigen vorhandene Exportkapazität anderer Länder, keine freie Kapazität oder Lieferbereitschaft.")
    return {"data": d, "meta": m}


@router.get("/trade/countries/{geo}", response_model=Antwort[dict], summary="Ein Exportland: Weltmarktanteil, Rang und Abnehmerkonzentration je Gut")
def country(request: Request, geo: str, conn=DB, year: Optional[int] = Query(None, ge=1995, le=2100)):
    if not (len(geo) == 2 and geo.isalpha() and geo.isupper()):
        raise HTTPException(422, detail={"code": "geo", "message": "geo als ISO-Code mit zwei Großbuchstaben"})
    y = _jahr(conn, year)
    zeilen = []
    for g in conn.execute(text("SELECT id, name, area FROM international.trade_good ORDER BY position")).mappings():
        w = _werte(conn, g["id"], y)
        if not w.get(geo):
            continue
        a = h.anteile(w)
        rang = 1 + sum(1 for k, v in w.items() if v > w[geo])
        partner = [dict(r) for r in conn.execute(text(
            "SELECT rank, partner, value FROM international.trade_partner WHERE good_id = :g AND geo = :geo AND year = :y ORDER BY rank"),
            {"g": g["id"], "geo": geo, "y": y}).mappings()]
        pw = {p["partner"]: p["value"] for p in partner}
        zeilen.append({"good": g["id"], "name": g["name"], "area": g["area"], "value": w[geo], "world_share": round(a[geo], 4), "rank": rang,
                       "partners": partner, "top5_partner_share": round(sum(pw.values()) / w[geo], 4) if partner else None,
                       "partner_hhi_top5": h.hhi(pw) if partner else None})
    if not zeilen:
        raise HTTPException(404, detail={"code": "nicht_gefunden", "message": f"Keine Exporte für {geo} im Jahr {y}"})
    m = _meta(request, conn, y)
    m["notes"].append("partner_hhi_top5 ist nur über die fünf größten Abnehmer gerechnet und überzeichnet daher die Konzentration; "
                      "top5_partner_share zeigt, welchen Teil der Exporte sie abdecken.")
    return {"data": {"geo": geo, "year": y, "goods": zeilen}, "meta": m}
