"""Rechenregeln für normalisierte Fakten, Skalierung, Währungen und Perioden. Nur Standardbibliothek, kein Netzwerk.

Die Währungsumrechnung wählt den Kurs nach festen Regeln (Stichtagskurs für Bilanzpositionen, Periodendurchschnitt für die GuV),
verwendet nie Kurse nach dem Bezugsdatum und begrenzt das Alter des Kurses. Originalwerte werden nicht überschrieben.
"""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

FX_METHODE = "fx-v1"


@dataclass(frozen=True)
class Fact:
    entity: str
    metric: str
    value: Decimal
    unit: str
    end: date
    start: date | None = None

    def __post_init__(self):
        if not self.value.is_finite():
            raise ValueError('Nicht endlicher Wert')
        if self.start is not None and self.start > self.end:
            raise ValueError('Ungültige Periode')


def scale_value(raw: str, exponent: int) -> Decimal:
    value = Decimal(raw) * (Decimal(10) ** exponent)
    if not value.is_finite():
        raise ValueError('Nicht endlicher Wert')
    return value


def convert(value: Decimal, rate: Decimal) -> Decimal:
    # rate = Einheiten Zielwährung pro Einheit Quellwährung
    if not value.is_finite() or not rate.is_finite() or rate <= 0:
        raise ValueError('Ungültiger Wert oder Wechselkurs')
    return value * rate


def ratio(numerator: Decimal | None, denominator: Decimal | None):
    if numerator is None or denominator is None or denominator == 0:
        return None
    if not numerator.is_finite() or not denominator.is_finite():
        raise ValueError('Nicht endlicher Wert')
    return numerator / denominator


def percent_to_ratio(percent: Decimal) -> Decimal:
    """15 (Prozent) -> 0.15. Der ursprüngliche Wert gehört in provenance."""
    if not percent.is_finite():
        raise ValueError('Nicht endlicher Wert')
    return percent / Decimal(100)


# Unterwährungen: Börsenkurse in Pence u. ä. dürfen nie als Hauptwährung gelesen werden
_UNTERWAEHRUNG = {"GBX": ("GBP", Decimal("0.01")), "GBp": ("GBP", Decimal("0.01")),
                  "ZAc": ("ZAR", Decimal("0.01")), "ILA": ("ILS", Decimal("0.01"))}


def haupt_waehrung(wert: Decimal, einheit: str) -> tuple[Decimal, str]:
    """Rechnet Pence/Agorot/Cent in die Hauptwährung um; andere Einheiten bleiben unverändert."""
    if einheit in _UNTERWAEHRUNG:
        ziel, faktor = _UNTERWAEHRUNG[einheit]
        return wert * faktor, ziel
    return wert, einheit


def periode_klasse(start: date | None, end: date) -> str:
    """'instant' ohne Beginn, sonst nach Dauer: annual (52/53 Wochen und 12 Monate), half_year, quarterly oder other.
    Maßgeblich ist die Periodendauer, nicht ein Feld 'fiscal year/period' des Anbieters."""
    if start is None:
        return "instant"
    tage = (end - start).days + 1
    if 350 <= tage <= 380:
        return "annual"
    if 175 <= tage <= 190:
        return "half_year"
    if 84 <= tage <= 98:
        return "quarterly"
    return "other"


def stichtagskurs(kurse: dict[date, Decimal], tag: date, max_alter_tage: int = 5):
    """Letzter Kurs am oder vor dem Tag (Feiertag/Wochenende -> vorangegangener Handelstag).
    Gibt (kurs, kurstag, alter_in_tagen) zurück oder None, wenn kein zulässiger Kurs vorliegt. Keine Kurse aus der Zukunft."""
    kandidaten = [d for d in kurse if d <= tag]
    if not kandidaten:
        return None
    d = max(kandidaten)
    alter = (tag - d).days
    if alter > max_alter_tage:
        return None
    return kurse[d], d, alter


def durchschnittskurs(kurse: dict[date, Decimal], start: date, end: date, min_tage: int = 150):
    """Arithmetisches Mittel der in der Periode vorhandenen Tageskurse (nur Kurse im Zeitraum, keine künftigen).
    Gibt (kurs, anzahl_kurse) zurück oder None, wenn weniger als min_tage Kurse vorliegen (bei Jahresperioden ca. Handelstage)."""
    werte = [k for d, k in kurse.items() if start <= d <= end]
    if len(werte) < min_tage:
        return None
    return sum(werte) / Decimal(len(werte)), len(werte)


def vergleichbar(a: dict, b: dict) -> bool:
    """Verhältniszahlen nur aus gleichem Standard, Konsolidierungskreis und gleicher Periode bilden."""
    return all(a.get(k) == b.get(k) for k in ("accounting_standard", "consolidation", "period_start", "period_end"))


if __name__ == '__main__':
    assert scale_value('1.25', 6) == Decimal('1250000')
    assert convert(Decimal('100'), Decimal('0.8')) == Decimal('80')
    assert ratio(Decimal('15'), Decimal('100')) == Decimal('0.15')
    assert ratio(None, Decimal('100')) is None
    assert ratio(Decimal('1'), Decimal('0')) is None
    try:
        scale_value('NaN', 0)
    except ValueError:
        pass
    else:
        raise AssertionError('NaN akzeptiert')
    print('Kernregeln: 6 Prüfungen erfolgreich')
