"""Zentrale Unternehmens-IDs (Stammdaten). Jedes Unternehmen im Repo hat genau eine ID der Form U000123.

Die ID ist ein fortlaufender, undurchsichtiger Schlüssel: Sie steckt weder in Name noch ISIN und ändert sich nie
(Umbenennung, Fusion, Börsengang, Schreibweise der Umlaute). Notierte und nicht notierte Unternehmen laufen im selben Nummernkreis.

Dateien (alle in stammdaten/):
  unternehmen_ids.csv      eine Zeile je Unternehmen (Name, Rechtsform, Branche, Sitz, ISINs, LEI, Ticker, Status ...)
  unternehmen_aliase.csv   alte IDs, Ordnernamen und Namensvarianten -> ID
  isin_zuordnung.csv       eine Zeile je ISIN; jede ISIN steht genau einmal, also nur bei einer ID

Nutzung in Skripten:
    sys.path.insert(0, str(Path(__file__).resolve().parents[N] / "stammdaten")); import ids
    reg = ids.lade()
    uid = reg.aufloesen("Deutsche Bank AG")      # Name, alte ID oder Ordnername -> ID (oder None)
    ordner = reg.ordner(uid)                     # Ordnername der Dokumente (bleibt die alte Schreibweise)
    uid = reg.registrieren(name=..., branche=..., isin=...)   # nur für wirklich neue Unternehmen
Prüfung: python3 stammdaten/pruefe_ids.py (Exit-Code 1 bei Verstoß, u. a. eine ISIN bei mehreren IDs).
"""
import csv
import re
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DIR = REPO / "stammdaten"
UNTERNEHMEN = DIR / "unternehmen_ids.csv"
ALIASE = DIR / "unternehmen_aliase.csv"
ISINS = DIR / "isin_zuordnung.csv"

KOPF_U = ["unternehmen_id", "name", "rechtsform", "branche", "gruppe", "rolle", "sitz", "land", "status", "isin_haupt",
          "weitere_isins", "lei", "ticker", "ordner", "herkunft", "nachfolger_von", "hinweis"]
KOPF_A = ["alias", "unternehmen_id", "art"]
KOPF_I = ["isin", "unternehmen_id", "art"]
ID_MUSTER = re.compile(r"^U\d{6}$")
ISIN_MUSTER = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}\d$")


def isin_pruefsumme_ok(isin):
    """ISO 6166: Luhn-Prüfziffer über die in Ziffern umgesetzte ISIN."""
    if not ISIN_MUSTER.match(isin or ""):
        return False
    ziffern = "".join(str(int(c, 36)) for c in isin)
    summe = 0
    for i, c in enumerate(reversed(ziffern)):
        d = int(c)
        if i % 2 == 1:
            d *= 2
            d = d - 9 if d > 9 else d
        summe += d
    return summe % 10 == 0


def schluessel(text):
    """Vergleichsschlüssel für Namen und Ordnernamen: Umlaute als ä/ae/a gleich, 'Aktiengesellschaft' = 'AG', ohne Satzzeichen."""
    s = str(text).lower().replace("&", " und ")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"\baktiengesellschaft\b", "ag", s)
    s = re.sub(r"[^a-z0-9]+", "", s)
    return re.sub(r"(?<=[aou])e", "", s)


def _lesen(pfad):
    if not Path(pfad).exists():
        return []
    with open(pfad, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _schreiben(pfad, kopf, zeilen):
    with open(pfad, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, kopf, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(zeilen)


class Register:
    def __init__(self):
        self.unternehmen = {r["unternehmen_id"]: r for r in _lesen(UNTERNEHMEN)}
        self.aliase = _lesen(ALIASE)
        self.isins = _lesen(ISINS)
        self._index()

    def _index(self):
        self.exakt = {}
        self.nach_schluessel = {}
        for a in self.aliase:
            self.exakt.setdefault(a["alias"], a["unternehmen_id"])
            self.nach_schluessel.setdefault(schluessel(a["alias"]), set()).add(a["unternehmen_id"])
        for uid, r in self.unternehmen.items():
            self.exakt.setdefault(uid, uid)
            self.nach_schluessel.setdefault(schluessel(r["name"]), set()).add(uid)
        self.nach_isin = {r["isin"]: r["unternehmen_id"] for r in self.isins}

    def aufloesen(self, text):
        """Name, alte ID, Ordnername, ISIN oder neue ID -> neue ID; None, wenn unbekannt oder mehrdeutig."""
        if not text:
            return None
        text = str(text).strip()
        if text in self.exakt:
            return self.exakt[text]
        if text in self.nach_isin:
            return self.nach_isin[text]
        ids = self.nach_schluessel.get(schluessel(text), set())
        return next(iter(ids)) if len(ids) == 1 else None

    def ordner(self, uid):
        """Ordnername der Dokumente (alte, nie umbenannte Schreibweise); Fallback: die ID selbst."""
        return self.unternehmen[uid]["ordner"] or uid

    def name(self, uid):
        return self.unternehmen[uid]["name"]

    def _naechste_id(self):
        höchste = max((int(u[1:]) for u in self.unternehmen), default=0)
        return f"U{höchste + 1:06d}"

    def registrieren(self, name, branche="", isin="", weitere_isins=(), ordner="", **felder):
        """Legt ein neues Unternehmen an (oder gibt die vorhandene ID zurück, wenn Name/ISIN/Ordner schon bekannt sind) und speichert sofort."""
        for kandidat in [isin, *weitere_isins, ordner, name]:
            uid = self.aufloesen(kandidat) if kandidat else None
            if uid:
                self.isins_zuordnen(uid, isin, weitere_isins)
                return uid
        uid = self._naechste_id()
        r = {k: "" for k in KOPF_U}
        r.update(felder, unternehmen_id=uid, name=name, branche=branche, ordner=ordner, isin_haupt=isin,
                 weitere_isins="|".join(weitere_isins), herkunft=felder.get("herkunft", "neu"),
                 status=felder.get("status") or ("börsennotiert" if isin else "nicht börsennotiert"))
        self.unternehmen[uid] = r
        for a, art in ((name, "name"), (ordner, "ordner")):
            if a:
                self.aliase.append({"alias": a, "unternehmen_id": uid, "art": art})
        self.isins_zuordnen(uid, isin, weitere_isins)
        self.speichern()
        return uid

    def isins_zuordnen(self, uid, isin, weitere, speichern=True):
        geaendert = False
        for i, art in [(isin, "haupt"), *[(w, "weitere") for w in weitere]]:
            if i and i not in self.nach_isin:
                self.isins.append({"isin": i, "unternehmen_id": uid, "art": art})
                self.nach_isin[i] = uid
                geaendert = True
            elif i and self.nach_isin[i] != uid:
                raise ValueError(f"ISIN {i} gehört schon zu {self.nach_isin[i]}, nicht zu {uid}")
        if geaendert and speichern:
            self.speichern()

    def aktualisieren(self, uid, **felder):
        """Übernimmt Stammdatenfelder (leere Werte überschreiben nichts); ISINs werden dabei auf Eindeutigkeit geprüft. Speichert nicht."""
        r = self.unternehmen[uid]
        weitere = [i for i in (felder.pop("weitere_isins", "") or "").replace(",", "|").replace(" ", "").split("|") if i]
        isin = felder.get("isin_haupt") or r["isin_haupt"]
        for k, v in felder.items():
            if k in KOPF_U and k != "unternehmen_id" and v not in ("", None):
                r[k] = v
        if isin or weitere:
            self.isins_zuordnen(uid, isin, weitere, speichern=False)
            alle = list(dict.fromkeys(i for i in [*r["weitere_isins"].split("|"), *weitere] if i and i != isin))
            r["weitere_isins"] = "|".join(alle)
        if r["isin_haupt"]:
            r["status"] = "börsennotiert"

    def speichern(self):
        _schreiben(UNTERNEHMEN, KOPF_U, sorted(self.unternehmen.values(), key=lambda r: r["unternehmen_id"]))
        _schreiben(ALIASE, KOPF_A, sorted(self.aliase, key=lambda r: (r["unternehmen_id"], r["art"], r["alias"])))
        _schreiben(ISINS, KOPF_I, sorted(self.isins, key=lambda r: r["isin"]))
        self._index()


_cache = None


def lade(neu=False):
    global _cache
    if _cache is None or neu:
        _cache = Register()
    return _cache
