# Zeitreihen (Langformat)

Einheitliche Ablage aller Zeitreihen über alle Erhebungen und Branchen. Die Erhebungsordner behalten ihre Rohdaten und Originaldokumente; hier steht, was Excel-Blätter und das Bank-Terminal (Ansicht TS) lesen.

## Dateien

- `zeitreihe_lang.csv`: eine Zeile je Unternehmen, Kennzahl und Stichtag.
- `stammdaten.csv`: eine Zeile je Unternehmen (ID, Name, Branche, Gruppe, Rechtsnachfolge).
- `Zeitreihen_Banken.xlsx`: Excel mit einem Blatt je Kennzahl (Zeilen Banken, Spalten Jahre), erzeugt von `skripte/excel_export.py`.
- `gruppen_lang.csv`: Gruppenreihen der Bundesbank (Sparkassen, Kreditgenossenschaften, Landesbanken, Kreditbanken, Großbanken) ab 1993, erzeugt von `skripte/bundesbank_gruppen.py` über die offene SDMX-Schnittstelle (keine Anmeldung). Bilanzsumme, Jahresüberschuss, Zinsüberschuss, Betriebsergebnis, EK-Rentabilität; dazu Bilanzstatistik (Dezember, ab 2002) mit Kapital und Zahl der Institute.
- `skripte/eba_hub_quartale.py`: übernimmt EU-KM1-Werte aller Stichtage (Juni 2025 bis Juni 2026) aus dem EBA-Hub-Export.
- `abrufliste_unternehmensregister.csv`: je Bank die kleinste Menge Geschäftsjahre, deren Jahresabschlüsse alle fehlenden Bilanzsummen 2016–2023 abdecken (ein Abschluss enthält Berichtsjahr und Vorjahr), sortiert nach Bilanzsumme in Stufen A/B/C; erzeugt von `skripte/abrufliste.py`. Für manuelle Downloads, die Sicherheitsabfrage des Unternehmensregisters wird nicht umgangen.
- `skripte/`: `migriere_banken.py` überführt die Bankenexcel ins Langformat, `excel_export.py` baut daraus die Excel.
- Das Bank-Terminal (`app/`, Ansicht TS auf F6) liest `zeitreihe_lang.csv` über `datenschicht.lade_lang`; mehr Jahre erscheinen dort ohne Codeänderung.

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
