# Importvorlage für Unternehmenslisten

`Importvorlage_Unternehmen.xlsx` ist die Excel-Vorlage, die andere Recherche-AIs oder Personen ausfüllen. `importieren.py` liest sie automatisch ein, prüft sie und legt die Daten im Repo ab.

## Blätter der Vorlage

| Blatt | Inhalt |
|---|---|
| Anleitung | Regeln für die ausfüllende AI (Pflichtfelder, Formate, Einheiten, Währung, Stichtag, keine Schätzwerte, Quelle+URL je Wert, leer lassen statt raten) |
| Unternehmen | Stammdaten, eine Zeile je Unternehmen: Name, Rechtsform, Land, Sitz, ISIN, Ticker, Börse, Börsennotiert, Branche, WZ/NACE, LEI, Handelsregisternummer, Website, Bank, Index-Zugehörigkeit, Beschreibung, Quelle. **Keine Unternehmens-ID**, die vergibt `stammdaten/ids.py` |
| Kennzahlen | Langformat: Unternehmen, Geschäftsjahr, Stichtag, Rechnungslegung, Währung, Einheit, Kennzahl, Wert, Quelle, URL, Seite, Hinweis |
| Kennzahlenliste | feste Liste der erlaubten Kennzahlen (43 Stück: Bilanz, GuV, Cashflow, Sonstige, Markt, Bank) mit Definition |
| Quellen-Dokumente | verwendete Berichte mit Link, Dokumentart, Abrufdatum |
| Listen | Dropdown-Werte (nicht ändern) |

Dropdowns (Datenvalidierung) gibt es für Land, Branche, Börsennotiert, Bank, Unternehmen (Kennzahlen und Quellen), Rechnungslegung, Währung, Einheit und Kennzahl. Gelbe Zeilen mit `[Beispiel]` sind Muster und werden ignoriert.

## Ablauf

```sh
python3 vorlagen/importieren.py Eingang.xlsx                  # nur prüfen, Bericht ausgeben
python3 vorlagen/importieren.py Eingang.xlsx --bericht pruefbericht.md
python3 vorlagen/importieren.py Eingang.xlsx --schreiben      # nur ohne Fehler: ID vergeben, Daten ablegen
python3 -m unittest discover -s vorlagen
python3 vorlagen/erstelle_vorlage.py                          # Vorlage neu bauen (nach Änderung an schema.py)
```

Benötigt `openpyxl`. Keine externen Dienste.

## Prüfungen

- Pflichtfelder, Listenwerte, Datumsformat, Geschäftsjahr gegen Stichtag, kein Stichtag in der Zukunft
- ISIN: Form und Prüfziffer (`ids.isin_pruefsumme_ok`); LEI: 20 Zeichen und Prüfsumme (ISO 7064)
- Dubletten in der Datei (Name, ISIN, LEI, Kennzahl je Jahr) und gegen den Bestand: ISIN, LEI und Name (auch alte Namen/Ordner) über `stammdaten/`. Bekanntes Unternehmen → keine neue ID, nur Ergänzung; Widerspruch (ISIN gehört zu A, Name zu B) → Fehler; ähnlicher Name (Ähnlichkeit ab 0,9) → Warnung
- Einheit passt zum Kennzahltyp (Geld, je Aktie, Prozent, Anzahl); Quelle und URL je Wert Pflicht
- Bilanzprobe je Unternehmen und Jahr: Summe Aktiva = Summe Passiva (0,5 %), Bilanzsumme gegen beide Seiten, Eigenkapital + Verbindlichkeiten gesamt = Bilanzsumme (1 %), Anlage- + Umlaufvermögen gegen Bilanzsumme (Warnung ab 3 %), eine Währung je Jahr

## Ergebnis von `--schreiben`

- Neue Unternehmen werden mit `ids.registrieren()` angelegt (ID `U000123`, ISIN-Eindeutigkeit bleibt geschützt); bekannte erhalten fehlende Stammdaten (LEI, Sitz, weitere ISINs).
- `import/daten/<ID>.json`: alle Werte als `eintraege` (Geschäftsjahr, Stichtag, Rechnungslegung, Währung, Kennzahl, `wert` in absoluten Einheiten, Eingabewert und -einheit, Quelle, URL, Seite, Hinweis, Importdatei) plus `quellen`. Erneuter Import überschreibt je Jahr und Kennzahl.
- Die Anbindung ans Terminal (`app/build.py`, `europa.py`) ist bewusst ein eigener Schritt.

## Pflege

Neue Kennzahlen, Branchen oder Länder nur in `schema.py` ergänzen und die Vorlage neu bauen; Vorlage und Import teilen sich dieses Schema.
