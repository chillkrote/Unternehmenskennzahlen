"""Tests ohne Datenbank: Hilfsfunktionen, Ratenbegrenzung, Suchdeutung, Fehlerformat."""
from fastapi.testclient import TestClient

from plattform.api.search import _branche
from plattform.config import Einstellungen, psycopg_url, sqlalchemy_url
from plattform.main import Ratenbegrenzer, erstellen


def test_url_umwandlung():
    assert sqlalchemy_url("postgresql://u:p@h:5432/d") == "postgresql+psycopg://u:p@h:5432/d"
    assert sqlalchemy_url("postgres://u@h/d") == "postgresql+psycopg://u@h/d"
    assert psycopg_url("postgresql+psycopg://u@h/d") == "postgresql://u@h/d"


def test_ratenbegrenzer_gleitendes_fenster():
    r = Ratenbegrenzer(3)
    assert [r.erlaubt("a", 100.0)[0] for _ in range(3)] == [True, True, True]
    ok, warten = r.erlaubt("a", 100.5)
    assert not ok and 1 <= warten <= 60
    assert r.erlaubt("b", 100.5)[0]                 # andere IP unabhängig
    assert r.erlaubt("a", 160.1)[0]                 # nach 60 s wieder frei
    assert Ratenbegrenzer(0).erlaubt("x")[0]       # 0 = aus


def test_branchen_deutung():
    assert _branche("automobile") == "automobil"
    assert _branche("banken") == "banken"
    assert _branche("pharma") == "pharma-gesundheit"
    assert _branche("xyz") is None
    assert _branche("de") is None                  # zu kurz für eine Präfixsuche


def test_schreibende_methoden_abgewiesen_ohne_db():
    app = erstellen(Einstellungen(database_url="postgresql://niemand@127.0.0.1:1/x", rate_limit_per_minute=0))
    c = TestClient(app)
    r = c.post("/api/v1/companies")
    assert r.status_code == 405 and r.json()["error"]["code"] == "nur_lesend"
    r = c.get("/api/v1/gibtsnicht")
    assert r.status_code == 404 and r.json()["error"]["code"] == "nicht_gefunden"


def test_health_ohne_datenbank_meldet_503():
    app = erstellen(Einstellungen(database_url="postgresql://niemand@127.0.0.1:1/x", rate_limit_per_minute=0))
    r = TestClient(app).get("/api/v1/health")
    assert r.status_code == 503 and r.json()["database"] == "nicht erreichbar"


def test_ratenbegrenzung_in_der_app():
    app = erstellen(Einstellungen(database_url="postgresql://niemand@127.0.0.1:1/x", rate_limit_per_minute=2))
    c = TestClient(app)
    codes = [c.get("/api/v1/gibtsnicht").status_code for _ in range(3)]
    assert codes == [404, 404, 429]
    assert "Retry-After" in c.get("/api/v1/gibtsnicht").headers


def test_openapi_dokumentiert_alle_endpunkte():
    app = erstellen(Einstellungen(database_url="postgresql://niemand@127.0.0.1:1/x", rate_limit_per_minute=0))
    pfade = set(TestClient(app).get("/api/v1/openapi.json").json()["paths"])
    for p in ("/api/v1/companies", "/api/v1/companies/{company_id}", "/api/v1/companies/{company_id}/metrics", "/api/v1/search",
              "/api/v1/countries", "/api/v1/countries/{code}", "/api/v1/sectors", "/api/v1/indicators", "/api/v1/updates", "/api/v1/health"):
        assert p in pfade
