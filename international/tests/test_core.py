import unittest
from datetime import date, timedelta
from decimal import Decimal as D

import dbhelp  # noqa: F401  (setzt sys.path)
from international_core import (Fact, convert, durchschnittskurs, haupt_waehrung, percent_to_ratio, periode_klasse, ratio,
                                scale_value, stichtagskurs, vergleichbar)


class Kernregeln(unittest.TestCase):
    def test_skalierung_tausend_million(self):
        self.assertEqual(scale_value('1204493', 3), D('1204493000'))
        self.assertEqual(scale_value('1.25', 6), D('1250000'))

    def test_nan_und_unendlich_abgelehnt(self):
        for roh in ('NaN', 'Infinity', '-Infinity'):
            with self.assertRaises(ValueError):
                scale_value(roh, 0)
        with self.assertRaises(ValueError):
            Fact('U1', 'assets', D('NaN'), 'EUR', date(2025, 12, 31))

    def test_negative_werte_bleiben_erhalten(self):
        self.assertEqual(Fact('U1', 'net_income', D('-5'), 'EUR', date(2025, 12, 31), date(2025, 1, 1)).value, D('-5'))

    def test_fehlende_werte_sind_none_nicht_null(self):
        self.assertIsNone(ratio(None, D('100')))
        self.assertIsNone(ratio(D('1'), D('0')))
        self.assertEqual(ratio(D('15'), D('100')), D('0.15'))

    def test_prozent_als_dezimalquote(self):
        self.assertEqual(percent_to_ratio(D('15')), D('0.15'))

    def test_pence_wird_pfund(self):
        self.assertEqual(haupt_waehrung(D('1250'), 'GBX'), (D('12.50'), 'GBP'))
        self.assertEqual(haupt_waehrung(D('12.5'), 'GBP'), (D('12.5'), 'GBP'))

    def test_ungueltige_periode(self):
        with self.assertRaises(ValueError):
            Fact('U1', 'revenue', D('1'), 'EUR', date(2025, 1, 1), date(2025, 12, 31))

    def test_periodenklassen_53_wochen(self):
        self.assertEqual(periode_klasse(None, date(2025, 12, 31)), 'instant')
        self.assertEqual(periode_klasse(date(2025, 1, 1), date(2025, 12, 31)), 'annual')
        self.assertEqual(periode_klasse(date(2024, 1, 1), date(2024, 12, 31)), 'annual')            # Schaltjahr
        self.assertEqual(periode_klasse(date(2025, 9, 28), date(2025, 9, 28) + timedelta(weeks=52) - timedelta(days=1)), 'annual')
        self.assertEqual(periode_klasse(date(2026, 9, 27), date(2026, 9, 27) + timedelta(weeks=53) - timedelta(days=1)), 'annual')
        self.assertEqual(periode_klasse(date(2025, 1, 1), date(2025, 3, 31)), 'quarterly')
        self.assertEqual(periode_klasse(date(2025, 1, 1), date(2025, 6, 30)), 'half_year')
        self.assertEqual(periode_klasse(date(2025, 1, 1), date(2025, 10, 31)), 'other')

    def test_vergleichbarkeit_einzel_konzern(self):
        a = dict(accounting_standard='HGB', consolidation='solo', period_start=None, period_end=date(2025, 12, 31))
        self.assertTrue(vergleichbar(a, dict(a)))
        self.assertFalse(vergleichbar(a, dict(a, consolidation='group')))
        self.assertFalse(vergleichbar(a, dict(a, accounting_standard='IFRS')))
        self.assertFalse(vergleichbar(a, dict(a, period_end=date(2024, 12, 31))))

    def test_umrechnung(self):
        self.assertEqual(convert(D('100'), D('0.8')), D('80'))
        for rate in (D('0'), D('-1'), D('NaN')):
            with self.assertRaises(ValueError):
                convert(D('1'), rate)


class Wechselkurse(unittest.TestCase):
    kurse = {date(2025, 12, 23): D('1.17'), date(2025, 12, 24): D('1.18'), date(2025, 12, 29): D('1.19')}

    def test_feiertag_nimmt_vorangegangenen_kurs(self):
        k, tag, alter = stichtagskurs(self.kurse, date(2025, 12, 25))
        self.assertEqual((k, tag, alter), (D('1.18'), date(2025, 12, 24), 1))

    def test_keine_kurse_aus_der_zukunft(self):
        self.assertIsNone(stichtagskurs({date(2026, 1, 2): D('1.2')}, date(2025, 12, 31)))
        k, tag, _ = stichtagskurs(self.kurse, date(2025, 12, 28))
        self.assertEqual(tag, date(2025, 12, 24))        # der Kurs vom 29.12. liegt nach dem Stichtag

    def test_alter_ist_begrenzt(self):
        self.assertIsNone(stichtagskurs(self.kurse, date(2026, 1, 20), max_alter_tage=5))

    def test_durchschnitt_braucht_genug_kurse(self):
        kurse = {date(2025, 1, 1) + timedelta(days=i): D(i % 3 + 1) for i in range(200)}
        k, n = durchschnittskurs(kurse, date(2025, 1, 1), date(2025, 12, 31), min_tage=150)
        self.assertEqual(n, 200)
        self.assertIsNone(durchschnittskurs(kurse, date(2025, 1, 1), date(2025, 3, 31), min_tage=150))


if __name__ == '__main__':
    unittest.main()
