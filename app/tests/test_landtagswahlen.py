"""Landtagswahlen aus amtlichen Dateien (app/landtagswahlen.py): Prüfregeln, Sollwerte des Endergebnisses, Stand im Wahlregister.

Aufruf: python3 -m unittest app/tests/test_landtagswahlen.py
"""
import copy
import json
import sys
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
import landtagswahlen as L  # noqa: E402


def _seite(*tabellen):
    return "".join('<script type="application/json" data-for="w%d" nonce="x">%s</script>' % (i, json.dumps({"x": {"tag": {"attribs": {"data": t}}}}))
                   for i, t in enumerate(tabellen))


class SachsenAnhalt2026(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.zeilen = L._st_zeilen(L.QUELLEN / "st_ltw26_land_kreise_wahlkreise.csv")
        cls.sitze = L._st_sitze()
        cls.geo = json.loads(L.ST_GEO.read_text(encoding="utf-8"))
        cls.w = L.st_ltw26()

    def test_amtliche_dateien_sind_in_sich_stimmig(self):
        self.assertEqual(L.st_pruefe(self.zeilen, self.sitze, self.geo), [])

    def test_sollwerte_des_endgueltigen_ergebnisses(self):
        g = self.w["g"]
        self.assertEqual((g["wb"], g["w"], g["bet"], g["bet_vor"]), (1706852, 1327991, 77.8, 60.3))
        z = {p: (n, x, v) for p, n, x, v in g["s"]["z"]}
        self.assertEqual(z["AfD"], (575971, 43.8, 20.8))
        self.assertEqual(z["CDU"], (226605, 17.2, 37.1))
        self.assertEqual(z["BSW"], (69355, 5.3, None))            # 2021 nicht angetreten: keine Veränderung, nicht 0
        self.assertEqual({p: n for p, n, _ in g["sitze"]}, {"CDU": 15, "AfD": 39, "Die Linke": 8, "SPD": 8, "GRÜNE": 8, "BSW": 5})
        self.assertEqual(g["sitze_n"], 83)
        self.assertEqual(dict(g["sitze_direkt"]), {"AfD": 38, "Die Linke": 3})
        self.assertEqual(self.w["status"], "endgültig")

    def test_wahlkreise_und_kreise(self):
        e = {u["id"]: u for u in self.w["einheiten"]}
        self.assertEqual((len(e["lwk"]["werte"]), len(e["kreis"]["werte"])), (41, 14))
        wk = e["lwk"]["werte"]["11"]
        self.assertEqual(wk["n"], "11 Magdeburg II")
        self.assertEqual(wk["direkt"], {"name": "Mustafa Groener", "partei": "Die Linke"})
        self.assertEqual(wk["s"]["e"][0][:3], ["Die Linke", 11430, 29.4])
        self.assertEqual(wk["s"]["z"][0], ["AfD", 9177, 23.6, 11.0])    # Veränderung aus der amtlichen Gewinn-und-Verlust-Tabelle
        self.assertEqual(sum(x["w"] for x in e["lwk"]["werte"].values()), self.w["g"]["w"])
        self.assertEqual(set(e["kreis"]["werte"]), {f["properties"]["id"] for f in json.loads((APP / "geo/kreise_de.geojson").read_text())["features"]
                                                    if f["properties"]["id"].startswith("15")})
        self.assertEqual({f["properties"]["id"] for f in self.geo["features"]}, set(e["lwk"]["werte"]))

    def test_grenzen_geschlossen_und_im_land(self):
        for f in self.geo["features"]:
            ringe = f["geometry"]["coordinates"] if f["geometry"]["type"] == "Polygon" else [r for p in f["geometry"]["coordinates"] for r in p]
            for r in ringe:
                self.assertEqual(r[0], r[-1])
                self.assertTrue(all(10.5 < x < 13.3 and 50.9 < y < 53.1 for x, y in r), f["properties"])

    def test_pruefung_findet_widersprueche(self):
        z = copy.deepcopy(self.zeilen)
        z[("WKR", "001", "")]["F02.AfD"] += 1
        f = L.st_pruefe(z, self.sitze)
        self.assertTrue(any("Summe F02.AfD" in x for x in f) and any("WKR 001: Summe der Parteien F" in x for x in f), f)
        z = copy.deepcopy(self.zeilen)
        z[("WKR", "011", "")]["Gewählt.im.Wahlkreis"] = "Muster, Max (CDU)"
        f = L.st_pruefe(z, self.sitze)
        self.assertTrue(any("WKR 011: gewählt CDU, meiste Erststimmen Die Linke" in x for x in f) and any("Sitze Die Linke" in x for x in f), f)
        s = copy.deepcopy(self.sitze)
        s[0]["Sitze.insgesamt"] += 1
        self.assertTrue(any("Sitze" in x for x in L.st_pruefe(self.zeilen, s)))
        g = {"features": self.geo["features"][:-1]}
        self.assertTrue(any("Grenzen" in x for x in L.st_pruefe(self.zeilen, self.sitze, g)))

    def test_vorlaeufige_datei_wird_abgelehnt(self):
        import tempfile
        roh = (L.QUELLEN / "st_ltw26_land_kreise_wahlkreise.csv").read_text(encoding="utf-8-sig").replace('"E";', '"V";', 1)
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "x.csv"
            p.write_text(roh, encoding="utf-8")
            with self.assertRaises(L.Pruefehler):
                L._st_zeilen(p)

    def test_vergleich_und_flaechen_aus_den_ergebnisseiten(self):
        land = _seite({"merkmal": ["Wahl&shy;be&shy;rech&shy;tig&shy;te<sup>1</sup>", "Wähler/innen, Wahl&shy;be&shy;tei&shy;li&shy;gung", "CDU", "BSW"],
                       "prozent.vj.x": ["NA", 60.3, 37.12, "NA"], "prozent.vj.y": ["NA", 60.3, 34.13, "NA"]})
        sitze = _seite({"partei_kurzname": ["CDU", "Insgesamt"], "anzahl_sitze_vj": [40, 97]})
        gv = _seite({"wkr": ["001", "001"], "partei_kurzname": ["CDU", "BSW"], "partei_stimmen.y": [7675, "NA"], "zst_insgesamt.y": [21191, 21191]})
        v = L.st_vergleich(land, sitze, gv)
        self.assertEqual(v["land"], {"bet": 60.3, "z": {"CDU": 37.12}, "e": {"CDU": 34.13}})
        self.assertEqual((v["sitze"], v["sitze_n"]), ({"CDU": 40}, 97))
        self.assertEqual(v["wahlkreise"], {"1": {"gueltig": 21191, "z": {"CDU": 7675}}})
        karte = '<script type="application/json" data-for="k">%s</script>' % json.dumps({"x": {"calls": [{"method": "addPolygons", "args": [
            [[[{"lng": [11.0, 11.1, 11.1], "lat": [52.0, 52.0, 52.1]}]]], None, "Wahlbeteiligung", {}, None, None, ["<b>07 Haldensleben</b><br>Wahlbeteiligung: 78 %"]]}]}})
        fc = L.st_flaechen(karte)
        self.assertEqual(fc["features"][0]["properties"], {"id": "7", "name": "Haldensleben"})
        self.assertEqual(fc["features"][0]["geometry"]["coordinates"][0], [[11.0, 52.0], [11.1, 52.0], [11.1, 52.1], [11.0, 52.0]])

    def test_register_waehlt_die_amtliche_wahl_unabhaengig_vom_wahlartikel(self):
        for datum in ("2026-09-06", "2021-06-06", None):
            self.assertEqual(L.wahl("DE-ST", datum)[0], "2026-09-06")
        self.assertIsNone(L.wahl("DE-XX", "2026-01-01"))

    def test_wahlregister_enthaelt_den_amtlichen_stand(self):
        w = next(x for x in json.loads((APP / "data/wahlen.json").read_text(encoding="utf-8"))["wahlen"] if x["gebiet"] == "DE-ST" and x["e"] == 2)
        self.assertEqual((w["id"], w["datum"], w["status"]), ("DE-ST-parl-2026", "2026-09-06", "endgültig"))
        self.assertEqual(w["g"]["s"]["z"][0], ["AfD", 575971, 43.8, 20.8])
        self.assertEqual([(u["id"], u["geo"], len(u["werte"])) for u in w["einheiten"]], [("kreis", "kreise-de", 14), ("lwk", "landtagswahlkreise-st", 41)])
        self.assertIn("Statistisches Landesamt Sachsen-Anhalt", w["quelle"]["name"])


class Abdeckung(unittest.TestCase):
    def test_uebersicht_passt_zum_wahlregister(self):
        import wahlabdeckung
        self.assertEqual(wahlabdeckung.main(["--pruefen"]), 0)
        z = {x["id"]: x for x in wahlabdeckung.tabelle()}
        st = z["DE-ST-parl-2026"]
        self.assertEqual((st["stufe"], st["stimmen_absolut"], st["vergleich_vorwahl"], st["sitze"], st["luecken"]), ("A", "ja", "ja", "ja", ""))
        self.assertIn("Landtagswahlkreise (41)", st["einheiten_mit_grenzen"])
        self.assertEqual(z["DE-BW-parl-2026"]["stufe"], "C")
        self.assertIn("keine amtliche Quelle", z["DE-BW-parl-2026"]["luecken"])

    def test_stufen(self):
        import wahlabdeckung
        w = {"e": 1, "g": {"sitze": [["A", 1, None]]}, "quelle": {"name": "IPU Parline"}}
        self.assertEqual(wahlabdeckung.stufe(w), "D")
        w = {"e": 1, "g": {"s": {"s": [["A", None, 50.0, None]]}}, "quelle": {"name": "Wikipedia (Wahlartikel)"}}
        self.assertEqual(wahlabdeckung.stufe(w), "C")
        w = {"e": 1, "g": {"s": {"s": [["A", 10, 50.0, None]]}}, "quelle": {"name": "Wahlbehörde"}, "einheiten": []}
        self.assertEqual(wahlabdeckung.stufe(w), "B")
        w["einheiten"] = [{"geo": "wahlkreise-x", "name": "Wahlkreise", "werte": {"1": {}}}]
        self.assertEqual(wahlabdeckung.stufe(w), "A")


if __name__ == "__main__":
    unittest.main()
