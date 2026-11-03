# Konzept: Strom und Pipelines auf der Weltkugel

Stand: 03.11.2026 · Entwurf · reines Konzept, kein Code

Ergänzt [weltkugel_handelsrouten_konzept.md](weltkugel_handelsrouten_konzept.md). Gleiche Regeln: nur frei verfügbare Quellen, keine kostenpflichtigen Dienste, Lizenzen nach Kenntnisstand und **vor dem Einbau je Quelle zu prüfen**. Gleiche Struktur: Tabellen `verkehr_knoten`, `verkehr_kante`, `verkehr_fluss` mit `modus = strom | pipeline_gas | pipeline_oel`.

## 1. Was gezeigt werden soll

- **Stufe 3 (Auftrag):** Stromimporte und Stromexporte je Land und Nachbarland, als grenzüberschreitende Leitungen.
- **Stufe 2 (Vorschlag):** Die drei größten Stromimport- und -exportpartner je Land als Linien, wie bei Waren. Große Öl-/Gaspipelines als Hauptachsen (z. B. Nord Stream, Druschba, Power of Siberia, TurkStream, Transmed, Keystone).
- **Stufe 1 (Vorschlag):** Nur die Kontinent-Summen, getrennt von Schiff/Bahn/Straße/Luft zuschaltbar. Strom ist dort fast ausschließlich innerhalb eines Kontinents, also kaum sichtbar; Pipelines nur als wenige Hauptachsen (Russland–Europa, Golf–Asien, Nordamerika).

## 2. Besonderheit gegenüber Waren

Strom und Pipelines sind **leitungsgebunden**: Der Weg ist durch das Netz fest vorgegeben, es gibt kein Routing und keinen Modal-Split. Dafür gibt es bei Strom echte Messwerte (physische Flüsse je Grenze), die Modellierung entfällt weitgehend. Zwei Wertarten bleiben getrennt: **physische Flüsse** (MWh, was tatsächlich über die Leitung ging) und **kommerzielle/Handelswerte** (USD aus Comtrade, HS 2716). Beide sind nicht dasselbe, die Oberfläche beschriftet sie entsprechend.

## 3. Quellen (frei verfügbar)

### 3.1 Strom

| Quelle | Inhalt | Nutzen | Format | Lizenz (Kenntnisstand) | Aktualität | Prüfen |
|---|---|---|---|---|---|---|
| ENTSO-E Transparency Platform | physische Grenzflüsse und Handelsfahrpläne Europas, stündlich | Messwert | REST-API (XML), kostenlos, Registrierung mit Sicherheitstoken | freie Weiterverwendung für eine Liste von (TSO-)Daten, Liste prüfen (Stand 03.11.2026 nicht vollständig gelesen) | stündlich bis täglich | Token als Secret ablegen; Abfragegrenze (laut Nutzergruppe 2019: 400 Anfragen/Minute) |
| Ember (Electricity Data Explorer) | Stromimporte/-exporte je Land, Erzeugung, jährlich und monatlich, weltweit | Messwert, Kontext | CSV | CC BY 4.0 (geprüft 03.11.2026); Downloadformat im Juli 2026 geändert | zweimal im Monat | Abdeckung der Länder, neues Format |
| Eurostat (`nrg_ti_eh`, `nrg_te_eh`) | Stromimporte/-exporte der EU-Länder nach Partnerland | Messwert | TSV/JSON | CC BY 4.0 | jährlich | Tabellencodes |
| EIA (USA, Open Data, EIA-930) | Stromaustausch der US-Regelzonen mit Kanada/Mexiko | Messwert | CSV/API | US-Behörde, gemeinfrei | stündlich/täglich | API-Schlüssel (kostenlos) |
| UN Comtrade (im Projekt), HS 2716 | Handelswert Strom bilateral | Kontext | JSON | frei | jährlich | – |
| OpenStreetMap (`power=line`, `power=cable`, `power=substation`) | Hochspannungsnetz, Umspannwerke, Seekabel | Geometrie | PBF/GeoJSON | ODbL | täglich | nur Leitungen ab 220 kV und grenzüberschreitende übernehmen |
| Global Power Plant Database (WRI) | Kraftwerke weltweit | Geometrie (Stufe 3) | CSV | CC BY 4.0 | statisch (2021) | Aktualität begrenzt |

Nicht verwenden: IEA-Datensätze (kostenpflichtig oder eingeschränkt), kommerzielle Netzdienste.

### 3.2 Pipelines (Öl, Gas)

| Quelle | Inhalt | Nutzen | Format | Lizenz | Aktualität | Prüfen |
|---|---|---|---|---|---|---|
| Global Energy Monitor: Global Oil Infrastructure Tracker und Global Gas Infrastructure Tracker | Trassen, Kapazität, Status (in Betrieb/gebaut/geplant) | Geometrie, Kapazität | GeoJSON/Excel, Download über Formular | CC BY 4.0 (geprüft 03.11.2026); Öl-Tracker wird jährlich aktualisiert | jährlich bis halbjährlich | Status-Feld nutzen; Adresse der Download-Seite neu suchen |
| ENTSOG Transparency Platform | physische Gasflüsse an Grenzpunkten Europas | Messwert | API/CSV | frei, Quelle nennen | täglich | Lizenzwortlaut |
| EIA | US-Gas/Öl-Pipelineflüsse und -importe nach Grenzpunkt | Messwert | CSV | gemeinfrei | monatlich | – |
| Eurostat (`nrg_ti_gas`, `nrg_ti_oil`) | Gas-/Ölimporte der EU nach Partnerland | Messwert | TSV | CC BY 4.0 | jährlich/monatlich | – |
| UN Comtrade, HS 2709/2711 | Handelswert Rohöl/Gas, auch per Schiff (LNG, Tanker) | Kontext | JSON | frei | jährlich | Anteil Pipeline vs. Schiff nicht enthalten |

Pipeline- und Schiffsanteil bei Öl/Gas wird je Land aus Eurostat/EIA abgeleitet und sonst als `modelliert` markiert. LNG- und Öltanker laufen über das Seenetz des Handelsrouten-Konzepts (Hormus, Suez, Malakka).

## 4. Datenmodell (Ergänzung)

```
verkehr_knoten     typ += umspannwerk | konverterstation | verdichterstation | grenzpunkt_gas | raffinerie | lng_terminal
verkehr_kante      modus = strom | pipeline_gas | pipeline_oel
                   zusatzfelder: spannung_kv, gleichstrom (ja/nein), durchmesser_mm, kapazitaet_mw bzw. kapazitaet_bcm/mbd, status
verkehr_fluss      einheit = MWh | GWh | TJ | Mio. m3 | Tonnen ; zusätzlich wert_usd (Comtrade)
                   art = physisch | handel
                   methode = gemessen | abgeleitet | modelliert
```

Grenzüberschreitende Strom- und Gasflüsse hängen an **Grenzkuppelstellen** (Knoten `grenzuebergang` mit Modus `strom`/`pipeline_gas`). Dadurch zeigen Nachbarländer (Stufe 3) Waren und Energie in derselben Tabelle.

## 5. Darstellung in den Zoomstufen

| Stufe | Strom | Pipelines |
|---|---|---|
| 1 | nur Kontinentsummen in der Auswahlansicht, schaltbar | wenige Hauptachsen als dicke, ruhige Linien |
| 2 | Top 3 Import-/Exportpartner je Land, als gebündelte Bögen | alle großen Fernleitungen, Engstellen mit Namen (z. B. Ukraine-Transit) |
| 3 | grenzüberschreitende Leitungen mit Richtung und Fluss, Seekabel (NordLink, NorNed, Viking Link), Umspannwerke | Trassen mit Kapazität/Status, Verdichter, LNG-Terminals, Raffinerien |

Strom hat eigene Farbe (nicht die der Verkehrsträger), Pfeilrichtung nach Netto-Fluss, Linienbreite nach Jahresenergie. Zeitreihen: Monats- bzw. Jahresschalter; Tageswerte nur auf Klick, damit die Datenmenge klein bleibt.

## 6. Reihenfolge und Aufwand

| Phase | Inhalt | Aufwand (Arbeitstage) |
|---|---|---|
| S0 | Quellen/Lizenzen prüfen, ENTSO-E-Token besorgen (kostenlos, Robin legt ihn als Secret an), Länderliste | 1 |
| S1 | Strom Europa: Grenzkuppelstellen, ENTSO-E/Eurostat/Ember, Stufe-2/3-Darstellung | 4–5 |
| S2 | Strom Rest der Welt: Ember (Länderebene), EIA (Nordamerika), OSM-Leitungen für Grenzkuppelstellen | 3–4 |
| S3 | Pipelines: GEM-Trassen, ENTSOG/EIA/Eurostat-Flüsse | 4–5 |
| S4 | Verzahnung mit Handelsrouten (LNG/Tanker, Grenzpunkte, Nachbarländer-Tabelle) | 2–3 |

Summe etwa 14–18 Arbeitstage. Empfehlung: nach Phase 1 des Handelsrouten-Konzepts, weil Stufe-3-Nachbarländer und Grenzpunkte gemeinsam genutzt werden.

## 7. Grenzen und Risiken

- **Physisch ≠ kommerziell:** Strom fließt nach Physik (Transit durch Dritte), gehandelt wird nach Verträgen. Beide getrennt anzeigen.
- **Abdeckung:** Außerhalb Europas, USA und weniger Länder gibt es keine stündlichen Grenzflüsse; dort nur Jahreswerte aus Ember/Comtrade, `abgeleitet`.
- **Sanktionen/Ereignisse:** Nord Stream, Ukraine-Transit, Kriegsschäden ändern Pipelineflüsse abrupt; Status und Jahr müssen im Datensatz stehen.
- **Lizenz OSM (ODbL)** wie im Haupt-Konzept; GEM und Ember nur mit Namensnennung.
- **Datenmenge:** nur Leitungen ab 220 kV bzw. grenzüberschreitend, Pipelines nur Fernleitungen, sonst sprengt es das Größenbudget der Einzeldatei.
- **ENTSO-E-Token:** nötig für die API; gehört als Secret in die Umgebung, nie ins Repo.

## 8. Offene Fragen an Robin

1. Reicht Stufe 2/3 für Strom wie oben, oder soll Strom auch auf Stufe 1 sichtbar sein?
2. Darf ich beim Start einen kostenlosen ENTSO-E-Token brauchen (Registrierung durch dich, Ablage als Secret)? Ohne Token gäbe es für Europa nur Eurostat/Ember-Jahreswerte.
3. Pipelines mit Status „geplant/im Bau“ anzeigen (gestrichelt) oder nur in Betrieb?
