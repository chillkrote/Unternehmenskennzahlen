/* ---------- Börse & Finanzen: Marktpuls, Zinsstrukturkurven, Währungen, Sektoren (Reiter BÖR, F8 bis F11 und Weltkugel) ----------
   Daten: FZ = data/finanz.json (finanz_abruf.py: Yahoo Finance, EZB, US-Finanzministerium) und die Kurse des Bereichs BÖR (BOE.korr()).
   Volatilität und Sektoren werden im Browser aus den Wochenkursen und dem Feld sektor der Unternehmen gerechnet.
   Läuft nach boerse.js; nutzt panel, esc, f0, f1, f2 des Hauptskripts erst zur Laufzeit. */
"use strict";
const FNZ = (() => {
  let FZ = null;
  const S = { sektor: "alle", land: "alle", vol: "52", kurve: "alle", ws: { k: "ytd", ab: false } };
  const lade = () => {
    if (FZ === null) { try { const d = JSON.parse(document.getElementById("finanz-daten").textContent); FZ = d && d.puls ? d : false; } catch { FZ = false; } }
    return FZ;
  };
  const da = () => !!lade();
  const datumDe = d => (d || "").split("-").reverse().join(".");
  const pct = v => v == null ? "–" : `${v > 0 ? "+" : ""}${f1.format(v * 100)} %`;
  const pos = v => v == null ? "" : v > 0 ? "pos" : v < 0 ? "neg" : "";
  const farbe = v => v == null ? "var(--ink-3)" : v >= 0 ? "var(--up)" : "var(--down)";
  const zahl = (v, d = 2) => v == null ? "–" : (Math.abs(v) >= 1000 ? f0 : d === 1 ? f1 : f2).format(v);
  const AMPEL = { rot: "var(--down)", gelb: "var(--amber)", gruen: "var(--up)" };

  /* Ampel: nur für Größen mit gängigen Schwellen, sonst keine */
  function ampel(p) {
    const v = p.wert;
    const r = {
      vix: v < 20 ? ["gruen", "ruhig (unter 20)"] : v < 30 ? ["gelb", "erhöht (20 bis 30)"] : ["rot", "Stress (über 30)"],
      vxn: v < 25 ? ["gruen", "ruhig (unter 25)"] : v < 35 ? ["gelb", "erhöht (25 bis 35)"] : ["rot", "Stress (über 35)"],
      move: v < 90 ? ["gruen", "ruhig (unter 90)"] : v < 120 ? ["gelb", "erhöht (90 bis 120)"] : ["rot", "Stress (über 120)"],
      ciss: v < .15 ? ["gruen", "ruhig (unter 0,15)"] : v < .35 ? ["gelb", "erhöht (0,15 bis 0,35)"] : ["rot", "Stress (über 0,35)"],
      abst_usa: v < 0 ? ["rot", "invertiert (kurz über lang)"] : v < .5 ? ["gelb", "flach (unter 0,5 Punkte)"] : ["gruen", "normal"],
      baa10y: v < 2 ? ["gruen", "ruhig (unter 2 Punkte)"] : v < 3 ? ["gelb", "erhöht (2 bis 3 Punkte)"] : ["rot", "Stress (über 3 Punkte)"],
      aaa10y: v < 1 ? ["gruen", "ruhig (unter 1 Punkt)"] : v < 1.5 ? ["gelb", "erhöht (1 bis 1,5 Punkte)"] : ["rot", "Stress (über 1,5 Punkte)"],
      nfci_kredit: v < 0 ? ["gruen", "lockerer als im Schnitt (unter 0)"] : v < .5 ? ["gelb", "strenger als im Schnitt (0 bis 0,5)"] : ["rot", "deutlich strenger (über 0,5)"],
      stlfsi: v < 0 ? ["gruen", "unter dem Schnitt (unter 0)"] : v < 1 ? ["gelb", "erhöht (0 bis 1)"] : ["rot", "Stress (über 1)"],
      abst_euro: v < 0 ? ["rot", "invertiert (kurz über lang)"] : v < .5 ? ["gelb", "flach (unter 0,5 Punkte)"] : ["gruen", "normal"]
    }[p.id];
    return r || null;
  }
  const punkt = a => a ? `<span title="${esc(a[1])}" style="display:inline-block;width:9px;height:9px;border-radius:50%;background:${AMPEL[a[0]]};margin-right:5px;vertical-align:baseline"></span>` : "";
  const wertText = p => p.diff ? `${f2.format(p.wert)} <small>Pkt.</small>` : p.id === "ciss" || p.gruppe === "spread" ? f2.format(p.wert) : zahl(p.wert, Math.abs(p.wert) < 10 ? 2 : 1);
  const aendText = p => {
    if (p.diff) return p.r1m == null ? "" : `1 M ${p.r1m > 0 ? "+" : ""}${f2.format(p.r1m)} Pkt.`;
    return p.r1t != null ? `Tag ${pct(p.r1t)}` : p.ytd != null ? `lfd. J. ${pct(p.ytd)}` : "";
  };
  const spark = (l, farb, n = 90, W = 84, H = 22) => {
    const w = (l || []).slice(-n).map(x => x[1]).filter(v => v != null);
    if (w.length < 3) return "";
    const lo = Math.min(...w), hi = Math.max(...w);
    const p = w.map((v, i) => (i ? "L" : "M") + (i / (w.length - 1) * W).toFixed(1) + " " + (H - 2 - (v - lo) / (hi - lo || 1) * (H - 4)).toFixed(1)).join("");
    return `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" style="width:${W}px;height:${H}px" aria-hidden="true"><path d="${p}" fill="none" stroke="${farb}" stroke-width="1.4" stroke-linejoin="round"/></svg>`;
  };
  const neutral = p => p.gruppe === "angst" || p.gruppe === "spread" || p.diff;   // steigende Angst ist nicht „gut“: keine Grün/Rot-Wertung
  const holen = id => (lade().puls || []).find(x => x.id === id);
  const LEISTE = ["vix", "move", "ciss", "baa10y", "abst_usa", "gold", "brent", "eurusd", "btc"];
  const kachel = p => {
    const a = ampel(p), tr = p.diff ? (p.verlauf.length ? p.wert - p.verlauf[Math.max(0, p.verlauf.length - 22)][1] : 0) : p.r1m;
    return `<div data-lv="${esc(p.id)}" title="${esc(p.name)} · ${esc(p.quelle)}${p.live ? " (live, ca. 15 Min. verzögert)" : ""} · Stand ${datumDe(p.datum)}${a ? " · " + a[1] : ""}" style="display:grid;gap:2px;padding:9px 11px;border:1px solid var(--line);border-radius:8px;background:var(--panel-2)">
      <span class="n" style="font-size:11px">${punkt(a)}${esc(p.name.replace(/ \(.*$/, ""))}</span>
      <b style="font:600 17px var(--mono)">${wertText(p)}</b>
      <span class="n" style="font-size:11px;color:${neutral(p) ? "var(--ink-3)" : farbe(p.r1t != null ? p.r1t : p.ytd)}">${esc(aendText(p))}</span>
      ${spark(p.verlauf, neutral(p) ? "var(--amber)" : farbe(tr))}</div>`;
  };
  /* Marktpuls-Leiste: acht Kacheln, oben im Überblick und auf der Weltkugel */
  function leiste() {
    if (!lade()) return "";
    const l = LEISTE.map(holen).filter(Boolean);
    return l.length ? `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px">${l.map(kachel).join("")}</div>` : "";
  }
  const leisteFuss = () => lade() ? `Ampel: grün ruhig, gelb erhöht, rot Stress (Schwellen im Tooltip). Yahoo Finance, EZB, US-Finanzministerium, Stand ${datumDe(lade().abruf)}; ohne Gewähr.` : "";
  const leisteLive = () => `<span data-lvfuss>${esc(lvText())}</span>`;

  /* ----- Realisierte Volatilität aus den Wochenkursen ----- */
  function vol(t, n) {
    const w = t.slice(-(n + 1));
    if (w.length < n + 1 || w.some(v => v == null || v <= 0)) return null;
    const r = []; for (let i = 1; i < w.length; i++) r.push(Math.log(w[i] / w[i - 1]));
    const m = r.reduce((a, b) => a + b, 0) / r.length;
    return Math.sqrt(r.reduce((a, b) => a + (b - m) ** 2, 0) / (r.length - 1)) * Math.sqrt(52);
  }
  const heat = (v, lo, hi) => { if (v == null) return ""; const q = Math.max(0, Math.min(1, (v - lo) / (hi - lo))); return `background:rgba(255,${Math.round(168 - 90 * q)},${Math.round(40 - 20 * q)},${(.08 + .5 * q).toFixed(2)})`; };
  function volTabelle() {
    const k = typeof BOE !== "undefined" && BOE.da() ? BOE.korr() : null;
    if (!k) return `<p class="n">Keine Indexkurse im Build.</p>`;
    const l = k.indizes.filter(x => x.t && !/VIX|ETF/.test(x.name)).map(x => ({ x, v13: vol(x.t, 13), v52: vol(x.t, 52), v26: vol(x.t, 26) })).filter(z => z.v52 != null || z.v13 != null);
    const key = S.vol === "13" ? "v13" : "v52";
    l.sort((a, b) => (b[key] ?? -1) - (a[key] ?? -1));
    const mx = Math.max(...l.map(z => z[key] || 0), .3);
    const chip = (v, n) => `<button type="button" data-fvol="${v}" aria-pressed="${S.vol === v}">${n}</button>`;
    return `<div class="ctrl" style="margin-bottom:8px">Sortiert nach ${chip("13", "13 Wochen")}${chip("52", "52 Wochen")}</div>
      <div style="max-height:420px;overflow:auto"><table class="tab"><thead><tr><th style="text-align:left">Index</th><th style="text-align:left">Land</th><th>Vol. 13 W.</th><th>Vol. 26 W.</th><th>Vol. 52 W.</th><th>Kurzfristig gegen Jahr</th></tr></thead><tbody>
      ${l.map(z => `<tr><td style="text-align:left;font-family:var(--sans)"><a class="flink" href="#b-verlauf" data-bplus="i:${esc(z.x.id)}">${esc(z.x.name)}</a></td><td class="n" style="text-align:left;font-family:var(--sans)">${esc(z.x.land || "")}</td>
        <td style="${heat(z.v13, 0, mx)}">${z.v13 == null ? "–" : f1.format(z.v13 * 100) + " %"}</td><td style="${heat(z.v26, 0, mx)}">${z.v26 == null ? "–" : f1.format(z.v26 * 100) + " %"}</td><td style="${heat(z.v52, 0, mx)}">${z.v52 == null ? "–" : f1.format(z.v52 * 100) + " %"}</td>
        <td class="${z.v13 != null && z.v52 != null ? (z.v13 > z.v52 * 1.25 ? "neg" : z.v13 < z.v52 * .8 ? "pos" : "") : ""}">${z.v13 != null && z.v52 ? (z.v13 / z.v52 > 1.25 ? "unruhiger" : z.v13 / z.v52 < .8 ? "ruhiger" : "wie üblich") : "–"}</td></tr>`).join("")}</tbody></table></div>`;
  }

  /* ----- F8 Marktpuls und Risiko ----- */
  function viewPuls() {
    if (!lade()) return keine("PLS", "Marktpuls");
    const angst = FZ.puls.filter(p => p.gruppe === "angst");
    const rest = FZ.puls.filter(p => p.gruppe !== "angst" && p.gruppe !== "spread");
    const spr = FZ.puls.filter(p => p.gruppe === "spread");
    const tab = l => `<div style="overflow-x:auto"><table class="tab"><thead><tr><th style="text-align:left">Größe</th><th>Stand</th><th>1 M</th><th>lfd. Jahr</th><th>1 J</th><th>Verlauf</th></tr></thead><tbody>${l.map(p => `<tr><td style="text-align:left;font-family:var(--sans)">${punkt(ampel(p))}<a class="flink" href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.name)}</a> <span class="n">${datumDe(p.datum)}</span></td>
      <td>${wertText(p)}</td><td class="${p.diff ? "" : pos(p.r1m)}">${p.diff ? (p.r1m == null ? "–" : (p.r1m > 0 ? "+" : "") + f2.format(p.r1m) + " Pkt.") : pct(p.r1m)}</td><td class="${pos(p.ytd)}">${pct(p.ytd)}</td>
      <td class="${p.diff ? "" : pos(p.r1j)}">${p.diff ? (p.r1j == null ? "–" : (p.r1j > 0 ? "+" : "") + f2.format(p.r1j) + " Pkt.") : pct(p.r1j)}</td><td>${spark(p.verlauf, neutral(p) ? "var(--amber)" : farbe(p.ytd ?? p.r1m), 130)}</td></tr>`).join("")}</tbody></table></div>`;
    return `<div class="grid">
      ${panel({ code: "PLS", titel: "Marktpuls", sub: "die wichtigsten Größen auf einen Blick", body: leiste(), fuss: leisteFuss() + " " + leisteLive() })}
      ${panel({ code: "RSK", titel: "Angst- und Stressindikatoren", sub: "implizite Schwankung der Optionsmärkte und EZB-Stressindex", breite: "w6", body: tab(angst.concat(rest.filter(p => p.id === "ciss"))), fuss: "VIX, VXN, OVX, GVZ und MOVE stammen von Yahoo Finance, der Stressindex CISS von der EZB. VSTOXX und VDAX sind bei Yahoo nicht frei verfügbar. Hohe Werte bedeuten Unruhe, nicht zwingend fallende Kurse." })}
      ${spr.length ? panel({ code: "SPR", titel: "Kreditspreads und Finanzbedingungen", sub: "Aufschlag von Unternehmensanleihen und Stress-Indizes der US-Notenbanken", breite: "w6", body: tab(spr) + `<p class="n" style="margin-top:8px">${spr.map(p => `${esc(p.name)}: ${esc(p.beschreibung || "")}`).join("<br>")}</p>`, fuss: "Quellenangabe: Moody's, Federal Reserve Bank of Chicago und of St. Louis, über FRED (Federal Reserve Bank of St. Louis). Die ICE-BofA-Spreads (High Yield, Euro) fehlen bewusst, ihre Weitergabe ist ohne Erlaubnis von ICE untersagt. Echte CDS-Kurse sind nicht kostenlos zu bekommen." }) : ""}
      ${panel({ code: "MKT", titel: "Zinsabstand, Währung, Rohstoffe, Krypto", sub: "Stand und Veränderung", breite: "w6", body: tab(rest.filter(p => p.id !== "ciss")), fuss: "Zinsabstand = Rendite 10 Jahre minus 2 Jahre; negativ heißt invertierte Kurve (siehe Zinskurven). Gold ist damit nicht mehr offen." })}
      ${panel({ code: "VOL", titel: "Realisierte Volatilität der Indizes", sub: "annualisiert, aus Wochenschlusskursen (13, 26 und 52 Wochen)", body: volTabelle(), fuss: "Standardabweichung der logarithmierten Wochenrenditen mal Wurzel 52. Farbe: je dunkler, desto unruhiger. Die Spalte rechts vergleicht die letzten 13 Wochen mit dem Jahr." })}</div>`;
  }

  /* ----- F9 Zinsstrukturkurven ----- */
  function kurvenBild(k) {
    const z = k.kurven, W = 560, H = 250, L = 38, R = 14, T = 12, B = 30, n = k.etiketten.length;
    const alle = Object.values(z).flatMap(c => c.werte).filter(v => v != null);
    let lo = Math.min(...alle), hi = Math.max(...alle); const pad = (hi - lo || 1) * .15; lo = Math.floor((lo - pad) * 2) / 2; hi = Math.ceil((hi + pad) * 2) / 2;
    const x = i => L + i / (n - 1) * (W - L - R), y = v => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
    const lin = (c, farb, dash, breit) => {
      let p = "", st = false;
      c.werte.forEach((v, i) => { if (v == null) { st = false; return; } p += (st ? "L" : "M") + x(i).toFixed(1) + " " + y(v).toFixed(1); st = true; });
      return `<path d="${p}" fill="none" stroke="${farb}" stroke-width="${breit}" ${dash ? 'stroke-dasharray="5 4"' : ""} stroke-linejoin="round"/>`;
    };
    let gitter = "";
    for (let v = lo; v <= hi + 1e-9; v += (hi - lo) > 4 ? 1 : .5) gitter += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)" stroke-width=".6"/><text x="${L - 5}" y="${y(v) + 3}" text-anchor="end" font-size="9.5" fill="var(--ink-3)">${f1.format(v)}</text>`;
    const ach = k.etiketten.map((e, i) => `<text x="${x(i)}" y="${H - 11}" text-anchor="middle" font-size="9.5" fill="var(--ink-3)">${e}</text>`).join("");
    const punkte = z.heute.werte.map((v, i) => v == null ? "" : `<circle cx="${x(i)}" cy="${y(v)}" r="2.6" fill="var(--amber)"><title>${k.etiketten[i]}: ${f2.format(v)} %</title></circle>`).join("");
    return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Zinsstrukturkurve ${esc(k.name)}" style="width:100%;height:auto;max-height:290px">${gitter}${ach}
      ${z.j1 ? lin(z.j1, "var(--ink-3)", true, 1.3) : ""}${z.m1 ? lin(z.m1, "#2f86dd", false, 1.3) : ""}${lin(z.heute, "var(--amber)", false, 2.2)}${punkte}</svg>
      <div class="n" style="display:flex;gap:14px;flex-wrap:wrap;font-size:11px"><span style="color:var(--amber)">▬ ${datumDe(z.heute.datum)} (heute)</span>${z.m1 ? `<span style="color:#2f86dd">▬ ${datumDe(z.m1.datum)} (vor 1 Monat)</span>` : ""}${z.j1 ? `<span>┅ ${datumDe(z.j1.datum)} (vor 1 Jahr)</span>` : ""}<span>Rendite in % · Laufzeit</span></div>`;
  }
  function kurvenTabelle(k) {
    const z = k.kurven, h = z.heute.werte;
    return `<div style="overflow-x:auto"><table class="tab" style="margin-top:8px"><thead><tr><th style="text-align:left">Laufzeit</th>${k.etiketten.map(e => `<th>${e}</th>`).join("")}</tr></thead><tbody>
      <tr><td style="text-align:left;font-family:var(--sans)">heute</td>${h.map(v => `<td>${v == null ? "–" : f2.format(v)}</td>`).join("")}</tr>
      ${z.m1 ? `<tr><td style="text-align:left;font-family:var(--sans)">Änd. zum Vormonat (Bp.)</td>${h.map((v, i) => { const d = v != null && z.m1.werte[i] != null ? Math.round((v - z.m1.werte[i]) * 100) : null; return `<td class="${pos(d)}">${d == null ? "–" : (d > 0 ? "+" : "") + d}</td>`; }).join("")}</tr>` : ""}
      ${z.j1 ? `<tr><td style="text-align:left;font-family:var(--sans)">Änd. zum Vorjahr (Bp.)</td>${h.map((v, i) => { const d = v != null && z.j1.werte[i] != null ? Math.round((v - z.j1.werte[i]) * 100) : null; return `<td class="${pos(d)}">${d == null ? "–" : (d > 0 ? "+" : "") + d}</td>`; }).join("")}</tr>` : ""}</tbody></table></div>`;
  }
  function abstandBild(k) {
    const l = k.abstand_2j10j; if (!l || l.length < 3) return "";
    const W = 560, H = 120, L = 38, R = 14, T = 8, B = 18, v = l.map(x => x[1]);
    let lo = Math.min(...v, 0), hi = Math.max(...v, 0); const pad = (hi - lo || .5) * .15; lo -= pad; hi += pad;
    const x = i => L + i / (l.length - 1) * (W - L - R), y = w => T + (1 - (w - lo) / (hi - lo)) * (H - T - B);
    const p = l.map((a, i) => (i ? "L" : "M") + x(i).toFixed(1) + " " + y(a[1]).toFixed(1)).join("");
    return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Zinsabstand 10 minus 2 Jahre" style="width:100%;height:auto;max-height:130px"><line x1="${L}" x2="${W - R}" y1="${y(0)}" y2="${y(0)}" stroke="var(--ink-3)" stroke-dasharray="3 3" stroke-width=".8"/>
      <text x="${L - 5}" y="${y(0) + 3}" text-anchor="end" font-size="9.5" fill="var(--ink-3)">0</text><path d="${p}" fill="none" stroke="var(--amber)" stroke-width="1.6"/>
      <text x="${L}" y="${H - 3}" font-size="9.5" fill="var(--ink-3)">${datumDe(l[0][0])}</text><text x="${W - R}" y="${H - 3}" text-anchor="end" font-size="9.5" fill="var(--ink-3)">${datumDe(l[l.length - 1][0])}</text></svg>`;
  }
  function kurvenPanel(k, code, breite) {
    const a = k.abstand_2j10j.length ? k.abstand_2j10j[k.abstand_2j10j.length - 1][1] : null;
    const hinweis = a == null ? "" : a < 0 ? `<p class="neg">Die Kurve ist <b>invertiert</b>: kurze Laufzeiten rentieren höher als lange (Abstand ${f2.format(a)} Punkte). Das galt historisch oft als Warnzeichen für eine Rezession.</p>`
      : a < .5 ? `<p style="color:var(--amber)">Die Kurve ist <b>flach</b>: Abstand 10 minus 2 Jahre nur ${f2.format(a)} Punkte.</p>` : `<p class="pos">Die Kurve hat eine <b>normale</b> Steigung (Abstand ${f2.format(a)} Punkte).</p>`;
    return panel({ code, titel: `Zinsstrukturkurve ${k.name}`, sub: "Rendite nach Laufzeit, heute gegen Vormonat und Vorjahr", breite, body: kurvenBild(k) + hinweis + kurvenTabelle(k) + `<div class="n" style="margin-top:8px">Zinsabstand 10 minus 2 Jahre, ein Jahr</div>` + abstandBild(k), fuss: `<a class="flink" href="${esc(k.url)}" target="_blank" rel="noopener">${esc(k.quelle)}</a>` });
  }
  function viewKurven() {
    if (!lade() || !Object.keys(FZ.kurven || {}).length) return keine("KRV", "Zinsstrukturkurven");
    return `<div class="grid">${FZ.kurven.euro ? kurvenPanel(FZ.kurven.euro, "KEU", "w6") : ""}${FZ.kurven.usa ? kurvenPanel(FZ.kurven.usa, "KUS", "w6") : ""}</div>`;
  }

  /* ----- F10 Währungen ----- */
  const MATRIX = ["EUR", "USD", "GBP", "JPY", "CHF", "CNY", "CAD", "AUD"];
  const kurs = (w, d) => w === "EUR" ? 1 : d[w] ? d[w].je_eur : null;
  function viewWaehr() {
    if (!lade() || !FZ.waehrungen || !Object.keys(FZ.waehrungen).length) return keine("WHR", "Währungen");
    const d = FZ.waehrungen, st = S.ws;
    const l = Object.entries(d).map(([c, x]) => ({ c, ...x })).sort((a, b) => {
      const x = a[st.k], y = b[st.k];
      if (typeof x === "string") return (st.ab ? 1 : -1) * x.localeCompare(y, "de");
      return (st.ab ? 1 : -1) * ((x ?? -9) - (y ?? -9));
    });
    const kopf = ([k, n, links]) => `<th${links ? ' style="text-align:left"' : ""}><button type="button" class="sortbtn" data-fws="${k}" style="background:none;border:0;color:inherit;font:inherit;cursor:pointer">${n}${st.k === k ? (st.ab ? " ▲" : " ▼") : ""}</button></th>`;
    const hz = v => v == null ? "" : `background:rgba(${v >= 0 ? "62,207,110" : "255,82,72"},${Math.min(.5, Math.abs(v) * 2.5 + .05).toFixed(2)})`;
    const tab = `<div style="max-height:520px;overflow:auto"><table class="tab"><thead><tr>${[["name", "Währung", 1], ["je_eur", "1 EUR ="], ["ytd", "lfd. Jahr"], ["r1j", "1 J."]].map(kopf).join("")}<th>10 Jahre (Monatswerte)</th></tr></thead><tbody>
      ${l.map(x => `<tr><td style="text-align:left;font-family:var(--sans)">${esc(x.name)} <span class="n">${x.c}</span></td><td>${x.je_eur >= 100 ? f0.format(x.je_eur) : x.je_eur >= 10 ? f1.format(x.je_eur) : f2.format(x.je_eur)}</td><td style="${hz(x.ytd)}" class="${pos(x.ytd)}">${pct(x.ytd)}</td><td style="${hz(x.r1j)}" class="${pos(x.r1j)}">${pct(x.r1j)}</td>
      <td>${spark(x.monat.map(m => [m[0], 1 / m[1]]), farbe(x.r1j), 120, 110)}</td></tr>`).join("")}</tbody></table></div>`;
    const mt = `<table class="tab"><thead><tr><th style="text-align:left">1 … =</th>${MATRIX.map(c => `<th>${c}</th>`).join("")}</tr></thead><tbody>${MATRIX.map(r => `<tr><td style="text-align:left;font-family:var(--sans)"><b>${r}</b></td>${MATRIX.map(c => {
      if (r === c) return `<td class="n">–</td>`;
      const a = kurs(r, d), b = kurs(c, d); if (!a || !b) return `<td>–</td>`;
      const v = b / a; return `<td>${v >= 100 ? f0.format(v) : v >= 10 ? f1.format(v) : v >= 1 ? f2.format(v) : (Math.round(v * 1e4) / 1e4).toLocaleString("de-DE", { minimumFractionDigits: 4 })}</td>`;
    }).join("")}</tr>`).join("")}</tbody></table>`;
    return `<div class="grid">
      ${panel({ code: "WHR", titel: "Währungen gegen den Euro", sub: `${l.length} EZB-Referenzkurse`, breite: "w7", body: tab, fuss: `Positive Werte: Die Währung hat zum Euro an Wert gewonnen. Verlauf: Wert der Währung in Euro, Monatsdurchschnitte. EZB-Referenzkurse, Stand ${datumDe(d.USD ? d.USD.datum : FZ.abruf)}.` })}
      ${panel({ code: "KRZ", titel: "Kreuzkurse", sub: "Zeile in Spalte umgerechnet", breite: "w5", body: mt, fuss: "Aus den EZB-Referenzkursen gerechnet (kein Marktkurs der Paare)." })}</div>`;
  }

  /* ----- F11 Sektoren aus den großen Unternehmen ----- */
  const ZEITEN = [["r1t", "1 Tag"], ["r1w", "1 Woche"], ["r1m", "1 Monat"], ["r3m", "3 Monate"], ["ytd", "lfd. Jahr"], ["r1j", "1 Jahr"]];
  function sektorDaten() {
    const k = typeof BOE !== "undefined" && BOE.da() ? BOE.korr() : null;
    if (!k) return null;
    const u = k.unternehmen.filter(x => (S.land === "alle" || x.land === S.land));
    const g = {};
    u.forEach(x => { (g[x.sektor || "Sonstige"] = g[x.sektor || "Sonstige"] || []).push(x); });
    return { k, u, g };
  }
  const gew = (l, key) => { let s = 0, w = 0; l.forEach(x => { if (x[key] != null && x.boerswert > 0) { s += x[key] * x.boerswert; w += x.boerswert; } }); return w ? s / w : null; };
  function viewSektoren() {
    const d = sektorDaten(); if (!d) return keine("SEK", "Sektoren");
    const laender = [...new Set(d.k.unternehmen.map(x => x.land).filter(Boolean))].sort((a, b) => a.localeCompare(b, "de"));
    const zeilen = Object.entries(d.g).map(([n, l]) => ({ n, l, wert: l.reduce((a, x) => a + (x.boerswert || 0), 0), ...Object.fromEntries(ZEITEN.map(([k]) => [k, gew(l, k)])) })).sort((a, b) => b.wert - a.wert);
    const tot = zeilen.reduce((a, z) => a + z.wert, 0) || 1;
    const hz = v => v == null ? "" : `background:rgba(${v >= 0 ? "62,207,110" : "255,82,72"},${Math.min(.55, Math.abs(v) * (v > .3 || v < -.3 ? 1 : 2.2) + .05).toFixed(2)})`;
    const tm = `<div style="display:flex;flex-wrap:wrap;gap:4px">${zeilen.map(z => `<button type="button" data-fsektor="${esc(z.n)}" title="${esc(z.n)}: ${z.l.length} Unternehmen, ${f0.format(z.wert)} Mrd. USD, lfd. Jahr ${pct(z.ytd)}" aria-pressed="${S.sektor === z.n}" style="flex:${Math.max(1, Math.round(z.wert / tot * 100))} 1 ${Math.max(90, Math.round(z.wert / tot * 620))}px;min-height:62px;padding:6px 8px;border:1px solid var(--line);border-radius:6px;color:inherit;text-align:left;cursor:pointer;${hz(z.ytd)}">
      <b style="font:600 12px var(--sans)">${esc(z.n)}</b><br><span style="font:600 13px var(--mono)">${pct(z.ytd)}</span><br><span class="n" style="font-size:10px">${f0.format(z.wert)} Mrd. USD</span></button>`).join("")}</div>`;
    const tab = `<table class="tab"><thead><tr><th style="text-align:left">Sektor</th><th>Anzahl</th><th>Börsenwert Mrd. USD</th>${ZEITEN.map(([, n]) => `<th>${n}</th>`).join("")}</tr></thead><tbody>
      ${zeilen.map(z => `<tr><td style="text-align:left;font-family:var(--sans)"><button type="button" class="flink" data-fsektor="${esc(z.n)}" style="background:none;border:0;cursor:pointer;padding:0;font:inherit">${esc(z.n)}</button></td><td>${z.l.length}</td><td>${f0.format(z.wert)}</td>${ZEITEN.map(([k]) => `<td style="${hz(z[k])}" class="${pos(z[k])}">${pct(z[k])}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
    const z = S.sektor !== "alle" && d.g[S.sektor];
    const mit = z ? `<table class="tab"><thead><tr><th style="text-align:left">Unternehmen</th><th style="text-align:left">Land</th><th>Börsenwert Mrd. USD</th><th>1 M</th><th>lfd. Jahr</th><th>1 J</th></tr></thead><tbody>${z.slice().sort((a, b) => (b.boerswert || 0) - (a.boerswert || 0)).slice(0, 25).map(x => `<tr><td style="text-align:left;font-family:var(--sans)"><a class="flink" href="#b-verlauf" data-bplus="u:${esc(x.symbol)}">${esc(x.name)}</a></td><td class="n" style="text-align:left;font-family:var(--sans)">${esc(x.land)}</td><td>${x.boerswert != null ? f0.format(x.boerswert) : "–"}</td><td class="${pos(x.r1m)}">${pct(x.r1m)}</td><td class="${pos(x.ytd)}">${pct(x.ytd)}</td><td class="${pos(x.r1j)}">${pct(x.r1j)}</td></tr>`).join("")}</tbody></table>` : "";
    const sel = `<select id="fland" aria-label="Land"><option value="alle">Alle Länder</option>${laender.map(l => `<option value="${esc(l)}"${l === S.land ? " selected" : ""}>${esc(l)}</option>`).join("")}</select>`;
    return `<div class="grid">
      ${panel({ code: "SEK", titel: "Sektoren: Kursentwicklung", sub: `${d.u.length} große Unternehmen ${S.land === "alle" ? "weltweit" : "in " + esc(S.land)}, nach Börsenwert gewichtet`, body: `<div class="ctrl" style="margin-bottom:8px">${sel}${S.sektor !== "alle" ? `<button type="button" data-fsektor="alle">Auswahl aufheben</button>` : ""}</div>${tm}`, fuss: "Fläche = Börsenwert, Farbe = Veränderung seit Jahresbeginn (Kurs in Landeswährung, gewichtet mit dem Börsenwert in USD). Nur die Unternehmen des Bereichs BÖR; Sektoren wie im Katalog." })}
      ${panel({ code: "SKZ", titel: "Sektoren nach Zeitraum", sub: "gewichtete Veränderung", body: tab })}
      ${z ? panel({ code: "SMI", titel: `${esc(S.sektor)}: größte Unternehmen`, sub: "bis zu 25", body: mit }) : ""}</div>`;
  }


  /* ===== Welle 2: Inflation, Realzins, Schulden, Börsenwert/BIP, Aufschläge, Bankensektor (data/finanz_makro.json) ===== */
  let MK = null;
  const makro = () => {
    if (MK === null) { try { const d = JSON.parse(document.getElementById("finanz-makro-daten").textContent); MK = d && d.inflation ? d : false; } catch { MK = false; } }
    return MK;
  };
  const nm = i => i === "XM" ? "Euroraum" : i === "SSM" ? "Euroraum (SSM-Gesamt)" : (typeof HDL !== "undefined" && HDL.name ? HDL.name(i) : i);
  const zeitDe2 = z => /^\d{4}-\d{2}$/.test(z || "") ? `${z.slice(5)}/${z.slice(0, 4)}` : (z || "").replace("-Q", " Q");
  const pz = (v, d = 1) => v == null ? "–" : (d === 2 ? f2 : f1).format(v) + " %";
  const EUROL = new Set(["AT", "BE", "BG", "CY", "DE", "EE", "ES", "FI", "FR", "GR", "HR", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PT", "SI", "SK"]);
  /* Messgrößen für die Länderfärbung der Weltkugel: Wert je Land, Farbe (diverg = negativ rot, positiv grün; sonst Amber nach Höhe) */
  const MESS = [
    { id: "inflation", name: "Inflation", einheit: "% z. Vorj.", skala: [0, 8], hol: (m, i) => m.inflation[i] && { v: m.inflation[i].v, zeit: m.inflation[i].zeit } },
    { id: "real", name: "Realzins (Leitzins minus Inflation)", einheit: "Punkte", diverg: 3, hol: (m, i) => m.realzins[i] && m.realzins[i].real != null && { v: m.realzins[i].real, zeit: m.realzins[i].zeit_infl } },
    { id: "real10", name: "Realrendite 10 Jahre", einheit: "Punkte", diverg: 4, hol: (m, i) => m.realzins[i] && m.realzins[i].real10 != null && { v: m.realzins[i].real10, zeit: m.realzins[i].zeit_infl } },
    { id: "schulden", name: "Schuldenquote Zentralstaat", einheit: "% BIP", skala: [0, 150], hol: (m, i) => m.schulden[i] && { v: m.schulden[i].v, zeit: m.schulden[i].jahr } },
    { id: "defizit", name: "Finanzierungssaldo Zentralstaat", einheit: "% BIP", diverg: 8, hol: (m, i) => m.defizit[i] && { v: m.defizit[i].v, zeit: m.defizit[i].jahr } },
    { id: "bwbip", name: "Börsenwert im Verhältnis zum BIP", einheit: "% BIP", skala: [0, 250], hol: (m, i) => m.boersenwert_bip[i] && { v: m.boersenwert_bip[i].v, zeit: m.boersenwert_bip[i].jahr } },
    { id: "aufschlag", name: "Renditeaufschlag auf Bundesanleihen", einheit: "Punkte", skala: [0, 4], hol: (m, i) => m.aufschlag[i] && { v: m.aufschlag[i].v, zeit: m.aufschlag[i].zeit } },
    { id: "cet1", name: "CET1-Quote des Bankensektors", einheit: "%", skala: [10, 24], hol: (m, i) => m.bankensektor[i] && m.bankensektor[i].cet1 && { v: m.bankensektor[i].cet1.v, zeit: m.bankensektor[i].cet1.zeit } }
  ];
  const messDef = id => MESS.find(x => x.id === id);
  /* Wert eines Landes; Euro-Länder ohne eigene Inflationsreihe fallen auf den Euroraum zurück (nur Leitzins und Rendite) */
  function messWerte(id) {
    const m = makro(), d = messDef(id); if (!m || !d) return {};
    const out = {};
    const laender = new Set([...Object.keys(m.inflation), ...Object.keys(m.schulden), ...Object.keys(m.defizit), ...Object.keys(m.boersenwert_bip), ...Object.keys(m.aufschlag), ...Object.keys(m.bankensektor)]);
    laender.forEach(i => { if (i === "XM" || i === "SSM") return; const w = d.hol(m, i); if (w && w.v != null) out[i] = w; });
    return out;
  }
  const messFarbe = (id, v) => {
    const d = messDef(id); if (v == null || !d) return null;
    if (d.diverg) { const q = Math.min(1, Math.abs(v) / d.diverg); return v >= 0 ? `rgba(62,207,110,${(.15 + .6 * q).toFixed(2)})` : `rgba(255,82,72,${(.15 + .6 * q).toFixed(2)})`; }
    const q = Math.max(0, Math.min(1, (v - d.skala[0]) / (d.skala[1] - d.skala[0])));
    return `rgba(255,168,40,${(.12 + .65 * q).toFixed(2)})`;
  };
  const messText = (id, w) => { const d = messDef(id); return !w ? "" : `${(d.einheit.includes("Punkte") ? (w.v > 0 ? "+" : "") : "") + f1.format(w.v)}${d.einheit.startsWith("%") && d.einheit !== "% z. Vorj." && d.einheit !== "% BIP" ? " %" : d.einheit === "% z. Vorj." || d.einheit === "% BIP" ? " %" : d.einheit === "Punkte" ? " Pkt." : ""}`; };
  const hzel = (v, lo, hi) => v == null ? "" : `background:rgba(255,168,40,${(.08 + .5 * Math.max(0, Math.min(1, (v - lo) / (hi - lo)))).toFixed(2)})`;
  const hdiv = (v, w) => v == null ? "" : `background:rgba(${v >= 0 ? "62,207,110" : "255,82,72"},${Math.min(.5, Math.abs(v) / w * .5 + .05).toFixed(2)})`;
  const kleinTab = (zeilen, kopf) => `<table class="tab"><thead><tr>${kopf.map((k, i) => `<th${i === 0 ? ' style="text-align:left"' : ""}>${k}</th>`).join("")}</tr></thead><tbody>${zeilen.join("")}</tbody></table>`;
  const keineMk = (code, titel) => `<div class="grid">${panel({ code, titel, body: `<p class="n">Keine Daten im Build. <code>python3 app/finanz_makro.py</code> schreibt <code>app/data/finanz_makro.json</code> (Workflow „Weltkugel-Daten“, montags).</p>` })}</div>`;

  /* ----- Reiter Makro: Inflation, Realzins, Staatsfinanzen, Aufschläge ----- */
  function viewMakro() {
    const m = makro(); if (!m) return keineMk("MAK", "Makro und Geld");
    const bw = document.getElementById("boerse-welt-daten") ? JSON.parse(document.getElementById("boerse-welt-daten").textContent) : null;
    const zl = Object.entries(m.realzins).sort((a, b) => (b[1].infl || 0) - (a[1].infl || 0));
    const real = kleinTab(zl.map(([i, e]) => `<tr><td style="text-align:left;font-family:var(--sans)">${esc(nm(i))}</td><td style="${hzel(e.infl, 0, 8)}">${pz(e.infl)}</td><td>${e.leit != null ? pz(e.leit, 2) : "–"}</td><td style="${hdiv(e.real, 3)}" class="${pos(e.real)}">${e.real != null ? (e.real > 0 ? "+" : "") + f1.format(e.real) : "–"}</td><td>${e.rend != null ? pz(e.rend, 2) : "–"}</td><td style="${hdiv(e.real10, 4)}" class="${pos(e.real10)}">${e.real10 != null ? (e.real10 > 0 ? "+" : "") + f1.format(e.real10) : "–"}</td><td>${spark(m.inflation[i].l.map(x => [x[0], x[1]]), "var(--amber)", 24)}</td><td class="n">${zeitDe2(e.zeit_infl)}</td></tr>`),
      ["Land", "Inflation", "Leitzins", "Realzins", "Rendite 10 J.", "Realrendite", "Inflation, 2 J.", "Stand"]);
    const ids = [...new Set([...Object.keys(m.schulden), ...Object.keys(m.defizit), ...Object.keys(m.boersenwert_bip)])].sort((a, b) => ((m.schulden[b] || {}).v ?? -1) - ((m.schulden[a] || {}).v ?? -1));
    const staat = kleinTab(ids.map(i => { const a = m.schulden[i], b = m.defizit[i], c = m.boersenwert_bip[i]; return `<tr><td style="text-align:left;font-family:var(--sans)">${esc(nm(i))}</td><td style="${hzel(a && a.v, 0, 150)}">${a ? pz(a.v) : "–"} <span class="n">${a ? a.jahr : ""}</span></td><td style="${hdiv(b && b.v, 8)}" class="${pos(b && b.v)}">${b ? pz(b.v) : "–"} <span class="n">${b ? b.jahr : ""}</span></td><td style="${hzel(c && c.v, 0, 250)}">${c ? pz(c.v, 0) : "–"} <span class="n">${c ? c.jahr : ""}</span></td></tr>`; }), ["Land", "Schulden (Zentralstaat)", "Finanzierungssaldo", "Börsenwert/BIP"]);
    const au = Object.entries(m.aufschlag).sort((a, b) => b[1].v - a[1].v).slice(0, 30);
    const aufs = kleinTab(au.map(([i, e]) => `<tr><td style="text-align:left;font-family:var(--sans)">${esc(nm(i))}</td><td>${pz(e.rend, 2)}</td><td style="${hzel(e.v, 0, 4)}">${e.v > 0 ? "+" : ""}${f2.format(e.v)}</td><td>${e.l ? spark(e.l, "var(--amber)", 60, 90) : ""}</td><td class="n">${zeitDe2(e.zeit)}</td></tr>`), ["Land", "Rendite 10 J.", "Aufschlag auf Bund (Pkt.)", "fünf Jahre", "Stand"]);
    const q = k => `<a class="flink" href="${esc(m.quellen[k].url)}" target="_blank" rel="noopener">${esc(m.quellen[k].name)}</a>`;
    return `<div class="grid">
      ${panel({ code: "REA", titel: "Inflation und Realzins", sub: `${zl.length} Länder und Euroraum`, breite: "w7", body: `<div style="max-height:560px;overflow:auto">${real}</div>`, fuss: `Realzins = Leitzins (BIS) minus jüngste Inflationsrate (OECD, Verbraucherpreise zum Vorjahr); Realrendite entsprechend mit der 10-jährigen Rendite. Stände können um einen Monat auseinanderliegen. ${q("inflation")}.` })}
      ${panel({ code: "STA", titel: "Staatsfinanzen und Börsenwert", sub: "letzter Jahreswert je Land", breite: "w5", body: `<div style="max-height:560px;overflow:auto">${staat}</div>`, fuss: `Weltbank, Zentralstaat; die Reihen sind lückenhaft und hinken ein bis zwei Jahre, Werte über sieben Jahre alt fehlen. ${q("schulden")}` })}
      ${panel({ code: "SPR", titel: "Renditeaufschläge auf Bundesanleihen", sub: "Ersatz für CDS-Prämien, die nicht kostenlos verfügbar sind", body: `<div style="max-height:460px;overflow:auto">${aufs}</div>`, fuss: `Rendite 10 Jahre minus Rendite Deutschland (OECD, Monatswerte). Das ist kein CDS-Kurs: Der Aufschlag spiegelt Ausfall-, Liquiditäts- und Währungsrisiko zusammen. ${q("aufschlag")}` })}</div>`;
  }

  /* ----- Reiter Bankensektor (EZB-Länder) ----- */
  const BK = [["cet1", "CET1-Quote", 10, 24, 1], ["roe", "Eigenkapitalrendite", 0, 16, 1], ["cir", "Aufwand-Ertrags-Quote", 80, 40, 1], ["npl", "Notleidende Kredite", 6, 0, 1], ["lcr", "Liquiditätsdeckung", 120, 220, 1], ["lev", "Verschuldungsquote", 4, 9, 1]];
  function viewBank() {
    const m = makro(); if (!m || !Object.keys(m.bankensektor).length) return keineMk("BNK", "Bankensektor");
    const zl = Object.entries(m.bankensektor).sort((a, b) => (a[0] === "SSM" ? -1 : b[0] === "SSM" ? 1 : ((b[1].cet1 || {}).v ?? -1) - ((a[1].cet1 || {}).v ?? -1)));
    const tab = kleinTab(zl.map(([i, e]) => `<tr><td style="text-align:left;font-family:var(--sans)">${i === "SSM" ? "<b>" : ""}${esc(nm(i))}${i === "SSM" ? "</b>" : ""}</td>${BK.map(([k, , lo, hi]) => `<td style="${hzel(e[k] && e[k].v, Math.min(lo, hi), Math.max(lo, hi))}">${e[k] ? f1.format(e[k].v) + " %" : "–"}</td>`).join("")}<td>${e.cet1 ? spark(e.cet1.l, "var(--amber)", 8, 70) : ""}</td><td class="n">${e.cet1 ? zeitDe2(e.cet1.zeit) : ""}</td></tr>`),
      ["Land", ...BK.map(b => b[1]), "CET1, 2 Jahre", "Stand"]);
    const de = (typeof BANKEN !== "undefined" && BANKEN) ? BANKEN.filter(b => b.cet1_quote != null) : [];
    const med = l => { const a = l.slice().sort((x, y) => x - y); return a.length ? a[Math.floor(a.length / 2)] : null; };
    const dek = de.length ? `<p class="n" style="margin-top:8px">Eigener Bestand (Offenlegung 31.12.2025): ${de.length} deutsche Banken mit CET1-Quote, Median ${f1.format(med(de.map(b => b.cet1_quote)) * 100)} % gegen ${m.bankensektor.DE && m.bankensektor.DE.cet1 ? f1.format(m.bankensektor.DE.cet1.v) + " % der bedeutenden Institute (EZB)" : "–"}. Die EZB-Zahl betrifft nur die großen, direkt beaufsichtigten Banken.</p>` : "";
    const q = m.quellen.bankensektor;
    return `<div class="grid">${panel({ code: "BNK", titel: "Bankensektor im Länderbild", sub: "bedeutende Institute je Land, EZB-Bankenaufsicht, vierteljährlich", body: `<div style="overflow-x:auto">${tab}</div>${dek}`, fuss: `Färbung je Spalte von ungünstig (hell) bis günstig (dunkel), bei Aufwand-Ertrags-Quote und notleidenden Krediten umgekehrt. <a class="flink" href="${esc(q.url)}" target="_blank" rel="noopener">${esc(q.name)}</a>. Nur Länder des Einheitlichen Aufsichtsmechanismus.` })}</div>`;
  }

  /* ----- Länderseite der Weltkugel (Stufe 2): Blöcke zu Inflation, Staat, Bankensektor ----- */
  function landBloecke(iso) {
    const m = makro(); if (!m) return "";
    const eu = EUROL.has(iso);
    const rz = m.realzins[iso] || (eu && m.realzins.XM) || null;
    const i = m.inflation[iso] || (eu && m.inflation.XM) || null;
    const zeile = (t, v, z) => v == null ? "" : `<tr><td>${esc(t)}</td><td style="text-align:right">${v}</td><td class="pct">${esc(z || "")}</td></tr>`;
    const a = m.aufschlag[iso], s = m.schulden[iso], d = m.defizit[iso], b = m.boersenwert_bip[iso], k = m.bankensektor[iso];
    const rows = [
      i ? zeile(`Inflation${m.inflation[iso] ? "" : " (Euroraum)"}`, pz(i.v), zeitDe2(i.zeit)) : "",
      rz && rz.real != null ? zeile("Realzins (Leitzins minus Inflation)", `${rz.real > 0 ? "+" : ""}${f1.format(rz.real)} Pkt.`, zeitDe2(rz.zeit_infl)) : "",
      rz && rz.real10 != null ? zeile("Realrendite 10 Jahre", `${rz.real10 > 0 ? "+" : ""}${f1.format(rz.real10)} Pkt.`, zeitDe2(rz.zeit_infl)) : "",
      a ? zeile("Rendite-Aufschlag auf Bund", `${a.v > 0 ? "+" : ""}${f2.format(a.v)} Pkt.`, zeitDe2(a.zeit)) : "",
      s ? zeile("Schulden des Zentralstaats", pz(s.v) + " BIP", s.jahr) : "", d ? zeile("Finanzierungssaldo Zentralstaat", pz(d.v) + " BIP", d.jahr) : "", b ? zeile("Börsenwert", pz(b.v, 0) + " BIP", b.jahr) : ""].join("");
    const bank = k ? `<div class="gk-block"><h3>Bankensektor (EZB-Aufsicht)</h3><table class="gk-tab"><tbody>${BK.map(([kk, n]) => k[kk] ? `<tr><td>${esc(n)}</td><td style="text-align:right">${f1.format(k[kk].v)} %</td><td class="pct">${esc(zeitDe2(k[kk].zeit))}</td></tr>` : "").join("")}</tbody></table>
      <p class="gk-quelle" style="margin-top:6px">Bedeutende Institute des Landes, EZB Supervisory Banking Statistics.</p></div>` : "";
    return (rows ? `<div class="gk-block"><h3>Preise, Realzins und Staat</h3><table class="gk-tab"><tbody>${rows}</tbody></table>
      <p class="gk-quelle" style="margin-top:6px">OECD (Inflation), BIS (Leitzins), Weltbank (Staat und Börsenwert, letzter Jahreswert), Aufschlag aus OECD-Renditen; kein CDS.</p></div>` : "") + bank;
  }
  const makroDa = () => !!makro();

  const keine = (code, titel) => `<div class="grid">${panel({ code, titel, body: `<p class="n">Keine Daten im Build. <code>python3 app/finanz_abruf.py</code> schreibt <code>app/data/finanz.json</code> (Workflow „Börsendaten Terminal“).</p>` })}</div>`;

  function klick(t) {
    const g = a => { const e = t.closest && t.closest("[" + a + "]"); return e ? e.getAttribute(a) : null; };
    let v;
    if ((v = g("data-fvol")) != null) { S.vol = v; render(); return true; }
    if ((v = g("data-fsektor")) != null) { S.sektor = S.sektor === v ? "alle" : v; render(); return true; }
    if ((v = g("data-fws")) != null) { S.ws = { k: v, ab: S.ws.k === v ? !S.ws.ab : v === "name" }; render(); return true; }
    return false;
  }
  function nachRender() {
    const e = document.getElementById("fland");
    if (e) e.addEventListener("change", () => { S.land = e.value; S.sektor = "alle"; render(); });
  }

  /* ----- Live-Kurse: Auf der Website (GitHub Pages) lädt die Seite alle zwei Minuten live.json vom Zweig daten-live nach (live_abruf.py, Workflow
     live.yml, Yahoo Finance, ca. 15 Minuten verzögert) und aktualisiert die Marktpuls-Kacheln an Ort und Stelle sowie die Kurse der Leitindizes.
     Im Artifact, lokal oder bei Fehlern passiert nichts: die Seite zeigt dann den Stand des Builds. ----- */
  const LIVE_URL = "https://raw.githubusercontent.com/chillkrote/Unternehmenskennzahlen/daten-live/live.json";
  const LV = { stand: null, fehler: false };
  const uhr = iso => { const t = new Date(iso); return isNaN(t) ? "" : t.toLocaleString("de-DE", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }); };
  const lvText = () => LV.stand ? `Live-Kurse: Abruf ${uhr(LV.stand)} Uhr (Yahoo Finance, ca. 15 Min. verzögert).` : "";
  function liveSetzen(d) {
    if (!lade() || !d || !d.werte) return false;
    for (const p of FZ.puls) {
      const w = d.werte[p.id];
      if (!w || p.diff || w.k == null) continue;
      p.wert = Math.round(w.k * 100) / 100;
      p.datum = (w.z || d.abruf || "").slice(0, 10) || p.datum;
      if (w.v) p.r1t = w.k / w.v - 1;
      p.live = true;
      const ende = p.verlauf && p.verlauf[p.verlauf.length - 1];
      if (ende) { if (ende[0] === p.datum) ende[1] = p.wert; else p.verlauf.push([p.datum, p.wert]); }
    }
    if (typeof BOE !== "undefined" && BOE.live) BOE.live(d.werte);
    LV.stand = d.abruf; LV.fehler = false;
    document.querySelectorAll("[data-lv]").forEach(e => { const p = holen(e.getAttribute("data-lv")); if (p) e.outerHTML = kachel(p); });
    document.querySelectorAll("[data-lvfuss]").forEach(e => { e.textContent = lvText(); });
    return true;
  }
  async function liveHolen(url) {
    try {
      const r = await fetch(url || LIVE_URL, { cache: "no-store" });
      if (!r.ok) throw new Error(r.status);
      return liveSetzen(await r.json());
    } catch { LV.fehler = true; return false; }
  }
  function liveStart() {
    // nur auf der veröffentlichten Website (github.io) oder mit ?live=<Adresse> zum Testen
    if (document.querySelector('meta[name="sphaerae-oeffentlich"]')) return;      // E1: öffentliche Fassung lädt nie Yahoo-Live-Kurse, auch nicht mit ?live=
    const q = new URLSearchParams(location.search).get("live");
    if (!q && !/\.github\.io$/.test(location.hostname)) return;
    const hol = () => { if (!document.hidden) liveHolen(q || LIVE_URL); };
    hol(); setInterval(hol, 120000);
    document.addEventListener("visibilitychange", () => { if (!document.hidden) hol(); });
  }
  setTimeout(liveStart, 1500);
  const meta = () => lade() ? `${FZ.puls.length} Marktgrößen · ${Object.keys(FZ.kurven).length} Zinskurven · ${Object.keys(FZ.waehrungen || {}).length} Währungen · Stand ${datumDe(FZ.abruf)}` : "";
  return { da, leiste, leisteFuss, leisteLive, viewPuls, viewKurven, viewWaehr, viewSektoren, viewMakro, viewBank, makroDa, mess: () => MESS, messDef, messWerte, messFarbe, messText, landBloecke, klick, nachRender, meta, liveSetzen, liveHolen, kurve: () => lade() && FZ.kurven, puls: holen };
})();
