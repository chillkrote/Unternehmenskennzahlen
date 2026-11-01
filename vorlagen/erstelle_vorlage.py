#!/usr/bin/env python3
"""Baut vorlagen/Importvorlage_Unternehmen.xlsx aus schema.py.   Aufruf: python3 vorlagen/erstelle_vorlage.py [Zieldatei]"""
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S

HIER = Path(__file__).resolve().parent
ZIEL = HIER / "Importvorlage_Unternehmen.xlsx"
MAXZ = 5000  # Zeilen mit Datenvalidierung
PFLICHT = PatternFill("solid", fgColor="1F3864")
OPTIONAL = PatternFill("solid", fgColor="5B6B8C")
BSP = PatternFill("solid", fgColor="FFF2CC")
SEITE = Side(style="thin", color="BBBBBB")


def kopf(ws, spalten, row=1):
    for i, (name, pflicht, breite, hinweis) in enumerate(spalten, 1):
        c = ws.cell(row, i, name + (" *" if pflicht else ""))
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PFLICHT if pflicht else OPTIONAL
        c.alignment = Alignment(wrap_text=True, vertical="center")
        c.comment = Comment(("Pflicht. " if pflicht else "Optional. ") + hinweis, "Vorlage")
        ws.column_dimensions[get_column_letter(i)].width = breite
    ws.row_dimensions[row].height = 32
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(spalten))}1"


def liste(ws, spalten, name, formel, fehler):
    col = [s[0] for s in spalten].index(name) + 1
    L = get_column_letter(col)
    dv = DataValidation(type="list", formula1=formel, allow_blank=True, showErrorMessage=True,
                        errorTitle="Ungültiger Wert", error=fehler)
    ws.add_data_validation(dv)
    dv.add(f"{L}2:{L}{MAXZ}")


def zahl_regel(ws, spalten, name, typ, fehler, **kw):
    col = [s[0] for s in spalten].index(name) + 1
    L = get_column_letter(col)
    dv = DataValidation(type=typ, operator="between", allow_blank=True, showErrorMessage=True,
                        errorTitle="Ungültiger Wert", error=fehler, **kw)
    ws.add_data_validation(dv)
    dv.add(f"{L}2:{L}{MAXZ}")


def baue(ziel=ZIEL):
    wb = Workbook()
    # --- Anleitung
    a = wb.active
    a.title = "Anleitung"
    a.column_dimensions["A"].width = 130
    zeilen = [
        ("Importvorlage Unternehmen und Kennzahlen (Version %s)" % S.VERSION, "titel"),
        ("Zweck: Diese Datei wird vom Import-Skript (vorlagen/importieren.py) automatisch eingelesen und geprüft. Bitte Struktur, Blattnamen und Spaltenköpfe NICHT ändern.", None),
        ("", None),
        ("Aufbau", "h"),
        ("1. Blatt Unternehmen: eine Zeile je Unternehmen (Stammdaten). Keine Unternehmens-ID eintragen, die vergeben wir selbst.", None),
        ("2. Blatt Kennzahlen: Langformat, eine Zeile je Wert (Unternehmen + Geschäftsjahr + Kennzahl). Die erlaubten Kennzahlen stehen auf dem Blatt Kennzahlenliste.", None),
        ("3. Blatt Quellen-Dokumente: eine Zeile je verwendetem Bericht/Dokument mit Link.", None),
        ("4. Blatt Listen: Dropdown-Werte; nicht ändern. Zeilen mit dem Namen [Beispiel]... sind Muster und werden ignoriert (gern löschen).", None),
        ("", None),
        ("Regeln", "h"),
        ("Pflichtfelder: Spalten mit * im Kopf (dunkelblau). Optionale Spalten (grau) leer lassen, wenn unbekannt.", None),
        ("Leer lassen statt raten: Keine Schätzungen, keine Hochrechnungen, keine Werte aus Erinnerung. Was nicht belegt ist, bleibt leer; die Zeile in Kennzahlen dann weglassen.", None),
        ("Jeder Wert braucht Quelle und URL (direkter Link auf Geschäftsbericht, Abschluss, Börsen- oder Registerseite) und, wenn möglich, die Seite. Bevorzugt Primärquellen (Geschäftsbericht, Unternehmensregister, SEC), erst danach Datenanbieter.", None),
        ("Keine kostenpflichtigen oder nur per Login/Captcha erreichbaren Quellen verwenden; Schutzmechanismen nicht umgehen.", None),
        ("Unternehmen: Name wie im Register, Land als englischer Name aus der Liste (z. B. Jordan, Saudi Arabia; Sonstige nur, wenn das Land nicht in der Liste steht), Branche aus der Liste. Börsennotiert ja/nein. ISIN 12 Zeichen (Prüfziffer wird geprüft), LEI 20 Zeichen (GLEIF). Bank = ja nur bei Kreditinstituten.", None),
        ("Vor dem Anlegen prüfen: Das Unternehmen darf nicht schon in der Liste unter anderem Namen/ISIN stehen (Dubletten werden beim Import gegen unseren Bestand geprüft und gemeldet).", None),
        ("Geschäftsjahr: Vierstellig, das Jahr, in dem das Geschäftsjahr endet. Stichtag: Datum des Abschlusses (TT.MM.JJJJ), z. B. 31.12.2025 oder 30.06.2025.", None),
        ("Rechnungslegung: HGB, IFRS, US-GAAP oder Sonstige, so wie im jeweiligen Abschluss. Je Unternehmen und Jahr den Konzernabschluss verwenden (bei nur Einzelabschluss: diesen und im Hinweis vermerken).", None),
        ("Währung: ISO-Code der Berichtswährung. NICHT in Euro umrechnen. Einheit: genau die Einheit, in der die Zahl in der Zelle steht (absolut, Tausend, Millionen, Milliarden). Beispiel: Bilanz in TEUR, Zelle 1.234 → Währung EUR, Einheit Tausend, Wert 1234.", None),
        ("Wert: reine Zahl, Dezimalzeichen Komma oder Punkt, kein Tausenderpunkt, kein Text. Minus für negative Werte (Verlust, Mittelabfluss). Prozentwerte als Prozentzahl (12,5 = 12,5 %) mit Einheit Prozent. Je-Aktie-Werte und Kurse mit Einheit absolut.", None),
        ("Mitarbeiter, Aktienanzahl: Einheit Anzahl (oder absolut/Tausend/Millionen bei Aktien).", None),
        ("Bilanzprobe: Wenn Bilanzsumme, Eigenkapital und Verbindlichkeiten gesamt angegeben werden, müssen sie zusammenpassen (Eigenkapital + Verbindlichkeiten = Bilanzsumme, Toleranz 1 %). Bei getrennten Seiten Summe Aktiva und Summe Passiva angeben; sie müssen gleich sein.", None),
        ("Zeitreihe: Gern bis zu zehn Geschäftsjahre zurück, jeweils aus dem Abschluss des betreffenden Jahres oder, falls nicht verfügbar, aus dem Folgejahresabschluss (Vorjahresspalte); dann im Hinweis \"Vorjahresspalte aus GJ ...\" vermerken. Angepasste (restated) Werte kennzeichnen.", None),
        ("Marktkapitalisierung und Aktienkurs: nur mit Bewertungstag als Stichtag und Quelle (Börse/Anbieter) angeben.", None),
        ("Jede Zeile soll für sich verständlich sein. Pro Unternehmen, Geschäftsjahr und Kennzahl genau eine Zeile (doppelte Zeilen werden als Fehler gemeldet).", None),
        ("", None),
        ("Abgabe", "h"),
        ("Datei als .xlsx speichern, Blattnamen unverändert lassen und dem Auftraggeber zurückgeben. Er führt aus: python3 vorlagen/importieren.py <Datei> (nur Prüfung); mit --schreiben werden Unternehmen angelegt und die Kennzahlen in import/ abgelegt.", None),
    ]
    for i, (t, st) in enumerate(zeilen, 1):
        c = a.cell(i, 1, t)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if st == "titel":
            c.font = Font(bold=True, size=15)
        elif st == "h":
            c.font = Font(bold=True, size=12, color="1F3864")
    # --- Listen
    L = wb.create_sheet("Listen")
    spalten = [("Rechnungslegung", S.RECHNUNGSLEGUNG), ("Einheit", S.EINHEITEN), ("JaNein", S.JA_NEIN),
               ("Währung", S.WAEHRUNGEN), ("Branche", S.BRANCHEN), ("Land", S.LAENDER), ("Dokumentart", S.DOKUMENTARTEN)]
    ref = {}
    for i, (n, werte) in enumerate(spalten, 1):
        L.cell(1, i, n).font = Font(bold=True)
        for j, w in enumerate(werte, 2):
            L.cell(j, i, w)
        ref[n] = f"Listen!${get_column_letter(i)}$2:${get_column_letter(i)}${len(werte) + 1}"
        L.column_dimensions[get_column_letter(i)].width = 22
    # --- Kennzahlenliste
    K = wb.create_sheet("Kennzahlenliste")
    kk = [("Kennzahl", True, 38, ""), ("Bereich", True, 11, ""), ("Typ", True, 10, ""), ("Nur Banken", True, 11, ""),
          ("Definition", True, 100, "")]
    kopf(K, kk)
    for i, k in enumerate(S.KENNZAHLEN, 2):
        for j, v in enumerate([k[0], k[2], k[3], "ja" if k[4] else "", k[5]], 1):
            K.cell(i, j, v).alignment = Alignment(wrap_text=True, vertical="top")
    kz_ref = f"Kennzahlenliste!$A$2:$A${len(S.KENNZAHLEN) + 1}"
    K.cell(len(S.KENNZAHLEN) + 3, 1, "Typ: Geld = Betrag in Währung und Einheit; JeAktie = Betrag je Aktie (Einheit absolut); Prozent; Anzahl.").font = Font(italic=True)
    # --- Unternehmen
    U = wb.create_sheet("Unternehmen", 1)
    kopf(U, S.UNTERNEHMEN)
    liste(U, S.UNTERNEHMEN, "Land", "=" + ref["Land"], "Bitte ein Land aus der Liste wählen (Sonstige, wenn nicht enthalten).")
    liste(U, S.UNTERNEHMEN, "Börsennotiert", "=" + ref["JaNein"], "ja oder nein")
    liste(U, S.UNTERNEHMEN, "Bank", "=" + ref["JaNein"], "ja oder nein")
    liste(U, S.UNTERNEHMEN, "Branche", "=" + ref["Branche"], "Bitte eine Branche aus der Liste wählen.")
    bsp_u = [
        [S.BEISPIEL + " Muster Maschinenbau AG", "AG", "Germany", "Stuttgart", "DE000EXMPL17", "MMB.DE", "Xetra", "ja", "industrie",
         "28.99", "", "HRB 123456, Amtsgericht Stuttgart", "https://www.beispiel.example", "nein", "SDAX",
         "Fiktives Muster. Hersteller von Werkzeugmaschinen.", "https://www.beispiel.example/investor-relations"],
        [S.BEISPIEL + " Beispiel Familienholding GmbH", "GmbH", "Germany", "Hamburg", "", "", "", "nein", "handel-konsum",
         "46.90", "", "HRB 7654, Amtsgericht Hamburg", "https://www.holding.example", "nein", "",
         "Fiktives Muster, nicht börsennotiert.", "https://www.unternehmensregister.de"],
    ]
    for r, zeile in enumerate(bsp_u, 2):
        for c, v in enumerate(zeile, 1):
            cell = U.cell(r, c, v)
            cell.fill = BSP
    # --- Kennzahlen
    Z = wb.create_sheet("Kennzahlen", 2)
    kopf(Z, S.KENNZAHLEN_SPALTEN)
    liste(Z, S.KENNZAHLEN_SPALTEN, "Unternehmen", f"=Unternehmen!$A$2:$A${MAXZ}", "Unternehmen zuerst im Blatt Unternehmen anlegen.")
    liste(Z, S.KENNZAHLEN_SPALTEN, "Rechnungslegung", "=" + ref["Rechnungslegung"], "HGB, IFRS, US-GAAP oder Sonstige.")
    liste(Z, S.KENNZAHLEN_SPALTEN, "Währung", "=" + ref["Währung"], "ISO-Währungscode aus der Liste.")
    liste(Z, S.KENNZAHLEN_SPALTEN, "Einheit", "=" + ref["Einheit"], "Einheit aus der Liste.")
    liste(Z, S.KENNZAHLEN_SPALTEN, "Kennzahl", "=" + kz_ref, "Nur Kennzahlen aus dem Blatt Kennzahlenliste.")
    zahl_regel(Z, S.KENNZAHLEN_SPALTEN, "Geschäftsjahr", "whole", "Vierstellige Jahreszahl 2000 bis 2100.", formula1="2000", formula2="2100")
    zahl_regel(Z, S.KENNZAHLEN_SPALTEN, "Stichtag", "date", "Datum TT.MM.JJJJ.", formula1="36526", formula2="73415")
    zahl_regel(Z, S.KENNZAHLEN_SPALTEN, "Wert", "decimal", "Nur Zahl, ohne Einheitentext.", formula1="-1E+18", formula2="1E+18")
    n = S.BEISPIEL + " Muster Maschinenbau AG"
    from datetime import date
    sd = date(2025, 12, 31)
    URL = "https://www.beispiel.example/gb2025.pdf"
    bsp_k = [
        [n, 2025, sd, "IFRS", "EUR", "Millionen", "Bilanzsumme", 1250.4, "Konzernbilanz GJ2025", URL, 112, ""],
        [n, 2025, sd, "IFRS", "EUR", "Millionen", "Eigenkapital", 480.2, "Konzernbilanz GJ2025", URL, 112, ""],
        [n, 2025, sd, "IFRS", "EUR", "Millionen", "Verbindlichkeiten gesamt", 770.2, "Konzernbilanz GJ2025", URL, 112, "Summe Rückstellungen und Verbindlichkeiten"],
        [n, 2025, sd, "IFRS", "EUR", "Millionen", "Umsatz", 1830.0, "Konzern-GuV GJ2025", URL, 110, ""],
        [n, 2025, sd, "IFRS", "EUR", "Millionen", "Jahresergebnis", -12.5, "Konzern-GuV GJ2025", URL, 110, "Verlust"],
        [n, 2025, sd, "IFRS", "EUR", "Tausend", "Mitarbeiter", None, "", "", None, ""],
    ]
    bsp_k[-1] = [n, 2025, sd, "IFRS", "EUR", "Anzahl", "Mitarbeiter", 7421, "Lagebericht, Mitarbeiter zum 31.12.", URL, 64, "Köpfe"]
    bsp_k.append([n, 2025, sd, "IFRS", "EUR", "absolut", "Dividende je Aktie", 0.35, "Gewinnverwendungsvorschlag", URL, 188, ""])
    for r, zeile in enumerate(bsp_k, 2):
        for c, v in enumerate(zeile, 1):
            cell = Z.cell(r, c, v)
            cell.fill = BSP
            if c == 3:
                cell.number_format = "DD.MM.YYYY"
    for r in range(2, MAXZ + 1):
        Z.cell(r, 3).number_format = "DD.MM.YYYY"
    # --- Quellen
    Q = wb.create_sheet("Quellen-Dokumente", 3)
    kopf(Q, S.QUELLEN_SPALTEN)
    liste(Q, S.QUELLEN_SPALTEN, "Unternehmen", f"=Unternehmen!$A$2:$A${MAXZ}", "Unternehmen zuerst im Blatt Unternehmen anlegen.")
    liste(Q, S.QUELLEN_SPALTEN, "Dokumentart", "=" + ref["Dokumentart"], "Dokumentart aus der Liste.")
    for c, v in enumerate([n, "Geschäftsbericht", 2025, "Geschäftsbericht 2025 (Konzernabschluss)", URL, date(2026, 10, 31), "de", "PDF, 220 Seiten"], 1):
        cell = Q.cell(2, c, v)
        cell.fill = BSP
        if c == 6:
            cell.number_format = "DD.MM.YYYY"
    for r in range(2, MAXZ + 1):
        Q.cell(r, 6).number_format = "DD.MM.YYYY"
    wb.move_sheet("Listen", offset=len(wb.sheetnames))
    wb.move_sheet("Kennzahlenliste", offset=-1)
    wb.properties.title = "Importvorlage Unternehmen und Kennzahlen v" + S.VERSION
    wb.save(ziel)
    return ziel


if __name__ == "__main__":
    print(baue(Path(sys.argv[1]) if len(sys.argv) > 1 else ZIEL))
