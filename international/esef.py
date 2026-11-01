"""ESEF-Adapter (IFRS-Konzernabschlüsse im xBRL-JSON-Format) über den Filing-Index https://filings.xbrl.org.

* Unternehmen werden über die LEI gefunden (ISIN -> LEI über die GLEIF-API, https://api.gleif.org/api/v1/lei-records?filter[isin]=...).
* Der Index liefert je Einreichung eine xBRL-JSON-Datei (OIM). ESEF ist ein Format, kein einheitlicher Download-Endpunkt; der Index deckt nicht
  jede Einreichung ab (Lücken je Unternehmen sind normal) und gibt `period_end` nicht immer korrekt an: maßgeblich sind die Perioden der Fakten.
* OIM-Perioden: ein Stichtag ist der Beginn des Folgetags ("2026-01-01T00:00:00" = Ende 31.12.2025); eine Dauer endet ebenso am Beginn des Folgetags.
* Nur Fakten ohne zusätzliche Dimensionen (Gesamtkonzern laut Primärrechnung), nur numerische Fakten mit ISO-Währung.
* Berichtigte Fassungen bleiben erhalten: jede Einreichung ist eine eigene Quelle (fxo_id); aktuelle Sicht über international.fact_as_of.
"""
import hashlib
import json
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

import ingest
from httpsafe import AbrufFehler, SichererClient, atomar_speichern
from international_core import periode_klasse

INDEX = "https://filings.xbrl.org"
HOSTS = {"filings.xbrl.org", "api.gleif.org"}
ANBIETER = "esef-filings-xbrl-org"
MAPPING_VERSION = "esef-v1"
LEI_MUSTER = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")

# metric_code -> IFRS-Konzepte in Rangfolge (je Einreichung und Periode gilt das erste vorhandene Konzept)
MAPPING = {
    "assets": {"concepts": ["ifrs-full:Assets"], "period": "instant"},
    "equity": {"concepts": ["ifrs-full:EquityAttributableToOwnersOfParent"], "period": "instant"},
    "equity_incl_nci": {"concepts": ["ifrs-full:Equity"], "period": "instant"},
    "revenue": {"concepts": ["ifrs-full:Revenue", "ifrs-full:RevenueFromContractsWithCustomers"], "period": "duration"},
    "net_income": {"concepts": ["ifrs-full:ProfitLossAttributableToOwnersOfParent"], "period": "duration"},
    "net_income_incl_nci": {"concepts": ["ifrs-full:ProfitLoss"], "period": "duration"},
    "operating_cash_flow": {"concepts": ["ifrs-full:CashFlowsFromUsedInOperatingActivities"], "period": "duration"},
}
OHNE_BANK = {"revenue"}


def lei_pruefen(lei):
    if not LEI_MUSTER.match(lei or ""):
        raise ValueError(f"LEI muss 20 Zeichen (18 alphanumerisch, 2 Prüfziffern) haben: {lei!r}")
    # ISO 17442: Prüfziffer nach ISO 7064 MOD 97-10 (Buchstaben als 10..35)
    if int("".join(str(int(c, 36)) for c in lei)) % 97 != 1:
        raise ValueError(f"LEI-Prüfziffer falsch: {lei}")
    return lei


def lei_zu_isin(client: SichererClient, isin):
    """GLEIF: ISIN -> (LEI, Name, Land). Genau ein Treffer erforderlich."""
    d = json.loads(client.holen(f"https://api.gleif.org/api/v1/lei-records?filter%5Bisin%5D={quote(isin)}"))
    treffer = d.get("data", [])
    if len(treffer) != 1:
        raise AbrufFehler(f"ISIN {isin}: {len(treffer)} LEI-Treffer bei GLEIF, genau 1 erwartet")
    e = treffer[0]["attributes"]["entity"]
    return lei_pruefen(treffer[0]["id"]), e["legalName"]["name"], e["legalAddress"]["country"]


def einreichungen(client: SichererClient, lei):
    """Alle Einreichungen der LEI im Index (JSON:API, mit Seitenfolge)."""
    lei_pruefen(lei)
    url, ausgabe = f"{INDEX}/api/entities/{lei}/filings", []
    for _ in range(50):
        d = json.loads(client.holen(url))
        ausgabe += d.get("data", [])
        url = (d.get("links") or {}).get("next")
        if not url:
            break
    return ausgabe


def abrufen(client: SichererClient, einreichung, speicher_verzeichnis):
    """Lädt die xBRL-JSON-Datei einer Einreichung (nur vom Index-Host) und speichert sie atomar. -> (pfad, sha256, bytes, url)."""
    a = einreichung["attributes"]
    if not a.get("json_url"):
        raise AbrufFehler(f"Einreichung ohne xBRL-JSON: {a.get('fxo_id')}")
    url = INDEX + a["json_url"]
    daten = client.holen(url)
    json.loads(daten)
    h = hashlib.sha256(daten).hexdigest()
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", a["fxo_id"]) + f"_{h[:12]}.json"
    pfad, _ = atomar_speichern(speicher_verzeichnis, name, daten)
    return pfad, h, len(daten), url


def _tag(s):
    return datetime.fromisoformat(s).date()


def periode(p):
    """OIM-Periode -> (beginn oder None, ende). Instant 2026-01-01T00:00:00 = Stichtag 2025-12-31; Dauer a/b endet am Vortag von b."""
    if "/" in p:
        a, b = p.split("/")
        return _tag(a), _tag(b) - timedelta(days=1)
    return None, _tag(p) - timedelta(days=1)


def extrahieren(rohdaten: dict, lei, mapping=MAPPING, metrics=None):
    """Numerische Fakten der gemappten Konzepte ohne zusätzliche Dimensionen für die LEI, mit Rang des Konzepts."""
    konzept_zu_metrik = {c: (m, r) for m, v in mapping.items() if metrics is None or m in metrics for r, c in enumerate(v["concepts"])}
    ausgabe = []
    for fid, f in rohdaten.get("facts", {}).items():
        dm = f.get("dimensions", {})
        if dm.get("concept") not in konzept_zu_metrik or set(dm) - {"concept", "entity", "period", "unit"}:
            continue
        if not str(dm.get("entity", "")).endswith(lei) or not str(dm.get("unit", "")).startswith("iso4217:"):
            continue
        try:
            wert = Decimal(str(f["value"]))
        except (InvalidOperation, KeyError):
            continue
        if not wert.is_finite():
            continue
        metric, rang = konzept_zu_metrik[dm["concept"]]
        beginn, ende = periode(dm["period"])
        ausgabe.append({"metric": metric, "concept": dm["concept"], "rang": rang, "start": beginn, "end": ende, "wert": wert,
                        "unit": dm["unit"].split(":", 1)[1], "decimals": f.get("decimals"), "fact_id": fid})
    return ausgabe


def normalisieren(eintraege, entity_id, source_id, einreichung):
    a = einreichung["attributes"]
    veroeffentlicht = a.get("published") or a.get("date_added")
    reported_at = date.fromisoformat(veroeffentlicht[:10]) if veroeffentlicht else None
    bester = {}
    for e in eintraege:
        k = (e["metric"], e["start"], e["end"])
        bester[k] = min(bester.get(k, e["rang"]), e["rang"])
    zeilen, gesehen = [], {}
    for e in eintraege:
        if e["rang"] != bester[(e["metric"], e["start"], e["end"])]:
            continue
        if (MAPPING[e["metric"]]["period"] == "instant") != (e["start"] is None):
            continue
        if e["start"] is not None and periode_klasse(e["start"], e["end"]) != "annual":
            continue
        schluessel = f"{e['concept']}|{e['unit']}|{e['start'] or ''}|{e['end']}"
        if schluessel in gesehen:
            if gesehen[schluessel] != e["wert"]:
                raise ValueError(f"Widerspruch in derselben Einreichung: {schluessel}")
            continue
        gesehen[schluessel] = e["wert"]
        zeilen.append({
            "entity_id": entity_id, "metric_code": e["metric"], "period_start": e["start"], "period_end": e["end"],
            "value": e["wert"], "unit": e["unit"], "accounting_standard": "IFRS",
            "consolidation": "group",       # ESEF-Pflicht gilt für den konsolidierten IFRS-Abschluss; Primärrechnung ohne Dimensionen
            "dimensions": {}, "source_id": source_id, "source_fact_key": schluessel, "mapping_version": MAPPING_VERSION,
            "quality": "raw", "reported_at": reported_at,
            "provenance": {"fxo_id": a.get("fxo_id"), "concept": e["concept"], "decimals": e["decimals"], "originalwert": str(e["wert"]),
                           "skalierung": 1, "index_sha256": a.get("sha256"), "index_period_end": a.get("period_end"),
                           "reported_at_quelle": "published" if a.get("published") else "date_added (Näherung)"},
        })
    return zeilen


def importieren(conn, rohdatei, sha256, url, einreichung, entity_id, lei, dry_run=False, bank=False):
    roh = json.loads(open(rohdatei, "rb").read())
    metrics = set(MAPPING) - (OHNE_BANK if bank else set())
    neu = alt = 0
    with ingest.ingestion_lauf(conn, "esef-filings", dry_run=dry_run) as lauf:
        conn.execute("INSERT INTO international.identifier (scheme, value, entity_id) VALUES ('LEI', %s, %s) ON CONFLICT DO NOTHING", (lei, entity_id))
        sid = ingest.quelle_registrieren(conn, ANBIETER, einreichung["attributes"]["fxo_id"], url, sha256, str(rohdatei),
                                         published_at=einreichung["attributes"].get("published"), rights_status="unverified")
        for z in normalisieren(extrahieren(roh, lei, metrics=metrics), entity_id, sid, einreichung):
            if ingest.fakt_einfuegen(conn, z):
                neu += 1
            else:
                alt += 1
        lauf.anzahl = neu
        lauf.wasserzeichen = {"lei": lei, "fxo_id": einreichung["attributes"]["fxo_id"], "sha256": sha256}
    return neu, alt
