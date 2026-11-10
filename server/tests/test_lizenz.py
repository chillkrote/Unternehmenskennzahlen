"""E1: Yahoo-Werte gelangen weder in die Server-Fassung der Oberfläche noch in die Server-Datenbank."""
import ast
import os
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


def test_schalter_fuer_lokale_datenbank():
    with mock.patch.dict(os.environ, {"SPHAERAE_MIT_YAHOO": ""}):
        assert not lizenz.mit_yahoo()
    with mock.patch.dict(os.environ, {"SPHAERAE_MIT_YAHOO": "1"}):
        assert lizenz.mit_yahoo()
