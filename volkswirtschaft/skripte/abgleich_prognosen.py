"""Gleicht alle Prognosen für Deutschland mit den tatsächlichen Werten ab und berechnet die Treffsicherheit je Herausgeber.

Eingabe   prognosen_institute.csv (breit, handgepflegt), prognosen_institute_historie.csv (lang, 2015 bis 2025), prognosen_oecd.csv (Economic Outlook),
          prognosen_ist.csv (tatsächliche Werte, siehe abruf_ist.py)
Ausgabe   prognosen_fehler.csv          eine Zeile je Prognosewert: Prognose, Ist (erste Veröffentlichung und aktueller Stand), Fehler = Prognose minus Ist
          prognosen_treffsicherheit.csv Kennzahlen je Herausgeber, Größe und Horizont: n, mittlerer absoluter Fehler (MAE), Bias (mittlerer Fehler), RMSE
Fehler > 0: Prognose zu hoch (BIP, Inflation: zu optimistisch bzw. zu hoch; Arbeitslosenquote: zu pessimistisch). Aufruf: python3 -I abgleich_prognosen.py
"""
import csv
import math
from collections import defaultdict
from pathlib import Path

AUS = Path(__file__).resolve().parents[1]
LETZTES_ISTJAHR = 2025
ILO = {"OECD", "EU-Kommission", "IWF"}   # Arbeitslosenquote dieser Herausgeber folgt der ILO-Abgrenzung, die übrigen der BA
HVPI = {"Deutsche Bundesbank", "EU-Kommission"}
GRENZEN = [(6, "0 bis 6 Monate"), (12, "7 bis 12 Monate"), (18, "13 bis 18 Monate"), (24, "19 bis 24 Monate"), (999, "über 24 Monate")]


def lies(n):
    with open(AUS / n, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def datum(s):
    t = (s + "-15").split("-") if len(s) == 7 else s.split("-")
    return int(t[0]), int(t[1])


def serie(h, gr, hinweis):
    """Zuordnung der Prognosegröße zur Ist-Reihe; None = nicht vergleichbar."""
    if gr == "bip_wachstum":
        return None if "kalenderbereinigt" in hinweis.lower() else "bip_wachstum"
    if gr == "inflation":
        return "inflation_hvpi" if (h in HVPI or "HVPI" in hinweis) else ("inflation" if h != "IWF" else None)
    if gr == "inflation_vpi":
        return "inflation"
    if gr == "inflation_hvpi":
        return "inflation_hvpi"
    if gr == "arbeitslosenquote":
        return "arbeitslosenquote_ilo" if h in ILO else "arbeitslosenquote"
    if gr == "finanzierungssaldo":
        return "finanzierungssaldo"
    return None


def sammle():
    """(herausgeber, ausgabe, datum, ist-serie, jahr) -> (wert, beleg, url); die Historie hat Vorrang vor der breiten Datei."""
    d = {}

    def put(h, a, dat, gr, hint, j, v, b, u, prio):
        s = serie(h, gr, hint)
        if not s or v == "":
            return
        key = (h, dat[:7], s, int(j))
        if key not in d or d[key][0] < prio:
            d[key] = (prio, h, a, dat, s, int(j), float(v), b, u)
    for r in lies("prognosen_institute_historie.csv"):
        put(r["herausgeber"], r["ausgabe"], r["veroeffentlicht"], r["groesse"], r["hinweis"], r["jahr"], r["wert"], r["beleg"], r["url"], 2)
    for r in lies("prognosen_institute.csv"):
        if r["geo"] != "DE":
            continue
        for j in ("2025", "2026", "2027", "2028"):
            put(r["herausgeber"], r["ausgabe"], r["veroeffentlicht"], r["groesse"], r["hinweis"], j, r["j" + j], r["beleg"], r["url"], 1)
    for r in lies("prognosen_oecd.csv"):
        if r["geo"] == "DE":
            put(r["herausgeber"], r["ausgabe"], r["veroeffentlicht"], r["groesse"], "", r["jahr"], r["wert"], r["beleg"], r["url"], 1)
    return [v[1:] for v in d.values()]


def bucket(m):
    return next(t for g, t in GRENZEN if m <= g)


def kennz(f):
    n = len(f)
    return dict(n=n, mae=sum(abs(x) for x in f) / n, bias=sum(f) / n, rmse=math.sqrt(sum(x * x for x in f) / n), min=min(f), max=max(f))


def main():
    ist = defaultdict(dict)
    for r in lies("prognosen_ist.csv"):
        ist[(r["groesse"], int(r["jahr"]))][r["vintage"]] = float(r["wert"])
    zeilen = []
    for h, a, dat, s, j, v, b, u in sammle():
        jy, jm = datum(dat)
        if j < jy or j > LETZTES_ISTJAHR:
            continue  # Schätzungen für zurückliegende Jahre und Jahre ohne Istwert zählen nicht als Prognose
        monate = (j * 12 + 12) - (jy * 12 + jm)
        e, k = ist[(s, j)].get("erst"), ist[(s, j)].get("aktuell")
        if e is None and k is None:
            continue
        zeilen.append(dict(herausgeber=h, ausgabe=a, veroeffentlicht=dat, groesse=s, jahr=j, horizont_jahre=j - jy, abstand_monate=monate, horizont=bucket(monate),
                           prognose=v, ist_erst="" if e is None else e, ist_aktuell="" if k is None else k,
                           fehler_erst="" if e is None else round(v - e, 3), fehler_aktuell="" if k is None else round(v - k, 3), beleg=b, url=u))
    zeilen.sort(key=lambda z: (z["herausgeber"], z["groesse"], z["veroeffentlicht"], z["jahr"]))
    fel = list(zeilen[0])
    with open(AUS / "prognosen_fehler.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fel)
        w.writeheader()
        w.writerows(zeilen)
    grp = defaultdict(list)
    for z in zeilen:
        for vint, col in (("erst", "fehler_erst"), ("aktuell", "fehler_aktuell")):
            if z[col] != "":
                for hz in (z["horizont"], "alle"):
                    grp[(z["herausgeber"], z["groesse"], hz, vint)].append((z[col], z["jahr"]))
    out = []
    for (h, gr, hz, vint), l in sorted(grp.items()):
        k = kennz([x for x, _ in l])
        out.append(dict(herausgeber=h, groesse=gr, horizont=hz, ist_vintage=vint, n=k["n"], mae=round(k["mae"], 3), bias=round(k["bias"], 3), rmse=round(k["rmse"], 3),
                        fehler_min=round(k["min"], 3), fehler_max=round(k["max"], 3), jahr_von=min(j for _, j in l), jahr_bis=max(j for _, j in l)))
    with open(AUS / "prognosen_treffsicherheit.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(len(zeilen), "Prognosewerte,", len(out), "Kennzahlenzeilen")


if __name__ == "__main__":
    main()
