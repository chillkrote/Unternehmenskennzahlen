"""Analyse (P4): Korrelation zweier Zeitreihen, gleiche Rechenregeln wie die Oberfläche (app/src/korrelation.js, KOR).

Ohne Bibliotheken, damit Server und Browser bis auf Rundung dasselbe Ergebnis liefern (Test: tests/test_analyse.py rechnet
dieselben Fälle mit KOR in Node nach). Frequenzen hier: A, Q, M (VWL-Reihen). Lücken bleiben Lücken, nichts wird aufgefüllt.
"""
import math

RANG = {"A": 1, "Q": 2, "M": 3}
PPJ = {"A": 1, "Q": 4, "M": 12}
TRANSFORMATIONEN = {"niveau": "Niveau", "diff": "Differenz zur Vorperiode", "pct": "Veränderung zur Vorperiode (%)",
                    "log": "Log-Rendite", "yoy": "Veränderung zum Vorjahr (%)"}
LAG_MAX = {"A": 3, "Q": 6, "M": 12}


# ---------- Statistik ----------
def _mean(xs):
    return sum(xs) / len(xs)


def pearson(x, y):
    n = len(x)
    if n < 3:
        return None
    mx, my = _mean(x), _mean(y)
    sxy = sxx = syy = 0.0
    for a, b in zip(x, y):
        dx, dy = a - mx, b - my
        sxy += dx * dy; sxx += dx * dx; syy += dy * dy
    if sxx <= 0 or syy <= 0:
        return None
    return max(-1.0, min(1.0, sxy / math.sqrt(sxx * syy)))


def raenge(x):
    """Mittlere Ränge bei Bindungen (1-basiert)."""
    idx = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(idx):
        j = i
        while j + 1 < len(idx) and x[idx[j + 1]] == x[idx[i]]:
            j += 1
        m = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[idx[k]] = m
        i = j + 1
    return r


def spearman(x, y):
    return pearson(raenge(x), raenge(y))


def _betacf(a, b, x):
    fp = 1e-300
    c, d = 1.0, 1 - (a + b) * x / (a + 1)
    if abs(d) < fp:
        d = fp
    d = 1 / d
    h = d
    for m in range(1, 301):
        m2 = 2 * m
        aa = m * (b - m) * x / ((a + m2 - 1) * (a + m2))
        d = 1 + aa * d; d = fp if abs(d) < fp else d
        c = 1 + aa / c; c = fp if abs(c) < fp else c
        d = 1 / d; h *= d * c
        aa = -(a + m) * (a + b + m) * x / ((a + m2) * (a + m2 + 1))
        d = 1 + aa * d; d = fp if abs(d) < fp else d
        c = 1 + aa / c; c = fp if abs(c) < fp else c
        d = 1 / d
        dl = d * c; h *= dl
        if abs(dl - 1) < 3e-16:
            break
    return h


def ibeta(a, b, x):
    """Regularisierte unvollständige Betafunktion I_x(a, b)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
    return bt * _betacf(a, b, x) / a if x < (a + 1) / (a + b + 2) else 1 - bt * _betacf(b, a, 1 - x) / b


def p_wert(r, n):
    """Zweiseitiger p-Wert für r bei n Beobachtungen (t-Verteilung, n-2 Freiheitsgrade)."""
    if r is None or n < 3:
        return None
    df = n - 2
    if abs(r) >= 1:
        return 0.0
    t2 = r * r * df / (1 - r * r)
    return ibeta(df / 2, 0.5, df / (df + t2))


def autokorr(x):
    return pearson(x[1:], x[:-1]) if len(x) > 4 else None


def stat(x, y):
    n = len(x)
    o = {"n": n, "r": None, "rho": None, "p": None, "p_rho": None, "ci": None, "slope": None, "intercept": None, "durbin_watson": None,
         "n_eff": None, "p_eff": None, "autocorr_a": None, "autocorr_b": None}
    if n < 3:
        return o
    o["r"], o["rho"] = pearson(x, y), spearman(x, y)
    o["p"], o["p_rho"] = p_wert(o["r"], n), p_wert(o["rho"], n)
    if o["r"] is not None and n > 3 and abs(o["r"]) < 1:
        z, se = math.atanh(o["r"]), 1 / math.sqrt(n - 3)
        o["ci"] = [math.tanh(z - 1.96 * se), math.tanh(z + 1.96 * se)]
    mx, my = _mean(x), _mean(y)
    sxx = sum((a - mx) ** 2 for a in x)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    if sxx > 0:
        o["slope"] = sxy / sxx
        o["intercept"] = my - o["slope"] * mx
        e = [b - o["intercept"] - o["slope"] * a for a, b in zip(x, y)]
        s2 = sum(v * v for v in e)
        s1 = sum((e[i] - e[i - 1]) ** 2 for i in range(1, len(e)))
        o["durbin_watson"] = s1 / s2 if s2 > 0 else None
    o["autocorr_a"], o["autocorr_b"] = autokorr(x), autokorr(y)
    if o["r"] is not None and o["autocorr_a"] is not None and o["autocorr_b"] is not None:   # effektive Stichprobe nach Bartlett
        q = o["autocorr_a"] * o["autocorr_b"]
        o["n_eff"] = max(3.0, min(n, n * (1 - q) / (1 + q)))
        o["p_eff"] = p_wert(o["r"], o["n_eff"])
    return o


# ---------- Zeit ----------
def parse(k):
    k = str(k)
    if len(k) == 4 and k.isdigit():
        return {"y": int(k)}
    if len(k) == 7 and k[4:6] == "-Q":
        return {"y": int(k[:4]), "q": int(k[6])}
    if len(k) == 7 and k[4] == "-":
        return {"y": int(k[:4]), "mo": int(k[5:7])}
    return None


def pkey(k, f):
    p = parse(k)
    if not p:
        return None
    if f == "A":
        return str(p["y"])
    if f == "Q":
        return f"{p['y']}-Q{p.get('q') or math.ceil(p['mo'] / 3)}"
    return f"{p['y']}-{p['mo']:02d}"


def pidx(k, f):
    p = parse(k)
    return p["y"] if f == "A" else p["y"] * 4 + p["q"] - 1 if f == "Q" else p["y"] * 12 + p["mo"] - 1


def auf_freq(freq, pts, f, agg):
    """Reihe auf Frequenz f: Mittel (Raten, Salden) oder letzter Wert (Bestände, Indizes)."""
    pts = sorted(pts, key=lambda p: p[0])
    if freq == f:
        return pts
    g = {}
    for k, v in pts:
        g.setdefault(pkey(k, f), []).append(v)
    return sorted(([k, _mean(vs) if agg == "mittel" else vs[-1]] for k, vs in g.items()), key=lambda p: p[0])


def auto_trans(art, f):
    if art in ("rate", "saldo", "quote"):
        return "niveau"
    return "pct" if f == "A" else "yoy"


def transf(pts, f, tr):
    if tr == "niveau":
        return [[p[0], p[1]] for p in pts]
    idx = {pidx(p[0], f): p[1] for p in pts}
    lag = PPJ.get(f, 1) if tr == "yoy" else 1
    out = []
    for k, v in pts:
        prev = idx.get(pidx(k, f) - lag)
        if prev is None:
            continue
        if tr == "diff":
            out.append([k, v - prev])
        elif tr == "log":
            if v > 0 and prev > 0:
                out.append([k, math.log(v / prev)])
        elif prev != 0 and tr in ("yoy", "pct"):
            out.append([k, (v - prev) / abs(prev) * 100])
    return out


def paare(pa, pb, f, lag, von=0, bis=0):
    mb = {pidx(p[0], f): p for p in pb}
    rows = []
    for k, v in pa:
        y = parse(k)["y"]
        if (von and y < von) or (bis and y > bis):
            continue
        q = mb.get(pidx(k, f) + lag)
        if q:
            rows.append({"period_a": k, "period_b": q[0], "a": v, "b": q[1]})
    return rows


def reihe_art(kind):
    return {"rate": "rate", "saldo": "saldo", "index": "index"}.get(kind, "niveau")


def reihe_agg(kind):
    return "mittel" if kind in ("rate", "saldo") else "letzter"


def korrelation(a, b, freq="auto", tr_a="auto", tr_b="auto", agg="auto", lag=0, von=0, bis=0, methode="pearson"):
    """a, b: {"freq", "kind", "pts": [[zeitraum, wert]]} (nur Beobachtungen). Ergebnis wie KOR.auswertungPaar."""
    f = min((a["freq"], b["freq"]), key=lambda x: RANG[x]) if freq == "auto" else freq
    teile = []
    for s, tr in ((a, tr_a), (b, tr_b)):
        if RANG[s["freq"]] < RANG[f]:
            raise ValueError(f"Reihe liegt nur mit Frequenz {s['freq']} vor, nicht {f}")
        t = auto_trans(reihe_art(s["kind"]), f) if tr == "auto" else tr
        g = reihe_agg(s["kind"]) if agg == "auto" else agg
        pts = [p for p in transf(auf_freq(s["freq"], s["pts"], f, g), f, t) if math.isfinite(p[1])]
        teile.append({"transform": t, "aggregation": g, "points": pts})
    pa, pb = teile[0]["points"], teile[1]["points"]
    rows = paare(pa, pb, f, lag, von, bis)
    x, y = [r["a"] for r in rows], [r["b"] for r in rows]
    fn = spearman if methode == "spearman" else pearson
    cc = []
    for k in range(-LAG_MAX[f], LAG_MAX[f] + 1):
        rr = paare(pa, pb, f, k, von, bis)
        cc.append({"lag": k, "n": len(rr), "r": fn([r["a"] for r in rr], [r["b"] for r in rr]) if len(rr) >= 5 else None})
    return {"frequency": f, "a": {k: v for k, v in teile[0].items() if k != "points"}, "b": {k: v for k, v in teile[1].items() if k != "points"},
            "lag": lag, "stats": stat(x, y), "cross_correlation": cc, "rows": rows}
