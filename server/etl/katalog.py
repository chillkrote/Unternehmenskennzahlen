"""Datenkatalog (Revision 0005): Quellenverzeichnis und Prognosegeber in die Datenbank.

Eine Quelle der Wahrheit für die Texte: die Tabelle in docs/datenquellen.md (Quelle, genutzt für, Abruf, Schlüssel,
Lizenz / Weiterverbreitung, Bewertung). server/katalog/datenquellen.csv ergänzt je Zeile nur, was maschinenlesbar sein muss
(Kennung, Bereich, Status, Entscheidung, Pflichtangabe, Aliase). Fehlt eine Zeile in einer der beiden Dateien, bricht der Import ab,
damit Verzeichnis und Katalog nicht auseinanderlaufen.

volkswirtschaft/prognosegeber_oecd.csv -> forecaster (Quelle „prognosegeber“).
Der Inhalt beider Tabellen wird in einer Transaktion ersetzt (ingestion_run „katalog“); sind die Dateien unverändert, passiert nichts.
"""
import csv
import hashlib
import re
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VERZEICHNIS = REPO / "docs" / "datenquellen.md"
ERGAENZUNG = REPO / "server" / "katalog" / "datenquellen.csv"
PROGNOSEGEBER = REPO / "volkswirtschaft" / "prognosegeber_oecd.csv"
LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
TRENNER = re.compile(r"(?<!\\)\|")          # Zellgrenze; ein maskierter Strich (\\|) gehört zum Zelltext
STATUS = ("geeignet", "namensnennung", "voraussichtlich", "pruefen", "eingeschraenkt", "kritisch", "erledigt")
KOPF = ("Quelle", "genutzt für", "Abruf (Skript)", "Schlüssel", "Lizenz / Weiterverbreitung", "Bewertung")


class KatalogFehler(ValueError):
    pass


def _klartext(s):
    """Markdown der Tabellenzelle -> Text (Links behalten ihren Text, Fettdruck und Code-Striche entfallen, Leerraum wird vereinheitlicht)."""
    s = LINK.sub(r"\1", s).replace("\\|", "|")
    return re.sub(r"\s+", " ", re.sub(r"\*\*|`", "", s).replace("\u00a0", " ")).strip() or None


def _zellen(zeile):
    z = zeile.strip()
    z = z[1:] if z.startswith("|") else z
    z = z[:-1] if z.endswith("|") and not z.endswith("\\|") else z
    return [c.strip() for c in TRENNER.split(z)]


def verzeichnis_lesen(pfad=VERZEICHNIS):
    """Die erste Tabelle mit der Spalte „Quelle“ aus datenquellen.md als Liste von Zeilen (Reihenfolge wie im Dokument)."""
    zeilen, kopf = [], None
    for z in Path(pfad).read_text(encoding="utf-8").splitlines():
        if not z.startswith("|"):
            if kopf and zeilen:
                break
            continue
        zellen = _zellen(z)
        if kopf is None:
            if zellen and zellen[0] == "Quelle":
                kopf = zellen
                fehlt = [k for k in KOPF if k not in kopf]
                if fehlt:
                    raise KatalogFehler(f"{pfad}: Spalten {fehlt} fehlen in der Quellentabelle")
            continue
        if set("".join(zellen)) <= set("-: "):
            continue
        if len(zellen) != len(kopf):
            # z. B. ein unmaskierter senkrechter Strich im Zelltext: sonst rutschen Lizenz und Bewertung still in falsche Spalten
            raise KatalogFehler(f"{pfad}: Zeile „{zellen[0][:60]}“ hat {len(zellen)} statt {len(kopf)} Zellen (senkrechten Strich im Text als \\| schreiben)")
        roh = dict(zip(kopf, zellen))
        links = [u for _, u in LINK.findall(" ".join(zellen))]
        zeilen.append({"quelle": _klartext(roh["Quelle"]), "genutzt_fuer": _klartext(roh.get("genutzt für", "")),
                       "abruf": _klartext(roh.get("Abruf (Skript)", "")), "schluessel": _klartext(roh.get("Schlüssel", "")),
                       "lizenz": _klartext(roh.get("Lizenz / Weiterverbreitung", "")), "bewertung": _klartext(roh.get("Bewertung", "")),
                       "links": list(dict.fromkeys(links))})
    if not zeilen:
        raise KatalogFehler(f"keine Quellentabelle in {pfad}")
    return zeilen


def katalog(verzeichnis=VERZEICHNIS, ergaenzung=ERGAENZUNG):
    """Verzeichnis und Ergänzung zusammengeführt; Abweichungen in den Quellnamen sind ein Fehler."""
    text = verzeichnis_lesen(verzeichnis)
    with open(ergaenzung, newline="", encoding="utf-8") as f:
        erg = list(csv.DictReader(f))
    for e in erg:
        e["quelle"] = _klartext(e["quelle"]) or ""
    nach_name = {e["quelle"]: e for e in erg}
    doppelt = sorted({t["quelle"] for t in text if sum(1 for x in text if x["quelle"] == t["quelle"]) > 1})
    ids = [e["id"] for e in erg]
    doppelt_id = sorted({i for i in ids if ids.count(i) > 1})
    falsch = sorted({e["status"] for e in erg} - set(STATUS))
    if doppelt or doppelt_id or falsch:
        raise KatalogFehler(f"Quellenkatalog uneindeutig: doppelte Quellen {doppelt}, doppelte Kennungen {doppelt_id}, unbekannte Status {falsch}")
    fehlt = [t["quelle"] for t in text if t["quelle"] not in nach_name]
    zuviel = sorted(set(nach_name) - {t["quelle"] for t in text})
    if fehlt or zuviel or len(nach_name) != len(erg):
        raise KatalogFehler(f"datenquellen.md und katalog/datenquellen.csv passen nicht zusammen: ohne Ergänzung {fehlt}, "
                            f"nicht im Verzeichnis {zuviel}")
    out = []
    for pos, t in enumerate(text):
        e = nach_name[t["quelle"]]
        out.append({"id": e["id"], "name": t["quelle"], "area": e["bereich"], "used_for": t["genutzt_fuer"], "access": t["abruf"],
                    "credentials": t["schluessel"], "license": t["lizenz"], "assessment": t["bewertung"], "status": e["status"],
                    "decision": e["entscheidung"] or None, "attribution": e["namensnennung"] or None, "links": t["links"],
                    "aliases": [a for a in (e["aliase"] or "").split("|") if a], "position": pos})
    return out


def _sha(*pfade):
    h = hashlib.sha256()
    for p in pfade:
        h.update(Path(p).read_bytes())
    return h.hexdigest()


def _int(s):
    try:
        return int(s)
    except (TypeError, ValueError):
        return None


def importieren(conn, dry_run=False, erzwingen=False, verzeichnis=VERZEICHNIS, ergaenzung=ERGAENZUNG, prognosegeber=PROGNOSEGEBER):
    import ingest
    bericht = Counter()
    quellen = katalog(verzeichnis, ergaenzung)
    sha = _sha(verzeichnis, ergaenzung, prognosegeber)
    alt = conn.execute("SELECT watermark->>'sha256' FROM international.ingestion_run WHERE adapter = 'katalog' AND status = 'ok' "
                       "ORDER BY id DESC LIMIT 1").fetchone()
    if alt and alt[0] == sha and not erzwingen:
        bericht["unveraendert"] = 1
        return bericht
    with open(prognosegeber, newline="", encoding="utf-8") as f:
        geber = list(csv.DictReader(f))
    with ingest.ingestion_lauf(conn, "katalog", dry_run=dry_run) as lauf:
        conn.execute("DELETE FROM international.forecaster")
        conn.execute("DELETE FROM international.data_source")
        for q in quellen:
            conn.execute(
                "INSERT INTO international.data_source (id, name, area, used_for, access, credentials, license, assessment, status, decision, "
                "attribution, links, aliases, position, run_id) VALUES (%(id)s,%(name)s,%(area)s,%(used_for)s,%(access)s,%(credentials)s,"
                "%(license)s,%(assessment)s,%(status)s,%(decision)s,%(attribution)s,%(links)s,%(aliases)s,%(position)s,%(run)s)",
                {**q, "run": lauf.run_id})
            bericht["quellen"] += 1
        for nr, g in enumerate(geber, start=1):
            conn.execute(
                "INSERT INTO international.forecaster (id, source_id, geo, country, publisher, type, publication, variables, horizon, rhythm, url, "
                "access, data_url, priority, note, http_status_url, http_status_data, checked, run_id) VALUES (%s,'prognosegeber',%s,%s,%s,%s,%s,"
                "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (nr, g["geo"], g["land"] or None, g["herausgeber"], g["typ"] or None, g["publikation"] or None, g["prognosegroessen"] or None,
                 g["horizont"] or None, g["rhythmus"] or None, g["url"] or None, g["zugang"] or None, g["daten_url"] or None,
                 _int(g["prioritaet"]), g["hinweis"] or None, g["http_status_url"] or None, g["http_status_daten"] or None,
                 g["geprueft"] or None, lauf.run_id))
            bericht["prognosegeber"] += 1
        # Reihen, deren Anbieter keiner Quelle zugeordnet ist (Hinweis, kein Abbruch: die Reihen kommen aus einem eigenen Import)
        bericht["reihen_ohne_quelle"] = conn.execute(
            "SELECT count(*) FROM international.series s WHERE NOT EXISTS (SELECT 1 FROM international.data_source d "
            "WHERE s.provider = ANY(d.aliases))").fetchone()[0]
        lauf.anzahl = bericht["quellen"] + bericht["prognosegeber"]
        lauf.wasserzeichen = {"sha256": sha}
    return bericht
