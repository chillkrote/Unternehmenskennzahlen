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

/* ---------- Politik & Wahlen: Bereich des Terminals (Reiter POL); Darstellung liegt als Entwurf zur Freigabe vor ---------- */
const POL = (() => {
  const viewUeb = () => `<div class="grid">${panel({ code: "POL", titel: "Politik & Wahlen", sub: "in Vorbereitung", body: `
    <p>Dieser Bereich ist angelegt; die Darstellung (Regierungen und Wahlkalender, Wer regiert und wann wird gewählt, Regionen) liegt als Entwurf mit Varianten zur Freigabe vor und wird danach gebaut.</p>
    <p class="n">Geplante freie Quellen: Wikidata (Staats- und Regierungschefs, Parteien), ParlGov (Ausrichtung der Parteien), V-Dem und Weltbank-Governance-Indikatoren, Bundeswahlleiterin, DAWUM (Umfragen Deutschland). Offene Datenfelder stehen in <code>app/OFFENE_DATENFELDER.md</code>.</p>
    ${typeof GLOBUS !== "undefined" ? `<p><a class="flink" href="#globus-politik">◉ Weltkugel, Darstellung Politik &amp; Wahlen</a></p>` : ""}` })}</div>`;
  return { viewUeb };
})();
