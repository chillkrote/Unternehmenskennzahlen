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
    vintage: Optional[dict[str, Any]] = Field(None, description="Begriffe und Grenzen der Versionierung (nur bei Fassungen/as_of)")


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


class ProfilKennzahl(BaseModel):
    code: str
    name: str
    unit: Optional[str] = None
    fmt: Optional[str] = None
    group: Optional[str] = None
    higher_is_better: Optional[bool] = None
    help: Optional[str] = None
    aliases: list[str] = []


class ProfilWert(BaseModel):
    metric: str
    value: float
    sector_n: int = Field(description="Unternehmen der Branche mit Wert (Vergleichsmenge)")
    sector_median: Optional[float] = None
    group_median: Optional[float] = Field(None, description="Median der Gruppe, nur bei mehr als zwei Unternehmen in der Gruppe")
    percentile: Optional[float] = Field(None, description="Anteil der Branchenwerte unter diesem Wert (0–1), ab drei Werten")


class Abschluss(BaseModel):
    fiscal_year: int
    period_end: date
    currency: str
    source: Optional[str] = None
    source_url: Optional[str] = None
    fetched: Optional[str] = None
    status: Optional[str] = None
    part_sources: dict[str, Any] = {}
    bilanz: dict[str, Optional[float]] = Field({}, description="Originalposten in gelieferter Reihenfolge, unskaliert")
    guv: dict[str, Optional[float]] = {}


class Profil(BaseModel):
    id: str
    name: str
    sector: str
    peer_group: Optional[str] = None
    listed: bool
    sector_n: int = Field(description="Unternehmen der Branche (Vergleichsmenge der Mediane)")
    group_n: int = 0
    attributes: dict[str, Any] = Field({}, description="Kopfangaben wie im Terminal (Sitz, Segment, Indizes, Rolle, Mutter, Archiv …)")
    values: list[ProfilWert] = []
    series: dict[str, Any] = {}
    statements: list[Abschluss] = []
    governance: Optional[dict[str, Any]] = None
    documents: list[dict[str, Any]] = []
    report_dates: list[dict[str, Any]] = []
    links: dict[str, str] = {}


class BranchenWert(BaseModel):
    metric: str
    n: int
    median: Optional[float] = None
    p25: Optional[float] = None
    p75: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None


class BranchenStatistik(BaseModel):
    sector: str
    group: Optional[str] = None
    country: Optional[str] = None
    companies: int
    metrics: list[BranchenWert]


class Reihe(BaseModel):
    id: str
    topic: Optional[str] = None
    name: str
    unit: Optional[str] = None
    fmt: Optional[str] = None
    kind: Optional[str] = None
    frequency: Optional[str] = None
    core: bool = False
    provider: Optional[str] = None
    dataset: Optional[str] = None
    filter: Optional[str] = None
    url: Optional[str] = None
    fetched: Optional[str] = None
    forecast_from: Optional[str] = Field(None, description="ab diesem Zeitraum Projektion, keine Beobachtung")
    note: Optional[str] = None
    geos: list[str] = Field([], description="Gebiete mit Werten (Codes der Quelle)")
    first_period: Optional[str] = None
    last_period: Optional[str] = None
    observations: int = 0
    source_updated: Optional[str] = Field(None, description="Stand der Quelle laut letztem Abruf (Quellenversion)")
    history_start: Optional[datetime] = Field(None, description="Beginn der gespeicherten Historie (erster Import); davor kein Datenbankstand")
    superseded_versions: int = Field(0, description="abgelöste Fassungen (revidierte oder entfallene Werte) seit history_start")
    meta: dict[str, Any] = {}


class Datenquelle(BaseModel):
    id: str
    name: str
    area: str = Field(description="Bereich: unternehmen, markt, finanzen, volkswirtschaft, handel, politik, geodaten, nachrichten, dienst")
    used_for: Optional[str] = None
    access: Optional[str] = Field(None, description="Abruf (Skripte im Repo)")
    credentials: Optional[str] = Field(None, description="Schlüssel nötig? Nur der Name, nie der Wert")
    license: Optional[str] = Field(None, description="Lizenz / Weiterverbreitung laut docs/datenquellen.md")
    assessment: Optional[str] = None
    status: str = Field(description="geeignet, namensnennung, voraussichtlich, pruefen, eingeschraenkt, kritisch, erledigt")
    cleared: bool = Field(description="für den öffentlichen Server freigegeben (geeignet, mit Namensnennung oder erledigt)")
    decision: Optional[str] = Field(None, description="offene Entscheidung (E1 …) in docs/datenquellen.md")
    attribution: Optional[str] = Field(None, description="Pflichtangabe für die Seite „Quellen“")
    links: list[str] = []
    aliases: list[str] = Field([], description="Kennungen in Importen (series.provider, source_document.provider, ingestion_run.adapter)")
    series: int = Field(0, description="VWL-Reihen dieser Quelle (/series)")
    datasets: list[str] = []
    observations: int = 0
    first_year: Optional[int] = Field(None, description="frühestes Jahr mit Werten (Reihen unterschiedlicher Frequenz)")
    last_year: Optional[int] = None
    fetched: Optional[str] = Field(None, description="letzter Abruf laut Reihenkatalog")
    documents: int = Field(0, description="registrierte Quelldokumente")
    last_run: Optional[datetime] = Field(None, description="letzter erfolgreicher Importlauf")
    forecasters: int = Field(0, description="Prognosegeber (/forecasters)")


class Prognosegeber(BaseModel):
    id: int
    geo: str
    country: Optional[str] = None
    publisher: str
    type: Optional[str] = None
    publication: Optional[str] = None
    variables: Optional[str] = None
    horizon: Optional[str] = None
    rhythm: Optional[str] = None
    url: Optional[str] = None
    access: Optional[str] = None
    data_url: Optional[str] = None
    priority: Optional[int] = Field(None, description="1 wichtigster Geber des Landes, 2 ergänzend, 3 nachrangig")
    note: Optional[str] = None
    http_status_url: Optional[str] = None
    http_status_data: Optional[str] = None
    checked: Optional[str] = None
