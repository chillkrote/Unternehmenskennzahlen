# Governance: Vorstand, Aufsichtsrat, Vergütung, Personenprofile

Erhebung für alle Unternehmen des Repos (Banken aus `banken/bilanzvergleich-gj2025`, Börsenunternehmen aus `boersennotierte-unternehmen`). Stand 27.10.2026: **Pilot mit drei Banken** (Commerzbank, Deutsche Bank, HypoVereinsbank), Schema steht. Die Börsenunternehmen folgen, sobald deren Geschäftsberichte abrufbar sind (siehe „Offen“).

## Regeln
- Jede Angabe trägt `quelle_dokument` (Pfad im Repo oder URL) und `seite` (**PDF-Seite**, nicht die aufgedruckte Seitenzahl).
- Es steht nur, was im Dokument steht. Das Geschlecht wird **nicht** aus Vornamen geschlossen; Frauenzahlen nur, wenn das Dokument sie nennt oder jedes Mitglied eine geschlechtsmarkierte Funktionsbezeichnung trägt (dann mit Hinweis in `bemerkung`). Sonst bleibt das Feld leer.
- Personenangaben beschränkt auf beruflich Relevantes aus Veröffentlichungen der Unternehmen (Organverzeichnis, § 285 Nr. 10 HGB / § 125 AktG, Geschäftsbericht, Website). Keine privaten Daten (kein Wohnort, keine Familie), auch wenn ein Verzeichnis sie nennt.
- Leere Felder bedeuten „nicht ermittelt“, ein Hinweis in `bemerkung` sagt warum. Kleine Institute ohne Pflichtangaben (z. B. Sparkassen) bleiben leer bzw. werden gekennzeichnet.

## Tabellen (UTF-8, Komma)
| Datei | Inhalt | Schlüssel |
|---|---|---|
| `personen.csv` | Stammtabelle, eine Zeile je Person | `person_id` (Slug des Namens ohne Titel; bei Namensgleichheit manuell mit Suffix) |
| `gremien_mitglieder.csv` | Mitgliedschaft in Vorstand/Geschäftsführung/Aufsichtsrat mit Funktion, Vertreterart (Anteilseigner, Arbeitnehmer, Arbeitnehmer (Gewerkschaft)), `seit`/`bis`, Beruf laut Dokument | `unternehmen_id`, `gj`, `organ`, `person_id` |
| `mandate_extern.csv` | weitere Gremienmandate (Typ a = gesetzlicher AR im Inland, b = vergleichbares Kontrollgremium) mit Zeitbezug; `gesellschaft_unternehmen_id` verknüpft, wenn die Gesellschaft selbst im Repo steht (z. B. Sigmar Gabriel: Deutsche Bank, Rheinmetall, Siemens Energy) | `person_id`, `gesellschaft` |
| `werdegang.csv` | beruflicher Werdegang in Stationen mit Quelle (Pilot: Beruf laut Organverzeichnis; Lebensläufe aus Geschäftsberichten/Websites folgen) | `person_id` |
| `verguetung.csv` | Vergütung je Gremium und GJ, Einzelwerte (soweit angegeben) und Gesamt, mit Basis (§ 285 Nr. 9a HGB, § 162 AktG, DCGK-Tabelle) | `unternehmen_id`, `gj`, `gremium`, `person_id` |
| `kennzahlen_gremien.csv` | Langformat je Unternehmen/GJ: `vorstand_mitglieder_zahl`, `vorstand_frauen_zahl`, `ar_mitglieder_zahl`, `ar_frauen_zahl`, `ar_arbeitnehmervertreter_zahl`, `ar_gewerkschaftsvertreter_zahl`, `mitbestimmung_ar` (MitbestG / DrittelbG / MontanMitbestG / keine), `pay_ratio` (CEO zu Durchschnittsbelegschaft laut Vergütungsbericht, mit Definition), `mitarbeiter_jahresdurchschnitt` | `unternehmen_id`, `gj`, `feld` |

`unternehmen_id` entspricht `zeitreihen/stammdaten.csv` (Banken) bzw. `universum/universum.csv` (Börsenunternehmen). Das Langformat erlaubt neue Felder ohne Schemaänderung und je Wert eine Quelle.

## Erhebungsreihenfolge
1. Pilot Banken aus lokal vorhandenen Jahresabschlüssen: erledigt für Commerzbank, Deutsche Bank, HypoVereinsbank (`skripte/pilot_banken.py`).
2. DAX/MDAX: Geschäftsbericht inkl. Corporate-Governance-Erklärung und Vergütungsbericht (Einzelvergütung, Pay Ratio, Frauenquote, Mitbestimmung).
3. Übrige große Banken (Landesbanken, DZ BANK, Aareal, apoBank, pbb …), dann SDAX/übrige Börsenunternehmen, dann Rest. Sparkassen/Genossenschaftsbanken nur mit den Pflichtangaben aus dem Jahresabschluss.
4. Folgejahre rückwärts (10 Jahre) für Zeitbezug der Mandate.

## Offen
- Pay Ratio, Frauenquote Vorstand, Einzelvergütung und ausführliche Lebensläufe stehen nicht im HGB-Jahresabschluss, sondern im Geschäftsbericht bzw. Vergütungsbericht. Für die Börsenunternehmen liegen die PDFs nicht im Repo (LFS-Upload damals gescheitert) und die Unternehmensseiten sind für die Sitzung gesperrt.
- Anbindung an das Bank-Terminal (`app/`): Profilseite je Unternehmen zeigt Gremien und Kennzahlen; Personen-Profilseite aus `personen`/`gremien_mitglieder`/`mandate_extern`/`werdegang`.
