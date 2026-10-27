# Bilanzvergleich Banken GJ 2025

Vergleich von 129 deutschen Banken (je 40 größte Sparkassen und Genossenschaftsbanken, Landesbanken, 40 größte Privatbanken) zum Stichtag 31.12.2025, seit 27.10.2026 ergänzt um 79 weitere Banken, die im EBA-Pillar-3-Datenhub mit dem Länderfilter DE erscheinen (Rolle „EBA-Hub“, grün hinterlegt). Stand der Erhebung: 27.10.2026.

## Inhalt

| Ordner | Inhalt |
|---|---|
| `auswertung/Bilanzvergleich_Banken_GJ2025.xlsx` | aktuelle Auswertung (Übersicht, Kernkapital, Zeitreihe, Offenlegung 31.12.2025, Eigenmittel CC1, RWA-Aufteilung OV1, Bilanzen 31.12.2025, Methodik) |
| `auswertung/archiv/` | frühere Stände der Excel-Datei |
| `auswertung/berichte/` | schriftliche Auswertungen als Markdown (Kapitalstrukturen, Kapitalanforderungen, Eigenkapitalvorschriften); Originale als Claude-Dokumente, Links jeweils in der ersten Zeile. Das Dashboard „Kapitalquoten deutscher Bankengruppen“ liegt unter https://claude.ai/artifact/TmXMqbTXNwx3yAy3QYqWtd |
| `auswertung/*.csv` | Arbeitslisten: noch fehlende Bilanzen (Unternehmensregister), Vorjahresabschlüsse auf Bank-Websites, Berichte zum manuellen Abruf |
| `dokumente/<bank>/` | Originaldokumente (PDF) je Bank: Jahresabschlüsse/Geschäftsberichte, Offenlegungsberichte, Halbjahresberichte |
| `dokumente/_mehrere-banken/` | Ranglisten (BVR, DSGV), die für die Auswahl der Banken genutzt wurden |
| `dokumente/index.csv` | ein Eintrag je Quelle: Bank, Dokumentart, Jahr, Datei, Status, Quell-URL, Abruf, SHA-256, welche Rohdaten/Blätter die Quelle nutzen |
| `webseiten/<bank>/` | HTML-Schnappschüsse, wo die Quelle eine Webseite war (z. B. Kennzahlen-Seiten, Lobbyregister) |
| `rohdaten/` | extrahierte Werte als JSON (Grundlage aller Blätter der Excel) |
| `rohdaten/eba-hub/` | Exporte aus dem EBA-Pillar-3-Datenhub: KM1, CC1, OV1, CC2 (Bilanz) zum 31.12.2025 und KM1 für alle Stichtage, jeweils Filter Country = Germany |
| `rohdaten/eba_hub_neu_2025.json` | aufbereitete Hub-Werte (KM1, CC1, OV1, Bilanz aus CC2) je Bank, getrennt nach neuen (79) und bereits erfassten (93) Banken |
| `rohdaten/skripte/` | `build.py` erzeugt die Excel aus den JSONs, `mk_zr.py` die Zeitreihe, `mk_hub_neu.py` die Datei `eba_hub_neu_2025.json` aus den Hub-Exporten; `erhebung/` enthält Download-, Parser- und Sortierskripte, `erhebung/eba-hub-export/` die Playwright-Skripte, die die normale Hub-Oberfläche bedienen |

`index.csv` ist semikolon-getrennt (UTF-8 mit BOM, öffnet direkt in Excel). Bei Quellen, die nicht mehr abrufbar sind, nennen `ersatz_datei` und `ersatz_hinweis` das Ersatzdokument bzw. warum es keins gibt. Die Spalte `bank` enthält bei einigen Quellen den Hinweistext aus der Erhebung statt nur des Banknamens.

## Abdeckung

- **Dokumente:** 256 Quellen aus der Erhebung, dazu 20 Ersatzdokumente (Nachsuche 27.10.2026). 44 Quellen waren am 26.10.2026 nicht mehr erreichbar. Für 18 davon gibt es jetzt ein neu geladenes Ersatzdokument (neue Adresse, Vorjahresbericht oder Offenlegungsbericht), für 14 stehen die Werte in einem eigenen Bericht der Bank, der schon im Repo liegt. Für 12 gibt es keinen frei abrufbaren Ersatz (u. a. BMW Bank, Mercedes-Benz Bank, BDK, C24, ODDO BHF, norisbank, Hauck Aufhäuser Lampe, Akbank, Santander, Hyundai); deren Abschlüsse liegen nur im Unternehmensregister oder hinter Bot-Schutz.
- **Bilanzen 31.12.2025 (HGB, volle Formblatt-1-Bilanz):** 99 von 129 Banken der bisherigen Auswahl (11 Sparkassen kamen am 27.10.2026 über die Hub-Tabelle CC2 dazu). Die 29 fehlenden stehen in `auswertung/Bilanzen_GJ2025_aus_Unternehmensregister.csv`; sie sind nur über das Unternehmensregister bzw. den Bundesanzeiger abrufbar.
- **Offenlegung KM1 31.12.2025:** 97 von 129 Banken (32 aus Berichten auf Bank-Websites, 65 aus dem EBA-Datenhub; Landesbank Berlin und Siemens Bank neu).
- **CC1/OV1:** 90 Banken der bisherigen Auswahl aus dem EBA-Datenhub.
- **EBA-Hub-Ergänzung (79 neue Banken):** KM1 78, CC1 77, OV1 75, Bilanzsumme 72, Eigenkapital 71, Fonds § 340g 55, volle Bilanz 57. Ohne CC2 im Hub: u. a. Trade Republic, BHW, SWK Bank, Sparkasse Duisburg, Sparkasse Südpfalz. Die neuen Banken sind einer der Gruppen zugeordnet (neue Gruppe „Förder- und Sonderinstitute“ für KfW IPEX und KfW Beteiligungsholding), zählen aber nicht für Top-10/Top-40-Ränge, Gruppenauswertung und Krefeld-Vergleich. Mediane gibt es zweifach: bisherige Auswahl und alle inkl. Ergänzung.
- **Lückenfüllung 27.10.2026:** Leere Zellen wurden aus frei abrufbaren Berichten nachgetragen (Offenlegungsberichte 2021–2025 mit Tabelle EU CC2, Geschäftsberichte mit Vorjahresspalte, GLEIF-Register für den Sitz). Offene Zellen über alle 208 Banken, vorher → nachher: Sitz 79 → 0, Jahresüberschuss 2025 136 → 68, Kernkapital-Posten (Bilanzgewinn) 132 → 60, Vorjahres-Bilanzsumme 90 → 43, Fonds § 340g 40 → 34, Eigenkapital 14 → 13, Bilanzsumme 7 → 6, volle Bilanz 51 → 50. Zeitreihe: Bilanzsumme 2021 jetzt für 48, 2022 für 61, 2023 für 79 Banken. 233 neue Quell-PDFs unter `dokumente/<bank>/` (in `index.csv` mit „Nacherhebung 27.10.2026“). Werte je Zelle mit Quelle in `rohdaten/nacherhebung_2026-10-27.json`, Sitz in `rohdaten/gleif_sitz.json`, Skripte in `rohdaten/skripte/erhebung/nacherhebung/`. Übernommen wird nur in leere Zellen und nur bei plausibler Größe zum Bestand. Bei Sparkassen ist der Jahresüberschuss gleich dem Bilanzgewinn (an 11 Sparkassen geprüft) und wird daraus übernommen. Korrigiert: Jahresüberschuss MünchenerHyp 2025/2024 (106,1 / 105,6 Mio. € laut GB 2025, vorher Halbjahreswert). Weiter offen sind vor allem KM1/CC1/OV1 für Banken ohne Hub-Eintrag und Abschlüsse privater Banken, die nur im Unternehmensregister stehen. Die DSGV- und BVR-Ranglisten 2021–2024 sind nicht mehr online.
- **Bilanz aus CC2:** Der Hub-Export lässt Posten ohne eigenen Schlüssel leer (meist Verbindlichkeiten gegenüber Kunden, Schuldtitel, Gewinnrücklage). Diese Posten sind als Differenz zur Bilanzsumme bzw. aus CC1 berechnet und in der Hinweis-Spalte vermerkt. IFRS-Gruppen (z. B. Banken mit Konzernabschluss) erhalten nur Summen.

## Quellen

- Geschäftsberichte, Jahresabschlüsse und Offenlegungsberichte auf den Websites der Banken
- EBA Pillar 3 Data Hub (edap-public.eba.europa.eu), Export über die normale Oberfläche (Data Points Report, Filter Country = Germany, Summarized data); keine API-Abfragen
- EU-CC2-Tabellen der Offenlegungsberichte (enthalten die HGB-Bilanz)
- hauptversammlung.de, Lobbyregister des Bundestages (für einzelne Privatbanken)
- GLEIF-LEI-Register (api.gleif.org) für den Sitz der neuen Hub-Institute

Unternehmensregister und Bundesanzeiger wurden nicht automatisiert abgefragt (Sicherheitsabfrage).

## Bekannte Abweichungen

- Hanseatic Bank: Übersicht nutzt die Bilanzsumme 2024, das Blatt Bilanzen die von 2025.
- Stadtsparkasse München (Eigenkapital 1.541 vs. 1.533 Mio. €) und Sparkasse Wuppertal (Bilanzsumme 8.312 vs. 8.295 Mio. €): kleine Differenzen zwischen Bilanz und Übersicht, in der Hinweis-Spalte vermerkt.
- Nicht übernommen: Sparkasse Bremen (CC2 nur auf Ebene der Finanzholding), Baader Bank (nur Konzernzahlen), TARGOBANK (keine HGB-Bilanz).
