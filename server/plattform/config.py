"""Einstellungen ausschließlich aus Umgebungsvariablen (keine Zugangsdaten im Repo). Beispiel: server/.env.example."""
import os
from dataclasses import dataclass, field


def _liste(wert):
    return [x.strip() for x in (wert or "").split(",") if x.strip()]


@dataclass(frozen=True)
class Einstellungen:
    database_url: str = field(default_factory=lambda: os.environ.get("DATABASE_URL", ""))
    # Browser-Ursprünge, die die API lesen dürfen (CORS). Leer = nur gleiche Herkunft (hinter Caddy unter derselben Domain).
    cors_origins: list = field(default_factory=lambda: _liste(os.environ.get("API_CORS_ORIGINS")))
    # Anfragen je Minute und IP-Adresse (prozesslokal; Caddy begrenzt zusätzlich). 0 = aus.
    rate_limit_per_minute: int = field(default_factory=lambda: int(os.environ.get("API_RATE_LIMIT_PER_MINUTE", "240")))
    # Obergrenze je SQL-Anweisung, schützt die Datenbank vor teuren Abfragen
    statement_timeout_ms: int = field(default_factory=lambda: int(os.environ.get("API_STATEMENT_TIMEOUT_MS", "5000")))
    max_page_size: int = field(default_factory=lambda: int(os.environ.get("API_MAX_PAGE_SIZE", "200")))
    # Browser-Cache für Listenantworten in Sekunden (Daten ändern sich höchstens einige Male am Tag)
    cache_seconds: int = field(default_factory=lambda: int(os.environ.get("API_CACHE_SECONDS", "300")))
    umgebung: str = field(default_factory=lambda: os.environ.get("PLATTFORM_UMGEBUNG", "entwicklung"))


def sqlalchemy_url(url: str) -> str:
    """postgresql://… (wie in den bisherigen Skripten) -> postgresql+psycopg://… für SQLAlchemy."""
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    return url


def psycopg_url(url: str) -> str:
    """Umkehrung für die bestehenden Importskripte (psycopg direkt)."""
    return url.replace("postgresql+psycopg://", "postgresql://", 1)
