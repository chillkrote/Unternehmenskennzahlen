/* ---------- Volkswirtschaftliche Kennzahlen, Daten und Berichte ----------
   Daten: VD = { serien[], laender[], themen[], berichte[], daten{serie_id:{geo:[[zeit,wert],…]}}, stand } (siehe vwl.py).
   Nichts ist verdrahtet: jede Reihe aus volkswirtschaft/serien.csv erscheint automatisch (Thema, Länder, Format aus der CSV).
   Läuft vor dem Hauptskript; nutzt dessen Hilfsfunktionen (panel, esc, f0, f1, f2) erst zur Laufzeit. */
"use strict";
const VWL = (() => {
  let VD = null, SER = {}, LAND = {}, THEMA = {};
  const S = { land: "DE", serie: null, geos: ["DE", "EA20", "FR"], fenster: "5", thema: "alle", ranking: null };
  const FARBE = { DE: "var(--amber)", EA20: "#e8ecf1", EU27_2020: "#939eac", FR: "#2f86dd", IT: "#17a88a", ES: "#9a6fe0", NL: "#e8484f", AT: "#3ecf6e" };
  const STRICH = { EU27_2020: "5 4" };
  const farbe = g => FARBE[g] || "var(--s4)";
  const FENSTER = { "5": "5 J.", "10": "10 J.", "20": "20 J.", max: "Max." };

  function init(d) {
    VD = d && d.serien && d.serien.length ? d : null;
    if (!VD) return false;
    SER = Object.fromEntries(VD.serien.map(s => [s.serie_id, s]));
    LAND = Object.fromEntries(VD.laender.map(l => [l.geo, l.name]));
    THEMA = Object.fromEntries(VD.themen.map(t => [t.thema, t.name]));
    S.serie = (VD.serien.find(s => s.kern) || VD.serien[0]).serie_id;
    return true;
  }
  const da = () => !!VD;

  /* ----- Zeit und Zahlen ----- */
  const MONATE = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"];
  function tx(z) {
    let m;
    if ((m = /^(\d{4})-Q(\d)$/.exec(z))) return +m[1] + (m[2] - 1) / 4;
    if ((m = /^(\d{4})-(\d\d)$/.exec(z))) return +m[1] + (m[2] - 1) / 12;
    return +z;
  }
  function zl(z) {
    let m;
    if ((m = /^(\d{4})-Q(\d)$/.exec(z))) return `Q${m[2]} ${m[1]}`;
    if ((m = /^(\d{4})-(\d\d)$/.exec(z))) return `${MONATE[m[2] - 1]} ${m[1]}`;
    return z;
  }
  function fv(s, v) {
    if (v == null) return "n. v.";
    switch (s.format) {
      case "pct1": return f1.format(v) + " %";
      case "pct2": return f2.format(v) + " %";
      case "zahl0": return f0.format(v);
      default: return f1.format(v);
    }
  }
  const dlt = (s, v) => v == null ? "" : (v > 0 ? "+" : v < 0 ? "−" : "") + (s.art === "niveau" || s.art === "index" ? f1.format(Math.abs(v)) + " %" : f1.format(Math.abs(v)) + " Pkt.");
  const pts = (id, g) => (VD.daten[id] && VD.daten[id][g]) || [];
  const geosVon = id => Object.keys(VD.daten[id] || {}).sort((a, b) => Object.keys(FARBE).indexOf(a) - Object.keys(FARBE).indexOf(b));
  const lname = g => LAND[g] || g;
  /* letzter Wert samt Veränderung (Raten/Salden: gegen Vorperiode; Niveaus/Indizes: gegen Vorjahr in %) */
  function letzter(s, g) {
    const p = pts(s.serie_id, g); if (!p.length) return null;
    const [z, v] = p[p.length - 1];
    let d = null;
    if (s.art === "niveau" || s.art === "index") {
      const n = s.frequenz === "Q" ? 4 : s.frequenz === "M" ? 12 : 1, vj = p[p.length - 1 - n];
      d = vj && vj[1] ? (v / vj[1] - 1) * 100 : null;
    } else if (p.length > 1) d = v - p[p.length - 2][1];
    return { z, v, d };
  }

  /* ----- Diagramme ----- */
  function spark(p, n) {
    p = p.slice(-n); if (p.length < 2) return "";
    const W = 120, H = 34, xs = p.map(q => tx(q[0])), x0 = xs[0], x1 = xs[xs.length - 1], vs = p.map(q => q[1]);
    const lo = Math.min(...vs, 0 > Math.min(...vs) ? 0 : Infinity), hi = Math.max(...vs, 0 < Math.max(...vs) ? 0 : -Infinity), r = hi - lo || 1;
    const X = t => ((t - x0) / (x1 - x0 || 1)) * W, Y = v => H - 3 - ((v - lo) / r) * (H - 6);
    const d = p.map((q, i) => (i ? "L" : "M") + X(xs[i]).toFixed(1) + " " + Y(q[1]).toFixed(1)).join("");
    const zero = lo < 0 && hi > 0 ? `<line x1="0" x2="${W}" y1="${Y(0)}" y2="${Y(0)}" stroke="var(--line)"/>` : "";
    return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:34px" aria-hidden="true">${zero}<path d="${d}" fill="none" stroke="var(--amber)" stroke-width="1.6" stroke-linejoin="round"/><circle cx="${X(x1)}" cy="${Y(vs[vs.length - 1])}" r="2.4" fill="var(--amber)"/></svg>`;
  }
  function nice(lo, hi, n = 5) {
    const r = hi - lo || 1, st0 = r / n, mag = Math.pow(10, Math.floor(Math.log10(st0))), st = [1, 2, 2.5, 5, 10].map(k => k * mag).find(k => k >= st0);
    const a = Math.floor(lo / st) * st, b = Math.ceil(hi / st) * st, tk = [];
    for (let v = a; v <= b + st / 2; v += st) tk.push(+v.toFixed(10));
    return { a, b, tk };
  }
  /* Linien über die Zeit: je Land eine Linie, Hover liefert alle Länder zu einem Zeitpunkt */
  function linien(s, geos, fenster) {
    const reihen = geos.map(g => ({ g, p: pts(s.serie_id, g) })).filter(r => r.p.length);
    if (!reihen.length) return `<p class="n">Für diese Auswahl liegen keine Werte vor.</p>`;
    const tmax = Math.max(...reihen.map(r => tx(r.p[r.p.length - 1][0])));
    const tmin = fenster === "max" ? Math.min(...reihen.map(r => tx(r.p[0][0]))) : tmax - +fenster;
    reihen.forEach(r => { r.p = r.p.filter(q => tx(q[0]) >= tmin - 1e-9); });
    const alle = reihen.flatMap(r => r.p.map(q => q[1]));
    const eng = innerWidth < 640, W = eng ? 430 : 820, H = eng ? 280 : 320, L = 46, R = 14, T = 12, B = 28, ach = nice(Math.min(...alle), Math.max(...alle));
    const X = t => L + ((t - tmin) / (tmax - tmin || 1)) * (W - L - R), Y = v => T + (1 - (v - ach.a) / (ach.b - ach.a || 1)) * (H - T - B);
    let h = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(s.name)}">`;
    ach.tk.forEach(v => { h += `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="${v === 0 ? "var(--ink-3)" : "var(--grid)"}"/><text x="${L - 8}" y="${Y(v) + 4}" text-anchor="end" style="font-family:var(--mono);font-size:10px">${fv({ format: s.format === "pct2" ? "pct2" : "zahl1" }, v).replace(/\.0$/, "")}</text>`; });
    const ja = [], j0 = Math.ceil(tmin), j1 = Math.floor(tmax), schritt = Math.max(1, Math.ceil((j1 - j0 + 1) / 8));
    for (let j = j0; j <= j1; j += schritt) ja.push(j);
    ja.forEach(j => { h += `<text x="${X(j)}" y="${H - 8}" text-anchor="middle" style="font-size:10px">${j}</text><line x1="${X(j)}" x2="${X(j)}" y1="${H - B}" y2="${H - B + 4}" stroke="var(--ink-3)"/>`; });
    reihen.slice().sort((a, b) => (a.g === "DE") - (b.g === "DE")).forEach(r => {
      const d = r.p.map((q, i) => (i ? "L" : "M") + X(tx(q[0])).toFixed(1) + " " + Y(q[1]).toFixed(1)).join("");
      h += `<path d="${d}" fill="none" stroke="${farbe(r.g)}" stroke-width="${r.g === "DE" ? 2.4 : 1.6}" stroke-linejoin="round"${STRICH[r.g] ? ` stroke-dasharray="${STRICH[r.g]}"` : ""}/>`;
      const q = r.p[r.p.length - 1];
      h += `<circle cx="${X(tx(q[0]))}" cy="${Y(q[1])}" r="3" fill="${farbe(r.g)}"/>`;
    });
    /* unsichtbare Streifen für Tooltips je Zeitpunkt */
    const zeiten = [...new Set(reihen.flatMap(r => r.p.map(q => q[0])))].sort(), bw = Math.max(2, (W - L - R) / zeiten.length);
    zeiten.forEach(z => {
      const zeilen = reihen.map(r => { const q = r.p.find(x => x[0] === z); return q ? `<span style="color:${r.g === "DE" ? "#ffa828" : "#e8ecf1"}">${esc(lname(r.g))}</span> ${fv(s, q[1])}` : null; }).filter(Boolean);
      h += `<rect x="${X(tx(z)) - bw / 2}" y="${T}" width="${bw}" height="${H - T - B}" fill="transparent" data-tip="${esc(`<b>${zl(z)}</b>\n${zeilen.join("\n")}`)}"/>`;
    });
    return h + "</svg>";
  }
  function balken(s, zeilen) {
    const eng = innerWidth < 640, W = eng ? 430 : 760, zh = 30, L = eng ? 96 : 130, R = 64, H = zeilen.length * zh + 8, vs = zeilen.map(z => z.v);
    const lo = Math.min(0, ...vs), hi = Math.max(0, ...vs), X = v => L + ((v - lo) / (hi - lo || 1)) * (W - L - R);
    let h = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Länder im Vergleich"><line x1="${X(0)}" x2="${X(0)}" y1="0" y2="${H}" stroke="var(--ink-3)"/>`;
    zeilen.forEach((z, i) => {
      const y = 4 + i * zh, x = X(Math.min(0, z.v)), w = Math.max(1, Math.abs(X(z.v) - X(0)));
      h += `<text x="${L - 10}" y="${y + 17}" text-anchor="end" style="font-size:12px;${z.g === "DE" ? "fill:var(--amber);font-weight:600" : ""}">${esc(lname(z.g))}</text>
        <rect x="${x}" y="${y + 3}" width="${w}" height="${zh - 10}" rx="2" fill="${z.g === "DE" ? "var(--amber)" : "var(--s3)"}" data-tip="${esc(`<b>${esc(lname(z.g))}</b>\n${zl(z.z)}: ${fv(s, z.v)}${z.vj != null ? `\nVorjahr: ${fv(s, z.vj)}` : ""}`)}"/>
        <text x="${z.v >= 0 ? X(z.v) + 6 : X(0) + 6}" y="${y + 17}" text-anchor="start" style="font-family:var(--mono);font-size:11px;fill:var(--ink)">${fv(s, z.v)}</text>`;
    });
    return h + "</svg>";
  }

  /* ----- Bausteine ----- */
  const chipRow = (items, attr, aktiv) => `<div class="ctrl" style="margin-bottom:10px">${items.map(([id, n]) => `<button type="button" ${attr}="${esc(id)}" aria-pressed="${id === aktiv}">${esc(n)}</button>`).join("")}</div>`;
  const geoChips = (id) => `<div class="ctrl" style="margin-bottom:10px">${geosVon(id).map(g => `<button type="button" data-vgeo="${esc(g)}" aria-pressed="${S.geos.includes(g)}" style="${S.geos.includes(g) ? `border-color:${farbe(g)}` : ""}"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${farbe(g)};margin-right:6px"></span>${esc(lname(g))}</button>`).join("")}</div>`;
  const stand = s => `Eurostat, Datensatz ${esc(s.datensatz)}${s.filter ? " (" + esc(s.filter.replace(/;/g, ", ")) + ")" : ""} · abgerufen ${esc(s.abruf)} · letzter Wert ${esc(zl(s.letzter_zeitraum))}`;
  const eurostatUrl = s => `https://ec.europa.eu/eurostat/databrowser/view/${encodeURIComponent(s.datensatz)}/default/table`;
  const geld = (s, g) => { const l = letzter(s, g); return l ? l : null; };
  const kachel = (s, g) => {
    const l = geld(s, g); if (!l) return "";
    const farbeD = l.d == null ? "var(--ink-3)" : "var(--ink-2)";
    return `<a class="tile" href="#v-reihe" data-vserie="${esc(s.serie_id)}" style="--gf:var(--amber);text-decoration:none"><div class="g" style="display:flex;gap:8px;align-items:baseline"><b>${esc(s.name)}</b></div>
      <div style="display:flex;align-items:baseline;gap:10px"><strong style="font:500 24px/1.1 var(--mono)">${fv(s, l.v)}</strong><span style="font:12px var(--mono);color:${farbeD}">${l.d == null ? "" : dlt(s, l.d)}</span></div>${spark(pts(s.serie_id, g), s.frequenz === "M" ? 60 : s.frequenz === "Q" ? 20 : 10)}
      <div class="mini">${esc(zl(l.z))}${s.art === "niveau" || s.art === "index" ? " · Veränderung ggü. Vorjahr" : s.frequenz === "A" ? "" : " · Veränderung ggü. Vorperiode"}</div></a>`;
  };

  /* ----- Ansichten ----- */
  function viewUeb() {
    const g = S.land, kern = VD.serien.filter(s => s.kern && pts(s.serie_id, g).length);
    const kopf = `<div class="picks" style="margin-bottom:10px"><h2 style="margin:0;font:600 22px/1.2 var(--sans)">Konjunkturüberblick</h2><span class="chip" style="cursor:default">${esc(lname(g))}</span></div>`
      + chipRow(VD.laender.filter(l => VD.serien.some(s => pts(s.serie_id, l.geo).length)).map(l => [l.geo, l.name]), "data-vland", g);
    const themen = VD.themen.filter(t => VD.serien.some(s => s.thema === t.thema));
    const sp = VD.laender.map(l => l.geo).filter(x => VD.serien.some(s => s.kern && pts(s.serie_id, x).length)).sort((a, b) => Object.keys(FARBE).indexOf(a) - Object.keys(FARBE).indexOf(b));
    const matrix = `<div class="scroll"><table class="kzt"><thead><tr><th style="text-align:left">Kennzahl</th><th style="text-align:left">Stand</th>${sp.map(x => `<th style="${x === "DE" ? "color:var(--amber)" : ""}">${esc(lname(x))}</th>`).join("")}</tr></thead><tbody>${themen.map(t => `<tr><td colspan="${sp.length + 2}" class="grp">${esc(t.name)}</td></tr>` + VD.serien.filter(s => s.thema === t.thema && sp.some(x => pts(s.serie_id, x).length)).map(s => {
      const ls = sp.map(x => letzter(s, x)), z = ls.find(Boolean);
      return `<tr><td style="text-align:left;font-family:var(--sans)"><a class="flink" href="#v-reihe" data-vserie="${esc(s.serie_id)}">${esc(s.name)}</a> <span class="pct">${esc(s.einheit)}</span></td><td class="n" style="text-align:left">${z ? esc(zl(z.z)) : ""}</td>${ls.map((l, i) => `<td class="${l ? "" : "n"}" style="${sp[i] === "DE" ? "color:var(--amber)" : ""}">${l ? fv(s, l.v) : "–"}</td>`).join("")}</tr>`;
    }).join("")).join("")}</tbody></table></div>`;
    return `<div class="grid"><div class="p" style="grid-column:span 12;border:0;background:none">${kopf}<div class="tape" style="margin-top:12px">${kern.map(s => kachel(s, g)).join("")}</div></div>
      ${panel({ code: "VWL 1", titel: "Länder im Überblick", sub: "jeweils letzter verfügbarer Wert; Stand je Zeile kann abweichen", body: matrix, fuss: `Quelle: Eurostat (Dissemination-API), Stand der Abrufe ${esc(VD.stand)}. Raten in % ggü. Vorjahr bzw. Vorquartal laut Reihenbeschreibung; Niveaus und Indizes in den Einheiten der Reihe. Euribor nur für den Euroraum.` })}</div>`;
  }

  function serienAuswahl() {
    const gr = VD.themen.map(t => ({ t, l: VD.serien.filter(s => s.thema === t.thema) })).filter(x => x.l.length);
    return `<select id="vserie" aria-label="Reihe" style="max-width:100%">${gr.map(x => `<optgroup label="${esc(x.t.name)}">${x.l.map(s => `<option value="${esc(s.serie_id)}"${s.serie_id === S.serie ? " selected" : ""}>${esc(s.name)}</option>`).join("")}</optgroup>`).join("")}</select>`;
  }
  function viewReihe() {
    const s = SER[S.serie], gs = geosVon(s.serie_id), sel = S.geos.filter(g => gs.includes(g));
    const auswahl = sel.length ? sel : [gs[0]];
    const kopf = `<div class="picks" style="margin-bottom:10px">${serienAuswahl()}<span class="n">${esc(s.einheit)} · ${s.frequenz === "M" ? "monatlich" : s.frequenz === "Q" ? "vierteljährlich" : "jährlich"}</span></div>`;
    const ctrl = geoChips(s.serie_id) + chipRow(Object.entries(FENSTER), "data-vfen", S.fenster);
    const tab = `<div class="scroll"><table class="kzt"><thead><tr><th style="text-align:left">Land</th><th>Letzter Wert</th><th>Stand</th><th>${s.art === "niveau" || s.art === "index" ? "Δ ggü. Vorjahr" : "Δ ggü. Vorperiode"}</th><th>Min (Fenster)</th><th>Max (Fenster)</th></tr></thead><tbody>${auswahl.map(g => {
      const l = letzter(s, g), p = pts(s.serie_id, g), tm = tx(p[p.length - 1][0]), w = p.filter(q => S.fenster === "max" || tx(q[0]) >= tm - +S.fenster).map(q => q[1]);
      return `<tr><td style="text-align:left;font-family:var(--sans);${g === "DE" ? "color:var(--amber)" : ""}">${esc(lname(g))}</td><td>${fv(s, l.v)}</td><td class="n">${esc(zl(l.z))}</td><td class="n">${l.d == null ? "–" : dlt(s, l.d)}</td><td class="n">${fv(s, Math.min(...w))}</td><td class="n">${fv(s, Math.max(...w))}</td></tr>`;
    }).join("")}</tbody></table></div>`;
    return `<div class="grid">${panel({ code: "VWL 2", titel: "Zeitreihe", sub: esc(s.name) + (s.hinweis ? " · " + esc(s.hinweis) : ""), body: kopf + ctrl + linien(s, auswahl, S.fenster),
      fuss: `${stand(s)}. <a class="flink" href="${esc(eurostatUrl(s))}" target="_blank" rel="noopener">Datensatz bei Eurostat</a>` })}
      ${panel({ code: "VWL 3", titel: "Kennwerte", sub: "für die gewählten Länder und das gewählte Fenster", body: tab })}</div>`;
  }

  function viewLaender() {
    const s = SER[S.serie], gs = geosVon(s.serie_id);
    const zeilen = gs.map(g => { const p = pts(s.serie_id, g); if (!p.length) return null; const n = s.frequenz === "Q" ? 4 : s.frequenz === "M" ? 12 : 1, vj = p[p.length - 1 - n]; return { g, z: p[p.length - 1][0], v: p[p.length - 1][1], vj: vj ? vj[1] : null }; }).filter(Boolean).sort((a, b) => b.v - a.v);
    const kopf = `<div class="picks" style="margin-bottom:10px">${serienAuswahl()}<span class="n">${esc(s.einheit)}</span></div>`;
    const tab = `<div class="scroll"><table class="kzt"><thead><tr><th style="text-align:left">Land</th><th style="text-align:left">Stand</th><th>Wert</th><th>Vorjahr</th><th>Rang</th></tr></thead><tbody>${zeilen.map((z, i) => `<tr><td style="text-align:left;font-family:var(--sans);${z.g === "DE" ? "color:var(--amber)" : ""}">${esc(lname(z.g))}</td><td class="n" style="text-align:left">${esc(zl(z.z))}</td><td>${fv(s, z.v)}</td><td class="n">${fv(s, z.vj)}</td><td class="n">${i + 1}</td></tr>`).join("")}</tbody></table></div>`;
    return `<div class="grid">${panel({ code: "VWL 4", titel: "Länder im Vergleich", sub: esc(s.name) + " · jeweils letzter Wert, absteigend", breite: "w7", body: kopf + balken(s, zeilen), fuss: stand(s) + ". Stand der Länder kann um eine Periode abweichen." })}
      <div class="col w5">${panel({ code: "VWL 5", titel: "Tabelle", body: tab })}</div></div>`;
  }

  function viewQuellen() {
    const b = VD.berichte || [];
    const bt = b.length ? `<div class="scroll"><table class="kzt"><thead><tr><th style="text-align:left">Bericht</th><th style="text-align:left">Herausgeber</th><th style="text-align:left">Rhythmus</th><th style="text-align:left">Thema</th></tr></thead><tbody>${b.map(x => `<tr><td style="text-align:left;font-family:var(--sans)"><a class="flink" href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.titel)}</a><div class="pct">${esc(x.beschreibung)}</div></td><td class="n" style="text-align:left;font-family:var(--sans)">${esc(x.herausgeber)}</td><td class="n" style="text-align:left;font-family:var(--sans)">${esc(x.rhythmus)}</td><td class="n" style="text-align:left;font-family:var(--sans)">${esc(x.thema)}</td></tr>`).join("")}</tbody></table></div>` : `<p class="n">Noch keine Berichte erfasst (volkswirtschaft/berichte.csv).</p>`;
    const st = `<div class="scroll"><table class="kzt"><thead><tr><th style="text-align:left">Reihe</th><th style="text-align:left">Thema</th><th style="text-align:left">Einheit</th><th>Takt</th><th>Zeitraum</th><th style="text-align:left">Datensatz</th></tr></thead><tbody>${VD.serien.map(s => `<tr><td style="text-align:left;font-family:var(--sans)"><a class="flink" href="#v-reihe" data-vserie="${esc(s.serie_id)}">${esc(s.name)}</a></td><td class="n" style="text-align:left;font-family:var(--sans)">${esc(THEMA[s.thema] || s.thema)}</td><td class="n" style="text-align:left;font-family:var(--sans)">${esc(s.einheit)}</td><td class="n">${esc(s.frequenz)}</td><td class="n">${esc(s.erster_zeitraum)} – ${esc(s.letzter_zeitraum)}</td><td class="n" style="text-align:left"><a class="flink" href="${esc(eurostatUrl(s))}" target="_blank" rel="noopener">${esc(s.datensatz)}</a></td></tr>`).join("")}</tbody></table></div>`;
    return `<div class="grid">${panel({ code: "BER", titel: "Berichte", sub: "regelmäßige Veröffentlichungen zur Konjunktur", breite: "w6", body: bt, fuss: "Links führen zu den Seiten der Herausgeber (neuer Tab)." })}
      ${panel({ code: "QUE", titel: "Datenquellen", sub: `${VD.serien.length} Reihen · Rohantworten der Eurostat-API im Repo unter volkswirtschaft/rohdaten/`, breite: "w6", body: st, fuss: `Abruf mit volkswirtschaft/skripte/abruf_eurostat.py, Stand ${esc(VD.stand)}. Weitere Reihen erscheinen hier automatisch, sobald sie in volkswirtschaft/serien.csv stehen.` })}</div>`;
  }

  /* ----- Bedienung ----- */
  function klick(t) {
    const g = a => { const e = t.closest && t.closest("[" + a + "]"); return e ? e.getAttribute(a) : null; };
    let v;
    if ((v = g("data-vland")) != null) { S.land = v; render(); return true; }
    if ((v = g("data-vgeo")) != null) { S.geos = S.geos.includes(v) ? S.geos.filter(x => x !== v) : [...S.geos, v]; if (!S.geos.length) S.geos = [v]; render(); return true; }
    if ((v = g("data-vfen")) != null) { S.fenster = v; render(); return true; }
    if ((v = g("data-vserie")) != null) { S.serie = v; if (location.hash === "#v-ueb" || location.hash === "#v-quellen") return false; render(); return true; }
    return false;
  }
  function nachRender() {
    const e = document.getElementById("vserie");
    if (e) e.addEventListener("change", () => { S.serie = e.value; render(); });
  }
  const meta = () => VD ? `${VD.serien.length} Reihen · ${VD.laender.length} Länder · Eurostat, Stand ${VD.stand}` : "";
  const finden = q => { q = (q || "").trim().toLowerCase(); return q && VD ? VD.serien.find(s => s.serie_id === q || s.name.toLowerCase().includes(q)) : null; };
  const waehle = id => { S.serie = id; };
  const datalist = () => VD ? VD.serien.map(s => `<option value="${esc(s.name)}">`).join("") : "";
  return { init, da, viewUeb, viewReihe, viewLaender, viewQuellen, klick, nachRender, meta, finden, waehle, datalist };
})();
