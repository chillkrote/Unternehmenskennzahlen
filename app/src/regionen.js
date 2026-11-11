/* ---------- Regionen auf der Weltkugel (Volkswirtschaft, Kreisebene) ----------
   Daten: <script id="regional-daten"> aus app/regional.py (VGR der Länder, Eurostat für KKS; NUTS-3), Schlüssel = Kreisschlüssel (AGS) wie
   bei den Kreisgrenzen (geo/kreise_de.geojson) und den Wahlergebnissen je Kreis (Wahlregister, Einheit mit geo "kreise-de").
   - Karte: Kreise eingefärbt nach einer Kennzahl und einem Jahr (Quintile), ab Zoomstufe 2 sichtbar; Klick wählt den Kreis.
   - Seitenleiste: Kennzahl und Jahr, Rangliste, Kreiskarte (alle Kennzahlen mit Verlauf und Rang unter 400 Kreisen, Wahlergebnis)
     und „Wirtschaft und Wahl“: Zusammenhang einer Kennzahl mit dem Stimmenanteil einer Partei über alle Kreise einer Wahl
     (Streudiagramm, Pearson und Spearman mit derselben Statistik wie die Korrelationsanalyse, KOR.stat).
   API-Fassung: Block wird mit der Form Volkswirtschaft geladen (globus.js: FORM_BLOECKE), Kreisgrenzen als wahlgeo/kreise-de.json,
   das Wahlregister erst, wenn „Wirtschaft und Wahl“ geöffnet wird. Einbindung: Ebene "regionen" über GLOBUS.ebene, globus.js ruft
   REGIONEN.offen()/seite()/einstieg()/legende(). */
"use strict";
const REGIONEN = (() => {
  const G = GLOBUS;
  let D = BLOCK.jetzt("regional-daten");
  const R = { serie: "r3_bip_je_einwohner", jahr: null, kreis: null, offen: false, wahl: null, partei: null, x: null, sort: "hoch" };
  try { const v = JSON.parse(localStorage.getItem("globus-regionen") || "{}"); if (v.serie) R.serie = v.serie; } catch { /* kein Speicher */ }
  const merken = () => { try { localStorage.setItem("globus-regionen", JSON.stringify({ serie: R.serie })); } catch { /* kein Speicher */ } };
  const FARBEN = ["#1b3a5b", "#2a6587", "#3f93a8", "#7cc4b0", "#e3e08f"];
  const KEIN = "#2a313b";
  const f3 = new Intl.NumberFormat("de-DE", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
  const da = () => !!(D && D.serien);
  const reihe = id => da() ? D.serien.find(s => s.id === id) || D.serien[0] : null;
  const wert = (sid, ags, j) => { const l = D.werte[sid] && D.werte[sid][ags]; const i = D.jahre.indexOf(+j); return l && i >= 0 ? l[i] : null; };
  // jüngstes Jahr, für das mindestens 90 % der Kreise einen Wert haben (Erwerbstätige: 2024 nur für Berlin und Hamburg)
  function jahrVoll(sid) {
    const n = Object.keys(D.regionen).length;
    for (let i = D.jahre.length - 1; i >= 0; i--) { let k = 0; for (const l of Object.values(D.werte[sid] || {})) if (l[i] != null) k++; if (k >= .9 * n) return D.jahre[i]; }
    return D.jahre[D.jahre.length - 1];
  }
  const jahr = () => R.jahr && D.jahre.includes(R.jahr) && querschnitt(R.serie, R.jahr).length ? R.jahr : jahrVoll(R.serie);
  const querschnitt = (sid, j) => Object.keys(D.regionen).map(a => [a, wert(sid, a, j)]).filter(x => x[1] != null);
  function format(s, v) {
    if (v == null) return "–";
    if (s.format === "pct1") return f1.format(v) + " %";
    if (s.format === "zahl1") return f1.format(v) + (s.einheit === "Tsd." ? " Tsd." : " " + s.einheit);
    if (s.einheit === "Mio. €") return v >= 1000 ? f1.format(v / 1000) + " Mrd. €" : f0.format(v) + " Mio. €";
    return f0.format(v) + (s.einheit && !/^Index/.test(s.einheit) ? " " + s.einheit : "");
  }
  // Quintile der gewählten Kennzahl im Jahr: [Grenzen], Farbe je Kreis
  function klassen() {
    const xs = querschnitt(R.serie, jahr()).map(x => x[1]).sort((a, b) => a - b);
    if (!xs.length) return [];
    return [1, 2, 3, 4].map(k => xs[Math.min(xs.length - 1, Math.floor(k * xs.length / 5))]);
  }
  const klasse = (v, gr) => v == null ? -1 : gr.filter(g => v >= g).length;
  function rang(sid, j, ags) {
    const q = querschnitt(sid, j).sort((a, b) => b[1] - a[1]);
    const i = q.findIndex(x => x[0] === ags);
    return i < 0 ? null : { r: i + 1, n: q.length };
  }

  /* ----- Grenzen ----- */
  let FC = null, GEO_LAEDT = null;
  function grenzen() {
    if (FC) return FC;
    const g = G.geo().KREISE;
    if (g && g.features) return (FC = g);
    if (!GEO_LAEDT) {
      let url = null; try { url = (JSON.parse(document.getElementById("wa-geo-nachladen").textContent) || {})["kreise-de"]; } catch { url = null; }
      if (url) GEO_LAEDT = fetch(url).then(r => r.ok ? r.json() : Promise.reject(Error("HTTP " + r.status))).then(fc => { FC = fc; anwenden(); })
        .catch(e => { console.warn("Kreisgrenzen nicht geladen:", e.message); });
    }
    return null;
  }
  function flaechen() {
    const fc = grenzen();
    if (!fc || !da()) return { type: "FeatureCollection", features: [] };
    const gr = klassen(), j = jahr(), s = reihe(R.serie);
    return { type: "FeatureCollection", features: fc.features.map(f => {
      const a = String(f.properties.id), v = wert(R.serie, a, j), k = klasse(v, gr);
      return { type: "Feature", geometry: f.geometry, properties: { id: a, name: (D.regionen[a] || [])[1] || f.properties.name, farbe: k < 0 ? KEIN : FARBEN[k],
        txt: format(s, v), gewaehlt: a === R.kreis ? 1 : 0 } };
    }) };
  }

  /* ----- Karte ----- */
  const karte = () => G.karte();
  G.ebene({ id: "regionen", name: "Kreise in Deutschland (BIP, Bevölkerung, Wirtschaftsstruktur)", gruppe: "Volkswirtschaft", an: D !== null, geplant: D === null, formen: ["vwl"],
    quellen: m => { m.addSource("rg-kreise", { type: "geojson", data: flaechen() }); },
    schichten: (m, vor) => {
      const sch = def => m.addLayer({ ...def, metadata: { ebene: "regionen" } }, vor);
      sch({ id: "rg-flaeche", type: "fill", source: "rg-kreise", minzoom: 3.4, paint: { "fill-color": ["get", "farbe"], "fill-opacity": ["interpolate", ["linear"], ["zoom"], 3.6, 0, 4.4, .82] } });
      sch({ id: "rg-linie", type: "line", source: "rg-kreise", minzoom: 3.4, paint: { "line-color": ["case", ["==", ["get", "gewaehlt"], 1], "#ffa828", "#07090c"],
        "line-width": ["case", ["==", ["get", "gewaehlt"], 1], 2.4, .4], "line-opacity": ["interpolate", ["linear"], ["zoom"], 3.6, 0, 4.4, 1] } });
    },
    klick: (e, m) => {
      if (m.getZoom() < 4) return false;
      const f = m.queryRenderedFeatures(e.point, { layers: ["rg-flaeche"].filter(id => m.getLayer(id)) });
      if (!f.length) return false;
      waehlen(f[0].properties.id); return true;
    } });
  if (G.infoTip) G.infoTip("rg-flaeche", p => { const s = reihe(R.serie); return `<b>${esc(p.name)}</b><br>${esc(s ? s.name : "")} ${esc(String(jahr()))}: <b>${esc(p.txt)}</b><br><span class="pct">klicken für die Kreiskarte</span>`; });
  function anwenden() {
    const m = karte();
    if (m && m.getSource("rg-kreise")) m.getSource("rg-kreise").setData(flaechen());
    if (G.zustand().form === "vwl") { G.legendeKarte(); if (R.offen || G.zustand().land === "DE") G.seiteZeichnen(); }
  }
  function waehlen(ags, fliegen) {
    R.kreis = R.kreis === ags && !fliegen ? null : ags; R.offen = true;
    anwenden();
    if (fliegen && R.kreis && karte() && FC) { const f = FC.features.find(x => String(x.properties.id) === ags); if (f) { const b = G.bbox(f); if (b) karte().fitBounds(b, { padding: 60, maxZoom: 8.5, duration: 900 }); } }
  }

  /* ----- Wahlen je Kreis (Wahlregister) ----- */
  let WD = null, WLAEDT = null;
  function wahlenMitKreisen() {
    if (!WD) return [];
    return WD.wahlen.filter(w => w.land === "DE" && (w.einheiten || []).some(u => u.geo === "kreise-de")).sort((a, b) => (b.datum || "").localeCompare(a.datum || ""));
  }
  function wahlregister() {
    if (WD || WLAEDT) return;
    WLAEDT = BLOCK.warte("wahlen-daten").then(d => { WD = d; anwenden(); });
  }
  // Werte der Kreis-Einheit einer Wahl (in der API-Fassung ausgelagert: u.nach)
  const KW = new Map();
  function kreiswerte(w) {
    const u = (w.einheiten || []).find(x => x.geo === "kreise-de"); if (!u) return null;
    if (u.werte && Object.keys(u.werte).length) return u.werte;
    if (u.nach && !KW.has(u.nach)) KW.set(u.nach, fetch(u.nach).then(r => r.ok ? r.json() : Promise.reject(Error("HTTP " + r.status))).then(x => { u.werte = x; anwenden(); })
      .catch(e => { console.warn("Kreiswerte nicht geladen:", e.message); }));
    return null;
  }
  const stimmen = (w, x) => { const s = (x && x.s) || {}; const k = (w.stimmarten && w.stimmarten.find(a => a[0] === "z")) ? "z" : Object.keys(s)[0]; return s[k] || []; };
  const anteil = (w, x, p) => { const e = stimmen(w, x).find(y => y[0] === p); return e ? e[2] : 0; };
  function parteienVon(w, werte) {
    const sum = {}; Object.values(werte).forEach(x => stimmen(w, x).forEach(y => { sum[y[0]] = (sum[y[0]] || 0) + y[1]; }));
    return Object.entries(sum).sort((a, b) => b[1] - a[1]).map(x => x[0]);
  }

  /* ----- Seitenleiste ----- */
  const opt = (v, t, sel) => `<option value="${esc(String(v))}"${String(v) === String(sel) ? " selected" : ""}>${esc(t)}</option>`;
  function spark(sid, ags) {
    const pts = D.jahre.map((j, i) => [j, (D.werte[sid][ags] || [])[i]]).filter(x => x[1] != null);
    if (pts.length < 2) return "";
    const ys = pts.map(x => x[1]), lo = Math.min(...ys), hi = Math.max(...ys), sp = hi - lo || 1;
    const X = i => i / (pts.length - 1) * 100, Y = v => 24 - (v - lo) / sp * 22;
    return `<svg viewBox="0 0 100 26" preserveAspectRatio="none" aria-hidden="true"><path d="${pts.map((x, i) => `${i ? "L" : "M"}${X(i).toFixed(1)},${Y(x[1]).toFixed(1)}`).join("")}" fill="none" stroke="#a3acb8" stroke-width="1.2" vector-effect="non-scaling-stroke"/></svg>`;
  }
  function steuerung() {
    const s = reihe(R.serie), j = jahr();
    return `<div class="gk-block rg-steuer"><label>Kennzahl <select data-rg="serie">${D.serien.map(x => opt(x.id, x.name, s.id)).join("")}</select></label>
      <label>Jahr <select data-rg="jahr">${[...D.jahre].reverse().filter(y => querschnitt(s.id, y).length).map(y => opt(y, String(y), j)).join("")}</select></label>
      <p class="gk-quelle">${esc(s.hinweis || "")} · Quelle: ${esc(s.quelle || "")}</p></div>`;
  }
  function rangliste() {
    const s = reihe(R.serie), j = jahr(), q = querschnitt(s.id, j).sort((a, b) => b[1] - a[1]), n = Object.keys(D.regionen).length;
    const xs = q.map(x => x[1]).sort((a, b) => a - b), med = xs.length ? xs[Math.floor(xs.length / 2)] : null;
    const liste = (R.sort === "hoch" ? q : [...q].reverse()).slice(0, 12);
    return `<div class="gk-block"><h3>${esc(s.name)} ${esc(String(j))}</h3>
      <p class="gk-quelle">${f0.format(q.length)} von ${f0.format(n)} Kreisen mit Wert · Median ${esc(format(s, med))}</p>
      <div class="gk-chips" style="margin:6px 0"><button type="button" data-rg-sort="hoch" aria-pressed="${R.sort === "hoch"}">Höchste</button><button type="button" data-rg-sort="tief" aria-pressed="${R.sort === "tief"}">Niedrigste</button></div>
      <ul class="gk-liste">${liste.map(([a, v]) => `<li><button type="button" data-rg-kreis="${esc(a)}">${esc(D.regionen[a][1])}</button><span class="r">${esc(format(s, v))}</span></li>`).join("")}</ul></div>`;
  }
  function kreisKarte(a) {
    const reg = D.regionen[a]; if (!reg) return "";
    const kacheln = D.serien.map(s => { const j = jahrVoll(s.id), v = wert(s.id, a, j), r = rang(s.id, j, a);
      return `<div><div class="t">${esc(s.name)} <span class="pct">${esc(String(j))}</span></div><div class="v">${esc(format(s, v))}</div><div class="z">${r ? `Rang ${f0.format(r.r)} von ${f0.format(r.n)}` : ""}</div>${spark(s.id, a)}</div>`; }).join("");
    let wahl = "";
    if (WD) {
      const ws = wahlenMitKreisen().map(w => [w, kreiswerte(w)]).filter(x => x[1] && x[1][a]);
      wahl = ws.map(([w, kw]) => { const x = kw[a], l = stimmen(w, x).slice(0, 6), bet = x.wb ? x.w / x.wb * 100 : null;
        return `<div class="gk-block"><h3>${esc(w.titel)} ${esc((w.datum || "").slice(0, 4))}${w.gebiet !== "DE" ? " · " + esc(w.name || w.gebiet) : ""}</h3>
          <table class="gk-tab"><tbody>${l.map(y => `<tr><td>${esc(y[0])}</td><td>${f1.format(y[2])} %</td><td class="pct">${y[3] != null ? (y[2] - y[3] >= 0 ? "+" : "−") + f1.format(Math.abs(y[2] - y[3])) : ""}</td></tr>`).join("")}</tbody></table>
          ${bet != null ? `<p class="gk-quelle">Wahlbeteiligung ${f1.format(bet)} % · ${esc(w.quelle && w.quelle.name || "")}</p>` : ""}</div>`; }).join("");
    } else wahl = `<div class="gk-block"><h3>Wahlergebnisse im Kreis</h3><div class="gk-chips"><button type="button" data-rg-wahlen>Wahlergebnisse laden</button></div></div>`;
    return `<div class="gk-block"><h3>${esc(reg[1])}</h3><p class="unter">Kreisschlüssel ${esc(a)} · NUTS-3 ${esc(reg[0])} · ${esc(reg[2])}</p>
      <div class="gk-kz" style="margin-top:8px">${kacheln}</div>
      <p class="gk-quelle" style="margin-top:6px">Jüngstes Jahr mit Werten für fast alle Kreise; Linie = Verlauf seit ${esc(String(D.jahre[0]))}; Rang unter allen Kreisen (1 = höchster Wert).</p></div>${wahl}`;
  }
  // Wirtschaft und Wahl: Kennzahl (x) gegen Stimmenanteil einer Partei (y) über die Kreise einer Wahl
  function wirtschaftUndWahl() {
    if (!WD) return `<div class="gk-block"><h3>Wirtschaft und Wahl</h3><p class="gk-leer">Zusammenhang zwischen einer Kennzahl und dem Stimmenanteil einer Partei über alle Kreise einer Wahl.</p>
      <div class="gk-chips" style="margin-top:8px"><button type="button" data-rg-wahlen>${WLAEDT ? "Wahlergebnisse werden geladen …" : "Wahlergebnisse laden"}</button></div></div>`;
    const ws = wahlenMitKreisen();
    if (!ws.length) return `<div class="gk-block"><h3>Wirtschaft und Wahl</h3><p class="gk-leer">Im Wahlregister gibt es keine Wahl mit Ergebnissen je Kreis.</p></div>`;
    const w = ws.find(x => x.id === R.wahl) || ws.find(x => x.gebiet === "DE") || ws[0];
    const kw = kreiswerte(w);
    if (!kw) return `<div class="gk-block"><h3>Wirtschaft und Wahl</h3><p class="gk-leer">Ergebnisse je Kreis werden geladen …</p></div>`;
    const parteien = parteienVon(w, kw).slice(0, 10), p = parteien.includes(R.partei) ? R.partei : parteien[0];
    const s = reihe(R.x || R.serie);
    // Kennzahl im Jahr der Wahl, sonst das jüngste Jahr davor mit Werten für fast alle Kreise
    const wj = +(w.datum || "").slice(0, 4), jahre = D.jahre.filter(y => y <= wj && querschnitt(s.id, y).length >= .9 * Object.keys(kw).length);
    const j = jahre.length ? jahre[jahre.length - 1] : jahrVoll(s.id);
    const pkt = Object.keys(kw).filter(a => D.regionen[a]).map(a => [a, wert(s.id, a, j), anteil(w, kw[a], p)]).filter(x => x[1] != null);
    const st = pkt.length >= 3 && typeof KOR !== "undefined" ? KOR.stat(pkt.map(x => x[1]), pkt.map(x => x[2])) : null;
    const auswahl = `<div class="rg-steuer"><label>Wahl <select data-rg="wahl">${ws.map(x => opt(x.id, `${x.titel} ${(x.datum || "").slice(0, 4)}${x.gebiet !== "DE" ? " (" + (x.name || x.gebiet) + ")" : ""}`, w.id)).join("")}</select></label>
      <label>Partei <select data-rg="partei">${parteien.map(x => opt(x, x, p)).join("")}</select></label>
      <label>Kennzahl <select data-rg="x">${D.serien.map(x => opt(x.id, x.name, s.id)).join("")}</select></label></div>`;
    const deut = r => r == null ? "" : Math.abs(r) < .1 ? "kein erkennbarer" : Math.abs(r) < .3 ? `schwacher ${r > 0 ? "positiver" : "negativer"}` : Math.abs(r) < .5 ? `mittlerer ${r > 0 ? "positiver" : "negativer"}` : `starker ${r > 0 ? "positiver" : "negativer"}`;
    const p3 = v => v == null ? "–" : v < .001 ? "< 0,001" : f3.format(v);
    // Steigung je sinnvollem Schritt der Kennzahl (z. B. je 10.000 € statt je 1 €)
    const xs = pkt.map(x => x[1]), schritt = 10 ** Math.floor(Math.log10(((Math.max(...xs) - Math.min(...xs)) || 1) / 5));
    return `<div class="gk-block"><h3>Wirtschaft und Wahl</h3>${auswahl}${streu(pkt, s, p, j)}
      ${st ? `<table class="gk-tab" style="margin-top:6px"><tbody><tr><td>Kreise</td><td>${f0.format(st.n)}</td></tr>
        <tr><td>Pearson r</td><td>${f2.format(st.r)} <span class="pct">(95 %: ${st.ci ? f2.format(st.ci[0]) + " bis " + f2.format(st.ci[1]) : "–"})</span></td></tr>
        <tr><td>Spearman ρ</td><td>${f2.format(st.rho)}</td></tr><tr><td>p-Wert (r)</td><td>${p3(st.p)}</td></tr>
        ${st.b != null ? `<tr><td>Steigung</td><td>${f2.format(st.b * schritt)} Pkt. je ${esc(format(s, schritt))}</td></tr>` : ""}</tbody></table>
        <p class="gk-quelle" style="margin-top:6px">${esc(deut(st.r))} Zusammenhang zwischen ${esc(s.name)} (${esc(String(j))}) und dem Anteil von ${esc(p)} (${esc(stimmartName(w))}). Er gilt für Kreise, nicht für Personen (ökologischer Fehlschluss), und ist keine Ursache. Kreise mit großen Pendlerströmen haben ein hohes BIP je Einwohner.</p>` : ""}
      <p class="gk-quelle">Wahl: ${esc(w.quelle && w.quelle.name || "")}. Wirtschaft: ${esc(D.quelle)}.</p></div>`;
  }
  const stimmartName = w => { const k = (w.stimmarten || []).find(a => a[0] === "z") || (w.stimmarten || [])[0]; return k ? k[1] : "Stimmen"; };
  function streu(pkt, s, partei, j) {
    if (pkt.length < 3) return `<p class="gk-leer">Zu wenige Kreise mit Werten.</p>`;
    const xs = pkt.map(x => x[1]), ys = pkt.map(x => x[2]), x0 = Math.min(...xs), x1 = Math.max(...xs), y1 = Math.max(...ys) * 1.05 || 1;
    const W = 300, H = 180, L = 34, B = 22, X = v => L + (v - x0) / ((x1 - x0) || 1) * (W - L - 6), Y = v => H - B - v / y1 * (H - B - 6);
    const ticks = [0, y1 / 2, y1].map(v => `<text x="${L - 4}" y="${Y(v) + 3}" text-anchor="end">${f0.format(v)}</text><line x1="${L}" x2="${W - 6}" y1="${Y(v)}" y2="${Y(v)}" stroke="#1f252d"/>`).join("");
    const pt = pkt.map(([a, x, y]) => `<circle cx="${X(x).toFixed(1)}" cy="${Y(y).toFixed(1)}" r="${a === R.kreis ? 4.5 : 2.4}" fill="${a === R.kreis ? "#ffa828" : "rgba(124,196,255,.55)"}" data-rg-kreis="${esc(a)}"><title>${esc(D.regionen[a][1])}: ${esc(format(s, x))}, ${f1.format(y)} %</title></circle>`).join("");
    return `<svg class="rg-streu" viewBox="0 0 ${W} ${H}" role="img" aria-label="Streudiagramm ${esc(s.name)} und Anteil ${esc(partei)}">${ticks}
      <text x="${L}" y="${H - 6}">${esc(format(s, x0))}</text><text x="${W - 6}" y="${H - 6}" text-anchor="end">${esc(format(s, x1))}</text>
      <text x="${L + 2}" y="10">${esc(partei)} in %</text>${pt}</svg><p class="gk-quelle">x: ${esc(s.name)} ${esc(String(j))} · y: Stimmenanteil ${esc(partei)} · Punkt anklicken wählt den Kreis</p>`;
  }
  function seite() {
    if (D === undefined) return `<div><h2>Kreise in Deutschland</h2><p class="gk-leer">Regionaldaten werden geladen …</p></div>`;
    if (!da()) return `<div><h2>Kreise in Deutschland</h2><p class="gk-leer">Keine Regionaldaten im Build (volkswirtschaft/regional, Abruf: volkswirtschaft/skripte/abruf_eurostat_regional.py).</p></div>`;
    return `<div><div class="gk-chips" style="margin-bottom:8px"><button type="button" data-rg-schliessen>← Deutschland</button></div><h2>Kreise in Deutschland</h2>
      <p class="unter" style="margin-top:4px">400 Kreise und kreisfreie Städte (NUTS-3) · Kreis auf der Karte oder in der Liste anklicken</p></div>
      ${steuerung()}${R.kreis ? kreisKarte(R.kreis) : ""}${wirtschaftUndWahl()}${rangliste()}
      <div class="gk-block"><h3>Quelle</h3><p class="gk-quelle">${esc(D.quelle)}, Abruf ${esc(D.stand)}; ${esc(D.lizenz)}. Zuordnung NUTS-3 zu Kreisschlüssel: Eurostat LAU-NUTS 2024. Kreisgrenzen: © GeoBasis-DE / BKG, dl-de/by-2-0. Preisbereinigte Kreiswerte gibt es nicht; das Wachstum ist nominal.</p></div>`;
  }
  // Einstieg auf der Länderseite Deutschland (Volkswirtschaft)
  function einstieg() {
    if (D === null) return "";
    if (!da()) return `<div class="gk-block"><h3>Kreise</h3><p class="gk-leer">Regionaldaten werden geladen …</p></div>`;
    const s = reihe("r3_bip_je_einwohner"), j = jahrVoll(s.id), q = querschnitt(s.id, j).sort((a, b) => b[1] - a[1]);
    return `<div class="gk-block"><h3>Kreise (Regionaldaten)</h3><p class="gk-quelle">${esc(s.name)} ${esc(String(j))}: höchster Wert ${esc(D.regionen[q[0][0]][1])} (${esc(format(s, q[0][1]))}), niedrigster ${esc(D.regionen[q[q.length - 1][0]][1])} (${esc(format(s, q[q.length - 1][1]))}).</p>
      <div class="gk-chips" style="margin-top:8px"><button type="button" data-rg-oeffnen>Kreise vergleichen</button><button type="button" data-rg-oeffnen="wahl">Wirtschaft und Wahl</button></div></div>`;
  }
  function legende() {
    if (!da()) return "";
    const s = reihe(R.serie), gr = klassen(), grenzen = [null, ...gr, null];
    return `<b>Kreise · ${esc(s.name)} ${esc(String(jahr()))}</b>${FARBEN.map((c, i) => `<span><svg width="12" height="12" aria-hidden="true"><rect width="12" height="12" rx="2" fill="${c}"/></svg>${grenzen[i] == null ? "unter " + esc(format(s, grenzen[i + 1])) : grenzen[i + 1] == null ? "ab " + esc(format(s, grenzen[i])) : esc(format(s, grenzen[i])) + " bis " + esc(format(s, grenzen[i + 1]))}</span>`).join("")}<small>Quintile der 400 Kreise · ab Stufe 2 sichtbar</small>`;
  }

  /* ----- Ereignisse ----- */
  addEventListener("sphaerae:block", e => { if (e.detail && e.detail.id === "regional-daten") { D = BLOCK.jetzt("regional-daten"); const eb = G.ebenen().find(x => x.id === "regionen"); if (eb && D) { eb.geplant = false; } anwenden(); } });
  document.addEventListener("click", ev => {
    if (!G.imGlobus()) return;
    const t = ev.target, a = n => { const x = t.closest && t.closest("[" + n + "]"); return x ? x.getAttribute(n) : null; };
    let v;
    if ((v = a("data-rg-oeffnen")) != null) { R.offen = true; if (v === "wahl") wahlregister(); const m = karte(); if (m && m.getZoom() < 4.6) m.flyTo({ center: [10.4, 51.1], zoom: 5, duration: 1200 }); G.seiteZeichnen(); return; }
    if (a("data-rg-schliessen") != null) { R.offen = false; R.kreis = null; anwenden(); G.seiteZeichnen(); return; }
    if ((v = a("data-rg-kreis")) != null) { waehlen(v, true); return; }
    if ((v = a("data-rg-sort")) != null) { R.sort = v; G.seiteZeichnen(); return; }
    if (a("data-rg-wahlen") != null) { wahlregister(); G.seiteZeichnen(); return; }
  });
  document.addEventListener("change", ev => {
    const t = ev.target; if (!t.matches || !t.matches("[data-rg]")) return;
    const k = t.dataset.rg, v = t.value;
    if (k === "serie") { R.serie = v; R.jahr = null; merken(); }
    else if (k === "jahr") R.jahr = +v;
    else if (k === "wahl") { R.wahl = v; R.partei = null; }
    else if (k === "partei") R.partei = v;
    else if (k === "x") R.x = v;
    anwenden(); G.seiteZeichnen();
  });
  document.addEventListener("globus:form", ev => { if (!ev.detail || ev.detail.form !== "vwl") R.offen = false; });
  return { offen: () => R.offen && G.zustand().form === "vwl", seite, einstieg, legende, zustand: () => R, waehlen, daten: () => D, oeffnen: () => { R.offen = true; G.seiteZeichnen(); } };
})();
