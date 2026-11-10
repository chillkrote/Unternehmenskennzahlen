"""Datenqualität (P3.2): Rechenregeln ohne Datenbank und der Prüfbericht über die API."""
from datetime import date

import pytest

from plattform import qualitaet as q


@pytest.mark.parametrize("zeitraum,soll", [("2026", 2026 * 12 + 11), ("2026-Q1", 2026 * 12 + 2), ("2026-Q4", 2026 * 12 + 11), ("2026-07", 2026 * 12 + 6)])
def test_monat(zeitraum, soll):
    assert q.monat(zeitraum) == soll


def test_verzug_je_frequenz():
    t = date(2026, 11, 10)
    assert q.verzug("2026-09", "M", t) == {"lag_months": 2, "allowed_months": 3, "stale": False}
    assert q.verzug("2026-06", "M", t)["stale"] is True
    assert q.verzug("2026-Q2", "Q", t)["stale"] is False          # Juni -> 5 Monate
    assert q.verzug("2025-Q4", "Q", t)["stale"] is True
    assert q.verzug("2024", "A", t)["stale"] is False and q.verzug("2023", "A", t)["stale"] is True
    assert q.verzug("2027", "A", t)["lag_months"] < 0           # Projektion
    assert q.verzug("2020", "X", t)["stale"] is False


def test_spruenge_findet_ausreisser_und_nur_den():
    punkte = [(f"20{10 + i // 12:02d}-{i % 12 + 1:02d}", 100 + (i % 3) * 0.5) for i in range(36)]
    assert q.spruenge(punkte) == []
    punkte[-1] = (punkte[-1][0], 140.0)
    s = q.spruenge(punkte)
    assert len(s) == 1 and s[0]["period"] == punkte[-1][0] and s[0]["change"] > 0


def test_spruenge_zu_kurze_reihe_und_konstante():
    assert q.spruenge([("2020", 1.0), ("2021", 50.0)]) == []
    assert q.spruenge([(str(2000 + i), 5.0) for i in range(30)] + [("2030", 9.0)]) == []   # MAD 0: keine Aussage


def test_erwartete_gebiete_aus_der_abruf_url():
    assert q.erwartete_gebiete("https://ec.europa.eu/x/data/une_rt_m?geo=DE&geo=EA21&geo=AT&unit=PC") == ["AT", "DE", "EA20"]
    assert q.erwartete_gebiete("https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,/DEU+EA20+GRC+GBR.M.N.CPI") == ["DE", "EA20", "EL", "UK"]
    assert q.erwartete_gebiete("https://www.ifo.de/umfrage/ifo-geschaeftsklima-deutschland") is None
    assert q.erwartete_gebiete(None) is None


def test_oecd_codes_wie_im_abrufskript():
    import importlib.util
    from pathlib import Path
    pfad = Path(__file__).resolve().parents[2] / "volkswirtschaft" / "skripte" / "gemeinsam.py"
    spec = importlib.util.spec_from_file_location("vwl_gemeinsam", pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert q.OECD_ISO3 == m.OECD_ISO3


def test_aktualitaet_je_gebiet_wird_nicht_vom_juengsten_gebiet_verdeckt():
    """Audit 2026-11, 4.2: früher zählte nur der jüngste Zeitraum über alle Gebiete, eine stehen gebliebene Länderreihe fiel nicht auf."""
    t = date(2026, 11, 10)
    a = q.aktualitaet({"DE": "2026-09", "AT": "2025-12", "JP": "2021-06", "UK": "2020-09"}, "M", t, erwartet=["AT", "DE", "FR", "JP", "UK"], quelle="Eurostat")
    assert a["source_last"] == "2026-09" and a["source"]["stale"] is False
    g = a["geos"]
    assert g["DE"]["status"] == "current" and g["DE"]["behind_source_months"] == 0
    assert g["AT"]["status"] == "stale" and g["AT"]["behind_source_months"] == 9 and g["AT"]["lag_months"] == 11
    assert g["JP"]["status"] == "dormant"
    assert g["UK"]["status"] == "not_published" and "EU-Austritt" in g["UK"]["reason"]
    assert g["FR"] == {"last_period": None, "lag_months": None, "behind_source_months": None, "status": "missing"}
    assert q.aktualitaet({"UK": "2020-09"}, "M", t, quelle="OECD")["geos"]["UK"]["status"] == "dormant"     # nur für Eurostat bekannt


def test_aktualitaet_ganze_quelle_veraltet():
    a = q.aktualitaet({"DE": "2026-03", "FR": "2026-03", "IT": "2026-01"}, "M", date(2026, 11, 10))
    assert a["source"]["stale"] is True
    assert a["geos"]["DE"]["status"] == "source_stale" and a["geos"]["IT"]["status"] == "stale"
    assert q.aktualitaet({}, "M", date(2026, 11, 10), erwartet=["DE"])["geos"]["DE"]["status"] == "missing"


def test_luecken_und_fenster():
    assert q.luecken(["2026-01", "2026-02", "2026-05"], "M") == ["2026-03", "2026-04"]
    assert q.luecken(["2025-Q3", "2026-Q1"], "Q") == ["2025-Q4"]
    assert q.luecken(["2019", "2022", "2023"], "A") == ["2020", "2021"]
    assert q.luecken(["2026-01"], "M") == [] and q.luecken(["2020", "2023"], "X") == []
    assert q.fenster("2026-02", "M") == [f"2025-{m:02d}" for m in range(3, 13)] + ["2026-01", "2026-02"]
    assert q.fenster("2026-Q1", "Q") == ["2024-Q2", "2024-Q3", "2024-Q4", "2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4", "2026-Q1"]
    assert q.fenster("2025", "A") == ["2021", "2022", "2023", "2024", "2025"] and q.fenster("2025", "X") == []
    for z, f in (("2026-07", "M"), ("2026-Q3", "Q"), ("2026", "A")):
        assert q.zeitraum_aus(q.monat(z), f) == z


def test_abruf_alter():
    t = date(2026, 11, 10)
    assert q.abruf_alter("2026-10-27", "M", t) == {"fetched": "2026-10-27", "age_days": 14, "allowed_days": 45, "overdue": False}
    assert q.abruf_alter("2026-08-01", "M", t)["overdue"] is True
    assert q.abruf_alter(None, "M", t) is None and q.abruf_alter("unklar", "M", t) is None


def test_anteil():
    assert q.anteil(21, 42) == 0.5 and q.anteil(1, 0) == 0.0


def test_pruefbericht_api(client):
    r = client.get("/api/v1/data-quality", params={"as_of": "2026-11-10"})
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["reference_date"] == "2026-11-10"
    assert {f["code"] for f in d["flags"]} >= {"pruefliste_getrennt"}
    assert all(f["open"] + f["decided"] == f["total"] for f in d["flags"])
    vwl = d["coverage"]["series"]
    assert len(vwl["geos"]) > 30 and all(0 <= x["share"] <= 1 and x["covered"] <= x["expected"] for x in vwl["rows"])
    # fester Nenner je Reihe: Eurostat-Reihen fragen 29 Gebiete an, nicht die 42 Gebiete aller Reihen zusammen (Audit 4.2)
    zeile = {x["series_id"]: x for x in vwl["rows"]}
    assert zeile["bip_qoq"]["expected"] == 29 and "UK" in zeile["bip_qoq"]["missing"] and zeile["bip_qoq"]["share"] > 0.9
    assert zeile["oecd_inflation"]["expected"] == 42 and zeile["euribor_3m"]["expected"] == 1 and zeile["euribor_3m"]["share"] == 1.0
    assert zeile["ifo_geschaeftsklima"]["basis"].startswith("Gebiete mit Werten")
    # Aktualität je Gebiet: stehen gebliebene Länderreihen fallen auf, obwohl die Reihe insgesamt aktuell ist
    fr = {x["series_id"]: x for x in d["freshness"]["rows"]}
    assert len(fr) == len(vwl["rows"])
    alq = {g["geo"]: g for g in fr["arbeitslosenquote"]["geos"]}
    assert fr["arbeitslosenquote"]["source_stale"] is False and alq["UK"]["status"] == "not_published" and alq["UK"]["last_period"] == "2020-09"
    oi = fr["oecd_inflation"]
    assert oi["source_stale"] is False and oi["status_counts"].get("stale", 0) + oi["status_counts"].get("dormant", 0) > 0
    assert all(g["status"] != "current" or g["gaps"] for f in fr.values() for g in f["geos"])
    assert all(sum(f["status_counts"].values()) >= f["status_counts"].get("current", 0) for f in fr.values())
    assert fr["oecd_eo_bip"]["source_last_period"] < "2026"            # Projektionen zählen nicht als Beobachtung
    assert d["summary"]["series_with_stale_geos"] > 0 and d["summary"]["geo_series_by_status"]["current"] > 1000
    assert {x["provider"] for x in d["freshness"]["by_provider"]} >= {"Eurostat", "OECD"}
    assert any(x["adapter"] == "vwl" and x["last_ok"] for x in d["freshness"]["import_runs"])
    prof = d["coverage"]["profile_metrics"]
    assert prof["denominator"] > 1000 and all(x["covered"] <= prof["denominator"] for x in prof["rows"])
    assert any(x["id"] == "unternehmensberichte" for x in d["uncleared_sources_with_data"])
    assert d["summary"]["stale_series"] == len(d["stale_series"]) and d["summary"]["jumps"] == len(d["jumps"])


def test_pruefbericht_reproduzierbar_und_stichtag(client):
    a = client.get("/api/v1/data-quality", params={"as_of": "2026-11-10"}).json()["data"]
    from plattform.api import quality
    quality._CACHE.clear()
    b = client.get("/api/v1/data-quality", params={"as_of": "2026-11-10"}).json()["data"]
    assert a == b
    spaet = client.get("/api/v1/data-quality", params={"as_of": "2030-01-01"}).json()["data"]
    assert spaet["summary"]["stale_series"] >= a["summary"]["stale_series"] and spaet["summary"]["stale_series"] > 0
    assert client.get("/api/v1/data-quality", params={"as_of": "kein-datum"}).status_code == 422
