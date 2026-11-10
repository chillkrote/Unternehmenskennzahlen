"""Tests für app/entsoe_abruf.py ohne Netz: XML-Auswertung, Zeitraum, Schlüssel nie in Fehlermeldungen.

    python3 -m unittest discover -s app/tests -p 'test_*.py'
"""
import sys
import unittest
import urllib.error
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import entsoe_abruf as E  # noqa: E402

XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:0">
  <TimeSeries>
    <Period>
      <timeInterval><start>2026-01-31T22:00Z</start><end>2026-02-01T01:00Z</end></timeInterval>
      <resolution>PT60M</resolution>
      <Point><position>1</position><quantity>1000</quantity></Point>
      <Point><position>2</position><quantity>2000</quantity></Point>
      <Point><position>3</position><quantity>500</quantity></Point>
    </Period>
    <Period>
      <timeInterval><start>2026-02-01T01:00Z</start><end>2026-02-01T01:30Z</end></timeInterval>
      <resolution>PT15M</resolution>
      <Point><position>1</position><quantity>400</quantity></Point>
      <Point><position>2</position><quantity>800</quantity></Point>
    </Period>
  </TimeSeries>
</Publication_MarketDocument>"""


class Monatswerte(unittest.TestCase):
    def test_summe_je_utc_monat(self):
        w = E.monatswerte(XML)
        self.assertAlmostEqual(w["2026-01"], 3.0)                      # 22 und 23 Uhr: 1000 + 2000 MWh
        self.assertAlmostEqual(w["2026-02"], 0.5 + 0.1 + 0.2)          # 0 Uhr stündlich, dann zwei Viertelstunden

    def test_a03_luecken_wiederholen_den_letzten_wert(self):
        x = XML.replace(b"<Point><position>2</position><quantity>2000</quantity></Point>", b"")
        w = E.monatswerte(x)
        self.assertAlmostEqual(w["2026-01"], 2.0)                      # Position 2 fehlt: 1000 MW gilt weiter
        self.assertAlmostEqual(w["2026-02"], 0.8)

    def test_letzter_punkt_gilt_bis_periodenende(self):
        x = XML.replace(b"<Point><position>2</position><quantity>800</quantity></Point>", b"")
        self.assertAlmostEqual(E.monatswerte(x)["2026-02"], 0.5 + 0.2)

    def test_unbekannte_aufloesung_wird_uebersprungen(self):
        self.assertEqual(E.monatswerte(XML.replace(b"PT60M", b"P1D").replace(b"PT15M", b"P7D")), {})


class Zeitraum(unittest.TestCase):
    def test_zwoelf_volle_monate_bis_vormonat(self):
        a, b = E.zeitraum(12, date(2026, 11, 10))
        self.assertEqual((a.year, a.month, b.year, b.month), (2025, 11, 2026, 11))

    def test_jahreswechsel(self):
        a, b = E.zeitraum(3, date(2026, 2, 1))
        self.assertEqual((a.year, a.month, b.month), (2025, 11, 2))


class Schluessel(unittest.TestCase):
    def test_fehlermeldung_ohne_schluessel(self):
        geheim = "GEHEIMER-SCHLUESSEL-123"
        def wirf(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 503, "nicht verfügbar", {}, None)
        with mock.patch.object(E.urllib.request, "urlopen", wirf), mock.patch.object(E.time, "sleep"), \
                mock.patch("sys.stderr") as err:
            with self.assertRaises(RuntimeError) as ctx:
                E.abfrage(geheim, "DE", "FR", *E.zeitraum(1, date(2026, 11, 1)), versuche=2)
        self.assertNotIn(geheim, str(ctx.exception))
        self.assertNotIn(geheim, "".join(str(c) for c in err.mock_calls))
        self.assertIn("DE>FR", str(ctx.exception))

    def test_keine_daten_ist_none(self):
        def wirf(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 400, "keine Daten", {}, None)
        with mock.patch.object(E.urllib.request, "urlopen", wirf):
            self.assertIsNone(E.abfrage("x", "DE", "FR", *E.zeitraum(1, date(2026, 11, 1))))

    def test_ohne_schluessel_abbruch(self):
        with mock.patch.dict(E.os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                E.schluessel()


if __name__ == "__main__":
    unittest.main()
