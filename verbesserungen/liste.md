# Verbesserungsliste (Stand 27.10.2026)

Grundlage: `review/2026-10-27_projektreview.md`, Memory-Notizen zu offenen Lücken. Regeln: nur kostenlose Quellen, kein Umgehen von Captcha/Bot-Schutz, IDs nur über `stammdaten/ids.py`, Dokumente ohne Git LFS.
Status: ☐ offen · ◐ in Arbeit · ☑ erledigt · ✋ braucht Robin (siehe unten)
Priorität: Wirkung (W) / Aufwand (A), je 1 (gering) bis 3 (hoch).

## A. Terminal-Verbesserungen und Code (ohne Daten, schnell)
| # | Punkt | W/A | Status |
|---|---|---|---|
| A1 | Links nur `http(s):` zulassen (N11) | 2/1 | ☑ PR #35 |
| A2 | Fünfte Bankengruppe „Förder- und Sonderinstitute“ mit Farbe (N9) | 2/1 | ☑ PR #35 |
| A3 | Abhängigkeiten pinnen `==` (N8) | 2/1 | ☑ PR #35 (Obergrenzen statt Festpinnen, Version in Actions nicht prüfbar) |
| A4 | Ehrlicher User-Agent + robots.txt-Prüfung in Crawlern (N6) | 2/2 | ✋ Rückfrage: ehrlicher UA kann Abrufe von Seiten verringern, die Browser-Kennungen verlangen |
| A5 | `berichte_abrufen.py` streamt Downloads (N7) | 1/1 | ☑ |
| A6 | Plausibilitätsgrenzen für Yahoo-Quoten in `build.py` (M7) | 3/1 | ☑ PR #35 (Quote/Multiple außerhalb Grenzen = leer) |
| A7 | Yahoo-Abgleich: „bestätigt“ nur für das letzte GJ (M6) | 2/2 | ☑ nur das neueste Yahoo-Jahr zählt als bestätigt, ältere Treffer als „nur älteres Jahr“ |
| A8 | Prozent-Einheit je Spalte statt Wert-Heuristik (N4) | 1/2 | ☐ |
| A9 | Prüfskript `pruefung/pruefe.py` (Bilanz geht auf, IDs, index.csv, SHA-256) | 3/2 | ☑ `pruefung/pruefe.py` |
| A10 | Terminal: Export (CSV) der aktuellen Tabelle, Watchlist, Hilfetexte | 2/3 | ◐ CSV-Export je Tabelle ☑, Merkliste (★ im Profil, Filter im Verzeichnis) ☑; Hilfetexte offen |
| A11 | Tests: Smoke-Test (Playwright) als Skript ins Repo | 2/2 | ☑ `app/tests/smoke.js` |

## B. Datenqualität (Reviewbefunde)
| # | Punkt | W/A | Status |
|---|---|---|---|
| B1 | Sechs Sparkassen: Übersicht auf HGB-Bilanz aus CC2 umstellen (M3, PR #30) | 3/1 | ☐ |
| B2 | Bilanzen die nicht aufgehen (LBS NordWest/NordOst, VB Stuttgart): Bilanzgewinn als Posten (M4) | 2/1 | ☐ |
| B3 | Governance-Querverweise/`person_id` (M9) | 2/2 | ☐ |
| B4 | `zeitreihen/README.md`: Status „verankert“ dokumentieren (N3) | 1/1 | ☑ |
| B5 | Doppelt abgelegte PDFs (N5) | 1/2 | ☐ |

## C. Fehlende Daten, die ich selbst im Netz suchen kann
| # | Punkt | W/A | Status |
|---|---|---|---|
| C1 | Fehlende Kurse der 41 Ticker (Alternativ-Ticker/Suffix prüfen) | 3/2 | ✋ Yahoo antwortet aus der Cloud mit 429; die 40 betroffenen Ticker meist neue ISIN/Neunotierung, im nächsten Actions-Lauf prüfen |
| C2 | Dividenden und Aktiensplits (Historie, Yahoo-Chart-API) | 3/2 | ☐ |
| C3 | Indexzugehörigkeit (DAX, MDAX, SDAX, TecDAX) aus Indexlisten | 3/1 | ☑ `universum/indexzugehoerigkeit.csv` + Abweichungsbericht |
| C4 | Stimmrechtsmitteilungen / Directors' Dealings (BaFin-Datenbanken, frei) | 2/3 | ☐ |
| C5 | Governance für restliche DAX/MDAX | 3/3 | ◐ eigener Thread |
| C6 | Ludwigsburg Vorjahres-Bilanzsumme (statt Zeitungswert) | 1/1 | ☐ |
| C7 | Sparkassen/Banken mit nur Vorjahres-Abschluss: neue Veröffentlichungen prüfen | 2/2 | ☐ |
| C8 | Segmentdaten (Umsatz je Segment) aus Berichten | 2/3 | ☐ |
| C9 | ESG-Kennzahlen aus Nachhaltigkeitsberichten (CO2, Frauenquote) | 2/3 | ☐ |
| C10 | Analystenschätzungen: nur frei verfügbare Quellen | 1/3 | ☐ prüfen |

## D. Dokumentation
| # | Punkt | W/A | Status |
|---|---|---|---|
| D1 | Governance-README (Stand, DSGVO-Zweck, Löschregel) | 2/1 | ✋ im Governance-Thread, um Konflikte zu vermeiden |
| D2 | Verbesserungsliste und Rückfrageliste pflegen | 1/1 | ◐ |

## Nicht durch mich lösbar / Rückfragen an Robin ✋
- 753 Berichte aus dem Unternehmensregister (Captcha, eigener Thread, Laptop).
- ~55 Banken ohne frei zugänglichen HGB-Abschluss 2025 (Bot-Schutz: Santander, Hyundai).
- Electron-Update (M12), Release statt Commit für `dist/` (M1) und Workflows (H4/M2) liegen im Workflow-Thread.
- Analystenschätzungen: meist nur kostenpflichtig – ohne Freigabe nicht umgesetzt.
