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
