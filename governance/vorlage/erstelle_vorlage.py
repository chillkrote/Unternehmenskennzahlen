#!/usr/bin/env python3
"""Baut governance/vorlage/Importvorlage_Governance.xlsx aus schema.py.
Aufruf aus dem Repo-Root: python3 governance/vorlage/erstelle_vorlage.py [Zieldatei]"""
import csv
import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

HIER = Path(__file__).resolve().parent
REPO = HIER.parent.parent
sys.path.insert(0, str(HIER))
import schema as S  # noqa: E402

ZIEL = HIER / "Importvorlage_Governance.xlsx"
MAXZ = 3000     # Zeilen mit Datenvalidierung
MAXF = 1500     # Zeilen mit Kontrollformel
ID_LIMIT = None  # nur für Tests: Zahl der Zeilen der ID-Liste begrenzen
PFLICHT = PatternFill("solid", fgColor="1F3864")
OPTIONAL = PatternFill("solid", fgColor="5B6B8C")
AUTO = PatternFill("solid", fgColor="A6A6A6")
BSP = PatternFill("solid", fgColor="FFF2CC")
B = S.BEISPIEL
DATUMSSPALTEN = {"Stand", "Mitglied seit", "Mitglied bis", "Abrufdatum", "Veröffentlicht am"}


def spalte(spalten, name):
    return [s[0] for s in spalten].index(name) + 1


def kopf(ws, spalten):
    for i, (name, pflicht, breite, hinweis) in enumerate(spalten, 1):
        auto = name.endswith("(automatisch)")
        c = ws.cell(1, i, name + (" *" if pflicht else ""))
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = AUTO if auto else (PFLICHT if pflicht else OPTIONAL)
        c.alignment = Alignment(wrap_text=True, vertical="center")
        c.comment = Comment(("Pflicht. " if pflicht else "Optional. ") + hinweis, "Vorlage", width=360, height=140)
        ws.column_dimensions[get_column_letter(i)].width = breite
    ws.row_dimensions[1].height = 44
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(spalten))}1"


def liste(ws, spalten, name, formel, fehler, warnung=False):
    L = get_column_letter(spalte(spalten, name))
    dv = DataValidation(type="list", formula1=formel, allow_blank=True, showErrorMessage=True,
                        errorStyle="warning" if warnung else "stop", errorTitle="Ungültiger Wert", error=fehler)
    ws.add_data_validation(dv)
    dv.add(f"{L}2:{L}{MAXZ}")


def regel(ws, spalten, name, typ, fehler, op="between", **kw):
    L = get_column_letter(spalte(spalten, name))
    dv = DataValidation(type=typ, operator=op, allow_blank=True, showErrorMessage=True, errorTitle="Ungültiger Wert", error=fehler, **kw)
    ws.add_data_validation(dv)
    dv.add(f"{L}2:{L}{MAXZ}")


def id_regel(ws, spalten, name):
    L = get_column_letter(spalte(spalten, name))
    dv = DataValidation(type="custom", formula1=f'=AND(LEN({L}2)=7,LEFT({L}2,1)="U",ISNUMBER(VALUE(MID({L}2,2,6))))',
                        allow_blank=True, showErrorMessage=True, errorTitle="Ungültige ID",
                        error="Format U000123 (siehe Blatt ID-Liste). Keine eigenen IDs vergeben.")
    ws.add_data_validation(dv)
    dv.add(f"{L}2:{L}{MAXZ}")


def auto_formeln(ws, spalten, auto_name, id_name):
    a, i = get_column_letter(spalte(spalten, auto_name)), get_column_letter(spalte(spalten, id_name))
    for r in range(2, MAXF + 1):
        c = ws[f"{a}{r}"]
        c.value = f"=IF({i}{r}=\"\",\"\",IFERROR(INDEX('ID-Liste'!$B$2:$B$40000,MATCH({i}{r},'ID-Liste'!$A$2:$A$40000,0)),\"ID unbekannt!\"))"
        c.font = Font(color="7F7F7F", italic=True)


def beispiel(ws, spalten, zeile):
    r = 2
    for c, v in enumerate(zeile, 1):
        cell = ws.cell(r, c, v)
        cell.fill = BSP
        if isinstance(v, date):
            cell.number_format = "DD.MM.YYYY"


def datumsformat(ws, spalten):
    for name in DATUMSSPALTEN:
        if name in [s[0] for s in spalten]:
            col = spalte(spalten, name)
            for r in range(2, MAXZ + 1):
                ws.cell(r, col).number_format = "DD.MM.YYYY"
            if name in ("Stand", "Abrufdatum", "Veröffentlicht am"):
                regel(ws, spalten, name, "date", "Datum TT.MM.JJJJ.", formula1="36526", formula2="73415")


def lade_ids():
    reg = REPO / "stammdaten" / "unternehmen_ids.csv"
    gov = set()
    for f in ("gremien_mitglieder.csv", "kennzahlen_gremien.csv", "verguetung.csv"):
        p = REPO / "governance" / f
        if p.exists():
            with open(p, encoding="utf-8-sig") as fh:
                gov |= {r["unternehmen_id"] for r in csv.DictReader(fh)}
    rows = []
    with open(reg, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            rows.append((r["unternehmen_id"], r["name"], r["land"], r["status"], r["isin_haupt"], "ja" if r["unternehmen_id"] in gov else ""))
    return sorted(rows, key=lambda x: x[1].lower())[:ID_LIMIT]


def anleitung(a):
    a.column_dimensions["A"].width = 135
    z = [
        ("Importvorlage Governance (Version %s)" % S.VERSION, "t"),
        ("Zweck: Gremien, Personen, Vergütung, Pay Ratio, Frauen- und Mitbestimmungszahlen per Hand erfassen. Das Import-Skript governance/vorlage/importieren.py liest die Datei, prüft sie und überführt sie in die Governance-Daten (governance/*.csv). Blattnamen, Spaltenköpfe und Reihenfolge NICHT ändern.", None),
        ("", None),
        ("Blätter", "h"),
        ("Gremienmitglieder: eine Zeile je Person, Organ, Unternehmen und Geschäftsjahr (Vorstand, Aufsichtsrat, Geschäftsführung ...). Hier werden Personen angelegt; alle anderen Blätter verweisen über den Namen darauf.", None),
        ("Vergütung: Einzelvergütung und Summenzeilen je Gremium in T€, mit Art (Basis der Zahl).", None),
        ("Kennzahlen Gremien: Zählfelder aus dem Blatt Feldliste (Zahl der Mitglieder, Frauen, Arbeitnehmer-/Gewerkschaftsvertreter, Mitbestimmungsregime, Mitarbeiterzahl).", None),
        ("Pay Ratio: Eingangsdaten für Variante A (Ø-Vergütung Beschäftigte), Variante B (Personalaufwand und Beschäftigte) oder die vom Unternehmen berichtete Quote. Berechnen müssen Sie nichts.", None),
        ("Geschlecht (Belege): Geschlecht einer Person nur mit wörtlichem Beleg aus dem Dokument. Grundlage für Frauenzahlen und Gender Pay Gap.", None),
        ("Mandate extern: weitere Aufsichtsrats- bzw. Kontrollgremienmandate einer Person (Typ a/b) mit Zeitbezug.", None),
        ("Werdegang: berufliche Stationen einer Person.", None),
        ("Quellen-Dokumente: Register der verwendeten Dokumente (Titel, Link, Abrufdatum, Veröffentlichungsdatum). Jeder https-Link, der in einem Datenblatt als Quelle steht, sollte hier einmal erfasst sein.", None),
        ("Feldliste, Listen, ID-Liste: Nachschlageblätter für Dropdowns, erlaubte Felder und Unternehmens-IDs. Nicht ändern.", None),
        ("", None),
        ("Regeln", "h"),
        ("Pflichtfelder: Spalten mit * im Kopf (dunkelblau). Optionale Spalten sind grau, die Kontrollspalte (automatisch) gesperrtgrau. Gelbe Zeilen sind Muster (Text [Beispiel]) und werden ignoriert; gern löschen.", None),
        ("Unternehmens-ID: immer eintragen (Format U000123). Sie steht in der ID-Liste (Name, Land, ISIN). Neue Unternehmen müssen zuerst über die Unternehmens-Importvorlage (vorlagen/) registriert werden; IDs nie selbst vergeben.", None),
        ("Leer lassen statt raten: nur eintragen, was im Dokument steht. Keine Schätzungen, keine Hochrechnungen, kein Wissen aus Erinnerung. Was fehlt, bleibt leer, die Begründung kommt in die Bemerkung.", None),
        ("Quelle und Seite je Zeile: Quelle = Pfad im Repo (governance/dokumente/<Ordner>/<Datei>.pdf) oder direkter https-Link. Seite = PDF-Seite, nicht die aufgedruckte Seitenzahl. Stand = Datum, auf das sich die Angabe bezieht.", None),
        ("Geschlecht niemals aus dem Vornamen ableiten. Frauenzahlen nur eintragen, wenn das Dokument sie nennt oder jede Person eine geschlechtsmarkierte Bezeichnung trägt (Beleg im Blatt Geschlecht).", None),
        ("Datenschutz: nur beruflich Relevantes aus Veröffentlichungen der Unternehmen (Organverzeichnis, § 285 Nr. 10 HGB, § 125 AktG, Geschäftsbericht, Website). Kein Wohnort, keine Familie, kein Geburtsdatum.", None),
        ("Namen: Personen in allen Blättern genau gleich schreiben (Titel wie im Dokument). Daraus entsteht die Personen-ID (Kleinbuchstaben ohne Titel, z. B. Dr. Bettina Orlopp wird bettina-orlopp). Name in Vergütung, Mandate, Werdegang und Geschlecht muss im Blatt Gremienmitglieder oder bereits in governance/personen.csv stehen.", None),
        ("Datumsangaben TT.MM.JJJJ; bei Mitglied seit/bis ist auch JJJJ-MM oder JJJJ als Text erlaubt. Geschäftsjahr vierstellig (das Jahr, in dem es endet).", None),
        ("Beträge: Vergütung in T€ als Zahl ohne Tausenderpunkt (6896,216). Keine Umrechnung fremder Währungen; solche Angaben mit Originalwert in die Bemerkung und die Zeile ohne Betrag lassen.", None),
        ("Pro Schlüssel genau eine Zeile: Gremienmitglieder (ID, GJ, Organ, Name), Vergütung (ID, GJ, Gremium, Name, Art), Kennzahlen (ID, GJ, Feld), Pay Ratio (ID, GJ, Variante, Bezug). Zeilen, die schon im Bestand stehen, werden als Fehler gemeldet.", None),
        ("Pay Ratio: Variante A braucht die Ø-Vergütung der Beschäftigten (T€) und den Beschäftigtenkreis; B braucht Personalaufwand (Mio. €) und Beschäftigtenzahl; Bericht braucht die berichtete Quote. Vorstandsvergütung für Zähler kommt aus dem Blatt Vergütung. Die Quote selbst wird später berechnet.", None),
        ("", None),
        ("Abgabe und Import", "h"),
        ("Datei als .xlsx speichern, Blattnamen unverändert. Prüfung ohne Schreiben: python3 governance/vorlage/importieren.py Datei.xlsx  (optional --bericht pruefbericht.md). Bei Fehlern wird nichts geschrieben.", None),
        ("Übernahme: python3 governance/vorlage/importieren.py Datei.xlsx --schreiben legt governance/handeingabe/<Dateiname>.json an und erzeugt die CSV-Tabellen neu (governance/skripte/build.py). Danach python3 governance/skripte/berechnung.py für Pay Ratio und Gender Pay Gap.", None),
    ]
    for i, (t, st) in enumerate(z, 1):
        c = a.cell(i, 1, t)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if st == "t":
            c.font = Font(bold=True, size=15)
        elif st == "h":
            c.font = Font(bold=True, size=12, color="1F3864")


def baue(ziel=ZIEL):
    wb = Workbook()
    anleitung(wb.active)
    wb.active.title = "Anleitung"
    # Nachschlageblätter
    L = wb.create_sheet("Listen")
    spalten = [("Organ", S.ORGANE), ("Vertreterart", S.VERTRETERART), ("Gremium", S.GREMIEN_VERG), ("Typ", S.MANDAT_TYP), ("Geschlecht", S.GESCHLECHT),
               ("Variante", S.VARIANTEN), ("Bezug Pay Ratio", S.BEZUG_PAYRATIO), ("Mitbestimmung", S.MITBESTIMMUNG), ("Vergütungsart", S.VERG_ARTEN),
               ("Werdegang-Art", S.WERDEGANG_ARTEN), ("Dokumentart", S.DOKUMENTARTEN)]
    ref = {}
    for i, (n, werte) in enumerate(spalten, 1):
        L.cell(1, i, n).font = Font(bold=True)
        for j, w in enumerate(werte, 2):
            L.cell(j, i, w)
        ref[n] = f"Listen!${get_column_letter(i)}$2:${get_column_letter(i)}${len(werte) + 1}"
        L.column_dimensions[get_column_letter(i)].width = 30
    F = wb.create_sheet("Feldliste")
    for i, (h, w) in enumerate([("Feld", 36), ("Typ", 8), ("Einheit", 10), ("Definition", 110)], 1):
        F.cell(1, i, h).font = Font(bold=True)
        F.column_dimensions[get_column_letter(i)].width = w
    for r, f in enumerate(S.FELDER, 2):
        for c, v in enumerate(f, 1):
            F.cell(r, c, v).alignment = Alignment(wrap_text=True, vertical="top")
    feld_ref = f"Feldliste!$A$2:$A${len(S.FELDER) + 1}"
    I = wb.create_sheet("ID-Liste")
    for i, (h, w) in enumerate([("Unternehmens-ID", 16), ("Name", 50), ("Land", 16), ("Status", 16), ("ISIN", 16), ("Governance erfasst", 18)], 1):
        I.cell(1, i, h).font = Font(bold=True)
        I.column_dimensions[get_column_letter(i)].width = w
    for r, row in enumerate(lade_ids(), 2):
        for c, v in enumerate(row, 1):
            I.cell(r, c, v)
    I.freeze_panes = "A2"
    I.auto_filter.ref = f"A1:F{I.max_row}"

    sd = date(2025, 12, 31)
    URL = "https://www.beispiel.example/verguetungsbericht-2025.pdf"
    ID = "U000000"
    # Gremienmitglieder
    ws = wb.create_sheet("Gremienmitglieder", 1)
    sp = S.GREMIEN
    kopf(ws, sp); auto_formeln(ws, sp, "Unternehmen (automatisch)", "Unternehmens-ID"); id_regel(ws, sp, "Unternehmens-ID")
    liste(ws, sp, "Organ", "=" + ref["Organ"], "Organ aus der Liste wählen.")
    liste(ws, sp, "Vertreterart", "=" + ref["Vertreterart"], "Vertreterart aus der Liste wählen.")
    regel(ws, sp, "Geschäftsjahr", "whole", "Vierstellige Jahreszahl 2000 bis 2100.", formula1="2000", formula2="2100")
    beispiel(ws, sp, [ID, None, 2025, "Aufsichtsrat", B + " Dr. Erika Mustermann", "stellv. Vorsitzende", "Arbeitnehmer (Gewerkschaft)", "01.05.2022", None,
                      "Gewerkschaftssekretärin", URL, 31, sd, "Fiktives Muster"])
    datumsformat(ws, sp)
    # Vergütung
    ws = wb.create_sheet("Vergütung", 2)
    sp = S.VERGUETUNG
    kopf(ws, sp); auto_formeln(ws, sp, "Unternehmen (automatisch)", "Unternehmens-ID"); id_regel(ws, sp, "Unternehmens-ID")
    liste(ws, sp, "Gremium", "=" + ref["Gremium"], "Gremium aus der Liste wählen.")
    liste(ws, sp, "Art", "=" + ref["Vergütungsart"], "Eigener Text ist zulässig, möglichst wörtlich aus dem Dokument.", warnung=True)
    regel(ws, sp, "Geschäftsjahr", "whole", "Vierstellige Jahreszahl 2000 bis 2100.", formula1="2000", formula2="2100")
    regel(ws, sp, "Betrag (TEUR)", "decimal", "Nur Zahl in T€ (kein Text, kein Tausenderpunkt).", formula1="0", formula2="1E+9")
    beispiel(ws, sp, [ID, None, 2025, "Vorstand", B + " Dr. Max Beispiel", 3450.5, S.VERG_ARTEN[0], URL, 28, sd, "Fiktives Muster; Original 3.450.500 EUR"])
    ws.append([ID, None, 2025, "Vorstand", B + " Gesamt (alle Mitglieder)", 9800, "Gesamtvergütung", URL, 29, sd, "Fiktives Muster"])
    for c in range(1, len(sp) + 1):
        ws.cell(3, c).fill = BSP
    datumsformat(ws, sp)
    # Kennzahlen Gremien
    ws = wb.create_sheet("Kennzahlen Gremien", 3)
    sp = S.KENNZAHLEN
    kopf(ws, sp); auto_formeln(ws, sp, "Unternehmen (automatisch)", "Unternehmens-ID"); id_regel(ws, sp, "Unternehmens-ID")
    liste(ws, sp, "Feld", "=" + feld_ref, "Nur Felder aus dem Blatt Feldliste.")
    regel(ws, sp, "Geschäftsjahr", "whole", "Vierstellige Jahreszahl 2000 bis 2100.", formula1="2000", formula2="2100")
    beispiel(ws, sp, [ID, None, 2025, "ar_frauen_zahl", 6, "Personen", URL, 41, sd, B + " Fiktives Muster"])
    datumsformat(ws, sp)
    # Pay Ratio
    ws = wb.create_sheet("Pay Ratio", 4)
    sp = S.PAYRATIO
    kopf(ws, sp); auto_formeln(ws, sp, "Unternehmen (automatisch)", "Unternehmens-ID"); id_regel(ws, sp, "Unternehmens-ID")
    liste(ws, sp, "Variante", "=" + ref["Variante"], "A, B oder Bericht.")
    liste(ws, sp, "Bezug", "=" + ref["Bezug Pay Ratio"], "Eigener Text ist zulässig.", warnung=True)
    regel(ws, sp, "Geschäftsjahr", "whole", "Vierstellige Jahreszahl 2000 bis 2100.", formula1="2000", formula2="2100")
    for n in ("Pay Ratio (berichtet)", "Ø-Vergütung Beschäftigte (TEUR)", "Personalaufwand Konzern (Mio. EUR)", "Beschäftigte (Anzahl)"):
        regel(ws, sp, n, "decimal", "Nur Zahl.", formula1="0", formula2="1E+12")
    beispiel(ws, sp, [ID, None, 2025, "A", "Vorstandsvorsitzender", None, 112.5, None, None, "Beschäftigte Deutschland, Vollzeitäquivalente", URL, 40, sd, B + " Fiktives Muster"])
    ws.append([ID, None, 2025, "Bericht", "Ausweis laut Bericht", 85.3, None, None, None, "Median aller Beschäftigten Konzern, Zielvergütung CEO", URL, 41, sd, B + " Fiktives Muster"])
    for c in range(1, len(sp) + 1):
        ws.cell(3, c).fill = BSP
    datumsformat(ws, sp)
    # Geschlecht
    ws = wb.create_sheet("Geschlecht (Belege)", 5)
    sp = S.GESCHLECHT_BELEGE
    kopf(ws, sp); auto_formeln(ws, sp, "Unternehmen (automatisch)", "Unternehmens-ID"); id_regel(ws, sp, "Unternehmens-ID")
    liste(ws, sp, "Geschlecht", "=" + ref["Geschlecht"], "weiblich, männlich oder divers.")
    beispiel(ws, sp, [B + " Dr. Erika Mustermann", ID, None, "weiblich", 'Bezeichnung "Vorständin" im Vergütungsbericht', URL, 28])
    # Mandate
    ws = wb.create_sheet("Mandate extern", 6)
    sp = S.MANDATE
    kopf(ws, sp); id_regel(ws, sp, "Gemeldet von (Unternehmens-ID)"); id_regel(ws, sp, "Gesellschaft-ID")
    auto_formeln(ws, sp, "Gemeldet von (automatisch)", "Gemeldet von (Unternehmens-ID)")
    liste(ws, sp, "Typ", "=" + ref["Typ"], "a oder b.")
    regel(ws, sp, "Geschäftsjahr", "whole", "Vierstellige Jahreszahl 2000 bis 2100.", formula1="2000", formula2="2100")
    beispiel(ws, sp, [B + " Dr. Max Beispiel", "a", "Muster Chemie AG", None, "Düsseldorf", "Mitglied des Aufsichtsrats", "seit 2024-05-15", ID, None, 2025, URL, 33, "Fiktives Muster"])
    # Werdegang
    ws = wb.create_sheet("Werdegang", 7)
    sp = S.WERDEGANG
    kopf(ws, sp)
    liste(ws, sp, "Art", "=" + ref["Werdegang-Art"], "Eigener Text ist zulässig.", warnung=True)
    beispiel(ws, sp, [B + " Dr. Max Beispiel", "Leiter Konzerncontrolling, Muster Maschinenbau AG", "Muster Maschinenbau AG", "2015-2020", S.WERDEGANG_ARTEN[2], URL, 34])
    # Quellen
    ws = wb.create_sheet("Quellen-Dokumente", 8)
    sp = S.QUELLEN
    kopf(ws, sp); auto_formeln(ws, sp, "Unternehmen (automatisch)", "Unternehmens-ID"); id_regel(ws, sp, "Unternehmens-ID")
    liste(ws, sp, "Dokumentart", "=" + ref["Dokumentart"], "Dokumentart aus der Liste.")
    beispiel(ws, sp, [ID, None, "Vergütungsbericht", 2025, B + " Vergütungsbericht 2025", URL, date(2026, 11, 4), date(2026, 3, 20), "de", "PDF, 48 Seiten"])
    datumsformat(ws, sp)
    wb.move_sheet("Listen", offset=len(wb.sheetnames))
    wb.move_sheet("Feldliste", offset=len(wb.sheetnames))
    wb.move_sheet("ID-Liste", offset=len(wb.sheetnames))
    wb.properties.title = "Importvorlage Governance v" + S.VERSION
    wb.save(ziel)
    return ziel


if __name__ == "__main__":
    print(baue(Path(sys.argv[1]) if len(sys.argv) > 1 else ZIEL))
