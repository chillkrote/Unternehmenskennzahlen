"""E1: Yahoo-Werte gelangen weder in die Server-Fassung der Oberfläche noch in die Server-Datenbank."""
import ast
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

from plattform import lizenz

REPO = Path(__file__).resolve().parents[2]


def _build_liste():
    baum = ast.parse((REPO / "app" / "build.py").read_text(encoding="utf-8"))
    for knoten in baum.body:
        if isinstance(knoten, ast.Assign) and any(getattr(t, "id", None) == "YAHOO_WERTE" for t in knoten.targets):
            return tuple(ast.literal_eval(knoten.value))
    raise AssertionError("YAHOO_WERTE fehlt in app/build.py")


def test_gleiche_liste_in_build_und_server():
    assert _build_liste() == lizenz.YAHOO_WERTE


def test_api_fassung_immer_oeffentlich():
    text = (REPO / "app" / "build.py").read_text(encoding="utf-8")
    assert "if a.api and not a.mit_yahoo:" in text and "a.oeffentlich = True" in text


def _konstante(name):
    baum = ast.parse((REPO / "app" / "build.py").read_text(encoding="utf-8"))
    for knoten in baum.body:
        if isinstance(knoten, ast.Assign) and any(getattr(t, "id", None) == name for t in knoten.targets):
            return tuple(ast.literal_eval(knoten.value))
    raise AssertionError(f"{name} fehlt in app/build.py")


def test_gleiche_regeln_fuer_dateien_und_abschluesse():
    assert _konstante("YAHOO_DATEIEN") == lizenz.YAHOO_DATEIEN
    assert _konstante("NICHT_YAHOO_WERTE") == lizenz.NICHT_YAHOO_WERTE
    assert "dist-api" in _konstante("SERVER_ORDNER")


def test_testschalter_ist_in_produktion_ein_fehler():
    import pytest
    with mock.patch.dict(os.environ, {"SPHAERAE_MIT_YAHOO": "1", "PLATTFORM_UMGEBUNG": "produktion"}):
        with pytest.raises(RuntimeError):
            lizenz.mit_yahoo()
    with mock.patch.dict(os.environ, {"SPHAERAE_MIT_YAHOO": "", "PLATTFORM_UMGEBUNG": "produktion"}):
        assert not lizenz.mit_yahoo()


def test_firma_ohne_yahoo_abschluesse():
    nichtbank = {"id": "U1", "werte": {"umsatz": 5.0, "x_anteil_stimmrechte": 0.3},
                 "abschluesse": [{"jahr": 2025, "quelle": "Yahoo Finance (Sekundärquelle; Originalabgleich offen)"},
                                 {"jahr": 2024, "quelle": "Geschäftsbericht (Primärquelle)"}],
                 "termine": [{"quelle": "yahoo"}, {"quelle": "finanzkalender"}]}
    f = lizenz.firma_ohne_yahoo_abschluesse(nichtbank)
    assert f["werte"] == {"x_anteil_stimmrechte": 0.3}
    assert [a["jahr"] for a in f["abschluesse"]] == [2024] and [t["quelle"] for t in f["termine"]] == ["finanzkalender"]
    bank = lizenz.firma_ohne_yahoo_abschluesse({"id": "U2", "bank": "X", "gruppe": "Private Banken", "werte": {"bilanzsumme": 1.0}})
    assert bank["werte"] == {"bilanzsumme": 1.0}                        # eigene Erhebung (HGB, EBA) bleibt


def _build(tmp, *args):
    import pytest
    if not (REPO / "app" / "src" / "terminal.html").exists():
        pytest.skip("app/src/terminal.html fehlt im Checkout")
    pytest.importorskip("openpyxl")
    ziel = tmp / "dist-test"
    r = subprocess.run([sys.executable, str(REPO / "app" / "build.py"), "--nur-seite", "--ziel", str(ziel), *args],
                       capture_output=True, text=True, cwd=REPO / "app")
    return ziel, r


def test_produktions_build_enthaelt_keine_gesperrten_daten(tmp_path):
    """Baut die Server-Fassung wie im Betrieb und prüft HTML, eingebettete Blöcke und alle Dateien daneben (Audit 2026-11, 4.5)."""
    ziel, r = _build(tmp_path, "--api", "/api/v1")
    assert r.returncode == 0, r.stderr[-2000:]
    assert lizenz.pruefe_ausgabe(ziel) == []
    m = json.loads((ziel / lizenz.MANIFEST).read_text())
    assert m["oeffentlich"] is True and m["yahoo_kurse"] is False
    assert not any((ziel / "data" / n).exists() for n in lizenz.YAHOO_DATEIEN)
    # die strenge Stufe findet in derselben Fassung die Yahoo-Abschlüsse (E6 offen): der Prüfer ist also nicht blind
    assert any("Yahoo-Termine" in v for v in lizenz.pruefe_ausgabe(ziel, streng=True))
    # der Prüfer schlägt an, wenn nachträglich eine gesperrte Datei oder ein gesperrter Wert auftaucht
    (ziel / "data" / "markt.json").write_text("{}")
    u = json.loads((ziel / "data" / "unternehmen.json").read_text())
    u["unternehmen"][0].setdefault("werte", {})["kgv"] = 12.0
    (ziel / "data" / "unternehmen.json").write_text(json.dumps(u))
    v = lizenz.pruefe_ausgabe(ziel)
    assert any("markt.json" in x for x in v) and any("Yahoo-Kurswerte" in x for x in v)


def test_strenger_build_ohne_yahoo_abschluesse(tmp_path):
    ziel, r = _build(tmp_path, "--api", "/api/v1", "--ohne-yahoo-abschluesse")
    assert r.returncode == 0, r.stderr[-2000:]
    assert lizenz.pruefe_ausgabe(ziel, streng=True) == []
    u = json.loads((ziel / "data" / "unternehmen.json").read_text())
    assert u["ohne_yahoo_abschluesse"] == 1 and any(f.get("werte", {}).get("bilanzsumme") for f in u["unternehmen"] if f.get("bank"))


def test_fassung_mit_yahoo_nie_im_server_ordner_und_vom_pruefer_erkannt(tmp_path):
    import pytest
    pytest.importorskip("openpyxl")
    r = subprocess.run([sys.executable, str(REPO / "app" / "build.py"), "--nur-seite", "--api", "/api/v1", "--mit-yahoo", "--ziel", "dist-api"],
                       capture_output=True, text=True, cwd=REPO / "app")
    assert r.returncode != 0 and "dist-api" in (r.stderr + r.stdout)
    ziel, r = _build(tmp_path, "--api", "/api/v1", "--mit-yahoo")
    assert r.returncode == 0, r.stderr[-2000:]
    v = lizenz.pruefe_ausgabe(ziel)
    assert any(lizenz.MANIFEST in x for x in v) and len(v) > 3


def test_schalter_fuer_lokale_datenbank():
    with mock.patch.dict(os.environ, {"SPHAERAE_MIT_YAHOO": ""}):
        assert not lizenz.mit_yahoo()
    with mock.patch.dict(os.environ, {"SPHAERAE_MIT_YAHOO": "1"}):
        assert lizenz.mit_yahoo()
