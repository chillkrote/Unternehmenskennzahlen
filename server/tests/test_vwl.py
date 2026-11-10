"""VWL-Reihen (P2.6): Referenztest gegen app/vwl.py (dieselben Daten wie die eingebettete Seite) und Vintage."""
import csv
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

import psycopg
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "app"))
sys.path.insert(0, str(REPO / "international"))
import vwl as vwl_build  # noqa: E402

DATEN = vwl_build.lade()


def test_katalog_wie_seite(client):
    r = client.get("/api/v1/series")
    assert r.status_code == 200
    kat = r.json()["data"]
    assert [s["id"] for s in kat] == [s["serie_id"] for s in DATEN["serien"]]
    for s, soll in zip(kat, DATEN["serien"]):
        assert s["name"] == soll["name"] and s["core"] == soll["kern"] and (s["forecast_from"] or "") == (soll.get("prognose_ab") or "")
        assert s["geos"] == sorted(DATEN["daten"][s["id"]])
        assert s["observations"] == sum(len(p) for p in DATEN["daten"][s["id"]].values())


def test_alle_werte_wie_seite(client):
    ids = [s["serie_id"] for s in DATEN["serien"]]
    n = 0
    for i in range(0, len(ids), 20):
        teil = ids[i:i + 20]
        d = client.get("/api/v1/observations", params={"series": ",".join(teil)}).json()["data"]
        for sid in teil:
            assert d[sid] == DATEN["daten"][sid], sid           # gleiche Gebiete, Zeiträume, Reihenfolge und Werte (bitgleich)
            n += sum(len(p) for p in d[sid].values())
    assert n == sum(len(p) for g in DATEN["daten"].values() for p in g.values())


def test_filter_gebiet_und_zeitraum(client):
    d = client.get("/api/v1/observations", params={"series": "bip_qoq", "geo": "DE,FR", "from": "2020-Q1", "to": "2020-Q4"}).json()["data"]
    assert set(d["bip_qoq"]) == {"DE", "FR"}
    assert [p for p, _ in d["bip_qoq"]["DE"]] == ["2020-Q1", "2020-Q2", "2020-Q3", "2020-Q4"]
    soll = dict(map(tuple, DATEN["daten"]["bip_qoq"]["DE"]))
    assert all(v == soll[p] for p, v in d["bip_qoq"]["DE"])


@pytest.mark.parametrize("par,code", [({"series": "gibtsnicht"}, 404), ({"series": "BIP;DROP"}, 422), ({"series": ",".join(["a"] * 61)}, 422),
                                      ({"series": "bip_qoq", "from": "2020-13"}, 422), ({}, 422)])
def test_eingabepruefung(client, par, code):
    assert client.get("/api/v1/observations", params=par).status_code == code


def test_reihe_einzeln(client):
    assert client.get("/api/v1/series/bip_qoq").json()["data"]["frequency"] == "Q"
    assert client.get("/api/v1/series/gibtsnicht").status_code == 404


def test_vintage_revision_und_stand(leere_db, tmp_path):
    """Zweiter Import mit geändertem und fehlendem Wert: alte Fassung bleibt, as_of liefert den damaligen Stand."""
    from alembic import command
    from etl import vwl
    from test_migrationen import _cfg
    import db as intl_db
    command.upgrade(_cfg(leere_db), "head")
    ordner = tmp_path / "vw"
    ordner.mkdir()
    shutil.copy(REPO / "volkswirtschaft/serien.csv", ordner)
    zeilen = list(csv.DictReader(open(REPO / "volkswirtschaft/zeitreihe_lang.csv", encoding="utf-8-sig")))
    klein = [z for z in zeilen if z["serie_id"] == "bip_qoq" and z["geo"] in ("DE", "FR")]

    def schreiben(rows):
        with open(ordner / "zeitreihe_lang.csv", "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["serie_id", "geo", "zeit", "wert"])
            w.writeheader()
            w.writerows(rows)
    schreiben(klein)
    with intl_db.verbinden(leere_db) as c:
        b1 = vwl.importieren(c, ordner=ordner)
        assert b1["neu"] == len(klein) and b1["revidiert"] == 0
        assert vwl.importieren(c, ordner=ordner)["unveraendert"] == 1
        c.execute("UPDATE international.observation SET valid_from = valid_from - interval '3 days'")   # erster Stand liegt zurück
        ziel, weg = klein[0], klein[1]
        neu = [dict(z, wert=str(float(z["wert"]) + 1)) if z is ziel else z for z in klein if z is not weg]
        schreiben(neu)
        b2 = vwl.importieren(c, ordner=ordner)
        assert (b2["revidiert"], b2["entfallen"], b2["neu"]) == (1, 1, 1)
        alt_neu = c.execute("SELECT value, valid_to IS NULL FROM international.observation WHERE series_id='bip_qoq' AND geo=%s AND period=%s "
                            "ORDER BY valid_from", (ziel["geo"], ziel["zeit"])).fetchall()
        assert alt_neu == [(float(ziel["wert"]), False), (float(ziel["wert"]) + 1, True)]
    from fastapi.testclient import TestClient
    from plattform.config import Einstellungen
    from plattform.main import erstellen
    cl = TestClient(erstellen(Einstellungen(database_url=leere_db, rate_limit_per_minute=0)))

    def g(geo, **p):
        d = cl.get("/api/v1/observations", params={"series": "bip_qoq", "geo": geo, **p}).json()["data"]["bip_qoq"]
        return dict(map(tuple, d.get(geo, [])))
    gestern = (date.today() - timedelta(days=1)).isoformat()
    assert g(ziel["geo"])[ziel["zeit"]] == float(ziel["wert"]) + 1
    assert g(ziel["geo"], as_of=gestern)[ziel["zeit"]] == float(ziel["wert"])
    assert weg["zeit"] not in g(weg["geo"]) and weg["zeit"] in g(weg["geo"], as_of=gestern)
    # Audit 2026-11, 4.4: Fassungen mit Erfassungszeitpunkt und Quellenstand; as_of ist Datenbankstand, keine Rekonstruktion
    rv = cl.get("/api/v1/series/bip_qoq/revisions", params={"geo": ziel["geo"], "period": ziel["zeit"]}).json()
    fass = rv["data"]
    assert [f["current"] for f in fass] == [False, True] and fass[0]["value"] == float(ziel["wert"]) and fass[1]["value"] != fass[0]["value"]
    assert fass[0]["recorded_to"] == fass[1]["recorded_from"] and fass[1]["recorded_to"] is None
    assert fass[1]["fetched"] and fass[1]["source_updated"] and fass[1]["status"] == "observation"
    assert rv["meta"]["vintage"]["reconstruction"] is False and rv["meta"]["vintage"]["history_start"] and rv["meta"]["pagination"]["total"] == 2
    alle = cl.get("/api/v1/series/bip_qoq/revisions").json()
    assert {(f["geo"], f["period"]) for f in alle["data"]} == {(ziel["geo"], ziel["zeit"]), (weg["geo"], weg["zeit"])}
    assert len(cl.get("/api/v1/series/bip_qoq/revisions", params={"only_revised": "false"}).json()["data"]) == len(klein) + 1
    assert cl.get("/api/v1/series/gibt_es_nicht/revisions").status_code == 404
    kat = cl.get("/api/v1/series/bip_qoq").json()["data"]
    assert kat["superseded_versions"] == 2 and kat["history_start"] and kat["source_updated"]
    alt = cl.get("/api/v1/observations", params={"series": "bip_qoq", "as_of": "2000-01-01"}).json()
    assert alt["data"]["bip_qoq"] == {} and any("vor dem Beginn der Historie" in n for n in alt["meta"]["notes"])
    assert alt["meta"]["vintage"]["reconstruction"] is False
    assert "vintage" not in cl.get("/api/v1/observations", params={"series": "bip_qoq"}).json()["meta"]
