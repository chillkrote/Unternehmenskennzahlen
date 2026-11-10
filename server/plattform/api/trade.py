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
QUELLE_IMPORT = "CEPII BACI (Etalab 2.0), app/data/gueter_importe.json"
HINWEIS_IMPORT = ("Importwerte aus der vollständigen bilateralen Matrix von BACI (abgeglichene Spiegelstatistik, FOB); sie weichen von nationalen "
                  "Importstatistiken (CIF, Ursprungsland) ab. supplier_hhi rechnet über alle zuordenbaren Lieferländer, nicht nur die aufgelisteten.")


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
    m["notes"] = [HINWEIS, f"Jahr {year}; Werte in Mio. US-Dollar.", h.BAENDER_HINWEIS,
                  "HHI und CR3 beschreiben hier die Konzentration der weltweiten Exporte, nicht die Abhängigkeit eines einzelnen Importlands "
                  "(dafür: /trade/import-dependencies)."]
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
        voll = conn.execute(text("SELECT partners, partner_hhi FROM international.trade_export WHERE good_id = :g AND geo = :geo AND year = :y"),
                            {"g": g["id"], "geo": geo, "y": y}).first()
        a = h.anteile(w)
        rang = 1 + sum(1 for k, v in w.items() if v > w[geo])
        partner = [dict(r) for r in conn.execute(text(
            "SELECT rank, partner, value FROM international.trade_partner WHERE good_id = :g AND geo = :geo AND year = :y ORDER BY rank"),
            {"g": g["id"], "geo": geo, "y": y}).mappings()]
        pw = {p["partner"]: p["value"] for p in partner}
        zeilen.append({"good": g["id"], "name": g["name"], "area": g["area"], "value": w[geo], "world_share": round(a[geo], 4), "rank": rang,
                       "partners": partner, "top5_partner_share": round(sum(pw.values()) / w[geo], 4) if partner else None,
                       "partner_count": voll.partners if voll else None,
                       "partner_hhi": voll.partner_hhi if voll else None,
                       "partner_hhi_complete": bool(voll and voll.partner_hhi is not None),
                       "partner_hhi_lower_bound": h.hhi_untergrenze(pw, w[geo]) if partner else None})
    if not zeilen:
        raise HTTPException(404, detail={"code": "nicht_gefunden", "message": f"Keine Exporte für {geo} im Jahr {y}"})
    m = _meta(request, conn, y)
    m["notes"].append("partner_hhi rechnet über alle Abnehmerländer (partner_count) und liegt nur für das letzte Jahr vor. "
                      "partner_hhi_lower_bound ist die Untergrenze aus den fünf aufgelisteten Abnehmern (Anteile an den gesamten Exporten); "
                      "das frühere Feld partner_hhi_top5 (Anteile nur unter den fünf, dadurch überzeichnet) ist entfallen.")
    return {"data": {"geo": geo, "year": y, "goods": zeilen}, "meta": m}


def _import_jahr(conn, year):
    j = conn.execute(text("SELECT max(year) FROM international.trade_import")).scalar()
    if j is None:
        raise HTTPException(404, detail={"code": "keine_daten", "message": "Keine Importdaten geladen (app/data/gueter_importe.json fehlt)"})
    return year or j


@router.get("/trade/import-dependencies", response_model=Antwort[dict],
            summary="Importabhängigkeit eines Landes: Lieferländer je Gut, Anteil eines Lieferlands, HHI über alle Lieferländer")
def import_dependencies(request: Request, conn=DB,
                        geo: str = Query(..., pattern=r"^[A-Z]{2}$", description="Importland (ISO-Code, zwei Großbuchstaben)"),
                        supplier: Optional[str] = Query(None, pattern=r"^[A-Z]{2}$", description="Lieferland: Abhängigkeit von genau diesem Land je Gut"),
                        good: Optional[str] = Query(None, max_length=40, description="nur dieses Gut (Liste: /trade/goods)"),
                        year: Optional[int] = Query(None, ge=1995, le=2100, description="Jahr (Standard: letztes)")):
    y = _import_jahr(conn, year)
    if good:
        _gut(conn, good)
    letzt = conn.execute(text("SELECT max(year) FROM international.trade_import_supplier")).scalar()
    zeilen = conn.execute(text(
        "SELECT i.good_id, g.name, g.area, i.value, i.unallocated, i.suppliers, i.hhi, i.top_supplier, i.top_share "
        "FROM international.trade_import i JOIN international.trade_good g ON g.id = i.good_id "
        "WHERE i.geo = :geo AND i.year = :y AND (CAST(:good AS text) IS NULL OR i.good_id = :good) ORDER BY g.position"),
        {"geo": geo, "y": y, "good": good}).mappings().all()
    if not zeilen:
        raise HTTPException(404, detail={"code": "nicht_gefunden", "message": f"Keine Importe für {geo} im Jahr {y}"})
    lief = {}
    if y == letzt:
        for r in conn.execute(text("SELECT good_id, rank, supplier, value FROM international.trade_import_supplier "
                                   "WHERE geo = :geo AND year = :y ORDER BY good_id, rank"), {"geo": geo, "y": y}).mappings():
            lief.setdefault(r["good_id"], []).append(r)
    verlauf = {}
    for r in conn.execute(text("SELECT good_id, year, value, suppliers, hhi, top_supplier, top_share FROM international.trade_import "
                               "WHERE geo = :geo AND (CAST(:good AS text) IS NULL OR good_id = :good) ORDER BY good_id, year"),
                          {"geo": geo, "good": good}).mappings():
        verlauf.setdefault(r["good_id"], []).append({"year": r["year"], "value": r["value"], "suppliers": r["suppliers"], "supplier_hhi": r["hhi"],
                                                     "top_supplier": r["top_supplier"], "top_share": r["top_share"]})
    out = []
    for z in zeilen:
        l = lief.get(z["good_id"], [])
        e = {"good": z["good_id"], "name": z["name"], "area": z["area"], "import_value": z["value"],
             "unallocated_share": h.importanteil(z["unallocated"], z["value"]) or 0.0, "supplier_count": z["suppliers"],
             "supplier_hhi": z["hhi"], "supplier_hhi_complete": True, "concentration_band": h.einstufung(z["hhi"]) if z["hhi"] is not None else None,
             "top_supplier": z["top_supplier"], "top_share": z["top_share"],
             "suppliers": [{"rank": x["rank"], "geo": x["supplier"], "value": x["value"], "import_share": h.importanteil(x["value"], z["value"])} for x in l],
             "suppliers_listed_share": h.importanteil(sum(x["value"] for x in l), z["value"]) if l else None,
             "history": verlauf.get(z["good_id"], [])}
        if supplier:
            treffer = next((x for x in l if x["supplier"] == supplier), None)
            if treffer:
                e["dependency"] = {"supplier": supplier, "import_share": h.importanteil(treffer["value"], z["value"]), "value": treffer["value"],
                                   "rank": treffer["rank"], "basis": "belegt"}
            elif y != letzt:
                e["dependency"] = {"supplier": supplier, "import_share": z["top_share"] if z["top_supplier"] == supplier else None, "value": None,
                                   "rank": 1 if z["top_supplier"] == supplier else None,
                                   "basis": "belegt (größtes Lieferland)" if z["top_supplier"] == supplier else
                                            f"für {y} ist nur das größte Lieferland gespeichert; einzelne Lieferländer nur für {letzt}"}
            else:
                grenze = h.importanteil(l[-1]["value"], z["value"]) if len(l) >= 10 else 0.0
                e["dependency"] = {"supplier": supplier, "import_share": None if len(l) >= 10 else 0.0, "value": None, "rank": None,
                                   "below_share": grenze, "basis": "nicht unter den zehn größten Lieferländern; Anteil höchstens below_share"
                                   if len(l) >= 10 else "kein Import aus diesem Land"}
        out.append(e)
    if supplier:
        out.sort(key=lambda e: -(e["dependency"]["import_share"] or 0))
    st = _stand(conn)
    m = meta(request, source=QUELLE_IMPORT, data_as_of=st[0])
    m["notes"] = [HINWEIS_IMPORT, f"Jahr {y}; Werte in Mio. US-Dollar. Einzelne Lieferländer (suppliers) nur für {letzt}, der Verlauf (history) "
                  "nennt je Jahr Importwert, Zahl der Lieferländer, HHI und das größte Lieferland.", h.BAENDER_HINWEIS,
                  "unallocated_share: Lieferland in der Quelle nicht zuordenbar (zählt zum Importwert, nicht zum HHI; der HHI ist dann eine Untergrenze).",
                  "Die Daten zeigen bisherige Lieferbeziehungen, keine freie Lieferkapazität anderer Länder."]
    return {"data": {"geo": geo, "year": y, "supplier": supplier, "goods": out}, "meta": m}
