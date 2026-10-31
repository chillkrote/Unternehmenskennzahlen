import json
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from openpyxl import load_workbook

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER.parent / "stammdaten"))
import erstelle_vorlage  # noqa: E402
import ids  # noqa: E402
import importieren as I  # noqa: E402

URL = "https://example.org/gb.pdf"


def kz(n, gj, bez, wert, einheit="Millionen", waehr="EUR"):
    return [n, gj, date(gj, 12, 31), "IFRS", waehr, einheit, bez, wert, "Konzernabschluss", URL, 10, ""]


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for n in ("unternehmen_ids.csv", "unternehmen_aliase.csv", "isin_zuordnung.csv"):
            shutil.copy(HIER.parent / "stammdaten" / n, self.tmp / n)
        ids.DIR = self.tmp
        ids.UNTERNEHMEN, ids.ALIASE, ids.ISINS = (self.tmp / "unternehmen_ids.csv", self.tmp / "unternehmen_aliase.csv", self.tmp / "isin_zuordnung.csv")
        ids._cache = None
        I.AUSGABE = self.tmp / "daten"
        self.datei = self.tmp / "t.xlsx"
        erstelle_vorlage.baue(self.datei)

    def fuelle(self, unt, kennz):
        wb = load_workbook(self.datei)
        for ws in (wb["Unternehmen"], wb["Kennzahlen"], wb["Quellen-Dokumente"]):
            ws.delete_rows(2, ws.max_row)
        for z in unt:
            wb["Unternehmen"].append(z)
        for z in kennz:
            wb["Kennzahlen"].append(z)
        wb.save(self.datei)

    def lauf(self):
        return I.laden_und_pruefen(self.datei)[0]

    def u(self, name, isin="", lei="", boerse="nein"):
        return [name, "AG", "Germany", "Ort", isin, "", "", boerse, "industrie", "", lei, "", "", "nein", "", "", URL]

    def test_vorlage_beispiele_werden_ignoriert(self):
        b = self.lauf()
        self.assertEqual(b.fehler, [])

    def test_gueltig_und_bilanzprobe(self):
        n = "Testfirma Neu AG"
        self.fuelle([self.u(n)], [kz(n, 2025, "Bilanzsumme", 100), kz(n, 2025, "Eigenkapital", 40), kz(n, 2025, "Verbindlichkeiten gesamt", 60)])
        self.assertEqual(self.lauf().fehler, [])

    def test_bilanzprobe_schlaegt_an(self):
        n = "Testfirma Neu AG"
        self.fuelle([self.u(n)], [kz(n, 2025, "Summe Aktiva", 100), kz(n, 2025, "Summe Passiva", 90),
                                  kz(n, 2025, "Bilanzsumme", 100), kz(n, 2025, "Eigenkapital", 10), kz(n, 2025, "Verbindlichkeiten gesamt", 50)])
        f = " ".join(self.lauf().fehler)
        self.assertIn("Aktiva", f)
        self.assertIn("Eigenkapital + Verbindlichkeiten", f)

    def test_isin_lei_und_dubletten(self):
        n = "Testfirma Neu AG"
        self.fuelle([self.u(n, isin="DE0007164601", boerse="ja")], [])
        f = " ".join(self.lauf().fehler)
        self.assertIn("DE0007164601 hat falsche", f)
        self.fuelle([self.u("Andere Firma AG", isin="DE0007164600")], [])  # SAP-ISIN gültig, aber im Bestand
        b = self.lauf()
        self.assertTrue(any("bereits im Bestand" in i for i in b.info), b.info)

    def test_einheit_und_doppelt(self):
        n = "Testfirma Neu AG"
        self.fuelle([self.u(n)], [kz(n, 2025, "Mitarbeiter", 10, "Milliarden"), kz(n, 2025, "Umsatz", 5), kz(n, 2025, "Umsatz", 6),
                                  kz(n, 2025, "CET1 Quote", 1)])
        f = " ".join(self.lauf().fehler)
        self.assertIn("Anzahl", f)
        self.assertIn("doppelt", f)
        self.assertIn("nicht in der Kennzahlenliste", f)

    def test_schreiben_vergibt_id_und_skaliert(self):
        n = "Testfirma Neu AG"
        self.fuelle([self.u(n)], [kz(n, 2025, "Umsatz", 5.5)])
        b, reg, unt, werte, q = I.laden_und_pruefen(self.datei)
        self.assertEqual(b.fehler, [])
        z = I.schreiben(reg, unt, werte, q, "t.xlsx")
        d = json.loads((I.AUSGABE / f"{z[n]}.json").read_text(encoding="utf-8"))
        self.assertEqual(d["eintraege"][0]["wert"], 5_500_000)
        self.assertEqual(ids.lade(True).aufloesen(n), z[n])

    def test_lei(self):
        self.assertTrue(I.lei_ok("529900T8BM49AURSDO55"))
        self.assertFalse(I.lei_ok("529900T8BM49AURSDO56"))


if __name__ == "__main__":
    unittest.main()
