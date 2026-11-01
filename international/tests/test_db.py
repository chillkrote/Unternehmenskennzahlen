"""Tests gegen eine echte PostgreSQL-Instanz (Wegwerf-Datenbank je Testklasse)."""
import csv
import json
import shutil
import subprocess
import unittest
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import psycopg
import psycopg.errors as pe

import dbhelp
import db
import export_vergleich
import import_de
import ingest
import sec
import esef

FIXTURE = Path(__file__).parent / "fixtures" / "sec_companyfacts_adtn_assets.json"
REPO = Path(__file__).resolve().parents[2]


class MitDb(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = dbhelp.wegwerf_db()
        cls.url = cls.ctx.__enter__()
        cls.conn = db.verbinden(cls.url)
        db.migrieren(cls.conn)
        db.laender_laden(cls.conn)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls.ctx.__exit__(None, None, None)

    def entity(self, eid, name="Test AG", **kw):
        self.conn.execute("INSERT INTO international.entity (id, legal_name, domicile, lei) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                          (eid, name, kw.get("domicile"), kw.get("lei")))

    def quelle(self, sha="a" * 64, ext="t"):
        return ingest.quelle_registrieren(self.conn, "test", ext, "https://example.org/x", sha, "x")

    def fakt(self, **kw):
        f = dict(entity_id="T1", metric_code="assets", period_start=None, period_end=date(2025, 12, 31), value=D(1), unit="EUR",
                 accounting_standard="HGB", consolidation="solo", dimensions={}, source_id=None, source_fact_key="k", mapping_version="t1",
                 quality="raw")
        f.update(kw)
        f["source_id"] = f["source_id"] or self.quelle()
        return ingest.fakt_einfuegen(self.conn, f)


@dbhelp.braucht_db
class Schema(MitDb):
    def test_migrationen_idempotent_und_manipulationssicher(self):
        self.assertEqual(db.migrieren(self.conn), [])
        self.conn.execute("UPDATE public.international_migrations SET sha256=repeat('0',64) WHERE name='001_kernmodell.sql'")
        with self.assertRaisesRegex(RuntimeError, "geändert"):
            db.migrieren(self.conn)
        h = self.conn.execute("SELECT sha256 FROM public.international_migrations WHERE name='002_metriken.sql'").fetchone()[0]
        import hashlib
        self.conn.execute("UPDATE public.international_migrations SET sha256=%s WHERE name='001_kernmodell.sql'",
                          (hashlib.sha256((db.MIGRATIONEN / "001_kernmodell.sql").read_text(encoding="utf-8").encode()).hexdigest(),))

    def test_38_laender(self):
        self.assertEqual(self.conn.execute("SELECT count(*) FROM international.country WHERE oecd_from IS NOT NULL").fetchone()[0], 38)

    def test_fehlender_lei_ist_zulaessig_ungueltiger_nicht(self):
        self.entity("T_LEI0")
        with self.assertRaises(pe.CheckViolation):
            self.entity("T_LEI1", lei="ZU_KURZ")

    def test_namensgleiche_entitaeten_werden_nicht_zusammengefuehrt(self):
        self.entity("T_N1", "Gleicher Name Inc.")
        self.entity("T_N2", "Gleicher Name Inc.")
        self.assertEqual(self.conn.execute("SELECT count(*) FROM international.entity WHERE legal_name='Gleicher Name Inc.'").fetchone()[0], 2)

    def test_mehrfachnotierung_und_gleicher_ticker_in_verschiedenen_laendern(self):
        self.entity("T_L1")
        iid = self.conn.execute("INSERT INTO international.instrument (entity_id, isin, kind) VALUES ('T_L1','US0378331005','security') RETURNING id").fetchone()[0]
        ins = "INSERT INTO international.listing (instrument_id, mic, ticker, currency, valid_from, valid_until) VALUES (%s,%s,%s,%s,%s,%s)"
        self.conn.execute(ins, (iid, "XNAS", "ABC", "USD", date(2020, 1, 1), None))
        self.conn.execute(ins, (iid, "XETR", "ABC", "EUR", date(2020, 1, 1), None))      # gleicher Ticker, andere Börse
        self.conn.execute(ins, (iid, "XLON", "ABC", "GBP", date(2020, 1, 1), None))      # Mehrfachnotierung desselben Instruments
        with self.assertRaises(pe.ExclusionViolation):                                    # Überlappung gleiche Börse + Ticker
            self.conn.execute(ins, (iid, "XNAS", "ABC", "USD", date(2022, 1, 1), None))
        with self.assertRaises(pe.CheckViolation):
            self.conn.execute(ins, (iid, "XPAR", "ABC", "EUR", date(2022, 1, 1), date(2021, 1, 1)))

    def test_tickerwechsel_ohne_ueberlappung_zulaessig(self):
        self.entity("T_L2")
        iid = self.conn.execute("INSERT INTO international.instrument (entity_id, isin, kind) VALUES ('T_L2',NULL,'security') RETURNING id").fetchone()[0]
        ins = "INSERT INTO international.listing (instrument_id, mic, ticker, currency, valid_from, valid_until) VALUES (%s,%s,%s,%s,%s,%s)"
        self.conn.execute(ins, (iid, "XNYS", "OLD", "USD", date(2010, 1, 1), date(2019, 12, 31)))
        self.conn.execute(ins, (iid, "XNYS", "OLD", "USD", date(2020, 1, 1), None))

    def test_fakt_regeln(self):
        self.entity("T1")
        with self.assertRaises(pe.CheckViolation):                                         # Stichtagswert mit Periodenbeginn
            self.fakt(period_start=date(2025, 1, 1), source_fact_key="a")
        with self.assertRaises(pe.CheckViolation):                                         # Zeitraumwert ohne Beginn
            self.fakt(metric_code="net_income", source_fact_key="b")
        with self.assertRaises(pe.CheckViolation):                                         # Geld ohne ISO-Währung
            self.fakt(unit="Mio", source_fact_key="c")
        with self.assertRaises(pe.CheckViolation):                                         # Quote nicht als Dezimalquote deklariert
            self.fakt(metric_code="cet1_ratio", unit="percent", consolidation="regulatory", source_fact_key="d")
        with self.assertRaises(pe.CheckViolation):                                         # CET1 nur mit aufsichtsrechtlichem Kreis
            self.fakt(metric_code="cet1_capital", consolidation="group", source_fact_key="e")
        with self.assertRaises(pe.CheckViolation):                                         # Beginn nach Ende
            self.fakt(metric_code="net_income", period_start=date(2026, 1, 1), source_fact_key="f")
        self.assertTrue(self.fakt(metric_code="net_income", period_start=date(2025, 1, 1), value=D("-12.5"), source_fact_key="g"))  # negativ ok
        self.assertTrue(self.fakt(metric_code="cet1_ratio", unit="ratio", consolidation="regulatory", value=D("0.15"), source_fact_key="h"))

    def test_wiederholter_import_ohne_duplikate(self):
        self.entity("T1")
        self.assertTrue(self.fakt(source_fact_key="idem"))
        self.assertFalse(self.fakt(source_fact_key="idem"))

    def test_restated_und_bekannt_zum(self):
        self.entity("T_R")
        s1, s2 = self.quelle("b" * 64, "orig"), self.quelle("c" * 64, "korr")
        self.fakt(entity_id="T_R", value=D(100), source_id=s1, source_fact_key="r1", reported_at=date(2025, 3, 1))
        self.fakt(entity_id="T_R", value=D(90), source_id=s2, source_fact_key="r1", reported_at=date(2025, 9, 1))
        q = "SELECT value FROM international.fact_as_of(%s) WHERE entity_id='T_R'"
        self.assertEqual([r[0] for r in self.conn.execute(q, (None,))], [D(90)])
        self.assertEqual([r[0] for r in self.conn.execute(q, (date(2025, 6, 1),))], [D(100)])
        self.assertEqual([r[0] for r in self.conn.execute(q, (date(2025, 1, 1),))], [])
        self.assertEqual(self.conn.execute("SELECT count(*) FROM international.fact WHERE entity_id='T_R'").fetchone()[0], 2)  # Original bleibt erhalten

    def test_abbruch_veroeffentlicht_nichts_und_setzt_kein_wasserzeichen(self):
        self.entity("T_A")
        with self.assertRaises(RuntimeError):
            with ingest.ingestion_lauf(self.conn, "test-abbruch") as lauf:
                self.fakt(entity_id="T_A", source_fact_key="x1")
                lauf.wasserzeichen = {"x": 1}
                raise RuntimeError("Abbruch mitten im Lauf")
        self.assertEqual(self.conn.execute("SELECT count(*) FROM international.fact WHERE entity_id='T_A'").fetchone()[0], 0)
        st, wz = self.conn.execute("SELECT status, watermark FROM international.ingestion_run WHERE adapter='test-abbruch'").fetchone()
        self.assertEqual((st, wz), ("failed", None))

    def test_fx_kurs_muss_positiv_sein(self):
        sid = self.quelle("d" * 64, "fx")
        with self.assertRaises(pe.CheckViolation):
            self.conn.execute("INSERT INTO international.fx_rate VALUES ('EUR','USD','2025-12-31',0,%s)", (sid,))


@dbhelp.braucht_db
class DeutscherImport(MitDb):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.zeilen = import_de.lies_csv(import_de.ZEITREIHE)
        cls.stamm = import_de.lies_csv(import_de.STAMM)
        cls.bericht = import_de.importieren(cls.conn)

    def test_alle_ids_unveraendert_uebernommen(self):
        ids = {r[0] for r in self.conn.execute("SELECT id FROM international.entity WHERE id ~ '^U[0-9]{6}$'")}
        self.assertEqual(ids, {z["unternehmen_id"] for z in self.stamm})

    def test_fakten_vollstaendig_und_wiederholbar(self):
        self.assertEqual(self.bericht["fakten_neu"], len(self.zeilen))
        self.assertEqual(self.conn.execute("SELECT count(*) FROM international.fact").fetchone()[0], len(self.zeilen))
        b2 = import_de.importieren(self.conn)
        self.assertEqual((b2["fakten_neu"], b2["fakten_vorhanden"]), (0, len(self.zeilen)))

    def test_dry_run_rollt_zurueck(self):
        with dbhelp.wegwerf_db() as url, db.verbinden(url) as c:
            db.migrieren(c)
            db.laender_laden(c)
            b = import_de.importieren(c, dry_run=True)
            self.assertEqual(b["fakten_neu"], len(self.zeilen))
            for t in ("entity", "fact", "source_document", "ingestion_run"):
                self.assertEqual(c.execute(f"SELECT count(*) FROM international.{t}").fetchone()[0], 0, t)

    def test_isin_und_lei_aus_stammdaten(self):
        erwartet = {i for z in self.stamm for i in [z["isin_haupt"]] + import_de.re.split(r"[;, ]+", z["weitere_isins"] or "") if i}
        n = self.conn.execute("SELECT count(*) FROM international.identifier WHERE scheme='ISIN'").fetchone()[0]
        self.assertEqual(n, len(erwartet))
        self.assertEqual(self.conn.execute("SELECT entity_id FROM international.identifier WHERE scheme='ISIN' AND value='US00486H1059'").fetchone()[0], "U000021")

    def test_regression_vergleichsexport_gleich_bisherige_zeitreihe(self):
        exp = export_vergleich.exportieren(self.conn)
        self.assertEqual(exp["schema_version"], "vergleich-v1")
        idx = {(z["unternehmen_id"], z["kennzahl"], z["stichtag"], z["rechnungslegung"], z["ebene"]): z for z in exp["zeilen"]}
        self.assertEqual(len(idx), len(self.zeilen))
        for r in self.zeilen:
            z = idx[(r["unternehmen_id"], r["kennzahl"], r["stichtag"], r["rechnungslegung"], r["ebene"])]
            self.assertEqual(z["wert"], float(r["wert"]), r)
            self.assertEqual(z["einheit"], r["einheit"])
            self.assertEqual(z["pruefstatus"], r["pruefstatus"])
        self.assertTrue(all(z["vergleichsgruppe"].count("|") == 3 for z in exp["zeilen"]))
        self.assertTrue(all(z["waehrung"] == "EUR" for z in exp["zeilen"] if z["einheit"] == "Mio. EUR"))

    def test_backup_und_restore(self):
        if not shutil.which("pg_dump") or not shutil.which("pg_restore"):
            self.skipTest("pg_dump/pg_restore nicht installiert")
        with dbhelp.wegwerf_db() as ziel_url:
            dump = subprocess.run(["pg_dump", "-Fc", "--dbname", self.url], capture_output=True, check=True).stdout
            subprocess.run(["pg_restore", "--no-owner", "--dbname", ziel_url], input=dump, capture_output=True, check=True)
            with db.verbinden(ziel_url) as c:
                for t in ("entity", "fact", "identifier", "source_document"):
                    a = self.conn.execute(f"SELECT count(*) FROM international.{t}").fetchone()[0]
                    b = c.execute(f"SELECT count(*) FROM international.{t}").fetchone()[0]
                    self.assertEqual(a, b, t)
                self.assertGreater(c.execute("SELECT count(*) FROM international.fact_current").fetchone()[0], 0)


@dbhelp.braucht_db
class SecImport(unittest.TestCase):
    def setUp(self):
        import hashlib
        self.ctx = dbhelp.wegwerf_db()
        self.conn = db.verbinden(self.ctx.__enter__())
        db.migrieren(self.conn)
        db.laender_laden(self.conn)
        self.conn.execute("INSERT INTO international.entity (id, legal_name, domicile) VALUES ('U000021','ADTRAN Holdings, Inc.','US')")
        self.sha = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()

    def tearDown(self):
        self.conn.close()
        self.ctx.__exit__(None, None, None)

    def test_import_idempotent_restated_und_as_of(self):
        neu, alt = sec.importieren(self.conn, FIXTURE, self.sha, "U000021", 926282)
        self.assertGreater(neu, 10)
        self.assertEqual((alt, sec.importieren(self.conn, FIXTURE, self.sha, "U000021", "0000926282")[0]), (0, 0))
        q = "SELECT value FROM international.fact_as_of(%s) WHERE entity_id='U000021' AND metric_code='assets' AND period_end=%s"
        self.assertEqual(self.conn.execute(q, (None, date(2023, 12, 31))).fetchone()[0], D(1677440000))               # berichtigt
        self.assertEqual(self.conn.execute(q, (date(2025, 4, 1), date(2023, 12, 31))).fetchone()[0], D(1682512000))   # bekannt zum 1.4.2025: Original
        self.assertEqual(self.conn.execute(q, (None, date(2025, 12, 31))).fetchone()[0], D(1204493000))
        self.assertEqual(self.conn.execute("SELECT entity_id FROM international.identifier WHERE scheme='CIK' AND value='0000926282'").fetchone()[0], "U000021")
        n = self.conn.execute("SELECT count(*) FROM international.fact WHERE entity_id='U000021' AND period_end='2023-12-31'").fetchone()[0]
        self.assertGreaterEqual(n, 3)                                                                                  # Fassungen bleiben erhalten

    def test_dry_run(self):
        neu, _ = sec.importieren(self.conn, FIXTURE, self.sha, "U000021", 926282, dry_run=True)
        self.assertGreater(neu, 0)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM international.fact").fetchone()[0], 0)

    def test_export_enthaelt_land_standard_waehrung_kreis(self):
        sec.importieren(self.conn, FIXTURE, self.sha, "U000021", 926282)
        z = [x for x in export_vergleich.exportieren(self.conn)["zeilen"] if x["unternehmen_id"] == "U000021" and x["stichtag"] == "2025-12-31"]
        self.assertEqual(len(z), 1)
        self.assertEqual((z[0]["sitzland"], z[0]["standard"], z[0]["waehrung"], z[0]["kreis"], z[0]["wert"]),
                         ("US", "US-GAAP", "USD", "unknown", 1204.493))
        self.assertTrue(z[0]["vergleichsgruppe"].startswith("bilanzsumme|USD|US-GAAP"))


if __name__ == '__main__':
    unittest.main()


@dbhelp.braucht_db
class EsefImport(unittest.TestCase):
    LEI = "549300E9PC51EN656011"
    FIX = Path(__file__).parent / "fixtures" / "esef_sanofi_auszug.json"

    def setUp(self):
        self.ctx = dbhelp.wegwerf_db()
        self.conn = db.verbinden(self.ctx.__enter__())
        db.migrieren(self.conn)
        db.laender_laden(self.conn)
        self.conn.execute("INSERT INTO international.entity (id, legal_name, domicile, lei) VALUES ('U1','Sanofi','FR',%s)", (self.LEI,))

    def tearDown(self):
        self.conn.close()
        self.ctx.__exit__(None, None, None)

    def einr(self, fxo, published):
        return {"attributes": {"fxo_id": fxo, "published": published, "date_added": published, "sha256": "x", "period_end": "2025-12-31"}}

    def laden(self, pfad, fxo, published, **kw):
        import hashlib
        h = hashlib.sha256(Path(pfad).read_bytes()).hexdigest()
        return esef.importieren(self.conn, pfad, h, "https://filings.xbrl.org/x.json", self.einr(fxo, published), "U1", self.LEI, **kw)

    def test_import_idempotent_berichtigung_und_bekannt_zum(self):
        import tempfile
        neu, alt = self.laden(self.FIX, self.LEI + "-2025-12-31-ESEF-FR-0", "2026-02-17 10:00:00")
        self.assertGreater(neu, 15)
        self.assertEqual(self.laden(self.FIX, self.LEI + "-2025-12-31-ESEF-FR-0", "2026-02-17 10:00:00"), (0, neu))
        roh = json.loads(self.FIX.read_text())
        for f in roh["facts"].values():
            if f["dimensions"].get("concept") == "ifrs-full:Assets" and f["dimensions"]["period"] == "2026-01-01T00:00:00":
                f["value"] = "126000000000.0"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "korr.json"
            p.write_text(json.dumps(roh))
            self.laden(p, self.LEI + "-2025-12-31-ESEF-FR-1", "2026-09-01 10:00:00")
        q = "SELECT value FROM international.fact_as_of(%s) WHERE entity_id='U1' AND metric_code='assets' AND period_end='2025-12-31'"
        self.assertEqual(self.conn.execute(q, (None,)).fetchone()[0], D(126000000000))
        self.assertEqual(self.conn.execute(q, (date(2026, 3, 1),)).fetchone()[0], D(126805000000))
        self.assertEqual(self.conn.execute("SELECT count(*) FROM international.source_document").fetchone()[0], 2)

    def test_dry_run_und_export(self):
        neu, _ = self.laden(self.FIX, self.LEI + "-2025-12-31-ESEF-FR-0", "2026-02-17 10:00:00", dry_run=True)
        self.assertGreater(neu, 0)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM international.fact").fetchone()[0], 0)
        self.laden(self.FIX, self.LEI + "-2025-12-31-ESEF-FR-0", "2026-02-17 10:00:00")
        z = [x for x in export_vergleich.exportieren(self.conn)["zeilen"] if x["kennzahl"] == "bilanzsumme" and x["stichtag"] == "2025-12-31"]
        self.assertEqual((z[0]["sitzland"], z[0]["standard"], z[0]["waehrung"], z[0]["kreis"], z[0]["wert"]), ("FR", "IFRS", "EUR", "group", 126805.0))
        self.assertEqual(self.conn.execute("SELECT entity_id FROM international.identifier WHERE scheme='LEI' AND value=%s", (self.LEI,)).fetchone()[0], "U1")
