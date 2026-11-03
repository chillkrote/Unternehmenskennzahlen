"""Gleicht die importierten DART-Werte mit dem Berichtstext ab (document.xml der Einreichung, unabhängig von der Konten-API).

Je Unternehmen und Kennzahl wird die jüngste Periode geprüft: Im Bericht muss eine Tabellenzeile stehen, deren Bezeichnung dem Kontonamen entspricht
und die den Betrag in Won, Tausend Won oder Millionen Won (Einheit des Berichts, ganzzahlig) enthält. Nur 'gleich' zählt als bestätigt.
Aufruf: DART_API=… INTERNATIONAL_DATABASE_URL=… python3 international/verify_kr.py   ->  pruefung_kr.csv
"""
import csv
import re
import sys
import zipfile
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
import dart  # noqa: E402
import db  # noqa: E402
from httpsafe import AbrufFehler  # noqa: E402

EINHEITEN = (("Won", Decimal(1)), ("Tsd. Won", Decimal(1000)), ("Mio. Won", Decimal(10 ** 6)))


def bericht_text(client, rcept_no):
    daten, _ = client.holen("document.xml", rcept_no=rcept_no)
    try:
        z = zipfile.ZipFile(BytesIO(daten))
    except zipfile.BadZipFile as e:
        raise AbrufFehler(f"document.xml {rcept_no} ist keine ZIP-Datei") from e
    return "\n".join(z.read(n).decode("utf-8", "replace") for n in z.namelist() if n.endswith(".xml"))


def frühere_fassungen(client, corp_code, rcept_no):
    """Andere Jahresberichte (Berichtigungen/Original) desselben Geschäftsjahres, jüngste zuerst; Berichtsjahr = Jahr vor dem Einreichungsjahr."""
    jahr = int(rcept_no[:4])
    daten, _ = client.holen("list.json", corp_code=corp_code, bgn_de=f"{jahr}0101", end_de=f"{jahr}1231", pblntf_detail_ty="A001")
    j = dart.json_pruefen(daten, erlaubt=("000", "013"))
    return [x["rcept_no"] for x in sorted(j.get("list", []), key=lambda x: x["rcept_no"], reverse=True) if x["rcept_no"] != rcept_no]


def zeilen(text):
    """Tabellenzeilen als Listen bereinigter Zellentexte."""
    for tr in re.findall(r"<TR\b.*?</TR>", text, re.S | re.I):
        zellen = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).replace("&amp;", "&").strip()
                  for c in re.findall(r"<T[DEH]\b.*?</T[DEH]>", tr, re.S | re.I)]
        if zellen:
            yield zellen


def label(s):
    s = re.sub(r"\(주[\d,\s]*\)", "", s)           # Verweis auf Anhangsangabe "(주35)"
    return re.sub(r"[\s().,·ㆍ\-\[\]0-9]|^[ⅠⅡⅢⅣⅤⅥIVX]+\.", "", s)


def formen(wert):
    """(Einheit, Zahlentext) für die Einheiten, in denen der Betrag ganzzahlig darstellbar ist."""
    for name, f in EINHEITEN:
        q = wert / f
        if q == q.to_integral_value():
            q = int(q)
            yield name, (f"{q:,}" if q >= 0 else f"({abs(q):,})"), f"{q:,}"


def pruefen(tabellenzeilen, kontoname, wert):
    ziel = label(kontoname)
    for z in tabellenzeilen:
        if label(z[0]) != ziel:
            continue
        for einheit, text, text2 in formen(wert):
            if any(c.replace(" ", "") in (text, text2, "△" + text2.lstrip("-"), "-" + text2.lstrip("-")) for c in z[1:]):
                return "gleich", z[0], einheit, text2
    return "nicht_gefunden", "", "", ""


def main():
    client = dart.DartClient()
    ausgabe = []
    with db.verbinden() as conn:
        paare = conn.execute(
            "SELECT DISTINCT ON (f.entity_id, f.metric_code) f.entity_id, e.legal_name, f.metric_code, f.period_start, f.period_end, f.value, "
            "f.provenance->>'rcept_no', f.provenance->>'konto', f.provenance->>'kontoname' "
            "FROM international.fact f JOIN international.entity e ON e.id=f.entity_id JOIN international.source_document s ON s.id=f.source_id "
            "WHERE s.provider=%s ORDER BY f.entity_id, f.metric_code, f.period_end DESC, f.reported_at DESC", (dart.ANBIETER,)).fetchall()
    cache, corp = {}, {}
    with db.verbinden() as conn:
        corp = dict(conn.execute("SELECT entity_id, value FROM international.identifier WHERE scheme='DART_CORP_CODE'").fetchall())

    def lade(r):
        if r not in cache:
            try:
                cache[r] = list(zeilen(bericht_text(client, r)))
            except AbrufFehler:
                cache[r] = None
        return cache[r]

    for uid, name, metric, start, ende, wert, rcept, konto, kontoname in paare:
        quelle, text_zeilen = rcept, lade(rcept)
        if text_zeilen is None:       # Dokument der berichtigten Fassung nicht abrufbar: andere Fassungen desselben Jahres versuchen
            for r in frühere_fassungen(client, corp[uid], rcept):
                if lade(r) is not None:
                    quelle, text_zeilen = r, cache[r]
                    break
        if text_zeilen is None:
            status, zeile, einheit, text = "dokument_nicht_abrufbar", "", "", ""
        else:
            status, zeile, einheit, text = pruefen(text_zeilen, kontoname, wert)
            if status == "gleich" and quelle != rcept:
                status = "gleich_in_anderer_fassung"       # Wert steht in der Original-/früheren Fassung; berichtigte Fassung selbst nicht abrufbar
        ausgabe.append([uid, name, metric, konto, f"{start or ''}..{ende}", f"{wert:f}", text.replace(",", "") + (" × Einheit " + einheit if einheit else ""),
                        quelle, zeile, status, date.today().isoformat()])
        print(uid, metric, ende, status)
    with open(HIER / "pruefung_kr.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["unternehmen_id", "name", "kennzahl", "dart_konto", "periode", "wert_datenbank_krw", "wert_bericht", "rcept_no", "zeile_im_bericht", "status", "geprueft_am"])
        w.writerows(ausgabe)


if __name__ == "__main__":
    main()
