#!/usr/bin/env python3
"""Liest die ausgefüllte Governance-Importvorlage, prüft sie und übernimmt sie (optional) in die Governance-Daten.

Aufruf aus dem Repo-Root:
  python3 governance/vorlage/importieren.py Datei.xlsx                    nur prüfen, Bericht ausgeben (ändert nichts)
  python3 governance/vorlage/importieren.py Datei.xlsx --bericht pb.md    Prüfbericht zusätzlich als Markdown speichern
  python3 governance/vorlage/importieren.py Datei.xlsx --schreiben        nur ohne Fehler: governance/handeingabe/<Datei>.json
                                                                          anlegen und governance/skripte/build.py ausführen
Exit-Code 1 bei Fehlern (dann wird nichts geschrieben).

Prüfungen: Pflichtfelder, Listenwerte, Unternehmens-ID gegen stammdaten/, Geschäftsjahr, Datumsformate, Seitenangaben,
Quellen (https-Link oder Repo-Pfad, Registereintrag), Personenbezug (Name muss im Blatt Gremienmitglieder oder in personen.csv
stehen, ähnliche Schreibweisen werden gemeldet), doppelte Zeilen in der Datei und gegen den Bestand, Zählwerte (Frauen <= Mitglieder,
Gewerkschaft <= Arbeitnehmer, Abgleich mit erfassten Namen), Summenzeilen Vergütung gegen Einzelwerte, Pay-Ratio-Eingangsdaten.
"""
import argparse
import csv
import datetime as dt
import difflib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HIER = Path(__file__).resolve().parent
REPO = HIER.parent.parent
GOV = REPO / "governance"
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(GOV / "skripte"))
sys.path.insert(0, str(REPO / "stammdaten"))
import schema as S  # noqa: E402

try:
    import ids as IDS  # noqa: E402
    import lib  # noqa: E402  (slug)
    slug = lib.slug
except Exception as e:  # pragma: no cover
    raise SystemExit(f"Repo-Module nicht ladbar: {e}")

AUSGABE = GOV / "handeingabe"
SUMMEN_PRAEFIX = ("Gesamt", "Barwert", "Zahlungen")
GJ_MIN, GJ_MAX = 2000, 2100
SEITE_RE = re.compile(r"^\d{1,4}([-–]\d{1,4})?(\s*,\s*\d{1,4}([-–]\d{1,4})?)*$")
ID_RE = re.compile(r"^U\d{6}$")


TOLERANT = False  # --tolerant: unverifizierte Seiten / Fremdwährungsbeträge zulassen (siehe README)
TOLERANT_WARNUNG = ("Doppelte Zeile in der Datei", "doppelt im Register", "steht bereits in", "mehrfach (auch im Blatt", "mehrere berichtete Pay Ratios",
                    "unbekannt: weder", "nicht in der Liste.", "Seite fehlt")


class Bericht:
    def __init__(self):
        self.fehler, self.warnungen, self.info = [], [], []

    def f(self, ort, text):
        if TOLERANT and any(t in text for t in TOLERANT_WARNUNG):
            self.warnungen.append(f"{ort}: (toleriert, Zeile übersprungen oder ungeprüft) {text}")
            return
        self.fehler.append(f"{ort}: {text}")

    def w(self, ort, text):
        self.warnungen.append(f"{ort}: {text}")


# ---------------------------------------------------------------- Werte lesen
def zahl(v):
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(" ", "").replace(" ", "")
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", s):
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d+,\d+", s):
        s = s.replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", s):
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def text(v):
    if v is None:
        return ""
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v).strip()


def datum(v):
    """Excel-Datum oder Text TT.MM.JJJJ / JJJJ-MM-TT -> date oder None."""
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    s = text(v)
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def teil_datum(v):
    """Für seit/bis: date -> ISO, sonst JJJJ-MM-TT, JJJJ-MM oder JJJJ als Text. Gibt (iso, ok) zurück."""
    if v is None or v == "":
        return "", True
    d = datum(v)
    if d:
        return d.isoformat(), True
    s = text(v)
    if re.fullmatch(r"\d{4}(-\d{2})?", s):
        return s, True
    return s, False


def ganzzahl(v):
    z = zahl(v)
    if z is None or z != int(z):
        return None
    return int(z)


def fmt_zahl(z):
    if z is None:
        return ""
    return str(int(z)) if float(z).is_integer() else repr(round(z, 6))


# ---------------------------------------------------------------- Excel einlesen
def lese(pfad):
    from openpyxl import load_workbook
    wb = load_workbook(pfad, data_only=True)
    out, fehler = {}, []
    for blatt, spalten in S.BLAETTER.items():
        if blatt not in wb.sheetnames:
            fehler.append(f"Blatt '{blatt}' fehlt.")
            continue
        ws = wb[blatt]
        kopf = [str(c.value or "").replace(" *", "").strip() for c in ws[1]]
        erwartet = [s[0] for s in spalten]
        if kopf[:len(erwartet)] != erwartet:
            fehler.append(f"Blatt '{blatt}': Spaltenköpfe weichen von der Vorlage ab (erwartet: {erwartet}).")
            continue
        zeilen = []
        for r, row in enumerate(ws.iter_rows(min_row=2, max_col=len(erwartet), values_only=True), 2):
            d = dict(zip(erwartet, row))
            for s in spalten:
                if s[0].endswith("(automatisch)"):
                    d.pop(s[0], None)
            if all(v is None or str(v).strip() == "" for v in d.values()):
                continue
            if any(isinstance(v, str) and v.strip().startswith(S.BEISPIEL) for v in d.values()):
                continue
            d["_ort"] = f"{blatt} Zeile {r}"
            zeilen.append(d)
        out[blatt] = zeilen
    return out, fehler


# ---------------------------------------------------------------- Bestand
def lade_csv(name):
    p = GOV / name
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


K_MIT = ("unternehmen_id", "gj", "organ", "person_id")


class Bestand:
    def __init__(self, ausnahme_json=None):
        self.reg = IDS.lade()
        self.personen = {r["person_id"]: r["name"] for r in lade_csv("personen.csv")}
        self.mitglieder = lade_csv("gremien_mitglieder.csv")
        self.verg = lade_csv("verguetung.csv")
        self.kenn = lade_csv("kennzahlen_gremien.csv")
        self.mandate = lade_csv("mandate_extern.csv")
        self.werdegang = lade_csv("werdegang.csv")
        self.gesch = lade_csv("berechnungen/geschlecht_belege.csv")
        # erneuter Import derselben Datei ersetzt die eigenen früheren Zeilen (sie zählen nicht als Bestand)
        if ausnahme_json and Path(ausnahme_json).exists():
            alt = json.load(open(ausnahme_json, encoding="utf-8"))
            for attr, key, cols in (("mitglieder", "mitglieder", K_MIT), ("verg", "verguetung", ("unternehmen_id", "gj", "gremium", "name", "art")),
                                    ("kenn", "kennzahlen", ("unternehmen_id", "gj", "feld")),
                                    ("mandate", "mandate", ("person_id", "gesellschaft", "ueber_unternehmen_id", "gj", "funktion")),
                                    ("werdegang", "werdegang", ("person_id", "station", "zeitraum"))):
                eigene = {tuple(str(r.get(c, "")) for c in cols) for r in alt.get(key, [])}
                setattr(self, attr, [r for r in getattr(self, attr) if tuple(str(r.get(c, "")) for c in cols) not in eigene])
            eigene_g = {(r["unternehmen_id"], slug(r["name"])) for r in alt.get("geschlecht", [])}
            self.gesch = [r for r in self.gesch if (r["unternehmen_id"], slug(r["name"])) not in eigene_g]
            neu = {r["person_id"] for r in alt.get("mitglieder", [])} | {r["person_id"] for r in alt.get("mandate", [])}
            rest = {r["person_id"] for r in self.mitglieder + self.mandate}
            for pid in neu - rest:
                self.personen.pop(pid, None)




def schluessel_mit(r):
    return (r["unternehmen_id"], str(r["gj"]), r["organ"], r["person_id"])


# ---------------------------------------------------------------- Prüfen
def pflicht(b, ort, d, namen):
    ok = True
    for n in namen:
        if TOLERANT and n in ("Seite", "Betrag (TEUR)"):
            continue
        if d.get(n) is None or str(d.get(n)).strip() == "":
            b.f(ort, f"Pflichtfeld '{n}' ist leer.")
            ok = False
    return ok


def pruefe_id(b, ort, uid, bestand, feld="Unternehmens-ID"):
    uid = text(uid)
    if not ID_RE.match(uid):
        b.f(ort, f"{feld} '{uid}' hat nicht das Format U000123.")
        return ""
    if uid not in bestand.reg.unternehmen:
        b.f(ort, f"{feld} '{uid}' steht nicht in stammdaten/unternehmen_ids.csv. Unternehmen zuerst über die Unternehmens-Importvorlage registrieren.")
        return ""
    return uid


def pruefe_gj(b, ort, v):
    g = ganzzahl(v)
    if g is None or not GJ_MIN <= g <= GJ_MAX:
        b.f(ort, f"Geschäftsjahr '{text(v)}' ist keine vierstellige Jahreszahl.")
        return None
    return g


class Quellenpruefung:
    def __init__(self, b, registrierte_urls):
        self.b, self.reg, self.benutzt = b, registrierte_urls, set()

    def __call__(self, ort, quelle, seite, seite_pflicht=True):
        q, s = text(quelle), text(seite)
        if not q:
            return "", ""
        if not (q.startswith("https://") or q.startswith("http://") or q.startswith("governance/dokumente/")):
            self.b.f(ort, f"Quelle '{q[:60]}' ist weder https-Link noch Pfad governance/dokumente/...")
        elif q.startswith("governance/dokumente/") and not (REPO / q).exists():
            self.b.w(ort, f"Datei '{q}' liegt (noch) nicht im Repo. Dokument mit dem Import zusammen ablegen.")
        elif q.startswith("http"):
            self.benutzt.add(q)
        if seite_pflicht and not s and not TOLERANT:
            self.b.f(ort, "Seite fehlt (PDF-Seite der Fundstelle).")
        elif s and not SEITE_RE.match(s.replace(".0", "")):
            self.b.f(ort, f"Seite '{s}' ungültig (Zahl, Bereich 12-13 oder Liste 12, 14).")
        return q, s


def bem_mit_stand(b, ort, bem, stand):
    bem = text(bem)
    if stand is None or stand == "":
        return bem
    d = datum(stand)
    if not d and TOLERANT:
        zusatz = f"Stand: {text(stand)}"
        return f"{bem}; {zusatz}" if bem else zusatz
    if not d:
        b.f(ort, f"Stand '{text(stand)}' ist kein Datum (TT.MM.JJJJ).")
        return bem
    zusatz = f"Stand: {d.strftime('%d.%m.%Y')}"
    return f"{bem}; {zusatz}" if bem else zusatz


def pruefe(daten, bestand, b):
    out = dict(mitglieder=[], verguetung=[], kennzahlen=[], mandate=[], werdegang=[], geschlecht=[], pay_ratio_eingang=[], dokumente=[])
    # --- Quellen-Dokumente (zuerst, für Registerabgleich)
    urls = set()
    for d in daten.get("Quellen-Dokumente", []):
        ort = d["_ort"]
        if not pflicht(b, ort, d, ["Unternehmens-ID", "Dokumentart", "Titel", "URL", "Abrufdatum"]):
            continue
        uid = pruefe_id(b, ort, d["Unternehmens-ID"], bestand)
        if text(d["Dokumentart"]) not in S.DOKUMENTARTEN:
            b.f(ort, f"Dokumentart '{text(d['Dokumentart'])}' nicht in der Liste.")
        if not datum(d["Abrufdatum"]):
            b.f(ort, "Abrufdatum ist kein Datum (TT.MM.JJJJ).")
        url = text(d["URL"])
        if not (url.startswith("http") or url.startswith("governance/dokumente/")):
            b.f(ort, f"URL '{url[:60]}' ungültig.")
        if url in urls:
            b.f(ort, f"Dokument '{url[:70]}' doppelt im Register.")
        urls.add(url)
        if uid:
            vd = datum(d.get("Veröffentlicht am"))
            out["dokumente"].append(dict(unternehmen_id=uid, dokumentart=text(d["Dokumentart"]), gj=ganzzahl(d.get("Geschäftsjahr")) or "", titel=text(d["Titel"]), url=url,
                                         abrufdatum=datum(d["Abrufdatum"]).isoformat() if datum(d["Abrufdatum"]) else "",
                                         veroeffentlicht=vd.isoformat() if vd else "", sprache=text(d.get("Sprache")), hinweis=text(d.get("Hinweis"))))
    quelle = Quellenpruefung(b, urls)

    # --- Gremienmitglieder
    neue_personen = {}
    gesehen = set()
    for d in daten.get("Gremienmitglieder", []):
        ort = d["_ort"]
        if not pflicht(b, ort, d, ["Unternehmens-ID", "Geschäftsjahr", "Organ", "Name", "Quelle", "Seite"]):
            continue
        uid = pruefe_id(b, ort, d["Unternehmens-ID"], bestand)
        gj = pruefe_gj(b, ort, d["Geschäftsjahr"])
        organ = text(d["Organ"])
        if organ not in S.ORGANE:
            b.f(ort, f"Organ '{organ}' nicht in der Liste {S.ORGANE}.")
        va = text(d.get("Vertreterart"))
        if va and va not in S.VERTRETERART:
            b.f(ort, f"Vertreterart '{va}' nicht in der Liste {S.VERTRETERART}.")
        if va and organ not in ("Aufsichtsrat", "Verwaltungsrat", "Beirat", "Gesellschafterausschuss"):
            b.w(ort, f"Vertreterart bei Organ {organ} ungewöhnlich.")
        seit, ok1 = teil_datum(d.get("Mitglied seit"))
        bis, ok2 = teil_datum(d.get("Mitglied bis"))
        if not ok1:
            b.f(ort, f"Mitglied seit '{text(d.get('Mitglied seit'))}' ungültig (TT.MM.JJJJ, JJJJ-MM oder JJJJ).")
        if not ok2:
            b.f(ort, f"Mitglied bis '{text(d.get('Mitglied bis'))}' ungültig (TT.MM.JJJJ, JJJJ-MM oder JJJJ).")
        if ok1 and ok2 and seit and bis and seit > bis:
            b.f(ort, f"Mitglied seit ({seit}) liegt nach Mitglied bis ({bis}).")
        name = text(d["Name"])
        pid = slug(name)
        if not pid:
            b.f(ort, f"Name '{name}' ergibt keine Personen-ID.")
            continue
        q, s = quelle(ort, d["Quelle"], d["Seite"])
        row = dict(unternehmen_id=uid, gj=gj, organ=organ, person_id=pid, name=name, funktion=text(d.get("Funktion")) or "Mitglied",
                   vertreter_art=va, seit=seit, bis=bis, beruf_laut_dokument=text(d.get("Beruf laut Dokument")), quelle_dokument=q, seite=s,
                   bemerkung=bem_mit_stand(b, ort, d.get("Bemerkung"), d.get("Stand")))
        if not (uid and gj):
            continue
        k = schluessel_mit(row)
        if k in gesehen:
            b.f(ort, f"Doppelte Zeile in der Datei: {uid}, GJ {gj}, {organ}, {name}.")
            continue
        gesehen.add(k)
        if any(schluessel_mit(r) == k for r in bestand.mitglieder):
            b.f(ort, f"{name} ({organ}, {uid}, GJ {gj}) steht bereits im Bestand governance/gremien_mitglieder.csv.")
            continue
        out["mitglieder"].append(row)
        if pid not in bestand.personen:
            bisher = neue_personen.get(pid)
            if bisher and bisher != name:
                b.w(ort, f"Person '{name}' und '{bisher}' ergeben dieselbe Personen-ID '{pid}'; gleiche Person?")
            neue_personen.setdefault(pid, name)
    alle_personen = dict(bestand.personen)
    alle_personen.update(neue_personen)
    for pid, name in neue_personen.items():
        nah = difflib.get_close_matches(pid, [p for p in bestand.personen], n=1, cutoff=0.92)
        if nah:
            b.w("Gremienmitglieder", f"Neue Person '{name}' (ID {pid}) ähnelt der bestehenden '{bestand.personen[nah[0]]}' (ID {nah[0]}). Schreibweise prüfen, sonst entstehen Dubletten.")

    def person(ort, name):
        pid = slug(text(name))
        if pid not in alle_personen:
            nah = difflib.get_close_matches(pid, list(alle_personen), n=1, cutoff=0.8)
            hint = f" Meinten Sie '{alle_personen[nah[0]]}'?" if nah else ""
            b.f(ort, f"Person '{text(name)}' unbekannt: weder im Blatt Gremienmitglieder noch in personen.csv.{hint}")
            return None
        return pid

    # --- Vergütung
    gesehen = set()
    summen, einzel = {}, defaultdict(float)
    mit_organ = {(r["unternehmen_id"], str(r["gj"]), r["organ"], r["person_id"]) for r in bestand.mitglieder + out["mitglieder"]}
    for d in daten.get("Vergütung", []):
        ort = d["_ort"]
        if not pflicht(b, ort, d, ["Unternehmens-ID", "Geschäftsjahr", "Gremium", "Name", "Betrag (TEUR)", "Art", "Quelle", "Seite"]):
            continue
        uid = pruefe_id(b, ort, d["Unternehmens-ID"], bestand)
        gj = pruefe_gj(b, ort, d["Geschäftsjahr"])
        grem = text(d["Gremium"])
        if grem not in S.GREMIEN_VERG:
            b.f(ort, f"Gremium '{grem}' nicht in der Liste.")
        betrag = zahl(d["Betrag (TEUR)"])
        if TOLERANT and betrag is None and text(d["Betrag (TEUR)"]) == "" and text(d.get("Bemerkung")):
            betrag = None  # Fremdwährung: Originalbetrag steht in der Bemerkung, keine Umrechnung
        elif betrag is None or betrag < 0:
            b.f(ort, f"Betrag '{text(d['Betrag (TEUR)'])}' ist keine Zahl >= 0 (T€).")
            continue
        if betrag is not None and betrag > 100000:
            b.w(ort, f"Betrag {betrag:,.0f} T€ ist ungewöhnlich hoch (über 100 Mio. €). Einheit T€ richtig?")
        name = text(d["Name"])
        summe = name.startswith(SUMMEN_PRAEFIX)
        pid = "" if summe else person(ort, name)
        if not summe and pid is None:
            continue
        if not summe and uid and gj and (uid, str(gj), grem, pid) not in mit_organ:
            b.w(ort, f"{name} ist für {uid}/GJ {gj} nicht als Mitglied im Organ {grem} erfasst (Blatt Gremienmitglieder).")
        q, s = quelle(ort, d["Quelle"], d["Seite"])
        row = dict(unternehmen_id=uid, gj=gj, gremium=grem, person_id=pid, name=name, betrag_tsd_eur=fmt_zahl(betrag) if betrag is not None else "", art=text(d["Art"]),
                   quelle_dokument=q, seite=s, bemerkung=bem_mit_stand(b, ort, d.get("Bemerkung"), d.get("Stand")))
        if not (uid and gj):
            continue
        k = (uid, str(gj), grem, name, row["art"])
        if k in gesehen:
            b.f(ort, f"Doppelte Zeile in der Datei: {uid}, GJ {gj}, {grem}, {name}, {row['art'][:40]}.")
            continue
        gesehen.add(k)
        if any((r["unternehmen_id"], str(r["gj"]), r["gremium"], r["name"], r["art"]) == k for r in bestand.verg):
            b.f(ort, f"{name} ({grem}, {uid}, GJ {gj}) mit dieser Art steht bereits in governance/verguetung.csv.")
            continue
        out["verguetung"].append(row)
        if betrag is None:
            continue
        if summe and name.startswith("Gesamt"):
            summen[(uid, str(gj), grem)] = (betrag, ort)
        elif not summe:
            einzel[(uid, str(gj), grem)] += betrag
    for k, (soll, ort) in summen.items():
        if k in einzel and soll > 0 and abs(einzel[k] - soll) / soll > 0.01:
            b.w(ort, f"Summenzeile {soll:,.1f} T€ weicht von der Summe der Einzelwerte in der Datei ({einzel[k]:,.1f} T€) um mehr als 1 % ab (evtl. ausgeschiedene Mitglieder oder Nebenleistungen).")

    # --- Geschlecht
    gesehen = set()
    for d in daten.get("Geschlecht (Belege)", []):
        ort = d["_ort"]
        if not pflicht(b, ort, d, ["Name", "Unternehmens-ID", "Geschlecht", "Beleg", "Quelle", "Seite"]):
            continue
        uid = pruefe_id(b, ort, d["Unternehmens-ID"], bestand)
        pid = person(ort, d["Name"])
        g = text(d["Geschlecht"])
        if g not in S.GESCHLECHT:
            b.f(ort, f"Geschlecht '{g}' nicht in der Liste {S.GESCHLECHT}.")
        beleg = text(d["Beleg"])
        if len(beleg) < 8 or re.search(r"vorname|first name|name klingt|anhand des namens", beleg, re.I):
            b.f(ort, "Beleg fehlt oder leitet das Geschlecht aus dem Namen ab; nur dokumentierte Angaben zulässig.")
        q, s = quelle(ort, d["Quelle"], d["Seite"])
        if not (uid and pid):
            continue
        if (uid, pid) in gesehen:
            b.f(ort, f"Doppelte Zeile in der Datei: {text(d['Name'])}, {uid}.")
            continue
        gesehen.add((uid, pid))
        if any(slug(r["name"]) == pid and r["unternehmen_id"] == uid for r in bestand.gesch):
            b.f(ort, f"Geschlechtsbeleg für {text(d['Name'])} ({uid}) steht bereits in berechnungen/geschlecht_belege.csv.")
            continue
        out["geschlecht"].append(dict(name=text(d["Name"]), unternehmen_id=uid, geschlecht=g, quelle_dokument=q, seite=s, beleg=beleg))

    # --- Kennzahlen Gremien
    gesehen = set()
    kz = {}
    for d in daten.get("Kennzahlen Gremien", []):
        ort = d["_ort"]
        if not pflicht(b, ort, d, ["Unternehmens-ID", "Geschäftsjahr", "Feld", "Wert", "Quelle", "Seite"]):
            continue
        uid = pruefe_id(b, ort, d["Unternehmens-ID"], bestand)
        gj = pruefe_gj(b, ort, d["Geschäftsjahr"])
        feld = text(d["Feld"])
        if feld not in S.FELD_NAMEN:
            b.f(ort, f"Feld '{feld}' nicht in der Feldliste.")
            continue
        einheit = text(d.get("Einheit")) or S.FELD_EINHEIT[feld]
        if S.FELD_TYP[feld] == "Zahl":
            z = zahl(d["Wert"])
            if z is None:
                b.f(ort, f"Wert '{text(d['Wert'])}' für {feld} ist keine Zahl.")
                continue
            if z < 0:
                b.f(ort, f"Wert für {feld} darf nicht negativ sein.")
                continue
            if feld.endswith("_zahl") and z != int(z):
                b.f(ort, f"Wert für {feld} muss eine ganze Zahl sein.")
                continue
            if feld.endswith("_pct") and z > 100:
                b.f(ort, f"Wert für {feld} ({z}) über 100 %.")
            wert = fmt_zahl(z)
        else:
            wert = text(d["Wert"])
            if feld == "mitbestimmung_ar" and wert not in S.MITBESTIMMUNG:
                b.f(ort, f"mitbestimmung_ar '{wert}' nicht in {S.MITBESTIMMUNG}.")
        q, s = quelle(ort, d["Quelle"], d["Seite"])
        if not (uid and gj):
            continue
        k = (uid, str(gj), feld)
        if k in gesehen:
            b.f(ort, f"Doppelte Zeile in der Datei: {uid}, GJ {gj}, {feld}.")
            continue
        gesehen.add(k)
        if any((r["unternehmen_id"], str(r["gj"]), r["feld"]) == k for r in bestand.kenn):
            b.f(ort, f"{feld} ({uid}, GJ {gj}) steht bereits in governance/kennzahlen_gremien.csv.")
            continue
        kz[k] = float(wert) if S.FELD_TYP[feld] == "Zahl" else wert
        out["kennzahlen"].append(dict(unternehmen_id=uid, gj=gj, feld=feld, wert=wert, einheit=einheit, quelle_dokument=q, seite=s,
                                      bemerkung=bem_mit_stand(b, ort, d.get("Bemerkung"), d.get("Stand"))))
    # Plausibilität der Zählwerte (neu + Bestand)
    bestand_kz = {(r["unternehmen_id"], str(r["gj"]), r["feld"]): r["wert"] for r in bestand.kenn}
    def kzw(uid, gj, feld):
        if (uid, gj, feld) in kz:
            return kz[(uid, gj, feld)]
        v = zahl(bestand_kz.get((uid, gj, feld)))
        return v
    for (uid, gj, feld) in list(kz):
        v = kz[(uid, gj, feld)]
        if not isinstance(v, float):
            continue
        for kleiner, groesser in (("vorstand_frauen_zahl", "vorstand_mitglieder_zahl"), ("ar_frauen_zahl", "ar_mitglieder_zahl"),
                                  ("geschaeftsfuehrung_frauen_zahl", "geschaeftsfuehrung_mitglieder_zahl"),
                                  ("ar_arbeitnehmervertreter_zahl", "ar_mitglieder_zahl"), ("ar_anteilseigner_zahl", "ar_mitglieder_zahl"),
                                  ("ar_gewerkschaftsvertreter_zahl", "ar_arbeitnehmervertreter_zahl"), ("ar_betriebsraete_zahl", "ar_arbeitnehmervertreter_zahl")):
            if feld == kleiner:
                g = kzw(uid, gj, groesser)
                if g is not None and v > g:
                    b.f("Kennzahlen Gremien", f"{uid} GJ {gj}: {kleiner} ({v:.0f}) größer als {groesser} ({g:.0f}).")
        if feld == "ar_mitglieder_zahl":
            a, n = kzw(uid, gj, "ar_arbeitnehmervertreter_zahl"), kzw(uid, gj, "ar_anteilseigner_zahl")
            if a is not None and n is not None and abs(a + n - v) > 0:
                b.w("Kennzahlen Gremien", f"{uid} GJ {gj}: Anteilseigner ({n:.0f}) + Arbeitnehmer ({a:.0f}) ergibt nicht ar_mitglieder_zahl ({v:.0f}).")
    # Abgleich mit erfassten Namen
    namen = defaultdict(set)
    for r in bestand.mitglieder + out["mitglieder"]:
        if str(r["bis"]) == "" or True:
            namen[(r["unternehmen_id"], str(r["gj"]), r["organ"])].add(r["person_id"])
    for (uid, gj, feld) in kz:
        organ = {"vorstand_mitglieder_zahl": "Vorstand", "ar_mitglieder_zahl": "Aufsichtsrat", "geschaeftsfuehrung_mitglieder_zahl": "Geschäftsführung"}.get(feld)
        if organ and (uid, gj, organ) in namen and abs(len(namen[(uid, gj, organ)]) - kz[(uid, gj, feld)]) > 0:
            b.w("Kennzahlen Gremien", f"{uid} GJ {gj}: {feld}={kz[(uid, gj, feld)]:.0f}, erfasst sind {len(namen[(uid, gj, organ)])} Namen (Ausgeschiedene/Ersatzmitglieder enthalten?).")

    # --- Pay Ratio
    gesehen = set()
    berichtet = defaultdict(list)
    for d in daten.get("Pay Ratio", []):
        ort = d["_ort"]
        if not pflicht(b, ort, d, ["Unternehmens-ID", "Geschäftsjahr", "Variante", "Beschäftigtenkreis / Basis", "Quelle", "Seite"]):
            continue
        uid = pruefe_id(b, ort, d["Unternehmens-ID"], bestand)
        gj = pruefe_gj(b, ort, d["Geschäftsjahr"])
        var = text(d["Variante"])
        bezug = text(d.get("Bezug"))
        if var not in S.VARIANTEN:
            b.f(ort, f"Variante '{var}' nicht in {S.VARIANTEN}.")
            continue
        basis = text(d["Beschäftigtenkreis / Basis"])
        if TOLERANT and isinstance(d.get("Pay Ratio (berichtet)"), str) and re.fullmatch(r"\s*[\d.,]+\s*:\s*1\s*", d["Pay Ratio (berichtet)"]):
            d["Pay Ratio (berichtet)"] = d["Pay Ratio (berichtet)"].split(":")[0].strip()  # "69:1" -> 69
        pr, av = zahl(d.get("Pay Ratio (berichtet)")), zahl(d.get("Ø-Vergütung Beschäftigte (TEUR)"))
        pa, bn = zahl(d.get("Personalaufwand Konzern (Mio. EUR)")), zahl(d.get("Beschäftigte (Anzahl)"))
        for n, v in (("Pay Ratio (berichtet)", d.get("Pay Ratio (berichtet)")), ("Ø-Vergütung Beschäftigte (TEUR)", d.get("Ø-Vergütung Beschäftigte (TEUR)")),
                     ("Personalaufwand Konzern (Mio. EUR)", d.get("Personalaufwand Konzern (Mio. EUR)")), ("Beschäftigte (Anzahl)", d.get("Beschäftigte (Anzahl)"))):
            if v not in (None, "") and zahl(v) is None:
                b.f(ort, f"{n}: '{text(v)}' ist keine Zahl.")
        if var == "A":
            if av is None or av <= 0:
                b.f(ort, "Variante A braucht 'Ø-Vergütung Beschäftigte (TEUR)' > 0.")
                continue
            if av > 1000 or av < 5:
                b.w(ort, f"Ø-Vergütung {av:,.1f} T€ ist ungewöhnlich (T€ je Beschäftigtem/Jahr erwartet).")
            if pr or pa or bn:
                b.w(ort, "Variante A: Felder der Varianten B/Bericht werden ignoriert.")
        elif var == "B":
            if not pa or not bn or pa <= 0 or bn <= 0:
                b.f(ort, "Variante B braucht Personalaufwand Konzern (Mio. EUR) und Beschäftigte (Anzahl), beide > 0.")
                continue
            je = pa * 1000 / bn
            if je < 10 or je > 500:
                b.w(ort, f"Personalaufwand je Beschäftigtem {je:,.0f} T€ unplausibel (Einheiten prüfen: Mio. €, Anzahl).")
            if av or pr:
                b.w(ort, "Variante B: Felder der Varianten A/Bericht werden ignoriert.")
        else:
            if pr is None or pr < 0 or (pr == 0 and not TOLERANT):
                b.f(ort, "Variante Bericht braucht die berichtete Pay Ratio > 0.")
                continue
            if pr > 2000:
                b.w(ort, f"Berichtete Pay Ratio {pr:,.1f} ist ungewöhnlich hoch.")
            if not bezug:
                b.f(ort, "Variante Bericht braucht den Bezug (worauf sich die Quote bezieht).")
        q, s = quelle(ort, d["Quelle"], d["Seite"])
        if not (uid and gj):
            continue
        k = (uid, str(gj), var, bezug)
        if k in gesehen:
            b.f(ort, f"Doppelte Zeile in der Datei: {uid}, GJ {gj}, Variante {var}, Bezug {bezug}.")
            continue
        gesehen.add(k)
        bem = bem_mit_stand(b, ort, d.get("Bemerkung"), d.get("Stand"))
        pre = f"Variante {var}; {basis}" + (f"; Bezug: {bezug}" if bezug else "")
        out["pay_ratio_eingang"].append(dict(unternehmen_id=uid, gj=gj, variante=var, bezug=bezug, pay_ratio=pr if var == "Bericht" else None,
                                             durchschnittsverguetung_teur=av if var == "A" else None, personalaufwand_mio=pa if var == "B" else None,
                                             beschaeftigte=bn if var == "B" else None, basis=basis, quelle_dokument=q, seite=s, bemerkung=bem))
        rows = []
        if var == "Bericht":
            rows.append(("pay_ratio", fmt_zahl(pr), "Verhältnis"))
            berichtet[(uid, gj)].append(ort)
        elif var == "A":
            rows.append(("durchschnittsverguetung_beschaeftigte_teur", fmt_zahl(av), "T€"))
        else:
            rows += [("personalaufwand_konzern_mio_eur", fmt_zahl(pa), "Mio. €"), ("beschaeftigte_konzern_zahl", fmt_zahl(bn), "Personen")]
        for feld, wert, einh in rows:
            k2 = (uid, str(gj), feld)
            if any((r["unternehmen_id"], str(r["gj"]), r["feld"]) == k2 for r in bestand.kenn):
                b.f(ort, f"{feld} ({uid}, GJ {gj}) steht bereits in governance/kennzahlen_gremien.csv.")
                continue
            if any((r["unternehmen_id"], str(r["gj"]), r["feld"]) == k2 for r in out["kennzahlen"]):
                b.f(ort, f"{feld} ({uid}, GJ {gj}) mehrfach (auch im Blatt Kennzahlen Gremien oder weiterer Pay-Ratio-Zeile).")
                continue
            out["kennzahlen"].append(dict(unternehmen_id=uid, gj=gj, feld=feld, wert=wert, einheit=einh, quelle_dokument=q, seite=s,
                                          bemerkung=f"{pre}; {bem}" if bem else pre))
    for (uid, gj), orte in berichtet.items():
        if len(orte) > 1:
            b.f(orte[1], f"{uid} GJ {gj}: mehrere berichtete Pay Ratios; nur ein Wert je Unternehmen/Jahr, weitere in die Bemerkung.")

    # --- Mandate extern
    gesehen = set()
    for d in daten.get("Mandate extern", []):
        ort = d["_ort"]
        if not pflicht(b, ort, d, ["Name", "Typ", "Gesellschaft", "Gemeldet von (Unternehmens-ID)", "Geschäftsjahr", "Quelle", "Seite"]):
            continue
        pid = person(ort, d["Name"])
        typ = text(d["Typ"]).lower()
        if typ not in S.MANDAT_TYP:
            b.f(ort, "Typ muss a oder b sein.")
        uid = pruefe_id(b, ort, d["Gemeldet von (Unternehmens-ID)"], bestand, "Gemeldet-von-ID")
        gid = ""
        if text(d.get("Gesellschaft-ID")):
            gid = pruefe_id(b, ort, d["Gesellschaft-ID"], bestand, "Gesellschaft-ID")
        gj = pruefe_gj(b, ort, d["Geschäftsjahr"])
        q, s = quelle(ort, d["Quelle"], d["Seite"])
        if not (pid and uid and gj):
            continue
        row = dict(person_id=pid, name=text(d["Name"]), typ=typ, gesellschaft=text(d["Gesellschaft"]), gesellschaft_unternehmen_id=gid, sitz=text(d.get("Sitz")),
                   funktion=text(d.get("Funktion")), gueltig=text(d.get("Gültig")), ueber_unternehmen_id=uid, gj=gj, quelle_dokument=q, seite=s, bemerkung=text(d.get("Bemerkung")))
        k = (pid, row["gesellschaft"], uid, str(gj), row["funktion"])
        if k in gesehen:
            b.f(ort, f"Doppelte Zeile in der Datei: {row['name']}, {row['gesellschaft']}.")
            continue
        gesehen.add(k)
        if any((r["person_id"], r["gesellschaft"], r["ueber_unternehmen_id"], str(r["gj"]), r["funktion"]) == k for r in bestand.mandate):
            b.f(ort, f"Mandat {row['name']} bei {row['gesellschaft']} ({uid}, GJ {gj}) steht bereits in mandate_extern.csv.")
            continue
        out["mandate"].append(row)

    # --- Werdegang
    gesehen = set()
    for d in daten.get("Werdegang", []):
        ort = d["_ort"]
        if not pflicht(b, ort, d, ["Name", "Station", "Quelle", "Seite"]):
            continue
        pid = person(ort, d["Name"])
        q, s = quelle(ort, d["Quelle"], d["Seite"])
        if not pid:
            continue
        row = dict(person_id=pid, name=text(d["Name"]), station=text(d["Station"]), organisation=text(d.get("Organisation")), zeitraum=text(d.get("Zeitraum")) or "lt. Dokument",
                   art=text(d.get("Art")), quelle_dokument=q, seite=s)
        k = (pid, row["station"], row["zeitraum"])
        if k in gesehen:
            b.f(ort, f"Doppelte Zeile in der Datei: {row['name']}: {row['station'][:40]}.")
            continue
        gesehen.add(k)
        if any((r["person_id"], r["station"], r["zeitraum"]) == k for r in bestand.werdegang):
            b.f(ort, f"Station '{row['station'][:40]}' von {row['name']} steht bereits in werdegang.csv.")
            continue
        out["werdegang"].append(row)

    # --- Quellenregister
    for q in sorted(quelle.benutzt - urls):
        b.w("Quellen-Dokumente", f"Link '{q[:80]}' wird als Quelle benutzt, steht aber nicht im Blatt Quellen-Dokumente.")
    b.info.append("Neue Personen: %d" % len(neue_personen))
    return out


# ---------------------------------------------------------------- Ausgabe
def bericht_text(datei, b, out):
    z = [f"# Prüfbericht Governance-Import: {Path(datei).name}", ""]
    zahlen = {k: len(v) for k, v in out.items()}
    z.append("Gelesen und fehlerfrei übernehmbar: " + ", ".join(f"{k}={v}" for k, v in zahlen.items()))
    z += [""] + [f"- {i}" for i in b.info]
    z += ["", f"## Fehler ({len(b.fehler)})"] + ([f"- {x}" for x in b.fehler] or ["keine"])
    z += ["", f"## Warnungen ({len(b.warnungen)})"] + ([f"- {x}" for x in b.warnungen] or ["keine"])
    return "\n".join(z) + "\n"


def schreiben(datei, out):
    AUSGABE.mkdir(exist_ok=True)
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(datei).stem)
    ziel = AUSGABE / f"{stem}.json"
    payload = dict(quelle_datei=Path(datei).name, importiert=dt.date.today().isoformat(), **out)
    with open(ziel, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1, default=str)
    return ziel


def hauptprogramm(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("datei")
    ap.add_argument("--schreiben", action="store_true", help="JSON ablegen und build.py ausführen")
    ap.add_argument("--bericht", help="Prüfbericht als Markdown speichern")
    ap.add_argument("--tolerant", action="store_true", help="Seite optional, Fremdwährungsbeträge ohne T€ zulassen, Duplikate überspringen")
    a = ap.parse_args(argv)
    global TOLERANT
    TOLERANT = a.tolerant
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(a.datei).stem)
    b = Bericht()
    daten, fehler = lese(a.datei)
    for f in fehler:
        b.f("Datei", f)
    bestand = Bestand(AUSGABE / f"{stem}.json")
    if not fehler:
        out = pruefe(daten, bestand, b)
    else:
        out = dict(mitglieder=[], verguetung=[], kennzahlen=[], mandate=[], werdegang=[], geschlecht=[], pay_ratio_eingang=[], dokumente=[])
    txt = bericht_text(a.datei, b, out)
    print(txt)
    if a.bericht:
        Path(a.bericht).write_text(txt, encoding="utf-8")
    if b.fehler:
        print("Abbruch: Es wurden Fehler gefunden, nichts geschrieben.", file=sys.stderr)
        return 1
    if a.schreiben:
        ziel = schreiben(a.datei, out)
        print("geschrieben:", ziel.relative_to(REPO))
        r = subprocess.run([sys.executable, str(GOV / "skripte" / "build.py")], cwd=REPO)
        if r.returncode:
            print("build.py fehlgeschlagen", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(hauptprogramm())
