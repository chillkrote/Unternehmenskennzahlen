"""Weltkugel, Politik & Wahlen: Parlamente aller Staaten und der Gliedstaaten bundesstaatlicher Länder -> data/parlamente.json.

Inhalt (alles kostenlos, ohne Schlüssel; Quelle und Stand stehen bei jedem Wert):
 - staaten: je Staat alle nationalen Parlamentskammern (Einkammer, Unterhaus, Oberhaus) mit
     * wahl:    Ergebnis der letzten Wahl in Sitzen je Partei, Regierungsparteien, Wahlbeteiligung, nächste Wahl
                (IPU Parline, CC BY-NC-SA 4.0, https://data.ipu.org)
     * aktuell: heutige Zusammensetzung laut Infobox des Wikipedia-Artikels der Kammer (CC BY-SA 4.0), mit Regierung/Opposition,
                soweit die Infobox das trennt
     * stimmen: Stimmenanteile der größten Parteien laut Infobox des Wikipedia-Artikels der letzten Wahl
 - gliedstaaten: je Bundesstaat (Liste FOEDERAL) jeder Gliedstaat mit Regierungschef und Partei (Wikidata, CC0) und denselben
   Angaben je Kammer aus Wikipedia.
 - juengst: alle Wahlen der letzten SCHWELLE_TAGE Tage (national und Gliedstaaten), mit dem Hinweis, ob das Ergebnis in der Quelle
   schon steht.

Schwelle "gerade gewählt": 30 Tage. Begründung: In den meisten Staaten liegen das amtliche Endergebnis und die konstituierende
Sitzung innerhalb von rund vier Wochen nach der Wahl (Deutschland: Art. 39 GG, spätestens 30. Tag; Vereinigtes Königreich,
Kanada, Indien ähnlich). So lange ist die Zusammensetzung "neu" und die Quellen werden noch nachgetragen. Danach gilt das Ergebnis
als Normalzustand.

    python3 app/parlamente_daten.py            # alles abrufen (erster Lauf rund 30 Minuten, danach Cache der Wahlartikel)
    python3 app/parlamente_daten.py --geo      # zusätzlich die Umrisse der Gliedstaaten (Natural Earth) neu erzeugen
    python3 app/parlamente_daten.py --nur-national
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

HIER = Path(__file__).resolve().parent
ZIEL = HIER / "data/parlamente.json"
GEO = HIER / "geo/gliedstaaten.geojson"
CACHE = HIER / "data/parlamente_wahlcache.json"   # Infoboxen der Wahlartikel (nicht in die Seite eingebettet)
UA = {"User-Agent": "Unternehmenskennzahlen/1.0 (https://github.com/chillkrote/Unternehmenskennzahlen)"}
IPU = "https://api.data.ipu.org/v1/"
SPARQL = "https://query.wikidata.org/sparql"
WIKI_RAW = "https://en.wikipedia.org/w/index.php?title={}&action=raw"
NE_A1 = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_1_states_provinces.geojson"
SCHWELLE_TAGE = 30
# Bundesstaaten (Föderationen) nach der Liste des Forum of Federations; Spanien und Italien sind Regionalstaaten und fehlen bewusst
FOEDERAL = ["AR", "AT", "AU", "BA", "BE", "BR", "CA", "CH", "DE", "ET", "FM", "IN", "IQ", "KM", "MX", "MY", "NG", "NP", "PK",
            "RU", "SD", "SO", "SS", "AE", "US", "VE"]
# Kammern, die Wikidata nicht als Teil des nationalen Parlaments führt (IPU-Kammercode -> Wikipedia-Artikel)
KAMMER_WIKI = {"DE-LC01": "Bundestag", "DE-UC01": "Bundesrat (Germany)", "NL-LC01": "House of Representatives (Netherlands)",
               "NL-UC01": "Senate (Netherlands)", "IE-LC01": "Dáil Éireann", "IE-UC01": "Seanad Éireann",
               "AT-LC01": "National Council (Austria)", "AT-UC01": "Federal Council (Austria)", "CN-LC01": "National People's Congress"}
TYP = {"lower_chamber": "unterhaus", "upper_chamber": "oberhaus", "unicameral": "einkammer"}
FARBEN = ["#8b95a3", "#a07850", "#6f8fa8", "#b07aa1", "#7f9c6b", "#c49a4a", "#5f7f9a", "#9a6f6f", "#6aa39b", "#a39a6a"]

_letzt = [0.0]


def holen(url, roh=False, versuche=5, pause=0.0, daten=None, kopf=None):
    for i in range(versuche):
        warte = pause - (time.time() - _letzt[0])
        if warte > 0:
            time.sleep(warte)
        try:
            req = urllib.request.Request(url, data=daten, headers={**UA, **(kopf or {})})
            with urllib.request.urlopen(req, timeout=180) as r:
                b = r.read()
            _letzt[0] = time.time()
            return b if roh else b.decode("utf-8-sig")
        except urllib.error.HTTPError as e:
            _letzt[0] = time.time()
            if e.code == 404:
                return None
            if i == versuche - 1:
                raise
            print("  Wiederholung", e.code, url[:100], file=sys.stderr)
            time.sleep(15 * (i + 1) if e.code == 429 else 5 * (i + 1))
        except Exception as e:  # noqa: BLE001
            _letzt[0] = time.time()
            if i == versuche - 1:
                raise
            print("  Wiederholung", url[:100], e, file=sys.stderr)
            time.sleep(5 * (i + 1))


def sparql(q):
    t = holen(SPARQL, daten=urllib.parse.urlencode({"query": q}).encode(), kopf={"Accept": "application/sparql-results+json",
                                                                                   "Content-Type": "application/x-www-form-urlencoded"}, pause=1)
    return json.loads(t)["results"]["bindings"]


def w(x, k):
    return x.get(k, {}).get("value", "")


def qid(x, k):
    return w(x, k).rsplit("/", 1)[-1]


def wiki_titel(url):
    return urllib.parse.unquote(url.rsplit("/wiki/", 1)[-1]).replace("_", " ") if url else ""


# ---------- IPU Parline ----------

def ipu_alle(pfad, groesse=500):
    out, seite = [], 1
    while True:
        t = holen(f"{IPU}{pfad}?page%5Bsize%5D={groesse}&page%5Bnumber%5D={seite}", pause=.5)
        d = json.loads(t)
        out += d["data"]
        if len(out) >= d["meta"]["total"] or not d["data"]:
            return out, d["meta"]
        seite += 1


def v(a, k):
    x = a.get(k) or {}
    return x.get("value") if isinstance(x, dict) else None


def tag(s):
    return s[:10] if isinstance(s, str) and re.match(r"\d{4}-\d{2}-\d{2}", s) else None


def zahl(x):
    if isinstance(x, (int, float)):
        return int(x)
    if isinstance(x, str) and re.fullmatch(r"\s*\d+\s*", x):
        return int(x)
    return None


def ipu():
    kammern, meta = ipu_alle("chambers")
    wahlen, _ = ipu_alle("elections")
    parteien = {p["political_party_code"]: (p.get("party_name") or {}).get("en") or p["political_party_code"]
                for p in json.loads(holen(IPU + "political_parties?page%5Bsize%5D=5000"))["data"]}
    heute = date.today().isoformat()
    nach_kammer = {}
    for e in wahlen:
        a = e["attributes"]
        d = v(a, "election_date") or {}
        von, bis = tag(d.get("from")), tag(d.get("to"))
        if von:
            nach_kammer.setdefault(v(a, "chamber"), []).append((von, bis or von, a, e["id"]))
    out = {}
    for k in kammern:
        a, code = k["attributes"], k["id"]
        iso = v(a, "parliament")
        def letzt(k):
            x = a.get(k)
            x = x[-1].get("value") if isinstance(x, list) and x else v(a, k)
            return (x.get("en") or x.get("fr")) if isinstance(x, dict) else x
        name = letzt("chamber_name") or code
        typ = TYP.get((v(a, "struct_parl_status") or {}).get("term"), "einkammer")
        sitze_soll = (a.get("statutory_members_number") or [{}])[-1].get("value") if isinstance(a.get("statutory_members_number"), list) else None
        sitze_ist = (a.get("current_members_number") or [{}])[-1].get("value") if isinstance(a.get("current_members_number"), list) else None
        liste = sorted(nach_kammer.get(code, []))
        vergangen = [x for x in liste if x[0] <= heute]
        kuenftig = [x for x in liste if x[0] > heute]
        mit_erg = [x for x in vergangen if v(x[2], "seats_per_parties")]
        kam = {"ipu": code, "name": name, "name_lokal": letzt("chamber_name_local") or "",
               "typ": typ, "sitze_soll": zahl(sitze_soll), "sitze_ist": zahl(sitze_ist), "ausgesetzt": bool(v(a, "is_suspended_chamber"))}
        if vergangen:
            von, bis, ea, eid = vergangen[-1]
            kam["letzte_wahl"] = {"datum": von, "bis": bis if bis != von else None, "art": (v(ea, "scope_of_elections") or {}).get("term"),
                                  "ergebnis_in_quelle": bool(v(ea, "seats_per_parties")), "quelle": "IPU Parline",
                                  "url": f"https://data.ipu.org/parliament/{iso}/"}
        if kuenftig:
            kam["naechste_wahl"] = {"datum": kuenftig[0][0], "quelle": "IPU Parline"}
        elif vergangen and tag(v(vergangen[-1][2], "expect_date_next_election")):
            kam["naechste_wahl"] = {"datum": tag(v(vergangen[-1][2], "expect_date_next_election")), "erwartet": True, "quelle": "IPU Parline"}
        # Ergebnis nur von der letzten Wahl; fehlt es dort und ist die Wahl jünger als 60 Tage, das der vorigen Wahl (als "vor der Wahl")
        vor_wahl = False
        if mit_erg and vergangen and mit_erg[-1] is not vergangen[-1]:
            vor_wahl = len(vergangen) > 1 and mit_erg[-1] is vergangen[-2] and (date.today() - date.fromisoformat(vergangen[-1][0])).days <= 60
            if not vor_wahl:
                mit_erg = []
        if mit_erg:
            von, bis, ea, eid = mit_erg[-1]
            sp = v(ea, "seats_per_parties") or []
            voll = []
            for s in sp:
                n = zahl(s.get("total_number_of_seats"))
                gesamt = next((b.get("value") for b in (s.get("vote_breakdown") or []) if ((b.get("label") or {}).get("en") or "").lower().startswith("full composition")), None)
                voll.append([parteien.get(s.get("party"), s.get("party")), n, zahl(gesamt)])
            teil = (v(ea, "scope_of_elections") or {}).get("term") == "partial_renewal"
            if teil and all(x[2] is not None for x in voll):
                sitze = [[x[0], x[2]] for x in voll]
                art = "Zusammensetzung nach der Teilwahl"
            else:
                sitze = [[x[0], x[1]] for x in voll if x[1] is not None]
                art = "neu vergebene Sitze der Teilwahl" if teil else "Sitze nach der Wahl"
            gov = (v(ea, "name_of_parties_government") or {})
            kam["wahl"] = {"datum": von, "art": art, "sitze": sorted(sitze, key=lambda x: -(x[1] or 0)),
                           "regierung_text": gov.get("en", "") if isinstance(gov, dict) else "",
                           "beteiligung": round(v(ea, "turnout"), 1) if isinstance(v(ea, "turnout"), (int, float)) else None, "vor_wahl": vor_wahl,
                           "quelle": "IPU Parline", "url": f"https://data.ipu.org/parliament/{iso}/"}
        out.setdefault(iso, []).append(kam)
    for l in out.values():
        l.sort(key=lambda k: ({"einkammer": 0, "unterhaus": 1, "oberhaus": 2}[k["typ"]], k["ipu"]))
    lizenz = (meta.get("licence") or {}).get("en", "").split("\n")[0].replace("This work is licensed under ", "").strip()
    lizenz = {"Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International": "CC BY-NC-SA 4.0"}.get(lizenz, lizenz)
    return out, lizenz


# ---------- Wikidata ----------

NATIONAL = """SELECT ?iso ?leg ?legWiki ?kammer ?kWiki ?typ WHERE {
  ?land wdt:P31 wd:Q3624078 ; wdt:P297 ?iso ; wdt:P194 ?leg .
  OPTIONAL { ?legWiki schema:about ?leg ; schema:isPartOf <https://en.wikipedia.org/> . }
  OPTIONAL { ?leg wdt:P527 ?kammer . ?kammer wdt:P31/wdt:P279* ?typ . VALUES ?typ { wd:Q637846 wd:Q375928 }
     OPTIONAL { ?kWiki schema:about ?kammer ; schema:isPartOf <https://en.wikipedia.org/> . } }
}"""

GLIED = """SELECT ?iso ?sub ?subLabel ?subDe ?code ?leg ?legWiki ?kammer ?kWiki ?kTyp ?hog ?hogLabel ?partei ?parteiLabel ?pkurz ?farbe WHERE {
  VALUES ?iso { %s }
  ?land wdt:P297 ?iso ; p:P150 ?st . ?st ps:P150 ?sub . FILTER NOT EXISTS { ?st pq:P582 [] }
  FILTER NOT EXISTS { ?sub wdt:P576 [] }
  ?sub wdt:P300 ?code . FILTER(STRSTARTS(?code, CONCAT(?iso, "-")))
  OPTIONAL { ?sub rdfs:label ?subDe . FILTER(LANG(?subDe) = "de") }
  OPTIONAL { ?sub wdt:P194 ?leg .
    OPTIONAL { ?legWiki schema:about ?leg ; schema:isPartOf <https://en.wikipedia.org/> . }
    OPTIONAL { ?leg wdt:P527 ?kammer . ?kWiki schema:about ?kammer ; schema:isPartOf <https://en.wikipedia.org/> .
               OPTIONAL { ?kammer wdt:P31/wdt:P279* ?kTyp . VALUES ?kTyp { wd:Q637846 wd:Q375928 } } } }
  OPTIONAL { ?sub wdt:P6 ?hog .
    OPTIONAL { ?hog p:P102 ?ps . ?ps ps:P102 ?partei . FILTER NOT EXISTS { ?ps pq:P582 [] }
      OPTIONAL { ?partei wdt:P1813 ?pkurz . FILTER(LANG(?pkurz) IN ("de", "en", "mul")) }
      OPTIONAL { ?partei wdt:P465 ?farbe } } }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,mul". }
}"""

FARBE_Q = """SELECT ?t ?farbe WHERE {
  VALUES ?t { %s }
  ?a schema:name ?t ; schema:isPartOf <https://en.wikipedia.org/> ; schema:about ?p . ?p wdt:P465 ?farbe .
}"""


def national_artikel():
    out = {}
    for x in sparql(NATIONAL):
        iso = w(x, "iso")
        e = out.setdefault(iso, {"leg": set(), "unterhaus": set(), "oberhaus": set()})
        if w(x, "legWiki"):
            e["leg"].add(wiki_titel(w(x, "legWiki")))
        if w(x, "kWiki"):
            e["unterhaus" if w(x, "typ").endswith("Q375928") else "oberhaus"].add(wiki_titel(w(x, "kWiki")))
    return out


def gliedstaaten_wd():
    out = {}
    for x in sparql(GLIED % " ".join(f'"{i}"' for i in FOEDERAL)):
        iso, code = w(x, "iso"), w(x, "code")
        g = out.setdefault(iso, {}).setdefault(code, {"name": w(x, "subLabel"), "name_de": w(x, "subDe"), "wikidata": qid(x, "sub"),
                                                       "parlament": "", "kammern": {}, "chef": {}})
        if w(x, "legWiki"):
            g["parlament"] = wiki_titel(w(x, "legWiki"))
        if w(x, "kWiki"):
            g["kammern"][wiki_titel(w(x, "kWiki"))] = "unterhaus" if w(x, "kTyp").endswith("Q375928") else "oberhaus" if w(x, "kTyp") else "?"
        if w(x, "hog"):
            c = g["chef"].setdefault(qid(x, "hog"), {"name": w(x, "hogLabel"), "partei": "", "partei_kurz": "", "farbe": ""})
            if w(x, "parteiLabel") and not c["partei"]:
                c["partei"] = w(x, "parteiLabel")
            if w(x, "pkurz") and (not c["partei_kurz"] or len(w(x, "pkurz")) < len(c["partei_kurz"])):
                c["partei_kurz"] = w(x, "pkurz")
            if w(x, "farbe") and re.fullmatch(r"[0-9A-Fa-f]{6}", w(x, "farbe")):
                c["farbe"] = "#" + w(x, "farbe").lower()
    return out


def parteifarben(titel):
    out, titel = {}, sorted({t for t in titel if t and '"' not in t and "\\" not in t})
    for i in range(0, len(titel), 150):
        teil = titel[i:i + 150]
        try:
            for x in sparql(FARBE_Q % " ".join(f'"{t}"@en' for t in teil)):
                f = w(x, "farbe")
                if re.fullmatch(r"[0-9A-Fa-f]{6}", f):
                    out[w(x, "t")] = "#" + f.lower()
        except Exception as e:  # noqa: BLE001
            print("  Parteifarben nicht abrufbar:", e, file=sys.stderr)
    return out


# ---------- Wikipedia-Infoboxen ----------

_cache_text = {}


def wikitext(titel):
    """Rohtext eines Artikels (folgt einer Weiterleitung). action=raw wird vom CDN ausgeliefert und ist aus der Cloud zuverlässiger
    als die API. Eine Sekunde Abstand zwischen den Abrufen."""
    if titel in _cache_text:
        return _cache_text[titel]
    t, ziel = None, titel
    for _ in range(3):
        t = holen(WIKI_RAW.format(urllib.parse.quote(ziel.replace(" ", "_"))), pause=1.0)
        m = re.match(r"\s*#REDIRECT\s*\[\[([^\]|#]+)", t or "", re.I)
        if not m:
            break
        ziel = m.group(1).strip()
    _cache_text[titel] = (t, ziel)
    return t, ziel


def infobox(t, name):
    """Gibt die Felder der ersten Infobox `name` als dict zurück (verschachtelte Vorlagen werden mitgezählt)."""
    m = re.search(r"\{\{\s*" + name, t or "", re.I)
    if not m:
        return None
    i, tiefe, start = m.start(), 0, m.start()
    while i < len(t):
        if t.startswith("{{", i):
            tiefe += 1
            i += 2
        elif t.startswith("}}", i):
            tiefe -= 1
            i += 2
            if tiefe == 0:
                break
        else:
            i += 1
    box = t[start:i]
    j = box.find("|")
    teile, puffer, tiefe_t, tiefe_l, i = [], [], 0, 0, j + 1
    while i < len(box) - 2:
        two = box[i:i + 2]
        if two in ("{{", "}}", "[[", "]]"):
            if two == "{{":
                tiefe_t += 1
            elif two == "}}":
                tiefe_t -= 1
            elif two == "[[":
                tiefe_l += 1
            else:
                tiefe_l -= 1
            puffer.append(two)
            i += 2
            continue
        ch = box[i]
        if ch == "|" and tiefe_t == 0 and tiefe_l <= 0:
            teile.append("".join(puffer))
            puffer = []
        else:
            puffer.append(ch)
        i += 1
    teile.append("".join(puffer))
    felder = {}
    for p in teile:
        if "=" in p:
            k, val = p.split("=", 1)
            felder[k.strip().lower()] = val.strip()
    return felder


def entlinken(s):
    s = re.sub(r"<ref[^>]*/>|<ref.*?</ref>|<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"\{\{\s*(?:efn|refn|sfn|cn|citation needed|ref label|note label)[^{}]*\}\}", "", s, flags=re.I)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"<[^>]+>", " ", s).replace("&nbsp;", " ").replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", s).strip()


MONAT = {m: i + 1 for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september",
                                          "october", "november", "december"])}


def datum_aus(s):
    """Letztes vollständiges Datum im Text (bei Zeiträumen wie '10 February 2022 – 7 March 2022' das Ende), sonst Monat oder Jahr."""
    s = re.sub(r"\{\{\s*start and end dates\|(\d{4})\|(\d{1,2})\|(\d{1,2})\|(\d{4})\|(\d{1,2})\|(\d{1,2})[^}]*\}\}",
               lambda m: f"{int(m.group(3))} {list(MONAT)[int(m.group(2)) - 1]} {m.group(1)} – {int(m.group(6))} {list(MONAT)[int(m.group(5)) - 1]} {m.group(4)}", s or "", flags=re.I)
    s = entlinken(re.sub(r"\{\{\s*(?:start date|end date|election date)[^|}]*\|(\d{4})\|(\d{1,2})\|(\d{1,2})[^}]*\}\}",
                         lambda m: f"{int(m.group(3))} {list(MONAT)[int(m.group(2)) - 1]} {m.group(1)}", s or "", flags=re.I))
    treffer = []
    for m in re.finditer(r"(\d{1,2})\s+([A-Za-z]+),?\s+(\d{4})|([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})", s):
        if m.group(1):
            t_, mo, j = int(m.group(1)), MONAT.get(m.group(2).lower()), int(m.group(3))
        else:
            t_, mo, j = int(m.group(5)), MONAT.get(m.group(4).lower()), int(m.group(6))
        if mo:
            try:
                treffer.append(date(j, mo, t_).isoformat())
            except ValueError:
                pass
    if treffer:
        return treffer[-1], treffer[0]
    m = re.search(r"([A-Za-z]+)\s+(\d{4})", s)
    if m and MONAT.get(m.group(1).lower()):
        x = f"{m.group(2)}-{MONAT[m.group(1).lower()]:02d}"
        return x, x
    m = re.search(r"\b(19|20)\d{2}\b", s)
    return (m.group(0), m.group(0)) if m else (None, None)


def erster_link(s):
    m = re.search(r"\[\[([^|\]#]+)", s or "")
    return m.group(1).strip() if m else ""


REGIERUNG = re.compile(r"government|governing|coalition|majority|treasury|ruling|cabinet|regierung|supported by|confidence", re.I)
OPPOSITION = re.compile(r"opposition|minority|other|vacant|crossbench|independent|non-?aligned|unaffiliated|non-inscrit|speaker|presiding", re.I)


def ohne_vorlagen(t, namen):
    """Entfernt Vorlagen {{name|...}} samt verschachtelter Vorlagen, auch über mehrere Zeilen."""
    muster = re.compile(r"\{\{\s*(?:" + namen + r")\s*[|}]", re.I)
    while True:
        m = muster.search(t)
        if not m:
            return t
        i, tiefe = m.start(), 0
        while i < len(t):
            if t.startswith("{{", i):
                tiefe += 1
                i += 2
            elif t.startswith("}}", i):
                tiefe -= 1
                i += 2
                if tiefe == 0:
                    break
            else:
                i += 1
        t = t[:m.start()] + t[i:]


def zusammensetzung(feld):
    """Parteien mit Sitzzahl aus `political_groups` (Zeilen mit Farbkästchen oder '(Zahl)'); fette Zeilen sind Blöcke.
    Zeilen, deren eingerückte Folgezeilen sich genau zu ihrer Zahl addieren (Fraktion -> Parteien), zählen nur über die Folgezeilen."""
    if not feld or re.match(r"\s*\{\{[^{}|]*(?:political groups|composition of)", feld, re.I):
        return None
    feld = re.sub(r"<ref[^>/]*/>|<ref.*?</ref>|<!--.*?-->", "", feld, flags=re.S)
    feld = ohne_vorlagen(feld, "efn|refn|sfn|cn|citation needed|cite [a-z]+|ref label|note label|nbsp")
    feld = re.sub(r"\{\{\s*party legend\s*\|([^|{}]+)\|(\d+)[^{}]*\}\}", r"{{color box|legend}} [[\1]] (\2)", feld, flags=re.I)
    feld = re.sub(r"\{\{\s*(?:ubl|unbulleted list|plainlist|nowrap)\s*\|", "", feld, flags=re.I)
    zeilen = re.split(r"\n|<br\s*/?>", feld)
    out, block, haupt = [], None, None
    for z in zeilen:
        roh = z.strip().lstrip("|").strip()
        if not roh:
            continue
        tiefe_z = len(re.match(r"[:*#]*", roh).group(0))
        nur_text = entlinken(re.sub(r"\{\{\s*(?:colou?r ?box|legend|party (?:colou?r|shading)[^{}]*|[A-Za-z ]*party colou?r)[^{}]*(?:\{\{[^{}]*\}\}[^{}]*)*\}\}", "", roh, flags=re.I))
        nur_text = re.sub(r"\{\{\s*nowrap\s*\|", "", nur_text, flags=re.I).replace("}}", "").strip(" *:#;")
        zahl = re.search(r"\((\d{1,4})(?:\s*(?:seats?|members?))?\)\s*$|[:–-]\s*(\d{1,4})\s*$", nur_text)
        hat_box = re.search(r"colou?r ?box|\{\{\s*legend|party colou?r|party shading", roh, re.I)
        fett = roh.lstrip(":*# ").startswith("'''") or roh.lstrip(":*# ").lower().startswith("{{nowrap|'''")
        if fett:
            block = nur_text
            if not roh.startswith((":", "*", "#")) and not hat_box:
                haupt = nur_text
            continue
        if not zahl:
            if not hat_box:
                block = nur_text or block
            continue
        n = int(zahl.group(1) or zahl.group(2))
        name = nur_text[:zahl.start()].strip(" :–-(") or "?"
        farbe = ""
        fm = re.search(r"colou?r ?box\s*\|\s*(#?[0-9A-Fa-f]{6}|#[0-9A-Fa-f]{3}|[a-zA-Z]+)\s*[|}]", roh, re.I)
        if fm and not fm.group(1).lower().startswith(("party", "canadian")):
            c = fm.group(1)
            farbe = ("#" + c.lstrip("#")) if re.fullmatch(r"#?[0-9A-Fa-f]{6}", c) else c.lower()
        pf = re.search(r"party colou?r\s*\|\s*([^|}]+)", roh, re.I)
        titel = erster_link(roh) or (pf.group(1).strip() if pf else "")
        reg = None
        for b in (block, haupt):
            if not b:
                continue
            kopf = b.split("(")[0]
            if OPPOSITION.search(kopf):
                reg = False
            elif REGIERUNG.search(kopf):
                reg = True
            if reg is not None:
                break
        if re.match(r"vacant|vakant|empty", name, re.I):
            name, titel, farbe = "vakant", "", "#3a4655"
        out.append({"partei": name[:60], "titel": titel, "sitze": n, "farbe": farbe, "block": (block or "")[:60], "regierung": reg, "tiefe": tiefe_z})
    # Fraktion mit Unterzeilen (z. B. CDU/CSU -> CDU, CSU): nur die Unterzeilen behalten
    weg = set()
    for i, g in enumerate(out):
        j = i + 1
        while j < len(out) and out[j]["tiefe"] > g["tiefe"]:
            j += 1
        kinder = out[i + 1:j]
        if kinder:
            t = min(k["tiefe"] for k in kinder)
            if sum(k["sitze"] for k in kinder if k["tiefe"] == t) == g["sitze"]:
                weg.add(i)
    out = [g for i, g in enumerate(out) if i not in weg]
    if any(g["regierung"] for g in out):
        for g in out:
            if g["regierung"] is None:
                g["regierung"] = False
    return out or None


def kammer_wiki(titel):
    """Infobox legislature eines Kammerartikels: Zusammensetzung, Sitze, letzte und nächste Wahl."""
    t, ziel = wikitext(titel)
    f = infobox(t, "Infobox legislature")
    if not f:
        return None
    sitze = None
    for k in ("seats", "members"):
        m = re.match(r"\s*([\d,]+)", entlinken(f.get(k, "")))
        if m:
            sitze = int(m.group(1).replace(",", ""))
            break
    gruppen = zusammensetzung(f.get("political_groups1") or f.get("political_groups"))
    summe = sum(g["sitze"] for g in gruppen) if gruppen else 0
    if gruppen and sitze and summe > sitze * 1.1:
        # dieselbe Liste zweimal (z. B. nach Partei und nach Bündnis): erster Abschnitt, der genau die Sitzzahl ergibt
        lauf = 0
        for i, g in enumerate(gruppen):
            lauf += g["sitze"]
            if lauf == sitze:
                gruppen, summe = gruppen[:i + 1], sitze
                break
    if gruppen and not sitze:
        sitze = summe
    ok = bool(gruppen) and sitze and .8 <= summe / sitze <= 1.1
    le, ne = f.get("last_election1") or f.get("last_election") or "", f.get("next_election1") or f.get("next_election") or ""
    le_d = datum_aus(le)
    ne_d = datum_aus(ne)
    return {"artikel": ziel, "name": entlinken(f.get("name", "")) or ziel, "sitze": sitze,
            "zusammensetzung": [{k: g[k] for k in ("partei", "titel", "sitze", "farbe", "regierung")} for g in gruppen] if ok else None,
            "zusammensetzung_ungeprueft": None if ok or not gruppen else f"Summe {summe} passt nicht zu {sitze} Sitzen",
            "letzte_wahl": {"datum": le_d[0], "beginn": le_d[1] if le_d[1] != le_d[0] else None, "artikel": erster_link(le), "text": entlinken(le)[:80]} if le_d[0] else None,
            "naechste_wahl": {"datum": ne_d[0], "artikel": erster_link(ne), "text": entlinken(ne)[:80]} if ne_d[0] else None}


def wahl_wiki(titel):
    """Infobox election des Wahlartikels: Datum, laufend?, Beteiligung, größte Parteien mit Stimmenanteil und Sitzen."""
    t, ziel = wikitext(titel)
    f = infobox(t, r"Infobox (?:legislative )?election")
    if not f:
        return None
    parteien = []
    for i in range(1, 13):
        p = f.get(f"party{i}") or f.get(f"alliance{i}")
        if not p:
            continue
        name = entlinken(re.sub(r"\{\{[^{}|]*party colou?r\|[^|}]*\|([^|}]*)(?:\|[^}]*)?\}\}", r"\1", p, flags=re.I))
        pct = re.search(r"([\d.]+)\s*%?", entlinken(f.get(f"percentage{i}", "") or f.get(f"pc{i}", "")))
        st = re.search(r"(\d+)", entlinken(f.get(f"seats{i}", "") or f.get(f"seats_after{i}", "")))
        parteien.append({"partei": name[:60], "titel": erster_link(p) or name, "prozent": float(pct.group(1)) if pct and pct.group(1).replace(".", "").isdigit() else None,
                         "sitze": int(st.group(1)) if st else None})
    bet = re.search(r"\b(\d{1,2}(?:\.\d+)?|100)\s*%", entlinken(re.sub(r"\{\{[^{}]*\}\}", "", f.get("turnout", ""))))
    return {"artikel": ziel, "datum": datum_aus(f.get("election_date", ""))[0], "laufend": f.get("ongoing", "").strip().lower() in ("yes", "y", "true"),
            "beteiligung": float(bet.group(1)) if bet else None, "parteien": [p for p in parteien if p["prozent"] is not None or p["sitze"] is not None]}


# ---------- Zusammenführen ----------

def tage_seit(d):
    if not d or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
        return None
    return (date.today() - date.fromisoformat(d)).days


def juengst_status(kam):
    """Hinweis, wenn die letzte Wahl höchstens SCHWELLE_TAGE zurückliegt; sagt, ob das Ergebnis schon in der Quelle steht."""
    lw = kam.get("letzte_wahl") or {}
    t = tage_seit(lw.get("datum"))
    if t is None or t < 0 or t > SCHWELLE_TAGE:
        return None
    w_ = kam.get("wahl") or {}
    st = kam.get("stimmen") or {}
    erg_da = (w_.get("datum") or "") >= lw["datum"] or bool(st.get("parteien") and st.get("datum") and st["datum"] >= lw["datum"] and not st.get("laufend"))
    akt = (kam.get("aktuell") or {})
    ipu_da = (w_.get("datum") or "") >= lw["datum"]
    ergebnis = "liegt vor" if ipu_da or (erg_da and t > 14) else "vorläufig (Wikipedia)" if erg_da else "noch nicht in der Quelle"
    return {"datum": lw["datum"], "tage": t, "ergebnis": ergebnis,
            "laufend": bool(st.get("laufend")), "zusammensetzung_vor_wahl": bool(akt) and not erg_da}


def hinweis_url(k):
    st, lw = k.get("stimmen") or {}, k.get("letzte_wahl") or {}
    if st.get("url") and (st.get("datum") or "") >= (lw.get("datum") or ""):
        return st["url"]
    return lw.get("url") or (k.get("wahl") or {}).get("url") or ""


def farben_setzen(liste, farben, belegt):
    for g in liste or []:
        if not g.get("farbe") or not g["farbe"].startswith("#"):
            g["farbe"] = farben.get(g.get("titel")) or farben.get(g.get("partei")) or g.get("farbe") or ""
        if not g["farbe"]:
            k = g.get("titel") or g.get("partei") or ""
            g["farbe"] = belegt.setdefault(k, FARBEN[sum(map(ord, k)) % len(FARBEN)])


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--geo", action="store_true")
    p.add_argument("--nur-national", action="store_true")
    a = p.parse_args()
    if a.geo or not GEO.exists():
        geo()
    alt = json.loads(ZIEL.read_text()) if ZIEL.exists() else {}
    alt_wahl = json.loads(CACHE.read_text()) if CACHE.exists() else alt.get("wahlartikel", {})
    heute = date.today()

    print("IPU Parline …", file=sys.stderr)
    try:
        ipu_d, ipu_lizenz = ipu()
    except Exception as e:  # noqa: BLE001
        print("IPU nicht abrufbar, alter Stand bleibt:", e, file=sys.stderr)
        ipu_d, ipu_lizenz = None, ""
    print("Wikidata …", file=sys.stderr)
    nat = national_artikel()
    glied = {} if a.nur_national else gliedstaaten_wd()

    wahlartikel = {}

    def wahl_holen(titel):
        """Wahlartikel aus dem Cache, außer die Wahl ist jünger als 90 Tage (Ergebnisse werden noch nachgetragen)."""
        if not titel:
            return None
        c = alt_wahl.get(titel)
        if c and c.get("datum") and len(c["datum"]) == 10 and (heute - date.fromisoformat(c["datum"])).days > 90 and not c.get("laufend"):
            wahlartikel[titel] = c
            return c
        try:
            r = wahl_wiki(titel)
        except Exception as e:  # noqa: BLE001
            print("  Wahlartikel", titel, e, file=sys.stderr)
            r = c
        if r:
            r["abruf"] = heute.isoformat() if r is not c else (c or {}).get("abruf")
            wahlartikel[titel] = r
        return r

    def mit_wiki(kam, titel):
        if not titel:
            return kam
        try:
            k = kammer_wiki(titel)
        except Exception as e:  # noqa: BLE001
            print("  Kammer", titel, e, file=sys.stderr)
            k = None
        if not k:
            kam.setdefault("wikipedia", titel)
            return kam
        kam["wikipedia"] = k["artikel"]
        if k["name"] and k["name"] != kam.get("name"):
            if kam.get("name"):
                kam["name_ipu"] = kam["name"]
            kam["name"] = k["name"]
        if k["zusammensetzung"]:
            kam["aktuell"] = {"sitze": k["zusammensetzung"], "summe": sum(g["sitze"] for g in k["zusammensetzung"]), "quelle": "Wikipedia",
                              "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(k["artikel"].replace(" ", "_")), "abruf": heute.isoformat()}
        elif k["zusammensetzung_ungeprueft"]:
            kam["hinweis"] = "Zusammensetzung in der Wikipedia-Infobox nicht auswertbar (" + k["zusammensetzung_ungeprueft"] + ")"
        if not kam.get("sitze_soll") and k["sitze"]:
            kam["sitze_soll"] = k["sitze"]
        wl = k["letzte_wahl"]
        if wl and (not kam.get("letzte_wahl") or (wl["datum"] and len(wl["datum"]) == 10 and wl["datum"] > kam["letzte_wahl"]["datum"])):
            kam["letzte_wahl"] = {"datum": wl["datum"], "beginn": wl.get("beginn"), "quelle": "Wikipedia",
                                  "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(wl["artikel"].replace(" ", "_")) if wl["artikel"] else kam.get("aktuell", {}).get("url", "")}
        if k["naechste_wahl"] and k["naechste_wahl"]["datum"] and k["naechste_wahl"]["datum"] >= heute.isoformat()[:len(k["naechste_wahl"]["datum"])] and not kam.get("naechste_wahl"):
            kam["naechste_wahl"] = {"datum": k["naechste_wahl"]["datum"], "quelle": "Wikipedia"}
        if wl and wl.get("artikel"):
            st = wahl_holen(wl["artikel"])
            if st and st.get("parteien"):
                kam["stimmen"] = {"datum": st.get("datum"), "laufend": st.get("laufend"), "beteiligung": st.get("beteiligung"),
                                  "parteien": st["parteien"][:8], "quelle": "Wikipedia",
                                  "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(st["artikel"].replace(" ", "_")), "abruf": st.get("abruf")}
        return kam

    # nationale Kammern
    staaten = {}
    basis = ipu_d if ipu_d is not None else {i: [{k_: v_ for k_, v_ in k.items() if k_ not in ("aktuell", "stimmen", "juengst")} for k in s.get("kammern", [])]
                                               for i, s in alt.get("staaten", {}).items()}
    n = 0
    for iso, kammern in sorted(basis.items()):
        art = nat.get(iso, {"leg": set(), "unterhaus": set(), "oberhaus": set()})
        if len(kammern) == 1:
            kammern[0]["typ"] = "einkammer"
        for kam in kammern:
            titel = KAMMER_WIKI.get(kam["ipu"])
            if not titel:
                if kam["typ"] == "einkammer":
                    titel = next(iter(sorted(art["leg"])), "") if not art["unterhaus"] else next(iter(sorted(art["unterhaus"])))
                else:
                    titel = next(iter(sorted(art[kam["typ"]])), "")
            mit_wiki(kam, titel)
            kam["juengst"] = juengst_status(kam)
            n += 1
            if n % 25 == 0:
                print(f"  {n} nationale Kammern", file=sys.stderr)
        staaten[iso] = {"kammern": kammern}

    # Gliedstaaten
    gl_out = {}
    if a.nur_national:
        # Gliedstaaten vom letzten vollen Lauf übernehmen, nur den Hinweis "gerade gewählt" neu berechnen
        gl_out = alt.get("gliedstaaten", {})
        for gs in gl_out.values():
            for g in gs.values():
                for kam in g["kammern"]:
                    kam["juengst"] = juengst_status(kam)
    for iso, subs in sorted(glied.items()):
        for code, g in sorted(subs.items()):
            kammern = []
            echte = {t: typ for t, typ in g["kammern"].items()}
            liste = [(t, typ) for t, typ in echte.items()]
            for t, typ in liste or [(g["parlament"], "einkammer")]:
                if not t:
                    continue
                kam = mit_wiki({"name": "", "typ": typ if typ != "?" else "kammer"}, t)
                if kam.get("aktuell") or kam.get("letzte_wahl") or not liste:
                    kammern.append(kam)
            # Bestandteile ohne Infobox (z. B. Ausschüsse) fallen weg; bleibt nichts, das Parlament selbst
            if liste and not kammern and g["parlament"]:
                kammern.append(mit_wiki({"name": "", "typ": "einkammer"}, g["parlament"]))
            if len(kammern) == 1:
                kammern[0]["typ"] = "einkammer"
            for kam in kammern:
                kam["juengst"] = juengst_status(kam)
            chef = sorted(g["chef"].values(), key=lambda c: (not c["partei"], c["name"]))
            gl_out.setdefault(iso, {})[code] = {"name": g["name"], "name_de": g["name_de"] if g["name_de"] and g["name_de"] != g["name"] else "",
                                                "wikidata": g["wikidata"], "regierungschef": chef[0] if chef else None, "kammern": kammern}
        print(f"  Gliedstaaten {iso}: {len(subs)}", file=sys.stderr)

    # Parteifarben aus Wikidata (P465) über die verlinkten Wikipedia-Artikel
    titel = set()
    alle_kammern = [k for s in staaten.values() for k in s["kammern"]] + [k for gs in gl_out.values() for g in gs.values() for k in g["kammern"]]
    for k in alle_kammern:
        for g in (k.get("aktuell") or {}).get("sitze", []) + (k.get("stimmen") or {}).get("parteien", []):
            titel.add(g.get("titel") or g.get("partei"))
        for g in (k.get("wahl") or {}).get("sitze", []):
            titel.add(g[0])
    farben = parteifarben(titel)
    belegt = {}
    for k in alle_kammern:
        farben_setzen((k.get("aktuell") or {}).get("sitze"), farben, belegt)
        farben_setzen((k.get("stimmen") or {}).get("parteien"), farben, belegt)
        if k.get("wahl"):
            # IPU-Namen: Farbe über gleichnamige Partei der Wikipedia-Zusammensetzung derselben Kammer
            akt = {re.sub(r"\W", "", (g.get("partei") or "").lower()): g["farbe"] for g in (k.get("aktuell") or {}).get("sitze", [])}
            akt.update({re.sub(r"\W", "", (g.get("titel") or "").lower()): g["farbe"] for g in (k.get("aktuell") or {}).get("sitze", [])})
            neu = []
            for s in k["wahl"]["sitze"]:
                schl = re.sub(r"\W", "", s[0].lower())
                kurz = re.search(r"\(([^)]+)\)\s*$", s[0])
                f = farben.get(s[0]) or akt.get(schl) or (akt.get(re.sub(r"\W", "", kurz.group(1).lower())) if kurz else None) \
                    or next((c for n_, c in akt.items() if n_ and len(n_) > 3 and (n_ in schl or schl in n_)), None)
                neu.append([s[0], s[1], f or belegt.setdefault(s[0], FARBEN[sum(map(ord, s[0])) % len(FARBEN)])])
            k["wahl"]["sitze"] = neu

    juengst = []
    for iso, s in staaten.items():
        for k in s["kammern"]:
            if k.get("juengst"):
                juengst.append({"iso": iso, "kammer": k.get("name"), "typ": k["typ"], **k["juengst"], "url": hinweis_url(k)})
    for iso, gs in gl_out.items():
        for code, g in gs.items():
            for k in g["kammern"]:
                if k.get("juengst"):
                    juengst.append({"iso": iso, "region": code, "region_name": g["name_de"] or g["name"], "kammer": k.get("name"), "typ": k["typ"], **k["juengst"],
                                    "url": hinweis_url(k)})
    juengst.sort(key=lambda x: x["datum"], reverse=True)

    out = {"abruf": heute.isoformat(), "schwelle_tage": SCHWELLE_TAGE,
           "quellen": {"ipu": {"name": f"IPU Parline der Interparlamentarischen Union ({ipu_lizenz or 'CC BY-NC-SA 4.0'})", "url": "https://data.ipu.org/",
                               "stand": heute.isoformat() if ipu_d is not None else alt.get("quellen", {}).get("ipu", {}).get("stand")},
                       "wikipedia": {"name": "Wikipedia (englisch), Infoboxen der Kammer- und Wahlartikel (CC BY-SA 4.0)", "url": "https://en.wikipedia.org/"},
                       "wikidata": {"name": "Wikidata (CC0): Parlamente P194/P527, Gliedstaaten P150/P300, Regierungschef P6, Partei P102, Parteifarbe P465",
                                    "url": "https://www.wikidata.org/"},
                       "geo": {"name": "Natural Earth 1:10 Mio., Admin 1 (gemeinfrei), vereinfacht", "url": "https://www.naturalearthdata.com/"}},
           "foederal": FOEDERAL, "staaten": staaten, "gliedstaaten": gl_out, "juengst": juengst}
    if a.nur_national:
        wahlartikel = {**alt_wahl, **wahlartikel}
    CACHE.write_text(json.dumps(wahlartikel, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    ZIEL.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    n_akt = sum(1 for k in alle_kammern if k.get("aktuell"))
    print(f"{ZIEL}: {len(staaten)} Staaten, {sum(len(s['kammern']) for s in staaten.values())} nationale Kammern, "
          f"{sum(len(g) for g in gl_out.values())} Gliedstaaten, {n_akt}/{len(alle_kammern)} Kammern mit aktueller Zusammensetzung, "
          f"{len(juengst)} Wahlen in den letzten {SCHWELLE_TAGE} Tagen", file=sys.stderr)


# ---------- Umrisse der Gliedstaaten ----------

def vereinfachen(pkte, tol):
    if len(pkte) < 5:
        return pkte
    def abst(p, a, b):
        (x, y), (x1, y1), (x2, y2) = p, a, b
        dx, dy = x2 - x1, y2 - y1
        if dx == dy == 0:
            return ((x - x1) ** 2 + (y - y1) ** 2) ** .5
        t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        return ((x - x1 - t * dx) ** 2 + (y - y1 - t * dy) ** 2) ** .5
    stapel, behalten = [(0, len(pkte) - 1)], {0, len(pkte) - 1}
    while stapel:
        a, b = stapel.pop()
        best, idx = 0, None
        for i in range(a + 1, b):
            d = abst(pkte[i], pkte[a], pkte[b])
            if d > best:
                best, idx = d, i
        if idx is not None and best > tol:
            behalten.add(idx)
            stapel += [(a, idx), (idx, b)]
    return [[round(x, 3), round(y, 3)] for i, (x, y) in enumerate(pkte) if i in behalten]


KLEIN = {"AT": .01, "CH": .008, "DE": .008, "BE": .008, "BA": .01, "KM": .005, "AE": .01, "FM": .005}


def geo():
    d = json.loads(holen(NE_A1, roh=True))
    feats = []
    for f in d["features"]:
        pr = f["properties"]
        iso = pr.get("iso_a2")
        if iso not in FOEDERAL or not pr.get("iso_3166_2"):
            continue
        tol = KLEIN.get(iso, .04 if iso not in ("RU", "CA", "US", "AU", "BR") else .06)
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        neu = [[vereinfachen(r, tol) for r in poly] for poly in polys]
        neu = [poly for poly in neu if len(poly[0]) >= 4]
        if not neu:
            continue
        feats.append({"type": "Feature", "properties": {"code": pr["iso_3166_2"], "iso": iso, "name": pr.get("name_de") or pr["name"], "wikidata": pr.get("wikidataid")},
                      "geometry": {"type": "MultiPolygon", "coordinates": neu}})
    GEO.write_text(json.dumps({"type": "FeatureCollection", "quelle": "Natural Earth 1:10 Mio., Admin 1 (gemeinfrei), vereinfacht",
                               "features": sorted(feats, key=lambda f: f["properties"]["code"])}, ensure_ascii=False, separators=(",", ":")))
    print(f"{GEO}: {len(feats)} Gliedstaaten, {GEO.stat().st_size // 1024} KB", file=sys.stderr)


if __name__ == "__main__":
    main()
