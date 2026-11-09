"""Gemeinsame Bausteine der Endpunkte: Datenbankverbindung je Anfrage, Antwort-Hülle, Pagination, Branchenkatalog."""
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, HTTPException, Request
from sqlalchemy import text

from ..db import engine

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "app"))
import register as _register  # noqa: E402  (Branchenbezeichnungen: eine Quelle für Oberfläche und API)

BRANCHEN = dict(_register.BRANCHEN)
# Synonyme und Abkürzungen für die Suche (klein geschrieben) -> Branchen-ID
BRANCHEN_SYNONYME = {
    "auto": "automobil", "autos": "automobil", "automobile": "automobil", "automotive": "automobil", "kfz": "automobil", "fahrzeuge": "automobil",
    "bank": "banken", "kreditinstitute": "banken", "sparkasse": "banken", "sparkassen": "banken", "volksbank": "banken",
    "versicherung": "versicherungen", "insurance": "versicherungen", "pharma": "pharma-gesundheit", "gesundheit": "pharma-gesundheit",
    "chemie": "chemie-rohstoffe", "rohstoffe": "chemie-rohstoffe", "software": "software-it", "it": "software-it", "tech": "technologie",
    "telekom": "telekom-medien", "medien": "telekom-medien", "energie": "energie", "versorger": "energie-versorger", "strom": "energie-versorger",
    "handel": "handel-konsum", "konsum": "handel-konsum", "logistik": "transport-logistik", "transport": "transport-logistik",
    "immobilie": "immobilien", "real estate": "immobilien", "industrial": "industrie", "maschinenbau": "industrie",
}
LAND_SYNONYME = {"uk": "GB", "england": "GB", "großbritannien": "GB", "grossbritannien": "GB", "usa": "US", "vereinigte staaten": "US",
                 "amerika": "US", "brd": "DE", "schweiz": "CH", "holland": "NL", "südkorea": "KR", "suedkorea": "KR", "korea": "KR",
                 "eu": None}


def verbindung(request: Request):
    """Eine read-only-Verbindung je Anfrage (Pool), wird nach der Antwort zurückgegeben."""
    eng = engine(request.app.state.einstellungen)
    with eng.connect() as conn:
        yield conn


DB = Depends(verbindung)


def jetzt():
    return datetime.now(timezone.utc)


def meta(request: Request, **extra):
    m = {"api_version": "1", "generated_at": jetzt(), "notes": []}
    m.update({k: v for k, v in extra.items() if v is not None})
    return m


def seite(total, page, page_size):
    return {"page": page, "page_size": page_size, "total": total, "pages": max(1, -(-total // page_size))}


def seitengroesse(request: Request, page_size: int):
    grenze = request.app.state.einstellungen.max_page_size
    if page_size > grenze:
        raise HTTPException(422, detail={"code": "seitengroesse", "message": f"page_size höchstens {grenze}"})
    return page_size


def register_stand(conn):
    """Zeitpunkt des letzten erfolgreichen Imports der Unternehmenstabelle und die Datei (für meta.data_as_of / source)."""
    r = conn.execute(text("SELECT file, imported_at FROM international.register_import ORDER BY id DESC LIMIT 1")).first()
    return (r.file, r.imported_at) if r else (None, None)
