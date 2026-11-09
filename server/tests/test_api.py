"""API-Integrationstests gegen die echten Repo-Daten in einer Wegwerf-Datenbank (Fixture geladene_db)."""
import csv
import sys
from pathlib import Path

import psycopg
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "app"))
TABELLE = REPO / "unternehmen-tabelle" / "Unternehmen_Tabelle.csv"


@pytest.fixture(scope="module")
def tabelle():
    with open(TABELLE, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


# ---------- Unternehmens-IDs bleiben erhalten ----------

def test_alle_ids_unveraendert_uebernommen(geladene_db, tabelle):
    ids_datei = {z["unternehmen_id"] for z in tabelle if z["unternehmen_id"]}
    with psycopg.connect(geladene_db) as c:
        ids_db = {r[0] for r in c.execute("SELECT entity_id FROM international.company_register WHERE active AND entity_id IS NOT NULL")}
        stamm = {r[0] for r in c.execute("SELECT id FROM international.entity")}
    assert ids_db == ids_datei
    with open(REPO / "stammdaten" / "unternehmen_ids.csv", encoding="utf-8") as f:
        assert {z["unternehmen_id"] for z in csv.DictReader(f)} <= stamm


def test_isin_hoechstens_einmal(geladene_db):
    with psycopg.connect(geladene_db) as c:
        assert c.execute("SELECT count(*) FROM (SELECT isin FROM international.company_register WHERE isin IS NOT NULL GROUP BY 1 HAVING count(*)>1) x").fetchone()[0] == 0


def test_beispiel_id_zuordnung(client):
    d = client.get("/api/v1/companies/U000836").json()["data"]
    assert d["name"] == "BAWAG" and d["isin"] == "AT0000BAWAG2" and d["country"] == "AT"
    assert {"scheme": "LEI", "value": "529900S9YO2JHTIIDG38"} in d["identifiers"]
    assert d["links"]["terminal"] == "#firma-U000836"


# ---------- Liste, Filter, Pagination ----------

def test_liste_gesamtzahl_wie_tabelle(client, tabelle):
    r = client.get("/api/v1/companies?page_size=5").json()
    assert r["meta"]["pagination"]["total"] == len(tabelle)
    assert len(r["data"]) == 5 and r["meta"]["source"].endswith("Unternehmen_Tabelle.csv") and r["meta"]["data_as_of"]


def test_pagination_lueckenlos(client):
    ids = []
    for p in (1, 2, 3):
        ids += [x["id"] for x in client.get(f"/api/v1/companies?country=AT&sort=id&page_size=7&page={p}").json()["data"]]
    alle = [x["id"] for x in client.get("/api/v1/companies?country=AT&sort=id&page_size=21").json()["data"]]
    assert ids == alle and len(set(ids)) == len(ids)


def test_filter_land_wie_oberflaeche(client, tabelle):
    import register
    codes = register.land_codes()
    erwartet = sum(1 for z in tabelle if codes.get(z["Land *"].strip().lower()) == "FR")
    assert client.get("/api/v1/companies?country=FR&page_size=1").json()["meta"]["pagination"]["total"] == erwartet
    assert client.get("/api/v1/companies?country=fr&page_size=1").json()["meta"]["pagination"]["total"] == erwartet
    unbekannt = sum(1 for z in tabelle if codes.get(z["Land *"].strip().lower(), "ZZ") == "ZZ")
    assert client.get("/api/v1/companies?country=ZZ&page_size=1").json()["meta"]["pagination"]["total"] == unbekannt


def test_filter_branche_notierung_kennzahlen(client, tabelle):
    erwartet = sum(1 for z in tabelle if z["Branche *"] == "banken" and z["Börsennotiert *"] == "ja")
    r = client.get("/api/v1/companies?sector=banken&listed=true&page_size=200").json()
    assert r["meta"]["pagination"]["total"] == erwartet and all(x["listed"] and x["sector"] == "banken" for x in r["data"])
    mit = client.get("/api/v1/companies?has_metrics=true&page_size=200").json()
    assert mit["meta"]["pagination"]["total"] > 100 and all(x["facts"] > 0 for x in mit["data"])
    ohne = client.get("/api/v1/companies?has_metrics=false&page_size=1").json()["meta"]["pagination"]["total"]
    assert ohne + mit["meta"]["pagination"]["total"] == len(tabelle)


def test_standardsortierung_kennzahlen_zuerst(client):
    d = client.get("/api/v1/companies?country=DE&page_size=200").json()["data"]
    f = [x["facts"] > 0 for x in d]
    assert f == sorted(f, reverse=True)


def test_suche_text_isin_ticker_alias(client):
    namen = [x["name"] for x in client.get("/api/v1/companies?q=volkswagen").json()["data"]]
    assert "Volkswagen AG" in namen
    assert client.get("/api/v1/companies?q=AT0000BAWAG2").json()["data"][0]["id"] == "U000836"
    assert client.get("/api/v1/companies?q=u000836").json()["data"][0]["id"] == "U000836"
    assert client.get("/api/v1/companies?q=BAWAG GROUP AG").json()["meta"]["pagination"]["total"] >= 1      # Alias
    assert client.get("/api/v1/companies?q=100%25_x").json()["meta"]["pagination"]["total"] == 0           # Platzhalter maskiert


def test_ids_filter_fuer_merkliste(client):
    r = client.get("/api/v1/companies?ids=U000836,U000712&sort=id").json()["data"]
    assert [x["id"] for x in r] == ["U000712", "U000836"]


def test_feldauswahl(client):
    r = client.get("/api/v1/companies?fields=name,country&page_size=2").json()["data"]
    assert all(set(x) == {"id", "name", "country"} for x in r)


@pytest.mark.parametrize("abfrage,code", [("page_size=1000", "seitengroesse"), ("sort=xyz", "sortierung"), ("sector=xyz", "branche"),
                                         ("fields=passwort", "felder"), ("ids=1,2", "ids"), ("country=DEU", "ungueltige_eingabe"),
                                         ("page=0", "ungueltige_eingabe")])
def test_eingabepruefung(client, abfrage, code):
    r = client.get("/api/v1/companies?" + abfrage)
    assert r.status_code == 422 and r.json()["error"]["code"] == code


def test_profil_fehler(client):
    assert client.get("/api/v1/companies/U999999").status_code == 404
    r = client.get("/api/v1/companies/DROP%20TABLE")
    assert r.status_code == 422 and r.json()["error"]["code"] == "id_format"


# ---------- Kennzahlen, Vintage ----------

def test_kennzahlen_mit_quelle_und_einheit(client):
    d = client.get("/api/v1/companies/U000148/metrics?metric=assets").json()["data"]
    assert d and all(x["unit"] == "EUR" and x["period_start"] is None for x in d)
    assert d[0]["source"]["object_key"] == "zeitreihen/zeitreihe_lang.csv" and "originalwert" in d[0]["provenance"]
    ende = [x["period_end"] for x in d]
    assert ende == sorted(ende)


def test_kennzahlen_wert_gleich_quelldatei(client):
    """Unabhängige Referenz: der Wert in der Quelldatei (Mio. EUR) muss exakt dem API-Wert (EUR) entsprechen."""
    with open(REPO / "zeitreihen" / "zeitreihe_lang.csv", encoding="utf-8") as f:
        z = [r for r in csv.DictReader(f) if r["unternehmen_id"] == "U000148" and r["kennzahl"] == "bilanzsumme"]
    assert z
    api = {x["period_end"]: x["value"] for x in client.get("/api/v1/companies/U000148/metrics?metric=assets").json()["data"]}
    assert {r["stichtag"] for r in z} <= set(api)
    for r in z:
        assert r["einheit"] == "Mio. EUR"
        assert api[r["stichtag"]] == pytest.approx(float(r["wert"]) * 1e6, rel=0, abs=0.5)


def test_kennzahlen_as_of_vor_erfassung_leer(client):
    assert client.get("/api/v1/companies/U000148/metrics?as_of=1990-01-01").json()["data"] == []


def test_kennzahlenkatalog(client):
    d = {k["code"]: k for k in client.get("/api/v1/indicators").json()["data"]}
    assert d["assets"]["observations"] > 0 and d["assets"]["unit_kind"] == "money" and d["cet1_ratio"]["regulatory"]


# ---------- Suche über Bereiche ----------

def test_universelle_suche_deutet_land_und_branche(client):
    d = client.get("/api/v1/search?q=Deutschland Automobile").json()["data"]
    assert d["interpreted"]["countries"] == ["DE"] and d["interpreted"]["sectors"] == ["automobil"]
    assert d["groups"]["country"][0]["id"] == "DE" and d["groups"]["sector"][0]["id"] == "automobil"
    assert d["groups"]["company"] and all(" DE " in f" {x['detail'].split('·')[0]} " for x in d["groups"]["company"])


def test_suche_fehlertolerant(client):
    namen = [x["label"] for x in client.get("/api/v1/search?q=Siemns&types=company").json()["data"]["groups"]["company"]]
    assert "Siemens AG" in namen


def test_suche_exakte_kennung_zuerst(client):
    g = client.get("/api/v1/search?q=DE0007236101&types=company").json()["data"]["groups"]["company"]
    assert g[0]["label"] == "Siemens AG" and g[0]["link"].startswith("#firma-U")


def test_suche_ungueltiger_typ(client):
    assert client.get("/api/v1/search?q=x&types=passwort").status_code == 422


# ---------- Länder, Branchen, Betrieb ----------

def test_laender_und_branchen(client, tabelle):
    l = {x["code"]: x for x in client.get("/api/v1/countries").json()["data"]}
    assert l["DE"]["name_de"] == "Deutschland" and l["DE"]["oecd_member"] and not l["CN"]["oecd_member"]
    de = client.get("/api/v1/countries/de").json()["data"]
    assert de["companies"] == l["DE"]["companies"] and de["sectors"]
    assert sum(b["companies"] for b in client.get("/api/v1/sectors").json()["data"]) == len(tabelle)


def test_updates_und_health(client):
    a = {x["adapter"]: x for x in client.get("/api/v1/updates").json()["data"]}
    assert a["import-unternehmenstabelle"]["status"] == "ok" and a["import-unternehmenstabelle"]["last_success_at"]
    h = client.get("/api/v1/health").json()
    assert h["status"] == "ok" and h["schema_revision"] == "0004"


def test_etag_und_cache(client):
    r = client.get("/api/v1/sectors")
    assert r.headers["cache-control"].startswith("public") and r.headers["etag"]
    assert client.get("/api/v1/sectors", headers={"If-None-Match": r.headers["etag"]}).status_code == 304


def test_cors_nur_fuer_erlaubte_herkunft(client):
    assert client.get("/api/v1/sectors", headers={"Origin": "http://localhost:8080"}).headers.get("access-control-allow-origin") == "http://localhost:8080"
    assert "access-control-allow-origin" not in client.get("/api/v1/sectors", headers={"Origin": "https://boese.example"}).headers


def test_api_verbindung_ist_nur_lesend(geladene_db):
    from sqlalchemy import text
    from plattform.config import Einstellungen
    from plattform.db import engine
    with engine(Einstellungen(database_url=geladene_db)).connect() as c:
        with pytest.raises(Exception, match="read-only"):
            c.execute(text("UPDATE international.company_register SET name = 'x' WHERE false"))


def test_keine_geheimnisse_in_antworten(client):
    for p in ("/api/v1/health", "/api/v1/updates", "/api/v1/companies?page_size=1"):
        t = client.get(p).text.lower()
        assert "password" not in t and "postgresql://" not in t
