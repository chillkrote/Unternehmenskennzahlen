# Volkswirtschaftliche Kennzahlen

Zeitreihen, Prognosen und Konjunkturindikatoren für das Terminal-Modul „Volkswirtschaft“. Alle Quellen sind frei zugänglich und ohne Schlüssel nutzbar; Bot-Sperren (BMWE, ifo.de, imf.org) werden nicht umgangen, diese Seiten sind nur verlinkt.

## Dateien

| Datei | Inhalt |
|---|---|
| `serien.csv` | Katalog: je Reihe Thema, Name, Einheit, Format, Takt, Quelle, Datensatz, Filter, Abruf-URL, Abrufdatum, Zeitraum, `prognose_ab` (erster Projektionszeitraum), Hinweis |
| `zeitreihe_lang.csv` | Langformat `serie_id, geo, zeit, wert` (Monat `2026-09`, Quartal `2026-Q2`, Jahr `2025`); Quelle, Abrufdatum und Einheit je Reihe stehen in `serien.csv` |
| `laender.csv` | `geo, name, oecd` (alle 38 OECD-Mitglieder, Euroraum, EU-27, OECD gesamt, G7; ISO-2-Codes in Eurostat-Schreibweise: EL, UK) |
| `themen.csv` | Themenbezeichnungen |
| `prognosen_institute.csv` | Prognosen für Deutschland (handgepflegt, eine Zeile je Ausgabe und Größe): Herausgeber, Ausgabe, Veröffentlichung, Jahreswerte 2025 bis 2028, `beleg` (Primärdokument oder Presse), URL, Hinweis. Ältere Ausgaben bleiben stehen |
| `prognosen_international.csv` | Pilot: Prognosen internationaler Geber im Langformat (wie `prognosen_oecd.csv`, plus `hinweis`): EZB-SPF (Euroraum), Philadelphia-Fed-SPF und Fed-SEP (USA), HM-Treasury-Konsens mit 30 Einzelprognostikern (UK), Funcas-Panel mit 19 Panelisten (Spanien), Bank of Canada, Bank of Japan. Rohdateien in `rohdaten/prognosen/`. Liste aller Geber: `prognosegeber_oecd.csv`, siehe `PROGNOSEGEBER.md` |
| `prognosen_oecd.csv` | Economic Outlook, Ausgaben 114 bis 119 (Nov. 2023 bis Juni 2026), alle OECD-Länder: BIP, Inflation, Arbeitslosenquote, Finanzierungssaldo (vom Skript geschrieben) |
| `konjunkturindikatoren.csv` | ifo, ZEW, Konsumklima, PMI u. a.: aktueller Wert, Vorwert, Veröffentlichung, nächste Termine, Link und Beschreibung (handgepflegt) |
| `ifo_geschaeftsklima.csv` | erfasste Monatswerte des ifo-Index mit Beleg (handgepflegt) |
| `berichte.csv` | regelmäßige Berichte mit Link (Bundesbank, Destatis, Institute, EU-Kommission, IWF, OECD) |
| `rohdaten/eurostat/*.json.gz`, `rohdaten/oecd/*.csv.gz` | unveränderte API-Antworten je Reihe |

## Abruf

```
python3 -I volkswirtschaft/skripte/abruf_eurostat.py   # europäische Länder (EU, EFTA, UK, TR), 27 Reihen
python3 -I volkswirtschaft/skripte/abruf_oecd.py       # alle OECD-Länder, 28 Reihen + Economic-Outlook-Ausgaben
python3 -I volkswirtschaft/skripte/abruf_prognosen_international.py   # Pilot Konsens und G7-Zentralbanken (braucht openpyxl, pdftotext)
python3 -I volkswirtschaft/skripte/abruf_ifo.py        # ifo-Reihe aus ifo_geschaeftsklima.csv
python3 app/build.py                                   # Terminal neu bauen
```

Jedes Skript ersetzt nur die Reihen seiner Quelle (`skripte/gemeinsam.py`), sie laufen einzeln und in beliebiger Reihenfolge. **Neue Reihe = ein Eintrag in `SERIEN`** (`s(...)` bzw. `eo(...)` in `abruf_oecd.py`, `s(...)` in `abruf_eurostat.py`); das Terminal liest die CSV ohne Codeänderung. Neue Economic-Outlook-Ausgabe = eine Zeile in `EO_AUSGABEN` und `EO_PROGNOSE_AB` anpassen. Die OECD begrenzt Abrufe (rund 60 pro Stunde); `abruf_oecd.py` braucht etwa 35.

## Reihen

- Eurostat (europäische OECD-Länder, seit 2005): BIP und Verwendung, HVPI nach Komponenten, Erzeugerpreise, Arbeitslosenquote, Arbeitskosten, Erwerbstätige, Einzelhandel, Produktion, Bau, Stimmung, Euribor, Schulden- und Defizitquote.
- OECD (alle Mitglieder): BIP-Wachstum (Quartal), Inflation und Kerninflation, Arbeitslosigkeit gesamt und Jugend (Monat), Frühindikator CLI, Geschäfts- und Verbrauchervertrauen, dazu 20 Jahresreihen aus dem Economic Outlook 119 (BIP, Inflation, Zinsen, Staatssaldo und -schuld, Leistungsbilanz, Konsum, Investitionen, Sparquote, Produktivität u. a.) mit Projektionen ab 2026.
- ifo Geschäftsklimaindex: nur erfasste Monate (Quelle und Beleg je Monat).

Wo Eurostat und OECD dieselbe Größe liefern (BIP, HVPI/CPI, Arbeitslosenquote), gilt im Terminal Eurostat für europäische Länder und die OECD-Reihe für alle übrigen (USA, Japan, Kanada, …).

## Prognosen für Deutschland

Stand 27.10.2026: Gemeinschaftsdiagnose (Herbst und Frühjahr 2026), Bundesregierung, Sachverständigenrat, ifo, IfW Kiel, DIW, RWI, IWH, IW Köln, IMK, Bundesbank, EU-Kommission, IWF, OECD, jeweils mit Vorgängerausgaben soweit gefunden. Spalte `beleg`: *Primärdokument* = PDF oder Seite des Herausgebers gelesen (Gemeinschaftsdiagnose, Sachverständigenrat, IMK, DIW, OECD-API), *Presse* = Zahlen aus Pressemeldungen und nicht am Original geprüft. Abgeleitete Werte (z. B. Sommerprognose aus der Revisionsangabe der Herbstprognose) sind im Hinweis gekennzeichnet. Lücken: IWH, IW Köln, ifo Sommer und EU-Kommission nur lückenhaft; Inflationsangabe der Herbstprojektion der Bundesregierung nur aus einer Fachmeldung.

## Grenzen

- Der Euroraum ist bei Eurostat je Datensatz EA20 oder EA21 (Arbeitslosenquote); Arbeitskosten und Euribor liegen nicht für alle Länder vor; der CLI nur für 13 Länder.
- Länder- und Reihenstand unterscheiden sich (Stand je Zeile im Terminal).
- ifo-Zeitreihe (xlsx), GENESIS (Anmeldung) und IWF-Datenabruf sind nicht automatisch erreichbar; Werte und Termine des ifo-Index wurden von der ifo-Seite übernommen, Lage- und Erwartungsindex liegen nur qualitativ vor.
- Jahreswerte des Economic Outlook gelten für den Stand EO 119 (Juni 2026); ab 2026 Projektion.
