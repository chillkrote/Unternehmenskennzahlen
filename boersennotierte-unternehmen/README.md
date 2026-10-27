# Börsennotierte Unternehmen in Deutschland: Kennzahlen GJ 2025

Erhebung aller in Deutschland notierten Aktiengesellschaften (Abgrenzung siehe [`universum/README.md`](universum/README.md)) mit Bilanz-, GuV- und Cashflow-Daten, Pflichtangaben (Mitarbeiter, Dividende, Aktienzahl, Stimmrechtsmitteilungen) und Kapitalmarktdaten, getrennt nach Branchen. Begonnen am 27.10.2026.

## Aufbau

```
boersennotierte-unternehmen/
  universum/                Börsenlisten (Originalabrufe), Unternehmensliste, Branchenzuordnung
  <branche>/
    README.md               Unternehmen der Branche, Abdeckung, Links zu den Geschäftsberichten
    auswertung/             <Branche>_Kennzahlen_GJ2025.xlsx
    dokumente/<firma>/      Geschäftsberichte/Jahresfinanzberichte (PDF, per Git LFS)
    dokumente/index.csv     Quelle, Abrufdatum, SHA-256, Seiten je Dokument
  auswertung/               Gesamtübersicht aller Branchen (eine Excel)
  rohdaten/yahoo/           je ISIN alle Rohdaten von Yahoo Finance (JSON)
  rohdaten/bafin/           BaFin-Datenbank bedeutender Stimmrechtsanteile, Gesamtexport
  rohdaten/berichte_status.json   je Unternehmen: Bericht geladen bzw. warum nicht
  skripte/                  Abruf, Berichtssuche, Excel-Erzeugung
```

Die PDFs liegen per **Git LFS** im Repo (Entscheidung vom 27.10.2026). Zum Auschecken der Dateien `git lfs install` und `git lfs pull`.

## Branchen

| Ordner | Branche |
|---|---|
| [automobil](automobil/) | Automobil und Zulieferer |
| [industrie](industrie/) | Industrie, Maschinenbau und Bau |
| [chemie-rohstoffe](chemie-rohstoffe/) | Chemie und Rohstoffe |
| [energie-versorger](energie-versorger/) | Versorger und erneuerbare Energien |
| [pharma-gesundheit](pharma-gesundheit/) | Pharma, Biotech und Gesundheit |
| [software-it](software-it/) | Software und IT-Dienstleistungen |
| [technologie](technologie/) | Technologie, Halbleiter und Elektronik |
| [telekom-medien](telekom-medien/) | Telekommunikation und Medien |
| [handel-konsum](handel-konsum/) | Handel, Konsum und Lebensmittel |
| [transport-logistik](transport-logistik/) | Transport und Logistik |
| [immobilien](immobilien/) | Immobilien |
| [finanzdienstleister](finanzdienstleister/) | Finanzdienstleister und Beteiligungsgesellschaften |
| [versicherungen](versicherungen/) | Versicherungen |
| [banken](banken/) | börsennotierte Banken, nur Kapitalmarktdaten; Erhebung unter [banken/bilanzvergleich-gj2025](../banken/bilanzvergleich-gj2025/) |

Stückzahlen und Abdeckung je Branche stehen im README des Branchenordners.

## Inhalt der Excel-Dateien

| Blatt | Inhalt |
|---|---|
| Übersicht | je Unternehmen: Stammdaten, letztes GJ (Umsatz, EBITDA, EBIT, Ergebnis, Bilanzsumme, EK, Nettofinanzschulden, Cashflows), Kurs, Börsenwert, EV, Multiples, Dividende, größter Meldepflichtiger laut BaFin, Link zum Geschäftsbericht |
| GuV, Bilanz, Cashflow | Konzernzahlen je Geschäftsjahr (bis zu fünf Jahre), Mio. Berichtswährung |
| Kennzahlen | Margen, Renditen, EK-Quote, Verschuldung, Capex- und Ausschüttungsquote je Jahr |
| Kapitalmarkt | Jahresschlusskurse 2019–2025, aktueller Kurs, Dividenden je Jahr, Kursentwicklung |
| Aktionäre (BaFin) | alle Stimmrechtsmitteilungen je Emittent (§§ 33, 34, 38, 39 WpHG) |
| Dokumente | im Repo abgelegte Berichte mit Quelle und SHA-256 |
| Rohdaten Yahoo | alle gelieferten Posten in Originalbezeichnung |
| Methodik | Quellen, Definitionen, Grenzen |

## Quellen

- Deutsche Börse (Listed companies, T7-Instrumentenlisten), Börse München (m:access), Börse Düsseldorf (Primärmarkt)
- Yahoo Finance über `yfinance` (Kurse, Marktdaten, standardisierte Konzernabschlüsse)
- BaFin-Datenbank bedeutender Stimmrechtsanteile (einmaliger Gesamtexport über die Oberfläche)
- Geschäftsberichte von den Investor-Relations-Seiten der Unternehmen

Unternehmensregister und Bundesanzeiger wurden nicht automatisiert abgefragt (Sicherheitsabfrage). Websites, die automatisierte Abrufe sperren (Bot-Schutz, Captcha), wurden nicht umgangen; diese Unternehmen stehen in `rohdaten/berichte_status.json` mit dem Vermerk „gesperrt“.

## Ablauf (Neuberechnung)

```
python3 universum/skripte/universum.py      # Börsenlisten -> Rohliste
python3 skripte/yahoo_abruf.py              # Yahoo-Daten je ISIN (vorhandene werden übersprungen; --neu, --info)
python3 universum/skripte/unternehmen.py    # Unternehmen, Branchen
python3 skripte/berichte_suche.py <ein.json> <aus.json>   # Geschäftsberichte auf den IR-Seiten suchen
python3 skripte/berichte_laden.py <aus.json>              # laden, prüfen, ablegen, index.csv
python3 skripte/dokumente_umsortieren.py    # nach Branchenänderungen
python3 skripte/build.py                    # Excel und Branchen-READMEs
```

## Stand und nächste Etappen

Etappe 1 (27.10.2026): Universum, Branchen, Kapitalmarkt- und Yahoo-Abschlussdaten für alle Unternehmen, Stimmrechte, erste Runde Geschäftsberichte. Offen: fehlende Geschäftsberichte (Websites mit Bot-Schutz oder reinem JavaScript), Abgleich der Yahoo-Zahlen mit den Berichten, Segmentangaben aus den Berichten, Branche für Branche.
