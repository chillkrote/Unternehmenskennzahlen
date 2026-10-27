/* ---------- Unternehmen außerhalb des Bankensektors: Branchenübersicht, Branche, Vergleich ----------
   Daten: UD = { demo, quellen, gruppen, branchen[], kennzahlen[], unternehmen[] } (siehe unternehmen.py).
   Läuft vor dem Hauptskript; nutzt dessen Hilfsfunktionen (panel, pct, median, ...) erst zur Laufzeit. */
"use strict";
const UNT = (() => {
  let UD = null, KZU = {}, BR = {}, FIRMEN = [];
  const S = { branche: "alle", markiert: null, sort: { k: "marktkap", ab: true }, rang: null, sx: "ebit_marge", sy: "kgv", usx: "kgv", usy: "ebit_marge", auswahl: null, matrixSort: null };

  /* ----- Aufbereitung ----- */
  function init(d) {
    UD = d && d.unternehmen && d.unternehmen.length ? d : null;
    if (!UD) return false;
    KZU = Object.fromEntries(UD.kennzahlen.map(k => [k.key, k]));
    BR = Object.fromEntries(UD.branchen.map(b => [b.id, b]));
    FIRMEN = UD.unternehmen.filter(f => BR[f.branche]);
    return true;
  }
  const da = () => !!UD;
  const inBranche = id => id === "alle" ? FIRMEN : FIRMEN.filter(f => f.branche === id);
  const w = (f, k) => f.werte[k] == null ? null : f.werte[k];
  const werte = (liste, k) => liste.map(f => w(f, k)).filter(v => v != null && isFinite(v));
  const med = (liste, k) => median(werte(liste, k));
  const kurzU = n => n.replace(/ (AG|SE|KGaA|GmbH|& Co\. KGaA|plc)\b/g, "").replace(/\(.*?\)/g, "").trim();
  const hatKz = k => !!KZU[k] && FIRMEN.some(f => w(f, k) != null);

  function fmt(k, v) {
    if (v == null) return "n. v.";
    const d = KZU[k] || { fmt: "zahl" };
    switch (d.fmt) {
      case "mio": return f0.format(v);
      case "pct": return pct(v, 1);
      case "chg": return chg(v);
      case "x": return (Math.abs(v) < 10 ? f2 : f1).format(v) + "x";
      case "eur": return f2.format(v);
      default: return (Math.abs(v) >= 100 ? f0 : f1).format(v);
    }
  }
  const mrd = v => v == null ? "n. v." : v >= 1e5 ? f0.format(v / 1e3) + " Mrd." : v >= 1e3 ? f1.format(v / 1e3) + " Mrd." : f0.format(v) + " Mio.";
  const name = k => KZU[k] ? KZU[k].name : k;

  /* ----- Banken als Branche aus den Börsendaten der Bankenansichten ----- */
  function bankenZeile() {
    if (typeof MARKT === "undefined" || !MARKT) return null;
    const seen = new Set(), b = MARKT.werte.filter(x => x.ebene === "Institut" && x.waehrung === "EUR" && !seen.has(x.ticker) && seen.add(x.ticker));
    if (!b.length) return null;
    const kz = k => median(b.map(x => x.kz && x.kz[k]).filter(v => v != null));
    return { n: b.length, marktkap: sum(b.map(x => (x.marktkap || 0) / 1e6)), werte: { kgv: kz("kgv"), kbv: kz("kbv"), div_rendite: kz("div_rendite"), roe: kz("roe"), ek_quote: kz("ek_quote"), r_ytd: median(b.map(x => x.r_ytd).filter(v => v != null)), netto_marge: null, ebit_marge: null } };
  }

  /* ----- Branchenwahl ----- */
  function chips(aktiv, attr, mitAlle = true) {
    const ids = [...(mitAlle ? [["alle", "Alle Branchen", FIRMEN.length]] : []), ...UD.branchen.map(b => [b.id, b.name, inBranche(b.id).length])];
    return `<div class="ctrl" style="margin-bottom:12px">${ids.map(([id, n, c]) => `<button type="button" ${attr}="${id}" aria-pressed="${id === aktiv}">${esc(n)} <span style="opacity:.6">${c}</span></button>`).join("")}</div>`;
  }

  /* ----- Übersicht über alle Branchen ----- */
  const MATRIX = ["kgv", "kbv", "ev_ebitda", "div_rendite", "ebit_marge", "netto_marge", "roe", "ek_quote", "verschuldung", "w_umsatz", "r_ytd"];
  function kacheln() {
    const st = (n, v) => `<div><span>${n}</span><strong>${v}</strong></div>`;
    const bz = bankenZeile();
    const alle = UD.branchen.map(b => {
      const l = inBranche(b.id);
      return `<a class="tile" href="#u-branche" data-uopen="${b.id}" style="--gf:var(--s3)"><div class="g"><b>${esc(b.name)}</b><span>n = ${l.length}</span></div>
        <div class="stats">${st("Börsenwert", mrd(sum(werte(l, "marktkap"))))}${st("KGV", fmt("kgv", med(l, "kgv")))}${st("EBIT-Marge", fmt("ebit_marge", med(l, "ebit_marge")))}${st("Div.-Rend.", fmt("div_rendite", med(l, "div_rendite")))}</div></a>`;
    }).join("");
    const bank = bz ? `<a class="tile" href="#mkt" style="--gf:var(--amber)"><div class="g"><b>Banken (börsennotiert)</b><span>n = ${bz.n} · eigene Ansichten</span></div>
        <div class="stats">${st("Börsenwert", mrd(bz.marktkap))}${st("KGV", fmt("kgv", bz.werte.kgv))}${st("RoE", fmt("roe", bz.werte.roe))}${st("Div.-Rend.", fmt("div_rendite", bz.werte.div_rendite))}</div></a>` : "";
    return `<div class="tape">${alle}${bank}</div>`;
  }

  function matrix() {
    const zeilen = UD.branchen.map(b => ({ id: b.id, name: b.name, n: inBranche(b.id).length, wert: k => med(inBranche(b.id), k), mk: sum(werte(inBranche(b.id), "marktkap")) }));
    const bz = bankenZeile();
    if (bz) zeilen.push({ id: "banken", name: "Banken (börsennotiert)", n: bz.n, wert: k => bz.werte[k] == null ? null : bz.werte[k], mk: bz.marktkap, extern: true });
    const spalten = MATRIX.filter(hatKz);
    const sk = S.matrixSort || "mk";
    zeilen.sort((a, b) => ((sk === "mk" ? b.mk : (b.wert(sk) ?? -Infinity)) - (sk === "mk" ? a.mk : (a.wert(sk) ?? -Infinity))));
    const spanne = {}; spalten.forEach(k => { const v = zeilen.map(z => z.wert(k)).filter(x => x != null); spanne[k] = [Math.min(...v), Math.max(...v)]; });
    const zelle = (z, k) => { const v = z.wert(k); if (v == null) return `<td class="n">–</td>`; const [lo, hi] = spanne[k], t = hi > lo ? (v - lo) / (hi - lo) : .5;
      return `<td style="background:rgba(255,168,40,${(.04 + .26 * t).toFixed(3)})">${fmt(k, v)}</td>`; };
    return `<div class="scroll"><table><thead><tr><th>Branche</th><th class="sortable" data-umatrix="mk">n</th><th class="sortable" data-umatrix="mk">Σ Börsenwert</th>${spalten.map(k => `<th class="sortable" data-umatrix="${k}" title="${esc(name(k))}">${esc(name(k).replace(/ \(.*\)/, ""))}${sk === k ? " ▼" : ""}</th>`).join("")}</tr></thead>
      <tbody>${zeilen.map(z => `<tr class="click" ${z.extern ? 'data-ugo="mkt"' : `data-uopen="${z.id}"`}><td>${esc(z.name)}</td><td class="n">${z.n}</td><td>${mrd(z.mk)}</td>${spalten.map(k => zelle(z, k)).join("")}</tr>`).join("")}</tbody></table></div>`;
  }

  function streuU(liste, kx, ky, hervor) {
    const pts = liste.filter(f => w(f, kx) != null && w(f, ky) != null);
    if (pts.length < 3) return `<p class="n">Zu wenige Werte für diese Kombination.</p>`;
    const W = 720, H = 400, x0 = 50, x1 = W - 16, y0 = 16, y1 = H - 32;
    const rg = k => { const xs = pts.map(f => w(f, k)); const lo = quant(xs, .03), hi = quant(xs, .97), p = (hi - lo) * .12 || .1; return [Math.min(lo - p, 0 > lo - p ? lo - p : lo - p), hi + p]; };
    const [lx, hx] = rg(kx), [ly, hy] = rg(ky);
    const sx = v => x0 + (x1 - x0) * (Math.min(Math.max(v, lx), hx) - lx) / (hx - lx), sy = v => y1 - (y1 - y0) * (Math.min(Math.max(v, ly), hy) - ly) / (hy - ly);
    const mk = Math.max(...pts.map(f => w(f, "marktkap") || 0)) || 1, rad = f => 3.5 + 9 * Math.sqrt((w(f, "marktkap") || 0) / mk);
    const tk = k => t => KZU[k].fmt === "pct" || KZU[k].fmt === "chg" ? nf(0).format(t * 100) + " %" : KZU[k].fmt === "x" ? f1.format(t) + "x" : f0.format(t);
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img">`;
    niceTicks(lx, hx, 7).forEach(t => s += `<line class="gl" x1="${sx(t)}" x2="${sx(t)}" y1="${y0}" y2="${y1}"/><text x="${sx(t)}" y="${y1 + 15}" text-anchor="middle">${tk(kx)(t)}</text>`);
    niceTicks(ly, hy, 6).forEach(t => s += `<line class="gl" x1="${x0}" x2="${x1}" y1="${sy(t)}" y2="${sy(t)}"/><text x="${x0 - 6}" y="${sy(t)}" text-anchor="end" dominant-baseline="middle">${tk(ky)(t)}</text>`);
    s += `<text x="${x1}" y="${H - 3}" text-anchor="end" style="fill:var(--amber)">${esc(name(kx))} →</text><text x="${x0}" y="${y0 - 5}" style="fill:var(--amber)">↑ ${esc(name(ky))}</text>`;
    const istH = f => hervor === "alle" ? false : f.branche === hervor;
    [...pts].sort((a, b) => istH(a) - istH(b) || (w(b, "marktkap") || 0) - (w(a, "marktkap") || 0)).forEach(f => {
      const h = istH(f) || f.name === S.markiert, tt = `<b>${esc(f.name)}</b>\n${esc(BR[f.branche].name)}\n${esc(name(kx))}: ${fmt(kx, w(f, kx))}\n${esc(name(ky))}: ${fmt(ky, w(f, ky))}\nBörsenwert: ${mrd(w(f, "marktkap"))}`;
      s += `<circle cx="${sx(w(f, kx))}" cy="${sy(w(f, ky))}" r="${rad(f)}" fill="${f.name === S.markiert ? "var(--key)" : h ? "var(--amber)" : "var(--s3)"}" fill-opacity="${h ? .85 : .5}" stroke="var(--panel)" stroke-width="1.5" data-umk="${esc(f.name)}" style="cursor:pointer" data-tip="${esc(tt)}"/>`;
    });
    const beschr = [...pts].filter(f => hervor === "alle" ? true : istH(f)).sort((a, b) => (w(b, "marktkap") || 0) - (w(a, "marktkap") || 0)).slice(0, hervor === "alle" ? 10 : 12);
    beschr.forEach(f => s += `<text x="${sx(w(f, kx)) + rad(f) + 3}" y="${sy(w(f, ky))}" dominant-baseline="middle" style="fill:var(--ink);pointer-events:none;font-size:10px">${esc(kurzU(f.name).split(" ").slice(0, 2).join(" "))}</text>`);
    return s + "</svg>";
  }
  function metrikWahl(attr, aktiv, liste) {
    return `<div class="ctrl" style="margin-bottom:10px">${liste.filter(hatKz).map(k => `<button type="button" ${attr}="${k}" aria-pressed="${k === aktiv}">${esc(name(k).replace(/ \(.*\)/, ""))}</button>`).join("")}</div>`;
  }
  const STREU_KZ = ["kgv", "kbv", "ev_ebitda", "ebit_marge", "netto_marge", "roe", "div_rendite", "verschuldung", "w_umsatz", "ek_quote", "r_ytd"];

  function viewUeb() {
    return `<div class="grid">
      <div class="p" style="grid-column:span 12;border:0;background:none">${kacheln()}</div>
      ${panel({ code: "UEB 1", titel: "Branchenvergleich", sub: "Median je Branche · Tönung = Höhe innerhalb der Spalte (keine Wertung) · Spaltenkopf sortiert · Zeile öffnet die Branche", body: matrix(),
        fuss: `${UD.demo ? "<b>Beispieldaten:</b> Stichprobe großer deutscher Börsenunternehmen aus Yahoo Finance, solange die Branchentabellen des Repos fehlen. " : ""}Konzernabschlüsse, Beträge in Mio. €. Banken werden mit eigenen Kennzahlen geführt (Börsenwert, KGV, KBV, RoE, EK-Quote aus den Börsendaten); Margen und Verschuldung gibt es bei Banken nicht.` })}
      ${panel({ code: "UEB 2", titel: "Alle Unternehmen im Streudiagramm", sub: "Kreisfläche ∝ Börsenwert · Klick auf einen Punkt markiert das Unternehmen", body:
        `<div class="ctrl" style="margin-bottom:6px"><span>X</span></div>${metrikWahl("data-ussx", S.usx, STREU_KZ)}<div class="ctrl" style="margin-bottom:6px"><span>Y</span></div>${metrikWahl("data-ussy", S.usy, STREU_KZ)}${streuU(FIRMEN, S.usx, S.usy, S.branche)}`,
        fuss: "Amber = gerade gewählte Branche, Grau = übrige. Ausreißer außerhalb der 3-%/97-%-Perzentile werden am Rand abgeschnitten." })}
    </div>`;
  }

  /* ----- Branche ----- */
  function rangU(k, liste) {
    const z = liste.map(f => ({ f, v: w(f, k) })).filter(x => x.v != null).sort((a, b) => b.v - a.v);
    if (!z.length) return `<p class="n">Keine Werte.</p>`;
    const W = 560, x0 = 170, x1 = W - 78, hz = 20, H = z.length * hz + 6, lo = Math.min(0, ...z.map(x => x.v)), hi = Math.max(0, ...z.map(x => x.v));
    const sx = v => x0 + (x1 - x0) * (v - lo) / ((hi - lo) || 1), md = median(z.map(x => x.v));
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img"><line x1="${sx(0)}" x2="${sx(0)}" y1="0" y2="${H}" stroke="var(--ink-3)"/>`;
    z.forEach(({ f, v }, i) => { const y = i * hz + 2, an = f.name === S.markiert, a = Math.min(sx(0), sx(v)), b = Math.max(sx(0), sx(v));
      s += `<text x="${x0 - 6}" y="${y + hz / 2}" text-anchor="end" dominant-baseline="middle" style="fill:${an ? "var(--amber)" : "var(--ink-2)"}">${esc(kurzU(f.name).slice(0, 26))}</text>`;
      s += `<rect x="${a}" y="${y + 3}" width="${Math.max(1, b - a)}" height="${hz - 8}" fill="${an ? "var(--amber)" : v < 0 ? "var(--down)" : "var(--s3)"}" data-umk="${esc(f.name)}" style="cursor:pointer" data-tip="${esc(`<b>${esc(f.name)}</b>\n${esc(name(k))}: ${fmt(k, v)}\nMedian: ${fmt(k, md)}`)}"/><text x="${x1 + 6}" y="${y + hz / 2}" dominant-baseline="middle" style="fill:var(--ink)">${fmt(k, v)}</text>`; });
    return s + `<line x1="${sx(md)}" x2="${sx(md)}" y1="0" y2="${H}" stroke="var(--amber)" stroke-dasharray="3 3"/></svg>`;
  }

  function profil(liste) {
    const andere = FIRMEN.filter(f => !liste.includes(f)), ks = Object.keys(KZU).filter(k => !["kurs", "marktkap"].includes(k) && KZU[k].fmt !== "mio" && werte(liste, k).length >= 2);
    if (!andere.length) return `<p class="n">Zum Vergleich fehlen weitere Branchen.</p>`;
    return `<div class="scroll"><table><thead><tr><th>Kennzahl</th><th>Median Branche</th><th>Median übrige</th><th>Abweichung</th></tr></thead><tbody>${ks.map(k => {
      const a = med(liste, k), b = med(andere, k), d = a != null && b != null ? a - b : null, pc = ["pct", "chg"].includes(KZU[k].fmt), h = KZU[k].hoch;
      const txt = d == null ? "–" : pc ? (d > 0 ? "+" : "") + f1.format(d * 100) + " Pp." : (d > 0 ? "+" : "") + f2.format(d) + (KZU[k].fmt === "x" ? "x" : "");
      const cl = d == null || h == null || Math.abs(d) < 1e-9 ? "" : (d > 0) === h ? "pos" : "neg";
      return `<tr><td>${esc(name(k))}</td><td>${fmt(k, a)}</td><td class="n">${fmt(k, b)}</td><td class="${cl}">${txt}</td></tr>`; }).join("")}</tbody></table></div>`;
  }

  function tabelleBranche(liste, b) {
    const sp = ["marktkap", ...(b ? b.schwerpunkt : ["ebit_marge", "kgv", "div_rendite", "roe"]).filter(hatKz).slice(0, 6), "r_ytd"].filter((k, i, a) => a.indexOf(k) === i && hatKz(k));
    if (!sp.includes(S.sort.k)) S.sort = { k: sp[0], ab: true };
    const sort = [...liste].sort((a, b2) => { const x = w(a, S.sort.k), y = w(b2, S.sort.k); if (x == null) return 1; if (y == null) return -1; return S.sort.ab ? y - x : x - y; });
    const meds = sp.map(k => med(liste, k));
    return `<div class="tblwrap"><table class="kzt"><thead><tr><th>Unternehmen</th>${S.branche === "alle" ? "<th style='text-align:left'>Branche</th>" : ""}${sp.map(k => `<th class="sortable" data-usort="${k}">${esc(name(k).replace(/ \(.*\)/, ""))}${S.sort.k === k ? (S.sort.ab ? " ▼" : " ▲") : ""}</th>`).join("")}<th></th></tr></thead>
      <tbody>${sort.map(f => `<tr class="click${f.name === S.markiert ? " sel" : ""}" data-umk="${esc(f.name)}"><td>${esc(kurzU(f.name))}${f.ticker ? ` <span class="pct">${esc(f.ticker.replace(/\.\w+$/, ""))}</span>` : ""}</td>${S.branche === "alle" ? `<td class="n" style="text-align:left;font-family:var(--sans)">${esc(BR[f.branche].name)}</td>` : ""}${sp.map(k => { const v = w(f, k); return `<td class="${v == null ? "n" : ["r_ytd", "w_umsatz", "w_jue"].includes(k) ? klasse(v) : ""}">${fmt(k, v)}</td>`; }).join("")}<td><button type="button" class="mini" data-uadd="${esc(f.name)}" title="In den Vergleich übernehmen">+</button></td></tr>`).join("")}
      <tr><td style="color:var(--amber)">Median</td>${S.branche === "alle" ? "<td></td>" : ""}${meds.map((v, i) => `<td style="color:var(--amber)">${fmt(sp[i], v)}</td>`).join("")}<td></td></tr></tbody></table></div>`;
  }

  function adapter(liste) { return liste.filter(f => f.kurse && f.kurse.length > 1).map(f => ({ ticker: f.ticker, bank: f.name, mutter: null, ebene: "Institut", kurse: f.kurse, datum: f.datum })); }

  function viewBra() {
    const b = BR[S.branche] || null, liste = inBranche(S.branche), rk = (b ? b.schwerpunkt : STREU_KZ).filter(hatKz);
    if (!S.rang || !hatKz(S.rang)) S.rang = rk[0];
    const marker = FIRMEN.find(f => f.name === S.markiert);
    mktMarkiert = marker ? marker.ticker : null;
    const ad = adapter(liste);
    const ctrl = `<div class="ctrl" style="margin-bottom:6px">${Object.entries(FENSTER).map(([k, [n]]) => `<button type="button" data-fenster="${k}" aria-pressed="${k === mktFenster}">${n}</button>`).join("")}</div>`;
    const stats = [["marktkap", "Σ Börsenwert", mrd(sum(werte(liste, "marktkap")))], ...rk.slice(0, 4).map(k => [k, "Median " + name(k).replace(/ \(.*\)/, ""), fmt(k, med(liste, k))])];
    return `<div class="grid">
      <div class="p" style="grid-column:span 12;border:0;background:none">${chips(S.branche, "data-ub")}
        <div class="tape">${stats.map(([k, n, v]) => `<div style="--gf:var(--amber)"><div class="g"><b>${esc(n)}</b></div><div class="stats" style="grid-template-columns:1fr"><div><strong style="font-size:20px">${v}</strong></div></div></div>`).join("")}</div></div>
      ${panel({ code: "BRA 1", titel: b ? b.name : "Alle Unternehmen", sub: `${liste.length} Unternehmen · Spaltenkopf sortiert · Zeile markiert · + übernimmt in den Vergleich`, breite: "w7", body: tabelleBranche(liste, b),
        fuss: UD.demo ? "<b>Beispieldaten:</b> Stichprobe aus Yahoo Finance. Die vollständigen Branchentabellen (alle deutschen Börsenunternehmen) ersetzen sie, sobald sie im Repo liegen." : "Konzernabschlüsse, Beträge in Mio. €." })}
      <div class="col w5">${panel({ code: "BRA 2", titel: "Rangfolge", sub: `${esc(name(S.rang))} · gestrichelt = Median`, body: metrikWahl("data-urang", S.rang, [...new Set([...rk, "roe", "ebit_marge", "kgv", "kbv", "div_rendite", "verschuldung", "w_umsatz"])]) + rangU(S.rang, liste) })}
        ${panel({ code: "BRA 3", titel: "Profil gegen die übrigen Branchen", sub: "Median der Branche gegen Median aller anderen Unternehmen", body: S.branche === "alle" ? `<p class="n">Eine Branche wählen.</p>` : profil(liste), fuss: "Grün/Rot bewertet nur Kennzahlen mit eindeutiger Richtung (z. B. Marge höher = besser, Verschuldung niedriger = besser)." })}</div>
      ${panel({ code: "BRA 4", titel: "Kursentwicklung indexiert", sub: `Schlusskurs, Beginn des Zeitraums = 100 · ${ad.length} Aktien`, breite: "w6", body: ctrl + (ad.length > 1 ? indexChart(ad) : `<p class="n">Keine Kurse.</p>`), fuss: "Kurse in Euro, nicht dividendenbereinigt." })}
      ${panel({ code: "BRA 5", titel: "Bewertung gegen Rentabilität", sub: "Kreisfläche ∝ Börsenwert", breite: "w6", body: `<div class="ctrl" style="margin-bottom:6px"><span>X</span></div>${metrikWahl("data-usx", S.sx, STREU_KZ)}<div class="ctrl" style="margin-bottom:6px"><span>Y</span></div>${metrikWahl("data-usy", S.sy, STREU_KZ)}${streuU(liste, S.sx, S.sy, "alle")}` })}
    </div>`;
  }

  /* ----- Vergleich einzelner Unternehmen ----- */
  function viewVgl() {
    if (!S.auswahl) { const top = [...FIRMEN].sort((a, b) => (w(b, "marktkap") || 0) - (w(a, "marktkap") || 0)); S.auswahl = []; const gesehen = new Set(); top.forEach(f => { if (S.auswahl.length < 4 && !gesehen.has(f.branche)) { gesehen.add(f.branche); S.auswahl.push(f.name); } }); }
    const cs = S.auswahl.map(n => FIRMEN.find(f => f.name === n)).filter(Boolean);
    const picks = `<div class="picks">${cs.map(f => `<span class="chip">${esc(kurzU(f.name))} <span class="pct">${esc(BR[f.branche].name)}</span><button type="button" data-uweg="${esc(f.name)}" aria-label="${esc(f.name)} entfernen">×</button></span>`).join("")}
      <input id="uadd" list="firmenliste" placeholder="+ Unternehmen hinzufügen (max. 6)" autocomplete="off" ${cs.length >= 6 ? "disabled" : ""}></div>`;
    const zeilen = UD.gruppen.map(g => { const ks = UD.kennzahlen.filter(k => k.gruppe === g && cs.some(f => w(f, k.key) != null)); if (!ks.length) return "";
      return `<tr><td colspan="${cs.length + 2}" class="grp">${esc(g)}</td></tr>` + ks.map(k => { const alle = werte(FIRMEN, k.key);
        return `<tr><td>${esc(k.name)}${k.einheit ? ` <span class="pct">${esc(k.einheit)}</span>` : ""}</td>${cs.map(f => { const v = w(f, k.key); if (v == null) return `<td class="n">n. v.</td>`; const p = perzentil(v, alle);
          return `<td>${fmt(k.key, v)} <span class="pct" title="Perzentil unter allen ${alle.length} Unternehmen">P${f0.format(p * 100).padStart(2, "0")}</span></td>`; }).join("")}<td class="n" title="Median aller Unternehmen">${fmt(k.key, median(alle))}</td></tr>`; }).join(""); }).join("");
    const matrixT = `<div class="scroll"><table class="kzt"><thead><tr><th>Kennzahl</th>${cs.map(f => `<th title="${esc(f.name)}">${esc(kurzU(f.name).slice(0, 16))}</th>`).join("")}<th>Median alle</th></tr></thead><tbody>${zeilen}</tbody></table></div>`;
    const bars = ["ebit_marge", "roe", "verschuldung", "kgv", "div_rendite", "w_umsatz"].filter(hatKz).map(k => `<div><div class="sub-h">${esc(name(k))}</div>${balkenU(k, cs)}</div>`).join("");
    const ad = adapter(cs), marker = cs[0];
    mktMarkiert = marker ? marker.ticker : null;
    const ctrl = `<div class="ctrl" style="margin-bottom:6px">${Object.entries(FENSTER).map(([k, [n]]) => `<button type="button" data-fenster="${k}" aria-pressed="${k === mktFenster}">${n}</button>`).join("")}</div>`;
    return `<div class="grid">
      ${panel({ code: "UCMP", titel: "Auswahl", sub: "Unternehmen aus allen Branchen frei kombinieren · + in der Branchenansicht oder Suche in der Kommandozeile", body: picks })}
      ${panel({ code: "UCMP 1", titel: "Kennzahlenmatrix", sub: "P = Perzentil unter allen Unternehmen (P99 = höchster Wert)", breite: "w7", body: matrixT })}
      ${panel({ code: "UCMP 2", titel: "Gegen den Branchenmedian", sub: "Balken = Unternehmen, Strich = Median der eigenen Branche", breite: "w5", body: `<div style="display:grid;gap:8px">${bars}</div>` })}
      ${panel({ code: "UCMP 3", titel: "Kursentwicklung indexiert", sub: `Beginn des Zeitraums = 100`, body: ctrl + (ad.length > 1 ? indexChart(ad) : `<p class="n">Mindestens zwei Unternehmen mit Kursen wählen.</p>`) })}
    </div>`;
  }
  function balkenU(k, cs) {
    const W = 520, x0 = 170, x1 = W - 74, hz = 19, z = cs.map(f => ({ f, v: w(f, k), md: med(inBranche(f.branche), k) }));
    const lo = Math.min(0, ...z.map(x => Math.min(x.v ?? 0, x.md ?? 0))), hi = Math.max(0, ...z.map(x => Math.max(x.v ?? 0, x.md ?? 0))) || 1, sx = v => x0 + (x1 - x0) * (v - lo) / ((hi - lo) || 1), H = z.length * hz + 4;
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img">`;
    z.forEach(({ f, v, md }, i) => { const y = i * hz + 2;
      s += `<text x="${x0 - 6}" y="${y + hz / 2}" text-anchor="end" dominant-baseline="middle">${esc(kurzU(f.name).slice(0, 24))}</text>`;
      if (v == null) { s += `<text x="${x0}" y="${y + hz / 2}" dominant-baseline="middle" style="fill:var(--ink-3)">n. v.</text>`; return; }
      s += `<rect x="${Math.min(sx(0), sx(v))}" y="${y + 3}" width="${Math.max(1, Math.abs(sx(v) - sx(0)))}" height="${hz - 7}" fill="${v < 0 ? "var(--down)" : "var(--s3)"}" data-tip="${esc(`<b>${esc(f.name)}</b>\n${esc(name(k))}: ${fmt(k, v)}\nMedian ${esc(BR[f.branche].name)}: ${fmt(k, md)}`)}"/>`;
      if (md != null) s += `<line x1="${sx(md)}" x2="${sx(md)}" y1="${y + 1}" y2="${y + hz - 2}" stroke="var(--amber)" stroke-width="2"/>`;
      s += `<text x="${x1 + 6}" y="${y + hz / 2}" dominant-baseline="middle" style="fill:var(--ink)">${fmt(k, v)}</text>`; });
    return s + "</svg>";
  }

  /* ----- Bedienung ----- */
  function hinzu(n) { if (!S.auswahl) viewVgl(); if (!S.auswahl.includes(n)) { S.auswahl.push(n); if (S.auswahl.length > 6) S.auswahl.shift(); } }
  function finden(q) { q = (q || "").trim().toLowerCase(); if (!q || !UD) return null; return FIRMEN.find(f => f.name.toLowerCase() === q) || FIRMEN.find(f => f.name.toLowerCase().includes(q) || (f.ticker || "").toLowerCase() === q); }
  function klick(t) {
    const g = a => { const e = t.closest && t.closest("[" + a + "]"); return e ? e.getAttribute(a) : null; };
    let v;
    if ((v = g("data-uadd")) != null) { hinzu(v); gehe("u-vergleich"); return true; }
    if ((v = g("data-uweg")) != null) { S.auswahl = S.auswahl.filter(x => x !== v); render(); return true; }
    if ((v = g("data-ub")) != null) { S.branche = v; S.rang = null; render(); return true; }
    if ((v = g("data-uopen")) != null) { S.branche = v; S.rang = null; gehe("u-branche"); return true; }
    if ((v = g("data-ugo")) != null) { gehe(v); return true; }
    if ((v = g("data-usort")) != null) { S.sort = { k: v, ab: S.sort.k === v ? !S.sort.ab : true }; render(); return true; }
    if ((v = g("data-umatrix")) != null) { S.matrixSort = v; render(); return true; }
    if ((v = g("data-urang")) != null) { S.rang = v; render(); return true; }
    if ((v = g("data-usx")) != null) { S.sx = v; render(); return true; }
    if ((v = g("data-usy")) != null) { S.sy = v; render(); return true; }
    if ((v = g("data-ussx")) != null) { S.usx = v; render(); return true; }
    if ((v = g("data-ussy")) != null) { S.usy = v; render(); return true; }
    if ((v = g("data-umk")) != null) { S.markiert = S.markiert === v ? null : v; render(); return true; }
    return false;
  }
  function nachRender() { const a = document.getElementById("uadd"); if (a) a.addEventListener("change", () => { const f = finden(a.value); if (f) { hinzu(f.name); render(); } }); }
  function datalist() { return UD ? FIRMEN.map(f => `<option value="${esc(f.name)}">`).join("") : ""; }
  function meta() { return UD ? `${FIRMEN.length} Unternehmen · ${UD.branchen.length} Branchen${UD.demo ? " · Beispieldaten" : ""}` : ""; }
  return { init, da, viewUeb, viewBra, viewVgl, klick, nachRender, datalist, finden, hinzu, meta, setBranche: id => { S.branche = id; } };
})();
