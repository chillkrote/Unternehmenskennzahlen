import csv
import json
import unittest
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import dbhelp  # noqa: F401
import esef
import verify_fr

FIXTURE = Path(__file__).parent / "fixtures" / "esef_sanofi_auszug.json"
LEI = "549300E9PC51EN656011"
EINR = {"attributes": {"fxo_id": LEI + "-2025-12-31-ESEF-FR-0", "published": "2026-02-17 17:21:23", "date_added": "2026-03-10 14:18:03", "sha256": "x", "period_end": "2025-12-31"}}


def fakt(concept, period, wert, unit="iso4217:EUR", entity="scheme:" + LEI, **extra):
    return {"value": str(wert), "decimals": -6, "dimensions": {"concept": concept, "entity": entity, "period": period, "unit": unit, **extra}}


class Lei(unittest.TestCase):
    def test_pruefziffer(self):
        self.assertEqual(esef.lei_pruefen(LEI), LEI)
        for s in ("", "549300E9PC51EN656012", "KURZ", "549300e9pc51en656011"):
            with self.assertRaises(ValueError, msg=s):
                esef.lei_pruefen(s)


class Perioden(unittest.TestCase):
    def test_oim_stichtag_und_dauer(self):
        self.assertEqual(esef.periode("2026-01-01T00:00:00"), (None, date(2025, 12, 31)))
        self.assertEqual(esef.periode("2025-01-01T00:00:00/2026-01-01T00:00:00"), (date(2025, 1, 1), date(2025, 12, 31)))
        self.assertEqual(esef.periode("2024-09-29T00:00:00/2025-09-28T00:00:00"), (date(2024, 9, 29), date(2025, 9, 27)))   # 52 Wochen


class Normalisierung(unittest.TestCase):
    def zeilen(self, facts, bank=False, einr=EINR):
        roh = {"facts": {f"f{i}": f for i, f in enumerate(facts)}}
        m = set(esef.MAPPING) - (esef.OHNE_BANK if bank else set())
        return esef.normalisieren(esef.extrahieren(roh, LEI, metrics=m), "U1", 1, einr)

    def test_fixture_sanofi_werte(self):
        roh = json.loads(FIXTURE.read_text())
        z = esef.normalisieren(esef.extrahieren(roh, LEI), "U1", 1, EINR)
        w = {(x["metric_code"], x["period_end"]): x["value"] for x in z}
        self.assertEqual(w[("assets", date(2025, 12, 31))], D(126805000000))
        self.assertEqual(w[("assets", date(2024, 12, 31))], D(132798000000))
        self.assertEqual(w[("net_income", date(2025, 12, 31))], D(7813000000))
        self.assertEqual(w[("net_income_incl_nci", date(2025, 12, 31))], D(7851000000))
        self.assertEqual(w[("operating_cash_flow", date(2025, 12, 31))], D(10750000000))
        self.assertTrue(all(x["accounting_standard"] == "IFRS" and x["consolidation"] == "group" and x["unit"] == "EUR" for x in z))
        self.assertTrue(all((x["period_start"] is None) == (x["metric_code"] in ("assets", "equity", "equity_incl_nci")) for x in z))

    def test_dimensionen_fremde_entitaet_und_nichtwaehrung_werden_ignoriert(self):
        a = "ifrs-full:Assets"
        z = self.zeilen([fakt(a, "2026-01-01T00:00:00", 100, **{"ifrs-full:ConsolidatedAndSeparateFinancialStatementsAxis": "ifrs-full:SeparateMember"}),
                         fakt(a, "2026-01-01T00:00:00", 200, entity="scheme:ANDERE"),
                         fakt(a, "2026-01-01T00:00:00", 300, unit="xbrli:shares"),
                         fakt(a, "2026-01-01T00:00:00", 400)])
        self.assertEqual([x["value"] for x in z], [D(400)])

    def test_kein_nan_keine_textfakten(self):
        a = "ifrs-full:Assets"
        self.assertEqual(self.zeilen([fakt(a, "2026-01-01T00:00:00", "NaN"), fakt(a, "2026-01-01T00:00:00", "Frankreich")]), [])

    def test_duplikat_einmal_widerspruch_fehler(self):
        a = "ifrs-full:Assets"
        self.assertEqual(len(self.zeilen([fakt(a, "2026-01-01T00:00:00", 5), fakt(a, "2026-01-01T00:00:00", 5)])), 1)
        f1, f2 = fakt(a, "2026-01-01T00:00:00", 5), fakt(a, "2026-01-01T00:00:00", 8)
        f1["decimals"] = f2["decimals"] = 0
        with self.assertRaisesRegex(ValueError, "Widerspruch"):
            self.zeilen([f1, f2])

    def test_rundungsabweichung_haeufigster_wert_sonst_unbekannt(self):
        a, p = "ifrs-full:Equity", "2026-01-01T00:00:00"

        def f(w):
            x = fakt(a, p, w)
            x["decimals"] = -3
            return x
        z = self.zeilen([f(2403793000), f(2403793000), f(2403792000)])
        self.assertEqual([x["value"] for x in z], [D(2403793000)])
        self.assertEqual(self.zeilen([f(2403793000), f(2403792000)]), [])     # Gleichstand: unbekannt
        with self.assertRaisesRegex(ValueError, "Widerspruch"):
            self.zeilen([f(2403793000), f(2403795000)])                       # über der Rundung

    def test_nur_jahresperioden_und_konzeptrang(self):
        r, rc = "ifrs-full:Revenue", "ifrs-full:RevenueFromContractsWithCustomers"
        z = self.zeilen([fakt(r, "2025-01-01T00:00:00/2026-01-01T00:00:00", 10), fakt(rc, "2025-01-01T00:00:00/2026-01-01T00:00:00", 9),
                         fakt(r, "2025-01-01T00:00:00/2025-04-01T00:00:00", 3), fakt(rc, "2024-01-01T00:00:00/2025-01-01T00:00:00", 8)])
        self.assertEqual(sorted((x["period_end"], x["value"]) for x in z), [(date(2024, 12, 31), D(8)), (date(2025, 12, 31), D(10))])

    def test_banken_ohne_umsatz(self):
        f = fakt("ifrs-full:Revenue", "2025-01-01T00:00:00/2026-01-01T00:00:00", 10)
        self.assertEqual(len(self.zeilen([f])), 1)
        self.assertEqual(self.zeilen([f], bank=True), [])

    def test_veroeffentlichungsdatum_mit_naeherung(self):
        a = fakt("ifrs-full:Assets", "2026-01-01T00:00:00", 1)
        self.assertEqual(self.zeilen([a])[0]["reported_at"], date(2026, 2, 17))
        ohne = {"attributes": {**EINR["attributes"], "published": None}}
        z = self.zeilen([a], einr=ohne)[0]
        self.assertEqual((z["reported_at"], z["provenance"]["reported_at_quelle"]), (date(2026, 3, 10), "date_added (Näherung)"))


class Dokument(unittest.TestCase):
    XHTML = b"""<html xmlns="http://www.w3.org/1999/xhtml" xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" xmlns:xbrli="http://www.xbrl.org/2003/instance"
      xmlns:xbrldi="http://xbrl.org/2006/xbrldi" xmlns:ixt="http://www.xbrl.org/inlineXBRL/transformation/2020-02-12"><body>
      <ix:header><ix:resources>
       <xbrli:context id="c1"><xbrli:entity><xbrli:identifier scheme="s">X</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:instant>2025-12-31</xbrli:instant></xbrli:period></xbrli:context>
       <xbrli:context id="c2"><xbrli:entity><xbrli:identifier scheme="s">X</xbrli:identifier><xbrli:segment><xbrldi:explicitMember dimension="d">m</xbrldi:explicitMember></xbrli:segment></xbrli:entity><xbrli:period><xbrli:instant>2025-12-31</xbrli:instant></xbrli:period></xbrli:context>
       <xbrli:context id="c3"><xbrli:entity><xbrli:identifier scheme="s">X</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:startDate>2025-01-01</xbrli:startDate><xbrli:endDate>2025-12-31</xbrli:endDate></xbrli:period></xbrli:context>
      </ix:resources></ix:header>
      <p><ix:nonFraction name="ifrs-full:Assets" contextRef="c1" scale="6" format="ixt:num-dot-decimal" unitRef="u">126,805</ix:nonFraction>
         <ix:nonFraction name="ifrs-full:Assets" contextRef="c2" scale="6" unitRef="u">1</ix:nonFraction>
         <ix:nonFraction name="ifrs-full:ProfitLoss" contextRef="c3" scale="6" sign="-" format="ixt:num-comma-decimal" unitRef="u">1.234,5</ix:nonFraction></p></body></html>"""

    def test_sichtbare_zahlen_mit_skalierung_vorzeichen_und_ohne_dimensionen(self):
        d = verify_fr.lies_dokument(self.XHTML)
        self.assertEqual(d[("ifrs-full:Assets", None, date(2025, 12, 31))], {D(126805000000)})
        self.assertEqual(d[("ifrs-full:ProfitLoss", date(2025, 1, 1), date(2025, 12, 31))], {D("-1234500000.0")})
        self.assertEqual(len(d), 2)


class Pilotliste(unittest.TestCase):
    LISTEN = {"fr_pilot.csv": ("FR", 2), "nl_pilot.csv": ("NL", 2), "it_pilot.csv": ("IT", 2), "es_pilot.csv": ("ES", 3),
              "be_pilot.csv": ("BE", 1, 10), "at_pilot.csv": ("AT", 2, 10), "fi_pilot.csv": ("FI", 1, 10), "ie_pilot.csv": ("IE", 2, 6),
              "pt_pilot.csv": ("PT", 1, 10), "dk_pilot.csv": ("DK", 1, 10), "se_pilot.csv": ("SE", 3, 10), "no_pilot.csv": ("NO", 2, 10),
              "pl_pilot.csv": ("PL", 3, 10),
              "gb_pilot.csv": ("GB", 4, 16), "gr_pilot.csv": ("GR", 2, 10), "si_pilot.csv": ("SI", 1, 7), "lt_pilot.csv": ("LT", 1, 8),
              "lv_pilot.csv": ("LV", 2, 6), "ee_pilot.csv": ("EE", 3, 8), "is_pilot.csv": ("IS", 2, 9), "lu_pilot.csv": ("LU", 0, 12),
              "hu_pilot.csv": ("HU", 0, 9), "sk_pilot.csv": ("SK", 5, 7), "cz_pilot.csv": ("CZ", 3, 7)}
    OHNE_ISIN = {"FI", "GR", "SI", "LT", "LV", "EE", "IS", "LU", "HU", "SK", "CZ"}

    def test_zehn_unternehmen_je_land_lei_isin_stammdaten(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "stammdaten"))
        import ids
        reg = ids.lade(neu=True)
        alle = set()
        for datei, (land, banken, *anzahl) in self.LISTEN.items():
            anzahl = anzahl[0] if anzahl else 10
            with open(Path(__file__).resolve().parents[1] / datei, encoding="utf-8", newline="") as f:
                zeilen = list(csv.DictReader(f))
            self.assertEqual(len(zeilen), anzahl, datei)
            self.assertEqual(sum(z["bank"] == "ja" for z in zeilen), banken, datei)
            self.assertEqual(len({z["lei"] for z in zeilen}), anzahl, datei)
            for z in zeilen:
                esef.lei_pruefen(z["lei"])
                self.assertEqual(z.get("land") or "FR", land, z["name"])
                if z["isin"]:
                    self.assertTrue(ids.isin_pruefsumme_ok(z["isin"]) and z["isin"].startswith(land), z["isin"])
                else:    # GLEIF führt dort keine inländische ISIN (oder sie ist über den Bestand belegt), siehe LUECKEN.md
                    self.assertIn(land, self.OHNE_ISIN, z["name"])
                if z["isin"]:
                    uid = reg.aufloesen(z["isin"])
                elif z["bestand_id"]:
                    uid = z["bestand_id"]
                else:
                    treffer = [u for u, r in reg.unternehmen.items() if r["lei"] == z["lei"]]
                    self.assertEqual(len(treffer), 1, z["name"])
                    uid = treffer[0]
                self.assertIsNotNone(uid, f"{z['name']} nicht in stammdaten registriert")
                self.assertEqual(reg.unternehmen[uid]["lei"], z["lei"])
                if z.get("bestand_id"):
                    self.assertEqual(uid, z["bestand_id"], z["name"])
                self.assertNotIn(uid, alle, f"{z['name']}: ID doppelt")
                alle.add(uid)
        self.assertEqual(len(alle), 225)


if __name__ == '__main__':
    unittest.main()
