"""Lizenzregeln, die Import und Oberfläche teilen (docs/datenquellen.md, Entscheidungen E1–E5).

E1 (Robin, 10.11.2026): Werte aus Yahoo Finance werden auf sphaerae.de nicht ausgeliefert, bis es eine freie Quelle oder eine
Vereinbarung gibt. Die Server-Datenbank nimmt sie deshalb gar nicht erst auf (etl/profile.py); für eine lokale Datenbank lassen
sie sich mit SPHAERAE_MIT_YAHOO=1 übernehmen. Dieselbe Liste steht in app/build.py (YAHOO_WERTE); tests/test_lizenz.py prüft die Gleichheit.
"""
import os

YAHOO_WERTE = ("kurs", "marktkap", "r_ytd", "r_1j", "kgv", "kbv", "kuv", "ev_ebitda", "div_rendite",
               "x_enterprise_value", "x_ev_umsatz", "x_aussch_ttungsquote", "x_kurs_nderung_52w", "x_52w_hoch", "x_52w_tief",
               "x_beta", "x_volumen_3m", "x_insider", "x_institutionen", "x_kgv_erwartet", "x_kgv")


def mit_yahoo() -> bool:
    return os.environ.get("SPHAERAE_MIT_YAHOO", "").strip().lower() in ("1", "true", "ja")
