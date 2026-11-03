import json
import unittest
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import dbhelp  # noqa: F401
import dart
from httpsafe import AbrufFehler, SichererClient

FIXTURE = Path(__file__).parent / "fixtures" / "dart_samsung_2024_auszug.json"
KEY = "0123456789abcdef0123456789abcdef01234567"


def roh():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class Extraktion(unittest.TestCase):
    def test_werte_samsung_2024(self):
        zeilen = dart.normalisieren(dart.extrahieren(roh()), "U001305", 1)
        w = {z["metric_code"]: z for z in zeilen}
        self.assertEqual(w["assets"]["value"], D("514531948000000"))
        self.assertEqual(w["assets"]["period_start"], None)
        self.assertEqual(w["assets"]["period_end"], date(2024, 12, 31))
        self.assertEqual(w["revenue"]["value"], D("300870903000000"))
        self.assertEqual(w["revenue"]["period_start"], date(2024, 1, 1))
        self.assertEqual(w["equity"]["value"], D("391687603000000"))
        self.assertEqual(w["equity_incl_nci"]["value"], D("402192070000000"))
        self.assertEqual(w["net_income"]["value"], D("33621363000000"))
        self.assertEqual(w["net_income_incl_nci"]["value"], D("34451351000000"))      # in GuV, Gesamtergebnisrechnung und Cashflow: gleicher Wert, eine Zeile
        self.assertEqual(w["operating_cash_flow"]["value"], D("72982621000000"))
        self.assertEqual(len(zeilen), 7)
        for z in zeilen:
            self.assertEqual((z["unit"], z["consolidation"], z["accounting_standard"]), ("KRW", "group", "IFRS"))
            self.assertEqual(z["reported_at"], date(2025, 3, 11))
            self.assertEqual(z["provenance"]["rcept_no"], "20250311001085")

    def test_vorjahresspalten_werden_nicht_uebernommen(self):
        a = [z for z in dart.normalisieren(dart.extrahieren(roh()), "U1", 1) if z["metric_code"] == "assets"]
        self.assertEqual([z["period_end"] for z in a], [date(2024, 12, 31)])

    def test_bank_ohne_umsatz(self):
        z = dart.normalisieren(dart.extrahieren(roh(), metrics=set(dart.MAPPING) - dart.OHNE_BANK), "U1", 1)
        self.assertNotIn("revenue", {x["metric_code"] for x in z})

    def test_altes_praefix_ifrs_unterstrich(self):
        r = roh()
        for z in r["list"]:
            z["account_id"] = z["account_id"].replace("ifrs-full_", "ifrs_")
        w = {z["metric_code"]: z for z in dart.normalisieren(dart.extrahieren(r), "U1", 1)}
        self.assertEqual(w["assets"]["value"], D("514531948000000"))
        self.assertEqual(w["assets"]["provenance"]["konto"], "ifrs_Assets")
        self.assertEqual(w["assets"]["provenance"]["konto_vereinheitlicht"], "ifrs-full_Assets")

    def test_widerspruch_und_fremde_waehrung(self):
        r = roh()
        zeile = next(z for z in r["list"] if z["account_id"] == "ifrs-full_ProfitLoss" and z["sj_div"] == "CF")
        zeile["thstrm_amount"] = "1"
        with self.assertRaises(ValueError):
            dart.normalisieren(dart.extrahieren(r), "U1", 1)
        r = roh()
        r["list"][0]["currency"] = "USD"
        with self.assertRaises(ValueError):
            dart.extrahieren(r)

    def test_detailachsen_und_leere_betraege(self):
        r = roh()
        r["list"][0]["account_detail"] = "Segment A"
        r["list"][1]["thstrm_amount"] = "-"
        n = len(dart.extrahieren(r))
        self.assertEqual(n, len(dart.extrahieren(roh())) - 2)


class Schluessel(unittest.TestCase):
    def client(self, antwort, aufgerufen):
        def transport(url, headers, timeout):
            aufgerufen.append((url, headers))
            if isinstance(antwort, Exception):
                raise antwort
            return 200, {}, iter([antwort])
        return dart.DartClient(SichererClient({dart.HOST}, user_agent="Test", transport=transport, schlafen=lambda s: None, kontakt_pflicht=False), key=KEY)

    def test_schluessel_im_aufruf_aber_nie_in_der_adresse_der_quelle(self):
        got = []
        c = self.client(b'{"status":"000"}', got)
        daten, oeffentlich = c.holen("company.json", corp_code="00126380")
        self.assertIn("crtfc_key=" + KEY, got[0][0])
        self.assertNotIn(KEY, oeffentlich)
        self.assertNotIn("crtfc_key", oeffentlich)

    def test_schluessel_fehlt_in_fehlermeldungen(self):
        got = []
        c = self.client(OSError(f"Verbindung getrennt: crtfc_key={KEY}"), got)
        with self.assertRaises(AbrufFehler) as cm:
            c.holen("company.json", corp_code="1")
        self.assertNotIn(KEY, str(cm.exception))
        self.assertIsNone(cm.exception.__cause__)

    def test_umgebungsvariable(self):
        import os
        alt = {k: os.environ.pop(k, None) for k in ("DART_API", "DART_API_KEY")}
        try:
            with self.assertRaises(AbrufFehler):
                dart.schluessel()
            os.environ["DART_API_KEY"] = KEY
            self.assertEqual(dart.schluessel(), KEY)
            os.environ["DART_API"] = "kurz"
            with self.assertRaises(AbrufFehler):
                dart.schluessel()
        finally:
            for k in ("DART_API", "DART_API_KEY"):
                os.environ.pop(k, None)
                if alt[k] is not None:
                    os.environ[k] = alt[k]

    def test_dart_status(self):
        self.assertEqual(dart.json_pruefen(b'{"status":"000"}')["status"], "000")
        with self.assertRaises(AbrufFehler):
            dart.json_pruefen(b'{"status":"020","message":"Limit"}')
        self.assertEqual(dart.json_pruefen(b'{"status":"013"}', erlaubt=("000", "013"))["status"], "013")


class Pruefen(unittest.TestCase):
    def test_bericht_zeile(self):
        import verify_kr
        tr = '<TR><TD>자산총계</TD><TD>514,531,948</TD><TD>455,905,980</TD></TR><TR><TD>부채총계</TD><TD>112,339,878</TD></TR>'
        z = list(verify_kr.zeilen(tr))
        self.assertEqual(verify_kr.pruefen(z, "자산총계", D("514531948000000"))[0], "gleich")
        self.assertEqual(verify_kr.pruefen(z, "자산총계", D("455905980000000"))[0], "gleich")   # Spalten werden nur zeilenweise verglichen
        self.assertEqual(verify_kr.pruefen(z, "자산총계", D("514531949000000"))[0], "nicht_gefunden")
        z2 = list(verify_kr.zeilen('<TR><TD>I. 영업수익 (주35)</TD><TD>12,035,007,218,975</TD></TR>'))
        self.assertEqual(verify_kr.pruefen(z2, "영업수익", D("12035007218975"))[0], "gleich")      # Anhangsverweis, Einheit Won
        self.assertEqual(verify_kr.pruefen(z, "부채총계", D("514531948000000"))[0], "nicht_gefunden")


if __name__ == "__main__":
    unittest.main()
