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


class Ergebnispraesentation(unittest.TestCase):
    """Baden-Württemberg und Berlin 2026: gleiche Ergebnispräsentation, ein Leser (praes_*)."""

    @classmethod
    def setUpClass(cls):
        cls.d = {c: json.loads((L.QUELLEN / f"{L.PRAES[c]['kuerzel']}_praesentation.json").read_text(encoding="utf-8")) for c in ("DE-BW", "DE-BE")}
        cls.geo = {c: json.loads((APP / dict(L.WAHL_GEO)[L.PRAES[c]["geo"]]).read_text(encoding="utf-8")) for c in ("DE-BW", "DE-BE")}
        cls.bw, cls.be = L.bw_ltw26(), L.be_agh26()

    def test_auszuege_sind_in_sich_stimmig(self):
        for c in ("DE-BW", "DE-BE"):
            self.assertEqual(L.praes_pruefe(self.d[c], L.PRAES[c], self.geo[c]), [], c)

    def test_bw_deckt_sich_mit_der_amtlichen_downloaddatei(self):
        self.assertEqual(L.bw_abgleich(self.d["DE-BW"]), [])
        d = copy.deepcopy(self.d["DE-BW"])
        z = next(z for z in d["wahlkreise"]["57"]["zeilen"] if z[0] == "CDU")
        z[5] = "21.049"
        self.assertTrue(any("57 - Singen: F2 CDU Datei 21048, Präsentation 21049" in x for x in L.bw_abgleich(d)), L.bw_abgleich(d)[:3])

    def test_sollwerte_baden_wuerttemberg(self):
        g = self.bw["g"]
        self.assertEqual((g["wb"], g["w"], g["bet"], g["bet_vor"]), (7764858, 5406737, 69.6, 63.8))
        self.assertEqual(g["s"]["z"][:2], [["GRÜNE", 1623208, 30.2, 32.6], ["CDU", 1595929, 29.7, 24.1]])
        self.assertEqual(g["s"]["e"][0], ["CDU", 1837689, 34.3, 24.1])
        self.assertEqual({p: n for p, n, _ in g["sitze"]}, {"GRÜNE": 56, "CDU": 56, "AfD": 35, "SPD": 10})
        self.assertEqual((g["sitze_n"], dict(g["sitze_direkt"])), (157, {"GRÜNE": 13, "CDU": 56, "AfD": 1}))
        self.assertNotIn("Übrige", [p for p, *_ in g["s"]["z"] + g["s"]["e"]])
        wk = self.bw["einheiten"][0]["werte"]
        self.assertEqual(len(wk), 70)
        self.assertEqual((wk["57"]["n"], wk["57"]["direkt"]), ("57 Singen", {"name": "Christoph Stetter", "partei": "CDU"}))
        self.assertEqual((wk["57"]["s"]["e"][0], wk["57"]["s"]["z"][0]), (["CDU", 24259, 36.2, 21.5], ["CDU", 21048, 31.4, 21.6]))
        self.assertEqual(sum(x["w"] for x in wk.values()), g["w"])
        self.assertEqual((self.bw["status"], self.bw["vor"]["datum"]), ("endgültig", "2021-03-14"))

    def test_sollwerte_berlin(self):
        g = self.be["g"]
        self.assertEqual((g["wb"], g["w"], g["bet"], g["bet_vor"]), (2487318, 1846344, 74.2, 62.9))
        self.assertEqual(g["s"]["z"][:2], [["Die Linke", 468391, 25.7, 12.2], ["CDU", 342746, 18.8, 28.3]])
        self.assertEqual({p: n for p, n, _ in g["sitze"]}, {"Die Linke": 45, "CDU": 33, "AfD": 29, "GRÜNE": 25, "SPD": 21})
        self.assertEqual((g["sitze_n"], dict(g["sitze_direkt"])), (153, {"Die Linke": 28, "CDU": 26, "AfD": 13, "GRÜNE": 10, "SPD": 1}))
        wk = self.be["einheiten"][0]["werte"]
        self.assertEqual(len(wk), 78)
        self.assertEqual((wk["0505"]["n"], wk["0505"]["direkt"]), ("Spandau 5", {"name": "Kai Wegner", "partei": "CDU"}))
        self.assertEqual(wk["0505"]["s"]["e"][0], ["CDU", 7583, 31.8, 46.9])
        self.assertEqual(sum(x["wb"] for x in wk.values()), g["wb"])

    def test_grenzen_passen_zu_den_wahlkreisen(self):
        rahmen = {"DE-BW": (7.4, 10.6, 47.4, 49.9), "DE-BE": (13.0, 13.8, 52.3, 52.7)}
        for c, w in (("DE-BW", self.bw), ("DE-BE", self.be)):
            self.assertEqual({f["properties"]["id"] for f in self.geo[c]["features"]}, set(w["einheiten"][0]["werte"]))
            x0, x1, y0, y1 = rahmen[c]
            for f in self.geo[c]["features"]:
                ringe = f["geometry"]["coordinates"] if f["geometry"]["type"] == "Polygon" else [r for p in f["geometry"]["coordinates"] for r in p]
                for r in ringe:
                    self.assertEqual(r[0], r[-1])
                    self.assertTrue(all(x0 < x < x1 and y0 < y < y1 for x, y in r), f["properties"])

    def test_pruefung_findet_widersprueche(self):
        d = copy.deepcopy(self.d["DE-BE"])
        z = next(z for z in d["wahlkreise"]["0505"]["zeilen"] if z[0] == "CDU")
        z[5] = "7.864"
        f = L.praes_pruefe(d, L.PRAES["DE-BE"])
        self.assertTrue(any("0505: Summe der Parteien (z)" in x for x in f) and any("Summe der Wahlkreise Zweitstimmen CDU" in x for x in f), f)
        d = copy.deepcopy(self.d["DE-BE"])
        next(z for z in d["gewaehlt"]["direkt"] if z[0].startswith("0505"))[2] = "SPD"
        self.assertTrue(any("Wahlkreis 0505: gewählt" in x for x in L.praes_pruefe(d, L.PRAES["DE-BE"])))
        d = copy.deepcopy(self.d["DE-BE"])
        d["titel"] = d["titel"].replace("Amtliches Endergebnis", "Vorläufiges Ergebnis")
        for w in d["wahlkreise"].values():
            w["titel"] = w["titel"].replace("Amtliches Endergebnis", "Vorläufiges Ergebnis")
        self.assertTrue(any("kein endgültiges Ergebnis" in x for x in L.praes_pruefe(d, L.PRAES["DE-BE"])))
        del d["wahlkreise"]["0505"]
        self.assertTrue(any("77 statt 78 Wahlkreise" in x for x in L.praes_pruefe(d, L.PRAES["DE-BE"])))
        self.assertTrue(any("Grenzen" in x for x in L.praes_pruefe(self.d["DE-BW"], L.PRAES["DE-BW"], {"features": self.geo["DE-BW"]["features"][:-1]})))

    def test_wahlregister_enthaelt_den_amtlichen_stand(self):
        reg = {x["id"]: x for x in json.loads((APP / "data/wahlen.json").read_text(encoding="utf-8"))["wahlen"]}
        for wid, datum, geo, n, erste in (("DE-BW-parl-2026", "2026-03-08", "landtagswahlkreise-bw", 70, ["GRÜNE", 1623208, 30.2, 32.6]),
                                           ("DE-BE-parl-2026", "2026-09-20", "landtagswahlkreise-be", 78, ["Die Linke", 468391, 25.7, 12.2])):
            w = reg[wid]
            self.assertEqual((w["datum"], w["status"]), (datum, "endgültig"))
            self.assertEqual(w["g"]["s"]["z"][0], erste)
            self.assertEqual([(u["id"], u["geo"], len(u["werte"])) for u in w["einheiten"]], [("lwk", geo, n)])
        self.assertEqual({c for c in L.WAHLEN}, {"DE-ST", "DE-BW", "DE-BE", "DE-RP", "DE-MV"})


class Tabellenwahlen(unittest.TestCase):
    """Rheinland-Pfalz und Mecklenburg-Vorpommern 2026: Tabellen der Landeswahlleitungen, gemeinsame Prüfung (tab_*)."""

    @classmethod
    def setUpClass(cls):
        cls.d = {"DE-RP": L.rp_lesen(), "DE-MV": L.mv_lesen()}
        cls.geo = {c: json.loads((APP / dict(L.WAHL_GEO)[L.TAB[c]["geo"]]).read_text(encoding="utf-8")) for c in cls.d}
        cls.rp, cls.mv = L.rp_ltw26(), L.mv_ltw26()

    def test_tabellen_sind_in_sich_stimmig(self):
        for c, d in self.d.items():
            self.assertEqual(L.tab_pruefe(d, L.TAB[c], self.geo[c]), [], c)

    def test_sollwerte_rheinland_pfalz(self):
        g = self.rp["g"]
        self.assertEqual((g["wb"], g["w"], g["bet"], g["bet_vor"]), (2990064, 2046542, 68.4, 64.3))
        self.assertEqual(g["s"]["z"][:3], [["CDU", 627954, 31.0, 27.7], ["SPD", 525807, 25.9, 35.7], ["AfD", 394756, 19.5, 8.3]])
        self.assertEqual(g["s"]["e"][0], ["CDU", 675037, 33.4, 31.4])
        self.assertEqual(next(x for x in g["s"]["z"] if x[0] == "BSW")[3], None)          # 2021 nicht angetreten
        self.assertEqual({p: n for p, n, _ in g["sitze"]}, {"CDU": 39, "SPD": 32, "AfD": 24, "GRÜNE": 10})
        self.assertEqual((g["sitze_n"], dict(g["sitze_direkt"])), (105, {"CDU": 39, "SPD": 13}))
        wk = self.rp["einheiten"][0]["werte"]
        self.assertEqual((len(wk), self.rp["einheiten"][0]["anzahl"]), (56, 52))       # 52 Wahlkreise und 4 geteilte Städte als ein Gebiet
        self.assertEqual((wk["S07315000"]["n"], wk["S07315000"]["wb"], wk["S07315000"]["teil"], wk["S07315000"]["stadt"]),
                         ("Mainz (Wahlkreise 27, 28 und 29)", 148778, ["27", "28", "29"], True))
        self.assertEqual((wk["27"]["n"], wk["27"]["direkt"], wk["27"]["bet_vor"]), ("27 Mainz I", {"name": "Michael Ebling", "partei": "SPD"}, None))
        self.assertEqual(wk["27"]["s"]["e"][0], ["SPD", 12056, 28.2, None])           # Wahlkreise neu zugeschnitten: kein Vergleich
        self.assertEqual(self.rp["stimmarten"], [["z", "Landesstimmen"], ["e", "Wahlkreisstimmen"]])

    def test_sollwerte_mecklenburg_vorpommern(self):
        g = self.mv["g"]
        self.assertEqual((g["wb"], g["w"], g["bet"], g["bet_vor"]), (1312565, 1024118, 78.0, 70.8))
        self.assertEqual(g["s"]["z"][:2], [["AfD", 388050, 38.2, 16.7], ["SPD", 360396, 35.5, 39.6]])
        self.assertEqual(g["sitze"], [["AfD", 32, 14], ["SPD", 29, 34], ["Die Linke", 5, 9], ["GRÜNE", 5, 5]])
        self.assertEqual((g["sitze_n"], dict(g["sitze_direkt"])), (71, {"AfD": 22, "SPD": 14}))
        wk = self.mv["einheiten"][0]["werte"]
        self.assertEqual((len(wk), self.mv["einheiten"][0]["anzahl"]), (39, 36))       # 36 Wahlkreise und 3 geteilte Städte
        self.assertEqual((wk["S13004000"]["n"], wk["S13004000"]["wb"], wk["S13004000"]["s"]["z"][0]), ("Schwerin (Wahlkreise 8 und 9)", 76444, ["SPD", 22918, 38.7, None]))
        self.assertEqual((wk["8"]["n"], wk["8"]["direkt"], wk["8"]["bet_vor"]), ("8 Schwerin I", {"name": "Manuela Schwesig", "partei": "SPD"}, 75.2))
        self.assertEqual((wk["8"]["s"]["e"][0], wk["8"]["s"]["z"][0]), (["SPD", 21369, 54.4, 46.4], ["SPD", 14862, 37.8, 35.2]))

    def test_grenzen_passen_zu_den_wahlkreisen(self):
        rahmen = {"DE-RP": (6.0, 8.6, 48.9, 51.0), "DE-MV": (10.5, 14.5, 53.0, 54.8)}
        for c, w in (("DE-RP", self.rp), ("DE-MV", self.mv)):
            ids, werte = {f["properties"]["id"] for f in self.geo[c]["features"]}, w["einheiten"][0]["werte"]
            in_staedten = {nr for x in werte.values() if x.get("stadt") for nr in x["teil"]}
            self.assertTrue(ids <= set(werte) and set(werte) - ids <= in_staedten, c)      # Wahlkreise ohne Fläche liegen ganz in einer Stadt
            self.assertIn("BKG", self.geo[c]["quelle"])                                     # E7: keine Shapes der Landeswahlleitungen mehr
            x0, x1, y0, y1 = rahmen[c]
            for f in self.geo[c]["features"]:
                for r in (r for p in f["geometry"]["coordinates"] for r in p):
                    self.assertEqual(r[0], r[-1])
                    self.assertTrue(all(x0 < x < x1 and y0 < y < y1 for x, y in r), f["properties"])

    def test_wahlkreise_aus_gemeinden(self):
        """E7: Zuordnung Gemeinde -> Wahlkreis vollständig; geteilte Städte über offene Stadtteile (Trier, Rostock) oder als ein Gebiet."""
        for kurz, land, n_gem in (("rp", "DE-RP", 2300), ("mv", "DE-MV", 724)):
            gem, teile = L.wk_zuordnung(kurz)
            self.assertEqual(len(gem), n_gem)
            nummern = {nr for _, wks in gem.values() for nr in wks} | {nr for t in teile.values() for nr in t.values()}
            self.assertEqual(nummern, {str(i) for i in range(1, L.TAB[land]["wahlkreise"] + 1)})
            self.assertTrue(set(teile) <= set(L.STADTTEILE) and all(len(gem[a][1]) > 1 for a in teile))
            for a, t in teile.items():
                self.assertEqual(set(t.values()), set(gem[a][1]), a)                      # Stadtteile decken alle Wahlkreise der Stadt
        self.assertEqual(sorted(n for n, _ in L.wk_staedte("rp").values()), ["Kaiserslautern", "Koblenz", "Ludwigshafen am Rhein", "Mainz"])
        self.assertEqual(sorted(n for n, _ in L.wk_staedte("mv").values()), ["Neubrandenburg", "Schwerin", "Stralsund"])

    def test_pruefung_findet_widersprueche(self):
        d = copy.deepcopy(self.d["DE-MV"])
        d["wahlkreise"]["8"]["z"]["p"]["SPD"] += 1
        f = L.tab_pruefe(d, L.TAB["DE-MV"])
        self.assertTrue(any("8: Summe der Parteien (z)" in x for x in f) and any("Summe der Wahlkreise SPD (z)" in x for x in f), f)
        d = copy.deepcopy(self.d["DE-MV"])
        d["direkt"]["8"][1] = "AfD"
        f = L.tab_pruefe(d, L.TAB["DE-MV"])
        self.assertTrue(any("Wahlkreis 8: gewählt" in x for x in f) and any("Sitze AfD: 22 Direktmandate, in den Wahlkreisen gewählt 23" in x for x in f), f)
        d = copy.deepcopy(self.d["DE-RP"])
        d["land"]["wb"] += 1
        del d["wahlkreise"]["52"]
        f = L.tab_pruefe(d, L.TAB["DE-RP"], self.geo["DE-RP"])
        self.assertTrue(any("51 statt 52 Wahlkreise" in x for x in f) and any("Summe der Wahlkreise Wahlberechtigte" in x for x in f) and any("Grenzen" in x for x in f), f)

    def test_vorlaeufige_datei_wird_abgelehnt(self):
        import tempfile
        roh = (L.QUELLEN / "mv_ltw26_wahlkreise.csv").read_text(encoding="utf-8").replace("Endgültiges Ergebnis", "Vorläufiges Ergebnis", 1)
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "x.csv"
            p.write_text(roh, encoding="utf-8")
            with self.assertRaises(L.Pruefehler):
                L._mv_csv(p)

    def test_lesefunktionen_der_quellen(self):
        kopf = [[None] * 8, [None, None, None, None, None, None, "SPD", "Bastian Ruhl"], [None] * 8, [None, None, None, None, "A1", "A", "D1", "D13"]]
        k, d = L.rp_tabelle(kopf + [["1 001 ", "G", "Betzdorf/Kirchen, WK", None, 5, 7, 3, None], ["x", "U", "Bezirk", None, 1, 1, 1, 1]])
        self.assertEqual((k, d), (["Schluessel", "Name", "A", "D:SPD", "D:Bastian Ruhl"], [["1 001", "Betzdorf/Kirchen", 7, 3, ""]]))
        seite = ("<table><tr><th>Wahlkreis</th><th>Name</th><th>Partei</th></tr><tr><td>01</td><td>A B</td><td>CDU</td></tr></table>"
                 "<table><tr><th>Listenplatz</th><th>Name</th><th>Partei</th></tr><tr><td>2</td><td>C D</td><td>SPD</td></tr></table>")
        self.assertEqual(L.rp_gewaehlte(seite), {"direkt": {"1": ["A B", "CDU"]}, "liste": [["C D", "SPD"]]})
        zelle = '<div style="top: %dpx; left: %dpx; width:20px; " class="S7">%s</div>'
        seite = zelle % (289, 130, "SPD") + zelle % (288, 458, "Pegel,&nbsp;Christian") + zelle % (289, 97, "1") + zelle % (288, 421, "39,4") + zelle % (250, 536, "Name, Vorname")
        self.assertEqual(L.mv_gewaehlte(seite), {"1": ["Christian Pegel", "SPD"]})
        b = {"Wahlbeteiligung MV": [["Mecklenburg-Vorpommern", None, 78, 1, 70.768], [1, "Greifswald", 76.8, 1, 72.05]],
             "SPD": [["x"], ["Stimmenanteile der SPD 2026"], ["Mecklenburg-Vorpommern", None, 37.4, 34.4, 3, 35.5, 39.6], [1, "Greifswald", 39.4, 29.9, 9.5, 33.2, 33.5]],
             "Endgültiges Ergebnis": [["Insgesamt", 71, 36, 35, 79], ["Die Linke 1)", 5, "-", 5, 9], ["BSW", "-", "-", "-", "x"]]}
        v = L.mv_vergleich(b)
        self.assertEqual(v["land"], {"bet": 70.77, "e": {"SPD": 34.4}, "z": {"SPD": 39.6}})
        self.assertEqual((v["wahlkreise"]["1"], v["sitze"]), ({"bet": 72.05, "e": {"SPD": 29.9}, "z": {"SPD": 33.5}}, {"Die Linke": 9}))

    def test_wahlregister_enthaelt_den_amtlichen_stand(self):
        reg = {x["id"]: x for x in json.loads((APP / "data/wahlen.json").read_text(encoding="utf-8"))["wahlen"]}
        # n = Wahlkreise und geteilte Städte (als ein Gebiet mit dem Stadtergebnis)
        for wid, datum, geo, n, erste in (("DE-RP-parl-2026", "2026-03-22", "landtagswahlkreise-rp", 56, ["CDU", 627954, 31.0, 27.7]),
                                           ("DE-MV-parl-2026", "2026-09-20", "landtagswahlkreise-mv", 39, ["AfD", 388050, 38.2, 16.7])):
            w = reg[wid]
            self.assertEqual((w["datum"], w["status"]), (datum, "endgültig"))
            self.assertEqual(w["g"]["s"]["z"][0], erste)
            self.assertEqual([(u["id"], u["geo"], len(u["werte"])) for u in w["einheiten"]], [("lwk", geo, n)])


class Abdeckung(unittest.TestCase):
    def test_uebersicht_passt_zum_wahlregister(self):
        import wahlabdeckung
        self.assertEqual(wahlabdeckung.main(["--pruefen"]), 0)
        z = {x["id"]: x for x in wahlabdeckung.tabelle()}
        st = z["DE-ST-parl-2026"]
        self.assertEqual((st["stufe"], st["stimmen_absolut"], st["vergleich_vorwahl"], st["sitze"], st["luecken"]), ("A", "ja", "ja", "ja", ""))
        self.assertIn("Landtagswahlkreise (41)", st["einheiten_mit_grenzen"])
        for wid, einheit in (("DE-BW-parl-2026", "Landtagswahlkreise (70)"), ("DE-BE-parl-2026", "Abgeordnetenhauswahlkreise (78)"),
                             ("DE-RP-parl-2026", "Landtagswahlkreise (52)"), ("DE-MV-parl-2026", "Landtagswahlkreise (36)")):
            self.assertEqual((z[wid]["stufe"], z[wid]["stimmen_absolut"], z[wid]["vergleich_vorwahl"]), ("A", "ja", "ja"))
            self.assertIn(einheit, z[wid]["einheiten_mit_grenzen"])
        self.assertEqual(z["DE-BY-parl-2023"]["stufe"], "C")
        self.assertIn("keine amtliche Quelle", z["DE-BY-parl-2023"]["luecken"])

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
