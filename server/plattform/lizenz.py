"""Lizenzregeln, die Import und Oberfläche teilen (docs/datenquellen.md, Entscheidungen E1–E6).

E1 (Robin, 10.11.2026): Werte aus Yahoo Finance werden auf sphaerae.de nicht ausgeliefert, bis es eine freie Quelle oder eine
Vereinbarung gibt. Die Server-Datenbank nimmt sie deshalb gar nicht erst auf (etl/profile.py); für eine lokale Datenbank lassen
sie sich mit SPHAERAE_MIT_YAHOO=1 übernehmen. Dieselbe Liste steht in app/build.py (YAHOO_WERTE); tests/test_lizenz.py prüft die Gleichheit.

Zwei Stufen (Audit 2026-11, 4.5):

* Stufe „kurse“ (E1, gilt immer in der öffentlichen Fassung): Kurse, Börsenwert und alle daraus berechneten Kennzahlen (YAHOO_WERTE),
  die Dateien markt.json, kurse_woche.json, boerse.json, live.json und die Marktpuls-Reihen aus Yahoo.
* Stufe „abschluesse“ (E6, offen, Schalter SPHAERAE_OHNE_YAHOO_ABSCHLUESSE=1 bzw. build.py --ohne-yahoo-abschluesse): zusätzlich die
  Konzernabschlüsse, die die Branchenmappen aus Yahoo übernommen haben (Abschlüsse mit Quelle „Yahoo Finance …“, die daraus
  abgeleiteten Kennzahlen der Nicht-Banken) und die geschätzten Berichtstermine mit Quelle „yahoo“.

pruefe_ausgabe(ordner) prüft einen fertigen Build systematisch (HTML, eingebettete JSON-Blöcke, Dateien daneben):

    python3 -m plattform.lizenz ../app/dist-api            # Stufe kurse; Rückgabewert 1 bei Verstößen
    python3 -m plattform.lizenz ../app/dist-api --streng   # zusätzlich Stufe abschluesse
"""
import json
import os
import re
import sys
from pathlib import Path

YAHOO_WERTE = ("kurs", "marktkap", "r_ytd", "r_1j", "kgv", "kbv", "kuv", "ev_ebitda", "div_rendite",
               "x_enterprise_value", "x_ev_umsatz", "x_aussch_ttungsquote", "x_kurs_nderung_52w", "x_52w_hoch", "x_52w_tief",
               "x_beta", "x_volumen_3m", "x_insider", "x_institutionen", "x_kgv_erwartet", "x_kgv")
# Dateien, die nur Yahoo-Daten enthalten und in einer öffentlichen Fassung nicht liegen dürfen
YAHOO_DATEIEN = ("markt.json", "kurse_woche.json", "boerse.json", "live.json")
# eingebettete Blöcke (script id), die in der öffentlichen Fassung leer („null“) sein müssen
YAHOO_BLOECKE = ("markt", "kurse", "boerse")
# Kennzahlen der Nicht-Banken, die nicht aus Yahoo stammen (BaFin-Stimmrechtsdatenbank); alles andere dort kommt aus den Yahoo-Abschlüssen
NICHT_YAHOO_WERTE = ("x_anteil_stimmrechte", "x_anzahl_meldepflichtige")
MANIFEST = "LIZENZ.json"
PRODUKTION = ("produktion", "production", "prod")


def _an(name):
    return os.environ.get(name, "").strip().lower() in ("1", "true", "ja")


def mit_yahoo() -> bool:
    """Lokale Testoption. In einer Produktionsumgebung (PLATTFORM_UMGEBUNG=produktion) ist sie ein Fehler, kein Schalter."""
    an = _an("SPHAERAE_MIT_YAHOO")
    if an and os.environ.get("PLATTFORM_UMGEBUNG", "").strip().lower() in PRODUKTION:
        raise RuntimeError("SPHAERAE_MIT_YAHOO ist in der Produktionsumgebung nicht erlaubt (E1, docs/datenquellen.md)")
    return an


def ohne_yahoo_abschluesse() -> bool:
    return _an("SPHAERAE_OHNE_YAHOO_ABSCHLUESSE")


def ist_yahoo_quelle(text) -> bool:
    return "yahoo" in str(text or "").lower()


def ist_yahoo_abschluss(abschluss: dict) -> bool:
    return ist_yahoo_quelle(abschluss.get("quelle"))


def hat_eigene_zahlen(firma: dict) -> bool:
    """Kennzahlen aus eigener Erhebung (Bilanzvergleich der Banken: HGB-Abschlüsse, EBA) statt aus den Yahoo-Branchenmappen."""
    return bool(firma.get("bank") or firma.get("gruppe"))


def firma_ohne_yahoo_abschluesse(f: dict) -> dict:
    """Stufe „abschluesse“ für ein Unternehmen aus unternehmen.json (verändert f und gibt es zurück)."""
    if f.get("abschluesse"):
        f["abschluesse"] = [a for a in f["abschluesse"] if not ist_yahoo_abschluss(a)]
    if f.get("termine"):
        f["termine"] = [t for t in f["termine"] if not ist_yahoo_quelle(t.get("quelle"))]
    if not hat_eigene_zahlen(f):
        f["werte"] = {k: v for k, v in (f.get("werte") or {}).items() if k in NICHT_YAHOO_WERTE}
    return f


# ---------- Prüfung eines fertigen Builds ----------
_BLOCK = re.compile(r'<script\b([^>]*)>(.*?)</script>', re.S)


def _bloecke(html):
    for m in _BLOCK.finditer(html):
        attr = m.group(1)
        if "application/json" not in attr:
            continue
        i = re.search(r'\bid="([^"]+)"', attr)
        if i:
            yield i.group(1), m.group(2).replace("<\\/", "</")


def _firmen_pruefen(d, wo, streng, fehler):
    if not isinstance(d, dict) or "unternehmen" not in d:
        return
    gesperrt = set(YAHOO_WERTE)
    kat = [k.get("key") for k in d.get("kennzahlen") or [] if k.get("key") in gesperrt]
    if kat:
        fehler.append(f"{wo}: Kennzahlenkatalog enthält gesperrte Kennzahlen {sorted(kat)[:5]}")
    n = sum(1 for f in d["unternehmen"] for k in (f.get("werte") or {}) if k in gesperrt)
    if n:
        fehler.append(f"{wo}: {n} Yahoo-Kurswerte in werte")
    if streng:
        a = sum(1 for f in d["unternehmen"] for x in f.get("abschluesse") or [] if ist_yahoo_abschluss(x))
        t = sum(1 for f in d["unternehmen"] for x in f.get("termine") or [] if ist_yahoo_quelle(x.get("quelle")))
        w = sum(1 for f in d["unternehmen"] if not hat_eigene_zahlen(f) for k in (f.get("werte") or {}) if k not in NICHT_YAHOO_WERTE)
        for zahl, was in ((a, "Yahoo-Abschlüsse"), (t, "Yahoo-Termine"), (w, "Kennzahlen aus Yahoo-Abschlüssen (Nicht-Banken)")):
            if zahl:
                fehler.append(f"{wo}: {zahl} {was}")


def _json_pruefen(name, text, wo, streng, fehler):
    try:
        d = json.loads(text)
    except ValueError:
        return
    if isinstance(d, dict) and "_nach" in d and len(d) == 1:
        return
    _firmen_pruefen(d, wo, streng, fehler)
    if isinstance(d, dict) and isinstance(d.get("puls"), list):
        n = sum(1 for x in d["puls"] if isinstance(x, dict) and ist_yahoo_quelle(x.get("quelle")))
        if n:
            fehler.append(f"{wo}: {n} Marktpuls-Reihen aus Yahoo")
    if isinstance(d, dict) and isinstance(d.get("banken"), list):
        n = sum(1 for b in d["banken"] if isinstance(b, dict) for k in b if k in ("kurs", "mkap", "mkap_ek", "marktkap"))
        if n:
            fehler.append(f"{wo}: {n} Kurs-/Börsenwertfelder bei Banken")
    if isinstance(d, dict) and isinstance(d.get("spalten"), list):
        s = [c for c in d["spalten"] if c in YAHOO_WERTE]
        if s:
            fehler.append(f"{wo}: Spalten {s} aus Yahoo")


def pruefe_ausgabe(ordner, streng=False):
    """Liste der Verstöße in einem Build-Ordner (leer = in Ordnung). Prüft das Manifest, verbotene Dateien, alle JSON-Dateien und
    alle eingebetteten JSON-Blöcke der HTML-Seiten."""
    ordner, fehler = Path(ordner), []
    mf = ordner / MANIFEST
    if not mf.exists():
        fehler.append(f"{MANIFEST} fehlt (Build nicht mit app/build.py erzeugt?)")
    else:
        m = json.loads(mf.read_text(encoding="utf-8"))
        if not m.get("oeffentlich") or m.get("yahoo_kurse"):
            fehler.append(f"{MANIFEST}: Build ist nicht öffentlich (oeffentlich={m.get('oeffentlich')}, yahoo_kurse={m.get('yahoo_kurse')})")
        if streng and m.get("yahoo_abschluesse"):
            fehler.append(f"{MANIFEST}: Build enthält Yahoo-Abschlüsse")
    for f in sorted(ordner.rglob("*")):
        if not f.is_file():
            continue
        rel = str(f.relative_to(ordner))
        if f.name in YAHOO_DATEIEN:
            fehler.append(f"{rel}: Datei mit Yahoo-Daten")
        elif f.suffix == ".json" and f.name != MANIFEST:
            _json_pruefen(f.name, f.read_text(encoding="utf-8"), rel, streng, fehler)
        elif f.suffix == ".html":
            html = f.read_text(encoding="utf-8")
            if not f.name.endswith(".fragment.html") and 'name="sphaerae-oeffentlich"' not in html:
                fehler.append(f"{rel}: Kennzeichen sphaerae-oeffentlich fehlt")
            for bid, inhalt in _bloecke(html):
                if bid in YAHOO_BLOECKE and inhalt.strip() != "null":
                    fehler.append(f"{rel}#{bid}: Block mit Yahoo-Daten ist nicht leer")
                else:
                    _json_pruefen(bid, inhalt, f"{rel}#{bid}", streng, fehler)
    return fehler


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        raise SystemExit(__doc__)
    verstoesse = pruefe_ausgabe(args[0], streng="--streng" in sys.argv)
    for v in verstoesse:
        print("VERSTOSS", v)
    print(f"{args[0]}: {len(verstoesse)} Verstöße")
    sys.exit(1 if verstoesse else 0)
