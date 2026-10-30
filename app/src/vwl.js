/* ---------- Volkswirtschaftliche Kennzahlen, Daten und Berichte ----------
   Daten: VD = { serien[], laender[], themen[], berichte[], indikatoren[], prognosen[], daten{serie_id:{geo:[[zeit,wert],…]}}, stand } (siehe vwl.py).
   Nichts ist verdrahtet: jede Reihe aus volkswirtschaft/serien.csv erscheint automatisch (Thema, Länder, Format aus der CSV).
   Reihen mit `prognose_ab` (OECD Economic Outlook) zeigen Werte ab diesem Zeitraum als Projektion (gestrichelt).
   Läuft vor dem Hauptskript; nutzt dessen Hilfsfunktionen (panel, esc, f0, f1, f2) erst zur Laufzeit. */
"use strict";
const VWL = (() => {
  let VD = null, ALLE_DATEN = null, SER = {}, LAND = {}, THEMA = {}, OECD = {}, REIHE = {};
  const S = { land: "DE", serie: null, geos: ["DE", "EA20", "FR"], fenster: "5", ljahr: "ist", pgr: "bip_wachstum", palle: false, pjahr: "2026", pland: "US", pgeber: "DE", pherr: null, pvint: "erst", phz: "alle" };
  const FARBE = { DE: "var(--amber)", EA20: "#e8ecf1", EU27_2020: "#939eac", OECD: "#939eac" };
  const PAL = ["#2f86dd", "#17a88a", "#9a6fe0", "#e8484f", "#3ecf6e", "#d9a441", "#e07fb0", "#5ec8d8", "#b4c24a", "#c0714a"];
  const STRICH = { EU27_2020: "5 4", OECD: "5 4" };
  const AGG = ["EA20", "EU27_2020", "OECD", "G7"];
  /* gleiche Größe aus zwei Quellen: Eurostat gilt, wo es das Land hat, sonst die OECD-Reihe (z. B. USA, Japan) */
  const GLEICH = { oecd_bip_qoq: "bip_qoq", oecd_bip_yoy: "bip_yoy", oecd_inflation: "hicp_gesamt", oecd_kerninflation: "hicp_kern", oecd_arbeitslosenquote: "arbeitslosenquote" };
  const UMGEKEHRT = Object.fromEntries(Object.entries(GLEICH).map(([o, e]) => [e, o]));
  const PRESETS = [["Standard", ["DE", "EA20", "FR"]], ["Euroraum groß", ["DE", "FR", "IT", "ES", "NL"]], ["G7", ["DE", "US", "JP", "UK", "FR", "IT", "CA"]], ["Nachbarn", ["DE", "FR", "NL", "AT", "PL", "CZ", "DK", "CH", "BE", "LU"]], ["Deutschland, OECD, USA", ["DE", "OECD", "US"]]];
  const FENSTER = { "5": "5 J.", "10": "10 J.", "20": "20 J.", max: "Max." };
  const GROESSEN = { bip_wachstum: ["BIP real", "%"], inflation: ["Inflation", "%"], arbeitslosenquote: ["Arbeitslosenquote", "%"], finanzierungssaldo: ["Finanzierungssaldo des Staates", "% des BIP"], leitzins: ["Leitzins (Projektion)", "%"] };
  const INFLATION = ["inflation", "inflation_vpi", "inflation_hvpi", "inflation_pce", "inflation_cpif"];
  const INFL_TAG = { inflation_vpi: "VPI", inflation_hvpi: "HVPI", inflation_pce: "PCE", inflation_cpif: "CPIF" };
  const farbe = g => FARBE[g] || PAL[Math.max(0, S.geos.filter(x => !FARBE[x]).indexOf(g)) % PAL.length];

  function init(d) {
    VD = d && d.serien && d.serien.length ? d : null;
    if (!VD) return false;
    ALLE_DATEN = VD;
    SER = Object.fromEntries(VD.serien.map(s => [s.serie_id, s]));
    LAND = Object.fromEntries(VD.laender.map(l => [l.geo, l.name]));
    OECD = Object.fromEntries(VD.laender.map(l => [l.geo, l.oecd === "1"]));
    THEMA = Object.fromEntries(VD.themen.map(t => [t.thema, t.name]));
    VD.prognosen = VD.prognosen || [];
    VD.indikatoren = VD.indikatoren || [];
    S.serie = (VD.serien.find(s => s.kern) || VD.serien[0]).serie_id;
    return true;
  }
  const da = () => !!VD;
  function setLand(code) {
    if (!ALLE_DATEN) return;
    if (code === 'alle') { VD = ALLE_DATEN; return; }
    VD = {...ALLE_DATEN, laender: ALLE_DATEN.laender.filter(l=>l.geo===code),
      daten: Object.fromEntries(Object.entries(ALLE_DATEN.daten).map(([key,values])=>[key,Object.fromEntries(Object.entries(values).filter(([geo])=>geo===code))])),
      prognosen: ALLE_DATEN.prognosen.filter(x=>!x.geo || x.geo===code)};
    S.land = code; S.geos = [code]; S.pland = code; S.pgeber = code;
  }

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
  const datumDe = d => { const t = (d || "").split("-"); return t.length === 3 ? `${t[2]}.${t[1]}.${t[0]}` : t.length === 2 ? `${MONATE[t[1] - 1]} ${t[0]}` : d; };
  const datumX = d => { const t = (d || "").split("-").map(Number); return t[0] + ((t[1] || 6) - 1) / 12 + ((t[2] || 15) - 1) / 365; };
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
  const istPunkt = (s, q) => !s.prognose_ab || q[0] < s.prognose_ab;
  const istPts = (s, g) => pts(s.serie_id, g).filter(q => istPunkt(s, q));
  const projPts = (s, g) => s.prognose_ab ? pts(s.serie_id, g).filter(q => !istPunkt(s, q)) : [];
  const GEOREIHE = Object.keys(FARBE);
  const geosVon = id => { const reihe = VD.laender.map(l => l.geo); return Object.keys(VD.daten[id] || {}).sort((a, b) => reihe.indexOf(a) - reihe.indexOf(b)); };
  const lname = g => LAND[g] || g;
  /* Reihe zu (Größe, Land): Eurostat, wenn vorhanden, sonst die gleichwertige OECD-Reihe */
  const wahl = (s, g) => pts(s.serie_id, g).length || !UMGEKEHRT[s.serie_id] ? s : (pts(UMGEKEHRT[s.serie_id], g).length ? SER[UMGEKEHRT[s.serie_id]] : s);
  /* letzter Istwert samt Veränderung (Raten/Salden: gegen Vorperiode; Niveaus/Indizes: gegen Vorjahr in %) */
  function letzter(s, g) {
    s = wahl(s, g);
    const p = istPts(s, g); if (!p.length) return null;
    const [z, v] = p[p.length - 1];
    let d = null;
    if (s.art === "niveau" || s.art === "index") {
      const n = s.frequenz === "Q" ? 4 : s.frequenz === "M" ? 12 : 1, vj = p[p.length - 1 - n];
      d = vj && vj[1] ? (v / vj[1] - 1) * 100 : null;
    } else if (p.length > 1) d = v - p[p.length - 2][1];
    return { z, v, d, s };
  }
  const projText = (s, g) => projPts(s, g).map(q => `${q[0]}: ${fv(s, q[1])}`).join(" · ");

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
  const achsenText = (s, v) => fv({ format: s.format === "pct2" ? "pct2" : "zahl1" }, v).replace(/,0$/, "").replace(/\.0$/, "");
  /* Linien über die Zeit: je Land eine Linie (Projektionen gestrichelt), Hover liefert alle Länder zu einem Zeitpunkt */
  function linien(s, geos, fenster) {
    const reihen = geos.map(g => ({ g, s: wahl(s, g), p: pts(wahl(s, g).serie_id, g) })).filter(r => r.p.length);
    if (!reihen.length) return `<p class="n">Für diese Auswahl liegen keine Werte vor.</p>`;
    const tmax = Math.max(...reihen.map(r => tx(r.p[r.p.length - 1][0])));
    const tmin = fenster === "max" ? Math.min(...reihen.map(r => tx(r.p[0][0]))) : tmax - +fenster;
    reihen.forEach(r => { r.p = r.p.filter(q => tx(q[0]) >= tmin - 1e-9); });
    const alle = reihen.flatMap(r => r.p.map(q => q[1]));
    const eng = innerWidth < 640, W = eng ? 430 : 820, H = eng ? 280 : 320, L = 46, R = 14, T = 12, B = 28, ach = nice(Math.min(...alle), Math.max(...alle));
    const X = t => L + ((t - tmin) / (tmax - tmin || 1)) * (W - L - R), Y = v => T + (1 - (v - ach.a) / (ach.b - ach.a || 1)) * (H - T - B);
    let h = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(s.name)}">`;
    ach.tk.forEach(v => { h += `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="${v === 0 ? "var(--ink-3)" : "var(--grid)"}"/><text x="${L - 8}" y="${Y(v) + 4}" text-anchor="end" style="font-family:var(--mono);font-size:10px">${achsenText(s, v)}</text>`; });
    const ja = [], j0 = Math.ceil(tmin), j1 = Math.floor(tmax), schritt = Math.max(1, Math.ceil((j1 - j0 + 1) / 8));
    for (let j = j0; j <= j1; j += schritt) ja.push(j);
    ja.forEach(j => { h += `<text x="${X(j)}" y="${H - 8}" text-anchor="middle" style="font-size:10px">${j}</text><line x1="${X(j)}" x2="${X(j)}" y1="${H - B}" y2="${H - B + 4}" stroke="var(--ink-3)"/>`; });
    const pa = s.prognose_ab && reihen.some(r => r.p.some(q => !istPunkt(r.s, q))) ? tx(s.prognose_ab) : null;
    if (pa != null && pa > tmin && pa <= tmax) h += `<line x1="${X(pa)}" x2="${X(pa)}" y1="${T}" y2="${H - B}" stroke="var(--ink-3)" stroke-dasharray="2 3"/><text x="${X(pa) + 5}" y="${T + 10}" style="font-size:10px">Projektion</text>`;
    const pfad = q => q.map((x, i) => (i ? "L" : "M") + X(tx(x[0])).toFixed(1) + " " + Y(x[1]).toFixed(1)).join("");
    reihen.slice().sort((a, b) => (a.g === "DE") - (b.g === "DE")).forEach(r => {
      const ist = r.p.filter(q => istPunkt(r.s, q)), pr = r.p.filter(q => !istPunkt(r.s, q)), w = r.g === "DE" ? 2.4 : 1.6;
      if (ist.length) h += `<path d="${pfad(ist)}" fill="none" stroke="${farbe(r.g)}" stroke-width="${w}" stroke-linejoin="round"${STRICH[r.g] ? ` stroke-dasharray="${STRICH[r.g]}"` : ""}/>`;
      if (pr.length) h += `<path d="${pfad(ist.length ? [ist[ist.length - 1], ...pr] : pr)}" fill="none" stroke="${farbe(r.g)}" stroke-width="${w}" stroke-dasharray="3 4" stroke-linejoin="round"/>`;
      const q = (ist.length ? ist : pr)[(ist.length ? ist : pr).length - 1];
      h += `<circle cx="${X(tx(q[0]))}" cy="${Y(q[1])}" r="3" fill="${farbe(r.g)}"/>`;
    });
    /* unsichtbare Streifen für Tooltips je Zeitpunkt */
    const zeiten = [...new Set(reihen.flatMap(r => r.p.map(q => q[0])))].sort(), bw = Math.max(2, (W - L - R) / zeiten.length);
    zeiten.forEach(z => {
      const zeilen = reihen.map(r => { const q = r.p.find(x => x[0] === z); return q ? `<span style="color:${r.g === "DE" ? "#ffa828" : "#e8ecf1"}">${esc(lname(r.g))}</span> ${fv(s, q[1])}${istPunkt(r.s, q) ? "" : " (Projektion)"}` : null; }).filter(Boolean);
      h += `<rect x="${X(tx(z)) - bw / 2}" y="${T}" width="${bw}" height="${H - T - B}" fill="transparent" data-tip="${esc(`<b>${zl(z)}</b>\n${zeilen.join("\n")}`)}"/>`;
    });
    return h + "</svg>";
  }
  function balken(s, zeilen) {
    const eng = innerWidth < 640, W = eng ? 430 : 760, zh = 26, L = eng ? 110 : 160, R = 64, H = zeilen.length * zh + 8, vs = zeilen.map(z => z.v);
    const lo = Math.min(0, ...vs), hi = Math.max(0, ...vs), X = v => L + ((v - lo) / (hi - lo || 1)) * (W - L - R);
    let h = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Länder im Vergleich"><line x1="${X(0)}" x2="${X(0)}" y1="0" y2="${H}" stroke="var(--ink-3)"/>`;
    zeilen.forEach((z, i) => {
      const y = 4 + i * zh, x = X(Math.min(0, z.v)), w = Math.max(1, Math.abs(X(z.v) - X(0))), fl = z.g === "DE" ? "var(--amber)" : AGG.includes(z.g) ? "var(--ink-3)" : "var(--s3)";
      h += `<text x="${L - 10}" y="${y + 15}" text-anchor="end" style="font-size:12px;${z.g === "DE" ? "fill:var(--amber);font-weight:600" : ""}">${esc(lname(z.g))}</text>
        <rect x="${x}" y="${y + 3}" width="${w}" height="${zh - 9}" rx="2" fill="${fl}" data-tip="${esc(`<b>${esc(lname(z.g))}</b>\n${zl(z.z)}: ${fv(s, z.v)}${z.vj != null ? `\nVorjahr: ${fv(s, z.vj)}` : ""}`)}"/>
        <text x="${z.v >= 0 ? X(z.v) + 6 : X(0) + 6}" y="${y + 15}" text-anchor="start" style="font-family:var(--mono);font-size:11px;fill:var(--ink)">${fv(s, z.v)}</text>`;
    });
    return h + "</svg>";
  }

  /* ----- Bausteine ----- */
  const chipRow = (items, attr, aktiv) => `<div class="ctrl" style="margin-bottom:10px">${items.map(([id, n]) => `<button type="button" ${attr}="${esc(id)}" aria-pressed="${id === aktiv}">${esc(n)}</button>`).join("")}</div>`;
  /* Länderauswahl: gewählte Länder als Chips (Klick entfernt), Schnellwahl und Auswahlfeld für alle weiteren */
  const geoChips = id => {
    const alle = geosVon(id), frei = alle.filter(g => !S.geos.includes(g));
    return `<div class="ctrl" style="margin-bottom:6px">${S.geos.filter(g => alle.includes(g)).map(g => `<button type="button" data-vgeo="${esc(g)}" aria-pressed="true" title="Klick entfernt das Land" style="border-color:${farbe(g)}"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${farbe(g)};margin-right:6px"></span>${esc(lname(g))} ×</button>`).join("")}
      <select id="vgeoadd" aria-label="Land hinzufügen"><option value="">Land hinzufügen …</option>${frei.map(g => `<option value="${esc(g)}">${esc(lname(g))}</option>`).join("")}</select></div>
      <div class="ctrl" style="margin-bottom:10px"><span class="n" style="margin-right:6px">Schnellwahl</span>${PRESETS.map(([n]) => `<button type="button" data-vpreset="${esc(n)}">${esc(n)}</button>`).join("")}</div>`;
  };
  const QUELLEN = { Eurostat: "Eurostat", OECD: "OECD Data", ifo: "ifo Institut" };
  const stand = s => `${QUELLEN[s.quelle] || s.quelle}, ${esc(s.datensatz)}${s.filter ? " (" + esc(s.filter.replace(/;/g, ", ")) + ")" : ""} · abgerufen ${esc(s.abruf)} · letzter Wert ${esc(zl(s.letzter_zeitraum))}`;
  const quellUrl = s => s.quelle === "Eurostat" ? `https://ec.europa.eu/eurostat/databrowser/view/${encodeURIComponent(s.datensatz)}/default/table` : s.quelle === "OECD" ? "https://data-explorer.oecd.org/" : s.url;
  const quellLink = s => `<a class="flink" href="${esc(sicherUrl(quellUrl(s)))}" target="_blank" rel="noopener">${esc(s.quelle === "ifo" ? "Seite bei ifo" : s.quelle === "OECD" ? "OECD Data Explorer" : "Datensatz bei Eurostat")}</a>`;
  const kachel = (s0, g) => {
    const l = letzter(s0, g); if (!l) return "";
    const s = l.s, farbeD = l.d == null ? "var(--ink-3)" : "var(--ink-2)";
    return `<a class="tile" href="#v-reihe" data-vserie="${esc(s.serie_id)}" style="--gf:var(--amber);text-decoration:none"><div class="g" style="display:flex;gap:8px;align-items:baseline"><b>${esc(s.name)}</b></div>
      <div style="display:flex;align-items:baseline;gap:10px"><strong style="font:500 24px/1.1 var(--mono)">${fv(s, l.v)}</strong><span style="font:12px var(--mono);color:${farbeD}">${l.d == null ? "" : dlt(s, l.d)}</span></div>${spark(istPts(s, g), s.frequenz === "M" ? 60 : s.frequenz === "Q" ? 20 : 10)}
      <div class="mini">${esc(zl(l.z))}${s.art === "niveau" || s.art === "index" ? " · Veränderung ggü. Vorjahr" : s.frequenz === "A" ? "" : " · Veränderung ggü. Vorperiode"}${projPts(s, g).length ? ` · Projektion ${esc(projText(s, g))}` : ""}</div></a>`;
  };
  const landWahl = (id, wert, aktiv) => `<select id="${id}" aria-label="Land" style="max-width:100%">${VD.laender.filter(l => aktiv(l.geo)).map(l => `<option value="${esc(l.geo)}"${l.geo === wert ? " selected" : ""}>${esc(l.name)}</option>`).join("")}</select>`;

  /* ----- Ansichten ----- */
  function viewUeb() {
    const g = S.land, hatDaten = geo => VD.serien.some(s => pts(s.serie_id, geo).length);
    const kern = VD.serien.filter(s => s.kern && !GLEICH[s.serie_id] && pts(wahl(s, g).serie_id, g).length);
    const kopf = `<div class="picks" style="margin-bottom:10px"><h2 style="margin:0;font:600 22px/1.2 var(--sans)">Konjunkturüberblick</h2>${landWahl("vland", g, hatDaten)}</div>`;
    const sp = S.geos.filter(hatDaten);
    const zeilenS = VD.serien.filter(s => !GLEICH[s.serie_id] && !s.prognose_ab && sp.some(x => pts(wahl(s, x).serie_id, x).length));
    const themen = VD.themen.filter(t => zeilenS.some(s => s.thema === t.thema));
    const matrix = `<div class="scroll"><table class="kzt"><thead><tr><th style="text-align:left">Kennzahl</th><th style="text-align:left">Stand</th>${sp.map(x => `<th style="${x === "DE" ? "color:var(--amber)" : ""}">${esc(lname(x))}</th>`).join("")}</tr></thead><tbody>${themen.map(t => `<tr><td colspan="${sp.length + 2}" class="grp">${esc(t.name)}</td></tr>` + zeilenS.filter(s => s.thema === t.thema).map(s => {
      const ls = sp.map(x => letzter(s, x)), z = ls.find(Boolean);
      return `<tr><td style="text-align:left;font-family:var(--sans)"><a class="flink" href="#v-reihe" data-vserie="${esc(s.serie_id)}">${esc(s.name)}</a> <span class="pct">${esc(s.einheit)}</span></td><td class="n" style="text-align:left">${z ? esc(zl(z.z)) : ""}</td>${ls.map((l, i) => `<td class="${l ? "" : "n"}" style="${sp[i] === "DE" ? "color:var(--amber)" : ""}">${l ? fv(l.s, l.v) : "–"}</td>`).join("")}</tr>`;
    }).join("")).join("")}</tbody></table></div>`;
    const tabKopf = `<div class="picks" style="margin-bottom:10px"><span class="n">Spalten dieser Tabelle: gewählte Länder der Zeitreihen- und Länderansicht</span></div>${geoChips(zeilenS.length ? zeilenS[0].serie_id : S.serie)}`;
    return `<div class="grid"><div class="p" style="grid-column:span 12;border:0;background:none">${kopf}<div class="tape" style="margin-top:12px">${kern.map(s => kachel(s, g)).join("")}</div></div>
      ${panel({ code: "VWL 1", titel: "Länder im Überblick", sub: "jeweils letzter verfügbarer Istwert; Stand je Zeile kann abweichen", body: tabKopf + matrix, fuss: `Quellen: Eurostat (Dissemination-API) für europäische Länder, sonst OECD (Data API); Stand der Abrufe ${esc(VD.stand)}. Raten in % ggü. Vorjahr bzw. Vorquartal laut Reihenbeschreibung; Niveaus und Indizes in den Einheiten der Reihe. Projektionen stehen in der Zeitreihen- und Länderansicht.` })}</div>`;
  }

  function serienAuswahl() {
    const gr = VD.themen.map(t => ({ t, l: VD.serien.filter(s => s.thema === t.thema) })).filter(x => x.l.length);
    return `<select id="vserie" aria-label="Reihe" style="max-width:100%">${gr.map(x => `<optgroup label="${esc(x.t.name)}">${x.l.map(s => `<option value="${esc(s.serie_id)}"${s.serie_id === S.serie ? " selected" : ""}>${esc(s.name)}</option>`).join("")}</optgroup>`).join("")}</select>`;
  }
  const takt = s => s.frequenz === "M" ? "monatlich" : s.frequenz === "Q" ? "vierteljährlich" : "jährlich";
  function viewReihe() {
    const s = SER[S.serie], gs = geosVon(s.serie_id), sel = S.geos.filter(g => gs.includes(g));
    const auswahl = sel.length ? sel : [gs[0]];
    const kopf = `<div class="picks" style="margin-bottom:10px">${serienAuswahl()}<span class="n">${esc(s.einheit)} · ${takt(s)} · ${esc(s.quelle)}</span></div>`;
    const ctrl = geoChips(s.serie_id) + chipRow(Object.entries(FENSTER), "data-vfen", S.fenster);
    const proj = !!s.prognose_ab;
    const tab = `<div class="scroll"><table class="kzt"><thead><tr><th style="text-align:left">Land</th><th>Letzter Istwert</th><th>Stand</th><th>${s.art === "niveau" || s.art === "index" ? "Δ ggü. Vorjahr" : "Δ ggü. Vorperiode"}</th><th>Min (Fenster)</th><th>Max (Fenster)</th>${proj ? "<th>Projektion</th>" : ""}</tr></thead><tbody>${auswahl.map(g => {
      const l = letzter(s, g), p = pts(s.serie_id, g); if (!l) return `<tr><td style="text-align:left;font-family:var(--sans)">${esc(lname(g))}</td><td colspan="${proj ? 6 : 5}" class="n">nur Projektion: ${esc(projText(s, g))}</td></tr>`;
      const tm = tx(l.z), w = p.filter(q => istPunkt(s, q) && (S.fenster === "max" || tx(q[0]) >= tm - +S.fenster)).map(q => q[1]);
      return `<tr><td style="text-align:left;font-family:var(--sans);${g === "DE" ? "color:var(--amber)" : ""}">${esc(lname(g))}</td><td>${fv(s, l.v)}</td><td class="n">${esc(zl(l.z))}</td><td class="n">${l.d == null ? "–" : dlt(s, l.d)}</td><td class="n">${fv(s, Math.min(...w))}</td><td class="n">${fv(s, Math.max(...w))}</td>${proj ? `<td class="n" style="text-align:left">${esc(projText(s, g)) || "–"}</td>` : ""}</tr>`;
    }).join("")}</tbody></table></div>`;
    return `<div class="grid">${panel({ code: "VWL 2", titel: "Zeitreihe", sub: esc(s.name) + (s.hinweis ? " · " + esc(s.hinweis) : ""), body: kopf + ctrl + linien(s, auswahl, S.fenster),
      fuss: `${stand(s)}. ${quellLink(s)}${proj ? ` · Projektion ab ${esc(s.prognose_ab)}` : ""}` })}
      ${panel({ code: "VWL 3", titel: "Kennwerte", sub: "für die gewählten Länder und das gewählte Fenster", body: tab })}</div>`;
  }

  function viewLaender() {
    const s = SER[S.serie], gs = geosVon(s.serie_id), proj = projPts(s, gs.find(g => projPts(s, g).length) || "DE").map(q => q[0]), jahr = S.ljahr !== "ist" && proj.includes(S.ljahr) ? S.ljahr : "ist";
    const zeilen = gs.map(g => {
      const p = jahr === "ist" ? istPts(s, g) : pts(s.serie_id, g).filter(q => q[0] === jahr); if (!p.length) return null;
      const n = s.frequenz === "Q" ? 4 : s.frequenz === "M" ? 12 : 1, all = pts(s.serie_id, g), i = all.findIndex(q => q[0] === p[p.length - 1][0]), vj = all[i - n];
      return { g, z: p[p.length - 1][0], v: p[p.length - 1][1], vj: vj ? vj[1] : null };
    }).filter(Boolean).sort((a, b) => b.v - a.v);
    const kopf = `<div class="picks" style="margin-bottom:10px">${serienAuswahl()}<span class="n">${esc(s.einheit)} · ${takt(s)}</span></div>` + (proj.length ? chipRow([["ist", "Letzter Istwert"], ...proj.map(j => [j, "Projektion " + j])], "data-vljahr", jahr) : "");
    const tab = `<div class="scroll"><table class="kzt"><thead><tr><th style="text-align:left">Land</th><th style="text-align:left">Stand</th><th>Wert</th><th>Vorjahr</th><th>Rang</th></tr></thead><tbody>${zeilen.map((z, i) => `<tr><td style="text-align:left;font-family:var(--sans);${z.g === "DE" ? "color:var(--amber)" : ""}">${esc(lname(z.g))}</td><td class="n" style="text-align:left">${esc(zl(z.z))}</td><td>${fv(s, z.v)}</td><td class="n">${fv(s, z.vj)}</td><td class="n">${i + 1}</td></tr>`).join("")}</tbody></table></div>`;
    return `<div class="grid">${panel({ code: "VWL 4", titel: "Länder im Vergleich", sub: esc(s.name) + (jahr === "ist" ? " · jeweils letzter Istwert, absteigend" : " · Projektion " + jahr + ", absteigend"), breite: "w7", body: kopf + balken(s, zeilen), fuss: stand(s) + ". Stand der Länder kann um eine Periode abweichen. Grau: Ländergruppen (Euroraum, EU-27, OECD, G7)." })}
      <div class="col w5">${panel({ code: "VWL 5", titel: "Tabelle", body: tab })}</div></div>`;
  }

  /* ----- Prognosen ----- */
  const BELEG = { "Primärdokument": ["P", "Primärdokument gelesen (PDF/Seite des Herausgebers)"], Presse: ["M", "Zahlen aus Pressemeldungen, nicht am Original geprüft"], "OECD-API": ["A", "OECD Data API"], API: ["A", "API des Herausgebers (z. B. EZB Data Portal)"] };
  const jahre = ["2025", "2026", "2027", "2028"];
  function ausgaben(geo, grp, nurNeueste) {
    const gl = grp === "inflation" ? INFLATION : [grp];
    let l = VD.prognosen.filter(p => p.geo === geo && gl.includes(p.groesse) && jahre.some(j => p.werte[j] != null));
    l.sort((a, b) => (b.datum > a.datum ? 1 : -1));
    if (nurNeueste) { const seen = {}; l = l.filter(p => seen[p.herausgeber] ? false : (seen[p.herausgeber] = true)); }
    else { const first = {}; l.forEach(p => { if (!(p.herausgeber in first)) first[p.herausgeber] = p.datum; }); l.sort((a, b) => (first[a.herausgeber] < first[b.herausgeber] ? 1 : first[a.herausgeber] > first[b.herausgeber] ? -1 : a.herausgeber < b.herausgeber ? -1 : b.datum > a.datum ? 1 : -1)); }
    if (geo !== "DE" && nurNeueste) { const k = p => /Konsens|Professional Forecasters/.test(p.herausgeber) ? 0 : 1; l.sort((a, b) => k(a) - k(b) || (b.datum > a.datum ? 1 : b.datum < a.datum ? -1 : 0)); }
    return l;
  }
  const pf = (p, v) => v == null ? "–" : fv({ format: "pct1" }, v);
  /* Kalenderjahr-Wert; Projektionen auf Quartalsbasis (Bank of England: Q3 des Jahres) füllen die Spalte des Jahres und werden markiert */
  const wj = (p, j) => p.werte[j] != null ? p.werte[j] : (p.werte[j + "-Q3"] != null ? p.werte[j + "-Q3"] : null);
  const imQ = (p, j) => p.werte[j] == null && p.werte[j + "-Q3"] != null;
  const konsens = p => /Konsens|Professional Forecasters/.test(p.herausgeber);
  function prognoseTabelle(l, fuss) {
    const bel = p => { const b = BELEG[p.beleg] || ["?", p.beleg]; return `<a class="flink" href="${esc(sicherUrl(p.url))}" target="_blank" rel="noopener" data-tip="${esc(b[1] + (p.hinweis ? "\n" + p.hinweis : ""))}">${b[0]}</a>`; };
    const st = [];
    jahre.forEach(j => { const v = l.filter(p => !konsens(p)).map(p => wj(p, j)).filter(x => x != null); st.push(v.length ? { n: v.length, lo: Math.min(...v), hi: Math.max(...v), m: v.reduce((a, b) => a + b, 0) / v.length } : null); });
    return `<div class="scroll"><table class="kzt"><thead><tr><th style="text-align:left">Herausgeber</th><th style="text-align:left">Ausgabe</th><th style="text-align:left">Stand</th>${jahre.map(j => `<th>${j}</th>`).join("")}<th title="P = Primärdokument gelesen, M = Pressemeldung, A = OECD-API">Beleg</th></tr></thead><tbody>${l.map(p => `<tr><td style="text-align:left;font-family:var(--sans);${p.herausgeber === "Gemeinschaftsdiagnose" || konsens(p) ? "font-weight:600" : ""}">${esc(p.herausgeber)}${INFL_TAG[p.groesse] ? ` <span class="pct">${INFL_TAG[p.groesse]}</span>` : ""}</td><td class="n" style="text-align:left;font-family:var(--sans)">${esc(p.ausgabe)}</td><td class="n" style="text-align:left">${esc(datumDe(p.datum))}</td>${jahre.map(j => `<td class="${wj(p, j) == null ? "n" : ""}"${imQ(p, j) ? ` data-tip="Vierquartalswert im 3. Quartal ${j}, nicht Kalenderjahr"` : ""}>${pf(p, wj(p, j))}${imQ(p, j) ? "<sup>Q3</sup>" : ""}</td>`).join("")}<td class="n">${bel(p)}</td></tr>`).join("")}</tbody>${fuss ? `<tfoot><tr><td colspan="3" style="text-align:left;font-family:var(--sans)"><b>Spanne</b> (Anzahl)</td>${st.map(x => `<td class="n">${x ? `${f1.format(x.lo)}–${f1.format(x.hi)} (${x.n})` : "–"}</td>`).join("")}<td></td></tr><tr><td colspan="3" style="text-align:left;font-family:var(--sans)"><b>Durchschnitt</b></td>${st.map(x => `<td>${x ? f1.format(x.m) + " %" : "–"}</td>`).join("")}<td></td></tr></tfoot>` : ""}</table></div>`;
  }
  /* Revisionen: Verlauf der Prognose für ein Zieljahr über die Veröffentlichungsdaten, eine Linie je Herausgeber */
  function revisionen(geo, grp, jahr) {
    const gl = grp === "inflation" ? INFLATION : [grp];
    const l = VD.prognosen.filter(p => p.geo === geo && gl.includes(p.groesse) && p.werte[jahr] != null && !konsens(p));
    const je = {}; l.forEach(p => (je[p.herausgeber] = je[p.herausgeber] || []).push({ x: datumX(p.datum), d: p.datum, a: p.ausgabe, v: p.werte[jahr] }));
    const hs = Object.keys(je).filter(h => je[h].length > 1);
    if (!hs.length) return `<p class="n">Für diese Auswahl liegen zu wenige Ausgaben vor.</p>`;
    hs.forEach(h => je[h].sort((a, b) => a.x - b.x));
    const alle = hs.flatMap(h => je[h]), xs = alle.map(q => q.x), vs = alle.map(q => q.v), x0 = Math.min(...xs) - 0.05, x1 = Math.max(...xs) + 0.05;
    const eng = innerWidth < 640, W = eng ? 430 : 760, H = eng ? 280 : 320, L = 42, R = 14, T = 12, B = 28, ach = nice(Math.min(...vs), Math.max(...vs));
    const X = t => L + ((t - x0) / (x1 - x0 || 1)) * (W - L - R), Y = v => T + (1 - (v - ach.a) / (ach.b - ach.a || 1)) * (H - T - B);
    const col = h => h === "Gemeinschaftsdiagnose" ? "var(--amber)" : h === "OECD" ? "#e8ecf1" : PAL[hs.indexOf(h) % PAL.length];
    let o = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Revisionen der Prognose für ${jahr}">`;
    ach.tk.forEach(v => { o += `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="${v === 0 ? "var(--ink-3)" : "var(--grid)"}"/><text x="${L - 8}" y="${Y(v) + 4}" text-anchor="end" style="font-family:var(--mono);font-size:10px">${f1.format(v)}</text>`; });
    const m0 = Math.ceil((x0 - Math.floor(x0)) * 12), sch = Math.max(1, Math.round((x1 - x0) * 12 / 7));
    for (let t = Math.floor(x0) + m0 / 12; t <= x1; t += sch / 12) o += `<text x="${X(t)}" y="${H - 8}" text-anchor="middle" style="font-size:10px">${MONATE[Math.floor((t % 1) * 12 + 0.01) % 12]} ${String(Math.floor(t)).slice(2)}</text>`;
    hs.forEach(h => {
      o += `<path d="${je[h].map((q, i) => (i ? "L" : "M") + X(q.x).toFixed(1) + " " + Y(q.v).toFixed(1)).join("")}" fill="none" stroke="${col(h)}" stroke-width="${h === "Gemeinschaftsdiagnose" ? 2.4 : 1.5}" stroke-linejoin="round"/>`;
      je[h].forEach(q => { o += `<circle cx="${X(q.x)}" cy="${Y(q.v)}" r="4" fill="${col(h)}" data-tip="${esc(`<b>${esc(h)}</b>\n${esc(q.a)} (${datumDe(q.d)})\nPrognose ${jahr}: ${f1.format(q.v)} %`)}"/>`; });
    });
    return `<div class="ctrl" style="margin-bottom:8px">${hs.map(h => `<span class="chip" style="cursor:default"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${col(h)};margin-right:6px"></span>${esc(h)}</span>`).join("")}</div>${o}</svg>`;
  }

  /* ----- Treffsicherheit: Prognose gegen tatsächliche Werte (volkswirtschaft/skripte/abgleich_prognosen.py) ----- */
  const HZ = ["alle", "0 bis 6 Monate", "7 bis 12 Monate", "13 bis 18 Monate", "19 bis 24 Monate", "über 24 Monate"];
  const ISTG = { bip_wachstum: ["bip_wachstum"], inflation: ["inflation", "inflation_hvpi"], arbeitslosenquote: ["arbeitslosenquote", "arbeitslosenquote_ilo"], finanzierungssaldo: ["finanzierungssaldo"] };
  const ISTN = { inflation: "Verbraucherpreise (VPI)", inflation_hvpi: "HVPI", arbeitslosenquote: "Quote nach BA", arbeitslosenquote_ilo: "ILO-Erwerbslosenquote" };
  const zieljahre = (grp, geo = "DE") => { const gl = grp === "inflation" ? INFLATION : [grp]; return [...new Set(VD.prognosen.filter(p => p.geo === geo && gl.includes(p.groesse)).flatMap(p => Object.keys(p.werte)))].sort(); };
  const f2 = new Intl.NumberFormat("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const f2s = new Intl.NumberFormat("de-DE", { minimumFractionDigits: 1, maximumFractionDigits: 1, signDisplay: "exceptZero" });
  function treffsicherheit(grp) {
    const A = VD.abgleich;
    if (!A || !A.treffsicherheit.length) return "";
    const gs = ISTG[grp], vint = S.pvint, hz = S.phz;
    const z = A.treffsicherheit.filter(t => gs.includes(t.g) && t.v === vint && t.hz === hz).sort((a, b) => a.mae - b.mae);
    const ctrl = chipRow([["erst", "Erste Veröffentlichung"], ["aktuell", "Aktueller (revidierter) Stand"]], "data-vpvint", vint) + chipRow(HZ.map(h => [h, h === "alle" ? "Alle Horizonte" : h]), "data-vphz", hz);
    const tab = z.length ? `<div class="scroll"><table class="kzt"><thead><tr><th style="text-align:left">Herausgeber</th><th style="text-align:left">Abgrenzung</th><th title="Anzahl verglichener Prognosewerte">n</th><th title="Mittlerer absoluter Fehler in Prozentpunkten">MAE</th><th title="Mittlerer Fehler (Prognose minus Ist): positiv = Prognose im Mittel zu hoch">Bias</th><th title="Wurzel des mittleren quadratischen Fehlers">RMSE</th><th>Zeitraum</th></tr></thead><tbody>${z.map(t => `<tr${t.n < 4 ? ' style="opacity:.6"' : ""}><td style="text-align:left;font-family:var(--sans);${t.h === "Gemeinschaftsdiagnose" ? "font-weight:600" : ""}">${esc(t.h)}</td><td class="n" style="text-align:left;font-family:var(--sans)">${esc(ISTN[t.g] || "")}</td><td>${t.n}</td><td>${f2.format(t.mae)}</td><td>${f2s.format(t.bias)}</td><td>${f2.format(t.rmse)}</td><td class="n">${t.von}–${t.bis}</td></tr>`).join("")}</tbody></table></div>` : `<p class="n">Für diese Auswahl liegen keine Vergleichswerte vor.</p>`;
    return panel({ code: "VWL 9", titel: "Treffsicherheit der Prognosen", sub: `${GROESSEN[grp][0]} · Prognose gegen tatsächlichen Wert, nach Herausgeber`, breite: "w6", body: ctrl + tab,
      fuss: "Fehler = Prognose minus Ist, in Prozentpunkten; MAE = mittlerer absoluter Fehler, Bias = mittlerer Fehler (positiv: zu hoch), RMSE = Wurzel des mittleren quadratischen Fehlers. Horizont = Monate von der Veröffentlichung bis zum Ende des Zieljahres. Grau: weniger als 4 Werte. Die Jahre 2020 bis 2022 (Pandemie, Energiekrise) gehen mit ein und treiben die Fehler. Ist-Werte: erste Veröffentlichung = Stand der Gemeinschaftsdiagnose im Frühjahr nach dem Jahr (Statistisches Bundesamt, Bundesagentur für Arbeit), aktueller Stand = Eurostat bzw. jüngste Gemeinschaftsdiagnose. Quelle: volkswirtschaft/prognosen_treffsicherheit.csv, prognosen_fehler.csv, prognosen_ist.csv." });
  }
  function fehlerMatrix(grp) {
    const A = VD.abgleich;
    if (!A || !A.fehler.length) return "";
    const gs = ISTG[grp], vint = S.pvint, hz = S.phz, fk = vint === "erst" ? "fe" : "fa", ik = vint === "erst" ? "ie" : "ia";
    const f = A.fehler.filter(x => gs.includes(x.g) && x[fk] != null && (hz === "alle" || x.hz === hz));
    const hs = [...new Set(f.map(x => x.h))].sort(), js = [...new Set(f.map(x => x.j))].sort();
    if (!js.length) return "";
    const ist = {}; A.ist.filter(x => gs.includes(x.groesse) && x.vintage === vint && x.wert != null).forEach(x => { (ist[x.jahr] = ist[x.jahr] || []).push(x); });
    const farb = v => { const a = Math.min(Math.abs(v) / 3, 1) * 0.55; return v === 0 ? "" : `background:${v > 0 ? `rgba(224,92,92,${a})` : `rgba(80,150,230,${a})`}`; };
    const zeilen = js.map(j => {
      const istz = (ist[j] || []).map(x => f1.format(x.wert)).join(" / ") || "–";
      return `<tr><td style="text-align:left">${j}</td><td>${istz}</td>${hs.map(h => { const v = f.filter(x => x.h === h && x.j === j).map(x => x[fk]); if (!v.length) return `<td class="n">–</td>`; const m = v.reduce((a, b) => a + b, 0) / v.length;
        return `<td style="${farb(m)}" data-tip="${esc(`<b>${esc(h)}</b>\nZieljahr ${j}: mittlerer Fehler ${f2s.format(m)} Punkte aus ${v.length} Ausgabe${v.length > 1 ? "n" : ""}`)}">${f2s.format(m)}</td>`; }).join("")}</tr>`; }).join("");
    return panel({ code: "VWL 10", titel: "Prognosefehler nach Zieljahr", sub: `${GROESSEN[grp][0]} · mittlerer Fehler (Prognose minus Ist) je Herausgeber und Zieljahr`, breite: "w6",
      body: `<div class="scroll"><table class="kzt"><thead><tr><th style="text-align:left">Zieljahr</th><th title="Tatsächlicher Wert (bei Inflation und Arbeitslosenquote: beide Abgrenzungen)">Ist</th>${hs.map(h => `<th>${esc(h.replace("Kiel Institut (IfW Kiel)", "IfW Kiel").replace("Deutsche Bundesbank", "Bundesbank").replace("Gemeinschaftsdiagnose", "Gem.diagn."))}</th>`).join("")}</tr></thead><tbody>${zeilen}</tbody></table></div>`,
      fuss: "Rot: Prognose zu hoch, blau: zu niedrig (Sättigung bei 3 Prozentpunkten). Mittel über alle Ausgaben des Herausgebers für das Zieljahr im gewählten Horizont. Auswahl von Ist-Stand und Horizont wie in VWL 9." });
  }
  function viewProg() {
    const pgeos = new Set(VD.prognosen.map(p => p.geo));
    const pg = pgeos.has(S.pgeber) ? S.pgeber : "DE", pname = LAND[pg] || pg, de = pg === "DE";
    const hat = gr => VD.prognosen.some(p => p.geo === pg && (gr === "inflation" ? INFLATION : [gr]).includes(p.groesse));
    const grp = hat(S.pgr) ? S.pgr : (Object.keys(GROESSEN).find(hat) || "bip_wachstum"), g = GROESSEN[grp];
    const l = ausgaben(pg, grp, !S.palle);
    const ctrl = `<div class="picks" style="margin-bottom:6px">${landWahl("vpgeber", pg, x => pgeos.has(x))}</div>` + chipRow(Object.entries(GROESSEN).filter(([k]) => hat(k)).map(([k, v]) => [k, v[0]]), "data-vpgr", grp) + chipRow([["neu", "Aktuellste Ausgabe je Herausgeber"], ["alle", "Alle Ausgaben (Vergleich älterer Prognosen)"]], "data-vpalle", S.palle ? "alle" : "neu");
    const a = panel({ code: "VWL 6", titel: `Prognosen für ${pname}`, sub: `${g[0]} (${g[1]}) · ` + (de ? "Wirtschaftsforschungsinstitute, Bundesregierung, Bundesbank, EU-Kommission, IWF, OECD" : "Zentralbank, Konsensumfragen und Einzelprognostiker, Ministerien, OECD, soweit frei zugänglich"), body: ctrl + (l.length ? prognoseTabelle(l, !S.palle) : `<p class="n">Keine Prognosen erfasst.</p>`),
      fuss: `Spalten: Prognose für das jeweilige Kalenderjahr, Veränderung ggü. Vorjahr bzw. Quote; ältere Ausgaben bleiben zum Vergleich erhalten. Beleg: P = Primärdokument gelesen, M = Pressemeldung (nicht am Original geprüft), A = OECD-API; Hinweise beim Überfahren. Inflation: Kennzeichnung VPI, HVPI oder PCE je Zeile; Basis (Jahresdurchschnitt oder Q4 zu Q4) und Abgrenzung stehen im Hinweis beim Überfahren des Belegs, Geber sind deshalb nur eingeschränkt vergleichbar. Konsenszeilen (fett) sind in Spanne und Durchschnitt nicht enthalten. Quelle: volkswirtschaft/prognosen_institute.csv, prognosen_oecd.csv und prognosen_international.csv.` });
    const rv = panel({ code: "VWL 7", titel: "Revisionen der Prognose", sub: `${pname}, ${g[0]}: Prognose für ${S.pjahr} nach Veröffentlichungsdatum`, breite: "w7", body: chipRow(zieljahre(grp, pg).map(j => [j, "für " + j]), "data-vpjahr", S.pjahr) + revisionen(pg, grp, S.pjahr), fuss: "Jeder Punkt eine Ausgabe, Herausgeber mit mindestens zwei Ausgaben. Punkte überfahren für Ausgabe und Wert." });
    const oecdGeos = [...new Set(VD.prognosen.filter(p => p.herausgeber === "OECD").map(p => p.geo))];
    const fg = S.pland && oecdGeos.includes(S.pland) ? S.pland : "US", ol = (gr) => ausgaben(fg, gr, false).filter(p => p.herausgeber === "OECD");
    const ob = ["bip_wachstum", "inflation", "arbeitslosenquote", "finanzierungssaldo"].map(gr => { const x = ol(gr); return x.length ? `<h3 style="margin:14px 0 6px;font:600 13px var(--sans)">${esc(GROESSEN[gr][0])} (${esc(GROESSEN[gr][1])})</h3>${prognoseTabelle(x, false)}` : ""; }).join("");
    const oe = panel({ code: "VWL 8", titel: "OECD-Prognosen nach Land", sub: "Economic Outlook, alle Ausgaben seit November 2023", breite: "w5", body: `<div class="picks" style="margin-bottom:6px">${landWahl("vpland", fg, x => oecdGeos.includes(x))}</div>` + (ob || `<p class="n">Keine Daten.</p>`), fuss: "Quelle: OECD Data API (DSD_EO, Ausgaben 114 bis 119); Abruf mit volkswirtschaft/skripte/abruf_oecd.py. Jahreswerte ohne Gewähr der Datenrevision." });
    return `<div class="grid">${a}${rv}<div class="col w5">${oe}</div>${de ? treffsicherheit(grp) + fehlerMatrix(grp) : ""}</div>`;
  }

  function viewQuellen() {
    const b = VD.berichte || [], ind = VD.indikatoren || [];
    const zahl = x => x.letzter_wert === "" ? `<span class="n">–</span>` : `<b>${esc(x.letzter_wert.replace(".", ","))}</b> <span class="pct">${esc(x.einheit)}</span>`;
    const it = ind.length ? `<div class="scroll"><table class="kzt"><thead><tr><th style="text-align:left">Indikator</th><th>Aktuell</th><th style="text-align:left">Stand</th><th>Vorwert</th><th style="text-align:left">Veröffentlicht</th><th style="text-align:left">Nächste Termine</th></tr></thead><tbody>${ind.map(x => `<tr><td style="text-align:left;font-family:var(--sans)"><a class="flink" href="${esc(sicherUrl(x.url))}" target="_blank" rel="noopener">${esc(x.indikator)}</a> <span class="pct">${esc(x.herausgeber)}</span><div class="pct">${esc(x.beschreibung)}</div>${x.hinweis ? `<div class="pct">${esc(x.hinweis)}</div>` : ""}</td><td>${zahl(x)}</td><td class="n" style="text-align:left">${esc(x.stand ? zl(x.stand) : "")}</td><td class="n">${x.vorwert ? esc(x.vorwert.replace(".", ",")) : ""}</td><td class="n" style="text-align:left">${esc(datumDe(x.veroeffentlicht.split(" ")[0]))}${x.veroeffentlicht.includes(" ") ? " " + esc(x.veroeffentlicht.split(" ")[1]) : ""}</td><td class="n" style="text-align:left;font-family:var(--sans)">${esc(x.naechste_termine.split("; ").map(datumDe).join(" · "))}</td></tr>`).join("")}</tbody></table></div>` : "";
    const bt = b.length ? `<div class="scroll"><table class="kzt"><thead><tr><th style="text-align:left">Bericht</th><th style="text-align:left">Herausgeber</th><th style="text-align:left">Rhythmus</th><th style="text-align:left">Thema</th></tr></thead><tbody>${b.map(x => `<tr><td style="text-align:left;font-family:var(--sans)">${x.url ? `<a class="flink" href="${esc(sicherUrl(x.url))}" target="_blank" rel="noopener">${esc(x.titel)}</a>` : esc(x.titel)}<div class="pct">${esc(x.beschreibung)}</div></td><td class="n" style="text-align:left;font-family:var(--sans)">${esc(x.herausgeber)}</td><td class="n" style="text-align:left;font-family:var(--sans)">${esc(x.rhythmus)}</td><td class="n" style="text-align:left;font-family:var(--sans)">${esc(x.thema)}</td></tr>`).join("")}</tbody></table></div>` : `<p class="n">Noch keine Berichte erfasst (volkswirtschaft/berichte.csv).</p>`;
    const st = `<div class="scroll"><table class="kzt"><thead><tr><th style="text-align:left">Reihe</th><th style="text-align:left">Thema</th><th style="text-align:left">Einheit</th><th style="text-align:left">Quelle</th><th>Takt</th><th>Zeitraum</th><th style="text-align:left">Datensatz</th></tr></thead><tbody>${VD.serien.map(s => `<tr><td style="text-align:left;font-family:var(--sans)"><a class="flink" href="#v-reihe" data-vserie="${esc(s.serie_id)}">${esc(s.name)}</a></td><td class="n" style="text-align:left;font-family:var(--sans)">${esc(THEMA[s.thema] || s.thema)}</td><td class="n" style="text-align:left;font-family:var(--sans)">${esc(s.einheit)}</td><td class="n" style="text-align:left;font-family:var(--sans)">${esc(s.quelle)}</td><td class="n">${esc(s.frequenz)}</td><td class="n">${esc(s.erster_zeitraum)} – ${esc(s.letzter_zeitraum)}</td><td class="n" style="text-align:left"><a class="flink" href="${esc(sicherUrl(quellUrl(s)))}" target="_blank" rel="noopener">${esc(s.datensatz)}</a></td></tr>`).join("")}</tbody></table></div>`;
    return `<div class="grid">${ind.length ? panel({ code: "IND", titel: "Konjunkturindikatoren Deutschland", sub: "ifo, ZEW, Konsumklima, Einkaufsmanager und weitere: aktuelle Werte und Veröffentlichungstermine, soweit frei verfügbar", body: it, fuss: "Wert und Termine stammen von den Seiten der Herausgeber bzw. aus Pressemeldungen (Abruf 27.10.2026); Verlauf des ifo-Index unter Zeitreihen. Pflege: volkswirtschaft/konjunkturindikatoren.csv." }) : ""}
      ${panel({ code: "BER", titel: "Berichte", sub: "regelmäßige Veröffentlichungen zur Konjunktur", breite: "w6", body: bt, fuss: "Links führen zu den Seiten der Herausgeber (neuer Tab). Einzelne Seiten (BMWE, ifo, IWF) sind für automatisierte Abrufe gesperrt und werden nur verlinkt." })}
      ${panel({ code: "QUE", titel: "Datenquellen", sub: `${VD.serien.length} Reihen · Rohantworten im Repo unter volkswirtschaft/rohdaten/`, breite: "w6", body: st, fuss: `Abruf mit volkswirtschaft/skripte/abruf_eurostat.py, abruf_oecd.py und abruf_ifo.py, Stand ${esc(VD.stand)}. Weitere Reihen erscheinen hier automatisch, sobald sie in volkswirtschaft/serien.csv stehen.` })}</div>`;
  }

  /* ----- Bedienung ----- */
  function klick(t) {
    const g = a => { const e = t.closest && t.closest("[" + a + "]"); return e ? e.getAttribute(a) : null; };
    let v;
    if ((v = g("data-vgeo")) != null) { S.geos = S.geos.filter(x => x !== v); if (!S.geos.length) S.geos = [v]; render(); return true; }
    if ((v = g("data-vpreset")) != null) { S.geos = PRESETS.find(p => p[0] === v)[1].slice(); render(); return true; }
    if ((v = g("data-vfen")) != null) { S.fenster = v; render(); return true; }
    if ((v = g("data-vljahr")) != null) { S.ljahr = v; render(); return true; }
    if ((v = g("data-vpgr")) != null) { S.pgr = v; render(); return true; }
    if ((v = g("data-vpalle")) != null) { S.palle = v === "alle"; render(); return true; }
    if ((v = g("data-vpjahr")) != null) { S.pjahr = v; render(); return true; }
    if ((v = g("data-vpvint")) != null) { S.pvint = v; render(); return true; }
    if ((v = g("data-vphz")) != null) { S.phz = v; render(); return true; }
    if ((v = g("data-vserie")) != null) { S.serie = v; S.ljahr = "ist"; if (location.hash === "#v-ueb" || location.hash === "#v-quellen") return false; render(); return true; }
    return false;
  }
  function nachRender() {
    const bind = (id, fn) => { const e = document.getElementById(id); if (e) e.addEventListener("change", () => fn(e.value)); };
    bind("vserie", v => { S.serie = v; S.ljahr = "ist"; render(); });
    bind("vland", v => { S.land = v; render(); });
    bind("vpland", v => { S.pland = v; render(); });
    bind("vpgeber", v => { S.pgeber = v; render(); });
    bind("vgeoadd", v => { if (v && !S.geos.includes(v)) S.geos.push(v); render(); });
  }
  const meta = () => VD ? `${VD.serien.length} Reihen · ${VD.laender.filter(l => l.oecd === "1").length} OECD-Länder · Eurostat, OECD, ifo, Stand ${VD.stand}` : "";
  const finden = q => { q = (q || "").trim().toLowerCase(); return q && VD ? VD.serien.find(s => s.serie_id === q || s.name.toLowerCase().includes(q)) : null; };
  const waehle = id => { S.serie = id; S.ljahr = "ist"; };
  const datalist = () => VD ? VD.serien.map(s => `<option value="${esc(s.name)}">`).join("") : "";
  return { init, da, setLand, laender: () => ALLE_DATEN ? ALLE_DATEN.laender.map(l=>l.geo) : [], korr: () => VD && { serien: VD.serien, laender: VD.laender, themen: VD.themen, daten: VD.daten }, viewUeb, viewReihe, viewLaender, viewProg, viewQuellen, klick, nachRender, meta, finden, waehle, datalist };
})();

