/* ---------- Wahlen auf der Weltkugel (Politik & Wahlen, Ansicht „Wahlen“) ----------
   Konzept (Robin, 06.11.2026, Doc „Konzept: Wahlergebnisse auf allen Ebenen“): Die Karte zeigt immer genau eine Wahl je Gebiet.
   - Ebenenleiter (links): E0 Supranational, E1 Staat, E2 Region, E3 Kommune, E4 Gemeinde; Namen je Land aus dem Wahlregister.
     Die Ebene wechselt nur per Klick, nie durch Zoomen.
   - Satzleiste (oben): ein Satz, der sagt, was die Karte zeigt (Ebene, Wahl, Stimmart, Einheit, Färbung); jedes Wort ist ein Auswahlfeld.
   - Zoom ändert nur die Auszählungseinheit derselben Wahl (Gesamt › erste › zweite Untergliederung), mit weicher Überblendung.
     Das Schloss in der Satzleiste hält die Einheit fest.
   - Ergebniskarte (Seitenleiste): für jede Wahl und jede Einheit gleich aufgebaut (Kopf mit Ebene und Pfad, gewählte Person,
     Sitzverteilung, Stimmen mit Veränderung, Kennzahlen, Liste der Einheiten, Ortsanker zu den anderen Ebenen, Quelle).
   - Wahlkreis (Mandat) = durchgezogene Grenze, Zählgebiet = gestrichelt, keine Daten = schraffiert. Farbe gehört den Parteien.
   Daten: <script id="wahlen-daten"> aus app/wahlen_daten.py (Format dort beschrieben); Grenzen über GLOBUS.geo().
   Einbindung: Ebene "wahlen" (formen politik, ansicht wahlen); globus.js ruft WAHLEN.seite() und WAHLEN.legende(). */
"use strict";
const WAHLEN = (() => {
  // API-Fassung: Register als data/wahlen.json, gleich nach dem Start geladen (api.js: BLOCK; Ereignis sphaerae:block unten)
  let D = BLOCK.jetzt("wahlen-daten") || null;
  const D_NACH = !D && !!BLOCK.status("wahlen-daten").laedt;
  const G = GLOBUS;
  let ALLE = D ? D.wahlen : [];
  let NACH_ID = Object.fromEntries(ALLE.map(w => [w.id, w]));
  let WARTET = null;            // Wahl, die vor dem Laden des Registers gewählt wurde
  const W = { e: 1, kammer: "unterhaus", fokus: null, sel: null, stimmart: {}, faerbung: "sieger", partei: "", fest: null, ort: null, sort: "rang", filter: "", leer: null };
  try { const v = JSON.parse(localStorage.getItem("globus-wahlen") || "{}"); if (v.e >= 0 && v.e <= 4) W.e = v.e; if (v.faerbung) W.faerbung = v.faerbung; } catch { /* kein Speicher */ }
  const merken = () => { try { localStorage.setItem("globus-wahlen", JSON.stringify({ e: W.e, faerbung: W.faerbung })); } catch { /* kein Speicher */ } };
  const OP = .8, Z1 = [3.4, 4], Z2 = [5.4, 6];
  const pct = x => x == null ? "–" : f1.format(x) + " %";
  const pp = x => x == null ? "" : (x > 0 ? "+" : x < 0 ? "−" : "±") + f1.format(Math.abs(x));
  const datum = d => !d ? "" : /^\d{4}-\d{2}-\d{2}$/.test(d) ? `${d.slice(8)}.${d.slice(5, 7)}.${d.slice(0, 4)}` : d;
  const tage = d => Math.round((Date.now() - Date.parse(d + "T12:00:00Z")) / 864e5);
  const latin1 = t => [...String(t || "")].map(c => c.charCodeAt(0) < 256 ? c : c.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/ł/g, "l").replace(/[^\u0000-ÿ]/g, "")).join("");
  const aktiv = () => { const s = G.zustand(); return s.form === "politik" && s.polAnsicht === "wahlen"; };
  const karte = () => G.karte();

  /* ----- Ebenen und Namen ----- */
  const bezugsland = () => (W.fokus && NACH_ID[W.fokus] ? NACH_ID[W.fokus].land : null) || G.zustand().land || null;
  function ebenenNamen(land) {
    if (!D) return ["Supranational", "Staat", "Region", "Kommune", "Gemeinde"];
    return D.ebenen[land] || (land && D.eu.includes(land) ? D.ebenen._EU : D.ebenen._);
  }
  const ebeneName = (e, land) => ebenenNamen(land === undefined ? bezugsland() : land)[e] || ebenenNamen(null)[e];
  const marke = (e, land) => `<span class="wa-marke"><b>E${e}</b>${esc(ebeneName(e, land))}</span>`;
  const KAMMERN = [["unterhaus", "Parlament (Unterhaus oder Einkammer)"], ["oberhaus", "Oberhaus, soweit direkt gewählt"], ["praesident", "Präsidentschaftswahlen (direkt gewählt)"]];
  const kammerVon = w => w.kammer === "oberhaus" || w.kammer === "praesident" ? w.kammer : "unterhaus";
  const passtKammer = w => w.e !== 1 || kammerVon(w) === W.kammer;
  // Bundeswahlen eines Landes (E1) nach Gremium: Parlament, Oberhaus, Präsident; je Art die jüngste Wahl
  const KAMMER_REIHE = ["unterhaus", "oberhaus", "praesident"];
  function kammernVon(land) {
    const m = {};
    ALLE.filter(w => w.e === 1 && w.land === land).forEach(w => { const k = kammerVon(w); if (!m[k] || (w.datum || "") > (m[k].datum || "")) m[k] = w; });
    return KAMMER_REIHE.filter(k => m[k]).map(k => [k, m[k]]);
  }
  const wahlenEbene = (e = W.e) => ALLE.filter(w => w.e === e && (e !== 1 || passtKammer(w)));
  const GRUPPE = ["Europawahl", "Nationale Parlamente", "Landtage und Regionalparlamente", "Kreistage und Räte kreisfreier Städte", "Gemeinderäte und Bezirksvertretungen"];
  function gruppenName(e = W.e) {
    if (e === 1 && W.kammer === "oberhaus") return "Oberhäuser (direkt gewählt)";
    if (e === 1 && W.kammer === "praesident") return "Präsidentschaftswahlen";
    if (e === 2 && bezugsland() === "DE") return "Landtage";
    return GRUPPE[e];
  }

  /* ----- Ergebnisse ----- */
  const stimmart = w => W.stimmart[w.id] || (w.stimmarten && w.stimmarten[0] ? w.stimmarten[0][0] : "s");
  const stimmartName = w => ((w.stimmarten || []).find(x => x[0] === stimmart(w)) || [, "Stimmen"])[1];
  // Anteile einer Wahl oder Einheit: [[partei, stimmen, prozent, vor]] absteigend; ohne Stimmen ersatzweise die Sitze
  function anteile(w, wert) {
    const s = wert && wert.s ? wert.s : (w.g || {}).s || {};
    const l = s[stimmart(w)] || s[Object.keys(s)[0]];
    if (l && l.length) return { l: [...l].sort((a, b) => (b[2] ?? -1) - (a[2] ?? -1)), sitze: false };
    const st = wert ? wert.sitze : (w.g || {}).sitze;
    if (st && st.length) { const n = st.reduce((a, x) => a + x[1], 0) || 1; return { l: st.map(x => [x[0], x[1], x[1] / n * 100, null]).sort((a, b) => b[2] - a[2]), sitze: true }; }
    return { l: [], sitze: false };
  }
  const WGR = ["#8f8ba8", "#a58fc7", "#7f9bc4", "#b79fb0", "#98b3a0", "#c4a77f", "#8fb0b8", "#b09090"];
  const NEUTRAL = ["#9aa5b8", "#c59f74", "#86b0a0", "#b18fb7", "#a7b26f", "#7fa3c7", "#c98a8a", "#8fb9c2", "#b8a37a", "#9c94c9"];
  function farbe(w, p) {
    const f = (D.farben[w.land] || {})[p] || (w.farben || {})[p];
    if (f) return f;
    const m = /^Wählergruppe (\d+)$/.exec(p); if (m) return WGR[(+m[1] - 1) % WGR.length];
    if (/^Sonstige|^Einzelbewerber|^EB /.test(p)) return "#8b95a3";
    let h = 0; for (const c of p) h = (h * 31 + c.charCodeAt(0)) >>> 0; return NEUTRAL[h % NEUTRAL.length];
  }
  const parteiName = (w, p) => { const n = (w.wgr || {})[p]; return n ? `${p} (${n.replace(/\s*\([^)]*\)$/, "").slice(0, 28)})` : p.replace("T I E R S C H U T Z", "TIERSCHUTZ"); };
  const beteiligung = (w, wert) => { const x = wert || w.g || {}; return x.bet != null ? x.bet : x.wb ? x.w / x.wb * 100 : null; };
  const BET = [[45, "#16324f"], [55, "#1f4e79"], [65, "#2e75b6"], [75, "#5ea3d9"], [999, "#a9d1f5"]];
  const betFarbe = b => (BET.find(x => b < x[0]) || BET[4])[1];
  // Farbe und Deckkraft eines Gebiets je nach Färbung
  function bewerten(w, wert) {
    const a = anteile(w, wert), top = a.l[0], zweit = a.l[1];
    const txt = top ? `${latin1(kurzName(top[0]))} ${f1.format(top[2])} %` : "";
    if (!top) return { farbe: "#3a4655", deck: .5, txt: "", top: null };
    if (W.faerbung === "beteiligung") { const b = beteiligung(w, wert); return b == null ? { farbe: "#3a4655", deck: .35, txt: "ohne Angabe", top } : { farbe: betFarbe(b), deck: 1, txt: `Beteiligung ${f1.format(b)} %`, top }; }
    if (W.faerbung === "anteil" && W.partei) {
      const x = a.l.find(y => y[0] === W.partei);
      return { farbe: farbe(w, W.partei), deck: x ? Math.max(.08, Math.min(1, x[2] / 45)) : .04, txt: `${latin1(kurzName(W.partei))} ${x ? f1.format(x[2]) + " %" : "–"}`, top };
    }
    if (W.faerbung === "vorsprung") { const v = top[2] - (zweit ? zweit[2] : 0); return { farbe: farbe(w, top[0]), deck: Math.max(.22, Math.min(1, .22 + v / 25 * .78)), txt: `${latin1(kurzName(top[0]))} +${f1.format(v)} Pkt.`, top }; }
    return { farbe: farbe(w, top[0]), deck: 1, txt, top };
  }
  const kurzName = p => String(p).replace(/\s*\((UK|Germany|France|Japan|India|United States)\)$/, "").replace(/^Wählergruppe (\d+)$/, "WG $1");

  /* ----- Grenzen ----- */
  let GEO = null;
  const idx = (fc, key) => { const m = {}; (fc ? fc.features : []).forEach(f => { const k = String(f.properties[key]); (m[k] = m[k] || []).push(f); }); return m; };
  // Nachzuladende Grenzen (globus.py: WAHL_GEO -> dist/wahlgeo/<art>.json); geladen wird erst, wenn eine Einheit sie braucht
  const NACH = (() => { try { return JSON.parse(document.getElementById("wa-geo-nachladen").textContent) || {}; } catch { return {}; } })();
  const LAEDT = new Map();
  // Schlüssel der Grenzen, die nur die API-Fassung nachlädt (globus.py: GEO_NACH_API; sonst properties.id)
  const SCHL = (() => { try { return JSON.parse(document.getElementById("wa-geo-schluessel").textContent) || {}; } catch { return {}; } })();
  function nachladen(art) {
    if (LAEDT.has(art) || !NACH[art]) return;
    LAEDT.set(art, fetch(NACH[art]).then(r => r.ok ? r.json() : Promise.reject(Error("HTTP " + r.status)))
      .then(fc => { geo()[art] = idx(fc, SCHL[art] || "id"); PUNKT.clear(); if (aktiv()) anwenden(); })
      .catch(e => { console.warn("Wahlkreisgrenzen nicht geladen:", art, e.message); }));
  }
  // Ausgelagerte Werte großer Einheiten (Gemeinden; globus.py: wahlen_aufteilen) -> u.werte, sobald die Wahl auf der Karte ist
  const WLAEDT = new Map();
  function werteNachladen(u) {
    if (!u.nach || u.geladen) return Promise.resolve();
    if (!WLAEDT.has(u.nach)) WLAEDT.set(u.nach, fetch(u.nach).then(r => r.ok ? r.json() : Promise.reject(Error("HTTP " + r.status)))
      .then(werte => { u.werte = werte; u.geladen = true; PUNKT.clear(); if (aktiv()) anwenden(); })
      .catch(e => { console.warn("Werte nicht geladen:", u.nach, e.message); }));
    return WLAEDT.get(u.nach);
  }
  function geo() {
    if (GEO) return GEO;
    const g = G.geo();
    GEO = { laender: idx(g.LAENDER, "iso"), "de-laender": idx(g.DE_GEO, "code"), gliedstaaten: idx(g.GL_GEO, "code"), kommunen: idx(g.KO_GEO, "id"), "wahlkreise-bund": idx(g.WK, "nr"), "kreise-de": idx(g.KREISE, "id"), roh: g };
    // nicht eingebettete Grenzen (API-Fassung) fehlen hier, damit flaechen() sie nachlädt
    [["kommunen", g.KO_GEO], ["wahlkreise-bund", g.WK], ["kreise-de", g.KREISE]].forEach(([art, fc]) => { if (!fc && NACH[art]) delete GEO[art]; });
    // weitere Wahlkreisgrenzen (globus.py bettet sie als <script id="wa-geo-<art>"> ein, Schlüssel properties.id), z. B. landtagswahlkreise-nw
    document.querySelectorAll('script[id^="wa-geo-"]:not(#wa-geo-nachladen)').forEach(el => { try { const fc = JSON.parse(el.textContent); if (fc) GEO[el.id.slice(7)] = idx(fc, "id"); } catch { /* fehlt */ } });
    return GEO;
  }
  // Gliedstaaten-Grenzen (API-Fassung: data/gliedstaaten.json, globus.js lädt sie nach dem Start): Index neu, Karte neu
  addEventListener("sphaerae:block", e => {
    if (e.detail.id === "wahlen-daten") {
      D = BLOCK.jetzt("wahlen-daten") || null; ALLE = D ? D.wahlen : []; NACH_ID = Object.fromEntries(ALLE.map(w => [w.id, w]));
      if (WARTET) { const [id, fl] = WARTET; WARTET = null; wahlWaehlen(id, fl); } else if (aktiv()) anwenden(); else G.seiteZeichnen();
      return;
    }
    if (e.detail.id !== "gliedstaaten-geo" || !GEO) return;
    const g = G.geo(); GEO.gliedstaaten = idx(g.GL_GEO, "code"); GEO.roh = g; PUNKT.clear(); if (aktiv()) anwenden();
  });
  const flaechen = (art, k) => { if (!art) return []; const m = geo()[art]; if (m) return m[String(k)] || []; nachladen(art); return []; };
  const ringFlaeche = r => { let s = 0; for (let i = 0; i < r.length - 1; i++) s += r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1]; return Math.abs(s / 2); };
  const PUNKT = new Map();
  function mittelpunkt(f) {
    if (PUNKT.has(f)) return PUNKT.get(f);
    let p;
    if (f.properties && f.properties.lx != null) p = [f.properties.lx, f.properties.ly];
    else { const polys = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates; let best = polys[0][0], fl = -1;
      polys.forEach(poly => { const a = ringFlaeche(poly[0]); if (a > fl) { fl = a; best = poly[0]; } });
      let sx = 0, sy = 0; best.forEach(([x, y]) => { sx += x; sy += y; }); p = [sx / best.length, sy / best.length]; }
    PUNKT.set(f, p); return p;
  }
  const BOX = new Map();
  function box(f) {
    if (BOX.has(f)) return BOX.get(f);
    let a = [180, 90, -180, -90]; const lauf = c => { if (typeof c[0] === "number") a = [Math.min(a[0], c[0]), Math.min(a[1], c[1]), Math.max(a[2], c[0]), Math.max(a[3], c[1])]; else c.forEach(lauf); };
    lauf(f.geometry.coordinates); BOX.set(f, a); return a;
  }
  function imRing(pt, r) { let in_ = false; for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const [xi, yi] = r[i], [xj, yj] = r[j]; if ((yi > pt[1]) !== (yj > pt[1]) && pt[0] < (xj - xi) * (pt[1] - yi) / (yj - yi) + xi) in_ = !in_; } return in_; }
  function enthaelt(f, pt) {
    const b = box(f); if (pt[0] < b[0] || pt[0] > b[2] || pt[1] < b[1] || pt[1] > b[3]) return false;
    const polys = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
    return polys.some(poly => imRing(pt, poly[0]) && !poly.slice(1).some(h => imRing(pt, h)));
  }

  /* ----- Kartendaten ----- */
  const alt = w => w.datum && tage(w.datum) > 5 * 365 ? 1 : 0;
  const einheitenMitGrenzen = w => (w.einheiten || []).filter(u => u.geo);
  function kartenDaten() {
    const g = [], u1 = [], u2 = [], gp = [], p1 = [], p2 = [];
    for (const w of wahlenEbene()) {
      const ue = einheitenMitGrenzen(w), b = bewerten(w), name = w.geo === "laender" ? G.landName(w.gebiet) : w.name;
      flaechen(w.geo, w.gebiet).forEach((f, i) => {
        g.push({ type: "Feature", geometry: f.geometry, properties: { w: w.id, u: -1, k: w.gebiet, farbe: b.farbe, deck: b.deck * (alt(w) ? .6 : 1), fein: ue.length ? 1 : 0, summe: w.g && w.g.summe ? 1 : 0 } });
        if (i === 0) gp.push({ type: "Feature", geometry: { type: "Point", coordinates: mittelpunkt(f) }, properties: { fein: ue.length ? 1 : 0, t: latin1(name), top: b.txt, r: w.g && w.g.wb ? w.g.wb : 0 } });
      });
      ue.forEach(u => { if (u.nach && !u.geladen) werteNachladen(u); });
      ue.slice(0, 2).forEach((u, ui) => {
        const ziel = ui === 0 ? u1 : u2, pz = ui === 0 ? p1 : p2, fein = ui === 0 && ue[1] ? 1 : 0;
        for (const [k, wert] of Object.entries(u.werte)) {
          const bb = bewerten(w, wert), fs = flaechen(u.geo, k);
          fs.forEach((f, i) => {
            ziel.push({ type: "Feature", geometry: f.geometry, properties: { w: w.id, u: (w.einheiten || []).indexOf(u), k, farbe: bb.farbe, deck: bb.deck, fein, art: u.art } });
            if (i === 0) pz.push({ type: "Feature", geometry: { type: "Point", coordinates: mittelpunkt(f) }, properties: { fein, t: latin1(wert.n || k), top: bb.txt, r: wert.wb || 0 } });
          });
        }
      });
    }
    return { g, u1, u2, gp, p1, p2 };
  }
  // Gebiete ohne Wahl auf dieser Ebene: schraffiert, nie mit Daten einer anderen Ebene gefüllt
  function leerDaten() {
    const l = wahlenEbene(), laender = new Set(l.map(w => w.land)), gebiete = new Set(l.map(w => w.gebiet)), out = [];
    const roh = geo().roh, add = (f, k, name) => out.push({ type: "Feature", geometry: f.geometry, properties: { k, name } });
    if (roh.LAENDER) roh.LAENDER.features.forEach(f => { const iso = f.properties.iso; if (!laender.has(iso)) add(f, iso, f.properties.name); });
    if (W.e === 2) {
      if (roh.GL_GEO) roh.GL_GEO.features.forEach(f => { if (f.properties.iso !== "DE" && laender.has(f.properties.iso) && !gebiete.has(f.properties.code)) add(f, f.properties.code, f.properties.name); });
    }
    if (W.e >= 3) {
      if (roh.DE_GEO && laender.has("DE")) roh.DE_GEO.features.forEach(f => { if (!l.some(w => w.region === f.properties.code)) add(f, f.properties.code, f.properties.name); });
      if (roh.KO_GEO) roh.KO_GEO.features.forEach(f => { const eb = f.properties.ebene; if ((W.e === 3 ? eb !== "gem" : eb !== "kreis") && !gebiete.has(f.properties.id)) add(f, f.properties.id, f.properties.name); });
    }
    return { type: "FeatureCollection", features: out };
  }
  const fc = features => ({ type: "FeatureCollection", features });
  function auswahlFlaechen() {
    const w = W.fokus && NACH_ID[W.fokus]; if (!w) return fc([]);
    if (W.sel) { const u = w.einheiten[W.sel.u]; return fc(flaechen(u && u.geo, W.sel.k).map(f => ({ type: "Feature", geometry: f.geometry, properties: {} }))); }
    return fc(flaechen(w.geo, w.gebiet).map(f => ({ type: "Feature", geometry: f.geometry, properties: {} })));
  }

  /* ----- Zoom und Einheit ----- */
  const tiefeAuto = () => { const m = karte(); const z = m ? m.getZoom() : 0; return z < (Z1[0] + Z1[1]) / 2 ? 0 : z < (Z2[0] + Z2[1]) / 2 ? 1 : 2; };
  const tiefe = () => W.fest != null ? W.fest : tiefeAuto();
  const op = ["*", OP, ["get", "deck"]], fein = ["==", ["get", "fein"], 1];
  function deck(schicht, wert = op) {
    const f = W.fest, mit = x => JSON.parse(JSON.stringify(x).replace(/"__OP__"/g, JSON.stringify(wert)));
    const O = "__OP__";
    let x;
    if (f != null) {
      if (schicht === "g") x = f === 0 ? O : ["case", fein, 0, O];
      else if (schicht === "u1") x = f === 1 ? O : f === 2 ? ["case", fein, 0, O] : 0;
      else x = f === 2 ? O : 0;
    } else if (schicht === "g") x = ["interpolate", ["linear"], ["zoom"], Z1[0], O, Z1[1], ["case", fein, 0, O]];
    else if (schicht === "u1") x = ["interpolate", ["linear"], ["zoom"], Z1[0], 0, Z1[1], O, Z2[0], O, Z2[1], ["case", fein, 0, O]];
    else x = ["interpolate", ["linear"], ["zoom"], Z2[0], 0, Z2[1], O];
    return mit(x);
  }
  // Einheit, die für eine Wahl bei Tiefe t sichtbar ist: -1 = Gesamt, sonst Index in w.einheiten
  function einheitBei(w, t = tiefe()) { const ue = einheitenMitGrenzen(w); if (!t || !ue.length) return -1; return w.einheiten.indexOf(ue[Math.min(t, ue.length) - 1]); }
  function einheitText(w, t = tiefe()) {
    const i = einheitBei(w, t);
    if (i < 0) return w.einheiten && w.einheiten.some(u => !u.geo) ? `Gesamt (${w.einheiten.find(u => !u.geo).name} in der Seitenleiste)` : "Gesamtergebnis";
    const u = w.einheiten[i]; return `je ${u.einzahl} (${f0.format(u.anzahl || Object.keys(u.werte).length)})${u.art === "zaehlgebiet" ? ", Zählgebiet" : ""}`;
  }

  /* ----- Ebene auf der Karte ----- */
  let schraffurDa = false;
  function schraffur(m) {
    if (m.hasImage("wa-schraffur")) return;
    const n = 8, data = new Uint8Array(n * n * 4);
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) { const an = (x + y) % n < 2, i = (y * n + x) * 4; data[i] = 74; data[i + 1] = 86; data[i + 2] = 101; data[i + 3] = an ? 200 : 0; }
    m.addImage("wa-schraffur", { width: n, height: n, data }); schraffurDa = true;
  }
  const LINIE = "#07090c";
  G.ebene({ id: "wahlen", name: "Wahlergebnisse (eine Wahl je Ebene)", gruppe: "Politik & Wahlen", an: !!D || D_NACH, geplant: !D && !D_NACH, formen: ["politik"], ansicht: "wahlen",
    quellen: m => { const d = kartenDaten(); ["g", "u1", "u2", "gp", "p1", "p2"].forEach(k => m.addSource("wa-" + k, { type: "geojson", data: fc(d[k]) }));
      m.addSource("wa-leer", { type: "geojson", data: leerDaten() }); m.addSource("wa-sel", { type: "geojson", data: auswahlFlaechen() }); },
    schichten: (m, vor) => {
      schraffur(m);
      const s = (def, unter = true) => m.addLayer({ ...def, metadata: { ebene: "wahlen" } }, unter ? vor : undefined);
      s({ id: "wa-leer", type: "fill", source: "wa-leer", paint: { "fill-pattern": "wa-schraffur", "fill-opacity": .55 } });
      s({ id: "wa-g-f", type: "fill", source: "wa-g", paint: { "fill-color": ["get", "farbe"], "fill-opacity": deck("g") } });
      s({ id: "wa-g-l", type: "line", source: "wa-g", paint: { "line-color": LINIE, "line-width": .8, "line-opacity": deck("g", .9) } });
      s({ id: "wa-g-ls", type: "line", source: "wa-g", filter: ["==", ["get", "summe"], 1], paint: { "line-color": "#c3cad3", "line-width": 1, "line-dasharray": [2, 2], "line-opacity": deck("g", .8) } });
      ["u1", "u2"].forEach(k => {
        s({ id: `wa-${k}-f`, type: "fill", source: "wa-" + k, paint: { "fill-color": ["get", "farbe"], "fill-opacity": deck(k) } });
        s({ id: `wa-${k}-l`, type: "line", source: "wa-" + k, filter: ["!=", ["get", "art"], "zaehlgebiet"], paint: { "line-color": LINIE, "line-width": k === "u1" ? 1.1 : .7, "line-opacity": deck(k, .95) } });
        s({ id: `wa-${k}-ld`, type: "line", source: "wa-" + k, filter: ["==", ["get", "art"], "zaehlgebiet"], paint: { "line-color": "#c3cad3", "line-width": .8, "line-dasharray": [2.5, 2], "line-opacity": deck(k, .75) } });
      });
      s({ id: "wa-sel", type: "line", source: "wa-sel", paint: { "line-color": "#ffa828", "line-width": 2.6 } });
      const t = (id, src, minz, schicht) => s({ id, type: "symbol", source: src, minzoom: minz, layout: {
        "text-field": ["format", ["get", "t"], { "font-scale": 1 }, "\n", {}, ["get", "top"], { "text-color": "#c3cad3", "font-scale": .86 }],
        "text-font": ["Noto Sans Regular"], "text-size": 10.5, "text-line-height": 1.15, "text-padding": 3, "text-max-width": 9, "symbol-sort-key": ["-", 0, ["get", "r"]] },
        paint: { "text-color": "#e8ecf1", "text-halo-color": "#07090c", "text-halo-width": 1.3, "text-opacity": deck(schicht, ["case", ["==", ["get", "t"], ""], 0, 1]) } }, false);
      t("wa-gp-t", "wa-gp", 2.2, "g"); t("wa-p1-t", "wa-p1", 4.3, "u1"); t("wa-p2-t", "wa-p2", 6.6, "u2");
    },
    klick: (e, m) => {
      if (!aktiv()) return false;
      const f = treffer(e.point, m);
      W.ort = [e.lngLat.lng, e.lngLat.lat];
      if (!f) return false;
      if (f.layer.id === "wa-leer") { W.fokus = null; W.sel = null; W.leer = f.properties.k; const iso = String(f.properties.k).slice(0, 2).toUpperCase(); anwenden(); if (/^[A-Z]{2}$/.test(iso) && G.zustand().land !== iso) G.landWaehlen(iso); return true; }
      const p = f.properties, w = NACH_ID[p.w]; W.leer = null;
      if (p.u === -1) { if (W.fokus === p.w && !W.sel) W.fokus = null; else { W.fokus = p.w; W.sel = null; } }
      else if (W.fokus === p.w && W.sel && W.sel.u === p.u && W.sel.k === p.k) W.sel = null;
      else { W.fokus = p.w; W.sel = { u: p.u, k: p.k }; }
      if (W.fokus && w.land !== G.zustand().land) G.landWaehlen(w.land);
      anwenden();
      // Klick auf ein Land in der Weltansicht: hinfliegen, damit die Untergliederung erscheint
      if (W.fokus && p.u === -1 && m.getZoom() < Z1[0] && einheitenMitGrenzen(w).length) zeigen(w.geo, w.gebiet, Z2[0] - .3);
      return true;
    } });
  // sichtbares Gebiet unter dem Mauszeiger (berücksichtigt Zoom-Überblendung und festgehaltene Einheit)
  function treffer(pt, m) {
    const ids = ["wa-u2-f", "wa-u1-f", "wa-g-f", "wa-leer"].filter(i => m.getLayer(i)); if (!ids.length) return null;
    const t = tiefe(), sicht = f => { if (f.layer.id === "wa-leer") return true; const u = f.layer.id === "wa-g-f" ? 0 : f.layer.id === "wa-u1-f" ? 1 : 2, fe = f.properties.fein === 1; return u === 0 ? (t === 0 || !fe) : u === 1 ? (t >= 1 && (t === 1 || !fe)) : t >= 2; };
    return m.queryRenderedFeatures(pt, { layers: ids }).find(sicht) || null;
  }
  function zeigen(art, k, maxZoom = 9) {
    const m = karte(), fs = flaechen(art, k); if (!m || !fs.length) return;
    const f = fs.reduce((a, b) => (box(b)[2] - box(b)[0]) * (box(b)[3] - box(b)[1]) > (box(a)[2] - box(a)[0]) * (box(a)[3] - box(a)[1]) ? b : a), b = art === "laender" ? G.bbox(f) : box(f);
    if (b[2] - b[0] > 170) { m.flyTo({ center: mittelpunkt(f), zoom: 3, duration: 1200 }); return; }
    m.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: { top: 150, bottom: 60, left: 170, right: 40 }, maxZoom, duration: 1100 });
  }

  /* ----- Tooltip ----- */
  let tip = null;
  const tipWeg = () => { if (tip) { tip.remove(); tip = null; } };
  function tooltipText(f) {
    if (f.layer.id === "wa-leer") return `<span class="pct">E${W.e} · ${esc(ebeneName(W.e, String(f.properties.k).slice(0, 2)))}</span><br><b>${esc(f.properties.name || f.properties.k)}</b><br>keine Daten auf dieser Ebene`;
    const p = f.properties, w = NACH_ID[p.w]; if (!w) return "";
    const u = p.u >= 0 ? w.einheiten[p.u] : null, wert = u ? u.werte[p.k] : null, a = anteile(w, wert), top = a.l[0], zweit = a.l[1], b = beteiligung(w, wert);
    const name = u ? wert.n : w.geo === "laender" ? G.landName(w.gebiet) : w.name;
    return `<span class="pct">E${w.e} · ${esc(ebeneName(w.e, w.land).toUpperCase())} · ${esc(w.titel)} ${esc(datum(w.datum))}</span><br><b>${esc(name)}</b>${u ? ` <span class="pct">${esc(u.einzahl)}${u.art === "zaehlgebiet" ? ", Zählgebiet" : ""}</span>` : ""}
      <br>${top ? `${esc(kurzName(top[0]))} ${pct(top[2])}${zweit ? ` vor ${esc(kurzName(zweit[0]))} ${pct(zweit[2])}` : ""}` : "kein Ergebnis"}${a.sitze ? " <span class=\"pct\">(nach Sitzen)</span>" : ""}
      ${W.faerbung === "anteil" && W.partei ? `<br>${esc(kurzName(W.partei))}: ${pct((a.l.find(x => x[0] === W.partei) || [])[2])}` : ""}${b != null ? `<br><span class="pct">Wahlbeteiligung ${pct(b)} · ${esc(stimmartName(w))}</span>` : `<br><span class="pct">${esc(stimmartName(w))}</span>`}`;
  }
  let gebunden = false;
  function binden() {
    const m = karte(); if (!m || gebunden) return; gebunden = true;
    m.on("mousemove", e => {
      if (!aktiv()) { if (tip) { tip.remove(); tip = null; } return; }
      const f = treffer(e.point, m);
      if (!f) { if (tip) { tip.remove(); tip = null; } return; }
      m.getCanvas().style.cursor = "pointer";
      if (!tip) tip = new maplibregl.Popup({ closeButton: false, closeOnClick: false, className: "gk-pop", offset: 12, maxWidth: "320px" });
      tip.setLngLat(e.lngLat).setHTML(tooltipText(f)).addTo(m);
    });
    m.getCanvas().addEventListener("mouseleave", () => { if (tip) { tip.remove(); tip = null; } });
    let letzte = tiefe();
    m.on("zoom", () => { if (!aktiv()) return; const t = tiefe(); if (t !== letzte) { letzte = t; satz(); G.legendeKarte(); if (W.fokus) G.seiteZeichnen(); } });
  }

  /* ----- Anwenden ----- */
  function kartenAnwenden() {
    const m = karte(); if (!m || !m.getSource("wa-g")) return;
    const d = kartenDaten();
    ["g", "u1", "u2", "gp", "p1", "p2"].forEach(k => m.getSource("wa-" + k).setData(fc(d[k])));
    m.getSource("wa-leer").setData(leerDaten()); m.getSource("wa-sel").setData(auswahlFlaechen());
    ["g", "u1", "u2"].forEach(k => { m.setPaintProperty(`wa-${k}-f`, "fill-opacity", deck(k)); });
    m.setPaintProperty("wa-g-l", "line-opacity", deck("g", .9)); m.setPaintProperty("wa-g-ls", "line-opacity", deck("g", .8));
    ["u1", "u2"].forEach(k => { m.setPaintProperty(`wa-${k}-l`, "line-opacity", deck(k, .95)); m.setPaintProperty(`wa-${k}-ld`, "line-opacity", deck(k, .75)); });
    [["wa-gp-t", "g"], ["wa-p1-t", "u1"], ["wa-p2-t", "u2"]].forEach(([id, k]) => m.setPaintProperty(id, "text-opacity", deck(k, ["case", ["==", ["get", "t"], ""], 0, 1])));
  }
  function anwenden() { tipWeg(); merken(); binden(); kartenAnwenden(); bedienung(); G.legendeKarte(); G.seiteZeichnen(); }
  // Ebenenwechsel: Leiste, Legende und Seitenleiste sofort, die Flächen blenden kurz aus und mit der neuen Ebene wieder ein
  // (kartenAnwenden setzt die Deckkraft zurück, MapLibre überblendet dabei mit seiner Standardübergangszeit)
  let blendTimer = 0;
  function umblenden() {
    const m = karte();
    if (!m || !m.getLayer("wa-g-f") || !aktiv()) { anwenden(); return; }
    tipWeg(); merken(); bedienung(); G.legendeKarte(); G.seiteZeichnen();
    const T = { duration: 220, delay: 0 };
    [["wa-g-f", "fill"], ["wa-u1-f", "fill"], ["wa-u2-f", "fill"], ["wa-leer", "fill"], ["wa-g-l", "line"], ["wa-g-ls", "line"], ["wa-u1-l", "line"], ["wa-u1-ld", "line"], ["wa-u2-l", "line"], ["wa-u2-ld", "line"], ["wa-gp-t", "text"], ["wa-p1-t", "text"], ["wa-p2-t", "text"]]
      .forEach(([id, a]) => { if (!m.getLayer(id)) return; m.setPaintProperty(id, `${a}-opacity-transition`, T); m.setPaintProperty(id, `${a}-opacity`, 0); });
    clearTimeout(blendTimer);
    blendTimer = setTimeout(() => { kartenAnwenden(); if (m.getLayer("wa-leer")) m.setPaintProperty("wa-leer", "fill-opacity", .55); }, 240);
  }

  /* ----- Satzleiste und Ebenenleiter ----- */
  function elemente() {
    const host = document.getElementById("gk-karte"); if (!host) return {};
    let s = document.getElementById("wa-satz"), l = document.getElementById("wa-leiter");
    if (!s) { s = document.createElement("div"); s.id = "wa-satz"; s.className = "wa-satz"; s.setAttribute("role", "group"); s.setAttribute("aria-label", "Was die Karte zeigt"); host.appendChild(s); }
    if (!l) { l = document.createElement("nav"); l.id = "wa-leiter"; l.className = "wa-leiter"; l.setAttribute("aria-label", "Politische Ebene"); host.appendChild(l); }
    return { s, l };
  }
  const opt = (v, t, an) => `<option value="${esc(v)}"${an ? " selected" : ""}>${esc(t)}</option>`;
  function satz() {
    const { s } = elemente(); if (!s) return;
    s.hidden = !aktiv() || !D; if (s.hidden) return;
    const w = W.fokus && NACH_ID[W.fokus], l = wahlenEbene(), land = bezugsland();
    const teile = [marke(W.e, land)];
    // Mehrere Bundeswahlen im selben Land (z. B. USA: Repräsentantenhaus, Senat, Präsident): eigene Schaltflächen
    const km = W.e === 1 && land ? kammernVon(land) : [];
    if (km.length > 1) teile.push(`<span class="wa-kammern" role="group" aria-label="Bundeswahl">${km.map(([k, x]) => `<button type="button" data-wa-kammer="${k}" aria-pressed="${W.kammer === k}">${esc(x.gremium || k)}</button>`).join("")}</span>`);
    // Wahl: im Fokus die Wahl selbst (andere Wahlen derselben Ebene und desselben Landes wählbar), sonst die Gruppe
    if (w) {
      const andere = ALLE.filter(x => x.e === w.e && x.land === w.land && (w.e === 1 ? kammerVon(x) === kammerVon(w) : x.gebiet === w.gebiet));
      teile.push(`<select data-wa="wahl" aria-label="Wahl">${opt("", `${gruppenName()} (alle)`, false)}${andere.map(x => opt(x.id, `${x.titel} ${datum(x.datum)}${x.e === 1 ? " · " + x.gremium : ""}`, x.id === w.id)).join("")}</select>`);
      teile.push(`<span class="wa-fix">${esc(w.geo === "laender" ? G.landName(w.gebiet) : w.name)}</span>`);
    } else {
      const jahre = l.map(x => (x.datum || "").slice(0, 4)).filter(Boolean).sort(), sp = jahre.length ? (jahre[0] === jahre.at(-1) ? jahre[0] : `${jahre[0]}–${jahre.at(-1)}`) : "";
      if (W.e !== 1) teile.push(`<span>${esc(gruppenName())}</span>`);
      else if (km.length < 2) teile.push(`<select data-wa="kammer" aria-label="Gremium">${KAMMERN.map(([k, t]) => opt(k, k === "oberhaus" ? "Nationale Oberhäuser (direkt gewählt)" : k === "praesident" ? "Präsidentschaftswahlen (direkt gewählt)" : "Nationale Parlamente (Unterhaus/Einkammer)", W.kammer === k)).join("")}</select>`);
      teile.push(`<span class="wa-fix">${l.length > 1 ? `jeweils letzte Wahl${sp ? ", " + sp : ""}` : sp}</span>`);
    }
    if (w && (w.stimmarten || []).length > 1) teile.push(`<span class="wa-teil"><span class="wa-trenn">·</span> <select data-wa="stimmart" aria-label="Stimmart">${w.stimmarten.map(([k, t]) => opt(k, t, stimmart(w) === k)).join("")}</select></span>`);
    // Einheit: automatisch nach Zoom oder festgehalten
    const bsp = w || l.find(x => einheitenMitGrenzen(x).length) || l[0];
    const tname = t => { if (!bsp) return t ? "Untergliederung" : "Gesamt"; const i = einheitBei(bsp, t); return i < 0 ? "Gesamtergebnis je Gebiet" : `je ${bsp.einheiten[i].einzahl}${w ? ` (${f0.format(bsp.einheiten[i].anzahl || Object.keys(bsp.einheiten[i].werte).length)})` : ""}`; };
    const tiefen = [0, 1, 2].filter(t => t === 0 || (bsp && einheitenMitGrenzen(bsp).length >= t));
    teile.push(`<span class="wa-teil"><span class="wa-trenn">·</span> <select data-wa="einheit" aria-label="Auszählungseinheit">${opt("auto", `${w ? einheitText(w) : tname(tiefe())} · automatisch nach Zoom`, W.fest == null)}${tiefen.map(t => opt(String(t), `${tname(t)} · festgehalten`, W.fest === t)).join("")}</select></span>`);
    // Färbung
    const parteien = w ? anteile(w).l.filter(x => x[2] >= 1).slice(0, 14).map(x => x[0]) : [];
    teile.push(`<span class="wa-teil"><span class="wa-trenn">·</span> <select data-wa="faerbung" aria-label="Färbung">${[["sieger", "gefärbt nach stärkster Partei"], ["vorsprung", "gefärbt nach Vorsprung"], ["beteiligung", "gefärbt nach Wahlbeteiligung"], ...(w ? [["anteil", "gefärbt nach Anteil einer Partei"]] : [])].map(([k, t]) => opt(k, t, W.faerbung === k)).join("")}</select></span>`);
    if (W.faerbung === "anteil" && w) teile.push(`<select data-wa="partei" aria-label="Partei">${parteien.map(p => opt(p, kurzName(p), W.partei === p)).join("")}</select>`);
    s.innerHTML = teile.join(" ");
  }
  function leiter() {
    const { l } = elemente(); if (!l) return;
    l.hidden = !aktiv() || !D; if (l.hidden) return;
    const land = bezugsland(), namen = ebenenNamen(land);
    const zahl = e => ALLE.filter(w => w.e === e && (!land || w.land === land) && (e !== 1 || passtKammer(w))).length;
    l.innerHTML = `<h4>Ebene${land ? " · " + esc(land) : ""}</h4>` + [0, 1, 2, 3, 4].filter(e => namen[e] !== null).map(e => { const n = zahl(e);
      return `<button type="button" data-wa-ebene="${e}" aria-pressed="${W.e === e}" class="${n ? "" : "ohne"}" title="${esc(`E${e} ${ebeneName(e, land)}: ${n ? f0.format(n) + " Wahlen mit Daten" : "Wahlen gibt es, Daten fehlen noch"}`)}"><b>E${e}</b><span>${esc(namen[e] || ebeneName(e, null))}</span><small>${n || "–"}</small></button>`; }).join("");
  }
  // Leiter sitzt direkt unter der Satzleiste (die je nach Wahl ein- oder zweizeilig ist), damit sie nie die Legende unten links verdeckt
  function bedienung() {
    satz(); leiter();
    const { s, l } = elemente(); if (!s || !l) return;
    if (s.hidden || window.matchMedia("(max-width: 820px)").matches) { l.style.top = ""; return; }
    l.style.top = (s.offsetTop + s.offsetHeight + 10) + "px";
  }

  /* ----- Seitenleiste ----- */
  function balken(w, l, max) {
    return l.map(([p, , x, vor]) => `<div class="wa-balken"><span title="${esc(parteiName(w, p))}">${esc(parteiName(w, p))}</span><i style="width:${(x / max * 100).toFixed(1)}%;background:${esc(farbe(w, p))}"></i><b>${f1.format(x)}</b><em>${vor != null ? pp(x - vor) : ""}</em></div>`).join("");
  }
  function sitzeOrdnen(w, sitze) {
    const o = (D.ordnung || {})[w.land]; if (!o) return [...sitze].sort((a, b) => b[1] - a[1]);
    const r = p => { const i = o.indexOf(/^Wählergruppe/.test(p) ? "Wählergruppen" : p); return i < 0 ? 11.5 : i; };
    return [...sitze].sort((a, b) => r(a[0]) - r(b[0]));
  }
  function ergebnis(w, wert, u) {
    const a = anteile(w, wert), x = wert || w.g || {}, sitze = wert ? wert.sitze : (w.g || {}).sitze, n = wert ? wert.sitze_n : (w.g || {}).sitze_n;
    const teile = [];
    const amt = !wert && w.g && w.g.amt;
    if (amt) teile.push(`<div class="wa-amt">Gewählt: <b>${esc(amt.amt)} ${esc(amt.name)}</b> (${esc(amt.partei)}), ${pct(amt.anteil)} · ${esc(amt.wahl)}</div>`);
    // Stadt mit mehreren Wahlkreisen, für die es keine offenen Stadtteilgrenzen gibt (landtagswahlen.py: wk_staedte): Ergebnis der ganzen Stadt
    if (wert && wert.stadt) teile.push(`<div class="wa-amt">Ergebnis der ganzen Stadt. Sie ist auf die Wahlkreise ${esc((wert.teil || []).join(", "))} verteilt; deren Grenzen innerhalb der Stadt sind nicht als offene Geodaten verfügbar, die Direktmandate stehen bei den Wahlkreisen.</div>`);
    else if (u && u.art === "wahlkreis" && w.id === "DE-BT-2025" && wert && wert.s && wert.s.e) {
      const e = [...wert.s.e].sort((p, q) => q[2] - p[2]), v = e[0][2] - (e[1] ? e[1][2] : 0);
      teile.push(`<div class="wa-amt">Erststimmen vorn: <b>${esc(e[0][0])}</b> mit ${pct(e[0][2])}, ${f1.format(v)} Punkte vor ${esc(e[1] ? e[1][0] : "–")}. <span class="pct">Ob der Sieger ein Mandat erhielt (Zweitstimmendeckung), steht noch nicht in den Daten.</span></div>`);
    }
    // Wahlkreis mit Direktmandat (relative Mehrheit der Erststimmen, z. B. Landtag NRW): gewählte Person, wenn die Quelle sie nennt
    // (Erststimmen, wo es zwei Stimmen gibt; bei reiner Mehrheitswahl wie im britischen Unterhaus die einzige Stimme)
    else if (u && u.art === "wahlkreis" && wert && wert.s && (wert.s.e || wert.direkt)) {
      const st = wert.s.e ? "e" : Object.keys(wert.s)[0], l = wert.s[st] || [];
      const e = [...l].sort((p, q) => q[2] - p[2]), v = e.length ? e[0][2] - (e[1] ? e[1][2] : 0) : null, d = wert.direkt;
      if (e.length || d) teile.push(`<div class="wa-amt">${st === "e" ? "Direktmandat" : "Gewählt"}: <b>${d ? `${esc(d.name)} (${esc(d.partei)})` : esc(e[0][0])}</b>${wert.runde ? ` im ${wert.runde}. Wahlgang` : ""}${e.length ? ` mit ${pct(e[0][2])}${st === "e" ? " der Erststimmen" : st === "zk" ? " nach Präferenzen" : ""}${e[1] ? `, ${f1.format(v)} Punkte vor ${esc(e[1][0])}` : " (ohne Gegenkandidat)"}` : ""}.</div>`);
    }
    if (sitze && sitze.length) {
      const so = sitzeOrdnen(w, sitze.filter(s => s[1] > 0));
      const summe = so.reduce((s, y) => s + y[1], 0), gr = [...so].sort((p, q) => q[1] - p[1])[0];
      teile.push(`<div class="gk-block"><h3>Sitzverteilung${n ? ` · ${f0.format(n)} Sitze` : ""}</h3>${G.halbkreis(so.map(y => [kurzName(y[0]), y[1], farbe(w, y[0])]), false)}
        <p class="gk-quelle" style="margin-top:4px">Mehrheit ab ${f0.format(Math.floor((n || summe) / 2) + 1)} Sitzen; stärkste Kraft ${esc(kurzName(gr[0]))} mit ${f0.format(gr[1])}.${so.some(y => y[2] != null) ? " Veränderung: " + so.filter(y => y[2] != null && y[1] !== y[2]).map(y => `${esc(kurzName(y[0]))} ${pp(y[1] - y[2]).replace(",0", "")}`).join(", ") + "." : ""}${!wert && w.g.sitze_hinweis ? " " + esc(w.g.sitze_hinweis) + "." : ""}</p></div>`);
    }
    if (a.l.length) {
      const l = a.l.filter(y => y[2] >= 1).slice(0, 10), rest = a.l.length - l.length, vor = a.l.some(y => y[3] != null);
      teile.push(`<div class="gk-block"><h3>${a.sitze ? "Anteil an den Sitzen" : esc(stimmartName(w))}, in %${vor ? ` <span class="pct" style="text-transform:none">· Veränderung zu ${esc((w.vor && w.vor.titel) || "Vorwahl")}</span>` : ""}</h3>
        ${(w.stimmarten || []).length > 1 ? `<div class="gk-chips" style="margin-bottom:6px">${w.stimmarten.map(([k, t]) => `<button type="button" data-wa-stimmart="${esc(k)}" aria-pressed="${stimmart(w) === k}">${esc(t)}</button>`).join("")}</div>` : ""}
        ${balken(w, l, Math.max(...l.map(y => y[2]), 1))}${rest > 0 ? `<p class="gk-quelle">${rest} weitere unter 1 %${a.l.length > 10 ? " bzw. nicht aufgeführt" : ""}</p>` : ""}</div>`);
    }
    const b = beteiligung(w, wert), zeilen = [];
    if (b != null) zeilen.push(`<tr><td>Wahlbeteiligung</td><td>${pct(b)}${!wert && w.g.bet_vor != null ? ` <span class="pct">(vorher ${pct(w.g.bet_vor)})</span>` : ""}</td></tr>`);
    if (x.wb) zeilen.push(`<tr><td>Wahlberechtigte</td><td>${f0.format(x.wb)}</td></tr>`);
    if (x.w) zeilen.push(`<tr><td>Wählende</td><td>${f0.format(x.w)}</td></tr>`);
    if (a.l[1]) zeilen.push(`<tr><td>Vorsprung der stärksten Partei</td><td>${f1.format(a.l[0][2] - a.l[1][2])} Pkt.</td></tr>`);
    if (zeilen.length) teile.push(`<div class="gk-block"><h3>Kennzahlen</h3><table class="gk-tab"><tbody>${zeilen.join("")}</tbody></table></div>`);
    return teile.join("");
  }
  function pfad(w, u, wert) {
    const p = [`<button type="button" data-wa-pfad="ebene">${esc(gruppenName(w.e))}</button>`];
    const gname = w.geo === "laender" ? G.landName(w.gebiet) : w.name;
    p.push(wert ? `<button type="button" data-wa-pfad="wahl">${esc(gname)}</button>` : `<span class="jetzt">${esc(gname)}</span>`);
    if (wert && wert.l && w.einheiten[0] && w.einheiten[0].werte[wert.l] && w.einheiten[0] !== u) p.push(`<button type="button" data-wa-einheit="0:${esc(wert.l)}">${esc(w.einheiten[0].werte[wert.l].n)}</button>`);
    if (wert) p.push(`<span class="jetzt">${esc(wert.n)}</span>`);
    return `<nav class="wa-pfad" aria-label="Pfad">${p.join("<span>›</span>")}</nav>`;
  }
  function kopf(w, u, wert) {
    const t = tage(w.datum), neu = t >= 0 && t <= 30;
    return `<div class="wa-kopf"><div class="wa-zeile">${marke(w.e, w.land)}<span class="wa-status${neu || w.status === "vorläufig" ? " neu" : ""}">${neu ? `gerade gewählt, vor ${t} Tagen · ` : ""}${esc(w.status || "Stand der Quelle")}</span></div>${pfad(w, u, wert)}
      <h2>${esc(w.titel)} ${esc(datum(w.datum))}</h2><p class="unter">${esc(w.gremium)}${u ? ` · ${esc(u.einzahl)}${u.art === "zaehlgebiet" ? " (Zählgebiet, hier wird kein Mandat vergeben)" : ""}` : ""}</p></div>`;
  }
  // Liste der Einheiten (Wahlkreise, Länder, Kreise …) bzw. der Wahlen einer Ebene; sortier- und filterbar
  function zeilenWerte(w, wert) { const a = anteile(w, wert), t = a.l[0], z = a.l[1]; return { p: t ? t[0] : "", x: t ? t[2] : null, v: t ? t[2] - (z ? z[2] : 0) : null, b: beteiligung(w, wert) }; }
  function tabelle(zeilen, erste) {
    const sp = [["name", erste], ["rang", "stärkste"], ["x", "%"], ["v", "Vorspr."], ["b", "Beteil."]];
    const q = W.filter.trim().toLowerCase(), f = q ? zeilen.filter(z => z.n.toLowerCase().includes(q)) : zeilen;
    const s = W.sort, sortiert = [...f].sort((a, b) => s === "name" ? a.n.localeCompare(b.n, "de", { numeric: true }) : s === "rang" ? a.p.localeCompare(b.p, "de") || (b.x ?? 0) - (a.x ?? 0) : (b[s] ?? -1) - (a[s] ?? -1));
    return `<input class="wa-filter" type="search" data-wa-filter placeholder="${esc(erste)} suchen" value="${esc(W.filter)}" aria-label="${esc(erste)} suchen">
      <table class="wa-tab"><thead><tr>${sp.map(([k, t]) => `<th><button type="button" data-wa-sort="${k}" aria-pressed="${W.sort === k}">${esc(t)}</button></th>`).join("")}</tr></thead><tbody>
      ${sortiert.slice(0, 450).map(z => `<tr class="${z.sel ? "sel" : ""}"><td><button type="button" ${z.attr}>${esc(z.n)}</button>${z.neu ? ` <span class="wa-status neu">neu</span>` : ""}</td><td style="text-align:left"><span class="p" style="background:${esc(z.f)}"></span>${esc(kurzName(z.p)).slice(0, 18)}</td><td>${z.x != null ? f1.format(z.x) : "–"}</td><td>${z.v != null ? f1.format(z.v) : "–"}</td><td>${z.b != null ? f1.format(z.b) : "–"}</td></tr>`).join("")}</tbody></table>
      ${sortiert.length > 450 ? `<p class="gk-quelle">die ersten 450 von ${f0.format(sortiert.length)}</p>` : ""}`;
  }
  function einheitenListe(w) {
    const t = Math.max(1, tiefe()), i = einheitBei(w, t), ohneGeo = (w.einheiten || []).findIndex(u => !u.geo), ui = i >= 0 ? i : ohneGeo;
    if (ui < 0) return "";
    const u = w.einheiten[ui];
    const zeilen = Object.entries(u.werte).map(([k, wert]) => { const z = zeilenWerte(w, wert); return { ...z, n: wert.n || k, f: farbe(w, z.p), attr: `data-wa-einheit="${ui}:${esc(k)}"`, sel: W.sel && W.sel.u === ui && W.sel.k === k }; });
    const andere = (w.einheiten || []).map((x, j) => [x, j]).filter(([x, j]) => j !== ui && x.geo);
    return `<div class="gk-block"><h3>${esc(u.name)} · ${f0.format(zeilen.length)}${u.art === "zaehlgebiet" ? " · Zählgebiete" : ""}</h3>
      ${andere.length ? `<div class="gk-chips" style="margin-bottom:6px">${andere.map(([x, j]) => `<button type="button" data-wa="einheit-wahl" data-wa-tiefe="${einheitenMitGrenzen(w).indexOf(x) + 1}">${esc(x.name)} zeigen</button>`).join("")}</div>` : ""}
      ${tabelle(zeilen, u.einzahl)}${u.quelle ? `<p class="gk-quelle" style="margin-top:6px">${esc(u.quelle)}</p>` : ""}</div>`;
  }
  // Ortsanker: Wahlen der anderen Ebenen am selben Ort
  function ortPunkt(w) {
    if (W.ort) return W.ort;
    const u = W.sel ? w.einheiten[W.sel.u] : null, fs = u ? flaechen(u.geo, W.sel.k) : flaechen(w.geo, w.gebiet);
    return fs.length ? mittelpunkt(fs[0]) : null;
  }
  function amOrt(pt, e) {
    if (!pt) return [];
    return ALLE.filter(x => x.e === e && flaechen(x.geo, x.gebiet).some(f => enthaelt(f, pt)));
  }
  function ortsanker(w) {
    const pt = ortPunkt(w); if (!pt) return "";
    const l = [0, 1, 2, 3, 4].filter(e => e !== w.e).flatMap(e => amOrt(pt, e).filter(x => e !== 1 || x.kammer !== "oberhaus").slice(0, 2));
    if (!l.length) return "";
    return `<div class="gk-block"><h3>Am selben Ort auf anderen Ebenen</h3><div class="wa-sprung">${l.map(x => `<button type="button" data-wa-sprung="${esc(x.id)}"><b>E${x.e} · ${esc(ebeneName(x.e, x.land))}</b><span>${esc(x.titel)} ${esc(datum(x.datum))} · ${esc(x.gremium)}</span></button>`).join("")}</div>
      <p class="gk-quelle" style="margin-top:6px">Der Wechsel behält den Ort: Die Karte zeigt dort die Einheit, in der derselbe Punkt liegt.</p></div>`;
  }
  function quelle(w) {
    const q = w.quelle || {};
    return `<div class="gk-block">${w.system ? `<p style="font-size:12px;margin-bottom:6px">${esc(w.system)}</p>` : ""}<p class="gk-quelle">${q.url ? `<a href="${esc(q.url)}" target="_blank" rel="noopener">${esc(q.name || "Quelle")}</a>` : esc(q.name || "")}${q.lizenz ? ", " + esc(q.lizenz) : ""}. Wahlregister Stand ${esc(D.stand)}.</p></div>`;
  }
  function wahlSeite(w) {
    const u = W.sel ? w.einheiten[W.sel.u] : null, wert = u ? u.werte[W.sel.k] : null;
    if (W.sel && !wert) { W.sel = null; return wahlSeite(w); }
    return kopf(w, u, wert) + ergebnis(w, wert, u) + (wert ? `<div class="gk-chips"><button type="button" data-wa-pfad="wahl">↑ Gesamtergebnis ${esc(w.geo === "laender" ? G.landName(w.gebiet) : w.name)}</button></div>` : "")
      + einheitenListe(w) + ortsanker(w) + quelle(w);
  }
  function ebenenSeite() {
    const land = G.zustand().land, l = wahlenEbene(), hier = land ? l.filter(w => w.land === land) : l;
    const n = ebenenNamen(land)[W.e];
    const kopfTxt = `<div class="wa-kopf"><div class="wa-zeile">${marke(W.e, land)}<span class="wa-status">${f0.format(hier.length)} Wahlen mit Daten${land ? " in " + esc(G.landName(land)) : " weltweit"}</span></div>
      <h2>${esc(gruppenName())}</h2><p class="unter">Jedes Gebiet zeigt seine jüngste Wahl auf dieser Ebene. Gebiet anklicken für das Ergebnis, hineinzoomen für die Untergliederung. Schraffiert: keine Daten auf dieser Ebene.</p></div>`;
    if (n === null) return kopfTxt + `<div class="gk-block"><p class="gk-leer">${esc(G.landName(land))} hat keine Wahlen auf der Ebene E${W.e}.</p></div>`;
    const leer = W.leer ? `<div class="gk-block"><p class="gk-leer">Für ${esc(String(W.leer).length === 2 ? G.landName(W.leer) : W.leer)} liegen auf der Ebene E${W.e} (${esc(ebeneName(W.e, String(W.leer).slice(0, 2)))}) noch keine Wahldaten vor.</p></div>` : "";
    const zeilen = hier.map(w => { const z = zeilenWerte(w); const t = tage(w.datum); return { ...z, n: `${w.geo === "laender" ? G.landName(w.gebiet) : w.name} · ${datum(w.datum)}`, f: farbe(w, z.p), attr: `data-wa-wahl="${esc(w.id)}"`, neu: t >= 0 && t <= 30 }; });
    const andereLaender = land && !hier.length ? `<p class="gk-leer">Für ${esc(G.landName(land))} gibt es auf dieser Ebene noch keine Daten.</p>` : "";
    return kopfTxt + leer + `<div class="gk-block"><h3>${esc(gruppenName())}${land ? " · " + esc(G.landName(land)) : ""}</h3>${andereLaender}${zeilen.length ? tabelle(zeilen, "Gebiet") : ""}
      ${land ? `<div class="gk-chips" style="margin-top:6px"><button type="button" data-gkland="">Alle Länder</button></div>` : ""}</div>
      <div class="gk-block"><p class="gk-quelle">Wahlregister (app/wahlen_daten.py), Stand ${esc(D.stand)}: ${f0.format(ALLE.length)} Wahlen. Quellen je Wahl in der Ergebniskarte. Nationale Ergebnisse: Wikipedia-Wahlartikel und IPU Parline; Deutschland: Die Bundeswahlleiterin, IT.NRW.</p></div>`;
  }
  function seite() {
    if (!D) { const st = BLOCK.status("wahlen-daten");
      return `<div><h2>Wahlen</h2><p class="gk-leer">${st.laedt ? "Wahlregister wird geladen …" : st.fehler ? `Wahlregister nicht geladen (${esc(st.fehler)}). <button type="button" data-wa-erneut>Erneut versuchen</button>` : "Kein Wahlregister im Build (app/wahlen_daten.py)."}</p></div>`; }
    const w = W.fokus && NACH_ID[W.fokus];
    return w ? wahlSeite(w) : ebenenSeite();
  }
  function legende() {
    const w = W.fokus && NACH_ID[W.fokus], l = w ? wahlenEbene().filter(x => x.land === w.land) : wahlenEbene(), t = tiefe();
    const titel = w ? `E${w.e} · ${w.titel} ${(w.datum || "").slice(0, 4)}` : `E${W.e} · ${gruppenName()}`;
    const was = W.faerbung === "beteiligung" ? "Wahlbeteiligung" : W.faerbung === "vorsprung" ? "stärkste Partei, kräftiger = größerer Vorsprung" : W.faerbung === "anteil" && W.partei ? `Anteil ${kurzName(W.partei)}, kräftiger = höher` : "stärkste Partei";
    const unter = w ? `${stimmartName(w)} · ${was} · ${einheitText(w, t)}${l.length > 1 ? ` · Zahlen: alle ${l.length} Wahlen dieser Ebene in ${G.landName(w.land)}` : ""}` : `${was} · ${t === 0 ? "je Gebiet" : "je Untergliederung, wo vorhanden"}`;
    const zaehl = {};
    if (W.faerbung === "sieger" || W.faerbung === "vorsprung") l.forEach(x => { const i = einheitBei(x, t); const werte = i >= 0 ? Object.values(x.einheiten[i].werte) : [null]; werte.forEach(v => { const a = anteile(x, v).l[0]; if (a) { const k = kurzName(a[0]); zaehl[k] = zaehl[k] || [0, farbe(x, a[0])]; zaehl[k][0]++; } }); });
    const sw = c => `<i class="wa-legende-flaeche" style="background:${esc(c)}"></i>`;
    const farben = W.faerbung === "beteiligung" ? BET.map(([g, c], i) => `<span>${sw(c)}${i === 0 ? `unter ${g} %` : i === BET.length - 1 ? `ab ${BET[i - 1][0]} %` : `${BET[i - 1][0]}–${g} %`}</span>`).join("")
      : Object.entries(zaehl).sort((a, b) => b[1][0] - a[1][0]).slice(0, 8).map(([k, [n, c]]) => `<span>${sw(c)}${esc(k)} <em style="color:var(--ink-3);font-style:normal">${f0.format(n)}</em></span>`).join("");
    const lin = (strich, farbe) => `<svg width="26" height="8" aria-hidden="true"><line x1="1" y1="4" x2="25" y2="4" stroke="${farbe}" stroke-width="1.6" ${strich ? `stroke-dasharray="${strich}"` : ""}/></svg>`;
    return `<b>${esc(titel)}</b><small>${esc(unter)}</small>${farben}
      <span>${lin("", "#c3cad3")}Wahlkreis (Mandat)</span><span>${lin("4 3", "#c3cad3")}nur Zählgebiet</span>
      <span><svg width="14" height="10" aria-hidden="true"><defs><pattern id="wa-sch" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="4" stroke="#4a5665" stroke-width="2"/></pattern></defs><rect width="14" height="10" fill="url(#wa-sch)"/></svg>keine Daten auf dieser Ebene</span>
      <span>${lin("", "#ffa828")}Auswahl</span>`;
  }

  /* ----- Bedienung ----- */
  function ebeneWaehlen(e) {
    if (e === W.e) { W.fokus = null; W.sel = null; anwenden(); return; }
    const vorher = W.fokus && NACH_ID[W.fokus], pt = vorher ? ortPunkt(vorher) : W.ort;
    W.e = e; W.fokus = null; W.sel = null; W.leer = null; W.filter = ""; W.fest = null;
    // Ortsanker: an derselben Stelle die Wahl der neuen Ebene und die Einheit, in der der Punkt liegt
    if (pt) { const w = amOrt(pt, e).filter(passtKammer)[0]; if (w) { W.fokus = w.id; einheitAmOrt(w, pt); } }
    umblenden();
  }
  function einheitAmOrt(w, pt) {
    const i = einheitBei(w, tiefe()); if (i < 0) return;
    const u = w.einheiten[i];
    // Grenzen noch nicht geladen: nach dem Laden dieselbe Stelle noch einmal suchen, solange die Wahl im Fokus bleibt
    if (u.nach && !u.geladen) { werteNachladen(u).then(() => { if (W.fokus === w.id && !W.sel && u.geladen) { einheitAmOrt(w, pt); anwenden(); } }); return; }
    if (u.geo && NACH[u.geo] && !geo()[u.geo]) { nachladen(u.geo); const p = LAEDT.get(u.geo); if (p) p.then(() => { if (W.fokus === w.id && !W.sel && geo()[u.geo]) { einheitAmOrt(w, pt); anwenden(); } }); return; }
    const k = Object.keys(u.werte).find(key => flaechen(u.geo, key).some(f => enthaelt(f, pt)));
    if (k) W.sel = { u: i, k };
  }
  function wahlWaehlen(id, fliegen = true) {
    BLOCK.freigeben("wahlen-daten", "gliedstaaten-geo");      // Deep Link auf eine Wahl, ohne dass die Form Politik schon offen war
    if (!D && BLOCK.status("wahlen-daten").laedt) { WARTET = [id, fliegen]; return; }
    const w = NACH_ID[id]; if (!w) { W.fokus = null; W.sel = null; anwenden(); return; }
    W.e = w.e; if (w.e === 1) W.kammer = kammerVon(w);
    W.fokus = id; W.sel = null; W.leer = null; W.filter = ""; W.ort = null;
    if (w.land !== G.zustand().land) G.landWaehlen(w.land);
    anwenden();
    if (fliegen) zeigen(w.geo, w.gebiet, einheitenMitGrenzen(w).length ? Z2[0] - .3 : 9);
  }
  document.addEventListener("click", ev => {
    if (!G.imGlobus()) return;
    const t = ev.target, a = n => { const x = t.closest && t.closest("[" + n + "]"); return x ? x.getAttribute(n) : null; };
    let v;
    if (a("data-wa-erneut") != null) { BLOCK.erneut("wahlen-daten"); G.seiteZeichnen(); return; }
    if ((v = a("data-wa-ebene")) != null) { ebeneWaehlen(+v); return; }
    if ((v = a("data-wa-kammer")) != null) {
      const land = bezugsland(), neu = (kammernVon(land).find(x => x[0] === v) || [])[1];
      if (neu && W.fokus) wahlWaehlen(neu.id, false); else { W.kammer = v; W.fokus = null; W.sel = null; umblenden(); }
      return;
    }
    if ((v = a("data-wa-wahl")) != null) { wahlWaehlen(v); return; }
    if ((v = a("data-wa-sprung")) != null) { const w = NACH_ID[v]; if (!w) return; const pt = W.fokus ? ortPunkt(NACH_ID[W.fokus]) : W.ort; W.e = w.e; W.fokus = w.id; W.sel = null; W.filter = ""; if (pt) { W.ort = pt; einheitAmOrt(w, pt); } if (w.land !== G.zustand().land) G.landWaehlen(w.land); anwenden(); return; }
    if ((v = a("data-wa-einheit")) != null) { const [ui, ...k] = v.split(":"), key = k.join(":"), w = NACH_ID[W.fokus]; if (!w) return; W.sel = { u: +ui, k: key }; W.ort = null; anwenden(); const u = w.einheiten[+ui]; if (u.geo) zeigen(u.geo, key, 9.5); return; }
    if ((v = a("data-wa-pfad")) != null) { if (v === "ebene") { W.fokus = null; W.sel = null; } else W.sel = null; W.ort = null; anwenden(); return; }
    if ((v = a("data-wa-stimmart")) != null) { if (W.fokus) W.stimmart[W.fokus] = v; anwenden(); return; }
    if ((v = a("data-wa-sort")) != null) { W.sort = v; G.seiteZeichnen(); return; }
    if ((v = a("data-wa-tiefe")) != null) { const m = karte(), z = +v === 1 ? (Z1[1] + Z2[0]) / 2 : Z2[1] + .4; if (W.fest != null) W.fest = +v; anwenden(); if (m && W.fest == null) m.easeTo({ zoom: z, duration: 800 }); return; }
  });
  document.addEventListener("change", ev => {
    const t = ev.target; if (!t.matches || !t.matches("[data-wa]")) return;
    const k = t.dataset.wa, v = t.value;
    if (k === "wahl") { if (v) wahlWaehlen(v, false); else { W.fokus = null; W.sel = null; anwenden(); } }
    else if (k === "kammer") { W.kammer = v; W.fokus = null; W.sel = null; umblenden(); }
    else if (k === "stimmart") { if (W.fokus) W.stimmart[W.fokus] = v; anwenden(); }
    else if (k === "einheit") { W.fest = v === "auto" ? null : +v; anwenden(); }
    else if (k === "faerbung") { W.faerbung = v; if (v === "anteil" && W.fokus && !W.partei) W.partei = (anteile(NACH_ID[W.fokus]).l[0] || [""])[0]; anwenden(); }
    else if (k === "partei") { W.partei = v; anwenden(); }
  });
  document.addEventListener("input", ev => {
    const t = ev.target; if (!t.matches || !t.matches("[data-wa-filter]")) return;
    W.filter = t.value; const pos = t.selectionStart; G.seiteZeichnen();
    const neu = document.querySelector("[data-wa-filter]"); if (neu) { neu.focus(); try { neu.setSelectionRange(pos, pos); } catch { /* */ } }
  });
  // Pfeiltasten: in der Liste von Einheit zu Einheit springen
  document.addEventListener("keydown", ev => {
    if (!aktiv() || !W.fokus || !W.sel || !["ArrowDown", "ArrowUp"].includes(ev.key) || /input|select|textarea/i.test((ev.target.tagName || ""))) return;
    const w = NACH_ID[W.fokus], u = w.einheiten[W.sel.u], keys = Object.keys(u.werte).sort((a, b) => (u.werte[a].n || a).localeCompare(u.werte[b].n || b, "de", { numeric: true }));
    const i = keys.indexOf(W.sel.k), j = Math.max(0, Math.min(keys.length - 1, i + (ev.key === "ArrowDown" ? 1 : -1)));
    if (j !== i) { ev.preventDefault(); W.sel = { u: W.sel.u, k: keys.at(j) }; W.ort = null; anwenden(); if (u.geo) zeigen(u.geo, keys.at(j), 9.5); }
  });
  document.addEventListener("globus:form", () => { tipWeg(); bedienung(); if (aktiv()) { binden(); kartenAnwenden(); } });
  document.addEventListener("globus:politik", () => { tipWeg(); bedienung(); if (aktiv()) { binden(); kartenAnwenden(); } });
  // Land in der Suche oder Seitenleiste gewählt: Leiter zeigt die Namen dieses Landes
  (function warte(n) { const m = karte(); if (m) { m.once("idle", () => { binden(); bedienung(); }); } else if (n < 200) setTimeout(() => warte(n + 1), 100); })(0);
  bedienung();
  return { seite, legende, zustand: () => W, wahl: id => NACH_ID[id], wahlWaehlen, ebeneWaehlen, anwenden };
})();
