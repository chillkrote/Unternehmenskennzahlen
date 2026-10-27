"""Übernimmt die handgepflegte Reihe ifo_geschaeftsklima.csv (zeit, wert, beleg) als Reihe `ifo_geschaeftsklima` in serien.csv und zeitreihe_lang.csv.

ifo.de und seine Zeitreihen-Downloads liegen hinter einer Browserprüfung (nicht umgangen); neue Monatswerte werden daher in
ifo_geschaeftsklima.csv eingetragen (Termine siehe konjunkturindikatoren.csv). Aufruf: python3 -I abruf_ifo.py"""
import csv
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import AUS, lies, schreibe  # noqa: E402


def main():
    zeilen = sorted((r["zeit"], float(r["wert"])) for r in lies("ifo_geschaeftsklima.csv"))
    heute = date.today().isoformat()
    meta = [{"serie_id": "ifo_geschaeftsklima", "thema": "nachfrage", "name": "ifo Geschäftsklimaindex", "einheit": "Punkte (2015 = 100)", "format": "zahl1",
             "art": "index", "frequenz": "M", "kern": 1, "quelle": "ifo", "datensatz": "ifo-Konjunkturtest", "filter": "Deutschland, gewerbliche Wirtschaft",
             "url": "https://www.ifo.de/umfrage/ifo-geschaeftsklima-deutschland", "stand_quelle": zeilen[-1][0], "abruf": heute,
             "erster_zeitraum": zeilen[0][0], "letzter_zeitraum": zeilen[-1][0], "anzahl": len(zeilen),
             "hinweis": "Lücken: nur erfasste Monate (Quelle je Monat in ifo_geschaeftsklima.csv); vollständige Reihe als Download auf ifo.de"}]
    schreibe("ifo", meta, [("ifo_geschaeftsklima", "DE", z, w) for z, w in zeilen])
    print(len(zeilen), "Monate")


if __name__ == "__main__":
    main()
