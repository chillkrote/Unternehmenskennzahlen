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
    assert vwl["denominator"] == len(vwl["geos"]) > 30 and all(0 <= x["share"] <= 1 for x in vwl["rows"])
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
