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

## Pilot mit Zahlen (30.10.2026)

`prognosen_international.csv` wird von `skripte/abruf_prognosen_international.py` erzeugt (Rohdateien unverändert in `rohdaten/prognosen/`). Jede Zahl stammt aus dem Primärdokument oder der API des Herausgebers, nicht aus Presse.

| Quelle | Land | Ausgabe | Größen | Besonderheit |
|---|---|---|---|---|
| EZB Survey of Professional Forecasters | Euroraum | Runden 2025-Q4 bis 2026-Q4 | BIP, HVPI, Arbeitslosigkeit | API ohne Schlüssel; Mittelwert, 2026 bis 2028 und langfristig |
| Philadelphia Fed SPF | USA | Q3 2026 (14.8.2026) | BIP, Arbeitslosigkeit, VPI, PCE | Median, aus dem PDF gelesen |
| Federal Reserve SEP | USA | 16.9.2026 | BIP, Arbeitslosigkeit, PCE, Leitzins | Median bis 2029 und langfristig |
| HM Treasury Konsens | UK | Oktober 2026 (21.10.2026) | BIP, VPI, Arbeitslosigkeit | 30 Einzelprognostiker (Banken, Institute, OBR, IWF, OECD) plus Durchschnitt und Median, 2026 und 2027 |
| Funcas Panel | Spanien | September 2026 (16.9.2026) | BIP, VPI, Arbeitslosigkeit, Finanzierungssaldo | 19 Einzelpanelisten, Konsens, zitierte Regierung, Banco de España, AIReF, EU-Kommission, IWF, OECD |
| Bank of Canada MPR | Kanada | 28.10.2026 | BIP, VPI | Q4 gegenüber Vorjahres-Q4, 2026 bis 2028 |
| Bank of Japan Outlook | Japan | 30.10.2026 | BIP, VPI ohne Frischwaren | Median der Vorstandsprognosen, Fiskaljahre (April bis März) |
| EZB/Eurosystem-Stabsprognosen | Euroraum | Runden Sep 2025 bis Sep 2026 | BIP, HVPI, Arbeitslosigkeit, Finanzierungssaldo | Annex-Excel der jeweiligen Runde |
| Nationale Zentralbanken des Euroraums (Bundesbank, Banque de France, Banca d'Italia, Banco de España, DNB, OeNB u. a.) | 17 OECD-Länder im Euroraum | Eurosystem-Runden Juni und Dezember, Juni 2024 bis Juni 2026 | BIP, HVPI, Arbeitslosenquote | EZB Macroeconomic Projections Database (API); Kennung der Runde: Buchstabe plus Jahr (W = März, G = Juni, S = September, A = Dezember), über den Vergleich mit den Annex-Dateien bestimmt |
| Bank of England MPR | UK | Juli 2026 | VPI, BIP, Arbeitslosenquote, Bank Rate | Projektion für das jeweils dritte Quartal (Vierquartalswerte), nicht Kalenderjahre |
| SECO Expertengruppe | CH | Sep 2026 (und Jun 2026 aus dem Klammerwert) | BIP (Sportevent-bereinigt), VPI, Arbeitslosenquote | Kalenderjahre, aus dem PDF-Anhang der Medienmitteilung |
| Riksbank (offene API) | SE | alle Runden 2015:1 bis 2026:3 | BIP, CPIF, VPI, Arbeitslosenquote, Leitzins, Finanzierungssaldo | Jahreswerte aus den Quartals- bzw. Monatsreihen der API berechnet |

Vergleichbarkeit: Die Basis (Jahresdurchschnitt oder Q4/Q4) steht je Zeile im `hinweis`. Die Reihen verschiedener Geber sind deshalb nicht ohne Weiteres gleichzusetzen.

### Nicht aufgenommen und warum

- **OECD Economic Outlook:** läuft bereits über die OECD-SDMX-API (`sdmx.oecd.org`, ohne Schlüssel) in `prognosen_oecd.csv` (Ausgaben 114 bis 119, alle Mitglieder). Die Webseite oecd.org bleibt für Bots gesperrt, die API nicht; auf sie wird nicht verzichtet.
- **Banque de France, Septemberprojektion 2026:** banque-france.fr liefert Bots „Access Denied“ (Akamai), nicht umgangen. Die Juni-Runde (Eurosystem) liegt über die EZB-Datenbank vor.
- **Bundesbank:** Die Juni-Werte der EZB-Datenbank stimmen mit den bisherigen Presseangaben in `prognosen_institute.csv` überein (BIP 0,5 / 0,8 / 1,4; HVPI 2,9 / 2,7 / 1,9) und sind nun am API-Beleg bestätigt.
- **Zwischenrunden der nationalen Zentralbanken** (März und September) veröffentlicht die EZB nur für den Euroraum; die Länderwerte gibt es nur für Juni und Dezember.
- **Bank of England:** Die Ausgabe vom November 2026 ist noch nicht veröffentlicht; die Seiten der Ausgaben wechseln das Muster (2026: Februar, April, Juli).
- **Weiter offen:** Banca d'Italia, Banco de España und die übrigen Zentralbanken außerhalb der Euro-Runden (Bulletin-Prognosen im Januar, April, Juli, Oktober), Zentralbanken und Institute der übrigen OECD-Länder (Australien, Neuseeland, Schweiz, Schweden, Norwegen, Korea, Mexiko, Chile, Türkei u. a.) und Ministerien.
- **Funcas-Zahlen** sind spanische Kommastellen im PDF, in der CSV mit Punkt.
