/* ---------- Korrelationsauswertung (KOR) ----------
   Rechnet vollständig im Browser, ohne Bibliotheken. Datenbasis sind nur die im Terminal vorhandenen Daten:
   VWL-Reihen (VWL.korr()), Unternehmen und Branchen (UNT.korr()), Kurse und Konzernabschlüsse (MARKT).
   Lücken bleiben Lücken: es wird nichts aufgefüllt oder interpoliert.
   Drei Modi: Zeitreihen A gegen B (mit Verzögerung), Matrix mehrerer Zeitreihen, Querschnitt über Unternehmen.
   Läuft vor dem Hauptskript; nutzt dessen Hilfsfunktionen (panel, esc, f0, f1, f2, median, render) erst zur Laufzeit. */
"use strict";
const KOR = (() => {
  /* ======================= Statistik ======================= */
  const mean = xs => xs.reduce((a, b) => a + b, 0) / xs.length;
  function pearson(x, y) {
    const n = x.length; if (n < 3) return null;
    const mx = mean(x), my = mean(y); let sxy = 0, sxx = 0, syy = 0;
    for (let i = 0; i < n; i++) { const dx = x[i] - mx, dy = y[i] - my; sxy += dx * dy; sxx += dx * dx; syy += dy * dy; }
    if (sxx <= 0 || syy <= 0) return null;               // konstante Reihe: r nicht definiert
    return Math.max(-1, Math.min(1, sxy / Math.sqrt(sxx * syy)));
  }
  function raenge(x) {                                    // mittlere Ränge bei Bindungen
    const idx = x.map((v, i) => i).sort((a, b) => x[a] - x[b]), r = new Array(x.length);
    for (let i = 0; i < idx.length;) {
      let j = i; while (j + 1 < idx.length && x[idx[j + 1]] === x[idx[i]]) j++;
      const m = (i + j) / 2 + 1; for (let k = i; k <= j; k++) r[idx[k]] = m; i = j + 1;
    }
    return r;
  }
  const spearman = (x, y) => pearson(raenge(x), raenge(y));
  function lgam(z) {                                      // ln Γ (Lanczos)
    const c = [76.18009172947146, -86.50532032941677, 24.01409824083091, -1.231739572450155, 0.1208650973866179e-2, -0.5395239384953e-5];
    let y = z, t = z + 5.5; t -= (z + .5) * Math.log(t); let s = 1.000000000190015;
    for (const k of c) s += k / ++y; return -t + Math.log(2.5066282746310005 * s / z);
  }
  function betacf(a, b, x) {
    const FP = 1e-300; let c = 1, d = 1 - (a + b) * x / (a + 1); if (Math.abs(d) < FP) d = FP; d = 1 / d; let h = d;
    for (let m = 1; m <= 300; m++) {
      const m2 = 2 * m; let aa = m * (b - m) * x / ((a + m2 - 1) * (a + m2));
      d = 1 + aa * d; if (Math.abs(d) < FP) d = FP; c = 1 + aa / c; if (Math.abs(c) < FP) c = FP; d = 1 / d; h *= d * c;
      aa = -(a + m) * (a + b + m) * x / ((a + m2) * (a + m2 + 1));
      d = 1 + aa * d; if (Math.abs(d) < FP) d = FP; c = 1 + aa / c; if (Math.abs(c) < FP) c = FP; d = 1 / d;
      const del = d * c; h *= del; if (Math.abs(del - 1) < 3e-16) break;
    }
    return h;
  }
  function ibeta(a, b, x) {                               // regularisierte unvollständige Betafunktion
    if (x <= 0) return 0; if (x >= 1) return 1;
    const bt = Math.exp(lgam(a + b) - lgam(a) - lgam(b) + a * Math.log(x) + b * Math.log(1 - x));
    return x < (a + 1) / (a + b + 2) ? bt * betacf(a, b, x) / a : 1 - bt * betacf(b, a, 1 - x) / b;
  }
  /* zweiseitiger p-Wert für r bei n Beobachtungen (t-Verteilung mit n-2 Freiheitsgraden) */
  function pWert(r, n) {
    if (r == null || n < 3) return null; const df = n - 2;
    if (Math.abs(r) >= 1) return 0;
    const t2 = r * r * df / (1 - r * r); return ibeta(df / 2, .5, df / (df + t2));
  }
  function stat(x, y) {
    const n = x.length, o = { n, r: null, rho: null, p: null, pRho: null, ci: null, b: null, a: null, dw: null, neff: null, pEff: null, ra: null, rb: null };
    if (n < 3) return o;
    o.r = pearson(x, y); o.rho = spearman(x, y);
    o.p = pWert(o.r, n); o.pRho = pWert(o.rho, n);
    if (o.r != null && n > 3 && Math.abs(o.r) < 1) { const z = Math.atanh(o.r), se = 1 / Math.sqrt(n - 3); o.ci = [Math.tanh(z - 1.96 * se), Math.tanh(z + 1.96 * se)]; }
    const mx = mean(x), my = mean(y); let sxx = 0, sxy = 0; for (let i = 0; i < n; i++) { sxx += (x[i] - mx) ** 2; sxy += (x[i] - mx) * (y[i] - my); }
    if (sxx > 0) {
      o.b = sxy / sxx; o.a = my - o.b * mx;
      const e = y.map((v, i) => v - o.a - o.b * x[i]); let s1 = 0, s2 = 0; e.forEach((v, i) => { s2 += v * v; if (i) s1 += (v - e[i - 1]) ** 2; });
      o.dw = s2 > 0 ? s1 / s2 : null;
    }
    o.ra = autokorr(x); o.rb = autokorr(y);
    if (o.r != null && o.ra != null && o.rb != null) {   // effektive Stichprobe nach Bartlett (Autokorrelation 1. Ordnung)
      const q = o.ra * o.rb; o.neff = Math.max(3, Math.min(n, n * (1 - q) / (1 + q))); o.pEff = pWert(o.r, o.neff);
    }
    return o;
  }
  function autokorr(x) { return x.length > 4 ? pearson(x.slice(1), x.slice(0, -1)) : null; }

  /* ======================= Zeit ======================= */
  const RANG = { A: 1, Q: 2, M: 3, D: 4 };
  const FNAME = { A: "Jahr", Q: "Quartal", M: "Monat", D: "Tag (Handelstage)" };
  const PPJ = { A: 1, Q: 4, M: 12 };
  const pad = n => String(n).padStart(2, "0");
  function parse(k) {
    k = String(k); let m;
    if ((m = /^(\d{4})$/.exec(k))) return { y: +m[1] };
    if ((m = /^(\d{4})-Q(\d)$/.exec(k))) return { y: +m[1], q: +m[2] };
    if ((m = /^(\d{4})-(\d\d)$/.exec(k))) return { y: +m[1], mo: +m[2] };
    if ((m = /^(\d{4})-(\d\d)-(\d\d)$/.exec(k))) return { y: +m[1], mo: +m[2], d: +m[3] };
    return null;
  }
  function pkey(k, f) {
    const p = parse(k); if (!p) return null;
    if (f === "A") return String(p.y);
    if (f === "Q") return `${p.y}-Q${p.q || Math.ceil(p.mo / 3)}`;
    if (f === "M") return `${p.y}-${pad(p.mo)}`;
    return String(k);
  }
  const jahrVon = k => parse(k).y;
  function pidx(k, f) { const p = parse(k); return f === "A" ? p.y : f === "Q" ? p.y * 4 + p.q - 1 : p.y * 12 + p.mo - 1; }
  const MON = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"];
  function zl(k) {
    const p = parse(k); if (!p) return String(k);
    if (p.d) return `${pad(p.d)}.${pad(p.mo)}.${p.y}`; if (p.q) return `Q${p.q} ${p.y}`; if (p.mo) return `${MON[p.mo - 1]} ${p.y}`; return String(p.y);
  }

  /* Reihe auf gewünschte Frequenz bringen: Mittel (Raten, Salden) oder letzter Wert (Bestände, Kurse, Indizes) */
  function aufFreq(s, f, agg) {
    if (s.freq === f) return s.pts.slice().sort((a, b) => a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0);
    const g = new Map();
    for (const [k, v] of s.pts.slice().sort((a, b) => a[0] < b[0] ? -1 : 1)) { const pk = pkey(k, f); if (!g.has(pk)) g.set(pk, []); g.get(pk).push(v); }
    const m = agg === "auto" ? s.agg : agg;
    return [...g.entries()].map(([k, vs]) => [k, m === "mittel" ? mean(vs) : vs[vs.length - 1]]).sort((a, b) => a[0] < b[0] ? -1 : 1);
  }
  const TRANS = { niveau: "Niveau", diff: "Differenz zur Vorperiode", pct: "Veränderung zur Vorperiode (%)", log: "Log-Rendite", yoy: "Veränderung zum Vorjahr (%)" };
  function autoTrans(s, f) {
    if (s.art === "kurs") return "log";
    if (s.art === "rate" || s.art === "saldo" || s.art === "quote") return "niveau";
    return f === "A" || f === "D" ? "pct" : "yoy";       // Niveaus/Indizes: Veränderungsrate statt Niveau
  }
  function transf(pts, f, tr) {
    if (tr === "niveau") return pts.map(p => [p[0], p[1]]);
    const idx = new Map(); pts.forEach((p, i) => idx.set(f === "D" ? i : pidx(p[0], f), p[1]));
    const lagN = tr === "yoy" ? PPJ[f] || 1 : 1, out = [];
    pts.forEach((p, i) => {
      const prev = idx.get((f === "D" ? i : pidx(p[0], f)) - lagN); if (prev == null) return;
      const v = p[1];
      if (tr === "diff") out.push([p[0], v - prev]);
      else if (tr === "log") { if (v > 0 && prev > 0) out.push([p[0], Math.log(v / prev)]); }
      else if (prev !== 0 && (tr === "yoy" || tr === "pct")) { if (prev > 0 || tr === "yoy" || tr === "pct") out.push([p[0], (v - prev) / Math.abs(prev) * 100]); }
    });
    return out;
  }

  /* ======================= Daten ======================= */
  let V = null, U = null, bereit = false;
  const cache = new Map();
  const KAB = { ertraege: "Erträge (Konzern)", zinsueberschuss: "Zinsüberschuss (Konzern)", vorsteuer: "Vorsteuerergebnis (Konzern)", steuern: "Steuern (Konzern)", jue: "Jahresüberschuss (Konzern)",
    eps: "Ergebnis je Aktie (Konzern)", aufwand: "Aufwand (Konzern)", bilanzsumme: "Bilanzsumme (Konzern)", ek: "Eigenkapital (Konzern)", tbv: "Mat. Eigenkapital (Konzern)", kredite: "Kredite (Konzern)", goodwill: "Goodwill (Konzern)" };
  function init() {
    if (bereit) return;
    bereit = true;
    V = typeof VWL !== "undefined" && VWL.da() ? VWL.korr() : null;
    U = typeof UNT !== "undefined" && UNT.da() ? UNT.korr() : null;
    if (V) { V.nameVon = Object.fromEntries(V.serien.map(s => [s.serie_id, s])); V.land = Object.fromEntries(V.laender.map(l => [l.geo, l.name])); }
    if (U) {
      U.nach = Object.fromEntries(U.firmen.map(f => [f.id, f]));
      U.zr = U.firmen.filter(f => Object.keys(fkz(f)).length);
      U.kursFirmen = U.firmen.filter(f => U.kurse(f));
    }
    S.A = vorgabe("vwl", 0); S.B = vorgabe("vwl", 1);
    S.matrix = [];
    if (U) {   // Vorgabe Querschnitt: die am dichtesten belegten Kennzahlen, Größenangaben (Beträge) nachrangig
      const n = k => U.firmen.filter(f => f.werte && f.werte[k] != null && isFinite(f.werte[k])).length, quote = k => U.kz[k] && ["pct", "x", "chg"].includes(U.kz[k].fmt);
      const ks = Object.keys(U.kz).filter(k => n(k) >= 10).sort((a, b) => (quote(b) - quote(a)) || (n(b) - n(a)));
      S.qs.set = ks.slice(0, 8); S.qs.x = ks[0] || S.qs.x; S.qs.y = ks[1] || S.qs.y;
    }
  }
  /* Jahreswerte eines Unternehmens: erhobene Reihen und Konzernabschlüsse (Yahoo) */
  function fkz(f) {
    if (f._kz) return f._kz;
    const o = {};
    for (const [k, r] of Object.entries(f.reihen || {})) if (r.punkte.length >= 1) o[k] = { name: U.kzName(k), pts: r.punkte.map(p => [String(p[0]), p[1]]), basis: r.basis };
    const m = f.ticker && typeof MARKT !== "undefined" && MARKT && MARKT.werte.find(x => x.ticker === f.ticker);
    if (m && m.abschluesse) for (const fe of Object.keys(KAB)) {
      const pts = m.abschluesse.filter(a => a[fe] != null).map(a => [String(a.jahr), a[fe]]);
      if (pts.length) o["y_" + fe] = { name: KAB[fe], pts, basis: "Konzernabschluss laut Yahoo Finance, " + (m.bilanzwaehrung || m.waehrung || "") };
    }
    f._kz = o; return o;
  }
  function seriesVWL(a, geo) {
    const s = V.nameVon[a], d = V.daten[a] && V.daten[a][geo]; if (!s || !d) return null;
    const pa = s.prognose_ab, pts = d.filter(p => !(pa && String(p[0]) >= pa)).map(p => [String(p[0]), p[1]]);   // Projektionen sind keine Beobachtungen
    if (!pts.length) return null;
    return { label: `${s.name} · ${V.land[geo] || geo}`, kurz: `${s.name.replace(/ \(.*?\)/, "")} ${geo}`, freq: s.frequenz, pts, art: s.art === "rate" ? "rate" : s.art === "saldo" ? "saldo" : s.art === "index" ? "index" : "niveau",
      agg: s.art === "rate" || s.art === "saldo" ? "mittel" : "letzter", einheit: s.einheit, quelle: "VWL", projektionen: !!pa };
  }
  function resolve(sp) {
    if (!sp) return null;
    const key = [sp.typ, sp.a, sp.b].join("|"); if (cache.has(key)) return cache.get(key);
    let r = null;
    try {
      if (sp.typ === "vwl" && V) r = seriesVWL(sp.a, sp.b);
      else if (sp.typ === "fkz" && U) {
        const f = U.nach[sp.a], k = f && fkz(f)[sp.b];
        if (k) r = { label: `${f.name} · ${k.name}`, kurz: `${U.kurz(f.name)} ${k.name}`, freq: "A", pts: k.pts, art: /quote|marge|rendite|ratio/.test(sp.b) ? "quote" : "niveau", agg: "letzter", einheit: k.basis, quelle: "Unternehmen" };
      } else if (sp.typ === "kurs" && U) {
        const f = U.nach[sp.a], k = f && U.kurse(f);
        if (k) r = { label: `${f.name} · Schlusskurs`, kurz: `${U.kurz(f.name)} Kurs`, freq: "D", pts: k.kurse.map(p => [p[0], p[1]]), art: "kurs", agg: "letzter", einheit: k.waehrung || "", quelle: "Kurse" };
      } else if (sp.typ === "bkz" && U) r = branchenKz(sp.a, sp.b);
      else if (sp.typ === "bkurs" && U) r = branchenKurs(sp.a);
    } catch (e) { r = null; }
    cache.set(key, r); return r;
  }
  const MINF = 3;                                         // Mindestzahl Unternehmen je Branchenwert
  function branchenKz(br, k) {
    const fs = U.firmen.filter(f => f.branche === br), j = new Map();
    for (const f of fs) { const s = fkz(f)[k]; if (!s) continue; for (const [y, v] of s.pts) { if (!j.has(y)) j.set(y, []); j.get(y).push(v); } }
    const pts = [...j.entries()].filter(([, v]) => v.length >= MINF).map(([y, v]) => [y, median(v)]).sort((a, b) => a[0] < b[0] ? -1 : 1);
    if (!pts.length) return null;
    const nm = (fs.map(f => fkz(f)[k]).find(Boolean) || {}).name || k;
    return { label: `${U.brName(br)} · Median ${nm}`, kurz: `${U.brName(br)} Median ${nm}`, freq: "A", pts, art: /quote|marge|rendite|ratio/.test(k) ? "quote" : "niveau", agg: "letzter", einheit: `Median über Unternehmen, mind. ${MINF} je Jahr`, quelle: "Branche" };
  }
  function branchenKurs(br) {                              // gleichgewichteter Index aus den Tagesrenditen der Unternehmen
    const fs = U.kursFirmen.filter(f => f.branche === br); if (fs.length < MINF) return null;
    const tag = new Map();
    for (const f of fs) { const k = U.kurse(f).kurse; for (let i = 1; i < k.length; i++) if (k[i][1] > 0 && k[i - 1][1] > 0) { const d = k[i][0]; if (!tag.has(d)) tag.set(d, []); tag.get(d).push(Math.log(k[i][1] / k[i - 1][1])); } }
    const ds = [...tag.keys()].sort().filter(d => tag.get(d).length >= MINF); if (ds.length < 5) return null;
    let ix = 100; const pts = [[ds[0], ix]];
    for (let i = 1; i < ds.length; i++) { ix *= Math.exp(mean(tag.get(ds[i]))); pts.push([ds[i], ix]); }
    return { label: `${U.brName(br)} · Kursindex (gleichgewichtet, ${fs.length} Werte)`, kurz: `${U.brName(br)} Kursindex`, freq: "D", pts, art: "kurs", agg: "letzter", einheit: "Index", quelle: "Branche" };
  }

  /* ======================= Zustand ======================= */
  const S = { modus: "paar", A: null, B: null, freq: "auto", agg: "auto", trA: "auto", trB: "auto", von: "", bis: "", lag: 0, methode: "pearson", logmat: false,
    matrix: [], mFreq: "auto", mTr: "auto", mMeth: "pearson", mNeu: null, qs: { x: "kgv", y: "roe", bra: "alle", not: "alle", lx: false, ly: false, set: [], meth: "pearson" } };
  function vorgabe(typ, nr) {
    if (typ === "vwl" && V) { const k = V.serien.filter(s => s.kern); const wahl = ["wirtschaftsstimmung", "produktion"].map(id => V.nameVon[id]).filter(Boolean);
      const s = (wahl[nr] || k[nr] || V.serien[nr] || V.serien[0]); return { typ: "vwl", a: s.serie_id, b: V.daten[s.serie_id] && V.daten[s.serie_id].DE ? "DE" : Object.keys(V.daten[s.serie_id] || {})[0] || "DE" }; }
    if (typ === "fkz" && U) { const f = U.zr[0], k = f && Object.keys(fkz(f))[0]; return { typ: "fkz", a: f ? f.id : "", b: k || "" }; }
    if (typ === "kurs" && U) return { typ: "kurs", a: U.kursFirmen[0] ? U.kursFirmen[0].id : "", b: "" };
    if (typ === "bkz" && U) { const br = U.branchen.find(b => bKz(b.id).length) || U.branchen[0]; return { typ: "bkz", a: br.id, b: (bKz(br.id)[0] || {}).key || "" }; }
    if (typ === "bkurs" && U) { const br = U.branchen.find(b => U.kursFirmen.filter(f => f.branche === b.id).length >= MINF) || U.branchen[0]; return { typ: "bkurs", a: br.id, b: "" }; }
    return { typ, a: "", b: "" };
  }
  const bKzCache = {};
  function bKz(br) {
    if (bKzCache[br]) return bKzCache[br];
    const m = new Map(); for (const f of U.firmen.filter(f => f.branche === br)) for (const [k, s] of Object.entries(fkz(f))) m.set(k, s.name);
    return bKzCache[br] = [...m.entries()].filter(([k]) => branchenKz(br, k)).map(([key, name]) => ({ key, name }));
  }
  const TYPEN = () => [["vwl", "Volkswirtschaft: Reihe", !!V], ["fkz", "Unternehmen: Jahreskennzahl", !!U && U.zr.length > 0], ["kurs", "Unternehmen: Aktienkurs", !!U && U.kursFirmen.length > 0],
    ["bkz", "Branche: Median einer Kennzahl", !!U && U.branchen.some(b => bKz(b.id).length)], ["bkurs", "Branche: Kursindex", !!U && U.branchen.some(b => U.kursFirmen.filter(f => f.branche === b.id).length >= MINF)]].filter(t => t[2]);

  /* ======================= Auswertung eines Paares ======================= */
  function vorbereiten(sp, f, tr, agg) {
    const s = resolve(sp); if (!s) return { fehler: "Reihe nicht verfügbar" };
    if (RANG[s.freq] < RANG[f]) return { fehler: `„${s.kurz}“ liegt nur ${FNAME[s.freq] === "Jahr" ? "jährlich" : s.freq === "Q" ? "vierteljährlich" : "monatlich"} vor, nicht pro ${FNAME[f]}` };
    const t = tr === "auto" ? autoTrans(s, f) : tr;
    if (t === "yoy" && f === "D") return { fehler: "Veränderung zum Vorjahr gibt es bei Tageswerten nicht" };
    return { s, t, f, pts: transf(aufFreq(s, f, agg), f, t).filter(p => isFinite(p[1])) };
  }
  function idxFn(f, ka, kb) {
    if (f !== "D") return k => pidx(k, f);
    const all = [...new Set([...ka, ...kb])].sort(), m = new Map(all.map((k, i) => [k, i])); return k => m.get(k);
  }
  function paare(pa, pb, f, lag, von, bis) {
    const ix = idxFn(f, pa.map(p => p[0]), pb.map(p => p[0])), mb = new Map(pb.map(p => [ix(p[0]), p]));
    const rows = [];
    for (const [k, v] of pa) {
      const y = jahrVon(k); if ((von && y < von) || (bis && y > bis)) continue;
      const q = mb.get(ix(k) + lag); if (q) rows.push({ k, kb: q[0], a: v, b: q[1] });
    }
    return rows;
  }
  const lagMax = f => ({ A: 3, Q: 6, M: 12, D: 20 })[f];
  function autoFreq(ss) { return ss.reduce((m, s) => RANG[s.freq] < RANG[m] ? s.freq : m, "D"); }

  function auswertungPaar() {
    const a = resolve(S.A), b = resolve(S.B);
    if (!a || !b) return { fehler: "Für Reihe A oder B liegen keine Daten vor." };
    const f = S.freq === "auto" ? autoFreq([a, b]) : S.freq;
    const A = vorbereiten(S.A, f, S.trA, S.agg), B = vorbereiten(S.B, f, S.trB, S.agg);
    if (A.fehler || B.fehler) return { fehler: A.fehler || B.fehler, f };
    const von = +S.von || 0, bis = +S.bis || 0, K = lagMax(f);
    const rows = paare(A.pts, B.pts, f, S.lag, von, bis);
    const x = rows.map(r => r.a), y = rows.map(r => r.b), st = stat(x, y);
    const cc = [];
    for (let k = -K; k <= K; k++) {
      const rr = paare(A.pts, B.pts, f, k, von, bis), xx = rr.map(r => r.a), yy = rr.map(r => r.b);
      cc.push({ k, n: rr.length, r: rr.length >= 5 ? (S.methode === "spearman" ? spearman(xx, yy) : pearson(xx, yy)) : null });
    }
    return { a, b, A, B, f, rows, x, y, st, cc, K, von, bis };
  }
  function hinweise(R) {
    const h = [], st = R.st;
    if (st.n < 3) { h.push(["warn", `Nur ${st.n} gemeinsame Beobachtungen: keine Auswertung möglich.`]); return h; }
    if (st.r == null) h.push(["warn", "Mindestens eine Reihe ist im Zeitraum konstant, der Korrelationskoeffizient ist nicht definiert."]);
    if (st.n < 10) h.push(["warn", `Sehr kurze Reihe (n = ${st.n}): Der Koeffizient schwankt stark, das Konfidenzintervall ist breit; Ergebnis nur als Hinweis lesen.`]);
    else if (st.n < 30) h.push(["hinweis", `Kurze Reihe (n = ${st.n}): Konfidenzintervall und p-Wert beachten, ein einzelner Ausreißer kann das Ergebnis tragen.`]);
    const trend = [R.A, R.B].filter(z => z.t === "niveau" && (z.s.art === "niveau" || z.s.art === "index" || z.s.art === "kurs"));
    if (trend.length) h.push(["warn", `Scheinkorrelation möglich: ${trend.map(z => "„" + z.s.kurz + "“").join(" und ")} liegt als Niveau vor, Reihen mit Trend korrelieren oft nur wegen des gemeinsamen Trends. Veränderungsrate oder Differenz prüfen.`]);
    else if (st.ra != null && st.rb != null && Math.abs(st.ra) > .8 && Math.abs(st.rb) > .8) h.push(["hinweis", `Beide Reihen sind stark autokorreliert (${f2.format(st.ra)} und ${f2.format(st.rb)}). Der p-Wert ist dann zu optimistisch; maßgeblich ist der angepasste p-Wert mit effektiver Stichprobe n_eff = ${f1.format(st.neff)}.`]);
    if ((R.A.t === "yoy" || R.B.t === "yoy") && R.f !== "A") h.push(["hinweis", "Veränderungen zum Vorjahr aus Monats- oder Quartalswerten überlappen sich und sind dadurch autokorreliert; der p-Wert ist zu optimistisch (siehe n_eff)."]);
    if (st.dw != null && st.dw < 1) h.push(["hinweis", `Durbin-Watson ${f2.format(st.dw)} (< 1): Die Residuen der Regressionsgeraden sind positiv autokorreliert, die Standardfehler sind unterschätzt.`]);
    if (st.r != null && st.rho != null && Math.abs(st.r - st.rho) > .2) h.push(["hinweis", `Pearson (${f2.format(st.r)}) und Spearman (${f2.format(st.rho)}) weichen deutlich ab: Ausreißer oder ein nichtlinearer Zusammenhang bestimmen das Ergebnis.`]);
    if (S.lag === 0 && R.cc.filter(c => c.r != null).length > 1) { const best = bestLag(R); if (best && best.k !== 0 && Math.abs(best.r) - Math.abs((R.cc.find(c => c.k === 0) || {}).r || 0) > .1) h.push(["hinweis", `Bei Verzögerung ${best.k > 0 ? "+" : ""}${best.k} ist die Korrelation höher (${f2.format(best.r)}). Das beste von ${R.cc.filter(c => c.r != null).length} Lags ist nicht multipel getestet; der p-Wert dafür wäre zu optimistisch.`]); }
    if (R.a.projektionen || R.b.projektionen) h.push(["info", "Projektionen (OECD Economic Outlook) sind ausgeschlossen, es zählen nur beobachtete Werte."]);
    if (R.a.freq !== R.f || R.b.freq !== R.f) h.push(["info", `Auf ${FNAME[R.f].replace(" (Handelstage)", "")}-Frequenz umgerechnet (${[R.a, R.b].filter(s => s.freq !== R.f).map(s => s.kurz + ": " + ((S.agg === "auto" ? s.agg : S.agg) === "mittel" ? "Mittel" : "letzter Wert")).join("; ")}).`]);
    if ([R.a, R.b].some(s => s.quelle === "Unternehmen" || s.quelle === "Branche") && R.f === "A") h.push(["info", "Jahreswerte der Unternehmen sind nach Berichtsjahr zugeordnet; abweichende Geschäftsjahre werden nicht verschoben."]);
    return h;
  }
  const bestLag = R => R.cc.filter(c => c.r != null).reduce((m, c) => !m || Math.abs(c.r) > Math.abs(m.r) ? c : m, null);

  /* ======================= Darstellung ======================= */
  const fz = v => v == null || !isFinite(v) ? "n. v." : new Intl.NumberFormat("de-DE", { maximumSignificantDigits: 4 }).format(v);
  const fr = v => v == null ? "n. v." : f2.format(v);
  const fp = p => p == null ? "n. v." : p < 0.001 ? "< 0,001" : nf(3).format(p);
  function nice(min, max, n = 5) {
    if (!(max > min)) { const d = Math.abs(min) * .1 || 1; min -= d; max += d; }
    const st0 = (max - min) / n, mag = 10 ** Math.floor(Math.log10(st0)), r = st0 / mag, st = (r < 1.5 ? 1 : r < 3 ? 2 : r < 7 ? 5 : 10) * mag;
    const a = Math.floor(min / st) * st, b = Math.ceil(max / st) * st, t = []; for (let v = a; v <= b + st / 2; v += st) t.push(+v.toPrecision(12));
    return { t, a, b };
  }
  function streu(pts, st, xn, yn, { href = false } = {}) {
    const W = 680, H = 400, L = 62, R = 16, T = 14, B = 46;
    const xs = pts.map(p => p.x), ys = pts.map(p => p.y), nx = nice(Math.min(...xs), Math.max(...xs)), ny = nice(Math.min(...ys), Math.max(...ys));
    const sx = v => L + (v - nx.a) / (nx.b - nx.a) * (W - L - R), sy = v => H - B - (v - ny.a) / (ny.b - ny.a) * (H - B - T);
    let s = `<svg viewBox="0 0 ${W} ${H}" style="max-width:760px" role="img" aria-label="Streudiagramm ${esc(xn)} gegen ${esc(yn)}">`;
    ny.t.forEach(v => { s += `<line class="gl" x1="${L}" x2="${W - R}" y1="${sy(v)}" y2="${sy(v)}"/><text x="${L - 6}" y="${sy(v) + 4}" text-anchor="end">${fz(v)}</text>`; });
    nx.t.forEach(v => { s += `<line class="gl" y1="${T}" y2="${H - B}" x1="${sx(v)}" x2="${sx(v)}"/><text x="${sx(v)}" y="${H - B + 16}" text-anchor="middle">${fz(v)}</text>`; });
    s += `<line class="ax" x1="${L}" x2="${W - R}" y1="${H - B}" y2="${H - B}"/><line class="ax" x1="${L}" x2="${L}" y1="${T}" y2="${H - B}"/>`;
    if (nx.a < 0 && nx.b > 0) s += `<line class="ax" x1="${sx(0)}" x2="${sx(0)}" y1="${T}" y2="${H - B}" stroke-dasharray="3 3"/>`;
    if (ny.a < 0 && ny.b > 0) s += `<line class="ax" x1="${L}" x2="${W - R}" y1="${sy(0)}" y2="${sy(0)}" stroke-dasharray="3 3"/>`;
    pts.forEach((p, i) => {
      const o = pts.length > 1 && p.t != null ? .3 + .7 * i / (pts.length - 1) : .75;
      const c = `<circle cx="${sx(p.x)}" cy="${sy(p.y)}" r="3.6" fill="var(--amber)" fill-opacity="${o.toFixed(2)}" stroke="var(--panel)" stroke-width="1" data-tip="${esc(p.tip)}"${href && p.href ? ' style="cursor:pointer"' : ""}/>`;
      s += href && p.href ? `<a href="${esc(p.href)}">${c}</a>` : c;
    });
    if (st.b != null) { const x0 = Math.min(...xs), x1 = Math.max(...xs); s += `<line x1="${sx(x0)}" y1="${sy(st.a + st.b * x0)}" x2="${sx(x1)}" y2="${sy(st.a + st.b * x1)}" stroke="var(--geno)" stroke-width="1.8" data-tip="${esc(`Regressionsgerade\ny = ${fz(st.a)} + ${fz(st.b)} · x\nR² = ${fr(st.r == null ? null : st.r * st.r)}`)}"/>`; }
    s += `<text x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle">${esc(xn)}</text><text transform="translate(14 ${(T + H - B) / 2}) rotate(-90)" text-anchor="middle">${esc(yn)}</text></svg>`;
    return s;
  }
  function linien(rows, an, bn) {
    const W = 680, H = 190, L = 40, R = 12, T = 10, B = 24, n = rows.length;
    const z = v => { const m = mean(v), sd = Math.sqrt(mean(v.map(q => (q - m) ** 2))) || 1; return v.map(q => (q - m) / sd); };
    const za = z(rows.map(r => r.a)), zb = z(rows.map(r => r.b)), all = za.concat(zb), mn = Math.min(...all), mx = Math.max(...all), ny = nice(mn, mx, 4);
    const sx = i => L + (n > 1 ? i / (n - 1) : .5) * (W - L - R), sy = v => H - B - (v - ny.a) / (ny.b - ny.a) * (H - B - T);
    let s = `<svg viewBox="0 0 ${W} ${H}" style="max-width:900px" role="img" aria-label="Verlauf beider Reihen, standardisiert">`;
    ny.t.forEach(v => { s += `<line class="gl" x1="${L}" x2="${W - R}" y1="${sy(v)}" y2="${sy(v)}"/><text x="${L - 6}" y="${sy(v) + 4}" text-anchor="end">${fz(v)}</text>`; });
    const lab = [0, Math.floor((n - 1) / 2), n - 1].filter((v, i, a) => a.indexOf(v) === i);
    lab.forEach(i => { s += `<text x="${sx(i)}" y="${H - 6}" text-anchor="${i === 0 ? "start" : i === n - 1 ? "end" : "middle"}">${esc(zl(rows[i].k))}</text>`; });
    const pl = (zv, c, d) => `<polyline fill="none" stroke="${c}" stroke-width="1.6" ${d ? 'stroke-dasharray="5 3"' : ""} points="${zv.map((v, i) => sx(i).toFixed(1) + "," + sy(v).toFixed(1)).join(" ")}"/>`;
    s += pl(za, "var(--amber)") + pl(zb, "var(--geno)", true);
    s += rows.map((r, i) => `<rect x="${sx(i) - Math.max(2, (W - L - R) / n / 2)}" y="${T}" width="${Math.max(4, (W - L - R) / n)}" height="${H - B - T}" fill="transparent" data-tip="${esc(`<b>${zl(r.k)}</b>\nA: ${fz(r.a)}\nB: ${fz(r.b)}${r.kb !== r.k ? " (" + zl(r.kb) + ")" : ""}`)}"/>`).join("");
    return legende([{ name: an + " (A)", farbe: "var(--amber)" }, { name: bn + " (B, gestrichelt)", farbe: "var(--geno)" }]) + s + "</svg>";
  }
  function kreuz(R) {
    const W = 680, H = 200, L = 40, R2 = 12, T = 12, B = 26, cs = R.cc, n = cs.length, bw = (W - L - R2) / n;
    const sy = v => T + (1 - v) / 2 * (H - T - B), sig = R.st.n > 2 ? 1.96 / Math.sqrt(Math.max(R.st.n, 4)) : null;
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Kreuzkorrelation nach Verzögerung">`;
    [-1, -.5, 0, .5, 1].forEach(v => { s += `<line class="gl" x1="${L}" x2="${W - R2}" y1="${sy(v)}" y2="${sy(v)}"/><text x="${L - 6}" y="${sy(v) + 4}" text-anchor="end">${f1.format(v)}</text>`; });
    if (sig) [sig, -sig].forEach(v => { s += `<line x1="${L}" x2="${W - R2}" y1="${sy(v)}" y2="${sy(v)}" stroke="var(--ink-3)" stroke-dasharray="4 3"/>`; });
    cs.forEach((c, i) => {
      const x = L + i * bw, sel = c.k === S.lag;
      if (c.r != null) s += `<rect x="${x + 2}" y="${Math.min(sy(0), sy(c.r))}" width="${Math.max(1, bw - 4)}" height="${Math.max(1, Math.abs(sy(c.r) - sy(0)))}" fill="${sel ? "var(--amber)" : "var(--s3)"}" data-klag="${c.k}" style="cursor:pointer" data-tip="${esc(`<b>Lag ${c.k > 0 ? "+" : ""}${c.k}</b>\nr = ${fr(c.r)}\nn = ${c.n}\nKlick: Lag übernehmen`)}"/>`;
      else s += `<rect x="${x + 2}" y="${sy(0) - 1}" width="${Math.max(1, bw - 4)}" height="2" fill="var(--line)" data-tip="${esc(`Lag ${c.k}: zu wenige Paare (n = ${c.n})`)}"/>`;
      if (n <= 27 || c.k % 5 === 0) s += `<text x="${x + bw / 2}" y="${H - 8}" text-anchor="middle" ${sel ? 'style="fill:var(--amber)"' : ""}>${c.k > 0 ? "+" : ""}${c.k}</text>`;
    });
    return s + "</svg>";
  }
  function farbeR(r, p) {
    if (r == null) return "transparent"; const a = (Math.abs(r) * .85 * (p != null && p > .05 ? .45 : 1)).toFixed(2);
    return r >= 0 ? `rgba(255,168,40,${a})` : `rgba(47,134,221,${a})`;
  }
  /* Matrix: namen[], zellen[i][j] = {r, n, p, rho} */
  function heat(namen, zellen, methode, klickAttr) {
    const n = namen.length, cs = n > 9 ? 40 : 52, L = 220, T = 28, W = L + n * cs + 10, H = T + n * cs + 6;
    const short = s => s.length > 34 ? s.slice(0, 33) + "…" : s;
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Korrelationsmatrix" style="max-width:${W}px">`;
    namen.forEach((nm, i) => {
      s += `<text x="${L - 8}" y="${T + i * cs + cs / 2 + 4}" text-anchor="end" data-tip="${esc(nm)}">${i + 1} ${esc(short(nm))}</text><text x="${L + i * cs + cs / 2}" y="${T - 10}" text-anchor="middle">${i + 1}</text>`;
      for (let j = 0; j < n; j++) {
        const c = zellen[i][j], v = c ? (methode === "spearman" ? c.rho : c.r) : null, p = c ? (methode === "spearman" ? c.pRho : c.p) : null;
        const tip = i === j ? esc(nm) : c && v != null ? esc(`<b>${namen[i]}</b>\n↔ ${namen[j]}\n${methode === "spearman" ? "Spearman ρ" : "Pearson r"} = ${fr(v)}\np = ${fp(p)} · n = ${c.n}${c.n < 10 ? "\nn < 10: kaum belastbar" : ""}`) : esc(`${namen[i]}\n↔ ${namen[j]}\nzu wenige gemeinsame Werte${c ? " (n = " + c.n + ")" : ""}`);
        s += `<rect x="${L + j * cs + 1}" y="${T + i * cs + 1}" width="${cs - 2}" height="${cs - 2}" rx="3" fill="${i === j ? "var(--panel-2)" : farbeR(v, p)}" stroke="var(--line)" ${klickAttr && i !== j && v != null ? `${klickAttr(i, j)} style="cursor:pointer"` : ""} data-tip="${tip}"/>`;
        if (i !== j && v != null) s += `<text x="${L + j * cs + cs / 2}" y="${T + i * cs + cs / 2 + 4}" text-anchor="middle" style="fill:${p != null && p > .05 ? "var(--ink-3)" : "var(--ink)"};font-family:var(--mono);font-size:${cs > 44 ? 12 : 10.5}px;pointer-events:none">${fr(v)}</text>`;
      }
    });
    return s + "</svg>";
  }
  const heatLegende = `<div class="legend" style="margin:8px 0 0"><span><i class="sw" style="background:rgba(47,134,221,.8)"></i>negativ</span><span><i class="sw" style="background:rgba(255,168,40,.8)"></i>positiv</span><span>Zahl in Grau: nicht signifikant (p &gt; 0,05, unkorrigiert), Farbe dann blasser</span></div>`;

  /* ----- Auswahlfelder ----- */
  const opt = (v, t, sel) => `<option value="${esc(v)}"${sel ? " selected" : ""}>${esc(t)}</option>`;
  function slotUi(id, sp) {
    const typen = TYPEN(); let h = `<div class="kslot" data-slot="${id}" style="display:flex;flex-wrap:wrap;gap:6px;align-items:center">`;
    h += `<select data-kf="typ" aria-label="Art der Reihe ${id}">${typen.map(t => opt(t[0], t[1], t[0] === sp.typ)).join("")}</select>`;
    if (sp.typ === "vwl") {
      const gr = V.themen.map(t => ({ t, l: V.serien.filter(s => s.thema === t.thema && V.daten[s.serie_id]) })).filter(g => g.l.length);
      h += `<select data-kf="a" aria-label="Reihe" style="max-width:100%">${gr.map(g => `<optgroup label="${esc(g.t.name)}">${g.l.map(s => opt(s.serie_id, s.name, s.serie_id === sp.a)).join("")}</optgroup>`).join("")}</select>`;
      const geos = Object.keys(V.daten[sp.a] || {}); h += `<select data-kf="b" aria-label="Land">${geos.map(g => opt(g, V.land[g] || g, g === sp.b)).join("")}</select>`;
    } else if (sp.typ === "fkz" || sp.typ === "kurs") {
      const f = U.nach[sp.a], liste = sp.typ === "fkz" ? U.zr : U.kursFirmen;
      h += `<input data-kf="firma" list="kor-l-${sp.typ}" value="${esc(f ? f.name : "")}" placeholder="Unternehmen wählen …" aria-label="Unternehmen" style="min-width:210px;background:#000;border:1px solid var(--line);border-radius:999px;padding:4px 12px">`;
      h += `<datalist id="kor-l-${sp.typ}">${liste.map(x => `<option value="${esc(x.name)}">`).join("")}</datalist>`;
      if (sp.typ === "fkz" && f) h += `<select data-kf="b" aria-label="Kennzahl">${Object.entries(fkz(f)).map(([k, s]) => opt(k, `${s.name} (${s.pts.length} J.)`, k === sp.b)).join("")}</select>`;
    } else if (sp.typ === "bkz" || sp.typ === "bkurs") {
      const brs = sp.typ === "bkz" ? U.branchen.filter(b => bKz(b.id).length) : U.branchen.filter(b => U.kursFirmen.filter(f => f.branche === b.id).length >= MINF);
      h += `<select data-kf="a" aria-label="Branche">${brs.map(b => opt(b.id, b.name, b.id === sp.a)).join("")}</select>`;
      if (sp.typ === "bkz") h += `<select data-kf="b" aria-label="Kennzahl">${bKz(sp.a).map(k => opt(k.key, k.name, k.key === sp.b)).join("")}</select>`;
    }
    return h + "</div>";
  }
  function slotAender(sp, feld, wert) {
    if (feld === "typ") return vorgabe(wert, 0);
    const n = { ...sp };
    if (feld === "firma") {
      const f = (sp.typ === "fkz" ? U.zr : U.kursFirmen).find(x => x.name.toLowerCase() === String(wert).trim().toLowerCase()) || (sp.typ === "fkz" ? U.zr : U.kursFirmen).find(x => x.name.toLowerCase().includes(String(wert).trim().toLowerCase()) && wert.trim().length > 2);
      if (!f) return n; n.a = f.id; if (sp.typ === "fkz") n.b = Object.keys(fkz(f))[0] || ""; return n;
    }
    n[feld] = wert;
    if (feld === "a" && sp.typ === "vwl") { const g = Object.keys(V.daten[wert] || {}); if (!g.includes(n.b)) n.b = g.includes("DE") ? "DE" : g[0]; }
    if (feld === "a" && sp.typ === "bkz") n.b = (bKz(wert)[0] || {}).key || "";
    return n;
  }
  const sel = (id, opts, cur, label) => `<select id="${id}" aria-label="${esc(label)}">${opts.map(([v, t]) => opt(v, t, String(v) === String(cur))).join("")}</select>`;
  const lab = (t, inh) => `<label style="display:inline-flex;gap:6px;align-items:center;color:var(--ink-3);font-size:12px">${t} ${inh}</label>`;
  const tabs = () => `<div class="ctrl" style="margin-bottom:12px">${[["paar", "Zeitreihen A ↔ B"], ["matrix", "Matrix mehrerer Reihen"], ["quer", "Querschnitt Unternehmen"]].map(([k, n]) => `<button type="button" data-kmodus="${k}" aria-pressed="${S.modus === k}">${n}</button>`).join("")}</div>`;

  /* ----- Modus Paar ----- */
  function viewPaar() {
    const R = auswertungPaar(), typen = TYPEN();
    const fOpt = [["auto", "Automatisch (gröbste Reihe)"], ["A", "Jahr"], ["Q", "Quartal"], ["M", "Monat"], ["D", "Tag"]];
    const trOpt = au => [["auto", "Automatisch" + (au ? ": " + TRANS[au] : "")], ...Object.entries(TRANS)];
    const kopf = `<div style="display:grid;gap:10px">
      <div><b style="color:var(--amber)">A</b> ${slotUi("A", S.A)}</div>
      <div><b style="color:var(--geno)">B</b> ${slotUi("B", S.B)}</div>
      <div class="ctrl">
        ${lab("Frequenz", sel("kfreq", fOpt, S.freq, "Frequenz"))}
        ${lab("A als", sel("ktrA", trOpt(R.A && R.A.t), S.trA, "Transformation A"))}
        ${lab("B als", sel("ktrB", trOpt(R.B && R.B.t), S.trB, "Transformation B"))}
        ${lab("Umrechnung", sel("kagg", [["auto", "Mittel bei Raten, sonst letzter Wert"], ["mittel", "immer Mittelwert"], ["letzter", "immer letzter Wert"]], S.agg, "Aggregation"))}
      </div>
      <div class="ctrl">
        ${lab("von Jahr", `<input id="kvon" type="number" min="1950" max="2100" value="${esc(S.von)}" placeholder="früheste" style="width:90px;background:#000;border:1px solid var(--line);border-radius:999px;padding:4px 10px">`)}
        ${lab("bis Jahr", `<input id="kbis" type="number" min="1950" max="2100" value="${esc(S.bis)}" placeholder="späteste" style="width:90px;background:#000;border:1px solid var(--line);border-radius:999px;padding:4px 10px">`)}
        ${lab("Verzögerung (B gegenüber A)", sel("klag", Array.from({ length: 2 * lagMax(R.f || "M") + 1 }, (_, i) => i - lagMax(R.f || "M")).map(k => [k, (k > 0 ? "+" : "") + k + (k === 0 ? " (gleichzeitig)" : "")]), S.lag, "Verzögerung"))}
        ${lab("Verfahren", sel("kmeth", [["pearson", "Pearson r"], ["spearman", "Spearman ρ"]], S.methode, "Verfahren"))}
        <button type="button" class="mini" data-ktausch>A ↔ B tauschen</button>
      </div></div>`;
    let out = panel({ code: "KOR 1", titel: "Zwei Reihen gegeneinander", sub: "Reihen aus Volkswirtschaft, Unternehmen, Branchen und Kursen frei kombinierbar", body: tabs() + kopf });
    if (R.fehler) return out + panel({ code: "KOR 2", titel: "Auswertung", body: `<p style="color:var(--down);margin:0">${esc(R.fehler)}${R.fehler.includes("nur") ? " Gröbere Frequenz wählen (Automatisch passt sie an)." : ""}</p>` });
    const st = R.st, ok = st.n >= 3 && st.r != null, aktL = S.lag;
    const kachel = (n, v, s2) => `<div class="tile" style="--gf:var(--amber)"><div class="g"><b>${n}</b></div><div class="stats"><div><strong>${v}</strong></div></div><div class="pct" style="padding:0 0 2px">${s2 || "&nbsp;"}</div></div>`;
    const prim = S.methode === "spearman" ? st.rho : st.r, pprim = S.methode === "spearman" ? st.pRho : st.p;
    out += panel({ code: "KOR 2", titel: "Kennzahlen der Korrelation", sub: `${esc(R.a.kurz)} ↔ ${esc(R.b.kurz)} · ${FNAME[R.f]} · n = ${st.n}${st.n ? " · " + esc(zl(R.rows[0].k)) + " bis " + esc(zl(R.rows[R.rows.length - 1].k)) : ""}`,
      body: ok ? `<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px">
        ${kachel(S.methode === "spearman" ? "Spearman ρ" : "Pearson r", fr(prim), "")}
        ${kachel(S.methode === "spearman" ? "Pearson r" : "Spearman ρ", fr(S.methode === "spearman" ? st.r : st.rho), "")}
        ${kachel("p-Wert", fp(pprim), "zweiseitig, unkorrigiert")}
        ${kachel("p-Wert angepasst", fp(st.pEff), st.neff != null ? "n_eff = " + f1.format(st.neff) : "")}
        ${kachel("95-%-Intervall (r)", st.ci ? `${fr(st.ci[0])} … ${fr(st.ci[1])}` : "n. v.", "Fisher-z")}
        ${kachel("R²", fr(st.r * st.r), "Bestimmtheitsmaß")}
        ${kachel("Steigung", fz(st.b), "B je Einheit A, Achsenabschnitt " + fz(st.a))}
        ${kachel("n", String(st.n), `Verzögerung ${aktL > 0 ? "+" : ""}${aktL}`)}
      </div>` : `<p style="margin:0;color:var(--ink-2)">Keine Auswertung möglich (n = ${st.n}${st.r == null && st.n >= 3 ? ", konstante Reihe" : ""}).</p>`,
      fuss: `p-Wert aus der t-Verteilung mit n − 2 Freiheitsgraden. „Angepasst“ ersetzt n durch die effektive Stichprobe n_eff = n·(1 − ρ<sub>A</sub>ρ<sub>B</sub>)/(1 + ρ<sub>A</sub>ρ<sub>B</sub>) aus den Autokorrelationen 1. Ordnung (Bartlett) und ist bei Zeitreihen die vorsichtigere Angabe.` });
    if (ok) {
      const pts = R.rows.map((r, i) => ({ x: r.a, y: r.b, t: i, tip: `<b>${zl(r.k)}</b>${r.kb !== r.k ? " → " + zl(r.kb) : ""}\nA: ${fz(r.a)}\nB: ${fz(r.b)}` }));
      const nm = (z, w) => `${w.kurz}${z.t === "niveau" ? "" : " (" + TRANS[z.t].replace(" (%)", "") + (/%|Verän/.test(TRANS[z.t]) ? ", %" : "") + ")"}`;
      out += `<div class="grid">${panel({ code: "KOR 3", titel: "Streudiagramm mit Regressionsgerade", breite: "w7", sub: "helle Punkte = jüngere Perioden", body: streu(pts, st, "A: " + nm(R.A, R.a), "B: " + nm(R.B, R.b)) })}
        ${panel({ code: "KOR 4", titel: "Kreuzkorrelation nach Verzögerung", breite: "w5", sub: `${S.methode === "spearman" ? "Spearman" : "Pearson"} · Klick auf Balken setzt die Verzögerung`, body: kreuz(R),
          fuss: `Positiver Lag k: B folgt A um k Perioden später (A eilt voraus), negativer Lag: A folgt B. Gestrichelte Linien: ±1,96/√n, Rauschband bei unabhängigen Reihen.` })}</div>`;
      out += panel({ code: "KOR 5", titel: "Verlauf beider Reihen (standardisiert)", sub: "z-Werte der ausgewerteten, transformierten Reihen, B ggf. mit gewählter Verzögerung", body: linien(R.rows, R.a.kurz, R.b.kurz) });
    }
    const hw = hinweise(R), farbe = { warn: "var(--down)", hinweis: "var(--amber)", info: "var(--ink-3)" };
    out += panel({ code: "KOR 6", titel: "Hinweise zur Belastbarkeit", body: `<ul style="margin:0;padding-left:18px;display:grid;gap:6px">${hw.map(([t, x]) => `<li style="color:${t === "info" ? "var(--ink-2)" : "var(--ink)"}"><b style="color:${farbe[t]}">${t === "warn" ? "Achtung" : t === "hinweis" ? "Hinweis" : "Info"}:</b> ${esc(x)}</li>`).join("") || "<li>Keine Auffälligkeiten.</li>"}</ul>`,
      fuss: "Korrelation misst den statistischen Gleichlauf, nicht Ursache und Wirkung. Der Datenbestand wird nicht ergänzt oder interpoliert: Perioden ohne Wert in einer der beiden Reihen fehlen in der Auswertung." });
    return out;
  }

  /* ----- Modus Matrix ----- */
  const PRESETS = () => [
    ["VWL-Kernreihen Deutschland", () => V ? V.serien.filter(s => s.kern && V.daten[s.serie_id] && V.daten[s.serie_id].DE && !s.prognose_ab && !s.serie_id.startsWith("oecd_")).slice(0, 12).map(s => ({ typ: "vwl", a: s.serie_id, b: "DE" })) : []],
    ["Kurse der größten notierten Unternehmen", () => U ? U.kursFirmen.slice().sort((a, b) => (b.werte.marktkap || 0) - (a.werte.marktkap || 0)).slice(0, 10).map(f => ({ typ: "kurs", a: f.id, b: "" })) : []],
    ["Branchen-Kursindizes", () => U ? U.branchen.filter(b => U.kursFirmen.filter(f => f.branche === b.id).length >= MINF).slice(0, 12).map(b => ({ typ: "bkurs", a: b.id, b: "" })) : []],
    ["Kurse und Zinsen/Stimmung", () => { const l = []; if (V) for (const id of ["euribor_3m", "wirtschaftsstimmung", "hicp_gesamt"]) if (V.daten[id] && V.daten[id].DE) l.push({ typ: "vwl", a: id, b: "DE" }); if (U) l.push(...U.kursFirmen.slice().sort((a, b) => (b.werte.marktkap || 0) - (a.werte.marktkap || 0)).slice(0, 5).map(f => ({ typ: "kurs", a: f.id, b: "" }))); return l; }]];
  function viewMatrix() {
    const fOpt = [["auto", "Automatisch (gröbste Reihe)"], ["A", "Jahr"], ["Q", "Quartal"], ["M", "Monat"], ["D", "Tag"]];
    const sers = S.matrix.map(sp => ({ sp, s: resolve(sp) })).filter(x => x.s);
    const f = S.mFreq === "auto" ? (sers.length ? autoFreq(sers.map(x => x.s)) : "M") : S.mFreq;
    const prep = sers.map(x => ({ ...x, v: vorbereiten(x.sp, f, S.mTr, S.agg) }));
    const ok = prep.filter(x => !x.v.fehler && x.v.pts.length >= 3), weg = prep.filter(x => x.v.fehler || x.v.pts.length < 3);
    const kopf = `<div style="display:grid;gap:10px"><div class="ctrl">${PRESETS().map(([n], i) => `<button type="button" data-kpreset="${i}">${esc(n)}</button>`).join("")}<button type="button" class="mini" data-kmleer>Leeren</button></div>
      <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center"><b style="color:var(--amber)">+</b> ${slotUi("M", S.mNeu || (S.mNeu = vorgabe("vwl", 0)))}<button type="button" class="mini" data-kmadd>Hinzufügen</button></div>
      <div class="ctrl">${lab("Frequenz", sel("kmfreq", fOpt, S.mFreq, "Frequenz"))}${lab("Transformation", sel("kmtr", [["auto", "Automatisch je Reihe"], ...Object.entries(TRANS)], S.mTr, "Transformation"))}
        ${lab("Verfahren", sel("kmmeth", [["pearson", "Pearson r"], ["spearman", "Spearman ρ"]], S.mMeth, "Verfahren"))}</div>
      <div class="ctrl">${S.matrix.map((sp, i) => { const r = resolve(sp); return `<span class="chip">${i + 1} ${esc(r ? r.kurz : "keine Daten")}<button type="button" data-kmweg="${i}" aria-label="Entfernen">×</button></span>`; }).join("") || '<span>Noch keine Reihe gewählt. Voreinstellung oder einzelne Reihen hinzufügen.</span>'}</div></div>`;
    let out = panel({ code: "KOR 1", titel: "Matrix mehrerer Reihen", sub: "alle Paare gleichzeitig, jeweils auf den gemeinsamen Zeitraum der beiden Reihen", body: tabs() + kopf });
    if (ok.length < 2) return out + panel({ code: "KOR 2", titel: "Korrelationsmatrix", body: `<p style="margin:0;color:var(--ink-2)">Mindestens zwei Reihen mit je drei Werten nötig.${weg.length ? " Ausgeschlossen: " + weg.map(x => esc(x.s.kurz) + (x.v.fehler ? " (" + esc(x.v.fehler) + ")" : " (zu wenige Werte)")).join("; ") : ""}</p>` });
    const zellen = ok.map((a, i) => ok.map((b, j) => {
      if (i === j) return { r: 1, rho: 1, n: a.v.pts.length, p: 0, pRho: 0 };
      const rows = paare(a.v.pts, b.v.pts, f, 0, 0, 0); if (rows.length < 3) return { n: rows.length };
      const x = rows.map(r => r.a), y = rows.map(r => r.b), r = pearson(x, y), rho = spearman(x, y);
      return { r, rho, n: rows.length, p: pWert(r, rows.length), pRho: pWert(rho, rows.length) };
    }));
    const namen = ok.map(x => x.s.kurz), nmin = Math.min(...zellen.flatMap((r, i) => r.filter((c, j) => i !== j).map(c => c.n)));
    out += panel({ code: "KOR 2", titel: "Korrelationsmatrix", sub: `${S.mMeth === "spearman" ? "Spearman ρ" : "Pearson r"} · ${FNAME[f]} · ${ok.length} Reihen · Klick auf Zelle öffnet das Paar`,
      body: `<div style="overflow-x:auto">${heat(namen, zellen, S.mMeth, (i, j) => `data-kpaar="${i},${j}"`)}</div>${heatLegende}`,
      fuss: `Kleinste Zahl gemeinsamer Beobachtungen: n = ${isFinite(nmin) ? nmin : "n. v."}. Bei ${ok.length * (ok.length - 1) / 2} gleichzeitigen Tests ist mit zufälligen „signifikanten“ Paaren zu rechnen (p-Werte nicht für Mehrfachtests korrigiert, Richtwert Bonferroni: p &lt; ${fp(0.05 / (ok.length * (ok.length - 1) / 2))}).${weg.length ? " Nicht berücksichtigt: " + weg.map(x => esc(x.s.kurz) + (x.v.fehler ? " (" + esc(x.v.fehler) + ")" : "")).join("; ") + "." : ""}` });
    const warn = [];
    if (S.mTr === "niveau" && ok.some(x => x.s.art !== "rate" && x.s.art !== "saldo" && x.s.art !== "quote")) warn.push("Niveaus von Beständen, Indizes oder Kursen enthalten Trends: Scheinkorrelationen sind wahrscheinlich. „Automatisch“ verwendet Veränderungsraten.");
    if (nmin < 10) warn.push(`Mindestens ein Paar hat weniger als 10 gemeinsame Beobachtungen (kleinstes n = ${nmin}); diese Zellen sind kaum belastbar.`);
    if (ok.some(x => x.v.t === "yoy") && f !== "A") warn.push("Veränderungen zum Vorjahr aus Monats- oder Quartalswerten überlappen sich; p-Werte sind zu optimistisch.");
    if (ok.some(x => x.s.projektionen)) warn.push("Projektionen sind ausgeschlossen.");
    if (warn.length) out += panel({ code: "KOR 3", titel: "Hinweise zur Belastbarkeit", body: `<ul style="margin:0;padding-left:18px;display:grid;gap:6px">${warn.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` });
    return out;
  }

  /* ----- Modus Querschnitt ----- */
  function qsFirmen() { const q = S.qs; return U.firmen.filter(f => (q.bra === "alle" || f.branche === q.bra) && (q.not === "alle" || (q.not === "ja") === !!f.notiert)); }
  function qsKz(fs) {
    return Object.keys(U.kz).filter(k => fs.filter(f => f.werte && f.werte[k] != null && isFinite(f.werte[k])).length >= 8);
  }
  function qsPaare(fs, kx, ky, lx, ly) {
    const o = []; let drop = 0;
    for (const f of fs) {
      let a = f.werte && f.werte[kx], b = f.werte && f.werte[ky]; if (a == null || b == null || !isFinite(a) || !isFinite(b)) continue;
      if (lx) { if (a <= 0) { drop++; continue; } a = Math.log10(a); } if (ly) { if (b <= 0) { drop++; continue; } b = Math.log10(b); }
      o.push({ f, a, b });
    }
    return { o, drop };
  }
  function viewQuer() {
    if (!U) return panel({ code: "KOR 1", titel: "Querschnitt", body: tabs() + '<p style="margin:0;color:var(--ink-2)">Keine Unternehmensdaten geladen.</p>' });
    const q = S.qs, fs = qsFirmen(), ks = qsKz(fs);
    if (ks.length && !ks.includes(q.x)) q.x = ks[0]; if (ks.length > 1 && !ks.includes(q.y)) q.y = ks.find(k => k !== q.x);
    q.set = q.set.filter(k => ks.includes(k));
    const pa = qsPaare(fs, q.x, q.y, q.lx, q.ly), st = stat(pa.o.map(p => p.a), pa.o.map(p => p.b));
    const kzo = cur => ks.map(k => [k, U.kzName(k)]).map(([k, n]) => opt(k, n, k === cur)).join("");
    const kopf = `<div style="display:grid;gap:10px"><div class="ctrl">
      ${lab("Branche", `<select id="qbra">${opt("alle", "Alle Branchen", q.bra === "alle")}${U.branchen.map(b => opt(b.id, b.name, b.id === q.bra)).join("")}</select>`)}
      ${lab("Notierung", sel("qnot", [["alle", "alle"], ["ja", "börsennotiert"], ["nein", "nicht notiert"]], q.not, "Notierung"))}
      ${lab("Verfahren", sel("qmeth", [["pearson", "Pearson r"], ["spearman", "Spearman ρ"]], q.meth, "Verfahren"))}</div>
      <div class="ctrl">${lab('<b style="color:var(--amber)">X</b>', `<select id="qx">${kzo(q.x)}</select>`)}<label class="pct"><input type="checkbox" id="qlx"${q.lx ? " checked" : ""}> log₁₀</label>
        ${lab('<b style="color:var(--geno)">Y</b>', `<select id="qy">${kzo(q.y)}</select>`)}<label class="pct"><input type="checkbox" id="qly"${q.ly ? " checked" : ""}> log₁₀</label></div></div>`;
    let out = panel({ code: "KOR 1", titel: "Querschnitt über Unternehmen", sub: `${fs.length} Unternehmen im Filter · zwei Kennzahlen gegeneinander, jeweils letzter erhobener Stand`, body: tabs() + kopf });
    if (ks.length < 2) return out + panel({ code: "KOR 2", titel: "Auswertung", body: '<p style="margin:0;color:var(--ink-2)">Im Filter haben weniger als zwei Kennzahlen mindestens 8 Werte.</p>' });
    const prim = q.meth === "spearman" ? st.rho : st.r, pp2 = q.meth === "spearman" ? st.pRho : st.p;
    out += panel({ code: "KOR 2", titel: "Kennzahlen der Korrelation", sub: `${esc(U.kzName(q.x))} ↔ ${esc(U.kzName(q.y))} · n = ${st.n} Unternehmen`,
      body: st.n >= 3 && st.r != null ? `<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px">
        ${[[q.meth === "spearman" ? "Spearman ρ" : "Pearson r", fr(prim), ""], [q.meth === "spearman" ? "Pearson r" : "Spearman ρ", fr(q.meth === "spearman" ? st.r : st.rho), ""], ["p-Wert", fp(pp2), "zweiseitig"], ["95-%-Intervall (r)", st.ci ? `${fr(st.ci[0])} … ${fr(st.ci[1])}` : "n. v.", "Fisher-z"], ["R²", fr(st.r * st.r), ""], ["n", String(st.n), pa.drop ? pa.drop + " ohne positiven Wert für log" : ""]]
          .map(([n, v, s2]) => `<div class="tile" style="--gf:var(--amber)"><div class="g"><b>${n}</b></div><div class="stats"><div><strong>${v}</strong></div></div><div class="pct" style="padding:0 0 2px">${s2 || "&nbsp;"}</div></div>`).join("")}</div>` : `<p style="margin:0;color:var(--ink-2)">Keine Auswertung möglich (n = ${st.n}).</p>`,
      fuss: "Querschnittskorrelation: ein Wert je Unternehmen. Größenkennzahlen (Börsenwert, Umsatz, Bilanzsumme) sind stark rechtsschief; dafür log₁₀ oder Spearman wählen. Verschiedene Rechnungslegung und Währungen sind nicht bereinigt; Quoten und Multiplikatoren sind vergleichbarer als Beträge." });
    if (st.n >= 3) {
      const pts = pa.o.map(p => ({ x: p.a, y: p.b, href: "#firma-" + p.f.id, tip: `<b>${esc(p.f.name)}</b>\n${esc(U.brName(p.f.branche))}\n${esc(U.kzName(q.x))}: ${fz(p.f.werte[q.x])}\n${esc(U.kzName(q.y))}: ${fz(p.f.werte[q.y])}\nKlick: Profil` }));
      out += panel({ code: "KOR 3", titel: "Streudiagramm", sub: "Klick auf einen Punkt öffnet das Unternehmensprofil", body: streu(pts, st, U.kzName(q.x) + (q.lx ? " (log₁₀)" : ""), U.kzName(q.y) + (q.ly ? " (log₁₀)" : ""), { href: true }) });
      const h = [];
      if (st.n < 30) h.push(`Wenige Unternehmen (n = ${st.n}): Koeffizient unsicher.`);
      if (st.r != null && st.rho != null && Math.abs(st.r - st.rho) > .2) h.push(`Pearson (${fr(st.r)}) und Spearman (${fr(st.rho)}) weichen stark ab: Ausreißer prägen das Ergebnis, log₁₀ oder Spearman verwenden.`);
      if (q.bra === "alle") h.push("Über alle Branchen gemischt kann ein Zusammenhang nur zwischen den Branchen bestehen (Simpson-Paradox). Auf eine Branche einschränken und vergleichen.");
      h.push("Die Streuung zeigt Gleichlauf zwischen Unternehmen zu einem Stichtag, keine zeitliche Abhängigkeit.");
      out += panel({ code: "KOR 4", titel: "Hinweise zur Belastbarkeit", body: `<ul style="margin:0;padding-left:18px;display:grid;gap:6px">${h.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` });
    }
    /* Matrix über mehrere Kennzahlen */
    const set = q.set, zellen = set.map(a => set.map(b => {
      if (a === b) return { r: 1, rho: 1, n: 0, p: 0, pRho: 0 };
      const pp = qsPaare(fs, a, b, false, false).o, x = pp.map(p => p.a), y = pp.map(p => p.b); if (pp.length < 3) return { n: pp.length };
      const r = pearson(x, y), rho = spearman(x, y); return { r, rho, n: pp.length, p: pWert(r, pp.length), pRho: pWert(rho, pp.length) };
    }));
    out += panel({ code: "KOR 5", titel: "Korrelationsmatrix der Kennzahlen", sub: "alle Paare im gewählten Filter; Klick auf Zelle übernimmt das Paar nach oben",
      body: `<div class="ctrl" style="margin-bottom:10px">${set.map((k, i) => `<span class="chip">${i + 1} ${esc(U.kzName(k))}<button type="button" data-kqweg="${k}" aria-label="Entfernen">×</button></span>`).join("")}
        <select id="qadd" aria-label="Kennzahl hinzufügen"><option value="">+ Kennzahl</option>${ks.filter(k => !set.includes(k)).map(k => opt(k, U.kzName(k))).join("")}</select></div>
        ${set.length >= 2 ? `<div style="overflow-x:auto">${heat(set.map(k => U.kzName(k)), zellen, q.meth, (i, j) => `data-kqpaar="${set[i]},${set[j]}"`)}</div>${heatLegende}` : '<p style="margin:0;color:var(--ink-2)">Mindestens zwei Kennzahlen wählen.</p>'}`,
      fuss: "Jedes Paar nutzt alle Unternehmen, für die beide Kennzahlen vorliegen; n steht im Tooltip. Mehrfachtests sind nicht korrigiert." });
    return out;
  }

  /* ======================= Ansicht und Ereignisse ======================= */
  function viewKorr() {
    init();
    if (!V && !U) return panel({ code: "KOR", titel: "Korrelation", body: '<p style="margin:0;color:var(--ink-2)">Keine Daten geladen.</p>' });
    return S.modus === "matrix" ? viewMatrix() : S.modus === "quer" && U ? viewQuer() : viewPaar();
  }
  function slotRef(id) { return id === "A" ? "A" : id === "B" ? "B" : "mNeu"; }
  function nachRender() {
    const bind = (id, fn) => { const e = document.getElementById(id); if (e) e.addEventListener("change", () => fn(e.type === "checkbox" ? e.checked : e.value)); };
    bind("kfreq", v => { S.freq = v; render(); }); bind("ktrA", v => { S.trA = v; render(); }); bind("ktrB", v => { S.trB = v; render(); });
    bind("kagg", v => { S.agg = v; render(); }); bind("kvon", v => { S.von = v; render(); }); bind("kbis", v => { S.bis = v; render(); });
    bind("klag", v => { S.lag = +v; render(); }); bind("kmeth", v => { S.methode = v; render(); });
    bind("kmfreq", v => { S.mFreq = v; render(); }); bind("kmtr", v => { S.mTr = v; render(); }); bind("kmmeth", v => { S.mMeth = v; render(); });
    bind("qbra", v => { S.qs.bra = v; render(); }); bind("qnot", v => { S.qs.not = v; render(); }); bind("qmeth", v => { S.qs.meth = v; render(); });
    bind("qx", v => { S.qs.x = v; render(); }); bind("qy", v => { S.qs.y = v; render(); }); bind("qlx", v => { S.qs.lx = v; render(); }); bind("qly", v => { S.qs.ly = v; render(); });
    bind("qadd", v => { if (v && !S.qs.set.includes(v)) S.qs.set.push(v); render(); });
    document.querySelectorAll("[data-kf]").forEach(e => e.addEventListener("change", () => {
      const id = e.closest("[data-slot]").dataset.slot, key = slotRef(id);
      S[key] = slotAender(S[key], e.dataset.kf, e.value); S.lag = 0; render();
    }));
  }
  function klick(t) {
    const c = s => t.closest(s);
    if (c("[data-kmodus]")) { S.modus = c("[data-kmodus]").dataset.kmodus; render(); return true; }
    if (c("[data-klag]")) { S.lag = +c("[data-klag]").dataset.klag; render(); return true; }
    if (c("[data-ktausch]")) { [S.A, S.B] = [S.B, S.A]; [S.trA, S.trB] = [S.trB, S.trA]; S.lag = -S.lag; render(); return true; }
    if (c("[data-kpreset]")) { const l = PRESETS()[+c("[data-kpreset]").dataset.kpreset][1](); S.matrix = l.filter(sp => resolve(sp)); render(); return true; }
    if (c("[data-kmleer]")) { S.matrix = []; render(); return true; }
    if (c("[data-kmadd]")) { const sp = S.mNeu; if (sp && resolve(sp) && !S.matrix.some(x => x.typ === sp.typ && x.a === sp.a && x.b === sp.b) && S.matrix.length < 14) S.matrix.push({ ...sp }); render(); return true; }
    if (c("[data-kmweg]")) { S.matrix.splice(+c("[data-kmweg]").dataset.kmweg, 1); render(); return true; }
    if (c("[data-kqweg]")) { S.qs.set = S.qs.set.filter(k => k !== c("[data-kqweg]").dataset.kqweg); render(); return true; }
    if (c("[data-kpaar]")) {
      const [i, j] = c("[data-kpaar]").dataset.kpaar.split(",").map(Number), ok = S.matrix.map(sp => ({ sp, s: resolve(sp) })).filter(x => x.s);
      const f = S.mFreq === "auto" ? autoFreq(ok.map(x => x.s)) : S.mFreq;
      const g = ok.filter(x => { const v = vorbereiten(x.sp, f, S.mTr, S.agg); return !v.fehler && v.pts.length >= 3; });
      if (g[i] && g[j]) { S.A = { ...g[i].sp }; S.B = { ...g[j].sp }; S.freq = S.mFreq; S.trA = S.trB = S.mTr; S.lag = 0; S.methode = S.mMeth; S.modus = "paar"; render(); scrollTo(0, 0); }
      return true;
    }
    if (c("[data-kqpaar]")) { const [x, y] = c("[data-kqpaar]").dataset.kqpaar.split(","); S.qs.x = x; S.qs.y = y; S.qs.lx = S.qs.ly = false; render(); scrollTo(0, 0); return true; }
    return false;
  }
  /* Einstieg von außen: zwei Reihen vorbelegen (z. B. aus einer Profilseite) */
  function setze(a, b) { init(); if (a) S.A = a; if (b) S.B = b; S.modus = "paar"; S.lag = 0; }
  const meta = () => { init(); return [V ? `${V.serien.length} VWL-Reihen` : "", U ? `${U.zr.length} Unternehmen mit Jahresreihen · ${U.kursFirmen.length} mit Kursen` : ""].filter(Boolean).join(" · "); };
  return { viewKorr, nachRender, klick, setze, meta, stat, pearson, spearman, pWert };
})();
