"""Regionaldaten (NUTS-3, Kreise): Abruf-Logik, Zuordnung NUTS-3 <-> Kreisschlüssel, innere Stimmigkeit der Daten, API /regions."""
import csv
import importlib.util
import json
from collections import defaultdict
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ORDNER = REPO / "volkswirtschaft/regional"
spec = importlib.util.spec_from_file_location("abruf_regional", REPO / "volkswirtschaft/skripte/abruf_regional.py")
ab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ab)


def _werte():
    w = defaultdict(dict)
    with open(ORDNER / "zeitreihe_lang.csv", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            w[z["serie_id"]][(z["geo"], z["zeit"])] = float(z["wert"])
    return w


W = _werte()
REG = ab.lies_regionen()


def test_jsonstat_entpacken():
    d = {"id": ["unit", "geo", "time"], "size": [1, 2, 2],
         "dimension": {"unit": {"category": {"index": {"MIO_EUR": 0}}}, "geo": {"category": {"index": {"DE111": 0, "DE112": 1}}},
                       "time": {"category": {"index": {"2022": 0, "2023": 1}}}},
         "value": {"0": 1.0, "1": 2.0, "3": 4.0}}
    assert ab.jsonstat_zeilen(d) == [("DE111", "2022", 1.0), ("DE111", "2023", 2.0), ("DE112", "2023", 4.0)]


def test_ableiten_nur_aus_demselben_jahr_und_gebiet():
    werte = {"r3_bws": {("A", "2022"): 200.0, ("A", "2023"): 0.0, ("B", "2023"): 10.0}, "r3_bws_industrie": {("A", "2022"): 50.0, ("A", "2023"): 10.0},
             "r3_bws_dienstleistung": {("A", "2022"): 140.0, ("B", "2022"): 7.0}}
    d = ab.ableiten(werte)
    assert d["r3_anteil_industrie"] == {("A", "2022"): 25.0}                 # Nenner 0 ergibt keinen Wert, B ohne Industriewert keinen
    assert d["r3_anteil_dienstleistung"] == {("A", "2022"): 70.0}            # B: Dienstleistung 2022, Gesamt nur 2023 -> kein Wert


def test_vgrdl_link_und_abgleich():
    html = '<a href="/sites/default/files/2026-09/vgrdl_r2b1_bs2025_4.xlsx">Excel</a>'
    assert ab.vgrdl_url(html) == "https://www.statistikportal.de/sites/default/files/2026-09/vgrdl_r2b1_bs2025_4.xlsx"
    with pytest.raises(SystemExit):
        ab.vgrdl_url("<html></html>")
    assert ab.abgleich({("A", "2023"): 100.0, ("B", "2023"): 100.0}, {("A", "2023"): 100.5, ("B", "2023"): 90.0}) == [("B", "2023", 100.0, 90.0, -10.0)]


def test_zuordnung_vollstaendig_und_eindeutig():
    kreise = {f["properties"]["id"] for f in json.loads((REPO / "app/geo/kreise_de.geojson").read_text())["features"]}
    assert len(REG) == 400
    assert len({r["nuts3"] for r in REG}) == len({r["ags"] for r in REG}) == 400
    assert {r["ags"] for r in REG} == kreise                                 # jede Kreisfläche der Karte hat eine NUTS-3-Region
    assert all(r["land"] == "DE-" + ab.LAND[r["ags"][:2]] for r in REG)
    nuts = {r["ags"]: r["nuts3"] for r in REG}
    assert nuts["08111"] == "DE111" and nuts["11000"] == "DE300" and nuts["02000"] == "DE600"   # Stuttgart, Berlin, Hamburg


def test_daten_decken_alle_kreise_und_sind_stimmig():
    codes = {r["nuts3"] for r in REG}
    for sid in ("r3_bip", "r3_bip_je_einwohner", "r3_bevoelkerung", "r3_bws", "r3_erwerbstaetige", "r3_bip_je_arbeitsstunde"):
        assert {g for g, _ in W[sid]} == codes, sid
        assert {t for _, t in W[sid]} == {str(j) for j in range(2000, 2025)}, sid      # VGRdL: 2000 bis 2024 ohne Lücke
    # BIP je Einwohner = BIP / Einwohner und BIP je Erwerbstätigen = BIP / Erwerbstätige (Einwohner und Erwerbstätige sind auf
    # 0,1 Tsd. gerundet, wie die VGRdL es für die Weitergabe vorschreibt; Abweichung daher unter 0,5 %)
    for k, v in W["r3_bip_je_einwohner"].items():
        assert abs(W["r3_bip"][k] * 1000 / W["r3_bevoelkerung"][k] - v) / v < 0.005, k
    for k, v in W["r3_bip_je_erwerbstaetigen"].items():
        assert abs(W["r3_bip"][k] * 1000 / W["r3_erwerbstaetige"][k] - v) / v < 0.005, k
    assert all(round(v, 1) == v for sid in ("r3_bevoelkerung", "r3_erwerbstaetige") for v in W[sid].values())
    # Bruttowertschöpfung der Industrie ist Teil der gesamten
    assert all(0 <= v <= 100 for v in W["r3_anteil_industrie"].values())
    # Summe der Kreise = Bundes-BIP (VGRdL-Zeile Deutschland und Eurostat nama_10r_3gdp geo=DE): 2021 3 682 340, 2023 4 219 310 Mio. €
    summe = defaultdict(float)
    for (g, t), v in W["r3_bip"].items():
        summe[t] += v
    assert abs(summe["2021"] - 3682340) < 5 and abs(summe["2023"] - 4219310) < 5 and abs(summe["2024"] - 4328970) < 5


def test_abgleich_mit_eurostat():
    """Eurostat verteilt dasselbe Bundes-BIP anders auf die Kreise (älterer Rechenstand); Mainz 2023 weicht am stärksten ab."""
    with open(ORDNER / "abgleich_eurostat.csv", encoding="utf-8") as f:
        z = list(csv.DictReader(f))
    assert z and all(abs(float(x["abweichung_pct"])) > 1 for x in z)
    assert z[0]["nuts3"] == "DEB35" and float(z[0]["bip_vgrdl_mio_eur"]) == W["r3_bip"][("DEB35", z[0]["jahr"])]


def test_katalog_der_regionalreihen():
    with open(ORDNER / "serien.csv", encoding="utf-8") as f:
        s = list(csv.DictReader(f))
    # Eurostat (KKS-Index) fehlt, solange Eurostat beim Abruf drosselt und kein früherer Stand in rohdaten/ liegt
    assert len(ab.VGRDL) + len(ab.ABGELEITET) <= len(s) <= len(ab.VGRDL) + len(ab.ABGELEITET) + len(ab.EUROSTAT)
    assert all(x["ebene"] == "nuts3" and len(x["erwartet"].split(",")) == 400 for x in s)
    assert {x["quelle"] for x in s} <= {ab.VGRDL_NAME, "Eurostat"} and all(x["url"].startswith("https://") for x in s)
    assert next(x for x in s if x["serie_id"] == "r3_bip")["letzter_zeitraum"] == "2024"
    assert all(x["serie_id"] in W for x in s)


# ---------------------------------------------------------------- API
def test_regionen_api(client):
    r = client.get("/api/v1/regions").json()["data"]
    assert len(r) == 400 and {x["level"] for x in r} == {"nuts3"}
    bw = client.get("/api/v1/regions", params={"parent": "DE-BW"}).json()["data"]
    assert len(bw) == 44 and all(x["national_code"].startswith("08") for x in bw)
    s = client.get("/api/v1/regions/08111").json()["data"]                    # Landesschlüssel oder NUTS-Code
    assert s["code"] == "DE111" and s == client.get("/api/v1/regions/DE111").json()["data"]
    bip = next(x for x in s["series"] if x["id"] == "r3_bip")
    assert bip["last"][1] == W["r3_bip"][("DE111", bip["last"][0])] and 1 <= bip["rank"] <= bip["of"] == 400
    assert client.get("/api/v1/regions/XX999").status_code == 404 and client.get("/api/v1/regions/a;b").status_code == 422


def test_regionalwerte_und_querschnitt(client):
    d = client.get("/api/v1/regions/values", params={"series": "r3_bip_je_einwohner", "year": "2023"}).json()["data"]
    assert d["covered"] == d["expected"] == 400 and d["year"] == "2023"
    top = min(d["values"], key=lambda x: x["rank"])
    assert top["value"] == max(W["r3_bip_je_einwohner"][(g, "2023")] for g in {r["nuts3"] for r in REG})
    assert client.get("/api/v1/regions/values", params={"series": "bip_qoq"}).status_code == 404     # Länderreihe, keine Regionalreihe
    q = client.get("/api/v1/regions/cross-section", params={"a": "r3_bip_je_einwohner", "b": "r3_bip_je_erwerbstaetigen"}).json()["data"]
    assert q["stat"]["n"] == 400 and q["stat"]["r"] > 0.5 and q["stat"]["p"] < 0.001 and "durbin_watson" not in q["stat"]
    from plattform import analyse as an
    xs, ys = [p[1] for p in q["points"]], [p[2] for p in q["points"]]
    assert q["stat"]["r"] == pytest.approx(an.pearson(xs, ys))


def test_regionalreihen_im_katalog_und_in_der_qualitaet(client):
    kat = client.get("/api/v1/series", params={"level": "nuts3"}).json()["data"]
    with open(ORDNER / "serien.csv", encoding="utf-8") as f:
        n = sum(1 for _ in csv.DictReader(f))
    assert len(kat) == n >= 12 and all(x["level"] == "nuts3" for x in kat)
    assert all(x["level"] == "country" for x in client.get("/api/v1/series", params={"level": "country"}).json()["data"])
    q = client.get("/api/v1/data-quality", params={"as_of": "2026-11-11"}).json()["data"]
    zeile = {x["series_id"]: x for x in q["coverage"]["series"]["rows"]}
    assert zeile["r3_bip"]["expected"] == 400 and zeile["r3_bip"]["share"] == 1.0
    assert any(x["adapter"] == "vwl_regional" and x["last_ok"] for x in q["freshness"]["import_runs"])
