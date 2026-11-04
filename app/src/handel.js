/* ---------- Handel: Bereich des Terminals (Reiter HDL) und Datenbasis der Weltkugel-Darstellung "Handel" ----------
   Daten (eingebettet von build.py):
     handel-daten  data/handel.json   UN Comtrade, je Land die 15 größten Export- und Importpartner (handel_abruf.py)
     welt-daten    data/welt.json     Weltbank-Kennzahlen aller Länder inkl. Zollsätzen, Eurostat-Stromhandel, Wirtschaftsräume (welt_daten.py)
     routen-daten  data/routen.json   Haupthandelsrouten, Engstellen, Drehkreuze (routen.py)
     news-daten    data/news_routen.json  echte Meldungen zu Störungen an Engstellen (GDELT oder Google News, news_routen.py)
   Ansichten: h-ueb (Überblick), h-laender (alle Länder), h-routen (Routen und Engstellen), h-strom (Stromhandel).
   Läuft vor dem Hauptskript; nutzt dessen Hilfsfunktionen (panel, esc, f0, f1, sicherUrl) erst zur Laufzeit. */
"use strict";
const HDL = (() => {
  let H = null, W = null, R = null, N = null;
  const S = { sort: { k: "export_welt", ab: false }, kont: "alle" };
  const DN = (() => { try { return new Intl.DisplayNames(["de"], { type: "region" }); } catch { return null; } })();
  const name = iso => { if (iso === "XK") return "Kosovo"; try { return (DN && DN.of(iso)) || iso; } catch { return iso; } };
  const mrd = v => v == null ? "–" : f1.format(v / 1e9);
  const pct = (v, n = 1) => v == null ? "–" : (n ? f1 : f0).format(v) + " %";
  const letzter = (iso, k) => { const l = W && W.laender[iso] && W.laender[iso][k]; return l && l.length ? l[l.length - 1] : null; };
  const datumDe = d => (d || "").slice(0, 10).split("-").reverse().join(".");
  const roh = id => { try { return JSON.parse(document.getElementById(id).textContent); } catch { return null; } };

  function init() {
    H = (d => d && d.laender ? d : null)(roh("handel-daten"));
    W = (d => d && d.laender ? d : null)(roh("welt-daten"));
    R = (d => d && d.korridore ? d : null)(roh("routen-daten"));
    N = (d => d && d.meldungen ? d : null)(roh("news-daten"));
    return !!H;
  }
  const da = () => !!H;
  const meta = () => H ? `${Object.keys(H.laender).length} Länder · UN Comtrade · Abruf ${datumDe(H.abruf)}` : "";
  /* Zollsatz eines Landes: Weltbank (angewandter Satz, einfacher Durchschnitt aller Waren); für die USA zusätzlich die effektive
     Belastung aus Zolleinnahmen ÷ Warenimporten, weil die Zölle seit 2025 weit über dem letzten Weltbank-Jahr liegen */
  function zoll(iso) {
    const e = letzter(iso, "zoll_einfach"), g = letzter(iso, "zoll_gewichtet");
    const out = { einfach: e ? e[1] : null, gewichtet: g ? g[1] : null, jahr: e ? e[0] : g ? g[0] : null, effektiv: null };
    if (iso === "US" && W && W.us_zoll_effektiv && W.us_zoll_effektiv.werte.length) { const l = W.us_zoll_effektiv.werte; out.effektiv = { wert: l[l.length - 1][1], zeit: l[l.length - 1][0] }; }
    return out;
  }
  const saldo = iso => { const h = H && H.laender[iso]; return h && h.export_welt != null && h.import_welt != null ? h.export_welt - h.import_welt : null; };
  const meldungen = () => N ? N.meldungen : {};
  const knoten = id => R ? R.knoten.find(k => k.id === id) : null;
  const globusLink = form => typeof GLOBUS !== "undefined" ? `<a class="flink" href="#globus-${form}">◉ Auf der Weltkugel zeigen</a>` : "";
  const chips = (l, attr, akt) => `<div class="chips" style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px">${l.map(([k, t]) => `<button type="button" class="chip" ${attr}="${esc(k)}" aria-pressed="${k === akt}">${esc(t)}</button>`).join("")}</div>`;
  const KONT = [["alle", "Alle"], ["Europe", "Europa"], ["Asia", "Asien"], ["Africa", "Afrika"], ["North America", "Nordamerika"], ["South America", "Südamerika"], ["Oceania", "Ozeanien"]];
  const kontVon = iso => (W && W.kontinente && W.kontinente[iso]) || null;
  function laenderZeilen() {
    return Object.entries(H.laender).map(([iso, h]) => {
      const z = zoll(iso), xb = letzter(iso, "exporte_bip");
      return { iso, name: name(iso), jahr: h.jahr, export_welt: h.export_welt, import_welt: h.import_welt, saldo: saldo(iso), zoll: z.einfach, zollg: z.gewichtet, zjahr: z.jahr,
        xbip: xb ? xb[1] : null, xp: (h.export || [])[0], mp: (h.import || [])[0], kont: kontVon(iso) };
    });
  }

  /* ----- F1 Überblick ----- */
  function viewUeb() {
    if (!H) return keineDaten();
    const z = laenderZeilen().filter(r => r.export_welt);
    const top = [...z].sort((a, b) => b.export_welt - a.export_welt).slice(0, 15);
    const tab = l => `<div class="scroll"><table class="kzt"><thead><tr><th style="text-align:left">Land</th><th>Exporte</th><th>Importe</th><th>Saldo</th><th>Zoll Ø</th><th>Jahr</th></tr></thead><tbody>${l.map(r =>
      `<tr><td style="text-align:left;font-family:var(--sans)">${esc(r.name)}</td><td>${mrd(r.export_welt)}</td><td>${mrd(r.import_welt)}</td><td class="${r.saldo >= 0 ? "pos" : "neg"}">${r.saldo > 0 ? "+" : ""}${mrd(r.saldo)}</td><td>${r.iso === "US" && zoll("US").effektiv ? `${pct(zoll("US").effektiv.wert)}*` : pct(r.zoll)}</td><td class="n">${esc(r.jahr)}</td></tr>`).join("")}</tbody></table></div>`;
    const ueber = [...z].filter(r => r.saldo != null).sort((a, b) => b.saldo - a.saldo);
    const us = W && W.us_zoll_effektiv;
    const stoer = Object.entries(meldungen()).map(([id, l]) => ({ k: knoten(id), m: l[0], n: l.length })).filter(x => x.k).sort((a, b) => (b.m.datum || "").localeCompare(a.m.datum || ""));
    return `<div class="grid">
      ${panel({ code: "HDL", titel: "Größte Exportländer", sub: "Warenhandel, Mrd. USD laut Meldung des Landes", body: tab(top), fuss: `UN Comtrade (Abruf ${datumDe(H.abruf)}). Zoll Ø = angewandter Zollsatz, einfacher Durchschnitt aller Waren (Weltbank, letztes verfügbares Jahr); * USA: effektive Belastung ${us ? esc(us.werte[us.werte.length - 1][0]) : ""}, Zolleinnahmen ÷ Warenimporte. ${globusLink("handel")}` })}
      ${panel({ code: "SAL", titel: "Überschüsse und Defizite", sub: "Saldo im Warenhandel, Mrd. USD", breite: "w6", body: tab(ueber.slice(0, 8).concat(ueber.slice(-8).reverse())), fuss: "Oben die acht größten Überschüsse, unten die acht größten Defizite." })}
      ${panel({ code: "STÖ", titel: "Störungen an Engstellen", sub: N ? `Meldungen der letzten ${N.tage} Tage, Abruf ${esc(N.abruf.replace("T", " "))}` : "keine Meldungen geladen", breite: "w6", body: stoer.length ? `<ul class="hliste">${stoer.map(x => `<li><b>${esc(x.k.name)}</b> <span class="n">${esc(x.n)} Meldung${x.n > 1 ? "en" : ""}</span><br><a class="flink" href="${esc(sicherUrl(x.m.url))}" target="_blank" rel="noopener">${esc(x.m.titel)}</a> <span class="n">${esc(x.m.quelle)} · ${esc(datumDe(x.m.datum))}</span></li>`).join("")}</ul>` : `<p class="n">Zurzeit keine passenden Meldungen.</p>`, fuss: `Originaltitel und Link, gefunden über ${esc(N ? N.quelle.split(" (")[0] : "GDELT")}; Titel nennt die Engstelle und eine Störung. Keine eigene Bewertung.` })}
      ${us ? panel({ code: "ZOL", titel: "Zollbelastung der USA", sub: "Zolleinnahmen ÷ Warenimporte, je Quartal", breite: "w6", body: usZollGrafik(us), fuss: `Abgeleitet, nicht amtlich veröffentlicht. ${esc(us.quelle)}. <a class="flink" href="${esc(us.url)}" target="_blank" rel="noopener">FRED</a>` }) : ""}</div>`;
  }
  function usZollGrafik(us) {
    const l = us.werte.slice(-16), mx = Math.max(...l.map(x => x[1]), 1), Wd = 640, Hh = 150, bw = Wd / l.length;
    return `<svg viewBox="0 0 ${Wd} ${Hh + 24}" role="img" aria-label="Effektive Zollbelastung der USA">${l.map((x, i) => { const h = x[1] / mx * Hh; return `<rect x="${i * bw + 3}" y="${Hh - h}" width="${bw - 6}" height="${h}" fill="var(--amber)"><title>${esc(x[0])}: ${f1.format(x[1])} %</title></rect>${i % 2 === l.length % 2 || i === l.length - 1 ? `<text x="${i * bw + bw / 2}" y="${Hh + 14}" text-anchor="middle" style="font-size:10px">${esc(x[0].replace("-Q", " Q"))}</text>` : ""}${i === l.length - 1 || x[1] === mx ? `<text x="${i * bw + bw / 2}" y="${Hh - h - 4}" text-anchor="middle" style="font-size:11px;fill:var(--ink)">${f1.format(x[1])}</text>` : ""}`; }).join("")}</svg>`;
  }

  /* ----- F2 Länder ----- */
  function viewLaender() {
    if (!H) return keineDaten();
    let z = laenderZeilen();
    if (S.kont !== "alle") z = z.filter(r => r.kont === S.kont);
    const k = S.sort.k, ab = S.sort.ab ? 1 : -1;
    z.sort((a, b) => k === "name" ? a.name.localeCompare(b.name, "de") * (S.sort.ab ? 1 : -1) * -1 : ((a[k] == null) - (b[k] == null)) || ((a[k] || 0) - (b[k] || 0)) * ab);
    const sp = [["name", "Land"], ["export_welt", "Exporte"], ["import_welt", "Importe"], ["saldo", "Saldo"], ["zoll", "Zoll Ø"], ["zollg", "Zoll gew."], ["xbip", "Exp. % BIP"]];
    const kopf = sp.map(([s, t]) => `<th${s === "name" ? ' style="text-align:left"' : ""}><button type="button" class="sortk" data-hsort="${s}">${t}${S.sort.k === s ? (S.sort.ab ? " ▲" : " ▼") : ""}</button></th>`).join("") + "<th style=\"text-align:left\">Größter Exportpartner</th><th style=\"text-align:left\">Größter Importpartner</th><th>Jahr</th>";
    const rows = z.map(r => `<tr><td style="text-align:left;font-family:var(--sans)">${esc(r.name)}</td><td>${mrd(r.export_welt)}</td><td>${mrd(r.import_welt)}</td><td class="${r.saldo == null ? "" : r.saldo >= 0 ? "pos" : "neg"}">${r.saldo == null ? "–" : (r.saldo > 0 ? "+" : "") + mrd(r.saldo)}</td>
      <td title="${r.zjahr ? "Weltbank " + r.zjahr : ""}">${pct(r.zoll)}</td><td>${pct(r.zollg)}</td><td>${pct(r.xbip, 0)}</td>
      <td style="text-align:left;font-family:var(--sans)">${r.xp ? `${esc(name(r.xp[0]))} <span class="n">${mrd(r.xp[1])}</span>` : "–"}</td><td style="text-align:left;font-family:var(--sans)">${r.mp ? `${esc(name(r.mp[0]))} <span class="n">${mrd(r.mp[1])}</span>` : "–"}</td><td class="n">${esc(r.jahr)}</td></tr>`).join("");
    return `<div class="grid">${panel({ code: "LND", titel: "Handel aller Länder", sub: `${z.length} Länder · Warenhandel Mrd. USD`, body: chips(KONT, "data-hkont", S.kont) + `<div class="scroll"><table class="kzt"><thead><tr>${kopf}</tr></thead><tbody>${rows}</tbody></table></div>`,
      fuss: `Exporte FOB, Importe meist CIF, je laut Meldung des Landes an UN Comtrade. Zollsätze: Weltbank WDI (angewandter Satz, einfacher bzw. handelsgewichteter Durchschnitt aller Waren, letztes verfügbares Jahr, Spalte im Tooltip); aktuelle Sonderzölle seit 2025 sind darin nicht enthalten (siehe Überblick für die USA). Exporte in % des BIP: Waren und Dienstleistungen, Weltbank. ${globusLink("handel")}` })}</div>`;
  }

  /* ----- F3 Routen und Engstellen ----- */
  const TRAEGER = { see: "Schiff", binnen: "Binnenschiff", bahn: "Bahn", strasse: "Straße", luft: "Luftfracht" };
  function viewRouten() {
    if (!R) return `<div class="grid">${panel({ code: "RTE", titel: "Routen", body: `<p class="n">Keine Routendaten. <code>python3 app/routen.py</code></p>` })}</div>`;
    const m = meldungen();
    const eng = R.knoten.filter(k => k.art === "engstelle").sort((a, b) => ((m[b.id] || []).length - (m[a.id] || []).length) || a.stufe - b.stufe || a.name.localeCompare(b.name, "de"));
    const nutzen = id => R.korridore.filter(k => k.engstellen.includes(id)).map(k => k.name);
    const etab = `<div class="scroll"><table class="kzt"><thead><tr><th style="text-align:left">Engstelle</th><th style="text-align:left">Träger</th><th style="text-align:left">Rolle</th><th style="text-align:left">Hauptrouten</th><th style="text-align:left">Aktuelle Meldung</th></tr></thead><tbody>${eng.map(k => { const l = m[k.id] || [];
      return `<tr><td style="text-align:left;font-family:var(--sans)">${l.length ? "⚠ " : ""}${esc(k.name)}</td><td style="text-align:left">${esc(TRAEGER[k.traeger] || k.traeger)}</td><td style="text-align:left;font-family:var(--sans)">${esc(k.rolle)}</td><td style="text-align:left;font-family:var(--sans)" class="n">${esc(nutzen(k.id).join(", ") || "–")}</td>
        <td style="text-align:left;font-family:var(--sans)">${l.length ? `<a class="flink" href="${esc(sicherUrl(l[0].url))}" target="_blank" rel="noopener">${esc(l[0].titel)}</a> <span class="n">${esc(l[0].quelle)} · ${esc(datumDe(l[0].datum))}${l.length > 1 ? ` · ${l.length - 1} weitere` : ""}</span>` : `<span class="n">–</span>`}</td></tr>`; }).join("")}</tbody></table></div>`;
    const ktab = `<div class="scroll"><table class="kzt"><thead><tr><th style="text-align:left">Hauptroute</th><th style="text-align:left">Träger</th><th>km</th><th style="text-align:left">Engstellen</th><th style="text-align:left">Hinweis</th></tr></thead><tbody>${R.korridore.map(k =>
      `<tr><td style="text-align:left;font-family:var(--sans)">${esc(k.name)}</td><td style="text-align:left">${esc(TRAEGER[k.traeger])}${k.schematisch ? ' <span class="n">schematisch</span>' : ""}</td><td>${f0.format(k.km)}</td><td style="text-align:left;font-family:var(--sans)">${esc(k.engstellen.map(id => (knoten(id) || {}).name || id).join(", ") || "–")}</td><td style="text-align:left;font-family:var(--sans)" class="n">${esc(k.hinweis)}</td></tr>`).join("")}</tbody></table></div>`;
    return `<div class="grid">${panel({ code: "ENG", titel: "Engstellen", sub: `${eng.length} Engstellen · ⚠ = aktuelle Meldung zu einer Störung`, body: etab, fuss: `Meldungen: ${N ? `${esc(N.quelle)}, Abruf ${esc(N.abruf.replace("T", " "))}, letzte ${N.tage} Tage` : "nicht geladen"}. Lage und Auswahl der Engstellen von Hand (app/geo/routen/knoten.csv). ${globusLink("handel")}` })}
      ${panel({ code: "RTE", titel: "Hauptrouten", sub: `${R.korridore.length} Achsen auf See, Schiene, Straße und in der Luft`, body: ktab, fuss: `Seewege berechnet über das Seewegenetz ${esc(R.quellen.seewege)}; Bahn, Straße und Luft schematisch (Stationen verbunden bzw. Großkreis). Mengen je Route liegen frei nicht vor.` })}</div>`;
  }

  /* ----- F4 Stromhandel ----- */
  function viewStrom() {
    const s = W && W.strom;
    if (!s || !s.paare) return `<div class="grid">${panel({ code: "STR", titel: "Stromhandel", body: `<p class="n">Keine Stromdaten. <code>python3 app/welt_daten.py</code></p>` })}</div>`;
    const paare = Object.entries(s.paare).map(([k, [v, art]]) => { const [a, b] = k.split(">"); return { a, b, v, art }; }).sort((x, y) => y.v - x.v);
    const netto = {}; paare.forEach(p => { netto[p.a] = (netto[p.a] || 0) + p.v; netto[p.b] = (netto[p.b] || 0) - p.v; });
    const nl = Object.entries(netto).sort((a, b) => b[1] - a[1]);
    const twh = v => f1.format(v / 1000);
    return `<div class="grid">${panel({ code: "STR", titel: "Größte Stromflüsse zwischen Ländern", sub: `${s.jahr}, TWh, Richtung Ausfuhrland → Einfuhrland`, breite: "w6", body: `<div class="scroll"><table class="kzt"><thead><tr><th style="text-align:left">von</th><th style="text-align:left">nach</th><th>TWh</th></tr></thead><tbody>${paare.slice(0, 30).map(p =>
      `<tr><td style="text-align:left;font-family:var(--sans)">${esc(name(p.a))}</td><td style="text-align:left;font-family:var(--sans)">${esc(name(p.b))}</td><td>${twh(p.v)}${p.art === "spiegel" ? "*" : ""}</td></tr>`).join("")}</tbody></table></div>`, fuss: `* nur Einfuhrmeldung des Ziellandes. ${esc(s.quelle)}. <a class="flink" href="${esc(s.url)}" target="_blank" rel="noopener">Eurostat</a>` })}
      ${panel({ code: "NET", titel: "Nettosaldo je Land", sub: `${s.jahr}, TWh, positiv = Nettoexporteur (nur Flüsse mit europäischen Meldeländern)`, breite: "w6", body: `<div class="scroll"><table class="kzt"><tbody>${nl.map(([iso, v]) => `<tr><td style="text-align:left;font-family:var(--sans)">${esc(name(iso))}</td><td class="${v >= 0 ? "pos" : "neg"}">${v > 0 ? "+" : ""}${twh(v)}</td></tr>`).join("")}</tbody></table></div>`, fuss: `Außerhalb Europas gibt es keine freie bilaterale Quelle ohne Schlüssel; dort zeigt die Weltkugel nur den Nettosaldo (Ember). ${globusLink("handel")}` })}</div>`;
  }
  const keineDaten = () => `<div class="grid">${panel({ code: "HDL", titel: "Handel", body: `<p class="n">Noch keine Handelsdaten. <code>python3 app/handel_abruf.py</code> und <code>python3 app/welt_daten.py</code>, danach <code>python3 app/build.py</code>.</p>` })}</div>`;

  function klick(t) {
    const g = a => { const e = t.closest && t.closest("[" + a + "]"); return e ? e.getAttribute(a) : null; };
    let v;
    if ((v = g("data-hsort")) != null) { S.sort = { k: v, ab: S.sort.k === v ? !S.sort.ab : v === "name" }; render(); return true; }
    if ((v = g("data-hkont")) != null) { S.kont = v; render(); return true; }
    return false;
  }
  return { init, da, meta, viewUeb, viewLaender, viewRouten, viewStrom, klick, zoll, saldo, name, daten: () => ({ H, W, R, N }) };
})();

/* ---------- Politik & Wahlen: Bereich des Terminals (Reiter POL) ----------
   Daten: politik-daten = data/politik.json (politik_daten.py: Wikidata, Wikipedia-Wahlkalender, Bundeswahlleiterin, DAWUM).
   Ansichten: p-ueb (Regierungen), p-wahlen (Wahlkalender), p-de (Deutschland: Bundestag, Umfragen, Länder),
   p-parl (Parlamente aller Staaten, gerade gewählt), p-glied (Gliedstaaten der Bundesstaaten). */
const POL = (() => {
  let P = null;
  const lade = () => { if (P === null) { try { P = JSON.parse(document.getElementById("politik-daten").textContent); } catch { P = false; } } return P; };
  const AUSR = { links: ["links", "#d9534f"], "mitte-links": ["Mitte-links", "#e8968f"], mitte: ["Mitte", "#d8c27a"], "mitte-rechts": ["Mitte-rechts", "#8fb3e0"], rechts: ["rechts", "#3d6fb6"] };
  const name = iso => HDL.name(iso);
  const datum = d => /^\d{4}-\d{2}-\d{2}$/.test(d) ? d.split("-").reverse().join(".") : /^\d{4}-\d{2}$/.test(d) ? `${d.slice(5)}/${d.slice(0, 4)}` : d;
  const jahr = String(new Date().getFullYear());
  const welt = f => typeof GLOBUS !== "undefined" ? `<p><a class="flink" href="#globus-${f}">◉ Auf der Weltkugel zeigen</a></p>` : "";
  const leer = () => `<div class="grid">${panel({ code: "POL", titel: "Politik & Wahlen", sub: "keine Daten", body: `<p class="n">Keine Politikdaten im Build (app/politik_daten.py).</p>` })}</div>`;
  const ausr = r => { const a = r && AUSR[r.ausrichtung]; return a ? `<span style="display:inline-block;width:9px;height:9px;border-radius:2px;background:${a[1]};margin-right:5px"></span>${a[0]}` : `<span class="n">ohne Zuordnung</span>`; };
  function viewUeb() {
    const d = lade(); if (!d) return leer();
    const bip = iso => { const W = HDL.daten().W, l = W && W.laender[iso] && W.laender[iso].bip_usd; return l && l.length ? l[l.length - 1][1] : 0; };
    const laender = Object.keys(d.regierungen).sort((a, b) => bip(b) - bip(a)).slice(0, 40);
    const zaehl = {}; Object.values(d.regierungen).forEach(r => { const k = r.ausrichtung || "ohne"; zaehl[k] = (zaehl[k] || 0) + 1; });
    const zeile = iso => { const r = d.regierungen[iso], h = r.regierungschef || r.staatsoberhaupt, w = (d.wahlen[iso] || []).filter(x => x.datum !== jahr)[0];
      return `<tr><td style="text-align:left">${esc(name(iso))}</td><td style="text-align:left;font-family:var(--sans)">${esc(h ? h.name : "–")}</td><td style="text-align:left" class="n">${esc(h ? h.partei_kurz || h.partei : "")}</td><td style="text-align:left">${ausr(r)}</td><td class="n">${w ? esc(datum(w.datum)) : "–"}</td></tr>`; };
    return `<div class="grid">${panel({ code: "REG", titel: "Regierungen der 40 größten Volkswirtschaften", sub: `Wikidata, Abruf ${esc(d.abruf)}`, breite: "w8", body: `<table class="tab"><thead><tr><th style="text-align:left">Land</th><th style="text-align:left">Regierungschef</th><th style="text-align:left">Partei</th><th style="text-align:left">Ausrichtung</th><th>nächste Wahl</th></tr></thead><tbody>${laender.map(zeile).join("")}</tbody></table>`,
        fuss: "Ausrichtung: Mittelwert der Wikidata-Angaben „politische Ausrichtung“ (P1387) der Partei des Regierungschefs, ohne Partei die des Staatsoberhaupts. Monarchien, Einparteienstaaten und Parteilose bleiben ohne Zuordnung. Nach BIP (Weltbank) geordnet." })}
      ${panel({ code: "AUS", titel: "Ausrichtung weltweit", sub: `${Object.keys(d.regierungen).length} Staaten`, breite: "w4", body: `<table class="tab"><tbody>${Object.keys(AUSR).map(k => `<tr><td style="text-align:left">${ausr({ ausrichtung: k })}</td><td>${f0.format(zaehl[k] || 0)}</td></tr>`).join("")}<tr><td style="text-align:left" class="n">ohne Zuordnung</td><td>${f0.format(zaehl.ohne || 0)}</td></tr></tbody></table>${welt("politik")}`,
        fuss: "Quelle Wikidata (CC0), von Freiwilligen gepflegt; Stand und Abweichungen bitte an der Quelle prüfen." })}</div>`;
  }
  function viewWahlen() {
    const d = lade(); if (!d) return leer();
    const alle = Object.entries(d.wahlen).flatMap(([iso, l]) => l.filter(w => w.datum !== jahr).map(w => ({ ...w, iso }))).sort((a, b) => a.datum.localeCompare(b.datum));
    return `<div class="grid">${panel({ code: "WAH", titel: "Nationale Wahlen der nächsten zwölf Monate", sub: `${alle.length} Termine in ${new Set(alle.map(w => w.iso)).size} Ländern`, breite: "w12",
      body: `<table class="tab"><thead><tr><th style="text-align:left">Datum</th><th style="text-align:left">Land</th><th style="text-align:left">Wahl</th><th style="text-align:left">Regierung jetzt</th></tr></thead><tbody>${alle.map(w => `<tr><td style="text-align:left" class="n">${esc(datum(w.datum))}</td><td style="text-align:left">${esc(name(w.iso))}</td><td style="text-align:left;font-family:var(--sans)">${w.url ? `<a class="flink" href="${esc(sicherUrl(w.url))}" target="_blank" rel="noopener">${esc(w.was)}</a>` : esc(w.was)}</td><td style="text-align:left">${ausr(d.regierungen[w.iso])}</td></tr>`).join("")}</tbody></table>${welt("politik")}`,
      fuss: "Wikipedia, „national electoral calendar“ (CC BY-SA 4.0). Monat statt Tag, wo der Termin noch nicht feststeht. Nachwahlen sind nicht enthalten." })}</div>`;
  }
  function viewDe() {
    const d = lade(); if (!d || !d.deutschland) return leer();
    const de = d.deutschland, bt = de.bundestag, um = (de.umfragen || {}).parlamente || {}, lr = de.landesregierungen || {}, btw = de.btw25 || {};
    const balken = l => l.map(([p, v]) => `<tr><td style="text-align:left">${esc(p)}</td><td>${f1.format(v)} %</td></tr>`).join("");
    const laender = Object.entries(lr).sort((a, b) => a[0].localeCompare(b[0]));
    const nameVon = code => ({ "DE-BW": "Baden-Württemberg", "DE-BY": "Bayern", "DE-BE": "Berlin", "DE-BB": "Brandenburg", "DE-HB": "Bremen", "DE-HH": "Hamburg", "DE-HE": "Hessen", "DE-MV": "Mecklenburg-Vorpommern", "DE-NI": "Niedersachsen", "DE-NW": "Nordrhein-Westfalen", "DE-RP": "Rheinland-Pfalz", "DE-SL": "Saarland", "DE-SN": "Sachsen", "DE-ST": "Sachsen-Anhalt", "DE-SH": "Schleswig-Holstein", "DE-TH": "Thüringen" })[code] || code;
    const sitze = bt.sitze.reduce((a, s) => a + s[1], 0);
    return `<div class="grid">${panel({ code: "BT", titel: "Bundestag", sub: esc(bt.stand), breite: "w4", body: `<table class="tab"><tbody>${bt.sitze.map(([p, k]) => `<tr><td style="text-align:left">${esc(p)}${bt.regierung.includes(p) ? " <span class=\"n\">Regierung</span>" : ""}</td><td>${k}</td></tr>`).join("")}<tr><td style="text-align:left"><b>Summe</b></td><td><b>${sitze}</b></td></tr></tbody></table>`,
        fuss: `Sitzverteilung nach der Wahl, Quelle <a class="flink" href="${esc(bt.quelle)}" target="_blank" rel="noopener">Bundeswahlleiterin</a>.` })}
      ${um.Bundestag ? panel({ code: "UMF", titel: "Jüngste Umfrage Bundestag", sub: `${esc(um.Bundestag.institut)}, ${esc(datum(um.Bundestag.datum))}`, breite: "w4", body: `<table class="tab"><tbody>${balken(um.Bundestag.werte)}</tbody></table>`, fuss: `DAWUM (${esc(de.umfragen.lizenz)}), ${esc(um.Bundestag.befragte || "")} Befragte.` }) : ""}
      ${panel({ code: "LDR", titel: "Länder", sub: "Regierungschef, jüngste Landtagsumfrage", breite: "w12", body: `<table class="tab"><thead><tr><th style="text-align:left">Land</th><th style="text-align:left">Regierungschef</th><th style="text-align:left">Partei</th><th style="text-align:left">BTW 2025 stärkste Partei</th><th style="text-align:left">jüngste Landtagsumfrage</th></tr></thead><tbody>
        ${laender.map(([c, l]) => { const n = nameVon(c), w = btw[n] || {}, s = Object.entries(w)[0], u = um[n]; return `<tr><td style="text-align:left">${esc(n)}</td><td style="text-align:left;font-family:var(--sans)">${esc(l.regierungschef)}</td><td style="text-align:left" class="n">${esc((l.parteien || []).join(", "))}</td><td style="text-align:left">${s ? `${esc(s[0])} ${f1.format(s[1])} %` : "–"}</td><td style="text-align:left">${u ? `${u.werte.slice(0, 3).map(([p, v]) => `${esc(p)} ${f0.format(v)}`).join(" · ")} <span class="n">${esc(u.institut)}, ${esc(datum(u.datum))}</span>` : "–"}</td></tr>`; }).join("")}</tbody></table>${welt("politik")}`,
        fuss: "Regierungschefs laut Wikidata; Bundestagswahl 2025 nach Ländern (Zweitstimmen, Bundeswahlleiterin, Datenlizenz Deutschland 2.0); Umfragen DAWUM (ODbL). Ergebnisse der letzten Landtagswahlen und Koalitionen sind noch offen." })}</div>`;
  }
  /* Parlamente aller Staaten (parlamente-daten = data/parlamente.json aus parlamente_daten.py) */
  let PA = null;
  const ladePA = () => { if (PA === null) { try { PA = JSON.parse(document.getElementById("parlamente-daten").textContent); } catch { PA = false; } } return PA; };
  const TYP = { einkammer: "Einkammer", unterhaus: "Unterhaus", oberhaus: "Oberhaus", kammer: "Kammer" };
  const sitze = k => k.aktuell && k.aktuell.sitze && k.aktuell.sitze.length ? { l: k.aktuell.sitze.map(g => [g.partei, g.sitze, g.farbe, g.regierung]), q: "Wikipedia" }
    : k.wahl && k.wahl.sitze && k.wahl.sitze.length ? { l: k.wahl.sitze.filter(x => x[1] != null).map(x => [x[0], x[1], x[2], null]), q: "IPU" } : null;
  const balkenSitze = s => { const n = s.l.reduce((a, g) => a + g[1], 0) || 1;
    return `<span style="display:inline-flex;width:120px;height:9px;border-radius:2px;overflow:hidden;vertical-align:middle;background:#2a313b">${s.l.map(g => `<i title="${esc(g[0])} ${g[1]}" style="display:block;width:${(g[1] / n * 100).toFixed(2)}%;background:${esc(g[2] || "#8b95a3")}"></i>`).join("")}</span>`; };
  const neuChip = j => j ? ` <span style="color:#ffa828" title="Wahl am ${esc(datum(j.datum))}, Ergebnis ${esc(j.ergebnis)}">● neu gewählt</span>` : "";
  const leerPA = () => `<div class="grid">${panel({ code: "PARL", titel: "Parlamente", sub: "keine Daten", body: `<p class="n">Keine Parlamentsdaten im Build (app/parlamente_daten.py).</p>` })}</div>`;
  function kammerZeile(iso, k, region) {
    const s = sitze(k), gr = s ? [...s.l].filter(g => g[0] !== "vakant").sort((a, b) => b[1] - a[1])[0] : null, n = s ? s.l.reduce((a, g) => a + g[1], 0) : 0, reg = s ? s.l.filter(g => g[3]).reduce((a, g) => a + g[1], 0) : 0;
    const st = k.stimmen && k.stimmen.parteien ? k.stimmen.parteien.filter(p => p.prozent != null)[0] : null;
    return `<tr><td style="text-align:left">${region ? esc(region) : esc(name(iso))}${neuChip(k.juengst)}</td><td style="text-align:left;font-family:var(--sans)">${esc(k.name || "")} <span class="n">${esc(TYP[k.typ] || "")}</span></td><td>${k.sitze_soll ? f0.format(k.sitze_soll) : n ? f0.format(n) : "–"}</td>
      <td style="text-align:left">${s ? balkenSitze(s) : "–"}</td><td style="text-align:left">${gr ? `${esc(gr[0])} ${f0.format(gr[1])}` : "–"}</td><td>${reg && n ? f0.format(reg / n * 100) + " %" : "–"}</td>
      <td style="text-align:left" class="n">${st ? `${esc(st.partei)} ${f1.format(st.prozent)} %` : "–"}</td><td class="n">${k.letzte_wahl ? esc(datum(k.letzte_wahl.datum)) : "–"}</td><td class="n">${k.naechste_wahl ? esc(datum(k.naechste_wahl.datum)) : "–"}</td><td class="n">${s ? s.q : ""}</td></tr>`;
  }
  const KOPF = `<thead><tr><th style="text-align:left">Land</th><th style="text-align:left">Kammer</th><th>Sitze</th><th style="text-align:left">Verteilung</th><th style="text-align:left">stärkste Fraktion</th><th>Regierungslager</th><th style="text-align:left">größte Partei, Stimmen</th><th>letzte Wahl</th><th>nächste Wahl</th><th>Quelle</th></tr></thead>`;
  function juengstPanel(a) {
    const d = lade() || {}, kal = Object.entries(d.wahlen_juengst || {}).flatMap(([iso, l]) => l.map(w => ({ ...w, iso })));
    const nah = (x, y) => Math.abs(Date.parse(x) - Date.parse(y)) <= 3 * 864e5;
    const l = [...kal.map(w => ({ datum: w.datum, wo: name(w.iso), was: w.was, url: w.url, st: ((a.juengst || []).find(j => j.iso === w.iso && !j.region && nah(j.datum, w.datum)) || {}).ergebnis || "" })),
      ...(a.juengst || []).filter(j => j.region || !kal.some(w => w.iso === j.iso && nah(w.datum, j.datum))).map(j => ({ datum: j.datum, wo: j.region ? `${name(j.iso)}, ${j.region_name}` : name(j.iso), was: j.kammer, url: j.url, st: j.ergebnis }))]
      .sort((x, y) => y.datum.localeCompare(x.datum));
    return panel({ code: "NEU", titel: `Gerade gewählt (letzte ${a.schwelle_tage} Tage)`, sub: `${l.length} Wahlen`, breite: "w12",
      body: l.length ? `<table class="tab"><thead><tr><th style="text-align:left">Datum</th><th style="text-align:left">Wo</th><th style="text-align:left">Wahl</th><th style="text-align:left">Ergebnis in der Quelle</th></tr></thead><tbody>${l.map(w => `<tr><td style="text-align:left" class="n">${esc(datum(w.datum))}</td><td style="text-align:left">${esc(w.wo)}</td><td style="text-align:left;font-family:var(--sans)">${w.url ? `<a class="flink" href="${esc(sicherUrl(w.url))}" target="_blank" rel="noopener">${esc(w.was)}</a>` : esc(w.was)}</td><td style="text-align:left;color:${w.st === "liegt vor" ? "#7cc4ff" : "#ffa828"}">${esc(w.st || "–")}</td></tr>`).join("")}</tbody></table>` : `<p class="n">Keine Wahlen in den letzten ${a.schwelle_tage} Tagen.</p>`,
      fuss: `Schwelle ${a.schwelle_tage} Tage: so lange dauern in den meisten Staaten amtliches Endergebnis und konstituierende Sitzung (Deutschland: Art. 39 GG). Nationaler Wahlkalender (Wikipedia) und Kammern (IPU Parline, Wikipedia-Infoboxen der Parlamente und Gliedstaaten).` });
  }
  function viewParl() {
    const a = ladePA(); if (!a) return leerPA();
    const bip = iso => { const W = HDL.daten().W, l = W && W.laender[iso] && W.laender[iso].bip_usd; return l && l.length ? l[l.length - 1][1] : 0; };
    const laender = Object.keys(a.staaten).sort((x, y) => bip(y) - bip(x) || name(x).localeCompare(name(y)));
    const n = laender.reduce((s, i) => s + a.staaten[i].kammern.length, 0), mit = laender.reduce((s, i) => s + a.staaten[i].kammern.filter(k => sitze(k)).length, 0);
    return `<div class="grid">${juengstPanel(a)}${panel({ code: "PARL", titel: "Nationale Parlamente", sub: `${laender.length} Staaten, ${n} Kammern, ${mit} mit Sitzverteilung · Abruf ${esc(datum(a.abruf))}`, breite: "w12",
      body: `<table class="tab">${KOPF}<tbody>${laender.map(i => a.staaten[i].kammern.map(k => kammerZeile(i, k)).join("")).join("")}</tbody></table>${welt("politik")}`,
      fuss: `Sitzverteilung: heutige Zusammensetzung laut Infobox des Wikipedia-Artikels der Kammer (CC BY-SA 4.0); fehlt sie, Sitze nach der letzten Wahl laut IPU Parline (${esc(((a.quellen || {}).ipu || {}).name || "")}). Regierungslager nur, wo die Infobox Regierung und Opposition trennt. Stimmenanteil laut Infobox des Wahlartikels. Nach BIP (Weltbank) geordnet.` })}</div>`;
  }
  let GL_LAND = "US";
  function viewGlied() {
    const a = ladePA(); if (!a) return leerPA();
    const laender = Object.keys(a.gliedstaaten || {}).sort((x, y) => name(x).localeCompare(name(y)));
    if (!laender.length) return leerPA();
    if (!laender.includes(GL_LAND)) GL_LAND = laender[0];
    const g = (a.gliedstaaten || {})[GL_LAND] || {};
    const chips = laender.map(i => `<button type="button" class="key" data-pglland="${esc(i)}" aria-pressed="${i === GL_LAND}" style="margin:0 4px 4px 0">${esc(name(i))} <span class="n">${Object.keys(a.gliedstaaten[i]).length}</span></button>`).join("");
    const zeilen = Object.entries(g).sort((x, y) => (x[1].name_de || x[1].name).localeCompare(y[1].name_de || y[1].name, "de")).map(([c, x]) => {
      const ch = x.regierungschef, koal = (x.koalition || []).length ? ` · Regierungslager ${esc(x.koalition.join(", "))}` : "", seit = ch && ch.seit ? ` · im Amt seit ${esc(ch.seit.split("-").reverse().join("."))}` : "", kopf = `<tr><td style="text-align:left" colspan="10" class="n" style="padding-top:6px">${esc(x.name_de || x.name)} · Regierungschef ${esc(ch ? ch.name : "–")}${ch && (ch.partei_kurz || ch.partei) ? ` (${esc(ch.partei_kurz || ch.partei)})` : ""}${seit}${koal}</td></tr>`;
      return kopf + (x.kammern.length ? x.kammern.map(k => kammerZeile(GL_LAND, k, x.name_de || x.name)).join("") : `<tr><td colspan="10" class="n" style="text-align:left">kein Parlament mit Wikipedia-Infobox gefunden</td></tr>`); }).join("");
    return `<div class="grid">${panel({ code: "GLD", titel: "Gliedstaaten und Regionen", sub: `${laender.length} Staaten · ${Object.keys(g).length} Gliedstaaten in ${esc(name(GL_LAND))}`, breite: "w12",
      body: `<div style="margin-bottom:8px">${chips}</div>${(a.rolle || {})[GL_LAND] ? `<p class="n" style="margin:0 0 6px">Amt „Regierungschef“ in dieser Ebene: ${esc(a.rolle[GL_LAND])}</p>` : ""}<table class="tab">${KOPF}<tbody>${zeilen}</tbody></table>${welt("politik")}`,
      fuss: "Gliedstaaten, Regionen und Regierungschefs mit Amtsantritt laut Wikidata (CC0, P150/P300/P6/P580/P102); Regierungslager laut Infobox (Regierung/Opposition); Parlamente und Wahltermine laut Infobox des Wikipedia-Artikels (CC BY-SA 4.0). Gliedstaaten ohne gepflegte Infobox bleiben leer (siehe app/OFFENE_DATENFELDER.md)." })}</div>`;
  }
  function klick(t) {
    const e = t.closest && t.closest("[data-pglland]"); if (!e) return false;
    GL_LAND = e.getAttribute("data-pglland"); render(); return true;
  }
  return { viewUeb, viewWahlen, viewDe, viewParl, viewGlied, klick };
})();

/* ---------- Börse: Zinsen, Devisen, Rohstoffe (Reiter BÖR, F6) aus data/boerse_welt.json (boerse_welt.py) ---------- */
const FIN = (() => {
  let B = null;
  const lade = () => { if (B === null) { try { B = JSON.parse(document.getElementById("boerse-welt-daten").textContent); } catch { B = false; } } return B; };
  const vz = v => v == null ? "–" : `<span class="${v >= 0 ? "pos" : "neg"}">${v > 0 ? "+" : ""}${f1.format(v * 100)} %</span>`;
  function view() {
    const d = lade(); if (!d) return `<div class="grid">${panel({ code: "ZIN", titel: "Zinsen, Devisen, Rohstoffe", sub: "keine Daten", body: `<p class="n">Keine Daten im Build (app/boerse_welt.py).</p>` })}</div>`;
    const nm = i => i === "XM" ? "Euroraum" : HDL.name(i);
    const letzt = l => l[l.length - 1];
    const tab = (o, titel) => `<table class="tab"><thead><tr><th style="text-align:left">Land</th><th>${titel}</th><th>vor 1 J.</th><th>Stand</th></tr></thead><tbody>${Object.entries(o).sort((a, b) => letzt(b[1])[1] - letzt(a[1])[1]).map(([i, l]) => `<tr><td style="text-align:left">${esc(nm(i))}</td><td>${f2.format(letzt(l)[1])} %</td><td class="n">${l.length > 12 ? f2.format(l[l.length - 13][1]) + " %" : "–"}</td><td class="n">${esc(letzt(l)[0])}</td></tr>`).join("")}</tbody></table>`;
    return `<div class="grid">${panel({ code: "LZI", titel: "Leitzinsen", sub: `${Object.keys(d.leitzins).length} Zentralbanken`, breite: "w4", body: tab(d.leitzins, "Leitzins"), fuss: `<a class="flink" href="${esc(d.quellen.leitzins.url)}" target="_blank" rel="noopener">${esc(d.quellen.leitzins.name)}</a>` })}
      ${panel({ code: "R10", titel: "Rendite 10-jähriger Staatsanleihen", sub: `${Object.keys(d.rendite10).length} Länder`, breite: "w4", body: tab(d.rendite10, "Rendite"), fuss: esc(d.quellen.rendite10.name) })}
      ${panel({ code: "DEV", titel: "Devisen und Rohstoffe", sub: `Abruf ${esc(d.abruf)}`, breite: "w4", body: `<table class="tab"><thead><tr><th style="text-align:left">1 EUR =</th><th>Kurs</th><th>zum USD lfd. J.</th></tr></thead><tbody>${Object.entries(d.devisen).map(([w, x]) => `<tr><td style="text-align:left">${esc(w)}</td><td>${f2.format(x.je_eur)}</td><td>${w === "USD" ? `EUR ${vz(-x.eur_ytd)}` : vz(x.usd_ytd)}</td></tr>`).join("")}</tbody></table>
        <table class="tab" style="margin-top:10px"><thead><tr><th style="text-align:left">Rohstoff</th><th>Preis</th><th>lfd. J.</th><th>1 J.</th></tr></thead><tbody>${(d.rohstoffe || []).map(r => `<tr><td style="text-align:left">${esc(r.name)} <span class="n">${esc(r.einheit)}</span></td><td>${f2.format(r.wert)}</td><td>${vz(r.ytd)}</td><td>${vz(r.r1j)}</td></tr>`).join("")}</tbody></table>${typeof GLOBUS !== "undefined" ? `<p><a class="flink" href="#globus-boerse">◉ Auf der Weltkugel zeigen</a></p>` : ""}`,
        fuss: "EZB-Referenzkurse; Rohstoffe über FRED (EIA, IMF). Gold ohne Schlüssel nicht frei verfügbar." })}</div>`;
  }
  return { view };
})();
