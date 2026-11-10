"""Handelsabhängigkeit (P5): Rechenregeln ohne Datenbank.

* Weltmarktanteil  Export eines Landes / Summe aller Exportländer (BACI deckt alle Exportländer ab, die Summe ist der Weltwert).
* HHI              Herfindahl-Hirschman-Index der Anteile in Punkten (Summe der quadrierten Anteile in Prozent, 0 bis 10 000).
                   Einstufung nach den Schwellen der US-Kartellbehörden (Merger Guidelines 2023): unter 1 000 gering,
                   1 000 bis 1 800 mäßig, über 1 800 hoch konzentriert.
* CR3              Anteil der drei größten Exportländer.
"""
SCHWELLEN = ((1000, "gering"), (1800, "maessig"))


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
