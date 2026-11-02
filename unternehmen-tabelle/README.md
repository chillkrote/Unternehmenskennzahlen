# Unternehmen-Tabelle (zusammengeführt)

Eine Tabelle für alle Unternehmen aus den Länderlisten, Börsenlisten und den Repo-Stammdaten. Stand 02.11.2026: **25.974 Unternehmen**.

| Datei | Inhalt |
|---|---|
| `Unternehmen_Tabelle.xlsx` | Blatt "Unternehmen" im Format der `vorlagen/Importvorlage_Unternehmen.xlsx` (17 Spalten), dazu die Blätter der Vorlage |
| `Unternehmen_Tabelle.csv` | dieselben Zeilen als CSV (Semikolon, UTF-8) |
| `id_zuordnung.csv` | Repo-Unternehmens-ID (`U000123`) je deutscher Zeile, mit Art (bestehend/neu) und Abgleichsweg |
| `Zwischenstand_Unternehmensliste.md` | Anzahl je Land, fehlende Angaben, eingearbeitete und offene Listen |
| `Pruefbericht_importieren.md` | Ausgabe von `vorlagen/importieren.py` |
| `skripte/deutschland_einfuegen.py` | fügt die deutschen Unternehmen aus `stammdaten/` ein (ergänzt Bestehendes, legt Neues an) |
| `skripte/bausteine/` | die einmal benutzten Zusammenführungs- und Anreicherungsskripte (GLEIF, SEC, ETF-Listen, Wikidata, EDGAR, Börsenlisten); sie lesen noch Pfade aus der Arbeitsumgebung und dienen als Nachweis des Vorgehens |

## Regeln

* Basiswerte haben Vorrang, es werden nur leere Felder gefüllt und neue Unternehmen angehängt.
* Jede automatische Ergänzung steht in der Spalte `Beschreibung` ("… bitte prüfen"). `Branche` und `Bank` bei neuen Zeilen aus Börsenlisten sind Platzhalter ("sonstige"/"nein").
* Keine Doppelten bei ISIN und LEI. Aktiengattungen stehen teils als eigene Zeilen.
* Die Tabelle hat keine ID-Spalte. Die Zuordnung zu `U000123` steht in `id_zuordnung.csv` (nur Deutschland). Für andere Länder wird eine ID erst über `stammdaten/ids.py` vergeben. Nie `stammdaten/erstellen.py --neu` ausführen.

## Prüfen

```
python3 vorlagen/importieren.py unternehmen-tabelle/Unternehmen_Tabelle.xlsx --bericht bericht.md   # dauert bei 26.000 Zeilen viele Minuten
python3 stammdaten/pruefe_ids.py
```

Bekannte Restfehler (6): AENA.MC/ANA.MC und CAE Inc./CA, Inc. (Basis), vier französische Firmen (LVMH, Capgemini, Schneider Electric, TotalEnergies), deren Name im ID-Register auf eine andere ID zeigt als ISIN und LEI.

## Deutschland neu einfügen

```
python3 unternehmen-tabelle/skripte/deutschland_einfuegen.py EINGABE.xlsx AUSGABE.xlsx
```

Abgleich über ISIN, LEI, dann eindeutigen normalisierten Namen. Treffer werden nur ergänzt (32 Zeilen), 659 deutsche Unternehmen kamen neu hinzu (Banken, Sparkassen und Börsen-AGs).
