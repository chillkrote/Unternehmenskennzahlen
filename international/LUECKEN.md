# Offene Lücken und nächste Schritte (28.10.2026)

## Braucht Entscheidung oder Zugang von Robin
* **OECD-Mitgliederliste:** gegen die englische Wikipedia geprüft (alle 38 Länder und Daten stimmen). Eine Prüfung gegen oecd.org selbst steht aus (automatischer Abruf liefert 403, Bot-Schutz wird nicht umgangen).
* **Docker:** `docker-compose.yml` ist in der Cloud-Umgebung nicht ausführbar (kein Docker-Daemon). Lokal einmal nach `DOCKER.md` durchlaufen.
* **Nutzungsrechte:** Bedingungen von SEC EDGAR, OECD-SDMX und EBA-Hub sind noch nicht rechtlich gelesen (`lizenz_status` ungeprüft).
* **Kontaktadresse im SEC-User-Agent:** Beim Live-Test (SEC, OECD-SDMX, Wikipedia) wurde `robin.leger@gmx.net` aus der Kontoidentität als Kontaktadresse im User-Agent übermittelt, weil die SEC eine echte Adresse verlangt. Bitte bestätigen oder für dauerhafte Läufe eine bewusst gewählte Adresse in `SEC_USER_AGENT` setzen.

## Technisch offen
* SEC: Pilot mit zehn Unternehmen (ADTRAN, Apple, Microsoft, JPMorgan, Bank of America, Johnson & Johnson, Chevron, Walmart, Coca-Cola, Caterpillar) geladen und für das jüngste Geschäftsjahr geprüft (`pruefung_us.csv`). Für den Pilotstatus fehlen:
  * Stichproben für ältere Jahre (bisher nur das jüngste Geschäftsjahr je Unternehmen und Kennzahl).
  * Mitarbeiter und aufsichtliche Bankkennzahlen (CET1, RWA, Quoten) für die zwei Banken; Companyfacts enthält sie nicht, die Quelle (z. B. Pillar-3-/FR Y-9C-Berichte) ist noch nicht geprüft.
  * Lücken je Unternehmen: Eigenkapital der Muttergesellschafter fehlt bei Caterpillar und Johnson & Johnson und endet bei ADTRAN 2021; Ergebnis der Muttergesellschafter fehlt bei Caterpillar nach 2010 (dort `net_income_incl_nci` vorhanden); Umsatz fehlt bei den Banken absichtlich. Es gilt: fehlende Werte bleiben leer, nichts wird aus anderen Tags ersetzt.
  * Konsolidierungskreis ist `unknown`, bis er je Filing belegt ist.
  * Pro Unternehmen sind rund 4 bis 8 MB Rohdaten nötig (Objektspeicher, nicht im Git).
* Frankreich: Pilot mit zehn ESEF-Meldern geladen und das jüngste Geschäftsjahr je Unternehmen und Kennzahl gegen das veröffentlichte Berichtsdokument geprüft (`pruefung_fr.csv`). Offen: Stichproben älterer Jahre und eine unabhängige Zweitquelle (z. B. Universal-Registration-Document-PDF); lückenhafter Index (Capgemini ohne 2023 und 2025, LVMH, Orange und Capgemini ohne 2025); Sanofi ohne Umsatz (Erweiterungskonzept); weniger als zehn Jahre, weil ESEF erst ab 2020 verbreitet ist (ältere Jahre nur als Vergleichswerte in späteren Berichten); Mitarbeiter und aufsichtliche Bankkennzahlen; Lizenz des Index ungeklärt; die amtliche Stelle info-financiere.fr wurde wegen Netzwerkblockade nicht geprüft.
* Wechselkurse: Adapter (EZB) fehlt; die Auswahlregeln (Stichtag/Durchschnitt, Altersgrenze, keine Zukunftskurse) sind in `international_core.py` getestet.
* Deutsche Börsenunternehmen (ohne Zeitreihe): `app/data/unternehmen.json` hat Werte ohne belegten Stichtag und Währungsbasis je Wert; erst nach Zuordnung zum Geschäftsjahr importieren.
* Listings (Börse/MIC/Ticker) für deutsche Unternehmen: die Stammdaten führen nur Yahoo-Ticker; MIC-Zuordnung wäre geraten und wurde nicht importiert. Die Tabelle ist mit Tests für Mehrfachnotierung und Tickerüberschneidung abgesichert.
* Oberfläche: Filter Sitzland/Börsenland/Rechnungslegung/Währung/Kreis; der Export liefert die Felder, die Oberfläche liest sie noch nicht. Vergleichsgruppen im Export verhindern nur, dass Mediane über Währungen gebildet werden, wenn die Oberfläche sie nutzt.
* API (FastAPI, lesend) und Desktop-Länderpakete: erst nach dem Pilot.
* PDF-Extraktion mit Seitennummer, Textausschnitt, Konfidenz: nicht gebaut (in Deutschland bereits Teil der Zeitreihen-Erhebung über `pruefstatus`).
* Bestehende Crawler im Repo nutzen `httpsafe.py` noch nicht.
