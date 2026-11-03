import copy
import json
import unittest
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import dbhelp  # noqa: F401
import sec

FIXTURE = Path(__file__).parent / "fixtures" / "sec_companyfacts_adtn_assets.json"


def eintrag(**kw):
    e = {"end": "2024-12-31", "val": 100, "accn": "0000000000-25-000001", "fy": 2024, "fp": "FY", "form": "10-K", "filed": "2025-03-03"}
    e.update(kw)
    return e


def roh(*eintraege, unit="USD"):
    return {"cik": 926282, "facts": {"us-gaap": {"Assets": {"units": {unit: list(eintraege)}}}}}


class Cik(unittest.TestCase):
    def test_auffuellen_auf_zehn_stellen(self):
        self.assertEqual(sec.cik_normalisieren(926282), "0000926282")
        self.assertEqual(sec.companyfacts_url("320193"), "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json")

    def test_nicht_numerische_cik_abgelehnt(self):
        for s in ("abc", "../x", "12345678901", "", "92 6282", "9262.82"):
            with self.assertRaises(ValueError, msg=s):
                sec.cik_normalisieren(s)


class Pilotliste(unittest.TestCase):
    def test_zehn_unternehmen_isin_cik_und_stammdaten(self):
        import csv
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "stammdaten"))
        import ids
        reg = ids.lade(neu=True)
        with open(Path(__file__).resolve().parents[1] / "us_pilot.csv", encoding="utf-8", newline="") as f:
            zeilen = list(csv.DictReader(f))
        self.assertEqual(len(zeilen), 10)
        self.assertEqual(sum(z["bank"] == "ja" for z in zeilen), 2)
        self.assertEqual(len({z["isin"] for z in zeilen}), 10)
        for z in zeilen:
            self.assertTrue(ids.isin_pruefsumme_ok(z["isin"]), z["isin"])
            sec.cik_normalisieren(z["cik"])
            self.assertIsNotNone(reg.aufloesen(z["isin"]), f"{z['name']} nicht in stammdaten registriert")


class Normalisierung(unittest.TestCase):
    def zeilen(self, r):
        return sec.normalisieren(sec.extrahieren(r), "U000021", 1)

    def test_nur_jahresformulare_und_gemappte_einheit(self):
        z = self.zeilen(roh(eintrag(), eintrag(form="10-Q", accn="a2", fp="Q1"), eintrag(form="8-K", accn="a3")))
        self.assertEqual(len(z), 1)
        self.assertEqual(self.zeilen(roh(eintrag(), unit="shares")), [])        # fremde Einheit wird nicht gemappt

    def test_stichtag_ohne_beginn_dauerwert_wird_nicht_gemappt(self):
        self.assertEqual(self.zeilen(roh(eintrag(start="2024-01-01"))), [])

    def test_restated_filings_bleiben_getrennte_fassungen(self):
        z = self.zeilen(roh(eintrag(val=1682512000, accn="A"), eintrag(val=1677440000, accn="B", form="10-K/A", filed="2025-05-20")))
        self.assertEqual(sorted(x["value"] for x in z), [D(1677440000), D(1682512000)])
        self.assertEqual(len({x["source_fact_key"] for x in z}), 2)

    def test_doppelte_in_selber_einreichung_einmal_widerspruch_fehler(self):
        self.assertEqual(len(self.zeilen(roh(eintrag(), eintrag(frame="CY2024Q4I")))), 1)
        with self.assertRaisesRegex(ValueError, "Widerspruch"):
            self.zeilen(roh(eintrag(val=1), eintrag(val=2)))

    def test_tagrangfolge_kein_mix_je_filing(self):
        def tag(name, val, **kw):
            e = {"end": "2024-12-31", "start": "2024-01-01", "val": val, "accn": "A", "form": "10-K", "filed": "2025-02-01", **kw}
            return {"units": {"USD": [e]}}
        r = {"cik": 1, "facts": {"us-gaap": {"Revenues": tag("Revenues", 120),
                                                "RevenueFromContractWithCustomerExcludingAssessedTax": tag("x", 100)}}}
        z = sec.normalisieren(sec.extrahieren(r), "U1", 1)
        self.assertEqual([(x["metric_code"], x["value"]) for x in z], [("revenue", D(100))])
        # anderes Filing ohne den bevorzugten Tag: dort gilt der nächste Rang
        r["facts"]["us-gaap"]["Revenues"]["units"]["USD"].append({"end": "2023-12-31", "start": "2023-01-01", "val": 90, "accn": "B", "form": "10-K", "filed": "2024-02-01"})
        self.assertEqual(sorted(x["value"] for x in sec.normalisieren(sec.extrahieren(r), "U1", 1)), [D(90), D(100)])

    def test_banken_ohne_umsatz(self):
        r = roh(eintrag())
        r["facts"]["us-gaap"]["Revenues"] = {"units": {"USD": [eintrag(start="2024-01-01")]}}
        self.assertEqual({e["metric"] for e in sec.extrahieren(r)}, {"assets", "revenue"})
        self.assertEqual({e["metric"] for e in sec.extrahieren(r, metrics=set(sec.MAPPING) - sec.OHNE_BANK)}, {"assets"})

    def test_fixture_adtran(self):
        r = json.loads(FIXTURE.read_text())
        z = self.zeilen(r)
        aktuell = {}
        for x in sorted(z, key=lambda x: (x["reported_at"], x["source_fact_key"])):
            aktuell[x["period_end"]] = x["value"]
        # an der Bilanz der 10-K 2025 (R2.htm) bzw. 10-K/A geprüfte Werte, USD
        self.assertEqual(aktuell[date(2025, 12, 31)], D(1204493000))
        self.assertEqual(aktuell[date(2024, 12, 31)], D(1171419000))
        self.assertEqual(aktuell[date(2023, 12, 31)], D(1677440000))         # berichtigt durch 10-K/A (Original 1.682.512.000)
        self.assertTrue(all(x["unit"] == "USD" and x["period_start"] is None and x["quality"] == "raw" for x in z))


if __name__ == '__main__':
    unittest.main()


class IfrsMelder(unittest.TestCase):
    """20-F/40-F-Melder mit ifrs-full-Tags: Berichtswährung bleibt erhalten, keine Umrechnung."""

    @staticmethod
    def roh():
        def e(val, end, form="20-F", start=None, accn="0000000000-26-000001"):
            d = {"val": val, "end": end, "accn": accn, "form": form, "filed": "2026-03-01", "fy": 2025, "fp": "FY"}
            if start:
                d["start"] = start
            return d
        return {"cik": 1, "facts": {"ifrs-full": {
            "Assets": {"units": {"CHF": [e(900, "2025-12-31")], "USD": [e(1000, "2025-12-31")], "shares": [e(5, "2025-12-31")]}},
            "ProfitLoss": {"units": {"CHF": [e(70, "2025-12-31", start="2025-01-01")]}},
            "Revenue": {"units": {"CHF": [e(500, "2025-12-31", start="2025-01-01", form="6-K")]}}}}}

    def test_waehrungen_getrennt_andere_einheiten_und_formulare_nicht(self):
        z = sec.normalisieren(sec.extrahieren(self.roh()), "U1", 1)
        werte = {(x["metric_code"], x["unit"]): x["value"] for x in z}
        self.assertEqual(werte, {("assets", "CHF"): D(900), ("assets", "USD"): D(1000), ("net_income_incl_nci", "CHF"): D(70)})

    def test_standard_und_mappingversion(self):
        for x in sec.normalisieren(sec.extrahieren(self.roh()), "U1", 1):
            self.assertEqual(x["accounting_standard"], "IFRS")
            self.assertEqual(x["mapping_version"], sec.MAPPING_VERSION_IFRS)

    def test_us_gaap_vor_ifrs(self):
        roh = self.roh()
        roh["facts"]["us-gaap"] = {"Assets": {"units": {"USD": [{"val": 1000, "end": "2025-12-31", "accn": "0000000000-26-000001", "form": "20-F", "filed": "2026-03-01"}]}}}
        z = [x for x in sec.normalisieren(sec.extrahieren(roh), "U1", 1) if x["metric_code"] == "assets"]
        self.assertEqual({(x["unit"], x["accounting_standard"]) for x in z}, {("USD", "US-GAAP"), ("CHF", "IFRS")})


class FpiPilotliste(unittest.TestCase):
    def test_felder_lei_cik_und_register(self):
        import csv
        import sys
        import esef
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "stammdaten"))
        import ids
        reg = ids.lade(neu=True)
        with open(Path(__file__).resolve().parents[1] / "sec_fpi_pilot.csv", encoding="utf-8", newline="") as f:
            zeilen = list(csv.DictReader(f))
        self.assertEqual(len(zeilen), 40)
        self.assertEqual(len({z["lei"] for z in zeilen}), 40)
        self.assertEqual(len({z["cik"] for z in zeilen}), 40)
        for z in zeilen:
            esef.lei_pruefen(z["lei"])
            self.assertIn(z["land"], {"CH", "CA", "AU", "MX", "CL", "TR", "IL"})
            self.assertIn(z["bank"], {"ja", "nein"})
            treffer = [u for u, r in reg.unternehmen.items() if r["lei"] == z["lei"]]
            self.assertEqual(len(treffer), 1, z["name"])
            if z["bestand_id"]:
                self.assertEqual(treffer[0], z["bestand_id"])
