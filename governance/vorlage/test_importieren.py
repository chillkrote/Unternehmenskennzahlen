"""Tests: python3 -m unittest discover -s governance/vorlage   (aus dem Repo-Root)"""
import tempfile
import unittest
from datetime import date
from pathlib import Path

from openpyxl import load_workbook

import importieren as I
import erstelle_vorlage as E
import schema as S

UID = "U000017"   # adidas, existiert in stammdaten; GJ 2019 ist im Bestand nicht vorhanden
Q = "https://www.beispiel.example/bericht.pdf"


def zeile(ws, werte):
    """In die erste leere Zeile schreiben (Formelzellen der Kontrollspalte zählen nicht)."""
    r = 2
    while any(c.value not in (None, "") and not str(c.value).startswith("=") for c in ws[r]):
        r += 1
    for c, v in enumerate(werte, 1):
        if v is not None:
            ws.cell(r, c, v)


def beispiele_leeren(wb):
    for n in S.BLAETTER:
        ws = wb[n]
        for r in range(2, 6):
            if any(isinstance(c.value, str) and c.value.startswith(S.BEISPIEL) for c in ws[r]):
                for c in ws[r]:
                    if not (isinstance(c.value, str) and c.value.startswith("=")):
                        c.value = None


class Basis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.vorlage = Path(cls.tmp.name) / "v.xlsx"
        E.MAXZ, E.MAXF, E.ID_LIMIT = 40, 40, 20   # kleine Vorlage: schnelle Tests
        E.baue(cls.vorlage)
        cls.bestand = I.Bestand()

    def gefuellt(self):
        wb = load_workbook(self.vorlage)
        beispiele_leeren(wb)
        zeile(wb["Gremienmitglieder"], [UID, None, 2019, "Vorstand", "Dr. Test Vorstandsfrau", "Vorsitzende", None, date(2018, 3, 1), None, "Juristin", Q, 12, date(2019, 12, 31), ""])
        zeile(wb["Gremienmitglieder"], [UID, None, 2019, "Vorstand", "Max Testmann", "Finanzen (CFO)", None, None, None, None, Q, 12, None, ""])
        zeile(wb["Gremienmitglieder"], [UID, None, 2019, "Aufsichtsrat", "Anna Arbeitnehmerin", "Mitglied", "Arbeitnehmer (Gewerkschaft)", None, None, None, Q, 40, None, ""])
        zeile(wb["Vergütung"], [UID, None, 2019, "Vorstand", "Dr. Test Vorstandsfrau", 3000, S.VERG_ARTEN[0], Q, 20, None, ""])
        zeile(wb["Vergütung"], [UID, None, 2019, "Vorstand", "Max Testmann", "2.000,5", S.VERG_ARTEN[0], Q, 20, None, ""])
        zeile(wb["Vergütung"], [UID, None, 2019, "Vorstand", "Gesamt (alle Mitglieder)", 5000.5, "Gesamtvergütung", Q, 21, None, ""])
        zeile(wb["Kennzahlen Gremien"], [UID, None, 2019, "vorstand_mitglieder_zahl", 2, None, Q, 12, None, ""])
        zeile(wb["Kennzahlen Gremien"], [UID, None, 2019, "vorstand_frauen_zahl", 1, None, Q, 12, None, ""])
        zeile(wb["Kennzahlen Gremien"], [UID, None, 2019, "mitbestimmung_ar", "MitbestG", None, Q, 40, None, ""])
        zeile(wb["Pay Ratio"], [UID, None, 2019, "A", "Vorstandsvorsitzender", None, 100, None, None, "Deutschland, FTE", Q, 22, None, ""])
        zeile(wb["Pay Ratio"], [UID, None, 2019, "Bericht", "Ausweis laut Bericht", 55.5, None, None, None, "Median Konzern", Q, 23, None, ""])
        zeile(wb["Geschlecht (Belege)"], ["Dr. Test Vorstandsfrau", UID, None, "weiblich", 'Bezeichnung "Vorständin"', Q, 12])
        zeile(wb["Mandate extern"], ["Max Testmann", "a", "Test AG", None, "Köln", "Mitglied des Aufsichtsrats", "seit 2019-01-01", UID, None, 2019, Q, 14, ""])
        zeile(wb["Werdegang"], ["Max Testmann", "CFO, Test GmbH", "Test GmbH", "2015-2018", S.WERDEGANG_ARTEN[2], Q, 14])
        zeile(wb["Quellen-Dokumente"], [UID, None, "Geschäftsbericht", 2019, "Geschäftsbericht 2019", Q, date(2026, 11, 4), None, "de", ""])
        return wb

    def lauf(self, wb):
        p = Path(self.tmp.name) / "t.xlsx"
        wb.save(p)
        daten, fehler = I.lese(p)
        b = I.Bericht()
        b.fehler += fehler
        out = I.pruefe(daten, self.bestand, b)
        return b, out


class Tests(Basis):
    def test_gueltige_datei(self):
        b, out = self.lauf(self.gefuellt())
        self.assertEqual(b.fehler, [], b.fehler)
        self.assertEqual(len(out["mitglieder"]), 3)
        self.assertEqual(out["verguetung"][1]["betrag_tsd_eur"], "2000.5")
        self.assertEqual(out["mitglieder"][0]["seit"], "2018-03-01")
        self.assertEqual(out["mitglieder"][0]["person_id"], "test-vorstandsfrau")
        felder = {k["feld"] for k in out["kennzahlen"]}
        self.assertTrue({"pay_ratio", "durchschnittsverguetung_beschaeftigte_teur", "mitbestimmung_ar"} <= felder)
        self.assertEqual(len(out["pay_ratio_eingang"]), 2)
        self.assertEqual(len(out["geschlecht"]), 1)

    def test_beispielzeilen_ignoriert(self):
        b, out = self.lauf(load_workbook(self.vorlage))
        self.assertEqual(b.fehler, [])
        self.assertEqual(sum(len(v) for v in out.values()), 0)

    def fehler(self, wb, teil):
        b, _ = self.lauf(wb)
        self.assertTrue(any(teil in f for f in b.fehler), (teil, b.fehler))

    def test_unbekannte_id(self):
        wb = self.gefuellt(); wb["Gremienmitglieder"]["A2"] = "U999999"
        self.fehler(wb, "stammdaten")

    def test_id_format(self):
        wb = self.gefuellt(); wb["Gremienmitglieder"]["A2"] = "adidas"
        self.fehler(wb, "Format U000123")

    def test_pflichtfeld(self):
        wb = self.gefuellt(); wb["Gremienmitglieder"]["K2"] = None
        self.fehler(wb, "Pflichtfeld 'Quelle'")

    def test_organ(self):
        wb = self.gefuellt(); wb["Gremienmitglieder"]["D2"] = "Rat"
        self.fehler(wb, "Organ")

    def test_quelle_ungueltig(self):
        wb = self.gefuellt(); wb["Gremienmitglieder"]["K2"] = "irgendwo"
        self.fehler(wb, "weder https-Link")

    def test_seite(self):
        wb = self.gefuellt(); wb["Gremienmitglieder"]["L2"] = "S. zwölf"
        self.fehler(wb, "Seite")

    def test_seit_nach_bis(self):
        wb = self.gefuellt(); wb["Gremienmitglieder"]["H2"] = date(2019, 5, 1); wb["Gremienmitglieder"]["I2"] = date(2019, 1, 1)
        self.fehler(wb, "liegt nach")

    def test_dublette_in_datei(self):
        wb = self.gefuellt(); zeile(wb["Gremienmitglieder"], [UID, None, 2019, "Vorstand", "Max Testmann", "x", None, None, None, None, Q, 12, None, ""])
        self.fehler(wb, "Doppelte Zeile")

    def test_dublette_im_bestand(self):
        wb = self.gefuellt()
        m = self.bestand.mitglieder[0]
        zeile(wb["Gremienmitglieder"], [m["unternehmen_id"], None, int(m["gj"]), m["organ"], m["name"], "", None, None, None, None, Q, 1, None, ""])
        self.fehler(wb, "bereits im Bestand")

    def test_person_unbekannt(self):
        wb = self.gefuellt(); wb["Vergütung"]["E2"] = "Unbekannt Person"
        self.fehler(wb, "unbekannt")

    def test_betrag_text(self):
        wb = self.gefuellt(); wb["Vergütung"]["F2"] = "viel"
        self.fehler(wb, "keine Zahl")

    def test_summe_warnung(self):
        wb = self.gefuellt(); wb["Vergütung"]["F4"] = 9000
        b, _ = self.lauf(wb)
        self.assertTrue(any("Summenzeile" in w for w in b.warnungen))

    def test_frauen_groesser_mitglieder(self):
        wb = self.gefuellt(); wb["Kennzahlen Gremien"]["E3"] = 5
        self.fehler(wb, "größer als")

    def test_mitbestimmung_wert(self):
        wb = self.gefuellt(); wb["Kennzahlen Gremien"]["E4"] = "irgendwas"
        self.fehler(wb, "mitbestimmung_ar")

    def test_feld_unbekannt(self):
        wb = self.gefuellt(); wb["Kennzahlen Gremien"]["D2"] = "foo"
        self.fehler(wb, "Feldliste")

    def test_pay_ratio_a_ohne_wert(self):
        wb = self.gefuellt(); wb["Pay Ratio"]["G2"] = None
        self.fehler(wb, "Variante A braucht")

    def test_pay_ratio_b_einheiten(self):
        wb = self.gefuellt(); zeile(wb["Pay Ratio"], [UID, None, 2019, "B", "", None, None, 5000, 80000, "Konzern Ø", Q, 30, None, ""])
        b, out = self.lauf(wb)
        self.assertEqual(b.fehler, [])
        self.assertTrue({"personalaufwand_konzern_mio_eur", "beschaeftigte_konzern_zahl"} <= {k["feld"] for k in out["kennzahlen"]})

    def test_geschlecht_aus_vorname(self):
        wb = self.gefuellt(); wb["Geschlecht (Belege)"]["E2"] = "ergibt sich aus dem Vornamen"
        self.fehler(wb, "Namen ab")

    def test_spaltenkopf_geaendert(self):
        wb = self.gefuellt(); wb["Vergütung"]["A1"] = "ID"
        self.fehler(wb, "Spaltenköpfe")

    def test_blatt_fehlt(self):
        wb = self.gefuellt(); del wb["Werdegang"]
        self.fehler(wb, "fehlt")

    def test_url_nicht_registriert(self):
        wb = self.gefuellt(); wb["Gremienmitglieder"]["K2"] = "https://anders.example/x.pdf"
        b, _ = self.lauf(wb)
        self.assertTrue(any("nicht im Blatt Quellen" in w for w in b.warnungen))


if __name__ == "__main__":
    unittest.main()
