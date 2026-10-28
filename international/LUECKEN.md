# Offene Lücken und nächste Schritte (28.10.2026)

## Braucht Entscheidung oder Zugang von Robin
* **OECD-Mitgliederliste und Beitrittsdaten** einmal manuell gegen oecd.org prüfen (automatischer Abruf liefert 403, Bot-Schutz wird nicht umgangen).
* **Docker:** `docker-compose.yml` ist in der Cloud-Umgebung nicht ausführbar (kein Docker-Daemon). Lokal auf dem eigenen Rechner einmal starten und den Schnelltest aus dem README durchlaufen.
* **Nutzungsrechte:** Bedingungen von SEC EDGAR, OECD-SDMX und EBA-Hub sind noch nicht rechtlich gelesen (`lizenz_status` ungeprüft).
* **Kontaktadresse im SEC-User-Agent:** Beim Live-Test (SEC, OECD-SDMX, Wikipedia) wurde `robin.leger@gmx.net` aus der Kontoidentität als Kontaktadresse im User-Agent übermittelt, weil die SEC eine echte Adresse verlangt. Bitte bestätigen oder für dauerhafte Läufe eine bewusst gewählte Adresse in `SEC_USER_AGENT` setzen.

## Technisch offen
* SEC: weitere Kennzahlen (Eigenkapital, Umsatz, Jahresüberschuss, Cashflow), mindestens 10 Unternehmen aus verschiedenen Branchen, darunter Banken separat; Stichproben (10 Werte) gegen Originalberichte; Konsolidierungskreis je Filing belegen; Zugriff auf `submissions`-Endpunkt für Filing-Metadaten.
* Frankreich (IFRS/ESEF): noch keine Quelle geprüft. ESEF ist ein Format, kein Download-Endpunkt; nationale Speichermechanismen und deren Bedingungen zuerst klären.
* Wechselkurse: Adapter (EZB) fehlt; die Auswahlregeln (Stichtag/Durchschnitt, Altersgrenze, keine Zukunftskurse) sind in `international_core.py` getestet.
* Deutsche Börsenunternehmen (ohne Zeitreihe): `app/data/unternehmen.json` hat Werte ohne belegten Stichtag und Währungsbasis je Wert; erst nach Zuordnung zum Geschäftsjahr importieren.
* Listings (Börse/MIC/Ticker) für deutsche Unternehmen: die Stammdaten führen nur Yahoo-Ticker; MIC-Zuordnung wäre geraten und wurde nicht importiert. Die Tabelle ist mit Tests für Mehrfachnotierung und Tickerüberschneidung abgesichert.
* Oberfläche: Filter Sitzland/Börsenland/Rechnungslegung/Währung/Kreis; der Export liefert die Felder, die Oberfläche liest sie noch nicht. Vergleichsgruppen im Export verhindern nur, dass Mediane über Währungen gebildet werden, wenn die Oberfläche sie nutzt.
* API (FastAPI, lesend) und Desktop-Länderpakete: erst nach dem Pilot.
* PDF-Extraktion mit Seitennummer, Textausschnitt, Konfidenz: nicht gebaut (in Deutschland bereits Teil der Zeitreihen-Erhebung über `pruefstatus`).
* Bestehende Crawler im Repo nutzen `httpsafe.py` noch nicht.
