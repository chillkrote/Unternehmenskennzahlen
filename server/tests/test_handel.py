"""Handelsabhängigkeit (P5a): Regeln gegen Referenzwerte und Endpunkte gegen die Quelldatei app/data/gueter.json."""
import json
from pathlib import Path

import pytest

from plattform import handel as h

GUETER = json.loads((Path(__file__).resolve().parents[2] / "app" / "data" / "gueter.json").read_text(encoding="utf-8"))


def test_hhi_referenz():
    assert h.hhi({"A": 1}) == 10000.0                                       # Monopol
    assert h.hhi({c: 1 for c in "ABCD"}) == 2500.0                          # vier gleich große: 4 · 25²
    assert h.hhi({"A": 30, "B": 30, "C": 20, "D": 20}) == 2600.0            # Lehrbuchbeispiel: 900+900+400+400
    assert h.hhi({}) == 0 and h.hhi({"A": 0}) == 0
    assert [h.einstufung(x) for x in (999, 1000, 1800, 1801)] == ["gering", "maessig", "hoch", "hoch"]


def test_anteile_cr_alternativen():
    w = {"CN": 50.0, "US": 20.0, "DE": 15.0, "FR": 10.0, "IT": 5.0}
    assert sum(h.anteile(w).values()) == pytest.approx(1.0)
    assert h.cr(w) == 0.85 and h.cr(w, 1) == 0.5
    alt = h.alternativen(w, ["CN"], 2)
    assert [a["geo"] for a in alt] == ["US", "DE"] and alt[0]["world_share"] == 0.2 and alt[0]["share_without_excluded"] == 0.4


def _welt(gut, jahr):
    i = GUETER["jahre"].index(jahr)
    return {geo: e[gut]["v"][i] for geo, e in GUETER["laender"].items() if gut in e and e[gut]["v"][i] is not None}


def test_gueter_wie_quelldatei(client):
    d = client.get("/api/v1/trade/goods").json()["data"]
    assert [g["id"] for g in d] == [g["id"] for g in GUETER["gruppen"]]
    j = GUETER["jahr"]
    for g in d:
        w = _welt(g["id"], j)
        # Weltwert in der Datei aus ungerundeten Daten, Länderwerte auf 0,1 gerundet: Abweichung höchstens 0,05 je Land
        assert g["year"] == j and g["world_value"] == pytest.approx(GUETER["welt"][g["id"]][str(j)], abs=0.05 * len(w) + 0.1)
        assert g["hhi"] == h.hhi(w) and g["top_exporter"] == max(w, key=w.get)


def test_gut_einzeln_und_verlauf(client):
    d = client.get("/api/v1/trade/goods/pkw", params={"top": 5}).json()["data"]
    assert len(d["exporters"]) == 5 and d["exporters"][0]["rank"] == 1
    assert sum(e["world_share"] for e in d["exporters"]) <= 1.0001
    assert [x["year"] for x in d["history"]] == GUETER["jahre"]
    assert client.get("/api/v1/trade/goods/gibtsnicht").status_code == 404


def test_alternativen(client):
    d = client.get("/api/v1/trade/goods/chips/alternatives", params={"exclude": "CN,TW", "n": 3}).json()["data"]
    assert len(d["alternatives"]) == 3 and not {"CN", "TW"} & {a["geo"] for a in d["alternatives"]}
    assert sum(a["share_without_excluded"] for a in d["alternatives"]) <= 1.0001
    assert client.get("/api/v1/trade/goods/chips/alternatives", params={"exclude": "china"}).status_code == 422


def test_laenderprofil(client):
    d = client.get("/api/v1/trade/countries/DE").json()["data"]
    pkw = next(g for g in d["goods"] if g["good"] == "pkw")
    quelle = GUETER["laender"]["DE"]["pkw"]
    assert pkw["value"] == quelle["v"][-1] and [p["partner"] for p in pkw["partners"]] == [p[0] for p in quelle["partner"]]
    assert 0 < pkw["top5_partner_share"] <= 1 and pkw["rank"] >= 1
    assert client.get("/api/v1/trade/countries/de").status_code == 422
    assert client.get("/api/v1/trade/countries/XX").status_code == 404


# ---------- Importabhängigkeit (Audit 2026-11, 4.3) ----------
IMPORTE = json.loads((Path(__file__).resolve().parents[2] / "app" / "data" / "gueter_importe.json").read_text(encoding="utf-8"))


def test_untergrenze_statt_top5_hhi():
    """Ein HHI nur über die größten Partner überzeichnet; aus einer Teilmenge folgt nur eine Untergrenze."""
    alle = {"a": 50, "b": 20, "c": 20, "d": 10}
    teil = {"a": 50, "b": 20}
    assert h.hhi(teil) > h.hhi(alle)                                     # früheres partner_hhi_top5: 5918 statt 3400
    assert h.hhi_untergrenze(teil, 100) == 2900.0 <= h.hhi(alle) <= h.hhi_obergrenze(teil, 100) == 3400.0
    assert h.hhi_untergrenze(alle, 100) == h.hhi(alle) and h.hhi_untergrenze({}, 0) == 0.0
    assert h.importanteil(30, 120) == 0.25 and h.importanteil(1, 0) is None and h.importanteil(None, 5) is None


def test_importabhaengigkeit_gegen_datei(client):
    r = client.get("/api/v1/trade/import-dependencies", params={"geo": "DE"})
    assert r.status_code == 200
    d = r.json()["data"]
    j = IMPORTE["jahre"].index(IMPORTE["jahr"])
    assert d["year"] == IMPORTE["jahr"] and len(d["goods"]) == sum(1 for e in IMPORTE["laender"]["DE"].values() if e["v"][j] is not None)
    for g in d["goods"]:
        q = IMPORTE["laender"]["DE"][g["good"]]
        assert g["import_value"] == q["v"][j] and g["supplier_count"] == q["n"][j] and g["supplier_hhi"] == q["hhi"][j]
        assert g["supplier_hhi_complete"] is True and [s["geo"] for s in g["suppliers"]] == [x[0] for x in q["top"]]
        assert g["supplier_count"] >= len(g["suppliers"]) and 0 < g["suppliers_listed_share"] <= 1.0001
        # der HHI über alle Lieferländer liegt nie unter der Untergrenze aus den aufgelisteten
        assert g["supplier_hhi"] >= h.hhi_untergrenze({s["geo"]: s["value"] for s in g["suppliers"]}, g["import_value"]) - 1.0
        assert g["top_supplier"] == g["suppliers"][0]["geo"] and g["top_share"] == pytest.approx(g["suppliers"][0]["import_share"], abs=0.002)
        assert [x["year"] for x in g["history"]] == [t for t, v in zip(IMPORTE["jahre"], q["v"]) if v is not None]
    assert any("Fusionskontrolle" in n for n in r.json()["meta"]["notes"]) and any("freie Lieferkapazität" in n for n in r.json()["meta"]["notes"])


def test_abhaengigkeit_von_einem_lieferland(client):
    d = client.get("/api/v1/trade/import-dependencies", params={"geo": "DE", "supplier": "CN"}).json()["data"]
    belegt = [g for g in d["goods"] if g["dependency"]["basis"] == "belegt"]
    assert belegt and all(g["dependency"]["import_share"] == pytest.approx(g["dependency"]["value"] / g["import_value"], abs=0.0001) for g in belegt)
    anteile = [g["dependency"]["import_share"] or 0 for g in d["goods"]]
    assert anteile == sorted(anteile, reverse=True)
    rest = [g for g in d["goods"] if g["dependency"]["basis"] != "belegt"]
    assert all(g["dependency"]["import_share"] is None and g["dependency"]["below_share"] <= g["suppliers"][-1]["import_share"] + 1e-9 for g in rest
               if len(g["suppliers"]) >= 10)
    eins = client.get("/api/v1/trade/import-dependencies", params={"geo": "DE", "good": "chips", "year": IMPORTE["jahre"][0]}).json()["data"]
    assert len(eins["goods"]) == 1 and eins["goods"][0]["suppliers"] == [] and eins["year"] == IMPORTE["jahre"][0]
    assert client.get("/api/v1/trade/import-dependencies", params={"geo": "de"}).status_code == 422
    assert client.get("/api/v1/trade/import-dependencies", params={"geo": "XX"}).status_code == 404
    assert client.get("/api/v1/trade/import-dependencies", params={"geo": "DE", "good": "gibtsnicht"}).status_code == 404


def test_abnehmer_hhi_vollstaendig_statt_top5(client):
    d = client.get("/api/v1/trade/countries/DE").json()["data"]
    pkw = next(g for g in d["goods"] if g["good"] == "pkw")
    q = GUETER["laender"]["DE"]["pkw"]
    assert "partner_hhi_top5" not in pkw and pkw["partner_hhi_complete"] is True
    assert pkw["partner_count"] == q["pn"] > 5 and pkw["partner_hhi"] == q["phhi"] >= pkw["partner_hhi_lower_bound"]
