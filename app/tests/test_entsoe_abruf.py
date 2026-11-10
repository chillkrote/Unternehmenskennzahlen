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


def _xml(start, ende, mw=1000):
    """Eine Periode mit einem Punkt (A03: gilt bis zum Periodenende), stündlich."""
    f = "%Y-%m-%dT%H:%MZ"
    return (f'<Publication_MarketDocument xmlns="urn:x"><TimeSeries><Period><timeInterval><start>{start.strftime(f)}</start>'
            f'<end>{ende.strftime(f)}</end></timeInterval><resolution>PT60M</resolution><Point><position>1</position>'
            f'<quantity>{mw}</quantity></Point></Period></TimeSeries></Publication_MarketDocument>').encode()


class Fenster(unittest.TestCase):
    """Zeiträume über zwölf Monate werden geteilt und lückenlos, ohne doppelte Monate, zusammengeführt (Audit 2026-11, 4.1)."""
    HEUTE = date(2026, 11, 10)

    def test_fenster_12_24_36(self):
        for monate, n in ((12, 1), (24, 2), (36, 3), (30, 3), (1, 1), (13, 2)):
            a, b = E.zeitraum(monate, self.HEUTE)
            f = E.fenster(a, b)
            self.assertEqual(len(f), n, monate)
            self.assertEqual((f[0][0], f[-1][1]), (a, b))
            for (x1, x2), (y1, y2) in zip(f, f[1:]):
                self.assertEqual(x2, y1)                               # schließen an, überlappen nicht
            for x1, x2 in f:
                self.assertLessEqual(len(E.monatsliste(x1, x2)), 12)
            self.assertEqual(len(E.monatsliste(a, b)), monate)
            self.assertEqual(E.monatsliste(a, b)[-1], "2026-10")

    def test_richtung_fuehrt_fenster_zusammen(self):
        for monate in (12, 24, 36):
            a, b = E.zeitraum(monate, self.HEUTE)
            abfragen = []
            def hole(token, von, nach, x, y):
                abfragen.append((x, y))
                return _xml(x - E.timedelta(hours=5), y + E.timedelta(hours=5))   # Quelle liefert über das Fenster hinaus
            w = E.richtung("x", "DE", "FR", a, b, hole=hole)
            self.assertEqual(len(abfragen), monate // 12)
            self.assertEqual(sorted(w), E.monatsliste(a, b))           # jeder Monat genau einmal, keiner außerhalb
            for m, (gwh, h) in w.items():
                self.assertAlmostEqual(h, E.stunden_im_monat(m))       # nichts doppelt an den Fenstergrenzen
                self.assertAlmostEqual(gwh, h)                         # 1000 MW je Stunde = 1 GWh

    def test_fenster_ohne_daten_bleibt_luecke(self):
        a, b = E.zeitraum(24, self.HEUTE)
        f = E.fenster(a, b)
        hole = lambda t, v, n, x, y: None if x == f[0][0] else _xml(x, y)
        w = E.richtung("x", "DE", "FR", a, b, hole=hole)
        out = E.zusammenstellen(E.monatsliste(a, b), {("DE", "FR"): w, ("FR", "DE"): None}, heute=self.HEUTE)
        self.assertEqual(out["paare"]["DE>FR"][:12], [None] * 12)
        self.assertTrue(all(v is not None for v in out["paare"]["DE>FR"][12:]))
        self.assertEqual(out["ohne_daten"], ["FR>DE"])
        self.assertEqual(out["vollstaendigkeit"]["monate_ohne_daten"], 12)

    def test_doppelte_zeitpunkte_zaehlen_einmal(self):
        a, b = E.zeitraum(1, self.HEUTE)
        x = _xml(a, b).replace(b"</TimeSeries>", _xml(a, b).split(b"<TimeSeries>")[1].split(b"</TimeSeries>")[0] + b"</TimeSeries>")
        self.assertAlmostEqual(E.monatswerte(x)["2026-10"], 744.0)

    def test_teilmonat_steht_unter_abdeckung(self):
        a, b = E.zeitraum(2, self.HEUTE)
        halb = E.datetime(2026, 10, 16, 12, tzinfo=E.timezone.utc)
        w = E.monatsstunden(_xml(a, halb), a, b)
        out = E.zusammenstellen(E.monatsliste(a, b), {("DE", "FR"): w}, heute=self.HEUTE)
        self.assertEqual(out["abdeckung"], {"DE>FR": {"2026-10": 0.5}})
        self.assertEqual(out["vollstaendigkeit"]["monate_teilweise"], 1)

    def test_utc_monatsgrenze(self):
        a, b = E.zeitraum(1, date(2026, 4, 1))                         # März 2026 mit Sommerzeitumstellung: in UTC 744 Stunden
        self.assertEqual((a.hour, a.tzinfo), (0, E.timezone.utc))
        self.assertEqual(E.stunden_im_monat("2026-03"), 744)
        self.assertEqual(E.stunden_im_monat("2024-02"), 696)

    def test_fehlgeschlagene_richtung_behaelt_alten_stand(self):
        monate = ["2026-09", "2026-10"]
        alt = {"monate": ["2026-08", "2026-09"], "paare": {"DE>FR": [1.0, 2.0]}, "abdeckung": {"DE>FR": {"2026-09": 0.9, "2026-08": 0.5}}}
        out = E.zusammenstellen(monate, {("DE", "FR"): RuntimeError("DE>FR: HTTP 503"), ("FR", "DE"): RuntimeError("FR>DE: HTTP 503")}, alt)
        self.assertEqual(out["paare"], {"DE>FR": [2.0, None]})
        self.assertEqual(out["uebernommen"], ["DE>FR"])
        self.assertEqual(out["abdeckung"], {"DE>FR": {"2026-09": 0.9}})
        self.assertEqual(out["ohne_daten"], ["FR>DE"])

    def test_zu_viele_ausfaelle_lassen_die_datei_stehen(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            ziel = Path(d) / "strom_entsoe.json"
            ziel.write_text('{"alt":1}')
            def wirf(*a, **k):
                raise RuntimeError("DE>FR: HTTP 503")
            with mock.patch.object(E, "ZIEL", ziel), mock.patch.object(E, "abfrage", wirf), mock.patch.object(E, "schluessel", lambda: "x"), \
                    mock.patch("sys.stderr"):
                with self.assertRaises(SystemExit):
                    E.main(["--monate", "24"])
            self.assertEqual(ziel.read_text(), '{"alt":1}')
            self.assertEqual(list(Path(d).iterdir()), [ziel])

    def test_main_verarbeitet_24_monate(self):
        import json, tempfile
        with tempfile.TemporaryDirectory() as d:
            ziel = Path(d) / "strom_entsoe.json"
            with mock.patch.object(E, "ZIEL", ziel), mock.patch.object(E, "abfrage", lambda t, v, n, x, y: _xml(x, y)), \
                    mock.patch.object(E, "schluessel", lambda: "x"), mock.patch.object(E, "GRENZEN", ["DE-FR"]), mock.patch("sys.stderr"):
                E.main(["--monate", "24"])
            out = json.loads(ziel.read_text())
            self.assertEqual(len(out["monate"]), 24)                   # früher: min(monate, 12)
            self.assertEqual(len(out["paare"]["DE>FR"]), 24)
            self.assertEqual(out["abdeckung"], {})


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
