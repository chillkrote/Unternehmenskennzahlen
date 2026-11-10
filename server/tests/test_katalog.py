"""Datenkatalog (P3.1): vollständig gegenüber docs/datenquellen.md, Reihen zugeordnet, Prognosegeber aus der CSV."""
import csv
import sys
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[1]
REPO = SERVER.parent
sys.path.insert(0, str(SERVER))
from etl import katalog  # noqa: E402


def test_verzeichnis_und_ergaenzung_deckungsgleich():
    k = katalog.katalog()
    assert len(k) == len(katalog.verzeichnis_lesen()) >= 30
    assert len({q["id"] for q in k}) == len(k)
    assert {q["status"] for q in k} <= {"geeignet", "namensnennung", "voraussichtlich", "pruefen", "eingeschraenkt", "kritisch", "erledigt"}
    y = next(q for q in k if q["id"] == "yahoo")
    assert y["status"] == "kritisch" and y["decision"] == "E1" and "**" not in y["assessment"]


def test_fehlende_ergaenzung_bricht_ab(tmp_path):
    erg = tmp_path / "e.csv"
    zeilen = list(csv.reader(open(katalog.ERGAENZUNG, encoding="utf-8")))
    with open(erg, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(zeilen[:-1])
    with pytest.raises(katalog.KatalogFehler):
        katalog.katalog(ergaenzung=erg)


def test_katalog_api_vollstaendig(client):
    r = client.get("/api/v1/data-catalog")
    assert r.status_code == 200
    d = r.json()["data"]
    assert [q["name"] for q in d] == [t["quelle"] for t in katalog.verzeichnis_lesen()]
    nach = {q["id"]: q for q in d}
    with open(REPO / "volkswirtschaft" / "serien.csv", newline="", encoding="utf-8") as f:
        reihen = list(csv.DictReader(f))
    assert sum(q["series"] for q in d) == len(reihen)                     # jede Reihe genau einer Quelle zugeordnet
    assert nach["eurostat"]["series"] == sum(1 for s in reihen if s["quelle"] == "Eurostat") and nach["eurostat"]["observations"] > 0
    assert nach["yahoo"]["cleared"] is False and nach["wikidata"]["cleared"] is True
    assert nach["prognosegeber"]["forecasters"] > 100


def test_katalog_filter_und_einzelquelle(client):
    frei = client.get("/api/v1/data-catalog", params={"cleared": "true"}).json()["data"]
    assert frei and all(q["cleared"] for q in frei)
    offen = client.get("/api/v1/data-catalog", params={"decision": "true"}).json()["data"]
    assert {"yahoo", "comtrade", "ipu", "google-news"} <= {q["id"] for q in offen}
    e = client.get("/api/v1/data-catalog/oecd").json()["data"]
    assert e["series"] == len(e["series_list"]) > 0 and "DSD_EO@DF_EO" in e["datasets"]
    assert client.get("/api/v1/data-catalog/gibtsnicht").status_code == 404
    assert client.get("/api/v1/data-catalog", params={"status": "falsch"}).status_code == 422


def test_prognosegeber(client):
    with open(REPO / "volkswirtschaft" / "prognosegeber_oecd.csv", newline="", encoding="utf-8") as f:
        geber = list(csv.DictReader(f))
    alle = client.get("/api/v1/forecasters").json()["data"]
    assert len(alle) == len(geber)
    fr = client.get("/api/v1/forecasters", params={"geo": "FR", "priority": 1}).json()["data"]
    assert fr and all(g["geo"] == "FR" and g["priority"] == 1 for g in fr)
