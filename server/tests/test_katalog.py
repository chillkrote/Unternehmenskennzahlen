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


def _verzeichnis(tmp_path, aendern):
    md = tmp_path / "d.md"
    md.write_text(aendern(katalog.VERZEICHNIS.read_text(encoding="utf-8")), encoding="utf-8")
    return md


def test_maskierter_strich_bleibt_im_zelltext(tmp_path):
    """Audit 2026-11, 4.6: ein senkrechter Strich im Text darf die Spalten nicht verschieben."""
    md = _verzeichnis(tmp_path, lambda t: t.replace("| GLEIF | LEI, Sitz, Register-Nr. |", "| GLEIF | LEI \\| Sitz, Register-Nr. |"))
    g = next(q for q in katalog.katalog(verzeichnis=md) if q["id"] == "gleif")
    assert g["used_for"] == "LEI | Sitz, Register-Nr." and g["assessment"] == "voraussichtlich geeignet"


def test_unmaskierter_strich_bricht_ab_statt_spalten_zu_verschieben(tmp_path):
    md = _verzeichnis(tmp_path, lambda t: t.replace("| GLEIF | LEI, Sitz, Register-Nr. |", "| GLEIF | LEI | Sitz, Register-Nr. |"))
    with pytest.raises(katalog.KatalogFehler, match="Zellen"):
        katalog.katalog(verzeichnis=md)


def test_doppelte_quelle_und_unbekannter_status_brechen_ab(tmp_path):
    zeile = next(z for z in katalog.VERZEICHNIS.read_text(encoding="utf-8").splitlines() if z.startswith("| GLEIF |"))
    with pytest.raises(katalog.KatalogFehler, match="doppelte Quellen"):
        katalog.katalog(verzeichnis=_verzeichnis(tmp_path, lambda t: t.replace(zeile, zeile + "\n" + zeile)))
    erg = tmp_path / "e.csv"
    erg.write_text(katalog.ERGAENZUNG.read_text(encoding="utf-8").replace(",GLEIF,unternehmen,voraussichtlich,", ",GLEIF,unternehmen,vielleicht,"), encoding="utf-8")
    with pytest.raises(katalog.KatalogFehler, match="unbekannte Status"):
        katalog.katalog(ergaenzung=erg)


def test_leerraum_im_quellnamen_ist_kein_unterschied(tmp_path):
    md = _verzeichnis(tmp_path, lambda t: t.replace("| GLEIF |", "|  GLEIF\u00a0 |"))
    assert any(q["id"] == "gleif" for q in katalog.katalog(verzeichnis=md))


def test_spaltenkopf_muss_vollstaendig_sein(tmp_path):
    with pytest.raises(katalog.KatalogFehler, match="Spalten"):
        katalog.katalog(verzeichnis=_verzeichnis(tmp_path, lambda t: t.replace("| Lizenz / Weiterverbreitung |", "| Lizenz |")))


def test_katalog_api_vollstaendig(client):
    r = client.get("/api/v1/data-catalog")
    assert r.status_code == 200
    d = r.json()["data"]
    assert [q["name"] for q in d] == [t["quelle"] for t in katalog.verzeichnis_lesen()]
    nach = {q["id"]: q for q in d}
    with open(REPO / "volkswirtschaft" / "serien.csv", newline="", encoding="utf-8") as f:
        reihen = list(csv.DictReader(f))
    with open(REPO / "volkswirtschaft" / "regional" / "serien.csv", newline="", encoding="utf-8") as f:
        reihen += list(csv.DictReader(f))                                    # Regionalreihen (NUTS-3) zählen zu Eurostat
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
