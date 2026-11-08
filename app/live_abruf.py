"""Börse & Finanzen, Kurzfristwerte: aktuelle Kurse (Yahoo Finance, ca. 15 Minuten verzögert) für Marktpuls, Leitindizes, Rohstoffe, Bitcoin
-> data/live.json. Klein (wenige KB), wird vom Workflow live.yml mehrmals täglich erzeugt und als einziger Commit auf den Zweig
`daten-live` gelegt (nicht auf main). Terminal und Weltkugel auf GitHub Pages laden die Datei alle 90 Sekunden nach.
Schlüssel in "werte": die Kennung der Marktpuls-Kachel (z. B. vix, gold, btc) oder das Yahoo-Symbol des Index (z. B. ^GDAXI).
Je Wert: k Kurs, v Schlusskurs des Vortags, z Zeitpunkt des letzten Kurses (UTC, ISO).
Kein Schlüssel nötig. Fällt Yahoo teilweise aus, fehlen nur die betroffenen Werte; bei weniger als der Hälfte wird nichts geschrieben.

    python3 app/live_abruf.py"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

HIER = Path(__file__).resolve().parent
ZIEL = HIER / "data/live.json"
# Kennung -> Yahoo-Symbol. Marktpuls-Kennungen wie in finanz_abruf.py (YAHOO) plus der Euro-Dollar-Kurs (dort aus der EZB, hier Yahoo).
PULS = {"vix": "^VIX", "vxn": "^VXN", "ovx": "^OVX", "gvz": "^GVZ", "move": "^MOVE", "gold": "GC=F", "silber": "SI=F", "brent": "BZ=F",
        "dxy": "DX-Y.NYB", "btc": "BTC-USD", "eth": "ETH-USD", "eurusd": "EURUSD=X"}
INDIZES = ["^GDAXI", "^GSPC", "^N225", "^HSI", "^FTSE", "^FCHI", "^BSESN", "^BVSP", "^STOXX50E", "^IXIC", "^DJI", "000001.SS"]


def main():
    symbole = {**PULS, **{s: s for s in INDIZES}}
    liste = sorted(set(symbole.values()))
    kurz = yf.download(liste, period="5d", interval="15m", group_by="ticker", progress=False, threads=True, auto_adjust=False)
    tag = yf.download(liste, period="10d", interval="1d", group_by="ticker", progress=False, threads=True, auto_adjust=False)
    werte = {}
    for schluessel, sym in symbole.items():
        try:
            c = kurz[sym]["Close"].dropna()
            d = tag[sym]["Close"].dropna()
            if c.empty or d.empty:
                raise ValueError("keine Werte")
            letzt = c.index[-1]
            # Vortag: war der letzte Tagesbalken schon der von heute, zählt der davor
            vortag = d.iloc[-2] if len(d) > 1 and d.index[-1].date() == letzt.date() else d.iloc[-1]
            werte[schluessel] = {"k": round(float(c.iloc[-1]), 4), "v": round(float(vortag), 4),
                                 "z": letzt.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ") if letzt.tzinfo else letzt.strftime("%Y-%m-%dT%H:%M:%SZ")}
        except Exception as e:  # noqa: BLE001
            print("  ohne Wert:", schluessel, sym, e, file=sys.stderr)
    if len(werte) < len(symbole) / 2:
        sys.exit(f"Nur {len(werte)} von {len(symbole)} Werten, nichts geschrieben")
    out = {"abruf": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "quelle": "Yahoo Finance, ca. 15 Minuten verzögert, ohne Gewähr", "werte": werte}
    ZIEL.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"{ZIEL}: {len(werte)} von {len(symbole)} Werten", file=sys.stderr)


if __name__ == "__main__":
    main()
