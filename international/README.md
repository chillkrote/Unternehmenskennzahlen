# Internationale Erweiterung (OECD) – Durchstich

Architektur für alle OECD-Mitgliedsländer mit schrittweise **belegter** Abdeckung. Länderabdeckung ist nicht Unternehmensabdeckung: `coverage.csv` führt je Land nur, was geprüft wurde; Unbekanntes bleibt leer. Stand 28.10.2026.

Ausgangspunkt ist der Arbeitsauftrag „OECD-Erweiterung“ (Übergabe-Entwurf). Er wurde als Entwurf behandelt und geprüft; Abweichungen stehen unten.

## Was jetzt funktioniert (getestet)

| Baustein | Datei | Stand |
|---|---|---|
| Kernmodell PostgreSQL (Schema `international`) | `migrations/001_kernmodell.sql`, `002_metriken.sql` | gegen PostgreSQL 16.15 ausgeführt, Tests grün |
| Rechenregeln (Skalierung, Pence, Perioden, Wechselkurswahl) | `international_core.py` | offline getestet |
| Import der deutschen Daten | `import_de.py` | 743 Unternehmen, 4.802 Fakten aus `zeitreihen/zeitreihe_lang.csv`, `--dry-run`, wiederholbar |
| Abgesicherter HTTP-Abruf | `httpsafe.py` | Allowlist, keine Weiterleitungen, Größen-/Zeitlimit, Retry-After, atomares Speichern, IP-Prüfung für offene Crawler |
| SEC-Adapter (Companyfacts) | `sec.py`, `us_pilot.py` | zehn US-Unternehmen (`us_pilot.csv`, davon zwei Banken) live geladen: Bilanzsumme, Eigenkapital (auch inkl. Minderheiten), Umsatz, Ergebnis, operativer Cashflow, ab 2007; berichtigte Fassungen bleiben erhalten |
| ESEF-Adapter (FR, NL, IT, ES, BE, AT, FI, IE, PT, DK, SE, NO, PL) | `esef.py`, `fr_pilot.py` | je zehn ESEF-Melder (`<kürzel>_pilot.csv`, 126 Unternehmen, Irland nur 6; Finnland ohne ISIN, nur LEI; bereits erfasste Zeilen über `bestand_id` ergänzt, keine neuen Dubletten) live über den Filing-Index filings.xbrl.org geladen (3 bis 9 Einreichungen je Unternehmen, Stichtage 2017 bis 2025); LEI je ISIN gegen GLEIF geprüft |
| Abgleich ESEF | `verify_fr.py`, `pruefung_<kürzel>.csv` | 67 (FR), 63 (NL), 49 (IT), 63 (ES), 63 (BE), 64 (AT), 63 (FI), 37 (IE), 62 (PT), 38 (DK), 66 (SE), 60 (NO), 66 (PL) Werte (jüngste Periode je Unternehmen und Kennzahl) gegen die sichtbaren Zahlen im veröffentlichten iXBRL-Dokument: alle gleich; Poste Italiane und Snam nicht geprüft (Dokument über 250 MB, Status `dokument_nicht_abrufbar`) |
| Abgleich mit Originalfilings | `verify_us.py`, `pruefung_us.csv` | 55 Werte (jüngstes Geschäftsjahr je Unternehmen und Kennzahl) gegen die Finanzberichtsseiten der 10-K: alle gleich (38 über Standardbezeichnung, 17 über gleichen Wert in sinnvoll benannter Zeile) |
| Vergleichsexport `vergleich-v1` | `export_vergleich.py` | deutsche Zeitreihe verlustfrei reproduziert (Regressionstest), plus Sitzland/Standard/Währung/Kreis/Vergleichsgruppe |
| Länder | `oecd_mitglieder.csv`, `coverage.csv` | 38 Mitglieder, Mitgliedschaftsdaten gegen die englische Wikipedia abgeglichen |

Unternehmenstabelle (26.113 Zeilen, Aliase, Prüfmarken) in SQL: siehe `UNTERNEHMENSTABELLE_SQL.md` (`import_unternehmen.py`, `export_unternehmen.py`).

Nicht fertig: Mitarbeiter und aufsichtliche Bankkennzahlen für die USA, Wechselkurs-Adapter (EZB), Oberflächenfilter, API, Desktop-Länderpakete, Börsenunternehmen (siehe `LUECKEN.md`).

## Start (lokal, ohne bezahlten Dienst)

```bash
# 1. Datenbank: entweder Docker (Schritt für Schritt in DOCKER.md; in der Cloud nicht getestet) ...
INTERNATIONAL_DB_PASSWORD='bitte-setzen' docker compose -f international/docker-compose.yml up -d
export INTERNATIONAL_DATABASE_URL="postgresql://postgres:bitte-setzen@127.0.0.1:5433/international"
# ... oder eine vorhandene lokale PostgreSQL-16-Instanz und eine eigene URL.

pip install -r international/requirements.txt
python3 international/db.py                       # Migrationen + 38 OECD-Länder
python3 international/import_de.py --dry-run      # Probelauf, rollt zurück
python3 international/import_de.py                # deutsche Daten importieren

export SEC_USER_AGENT="Ihr Name ihre.adresse@example.org"   # SEC verlangt eine echte Kontaktadresse
export INTERNATIONAL_USER_AGENT="$SEC_USER_AGENT"            # gilt für alle Adapter, SEC_USER_AGENT ist der Ersatz
python3 international/sec.py --cik 926282 --entity U000021 --dry-run   # ein Unternehmen
python3 international/us_pilot.py register        # die zehn US-Pilotunternehmen über stammdaten/ids.py anlegen
python3 international/us_pilot.py import          # laden und importieren (je ca. 4 bis 8 MB, rate-limitiert)
python3 international/verify_us.py                # Abgleich mit den Originalfilings -> pruefung_us.csv

python3 international/fr_pilot.py register [--csv=nl_pilot.csv]   # zehn Pilotunternehmen anlegen (LEI gegen GLEIF geprüft); ohne --csv Frankreich
python3 international/fr_pilot.py import [--csv=nl_pilot.csv]     # ESEF-Einreichungen laden und importieren
python3 international/verify_fr.py [--csv=nl_pilot.csv]           # Abgleich mit den Berichtsdokumenten -> pruefung_<kürzel>.csv

python3 international/export_vergleich.py [--as-of 2025-04-01]   # -> international/export/vergleich-v1.json
```

Tests (offline, ohne Datenanbieter): `INTERNATIONAL_TEST_DATABASE_URL=postgresql://postgres:PW@127.0.0.1:5433/postgres python3 -m unittest discover -s international/tests`. Ohne diese Variable laufen nur die Tests ohne Datenbank (die DB-Tests werden übersprungen). CI: `.github/workflows/international.yml` (PostgreSQL-16-Service).

## Migrationsanleitung

* Migrationen sind nummerierte SQL-Dateien, werden in Dateinamenreihenfolge je Datei in einer Transaktion angewendet und mit SHA-256 in `public.international_migrations` vermerkt. Eine nachträglich geänderte, schon angewendete Datei bricht ab: neue Datei anlegen statt ändern.
* Es gibt kein `DROP` und keine Eingriffe in bestehende Repo-Daten. Das Schema `international` ist neu; `stammdaten/` wird nur gelesen.
* Unternehmens-IDs (`U000123`) werden unverändert als `entity.id` übernommen. Neue Unternehmen nur über `stammdaten/ids.py` registrieren, danach `import_de.py` erneut laufen lassen (Entitäten werden per Upsert fortgeschrieben).
* Backup/Restore: `pg_dump -Fc` / `pg_restore --no-owner`; im Test (`test_backup_und_restore`) wird ein Dump in eine zweite Datenbank zurückgespielt und die Zeilenzahlen verglichen. Objektspeicher (`international/objektspeicher/`, nicht im Git) separat sichern.

## Abweichungen vom Entwurf und Entscheidungen

1. **Zeitraum:** Der Entwurf nennt fünf Geschäftsjahre fürs MVP. Dem Projektstandard (10 Jahre, so vollständig wie möglich) wird gefolgt; der SEC-Adapter lädt alles, was Companyfacts liefert (bei ADTRAN ab 2009).
2. **Schema-Ergänzungen** (in der Migration begründet): `fact.reported_at` und `fact_as_of()` für „bekannt zum“ und berichtigte Abschlüsse; `fact.provenance`; `metric.regulatory` mit Trigger (CET1, RWA, LCR usw. nur mit `consolidation='regulatory'`); `ingestion_run.watermark`; Ausschluss-Constraint gegen überlappende Tickerzuordnungen; Trigger für Periodentyp/Einheit (instant ohne Beginn, duration mit Beginn, Geld braucht ISO-Währung, Quote als Dezimalquote). Zusätzliche Länder außerhalb der OECD (BG, CY, CN, MT) werden als Sitzländer ohne `oecd_from` angelegt.
3. **Einheiten:** deutsche Werte stehen in Mio. EUR; im Modell als EUR, Originalwert und Skalierung in `provenance`. Der Export rechnet wieder in Mio. um.
4. **Konsolidierung:** Companyfacts nennt den Kreis nicht; US-Werte stehen deshalb auf `unknown`, bis ein Abgleich mit dem Abschluss vorliegt. Aufsichtliche Werte (Pillar 3/EBA) sind `regulatory`, HGB-Einzelabschlüsse `solo`.
5. **Abschnitt 7 des Entwurfs** (Tooltip-XSS, Desktop-Quelle, SSRF, Validierung vor Push, Rebase) wurde nicht erneut umgesetzt; dafür gelten die Entwurfs-PRs #43 bis #47. `httpsafe.py` ist der neue sichere Downloader für die internationalen Adapter; die bestehenden Crawler wurden nicht umgestellt.
6. **Quellenzugriff:** oecd.org liefert für automatische Abrufe HTTP 403 (Bot-Schutz, wird nicht umgangen). Die Mitgliedschaftsdaten stammen aus der Tabelle „Current members“ der englischen Wikipedia (Seite OECD, Stand 28.10.2026), die die OECD-Ratifizierungsliste zitiert; alle 38 Länder stimmen mit der Liste und mit den ISO3-Codes im OECD-SDMX-Codelist `CL_AREA` überein. Dabei sind die Gründungsdaten der Gründungsländer auf deren einzelne Ratifizierungsdaten korrigiert worden. Eine Prüfung gegen oecd.org selbst steht aus.
7. **US-Pilot:** Exxon Mobil wurde nicht gewählt, weil die SEC unter dem Ticker XOM inzwischen die ExxonMobil Holdings Corp (CIK 2115436) führt und die Zuordnung der ISIN zur CIK nicht belegt ist; stattdessen Chevron.
8. **Umsatz** ist der erste vorhandene Tag aus `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`, `SalesRevenueNet`, `SalesRevenueGoodsNet` (je Filing und Periode, nie gemischt; der Tag steht in `provenance`). Er ist damit je Unternehmen der ausgewiesene Umsatz, nicht immer der Gesamtertrag (Walmart: Net sales 706,4 Mrd. USD, nicht Total revenues 713,2 Mrd.). Für Banken wird kein Umsatz geladen.

9. **ESEF-Länder (FR, NL, IT, ES, BE, AT, FI, IE, PT, DK, SE, NO, PL):** Als Quelle dient der Filing-Index filings.xbrl.org (ESEF-Berichte mit xBRL-JSON, Länderfilter FR, NL, IT, ES, BE, AT, FI, IE, PT, DK, SE, NO, PL) und die GLEIF-API. Die amtliche französische Stelle (info-financiere.fr) war über den Proxy nicht erreichbar und wurde nicht genutzt. Der Index hat Lücken und führt `period_end` teils falsch; maßgeblich sind die Perioden der Fakten (OIM: Stichtag = Beginn des Folgetags, wird umgerechnet). Der Konsolidierungskreis ist `group`, abgeleitet aus der ESEF-Pflicht zum konsolidierten IFRS-Abschluss und der Beschränkung auf dimensionslose Fakten. Für ältere Einreichungen ohne Veröffentlichungsdatum dient `date_added` als Näherung für „bekannt seit“ (steht in `provenance`).
10. **Lizenz:** Die Seite filings.xbrl.org trägt „© XBRL“, eine Lizenz für die Wiederverwendung wurde nicht gefunden. Die Rohdaten liegen deshalb nur im ungetrackten Objektspeicher, nicht im Git; der Test-Auszug enthält 33 Fakten eines Unternehmens.

## Kosten

Bisher keine laufenden Kosten: lokale PostgreSQL, öffentliche Quellen (SEC EDGAR, OECD-SDMX), kein bezahlter Dienst. Zahlen für Speicher, Abruffrequenz und Lizenzen lassen sich erst nach dem Pilot aus gemessenen Größen ableiten (eine SEC-Companyfacts-Antwort hat rund 5 MB; Nutzungsbedingungen der Quellen sind in `coverage.csv` als „ungeprüft“ geführt). Kommerzielle Datenanbieter (LSEG, FactSet, S&P) wurden weder angefragt noch gebucht.

## Weitere Dokumente

* `MAPPING.md` – Mappingkatalog (Kennzahlen, Quelle, Tag/Spalte, Status)
* `LUECKEN.md` – offene Lücken, Entscheidungen und nächste Schritte
* `coverage.csv` – eine Zeile je OECD-Land
