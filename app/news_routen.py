"""Weltkugel: echte Meldungen zu Störungen an den Engstellen der Haupthandelsrouten -> data/news_routen.json.

Quellen (beide kostenlos, ohne Schlüssel, nur Verweise auf Artikel: Titel, Adresse, Quelle, Datum, keine Volltexte):
 - GDELT DOC 2.0 API (https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/), streng gedrosselt (HTTP 429 bei geteilten Adressen)
 - Google News RSS-Suche (news.google.com/rss/search), Ausweichquelle, wenn GDELT nicht antwortet (--quelle auto, Vorgabe) Abgefragt werden je Engstelle die Suchbegriffe aus
app/geo/routen/knoten.csv zusammen mit Störungswörtern, Sprache Englisch oder Deutsch, letzte 14 Tage.

Damit nur passende Meldungen erscheinen, muss der Titel selbst den Ort (einen der Suchbegriffe) UND ein Störungswort enthalten.
Es wird nichts zusammengefasst oder umformuliert: angezeigt werden Originaltitel, Quelle (Domain), Datum und Link.

    python3 app/news_routen.py [--tage 14] [--quelle auto|gdelt|googlenews]
"""
import argparse
import csv
import json
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
ZIEL = HIER / "data/news_routen.json"
API = "https://api.gdeltproject.org/api/v2/doc/doc?"
STOER_EN = ["closure", "closed", "closes", "attack", "attacked", "attacks", "blocked", "blockade", "disruption", "disrupted", "disrupts",
            "suspended", "suspends", "delays", "delayed", "congestion", "strike", "low water", "collision", "grounded", "diverted",
            "divert", "drought", "halt", "halted", "seized", "seizure", "missile", "drone", "explosion", "backlog", "queue", "jam",
            "restrictions", "shut", "outage", "threat", "threatens", "reroute", "rerouting"]
STOER_DE = ["störung", "gesperrt", "sperrung", "angriff", "stau", "niedrigwasser", "blockade", "blockiert", "streik", "unterbrochen",
            "umleitung", "wartezeit", "beschuss", "eingeschränkt", "kollision", "havarie"]
# Titel mit diesen Wörtern betreffen nicht den Warenverkehr (Ausflugsbahn am Kap, Staumelder-Sammelseiten, Polizeimeldungen)
AUSSCHLUSS = ["funicular", "staumelder", "border patrol agent", "tourist", "touristen"]
# GDELT begrenzt die Länge der Abfrage; die feinere Prüfung macht titel_passt()
ABFRAGE_STOER = "(closure OR attack OR blocked OR disruption OR suspended OR delays OR congestion OR diverted OR Sperrung OR Störung)"


def begriffe(suche):
    """Ortsbegriffe für die Titelprüfung: die Phrasen in Anführungszeichen."""
    return [b.lower() for b in re.findall(r'"([^"]+)"', suche)]


def titel_passt(titel, orte):
    t = " " + re.sub(r"\s+", " ", titel.lower()) + " "
    ort = any(o in t for o in orte)
    stoer = any(re.search(r"\b" + re.escape(w) + r"\b", t) for w in STOER_EN + STOER_DE)
    raus = any(w in t for w in AUSSCHLUSS)
    return ort and stoer and not raus


def abfragen(suche, tage):
    # GDELT erlaubt Klammern nur um ODER-Verknüpfungen: einzelne Begriffe und schon geklammerte Ausdrücke bleiben, wie sie sind
    ort = f"({suche})" if " OR " in suche and "(" not in suche else suche
    q = f"{ort} {ABFRAGE_STOER} (sourcelang:english OR sourcelang:german)"
    url = API + urllib.parse.urlencode({"query": q, "mode": "artlist", "maxrecords": 75, "format": "json", "timespan": f"{tage}d", "sort": "datedesc"})
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Unternehmenskennzahlen/1.0"}), timeout=60) as r:
                text = r.read().decode("utf-8", "replace")
            if not text.strip().startswith("{"):
                raise ValueError(text[:120])
            return json.loads(text).get("articles", [])
        except Exception as e:  # noqa: BLE001
            print("  Wiederholung:", e, file=sys.stderr)
            time.sleep(20 * (i + 1))
    return None


GN = "https://news.google.com/rss/search?"
GN_SPRACHEN = (("en-US", "US", "US:en", "English"), ("de", "DE", "DE:de", "German"))


def googlenews(suche, tage):
    """Google News RSS: je Sprache eine Suche; liefert Einträge im GDELT-Format (title, url, domain, language, seendate)."""
    out = []
    for hl, gl, ceid, sprache in GN_SPRACHEN:
        url = GN + urllib.parse.urlencode({"q": f"{suche} when:{tage}d", "hl": hl, "gl": gl, "ceid": ceid})
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Unternehmenskennzahlen/1.0"}), timeout=60) as r:
                wurzel = ET.fromstring(r.read())
        except Exception as e:  # noqa: BLE001
            print("  Google News nicht abrufbar:", e, file=sys.stderr)
            return None
        for it in wurzel.iter("item"):
            q = it.find("source")
            quelle = (q.text or "").strip() if q is not None else ""
            titel = it.findtext("title", "")
            if quelle and titel.endswith(" - " + quelle):
                titel = titel[: -len(quelle) - 3]   # Google hängt die Quelle an den Titel an
            try:
                d = parsedate_to_datetime(it.findtext("pubDate", "")).strftime("%Y%m%d")
            except Exception:  # noqa: BLE001
                d = ""
            out.append({"title": titel, "url": it.findtext("link", ""), "domain": quelle or (q.get("url", "") if q is not None else ""),
                        "language": sprache, "seendate": d})
        time.sleep(2)
    out.sort(key=lambda x: x["seendate"], reverse=True)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tage", type=int, default=14)
    p.add_argument("--quelle", choices=("auto", "gdelt", "googlenews"), default="auto")
    a = p.parse_args()
    alt = json.loads(ZIEL.read_text()) if ZIEL.exists() else {"meldungen": {}}
    meldungen, fehler = {}, []
    quelle = a.quelle      # auto: GDELT, nach der ersten gescheiterten Abfrage für den Rest Google News
    genutzt = set()
    for r in csv.DictReader(open(HIER / "geo/routen/knoten.csv", encoding="utf-8")):
        if r["art"] != "engstelle" or not r["suche"]:
            continue
        arts = None
        if quelle in ("auto", "gdelt"):
            arts = abfragen(r["suche"], a.tage)
            time.sleep(12)    # GDELT: höchstens eine Abfrage alle fünf Sekunden (mit Abstand, sonst 429)
            if arts is not None:
                genutzt.add("GDELT")
            elif quelle == "auto":
                print("  GDELT antwortet nicht, weiter mit Google News", file=sys.stderr)
                quelle = "googlenews"
        if arts is None and quelle == "googlenews":
            arts = googlenews(r["suche"], a.tage)
            if arts is not None:
                genutzt.add("Google News")
        if arts is None:
            fehler.append(r["id"])
            if r["id"] in alt.get("meldungen", {}):
                meldungen[r["id"]] = alt["meldungen"][r["id"]]   # alter Stand bleibt, statt still zu verschwinden
            continue
        orte, gesehen, liste = begriffe(r["suche"]), set(), []
        for x in arts:
            titel = re.sub(r"\s+", " ", x.get("title", "")).strip().replace(" ,", ",").replace(" .", ".").replace(" :", ":").replace(" ' ", "'")
            if not titel or not titel_passt(titel, orte):
                continue
            k = titel.lower()[:80]
            if k in gesehen:
                continue
            gesehen.add(k)
            d = x.get("seendate", "")
            liste.append({"titel": titel, "url": x["url"], "quelle": x.get("domain", ""), "sprache": x.get("language", ""), "dienst": "Google News" if "news.google.com" in x["url"] else "GDELT",
                          "datum": f"{d[:4]}-{d[4:6]}-{d[6:8]}" if len(d) >= 8 else ""})
            if len(liste) >= 5:
                break
        if liste:
            meldungen[r["id"]] = liste
        print(f"  {r['id']}: {len(arts)} Artikel, {len(liste)} passend", file=sys.stderr)
    out = {"abruf": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "tage": a.tage, "fehler": fehler,
           "quelle": " und ".join(sorted(genutzt)) + " (Verweise auf Artikel; Titel unverändert)" if genutzt else "keine Quelle erreichbar",
           "url": "https://news.google.com/" if genutzt == {"Google News"} else "https://www.gdeltproject.org/",
           "regel": "Titel nennt den Ort und ein Störungswort; Sprache Englisch oder Deutsch; letzte Tage laut 'tage'",
           "meldungen": meldungen}
    ZIEL.write_text(json.dumps(out, ensure_ascii=False, indent=0))
    print(f"{ZIEL}: Meldungen zu {len(meldungen)} Engstellen, Fehler bei {fehler}", file=sys.stderr)


if __name__ == "__main__":
    main()
