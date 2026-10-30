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

Summe Aktiva = Summe Passiva auf derselben Seite; Einheit (TEUR/Mio.) aus dem Terminalwert Bilanzsumme hergeleitet (Abweichung unter 25 %);
Eigenkapital höchstens Bilanzsumme und Eigenkapitalquote innerhalb 8 Punkten der Yahoo-Quote; Umsatz 0,75 bis 1,35 des Yahoo-Werts.
Was nicht besteht, bleibt leer. Verbindlichkeiten sind Bilanzsumme minus Eigenkapital (als abgeleitet benannt).

## Pilot

`daten/<ID>.json` im Format von `europa/ergaenzungen` für 20 deutsche und luxemburgische Unternehmen (Bilanz 2025 und, wo plausibel, 2024).
Drei Berichtsseiten von Hand gegengelesen (PWO, RealTech, Blue Cap), alle stimmen. Von 128 Berichten bestanden 34 die Bilanzprüfung,
20 zusätzlich die Eigenkapitalprüfung. Umsatz bei 8, Ergebnis bei 5; Cashflow und EBIT sind noch nicht übernommen, weil das Layout je Bericht zu stark abweicht.

## Skripte

```
python3 abschluesse-nichtbanken/skripte/vorbereiten.py /tmp/arbeit
python3 abschluesse-nichtbanken/skripte/pilot.py /tmp/arbeit schreiben
```

## Offen / nächste Stufen

- Extraktor je Gliederungsvariante (HGB/IFRS) ausbauen: Umsatz, EBIT, Ergebnis, Cashflow, Finanzverbindlichkeiten.
- Die 94 geprüften, aber unvollständigen Berichte per Seitenvorlage nachtragen.
- Historie 10 Jahre: Vorjahres-Spalten und ältere Berichte (`zeitreihen/abrufliste_unternehmensregister.csv` als Muster).
- Nach Freigabe: europäische 534 über `europa/abrufen.py` (Workflow `europa.yml`) mit Primärquellenabgleich.
- Terminal: Einbindung über `europa.py` (`ergaenzungen/` bzw. neue `daten`-Quelle) als Folgeschritt.
