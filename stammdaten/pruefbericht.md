# Prüfbericht Einführung der zentralen Unternehmens-ID

Stand 27.10.2026. Aufruf der Kontrolle: `python3 stammdaten/pruefe_ids.py` (Ausgabe am Ende).

| | vorher | nachher |
|---|---|---|
| Unternehmen (verschiedene IDs; Terminal: Einträge) | 746 (208 Banken-Stammdaten + 543 Börsenuniversum, 5 mit zufällig gleicher ID) | **743** |
| zusammengeführte Dubletten | | 8 (Deutsche Bank, Commerzbank, Deutsche Pfandbriefbank, Baader Bank, ProCredit Holding, UmweltBank, Merkur Privatbank, Varengold Bank = Ascory Bank) |
| ID-Schemata | 2 (Umlaut als `ae/oe/ue` bzw. weggelassen), dazu 12 `slug()`-Funktionen, Universum auf 60 Zeichen gekürzt | 1 (`U000123`), Auflösung nur über `stammdaten/ids.py` |
| ISINs | 556 im Universum | 556, jede genau einer ID (`isin_zuordnung.csv`) |
| ISIN bei mehreren IDs | nicht geprüft | **0** (Prüfung im Build, im Workflow und als Test) |
| ID-Verweise in CSV-Dateien | 7.776 (zeitreihen 5.297, boersennotierte-unternehmen 1.391, governance 726, termine 362) | 7.776, alle umgestellt |
| ID-Verweise in JSON (Terminal-Daten, Status-Dateien) | | 1.242 Stellen in 4 Status-/Korrekturdateien umgestellt, Terminal-Daten neu gebaut |
| verwaiste Verweise | 0 formal; im Terminal dennoch tote Governance-Links und Dubletten, weil dieselbe Gesellschaft unter zwei IDs lief | **0** |
| Aliase (alte IDs, Ordnernamen, Namensvarianten) | | 1.591 |

Datenverlust: keiner. Die Migration hat in den 29 betroffenen CSV-Dateien nur ID-Zellen geändert (Zeilenzahl und Format unverändert, Inhalt außerhalb der ID-Spalte byte-gleich, geprüft für `universum.csv` und `universum_instrumente.csv` durch Vergleich ohne ID-Spalte). Das Governance-Build (`governance/skripte/build.py`) erzeugt nach der Umstellung der Skripte dieselben CSV-Dateien wie die migrierten. Das Universum-Skript (`unternehmen.py`) reproduziert `universum.csv` und `universum_instrumente.csv` inhaltsgleich mit den neuen IDs. Dokumentordner wurden nicht umbenannt.

Terminal nach dem Umbau (Browsertest): `#firma-U000148` (Deutsche Bank) öffnet das Profil, ebenso die alten Lesezeichen `#firma-deutsche-bank-ag` und `#firma-deutsche-bank-aktiengesellschaft`; keine Konsolenfehler.

Offene Fälle für Robin (kein Datenverlust, aber Entscheidung bei Bedarf): siehe `dubletten.csv`, Zeilen "geprüft: getrennt gelassen" (Grenke Mutter/Tochter, ähnliche Namen wie Sto/Ströer, Sparkasse Holstein/Südholstein).

```
743 Unternehmen, 556 ISINs (je genau einer ID), 1591 Aliase, 8519 geprüfte ID-Verweise
```
