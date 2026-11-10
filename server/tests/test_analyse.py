"""Analyse (P4): Rechenregeln gegen Referenzwerte und gegen die Oberfläche (KOR in Node), Endpunkt /analysis/correlation."""
import json
import math
import random
import shutil
import subprocess
from pathlib import Path

import pytest

from plattform import analyse as an

KOR_JS = Path(__file__).resolve().parents[2] / "app" / "src" / "korrelation.js"
# Anscombe-Quartett, Datensatz I: r = 0,81642, Regressionsgerade y = 3,0001 + 0,5001 x (Anscombe 1973)
AX = [10, 8, 13, 9, 11, 14, 6, 4, 12, 7, 5]
AY = [8.04, 6.95, 7.58, 8.81, 8.33, 9.96, 7.24, 4.26, 10.84, 4.82, 5.68]


def test_referenzwerte_anscombe():
    s = an.stat(AX, AY)
    assert s["r"] == pytest.approx(0.81642, abs=1e-5)
    assert s["slope"] == pytest.approx(0.5001, abs=1e-4) and s["intercept"] == pytest.approx(3.0001, abs=1e-4)
    assert s["n"] == 11 and s["ci"][0] < s["r"] < s["ci"][1]


def test_referenzwerte_p_und_spearman():
    assert an.p_wert(0.5, 10) == pytest.approx(0.141113, abs=1e-5)          # t = 1,633 bei 8 Freiheitsgraden
    assert an.p_wert(0.0, 30) == pytest.approx(1.0) and an.p_wert(1.0, 5) == 0.0
    assert an.spearman([1, 2, 3, 4, 5], [5, 6, 7, 8, 7]) == pytest.approx(0.8207827, abs=1e-6)   # Bindung: mittlere Ränge
    assert an.raenge([3, 1, 3, 2]) == [3.5, 1, 3.5, 2]
    assert an.pearson([1, 1, 1, 1], [1, 2, 3, 4]) is None


def test_transformationen():
    q = [["2020-Q1", 100.0], ["2020-Q2", 110.0], ["2020-Q3", 99.0], ["2020-Q4", 99.0], ["2021-Q1", 120.0]]
    assert an.transf(q, "Q", "yoy") == [["2021-Q1", 20.0]]
    assert an.transf(q, "Q", "pct")[0] == ["2020-Q2", pytest.approx(10.0)]
    assert an.transf(q, "Q", "diff")[1] == ["2020-Q3", -11.0]
    assert an.transf(q, "Q", "log")[0][1] == pytest.approx(math.log(1.1))
    m = [[f"2020-{i:02d}", float(i)] for i in range(1, 13)]
    assert an.auf_freq("M", m, "Q", "mittel") == [["2020-Q1", 2.0], ["2020-Q2", 5.0], ["2020-Q3", 8.0], ["2020-Q4", 11.0]]
    assert an.auf_freq("M", m, "A", "letzter") == [["2020", 12.0]]


def test_lag_verschiebt_b():
    a = [[str(2000 + i), float(i)] for i in range(10)]
    b = [[str(2000 + i), float(i * i)] for i in range(10)]
    r = an.paare(a, b, "A", 2)
    assert r[0] == {"period_a": "2000", "period_b": "2002", "a": 0.0, "b": 4.0} and len(r) == 8


@pytest.mark.skipif(not shutil.which("node"), reason="Node nicht installiert")
def test_gleich_wie_oberflaeche():
    """Dieselben Fälle in KOR (Browser-Code) und in plattform/analyse.py: gleiche Statistik bis auf Rundung."""
    rnd = random.Random(7)
    faelle = [[AX, AY]]
    for n in (5, 12, 40, 120):
        x = [rnd.gauss(0, 1) for _ in range(n)]
        faelle.append([x, [0.6 * v + rnd.gauss(0, 1) + (1 if i % 7 == 0 else 0) for i, v in enumerate(x)]])
    m = [[f"{2010 + i // 12}-{i % 12 + 1:02d}", 100 + i + rnd.gauss(0, 3)] for i in range(60)]
    skript = f"""
const fs=require("fs"),vm=require("vm");const c=vm.createContext({{Intl,Math}});
vm.runInContext(fs.readFileSync({json.dumps(str(KOR_JS))},"utf8")+";globalThis.K=KOR;",c);
const F={json.dumps(faelle)}, M={json.dumps(m)}, R=c.K.rechnen;
const q=R.aufFreq({{freq:"M",pts:M,agg:"letzter"}},"Q","auto");
console.log(JSON.stringify({{stat:F.map(f=>c.K.stat(f[0],f[1])), q, yoy:R.transf(q,"Q","yoy"), log:R.transf(M,"M","log")}}));"""
    js = json.loads(subprocess.run(["node", "-e", skript], capture_output=True, text=True, check=True).stdout)
    namen = {"r": "r", "rho": "rho", "p": "p", "pRho": "p_rho", "b": "slope", "a": "intercept", "dw": "durbin_watson", "neff": "n_eff", "pEff": "p_eff",
             "ra": "autocorr_a", "rb": "autocorr_b"}
    for (x, y), soll in zip(faelle, js["stat"]):
        ist = an.stat(x, y)
        for k_js, k_py in namen.items():
            if soll[k_js] is None:
                assert ist[k_py] is None, k_py
            else:
                assert ist[k_py] == pytest.approx(soll[k_js], rel=1e-9, abs=1e-12), k_py
    q = an.auf_freq("M", m, "Q", "letzter")
    assert q == js["q"]
    yoy = an.transf(q, "Q", "yoy")
    assert [p[0] for p in yoy] == [p[0] for p in js["yoy"]] and [p[1] for p in yoy] == pytest.approx([p[1] for p in js["yoy"]], rel=1e-12)
    for (k1, v1), (k2, v2) in zip(an.transf(m, "M", "log"), js["log"]):
        assert k1 == k2 and v1 == pytest.approx(v2, rel=1e-12)


def test_api_korrelation(client):
    r = client.get("/api/v1/analysis/correlation", params={"a": "bip_yoy:DE", "b": "bip_yoy:FR"})
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["frequency"] == "Q" and d["stats"]["n"] == len(d["rows"]) > 40 and 0.5 < d["stats"]["r"] <= 1
    assert d["a"]["transform"] == "niveau"                        # Rate: Niveau
    x, y = [z["a"] for z in d["rows"]], [z["b"] for z in d["rows"]]
    assert d["stats"]["r"] == pytest.approx(an.pearson(x, y))
    assert len(d["cross_correlation"]) == 2 * an.LAG_MAX["Q"] + 1
    lag = client.get("/api/v1/analysis/correlation", params={"a": "bip_yoy:DE", "b": "bip_yoy:FR", "lag": 1, "from": 2010, "to": 2019}).json()["data"]
    assert all(2010 <= int(z["period_a"][:4]) <= 2019 for z in lag["rows"]) and lag["lag"] == 1


def test_api_korrelation_csv_und_fehler(client):
    r = client.get("/api/v1/analysis/correlation", params={"a": "bip_yoy:DE", "b": "bip_yoy:FR", "format": "csv"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    zeilen = r.text.lstrip("﻿").strip().split("\r\n")
    assert zeilen[0].startswith("zeitraum_a;zeitraum_b;") and len(zeilen) > 40
    assert client.get("/api/v1/analysis/correlation", params={"a": "gibtsnicht:DE", "b": "bip_yoy:FR"}).status_code == 404
    assert client.get("/api/v1/analysis/correlation", params={"a": "bip_yoy", "b": "bip_yoy:FR"}).status_code == 422
    assert client.get("/api/v1/analysis/correlation", params={"a": "bip_yoy:DE", "b": "bip_yoy:FR", "ta": "quadrat"}).status_code == 422


def test_observations_csv(client):
    r = client.get("/api/v1/observations", params={"series": "bip_yoy", "geo": "DE", "format": "csv"})
    j = client.get("/api/v1/observations", params={"series": "bip_yoy", "geo": "DE"}).json()["data"]
    zeilen = r.text.lstrip("﻿").strip().split("\r\n")
    assert zeilen[0] == "reihe;gebiet;zeitraum;wert" and len(zeilen) - 1 == len(j["bip_yoy"]["DE"])
