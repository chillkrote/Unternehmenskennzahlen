# Prognosegeber der OECD-Länder (Recherche, Stand 30.10.2026)

Erster Schritt für den Ausbau des Terminal-Bereichs „Prognosen“ über Deutschland hinaus. Noch **nicht** im Terminal eingebunden.

Datei: `prognosegeber_oecd.csv` (Schema angelehnt an `prognosen_institute.csv` und `laender.csv`, `geo` in Eurostat-Schreibweise: EL, UK; zusätzlich OECD = Organisationen mit Länderabdeckung, EA20 = Euroraum).

| Spalte | Inhalt |
|---|---|
| `geo`, `land` | Land (alle 38 OECD-Mitglieder, Deutschland nur als Verweis auf `prognosen_institute.csv`) |
| `herausgeber`, `typ` | Zentralbank, Forschungsinstitut, Ministerium/Behörde, Fiskalrat/Haushaltsbüro, Bank/Unternehmen, Umfrage/Panel, Internationale Organisation |
| `publikation`, `prognosegroessen`, `horizont`, `rhythmus` | Was veröffentlicht wird, welche Größen, wie weit voraus, wie oft |
| `url`, `zugang` | Seite der Prognose; Format (API, CSV/XLSX, PDF, HTML) |
| `daten_url` | maschinenlesbarer Zugang, soweit bekannt (API, Datenportal, Excel-Anhang) |
| `prioritaet` | 1 = wichtigster Geber des Landes für den Terminal-Bereich, 2 = ergänzend, 3 = nachrangig oder teils kostenpflichtig |
| `http_status_url`, `http_status_daten`, `geprueft` | Ergebnis der Erreichbarkeitsprüfung (`skripte/pruefe_prognosegeber.py`) |

## Belegstand (wichtig)

- **Geprüft** ist nur, ob die URL antwortet (HTTP-Status). Rund 80 % der Adressen liefern 200.
- **Nicht geprüft** sind Horizont, Rhythmus, Prognosegrößen und Zugangsformat je Zeile. Sie stammen aus dem Fachwissen zu den jeweiligen Publikationen und müssen vor einer Einbindung je Quelle am Dokument bestätigt werden (wie bei der Spalte `beleg` in `prognosen_institute.csv`: hier entspricht jede Zeile dem Beleg „nicht am Primärdokument gelesen“).
- Bei 31 Adressen war die genaue Unterseite nicht mehr vorhanden (404) und wurde automatisch durch die nächsthöhere erreichbare Übersichtsseite ersetzt; der Hinweis nennt die ursprüngliche Adresse.
- Status 403 oder 405 ist meist Bot-Schutz (z. B. OECD.org, OBR, CBO, BLS, RBNZ, Banco de México). Er wurde nicht umgangen; die Seiten sind verlinkt, aber nicht automatisch abrufbar. Status „Fehler: URLError“ (Verbindung gescheitert) kann an der Umgebung oder an der Adresse liegen und ist offen.
- Keine kostenpflichtigen Dienste: Consensus Economics, Bloomberg-/Reuters-Umfragen, IHS Markit, Oxford Economics (nur freie Teile) und BAK/NZIER-Vollversionen sind als nachrangig gekennzeichnet.

## Abdeckung

- 37 Länder ohne Deutschland: alle haben eine Zentralbank, 35 ein Ministerium oder eine Behörde mit eigener Prognose, alle mindestens drei Geber verschiedenen Typs (Zählung aus der CSV; Island und Slowenien-Bank/Lettland u. a. sind teils nur mit der Startseite belegt).
- Ohne eigenes unabhängiges Forschungsinstitut mit freier Prognose gefunden: Australien, Chile, Costa Rica, Tschechien, Island, Israel, Lettland, Litauen, Luxemburg, Mexiko, Norwegen, Portugal, Slowakei, Slowenien. Hier tragen Zentralbank, Ministerium und Banken.
- Internationale Organisationen (OECD, IWF, EU-Kommission, Weltbank, UN, EZB) decken alle Länder gleichmäßig ab; im Terminal ist bisher nur die OECD (Economic Outlook 114 bis 119) eingebunden.

## Maschinenlesbar (beste Kandidaten für die Einbindung)

1. **EZB Data Portal** (Staff Projections und Survey of Professional Forecasters, Euroraum): API und CSV, kein Schlüssel.
2. **Philadelphia Fed SPF** (USA): CSV/XLSX, Konsens bis 10 Jahre.
3. **Fed SEP** (USA) und **CBO** (XLSX): SEP über federalreserve.gov bzw. FRED (kostenloser Schlüssel); CBO-Seite liefert Bots 403.
4. **Bank of England**: Datenbank-Export und Fan-Chart-Excel; **OBR**: Supplementary Tables (403 für Bots).
5. **HM Treasury „Forecasts for the UK economy“**: Konsens von rund 40 Prognostikern, CSV/XLSX.
6. **Norges Bank**, **Statistics Norway** (PxWeb-API), **Riksbank** (API), **SNB** (data.snb.ch), **CPB** (Excel), **RBNZ** (Excel), **Bank of Canada Valet-API**, **Banxico SIE-API** (kostenloser Token), **TCMB EVDS** (kostenloser Schlüssel), **BoK ECOS** (kostenloser Schlüssel).
7. Konsensumfragen: Funcas (Spanien), JCER ESP (Japan), Banxico, Banco de la República, Banco Central de Chile, TCMB: alle als XLSX.

Übrige Geber liefern Prognosen nur als PDF; hier wäre PDF-Auswertung je Quelle nötig.

## Offene Punkte und Lücken

- IWF-WEO ist über imf.org bot-geschützt (nicht umgangen); Alternative DBnomics wurde nicht geprüft.
- Zahlenwerte wurden bewusst noch nicht erhoben (nur Geberliste). Nächster Schritt wäre eine Pilotauswahl, z. B. EZB-SPF, Philadelphia-SPF, HM-Treasury-Konsens, Funcas-Panel und die OECD-Hauptländer.
- Das Schema der Terminal-Tabelle (`prognosen_institute.csv`) ist auf Jahreswerte 2025 bis 2028 mit Spalte `beleg` ausgelegt. Für andere Länder wäre `geo` die Verbindung zu `laender.csv`.
- Banken/Unternehmen (Typ „Bank/Unternehmen“) sind je Land nur beispielhaft; ob weitere aufgenommen werden sollen, ist offen.
- Mehrere Fiskalräte sind nur mit Startseite eingetragen; Prognoserhythmen dort sind unregelmäßig.
