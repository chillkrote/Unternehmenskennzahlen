"""DART-Adapter (Südkorea): konsolidierte K-IFRS-Jahresabschlüsse über die OpenDART-API der Finanzaufsicht (https://opendart.fss.or.kr).

* Zugang nur über den Schlüssel in der Umgebungsvariablen DART_API (ersatzweise DART_API_KEY). Der Schlüssel wird als Parameter crtfc_key gesendet,
  nie ausgegeben, nie gespeichert: Quellenadresse, Rohdatei, Fehlermeldungen und Protokoll enthalten ihn nicht.
* Unternehmen werden über corp_code geführt (corpCode.xml, Zuordnung per Börsenkürzel); Name, Börsenkürzel und Geschäftsjahresende werden mit company.json geprüft.
* fnlttSinglAcntAll (reprt_code 11011 = Jahresbericht, fs_div CFS = Konzernabschluss) liefert die Hauptrechnungen mit IFRS-Kontenkennung (ifrs-full_…).
  Je Bericht gilt nur die Spalte des Berichtsjahres (thstrm); die Vorjahresspalten sind Vergleichswerte und werden nicht übernommen,
  damit jede Fassung zu ihrem Bericht (rcept_no) gehört. Spätere Berichtigungen bleiben als eigene Quelle erhalten.
* Beträge stehen in KRW (ganze Won) und werden nie umgerechnet.
"""
import hashlib
import json
import os
import re
import zipfile
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO
from urllib.parse import urlencode

import esef
import ingest
from httpsafe import AbrufFehler, SichererClient, atomar_speichern
from international_core import periode_klasse

HOST = "opendart.fss.or.kr"
BASIS = f"https://{HOST}/api/"
ANBIETER = "dart-opendart"
MAPPING_VERSION = "dart-v1"
BERICHT_JAHR = "11011"          # Jahresbericht (Geschäftsbericht)
KONZERN = "CFS"                 # konsolidiert; OFS wäre der Einzelabschluss
SAETZE = {"BS", "IS", "CIS", "CF"}

# Kennzahlen und Rangfolge der Konzepte wie beim ESEF-Adapter (IFRS-Konzept ifrs-full:X wird bei DART als ifrs-full_X geführt)
MAPPING = {m: {**v, "concepts": [c.replace(":", "_") for c in v["concepts"]]} for m, v in esef.MAPPING.items()}
OHNE_BANK = esef.OHNE_BANK


def schluessel():
    k = os.environ.get("DART_API") or os.environ.get("DART_API_KEY") or ""
    if not re.fullmatch(r"[0-9A-Za-z]{20,64}", k):
        raise AbrufFehler("DART-Schlüssel fehlt oder hat ein unerwartetes Format (Umgebungsvariable DART_API oder DART_API_KEY)")
    return k


NEUTRALER_AGENT = "Unternehmenskennzahlen-Forschung (github.com/chillkrote/Unternehmenskennzahlen)"


def neutraler_client(hosts):
    """Client für Anbieter ohne Kontaktpflicht (DART, GLEIF-Suche): neutrale Kennung statt persönlicher Adresse im User-Agent."""
    return SichererClient(hosts, user_agent=os.environ.get("DART_USER_AGENT") or NEUTRALER_AGENT, max_bytes=60_000_000, timeout=120,
                          min_abstand=0.3, max_versuche=5, kontakt_pflicht=False)


class DartClient:
    """Dünne Hülle um SichererClient: hängt den Schlüssel an und entfernt ihn aus jeder Fehlermeldung."""

    def __init__(self, client=None, key=None):
        self._key = key or schluessel()
        self.client = client or neutraler_client({HOST})

    def holen(self, endpunkt, **params):
        """Gibt (bytes, öffentliche Adresse ohne Schlüssel) zurück."""
        oeffentlich = BASIS + endpunkt + ("?" + urlencode(params) if params else "")
        url = BASIS + endpunkt + "?" + urlencode({"crtfc_key": self._key, **params})
        try:
            return self.client.holen(url), oeffentlich
        except AbrufFehler as e:
            raise AbrufFehler(str(e).replace(self._key, "***")) from None


def json_pruefen(daten, erlaubt=("000",)):
    try:
        j = json.loads(daten)
    except ValueError as e:
        raise AbrufFehler("Antwort ist kein JSON") from e
    if j.get("status") not in erlaubt:
        raise AbrufFehler(f"DART-Status {j.get('status')}: {j.get('message')}")
    return j


def firmenliste(client: DartClient, cache=None, max_alter_tage=7):
    """{Börsenkürzel: (corp_code, Name)} aus corpCode.xml (nur börsennotierte Gesellschaften mit Kürzel). Die 3,6-MB-Datei wird mit cache=Pfad
    wiederverwendet, solange sie jünger als max_alter_tage ist (der Abruf bricht gelegentlich ab)."""
    import time
    from pathlib import Path
    cache = Path(cache) if cache else None
    if cache and cache.exists() and time.time() - cache.stat().st_mtime < max_alter_tage * 86400:
        daten = cache.read_bytes()
    else:
        daten, _ = client.holen("corpCode.xml")
        if cache:
            atomar_speichern(cache.parent, cache.name, daten)
    try:
        xml = zipfile.ZipFile(BytesIO(daten)).read("CORPCODE.xml").decode("utf-8")
    except (zipfile.BadZipFile, KeyError) as e:
        raise AbrufFehler("corpCode.xml ist keine gültige ZIP-Datei") from e
    ergebnis = {}
    for m in re.finditer(r"<list>(.*?)</list>", xml, re.S):
        b = m.group(1)
        sc = re.search(r"<stock_code>\s*(\d{6})\s*<", b)
        if sc:
            ergebnis[sc.group(1)] = (re.search(r"<corp_code>(\d{8})<", b).group(1), re.search(r"<corp_name>(.*?)<", b).group(1))
    return ergebnis


def firma(client: DartClient, corp_code):
    daten, _ = client.holen("company.json", corp_code=corp_code)
    return json_pruefen(daten)


def abschluss_abrufen(client: DartClient, corp_code, jahr, speicher_verzeichnis):
    """Rohantwort sichern. Gibt None zurück, wenn DART für dieses Jahr keine Daten hat (Status 013), sonst (pfad, sha256, bytes, öffentliche Adresse, json)."""
    daten, url = client.holen("fnlttSinglAcntAll.json", corp_code=corp_code, bsns_year=jahr, reprt_code=BERICHT_JAHR, fs_div=KONZERN)
    j = json_pruefen(daten, erlaubt=("000", "013"))
    if j["status"] == "013":
        return None
    h = hashlib.sha256(daten).hexdigest()
    pfad, h2 = atomar_speichern(speicher_verzeichnis, f"{corp_code}_{jahr}_{h[:16]}.json", daten)
    return pfad, h2, len(daten), url, j


def kontoname_vereinheitlichen(account_id):
    """Berichte bis etwa GJ2018 führen die IFRS-Konten als ifrs_X, spätere als ifrs-full_X: gleiches Konzept, gleiche Bedeutung."""
    a = account_id or ""
    return "ifrs-full_" + a[len("ifrs_"):] if a.startswith("ifrs_") else a


def betrag(text):
    t = (text or "").replace(",", "").strip()
    if t in ("", "-"):
        return None
    try:
        return Decimal(t)
    except InvalidOperation:
        return None


def extrahieren(roh: dict, metrics=None):
    """Einträge der gemappten Konzepte aus den Hauptrechnungen, nur Zeilen ohne Detailachse (account_detail '-'), nur Berichtsjahr, nur KRW."""
    ausgabe = []
    for z in roh.get("list", []):
        if z.get("sj_div") not in SAETZE or z.get("account_detail", "-") != "-":
            continue
        for metric, m in MAPPING.items():
            if metrics is not None and metric not in metrics:
                continue
            konto = kontoname_vereinheitlichen(z.get("account_id"))
            if konto in m["concepts"]:
                if z.get("currency") != "KRW":
                    raise ValueError(f"Währung {z.get('currency')} statt KRW: {z.get('account_id')}")
                w = betrag(z.get("thstrm_amount"))
                if w is not None:
                    ausgabe.append({"metric": metric, "concept": konto, "konto_original": z["account_id"], "rang": m["concepts"].index(konto),
                                    "wert": w, "name": z.get("account_nm"), "satz": z["sj_div"], "rcept_no": z["rcept_no"], "jahr": int(z["bsns_year"]),
                                    "periode_text": z.get("thstrm_nm")})
    return ausgabe


def normalisieren(eintraege, entity_id, source_id):
    """Fakt-Zeilen (Geschäftsjahr = Kalenderjahr; das prüft kr_pilot über acc_mt = 12). Je Kennzahl gilt das Konzept mit dem besten Rang;
    derselbe Wert in mehreren Rechnungen (z. B. ProfitLoss in GuV und Cashflow) zählt einmal, verschiedene Werte sind ein Widerspruch."""
    bester = {}
    for e in eintraege:
        bester[e["metric"]] = min(bester.get(e["metric"], e["rang"]), e["rang"])
    gruppen = {}
    for e in eintraege:
        if e["rang"] == bester[e["metric"]]:
            gruppen.setdefault(e["metric"], []).append(e)
    zeilen = []
    for metric, liste in gruppen.items():
        if len({x["wert"] for x in liste}) > 1:
            raise ValueError(f"Widerspruch im selben Bericht: {metric} {sorted({str(x['wert']) for x in liste})}")
        e = liste[0]
        jahr = e["jahr"]
        start = None if MAPPING[metric]["period"] == "instant" else date(jahr, 1, 1)
        ende = date(jahr, 12, 31)
        if start is not None and periode_klasse(start, ende) != "annual":
            continue
        zeilen.append({
            "entity_id": entity_id, "metric_code": metric, "period_start": start, "period_end": ende,
            "value": e["wert"], "unit": "KRW", "accounting_standard": "IFRS", "consolidation": "group",
            "dimensions": {}, "source_id": source_id, "source_fact_key": f"{e['concept']}|KRW|{start or ''}|{ende}|{e['rcept_no']}",
            "mapping_version": MAPPING_VERSION, "quality": "raw",
            "reported_at": date(int(e["rcept_no"][:4]), int(e["rcept_no"][4:6]), int(e["rcept_no"][6:8])),
            "provenance": {"rcept_no": e["rcept_no"], "konto": e["konto_original"], "konto_vereinheitlicht": e["concept"], "kontoname": e["name"], "rechnung": e["satz"], "spalte": e["periode_text"],
                           "berichtsart": "Jahresbericht (11011)", "abschluss": "Konzern (CFS), K-IFRS", "originalwert": str(e["wert"]), "skalierung": 1},
        })
    return zeilen


def importieren(conn, rohdatei, sha256, url, entity_id, corp_code, stock_code, bank=False, dry_run=False):
    roh = json.loads(open(rohdatei, "rb").read())
    metrics = set(MAPPING) - (OHNE_BANK if bank else set())
    eintraege = extrahieren(roh, metrics=metrics)
    if not eintraege:
        return 0, 0
    rcept = {e["rcept_no"] for e in eintraege}
    if len(rcept) != 1:
        raise ValueError(f"Mehrere Berichtsnummern in einer Antwort: {sorted(rcept)}")
    neu = alt = 0
    with ingest.ingestion_lauf(conn, "dart-opendart", dry_run=dry_run) as lauf:
        conn.execute("INSERT INTO international.identifier (scheme, value, entity_id) VALUES ('DART_CORP_CODE', %s, %s) ON CONFLICT DO NOTHING", (corp_code, entity_id))
        conn.execute("INSERT INTO international.identifier (scheme, value, entity_id) VALUES ('KRX_CODE', %s, %s) ON CONFLICT DO NOTHING", (stock_code, entity_id))
        sid = ingest.quelle_registrieren(conn, ANBIETER, rcept.copy().pop(), url, sha256, str(rohdatei), rights_status="unverified")
        for z in normalisieren(eintraege, entity_id, sid):
            if ingest.fakt_einfuegen(conn, z):
                neu += 1
            else:
                alt += 1
        lauf.anzahl = neu
        lauf.wasserzeichen = {"corp_code": corp_code, "rcept_no": next(iter(rcept)), "sha256": sha256}
    return neu, alt
