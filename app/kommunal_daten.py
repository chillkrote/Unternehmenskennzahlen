#!/usr/bin/env python3
"""Kommunalwahlen: Räte, Kreistage und Bezirksvertretungen -> app/data/kommunal.json

Quelle (Stand jetzt): IT.NRW / Ministerium des Innern NRW, "Kommunalwahlen 2025, Heft 3, Endgültige Ergebnisse in
Nordrhein-Westfalen" (Erschienen Oktober 2025, aktualisiert 04.11.2025), Datenlizenz Deutschland - Namensnennung 2.0.
Der Volltext des Hefts liegt in kommunalwahlen/nrw_2025/*.txt (aus dem PDF extrahiert). Das Skript liest dort

  Tabelle 1  Wahlberechtigte, Wähler, Stimmenverteilung je Rat/Kreistag (2025 und 2020)
  Tabelle 2  Sitzverteilung je Rat/Kreistag (2025 und 2020)
  Tabelle 3  Oberbürgermeister- und Landratswahlen (Gewählte/r)
  Tabelle 4  Bezirksvertretungen der kreisfreien Städte (Stimmen und Sitze)
  Wählergruppen-Verzeichnis (Namen der "Wählergruppe 1..n" je Gebiet)

Jede Zahl wird gegen Summen geprüft (Stimmen = gültige Stimmen, Sitze = Insgesamt, Frauen + Männer = Sitze);
Abweichungen stehen unter "pruefung" im Ergebnis und werden beim Lauf ausgegeben.

  python3 app/kommunal_daten.py [Textdatei]
"""
import json, re, sys, unicodedata
from pathlib import Path

HIER = Path(__file__).parent
QUELLE_TXT = HIER.parent / "kommunalwahlen/nrw_2025/IT-NRW_Kommunalwahlen_2025_Heft3_Endgueltige_Ergebnisse.txt"
AUS = HIER / "data/kommunal.json"

# Parteifarben (wie in der Weltkugel/Bundestag verwendet; Wählergruppen grau-violett, Rest grau)
FARBE = {"CDU": "#6b6b6b", "SPD": "#e3000f", "GRÜNE": "#46962b", "FDP": "#ffed00", "AfD": "#00a2de", "Die Linke": "#be3075",
         "Die PARTEI": "#b5152b", "Volt": "#562883", "PIRATEN": "#ff8800", "ÖDP": "#f37021", "Tierschutzpartei": "#008c95",
         "T I E R S C H U T Z": "#00a39a", "BSW": "#a0285f", "FREIE WÄHLER": "#f7a600", "DKP": "#c00000", "ZENTRUM": "#6b4a2b",
         "FAMILIE": "#ff9bc8", "AUFBRUCH C": "#7f7fbf", "BIG": "#7fbfbf", "Volksabstimmung": "#999966", "dieBasis": "#6aa8d8",
         "Team Todenhöfer": "#4c8c8c", "WerteUnion": "#5a6e8c", "DAVA": "#808080", "Die LIEBE": "#ef7f9f", "LD": "#e0b040",
         "LfK": "#c0a0d0", "PdH": "#e8c8a0", "Wählergruppen": "#8f8ba8", "Einzelbewerber/-innen": "#6f7683", "Sonstige": "#4d5662"}
GRAU = "#8b95a3"

INT = r"(?:\d{1,3}(?: \d{3})*|–)"


def zahl(s):
    return 0 if s == "–" else int(s.replace(" ", ""))


def prozent(s):
    return None if s == "–" else float(s.replace(",", "."))


PCT = re.compile(r"^(?:\d{1,3},\d|0|100|–)$")


def zerlegen(tokens, art):
    """Alle Zerlegungen der Zahlen-Tokens in Werte; art: 'i' = Ganzzahl (Tausendergruppen möglich), 'p' = Prozent (ein Token)."""
    def rek(i, k):
        if k == len(art):
            if i == len(tokens):
                yield []
            return
        if i >= len(tokens):
            return
        if art[k] == "p":
            if PCT.match(tokens[i]):
                for rest in rek(i + 1, k + 1):
                    yield [tokens[i]] + rest
            return
        t = tokens[i]
        if t == "–":
            for rest in rek(i + 1, k + 1):
                yield [t] + rest
            return
        if not re.fullmatch(r"\d{1,3}", t):
            return
        s = t
        j = i + 1
        while True:
            for rest in rek(j, k + 1):
                yield [s] + rest
            if j < len(tokens) and re.fullmatch(r"\d{3}", tokens[j]):
                s += " " + tokens[j]
                j += 1
            else:
                break
    return rek(0, 0)


NAME = r"(Wählergruppe \d+|[^\d–][^\d–]*?)"


def zeile(txt, art):
    """Zeile 'Name Zahl Zahl ...' -> (name, [token-Listen der Zerlegungen]) oder None"""
    m = re.match(rf"^{NAME} ((?:[\d,–]+ ?)+)$", txt)
    if not m:
        return None
    name = m.group(1).strip()
    toks = m.group(2).split()
    return name, list(zerlegen(toks, art))


def seiten_sauber(zeilen):
    """Seitenzahlen, Fußnoten und wiederholte Kopfzeilen entfernen"""
    out = []
    for z in zeilen:
        z = z.rstrip()
        if re.fullmatch(r"- \d+ -", z) or not z.strip():
            continue
        if re.fullmatch(r"\s*\d\)", z) and out:      # Fußnotenzeichen allein in einer Zeile gehört zur Zeile davor
            out[-1] += " " + z.strip()
            continue
        out.append(z)
    return out


def abschnitt(L, start, ende):
    i = [k for k, z in enumerate(L) if z.startswith(start)][-1]
    j = next(k for k, z in enumerate(L) if k > i and z.startswith(ende))
    return L[i:j]


def gebiet_typ(name):
    if name.startswith("Krfr. Stadt"):
        return "kreisfreie Stadt", name[len("Krfr. Stadt "):]
    if name.startswith("Städteregion"):
        return "Städteregion", re.sub(r" \d\)$", "", name)
    if name.startswith("Paderborn, Kreis"):
        return "Kreis", "Kreis Paderborn"
    return "Kreis", name


def slug(s):
    s = unicodedata.normalize("NFKD", s.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss"))
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def ist_gebietskopf(z):
    return bool(re.match(r"^(Krfr\. Stadt |Kreis |Rhein-|Städteregion|Paderborn, Kreis|Oberbergischer|Rheinisch-|Ennepe|Hochsauerland|Märkischer)", z)) and not re.search(r"\d [\d–]", z)


def lesen_tabelle1(L, pruef):
    """Rat/Kreistag: Wahlberechtigte, Wähler, Stimmen. Rückgabe: {Gebietsname: {...}}"""
    sec = abschnitt(L, "1. Wahlberechtigte, Wähler/-innen und Stimmenverteilung", "2. Sitzverteilung")
    gebiete, g = {}, None
    for k, z in enumerate(sec):
        nxt = sec[k + 1] if k + 1 < len(sec) else ""
        if nxt.startswith("Wahlberechtigte ohne Sperrvermerk") and not z.startswith(("Wahlberechtigte", "Merkmal")):
            nm = re.sub(r"\s*\d\)$", "", z).strip()
            g = gebiete.setdefault(nm, {"stimmen": []}) if nm and not nm.startswith(("Nordrhein", "Regierungsbezirk", "Kreisfreie", "Kreise")) else None
            if g is not None and "stimmen" in g and g.get("_fertig"):
                g = None
            continue
        if g is None:
            continue
        m = re.match(r"^(Wahlberechtigte insgesamt|Wähler/-innen|Ungültige Stimmen|Gültige Stimmen) (.+)$", z)
        if m:
            r = zeile(z, "ipip")
            if r and r[1]:
                v = r[1][0]
                key = {"Wahlberechtigte insgesamt": "wahlberechtigte", "Wähler/-innen": "waehler", "Ungültige Stimmen": "ungueltig", "Gültige Stimmen": "gueltig"}[r[0]]
                g[key] = [zahl(v[0]), zahl(v[2])]
                if key == "gueltig":
                    g["_gueltig"] = True
            continue
        if not g.get("_gueltig") or z in ("davon",) or z.startswith(("*)", "Wahlberechtigte", "darunter")):
            continue
        r = zeile(z, "ipip")
        if not r or not r[1]:
            continue
        name, opts = r
        gv = g["gueltig"]
        # passende Zerlegung: Prozent muss zur Stimmenzahl passen
        gut = None
        for v in opts:
            a, pa, b, pb = zahl(v[0]), prozent(v[1]), zahl(v[2]), prozent(v[3])
            ok = (pa is None or abs(a / gv[0] * 100 - pa) <= .06 + (0.05 if pa == 0 else 0)) and (pb is None or abs(b / gv[1] * 100 - pb) <= .06 + (0.05 if pb == 0 else 0))
            if ok:
                gut = (a, pa, b, pb)
                break
        if gut is None:
            pruef.append(f"T1 {z}: keine passende Zerlegung")
            continue
        leer = lambda t: None if t == "–" else None
        g["stimmen"].append({"partei": name, "stimmen": None if opts[0][0] == "–" else gut[0], "prozent": gut[1],
                             "stimmen_2020": None if (gut[3] is None and gut[2] == 0) else gut[2], "prozent_2020": gut[3]})
        if name in ("Sonstige",):
            g["_fertig"] = True
    for nm, g in gebiete.items():
        for k in ("_gueltig", "_fertig"):
            g.pop(k, None)
    return gebiete


def lesen_tabelle2(L, pruef):
    sec = abschnitt(L, "2. Sitzverteilung bei den Wahlen", "3. Ergebnisse der Oberbürger") if any(z.startswith("3. Ergebnisse der Oberbürger") for z in L) else None
    if sec is None:
        sec = abschnitt(L, "2. Sitzverteilung bei den Wahlen", "3.1 Ergebnisse der Oberbürgermeisterwahlen")
    # zweites Vorkommen (das erste ist das Inhaltsverzeichnis)
    idx = [k for k, z in enumerate(L) if z.startswith("2. Sitzverteilung bei den Wahlen")]
    start = idx[-1]
    ende = next(k for k, z in enumerate(L) if k > start and z.startswith("3.1 Ergebnisse der Oberbürgermeisterwahlen"))
    sec = L[start:ende]
    gebiete, g = {}, None
    for k, z in enumerate(sec):
        nxt = sec[k + 1] if k + 1 < len(sec) else ""
        if nxt.startswith("Anzahl der Sitze im ") and (ist_gebietskopf(z) or z.startswith(("Krfr", "Kreis", "Städteregion", "Paderborn"))):
            nm = re.sub(r"\s*\d\)$", "", z).strip()
            g = gebiete.setdefault(nm, {"sitze": []})
            g["gremium"] = {"Rat": "Rat", "Kreistag": "Kreistag", "Städteregionstag": "Städteregionstag"}.get(nxt.replace("Anzahl der Sitze im ", "").strip(), nxt)
            continue
        if nxt.startswith("Anzahl der Sitze in den "):
            g = None
        if g is None:
            continue
        if z.startswith("Insgesamt "):
            r = zeile(z, "i" * 10)
            if r and r[1]:
                for v in r[1]:
                    n = [zahl(x) for x in v]
                    if n[0] + n[1] == n[2] and n[3] + n[4] == n[2] and n[5] + n[6] == n[7] and n[8] + n[9] == n[7]:
                        g["insgesamt"] = n
                        break
            continue
        if "insgesamt" not in g or z in ("davon",) or z.startswith(("*)", "dem Aachen", "Noch")):
            continue
        r = zeile(z, "i" * 10)
        if not r or not r[1]:
            continue
        name, opts = r
        for v in opts:
            n = [zahl(x) for x in v]
            if n[0] + n[1] == n[2] and n[3] + n[4] == n[2] and n[5] + n[6] == n[7] and n[8] + n[9] == n[7]:
                g["sitze"].append({"partei": name, "wahlbezirk": n[0], "reserve": n[1], "gesamt": n[2], "frauen": n[3], "maenner": n[4], "gesamt_2020": n[7]})
                break
        else:
            pruef.append(f"T2 {z}: keine passende Zerlegung")
    return gebiete


def lesen_bezirke(L, pruef):
    idx = [k for k, z in enumerate(L) if z.startswith("4. Ergebnisse der Wahlen zu den Bezirksvertretungen")]
    start = idx[-1]
    ende = next(k for k, z in enumerate(L) if k > start and z.startswith("5. Ergebnis der Wahl der Verbandsversammlung"))
    sec = L[start:ende]
    out, stadt, b = {}, None, None
    skip = ("Nordrhein-Westfalen", "Regierungsbezirk", "Kreisfreie Städte")
    for k, z in enumerate(sec):
        nxt = sec[k + 1] if k + 1 < len(sec) else ""
        if z.startswith("Krfr. Stadt ") and not re.search(r"\d ", re.sub(r"\s*\d\)$", "", z)):
            stadt = re.sub(r"\s*\d\)$", "", z).strip()
            out.setdefault(stadt, [])
            b = None
            continue
        if nxt.startswith("Wahlberechtigte ohne Sperrvermerk") and not z.startswith(("Wahlberechtigte", "Merkmal")):
            if z.startswith(skip) or stadt is None:
                b = None
                continue
            b = {"name": z.strip(), "stimmen": []}
            out[stadt].append(b)
            continue
        if b is None:
            continue
        m = re.match(r"^(Wahlberechtigte insgesamt|Wähler/-innen|Ungültige Stimmen) (.+)$", z)
        if m:
            t = z[len(m.group(1)):].split()
            key = {"Wahlberechtigte insgesamt": "wahlberechtigte", "Wähler/-innen": "waehler", "Ungültige Stimmen": "ungueltig"}[m.group(1)]
            if key == "wahlberechtigte" or key == "waehler":
                t = t[:-3] if t[-3:] == ["X", "X", "X"] else t
                for v in zerlegen(t, "ip"):
                    b[key] = zahl(v[0]); break
            else:
                t = t[:-3] if t[-3:] == ["X", "X", "X"] else t
                for v in zerlegen(t, "ip"):
                    b[key] = zahl(v[0]); break
            continue
        if z.startswith("Vertreter(-innen) insgesamt"):
            continue
        m = re.match(r"^(\d[\d ]*) (100) (\d+) (\d+) (\d+)$", z)
        if m and "gueltig" not in b and not z.startswith("Wähl"):
            pass
        # Gültige Stimmen / Vertreter insgesamt: erste Zeile nach "Vertreter(-innen) insgesamt" mit 5 Werten
        if "gueltig" not in b and re.match(r"^[\d ]+ 100 [\d ]+$", z):
            t = z.split()
            for v in zerlegen(t, "ipiii"):
                n = [zahl(v[0]), zahl(v[2]), zahl(v[3]), zahl(v[4])]
                if n[2] + n[3] == n[1]:
                    b["gueltig"] = n[0]; b["sitze_gesamt"] = n[1]; b["sitze_frauen"] = n[2]; b["sitze_maenner"] = n[3]
                    break
            continue
        if "gueltig" not in b or z == "davon" or z.startswith(("*)", "Noch", "Kommunalwahlen", "Stimmen", "Verwaltungsbezirk", "Merkmal", "Anzahl")):
            continue
        r = zeile(z, "ipiii")
        if not r or not r[1]:
            continue
        name, opts = r
        for v in opts:
            n = zahl(v[0]); p = prozent(v[1]); s = zahl(v[2]); f = zahl(v[3]); mm = zahl(v[4])
            if f + mm == s and (p is None or abs(n / b["gueltig"] * 100 - p) <= .1 + (0.05 if p == 0 else 0)):
                b["stimmen"].append({"partei": name, "stimmen": n, "prozent": p, "sitze": s, "frauen": f, "maenner": mm})
                break
        else:
            pruef.append(f"T4 {stadt} / {b['name']}: {z}: keine passende Zerlegung")
    return out


def lesen_wgr(L):
    """'Wählergruppen (WGR) ... Räte' -> {Gebiet: {'Wählergruppe 1': Name}}"""
    idx = [k for k, z in enumerate(L) if z.startswith("Wählergruppen (WGR) bei den Wahlen zu den Vertretungen")]
    start = idx[1] if len(idx) > 1 else idx[0]
    ende = next(k for k, z in enumerate(L) if k > start and z.startswith("Noch: Wählergruppen (WGR) bei den Wahlen zu den Bezirksvertretungen"))
    sec = [z for z in L[start:ende] if not z.startswith(("Wählergruppen (WGR)", "Noch: Wählergruppen", "der kreisfreien Städte", "und Bezirksvertretungen", "Regierungsbezirk"))]
    out, g, letzt = {}, None, None
    for z in sec:
        m = re.match(r"^((?:Krfr\. Stadt |Kreis |Rhein-|Städteregion|Paderborn, Kreis|Oberbergischer|Rheinisch-|Ennepe|Hochsauerland|Märkischer)[^\d]*?) (WGR \d+) (.*)$", z)
        if m:
            g = re.sub(r"\s*\d\)$", "", m.group(1)).strip()
            out.setdefault(g, {})
            letzt = ("Wählergruppe " + m.group(2).split()[1], g)
            out[g][letzt[0]] = m.group(3).strip()
            continue
        m = re.match(r"^(WGR \d+) (.*)$", z)
        if m and g:
            letzt = ("Wählergruppe " + m.group(1).split()[1], g)
            out[g][letzt[0]] = m.group(2).strip()
            continue
        if letzt and g:
            out[letzt[1]][letzt[0]] += " " + z.strip()
    return out


def nachname_zuletzt(n):
    """'Keller, Dr. Stephan' -> 'Dr. Stephan Keller'"""
    t = [x.strip() for x in n.split(",")]
    return " ".join(t[1:] + t[:1]) if len(t) > 1 else n


def lesen_buergermeister(L):
    """Gewählte Oberbürgermeister/Landräte: letzte Zeile 'Bei der (Stichwahl am ... | Wahl am ...) als ... gewählt:' + Folgezeile"""
    res = {}
    for typ, a, b in (("Oberbürgermeister", "3.1 Ergebnisse der Oberbürgermeisterwahlen", "3.2 Ergebnisse der Landratswahlen"),
                      ("Landrat", "3.2 Ergebnisse der Landratswahlen", "4. Ergebnisse der Wahlen zu den Bezirksvertretungen")):
        s0 = [k for k, z in enumerate(L) if z.startswith(a) and "...." not in z]
        e0 = [k for k, z in enumerate(L) if z.startswith(b) and "...." not in z]
        if not s0 or not e0:
            continue
        sec = L[s0[0]:e0[-1]] if typ == "Landrat" else L[s0[0]:next(k for k in e0 if k > s0[0])]
        g = None
        for k, z in enumerate(sec):
            if re.match(r"^(Krfr\. Stadt |Kreis |Rhein-|Städteregion|Paderborn, Kreis|Oberbergischer|Rheinisch-|Ennepe|Hochsauerland|Märkischer)", z) and not re.search(r"\d \d", z) and not z.startswith("Kreisfreie"):
                g = re.sub(r"\s*\d\)$", "", z).strip()
                continue
            m = re.match(r"^Bei der (Stichwahl|Wahl) am ([\d.]+) als .* gewählt:$", z)
            if m and g and k + 1 < len(sec) and m.group(2).endswith("2025"):
                n = sec[k + 1]
                mm = re.match(r"^(.*), ([^,]+) mit ([\d,]+)\s?% der gültigen Stimmen$", n)
                if mm and "Zum Vergleich" not in sec[k - 1]:
                    # nur den ersten Treffer je Gebiet (aktuell) nehmen; "Zum Vergleich" folgt danach
                    vorher = sec[k - 1] if k else ""
                    if g not in res and not vorher.startswith("Zum Vergleich"):
                        nach_name = mm.group(1).split(", ")
                        res[g] = {"amt": typ, "name": nachname_zuletzt(mm.group(1)), "partei": mm.group(2), "anteil": float(mm.group(3).replace(",", ".")),
                                  "wahl": ("Stichwahl " if m.group(1) == "Stichwahl" else "Wahl ") + m.group(2)}
    return res


def aufbauen(txt):
    L = seiten_sauber(txt.splitlines())
    pruef = []
    t1 = lesen_tabelle1(L, pruef)
    t2 = lesen_tabelle2(L, pruef)
    t4 = lesen_bezirke(L, pruef)
    wgr = lesen_wgr(L)
    bm = lesen_buergermeister(L)
    gebiete = []
    for nm, s in t2.items():
        typ, kurz = gebiet_typ(nm)
        d1 = t1.get(nm) or t1.get(nm + " 1)") or {}
        if not d1:
            pruef.append(f"{nm}: Tabelle 1 fehlt")
        rbz = ""
        gebiete.append({"id": slug(kurz if typ == "kreisfreie Stadt" else kurz), "name": kurz, "typ": typ, "gremium": s.get("gremium"),
                        "wahlberechtigte": (d1.get("wahlberechtigte") or [None, None])[0], "waehler": (d1.get("waehler") or [None, None])[0],
                        "ungueltig": (d1.get("ungueltig") or [None, None])[0], "gueltig": (d1.get("gueltig") or [None, None])[0],
                        "wahlberechtigte_2020": (d1.get("wahlberechtigte") or [None, None])[1], "waehler_2020": (d1.get("waehler") or [None, None])[1],
                        "stimmen": d1.get("stimmen", []), "sitze": s["sitze"], "sitze_gesamt": s["insgesamt"][2], "sitze_gesamt_2020": s["insgesamt"][7],
                        "wgr": wgr.get(nm, {}), "buergermeister": bm.get(nm), "bezirke": t4.get(nm, []), "_name_quelle": nm})
    # Prüfungen
    for g in gebiete:
        if g["gueltig"] and g["stimmen"]:
            ss = sum(x["stimmen"] or 0 for x in g["stimmen"])
            if abs(ss - g["gueltig"]) > 0:
                pruef.append(f"{g['name']}: Stimmen {ss} <> gültig {g['gueltig']}")
        if sum(x["gesamt"] for x in g["sitze"]) != g["sitze_gesamt"]:
            pruef.append(f"{g['name']}: Sitze {sum(x['gesamt'] for x in g['sitze'])} <> {g['sitze_gesamt']}")
        for b in g["bezirke"]:
            ss = sum(x["stimmen"] for x in b["stimmen"])
            if b.get("gueltig") and ss != b["gueltig"]:
                pruef.append(f"{g['name']}/{b['name']}: Stimmen {ss} <> gültig {b['gueltig']}")
            sg = sum(x["sitze"] for x in b["stimmen"])
            if b.get("sitze_gesamt") is not None and sg != b["sitze_gesamt"]:
                pruef.append(f"{g['name']}/{b['name']}: Sitze {sg} <> {b['sitze_gesamt']}")
    return gebiete, pruef


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else QUELLE_TXT
    gebiete, pruef = aufbauen(src.read_text(encoding="utf-8"))
    for g in gebiete:
        g.pop("_name_quelle", None)
    out = {"land": "Nordrhein-Westfalen", "wahltag": "2025-09-14", "vergleich": "2020-09-13", "farben": FARBE,
           "quelle": {"name": "IT.NRW / Ministerium des Innern NRW, Kommunalwahlen 2025, Heft 3: Endgültige Ergebnisse (Oktober 2025, aktualisiert 04.11.2025)",
                      "lizenz": "Datenlizenz Deutschland – Namensnennung 2.0", "url": "https://www.wahlergebnisse.nrw/kommunalwahlen/2025/"},
           "gebiete": gebiete, "pruefung": pruef}
    AUS.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    nb = sum(len(g["bezirke"]) for g in gebiete)
    print(f"{len(gebiete)} Gebiete, {nb} Bezirksvertretungen, {len(pruef)} Prüfhinweise")
    for p in pruef[:40]:
        print("  ", p)


if __name__ == "__main__":
    main()
