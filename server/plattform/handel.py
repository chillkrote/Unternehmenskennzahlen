"""Handelsabhängigkeit (P5): Rechenregeln ohne Datenbank.

Fünf verschiedene Fragen, die nicht verwechselt werden dürfen (Audit 2026-11, 4.3):

1. Konzentration der weltweiten Exporte eines Gutes: Weltmarktanteile, HHI, CR3 über alle Exportländer (trade_export).
2. Importabhängigkeit eines Landes von einem Lieferland: Importwert aus X / gesamter Importwert des Landes für das Gut
   (importanteil; trade_import, trade_import_supplier).
3. Konzentration der tatsächlichen Lieferländer eines Importlands: HHI über ALLE seine Lieferländer (trade_import.hhi). Ein HHI nur
   über die größten fünf oder zehn ist kein Lieferanten-HHI; aus einer Teilmenge lässt sich nur eine Untergrenze angeben
   (hhi_untergrenze: Anteile am Gesamtwert, nicht an der Teilmenge).
4. Alternative Exportländer: wer exportiert das Gut außerdem (alternativen). Das ist vorhandenes Exportvolumen,
5. keine freie Lieferkapazität: ob ein Land Mengen umlenken oder ausweiten kann, steht in keiner der Quellen.

* Weltmarktanteil  Export eines Landes / Summe aller Exportländer (BACI deckt alle Exportländer ab, die Summe ist der Weltwert).
* HHI              Herfindahl-Hirschman-Index der Anteile in Punkten (Summe der quadrierten Anteile in Prozent, 0 bis 10 000).
* Bänder           unter 1 000 gering, 1 000 bis 1 800 mäßig, darüber hoch konzentriert. Die Grenzen stammen aus der Fusionskontrolle
                   (US Merger Guidelines 2023) und beschreiben Marktkonzentration. Sie sind eine Lesehilfe, kein Grenzwert für
                   Versorgungssicherheit: Ein Importland kann bei niedrigem HHI von einem einzelnen Lieferland abhängen und umgekehrt.
* CR3              Anteil der drei größten Exportländer.
"""
SCHWELLEN = ((1000, "gering"), (1800, "maessig"))
BAENDER_HINWEIS = ("HHI-Bänder aus der Fusionskontrolle (US Merger Guidelines 2023: 1 000 / 1 800) als Lesehilfe für Konzentration; "
                   "kein Grenzwert für Versorgungssicherheit.")


def anteile(werte: dict) -> dict:
    """{land: wert} -> {land: anteil}, Anteile summieren sich zu 1 (leere oder Nullsumme: leer)."""
    s = sum(v for v in werte.values() if v and v > 0)
    return {k: v / s for k, v in werte.items() if v and v > 0} if s > 0 else {}


def hhi(werte: dict) -> float:
    return round(sum((a * 100) ** 2 for a in anteile(werte).values()), 1)


def einstufung(h: float) -> str:
    for grenze, name in SCHWELLEN:
        if h < grenze:
            return name
    return "hoch"


def cr(werte: dict, n: int = 3) -> float:
    return round(sum(sorted(anteile(werte).values(), reverse=True)[:n]), 4)


def alternativen(werte: dict, ohne, n: int = 5):
    """Größte Exportländer ohne die genannten; Anteil am Weltmarkt und am verbleibenden Markt."""
    ohne = set(ohne)
    rest = {k: v for k, v in werte.items() if k not in ohne and v and v > 0}
    ges, ar = sum(v for v in werte.values() if v and v > 0), anteile(rest)
    top = sorted(rest.items(), key=lambda x: (-x[1], x[0]))[:n]
    return [{"geo": k, "value": v, "world_share": round(v / ges, 4) if ges else 0.0, "share_without_excluded": round(ar[k], 4)} for k, v in top]


def importanteil(aus_lieferland, gesamt):
    """Importabhängigkeit: Importwert aus einem Lieferland / gesamter Importwert des Landes für das Gut (None ohne Importe)."""
    return round(aus_lieferland / gesamt, 4) if gesamt and gesamt > 0 and aus_lieferland is not None else None


def hhi_untergrenze(teilwerte: dict, gesamt) -> float:
    """Untergrenze des HHI, wenn nur ein Teil der Partner bekannt ist: Anteile am Gesamtwert (nicht an der Teilmenge) quadriert.
    Der wahre HHI ist mindestens so groß; mit den übrigen Partnern kommt nur noch etwas hinzu."""
    if not gesamt or gesamt <= 0:
        return 0.0
    return round(sum((v / gesamt * 100) ** 2 for v in teilwerte.values() if v and v > 0), 1)


def hhi_obergrenze(teilwerte: dict, gesamt) -> float:
    """Obergrenze dazu: der unbekannte Rest läge bei einem einzigen weiteren Partner, höchstens so groß wie der kleinste bekannte."""
    if not gesamt or gesamt <= 0:
        return 0.0
    pos = [v for v in teilwerte.values() if v and v > 0]
    rest, kleinster = max(gesamt - sum(pos), 0.0), min(pos, default=0.0)
    ober, r = sum((v / gesamt * 100) ** 2 for v in pos), rest
    while r > 1e-12 and kleinster > 0:
        stueck = min(r, kleinster)
        ober += (stueck / gesamt * 100) ** 2
        r -= stueck
    return round(ober, 1)
