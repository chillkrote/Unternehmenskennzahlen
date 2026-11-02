"""Tests des Unternehmenstabellen-Imports gegen PostgreSQL (echte Tabelle aus unternehmen-tabelle/, ca. 10 s)."""
import csv
import io
import unittest

import psycopg.errors as pe

import dbhelp
import export_unternehmen
import import_unternehmen as iu
from test_db import MitDb, REPO


@dbhelp.braucht_db
class Unternehmenstabelle(MitDb):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.zeilen = iu.lies_csv(iu.TABELLE, ";")
        cls.bericht = iu.importieren(cls.conn)

    def n(self, sql, *a):
        return self.conn.execute(sql, a).fetchone()[0]

    def test_alle_zeilen_importiert_ids_unveraendert(self):
        self.assertEqual(self.n("SELECT count(*) FROM international.company_register"), len(self.zeilen))
        mit_id = {z["unternehmen_id"] for z in self.zeilen if z["unternehmen_id"]}
        db_ids = {r[0] for r in self.conn.execute("SELECT entity_id FROM international.company_register WHERE entity_id IS NOT NULL")}
        self.assertEqual(db_ids, mit_id)
        # Zeilen ohne ID bekommen keine neue ID und keinen entity-Eintrag
        self.assertEqual(self.n("SELECT count(*) FROM international.entity WHERE id !~ '^U[0-9]{6}$'"), 0)

    def test_wiederholter_import_aendert_nichts(self):
        b2 = iu.importieren(self.conn)
        self.assertEqual(b2["nicht_mehr_in_tabelle"], 0)
        self.assertEqual(self.n("SELECT count(*) FROM international.company_register"), len(self.zeilen))
        self.assertEqual(self.n("SELECT count(*) FROM international.review_flag"), self.bericht["pruefmarken"])

    def test_export_ist_byteweise_die_tabelle(self):
        ziel = REPO / "international" / "export" / "_test_unternehmen.csv"
        ziel.parent.mkdir(exist_ok=True)
        try:
            export_unternehmen.exportieren(self.conn, ziel)
            self.assertEqual(ziel.read_bytes(), iu.TABELLE.read_bytes())
        finally:
            ziel.unlink(missing_ok=True)

    def test_isin_nie_bei_mehreren_unternehmen(self):
        self.assertEqual(self.n("SELECT count(*) FROM (SELECT isin FROM international.company_register WHERE isin IS NOT NULL GROUP BY isin HAVING count(*)>1) x"), 0)
        # ISIN des Registers gehört in instrument demselben Unternehmen wie in der Tabelle
        self.assertEqual(self.n("SELECT count(*) FROM international.company_register r JOIN international.instrument i ON i.isin=r.isin WHERE i.entity_id IS DISTINCT FROM r.entity_id"), 0)

    def test_trigger_weist_fremde_isin_ab(self):
        isin, uid = self.conn.execute("SELECT isin, entity_id FROM international.instrument LIMIT 1").fetchone()
        with self.assertRaises(pe.CheckViolation):
            self.conn.execute("INSERT INTO international.company_register (row_key,row_no,name,country_name,isin,listed,sector,is_bank,source_url) "
                              "VALUES ('T:1',999999,'Fremd','Germany',%s,true,'sonstige',false,'x')", (isin,))

    def test_aliase_und_pruefmarken(self):
        self.assertGreater(self.bericht["aliase"], 2000)
        # Alias "029-group-se" führt zur ID U000001
        self.assertEqual(self.n("SELECT r.entity_id FROM international.company_alias a JOIN international.company_register r USING (row_key) WHERE a.alias='029-group-se'"), "U000001")
        self.assertEqual(self.n("SELECT count(*) FROM international.review_flag WHERE code='automatisch_ergaenzt'"),
                         sum("bitte prüfen" in z["Beschreibung"] for z in self.zeilen))
        self.assertGreater(self.n("SELECT count(*) FROM international.review_flag WHERE decision='getrennt gelassen'"), 0)

    def test_zeile_verschwindet_wird_inaktiv_nicht_geloescht(self):
        gekuerzt = self.zeilen[1:]
        puffer = io.StringIO()
        w = csv.DictWriter(puffer, fieldnames=iu.SPALTEN, delimiter=";", lineterminator="\r\n")
        w.writeheader()
        w.writerows(gekuerzt)
        ziel = REPO / "international" / "export" / "_test_gekuerzt.csv"
        ziel.parent.mkdir(exist_ok=True)
        ziel.write_text(puffer.getvalue(), encoding="utf-8-sig", newline="")
        try:
            b = iu.importieren(self.conn, datei=ziel)
            self.assertEqual(b["nicht_mehr_in_tabelle"], 1)
            self.assertEqual(self.n("SELECT count(*) FROM international.company_register WHERE NOT active"), 1)
            self.assertEqual(self.n("SELECT count(*) FROM international.company_register"), len(self.zeilen))
        finally:
            ziel.unlink(missing_ok=True)
            iu.importieren(self.conn)
        self.assertEqual(self.n("SELECT count(*) FROM international.company_register WHERE NOT active"), 0)

    def test_doppelte_isin_in_tabelle_bricht_vor_dem_schreiben_ab(self):
        a = dict(self.zeilen[0]); b = dict(self.zeilen[1]); a["ISIN"] = b["ISIN"] = "DE0000000001"
        a["unternehmen_id"] = b["unternehmen_id"] = ""
        fehler = iu.pruefen([a, b], {}, {})
        self.assertTrue(any("steht in 2 Zeilen" in f for f in fehler))


class OhneDb(unittest.TestCase):
    def test_zeilenschluessel_stabil_und_eindeutig(self):
        z = iu.lies_csv(iu.TABELLE, ";")
        k = iu.zeilenschluessel(z)
        self.assertEqual(len(set(k)), len(z))
        self.assertEqual(k, iu.zeilenschluessel(z))

    def test_tabelle_hat_erwartete_spalten(self):
        self.assertEqual(list(iu.lies_csv(iu.TABELLE, ";")[0]), iu.SPALTEN)


if __name__ == "__main__":
    unittest.main()
