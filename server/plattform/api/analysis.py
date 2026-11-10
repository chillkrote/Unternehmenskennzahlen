"""Analyse (P4): Korrelation zweier VWL-Reihen mit denselben Regeln wie die Oberfläche (plattform/analyse.py), Export als CSV."""
import csv
import io
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy import text

from .. import analyse as an
from ..schemas import Antwort
from .common import DB, meta

router = APIRouter(tags=["Analyse"])
REIHE = r"^[a-z0-9_]{1,60}:[A-Z0-9_]{2,12}$"
TRANS = "^(auto|" + "|".join(an.TRANSFORMATIONEN) + ")$"


def _reihe(conn, spec, name):
    sid, geo = spec.split(":")
    s = conn.execute(text("SELECT id, name, unit, frequency, kind, forecast_from FROM international.series WHERE id = :id"), {"id": sid}).mappings().first()
    if not s:
        raise HTTPException(404, detail={"code": "nicht_gefunden", "message": f"{name}: keine Reihe {sid!r} (Katalog: /series)"})
    if s["frequency"] not in an.RANG:
        raise HTTPException(422, detail={"code": "frequenz", "message": f"{name}: Frequenz {s['frequency']!r} wird nicht unterstützt"})
    pts = [[p, v] for p, v in conn.execute(text(
        "SELECT period, value FROM international.observation WHERE series_id = :id AND geo = :geo AND valid_to IS NULL "
        "AND (CAST(:pa AS text) IS NULL OR period COLLATE \"C\" < :pa) ORDER BY period COLLATE \"C\""),
        {"id": sid, "geo": geo, "pa": s["forecast_from"]})]                     # Projektionen sind keine Beobachtungen
    if not pts:
        raise HTTPException(404, detail={"code": "keine_werte", "message": f"{name}: keine Werte für {sid} in {geo}"})
    return {"id": sid, "geo": geo, "name": s["name"], "unit": s["unit"], "freq": s["frequency"], "kind": s["kind"], "pts": pts,
            "projections_excluded": bool(s["forecast_from"])}


def _csv(zeilen, kopf):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    w.writerow(kopf)
    w.writerows(zeilen)
    return Response("﻿" + buf.getvalue(), media_type="text/csv; charset=utf-8")


@router.get("/analysis/correlation", summary="Korrelation zweier VWL-Reihen (Pearson, Spearman, p-Werte, n_eff, Kreuzkorrelation)")
def correlation(request: Request, conn=DB,
                a: str = Query(..., pattern=REIHE, description="Reihe A als reihe:gebiet, z. B. bip_yoy:DE"),
                b: str = Query(..., pattern=REIHE, description="Reihe B als reihe:gebiet"),
                freq: str = Query("auto", pattern="^(auto|A|Q|M)$", description="gemeinsame Frequenz; auto = die gröbere der beiden"),
                ta: str = Query("auto", pattern=TRANS, description="Transformation A: " + ", ".join(an.TRANSFORMATIONEN)),
                tb: str = Query("auto", pattern=TRANS, description="Transformation B"),
                agg: str = Query("auto", pattern="^(auto|mittel|letzter)$", description="Umrechnung auf gröbere Frequenz"),
                lag: int = Query(0, ge=-12, le=12, description="B wird um so viele Perioden verschoben (positiv: B folgt A)"),
                from_: Optional[int] = Query(None, alias="from", ge=1900, le=2100, description="ab Jahr"),
                to: Optional[int] = Query(None, ge=1900, le=2100, description="bis Jahr"),
                method: str = Query("pearson", pattern="^(pearson|spearman)$", description="Maß der Kreuzkorrelation"),
                format: str = Query("json", pattern="^(json|csv)$", description="csv: gepaarte Werte als Tabelle (Semikolon, UTF-8)")):
    ra, rb = _reihe(conn, a, "a"), _reihe(conn, b, "b")
    try:
        e = an.korrelation(ra, rb, freq, ta, tb, agg, lag, from_ or 0, to or 0, method)
    except ValueError as x:
        raise HTTPException(422, detail={"code": "frequenz", "message": str(x)})
    if format == "csv":
        return _csv([[r["period_a"], r["period_b"], r["a"], r["b"]] for r in e["rows"]],
                     ["zeitraum_a", "zeitraum_b", f"{a} ({e['a']['transform']})", f"{b} ({e['b']['transform']})"])
    for k, r in (("a", ra), ("b", rb)):
        e[k].update({"series_id": r["id"], "geo": r["geo"], "name": r["name"], "unit": r["unit"], "frequency": r["freq"],
                     "projections_excluded": r["projections_excluded"]})
    m = meta(request, source="international.observation (aktueller Stand)")
    m["notes"] = ["Gleiche Rechenregeln wie die Korrelationsansicht im Terminal (KOR); p-Werte ohne Korrektur für Mehrfachtests.",
                  "Bei autokorrelierten Reihen gilt p_eff (effektive Stichprobe nach Bartlett) statt p."]
    return {"data": e, "meta": m}
