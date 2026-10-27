# Berichtstermine und automatischer Abruf

Erfasst, wann Börsenunternehmen (`boersennotierte-unternehmen/`) und selbst notierte Banken Quartals-, Halbjahres- und
Jahresberichte veröffentlichen, lädt die Berichte am Termin herunter und stellt Termine und Berichte im Terminal bereit
(F5 „Termine“ sowie das Panel „Berichtstermine“ auf jeder Profilseite). Keine kostenpflichtigen Dienste, kein Umgehen von Bot-Schutz.

## Ablauf (GitHub Actions `.github/workflows/termine.yml`, täglich 05:20 und 16:20 UTC, auch von Hand startbar)

1. **Finanzkalender lesen** (nur montags): `skripte/finanzkalender_scan.py` sucht auf der Website jedes Unternehmens die Finanzkalender-Seite
   und liest Zeilen mit Datum und Berichts-Stichwort nach `rohdaten/finanzkalender.csv`. Seiten, die den Kalender per JavaScript nachladen oder
   Bot-Schutz haben, liefern nichts (Status je Unternehmen in `rohdaten/finanzkalender_status.json`).
2. **Termine zusammenführen**: `skripte/termine_erfassen.py` schreibt `termine.csv`. Quellen nach Rang: `manuell` (`termine_manuell.csv`) >
   `finanzkalender` > `yahoo` (yfinance, kostenlos; Zukunftstermine sind meist Schätzungen). Je Bericht (Unternehmen, Periodenende, Berichtsart)
   bleibt ein Eintrag; das Periodenende wird aus Termin und Geschäftsjahresende (Yahoo-Rohdaten) abgeleitet.
3. **Berichte laden**: `skripte/berichte_abrufen.py` nimmt jeden Eintrag, dessen Termin erreicht ist (bis 21 Tage zurück), crawlt die
   Unternehmenswebsite (zwei Ebenen Investor-Relations-Links), bewertet PDF-Links nach Berichtsart und Periode, prüft das PDF (lesbar,
   Berichtsart und Periode auf den ersten Seiten, kein Foliensatz) und legt es unter `<branche>/dokumente/<id>/<Jahr>_<Q1|H1|Q3|GB>_<Name>.pdf` ab
   (Banken: `banken/unterjahr/dokumente/<id>/`), mit Zeile in der `index.csv` (Quelle, Abrufdatum, SHA-256, Seiten, Bytes). Nicht gefunden:
   täglicher Neuversuch bis zu 10 Mal, dann `nicht_gefunden`; Bot-Schutz: `gesperrt`; Dateien über 95 MB werden nicht gespeichert, sondern in
   `rohdaten/zu_gross.txt` gemeldet. Normale Git-Dateien, kein LFS.
4. **Terminal neu bauen** (`app/build.py`) und alles in `main` committen.

## Dateien

| Datei | Inhalt |
|---|---|
| `termine.csv` | `unternehmen_id; name; branche; ticker; berichtsart; periode_ende; termin; quelle; quelle_url; status; stand; abruf_status; versuche; datei; sha256; hinweis` |
| `termine_manuell.csv` | von Hand gepflegte, bestätigte Termine (`unternehmen_id; berichtsart; periode_ende; termin; status; quelle_url; hinweis`); hat Vorrang |
| `finanzkalender_quellen.csv` | optional je Unternehmen `url` (Kalenderseite) und `berichte_url` (Startseite für die Berichtssuche, nötig bei Banken ohne Website im Universum) |
| `rohdaten/` | Scan-Ergebnisse, Status, Meldungen |
| `requirements.txt` | yfinance, requests, pypdf, openpyxl |

`berichtsart`: Q1-Bericht, Halbjahresbericht, Q3-Bericht, Jahresbericht. `status`: `erwartet` (Schätzung), `bestätigt` (Finanzkalender oder manuell),
`erschienen`. `abruf_status`: leer, `offen`, `geladen`, `nicht_gefunden`, `gesperrt`, `zu_gross`.

## Grenzen

* Yahoo kennt Termine für rund ein Drittel der Unternehmen (v. a. Index- und größere Werte); Nebenwerte stehen nur bei bestätigten oder manuellen Terminen drin.
* Der Finanzkalender-Scan ist heuristisch; JavaScript-Kalender (z. B. SAP, BMW, Siemens) liefert er nicht. Für wichtige Werte Termine in `termine_manuell.csv` eintragen.
* Der Abruf findet nur PDFs, die auf der Website ohne Anmeldung und ohne Bot-Schutz verlinkt sind. Nicht Gefundenes bleibt in `termine.csv` sichtbar.
* Banken mit Pillar-3-/HGB-Berichten ohne Börsennotierung sind nicht erfasst (keine Termine, die sich automatisch beschaffen ließen).

## Von Hand ausführen

```bash
pip install -r termine/requirements.txt
python3 termine/skripte/finanzkalender_scan.py [--nur=<id,id>]
python3 termine/skripte/termine_erfassen.py [--rueck=45] [--nur=<id,id>]
python3 termine/skripte/berichte_abrufen.py [--trocken] [--nur=<id,id>] [--fenster=21]
python3 app/build.py
```
