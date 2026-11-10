"""Unternehmensprofile (P2.3): Referenztest gegen app/data/unternehmen.json und die Rechenregeln der Seite (unternehmen.js)."""
import json
import math
from collections import defaultdict

import psycopg
import pytest

from etl import profile

from plattform.lizenz import YAHOO_WERTE, mit_yahoo

DATEN = json.loads(profile.DATEI.read_text(encoding="utf-8"))
if not mit_yahoo():          # E1: der Import lässt Yahoo-Kennzahlen weg; Sollwerte entsprechend ohne sie
    DATEN["kennzahlen"] = [k for k in DATEN["kennzahlen"] if k["key"] not in YAHOO_WERTE]
    for _f in DATEN["unternehmen"]:
        _f["werte"] = {k: v for k, v in _f["werte"].items() if k not in YAHOO_WERTE}
FIRMEN = DATEN["unternehmen"]
NACH_ID = {f["id"]: f for f in FIRMEN}


# --- Rechenregeln wie im Terminal (terminal.html: quant/median/perzentil, unternehmen.js: viewProfil) ---
def quant(xs, q):
    if not xs:
        return None
    s = sorted(xs)
    i = (len(s) - 1) * q
    lo = math.floor(i)
    return s[lo] + (s[math.ceil(i)] - s[lo]) * (i - lo)


def werte(liste, k):
    return [f["werte"][k] for f in liste if f["werte"].get(k) is not None and math.isfinite(f["werte"][k])]


def erwartet(f, land=None):
    alle = [x for x in FIRMEN if land is None or (x.get("land_code") or "ZZ") == land]
    peers = [x for x in alle if x["branche"] == f["branche"]]
    gp = [x for x in peers if x.get("gruppe") == f["gruppe"]] if f.get("gruppe") else []
    aus = {}
    for k in DATEN["kennzahlen"]:
        v = f["werte"].get(k["key"])
        if v is None:
            continue
        a = werte(peers, k["key"])
        aus[k["key"]] = {"value": v, "sector_n": len(a), "sector_median": quant(a, .5),
                         "group_median": quant(werte(gp, k["key"]), .5) if len(gp) > 2 else None,
                         "percentile": (len([x for x in a if x < v]) / max(1, len(a) - 1)) if len(a) >= 3 else None}
    return aus, len(peers)


def gleich(a, b):
    if a is None or b is None:
        return a is b
    return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-15)


def stichprobe():
    """je Branche das erste und das letzte Unternehmen, dazu Unternehmen mit Gruppe, Abschlüssen, Gremien und Termine"""
    ids, je = [], defaultdict(list)
    for f in FIRMEN:
        je[f["branche"]].append(f["id"])
    for l in je.values():
        ids += [l[0], l[-1]]
    for bed in (lambda f: f.get("gruppe"), lambda f: f.get("abschluesse"), lambda f: f.get("gov"), lambda f: f.get("termine")):
        ids += [f["id"] for f in FIRMEN if bed(f)][:3]
    return sorted(set(ids))


def test_alle_profile_und_werte_unveraendert(geladene_db):
    with psycopg.connect(geladene_db) as c:
        db = {(e, m): v for e, m, v in c.execute("SELECT entity_id, metric_code, value FROM international.company_profile_value")}
        profile_db = {r[0]: r[1:] for r in c.execute("SELECT entity_id, name, sector, peer_group, listed FROM international.company_profile")}
        katalog = [r[0] for r in c.execute("SELECT code FROM international.profile_metric ORDER BY position")]
    soll = {(f["id"], k): v for f in FIRMEN for k, v in f["werte"].items()}
    assert len(db) == len(soll)
    assert all(db[k] == v for k, v in soll.items()), "jeder Wert muss bitgleich aus unternehmen.json übernommen sein"
    assert set(profile_db) == set(NACH_ID)
    for uid, (name, sector, grp, listed) in profile_db.items():
        f = NACH_ID[uid]
        assert (name, sector, grp, listed) == (f["name"], f["branche"], f.get("gruppe"), bool(f.get("notiert")))
    assert katalog == [k["key"] for k in DATEN["kennzahlen"]]


def test_alle_abschlussposten_unveraendert(geladene_db):
    with psycopg.connect(geladene_db) as c:
        kopf = {r[0]: r[1:] for r in c.execute(
            "SELECT id, entity_id, position, fiscal_year, period_end::text, currency FROM international.financial_statement")}
        posten = defaultdict(lambda: {"bilanz": [], "guv": []})
        for sid, teil, label, v in c.execute(
                "SELECT statement_id, part, label, value FROM international.financial_statement_line ORDER BY statement_id, part, position"):
            posten[sid][teil].append((label, v))
    db = {(e, pos): (j, ende, w, posten[sid]) for sid, (e, pos, j, ende, w) in kopf.items()}
    n = 0
    for f in FIRMEN:
        for pos, a in enumerate(f.get("abschluesse") or []):
            j, ende, w, p = db[(f["id"], pos)]
            assert (j, ende, w) == (a["jahr"], a["ende"], a["waehrung"])
            for teil in ("bilanz", "guv"):
                assert p[teil] == list(a[teil].items()), (f["id"], pos, teil)
            n += 1
    assert n == len(db)


@pytest.mark.parametrize("uid", stichprobe())
def test_profil_wie_terminal(client, uid):
    f = NACH_ID[uid]
    r = client.get(f"/api/v1/companies/{uid}/profile")
    assert r.status_code == 200
    d = r.json()["data"]
    soll, n = erwartet(f)
    assert d["sector_n"] == n
    assert [v["metric"] for v in d["values"]] == list(soll), "Reihenfolge wie Kennzahlenkatalog"
    for v in d["values"]:
        s = soll[v["metric"]]
        assert v["value"] == s["value"] and v["sector_n"] == s["sector_n"]
        for k in ("sector_median", "group_median", "percentile"):
            assert gleich(v[k], s[k]), (uid, v["metric"], k, v[k], s[k])
    assert d["series"] == (f.get("reihen") or {})
    assert d["governance"] == f.get("gov")
    assert d["documents"] == (f.get("dokumente") or [])
    assert d["report_dates"] == (f.get("termine") or [])
    assert [(a["fiscal_year"], a["period_end"], list(a["bilanz"].items()), list(a["guv"].items())) for a in d["statements"]] == \
        [(a["jahr"], a["ende"], list(a["bilanz"].items()), list(a["guv"].items())) for a in f.get("abschluesse") or []]
    for k in ("sitz", "isin", "ticker", "segment", "land_code", "indizes", "archiv_url", "abschluss", "mutter"):
        assert d["attributes"].get(k) == f.get(k)


def test_profil_vergleich_nach_land(client):
    f = next(x for x in FIRMEN if x.get("land_code") == "DE" and x["branche"] == "banken")
    d = client.get(f"/api/v1/companies/{f['id']}/profile?country=de").json()["data"]
    soll, n = erwartet(f, "DE")
    assert d["sector_n"] == n
    for v in d["values"]:
        assert gleich(v["sector_median"], soll[v["metric"]]["sector_median"])


def test_profil_fehler(client):
    assert client.get("/api/v1/companies/X1/profile").status_code == 422
    r = client.get("/api/v1/companies/U999999/profile")
    assert r.status_code == 404 and r.json()["error"]["code"] == "kein_profil"


def test_branchenstatistik(client):
    r = client.get("/api/v1/sectors/banken/statistics?group=Sparkassen")
    assert r.status_code == 200
    d = r.json()["data"]
    sk = [f for f in FIRMEN if f["branche"] == "banken" and f.get("gruppe") == "Sparkassen"]
    assert d["companies"] == len(sk)
    for m in d["metrics"]:
        a = werte(sk, m["metric"])
        assert m["n"] == len(a)
        assert gleich(m["median"], quant(a, .5)) and gleich(m["p25"], quant(a, .25)) and gleich(m["p75"], quant(a, .75))
    assert client.get("/api/v1/sectors/gibtsnicht/statistics").status_code == 404


def test_profilkatalog_und_verweis(client):
    kat = client.get("/api/v1/profile-metrics").json()["data"]
    assert [k["code"] for k in kat] == [k["key"] for k in DATEN["kennzahlen"]]
    uid = FIRMEN[0]["id"]
    d = client.get(f"/api/v1/companies/{uid}").json()["data"]
    assert d["links"]["profile"] == f"/api/v1/companies/{uid}/profile"
    assert d["facts"] >= len(FIRMEN[0]["werte"])


def test_keine_yahoo_werte_in_der_datenbank(geladene_db):
    with psycopg.connect(geladene_db) as c:
        n = c.execute("SELECT count(*) FROM international.company_profile_value WHERE metric_code = ANY(%s)", (list(YAHOO_WERTE),)).fetchone()[0]
        k = c.execute("SELECT count(*) FROM international.profile_metric WHERE code = ANY(%s)", (list(YAHOO_WERTE),)).fetchone()[0]
    assert (n, k) == (0, 0)


def test_profilimport_unveraendert_wird_uebersprungen(geladene_db):
    import db as intl_db
    with intl_db.verbinden(geladene_db) as c:
        assert profile.importieren(c)["unveraendert"] == 1
