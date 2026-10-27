"""Tests der zentralen Unternehmens-IDs. Aufruf: python3 -m unittest discover -s stammdaten -v   (auch im Workflow stammdaten.yml)."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ids
import pruefe_ids


class RepoZustand(unittest.TestCase):
    def test_pruefung_ohne_fehler(self):
        fehler, info = pruefe_ids.pruefen()
        self.assertEqual(fehler, [], "\n".join(fehler[:20]))
        self.assertGreater(info["unternehmen"], 700)

    def test_keine_isin_bei_mehreren_ids(self):
        je_isin = {}
        for r in ids._lesen(ids.ISINS):
            je_isin.setdefault(r["isin"], set()).add(r["unternehmen_id"])
        self.assertEqual([i for i, v in je_isin.items() if len(v) > 1], [])

    def test_alte_schreibweisen_zeigen_auf_dieselbe_id(self):
        reg = ids.Register()
        db = {reg.aufloesen(x) for x in ("deutsche-bank-ag", "deutsche-bank-aktiengesellschaft", "Deutsche Bank AG",
                                         "Deutsche Bank Aktiengesellschaft", "DE0005140008")}
        self.assertEqual(len(db), 1)
        self.assertRegex(db.pop(), r"^U\d{6}$")
        self.assertEqual(reg.aufloesen("baader-bank-ag"), reg.aufloesen("baader-bank-aktiengesellschaft"))


class Verstoesse(unittest.TestCase):
    """Die Prüfung muss echte Verstöße melden. Dafür läuft sie gegen eine verfälschte Kopie der Stammdaten."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.orig = (ids.UNTERNEHMEN, ids.ALIASE, ids.ISINS)
        for n in (ids.UNTERNEHMEN, ids.ALIASE, ids.ISINS):
            shutil.copy(n, self.tmp / n.name)
        ids.UNTERNEHMEN, ids.ALIASE, ids.ISINS = (self.tmp / n.name for n in self.orig)

    def tearDown(self):
        ids.UNTERNEHMEN, ids.ALIASE, ids.ISINS = self.orig
        shutil.rmtree(self.tmp)

    def test_isin_bei_zwei_ids_faellt_auf(self):
        zeilen = ids._lesen(ids.ISINS)
        zeilen.append({"isin": zeilen[0]["isin"], "unternehmen_id": "U999999", "art": "weitere"})
        ids._schreiben(ids.ISINS, ids.KOPF_I, zeilen)
        fehler, _ = pruefe_ids.pruefen()
        self.assertTrue(any("bei mehreren IDs" in f for f in fehler), fehler[:3])

    def test_registrieren_verweigert_fremde_isin(self):
        reg = ids.Register()
        erste = next(iter(reg.nach_isin))
        uid_neu = reg.registrieren(name="Testfirma Zeta AG", ordner="testfirma-zeta-ag")
        with self.assertRaises(ValueError):
            reg.isins_zuordnen(uid_neu, erste, [])

    def test_neue_ids_werden_nie_wiederverwendet(self):
        reg = ids.Register()
        hoechste = max(int(u[1:]) for u in reg.unternehmen)
        uid = reg.registrieren(name="Testfirma Omega AG", ordner="testfirma-omega-ag")
        self.assertEqual(uid, f"U{hoechste + 1:06d}")
        self.assertEqual(reg.registrieren(name="Testfirma Omega AG"), uid)  # gleicher Name: keine zweite ID


class IsinFormat(unittest.TestCase):
    def test_pruefziffer(self):
        self.assertTrue(ids.isin_pruefsumme_ok("DE0005140008"))
        self.assertFalse(ids.isin_pruefsumme_ok("DE0005140009"))
        self.assertFalse(ids.isin_pruefsumme_ok("XX"))


if __name__ == "__main__":
    unittest.main()
