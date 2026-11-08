"use strict";
/* ---------- Meldungen: gemeinsame Regeln für Terminal (HDL) und Weltkugel ----------
   Ein Symbol je Meldungstyp (Form), das Alter bestimmt die Farbe. Das Alter wird beim Anzeigen aus dem Datum der Quelle
   gerechnet (nicht beim Abruf), damit auch eine ältere Seite abgelaufene Meldungen selbst ausblendet.
   Fenster: 3 Tage (Vorgabe), Reiter 7 und 14 Tage. Themen (Bereiche) bekommen eigene Reiter und erscheinen nur dort. */
const MLD = (() => {
  const INK = "#07090c";
  // Typ -> [Name, Zeichnung in 16x16, Füllfarbe wird eingesetzt; Zeichen in INK]
  const TYPEN = {
    angriff:  ["Angriff",        f => `<path d="M8 1.2 15.2 14.4H.8Z" fill="${f}"/><rect x="7.2" y="5.6" width="1.6" height="4.6" fill="${INK}"/><rect x="7.2" y="11" width="1.6" height="1.6" fill="${INK}"/>`],
    sperrung: ["Sperrung",       f => `<circle cx="8" cy="8" r="7" fill="${f}"/><rect x="3.6" y="7" width="8.8" height="2" fill="${INK}"/>`],
    wetter:   ["Wetter, Pegel",  f => `<path d="M8 1.2C8 1.2 2.8 7 2.8 10.2a5.2 5.2 0 0 0 10.4 0C13.2 7 8 1.2 8 1.2Z" fill="${f}"/>`],
    streik:   ["Streik",         f => `<rect x="1.5" y="1.5" width="13" height="13" rx="2.5" fill="${f}"/><rect x="5" y="4.4" width="2" height="7.2" fill="${INK}"/><rect x="9" y="4.4" width="2" height="7.2" fill="${INK}"/>`],
    stau:     ["Stau, Verzug",   f => `<circle cx="8" cy="8" r="7" fill="${f}"/><path d="M8 4v4.4l3 1.8" fill="none" stroke="${INK}" stroke-width="1.6" stroke-linecap="round"/>`],
    unfall:   ["Unfall",         f => `<path d="M5 .9h6L15.1 5v6L11 15.1H5L.9 11V5Z" fill="${f}"/><path d="M5.2 5.2l5.6 5.6M10.8 5.2l-5.6 5.6" stroke="${INK}" stroke-width="1.6" stroke-linecap="round"/>`],
    sonst:    ["Hinweis",        f => `<circle cx="8" cy="8" r="7" fill="${f}"/><rect x="7.2" y="7" width="1.6" height="5" fill="${INK}"/><rect x="7.2" y="4" width="1.6" height="1.6" fill="${INK}"/>`]
  };
  const FARBE = { neu: "#ffb020", aktuell: "#c08a22", aelter: "#7d8794" };
  const STAND = { neu: "heute oder gestern", aktuell: "bis 3 Tage", aelter: "älter" };
  const THEMEN = { route: "Handelsrouten" };           // weitere Themen (Wahlen, Berichte ...) tragen sich hier ein und bekommen einen eigenen Reiter
  const S = { fenster: 3, thema: "alle" };
  const FENSTER = [3, 7, 14];

  const alter = d => {                                  // Tage seit dem Datum der Quelle (Kalendertage, lokal)
    const t = Date.parse((d || "").slice(0, 10) + "T00:00:00Z"); if (isNaN(t)) return null;
    const h = new Date(); return Math.round((Date.UTC(h.getFullYear(), h.getMonth(), h.getDate()) - t) / 864e5);
  };
  const stand = a => a == null ? "aelter" : a <= 1 ? "neu" : a <= 3 ? "aktuell" : "aelter";
  const alterText = d => { const a = alter(d); return a == null ? "" : a <= 0 ? "heute" : a === 1 ? "gestern" : `vor ${a} Tagen`; };
  const typ = m => TYPEN[m && m.typ] ? m.typ : "sonst";
  const svg = (t, st, px = 14) => `<svg class="mld-sym" width="${px}" height="${px}" style="width:${px}px;height:${px}px;max-width:none" viewBox="0 0 16 16" role="img" aria-label="${TYPEN[t][0]}"><title>${TYPEN[t][0]}</title>${TYPEN[t][1](FARBE[st])}</svg>`;
  const symbol = (m, px) => svg(typ(m), stand(alter(m.datum)), px);
  /* Bild für die Karte (SVG als Rastergrafik), Name mld-<typ>-<stand> */
  const bildName = (t, st) => `mld-${t}-${st}`;
  function bildLaden(map, name) {
    const [, t, st] = name.split("-"); if (!TYPEN[t] || !FARBE[st] || map.hasImage(name)) return;
    const n = 36, img = new Image(n, n);
    img.onload = () => { if (!map.hasImage(name)) map.addImage(name, img); };
    img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="${n}" height="${n}" viewBox="0 0 16 16">${TYPEN[t][1](FARBE[st])}</svg>`);
  }
  /* Liste im gewählten Fenster (neueste zuerst); Themenreiter filtert nach bereich */
  const sichtbar = (liste, fenster = S.fenster) => (liste || []).filter(m => { const a = alter(m.datum); return a != null && a <= fenster && a >= -1 && (S.thema === "alle" || (m.bereich || "route") === S.thema); })
    .sort((x, y) => (y.datum || "").localeCompare(x.datum || ""));
  const gesamt = liste => (liste || []).filter(m => { const a = alter(m.datum); return a != null && a <= 14; }).length;
  const reiter = (n = null) => {                         // Reiter: Zeitfenster (und Themen, sobald es mehrere gibt)
    const f = FENSTER.map(d => `<button type="button" class="${S.fenster === d ? "on" : ""}" data-mfenster="${d}">${d} Tage</button>`).join("");
    const th = Object.keys(THEMEN).length > 1 ? `<span class="mld-th">${["alle", ...Object.keys(THEMEN)].map(k => `<button type="button" class="${S.thema === k ? "on" : ""}" data-mthema="${k}">${k === "alle" ? "Alle" : THEMEN[k]}</button>`).join("")}</span>` : "";
    return `<div class="mld-reiter">${f}${th}${n != null ? `<span class="mld-n">${n}</span>` : ""}</div>`;
  };
  const legende = () => `<div class="mld-leg">${Object.keys(TYPEN).map(t => `<span>${svg(t, "neu", 12)}${TYPEN[t][0]}</span>`).join("")}<span class="mld-alt">Farbe: ${["neu", "aktuell", "aelter"].map(s => `<i style="background:${FARBE[s]}"></i>${STAND[s]}`).join(" ")}</span></div>`;
  /* Warnung, wenn der Abruf der Daten lange her ist oder fehlschlug */
  const banner = (abruf, fehler) => {
    const t = Date.parse(abruf || ""); const std = isNaN(t) ? null : Math.round((Date.now() - t) / 36e5);
    const alt = std == null ? "Abrufzeit unbekannt" : std > 48 ? `Abruf vor ${Math.round(std / 24)} Tagen, Daten möglicherweise veraltet` : "";
    const fe = fehler && fehler.length ? `Abruf fehlgeschlagen bei ${fehler.length} Engstelle(n); dort ältere Meldungen, gekennzeichnet` : "";
    const txt = [alt, fe].filter(Boolean).join(" · ");
    return txt ? `<p class="mld-warn">${txt}</p>` : "";
  };
  const stempel = abruf => { const t = Date.parse(abruf || ""); if (isNaN(t)) return ""; const h = Math.round((Date.now() - t) / 36e5); return h < 1 ? "Abruf eben" : h < 48 ? `Abruf vor ${h} Std.` : `Abruf vor ${Math.round(h / 24)} Tagen`; };
  /* Klick auf einen Reiter; liefert true, wenn behandelt */
  function klick(t) {
    const b = t.closest && t.closest("[data-mfenster],[data-mthema]"); if (!b) return false;
    if (b.dataset.mfenster) S.fenster = +b.dataset.mfenster; else S.thema = b.dataset.mthema;
    return true;
  }
  return { TYPEN, FARBE, S, alter, stand, alterText, typ, svg, symbol, bildName, bildLaden, sichtbar, gesamt, reiter, legende, banner, stempel, klick };
})();
