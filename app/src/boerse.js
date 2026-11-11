/* ---------- Börsendaten: Indizes (Welt, OECD, Nicht-OECD) und große Unternehmen weltweit ----------
   Daten: BD = { abruf, quelle, wochen[], indizes[], unternehmen[], ohne_kurse } (siehe boersen_abruf.py, Quelle Yahoo Finance).
   Je Eintrag: kurs, datum, r1t/r1w/r1m/r3m/ytd/r1j/r3j/r5j/r10j (Veränderung als Bruch), hoch52, tief52, t[] (Wochenschlusskurse passend zu wochen[]),
   bei Unternehmen boerswert (Mrd. USD), sektor, land, id (nur wenn das Unternehmen in stammdaten/ steht).
   Auswahlschlüssel im Verlauf: "i:<id>" für Indizes, "u:<symbol>" für Unternehmen.
   Läuft vor dem Hauptskript; nutzt dessen Hilfsfunktionen (panel, esc, f0, f1, f2, sicherUrl) erst zur Laufzeit. */
"use strict";
const BOE = (() => {
  let BD = null, IND = {}, UNT = {};
  const S = { gruppe: "alle", region: "alle", isort: { k: "ytd", ab: false }, land: "alle", sektor: "alle", usort: { k: "boerswert", ab: false }, suche: "", sel: [], fenster: "5", log: false };
  const GRUPPEN = [["Welt", "Weltindizes"], ["OECD", "OECD-Länder"], ["Nicht-OECD", "Schwellen- und Entwicklungsländer"]];
  const PAL = ["#ffa828", "#2f86dd", "#17a88a", "#9a6fe0", "#e8484f", "#3ecf6e", "#e07fb0", "#5ec8d8", "#b4c24a", "#c0714a"];
  const FENSTER = { "1": "1 J.", "3": "3 J.", "5": "5 J.", "10": "10 J." };
  const PRESETS = [
    ["Leitindizes", ["i:^GDAXI", "i:^GSPC", "i:^N225", "i:^FTSE", "i:^HSI"]],
    ["Weltindizes", ["i:^990100-USD-STRD", "i:^892400-USD-STRD", "i:^891800-USD-STRD"]],
    ["Schwellenländer", ["i:^BVSP", "i:^BSESN", "i:000001.SS", "i:^TWII", "i:^J203.JO"]],
    ["Europa", ["i:^GDAXI", "i:^FCHI", "i:^FTSE", "i:^STOXX50E", "i:^SSMI"]],
    ["US-Technologie", ["u:AAPL", "u:MSFT", "u:NVDA", "u:GOOGL", "u:AMZN", "u:META"]],
    ["DAX-Schwergewichte", ["u:SAP.DE", "u:SIE.DE", "u:ALV.DE", "u:DTE.DE", "u:MBG.DE"]]];
  const pos = v => v == null ? "" : v > 0 ? "pos" : v < 0 ? "neg" : "";
  const chg = v => v == null ? "–" : (v > 0 ? "+" : "") + f1.format(v * 100) + " %";
  const kursF = v => v == null ? "–" : (Math.abs(v) >= 1000 ? f0 : f2).format(v);
  const datumDe = d => (d || "").split("-").reverse().join(".");
  const holen = k => k.startsWith("i:") ? IND[k.slice(2)] : UNT[k.slice(2)];
  const gueltig = k => !!holen(k);

  function init(d) {
    BD = d && d.indizes && d.indizes.length ? d : null;
    if (!BD) return false;
    IND = Object.fromEntries(BD.indizes.map(x => [x.id, x]));
    UNT = Object.fromEntries(BD.unternehmen.map(x => [x.symbol, x]));
    S.sel = PRESETS[0][1].filter(gueltig);
    if (!S.sel.length) S.sel = BD.indizes.slice(0, 4).map(x => "i:" + x.id);
    return true;
  }
  const da = () => !!BD;
  const meta = () => BD ? `${BD.indizes.length} Indizes · ${BD.unternehmen.length} Unternehmen · Yahoo Finance, Stand ${datumDe((BD.abruf || "").slice(0, 10))}` : "";

  /* ----- Bausteine ----- */
  const spark = (t, farbe, n = 52) => {
    const w = t.slice(-n).filter(v => v != null);
    if (w.length < 3) return "";
    const lo = Math.min(...w), hi = Math.max(...w), W = 84, H = 22;
    const p = w.map((v, i) => (i ? "L" : "M") + (i / (w.length - 1) * W).toFixed(1) + " " + (H - 2 - (v - lo) / (hi - lo || 1) * (H - 4)).toFixed(1)).join("");
    return `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" aria-hidden="true"><path d="${p}" fill="none" stroke="${farbe}" stroke-width="1.4" stroke-linejoin="round"/></svg>`;
  };
  const sparkF = x => spark(x.t, x.ytd == null || x.ytd >= 0 ? "var(--up)" : "var(--down)");
  const spanne = x => {
    if (x.hoch52 == null || x.tief52 == null || x.hoch52 === x.tief52) return "";
    const p = Math.max(0, Math.min(1, (x.kurs - x.tief52) / (x.hoch52 - x.tief52)));
    return `<div title="52-Wochen-Spanne: ${kursF(x.tief52)} bis ${kursF(x.hoch52)}" style="position:relative;width:90px;height:6px;background:var(--line);border-radius:3px;display:inline-block;vertical-align:middle"><i style="position:absolute;left:calc(${(p * 100).toFixed(0)}% - 3px);top:-2px;width:6px;height:10px;background:var(--amber);border-radius:2px"></i></div>`;
  };
  const chips = (items, attr, aktiv) => `<div class="ctrl" style="margin-bottom:10px">${items.map(([id, n]) => `<button type="button" ${attr}="${esc(id)}" aria-pressed="${id === aktiv}">${esc(n)}</button>`).join("")}</div>`;
  const kopf = (liste, art, st) => liste.map(([k, n, links]) => `<th${links ? ' style="text-align:left"' : ""}><button type="button" class="sortbtn" data-bsort="${art}:${k}" style="background:none;border:0;color:inherit;cursor:pointer;font:inherit;padding:0">${esc(n)}${st.k === k ? (st.ab ? " ▲" : " ▼") : ""}</button></th>`).join("");
  const sortiere = (arr, st) => arr.slice().sort((a, b) => {
    const x = a[st.k], y = b[st.k];
    if (typeof x === "string" || typeof y === "string") return (st.ab ? 1 : -1) * String(x || "").localeCompare(String(y || ""), "de");
    if (x == null && y == null) return 0;
    if (x == null) return 1;
    if (y == null) return -1;
    return st.ab ? x - y : y - x;
  });
  const plus = k => `<button type="button" class="btn" data-bplus="${esc(k)}" title="In den Verlauf übernehmen" style="padding:0 7px">+</button>`;
  const rendZellen = x => ["r1t", "r1m", "ytd", "r1j", "r5j"].map(k => `<td class="${pos(x[k])}">${chg(x[k])}</td>`).join("");

  /* ----- F1 Überblick ----- */
  function kachel(x, art) {
    return `<a href="#b-verlauf" data-bplus="${art}:${esc(art === "i" ? x.id : x.symbol)}" style="display:grid;gap:2px;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--panel-2);color:inherit;text-decoration:none">
      <span class="n" style="font-size:11px">${esc(x.name)}</span><b style="font:600 18px var(--mono)">${kursF(x.kurs)}</b>
      <span style="display:flex;justify-content:space-between;align-items:center;gap:6px"><span class="${pos(x.r1t)}" style="font:12px var(--mono);white-space:nowrap">${chg(x.r1t)}</span>${sparkF(x)}</span>
      <span class="n" style="font-size:11px">seit Jahresbeginn <span class="${pos(x.ytd)}">${chg(x.ytd)}</span></span></a>`;
  }
  function laenderKacheln() {
    return GRUPPEN.map(([g, n]) => {
      const nachLand = new Map();
      BD.indizes.filter(x => x.gruppe === g && x.land && x.ytd != null).forEach(x => { if (!nachLand.has(x.land)) nachLand.set(x.land, x); });
      const l = [...nachLand.values()].sort((a, b) => b.ytd - a.ytd);
      if (!l.length) return "";
      const farbe = v => { const a = Math.min(.55, Math.abs(v) * 1.2 + .08); return v >= 0 ? `rgba(62,207,110,${a})` : `rgba(255,82,72,${a})`; };
      return `<h3 style="margin:14px 0 8px;font:600 13px var(--sans);color:var(--ink-2)">${esc(n)} <span class="n">(${l.length} Länder, jeweils Leitindex)</span></h3>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:6px">${l.map(x => `<a href="#b-verlauf" data-bplus="i:${esc(x.id)}" title="${esc(x.name)}" style="display:grid;padding:7px 9px;border-radius:6px;background:${farbe(x.ytd)};color:inherit;text-decoration:none;border:1px solid var(--line)"><span style="font-size:12px">${esc(x.land)}</span><b style="font:600 13px var(--mono)">${chg(x.ytd)}</b><span class="n" style="font-size:10px">${esc(x.name)}</span></a>`).join("")}</div>`;
    }).join("");
  }
  function extrem(liste, art, k, n) {
    const l = liste.filter(x => x[k] != null).sort((a, b) => b[k] - a[k]);
    const z = x => `<tr class="click"><td style="text-align:left;font-family:var(--sans)"><a class="flink" href="#b-verlauf" data-bplus="${art}:${esc(art === "i" ? x.id : x.symbol)}">${esc(x.name)}</a> <span class="n">${esc(x.land || "")}</span></td><td class="${pos(x[k])}">${chg(x[k])}</td></tr>`;
    return `<div class="scroll"><table class="kzt"><tbody>${l.slice(0, n).map(z).join("")}<tr><td colspan="2" class="n" style="text-align:center">…</td></tr>${l.slice(-n).reverse().map(z).join("")}</tbody></table></div>`;
  }
  function viewUeb() {
    if (!BD) return keineDaten();
    const wi = BD.indizes.filter(x => x.gruppe === "Welt" && x.kurs != null && !/VIX|ETF/.test(x.name)).slice(0, 4);
    const lei = ["^GDAXI", "^GSPC", "^N225", "^HSI", "^FTSE", "^FCHI", "^BSESN", "^BVSP"].map(id => IND[id]).filter(Boolean);
    const puls = typeof FNZ !== "undefined" && FNZ.da() ? panel({ code: "PLS", titel: "Marktpuls", sub: "Angst, Zinsabstand, Gold, Öl, Euro, Bitcoin", body: FNZ.leiste(), fuss: FNZ.leisteFuss() + " " + FNZ.leisteLive() + " Mehr unter F8 bis F11." }) : "";
    return `<div class="grid">
      ${puls}
      ${panel({ code: "BÖR", titel: "Leitindizes", sub: "Stand, Tagesveränderung und Verlauf des letzten Jahres", body: `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:8px">${wi.concat(lei).map(x => kachel(x, "i")).join("")}</div>`, fuss: `Klick auf eine Kachel übernimmt den Index in den Verlauf (F4). Quelle Yahoo Finance, Stand ${datumDe((BD.abruf || "").slice(0, 10))}; Kurse verzögert und ohne Gewähr.` })}
      ${panel({ code: "LND", titel: "Länder seit Jahresbeginn", sub: "Leitindex je Land, Farbe = Veränderung seit Jahresbeginn in Landeswährung", body: laenderKacheln() })}
      ${panel({ code: "TOP", titel: "Indizes: Gewinner und Verlierer", sub: "seit Jahresbeginn", breite: "w6", body: extrem(BD.indizes, "i", "ytd", 6) })}
      ${panel({ code: "TOP", titel: "Unternehmen: Gewinner und Verlierer", sub: "seit Jahresbeginn", breite: "w6", body: extrem(BD.unternehmen, "u", "ytd", 6) })}</div>`;
  }

  /* ----- F2 Indizes ----- */
  function viewInd() {
    if (!BD) return keineDaten();
    const regionen = [...new Set(BD.indizes.filter(x => S.gruppe === "alle" || x.gruppe === S.gruppe).map(x => x.region))].sort();
    if (S.region !== "alle" && !regionen.includes(S.region)) S.region = "alle";
    const l = sortiere(BD.indizes.filter(x => (S.gruppe === "alle" || x.gruppe === S.gruppe) && (S.region === "alle" || x.region === S.region)), S.isort);
    const spalten = [["name", "Index", 1], ["land", "Land", 1], ["kurs", "Stand"], ["r1t", "1 T."], ["r1m", "1 Mon."], ["ytd", "YTD"], ["r1j", "1 J."], ["r5j", "5 J."], ["r10j", "10 J."]];
    const tab = `<div class="scroll"><table class="kzt"><thead><tr>${kopf(spalten, "i", S.isort)}<th>52-Wochen-Spanne</th><th>Verlauf 1 J.</th><th></th></tr></thead><tbody>${l.map(x => `<tr>
      <td style="text-align:left;font-family:var(--sans)"><a class="flink" href="#b-verlauf" data-bplus="i:${esc(x.id)}">${esc(x.name)}</a></td><td class="n" style="text-align:left;font-family:var(--sans)">${esc(x.land || (x.gruppe === "Welt" ? "Welt" : ""))}</td>
      <td>${kursF(x.kurs)}</td>${["r1t", "r1m", "ytd", "r1j", "r5j", "r10j"].map(k => `<td class="${pos(x[k])}">${chg(x[k])}</td>`).join("")}<td>${spanne(x)}</td><td>${sparkF(x)}</td><td>${plus("i:" + x.id)}</td></tr>`).join("")}</tbody></table></div>`;
    return `<div class="grid">${panel({
      code: "IDX", titel: "Aktienindizes", sub: `${l.length} von ${BD.indizes.length} Indizes`,
      body: chips([["alle", "Alle"], ...GRUPPEN], "data-bgruppe", S.gruppe) + chips([["alle", "Alle Regionen"], ...regionen.map(r => [r, r])], "data-bregion", S.region) + tab,
      fuss: `Veränderungen in Landeswährung des Index, ohne Dividenden (Kursindizes; DAX ist ein Performanceindex). 5 und 10 Jahre gelten nur, wo Yahoo so weit zurückreicht. ${BD.ohne_kurse && BD.ohne_kurse.indizes.length ? `Ohne frei verfügbare Kurse: ${esc(BD.ohne_kurse.indizes.join(", "))}.` : ""}`
    })}</div>`;
  }

  /* ----- F3 Unternehmen ----- */
  function viewUnt() {
    if (!BD) return keineDaten();
    const laender = [...new Set(BD.unternehmen.map(x => x.land))].sort((a, b) => a.localeCompare(b, "de")), sektoren = [...new Set(BD.unternehmen.map(x => x.sektor))].sort((a, b) => a.localeCompare(b, "de"));
    const q = S.suche.trim().toLowerCase();
    const l = sortiere(BD.unternehmen.filter(x => (S.land === "alle" || x.land === S.land) && (S.sektor === "alle" || x.sektor === S.sektor) && (!q || x.name.toLowerCase().includes(q) || x.symbol.toLowerCase().includes(q))), S.usort);
    const spalten = [["name", "Unternehmen", 1], ["land", "Land", 1], ["sektor", "Sektor", 1], ["boerswert", "Börsenwert Mrd. USD"], ["kurs", "Kurs"], ["r1t", "1 T."], ["r1m", "1 Mon."], ["ytd", "YTD"], ["r1j", "1 J."], ["r5j", "5 J."]];
    const tab = `<div class="scroll"><table class="kzt"><thead><tr>${kopf(spalten, "u", S.usort)}<th>52-Wochen-Spanne</th><th>Verlauf 1 J.</th><th></th></tr></thead><tbody>${l.map(x => `<tr>
      <td style="text-align:left;font-family:var(--sans)"><a class="flink" href="#b-verlauf" data-bplus="u:${esc(x.symbol)}">${esc(x.name)}</a> <span class="n">${esc(x.symbol)}</span>${x.id ? ` <a class="flink" href="#firma-${esc(x.id)}" title="Profilseite mit Kennzahlen und Dokumenten">Profil</a>` : ""}</td>
      <td class="n" style="text-align:left;font-family:var(--sans)">${esc(x.land)}</td><td class="n" style="text-align:left;font-family:var(--sans)">${esc(x.sektor)}</td><td>${x.boerswert == null ? "–" : (x.boerswert >= 100 ? f0 : f1).format(x.boerswert)}</td>
      <td>${kursF(x.kurs)} <span class="n">${esc(x.waehrung || "")}</span></td>${rendZellen(x)}<td>${spanne(x)}</td><td>${sparkF(x)}</td><td>${plus("u:" + x.symbol)}</td></tr>`).join("")}</tbody></table></div>`;
    const ctrl = `<div class="ctrl" style="margin-bottom:10px"><input id="bsuche" type="search" placeholder="Name oder Symbol …" value="${esc(S.suche)}" style="background:var(--field);border:1px solid var(--line);border-radius:8px;padding:4px 10px">
      <select id="bland" aria-label="Land"><option value="alle">Alle Länder</option>${laender.map(x => `<option${x === S.land ? " selected" : ""}>${esc(x)}</option>`).join("")}</select>
      <select id="bsektor" aria-label="Sektor"><option value="alle">Alle Sektoren</option>${sektoren.map(x => `<option${x === S.sektor ? " selected" : ""}>${esc(x)}</option>`).join("")}</select></div>`;
    return `<div class="grid">${panel({
      code: "UNT", titel: "Große Unternehmen weltweit", sub: `${l.length} von ${BD.unternehmen.length} Unternehmen`, body: ctrl + tab,
      fuss: `Auswahl nach Börsenwert und Bekanntheit, kein Index. Kurse in Börsenwährung (Londoner in Pence), Börsenwert mit Yahoo-Wechselkursen in US-Dollar umgerechnet. Unternehmen mit „Profil“ stehen auch in den Unternehmenskennzahlen. ${BD.ohne_kurse && BD.ohne_kurse.unternehmen.length ? `Ohne frei verfügbare Kurse: ${esc(BD.ohne_kurse.unternehmen.join(", "))}.` : ""}`
    })}</div>`;
  }

  /* ----- F4 Verlauf ----- */
  const nice = (lo, hi) => {
    const s = (hi - lo) / 5 || 1, z = Math.pow(10, Math.floor(Math.log10(s))), m = s / z, st = (m <= 1 ? 1 : m <= 2 ? 2 : m <= 5 ? 5 : 10) * z;
    const a = Math.floor(lo / st) * st, b = Math.ceil(hi / st) * st, tk = [];
    for (let v = a; v <= b + st / 2; v += st) tk.push(+v.toFixed(6));
    return { a, b, tk };
  };
  function verlauf() {
    const items = S.sel.filter(gueltig).map(k => ({ k, x: holen(k) }));
    if (!items.length) return `<p class="n">Noch nichts ausgewählt.</p>`;
    const W = BD.wochen, letzt = new Date(W[W.length - 1]), grenze = new Date(letzt); grenze.setFullYear(grenze.getFullYear() - +S.fenster);
    const i0 = Math.max(0, W.findIndex(d => new Date(d) >= grenze));
    const reihen = items.map((it, n) => {
      const t = it.x.t.slice(i0), b = t.find(v => v != null);
      return { name: it.x.name, farbe: PAL[n % PAL.length], y: t.map(v => v == null || !b ? null : v / b * 100) };
    });
    const alle = reihen.flatMap(r => r.y.filter(v => v != null));
    if (!alle.length) return `<p class="n">Für das Fenster liegen keine Kurse vor.</p>`;
    const f = S.log ? Math.log : (v => v), lo = f(Math.min(...alle)), hi = f(Math.max(...alle));
    const eng = innerWidth < 640, Wd = eng ? 430 : 900, H = eng ? 300 : 380, L = 46, R = 14, T = 12, B = 28, n = W.length - i0;
    const tk = S.log ? (() => { const r = []; for (let v = Math.pow(10, Math.floor(Math.log10(Math.min(...alle)))); v <= Math.max(...alle) * 2; v *= 10) [1, 2, 5].forEach(m => { const w = v * m; if (w >= Math.min(...alle) * .8 && w <= Math.max(...alle) * 1.25) r.push(w); }); return r; })() : nice(lo, hi).tk;
    const ya = S.log ? lo - .03 : Math.min(lo, tk[0]), yb = S.log ? hi + .03 : Math.max(hi, tk[tk.length - 1]);
    const X = i => L + i / (n - 1 || 1) * (Wd - L - R), Y = v => T + (1 - (f(v) - ya) / (yb - ya || 1)) * (H - T - B);
    let h = `<svg viewBox="0 0 ${Wd} ${H}" role="img" aria-label="Kursverlauf, indexiert auf 100">`;
    tk.forEach(v => { h += `<line x1="${L}" x2="${Wd - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="${v === 100 ? "var(--ink-3)" : "var(--grid)"}"/><text x="${L - 8}" y="${Y(v) + 4}" text-anchor="end" style="font-family:var(--mono);font-size:10px">${f0.format(v)}</text>`; });
    let vj = null;
    for (let i = 0; i < n; i++) { const j = +W[i0 + i].slice(0, 4); if (j !== vj) { vj = j; if (i > n * .03) h += `<line x1="${X(i)}" x2="${X(i)}" y1="${T}" y2="${H - B}" stroke="var(--grid)"/><text x="${X(i)}" y="${H - 8}" text-anchor="middle" style="font-size:10px">${j}</text>`; } }
    reihen.forEach(r => {
      const p = r.y.map((v, i) => v == null ? null : [i, v]).filter(Boolean);
      h += `<path d="${p.map((q, i) => (i ? "L" : "M") + X(q[0]).toFixed(1) + " " + Y(q[1]).toFixed(1)).join("")}" fill="none" stroke="${r.farbe}" stroke-width="1.7" stroke-linejoin="round"/>`;
      if (p.length) h += `<circle cx="${X(p[p.length - 1][0])}" cy="${Y(p[p.length - 1][1])}" r="3" fill="${r.farbe}"/>`;
    });
    const bw = Math.max(2, (Wd - L - R) / n);
    for (let i = 0; i < n; i++) {
      const z = reihen.map(r => r.y[i] == null ? null : `<span style="color:${r.farbe}">${esc(r.name)}</span> ${f1.format(r.y[i])}`).filter(Boolean);
      h += `<rect x="${X(i) - bw / 2}" y="${T}" width="${bw}" height="${H - T - B}" fill="transparent" data-tip="${esc(`<b>Woche ab ${datumDe(W[i0 + i])}</b>\n${z.join("\n")}`)}"/>`;
    }
    const leg = `<div class="legend">${items.map((it, n2) => `<span><i class="sw" style="background:${PAL[n2 % PAL.length]}"></i>${esc(it.x.name)} <button type="button" data-bweg="${esc(it.k)}" title="Entfernen" style="background:none;border:0;color:var(--ink-3);cursor:pointer">×</button></span>`).join("")}</div>`;
    return h + "</svg>" + leg;
  }
  function viewVerlauf() {
    if (!BD) return keineDaten();
    const opt = (liste, art, id, nm) => liste.filter(x => !S.sel.includes(art + ":" + x[id])).map(x => `<option value="${art}:${esc(x[id])}">${esc(x[nm])}${x.land ? " (" + esc(x.land) + ")" : ""}</option>`).join("");
    const add = `<select id="badd" aria-label="Hinzufügen"><option value="">Index oder Unternehmen hinzufügen …</option>
      ${GRUPPEN.map(([g, n]) => `<optgroup label="${esc(n)}">${opt(BD.indizes.filter(x => x.gruppe === g), "i", "id", "name")}</optgroup>`).join("")}
      <optgroup label="Unternehmen">${opt(BD.unternehmen, "u", "symbol", "name")}</optgroup></select>`;
    const ctl = `<div class="ctrl" style="margin-bottom:8px">${add}<span>Fenster</span>${Object.entries(FENSTER).map(([k, n]) => `<button type="button" data-bfen="${k}" aria-pressed="${S.fenster === k}">${n}</button>`).join("")}
      <button type="button" data-blog aria-pressed="${S.log}">Log. Skala</button></div>
      <div class="ctrl" style="margin-bottom:10px"><span>Schnellwahl</span>${PRESETS.map(([n]) => `<button type="button" data-bpreset="${esc(n)}">${esc(n)}</button>`).join("")}</div>`;
    const sel = S.sel.filter(gueltig).map(k => holen(k));
    const tab = `<div class="scroll"><table class="kzt"><thead><tr><th style="text-align:left">Auswahl</th><th>Stand</th><th>1 T.</th><th>1 Mon.</th><th>YTD</th><th>1 J.</th><th>5 J.</th><th>10 J.</th></tr></thead><tbody>${sel.map(x => `<tr><td style="text-align:left;font-family:var(--sans)">${esc(x.name)}</td><td>${kursF(x.kurs)}</td>${["r1t", "r1m", "ytd", "r1j", "r5j", "r10j"].map(k => `<td class="${pos(x[k])}">${chg(x[k])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
    return `<div class="grid">${panel({ code: "VLF", titel: "Kursverlauf", sub: `auf 100 indexiert, Wochenschlusskurse, bis zu ${Math.round(BD.wochen.length / 52)} Jahre`, body: ctl + verlauf(), fuss: "Indexiert auf den ersten Kurs im Fenster, damit Indizes und Unternehmen in verschiedenen Währungen vergleichbar sind (Landeswährung, keine Wechselkursbereinigung). Wochenkurse von Yahoo Finance." })}
      ${panel({ code: "KZ", titel: "Kennzahlen der Auswahl", sub: "Veränderung in Landeswährung", body: tab })}</div>`;
  }

  /* ----- F5 Quellen ----- */
  function viewQuellen() {
    if (!BD) return keineDaten();
    const o = BD.ohne_kurse || { indizes: [], unternehmen: [] };
    return `<div class="grid">${panel({
      code: "QUE", titel: "Quellen und Stand", sub: "frei verfügbare Daten, keine kostenpflichtigen Dienste", body: `
      <p>Kurse: <a class="flink" href="https://finance.yahoo.com/" target="_blank" rel="noopener">Yahoo Finance</a> über die freie Bibliothek yfinance. Abruf per GitHub-Workflow (Yahoo sperrt Abrufe aus manchen Cloud-Umgebungen), werktags nach Handelsschluss; Skript <code>app/boersen_abruf.py</code>, Katalog <code>app/boersen_katalog.json</code>.</p>
      <p class="n">Abruf: ${esc(BD.abruf)} · ${BD.indizes.length} Indizes (${GRUPPEN.map(([g, n]) => `${BD.indizes.filter(x => x.gruppe === g).length} ${esc(n)}`).join(", ")}) · ${BD.unternehmen.length} Unternehmen in ${new Set(BD.unternehmen.map(x => x.land)).size} Ländern · ${BD.wochen.length} Wochen bis ${datumDe(BD.wochen[BD.wochen.length - 1])}</p>
      <p>Indizes ohne frei verfügbare Kurse (Yahoo liefert keine Daten): ${o.indizes.length ? esc(o.indizes.join(", ")) : "keine"}.</p>
      <p>Unternehmen ohne Kurse: ${o.unternehmen.length ? esc(o.unternehmen.join(", ")) : "keine"}.</p>
      <p>Neue Indizes oder Unternehmen: einen Eintrag in <code>app/boersen_katalog.json</code> ergänzen (Index: Name, Land, Gruppe, Region, Yahoo-Symbole als Kandidaten; Unternehmen: Name, Symbol, Land, Sektor). Eine Unternehmens-ID vergibt der Abruf nie; sie wird nur übernommen, wenn der Ticker schon in <code>stammdaten/unternehmen_ids.csv</code> steht.</p>`,
      fuss: "Kurse sind verzögert und ohne Gewähr; Lizenzbedingungen von Yahoo Finance beachten. Weltindizes wie MSCI sind teils nur als ETF-Stellvertreter oder gar nicht frei verfügbar."
    })}</div>`;
  }
  const keineDaten = () => document.querySelector('meta[name="sphaerae-oeffentlich"]') ? `<div class="grid">${panel({ code: "BÖR", titel: "Börsendaten", body: `<p class="n">Kurse und Börsendaten stammen aus Yahoo Finance und dürfen auf dieser öffentlichen Seite nicht weitergegeben werden (Lizenz, siehe Datenquellen). Zinsen, Wechselkurse und Renditen finden sich unter Börse &amp; Finanzen.</p>` })}</div>` :
    `<div class="grid">${panel({ code: "BÖR", titel: "Börsendaten", body: `<p class="n">Noch keine Daten. <code>python3 app/boersen_abruf.py</code> schreibt <code>app/data/boerse.json</code>, danach <code>python3 app/build.py</code>.</p>` })}</div>`;

  /* ----- Bedienung ----- */
  function dazu(k) { if (gueltig(k) && !S.sel.includes(k)) { S.sel.push(k); if (S.sel.length > 10) S.sel.shift(); } }
  function klick(t) {
    const g = a => { const e = t.closest && t.closest("[" + a + "]"); return e ? e.getAttribute(a) : null; };
    let v;
    if ((v = g("data-bplus")) != null) {
      dazu(v);
      const el = t.closest("[data-bplus]");
      if (el.tagName === "BUTTON") { el.textContent = "✓"; el.title = "In der Auswahl des Verlaufs (F4)"; return true; }   // Tabellenknopf: Seite bleibt, Anker führen zum Verlauf
      if (location.hash === "#b-verlauf") { render(); return true; }
      return false;
    }
    if ((v = g("data-bweg")) != null) { S.sel = S.sel.filter(x => x !== v); render(); return true; }
    if ((v = g("data-bgruppe")) != null) { S.gruppe = v; render(); return true; }
    if ((v = g("data-bregion")) != null) { S.region = v; render(); return true; }
    if ((v = g("data-bfen")) != null) { S.fenster = v; render(); return true; }
    if (t.closest && t.closest("[data-blog]")) { S.log = !S.log; render(); return true; }
    if ((v = g("data-bpreset")) != null) { S.sel = PRESETS.find(p => p[0] === v)[1].filter(gueltig); render(); return true; }
    if ((v = g("data-bsort")) != null) {
      const [art, k] = v.split(":"), st = art === "i" ? S.isort : S.usort, neu = { k, ab: st.k === k ? !st.ab : ["name", "land", "sektor"].includes(k) };
      if (art === "i") S.isort = neu; else S.usort = neu;
      render(); return true;
    }
    return false;
  }
  function nachRender() {
    const bind = (id, fn) => { const e = document.getElementById(id); if (e) e.addEventListener("change", () => fn(e.value)); };
    bind("badd", v => { if (v) { dazu(v); render(); } });
    bind("bland", v => { S.land = v; render(); });
    bind("bsektor", v => { S.sektor = v; render(); });
    const s = document.getElementById("bsuche");
    if (s) s.addEventListener("input", () => { S.suche = s.value; const pos0 = s.selectionStart; render(); const n = document.getElementById("bsuche"); n.focus(); n.setSelectionRange(pos0, pos0); });
  }
  /* Kommandozeile: Name oder Symbol -> Eintrag in den Verlauf */
  function finden(q) {
    q = (q || "").trim().toLowerCase();
    if (!q || !BD) return null;
    const i = BD.indizes.find(x => x.name.toLowerCase() === q || x.id.toLowerCase() === q) || BD.indizes.find(x => x.name.toLowerCase().includes(q));
    const u = BD.unternehmen.find(x => x.name.toLowerCase() === q || x.symbol.toLowerCase() === q) || BD.unternehmen.find(x => x.name.toLowerCase().includes(q));
    return (u && (!i || u.name.toLowerCase() === q || u.symbol.toLowerCase() === q)) ? "u:" + u.symbol : i ? "i:" + i.id : null;
  }
  const waehle = k => { dazu(k); };
  const datalist = () => BD ? BD.indizes.map(x => `<option value="${esc(x.name)}">`).join("") + BD.unternehmen.map(x => `<option value="${esc(x.name)}">`).join("") : "";
  /* für die Korrelation: Wochenkurse von Indizes und Unternehmen */
  const korr = () => BD && { wochen: BD.wochen, indizes: BD.indizes, unternehmen: BD.unternehmen };
  /* Live-Kurse (siehe finanz.js): Kurs und Tagesänderung der Indizes überschreiben; die Veränderung seit Jahresbeginn wird auf den neuen Kurs umgerechnet */
  function live(w) {
    for (const x of (BD ? BD.indizes : [])) {
      const l = w[x.symbol] || w[x.id];
      if (!l || l.k == null || x.kurs == null) continue;
      if (x.ytd != null) x.ytd = l.k / (x.kurs / (1 + x.ytd)) - 1;
      x.kurs = l.k; x.datum = (l.z || "").slice(0, 10) || x.datum; if (l.v) x.r1t = l.k / l.v - 1;
    }
  }
  return { init, da, meta, live, viewUeb, viewInd, viewUnt, viewVerlauf, viewQuellen, klick, nachRender, finden, waehle, datalist, korr };
})();
