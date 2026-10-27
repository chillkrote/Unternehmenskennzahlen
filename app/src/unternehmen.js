/* ---------- Unternehmen aller Branchen (Banken sind eine Branche unter vielen) ----------
   Daten: UD = { demo, repo, zweig, quellen, gruppen, branchen[], kennzahlen[], unternehmen[] } (siehe unternehmen.py).
   Je Unternehmen: id, name, branche, gruppe?, notiert, werte{}, reihen{}?, dokumente[]?, ticker?, kurse?.
   Läuft vor dem Hauptskript; nutzt dessen Hilfsfunktionen (panel, pct, median, ...) erst zur Laufzeit. */
"use strict";
const UNT = (() => {
  let hoverBereit = false;
  let UD = null, KZU = {}, BR = {}, FIRMEN = [], NACH_ID = {};
  const S = { branche: "alle", gruppe: "alle", notiert: "alle", markiert: null, sort: { k: "marktkap", ab: true }, rang: null, tBranche: "alle", tZeit: "90", tArt: "alle",
    sx: "ebit_marge", sy: "kgv", usx: "kgv", usy: "ebit_marge", auswahl: null, matrixSort: null, dokTyp: "alle" };

  /* ----- Aufbereitung ----- */
  function init(d) {
    UD = d && d.unternehmen && d.unternehmen.length ? d : null;
    if (!UD) return false;
    KZU = Object.fromEntries(UD.kennzahlen.map(k => [k.key, k]));
    BR = Object.fromEntries(UD.branchen.map(b => [b.id, b]));
    FIRMEN = UD.unternehmen.filter(f => BR[f.branche]);
    NACH_ID = Object.fromEntries(FIRMEN.map(f => [f.id, f]));
    if (!hoverBereit) { hoverBereit = true; hoverVerdrahten(); }
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
  /* Kurse für die Korrelationsauswertung: täglich (kurse_hist in markt.json, Banken), sonst Wochenkurse aller Notierten (kurse_woche.json), sonst der Verlauf der Ansichten */
  let wochenIdx = null;
  function kurseHist(f) {
    const m = f.ticker && typeof MARKT !== "undefined" && MARKT && MARKT.werte.find(x => x.ticker === f.ticker);
    if (m && m.kurse_hist && m.kurse_hist.length > 1) return { ticker: f.ticker, kurse: m.kurse_hist, waehrung: m.waehrung, freq: "D" };
    if (f.ticker && typeof KURSE !== "undefined" && KURSE && KURSE.t[f.ticker]) {
      const v = KURSE.t[f.ticker], pts = [];
      for (let i = 0; i < v.length; i++) if (v[i] != null) pts.push([KURSE.daten[i], v[i]]);
      if (pts.length > 1) return { ticker: f.ticker, kurse: pts, freq: "W" };
    }
    const k = kurseVon(f);
    return k ? { ...k, freq: "D" } : null;
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
    return `<div class="scroll"><table class="hov"><thead><tr><th>Branche</th>${kopf("n", "n")}<th>notiert</th>${kopf("mk", "Σ Börsenwert")}${spalten.map(k => `<th class="sortable" data-umatrix="${k}" title="${esc(kzName(k))}">${esc(kurzKz(k))}${sk === k ? " ▼" : ""}</th>`).join("")}</tr></thead>
      <tbody>${zeilen.map(z => `<tr class="click" data-uopen="${esc(z.id)}"><td>${esc(z.name)}</td><td class="n">${z.n}</td><td class="n">${z.nn || "–"}</td><td>${z.mk ? mrd(z.mk) : "–"}</td>${spalten.map(k => zelle(z, k)).join("")}</tr>`).join("")}</tbody></table></div>`;
  }

  /* ----- Interaktives Streudiagramm -----
     Hover (nächster Punkt im Umkreis, Rest tritt zurück), Tooltip, Klick öffnet das Profil, Legende schaltet Branchen,
     Rad zoomt, Ziehen verschiebt, Doppelklick setzt zurück, Suche markiert ein Unternehmen. Nach dem Aufbau wird nichts
     mehr über render() neu gezeichnet; Hover und Zoom ändern nur Attribute und Klassen. */
  const BR_FARBE = ["#ffa828", "#4aa3ff", "#2fc4a0", "#a98bf0", "#f0627a", "#8ccf4a", "#6ad0e8", "#e07fd0", "#c28a5a", "#8aa0b8", "#5f7be0", "#d9d0a0"];
  const brFarbe = id => { const i = UD.branchen.findIndex(b => b.id === id); return BR_FARBE[(i < 0 ? 0 : i) % BR_FARBE.length]; };
  const SCAT = {}, SCST = {};      // id -> Konfiguration (wird beim Aufbau der Seite gefüllt, beim Einhängen gelesen)
  const SVGNS = "http://www.w3.org/2000/svg";
  function streuU(liste, kx, ky, hervor, hervorG, opt = {}) {
    const pts = liste.filter(f => w(f, kx) != null && w(f, ky) != null);
    if (pts.length < 3 || !KZU[kx] || !KZU[ky]) return `<p class="n">Zu wenige Werte für diese Kombination.</p>`;
    const id = "sc" + (opt.id || "x");
    SCAT[id] = { pts, kx, ky, hervor, hervorG, legende: !!opt.legende };
    const brs = opt.legende ? UD.branchen.map(b => [b, pts.filter(f => f.branche === b.id).length]).filter(x => x[1]) : [];
    return `<div class="uscat" id="${id}" data-sc="${id}">
      <div class="sc-bar"><input type="search" class="sc-find" list="firmenliste" placeholder="Unternehmen suchen …" aria-label="Unternehmen im Streudiagramm suchen" autocomplete="off">
        <button type="button" class="sc-reset" hidden>Zoom zurücksetzen</button><span class="sc-info">Mausrad zoomt · Ziehen verschiebt · Klick öffnet das Profil</span></div>
      ${brs.length ? `<div class="sc-legend" role="group" aria-label="Branchen ein- oder ausblenden">${brs.map(([b, n]) =>
        `<button type="button" class="sc-chip" data-scb="${esc(b.id)}" aria-pressed="true" title="Klick blendet aus, Doppelklick zeigt nur diese Branche"><i style="background:${brFarbe(b.id)}"></i>${esc(b.name)} <span>${n}</span></button>`).join("")}</div>` : ""}
      <div class="sc-plot"></div></div>`;
  }
  function scatterInit(el) {
    const c = SCAT[el.dataset.sc]; if (!c || el._init) return; el._init = true;
    const { pts, kx, ky } = c, plot = el.querySelector(".sc-plot"), info = el.querySelector(".sc-info"), reset = el.querySelector(".sc-reset"), find = el.querySelector(".sc-find");
    const sk = pts.some(f => w(f, "marktkap")) ? "marktkap" : pts.some(f => w(f, "bilanzsumme")) ? "bilanzsumme" : null;
    const mk = sk ? Math.max(...pts.map(f => w(f, sk) || 0)) || 1 : 1, rad = f => sk ? 3.5 + 9 * Math.sqrt((w(f, sk) || 0) / mk) : 4.5;
    const rg = k => { const xs = pts.map(f => w(f, k)), lo = quant(xs, .03), hi = quant(xs, .97), p = (hi - lo) * .12 || .1; return [lo - p, hi + p]; };
    const home = { x: rg(kx), y: rg(ky) };
    const merk = SCST[el.id] || (SCST[el.id] = { hide: new Set(), find: null, achsen: "", dom: null }), achsen = kx + "|" + ky;
    if (merk.achsen !== achsen) { merk.achsen = achsen; merk.dom = null; }       // Achsenwechsel setzt den Zoom zurück, Legende und Suche bleiben
    const st = { dom: merk.dom, hide: merk.hide, hot: null, brHot: null, find: merk.find, W: 0, H: 0 };
    const farbe = f => c.legende ? brFarbe(f.branche) : (f.branche === c.hervor && c.hervor !== "alle" ? "var(--amber)" : "var(--s3)");
    const dim = f => c.hervor !== "alle" && c.legende && !(f.branche === c.hervor && (!c.hervorG || c.hervorG === "alle" || f.gruppe === c.hervorG));
    const tk = k => t => KZU[k].fmt === "pct" || KZU[k].fmt === "chg" ? nf(0).format(t * 100) + " %" : KZU[k].fmt === "x" ? f1.format(t) + "x" : f0.format(t);
    const tipText = f => `<b>${esc(f.name)}</b>\n${esc(brName(f.branche))}${f.gruppe ? " · " + esc(f.gruppe) : ""}\n${esc(kzName(kx))}: ${fmt(kx, w(f, kx))}\n${esc(kzName(ky))}: ${fmt(ky, w(f, ky))}${sk && w(f, sk) != null ? `\n${esc(kzName(sk))}: ${sk === "marktkap" || sk === "bilanzsumme" ? mrd(w(f, sk)) : fmt(sk, w(f, sk))}` : ""}\nKlick: Profil öffnen`;
    const M = { l: 50, r: 16, t: 16, b: 32 };
    let svg, circles = [], axes, top, X = [], Y = [], sicht = [];
    const dom = () => st.dom || home;
    const sx = v => { const [lo, hi] = dom().x; const t = (v - lo) / (hi - lo); return M.l + (st.W - M.l - M.r) * (st.dom ? t : Math.min(Math.max(t, 0), 1)); };
    const sy = v => { const [lo, hi] = dom().y; const t = (v - lo) / (hi - lo); return st.H - M.b - (st.H - M.t - M.b) * (st.dom ? t : Math.min(Math.max(t, 0), 1)); };
    const el_ = (n, a) => { const e = document.createElementNS(SVGNS, n); for (const k in a) e.setAttribute(k, a[k]); return e; };

    function layout() {
      st.W = Math.max(300, Math.round(plot.clientWidth || 720)); st.H = Math.round(Math.min(560, Math.max(300, st.W * .56)));
      plot.innerHTML = `<svg viewBox="0 0 ${st.W} ${st.H}" width="${st.W}" height="${st.H}" role="img" aria-label="Streudiagramm ${esc(kzName(kx))} gegen ${esc(kzName(ky))}"><defs><clipPath id="${el.id}-clip"><rect x="${M.l}" y="${M.t - 4}" width="${st.W - M.l - M.r}" height="${st.H - M.t - M.b + 8}"/></clipPath></defs><g class="sc-axes"></g><g class="sc-pts" clip-path="url(#${el.id}-clip)"></g><g class="sc-top" style="pointer-events:none"></g></svg>`;
      svg = plot.firstChild; axes = svg.querySelector(".sc-axes"); top = svg.querySelector(".sc-top");
      const g = svg.querySelector(".sc-pts");
      const ord = [...pts].sort((a, b) => (w(b, sk) || 0) - (w(a, sk) || 0));       // große zuerst, kleine liegen oben
      circles = ord.map(f => { const e = el_("circle", { r: rad(f), fill: farbe(f), "fill-opacity": dim(f) ? .22 : .62, stroke: "var(--panel)", "stroke-width": 1.2, class: "pt" }); g.appendChild(e); return { f, e, r: rad(f) }; });
      place();
    }
    /* Positionen, Achsen und Sichtbarkeit neu setzen (Zoom, Verschieben, Legende) */
    function place() {
      const d = dom(); let s = "";
      niceTicks(d.x[0], d.x[1], Math.max(3, Math.round(st.W / 100))).forEach(t => { const x = sx(t); if (x < M.l - 1 || x > st.W - M.r + 1) return; s += `<line class="gl" x1="${x}" x2="${x}" y1="${M.t}" y2="${st.H - M.b}"/><text x="${x}" y="${st.H - M.b + 15}" text-anchor="middle">${tk(kx)(t)}</text>`; });
      niceTicks(d.y[0], d.y[1], 6).forEach(t => { const y = sy(t); if (y < M.t - 1 || y > st.H - M.b + 1) return; s += `<line class="gl" x1="${M.l}" x2="${st.W - M.r}" y1="${y}" y2="${y}"/><text x="${M.l - 6}" y="${y}" text-anchor="end" dominant-baseline="middle">${tk(ky)(t)}</text>`; });
      s += `<text x="${st.W - M.r}" y="${st.H - 3}" text-anchor="end" style="fill:var(--amber)">${esc(kzName(kx))} →</text><text x="${M.l}" y="${M.t - 5}" style="fill:var(--amber)">↑ ${esc(kzName(ky))}</text>`;
      axes.innerHTML = s;
      sicht = [];
      for (const o of circles) {
        const x = sx(w(o.f, kx)), y = sy(w(o.f, ky)), an = !st.hide.has(o.f.branche) && (!st.dom || (x >= M.l - o.r && x <= st.W - M.r + o.r && y >= M.t - o.r && y <= st.H - M.b + o.r));
        o.x = x; o.y = y; o.an = an;
        o.e.setAttribute("cx", x); o.e.setAttribute("cy", y); o.e.style.display = an ? "" : "none";
        if (an) sicht.push(o);
      }
      merk.dom = st.dom; merk.find = st.find; reset.hidden = !st.dom;
      info.textContent = `${sicht.length} von ${pts.length} Unternehmen sichtbar${st.dom ? " · gezoomt" : ""}`;
      markieren();
    }
    /* Hervorhebung: oberste Ebene mit vergrößertem Punkt und Beschriftung, übrige Punkte treten zurück */
    function markieren() {
      top.innerHTML = "";
      const hat = st.hot || st.find;
      svg.classList.toggle("has-hot", !!st.hot);
      svg.classList.toggle("has-br", !!st.brHot && !st.hot);
      for (const o of circles) o.e.classList.toggle("brhot", !!st.brHot && o.f.branche === st.brHot);
      const zeige = (id, ring) => {
        const o = circles.find(x => x.f.id === id && x.an); if (!o) return;
        top.appendChild(el_("circle", { cx: o.x, cy: o.y, r: o.r * (ring ? 1.25 : 1.5) + 2, fill: ring ? "none" : farbe(o.f), "fill-opacity": 1, stroke: ring ? "var(--key)" : "var(--ink)", "stroke-width": ring ? 2 : 1.5 }));
        const t = el_("text", { x: o.x + o.r * 1.5 + 6, y: o.y - 2, "dominant-baseline": "middle", style: "font-size:12px;font-weight:600;paint-order:stroke;stroke:var(--panel);stroke-width:4px;stroke-linejoin:round;fill:" + (ring ? "var(--key)" : "var(--ink)") });
        t.textContent = kurzU(o.f.name);
        top.appendChild(t);
        const bb = t.getBBox(); if (bb.x + bb.width > st.W - 4) { t.setAttribute("x", o.x - o.r * 1.5 - 6); t.setAttribute("text-anchor", "end"); }
      };
      if (st.find && st.find !== st.hot) zeige(st.find, true);
      if (st.hot) zeige(st.hot, false);
      if (!hat && !st.brHot) {                                                   // Ruhezustand: die größten Unternehmen beschriften
        sicht.filter(o => !dim(o.f)).sort((a, b) => b.r - a.r).slice(0, st.W < 500 ? 4 : 8).forEach(o => {
          const t = el_("text", { x: o.x + o.r + 3, y: o.y, "dominant-baseline": "middle", style: "fill:var(--ink-2);font-size:10px;paint-order:stroke;stroke:var(--panel);stroke-width:3px" });
          t.textContent = kurzU(o.f.name).split(" ").slice(0, 2).join(" "); top.appendChild(t);
        });
      }
      el.querySelectorAll(".sc-chip").forEach(b => { b.classList.toggle("hov", st.brHot === b.dataset.scb); });
    }
    function setHot(id, quelle) {
      if (st.hot === id) return;
      st.hot = id; markieren();
      const o = id && circles.find(x => x.f.id === id);
      if (svg) { if (o && quelle !== "ext") svg.setAttribute("data-tip", tipText(o.f)); else svg.removeAttribute("data-tip"); }
      if (quelle !== "ext") verknuepfen(id);
    }
    /* gleiche Unternehmen in Tabellen und Balken auf der Seite mitleuchten lassen */
    function verknuepfen(id) {
      document.querySelectorAll(".hl-x").forEach(e => e.classList.remove("hl-x"));
      if (!id) return;
      document.querySelectorAll(`tr[data-umk="${CSS.escape(id)}"]`).forEach(r => {
        r.classList.add("hl-x");
        const wr = r.closest(".tblwrap"); if (wr) { const a = r.offsetTop, b = a + r.offsetHeight; if (a < wr.scrollTop + 30) wr.scrollTop = a - 30; else if (b > wr.scrollTop + wr.clientHeight) wr.scrollTop = b - wr.clientHeight + 4; }
      });
    }
    el._api = {
      hover: id => setHot(id && circles.some(o => o.f.id === id && o.an) ? id : null, "ext"),
      branche: id => { st.brHot = id; markieren(); },
    };
    const naechster = (mx, my) => { let best = null, bd = Infinity; for (const o of sicht) { const d = Math.hypot(o.x - mx, o.y - my); if (d < Math.max(14, o.r + 8) && d < bd) { best = o; bd = d; } } return best; };
    const lokal = e => { const r = svg.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };

    /* Zeiger: Hover per Nachbarsuche, Ziehen verschiebt */
    let drag = null;
    plot.addEventListener("pointermove", e => {
      if (!svg) return;
      const [mx, my] = lokal(e);
      if (drag) {
        const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
        if (!drag.bewegt && Math.hypot(dx, dy) < 4) return;
        drag.bewegt = true; plot.classList.add("ziehen"); svg.removeAttribute("data-tip");
        const [xl, xh] = drag.dom.x, [yl, yh] = drag.dom.y, bw = st.W - M.l - M.r, bh = st.H - M.t - M.b;
        st.dom = { x: [xl - dx / bw * (xh - xl), xh - dx / bw * (xh - xl)], y: [yl + dy / bh * (yh - yl), yh + dy / bh * (yh - yl)] };
        place(); return;
      }
      const o = naechster(mx, my);
      plot.style.cursor = o ? "pointer" : "";
      setHot(o ? o.f.id : null);
    });
    plot.addEventListener("pointerdown", e => { if (e.button !== 0 || !svg) return; drag = { x: e.clientX, y: e.clientY, dom: { x: [...dom().x], y: [...dom().y] }, bewegt: false }; });
    addEventListener("pointerup", () => { if (!drag) return; const b = drag.bewegt; drag = null; plot.classList.remove("ziehen"); if (b) { el._ziehte = true; setTimeout(() => el._ziehte = false); } });
    plot.addEventListener("pointerleave", () => { if (!drag) setHot(null); });
    plot.addEventListener("click", e => { if (el._ziehte || !svg) return; const o = naechster(...lokal(e)); if (o) gehe("firma-" + o.f.id); });
    plot.addEventListener("dblclick", () => { st.dom = null; place(); });
    plot.addEventListener("wheel", e => {
      if (!svg) return; e.preventDefault();
      const [mx, my] = lokal(e), d = dom(), f = Math.exp(Math.max(-300, Math.min(300, e.deltaY)) * .0016);
      const bw = st.W - M.l - M.r, bh = st.H - M.t - M.b, tx = Math.min(1, Math.max(0, (mx - M.l) / bw)), ty = Math.min(1, Math.max(0, 1 - (my - M.t) / bh));
      const z = (r, t0, ref) => { const span = (r[1] - r[0]) * f, a = r[0] + (r[1] - r[0]) * t0; return [a - span * t0, a + span * (1 - t0)]; };
      const nx = z(d.x, tx), ny = z(d.y, ty);
      if (f < 1 && ((nx[1] - nx[0]) < (home.x[1] - home.x[0]) * 1e-3 || (ny[1] - ny[0]) < (home.y[1] - home.y[0]) * 1e-3)) return;
      st.dom = { x: nx, y: ny }; svg.removeAttribute("data-tip"); st.hot = null; place();
    }, { passive: false });
    reset.addEventListener("click", () => { st.dom = null; place(); });
    /* Suche: markiert, ohne neu zu zeichnen; Enter öffnet das Profil */
    find.addEventListener("input", () => {
      const f = finden(find.value), o = f && pts.includes(f) ? f : null;
      st.find = o ? o.id : null;
      if (o && st.hide.has(o.branche)) { st.hide.delete(o.branche); legendeSync(); }
      if (o && st.dom) { st.dom = null; }
      place();
    });
    find.addEventListener("keydown", e => { if (e.key === "Enter") { const f = finden(find.value); if (f && NACH_ID[f.id]) gehe("firma-" + f.id); } if (e.key === "Escape") { find.value = ""; st.find = null; place(); } });
    /* Legende */
    const legendeSync = () => el.querySelectorAll(".sc-chip").forEach(b => b.setAttribute("aria-pressed", String(!st.hide.has(b.dataset.scb))));
    el.addEventListener("mouseover", e => { const b = e.target.closest && e.target.closest(".sc-chip"); if (b && !st.hide.has(b.dataset.scb)) { st.brHot = b.dataset.scb; markieren(); } });
    el.addEventListener("mouseout", e => { if (e.target.closest && e.target.closest(".sc-chip") && st.brHot) { st.brHot = null; markieren(); } });
    el.addEventListener("click", e => {
      const b = e.target.closest && e.target.closest(".sc-chip"); if (!b) return;
      const id = b.dataset.scb; if (st.hide.has(id)) st.hide.delete(id); else st.hide.add(id);
      st.brHot = st.hide.has(id) ? null : id; legendeSync(); place();
    });
    el.addEventListener("dblclick", e => {
      const b = e.target.closest && e.target.closest(".sc-chip"); if (!b) return;
      const alle = [...el.querySelectorAll(".sc-chip")].map(x => x.dataset.scb);
      st.hide = new Set(alle.filter(x => x !== b.dataset.scb)); legendeSync(); place();
    });
    if (typeof ResizeObserver !== "undefined") {
      let breite = 0; new ResizeObserver(() => { const nb = Math.round(plot.clientWidth); if (nb && nb !== breite) { const erst = !breite; breite = nb; if (!erst) { layout(); } } }).observe(plot);
    }
    legendeSync(); if (st.find) { const f = NACH_ID[st.find]; if (f) find.value = f.name; }
    layout();
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
      ${panel({ code: "UEB 2", titel: "Alle Unternehmen im Streudiagramm", sub: "Kreisfläche ∝ Börsenwert · Maus darauf = hervorheben · Klick öffnet das Profil · Legende schaltet Branchen", body:
        `<div class="ctrl" style="margin-bottom:6px"><span>X</span></div>${metrikWahl("data-ussx", S.usx, FIRMEN, STREU_KZ)}<div class="ctrl" style="margin-bottom:6px"><span>Y</span></div>${metrikWahl("data-ussy", S.usy, FIRMEN, STREU_KZ)}${streuU(FIRMEN, S.usx, S.usy, S.branche, S.gruppe, { id: "ueb", legende: true })}`,
        fuss: "Farbe = Branche. Die Ansicht beginnt mit den 3-%/97-%-Perzentilen als Rahmen, Ausreißer sitzen am Rand; wer hineinzoomt, sieht sie in echter Lage. Eine in Branche (F2) gewählte Branche bleibt kräftig, die übrigen treten zurück." })}
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
      ${kz.length > 1 ? panel({ code: "BRA 5", titel: "Kennzahlen gegeneinander", sub: `Kreisfläche ∝ ${hatL(liste, "marktkap") ? "Börsenwert" : "Bilanzsumme"}`, breite: ad.length > 1 ? "w6" : "", body: `<div class="ctrl" style="margin-bottom:6px"><span>X</span></div>${metrikWahl("data-usx", S.sx, liste, STREU_KZ)}<div class="ctrl" style="margin-bottom:6px"><span>Y</span></div>${metrikWahl("data-usy", S.sy, liste, STREU_KZ)}${streuU(liste, S.sx, S.sy, "alle", "alle", { id: "bra" })}` }) : ""}
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
    return panel({ code: "DOK", titel: "Dokumente", sub: `${d.length} Datei${d.length === 1 ? "" : "en"} im Repo · Datei öffnen bzw. herunterladen über GitHub`, body: chips +
      `<div class="scroll"><table><thead><tr><th style="text-align:left">Jahr</th><th style="text-align:left">Art</th><th style="text-align:left">Dokument</th><th>Größe</th><th style="text-align:left">Quelle</th><th></th></tr></thead><tbody>${zeigen.map(x => `<tr><td>${x.jahr || "–"}</td><td style="text-align:left;font-family:var(--sans)">${esc(x.typ)}</td>
        <td style="text-align:left;font-family:var(--sans)" title="${esc(x.pfad)}">${esc(x.titel)}<div class="pct">${esc(x.pfad)}${x.sha256 ? ` · SHA-256 ${esc(x.sha256.slice(0, 10))}…` : ""}</div></td><td class="n">${mb(x.kb)}</td>
        <td style="text-align:left;font-family:var(--sans)">${x.url ? `<a class="flink" href="${esc(sicherUrl(x.url))}" target="_blank" rel="noopener">Original${x.abruf ? ` (${esc(x.abruf.replace(/^Download /, ""))})` : ""}</a>` : "–"}</td>
        <td style="white-space:nowrap"><a class="btn" href="${esc(sicherUrl(dokUrl(x.pfad, "raw")))}" target="_blank" rel="noopener">Datei</a> <a class="btn" href="${esc(sicherUrl(dokUrl(x.pfad, "blob")))}" target="_blank" rel="noopener">GitHub</a></td></tr>`).join("")}</tbody></table></div>`,
      fuss: "Die Dateien liegen im GitHub-Repo; je nach Repo-Einstellung ist dafür eine Anmeldung mit Zugriff nötig. Der Pfad zeigt den Speicherort im Repo." });
  }

  /* ----- Gremien und Vergütung (governance/*.csv, über die Unternehmens-ID verbunden) ----- */
  const GOV_FELD = { vorstand_mitglieder_zahl: "Vorstand: Mitglieder", vorstand_frauen_zahl: "Vorstand: Frauen", geschaeftsfuehrung_mitglieder_zahl: "Geschäftsführung: Mitglieder",
    geschaeftsfuehrung_frauen_zahl: "Geschäftsführung: Frauen", ar_mitglieder_zahl: "Aufsichtsrat: Mitglieder", ar_frauen_zahl: "Aufsichtsrat: Frauen",
    ar_arbeitnehmervertreter_zahl: "AR: Arbeitnehmervertreter", ar_gewerkschaftsvertreter_zahl: "AR: davon Gewerkschaft", ar_betriebsraete_zahl: "AR: davon Betriebsräte",
    mitbestimmung_ar: "Mitbestimmung im AR", pay_ratio: "Pay Ratio (CEO zu Belegschaft)", mitarbeiter_jahresdurchschnitt: "Mitarbeitende (Durchschnitt)" };
  const govName = k => GOV_FELD[k] || k.replace(/_zahl$/, "").replace(/^ar_/, "AR: ").replace(/_/g, " ");
  const ORGAN_REIHE = ["Vorstand", "Geschäftsführung", "Aufsichtsrat"];
  const gjLabel = j => "GJ " + j;
  function mandateZelle(m) {
    const ms = m.mandate || [], ws = m.werdegang || [];
    if (!ms.length && !ws.length) return "";
    const li = ms.map(x => `<li>${x.gesellschaft_unternehmen_id && NACH_ID[x.gesellschaft_unternehmen_id] ? `<a class="flink" href="#firma-${esc(x.gesellschaft_unternehmen_id)}">${esc(x.gesellschaft)}</a>` : esc(x.gesellschaft)}${x.funktion ? ", " + esc(x.funktion) : ""} <span class="pct">${x.typ === "a" ? "gesetzl. AR" : "vergl. Gremium"}${x.gueltig ? " · " + esc(x.gueltig) : ""}</span></li>`).join("")
      + ws.map(x => `<li>${esc(x.station || "")}${x.organisation ? ", " + esc(x.organisation) : ""}${x.zeitraum ? ` <span class="pct">${esc(x.zeitraum)}</span>` : ""}</li>`).join("");
    return `<details><summary class="pct" style="cursor:pointer">${ms.length} Mandat${ms.length === 1 ? "" : "e"}${ws.length ? ` · ${ws.length} Station${ws.length === 1 ? "" : "en"}` : ""}</summary><ul style="margin:4px 0 0 16px;padding:0;font-family:var(--sans);font-size:12px">${li}</ul></details>`;
  }
  function gremienPanel(f) {
    const g = f.gov;
    if (!g || !(g.mitglieder.length || g.kennzahlen.length)) return panel({ code: "GOV 1", titel: "Gremien", body: `<p class="n">Zu diesem Unternehmen sind Vorstand und Aufsichtsrat noch nicht ermittelt. Die Erhebung steht in <code>governance/</code>; sobald dort Zeilen mit der Kennung <code>${esc(f.id)}</code> stehen, erscheinen sie hier.</p>` });
    const jahre = [...new Set([...g.mitglieder, ...g.kennzahlen].map(x => x.gj))].sort((a, b) => b - a);
    if (!jahre.includes(S.govGj)) S.govGj = jahre[0];
    const chips = jahre.length > 1 ? chipRow(jahre.map(j => [String(j), gjLabel(j), 0]).map(([a, b]) => [a, b]), "data-ugj", String(S.govGj)) : "";
    const mj = g.mitglieder.filter(m => m.gj === S.govGj), kj = g.kennzahlen.filter(k => k.gj === S.govGj && k.wert !== "");
    const kacheln = kj.length ? `<div class="tape" style="margin-bottom:12px">${kj.map(k => `<div style="--gf:var(--amber)" data-tip="${esc(govName(k.feld) + (k.bem ? "\n" + k.bem : "") + (k.seite ? "\nPDF-Seite " + k.seite : ""))}"><div class="g"><b>${esc(govName(k.feld))}</b></div><div class="stats" style="grid-template-columns:1fr"><div><strong style="font-size:${k.wert.length > 14 ? 13 : 20}px">${esc(k.wert)}</strong>${k.einheit && k.einheit !== "Personen" ? ` <span class="pct">${esc(k.einheit)}</span>` : ""}</div></div></div>`).join("")}</div>` : "";
    const organe = [...new Set(mj.map(m => m.organ))].sort((a, b) => (ORGAN_REIHE.indexOf(a) + 99) % 99 - (ORGAN_REIHE.indexOf(b) + 99) % 99);
    const tab = o => { const l = mj.filter(m => m.organ === o), art = l.some(m => m.art);
      return `<div class="sub-h">${esc(o)} <span class="pct">${l.length} Personen</span></div><div class="scroll"><table class="kzt"><thead><tr><th style="text-align:left">Name</th><th style="text-align:left">Funktion</th>${art ? `<th style="text-align:left">Vertretung</th>` : ""}<th style="text-align:left">Beruf laut Dokument</th><th style="text-align:left">Weitere Mandate</th><th>Seite</th></tr></thead><tbody>${l.map(m => `<tr><td style="text-align:left;font-family:var(--sans)">${esc(m.name)}</td><td style="text-align:left;font-family:var(--sans)">${esc(m.funktion)}${m.seit || m.bis ? ` <span class="pct">${m.seit ? "seit " + esc(m.seit) : ""} ${m.bis ? "bis " + esc(m.bis) : ""}</span>` : ""}</td>${art ? `<td style="text-align:left;font-family:var(--sans)">${esc(m.art)}</td>` : ""}<td style="text-align:left;font-family:var(--sans);white-space:normal;min-width:220px;max-width:420px">${esc(m.beruf)}</td><td style="text-align:left">${mandateZelle(m)}</td><td class="n">${esc(m.seite)}</td></tr>`).join("")}</tbody></table></div>`; };
    return panel({ code: "GOV 1", titel: "Gremien", sub: `Vorstand bzw. Geschäftsführung und Aufsichtsrat · ${gjLabel(S.govGj)}`, body: chips + kacheln + (organe.length ? organe.map(tab).join("") : `<p class="n">Für ${gjLabel(S.govGj)} sind nur Kennzahlen, keine Mitglieder erhoben.</p>`),
      fuss: `Quelle: ${g.quellen.map(q => `<a class="flink" href="${esc(sicherUrl(dokUrl(q, "blob")))}" target="_blank" rel="noopener">${esc(q.split("/").pop())}</a>`).join(", ") || "governance/"}. Leere Angaben sind nicht ermittelt (Begründung in governance/*.csv, Spalte bemerkung); „Seite“ ist die PDF-Seite.` });
  }
  function verguetungPanel(f) {
    const v = f.gov && f.gov.verguetung || [];
    if (!v.length) return panel({ code: "GOV 2", titel: "Vergütung", body: `<p class="n">Vergütungsangaben sind für dieses Unternehmen noch nicht ermittelt (Quelle: Anhang nach § 285 Nr. 9a HGB bzw. Vergütungsbericht nach § 162 AktG).</p>` });
    const jahre = [...new Set(v.map(x => x.gj))].sort((a, b) => b - a), gremien = [...new Set(v.map(x => x.gremium))];
    const geld = x => x.betrag == null ? "n. v." : f1.format(x.betrag / 1e3);
    return panel({ code: "GOV 2", titel: "Vergütung", sub: "Gesamtbezüge je Gremium in Mio. €", body: `<div class="scroll"><table class="kzt"><thead><tr><th style="text-align:left">Gremium</th><th style="text-align:left">Angabe</th>${jahre.map(j => `<th>${gjLabel(j)}</th>`).join("")}<th style="text-align:left">Basis</th></tr></thead><tbody>${gremien.map(gr => {
      const namen = [...new Set(v.filter(x => x.gremium === gr).map(x => x.name))];
      return namen.map((n, i) => { const zs = v.filter(x => x.gremium === gr && x.name === n), basis = zs[0];
        return `<tr><td style="text-align:left;font-family:var(--sans)">${i === 0 ? esc(gr) : ""}</td><td style="text-align:left;font-family:var(--sans)">${esc(n)}</td>${jahre.map(j => { const z = zs.find(x => x.gj === j); return `<td class="${z ? "" : "n"}"${z && z.bem ? ` data-tip="${esc(z.bem)}"` : ""}>${z ? geld(z) : "–"}</td>`; }).join("")}<td class="n" style="text-align:left;font-family:var(--sans)">${esc(basis.art)}${basis.seite ? ` · PDF-S. ${esc(basis.seite)}` : ""}</td></tr>`; }).join("");
    }).join("")}</tbody></table></div>`, fuss: "Beträge laut Veröffentlichung des Unternehmens; die Basis (HGB-Gesamtbezüge, Zuwendungen, Pensionsbarwerte) unterscheidet sich je Zeile und ist nicht ohne Weiteres vergleichbar." });
  }

  function viewProfil(id) {
    id = NACH_ID[id] ? id : ((UD.alt_ids || {})[id] || id);   // alte Lesezeichen (#firma-deutsche-bank-ag) auf die zentrale ID umleiten
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
        <button type="button" class="chip" data-uwatch="${esc(f.id)}" aria-pressed="${merkListe().has(f.id)}" title="Merkliste (nur auf diesem Gerät)">${merkListe().has(f.id) ? "★ gemerkt" : "☆ merken"}</button>
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
      ${gremienPanel(f)}
      ${verguetungPanel(f)}
      ${termineProfil(f)}
      ${dokumentePanel(f)}
    </div>`;
  }


  /* ----- Berichtstermine (termine/termine.csv, siehe termine/README.md) ----- */
  const heuteIso = () => new Date().toISOString().slice(0, 10);
  const datumDe = iso => { const [j, m, t] = iso.split("-"); return `${t}.${m}.${j}`; };
  const TAGE = ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"];
  const wochentag = iso => TAGE[new Date(iso + "T12:00:00Z").getUTCDay()];
  const TSTATUS = { "erwartet": ["erwartet", "Schätzung (Yahoo Finance), noch nicht vom Unternehmen bestätigt"], "bestätigt": ["bestätigt", "Termin laut Finanzkalender des Unternehmens"],
    "angekündigt": ["bestätigt", "Termin laut Finanzkalender des Unternehmens"], "erschienen": ["erschienen", "Bericht ist veröffentlicht"] };
  const tStatus = t => (TSTATUS[t.status] || [t.status, ""]);
  function tagInfo(termin) { const d = Math.round((new Date(termin + "T12:00:00Z") - new Date(heuteIso() + "T12:00:00Z")) / 864e5); return d === 0 ? "heute" : d === 1 ? "morgen" : d > 1 ? `in ${d} Tagen` : d === -1 ? "gestern" : `vor ${-d} Tagen`; }
  const alleTermine = () => { const g = new Set(); // dieselbe Aktie unter zwei Kennungen (Bilanzvergleich-Bank und Börsenunternehmen) nur einmal
    return FIRMEN.flatMap(f => (f.termine || []).map(t => ({ ...t, f }))).filter(t => { const k = (t.f.ticker || t.f.id).split(".")[0].toUpperCase() + t.termin + t.berichtsart; return g.has(k) ? false : (g.add(k), true); }); };
  const berichtLink = t => t.datei ? `<a class="btn" href="${esc(sicherUrl(dokUrl(t.datei, "raw")))}" target="_blank" rel="noopener">Bericht</a>` : t.abruf_status === "gesperrt" ? `<span class="pct" title="Seite verweigert den automatischen Abruf">gesperrt</span>` : t.abruf_status === "nicht_gefunden" ? `<span class="pct">nicht gefunden</span>` : "";
  const quelleTxt = t => t.quelle === "yahoo" ? "Yahoo Finance" : t.quelle === "finanzkalender" ? "Finanzkalender" : t.quelle === "manuell" ? "manuell erfasst" : t.quelle;
  const termineHinweis = "Termine aus Yahoo Finance sind Schätzungen (Status „erwartet“); Termine aus dem Finanzkalender des Unternehmens oder von Hand erfasste gelten als bestätigt. Fällige Berichte lädt der Abruf täglich nach GitHub (termine/), sofern die Unternehmenswebsite sie ohne Bot-Schutz anbietet.";

  function termineProfil(f) {
    const t = f.termine || [];
    if (!t.length) return panel({ code: "TRM", titel: "Berichtstermine", body: `<p class="n">Für dieses Unternehmen ist kein Veröffentlichungstermin bekannt (Yahoo Finance und Finanzkalender liefern keinen). Von Hand ergänzen: <code>termine/termine_manuell.csv</code>.</p>` });
    const h = heuteIso(), naechster = t.find(x => x.termin >= h && x.status !== "erschienen") || t.find(x => x.termin >= h);
    const kopf = naechster ? `<p style="margin:0 0 10px"><strong style="font:600 18px var(--mono)">${wochentag(naechster.termin)} ${datumDe(naechster.termin)}</strong> · ${esc(naechster.berichtsart)} (Periode bis ${datumDe(naechster.periode_ende)}) · ${tagInfo(naechster.termin)} · <span class="pct" title="${esc(tStatus(naechster)[1])}">${esc(tStatus(naechster)[0])}</span></p>` : `<p class="n">Kein künftiger Termin bekannt.</p>`;
    return panel({ code: "TRM", titel: "Berichtstermine", sub: "Quartals-, Halbjahres- und Jahresberichte", body: kopf +
      `<div class="scroll"><table><thead><tr><th style="text-align:left">Termin</th><th style="text-align:left">Bericht</th><th style="text-align:left">Periode bis</th><th style="text-align:left">Status</th><th style="text-align:left">Quelle</th><th></th></tr></thead><tbody>${t.map(x => `<tr><td>${datumDe(x.termin)} <span class="pct">${wochentag(x.termin)}</span></td><td style="text-align:left;font-family:var(--sans)">${esc(x.berichtsart)}</td><td>${x.periode_ende ? datumDe(x.periode_ende) : "–"}</td><td style="text-align:left;font-family:var(--sans)" title="${esc(tStatus(x)[1])}">${esc(tStatus(x)[0])}</td><td style="text-align:left;font-family:var(--sans)">${x.quelle_url ? `<a class="flink" href="${esc(sicherUrl(x.quelle_url))}" target="_blank" rel="noopener">${esc(quelleTxt(x))}</a>` : esc(quelleTxt(x))}</td><td>${berichtLink(x)}</td></tr>`).join("")}</tbody></table></div>`, fuss: termineHinweis });
  }

  function viewTermine() {
    const alle = alleTermine(), h = heuteIso();
    if (!alle.length) return `<div class="grid">${panel({ code: "TRM", titel: "Berichtstermine", body: `<p class="n">Noch keine Termine im Repo. <code>python3 termine/skripte/termine_erfassen.py</code> erzeugt <code>termine/termine.csv</code>; der Workflow „Berichtstermine“ macht das täglich.</p>` })}</div>`;
    const bis = S.tZeit === "alle" ? "9999" : new Date(Date.now() + (+S.tZeit) * 864e5).toISOString().slice(0, 10);
    const arten = [...new Set(alle.map(t => t.berichtsart))].sort();
    const passt = t => (S.tBranche === "alle" || t.f.branche === S.tBranche) && (S.tArt === "alle" || t.berichtsart === S.tArt);
    const kommend = alle.filter(t => passt(t) && t.termin >= h && t.termin <= bis).sort((a, b) => a.termin.localeCompare(b.termin) || a.f.name.localeCompare(b.f.name, "de"));
    const zuletzt = alle.filter(t => passt(t) && t.termin < h).sort((a, b) => b.termin.localeCompare(a.termin) || a.f.name.localeCompare(b.f.name, "de"));
    const brN = id => alle.filter(t => t.f.branche === id).length;
    const ctrl = chipRow([["alle", "Alle Branchen", alle.length], ...UD.branchen.filter(b => brN(b.id)).map(b => [b.id, b.name, brN(b.id)])], "data-utb", S.tBranche)
      + chipRow([["30", "30 Tage"], ["90", "90 Tage"], ["180", "180 Tage"], ["alle", "Alle künftigen"]].map(([i, n]) => [i, n]), "data-utz", S.tZeit)
      + (arten.length > 1 ? chipRow([["alle", "Alle Berichtsarten"], ...arten.map(a => [a, a])], "data-uta", S.tArt) : "");
    let monat = "";
    const zeile = t => `<tr><td style="white-space:nowrap">${datumDe(t.termin)} <span class="pct">${wochentag(t.termin)}</span></td><td style="text-align:left;font-family:var(--sans)">${profilLink(t.f, t.f.name)}${t.f.ticker ? ` <span class="pct">${esc(t.f.ticker)}</span>` : ""}</td><td style="text-align:left;font-family:var(--sans)">${esc(t.berichtsart)}${t.periode_ende ? ` <span class="pct">bis ${datumDe(t.periode_ende)}</span>` : ""}</td><td style="text-align:left;font-family:var(--sans)" title="${esc(tStatus(t)[1])}">${esc(tStatus(t)[0])}</td><td class="n">${t.termin >= h ? tagInfo(t.termin) : ""}</td><td>${t.termin < h ? berichtLink(t) : ""}</td></tr>`;
    const kopfZ = `<thead><tr><th style="text-align:left">Termin</th><th style="text-align:left">Unternehmen</th><th style="text-align:left">Bericht</th><th style="text-align:left">Status</th><th></th><th></th></tr></thead>`;
    const kommendHtml = kommend.length ? `<div class="scroll"><table>${kopfZ}<tbody>${kommend.map(t => { const m = t.termin.slice(0, 7), z = m !== monat ? `<tr><td colspan="6" class="grp">${["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"][+m.slice(5) - 1]} ${m.slice(0, 4)}</td></tr>` : ""; monat = m; return z + zeile(t); }).join("")}</tbody></table></div>` : `<p class="n">Im gewählten Zeitraum ist kein Termin bekannt.</p>`;
    const nG = zuletzt.filter(t => t.datei).length;
    return `<div class="grid">${panel({ code: "TRM", titel: "Kommende Berichtstermine", sub: `${kommend.length} Termine · ${new Set(kommend.map(t => t.f.id)).size} Unternehmen`, body: ctrl + kommendHtml, fuss: termineHinweis })}
      ${panel({ code: "TRM 2", titel: "Zuletzt fällig", sub: `${zuletzt.length} Berichte der letzten Wochen · ${nG} davon im Repo`, body: zuletzt.length ? `<div class="scroll"><table>${kopfZ}<tbody>${zuletzt.slice(0, 80).map(zeile).join("")}</tbody></table></div>` : `<p class="n">Noch keine fälligen Berichte erfasst.</p>` })}</div>`;
  }

  /* ----- Verzeichnis aller Unternehmen ----- */
  function viewVerz() {
    const zeilen = [...FIRMEN].sort((a, b) => a.name.localeCompare(b.name, "de"));
    return `<div class="grid">${panel({ code: "VERZ", titel: "Verzeichnis", sub: `${FIRMEN.length} Unternehmen · Suche nach Name, Ticker oder Gruppe`, body:
      `<div class="picks" style="margin-bottom:12px"><input id="usuche" placeholder="Suchen …" autocomplete="off" style="width:320px"><select id="ubr"><option value="">Alle Branchen</option>${UD.branchen.map(b => `<option value="${esc(b.id)}">${esc(b.name)}</option>`).join("")}</select>
        <select id="unot"><option value="">Notiert und nicht notiert</option><option value="1">Börsennotiert</option><option value="0">Nicht börsennotiert</option><option value="m">Nur Merkliste ★</option></select><span class="n" id="uzahl"></span></div>
      <div class="tblwrap"><table class="kzt"><thead><tr><th>Unternehmen</th><th></th><th style="text-align:left">Branche</th><th style="text-align:left">Gruppe</th><th>Dokumente</th><th>Jahre</th></tr></thead><tbody id="uverz">${zeilen.map(f => {
        const jahre = Math.max(0, ...Object.values(f.reihen || {}).map(r => r.punkte.length));
        return `<tr data-w="${esc(f.id)}" data-q="${esc((f.name + " " + (f.ticker || "") + " " + (f.gruppe || "") + " " + (f.isin || "")).toLowerCase())}" data-b="${esc(f.branche)}" data-n="${f.notiert ? 1 : 0}"><td>${profilLink(f, f.name)}</td><td>${punkt(f)}</td><td class="n" style="text-align:left;font-family:var(--sans)">${esc(brName(f.branche))}</td><td class="n" style="text-align:left;font-family:var(--sans)">${esc(f.gruppe || "")}</td><td class="${(f.dokumente || []).length ? "" : "n"}">${(f.dokumente || []).length || "–"}</td><td class="n">${jahre || "–"}</td></tr>`; }).join("")}</tbody></table></div>` })}</div>`;
  }
  /* ----- Merkliste (nur im Browser dieses Geräts; ohne Speicher bleibt sie für die Sitzung) ----- */
  let merk = null;
  const merkListe = () => { if (!merk) { try { merk = new Set(JSON.parse(localStorage.getItem("merkliste") || "[]")); } catch (e) { merk = new Set(); } } return merk; };
  function merkUmschalten(id) { const m = merkListe(); m.has(id) ? m.delete(id) : m.add(id); try { localStorage.setItem("merkliste", JSON.stringify([...m])); } catch (e) { /* kein Speicher */ } }
  function verzFilter() {
    const q = (document.getElementById("usuche") || {}).value, br = (document.getElementById("ubr") || {}).value, nt = (document.getElementById("unot") || {}).value, nurM = nt === "m";
    let n = 0;
    document.querySelectorAll("#uverz tr").forEach(tr => { const ok = (!q || tr.dataset.q.includes(q.toLowerCase())) && (!br || tr.dataset.b === br) && (!nt || (nurM ? merkListe().has(tr.dataset.w) : tr.dataset.n === nt)); tr.hidden = !ok; if (ok) n++; });
    const z = document.getElementById("uzahl"); if (z) z.textContent = n + " angezeigt";
  }

  /* ----- Hover über Seitengrenzen: Tabellenzeile/Balken <-> Streudiagramm, Zeilen- und Spaltenhervorhebung ----- */
  function hoverVerdrahten() {
    const sc = () => document.querySelector(".uscat");
    document.addEventListener("mouseover", e => {
      const t = e.target; if (!t.closest) return;
      const inSc = t.closest(".uscat"), s = sc();
      const zeile = t.closest("tr[data-uopen]");                                  // Branchenzeile -> Branche im Streudiagramm
      if (s && s._api && !inSc) s._api.branche(zeile ? zeile.dataset.uopen : null);
      const m = t.closest("[data-umk]");                                          // Tabellenzeile, Balken -> Punkt im Streudiagramm
      const id = m ? m.dataset.umk : null;
      if (!inSc) document.querySelectorAll(".uscat").forEach(x => x._api && x._api.hover(id));
      document.querySelectorAll(".hl-b").forEach(x => x.classList.remove("hl-b"));
      if (id && !t.closest(".uscat")) { const svg = m.closest("svg"); if (svg) { svg.classList.add("has-hl"); m.classList.add("hl-b"); } }
      document.querySelectorAll("svg.has-hl").forEach(x => { if (!id || !x.contains(m)) x.classList.remove("has-hl"); });
      const td = t.closest("td, th"), tb = td && td.closest("table.kzt, table.hov");   // Spalte der Tabelle mitleuchten lassen
      document.querySelectorAll(".colhl").forEach(x => x.classList.remove("colhl"));
      if (td && tb) { const i = td.cellIndex; tb.querySelectorAll("tr").forEach(r => { const c = r.cells[i]; if (c && c.tagName !== "TH") c.classList.add("colhl"); }); }
    });
    document.addEventListener("mouseleave", () => { document.querySelectorAll(".colhl, .hl-b").forEach(x => x.classList.remove("colhl", "hl-b")); }, true);
    document.addEventListener("keydown", e => { if (e.key === "Enter" && e.target.matches && e.target.matches("th.sortable")) e.target.click(); });
  }

  /* ----- Bedienung ----- */
  function hinzu(id) { if (!S.auswahl) viewVgl(); if (!S.auswahl.includes(id)) { S.auswahl.push(id); if (S.auswahl.length > 6) S.auswahl.shift(); } }
  function finden(q) { q = (q || "").trim().toLowerCase(); if (!q || !UD) return null; return FIRMEN.find(f => f.name.toLowerCase() === q || f.id === q) || FIRMEN.find(f => (f.ticker || "").toLowerCase() === q || (f.isin || "").toLowerCase() === q) || FIRMEN.find(f => f.name.toLowerCase().includes(q)); }
  function klick(t) {
    const g = a => { const e = t.closest && t.closest("[" + a + "]"); return e ? e.getAttribute(a) : null; };
    let v;
    if ((v = g("data-uwatch")) != null) { merkUmschalten(v); render(); return true; }
    if ((v = g("data-uadd")) != null) { hinzu(v); gehe("u-vergleich"); return true; }
    if ((v = g("data-uweg")) != null) { S.auswahl = S.auswahl.filter(x => x !== v); render(); return true; }
    if ((v = g("data-ub")) != null) { S.branche = v; S.gruppe = "alle"; S.notiert = "alle"; S.rang = null; render(); return true; }
    if ((v = g("data-ug")) != null) { S.gruppe = v; render(); return true; }
    if ((v = g("data-un")) != null) { S.notiert = v; render(); return true; }
    if ((v = g("data-ugj")) != null) { S.govGj = +v; render(); return true; }
    if ((v = g("data-utb")) != null) { S.tBranche = v; render(); return true; }
    if ((v = g("data-utz")) != null) { S.tZeit = v; render(); return true; }
    if ((v = g("data-uta")) != null) { S.tArt = v; render(); return true; }
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
    document.querySelectorAll(".uscat").forEach(scatterInit);
    document.querySelectorAll("#view th.sortable").forEach(th => th.tabIndex = 0);  }
  const datalist = () => UD ? FIRMEN.map(f => `<option value="${esc(f.name)}">`).join("") : "";
  const meta = () => UD ? `${FIRMEN.length} Unternehmen · ${nNotiert(FIRMEN)} börsennotiert · ${UD.branchen.length} Branchen${UD.demo ? " · teils Beispieldaten" : ""}` : "";
  return { init, da, korr: () => UD && { firmen: FIRMEN, branchen: UD.branchen, kz: KZU, kzName, brName, kurz: kurzU, kurse: kurseHist }, viewUeb, viewBra, viewVgl, viewProfil, viewVerz, viewTermine, klick, nachRender, datalist, finden, hinzu, meta, existiert: id => !!NACH_ID[id] || !!(UD.alt_ids || {})[id] };
})();
