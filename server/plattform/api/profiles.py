"""Unternehmensprofile (Revision 0003): Kennzahlen mit Branchenvergleich, Abschlussposten, Gremien, Dokumente, Termine.

Die Vergleichswerte rechnet die Datenbank wie bisher die Seite (app/src/unternehmen.js, viewProfil):
* Branchenmedian: Median aller Werte der Branche (lineare Interpolation wie quant() im Terminal = percentile_cont)
* Gruppenmedian: nur wenn die Gruppe mehr als zwei Unternehmen hat
* Rang: Anteil der Branchenwerte unter dem Wert, geteilt durch (n − 1), erst ab drei Werten
Optional nur Unternehmen eines Sitzlandes (wie die Länderauswahl im Terminal; ZZ = unbekannt).
"""
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import text

from ..schemas import Antwort, BranchenStatistik, Profil, ProfilKennzahl
from .common import DB, meta

router = APIRouter(tags=["Unternehmensprofile"])

ID_MUSTER = r"^U\d{6}$"
LAND = "COALESCE(p.attributes->>'land_code', 'ZZ')"

VERGLEICH = f"""
  SELECT count(*) AS n, percentile_cont(0.5) WITHIN GROUP (ORDER BY x.value) AS med, count(*) FILTER (WHERE x.value < v.value) AS unter
    FROM international.company_profile_value x JOIN international.company_profile p ON p.entity_id = x.entity_id
   WHERE x.metric_code = v.metric_code AND p.sector = :sector AND (CAST(:country AS text) IS NULL OR {LAND} = :country)"""


def _stand(conn):
    s = conn.execute(text("""
        SELECT s.imported_at, s.file_sha256, s.sources, d.object_key FROM international.profile_snapshot s
          JOIN international.source_document d ON d.id = s.source_id WHERE s.is_current""")).mappings().first()
    if not s:
        raise HTTPException(503, detail={"code": "keine_profile", "message": "Noch keine Unternehmensprofile importiert (ETL: etl.profile)"})
    return s


def _meta(request, s, notes=()):
    m = meta(request, source=f"{s['object_key']} (SHA-256 {s['file_sha256'][:12]})", data_as_of=s["imported_at"])
    m["notes"] = ["Quellen des Builds: " + ", ".join(s["sources"])] + list(notes)
    return m


def _land(country):
    if country is None:
        return None
    return country.upper()


@router.get("/profile-metrics", response_model=Antwort[list[ProfilKennzahl]], summary="Kennzahlenkatalog der Unternehmensprofile")
def profile_metrics(request: Request, conn=DB):
    s = _stand(conn)
    zeilen = conn.execute(text("""SELECT code, name, unit, fmt, metric_group AS "group", higher_is_better, help, aliases
                                    FROM international.profile_metric ORDER BY position""")).mappings().all()
    return {"data": [dict(z) for z in zeilen], "meta": _meta(request, s)}


@router.get("/companies/{company_id}/profile", response_model=Antwort[Profil], summary="Vollständiges Unternehmensprofil")
def company_profile(request: Request, company_id: str, conn=DB,
                    country: Optional[str] = Query(None, pattern=r"^[A-Za-z]{2}$", description="Vergleichsmenge auf ein Sitzland beschränken (ZZ = unbekannt)")):
    cid = company_id.upper()
    if not re.match(ID_MUSTER, cid):
        raise HTTPException(422, detail={"code": "id_format", "message": "Unternehmens-ID im Format U000123 erwartet"})
    s = _stand(conn)
    p = conn.execute(text("SELECT * FROM international.company_profile WHERE entity_id = :id"), {"id": cid}).mappings().first()
    if not p:
        raise HTTPException(404, detail={"code": "kein_profil", "message": f"Zu {cid} gibt es kein Profil mit Kennzahlen (Stammdaten: /companies/{cid})"})
    land = _land(country)
    par = {"id": cid, "sector": p["sector"], "grp": p["peer_group"], "country": land}
    n_branche, n_gruppe = conn.execute(text(f"""
        SELECT count(*), count(*) FILTER (WHERE p.peer_group = CAST(:grp AS text))
          FROM international.company_profile p WHERE p.sector = :sector AND (CAST(:country AS text) IS NULL OR {LAND} = :country)"""), par).one()
    gruppe_zeigen = p["peer_group"] is not None and n_gruppe > 2
    werte = []
    for z in conn.execute(text(f"""
        SELECT v.metric_code, v.value, s.n, s.med, s.unter, g.med AS gmed
          FROM international.company_profile_value v JOIN international.profile_metric m ON m.code = v.metric_code
          CROSS JOIN LATERAL ({VERGLEICH}) s
          CROSS JOIN LATERAL ({VERGLEICH} AND p.peer_group = CAST(:grp AS text)) g
         WHERE v.entity_id = :id ORDER BY m.position"""), par).mappings():
        werte.append({"metric": z["metric_code"], "value": z["value"], "sector_n": z["n"], "sector_median": z["med"],
                      "group_median": z["gmed"] if gruppe_zeigen else None,
                      "percentile": z["unter"] / max(1, z["n"] - 1) if z["n"] >= 3 else None})
    abschluesse, nach_id = [], {}
    for a in conn.execute(text("""SELECT id, fiscal_year, period_end, currency, source, source_url, fetched, status, part_sources
                                    FROM international.financial_statement WHERE entity_id = :id ORDER BY position"""), par).mappings():
        e = {k: a[k] for k in a.keys() if k != "id"}
        e["bilanz"], e["guv"] = {}, {}
        nach_id[a["id"]] = e
        abschluesse.append(e)
    if nach_id:
        for z in conn.execute(text("""SELECT statement_id, part, label, value FROM international.financial_statement_line
                                        WHERE statement_id = ANY(:ids) ORDER BY statement_id, part, position"""), {"ids": list(nach_id)}):
            nach_id[z[0]][z[1]][z[2]] = z[3]
    d = {"id": cid, "name": p["name"], "sector": p["sector"], "peer_group": p["peer_group"], "listed": p["listed"],
         "sector_n": n_branche, "group_n": n_gruppe, "attributes": p["attributes"], "values": werte, "series": p["series"],
         "statements": abschluesse, "governance": p["governance"], "documents": p["documents"], "report_dates": p["report_dates"],
         "links": {"self": f"/api/v1/companies/{cid}/profile", "company": f"/api/v1/companies/{cid}", "terminal": f"#firma-{cid}"}}
    notes = ["Kennzahlen: Stand des Builds (app/data/unternehmen.json); Beträge in Mio. €, Quoten als Dezimalzahl.",
             "Abschlussposten unskaliert in Berichtswährung; fehlende Posten sind nicht vorhanden, nicht null."]
    if land:
        notes.append(f"Vergleichsmenge: nur Unternehmen mit Sitzland {land}")
    return {"data": d, "meta": _meta(request, s, notes)}


@router.get("/sectors/{sector}/statistics", response_model=Antwort[BranchenStatistik], summary="Branchenkennzahlen: Median, Quartile, Spanne")
def sector_statistics(request: Request, sector: str, conn=DB,
                      group: Optional[str] = Query(None, max_length=80, description="nur diese Gruppe der Branche (z. B. Sparkassen)"),
                      country: Optional[str] = Query(None, pattern=r"^[A-Za-z]{2}$", description="nur dieses Sitzland (ZZ = unbekannt)")):
    s = _stand(conn)
    branchen = conn.execute(text("SELECT sectors FROM international.profile_snapshot WHERE is_current")).scalar_one()
    if sector not in {b["id"] for b in branchen}:
        raise HTTPException(404, detail={"code": "branche", "message": f"unbekannte Branche {sector!r}", "details": [b["id"] for b in branchen]})
    land = _land(country)
    par = {"sector": sector, "grp": group, "country": land}
    filt = f"p.sector = :sector AND (CAST(:grp AS text) IS NULL OR p.peer_group = :grp) AND (CAST(:country AS text) IS NULL OR {LAND} = :country)"
    n = conn.execute(text(f"SELECT count(*) FROM international.company_profile p WHERE {filt}"), par).scalar_one()
    zeilen = conn.execute(text(f"""
        SELECT x.metric_code AS metric, count(*) AS n, percentile_cont(0.5) WITHIN GROUP (ORDER BY x.value) AS median,
               percentile_cont(0.25) WITHIN GROUP (ORDER BY x.value) AS p25, percentile_cont(0.75) WITHIN GROUP (ORDER BY x.value) AS p75,
               min(x.value) AS min, max(x.value) AS max
          FROM international.company_profile_value x JOIN international.company_profile p ON p.entity_id = x.entity_id
          JOIN international.profile_metric m ON m.code = x.metric_code
         WHERE {filt} GROUP BY x.metric_code, m.position ORDER BY m.position"""), par).mappings().all()
    d = {"sector": sector, "group": group, "country": land, "companies": n, "metrics": [dict(z) for z in zeilen]}
    return {"data": d, "meta": _meta(request, s, ["Quartile mit linearer Interpolation (wie im Terminal)."])}
