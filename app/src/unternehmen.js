/* ---------- Unternehmen aller Branchen (Banken sind eine Branche unter vielen) ----------
   Daten: UD = { demo, repo, zweig, quellen, gruppen, branchen[], kennzahlen[], unternehmen[] } (siehe unternehmen.py).
   Je Unternehmen: id, name, branche, gruppe?, notiert, werte{}, reihen{}?, dokumente[]?, ticker?, kurse?.
   Läuft vor dem Hauptskript; nutzt dessen Hilfsfunktionen (panel, pct, median, ...) erst zur Laufzeit. */
"use strict";
const UNT = (() => {
  let UD = null, KZU = {}, BR = {}, FIRMEN = [], NACH_ID = {};
  const S = { branche: "alle", gruppe: "alle", notiert: "alle", markiert: null, sort: { k: "marktkap", ab: true }, rang: null,
    sx: "ebit_marge", sy: "kgv", usx: "kgv", usy: "ebit_marge", auswahl: null, matrixSort: null, dokTyp: "alle" };

  /* ----- Aufbereitung ----- */
  function init(d) {
    UD = d && d.unternehmen && d.unternehmen.length ? d : null;
    if (!UD) return false;
    KZU = Object.fromEntries(UD.kennzahlen.map(k => [k.key, k]));
    BR = Object.fromEntries(UD.branchen.map(b => [b.id, b]));
    FIRMEN = UD.unternehmen.filter(f => BR[f.branche]);
    NACH_ID = Object.fromEntries(FIRMEN.map(f => [f.id, f]));
    return true;
  }
  const da = () => !!UD;
  const inBranche = id => id === "alle" ? FIRMEN : FIRMEN.filter(f => f.branche === id);
  const w = (f, k) => f.werte[k] == null ? null : f.werte[k];
  const werte = (liste, k) => liste.map(f => w(f, k)).filter(v => v != null && isFinite(v));
  const med = (liste, k) => median(werte(liste, k));
  const kurzU = n => n.replace(/ (AG|SE|KGaA|GmbH|eG|& Co\. KGaA|plc)\b/g, "").replace(/\(.*?\)/g, "").trim();
  const hatKz = k => !!KZU[k] && FIRMEN.some(f => w(f, k) != null);
  const hatL = (liste, k) => !!KZU[k] && liste.some(f => w(f, k) != null);
  const kzName = k => KZU[k] ? KZU[k].name : k === "fonds_340g" ? "Fonds § 340g" : k.replace(/_/g, " ");
  const kurzKz = k => kzName(k).replace(/ \(.*\)/, "");

  function fmt(k, v) {
    if (v == null) return "n. v.";
    const d = KZU[k] || { fmt: /quote|ratio|marge|rendite/.test(k) ? "pct" : "mio" };
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
  const mb = kb => kb == null ? "" : kb >= 1024 ? f1.format(kb / 1024) + " MB" : f0.format(kb) + " KB";
  const brName = id => BR[id] ? BR[id].name : id;
  const nNotiert = l => l.filter(f => f.notiert).length;
  /* Größenkennzahl einer Liste: Börsenwert, sonst Bilanzsumme, sonst Umsatz */
  function groesse(l) {
    for (const [k, n] of [["marktkap", "Σ Börsenwert"], ["bilanzsumme", "Σ Bilanzsumme"], ["umsatz", "Σ Umsatz"]]) {
      const s = sum(werte(l, k)); if (s > 0) return { k, n, v: s };
    }
    return null;
  }
  function kurseVon(f) {
    if (f.kurse && f.kurse.length > 1) return { ticker: f.ticker, bank: f.name, mutter: null, ebene: "Institut", kurse: f.kurse, datum: f.datum };
    const m = f.ticker && typeof MARKT !== "undefined" && MARKT && MARKT.werte.find(x => x.ticker === f.ticker);
    return m && m.kurse && m.kurse.length > 1 ? { ticker: m.ticker, bank: f.name, mutter: null, ebene: "Institut", kurse: m.kurse, datum: m.datum } : null;
  }
  const adapter = liste => liste.map(kurseVon).filter(Boolean);
  const profilLink = (f, text) => `<a class="flink" href="#firma-${f.id}">${esc(text == null ? kurzU(f.name) : text)}</a>`;
  const punkt = f => f.notiert ? `<span class="dot" data-tip="börsennotiert${f.ticker ? " · " + esc(f.ticker) : ""}">●</span>` : "";

  /* ----- Filter der Branchenansicht ----- */
  function aktuelleListe() {
    let l = inBranche(S.branche);
    if (S.gruppe !== "alle") l = l.filter(f => f.gruppe === S.gruppe);
    if (S.notiert === "ja") l = l.filter(f => f.notiert);
    if (S.notiert === "nein") l = l.filter(f => !f.notiert);
    return l;
  }
  const chipRow = (items, attr, aktiv) => `<div class="ctrl" style="margin-bottom:10px">${items.map(([id, n, c]) =>
    `<button type="button" ${attr}="${esc(id)}" aria-pressed="${id === aktiv}">${esc(n)}${c != null ? ` <span style="opacity:.6">${c}</span>` : ""}</button>`).join("")}</div>`;
  function filterZeilen(b) {
    const basis = inBranche(S.branche);
    let h = chipRow([["alle", "Alle Branchen", FIRMEN.length], ...UD.branchen.map(x => [x.id, x.name, inBranche(x.id).length])], "data-ub", S.branche);
    if (b && b.gruppen.length) h += chipRow([["alle", "Alle Gruppen", basis.length], ...b.gruppen.map(g => [g, g, basis.filter(f => f.gruppe === g).length])], "data-ug", S.gruppe);
    const mitGruppe = S.gruppe === "alle" ? basis : basis.filter(f => f.gruppe === S.gruppe), n = nNotiert(mitGruppe);
    if (n && n < mitGruppe.length) h += chipRow([["alle", "Notiert und nicht notiert", mitGruppe.length], ["ja", "Börsennotiert", n], ["nein", "Nicht börsennotiert", mitGruppe.length - n]], "data-un", S.notiert);
    return h;
  }

  /* ----- Übersicht über alle Branchen ----- */
  const MATRIX = ["kgv", "kbv", "ev_ebitda", "div_rendite", "ebit_marge", "netto_marge", "roe", "ek_quote", "verschuldung", "w_umsatz", "r_ytd"];
  function schwerpunkt(b, l, n) { return (b.schwerpunkt || []).filter(k => hatL(l, k)).slice(0, n); }
  function kacheln() {
    const st = (n, v) => `<div><span>${n}</span><strong>${v}</strong></div>`;
    return `<div class="tape">${UD.branchen.map(b => {
      const l = inBranche(b.id), g = groesse(l), nn = nNotiert(l), ks = schwerpunkt(b, l, 3);
      return `<a class="tile" href="#u-branche" data-uopen="${esc(b.id)}" style="--gf:${b.id === "banken" ? "var(--amber)" : "var(--s3)"}"><div class="g"><b>${esc(b.name)}</b><span>n = ${l.length}${nn && nn < l.length ? ` · ${nn} notiert` : nn ? "" : " · nicht notiert"}</span></div>
        <div class="stats">${g ? st(g.n, g.k === "marktkap" || g.k === "bilanzsumme" ? mrd(g.v) : f0.format(g.v)) : ""}${ks.map(k => st(esc(kurzKz(k)), fmt(k, med(l, k)))).join("")}</div></a>`;
    }).join("")}</div>`;
  }

  function matrix() {
    const zeilen = UD.branchen.map(b => { const l = inBranche(b.id); return { id: b.id, name: b.name, n: l.length, nn: nNotiert(l), wert: k => med(l, k), mk: sum(werte(l, "marktkap")) }; });
    const spalten = MATRIX.filter(hatKz);
    const sk = S.matrixSort || "n";
    const sw = (z, k) => k === "n" ? z.n : k === "mk" ? z.mk : (z.wert(k) ?? -Infinity);
    zeilen.sort((a, b) => sw(b, sk) - sw(a, sk));
    const spanne = {}; spalten.forEach(k => { const v = zeilen.map(z => z.wert(k)).filter(x => x != null); spanne[k] = [Math.min(...v), Math.max(...v)]; });
    const zelle = (z, k) => { const v = z.wert(k); if (v == null) return `<td class="n">–</td>`; const [lo, hi] = spanne[k], t = hi > lo ? (v - lo) / (hi - lo) : .5;
      return `<td style="background:rgba(255,168,40,${(.04 + .26 * t).toFixed(3)})">${fmt(k, v)}</td>`; };
    const kopf = (k, t) => `<th class="sortable" data-umatrix="${k}">${t}${sk === k ? " ▼" : ""}</th>`;
    return `<div class="scroll"><table><thead><tr><th>Branche</th>${kopf("n", "n")}<th>notiert</th>${kopf("mk", "Σ Börsenwert")}${spalten.map(k => `<th class="sortable" data-umatrix="${k}" title="${esc(kzName(k))}">${esc(kurzKz(k))}${sk === k ? " ▼" : ""}</th>`).join("")}</tr></thead>
      <tbody>${zeilen.map(z => `<tr class="click" data-uopen="${esc(z.id)}"><td>${esc(z.name)}</td><td class="n">${z.n}</td><td class="n">${z.nn || "–"}</td><td>${z.mk ? mrd(z.mk) : "–"}</td>${spalten.map(k => zelle(z, k)).join("")}</tr>`).join("")}</tbody></table></div>`;
  }

  function streuU(liste, kx, ky, hervor, hervorG) {
    const pts = liste.filter(f => w(f, kx) != null && w(f, ky) != null);
    if (pts.length < 3 || !KZU[kx] || !KZU[ky]) return `<p class="n">Zu wenige Werte für diese Kombination.</p>`;
    const W = 720, H = 400, x0 = 50, x1 = W - 16, y0 = 16, y1 = H - 32;
    const rg = k => { const xs = pts.map(f => w(f, k)); const lo = quant(xs, .03), hi = quant(xs, .97), p = (hi - lo) * .12 || .1; return [lo - p, hi + p]; };
    const [lx, hx] = rg(kx), [ly, hy] = rg(ky);
    const sx = v => x0 + (x1 - x0) * (Math.min(Math.max(v, lx), hx) - lx) / (hx - lx), sy = v => y1 - (y1 - y0) * (Math.min(Math.max(v, ly), hy) - ly) / (hy - ly);
    const sk = pts.some(f => w(f, "marktkap")) ? "marktkap" : pts.some(f => w(f, "bilanzsumme")) ? "bilanzsumme" : null;
    const mk = sk ? Math.max(...pts.map(f => w(f, sk) || 0)) || 1 : 1, rad = f => sk ? 3.5 + 9 * Math.sqrt((w(f, sk) || 0) / mk) : 4.5;
    const tk = k => t => KZU[k].fmt === "pct" || KZU[k].fmt === "chg" ? nf(0).format(t * 100) + " %" : KZU[k].fmt === "x" ? f1.format(t) + "x" : f0.format(t);
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img">`;
    niceTicks(lx, hx, 7).forEach(t => s += `<line class="gl" x1="${sx(t)}" x2="${sx(t)}" y1="${y0}" y2="${y1}"/><text x="${sx(t)}" y="${y1 + 15}" text-anchor="middle">${tk(kx)(t)}</text>`);
    niceTicks(ly, hy, 6).forEach(t => s += `<line class="gl" x1="${x0}" x2="${x1}" y1="${sy(t)}" y2="${sy(t)}"/><text x="${x0 - 6}" y="${sy(t)}" text-anchor="end" dominant-baseline="middle">${tk(ky)(t)}</text>`);
    s += `<text x="${x1}" y="${H - 3}" text-anchor="end" style="fill:var(--amber)">${esc(kzName(kx))} →</text><text x="${x0}" y="${y0 - 5}" style="fill:var(--amber)">↑ ${esc(kzName(ky))}</text>`;
    const istH = f => hervor === "alle" ? false : f.branche === hervor && (!hervorG || hervorG === "alle" || f.gruppe === hervorG);
    const gr = f => sk ? (w(f, sk) || 0) : 0;
    [...pts].sort((a, b) => istH(a) - istH(b) || gr(b) - gr(a)).forEach(f => {
      const h = istH(f) || f.id === S.markiert, tt = `<b>${esc(f.name)}</b>\n${esc(brName(f.branche))}${f.gruppe ? " · " + esc(f.gruppe) : ""}\n${esc(kzName(kx))}: ${fmt(kx, w(f, kx))}\n${esc(kzName(ky))}: ${fmt(ky, w(f, ky))}${sk ? `\n${esc(kzName(sk))}: ${mrd(w(f, sk))}` : ""}`;
      s += `<circle cx="${sx(w(f, kx))}" cy="${sy(w(f, ky))}" r="${rad(f)}" fill="${f.id === S.markiert ? "var(--key)" : h ? "var(--amber)" : "var(--s3)"}" fill-opacity="${h ? .85 : .5}" stroke="var(--panel)" stroke-width="1.5" data-umk="${esc(f.id)}" style="cursor:pointer" data-tip="${esc(tt)}"/>`;
    });
    const beschr = [...pts].filter(f => hervor === "alle" ? true : istH(f)).sort((a, b) => gr(b) - gr(a)).slice(0, hervor === "alle" ? 10 : 12);
    beschr.forEach(f => s += `<text x="${sx(w(f, kx)) + rad(f) + 3}" y="${sy(w(f, ky))}" dominant-baseline="middle" style="fill:var(--ink);pointer-events:none;font-size:10px">${esc(kurzU(f.name).split(" ").slice(0, 2).join(" "))}</text>`);
    return s + "</svg>";
  }
  function metrikWahl(attr, aktiv, liste, ks) {
    return `<div class="ctrl" style="margin-bottom:10px">${ks.filter(k => hatL(liste, k)).map(k => `<button type="button" ${attr}="${k}" aria-pressed="${k === aktiv}">${esc(kurzKz(k))}</button>`).join("")}</div>`;
  }
  const STREU_KZ = ["kgv", "kbv", "ev_ebitda", "ebit_marge", "netto_marge", "roe", "roa", "div_rendite", "verschuldung", "w_umsatz", "w_bilanzsumme", "ek_quote", "cet1_quote", "lr", "bilanzsumme", "r_ytd"];
  const fuss = b => UD.demo && !(b && b.id === "banken") ? "<b>Beispieldaten:</b> Die Nicht-Bank-Branchen zeigen eine Stichprobe aus Yahoo Finance, bis die Branchentabellen im Repo liegen. " : "";

  function viewUeb() {
    return `<div class="grid">
      <div class="p" style="grid-column:span 12;border:0;background:none">${kacheln()}</div>
      ${panel({ code: "UEB 1", titel: "Branchenvergleich", sub: "Median je Branche · Tönung = Höhe innerhalb der Spalte (keine Wertung) · Spaltenkopf sortiert · Zeile öffnet die Branche", body: matrix(),
        fuss: `${fuss()}Banken sind eine Branche unter allen: HGB-Einzelabschlüsse, Börsenkennzahlen nur bei selbst notierten Instituten. Nicht börsennotierte Unternehmen erscheinen mit Abschlusskennzahlen, ohne Kapitalmarktwerte.` })}
      ${panel({ code: "UEB 2", titel: "Alle Unternehmen im Streudiagramm", sub: "Kreisfläche ∝ Börsenwert · Klick auf einen Punkt markiert das Unternehmen", body:
        `<div class="ctrl" style="margin-bottom:6px"><span>X</span></div>${metrikWahl("data-ussx", S.usx, FIRMEN, STREU_KZ)}<div class="ctrl" style="margin-bottom:6px"><span>Y</span></div>${metrikWahl("data-ussy", S.usy, FIRMEN, STREU_KZ)}${streuU(FIRMEN, S.usx, S.usy, S.branche, S.gruppe)}`,
        fuss: "Amber = gerade gewählte Branche, Grau = übrige. Ausreißer außerhalb der 3-%/97-%-Perzentile werden am Rand abgeschnitten." })}
    </div>`;
  }

  /* ----- Branche ----- */
  function rangU(k, liste) {
    const z = liste.map(f => ({ f, v: w(f, k) })).filter(x => x.v != null).sort((a, b) => b.v - a.v);
    if (!z.length) return `<p class="n">Keine Werte.</p>`;
    const zeigen = z.length > 40 ? [...z.slice(0, 20), ...z.slice(-20)] : z;
    const W = 560, x0 = 170, x1 = W - 78, hz = 20, H = zeigen.length * hz + 6, lo = Math.min(0, ...z.map(x => x.v)), hi = Math.max(0, ...z.map(x => x.v));
    const sx = v => x0 + (x1 - x0) * (v - lo) / ((hi - lo) || 1), md = median(z.map(x => x.v));
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img"><line x1="${sx(0)}" x2="${sx(0)}" y1="0" y2="${H}" stroke="var(--ink-3)"/>`;
    zeigen.forEach(({ f, v }, i) => { const y = i * hz + 2, an = f.id === S.markiert, a = Math.min(sx(0), sx(v)), b = Math.max(sx(0), sx(v));
      s += `<text x="${x0 - 6}" y="${y + hz / 2}" text-anchor="end" dominant-baseline="middle" style="fill:${an ? "var(--amber)" : "var(--ink-2)"}">${esc(kurzU(f.name).slice(0, 26))}</text>`;
      s += `<rect x="${a}" y="${y + 3}" width="${Math.max(1, b - a)}" height="${hz - 8}" fill="${an ? "var(--amber)" : v < 0 ? "var(--down)" : "var(--s3)"}" data-umk="${esc(f.id)}" style="cursor:pointer" data-tip="${esc(`<b>${esc(f.name)}</b>\n${esc(kzName(k))}: ${fmt(k, v)}\nMedian: ${fmt(k, md)}`)}"/><text x="${x1 + 6}" y="${y + hz / 2}" dominant-baseline="middle" style="fill:var(--ink)">${fmt(k, v)}</text>`; });
    return s + `<line x1="${sx(md)}" x2="${sx(md)}" y1="0" y2="${H}" stroke="var(--amber)" stroke-dasharray="3 3"/></svg>` +
      (z.length > 40 ? `<p class="n" style="margin:6px 0 0">Gezeigt: die 20 höchsten und die 20 niedrigsten von ${z.length} Werten.</p>` : "");
  }

  function profilTab(liste) {
    const andere = FIRMEN.filter(f => !liste.includes(f)), ks = Object.keys(KZU).filter(k => !["kurs", "marktkap"].includes(k) && KZU[k].fmt !== "mio" && werte(liste, k).length >= 2 && werte(andere, k).length >= 2);
    if (!andere.length || !ks.length) return `<p class="n">Zum Vergleich fehlen gemeinsame Kennzahlen mit anderen Branchen.</p>`;
    return `<div class="scroll"><table><thead><tr><th>Kennzahl</th><th>Median Auswahl</th><th>Median übrige</th><th>Abweichung</th></tr></thead><tbody>${ks.map(k => {
      const a = med(liste, k), b = med(andere, k), d = a != null && b != null ? a - b : null, pc = ["pct", "chg"].includes(KZU[k].fmt), h = KZU[k].hoch;
      const txt = d == null ? "–" : pc ? (d > 0 ? "+" : "") + f1.format(d * 100) + " Pp." : (d > 0 ? "+" : "") + f2.format(d) + (KZU[k].fmt === "x" ? "x" : "");
      const cl = d == null || h == null || Math.abs(d) < 1e-9 ? "" : (d > 0) === h ? "pos" : "neg";
      return `<tr><td>${esc(kzName(k))}</td><td>${fmt(k, a)}</td><td class="n">${fmt(k, b)}</td><td class="${cl}">${txt}</td></tr>`; }).join("")}</tbody></table></div>`;
  }

  function tabelleBranche(liste, b) {
    const ks = b ? schwerpunkt(b, liste, 5) : STREU_KZ.filter(k => hatL(liste, k)).slice(0, 5);
    const sp = [...(hatL(liste, "marktkap") ? ["marktkap"] : []), ...ks, ...(hatL(liste, "r_ytd") ? ["r_ytd"] : [])].filter((k, i, a) => a.indexOf(k) === i);
    if (!sp.includes(S.sort.k)) S.sort = { k: sp.includes("bilanzsumme") ? "bilanzsumme" : sp[0], ab: true };
    if (S.sort.auto !== S.branche + S.gruppe + S.notiert && !S.sort.manuell) S.sort = { k: sp.includes("bilanzsumme") ? "bilanzsumme" : sp[0], ab: true, auto: S.branche + S.gruppe + S.notiert };
    const sort = [...liste].sort((a, b2) => { const x = w(a, S.sort.k), y = w(b2, S.sort.k); if (x == null) return 1; if (y == null) return -1; return S.sort.ab ? y - x : x - y; });
    const meds = sp.map(k => med(liste, k)), spalte2 = S.branche === "alle" ? "Branche" : (b && b.gruppen.length ? "Gruppe" : null);
    return `<div class="tblwrap"><table class="kzt"><thead><tr><th>Unternehmen</th><th></th>${spalte2 ? `<th style='text-align:left'>${spalte2}</th>` : ""}${sp.map(k => `<th class="sortable" data-usort="${k}">${esc(kurzKz(k))}${S.sort.k === k ? (S.sort.ab ? " ▼" : " ▲") : ""}</th>`).join("")}<th></th></tr></thead>
      <tbody>${sort.map(f => `<tr class="click${f.id === S.markiert ? " sel" : ""}" data-umk="${esc(f.id)}"><td>${profilLink(f)}</td><td>${punkt(f)}</td>${spalte2 ? `<td class="n" style="text-align:left;font-family:var(--sans)">${esc(spalte2 === "Branche" ? brName(f.branche) : f.gruppe || "")}</td>` : ""}${sp.map(k => { const v = w(f, k); return `<td class="${v == null ? "n" : ["r_ytd", "w_umsatz", "w_jue", "w_bilanzsumme"].includes(k) ? klasse(v) : ""}">${fmt(k, v)}</td>`; }).join("")}<td><button type="button" class="mini" data-uadd="${esc(f.id)}" title="In den Vergleich übernehmen">+</button></td></tr>`).join("")}
      <tr><td style="color:var(--amber)">Median</td><td></td>${spalte2 ? "<td></td>" : ""}${meds.map((v, i) => `<td style="color:var(--amber)">${fmt(sp[i], v)}</td>`).join("")}<td></td></tr></tbody></table></div>`;
  }

  const BANK_ANALYSE = [["grp", "GRP", "Gruppen", "Kennzahlen und Kapitalstruktur je Bankengruppe"], ["quot", "QUOT", "Quoten", "Verteilung der Kapitalquoten, Streudiagramme"],
    ["cmp", "CMP", "Einzelbanken", "Banken frei kombinieren und vergleichen"], ["rank", "RANK", "Liste", "Rangliste aller Institute"],
    ["mkt", "MKT", "Börse", "Kurse und Bewertung der notierten Banken"], ["ts", "TS", "Zeitreihen", "Bilanzsumme, Eigenkapital, Ergebnis über mehrere Jahre"]];
  function bankenAnalyse() {
    return `<div class="tape">${BANK_ANALYSE.map(([h, c, n, t]) => `<a class="tile" href="#${h}" style="--gf:var(--amber)"><div class="g"><b>${n}</b><span>${c}</span></div><div class="mini">${t}</div></a>`).join("")}</div>`;
  }

  function viewBra() {
    const b = BR[S.branche] || null;
    if (b && S.gruppe !== "alle" && !b.gruppen.includes(S.gruppe)) S.gruppe = "alle";
    if (!b) S.gruppe = "alle";
    const basis = inBranche(S.branche);
    if (S.notiert !== "alle" && !(nNotiert(basis) && nNotiert(basis) < basis.length)) S.notiert = "alle";
    const liste = aktuelleListe(), rk = (b ? schwerpunkt(b, liste, 6) : STREU_KZ.filter(k => hatL(liste, k)));
    if (!S.rang || !hatL(liste, S.rang)) S.rang = rk[0];
    const kz = STREU_KZ.filter(k => hatL(liste, k));
    if (!kz.includes(S.sx)) S.sx = kz.find(k => k !== S.sy) || kz[0];
    if (!kz.includes(S.sy) || S.sy === S.sx) S.sy = kz.find(k => k !== S.sx) || kz[0];
    const marker = FIRMEN.find(f => f.id === S.markiert);
    mktMarkiert = marker ? marker.ticker : null;
    const ad = adapter(liste), g = groesse(liste);
    const ctrl = `<div class="ctrl" style="margin-bottom:6px">${Object.entries(FENSTER).map(([k, [n]]) => `<button type="button" data-fenster="${k}" aria-pressed="${k === mktFenster}">${n}</button>`).join("")}</div>`;
    const stats = [...(g ? [[g.k, g.n, g.k === "marktkap" || g.k === "bilanzsumme" ? mrd(g.v) : f0.format(g.v)]] : []), ...rk.slice(0, 4).map(k => [k, "Median " + kurzKz(k), fmt(k, med(liste, k))])];
    const titel = (b ? b.name : "Alle Unternehmen") + (S.gruppe !== "alle" ? " · " + S.gruppe : "");
    const nn = nNotiert(liste);
    return `<div class="grid">
      <div class="p" style="grid-column:span 12;border:0;background:none">${filterZeilen(b)}
        <div class="tape">${stats.map(([k, n, v]) => `<div style="--gf:var(--amber)"><div class="g"><b>${esc(n)}</b></div><div class="stats" style="grid-template-columns:1fr"><div><strong style="font-size:20px">${v}</strong></div></div></div>`).join("")}</div></div>
      ${b && b.analyse ? panel({ code: "BRA 0", titel: "Spezialansichten Banken", sub: "Aufsichtsrechtliche Kennzahlen, Kapitalstruktur, Börse, Zeitreihen", body: bankenAnalyse() }) : ""}
      ${panel({ code: "BRA 1", titel: titel, sub: `${liste.length} Unternehmen${nn ? ` · ${nn} börsennotiert (●)` : ""} · Name öffnet die Profilseite · Spaltenkopf sortiert · + übernimmt in den Vergleich`, body: tabelleBranche(liste, b),
        fuss: `${fuss(b)}${b && b.id === "banken" ? "HGB-Einzelabschlüsse, Mio. €; Eigenkapitalrendite = Jahresüberschuss / Eigenkapital." : "Konzernabschlüsse, Beträge in Mio. €."}` })}
      ${panel({ code: "BRA 2", titel: "Rangfolge", sub: `${esc(kzName(S.rang || ""))} · gestrichelt = Median`, breite: "w6", body: metrikWahl("data-urang", S.rang, liste, [...new Set([...rk, ...STREU_KZ])]) + rangU(S.rang, liste) })}
      ${panel({ code: "BRA 3", titel: "Profil gegen die übrigen Branchen", sub: "Median der Auswahl gegen Median aller anderen Unternehmen", breite: "w6", body: S.branche === "alle" ? `<p class="n">Eine Branche wählen.</p>` : profilTab(liste), fuss: "Grün/Rot bewertet nur Kennzahlen mit eindeutiger Richtung (z. B. Marge höher = besser, Verschuldung niedriger = besser)." })}
      ${ad.length > 1 ? panel({ code: "BRA 4", titel: "Kursentwicklung indexiert", sub: `Schlusskurs, Beginn des Zeitraums = 100 · ${ad.length} Aktien`, breite: "w6", body: ctrl + indexChart(ad), fuss: "Kurse in Landeswährung, nicht dividendenbereinigt." }) : ""}
      ${kz.length > 1 ? panel({ code: "BRA 5", titel: "Kennzahlen gegeneinander", sub: `Kreisfläche ∝ ${hatL(liste, "marktkap") ? "Börsenwert" : "Bilanzsumme"}`, breite: ad.length > 1 ? "w6" : "", body: `<div class="ctrl" style="margin-bottom:6px"><span>X</span></div>${metrikWahl("data-usx", S.sx, liste, STREU_KZ)}<div class="ctrl" style="margin-bottom:6px"><span>Y</span></div>${metrikWahl("data-usy", S.sy, liste, STREU_KZ)}${streuU(liste, S.sx, S.sy, "alle")}` }) : ""}
    </div>`;
  }

  /* ----- Vergleich einzelner Unternehmen ----- */
  function viewVgl() {
    if (!S.auswahl) { const top = [...FIRMEN].sort((a, b) => (w(b, "marktkap") || 0) - (w(a, "marktkap") || 0)); S.auswahl = []; const gesehen = new Set(); top.forEach(f => { if (S.auswahl.length < 4 && !gesehen.has(f.branche)) { gesehen.add(f.branche); S.auswahl.push(f.id); } }); }
    const cs = S.auswahl.map(n => NACH_ID[n]).filter(Boolean);
    const picks = `<div class="picks">${cs.map(f => `<span class="chip">${esc(kurzU(f.name))} <span class="pct">${esc(brName(f.branche))}</span><button type="button" data-uweg="${esc(f.id)}" aria-label="${esc(f.name)} entfernen">×</button></span>`).join("")}
      <input id="uadd" list="firmenliste" placeholder="+ Unternehmen hinzufügen (max. 6)" autocomplete="off" ${cs.length >= 6 ? "disabled" : ""}></div>`;
    const peers = f => inBranche(f.branche);
    const zeilen = UD.gruppen.map(g => { const ks = UD.kennzahlen.filter(k => k.gruppe === g && cs.some(f => w(f, k.key) != null)); if (!ks.length) return "";
      return `<tr><td colspan="${cs.length + 1}" class="grp">${esc(g)}</td></tr>` + ks.map(k => `<tr><td>${esc(k.name)}${k.einheit ? ` <span class="pct">${esc(k.einheit)}</span>` : ""}</td>${cs.map(f => { const v = w(f, k.key); if (v == null) return `<td class="n">n. v.</td>`;
          const alle = werte(peers(f), k.key), p = alle.length >= 3 ? perzentil(v, alle) : null;
          return `<td>${fmt(k.key, v)} ${p == null ? "" : `<span class="pct" title="Perzentil unter den ${alle.length} Unternehmen der Branche">P${f0.format(p * 100).padStart(2, "0")}</span>`}</td>`; }).join("")}</tr>`).join(""); }).join("");
    const matrixT = cs.length ? `<div class="scroll"><table class="kzt"><thead><tr><th>Kennzahl</th>${cs.map(f => `<th title="${esc(f.name)}">${profilLink(f, kurzU(f.name).slice(0, 16))}</th>`).join("")}</tr></thead><tbody>${zeilen}</tbody></table></div>` : `<p class="n">Unternehmen hinzufügen.</p>`;
    const bars = ["ebit_marge", "roe", "ek_quote", "verschuldung", "kgv", "div_rendite", "w_umsatz", "bilanzsumme"].filter(k => cs.some(f => w(f, k) != null)).map(k => `<div><div class="sub-h">${esc(kzName(k))}</div>${balkenU(k, cs)}</div>`).join("");
    const ad = adapter(cs), marker = cs[0];
    mktMarkiert = marker ? marker.ticker : null;
    const ctrl = `<div class="ctrl" style="margin-bottom:6px">${Object.entries(FENSTER).map(([k, [n]]) => `<button type="button" data-fenster="${k}" aria-pressed="${k === mktFenster}">${n}</button>`).join("")}</div>`;
    return `<div class="grid">
      ${panel({ code: "UCMP", titel: "Auswahl", sub: "Unternehmen aus allen Branchen frei kombinieren · + in der Branchenansicht oder Suche in der Kommandozeile", body: picks })}
      ${panel({ code: "UCMP 1", titel: "Kennzahlenmatrix", sub: "P = Perzentil in der eigenen Branche (P99 = höchster Wert) · Name öffnet die Profilseite", breite: "w7", body: matrixT, fuss: `${fuss()}Banken: HGB-Einzelabschluss; übrige Unternehmen Konzernabschluss. Werte verschiedener Rechnungslegung sind nur bedingt vergleichbar.` })}
      ${panel({ code: "UCMP 2", titel: "Gegen den Branchenmedian", sub: "Balken = Unternehmen, Strich = Median der eigenen Branche", breite: "w5", body: `<div style="display:grid;gap:8px">${bars}</div>` })}
      ${ad.length > 1 ? panel({ code: "UCMP 3", titel: "Kursentwicklung indexiert", sub: "Beginn des Zeitraums = 100", body: ctrl + indexChart(ad) }) : ""}
    </div>`;
  }
  function balkenU(k, cs) {
    const W = 520, x0 = 170, x1 = W - 74, hz = 19, z = cs.map(f => ({ f, v: w(f, k), md: med(inBranche(f.branche), k) }));
    const lo = Math.min(0, ...z.map(x => Math.min(x.v ?? 0, x.md ?? 0))), hi = Math.max(0, ...z.map(x => Math.max(x.v ?? 0, x.md ?? 0))) || 1, sx = v => x0 + (x1 - x0) * (v - lo) / ((hi - lo) || 1), H = z.length * hz + 4;
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img">`;
    z.forEach(({ f, v, md }, i) => { const y = i * hz + 2;
      s += `<text x="${x0 - 6}" y="${y + hz / 2}" text-anchor="end" dominant-baseline="middle">${esc(kurzU(f.name).slice(0, 24))}</text>`;
      if (v == null) { s += `<text x="${x0}" y="${y + hz / 2}" dominant-baseline="middle" style="fill:var(--ink-3)">n. v.</text>`; return; }
      s += `<rect x="${Math.min(sx(0), sx(v))}" y="${y + 3}" width="${Math.max(1, Math.abs(sx(v) - sx(0)))}" height="${hz - 7}" fill="${v < 0 ? "var(--down)" : "var(--s3)"}" data-tip="${esc(`<b>${esc(f.name)}</b>\n${esc(kzName(k))}: ${fmt(k, v)}\nMedian ${esc(brName(f.branche))}: ${fmt(k, md)}`)}"/>`;
      if (md != null) s += `<line x1="${sx(md)}" x2="${sx(md)}" y1="${y + 1}" y2="${y + hz - 2}" stroke="var(--amber)" stroke-width="2"/>`;
      s += `<text x="${x1 + 6}" y="${y + hz / 2}" dominant-baseline="middle" style="fill:var(--ink)">${fmt(k, v)}</text>`; });
    return s + "</svg>";
  }

  /* ----- Profilseite eines Unternehmens ----- */
  function reiheSvg(key, r) {
    const p = r.punkte, W = 300, H = 130, x0 = 8, x1 = W - 8, y0 = 22, y1 = H - 20;
    const lo = Math.min(0, ...p.map(x => x[1])), hi = Math.max(0, ...p.map(x => x[1])) || 1, sy = v => y1 - (y1 - y0) * (v - lo) / ((hi - lo) || 1), bw = (x1 - x0) / p.length;
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img"><line x1="${x0}" x2="${x1}" y1="${sy(0)}" y2="${sy(0)}" stroke="var(--ink-3)"/>`;
    p.forEach(([j, v], i) => { const x = x0 + i * bw + bw * .18, last = i === p.length - 1, a = Math.min(sy(0), sy(v)), h = Math.max(1, Math.abs(sy(v) - sy(0)));
      s += `<rect x="${x}" y="${a}" width="${bw * .64}" height="${h}" fill="${last ? "var(--amber)" : v < 0 ? "var(--down)" : "var(--s3)"}" data-tip="${esc(`<b>${j}</b>\n${esc(kzName(key))}: ${fmt(key, v)}\n${esc(r.basis)}`)}"/>`;
      s += `<text x="${x + bw * .32}" y="${v >= 0 ? a - 4 : a + h + 11}" text-anchor="middle" style="font-size:10px;fill:var(--ink)">${fmt(key, v)}</text><text x="${x + bw * .32}" y="${H - 5}" text-anchor="middle" style="font-size:10px">${j}</text>`; });
    return s + "</svg>";
  }

  const dokUrl = (pfad, art) => `https://github.com/${UD.repo}/${art}/${UD.zweig}/${pfad.split("/").map(encodeURIComponent).join("/")}`;
  function dokumentePanel(f) {
    const d = f.dokumente || [];
    if (!d.length) return panel({ code: "DOK", titel: "Dokumente", body: `<p class="n">Zu diesem Unternehmen liegen noch keine Dokumente im Repo. Ablage: <code>…/dokumente/${esc(f.id)}/</code> (PDF, HTML-Sicherungen) oder ein Eintrag in der <code>index.csv</code> der Erhebung.</p>` });
    const typen = [...new Set(d.map(x => x.typ))].sort();
    if (S.dokTyp !== "alle" && !typen.includes(S.dokTyp)) S.dokTyp = "alle";
    const zeigen = S.dokTyp === "alle" ? d : d.filter(x => x.typ === S.dokTyp);
    const chips = typen.length > 1 ? chipRow([["alle", "Alle", d.length], ...typen.map(t => [t, t, d.filter(x => x.typ === t).length])], "data-udok", S.dokTyp) : "";
    return panel({ code: "DOK", titel: "Dokumente", sub: `${d.length} Datei${d.length === 1 ? "" : "en"} im Repo · Download und Ansicht über GitHub`, body: chips +
      `<div class="scroll"><table><thead><tr><th style="text-align:left">Jahr</th><th style="text-align:left">Art</th><th style="text-align:left">Dokument</th><th>Größe</th><th style="text-align:left">Quelle</th><th></th></tr></thead><tbody>${zeigen.map(x => `<tr><td>${x.jahr || "–"}</td><td style="text-align:left;font-family:var(--sans)">${esc(x.typ)}</td>
        <td style="text-align:left;font-family:var(--sans)" title="${esc(x.pfad)}">${esc(x.titel)}<div class="pct">${esc(x.pfad)}${x.sha256 ? ` · SHA-256 ${esc(x.sha256.slice(0, 10))}…` : ""}</div></td><td class="n">${mb(x.kb)}</td>
        <td style="text-align:left;font-family:var(--sans)">${x.url ? `<a class="flink" href="${esc(x.url)}" target="_blank" rel="noopener">Original${x.abruf ? ` (${esc(x.abruf.replace(/^Download /, ""))})` : ""}</a>` : "–"}</td>
        <td style="white-space:nowrap"><a class="btn" href="${esc(dokUrl(x.pfad, "raw"))}" target="_blank" rel="noopener" download>Download</a> <a class="btn" href="${esc(dokUrl(x.pfad, "blob"))}" target="_blank" rel="noopener">GitHub</a></td></tr>`).join("")}</tbody></table></div>`,
      fuss: "Die Dateien liegen im GitHub-Repo; je nach Repo-Einstellung ist dafür eine Anmeldung mit Zugriff nötig. Der Pfad zeigt den Speicherort im Repo." });
  }

  function viewProfil(id) {
    const f = NACH_ID[id];
    if (!f) return `<div class="grid">${panel({ code: "UNT", titel: "Unternehmen nicht gefunden", body: `<p>Kein Unternehmen mit der Kennung <code>${esc(id)}</code>. <a class="flink" href="#u-verzeichnis">Zum Verzeichnis</a></p>` })}</div>`;
    S.profil = id;
    const b = BR[f.branche], peers = inBranche(f.branche), gp = f.gruppe ? peers.filter(x => x.gruppe === f.gruppe) : [];
    const kzs = UD.kennzahlen.filter(k => w(f, k.key) != null);
    const kachel = (k, label) => `<div style="--gf:var(--amber)"><div class="g"><b>${esc(label || kurzKz(k))}</b></div><div class="stats" style="grid-template-columns:1fr"><div><strong style="font-size:20px">${fmt(k, w(f, k))}</strong></div></div></div>`;
    const top = ["marktkap", "bilanzsumme", "umsatz", "ek_quote", "cet1_quote", "roe", "ebit_marge", "kgv", "div_rendite"].filter(k => w(f, k) != null).slice(0, 5);
    const ad = kurseVon(f);
    mktMarkiert = ad ? ad.ticker : null;
    const ctrl = `<div class="ctrl" style="margin-bottom:6px">${Object.entries(FENSTER).map(([k, [n]]) => `<button type="button" data-fenster="${k}" aria-pressed="${k === mktFenster}">${n}</button>`).join("")}</div>`;
    const kopf = `<div class="picks" style="margin-bottom:10px"><a class="flink" href="#u-ueb">Branchen</a> › <a class="flink" href="#u-branche" data-uopen="${esc(f.branche)}">${esc(b.name)}</a>${f.gruppe ? ` › <a class="flink" href="#u-branche" data-uopen="${esc(f.branche)}" data-ugruppe="${esc(f.gruppe)}">${esc(f.gruppe)}</a>` : ""}</div>
      <div class="picks"><h2 style="margin:0;font:600 22px/1.2 var(--sans)">${esc(f.name)}</h2>
        <span class="chip" style="cursor:default">${f.notiert ? `börsennotiert${f.ticker ? " · " + esc(f.ticker) : ""}${f.isin ? " · " + esc(f.isin) : ""}` : "nicht börsennotiert"}</span>
        ${f.mutter ? `<span class="chip" style="cursor:default">Börsenkurs nur der Mutter: ${esc(f.mutter.name || f.mutter.ticker)}</span>` : ""}
        ${f.sitz ? `<span class="chip" style="cursor:default">${esc(f.sitz)}</span>` : ""}${f.rolle ? `<span class="chip" style="cursor:default">${esc(f.rolle)}</span>` : ""}${f.demo ? `<span class="chip" style="cursor:default">Beispieldaten</span>` : ""}
        <button type="button" class="mini" data-uadd="${esc(f.id)}">+ Vergleich</button>${f.bank ? ` <button type="button" class="mini" data-bank="${esc(f.bank)}">+ Banken-Vergleich</button>` : ""}</div>`;
    const reihen = Object.entries(f.reihen || {}).filter(([k, r]) => r.punkte.length >= 2);
    const gruppen = UD.gruppen.map(g => {
      const ks = kzs.filter(k => k.gruppe === g); if (!ks.length) return "";
      return `<tr><td colspan="5" class="grp">${esc(g)}</td></tr>` + ks.map(k => { const v = w(f, k.key), a = werte(peers, k.key), p = a.length >= 3 ? perzentil(v, a) : null;
        return `<tr><td>${esc(k.name)}${k.einheit ? ` <span class="pct">${esc(k.einheit)}</span>` : ""}</td><td>${fmt(k.key, v)}</td><td class="n">${fmt(k.key, median(a))}</td><td class="n">${gp.length > 2 ? fmt(k.key, med(gp, k.key)) : "–"}</td><td class="n">${p == null ? "–" : "P" + f0.format(p * 100).padStart(2, "0")}</td></tr>`; }).join("");
    }).join("");
    return `<div class="grid">
      <div class="p" style="grid-column:span 12;border:0;background:none">${kopf}<div class="tape" style="margin-top:12px">${top.map(k => kachel(k)).join("")}</div></div>
      ${panel({ code: "UNT 1", titel: "Kennzahlen", sub: `Median und Perzentil im Vergleich zu ${peers.length} Unternehmen der Branche ${esc(b.name)}`, breite: "w7", body: kzs.length ? `<div class="scroll"><table class="kzt"><thead><tr><th>Kennzahl</th><th>Wert</th><th>Median Branche</th><th>${f.gruppe ? "Median " + esc(f.gruppe) : "Median Gruppe"}</th><th>Rang</th></tr></thead><tbody>${gruppen}</tbody></table></div>` : `<p class="n">Noch keine Kennzahlen erhoben.</p>`,
        fuss: `${f.abschluss ? esc(f.abschluss) + ". " : ""}${f.demo ? "Beispieldaten aus Yahoo Finance. " : ""}Beträge in Mio. €; P99 = höchster Wert der Branche.` })}
      <div class="col w5">${ad ? panel({ code: "UNT 2", titel: "Kursentwicklung", sub: `${esc(f.ticker)} · Beginn des Zeitraums = 100`, body: ctrl + indexChart([ad]) }) : panel({ code: "UNT 2", titel: "Börse", body: `<p class="n">${f.notiert ? "Keine Kurse im Datensatz." : "Nicht börsennotiert: keine Kurs- und Bewertungskennzahlen."}</p>` })}</div>
      ${reihen.length ? panel({ code: "UNT 3", titel: "Zeitreihen", sub: "je Kennzahl über die erhobenen Stichtage, Amber = jüngster Wert", body: `<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px">${reihen.map(([k, r]) => `<div><div class="sub-h">${esc(kzName(k))} <span class="pct">${esc(r.basis)}</span></div>${reiheSvg(k, r)}</div>`).join("")}</div>`, fuss: "Rechnungslegung und Konsolidierungsebene stehen je Reihe; Reihen verschiedener Basis werden nicht vermischt." }) : ""}
      ${dokumentePanel(f)}
    </div>`;
  }

  /* ----- Verzeichnis aller Unternehmen ----- */
  function viewVerz() {
    const zeilen = [...FIRMEN].sort((a, b) => a.name.localeCompare(b.name, "de"));
    return `<div class="grid">${panel({ code: "VERZ", titel: "Verzeichnis", sub: `${FIRMEN.length} Unternehmen · Suche nach Name, Ticker oder Gruppe`, body:
      `<div class="picks" style="margin-bottom:12px"><input id="usuche" placeholder="Suchen …" autocomplete="off" style="width:320px"><select id="ubr"><option value="">Alle Branchen</option>${UD.branchen.map(b => `<option value="${esc(b.id)}">${esc(b.name)}</option>`).join("")}</select>
        <select id="unot"><option value="">Notiert und nicht notiert</option><option value="1">Börsennotiert</option><option value="0">Nicht börsennotiert</option></select><span class="n" id="uzahl"></span></div>
      <div class="tblwrap"><table class="kzt"><thead><tr><th>Unternehmen</th><th></th><th style="text-align:left">Branche</th><th style="text-align:left">Gruppe</th><th>Dokumente</th><th>Jahre</th></tr></thead><tbody id="uverz">${zeilen.map(f => {
        const jahre = Math.max(0, ...Object.values(f.reihen || {}).map(r => r.punkte.length));
        return `<tr data-q="${esc((f.name + " " + (f.ticker || "") + " " + (f.gruppe || "") + " " + (f.isin || "")).toLowerCase())}" data-b="${esc(f.branche)}" data-n="${f.notiert ? 1 : 0}"><td>${profilLink(f, f.name)}</td><td>${punkt(f)}</td><td class="n" style="text-align:left;font-family:var(--sans)">${esc(brName(f.branche))}</td><td class="n" style="text-align:left;font-family:var(--sans)">${esc(f.gruppe || "")}</td><td class="${(f.dokumente || []).length ? "" : "n"}">${(f.dokumente || []).length || "–"}</td><td class="n">${jahre || "–"}</td></tr>`; }).join("")}</tbody></table></div>` })}</div>`;
  }
  function verzFilter() {
    const q = (document.getElementById("usuche") || {}).value, br = (document.getElementById("ubr") || {}).value, nt = (document.getElementById("unot") || {}).value;
    let n = 0;
    document.querySelectorAll("#uverz tr").forEach(tr => { const ok = (!q || tr.dataset.q.includes(q.toLowerCase())) && (!br || tr.dataset.b === br) && (!nt || tr.dataset.n === nt); tr.hidden = !ok; if (ok) n++; });
    const z = document.getElementById("uzahl"); if (z) z.textContent = n + " angezeigt";
  }

  /* ----- Bedienung ----- */
  function hinzu(id) { if (!S.auswahl) viewVgl(); if (!S.auswahl.includes(id)) { S.auswahl.push(id); if (S.auswahl.length > 6) S.auswahl.shift(); } }
  function finden(q) { q = (q || "").trim().toLowerCase(); if (!q || !UD) return null; return FIRMEN.find(f => f.name.toLowerCase() === q || f.id === q) || FIRMEN.find(f => (f.ticker || "").toLowerCase() === q || (f.isin || "").toLowerCase() === q) || FIRMEN.find(f => f.name.toLowerCase().includes(q)); }
  function klick(t) {
    const g = a => { const e = t.closest && t.closest("[" + a + "]"); return e ? e.getAttribute(a) : null; };
    let v;
    if ((v = g("data-uadd")) != null) { hinzu(v); gehe("u-vergleich"); return true; }
    if ((v = g("data-uweg")) != null) { S.auswahl = S.auswahl.filter(x => x !== v); render(); return true; }
    if ((v = g("data-ub")) != null) { S.branche = v; S.gruppe = "alle"; S.notiert = "alle"; S.rang = null; render(); return true; }
    if ((v = g("data-ug")) != null) { S.gruppe = v; render(); return true; }
    if ((v = g("data-un")) != null) { S.notiert = v; render(); return true; }
    if ((v = g("data-udok")) != null) { S.dokTyp = v; render(); return true; }
    if ((v = g("data-uopen")) != null) { S.branche = v; S.gruppe = g("data-ugruppe") || "alle"; S.notiert = "alle"; S.rang = null; gehe("u-branche"); return true; }
    if ((v = g("data-usort")) != null) { S.sort = { k: v, ab: S.sort.k === v ? !S.sort.ab : true, manuell: true, auto: S.branche + S.gruppe + S.notiert }; render(); return true; }
    if ((v = g("data-umatrix")) != null) { S.matrixSort = v; render(); return true; }
    if ((v = g("data-urang")) != null) { S.rang = v; render(); return true; }
    if ((v = g("data-usx")) != null) { S.sx = v; render(); return true; }
    if ((v = g("data-usy")) != null) { S.sy = v; render(); return true; }
    if ((v = g("data-ussx")) != null) { S.usx = v; render(); return true; }
    if ((v = g("data-ussy")) != null) { S.usy = v; render(); return true; }
    if (t.closest && t.closest("a.flink, a.btn, a.tile")) return false;       // Links laufen über den Hash
    if ((v = g("data-umk")) != null) { S.markiert = S.markiert === v ? null : v; render(); return true; }
    return false;
  }
  function nachRender() {
    const a = document.getElementById("uadd");
    if (a) a.addEventListener("change", () => { const f = finden(a.value); if (f) { hinzu(f.id); render(); } });
    ["usuche", "ubr", "unot"].forEach(i => { const e = document.getElementById(i); if (e) e.addEventListener("input", verzFilter); });
    if (document.getElementById("uverz")) verzFilter();
  }
  const datalist = () => UD ? FIRMEN.map(f => `<option value="${esc(f.name)}">`).join("") : "";
  const meta = () => UD ? `${FIRMEN.length} Unternehmen · ${nNotiert(FIRMEN)} börsennotiert · ${UD.branchen.length} Branchen${UD.demo ? " · teils Beispieldaten" : ""}` : "";
  return { init, da, viewUeb, viewBra, viewVgl, viewProfil, viewVerz, klick, nachRender, datalist, finden, hinzu, meta, existiert: id => !!NACH_ID[id] };
})();
