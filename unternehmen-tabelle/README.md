# Unternehmen-Tabelle (zusammengeführt)

Eine Tabelle für alle Unternehmen aus den Länderlisten, Börsenlisten und den Repo-Stammdaten. Stand 02.11.2026: **26.130 Unternehmen** (sieben Namenszeilen mit ESEF-Pilot zusammengelegt, siehe `bereinigung_protokoll_esef.csv`).

| Datei | Inhalt |
|---|---|
| `Unternehmen_Tabelle.xlsx` | Blatt "Unternehmen" im Format der `vorlagen/Importvorlage_Unternehmen.xlsx` (17 Spalten), dazu die Blätter der Vorlage |
| `Unternehmen_Tabelle.csv` | dieselben Zeilen als CSV (Semikolon, UTF-8), vorn mit der Spalte `unternehmen_id` (`U000123`, leer wenn das Unternehmen noch keine Repo-ID hat) |
| `id_zuordnung.csv` | Repo-Unternehmens-ID (`U000123`) je Zeile mit ID (alle 1.288 Unternehmen des ID-Registers), mit Land, Art (bestehend/neu) und Abgleichsweg |
| `Zwischenstand_Unternehmensliste.md` | Anzahl je Land, fehlende Angaben, eingearbeitete und offene Listen |
| `Pruefbericht_importieren.md` | Ausgabe von `vorlagen/importieren.py` |
| `skripte/deutschland_einfuegen.py` | gleicht alle Unternehmen aus `stammdaten/` ab (ohne Landangabe alle Länder; ergänzt Bestehendes, legt Neues an, schreibt `id_zuordnung.csv` und die CSV mit ID-Spalte) |
| `skripte/bereinigung.py` | gezielte Bereinigung: benennt 3 Zeilen mit Spaltenüberschrift als Namen um, legt eindeutige Doppelzeilen zusammen; Ergebnis in `bereinigung_protokoll.csv`, offene Fälle in `bereinigung_pruefliste.csv` |
| `skripte/pruefliste_entscheiden.py` | setzt die Entscheidungen zur Prüfliste um (21 weitere Zusammenlegungen); `bereinigung_pruefliste.csv` hat dazu die Spalten `entscheidung` und `begruendung` für alle 90 Fälle |
| `skripte/bausteine/` | die einmal benutzten Zusammenführungs- und Anreicherungsskripte (GLEIF, SEC, ETF-Listen, Wikidata, EDGAR, Börsenlisten); sie lesen noch Pfade aus der Arbeitsumgebung und dienen als Nachweis des Vorgehens |

## Regeln

* Basiswerte haben Vorrang, es werden nur leere Felder gefüllt und neue Unternehmen angehängt.
* Jede automatische Ergänzung steht in der Spalte `Beschreibung` ("… bitte prüfen"). `Branche` und `Bank` bei neuen Zeilen aus Börsenlisten sind Platzhalter ("sonstige"/"nein").
* Keine Doppelten bei ISIN und LEI. Aktiengattungen stehen teils als eigene Zeilen.
* Das Excel-Blatt behält das 17-Spalten-Format der Importvorlage (keine ID-Spalte, damit `importieren.py` es liest). Die IDs stehen in `id_zuordnung.csv` und in der CSV-Spalte `unternehmen_id`. Neue IDs nur über `stammdaten/ids.py`, nie `stammdaten/erstellen.py --neu`.

## Prüfen

```
python3 vorlagen/importieren.py unternehmen-tabelle/Unternehmen_Tabelle.xlsx --bericht bericht.md   # dauert bei 26.000 Zeilen viele Minuten
python3 stammdaten/pruefe_ids.py
```

Bekannte Restfehler (6): AENA.MC/ANA.MC und CAE Inc./CA, Inc. (Basis), vier französische Firmen (LVMH, Capgemini, Schneider Electric, TotalEnergies), deren Name im ID-Register auf eine andere ID zeigt als ISIN und LEI.

## Register neu abgleichen

```
python3 unternehmen-tabelle/skripte/deutschland_einfuegen.py EINGABE.xlsx AUSGABE.xlsx [LAND]
```

Abgleich über ISIN, LEI, dann eindeutigen normalisierten Namen. Treffer werden nur ergänzt. Bisher: 1.288 Registerfirmen, davon 918 schon vollständig vorhanden, 45 ergänzt, 325 neu angehängt (davon rund 660 deutsche Firmen im ersten Lauf).
