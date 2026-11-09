"""Antwortformate der API (Pydantic). Einheitlich: {"data": …, "meta": {…}} bzw. {"error": {…}}."""
from datetime import date, datetime
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Seite(BaseModel):
    page: int = Field(description="aktuelle Seite, ab 1")
    page_size: int
    total: int = Field(description="Treffer insgesamt (alle Seiten)")
    pages: int


class Meta(BaseModel):
    api_version: str = "1"
    generated_at: datetime
    pagination: Optional[Seite] = None
    source: Optional[str] = Field(None, description="Herkunft der Daten (Datei bzw. Import)")
    data_as_of: Optional[datetime] = Field(None, description="Zeitpunkt des letzten erfolgreichen Imports dieser Daten")
    notes: list[str] = []


class Antwort(BaseModel, Generic[T]):
    data: T
    meta: Meta


class Fehler(BaseModel):
    code: str
    message: str
    details: Any = None


class FehlerAntwort(BaseModel):
    error: Fehler


class UnternehmenKurz(BaseModel):
    id: str = Field(description="Unternehmens-ID (U000123), dauerhaft, nie aus ISIN o. Ä. abgeleitet")
    name: str
    country: Optional[str] = Field(None, description="Sitzland ISO-3166-Alpha-2; null = unbekannt")
    country_name: str = Field(description="Land wie in der Unternehmenstabelle")
    seat: Optional[str] = None
    sector: str
    listed: bool
    is_bank: bool
    isin: Optional[str] = None
    ticker: Optional[str] = None
    exchange: Optional[str] = None
    lei: Optional[str] = None
    facts: int = Field(0, description="Anzahl Kennzahlenwerte in der Datenbank")


class UnternehmenZeile(BaseModel):
    """Zeile der Unternehmensliste; mit ?fields= werden nur die gewählten Felder geliefert (id immer)."""
    id: str
    name: Optional[str] = None
    country: Optional[str] = None
    country_name: Optional[str] = None
    seat: Optional[str] = None
    sector: Optional[str] = None
    listed: Optional[bool] = None
    is_bank: Optional[bool] = None
    isin: Optional[str] = None
    ticker: Optional[str] = None
    exchange: Optional[str] = None
    lei: Optional[str] = None
    facts: Optional[int] = None


class Kennung(BaseModel):
    scheme: str = Field(description="ISIN, LEI, TICKER, ROW_KEY …")
    value: str


class Pruefmarke(BaseModel):
    code: str
    detail: str
    decision: Optional[str] = None
    reason: Optional[str] = None


class Unternehmen(UnternehmenKurz):
    legal_form: Optional[str] = None
    nace: Optional[str] = None
    register_no: Optional[str] = None
    website: Optional[str] = None
    indices: Optional[str] = None
    description: Optional[str] = None
    source_url: str
    identifiers: list[Kennung] = []
    aliases: list[str] = []
    review_flags: list[Pruefmarke] = []
    metrics: list[str] = Field([], description="Kennzahlen-Codes mit Werten (Details: /companies/{id}/metrics)")
    links: dict[str, str] = {}


class Beobachtung(BaseModel):
    metric: str
    period_start: Optional[date] = None
    period_end: date
    value: float
    unit: str
    accounting_standard: str
    consolidation: str
    quality: str
    reported_at: Optional[date] = Field(None, description="Veröffentlichungsdatum laut Quelle (Vintage)")
    recorded_at: datetime = Field(description="Zeitpunkt der Erfassung in der Datenbank")
    source: dict[str, Any]
    provenance: dict[str, Any] = {}


class Land(BaseModel):
    code: str
    iso3: Optional[str] = None
    name: str
    name_de: Optional[str] = None
    region: Optional[str] = None
    oecd_member: bool
    companies: int = 0


class Branche(BaseModel):
    id: str
    name: str
    companies: int


class Kennzahl(BaseModel):
    code: str
    description: str
    period_kind: str
    unit_kind: str
    regulatory: bool
    observations: int
    companies: int


class Treffer(BaseModel):
    type: str = Field(description="company | country | sector | indicator")
    id: str
    label: str
    detail: Optional[str] = None
    score: float
    link: str = Field(description="Ziel in der Oberfläche (Hash-Route) bzw. API-Pfad")


class Suchergebnis(BaseModel):
    query: str
    interpreted: dict[str, Any] = Field({}, description="erkannte Filter, z. B. Land oder Branche aus den Suchwörtern")
    groups: dict[str, list[Treffer]]


class Lauf(BaseModel):
    adapter: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    imported_count: int
    last_success_at: Optional[datetime] = None


class Gesundheit(BaseModel):
    status: str
    database: str
    schema_revision: Optional[str] = None
    version: str
