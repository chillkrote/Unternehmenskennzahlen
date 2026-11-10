"""Abhängigkeit im Terminal (HDL F5, app/src/handel.js: ABH) rechnet wie der Server (server/plattform/handel.py).

Für jede Gütergruppe aus app/data/gueter.json: HHI, Einstufung, CR3 und Alternativen (ohne das größte Exportland) in Node und Python.
Ohne Node oder ohne gueter.json wird der Test übersprungen.

    python3 -m unittest discover -s app/tests -p 'test_*.py'
"""
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "server"))
from plattform import handel  # noqa: E402

GUETER = REPO / "app/data/gueter.json"
JS = r"""
const fs = require("fs"), vm = require("vm");
const ctx = { Intl, console }; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[1], "utf8") + "\n;this.HDL = HDL;", ctx);
const A = ctx.HDL.ABH, faelle = JSON.parse(fs.readFileSync(0, "utf8"));
console.log(JSON.stringify(faelle.map(([w, ohne]) => ({ hhi: A.hhi(w), stufe: A.einstufung(A.hhi(w)), cr3: A.cr(w), alt: A.alternativen(w, ohne, 5) }))));
"""


def werte(d, gid):
    j = d["jahre"].index(d["jahr"])
    return {iso: e[gid]["v"][j] for iso, e in d["laender"].items() if gid in e and e[gid].get("v") and e[gid]["v"][j] is not None}


@unittest.skipUnless(shutil.which("node") and GUETER.exists(), "Node oder gueter.json fehlt")
class GleicheRegeln(unittest.TestCase):
    def test_alle_gueter(self):
        d = json.loads(GUETER.read_text(encoding="utf-8"))
        faelle = []
        for g in d["gruppen"]:
            w = werte(d, g["id"])
            groesstes = max(w, key=w.get) if w else None
            faelle.append([w, [groesstes] if groesstes else []])
        faelle.append([{"A": 1, "B": 1, "C": 0, "D": None}, ["A"]])     # Nullen und Lücken
        faelle.append([{}, []])
        r = subprocess.run(["node", "-e", JS, str(REPO / "app/src/handel.js")], input=json.dumps(faelle), capture_output=True, text=True, check=True)
        js = json.loads(r.stdout)
        self.assertEqual(len(js), len(faelle))
        for (w, ohne), j in zip(faelle, js):
            self.assertAlmostEqual(j["hhi"], handel.hhi(w), places=1)
            self.assertEqual(j["stufe"], handel.einstufung(handel.hhi(w)))
            self.assertAlmostEqual(j["cr3"], handel.cr(w), places=4)
            py = handel.alternativen(w, ohne, 5)
            self.assertEqual([a["geo"] for a in j["alt"]], [a["geo"] for a in py])
            for a, b in zip(j["alt"], py):
                self.assertAlmostEqual(a["world_share"], b["world_share"], places=4)
                self.assertAlmostEqual(a["share_without_excluded"], b["share_without_excluded"], places=4)


if __name__ == "__main__":
    unittest.main()
