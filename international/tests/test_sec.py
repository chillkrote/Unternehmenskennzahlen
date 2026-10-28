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
