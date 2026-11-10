"""Datenqualität (P3.2): reine Rechenregeln, ohne Datenbank, damit der Prüfbericht reproduzierbar und einzeln testbar ist.

* Verzug     Wie weit liegt der letzte Zeitraum einer Reihe hinter dem Stichtag? Zeiträume (JJJJ, JJJJ-MM, JJJJ-Qn) werden auf
             den letzten Monat des Zeitraums abgebildet; erlaubt ist ein üblicher Veröffentlichungsabstand je Frequenz.
* Sprünge    Robuste Ausreißerprüfung der jüngsten Veränderungen einer Reihe je Gebiet: Abstand der Veränderung vom Median aller
             früheren Veränderungen in Vielfachen der skalierten mittleren absoluten Abweichung (MAD · 1,4826).
* Abdeckung  Anteil mit festem Nenner (der Nenner wird vorher festgelegt und nicht aus den vorhandenen Werten abgeleitet):
             je Reihe die Gebiete, die bei der Quelle angefragt werden (erwartete_gebiete), nicht die Vereinigung aller Gebiete
             irgendeiner Reihe.
* Aktualität je Gebiet (Audit 2026-11, 4.2): Der jüngste Zeitraum über alle Gebiete verdeckt, dass einzelne Länderreihen
             stehen geblieben sind. aktualitaet() stuft deshalb jedes Gebiet einzeln ein:
               current        innerhalb des erlaubten Abstands
               stale          die Quelle ist aktuell, dieses Gebiet liegt zurück (einzelne Länderreihe veraltet)
               source_stale   schon der jüngste Wert der ganzen Reihe ist zu alt (Quelle oder Abruf veraltet)
               dormant        seit RUHEND_MONATE kein neuer Wert: eingestellt oder von der Quelle nicht mehr geliefert
               not_published  bekannter Fall, in dem die Quelle für dieses Gebiet grundsätzlich nichts Neueres veröffentlicht (BEKANNT)
               missing        erwartet, aber ohne jeden Wert
* Lücken     Fehlende Zeiträume zwischen erstem und letztem Wert eines Gebiets (luecken) und Verfügbarkeit im Vergleichszeitraum
             (die letzten FENSTER[frequenz] Zeiträume bis zum jüngsten Wert der Reihe).
* Abruf      Alter des letzten Abrufs laut Reihe; über ABRUF_MAX_TAGE gilt der Abruf als überfällig (Hinweis auf technischen Fehler).
"""
import re
from datetime import date
from statistics import median

# erlaubter Abstand zwischen Stichtag und letztem Monat des letzten Zeitraums, in Monaten
ERLAUBT_MONATE = {"M": 3, "Q": 6, "A": 24}
SPRUNG_SCHWELLE = 6.0          # Vielfache der skalierten MAD
SPRUNG_MIN_HISTORIE = 12       # mindestens so viele frühere Veränderungen
SPRUNG_LETZTE = 3              # die jüngsten n Veränderungen werden geprüft
MAD_FAKTOR = 1.4826
MITTEL_FAKTOR = 1.2533       # mittlere absolute Abweichung -> Standardabweichung (Normalverteilung)


# seit so vielen Monaten kein neuer Wert: die Länderreihe gilt als ruhend (eingestellt oder nicht mehr geliefert), nicht bloß als verspätet
RUHEND_MONATE = {"M": 18, "Q": 24, "A": 60}
# Vergleichszeitraum: so viele Zeiträume bis zum jüngsten Wert der Reihe
FENSTER = {"M": 12, "Q": 8, "A": 5}
# erwarteter Rhythmus der Veröffentlichung (Anzeige) und höchstes Alter des letzten Abrufs in Tagen
RHYTHMUS = {"M": "monatlich", "Q": "vierteljährlich", "A": "jährlich"}
ABRUF_MAX_TAGE = {"M": 45, "Q": 60, "A": 120}
# (Quelle, Gebiet) -> Grund: die Quelle veröffentlicht für dieses Gebiet grundsätzlich keine neueren Werte
BEKANNT = {("Eurostat", "UK"): "Eurostat führt das Vereinigte Königreich seit dem EU-Austritt (Ende 2020) nicht mehr fort"}
# ISO-3-Codes der OECD -> Gebietscode der Reihen (wie volkswirtschaft/skripte/gemeinsam.py: OECD_ISO3; tests/test_qualitaet.py prüft die Gleichheit)
OECD_ISO3 = {"DEU": "DE", "EA20": "EA20", "EU27_2020": "EU27_2020", "OECD": "OECD", "G7": "G7", "AUS": "AU", "AUT": "AT", "BEL": "BE", "CAN": "CA",
             "CHL": "CL", "COL": "CO", "CRI": "CR", "CZE": "CZ", "DNK": "DK", "EST": "EE", "FIN": "FI", "FRA": "FR", "GRC": "EL", "HUN": "HU",
             "ISL": "IS", "IRL": "IE", "ISR": "IL", "ITA": "IT", "JPN": "JP", "KOR": "KR", "LVA": "LV", "LTU": "LT", "LUX": "LU", "MEX": "MX",
             "NLD": "NL", "NZL": "NZ", "NOR": "NO", "POL": "PL", "PRT": "PT", "SVK": "SK", "SVN": "SI", "ESP": "ES", "SWE": "SE", "CHE": "CH",
             "TUR": "TR", "GBR": "UK", "USA": "US"}


# Eurostat führt den Euroraum je Datensatz unter wechselnden Codes; die Reihen speichern ihn einheitlich als EA20 (abruf_eurostat.py)
EURORAUM = {"EA": "EA20", "EA19": "EA20", "EA21": "EA20"}


def erwartete_gebiete(url):
    """Gebiete, die der Abruf bei der Quelle anfragt, aus der Abruf-URL der Reihe: Eurostat (?geo=DE&geo=…) und OECD-SDMX
    (/DEU+EA20+….M…). None, wenn die URL keine Gebietsliste trägt (dann gibt es keinen festen Nenner)."""
    if not url:
        return None
    g = re.findall(r"[?&]geo=([A-Z0-9_]+)", url)
    if g:
        return sorted({EURORAUM.get(x, x) for x in g})
    m = re.search(r"/((?:[A-Z0-9_]+\+)+[A-Z0-9_]+)[.?/]", url)
    if m:
        codes = m.group(1).split("+")
        if all(c in OECD_ISO3 for c in codes):
            return sorted({OECD_ISO3[c] for c in codes})
    return None


def zeitraum_aus(index: int, frequenz: str) -> str:
    """Umkehrung von monat() für den letzten Monat eines Zeitraums."""
    j, m = divmod(index, 12)
    return str(j) if frequenz == "A" else f"{j}-Q{m // 3 + 1}" if frequenz == "Q" else f"{j}-{m + 1:02d}"


SCHRITT = {"M": 1, "Q": 3, "A": 12}


def luecken(perioden, frequenz):
    """Fehlende Zeiträume zwischen dem ersten und dem letzten vorhandenen (ohne Ränder). Unbekannte Frequenz: leer."""
    n = SCHRITT.get(frequenz)
    if not n or len(perioden) < 2:
        return []
    da = {monat(p) for p in perioden}
    return [zeitraum_aus(i, frequenz) for i in range(min(da), max(da), n) if i not in da]


def fenster(letzter: str, frequenz: str):
    """Die Zeiträume des Vergleichszeitraums, endend mit `letzter` (aufsteigend)."""
    n, k = SCHRITT.get(frequenz), FENSTER.get(frequenz)
    if not n:
        return []
    e = monat(letzter)
    return [zeitraum_aus(e - i * n, frequenz) for i in range(k - 1, -1, -1)]


def aktualitaet(letzte: dict, frequenz: str, stichtag: date, erwartet=None, quelle=None):
    """letzte: {gebiet: letzter beobachteter Zeitraum}. Stuft jedes Gebiet einzeln ein (Status siehe Modulkopf).

    Maßstab ist der Stichtag, nicht der jüngste Wert der Reihe: so fällt auch eine insgesamt veraltete Quelle auf.
    Liefert {"source_last", "source": verzug(...), "geos": {gebiet: {"last_period", "lag_months", "behind_source_months", "status", "reason"?}}}."""
    quelle_letzter = max(letzte.values(), key=monat, default=None)
    qv = verzug(quelle_letzter, frequenz, stichtag) if quelle_letzter else None
    ruhend = RUHEND_MONATE.get(frequenz)
    out = {}
    for g in sorted(set(letzte) | set(erwartet or ())):
        l = letzte.get(g)
        if l is None:
            out[g] = {"last_period": None, "lag_months": None, "behind_source_months": None, "status": "missing"}
            if (quelle, g) in BEKANNT:
                out[g].update(status="not_published", reason=BEKANNT[(quelle, g)])
            continue
        v = verzug(l, frequenz, stichtag)
        e = {"last_period": l, "lag_months": v["lag_months"], "behind_source_months": monat(quelle_letzter) - monat(l)}
        if not v["stale"]:
            e["status"] = "current"
        elif (quelle, g) in BEKANNT:
            e.update(status="not_published", reason=BEKANNT[(quelle, g)])
        elif ruhend is not None and v["lag_months"] > ruhend:
            e["status"] = "dormant"
        elif qv["stale"] and e["behind_source_months"] == 0:
            e["status"] = "source_stale"
        else:
            e["status"] = "stale"
        out[g] = e
    return {"source_last": quelle_letzter, "source": qv, "geos": out}


def abruf_alter(abruf, frequenz: str, stichtag: date):
    """Alter des letzten Abrufs in Tagen und ob er überfällig ist. abruf: 'JJJJ-MM-TT' laut Reihe; unlesbar: None."""
    try:
        tage = (stichtag - date.fromisoformat(str(abruf)[:10])).days
    except (TypeError, ValueError):
        return None
    grenze = ABRUF_MAX_TAGE.get(frequenz)
    return {"fetched": str(abruf)[:10], "age_days": tage, "allowed_days": grenze, "overdue": grenze is not None and tage > grenze}


def monat(zeitraum: str) -> int:
    """Laufender Monatsindex des letzten Monats eines Zeitraums (JJJJ -> Dezember, JJJJ-Qn -> letzter Quartalsmonat)."""
    j = int(zeitraum[:4])
    if len(zeitraum) == 4:
        return j * 12 + 11
    if zeitraum[5] == "Q":
        return j * 12 + 3 * int(zeitraum[6]) - 1
    return j * 12 + int(zeitraum[5:7]) - 1


def verzug(letzter: str, frequenz: str, stichtag: date) -> dict:
    """Verzug in Monaten und ob er über dem erlaubten Abstand liegt (unbekannte Frequenz: nie veraltet)."""
    m = stichtag.year * 12 + stichtag.month - 1 - monat(letzter)
    grenze = ERLAUBT_MONATE.get(frequenz)
    return {"lag_months": m, "allowed_months": grenze, "stale": grenze is not None and m > grenze}


def spruenge(punkte, schwelle=SPRUNG_SCHWELLE, min_historie=SPRUNG_MIN_HISTORIE, letzte=SPRUNG_LETZTE):
    """punkte: [(zeitraum, wert)] aufsteigend. Liefert auffällige Veränderungen unter den jüngsten `letzte`.

    Je geprüfter Veränderung dienen nur die früheren Veränderungen als Maßstab (kein Blick in die Zukunft)."""
    d = [(punkte[i][0], punkte[i - 1][1], punkte[i][1], punkte[i][1] - punkte[i - 1][1]) for i in range(1, len(punkte))]
    out = []
    for k in range(max(min_historie, len(d) - letzte), len(d)):
        frueher = [x[3] for x in d[:k]]
        med = median(frueher)
        abw = [abs(x - med) for x in frueher]
        mad = median(abw) * MAD_FAKTOR or sum(abw) / len(abw) * MITTEL_FAKTOR    # MAD 0 (z. B. wiederkehrende Stufen): mittlere Abweichung
        if mad == 0:
            continue
        z = (d[k][3] - med) / mad
        if abs(z) > schwelle:
            out.append({"period": d[k][0], "previous": d[k][1], "value": d[k][2], "change": d[k][3], "score": round(z, 2)})
    return out


def anteil(gedeckt: int, nenner: int) -> float:
    return round(gedeckt / nenner, 4) if nenner else 0.0
