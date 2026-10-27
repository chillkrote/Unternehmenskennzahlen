# Stammdaten: zentrale Unternehmens-ID

Jedes Unternehmen im Repo (Banken, Börsenunternehmen, Governance, Termine, Kurse, Zeitreihen, Terminal) hat **genau eine ID** der Form `U000123`.
Die Tabelle `unternehmen_ids.csv` ist die einzige Quelle; alle anderen Dateien verweisen nur darauf.

## Warum eine undurchsichtige Nummer

* **Nicht aus der ISIN abgeleitet:** Es sind auch nicht börsennotierte Unternehmen gelistet (Sparkassen, Volksbanken, Tochterbanken), und eine Gesellschaft kann mehrere ISINs haben oder später eine bekommen.
* **Nicht aus dem Namen abgeleitet:** Die alten Slugs ("deutsche-bank-ag" gegenüber "deutsche-bank-aktiengesellschaft", Umlaute als `ue` oder weggelassen, auf 60 Zeichen gekürzt) haben im Terminal Dubletten und tote Governance-Links erzeugt. Umbenennungen (Varengold Bank AG heißt jetzt Ascory Bank AG) und Fusionen dürfen die ID nicht ändern.
* **Fortlaufend, nie wiederverwendet, nie gelöscht.** Ein zusammengeführtes Unternehmen behält die ID, die andere wird zum Alias.

## Dateien

| Datei | Inhalt |
|---|---|
| `unternehmen_ids.csv` | eine Zeile je Unternehmen: `unternehmen_id, name, rechtsform, branche, gruppe, rolle, sitz, land, status (börsennotiert / nicht börsennotiert), isin_haupt, weitere_isins, lei, ticker, ordner, herkunft, nachfolger_von, hinweis` |
| `unternehmen_aliase.csv` | `alias, unternehmen_id, art`: `id_alt` (frühere Slug-IDs), `ordner` (Ordnername der Dokumente), `name` (Namensvarianten, GLEIF-/Hub-Rechtsnamen) |
| `isin_zuordnung.csv` | `isin, unternehmen_id, art (haupt/weitere)`: jede ISIN steht genau einmal |
| `dubletten.csv` | Entscheidungen bei Dubletten: was zusammengeführt wurde und warum, was geprüft und getrennt blieb |
| `pruefbericht.md` | Stand der Migration (Anzahl vorher/nachher, verwaiste Verweise) |
| `ids.py` | Bibliothek: `ids.lade()`, `aufloesen(name / alte ID / Ordner / ISIN)`, `ordner(id)`, `registrieren(...)` |
| `pruefe_ids.py` | Kontrolle (siehe unten) |
| `test_ids.py` | Tests der Kontrolle und der Registrierung |
| `migriere_ids.py` | stellt CSV-/JSON-Dateien von alten Schreibweisen auf die ID um (idempotent) |
| `erstellen.py` | einmaliges Aufsetzen der Tabellen aus dem Bestand (läuft nicht erneut, ohne `--neu`; `--neu` würde IDs neu vergeben) |

Die **Ordner der Dokumente** behalten ihre bisherigen Namen (`ordner` in der Tabelle). Das sind Dateipfade, keine IDs, und ein Umbenennen von mehr als 800 Dokumenten brächte nur Git-Rauschen. Skripte holen den Ordner über `ids.lade().ordner(id)`.

## Die Kontrolle: eine ISIN nie bei mehreren IDs

`python3 stammdaten/pruefe_ids.py` bricht mit Exit-Code 1 ab, wenn

1. eine ISIN bei mehreren IDs steht, in `isin_zuordnung.csv`, `unternehmen_ids.csv`, in `universum*.csv` oder in `app/data/*.json`,
2. eine ISIN formal ungültig ist (Format, Prüfziffer),
3. ein Alias auf mehrere IDs zeigt,
4. irgendeine Spalte `unternehmen_id`, `gesellschaft_unternehmen_id` oder `ueber_unternehmen_id` in einer CSV oder eine `id` in `app/data/*.json` auf eine nicht vorhandene ID zeigt (verwaiste Verweise),
5. mit `--gegen=origin/main` eine ID gegenüber dem Basisstand verschwunden ist oder eine ISIN die ID gewechselt hat.

Sie läuft an drei Stellen: im Build des Terminals (`app/build.py`, damit die Daten-Workflows nichts Fehlerhaftes committen), im Workflow `.github/workflows/stammdaten.yml` (Pull Requests und Pushes auf main, mit den Tests) und von Hand.

## Neues Unternehmen aufnehmen

* Börsenunternehmen: `boersennotierte-unternehmen/universum/skripte/unternehmen.py` vergibt über das Register automatisch eine ID (erst ISIN, dann Ordner/Name, sonst neu).
* Sonst im Skript: `ids.lade().registrieren(name=..., branche=..., isin=..., ordner=<Ordnername>)`; wer eine bekannte ISIN einem anderen Unternehmen geben will, bekommt einen Fehler.
* Neue Zeilen in CSVs immer mit der ID aus dieser Tabelle. Alte Schreibweisen löst `python3 stammdaten/migriere_ids.py` auf (idempotent; das Governance-Build macht es selbst).
* Zusammenführung zweier Einträge: die kleinere ID behalten, die andere als Alias (`art=id_alt`) eintragen, in `dubletten.csv` begründen, ISINs auf die behaltene ID umhängen. Die verworfene ID bleibt als Zeile in `unternehmen_ids.csv` stehen (mit `hinweis`), damit die Prüfung gegen den Basisstand nicht anschlägt.

## Dubletten (Stand der Einführung)

Zusammengeführt wurden Deutsche Bank, Commerzbank, Deutsche Pfandbriefbank, Baader Bank, ProCredit Holding, UmweltBank, Merkur Privatbank (Bilanzvergleich und Börsenuniversum führten dieselbe Gesellschaft getrennt) sowie Varengold Bank AG = Ascory Bank AG (Umbenennung laut GLEIF, gleiche LEI). Begründungen in `dubletten.csv`.
Bewusst getrennt blieben unter anderem Grenke AG und GRENKE BANK AG (Mutter und Tochter), Mercedes-Benz Group AG und Mercedes-Benz Bank AG sowie UniCredit SpA und die HypoVereinsbank.
