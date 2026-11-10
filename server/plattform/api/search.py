"""Universelle Suche über Unternehmen, Länder, Branchen und Kennzahlen (PostgreSQL pg_trgm, kein eigener Suchserver).

Ablauf: Die Suchwörter werden zuerst als Land, Branche oder Kennzahl gedeutet (Namen, deutsche Namen, ISO-Codes, Synonyme).
Erkannte Länder und Branchen werden für die Unternehmenssuche zu Filtern, die restlichen Wörter durchsuchen Namen und Aliase
(ähnlichkeitsbasiert, fehlertolerant) sowie exakte Kennungen (ID, ISIN, LEI, Ticker). „Deutschland Automobile“ liefert so
das Land, die Branche und deutsche Automobilunternehmen."""
import re
import unicodedata
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import text

from ..schemas import Antwort, Suchergebnis
from .common import BRANCHEN, BRANCHEN_SYNONYME, DB, LAND_SYNONYME, meta

router = APIRouter(tags=["Suche"])
TYPEN = ("company", "country", "sector", "indicator")


def _ohne_akzent(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def _laender(conn, woerter):
    """Wort (oder Wortpaar) -> Land, über ISO-Codes, englische/deutsche Namen und Synonyme."""
    treffer, verbraucht = [], set()
    kandidaten = [(i, i + 1, woerter[i]) for i in range(len(woerter))] + [(i, i + 2, woerter[i] + " " + woerter[i + 1]) for i in range(len(woerter) - 1)]
    for a, b, w in sorted(kandidaten, key=lambda t: t[0] - t[1]):           # Wortpaare zuerst
        if any(i in verbraucht for i in range(a, b)):
            continue
        code = LAND_SYNONYME.get(w)
        if code is None and len(w) >= 2:
            r = conn.execute(text("""
                SELECT iso2 FROM international.country
                 WHERE lower(iso2) = :w OR lower(COALESCE(iso3,'')) = :w OR lower(name) = :w OR lower(COALESCE(name_de,'')) = :w
                 ORDER BY (lower(iso2) = :w) DESC LIMIT 1"""), {"w": w}).first() if (len(w) > 3 or len(w) in (2, 3) and w.isalpha()) else None
            code = r[0] if r else None
            if code and len(w) == 2 and w in ("in", "an", "am", "im", "um", "es", "de", "it", "be", "no", "is", "at", "to", "so"):
                # zweibuchstabige Wörter nur als Code werten, wenn sie in Großschrift eingegeben wurden (siehe _deuten)
                code = None
        if code:
            treffer.append(code)
            verbraucht.update(range(a, b))
    return treffer, verbraucht


def _branche(w):
    w2 = _ohne_akzent(w)
    if w in BRANCHEN:
        return w
    if w in BRANCHEN_SYNONYME:
        return BRANCHEN_SYNONYME[w]
    for bid, name in BRANCHEN.items():
        n = name.lower()
        if len(w) >= 4 and (w == n or n.startswith(w) or w2 == _ohne_akzent(n)):
            return bid
    return None


@router.get("/search", response_model=Antwort[Suchergebnis], summary="Eine Suche über alle Datenbereiche")
def search(request: Request, conn=DB,
           q: str = Query(..., min_length=1, max_length=120, description="Suchtext, z. B. „Deutschland Automobile“ oder eine ISIN"),
           types: Optional[str] = Query(None, description="kommagetrennt: company,country,sector,indicator (Standard: alle)"),
           limit: int = Query(8, ge=1, le=50, description="Treffer je Gruppe")):
    typen = TYPEN if not types else tuple(t.strip() for t in types.split(",") if t.strip())
    if any(t not in TYPEN for t in typen):
        raise HTTPException(422, detail={"code": "typen", "message": f"types nur aus {list(TYPEN)}"})
    roh = q.strip()
    gross = {w for w in re.split(r"\s+", roh) if re.fullmatch(r"[A-Z]{2,3}", w)}
    woerter = [w for w in re.split(r"\s+", roh.lower()) if w]
    laender, verbraucht = _laender(conn, woerter)
    for w in gross:                                        # „DE“, „IT“ in Großschrift sind eindeutig Ländercodes
        r = conn.execute(text("SELECT iso2 FROM international.country WHERE iso2 = :w OR iso3 = :w"), {"w": w}).first()
        if r and r[0] not in laender:
            laender.append(r[0])
            verbraucht.update(i for i, x in enumerate(woerter) if x == w.lower())
    branchen = []
    for i, w in enumerate(woerter):
        if i in verbraucht:
            continue
        b = _branche(w)
        if b:
            branchen.append(b)
            verbraucht.add(i)
    rest = " ".join(w for i, w in enumerate(woerter) if i not in verbraucht)
    gruppen = {}

    if "country" in typen:
        rows = conn.execute(text("""
            SELECT c.iso2, c.name, c.name_de, c.region, (SELECT count(*) FROM international.company_register r WHERE r.active AND r.domicile = c.iso2) AS n,
                   GREATEST(similarity(lower(c.name), :q), similarity(lower(COALESCE(c.name_de,'')), :q)) AS s
              FROM international.country c
             WHERE c.iso2 = ANY(:codes) OR lower(c.name) % :q OR lower(COALESCE(c.name_de,'')) % :q
                OR lower(c.name) LIKE :p OR lower(COALESCE(c.name_de,'')) LIKE :p
             ORDER BY (c.iso2 = ANY(:codes)) DESC, s DESC LIMIT :lim"""),
            {"codes": laender, "q": roh.lower(), "p": roh.lower() + "%", "lim": limit}).mappings().all()
        gruppen["country"] = [{"type": "country", "id": r["iso2"], "label": r["name_de"] or r["name"],
                               "detail": f"{r['region'] or ''} · {r['n']:,} Unternehmen".replace(",", ".").strip(" ·"),
                               "score": 1.0 if r["iso2"] in laender else round(float(r["s"]), 3), "link": f"/api/v1/countries/{r['iso2']}"} for r in rows]

    if "sector" in typen:
        sek = list(dict.fromkeys(branchen + [b for b in (_branche(w) for w in woerter) if b]))
        if not sek:
            sek = [b for b, n in BRANCHEN.items() if roh.lower() in n.lower() or roh.lower() in b][:limit]
        zaehl = dict(conn.execute(text("SELECT sector, count(*) FROM international.company_register WHERE active AND sector = ANY(:s) GROUP BY 1"), {"s": sek}).all()) if sek else {}
        gruppen["sector"] = [{"type": "sector", "id": b, "label": BRANCHEN[b], "detail": f"{zaehl.get(b, 0):,} Unternehmen".replace(",", "."),
                              "score": 1.0, "link": f"/api/v1/companies?sector={b}"} for b in sek[:limit]]

    if "indicator" in typen:
        rows = conn.execute(text("""
            SELECT code, description, GREATEST(similarity(lower(description), :q), similarity(code, :q)) AS s FROM international.metric
             WHERE lower(description) LIKE :p OR code LIKE :p OR lower(description) % :q ORDER BY s DESC LIMIT :lim"""),
            {"q": roh.lower(), "p": "%" + roh.lower() + "%", "lim": limit}).mappings().all()
        gruppen["indicator"] = [{"type": "indicator", "id": r["code"], "label": r["description"].split(";")[0][:90], "detail": r["code"],
                                 "score": round(float(r["s"]), 3), "link": f"/api/v1/indicators#{r['code']}"} for r in rows]

    if "company" in typen:
        par = {"lim": limit, "codes": laender or None, "sek": branchen or None}
        filt = " AND (CAST(:codes AS text[]) IS NULL OR r.domicile = ANY(CAST(:codes AS text[])))" \
               " AND (CAST(:sek AS text[]) IS NULL OR r.sector = ANY(CAST(:sek AS text[])))"
        if rest:
            par.update(q=rest, qu=rest.upper(), p=rest + "%")
            sql = f"""
              WITH kand AS (
                SELECT r.row_key, 2.0 AS s FROM international.company_register r
                 WHERE r.active AND (r.entity_id = :qu OR r.isin = :qu OR r.lei = :qu OR lower(COALESCE(r.ticker,'')) = :q)
                UNION ALL
                SELECT r.row_key, similarity(lower(r.name), :q) + CASE WHEN lower(r.name) LIKE :p THEN 0.5 ELSE 0 END
                  FROM international.company_register r WHERE r.active AND (lower(r.name) % :q OR lower(r.name) LIKE :p)
                UNION ALL
                SELECT a.row_key, similarity(lower(a.alias), :q) * 0.9 FROM international.company_alias a WHERE lower(a.alias) % :q)
              SELECT r.entity_id, r.name, r.domicile, r.sector, r.listed, r.isin, max(k.s) AS s
                FROM kand k JOIN international.company_register r ON r.row_key = k.row_key
               WHERE r.active AND r.entity_id IS NOT NULL {filt}
               GROUP BY 1,2,3,4,5,6 ORDER BY s DESC, r.name LIMIT :lim"""
        elif laender or branchen:
            sql = f"""SELECT r.entity_id, r.name, r.domicile, r.sector, r.listed, r.isin, 1.0 AS s
                        FROM international.company_register r WHERE r.active AND r.entity_id IS NOT NULL {filt}
                       ORDER BY (SELECT count(*) FROM international.fact x WHERE x.entity_id = r.entity_id) DESC, r.listed DESC, r.name LIMIT :lim"""
        else:
            sql = None
        rows = conn.execute(text(sql), par).mappings().all() if sql else []
        if (laender or branchen) and len(woerter) > 1:
            # Der ganze Text kann selbst ein Name sein („Deutsche Bank“: „Bank“ ist auch eine Branche). Namen, die mit dem
            # vollen Suchtext beginnen oder ihm sehr ähnlich sind, stehen deshalb vor den gefilterten Treffern.
            voll = conn.execute(text("""
                SELECT r.entity_id, r.name, r.domicile, r.sector, r.listed, r.isin,
                       similarity(lower(r.name), :q) + CASE WHEN lower(r.name) LIKE :p THEN 0.5 ELSE 0 END AS s
                  FROM international.company_register r
                 WHERE r.active AND r.entity_id IS NOT NULL AND (lower(r.name) LIKE :p OR lower(r.name) % :q)
                 ORDER BY s DESC, length(r.name), r.name LIMIT :lim"""), {"q": roh.lower(), "p": roh.lower() + "%", "lim": limit}).mappings().all()
            vorne = [r for r in voll if float(r["s"]) >= 0.9]
            ids = {r["entity_id"] for r in vorne}
            rows = (vorne + [r for r in rows if r["entity_id"] not in ids])[:limit]
        gruppen["company"] = [{"type": "company", "id": r["entity_id"], "label": r["name"],
                               "detail": " · ".join(x for x in (r["domicile"] or "?", BRANCHEN.get(r["sector"], r["sector"]),
                                                                  "börsennotiert" if r["listed"] else "nicht notiert", r["isin"] or "") if x),
                               "score": round(float(r["s"]), 3), "link": f"#firma-{r['entity_id']}"} for r in rows]

    interpretiert = {k: v for k, v in (("countries", laender), ("sectors", branchen), ("text", rest)) if v}
    return {"data": {"query": roh, "interpreted": interpretiert, "groups": gruppen}, "meta": meta(request)}
