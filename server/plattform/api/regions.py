"""Regionen (Revision 0009): NUTS-3-Gebiete mit amtlichem Landesschlüssel, Werte einer Reihe über alle Regionen eines Jahres
(Querschnitt für Karten) und Zusammenhang zweier Regionalreihen im Querschnitt (dieselbe Statistik wie /analysis/correlation).

Werte stehen in series/observation (geo = NUTS-3-Code); Reihen der Ebene stehen in series.meta.ebene = "nuts3".
Gebiete lassen sich über den NUTS-Code (DE111) oder den Landesschlüssel (Kreisschlüssel 08111) ansprechen.
"""
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import text

from .. import analyse as an
from ..schemas import Antwort
from .common import DB, meta

router = APIRouter(tags=["Regionen"])
CODE = r"^[A-Z0-9]{2,10}$"
REIHE = r"^[a-z0-9_]{1,60}$"
SPALTEN = "code, level, country, national_code, name, name_source, parent, classification"


def _stand(conn):
    return conn.execute(text("SELECT finished_at FROM international.ingestion_run WHERE adapter IN ('regionen', 'vwl_regional') AND status = 'ok' "
                             "ORDER BY id DESC LIMIT 1")).scalar()


def _region(conn, code):
    if not re.match(CODE, code):
        raise HTTPException(422, detail={"code": "code", "message": "Code: NUTS-3 (DE111) oder Landesschlüssel (08111)"})
    r = conn.execute(text(f"SELECT {SPALTEN} FROM international.region WHERE code = :c OR national_code = :c ORDER BY code = :c DESC LIMIT 1"),
                     {"c": code}).mappings().first()
    if not r:
        raise HTTPException(404, detail={"code": "nicht_gefunden", "message": f"Keine Region {code!r} (Liste: /regions)"})
    return dict(r)


def _reihe(conn, sid):
    if not re.match(REIHE, sid):
        raise HTTPException(422, detail={"code": "series", "message": "series: Kennung einer Regionalreihe (Katalog: /series?level=nuts3)"})
    s = conn.execute(text("SELECT id, name, unit, kind, frequency, provider, dataset, note, meta->>'stand_quelle' AS source_updated "
                          "FROM international.series WHERE id = :id AND meta->>'ebene' = 'nuts3'"), {"id": sid}).mappings().first()
    if not s:
        raise HTTPException(404, detail={"code": "nicht_gefunden", "message": f"Keine Regionalreihe {sid!r} (Katalog: /series?level=nuts3)"})
    return dict(s)


def _querschnitt(conn, sid, jahr, country, parent=None):
    """{code: wert} einer Reihe für ein Jahr (ohne Jahr: jüngstes Jahr mit Werten) über alle Regionen des Staats; dazu das Jahr."""
    if jahr is None:
        jahr = conn.execute(text("SELECT max(o.period) FROM international.observation o JOIN international.region r ON r.code = o.geo "
                                 "WHERE o.series_id = :s AND o.valid_to IS NULL AND r.country = :c"), {"s": sid, "c": country}).scalar()
    werte = {g: v for g, v in conn.execute(text(
        "SELECT o.geo, o.value FROM international.observation o JOIN international.region r ON r.code = o.geo "
        "WHERE o.series_id = :s AND o.period = :p AND o.valid_to IS NULL AND r.country = :c AND (CAST(:pa AS text) IS NULL OR r.parent = :pa) "
        "ORDER BY o.geo"), {"s": sid, "p": jahr, "c": country, "pa": parent})}
    return jahr, werte


@router.get("/regions", response_model=Antwort[list[dict]], summary="Regionen (NUTS-3) mit Landesschlüssel und übergeordnetem Gebiet")
def regions(request: Request, conn=DB, country: str = Query("DE", pattern=r"^[A-Z]{2}$", description="Staat (ISO-2, Eurostat-Schreibweise)"),
            parent: Optional[str] = Query(None, pattern=r"^[A-Z]{2}-[A-Z0-9]{1,3}$", description="nur Regionen dieses Gebiets (DE-BW)")):
    z = conn.execute(text(f"SELECT {SPALTEN} FROM international.region WHERE country = :c AND (CAST(:p AS text) IS NULL OR parent = :p) ORDER BY code"),
                     {"c": country, "p": parent}).mappings().all()
    return {"data": [dict(x) for x in z], "meta": meta(request, source="volkswirtschaft/regional/regionen.csv (Eurostat LAU-NUTS 2024)", data_as_of=_stand(conn))}


@router.get("/regions/values", response_model=Antwort[dict], summary="Werte einer Regionalreihe für alle Regionen eines Jahres (Karte), mit Rang")
def region_values(request: Request, conn=DB, series: str = Query(..., description="Regionalreihe, z. B. r3_bip_je_einwohner"),
                  year: Optional[str] = Query(None, pattern=r"^\d{4}$", description="Jahr; ohne: jüngstes Jahr mit Werten"),
                  country: str = Query("DE", pattern=r"^[A-Z]{2}$"), parent: Optional[str] = Query(None, pattern=r"^[A-Z]{2}-[A-Z0-9]{1,3}$")):
    s = _reihe(conn, series)
    jahr, werte = _querschnitt(conn, series, year, country, parent)
    erwartet = conn.execute(text("SELECT count(*) FROM international.region WHERE country = :c AND (CAST(:p AS text) IS NULL OR parent = :p)"),
                            {"c": country, "p": parent}).scalar()
    folge = sorted(werte, key=lambda g: -werte[g])
    rang = {g: i + 1 for i, g in enumerate(folge)}
    xs = sorted(werte.values())
    median = (xs[len(xs) // 2] if len(xs) % 2 else (xs[len(xs) // 2 - 1] + xs[len(xs) // 2]) / 2) if xs else None
    d = {"series": s, "year": jahr, "country": country, "parent": parent, "expected": erwartet, "covered": len(werte), "median": median,
         "values": [{"code": g, "value": werte[g], "rank": rang[g]} for g in sorted(werte)]}
    return {"data": d, "meta": meta(request, source="series/observation (Eurostat, Regionale VGR)", data_as_of=_stand(conn))}


@router.get("/regions/cross-section", response_model=Antwort[dict],
            summary="Zusammenhang zweier Regionalreihen über alle Regionen eines Jahres (Pearson, Spearman, p-Wert, Regression)")
def cross_section(request: Request, conn=DB, a: str = Query(..., description="Reihe a"), b: str = Query(..., description="Reihe b"),
                  year: Optional[str] = Query(None, pattern=r"^\d{4}$", description="Jahr; ohne: jüngstes Jahr, in dem beide Werte haben"),
                  country: str = Query("DE", pattern=r"^[A-Z]{2}$"), parent: Optional[str] = Query(None, pattern=r"^[A-Z]{2}-[A-Z0-9]{1,3}$")):
    sa, sb = _reihe(conn, a), _reihe(conn, b)
    if year is None:
        year = conn.execute(text("SELECT max(x.period) FROM international.observation x JOIN international.observation y "
                                 "ON y.geo = x.geo AND y.period = x.period AND y.series_id = :b AND y.valid_to IS NULL "
                                 "JOIN international.region r ON r.code = x.geo WHERE x.series_id = :a AND x.valid_to IS NULL AND r.country = :c"),
                            {"a": a, "b": b, "c": country}).scalar()
    _, wa = _querschnitt(conn, a, year, country, parent)
    _, wb = _querschnitt(conn, b, year, country, parent)
    codes = sorted(set(wa) & set(wb))
    st = an.stat([wa[g] for g in codes], [wb[g] for g in codes])
    # Querschnitt: Reihenfolge der Regionen ist willkürlich, Autokorrelation und Durbin-Watson sind hier ohne Bedeutung
    for k in ("durbin_watson", "autocorr_a", "autocorr_b", "n_eff", "p_eff"):
        st.pop(k, None)
    d = {"a": sa, "b": sb, "year": year, "country": country, "parent": parent, "stat": st,
         "points": [[g, wa[g], wb[g]] for g in codes],
         "notes": ["Querschnitt über Regionen eines Jahres; ein Zusammenhang ist keine Ursache (ökologischer Fehlschluss: "
                   "Aussagen gelten für Regionen, nicht für Personen)."]}
    return {"data": d, "meta": meta(request, source="series/observation (Eurostat, Regionale VGR)", data_as_of=_stand(conn))}


@router.get("/regions/{code}", response_model=Antwort[dict], summary="Eine Region mit allen Regionalreihen (Zeitreihe, letzter Wert, Rang im Staat)")
def region_eine(request: Request, code: str, conn=DB):
    r = _region(conn, code)
    reihen = conn.execute(text("SELECT id, name, unit, kind FROM international.series WHERE meta->>'ebene' = 'nuts3' ORDER BY position")).mappings().all()
    werte = {}
    for sid, per, val in conn.execute(text("SELECT series_id, period, value FROM international.observation WHERE geo = :g AND valid_to IS NULL "
                                           "ORDER BY series_id, period COLLATE \"C\""), {"g": r["code"]}):
        werte.setdefault(sid, []).append([per, val])
    aus = []
    for s in reihen:
        pts = werte.get(s["id"], [])
        letzt = pts[-1] if pts else None
        rang = n = None
        if letzt:
            rang, n = conn.execute(text(
                "SELECT count(*) FILTER (WHERE o.value > :v) + 1, count(*) FROM international.observation o JOIN international.region x ON x.code = o.geo "
                "WHERE o.series_id = :s AND o.period = :p AND o.valid_to IS NULL AND x.country = :c"),
                {"v": letzt[1], "s": s["id"], "p": letzt[0], "c": r["country"]}).one()
        aus.append({**dict(s), "points": pts, "last": letzt, "rank": rang, "of": n})
    return {"data": {**r, "series": aus}, "meta": meta(request, source="series/observation, region", data_as_of=_stand(conn))}
