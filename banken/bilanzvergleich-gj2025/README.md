# Bilanzvergleich Banken GJ 2025

Vergleich von 129 deutschen Banken (je 40 größte Sparkassen und Genossenschaftsbanken, Landesbanken, 40 größte Privatbanken) zum Stichtag 31.12.2025. Stand der Erhebung: 26.10.2026.

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
| `rohdaten/eba-hub/` | Exporte aus dem EBA-Pillar-3-Datenhub (KM1, CC1, OV1 zum 31.12.2025) |
| `rohdaten/skripte/` | `build.py` erzeugt die Excel aus den JSONs, `mk_zr.py` die Zeitreihe; `erhebung/` enthält Download-, Parser- und Sortierskripte |

`index.csv` ist semikolon-getrennt (UTF-8 mit BOM, öffnet direkt in Excel). Bei Quellen, die nicht mehr abrufbar sind, nennen `ersatz_datei` und `ersatz_hinweis` das Ersatzdokument bzw. warum es keins gibt. Die Spalte `bank` enthält bei einigen Quellen den Hinweistext aus der Erhebung statt nur des Banknamens.

## Abdeckung

- **Dokumente:** 256 Quellen aus der Erhebung, dazu 20 Ersatzdokumente (Nachsuche 27.10.2026). 44 Quellen waren am 26.10.2026 nicht mehr erreichbar. Für 18 davon gibt es jetzt ein neu geladenes Ersatzdokument (neue Adresse, Vorjahresbericht oder Offenlegungsbericht), für 14 stehen die Werte in einem eigenen Bericht der Bank, der schon im Repo liegt. Für 12 gibt es keinen frei abrufbaren Ersatz (u. a. BMW Bank, Mercedes-Benz Bank, BDK, C24, ODDO BHF, norisbank, Hauck Aufhäuser Lampe, Akbank, Santander, Hyundai); deren Abschlüsse liegen nur im Unternehmensregister oder hinter Bot-Schutz.
- **Bilanzen 31.12.2025 (HGB, volle Formblatt-1-Bilanz):** 89 von 129 Banken. Die 40 fehlenden stehen in `auswertung/Bilanzen_GJ2025_aus_Unternehmensregister.csv`; sie sind nur über das Unternehmensregister bzw. den Bundesanzeiger abrufbar.
- **Offenlegung KM1 31.12.2025:** 95 von 129 Banken (32 aus Berichten auf Bank-Websites, 63 aus dem EBA-Datenhub).
- **CC1/OV1:** 89 Banken aus dem EBA-Datenhub.

## Quellen

- Geschäftsberichte, Jahresabschlüsse und Offenlegungsberichte auf den Websites der Banken
- EBA Pillar 3 Data Hub (edap-public.eba.europa.eu), Export über die normale Oberfläche
- EU-CC2-Tabellen der Offenlegungsberichte (enthalten die HGB-Bilanz)
- hauptversammlung.de, Lobbyregister des Bundestages (für einzelne Privatbanken)

Unternehmensregister und Bundesanzeiger wurden nicht automatisiert abgefragt (Sicherheitsabfrage).

## Bekannte Abweichungen

- Hanseatic Bank: Übersicht nutzt die Bilanzsumme 2024, das Blatt Bilanzen die von 2025.
- Stadtsparkasse München (Eigenkapital 1.541 vs. 1.533 Mio. €) und Sparkasse Wuppertal (Bilanzsumme 8.312 vs. 8.295 Mio. €): kleine Differenzen zwischen Bilanz und Übersicht, in der Hinweis-Spalte vermerkt.
- Nicht übernommen: Sparkasse Bremen (CC2 nur auf Ebene der Finanzholding), Baader Bank (nur Konzernzahlen), TARGOBANK (keine HGB-Bilanz).
