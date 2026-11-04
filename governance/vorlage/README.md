# Importvorlage Governance

`Importvorlage_Governance.xlsx` ist die Excel-Vorlage, in die Gremien, Personen, Vergütung, Pay-Ratio-Eingangsdaten, Frauen- und Mitbestimmungszahlen per Hand (oder durch eine Recherche-AI) eingetragen werden. `importieren.py` liest sie, prüft sie und überführt sie in die Governance-Datenstruktur (`governance/*.csv`).

## Blätter

| Blatt | Inhalt | Ziel |
|---|---|---|
| Anleitung | Regeln (Quelle je Zeile, Seite = PDF-Seite, leer statt raten, Geschlecht nie aus Vornamen, kein Privates) | |
| Gremienmitglieder | Person, Organ, Funktion, Vertreterart, seit/bis, Beruf laut Dokument, Quelle, Seite, Stand | `gremien_mitglieder.csv`, `personen.csv` |
| Vergütung | Einzel- und Summenwerte in T€ je Gremium mit Art, Quelle, Seite, Stand | `verguetung.csv` |
| Kennzahlen Gremien | Felder aus der Feldliste: Zahl Mitglieder, Frauen, Arbeitnehmer-/Gewerkschaftsvertreter, Mitbestimmung, Mitarbeiter | `kennzahlen_gremien.csv` |
| Pay Ratio | Variante A (Ø-Vergütung Beschäftigte), B (Personalaufwand und Beschäftigte) oder vom Unternehmen berichtete Quote | `kennzahlen_gremien.csv` (`pay_ratio`, `durchschnittsverguetung_beschaeftigte_teur`, `personalaufwand_konzern_mio_eur`, `beschaeftigte_konzern_zahl`) und Eingang für `berechnung.py` |
| Geschlecht (Belege) | Geschlecht einer Person mit wörtlichem Beleg | `berechnungen/geschlecht_belege.csv` (Grundlage Frauenzahlen und Gender Pay Gap) |
| Mandate extern | weitere Aufsichts-/Kontrollgremienmandate (Typ a/b) mit Zeitbezug | `mandate_extern.csv` |
| Werdegang | berufliche Stationen | `werdegang.csv` |
| Quellen-Dokumente | Register der Dokumente (Titel, Link, Abruf-, Veröffentlichungsdatum) | `handeingabe/<Datei>.json` |
| Feldliste, Listen, ID-Liste | Nachschlageblätter für Dropdowns, Felder und Unternehmens-IDs | |

Pflichtspalten sind dunkelblau und mit `*` markiert, optionale grau; Spaltenbeschreibungen stehen als Kommentar am Spaltenkopf. Dropdowns gibt es für Organ, Vertreterart, Gremium, Typ, Geschlecht, Variante, Feld, Dokumentart (Vergütungsart/Werdegang-Art/Bezug mit Warnung statt Sperre). Die Spalte „Unternehmen (automatisch)“ zeigt per Formel den Namen zur ID. Gelbe Zeilen mit `[Beispiel]` werden ignoriert.

## Ablauf (aus dem Repo-Root)

```sh
python3 governance/vorlage/importieren.py Eingang.xlsx                  # nur prüfen
python3 governance/vorlage/importieren.py Eingang.xlsx --bericht pb.md  # Prüfbericht speichern
python3 governance/vorlage/importieren.py Eingang.xlsx --schreiben     # nur ohne Fehler
python3 governance/skripte/berechnung.py                                 # Pay Ratio und Gender Pay Gap neu rechnen (GJ 2025)
python3 -m unittest discover -s governance/vorlage                       # Tests
python3 governance/vorlage/erstelle_vorlage.py                           # Vorlage neu bauen (nach Änderung an schema.py)
```

`--schreiben` legt `governance/handeingabe/<Dateiname>.json` ab und startet `governance/skripte/build.py`. Die CSVs bleiben damit aus den Quellen reproduzierbar: `lib.write_all()` liest zusätzlich alle `handeingabe/*.json`. Erneuter Import derselben Datei (gleicher Dateiname) ersetzt die frühere Lieferung. Benötigt `openpyxl`, keine externen Dienste.

## Prüfungen

Pflichtfelder, Spaltenköpfe und Blätter, Listenwerte, Unternehmens-ID gegen `stammdaten/`, Geschäftsjahr, Datumsformate, Seitenangabe, Quelle (https-Link oder Repo-Pfad, Registereintrag), Personenbezug (Name muss im Blatt Gremienmitglieder oder in `personen.csv` stehen; ähnliche Schreibweisen werden gemeldet), Dubletten in der Datei und gegen den Bestand, Zählwerte (Frauen ≤ Mitglieder, Gewerkschaft ≤ Arbeitnehmer, Anteilseigner + Arbeitnehmer = Aufsichtsrat, Abgleich mit erfassten Namen), Summenzeilen gegen Einzelvergütungen (1 %), Plausibilität der Pay-Ratio-Eingangsdaten, Geschlechtsbeleg (kein Verweis auf Vornamen). Fehler verhindern jede Übernahme, Warnungen nicht.

## Grenzen

- `berechnung.py` rechnet nur das Geschäftsjahr 2025; Pay-Ratio-Eingangsdaten für andere Jahre landen in `kennzahlen_gremien.csv`, werden aber nicht verrechnet.
- Bestehende Zeilen werden nicht überschrieben; Korrekturen am Bestand erfolgen in den Erhebungsmodulen (`skripte/boerse_*.py`).
- Neue Unternehmen müssen vorher über die Unternehmens-Importvorlage (`vorlagen/`) bzw. `stammdaten/ids.py` registriert sein.
