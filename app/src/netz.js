/* ---------- Unternehmensnetz auf der Weltkugel ----------
   Zeigt für ein gewähltes Unternehmen (z. B. Volkswagen) vom Hauptsitz aus Werke, Töchter, Lieferungen zwischen Standorten
   (mit Stückzahlen, soweit veröffentlicht), Gemeinschaftsunternehmen, Beteiligungen, Eigentümer und wichtige Kunden.

   Daten: <script id="geo-netze"> aus stammdaten/beziehungen/daten/<ID>_<name>.json (geprüft von beziehungen.py), je Konzern
   { unternehmen_id, name, stand, berichtsjahr, quellen{}, standorte[], beziehungen[] }. Jede Angabe trägt Quellen und Jahr;
   unsicher: true wird gestrichelt bzw. mit ⚠ gezeigt.

   Einbindung: Ebene "netz" über GLOBUS.ebene (vorrang: Klick vor den Unternehmenspunkten). Geöffnet wird das Netz, wenn die
   Weltkugel ein Unternehmen öffnet ("globus:firma"), das ein Netz hat oder darin als Standort vorkommt (z. B. Porsche AG). */
"use strict";
const NETZ = (() => {
  const NETZE = (() => { try { return JSON.parse(document.getElementById("geo-netze").textContent) || {}; } catch { return {}; } })();
  const INDEX = {};                                      // Unternehmens-ID -> { n: Netz-ID, s: Standort-ID }
  for (const [nid, d] of Object.entries(NETZE)) {
    const haupt = d.standorte.find(s => s.art === "hauptsitz") || d.standorte[0];
    d.st = Object.fromEntries(d.standorte.map(s => [s.id, s]));
    d.haupt = haupt.id;
    d.quellNr = Object.fromEntries(Object.keys(d.quellen).map((k, i) => [k, i + 1]));
    for (const s of d.standorte) if (s.unternehmen_id && !INDEX[s.unternehmen_id]) INDEX[s.unternehmen_id] = { n: nid, s: s.id };
    INDEX[nid] = { n: nid, s: haupt.id };
  }

  /* Beziehungsarten: Farbe UND Linienstil (nicht nur Farbe), jede Art einzeln filterbar. Weder Grün noch Rot: beides gehört den Handelsströmen
     (Export grün, Import rot). dash = Strich/Lücke in Linienbreiten (MapLibre), null = durchgezogen; css = gleiches Muster für die Legende in px. */
  const ART = {
    tochter:       { name: "Tochtergesellschaft", farbe: "#ffa828", dash: null, css: "" },
    produktion:    { name: "Produktionsstandort", farbe: "#2ec4d6", dash: [1, 2], css: "1 4" },
    lieferung:     { name: "Warenverkehr / Lieferung", farbe: "#4da3ff", dash: [4, 2], css: "9 5" },
    logistik:      { name: "Logistik", farbe: "#8b95a3", dash: [4, 2, 1, 2], css: "9 4 2 4" },
    joint_venture: { name: "Gemeinschaftsunternehmen", farbe: "#b57bff", dash: [2.4, 1.4], css: "5 3" },
    beteiligung:   { name: "Beteiligung", farbe: "#ff7ac8", dash: [1, 1.2], css: "2 3" },
    eigentuemer:   { name: "Eigentümer", farbe: "#e8ecf1", dash: [7, 2, 7, 2], css: "14 4" },
    kunde:         { name: "Kunde", farbe: "#f2e04a", dash: [3, 1.6, 1, 1.6], css: "6 3 2 3" },
    lieferant:     { name: "Lieferant", farbe: "#d9a21b", dash: [5, 1.5], css: "10 3" },
    partner:       { name: "Partner", farbe: "#ff7ac8", dash: [1, 1.2], css: "2 3" },
    filiale:       { name: "Filiale / Niederlassung", farbe: "#6fd0e8", dash: [3, 3], css: "6 6" },
  };
  const swatch = (a, b = 36) => `<svg class="nz-sw" width="${b}" height="8" aria-hidden="true"><line x1="1" y1="4" x2="${b - 1}" y2="4" stroke="${THEMA.farbe(a.farbe, 'line-color')}" stroke-width="2.6"${a.css ? ` stroke-dasharray="${a.css}"` : ' stroke-linecap="round"'}/></svg>`;
  /* Standortarten: Farbe der Punkte */
  const ORT = {
    hauptsitz: ["Konzernzentrale", "#ffa828"], hauptsitz_tochter: ["Sitz einer Tochter", "#ffc56b"], fahrzeugwerk: ["Fahrzeugwerk", "#2ec4d6"],
    komponentenwerk: ["Komponentenwerk", "#4da3ff"], werk: ["Produktionsstandort", "#2ec4d6"], filiale: ["Filiale / Niederlassung", "#d9a21b"], batterie: ["Batteriewerk", "#9ad7f2"], finanzen: ["Finanzdienstleistungen", "#d9a21b"],
    vertrieb: ["Vertrieb / Auslieferung", "#8b95a3"], entwicklung: ["Entwicklung", "#8b95a3"], joint_venture: ["Gemeinschaftsunternehmen", "#b57bff"],
    beteiligung: ["Beteiligung", "#ff7ac8"], partner: ["Partner", "#ff7ac8"], kunde: ["Kunde", "#f2e04a"], eigentuemer: ["Eigentümer", "#e8ecf1"], lieferant: ["Lieferant", "#d9a21b"],
  };
  const S = { netz: null, aus: new Set(), wahl: null, bez: null };
  const nf = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 2 });
  const e = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const landName = (() => { let dn = null; try { dn = new Intl.DisplayNames(["de"], { type: "region" }); } catch { dn = null; } return c => { try { return (dn && dn.of(c)) || c; } catch { return c; } }; })();
  const netz = () => S.netz && NETZE[S.netz];
  // Kartenschrift ist nur für Latin-1 eingebettet: andere Zeichen (ő, ł, ả) ohne Akzent, sonst fehlen sie in der Beschriftung
  const latin1 = t => [...t].map(c => c.charCodeAt(0) < 256 ? c : c.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/ł/g, "l").replace(/Ł/g, "L").replace(/[^\u0000-\u00ff]/g, "")).join("");
  const wert = z => `${z.vergleich ? e(z.vergleich) + " " : ""}${nf.format(z.wert)} ${e(z.einheit)}`;

  /* ----- Kartendaten ----- */
  const sichtbareBez = d => d.beziehungen.filter(b => !S.aus.has(b.art));
  function sichtbareOrte(d) {
    const ids = new Set([d.haupt]);
    sichtbareBez(d).forEach(b => { ids.add(b.von); ids.add(b.nach); });
    return d.standorte.filter(s => ids.has(s.id));
  }
  const stueck = z => /Fahrzeug|Motor|Antrieb|Getriebe|Batterie|Motorr/.test(z.einheit) && !/Kapazität|seit|Anteil/i.test(z.name);
  function punktRadius(d, s) {
    if (s.id === d.haupt) return 11;
    const p = (s.kennzahlen || []).filter(stueck).map(z => z.wert).sort((a, b) => b - a)[0];
    const r = p ? 4 + 1.6 * Math.log10(1 + p / 5000) : 4.5;
    return Math.min(10, /hauptsitz/.test(s.art) ? Math.max(r, 7.5) : r);
  }
  function breite(b) {
    const m = b.menge;
    if (m && /Fahrzeug|Motor|Antrieb|Getriebe|Batterie|Komponent/.test(m.einheit)) return Math.min(7, 1.4 + 1.3 * Math.log10(1 + m.wert / 10000));
    if (b.anteil) return Math.min(6, 1.2 + b.anteil / 14);
    return 1.5;
  }
  function daten() {
    const leer = { type: "FeatureCollection", features: [] };
    const d = netz(); if (!d) return { punkte: leer, linien: leer, marken: leer };
    const orte = sichtbareOrte(d);
    const punkte = { type: "FeatureCollection", features: orte.map(s => ({ type: "Feature", geometry: { type: "Point", coordinates: [s.lon, s.lat] },
      properties: { id: s.id, name: s.name, kurz: latin1(s.ort), art: s.art, farbe: (ORT[s.art] || ORT.vertrieb)[1], r: punktRadius(d, s), haupt: s.id === d.haupt ? 1 : 0,
        unsicher: s.unsicher ? 1 : 0, gewaehlt: s.id === S.wahl ? 1 : 0 } })) };
    // mehrere Beziehungen zwischen denselben zwei Orten: Bögen verschieden weit ausbiegen, damit sie nicht aufeinander liegen
    const paar = {}, sb = sichtbareBez(d), pk = b => [b.von, b.nach].sort().join("|");
    sb.forEach(b => { (paar[pk(b)] = paar[pk(b)] || []).push(b); });
    const marken = [];
    const linien = { type: "FeatureCollection", features: sb.map(b => {
      const a = d.st[b.von], z = d.st[b.nach], gr = paar[pk(b)], k = gr.indexOf(b), n = gr.length;
      const hub = (n > 1 ? (k - (n - 1) / 2) * .07 : 0) * (b.von < b.nach ? 1 : -1);
      const bg = GLOBUS.bogen([a.lon, a.lat], [z.lon, z.lat], 48, hub);
      if (b.unsicher) marken.push({ type: "Feature", geometry: { type: "Point", coordinates: bg[24] }, properties: { art: b.art } });
      return { type: "Feature", geometry: { type: "LineString", coordinates: bg },
        properties: { i: d.beziehungen.indexOf(b), art: b.art, farbe: (ART[b.art] || ART.partner).farbe, breite: breite(b), unsicher: b.unsicher ? 1 : 0,
          bezug: S.wahl && (b.von === S.wahl || b.nach === S.wahl) ? 1 : 0 } };
    }) };
    return { punkte, linien, marken: { type: "FeatureCollection", features: marken } };
  }
  function aktualisieren() {
    const m = GLOBUS.karte(); if (!m || !m.getSource("netz-punkte")) return;
    const x = daten();
    m.getSource("netz-punkte").setData(x.punkte);
    m.getSource("netz-linien").setData(x.linien);
    m.getSource("netz-marken").setData(x.marken);
  }

  /* Pfeilspitze als SDF-Bild (Farbe kommt aus icon-color) */
  function pfeil(m) {
    if (m.hasImage("netz-pfeil")) return;
    const n = 24, data = new Uint8Array(n * n * 4);
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
      // Dreieck nach rechts: Spitze bei x = n-3, Basis bei x = 5
      const t = (x - 5) / (n - 8), halb = (1 - t) * (n / 2 - 4), innen = t >= 0 && t <= 1 && Math.abs(y - n / 2 + .5) <= halb;
      data[(y * n + x) * 4 + 3] = innen ? 255 : 0;
    }
    m.addImage("netz-pfeil", { width: n, height: n, data }, { sdf: true });
  }

  const farbeAusDaten = ["get", "farbe"];
  GLOBUS.ebene({ id: "netz", name: "Unternehmensnetz (gewähltes Unternehmen)", gruppe: "Unternehmen", an: true, vorrang: true,
    quellen: m => { const x = daten(); m.addSource("netz-linien", { type: "geojson", data: x.linien }); m.addSource("netz-punkte", { type: "geojson", data: x.punkte }); m.addSource("netz-marken", { type: "geojson", data: x.marken }); pfeil(m); },
    schichten: m => {
      const opac = ["case", ["==", ["get", "bezug"], 1], 1, S.wahl ? .28 : .8];
      const sch = def => m.addLayer({ ...def, metadata: { ebene: "netz" } });
      // eine Linienschicht je Art (Strichmuster lassen sich in MapLibre nicht je Objekt wählen)
      Object.entries(ART).forEach(([art, a]) => sch({ id: "netz-linie-" + art, type: "line", source: "netz-linien", filter: ["==", ["get", "art"], art],
        layout: { "line-cap": a.dash ? "butt" : "round" }, paint: { "line-color": a.farbe, "line-width": ["get", "breite"], "line-opacity": ["*", opac, ["case", ["==", ["get", "unsicher"], 1], .6, 1]], ...(a.dash ? { "line-dasharray": a.dash } : {}) } }));
      sch({ id: "netz-pfeil", type: "symbol", source: "netz-linien", layout: { "symbol-placement": "line", "symbol-spacing": 110, "icon-image": "netz-pfeil",
        "icon-size": ["interpolate", ["linear"], ["get", "breite"], 1, .45, 7, .8], "icon-allow-overlap": false, "icon-padding": 6, "icon-rotation-alignment": "map" },
        paint: { "icon-color": farbeAusDaten, "icon-opacity": opac } });
      sch({ id: "netz-unsicher", type: "symbol", source: "netz-marken", layout: { "text-field": "?", "text-font": ["Noto Sans Bold"], "text-size": 14, "text-allow-overlap": false, "text-padding": 6 },
        paint: { "text-color": "#ffd27a", "text-halo-color": "#07090c", "text-halo-width": 1.8 } });
      sch({ id: "netz-halo", type: "circle", source: "netz-punkte", filter: ["==", ["get", "gewaehlt"], 1],
        paint: { "circle-radius": ["+", ["get", "r"], 7], "circle-color": "rgba(0,0,0,0)", "circle-stroke-color": "#ffffff", "circle-stroke-width": 2 } });
      sch({ id: "netz-punkt", type: "circle", source: "netz-punkte",
        paint: { "circle-radius": ["get", "r"], "circle-color": farbeAusDaten, "circle-stroke-color": ["case", ["==", ["get", "unsicher"], 1], "#ffd27a", "#07090c"],
          "circle-stroke-width": ["case", ["==", ["get", "haupt"], 1], 2.5, 1.3] } });
      sch({ id: "netz-name", type: "symbol", source: "netz-punkte",
        filter: ["any", ["==", ["get", "haupt"], 1], ["==", ["get", "gewaehlt"], 1], [">=", ["zoom"], 3.6]],
        layout: { "text-field": ["get", "kurz"], "text-font": ["Noto Sans Regular"], "text-size": ["case", ["==", ["get", "haupt"], 1], 13, 11], "text-offset": [0, 1.2],
          "text-anchor": "top", "text-optional": true, "text-max-width": 9, "symbol-sort-key": ["-", 0, ["get", "r"]], "text-padding": 3 },
        paint: { "text-color": "#e8ecf1", "text-halo-color": "#07090c", "text-halo-width": 1.4 } });
    },
    klick: (ev, m) => {
      if (!netz()) return false;
      const lay = ["netz-punkt", ...Object.keys(ART).map(k => "netz-linie-" + k)].filter(l => m.getLayer(l));
      const f = lay.length ? m.queryRenderedFeatures([[ev.point.x - 4, ev.point.y - 4], [ev.point.x + 4, ev.point.y + 4]], { layers: lay }) : [];
      const p = f.find(x => x.layer.id === "netz-punkt");
      if (p) { waehlen(p.properties.id, { fliegen: false }); return true; }
      if (f.length) { bezZeigen(f[0].properties.i); return true; }
      return false;
    } });

  /* ----- Tooltip ----- */
  let tip = null;
  function tooltip(ev) {
    const m = GLOBUS.karte(), d = netz();
    if (!m || !d || !m.getLayer("netz-punkt")) return;
    const lay = ["netz-punkt", ...Object.keys(ART).map(k => "netz-linie-" + k)].filter(l => m.getLayer(l));
    const f = ev && lay.length ? m.queryRenderedFeatures([[ev.point.x - 3, ev.point.y - 3], [ev.point.x + 3, ev.point.y + 3]], { layers: lay }) : [];
    if (!f.length) { if (tip) { tip.remove(); tip = null; } return; }
    const p = f.find(x => x.layer.id === "netz-punkt") || f[0];
    let html;
    if (p.layer.id === "netz-punkt") {
      const s = d.st[p.properties.id], z = (s.kennzahlen || [])[0];
      html = `<b>${e(s.name)}</b><br><span class="pct">${e((ORT[s.art] || [s.art])[0])} · ${e(s.ort)}, ${e(landName(s.land))}</span>${z ? `<br>${e(z.name)}: ${wert(z)} (${z.jahr})` : ""}${s.unsicher ? "<br>⚠ unsicher" : ""}`;
    } else {
      const b = d.beziehungen[p.properties.i];
      html = `<b>${e(d.st[b.von].ort)} → ${e(d.st[b.nach].ort)}</b><br><span class="pct">${e((ART[b.art] || { name: b.art }).name)}${b.gut ? " · " + e(b.gut) : ""}</span>${b.menge ? `<br>${wert(b.menge)} (${b.menge.jahr})` : b.anteil ? `<br>Anteil ${nf.format(b.anteil)} %` : ""}${b.unsicher ? "<br>⚠ unsicher" : ""}`;
    }
    if (!tip) tip = new maplibregl.Popup({ closeButton: false, closeOnClick: false, className: "gk-pop", offset: 12, maxWidth: "300px" });
    tip.setLngLat(ev.lngLat).setHTML(html).addTo(m);
  }

  /* ----- Panel ----- */
  function panel() {
    let el = document.getElementById("netz-panel");
    if (!el) {
      el = document.createElement("section"); el.id = "netz-panel"; el.className = "nz"; el.setAttribute("aria-label", "Unternehmensnetz");
      document.getElementById("gk-karte").appendChild(el);
    }
    return el;
  }
  const quelleLink = (d, k) => { const q = d.quellen[k]; return q ? `<a href="${e(q.url)}" target="_blank" rel="noopener" title="${e(q.titel)} (${e(q.herausgeber || "")}, ${q.jahr})">[${d.quellNr[k]}]</a>` : ""; };
  const quellen = (d, ks) => (ks || []).map(k => quelleLink(d, k)).join("");
  function bezZeile(d, b, sicht) {
    const ander = d.st[b.von === sicht ? b.nach : b.von], raus = b.von === sicht, a = ART[b.art] || { name: b.art, farbe: "#888" };
    return `<li><i style="background:${a.farbe}"></i><div><button type="button" data-nzort="${e(ander.id)}">${raus ? "→" : "←"} ${e(ander.name)}</button>
      <div class="nz-k">${e(a.name)}${b.gut ? ": " + e(b.gut) : ""}${b.menge ? ` · <b>${wert(b.menge)}</b> (${b.menge.jahr})` : b.anteil ? ` · <b>${nf.format(b.anteil)} %</b>` : ""}${b.unsicher ? ' · <span class="nz-u">⚠ unsicher</span>' : ""} ${quellen(d, b.quellen)}</div>
      ${b.text ? `<div class="nz-t">${e(b.text)}</div>` : ""}</div></li>`;
  }
  function ortAnsicht(d, s) {
    const bez = d.beziehungen.filter(b => b.von === s.id || b.nach === s.id);
    const kz = (s.kennzahlen || []).map(z => `<tr><td>${e(z.name)}${z.unsicher ? ' <span class="nz-u" title="Sekundärquelle oder nicht bestätigt">⚠</span>' : ""}</td><td>${wert(z)}</td><td>${z.jahr} ${quellen(d, [z.quelle || (s.quellen || [])[0]])}</td></tr>`).join("");
    const profil = s.unternehmen_id ? `<button type="button" class="gk-knopf" data-nzprofil="${e(s.unternehmen_id)}">Unternehmensprofil öffnen</button>` : "";
    return `<button type="button" class="nz-zurueck" data-nzliste>‹ Alle Standorte</button>
      <h4>${e(s.name)}</h4>
      <div class="nz-meta"><span class="nz-art" style="--f:${(ORT[s.art] || ORT.vertrieb)[1]}">${e((ORT[s.art] || [s.art])[0])}</span> ${e(s.ort)}, ${e(landName(s.land))}${s.status ? ` · ${e(s.status)}` : ""}</div>
      <div class="nz-meta">${e(s.gesellschaft || "")}${s.marke && s.marke !== s.gesellschaft ? ` · ${e(s.marke)}` : ""}</div>
      <p>${e(s.taetigkeit)} ${quellen(d, s.quellen)}</p>
      ${s.unsicher || s.hinweis ? `<p class="nz-hin">${s.unsicher ? "⚠ " : ""}${e(s.hinweis || "Angabe unsicher.")}</p>` : ""}
      ${kz ? `<table class="gk-tab nz-tab"><thead><tr><th>Kennzahl</th><th>Wert</th><th>Jahr</th></tr></thead><tbody>${kz}</tbody></table>` : `<p class="gk-leer">Keine Kennzahlen veröffentlicht oder noch nicht erfasst.</p>`}
      ${profil}
      ${bez.length ? `<h5>Beziehungen (${bez.length})</h5><ul class="nz-bez">${bez.map(b => bezZeile(d, b, s.id)).join("")}</ul>` : ""}`;
  }
  function listeAnsicht(d) {
    const orte = sichtbareOrte(d), gruppen = {};
    const gruppe = s => s.id === d.haupt ? "0Konzern" : ["joint_venture", "beteiligung", "partner"].includes(s.art) ? "2Gemeinschaftsunternehmen und Beteiligungen"
      : s.art === "eigentuemer" ? "3Eigentümer" : s.art === "kunde" ? "4Kunden" : "1" + (s.marke || "Sonstige");
    orte.forEach(s => { const g = gruppe(s); (gruppen[g] = gruppen[g] || []).push(s); });
    const haupt = (s) => { const z = (s.kennzahlen || []).find(stueck) || (s.kennzahlen || [])[0]; return z ? `${nf.format(z.wert)} ${z.einheit.replace(/ \(.*\)$/, "")}` : ""; };
    return Object.keys(gruppen).sort((a, b) => a.localeCompare(b, "de")).map(g => `<h5>${e(g.slice(1))}</h5><ul class="gk-liste nz-liste">${gruppen[g].map(s =>
      `<li><button type="button" data-nzort="${e(s.id)}"><i style="background:${(ORT[s.art] || ORT.vertrieb)[1]}"></i>${e(s.name)}${s.unsicher ? " ⚠" : ""}</button><span class="r">${e(haupt(s))}</span></li>`).join("")}</ul>`).join("");
  }
  function bezAnsicht(d, b) {
    const a = ART[b.art] || { name: b.art, farbe: "#888" };
    return `<button type="button" class="nz-zurueck" data-nzliste>‹ Alle Standorte</button>
      <h4>${e(d.st[b.von].name)} → ${e(d.st[b.nach].name)}</h4>
      <div class="nz-meta"><span class="nz-art" style="--f:${a.farbe}">${e(a.name)}</span>${b.gut ? " " + e(b.gut) : ""}</div>
      ${b.menge ? `<div class="nz-gross">${wert(b.menge)} <small>${b.menge.jahr}</small></div>` : b.anteil ? `<div class="nz-gross">${nf.format(b.anteil)} % <small>Anteil${b.jahr ? " " + b.jahr : ""}</small></div>` : ""}
      <p>${e(b.text || "")} ${quellen(d, b.quellen)}</p>
      ${b.unsicher ? `<p class="nz-hin">⚠ Unsicher: ${b.ziel_sammel ? "Empfänger stellvertretend gewählt oder " : ""}Angabe nur aus Presse oder nicht ausdrücklich belegt.</p>` : b.ziel_sammel ? `<p class="nz-hin">Die Quelle nennt die Gesamtmenge für mehrere Empfängerwerke; der Bogen zeigt stellvertretend zum Hauptsitz bzw. Hauptabnehmer.</p>` : ""}
      <div class="nz-zwei"><button type="button" class="gk-knopf" data-nzort="${e(b.von)}">${e(d.st[b.von].ort)}</button><button type="button" class="gk-knopf" data-nzort="${e(b.nach)}">${e(d.st[b.nach].ort)}</button></div>`;
  }
  function zeichnen() {
    const d = netz(), el = panel();
    el.hidden = !d;
    if (!d) return;
    const arten = d => { const n = {}; d.beziehungen.forEach(b => { n[b.art] = (n[b.art] || 0) + 1; }); return Object.entries(n).sort((x, y) => y[1] - x[1]); };
    const inhalt = S.bez != null ? bezAnsicht(d, d.beziehungen[S.bez]) : S.wahl ? ortAnsicht(d, d.st[S.wahl]) : listeAnsicht(d);
    const qliste = Object.entries(d.quellen).map(([k, q]) => `<li id="nzq-${e(k)}">[${d.quellNr[k]}] <a href="${e(q.url)}" target="_blank" rel="noopener">${e(q.titel)}</a> <span>${e(q.herausgeber || "")}, ${q.jahr}${q.art === "presse" ? ", Presse" : ""}</span></li>`).join("");
    el.innerHTML = `<header><div><small>UNTERNEHMENSNETZ</small><b>${e(d.name)}</b><span>Geschäftsjahr ${d.berichtsjahr} · Stand ${e(d.stand.split("-").reverse().join("."))} · ${d.standorte.length} Standorte, ${d.beziehungen.length} Beziehungen</span></div>
        <div class="nz-kn"><button type="button" data-nzklein aria-label="Panel ein- oder ausklappen" title="Ein-/ausklappen">▾</button><button type="button" data-nzzu aria-label="Netz ausblenden" title="Netz ausblenden">✕</button></div></header>
      <div class="nz-rumpf">
      <div class="gk-chips nz-chips" role="group" aria-label="Beziehungsarten (Legende und Filter)">${arten(d).map(([art, n]) => { const a = ART[art] || ART.partner;
        return `<button type="button" data-nzart="${art}" aria-pressed="${!S.aus.has(art)}" title="${e(a.name)} ein-/ausblenden">${swatch(a)}${e(a.name)} <span>${n}</span></button>`; }).join("")}</div>
      <p class="nz-leg">Farbe und Strichmuster zeigen die Art, der Pfeil die Richtung, Breite die Menge bzw. den Anteil, <b>?</b> = unsicher (Linie blasser). Handelsströme sind grün (Export) und rot (Import) und treten zurück, solange dieses Netz offen ist.</p>
      <div class="nz-inhalt">${inhalt}</div>
      <details class="nz-q"><summary>Quellen und Hinweise (${Object.keys(d.quellen).length})</summary><p>${e(d.hinweis || "")}</p><p>Bögen: Breite nach Stückzahl bzw. Anteil, Pfeil zeigt die Richtung, ? und blassere Linie = unsicher. Punkte: Größe nach Produktion, Koordinate = Ortsmitte.</p><ol>${qliste}</ol></details>
      </div>`;
  }

  /* ----- Steuerung ----- */
  function zeigen(nid, sid, opt = {}) {
    const neu = S.netz !== nid, vorher = S.wahl;
    S.netz = nid; S.bez = null;
    melden();
    S.wahl = sid && sid !== NETZE[nid].haupt ? sid : null;
    const m = GLOBUS.karte();
    const eb = GLOBUS.ebenen().find(x => x.id === "netz");
    if (eb && !eb.an) { eb.an = true; GLOBUS.sichtbar("netz"); }
    aktualisieren(); zeichnen();
    if (m && (neu || opt.fliegen || S.wahl !== vorher)) {
      const s = NETZE[nid].st[sid || NETZE[nid].haupt];
      setTimeout(() => m.flyTo({ center: [s.lon, s.lat], zoom: S.wahl ? 3.6 : 1.6, duration: 1500, padding: rand() }), 30);
    }
    if (neu) GLOBUS.hinweis(`Unternehmensnetz ${NETZE[nid].name}: ${NETZE[nid].standorte.length} Standorte und ${NETZE[nid].beziehungen.length} Beziehungen`);
  }
  // Kartenmitte neben das Panel legen (breit: Panel rechts, schmal: Panel unten)
  const rand = () => S.netz ? (innerWidth > 820 ? { right: 350, left: 0, top: 0, bottom: 0 } : { bottom: Math.round(innerHeight * .5), left: 0, right: 0, top: 0 }) : { left: 0, right: 0, top: 0, bottom: 0 };
  function melden() { document.dispatchEvent(new CustomEvent("globus:netz", { detail: { offen: !!S.netz } })); }
  function verbergen() { S.netz = null; melden(); S.wahl = null; S.bez = null; aktualisieren(); zeichnen(); if (tip) { tip.remove(); tip = null; } const m = GLOBUS.karte(); if (m) m.easeTo({ padding: rand(), duration: 400 }); }
  function waehlen(sid, opt = {}) {
    const d = netz(); if (!d || !d.st[sid]) return;
    S.wahl = sid === S.wahl && !opt.fliegen ? S.wahl : sid; S.bez = null;
    aktualisieren(); zeichnen();
    const m = GLOBUS.karte(), s = d.st[sid];
    if (m && opt.fliegen !== false) m.flyTo({ center: [s.lon, s.lat], zoom: Math.max(m.getZoom(), 3.4), duration: 1100, padding: rand() });
    const i = panel().querySelector(".nz-inhalt"); if (i) i.scrollTop = 0;
  }
  function bezZeigen(i) { const d = netz(); if (!d) return; S.bez = i; S.wahl = null; aktualisieren(); zeichnen(); }

  document.addEventListener("globus:firma", ev => { const x = INDEX[ev.detail.id]; if (x) zeigen(x.n, x.s); });
  document.addEventListener("click", ev => {
    const t = ev.target; if (!t.closest || !t.closest("#netz-panel")) return;
    const g = a => { const x = t.closest("[" + a + "]"); return x ? x.getAttribute(a) : null; };
    let v;
    if ((v = g("data-nzort")) != null) waehlen(v);
    else if (g("data-nzliste") != null) { S.wahl = null; S.bez = null; aktualisieren(); zeichnen(); }
    else if ((v = g("data-nzart")) != null) { S.aus.has(v) ? S.aus.delete(v) : S.aus.add(v); if (S.wahl && !sichtbareOrte(netz()).some(s => s.id === S.wahl)) S.wahl = null; aktualisieren(); zeichnen(); }
    else if (g("data-nzzu") != null) verbergen();
    else if (g("data-nzklein") != null) panel().classList.toggle("klein");
    else if ((v = g("data-nzprofil")) != null) GLOBUS.oeffnen(v, { fliegen: false });
    else return;
    ev.stopPropagation();
  });
  // Tooltip: eigener Listener auf der Karte, sobald sie existiert (die Karte wird erst beim ersten Öffnen der Weltkugel angelegt)
  (function warte(n) {
    const m = GLOBUS.karte();
    if (m) { m.on("mousemove", tooltip); m.getCanvas().addEventListener("mouseleave", () => tooltip(null)); return; }
    if (n < 600) setTimeout(() => warte(n + 1), 100);
  })(0);
  return { zeigen, verbergen, waehlen, daten, netze: () => NETZE, index: () => INDEX };
})();
