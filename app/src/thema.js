/* Darstellung: drei Farbmodi (Dunkel = Standard, Hell, Dunkelblau). Zahnrad oben rechts (Terminal-Kopf und Weltkugel-Kopf) öffnet die
   Einstellungen. Die Auswahl steht in localStorage ("sphaerae-thema") und als data-thema am <html>; die Farben selbst sind CSS-Variablen
   (terminal.html, :root[data-thema=…]). Die Karte (MapLibre) kennt keine CSS-Variablen: THEMA.karte(map) hängt sich an addLayer,
   setPaintProperty, setLayoutProperty, setStyle und setSky, merkt sich die Originalfarben (Dunkel) und rechnet sie je Modus um. */
const THEMA = (() => {
  const SCHLUESSEL = "sphaerae-thema";
  const MODI = [
    { id: "dunkel", name: "Dunkel", text: "Standard, Terminal im Dunkeln", f: ["#07090c", "#0e1116", "#ffa828"] },
    { id: "hell", name: "Hell", text: "Heller Hintergrund, dunkle Schrift", f: ["#f4f5f7", "#ffffff", "#b86200"] },
    { id: "dunkelblau", name: "Dunkelblau", text: "Nachtblau statt Schwarz", f: ["#081426", "#0d1c33", "#ffa828"] },
  ];
  const gueltig = t => MODI.some(m => m.id === t);
  let aktuell = "dunkel";
  try { const t = localStorage.getItem(SCHLUESSEL); if (gueltig(t)) aktuell = t; } catch (e) { /* kein Speicher (privates Fenster, Vorschau) */ }
  const html = document.documentElement;
  const setzeAttr = () => { if (aktuell === "dunkel") html.removeAttribute("data-thema"); else html.setAttribute("data-thema", aktuell); };
  setzeAttr();

  /* ----- Farben umrechnen (für die Karte und für Farben, die im Code stehen) ----- */
  const hex2 = n => Math.round(Math.max(0, Math.min(255, n))).toString(16).padStart(2, "0");
  function lesen(c) {
    if (typeof c !== "string") return null;
    let m = c.match(/^#([0-9a-f]{3,8})$/i);
    if (m) {
      let h = m[1];
      if (h.length === 3 || h.length === 4) h = [...h].map(x => x + x).join("");
      if (h.length !== 6 && h.length !== 8) return null;
      return { r: parseInt(h.slice(0, 2), 16), g: parseInt(h.slice(2, 4), 16), b: parseInt(h.slice(4, 6), 16), a: h.length === 8 ? parseInt(h.slice(6, 8), 16) / 255 : 1 };
    }
    m = c.match(/^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$/i);
    if (m) return { r: +m[1], g: +m[2], b: +m[3], a: m[4] == null ? 1 : +m[4] };
    return null;
  }
  function zuHsl({ r, g, b }) {
    r /= 255; g /= 255; b /= 255;
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn;
    if (!d) return [0, 0, l];
    const s = d / (1 - Math.abs(2 * l - 1));
    const h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
    return [(h * 60 + 360) % 360, s, l];
  }
  function ausHsl(h, s, l) {
    const c = (1 - Math.abs(2 * l - 1)) * s, x = c * (1 - Math.abs((h / 60) % 2 - 1)), m = l - c / 2;
    const [r, g, b] = h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x] : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x];
    return { r: (r + m) * 255, g: (g + m) * 255, b: (b + m) * 255 };
  }
  const schreiben = (p, a) => a < 1 ? `rgba(${Math.round(p.r)},${Math.round(p.g)},${Math.round(p.b)},${+a.toFixed(3)})` : "#" + hex2(p.r) + hex2(p.g) + hex2(p.b);
  // Grundkarte und feste Flächen: gezielte Gegenstücke (Schlüssel = Farbe im Dunkelmodus)
  const GEGEN = {
    hell: {
      "#0a1320": "#cddcea", "#161c24": "#eef0f3", "#19202a": "#eceff2", "#18211f": "#e1e9de", "#1f2731": "#f7f9fb", "#1c222c": "#e5e8ec",
      "#0f1b2c": "#b6cde4", "#222a35": "#dde1e6", "#2a3442": "#d0d5dc", "#3a4554": "#bec5cf", "#2b313b": "#c5cad2", "#323b48": "#b9c0ca",
      "#536072": "#9aa3b0", "#0d1724": "#d9e4f0", "#18273b": "#edf2f8", "#1c1433": "#f4f0fb", "#f1e8ff": "#3a2370",
    },
    dunkelblau: {
      "#0a1320": "#06142b", "#161c24": "#12284a", "#19202a": "#14294a", "#18211f": "#132c45", "#1f2731": "#1d3354", "#1c222c": "#183052",
      "#0f1b2c": "#0b1e3d", "#222a35": "#1c3557", "#2a3442": "#22406a", "#3a4554": "#2f4d78", "#0d1724": "#0b2045", "#18273b": "#1a3a66", "#07090c": "#050d1b",
    },
  };
  function farbe(c, prop = "", modus = aktuell) {
    if (modus === "dunkel" || typeof c !== "string") return c;
    const p = lesen(c.trim());
    if (!p || p.a === 0) return c;
    const schl = "#" + hex2(p.r) + hex2(p.g) + hex2(p.b);
    const g = (GEGEN[modus] || {})[schl];
    if (g) return p.a < 1 ? schreiben(lesen(g), p.a) : g;
    let [h, s, l] = zuHsl(p);
    const neutral = s < .3 || l < .06, halo = /halo/.test(prop), text = !halo && /(text|icon)-color/.test(prop);
    if (modus === "hell") {
      if (halo) { if (l < .4) { l = 1 - l; s *= .4; } }
      else if (neutral) { l = 1 - l; if (text) l = Math.min(l, .42); }
      else if (text && l > .45) l = .36;
    } else if (modus === "dunkelblau") {
      if (neutral) { h = 214; s = l < .5 ? Math.max(s, .45) : Math.max(s, .2); }
    }
    return schreiben(ausHsl(h, s, l), p.a);
  }
  // Ausdrücke und Objekte (MapLibre-Ausdrücke, format-Optionen, Himmel) rekursiv umrechnen; Schlüssel mit "color" bestimmen die Art
  function wert(v, prop = "", modus = aktuell) {
    if (modus === "dunkel") return v;
    if (typeof v === "string") return /^(#|rgb)/i.test(v) ? farbe(v, prop, modus) : v;
    if (Array.isArray(v)) return v.map(x => wert(x, prop, modus));
    if (v && typeof v === "object") { const o = {}; for (const k in v) o[k] = wert(v[k], /color/.test(k) ? k : prop, modus); return o; }
    return v;
  }
  const farbig = k => /color|text-field/.test(k);

  /* ----- Karte ----- */
  const ORIG = new Map();      // Schicht-ID -> { paint: {…}, layout: {…} } mit den Dunkel-Werten
  let himmelOrig = null, karteRoh = null, karteObj = null;
  const merk = (id, art, k, v) => { let o = ORIG.get(id); if (!o) ORIG.set(id, o = { paint: {}, layout: {} }); o[art][k] = v; };
  function schicht(l) {
    if (!l || typeof l !== "object" || !l.id) return l;
    const n = { ...l };
    for (const art of ["paint", "layout"]) if (l[art]) {
      n[art] = {};
      for (const k in l[art]) { if (farbig(k)) { merk(l.id, art, k, l[art][k]); n[art][k] = wert(l[art][k], k); } else n[art][k] = l[art][k]; }
    }
    return n;
  }
  function stil(s) {      // ganzes Stilobjekt (Konstruktor, setStyle)
    if (!s || typeof s !== "object") return s;
    ORIG.clear();
    himmelOrig = s.sky || null;
    return { ...s, sky: s.sky ? wert(s.sky, "") : s.sky, layers: (s.layers || []).map(schicht) };
  }
  function karte(map) {
    if (!map || map.__thema) return map;
    map.__thema = true;
    const roh = karteRoh = { add: map.addLayer.bind(map), paint: map.setPaintProperty.bind(map), layout: map.setLayoutProperty.bind(map),
      style: map.setStyle.bind(map), sky: map.setSky ? map.setSky.bind(map) : null };
    karteObj = map;
    map.addLayer = (l, vor) => roh.add(schicht(l), vor);
    map.setPaintProperty = (id, k, v, o) => { if (farbig(k)) merk(id, "paint", k, v); return roh.paint(id, k, farbig(k) ? wert(v, k) : v, o); };
    map.setLayoutProperty = (id, k, v, o) => { if (farbig(k)) merk(id, "layout", k, v); return roh.layout(id, k, farbig(k) ? wert(v, k) : v, o); };
    map.setStyle = (s, o) => roh.style(stil(s), o);
    if (roh.sky) map.setSky = s => { himmelOrig = s; return roh.sky(wert(s, "")); };
    return map;
  }
  function karteNeuFaerben() {
    const map = karteObj, roh = karteRoh;
    if (!map || !roh) return;
    try {
      for (const [id, o] of ORIG) {
        if (!map.getLayer(id)) continue;
        for (const k in o.paint) roh.paint(id, k, wert(o.paint[k], k));
        for (const k in o.layout) roh.layout(id, k, wert(o.layout[k], k));
      }
      if (himmelOrig && roh.sky) roh.sky(wert(himmelOrig, ""));
    } catch (e) { console.warn("Kartenfarben", e); }
  }

  /* ----- Umschalten ----- */
  function setzen(t) {
    if (!gueltig(t) || t === aktuell) return;
    aktuell = t;
    try { if (t === "dunkel") localStorage.removeItem(SCHLUESSEL); else localStorage.setItem(SCHLUESSEL, t); } catch (e) { /* ohne Speicher gilt die Wahl bis zum Neuladen */ }
    setzeAttr();
    karteNeuFaerben();
    document.querySelectorAll(".th-fenster input[name=th-modus]").forEach(i => { i.checked = i.value === t; });
    document.dispatchEvent(new CustomEvent("sphaerae:thema", { detail: { thema: t } }));
  }

  /* ----- Zahnrad und Einstellungsfenster ----- */
  const ZAHNRAD = `<svg viewBox="0 0 24 24" width="17" height="17" aria-hidden="true"><path fill="currentColor" d="M19.14 12.94c.04-.31.06-.62.06-.94s-.02-.63-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.62l-1.92-3.32a.49.49 0 0 0-.59-.22l-2.39.96a7.03 7.03 0 0 0-1.62-.94l-.36-2.54A.48.48 0 0 0 13.92 3h-3.84a.48.48 0 0 0-.48.41l-.36 2.54c-.59.24-1.13.56-1.62.94l-2.39-.96a.48.48 0 0 0-.59.22L2.72 9.47a.48.48 0 0 0 .12.62l2.03 1.58c-.05.31-.07.63-.07.94s.02.63.06.94l-2.03 1.58a.49.49 0 0 0-.12.62l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32a.48.48 0 0 0-.12-.62l-2.01-1.58ZM12 15.6A3.6 3.6 0 1 1 12 8.4a3.6 3.6 0 0 1 0 7.2Z"/></svg>`;
  let fenster = null, ausloeser = null;
  function fensterBauen() {
    const el = document.createElement("div");
    el.className = "th-fenster";
    el.id = "th-fenster";
    el.setAttribute("role", "dialog");
    el.setAttribute("aria-label", "Einstellungen");
    el.hidden = true;
    el.innerHTML = `<div class="th-kopf"><h2>Einstellungen</h2><button type="button" class="th-zu" aria-label="Schließen">✕</button></div>
      <fieldset class="th-modi"><legend>Darstellung</legend>${MODI.map(m => `<label class="th-modus">
        <input type="radio" name="th-modus" value="${m.id}"${m.id === aktuell ? " checked" : ""}>
        <span class="th-vorschau" style="background:${m.f[0]}"><i style="background:${m.f[1]}"></i><b style="background:${m.f[2]}"></b></span>
        <span class="th-text"><strong>${m.name}</strong><small>${m.text}</small></span></label>`).join("")}</fieldset>
      <p class="th-fuss">Die Auswahl gilt für Terminal und Weltkugel und bleibt in diesem Browser gespeichert.</p>`;
    el.addEventListener("change", e => { if (e.target.name === "th-modus") setzen(e.target.value); });
    el.querySelector(".th-zu").addEventListener("click", () => schliessen(true));
    document.body.appendChild(el);
    return el;
  }
  function oeffnen(knopf) {
    if (!fenster) fenster = fensterBauen();
    ausloeser = knopf;
    fenster.hidden = false;
    const r = knopf.getBoundingClientRect();
    fenster.style.top = Math.round(r.bottom + 8) + "px";
    fenster.style.right = Math.max(8, Math.round(window.innerWidth - r.right)) + "px";
    document.querySelectorAll(".th-zahnrad").forEach(b => b.setAttribute("aria-expanded", String(b === knopf)));
    (fenster.querySelector("input:checked") || fenster.querySelector("input")).focus();
  }
  function schliessen(fokus) {
    if (!fenster || fenster.hidden) return;
    fenster.hidden = true;
    document.querySelectorAll(".th-zahnrad").forEach(b => b.setAttribute("aria-expanded", "false"));
    if (fokus && ausloeser) ausloeser.focus();
  }
  function knopf(ziel, klasse) {
    if (!ziel || ziel.querySelector(".th-zahnrad")) return;
    const b = document.createElement("button");
    b.type = "button";
    b.className = "th-zahnrad " + (klasse || "");
    b.title = "Einstellungen";
    b.setAttribute("aria-label", "Einstellungen");
    b.setAttribute("aria-haspopup", "dialog");
    b.setAttribute("aria-expanded", "false");
    b.setAttribute("aria-controls", "th-fenster");
    b.innerHTML = ZAHNRAD;
    b.addEventListener("click", e => { e.stopPropagation(); if (fenster && !fenster.hidden && ausloeser === b) schliessen(false); else oeffnen(b); });
    ziel.appendChild(b);
  }
  function einbauen() {
    knopf(document.querySelector(".top .cmd"), "th-terminal");
    knopf(document.querySelector("#globus .gk-kopf"), "gk-knopf th-globus");
    document.addEventListener("click", e => { if (fenster && !fenster.hidden && !fenster.contains(e.target)) schliessen(false); });
    document.addEventListener("keydown", e => { if (e.key === "Escape" && fenster && !fenster.hidden) { schliessen(true); e.stopPropagation(); } }, true);
    window.addEventListener("resize", () => schliessen(false));
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", einbauen); else setTimeout(einbauen, 0);

  return { aktuell: () => aktuell, karteObjekt: () => karteObj, setzen, modi: () => MODI.map(m => m.id), farbe, wert, karte, stil, einbauen };
})();
