# Abschlüsse der Nicht-Banken ohne Abschlussposten (Pilot)

## Ausgangslage (30.10.2026)

Das Terminal führt 1.274 Unternehmen. Davon haben 367 Nicht-Banken (327 deutsche) nur Yahoo-Kennzahlen
(Kurs, Börsenwert, TTM-Quoten) und keine Bilanz-/GuV-Posten im Stil von `europa/daten`. Weitere 205 deutsche Banken
sind in der Branche Banken über die Bankbilanz abgedeckt (nicht Gegenstand hier). 128 der 367 haben den Geschäftsbericht 2025
bereits als PDF im Repo (`boersennotierte-unternehmen/*/dokumente`).

## Quellenwahl

1. **Geschäftsberichte im Repo (Primärquelle)**: Bilanzsumme, Eigenkapital, Umsatz, Ergebnis aus der gedruckten Seite. Quelle, Datei und Seite je Unternehmen.
2. **Yahoo über `europa/abrufen.py`** als Sekundärquelle für Mehrjahreswerte (heute Antwort 429, Lauf später per Workflow).
3. **ESEF/XBRL**: filings.xbrl.org hat keine deutschen Einreichungen (Deutschland veröffentlicht über das Unternehmensregister, Captcha, nicht umgehen). Für ausländische Emittenten (LU, NL, CH) prüfbar.
4. **Fehlende Berichte** (239): erst Nachsuche der Bericht-PDFs (`berichte_suche.py`), danach Schritt 1.

## Prüfregeln

- Bilanzsumme: Summe Aktiva = Summe Passiva (gleiche oder Folgeseite); sonst eine einzelne Zeile, die dem Terminalwert (Yahoo) auf 3 % entspricht. Das Feld `kontrolle.bilanzsumme` nennt die Stufe.
- Einheit (TEUR/Mio.) aus dem Terminalwert hergeleitet (Abweichung unter 25 %), sonst aus dem Seitenkopf.
- Eigenkapital höchstens Bilanzsumme, Eigenkapitalquote innerhalb 8 Punkten der Yahoo-Quote. Verbindlichkeiten = Bilanzsumme minus Eigenkapital (als abgeleitet benannt).
- Umsatz positiv, 1 % bis 15fache der Bilanzsumme und innerhalb 35 % des Yahoo-Werts; Ergebnis und EBIT gegen Yahoo-Nettomarge (4 Punkte) und EBIT-Marge (5 Punkte).
- Operativer Cashflow von der Kapitalflussrechnungs-Seite, 0,2 % bis 50 % der Bilanzsumme; keine Gegenprobe, deshalb im Feld `kontrolle` vermerkt.

Was nicht besteht, bleibt leer.

## Stand (31.10.2026)

Quellen: 184 Berichte 2025 im Repo (Geschäftsbericht, Jahresfinanzbericht, Konzern- oder Jahresabschluss). Davon in `daten/`: Bilanzsumme 98, Eigenkapital 59, Umsatz 46, Ergebnis 23, EBIT 6, operativer Cashflow 51. 20 davon sind Einzelabschlüsse (Feld `abschluss`), 4 haben umgekehrte Spaltenfolge im Bericht (Feld `kontrolle.spalten_umgekehrt`).
Gegenprobe von Hand: PWO, RealTech, Blue Cap.

## Nachsuche der fehlenden Berichte (31.10.2026)

Von 238 Nicht-Banken ohne Abschlussposten und ohne Geschäftsbericht in der Liste hatten 51 schon einen Jahres- oder Konzernabschluss im Repo. Für die übrigen 187 lief `berichte_suche.py` (Tiefe 3, Sitemap) und `berichte_laden.py` für die 139 mit Website: 5 geladen, 2 davon verworfen (Geschäftsjahr 2019 bzw. 2024). Gründe für den Rest:
Website ohne auffindbare PDF-Links 54, Bot-Schutz oder Sperre 20 (nicht umgangen), SSL-, Verbindungs- und Protokollfehler 13, PDF ohne erkennbares Geschäftsjahr, nur Auszug oder falsche Datei rund 30, ohne Website 48. Eine Stichprobe per Websuche (HWA, a.i.s., LEWAG) fand ebenfalls kein frei zugängliches PDF für 2025.

## Yahoo-Abschlüsse als Sekundärquelle (31.10.2026)

Yahoo antwortet aus dieser Umgebung weiter mit 429, deshalb nutzt `skripte/yahoo_uebernehmen.py` die im Repo liegenden, ISIN-gebundenen Rohdaten (`boersennotierte-unternehmen/rohdaten/yahoo`). Ergebnis in `yahoo/<ID>.json` (alle jährlichen Bilanz-, GuV- und Cashflow-Posten mit Originalbezeichnung, bis zu 5 Jahre, Berichtswährung laut Yahoo): 270 Unternehmen. Offen (`yahoo/offen.csv`): 52 ohne belegte Berichtswährung, 42 ohne Jahresabschlussdaten, 3 ohne Rohdaten. Eine Währung wird nie angenommen.
Gegenprobe: Bei 75 Unternehmen mit Bericht und Yahoo-Wert weicht die Bilanzsumme 2025 bei 72 um höchstens 2 % ab. Die 5 anfänglichen Abweichungen waren: Leifheit und FRoSTA (Spaltenköpfe 2024 | 2025 statt 2025 | 2024, jetzt erkannt), OVB (falsche Seite, Restatement-Tabelle statt Konzernbilanz, Label „Summe der Vermögenswerte“ fehlte), Hoftex und DATA MODUL (der Bericht enthält nur den HGB-Einzelabschluss, Yahoo den Konzern; in den Dateien als `abschluss: Einzelabschluss` gekennzeichnet). Neu aufgefallen: Rostra AG (+5 %, IFRS-Konzernbericht gegen Yahoo-Wert). Berichtsdaten in `daten/` haben Vorrang, Yahoo ergänzt Historie und Lücken.

## Skripte

```
python3 abschluesse-nichtbanken/skripte/vorbereiten.py /tmp/arbeit
python3 abschluesse-nichtbanken/skripte/uebernehmen.py /tmp/arbeit schreiben
```

## Offen / nächste Stufen

- Extraktor je Gliederungsvariante (HGB/IFRS) ausbauen: Umsatz, EBIT, Ergebnis, Cashflow, Finanzverbindlichkeiten.
- Die 94 geprüften, aber unvollständigen Berichte per Seitenvorlage nachtragen.
- Historie 10 Jahre: Vorjahres-Spalten und ältere Berichte (`zeitreihen/abrufliste_unternehmensregister.csv` als Muster).
- Nach Freigabe: europäische 534 über `europa/abrufen.py` (Workflow `europa.yml`) mit Primärquellenabgleich.
- Terminal: Einbindung über `europa.py` (`ergaenzungen/` bzw. neue `daten`-Quelle) als Folgeschritt.

## Terminal-Anbindung (01.11.2026)

`app/europa.py` (`nichtbanken`, aufgerufen in `app/unternehmen.py` nach `ergaenzen`) lädt für jedes Nicht-Bank-Unternehmen ohne Tabellenabschlüsse zuerst `yahoo/<ID>.json` und legt `daten/<ID>.json` je Periode darüber (Bericht vor Yahoo). Bei abweichender Berichtswährung zählt nur der Bericht. Vergleichsfelder (Bilanzsumme, Eigenkapital, Umsatz, EBIT, Ergebnis, EK-Quote, EBIT-Marge) entstehen nur aus EUR-Abschlüssen und überschreiben keine vorhandenen Werte. Ergebnis: 923 von 1.010 Nicht-Banken haben Abschlüsse im Profil, 87 bleiben offen. Die Ansicht „Bilanz- und GuV-Abdeckung“ (ABS) bleibt auf das Tabellenuniversum beschränkt.
