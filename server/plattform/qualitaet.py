"""Datenqualität (P3.2): reine Rechenregeln, ohne Datenbank, damit der Prüfbericht reproduzierbar und einzeln testbar ist.

* Verzug     Wie weit liegt der letzte Zeitraum einer Reihe hinter dem Stichtag? Zeiträume (JJJJ, JJJJ-MM, JJJJ-Qn) werden auf
             den letzten Monat des Zeitraums abgebildet; erlaubt ist ein üblicher Veröffentlichungsabstand je Frequenz.
* Sprünge    Robuste Ausreißerprüfung der jüngsten Veränderungen einer Reihe je Gebiet: Abstand der Veränderung vom Median aller
             früheren Veränderungen in Vielfachen der skalierten mittleren absoluten Abweichung (MAD · 1,4826).
* Abdeckung  Anteil mit festem Nenner (der Nenner wird vorher festgelegt und nicht aus den vorhandenen Werten abgeleitet).
"""
from datetime import date
from statistics import median

# erlaubter Abstand zwischen Stichtag und letztem Monat des letzten Zeitraums, in Monaten
ERLAUBT_MONATE = {"M": 3, "Q": 6, "A": 24}
SPRUNG_SCHWELLE = 6.0          # Vielfache der skalierten MAD
SPRUNG_MIN_HISTORIE = 12       # mindestens so viele frühere Veränderungen
SPRUNG_LETZTE = 3              # die jüngsten n Veränderungen werden geprüft
MAD_FAKTOR = 1.4826
MITTEL_FAKTOR = 1.2533       # mittlere absolute Abweichung -> Standardabweichung (Normalverteilung)


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
