# Zeitreihen (Langformat)

Einheitliche Ablage aller Zeitreihen über alle Erhebungen und Branchen. Die Erhebungsordner behalten ihre Rohdaten und Originaldokumente; hier steht, was Excel-Blätter und das Bank-Terminal (Ansicht TS) lesen.

## Dateien

- `zeitreihe_lang.csv`: eine Zeile je Unternehmen, Kennzahl und Stichtag.
- `stammdaten.csv`: eine Zeile je Unternehmen (ID, Name, Branche, Gruppe, Rechtsnachfolge).
- `skripte/`: Skripte, die das Langformat erzeugen (`migriere_banken.py` überführt die Bankenexcel).

## Spalten von `zeitreihe_lang.csv`

| Spalte | Bedeutung |
|---|---|
| `unternehmen_id` | Schlüssel aus `stammdaten.csv` (Slug des Namens) |
| `kennzahl` | z. B. `bilanzsumme`, `eigenkapital`, `fonds_340g`, `jahresueberschuss`, `cet1`, `cet1_quote` |
| `stichtag` | Bilanzstichtag (ISO) |
| `wert`, `einheit`, `waehrung` | Wert in Berichtswährung; Umrechnung erst bei der Anzeige |
| `rechnungslegung` | `HGB`, `IFRS` oder `aufsichtlich` (Pillar 3); Reihen werden nie vermischt |
| `ebene` | `Einzel` oder `Konzern` |
| `quelle` | Quelle bzw. Hinweis aus der Erhebung |
| `pruefstatus` | `geparst`, `plausibilisiert` oder `manuell bestätigt` |

## Regeln

- Änderungen der Bilanzierung (neues Formblatt, anderer Konsolidierungskreis) bekommen eine neue Zeile mit anderer `rechnungslegung` oder `ebene`; vorhandene Werte werden nicht still überschrieben.
- Fusionen: `nachfolger_von` und `nachfolge_datum` in `stammdaten.csv`. Standardsicht ist der Rechtsträger, eine Pro-forma-Summe wird nur auf Wunsch berechnet und gekennzeichnet.
- Ziel der Rückwärtserhebung sind 10 Jahre. Es werden ausschließlich frei zugängliche Quellen genutzt; keine Bezahl-APIs, keine Umgehung von Captchas oder Bot-Sperren.

Stand: Erstbefüllung aus `Bilanzvergleich_Banken_GJ2025.xlsx` (Blätter "Zeitreihe 2021-2025" und "Offenlegung 31.12.2025").
