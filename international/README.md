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
| SEC-Adapter (Companyfacts, Bilanzsumme) | `sec.py` | live für ADTRAN Holdings (U000021, CIK 926282) abgerufen, 36 Fassungen; 3 Werte gegen Bilanzen der 10-K/10-K/A geprüft |
| Vergleichsexport `vergleich-v1` | `export_vergleich.py` | deutsche Zeitreihe verlustfrei reproduziert (Regressionstest), plus Sitzland/Standard/Währung/Kreis/Vergleichsgruppe |
| Länder | `oecd_mitglieder.csv`, `coverage.csv` | 38 Mitglieder |

Nicht fertig: Pilot Frankreich, weitere US-Unternehmen, Kennzahlen außer Bilanzsumme für die USA, Wechselkurs-Adapter (EZB), Oberflächenfilter, API, Desktop-Länderpakete, Börsenunternehmen (siehe `LUECKEN.md`).

## Start (lokal, ohne bezahlten Dienst)

```bash
# 1. Datenbank: entweder Docker (nicht in der Cloud-Umgebung getestet) ...
INTERNATIONAL_DB_PASSWORD='bitte-setzen' docker compose -f international/docker-compose.yml up -d
export INTERNATIONAL_DATABASE_URL="postgresql://postgres:bitte-setzen@127.0.0.1:5433/international"
# ... oder eine vorhandene lokale PostgreSQL-16-Instanz und eine eigene URL.

pip install -r international/requirements.txt
python3 international/db.py                       # Migrationen + 38 OECD-Länder
python3 international/import_de.py --dry-run      # Probelauf, rollt zurück
python3 international/import_de.py                # deutsche Daten importieren

export SEC_USER_AGENT="Ihr Name ihre.adresse@example.org"   # SEC verlangt eine echte Kontaktadresse
python3 international/sec.py --cik 926282 --entity U000021 --dry-run
python3 international/sec.py --cik 926282 --entity U000021

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
6. **Quellenzugriff:** oecd.org liefert für automatische Abrufe HTTP 403 (Bot-Schutz, wird nicht umgangen). Die Mitgliederliste (38 Länder) stützt sich deshalb auf die öffentliche Darstellung (Wikipedia, Stand 28.10.2026: 38 Mitglieder) und den Abgleich der ISO3-Codes mit dem OECD-SDMX-Codelist `CL_AREA`. Beitrittsdaten sind nicht gegen oecd.org geprüft. Vor produktiver Nutzung bitte einmal manuell gegen https://www.oecd.org/en/about/members-partners.html prüfen.

## Kosten

Bisher keine laufenden Kosten: lokale PostgreSQL, öffentliche Quellen (SEC EDGAR, OECD-SDMX), kein bezahlter Dienst. Zahlen für Speicher, Abruffrequenz und Lizenzen lassen sich erst nach dem Pilot aus gemessenen Größen ableiten (eine SEC-Companyfacts-Antwort hat rund 5 MB; Nutzungsbedingungen der Quellen sind in `coverage.csv` als „ungeprüft“ geführt). Kommerzielle Datenanbieter (LSEG, FactSet, S&P) wurden weder angefragt noch gebucht.

## Weitere Dokumente

* `MAPPING.md` – Mappingkatalog (Kennzahlen, Quelle, Tag/Spalte, Status)
* `LUECKEN.md` – offene Lücken, Entscheidungen und nächste Schritte
* `coverage.csv` – eine Zeile je OECD-Land
