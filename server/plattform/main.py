"""FastAPI-Anwendung: öffentliche, lesende API unter /api/v1 (OpenAPI unter /api/v1/docs und /api/v1/openapi.json).

Start lokal:  DATABASE_URL=postgresql://… uvicorn plattform.main:app --reload   (aus server/)
"""
import hashlib
import logging
import re
import threading
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy.exc import DBAPIError, OperationalError

from . import __version__
from .api import catalog, companies, misc, profiles, quality, search, series
from .config import Einstellungen

log = logging.getLogger("sphaerae.api")
ZEITSTEMPEL = re.compile(rb'"generated_at":"[^"]*"')

BESCHREIBUNG = """
Lesende API der Wirtschaftsdatenplattform **sphaerae**.

* Einheitliche Antworten: `{"data": …, "meta": {api_version, generated_at, pagination?, source?, data_as_of?, notes[]}}`,
  Fehler als `{"error": {code, message, details}}`.
* Unternehmens-IDs (`U000123`) sind dauerhaft und werden nie aus ISIN, LEI oder Ticker abgeleitet.
* Datumswerte nach ISO 8601, Zahlen unskaliert in der angegebenen Einheit, Quoten als Dezimalzahl. Fehlende Werte fehlen
  (sie werden nie als 0 geliefert).
* Begrenzungen: höchstens `API_MAX_PAGE_SIZE` Zeilen je Seite, Zeitlimit je Datenbankabfrage, Anfragen je Minute und IP.
"""


def _fehler(status, code, message, details=None, headers=None):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "details": details}}, headers=headers)


class Ratenbegrenzer:
    """Gleitendes Fenster je Client-IP, prozesslokal (ein API-Prozess je Server). Kein Redis nötig, solange nur ein Prozess läuft."""

    def __init__(self, je_minute):
        self.je_minute = je_minute
        self.fenster = defaultdict(deque)
        self.sperre = threading.Lock()

    def erlaubt(self, schluessel, jetzt=None):
        if self.je_minute <= 0:
            return True, 0
        jetzt = jetzt or time.monotonic()
        with self.sperre:
            q = self.fenster[schluessel]
            while q and q[0] <= jetzt - 60:
                q.popleft()
            if len(q) >= self.je_minute:
                return False, int(60 - (jetzt - q[0])) + 1
            q.append(jetzt)
            if len(self.fenster) > 50000:          # Speicher begrenzen: leere Fenster verwerfen
                for k in [k for k, v in self.fenster.items() if not v]:
                    del self.fenster[k]
            return True, 0


def erstellen(einstellungen: Einstellungen | None = None) -> FastAPI:
    e = einstellungen or Einstellungen()
    app = FastAPI(title="sphaerae API", version=__version__, description=BESCHREIBUNG,
                  docs_url="/api/v1/docs", redoc_url=None, openapi_url="/api/v1/openapi.json")
    app.state.einstellungen = e
    app.state.raten = Ratenbegrenzer(e.rate_limit_per_minute)

    @app.middleware("http")
    async def schutz_und_cache(request: Request, call_next):
        if request.url.path.startswith("/api/") and request.url.path != "/api/v1/health":
            ok, warten = app.state.raten.erlaubt(request.client.host if request.client else "?")
            if not ok:
                return _fehler(429, "zu_viele_anfragen", "Zu viele Anfragen; bitte kurz warten.", headers={"Retry-After": str(warten)})
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            return _fehler(405, "nur_lesend", "Die öffentliche API ist nur lesend.")
        antwort = await call_next(request)
        h = antwort.headers
        h["X-Content-Type-Options"] = "nosniff"
        h["Referrer-Policy"] = "no-referrer"
        h["X-API-Version"] = "1"
        if request.url.path == "/api/v1/docs":
            return antwort        # Swagger-Oberfläche lädt eigene Skripte; CSP setzt Caddy für die Website
        h["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        # Bedingte Anfragen: ETag über den Inhalt, 304 bei unverändertem Stand. Spart Übertragung bei Wiederholungen.
        if request.method == "GET" and antwort.status_code == 200 and h.get("content-type", "").startswith("application/json") \
                and request.url.path != "/api/v1/health":
            koerper = b"".join([teil async for teil in antwort.body_iterator])
            # Zeitstempel der Antwort (meta.generated_at) zählt nicht zum Inhalt, sonst wäre jeder ETag neu
            etag = 'W/"' + hashlib.sha1(ZEITSTEMPEL.sub(b"", koerper)).hexdigest()[:20] + '"'
            kopf = {k: v for k, v in h.items() if k.lower() != "content-length"}
            kopf.update({"ETag": etag, "Cache-Control": f"public, max-age={e.cache_seconds}"})
            if request.headers.get("if-none-match") == etag:
                return Response(status_code=304, headers={k: v for k, v in kopf.items() if k.lower() != "content-type"})
            return Response(content=koerper, status_code=200, headers=kopf, media_type="application/json")
        if request.url.path == "/api/v1/health":
            h["Cache-Control"] = "no-store"
        return antwort

    app.add_middleware(GZipMiddleware, minimum_size=1000)
    if e.cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=e.cors_origins, allow_methods=["GET", "HEAD", "OPTIONS"],
                           allow_headers=["If-None-Match"], expose_headers=["ETag", "X-API-Version", "Retry-After"], max_age=600)

    @app.exception_handler(HTTPException)
    async def http_fehler(_request, exc: HTTPException):
        d = exc.detail if isinstance(exc.detail, dict) else {"code": {404: "nicht_gefunden"}.get(exc.status_code, "fehler"), "message": str(exc.detail)}
        return _fehler(exc.status_code, d.get("code", "fehler"), d.get("message", ""), d.get("details"))

    from starlette.exceptions import HTTPException as StarletteHTTPException

    @app.exception_handler(StarletteHTTPException)
    async def starlette_fehler(_request, exc):
        return _fehler(exc.status_code, "nicht_gefunden" if exc.status_code == 404 else "fehler",
                       "Unbekannter Pfad" if exc.status_code == 404 else str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def eingabe_fehler(_request, exc: RequestValidationError):
        details = [{"ort": ".".join(str(x) for x in f.get("loc", [])), "meldung": f.get("msg")} for f in exc.errors()]
        return _fehler(422, "ungueltige_eingabe", "Ungültige Parameter", details)

    @app.exception_handler(DBAPIError)
    async def db_fehler(_request, exc: DBAPIError):
        if "statement timeout" in str(exc.orig).lower() or "canceling statement" in str(exc.orig).lower():
            return _fehler(504, "zeitlimit", "Die Abfrage war zu aufwendig; bitte Filter enger fassen.")
        log.exception("Datenbankfehler")
        status = 503 if isinstance(exc, OperationalError) else 500
        return _fehler(status, "datenbank", "Datenbank derzeit nicht verfügbar" if status == 503 else "Interner Fehler")

    @app.exception_handler(Exception)
    async def unbekannt(_request, exc):
        log.exception("Unerwarteter Fehler")
        return _fehler(500, "intern", "Interner Fehler")

    for r in (companies.router, profiles.router, series.router, catalog.router, quality.router, search.router, misc.router):
        app.include_router(r, prefix="/api/v1")
    return app


app = erstellen()
