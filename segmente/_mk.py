"""Baut die JSON-Eingabe für anfuegen.py aus einer kompakten Beschreibung (Hilfsskript)."""
import json
import sys

def bauen(uid, doc, seite, waehrung, segs, daten, bem=""):
    """daten: {gj: {kennzahl: [werte je segs]}}; seite: int oder {gj: int}"""
    zeilen = []
    for gj, kz in daten.items():
        for k, v in kz.items():
            assert len(v) == len(segs), (gj, k, len(v), len(segs))
            for s, x in zip(segs, v):
                if x is None:
                    continue
                zeilen.append(dict(unternehmen_id=uid, gj=gj, segment=s, kennzahl=k, wert_mio=x, waehrung=waehrung, quelle_dokument=doc,
                                   pdf_seite=seite[gj] if isinstance(seite, dict) else seite, pruefstatus="aus Bericht gelesen", bemerkung=bem))
    return zeilen
