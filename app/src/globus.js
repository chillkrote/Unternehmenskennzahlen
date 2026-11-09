/* ---------- Weltkugel: alternative Oberfläche des Terminals ----------
   Karte: MapLibre GL (BSD-3, im Build eingebettet) in Globus-Projektion. Grundkarte aus OpenStreetMap-Daten über OpenFreeMap
   (Vektorkacheln, kostenlos, ohne Schlüssel); ohne Netz oder bei gesperrten Kacheln eine einfache Karte aus den eingebetteten
   Natural-Earth-Ländergrenzen. Schriften für Beschriftungen sind eingebettet (Noto Sans, Bereich 0–255).

   Ebenen: jede Darstellung auf der Karte ist eine Ebene in EBENEN (Länder, Unternehmen, später Handelsströme, Lieferketten).
   Eine Ebene bringt ihre Quellen und Schichten selbst mit und wird nach jedem Wechsel der Grundkarte neu angelegt.
   Neue Ebenen: GLOBUS.ebene({ id, name, gruppe, an, quellen(map), schichten(map, vor), klick?(e, map), vorrang? }).
   vorrang: Klick und Tooltip gehen vor den Unternehmenspunkten an diese Ebene (Unternehmensnetz, app/src/netz.js).

   Läuft nach dem Hauptskript des Terminals im selben Dokument und nutzt dessen Teile weiter:
   UNT.viewProfil (Profil im Fenster), UNT.viewVgl (Vergleich), VWL (Länderdaten), BOE (Indizes), render/gehe (Hash-Navigation). */
"use strict";
const GLOBUS = (() => {
  const roh = id => { try { return JSON.parse(document.getElementById(id).textContent); } catch { return null; } };
  const LAENDER = roh("geo-laender") || { type: "FeatureCollection", features: [] };
  const SITZE = roh("geo-sitze") || { spalten: [], zeilen: [] };
  const GLYPHEN = roh("geo-glyphen") || {};
  const HANDEL = (d => d && d.laender ? d : null)(roh("handel-daten"));   // vom Terminal eingebettet (Bereich HDL)
  const WELT = (d => d && d.laender ? d : null)(roh("welt-daten"));       // Weltbank-Kennzahlen, Zölle, Stromhandel, Wirtschaftsräume
  const ROUTEN = (d => d && d.korridore ? d : null)(roh("routen-daten")); // Haupthandelsrouten, Engstellen, Drehkreuze
  const NEWS = (d => d && d.meldungen ? d : null)(roh("news-daten"));     // echte Meldungen zu Störungen an Engstellen (GDELT oder Google News)
  const TABELLE = (d => d && d.zeilen ? d : null)(roh("geo-tabelle"));    // gesamte Unternehmenstabelle mit Punkt (tabelle_geo.csv)
  const STUFEN = roh("geo-stufen") || { nachbarn: {}, strom: {} };     // Nachbarländer und Nettostrom (handel_stufen.py)
  const DN = (() => { try { return new Intl.DisplayNames(["de"], { type: "region" }); } catch { return null; } })();
  // kurze Namen für Beschriftungen auf der Karte
  const KURZNAME = { CN: "China", US: "USA", GB: "UK", AE: "VAE", RU: "Russland", KR: "Südkorea", KP: "Nordkorea", CD: "DR Kongo", CF: "Zentralafrika", BA: "Bosnien-H.", DO: "Dom. Rep." };
  const landKurz = iso => KURZNAME[iso] || landName(iso);
  const landName = iso => { const f = NACH_ISO[iso]; if (f) return f.properties.name; try { return (DN && DN.of(iso)) || iso; } catch { return iso; } };
  const NACH_ISO = {};
  LAENDER.features.forEach(f => { if (!NACH_ISO[f.properties.iso]) NACH_ISO[f.properties.iso] = f; });   // erster Treffer = Hauptfläche (Australien vor Nebengebieten)
  /* ----- Zoomstufen -----
     1 (ganz weit, Zoom < 2,6): Handel von Kontinent zu Kontinent. 2 (2,6 bis 5): die drei größten Export- und Importströme je Land.
     3 (ab 5): Unternehmen nach Sitz, Handel mit jedem Nachbarland, Nettostrom. Übergänge sind weiche Ein-/Ausblendungen (Deckkraft nach Zoom). */
  const ZG = [2.6, 5];
  const stufeVon = z => z < ZG[0] ? 1 : z < ZG[1] ? 2 : 3;
  const KONT = [["EU", "Europa", "Europe", [15, 50], "#5b8def"], ["AS", "Asien", "Asia", [90, 40], "#e0a458"], ["AF", "Afrika", "Africa", [20, 5], "#c76f5a"],
    ["NA", "Nordamerika", "North America", [-100, 45], "#5fb88a"], ["SA", "Südamerika", "South America", [-60, -15], "#b07fd6"], ["OC", "Ozeanien", "Oceania", [135, -25], "#4cb8c4"]];
  const KONT_NAME = Object.fromEntries(KONT.map(k => [k[0], k[1]]));
  // erster Treffer gewinnt (Australien hat Nebengebiete mit gleichem Code); Gebiete ohne eigene Fläche als Handelspartner ergänzt
  const KONT_VON = { GI: "EU", TK: "OC" }; LAENDER.features.forEach(f => { const k = KONT.find(x => x[2] === f.properties.kontinent); if (k && !(f.properties.iso in KONT_VON)) KONT_VON[f.properties.iso] = k[0]; });
  // bilaterale Ströme "Exportland>Importland" -> USD: Meldung des Exportlandes, fehlt das Paar dort, die Spiegelmeldung des Importlandes
  const PAAR = new Map(), SPIEGEL = new Set();
  if (HANDEL) {
    for (const [iso, h] of Object.entries(HANDEL.laender)) (h.export || []).forEach(([q, v]) => PAAR.set(iso + ">" + q, v));
    for (const [iso, h] of Object.entries(HANDEL.laender)) (h.import || []).forEach(([q, v]) => { const k = q + ">" + iso; if (!PAAR.has(k)) { PAAR.set(k, v); SPIEGEL.add(k); } });
  }
  const KMAT = {}; KONT.forEach(a => { KMAT[a[0]] = {}; KONT.forEach(b => { KMAT[a[0]][b[0]] = 0; }); });
  PAAR.forEach((v, k) => { const [x, y] = k.split(">"), a = KONT_VON[x], b = KONT_VON[y]; if (a && b) KMAT[a][b] += v; });
  // Anteil der aufgeführten Ströme an den gemeldeten Gesamtexporten (nur Länder mit eigener Meldung)
  const KABD = {}; if (HANDEL) KONT.forEach(([k]) => { let g = 0, e = 0; for (const [iso, h] of Object.entries(HANDEL.laender)) if (KONT_VON[iso] === k && h.export_welt) { g += h.export_welt; e += (h.export || []).reduce((a, x) => a + x[1], 0); } KABD[k] = g ? e / g : null; });
  const KURZ = { EU: "Eur", AS: "Asi", AF: "Afr", NA: "NAm", SA: "SAm", OC: "Oze" };
  // Berichtsjahre der Länderströme (jüngstes gemeldetes Jahr je Land)
  const HANDEL_JAHRE = (() => { if (!HANDEL) return ""; const j = Object.values(HANDEL.laender).map(h => h.jahr).filter(Boolean), n = {}; j.forEach(x => { n[x] = (n[x] || 0) + 1; });
    const top = Object.entries(n).sort((a, b) => b[1] - a[1]).map(x => x[0]); return top.length > 1 ? `${top[1] < top[0] ? top[1] : top[0]}/${top[1] < top[0] ? top[0] : top[1]}` : (top[0] || ""); })();
  const nachbarnVon = iso => STUFEN.nachbarn[iso] || [];
  /* Kontinent der Besucherin bzw. des Besuchers: Zeitzone, dann Sprachregion des Browsers, sonst Europa (die IP-Abfrage ist nur auf Knopfdruck) */
  function besucherKontinent() {
    let tz = ""; try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ""; } catch { tz = ""; }
    const v = tz.split("/")[0], ort = tz.split("/").slice(1).join("/");
    if (v === "Europe") return "EU";
    if (v === "Africa") return "AF";
    if (v === "Indian") return /Antananarivo|Mauritius|Reunion|Comoro|Mayotte|Mahe/.test(ort) ? "AF" : "AS";
    if (v === "Asia") return "AS";
    if (v === "Australia" || (v === "Pacific" && !/Honolulu|Johnston/.test(ort))) return "OC";
    if (v === "Pacific") return "NA";
    if (v === "Atlantic") return /Reykjavik|Azores|Madeira|Canary|Faroe/.test(ort) ? "EU" : /Bermuda/.test(ort) ? "NA" : /Cape_Verde|St_Helena/.test(ort) ? "AF" : "SA";
    if (v === "America") return /Argentina|Buenos_Aires|Sao_Paulo|Bogota|Lima|Santiago|Caracas|La_Paz|Montevideo|Asuncion|Guayaquil|Cayenne|Paramaribo|Guyana|Bahia|Fortaleza|Recife|Manaus|Belem|Cuiaba|Campo_Grande|Porto_Velho|Rio_Branco|Punta_Arenas|Maceio|Araguaina|Noronha|Boa_Vista|Santarem|Eirunepe|Cordoba|Catamarca|Jujuy|Mendoza|Rosario|Cuiaba/.test(ort) ? "SA" : "NA";
    if (/^(US|Canada|Mexico)$/.test(v)) return "NA";
    const reg = ((navigator.language || "").split("-")[1] || "").toUpperCase();
    return KONT_VON[reg] || "EU";
  }
  // ein Beschriftungspunkt je Land (sonst beschriftet MapLibre jedes Kachelstück der Fläche)
  const LAENDER_PUNKTE = { type: "FeatureCollection", features: LAENDER.features.map(f => ({ type: "Feature", geometry: { type: "Point", coordinates: [f.properties.lx, f.properties.ly] },
    properties: { iso: f.properties.iso, name: f.properties.name, einwohner: f.properties.einwohner || 0 } })) };
  const namensFarbe = () => ["case", ["in", ["get", "iso"], ["literal", S.auswahl]], "#ffa828", "#8b95a3"];
  const VWL_GEO = iso => ({ GB: "UK", GR: "EL" }[iso] || iso);       // Eurostat-/OECD-Kürzel im VWL-Datensatz
  const OSM_URL = "https://tiles.openfreemap.org/planet";
  /* ----- Darstellungsformen -----
     Fünf Formen mit je drei Zoomstufen; jede Ebene nennt die Formen, in denen sie erscheint (formen), sonst erscheint sie immer.
     Börse, Unternehmen und Politik nach den freigegebenen Varianten 1A, 2A, 3A (Robin, 04.11.2026). */
  const FORMEN = [["handel", "Handel", "h-ueb"], ["vwl", "Volkswirtschaft", "v-ueb"], ["boerse", "Börse & Finanzen", "b-ueb"], ["unternehmen", "Unternehmen", "u-ueb"], ["politik", "Politik & Wahlen", "p-ueb"]];
  const ENTWURF = {};
  const S = { bm: "index", gut: null, form: "handel", auswahl: [], raum: null, buendnis: null, region: null, polAnsicht: "wahlen", u1: "anzahl", k1: "top15", netzOffen: false, handelMitNetz: false, stufe: 1, kont: null, kont2: null, nutzer: false, land: null, handel: "beide", nurLand: true, grund: null, offen: [], aktiv: null, z: 10, hover: null, ebenenOffen: false };
  let map = null, klassisch = null, imGlobus = false, hinweisTimer = 0, osmFehler = 0, osmGeladen = false;

  /* ----- Unternehmen mit Sitz-Koordinaten -----
     Zwei Quellen: Unternehmen des Terminals (Sitz aus sitz_geo.csv, Fenster mit Profil und Kennzahlen) und die übrigen Zeilen der
     Unternehmenstabelle (tabelle_geo.csv, Fenster mit Stammdaten). Ist nur das Land bekannt (genau = 0), gibt es keinen eigenen
     Punkt (er würde einen Ort vortäuschen), sondern je Land einen Ring in der Landesmitte mit der Anzahl; er öffnet die Liste. */
  let PUNKTE = [];       // GeoJSON-Features je Unternehmen
  const STAMM = {};      // Unternehmens-ID bzw. Schlüssel -> Zeile der Tabelle, für alle Unternehmen ohne Kennzahlen im Terminal
  const NUR_LAND = {};   // ISO -> [{ id, name, branche, art }] Unternehmen, deren Sitz nur auf Landesebene bekannt ist
  function tabZeile(z) {
    const o = {}; TABELLE.spalten.forEach((s, j) => { o[s] = TABELLE.listen[s] ? TABELLE.listen[s][z[j]] : z[j]; });
    if (TABELLE.schlank) o.k = o.id;          // API-Fassung: Schlüssel = ID, Details kommen beim Öffnen aus /companies/{id}
    return o;
  }
  function punkteBauen() {
    const sp = SITZE.spalten, i = n => sp.indexOf(n);
    PUNKTE = [];
    const terminal = new Set(), punkt = (lon, lat, p) => PUNKTE.push({ type: "Feature", geometry: { type: "Point", coordinates: [lon, lat] }, properties: p });
    // art "t": Kennzahlen im Terminal; "s": nur Stammdaten (Platzhalter-Eintrag des Terminals oder nur in der Tabelle)
    const firmaProps = f => ({ id: f.id, name: UNT.kurzName(f.name).replace(/ Aktiengesellschaft$/, ""), branche: UNT.brName(f.branche), notiert: f.notiert ? 1 : 0, art: f.stub ? "s" : "t" });
    for (const z of SITZE.zeilen) {
      const f = UNT.nachId(z[i("id")]);
      if (!f) continue;                              // nur Unternehmen, die das Terminal kennt
      terminal.add(f.id);
      punkt(z[i("lon")], z[i("lat")], { ...firmaProps(f), ort: z[i("ort")], land: z[i("land")] || f.land_code || "", genau: 1, unsicher: z[i("quelle")] === "gleif-name" ? 1 : 0 });
    }
    if (!TABELLE) return;
    for (const r of TABELLE.zeilen.map(tabZeile)) {
      const f = r.id && UNT.nachId(r.id);
      if (f && terminal.has(f.id)) continue;        // schon mit genauerem Sitz aus sitz_geo.csv
      if (!f || f.stub) STAMM[f ? f.id : r.k] = r;
      const p = f ? { ...firmaProps(f), land: r.land || f.land_code || "" } : { id: r.k, name: r.name, branche: r.branche ? UNT.brName(r.branche) : "", land: r.land, notiert: r.notiert === "ja" ? 1 : 0, art: "s" };
      if (f) terminal.add(f.id);
      if (r.genau) punkt(r.lon, r.lat, { ...p, ort: r.ort || r.sitz, genau: 1, unsicher: 0 });
      else if (NACH_ISO[p.land]) (NUR_LAND[p.land] = NUR_LAND[p.land] || []).push(p);
    }
  }
  function landRingDaten() {
    const f = Object.entries(NUR_LAND).filter(([iso]) => !(S.land && S.nurLand) || iso === S.land).map(([iso, l]) => ({ type: "Feature",
      geometry: { type: "Point", coordinates: [NACH_ISO[iso].properties.lx, NACH_ISO[iso].properties.ly] }, properties: { iso, n: l.length } }));
    return { type: "FeatureCollection", features: f };
  }
  const firmenImLand = iso => UNT.unternehmenAlle().filter(f => (f.land_code || "") === iso);
  const stammImLand = iso => Object.values(STAMM).filter(r => r.land === iso);
  const nurLandAnzahl = () => Object.values(NUR_LAND).reduce((a, l) => a + l.length, 0);
  const ohneSitz = iso => { const mit = new Set(PUNKTE.map(p => p.properties.id)); return firmenImLand(iso).filter(f => !mit.has(f.id)); };

  /* ----- Ebenen ----- */
  const EBENEN = [];
  // Später registrierte Ebenen (z. B. netz.js) sofort anlegen, sobald der Stil steht; isStyleLoaded() ist auch während des Kachelladens false
  let stilBereit = false;
  function ebene(def) { EBENEN.push({ an: true, gruppe: "Karte", ...def }); if (map && stilBereit) ebeneAnlegen(EBENEN[EBENEN.length - 1]); ebenenListe(); }
  const vorBeschriftung = () => { const l = (map.getStyle().layers || []).find(x => x.type === "symbol" && x.id.startsWith("osm-")); return l ? l.id : undefined; };
  function ebeneAnlegen(e) {
    if (!e.quellen) return;
    try { e.quellen(map); e.schichten(map, vorBeschriftung()); sichtbar(e); if (stilBereit && S.netzOffen) ueberlagerung(); }
    catch (err) { console.warn("Ebene", e.id, err); }
  }
  /* Handelsebenen treten zurück, solange ein Unternehmensnetz offen ist (sonst liegen Kontinent-/Länderbögen über den Netzbögen);
     der Schalter "Handel zusätzlich zeigen" in der Legende hebt das auf */
  const handelVerdraengt = id => (id === "kontinente" || id === "handel") && S.netzOffen && !S.handelMitNetz;
  // ansicht: Politik hat zwei Ansichten (Wahlen, src/wahlen.js; Regierungen, Ebene "politik"); eine Ebene mit ansicht erscheint nur in ihrer
  const ebeneAn = e => e.an && !handelVerdraengt(e.id) && (!e.formen || e.formen.includes(S.form)) && (!e.ansicht || e.ansicht === S.polAnsicht);
  function sichtbar(e) { (map.getStyle().layers || []).filter(l => l.metadata && l.metadata.ebene === e.id).forEach(l => map.setLayoutProperty(l.id, "visibility", ebeneAn(e) ? "visible" : "none")); if (e.id === "handel") richtungAnwenden(); if (e.id === "kontinente") kontAnwenden(); }
  // bei offenem Unternehmensnetz: Punkte und Namen der Sitze zurücknehmen, damit sie die Netzpunkte nicht verdecken
  function ueberlagerung() {
    if (!map || !stilBereit) return;
    EBENEN.filter(e => e.id === "kontinente" || e.id === "handel").forEach(e => map.getLayer(e.id === "handel" ? "handel-x" : "k-x") && sichtbar(e));
    const n = !!S.netzOffen;
    if (map.getLayer("unt-name")) map.setLayoutProperty("unt-name", "visibility", n ? "none" : "visible");
    if (map.getLayer("unt-land-zahl")) map.setLayoutProperty("unt-land-zahl", "visibility", n ? "none" : "visible");
    if (map.getLayer("unt-punkt")) map.setPaintProperty("unt-punkt", "circle-opacity", n ? .35 : 1);
    if (map.getLayer("unt-punkt")) map.setPaintProperty("unt-punkt", "circle-stroke-opacity", n ? .35 : 1);
    legendeKarte();
  }
  const schicht = (ebeneId, def, vor) => map.addLayer({ ...def, metadata: { ebene: ebeneId } }, vor);

  /* Länderflächen: Auswahl und Hover über feature-state, Beschriftung mit deutschem Namen */
  ebene({ id: "laender", name: "Länder", gruppe: "Karte", an: true,
    quellen: m => { m.addSource("laender", { type: "geojson", data: LAENDER }); m.addSource("laender-punkte", { type: "geojson", data: LAENDER_PUNKTE }); },
    schichten: (m, vor) => {
      const osm = S.grund === "osm";
      // einfache Karte: die Länderflächen sind die Landmasse
      if (!osm) schicht("laender", { id: "laender-land", type: "fill", source: "laender", paint: { "fill-color": "#19202a" } }, vor);
      schicht("laender", { id: "laender-flaeche", type: "fill", source: "laender", paint: {
        "fill-color": ["case", ["boolean", ["feature-state", "gewaehlt"], false], "#ffa828", "#8fa3bd"],
        // gewähltes Land: kräftig auf dem Globus, beim Hineinzoomen fast durchsichtig, damit Karte und Punkte lesbar bleiben
        "fill-opacity": ["interpolate", ["linear"], ["zoom"],
          3, ["case", ["boolean", ["feature-state", "gewaehlt"], false], osm ? .24 : .3, ["boolean", ["feature-state", "hover"], false], .12, 0],
          6.5, ["case", ["boolean", ["feature-state", "gewaehlt"], false], .05, ["boolean", ["feature-state", "hover"], false], .03, 0]] } }, vor);
      schicht("laender", { id: "laender-linie", type: "line", source: "laender", paint: {
        "line-color": ["case", ["boolean", ["feature-state", "gewaehlt"], false], "#ffa828", osm ? "rgba(0,0,0,0)" : "#3a4655"],
        "line-width": ["case", ["boolean", ["feature-state", "gewaehlt"], false], 1.8, .6] } }, vor);
      schicht("laender", { id: "laender-name", type: "symbol", source: "laender-punkte", maxzoom: 5.5,
        layout: { "text-field": ["get", "name"], "text-font": ["Noto Sans Regular"], "text-size": ["interpolate", ["linear"], ["zoom"], 1, 9, 4, 13],
          "text-max-width": 7, "text-padding": 4, "symbol-sort-key": ["-", 0, ["get", "einwohner"]] },
        paint: { "text-color": namensFarbe(), "text-halo-color": "#07090c", "text-halo-width": 1.2, "text-opacity": ["interpolate", ["linear"], ["zoom"], 2.2, 0, 3, 1] } });
    } });

  /* Unternehmen nach Sitz: Cluster, die beim Hineinzoomen in kleinere Gruppen und Einzelpunkte zerfallen */
  ebene({ id: "unternehmen", name: "Unternehmen (Sitz)", gruppe: "Unternehmen", an: true, formen: ["unternehmen", "vwl", "boerse"],
    quellen: m => {
      m.addSource("unternehmen", { type: "geojson", data: punkteDaten(), cluster: true, clusterRadius: 46, clusterMaxZoom: 11,
        clusterProperties: { notiert: ["+", ["get", "notiert"]], kennzahlen: ["+", ["case", ["==", ["get", "art"], "t"], 1, 0]] } });
      m.addSource("unt-land", { type: "geojson", data: landRingDaten() });
    },
    schichten: (m) => {
      const ab = ZG[1];   // erst in Stufe 3 sichtbar
      // Ring in der Landesmitte: Unternehmen, deren Sitz nur auf Landesebene bekannt ist (Klick öffnet die Liste)
      schicht("unternehmen", { id: "unt-land-ring", type: "circle", source: "unt-land", minzoom: ab, paint: {
        "circle-color": "rgba(7,9,12,.6)", "circle-stroke-color": "#8b95a3", "circle-stroke-width": 1.4,
        "circle-radius": ["step", ["get", "n"], 14, 50, 18, 500, 23, 2000, 28],
        "circle-opacity": ["interpolate", ["linear"], ["zoom"], ab, 0, ab + .5, 1], "circle-stroke-opacity": ["interpolate", ["linear"], ["zoom"], ab, 0, ab + .5, 1] } });
      schicht("unternehmen", { id: "unt-land-zahl", type: "symbol", source: "unt-land", minzoom: ab,
        layout: { "text-field": ["format", ["number-format", ["get", "n"], { locale: "de-DE" }], { "font-scale": 1 }, "\nohne Ort", { "font-scale": .75 }],
          "text-font": ["Noto Sans Bold"], "text-size": 11, "text-line-height": 1.05, "text-allow-overlap": true },
        paint: { "text-color": "#c3cad3" } });
      schicht("unternehmen", { id: "unt-cluster", type: "circle", source: "unternehmen", filter: ["has", "point_count"], minzoom: ab, paint: {
        "circle-color": "rgba(255,168,40,.28)", "circle-stroke-color": "#ffa828", "circle-stroke-width": 1.4,
        "circle-radius": ["step", ["get", "point_count"], 11, 5, 14, 15, 18, 40, 23, 100, 29, 250, 35, 1000, 41, 4000, 47],
        "circle-opacity": ["interpolate", ["linear"], ["zoom"], ab, 0, ab + .5, 1], "circle-stroke-opacity": ["interpolate", ["linear"], ["zoom"], ab, 0, ab + .5, 1] } });
      schicht("unternehmen", { id: "unt-anzahl", type: "symbol", source: "unternehmen", filter: ["has", "point_count"], minzoom: ab,
        layout: { "text-field": ["to-string", ["get", "point_count"]], "text-font": ["Noto Sans Bold"], "text-size": 11, "text-allow-overlap": true },
        paint: { "text-color": "#ffe2b5" } });
      // groß: im Terminal mit Kennzahlen; klein: nur Stammdaten aus der Unternehmenstabelle
      schicht("unternehmen", { id: "unt-punkt", type: "circle", source: "unternehmen", filter: ["!", ["has", "point_count"]], minzoom: ab, paint: {
        "circle-color": ["case", ["==", ["get", "notiert"], 1], "#ffa828", "#2f86dd"],
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, ["case", ["==", ["get", "art"], "t"], 4, 2.6], 10, ["case", ["==", ["get", "art"], "t"], 6.5, 4.6]],
        "circle-stroke-color": "#07090c", "circle-stroke-width": 1.2 } });
      schicht("unternehmen", { id: "unt-offen", type: "circle", source: "unternehmen", filter: ["all", ["!", ["has", "point_count"]], ["in", ["get", "id"], ["literal", S.offen.filter(x => x.art === "firma" || x.art === "stamm").map(x => x.id)]]],
        paint: { "circle-color": "rgba(0,0,0,0)", "circle-radius": 11, "circle-stroke-color": "#ffffff", "circle-stroke-width": 2 } });
      schicht("unternehmen", { id: "unt-name", type: "symbol", source: "unternehmen", filter: ["!", ["has", "point_count"]], minzoom: 7,
        layout: { "text-field": ["get", "name"], "text-font": ["Noto Sans Regular"], "text-size": 11, "text-offset": [0, 1.1], "text-anchor": "top", "text-optional": true, "text-max-width": 9 },
        paint: { "text-color": "#e8ecf1", "text-halo-color": "#07090c", "text-halo-width": 1.3 } });
    } });

  /* Handelsströme (data/handel.json, handel_abruf.py): beim gewählten Land Bögen zu den wichtigsten Partnern, Exporte grün vom Land
     weg, Importe rot zum Land hin; Breite nach Wert. Format je Land: { jahr, export_welt, import_welt, export: [[ISO2, USD], …], import: […] }.
     Vorbereitet: Lieferketten zwischen Unternehmens-IDs, z. B. { lieferketten: [{ von: "U000123", nach: "U000456", art, gut, quelle }] },
     als Bögen zwischen den Sitzen. */
  const leerFC = { type: "FeatureCollection", features: [] };
  // Verlauf von blass (Herkunft) nach kräftig (Ziel) zeigt die Richtung
  const verlauf = rgb => ["interpolate", ["linear"], ["line-progress"], 0, `rgba(${rgb},0.08)`, 1, `rgba(${rgb},0.95)`];
  // Exporte grün (durchgezogen, Verlauf blass → kräftig), Importe rot (gestrichelt), beides mit Pfeilspitzen; Seitenwahl: Exporte biegen nach links, Importe nach rechts aus
  const GRUEN = "62,207,110", ROT = "255,82,82", HEX_EXP = "#3ecf6e", HEX_IMP = "#ff5252";
  const hPfeil = m => {
    if (m.hasImage("h-pfeil")) return;
    const n = 24, data = new Uint8Array(n * n * 4);
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) { const t = (x - 5) / (n - 8), halb = (1 - t) * (n / 2 - 4); data[(y * n + x) * 4 + 3] = t >= 0 && t <= 1 && Math.abs(y - n / 2 + .5) <= halb ? 255 : 0; }
    m.addImage("h-pfeil", { width: n, height: n, data }, { sdf: true });
  };
  // Handelslinie: Export = Verlauf, Import = gestrichelt; dazu eine Pfeilschicht entlang der Linie
  function handelLinie(eb, id, quelle, imp, breite, op, extra = {}) {
    const rgb = imp ? ROT : GRUEN;
    schicht(eb, { id, type: "line", source: quelle, layout: { "line-cap": imp ? "butt" : "round" }, paint: { "line-width": breite, "line-opacity": op,
      ...(imp ? { "line-color": `rgb(${rgb})`, "line-dasharray": [2.2, 1.6] } : { "line-gradient": verlauf(rgb) }), ...extra } });
    schicht(eb, { id: id + "-pfeil", type: "symbol", source: quelle, layout: { "symbol-placement": "line", "symbol-spacing": 95, "icon-image": "h-pfeil", "icon-size": .5,
      "icon-allow-overlap": true, "icon-ignore-placement": true, "icon-rotation-alignment": "map" }, paint: { "icon-color": `rgb(${rgb})`, "icon-opacity": op } });
  }
  const HANDEL_SCHICHTEN = ["k-x", "k-m", "handel-x", "handel-m", "nb-x", "nb-m"];
  ebene({ id: "kontinente", name: "Handel der größten Volkswirtschaften bzw. Kontinente (Stufe 1)", gruppe: "Handel", an: !!HANDEL, geplant: !HANDEL, formen: ["handel"],
    quellen: m => {
      m.addSource("k-x", { type: "geojson", data: kontDaten("export"), lineMetrics: true }); m.addSource("k-m", { type: "geojson", data: kontDaten("import"), lineMetrics: true });
      m.addSource("k-pkt", { type: "geojson", data: kontPunkte() }); m.addSource("k-wert", { type: "geojson", data: kontWerte() });
      m.addSource("k15-pkt", { type: "geojson", data: k15Punkte() });
    },
    schichten: m => {
      // Länderflächen nach Kontinent eingefärbt; gewählter Kontinent (und Gegenüber) kräftiger
      schicht("kontinente", { id: "k-flaeche", type: "fill", source: "laender", paint: {
        "fill-color": ["match", ["get", "kontinent"], ...KONT.flatMap(k => [k[2], k[4]]), "#8fa3bd"],
        "fill-opacity": ["interpolate", ["linear"], ["zoom"], 2.2, kontFuell(), 2.7, 0] } }, vorBeschriftung());
      hPfeil(m);
      const breite = ["get", "w"], op = ["interpolate", ["linear"], ["zoom"], 2.1, ["case", ["get", "fokus"], 1, .55], 2.6, 0];
      handelLinie("kontinente", "k-x", "k-x", false, breite, op); handelLinie("kontinente", "k-m", "k-m", true, breite, op);
      schicht("kontinente", { id: "k-wert", type: "symbol", source: "k-wert", layout: { "text-field": ["get", "t"], "text-font": ["Noto Sans Regular"], "text-size": 11, "text-allow-overlap": false, "text-padding": 6, "symbol-sort-key": ["-", 0, ["get", "wert"]], "text-offset": ["case", ["==", ["get", "richtung"], "export"], ["literal", [0, -.8]], ["literal", [0, .8]]] },
        paint: { "text-color": ["case", ["==", ["get", "richtung"], "export"], HEX_EXP, HEX_IMP], "text-halo-color": "#07090c", "text-halo-width": 1.4, "text-opacity": ["interpolate", ["linear"], ["zoom"], 2.1, 1, 2.6, 0] } });
      // die 15 größten Volkswirtschaften (Punkt und Name), nur im Modus "15 größte"
      const op15 = ["interpolate", ["linear"], ["zoom"], 2.1, 1, 2.6, 0];
      schicht("kontinente", { id: "k15-punkt", type: "circle", source: "k15-pkt", paint: { "circle-radius": 4, "circle-color": ["case", ["get", "imKont"], "#ffa828", "#c3cad3"], "circle-stroke-color": "#07090c", "circle-stroke-width": 1.2, "circle-opacity": op15, "circle-stroke-opacity": op15 } });
      schicht("kontinente", { id: "k15-name", type: "symbol", source: "k15-pkt", layout: { "text-field": ["get", "name"], "text-font": ["Noto Sans Regular"], "text-size": 11, "text-offset": [0, .9], "text-anchor": "top", "text-optional": true },
        paint: { "text-color": ["case", ["get", "imKont"], "#ffd08a", "#c3cad3"], "text-halo-color": "#07090c", "text-halo-width": 1.3, "text-opacity": op15 } });
      schicht("kontinente", { id: "k-name", type: "symbol", source: "k-pkt", layout: { "text-field": ["get", "name"], "text-font": ["Noto Sans Regular"], "text-size": 15, "text-allow-overlap": true },
        paint: { "text-color": ["case", ["get", "gewaehlt"], "#ffa828", "#d4dbe5"], "text-halo-color": "#07090c", "text-halo-width": 1.6, "text-opacity": ["interpolate", ["linear"], ["zoom"], 2.2, 1, 2.6, 0] } });
    } });
  ebene({ id: "handel", name: "Handelsströme gewählter Länder (Stufe 2) und mit Nachbarn (Stufe 3)", gruppe: "Handel", an: !!HANDEL, geplant: !HANDEL, formen: ["handel", "vwl"],
    quellen: m => {
      m.addSource("handel-x", { type: "geojson", data: handelDaten("export"), lineMetrics: true }); m.addSource("handel-m", { type: "geojson", data: handelDaten("import"), lineMetrics: true });
      m.addSource("nb-x", { type: "geojson", data: nachbarDaten("export"), lineMetrics: true }); m.addSource("nb-m", { type: "geojson", data: nachbarDaten("import"), lineMetrics: true });
      m.addSource("strom", { type: "geojson", data: stromDaten() });
    },
    schichten: m => {
      hPfeil(m);
      const breite = ["interpolate", ["linear"], ["get", "anteil"], 0, 1, .25, 7];
      // Stufe 2: von ~2,6 bis ~5 (dann übernehmen die Nachbarländer, ohne Überblendung beider Stufen)
      const op2 = ["interpolate", ["linear"], ["zoom"], 2.6, 0, 3.2, ["case", ["get", "alle"], .28, 1], 4.4, ["case", ["get", "alle"], .28, 1], 4.9, 0];
      handelLinie("handel", "handel-x", "handel-x", false, ["case", ["get", "alle"], ["interpolate", ["linear"], ["get", "anteil"], 0, .6, .25, 2.4], breite], op2);
      handelLinie("handel", "handel-m", "handel-m", true, breite, op2);
      // Stufe 3: Nachbarländer, Export und Import als getrennte Bögen (Ausbiegung statt Versatz)
      const op3 = ["interpolate", ["linear"], ["zoom"], 4.9, 0, 5.4, 1], w3 = ["interpolate", ["linear"], ["get", "anteil"], 0, 1.5, .25, 9];
      handelLinie("handel", "nb-x", "nb-x", false, w3, op3); handelLinie("handel", "nb-m", "nb-m", true, w3, op3);
      schicht("handel", { id: "strom-text", type: "symbol", source: "strom", layout: { "text-field": ["get", "t"], "text-font": ["Noto Sans Regular"], "text-size": 11, "text-offset": [0, 1.6], "text-allow-overlap": false, "text-padding": 4, "symbol-sort-key": ["-", 0, ["abs", ["get", "netto"]]] },
        paint: { "text-color": ["case", [">=", ["get", "netto"], 0], HEX_IMP, HEX_EXP], "text-halo-color": "#07090c", "text-halo-width": 1.4, "text-opacity": ["interpolate", ["linear"], ["zoom"], 4.9, 0, 5.4, 1] } });
      richtungAnwenden();
    } });
  ebene({ id: "lieferketten", name: "Lieferketten", gruppe: "In Vorbereitung", an: false, geplant: true, formen: ["unternehmen"] });

  /* Großkreisbogen zwischen zwei Punkten; Längengrade fortlaufend, damit Bögen über die Datumsgrenze nicht quer über die Karte springen */
  function bogen(a, b, n = 64, hub = 0) {
    const r = Math.PI / 180, [l1, p1, l2, p2] = [a[0] * r, a[1] * r, b[0] * r, b[1] * r];
    const v = (l, p) => [Math.cos(p) * Math.cos(l), Math.cos(p) * Math.sin(l), Math.sin(p)];
    const A = v(l1, p1), B = v(l2, p2), w = Math.acos(Math.max(-1, Math.min(1, A[0] * B[0] + A[1] * B[1] + A[2] * B[2])));
    if (w < 1e-6) return [a, b];
    const pkt = [];
    let vorher = null;
    for (let i = 0; i <= n; i++) {
      const t = i / n, k1 = Math.sin((1 - t) * w) / Math.sin(w), k2 = Math.sin(t * w) / Math.sin(w);
      const x = k1 * A[0] + k2 * B[0], y = k1 * A[1] + k2 * B[1], z = k1 * A[2] + k2 * B[2];
      let lon = Math.atan2(y, x) / r; const lat = Math.atan2(z, Math.hypot(x, y)) / r;
      if (vorher != null) while (lon - vorher > 180) lon -= 360;
      if (vorher != null) while (vorher - lon > 180) lon += 360;
      vorher = lon; pkt.push([lon, lat]);
    }
    // Ausbiegen zur Seite (Anteil der Länge): trennt gegenläufige und gleichlaufende Bögen zwischen denselben Orten
    if (hub) {
      const dx = pkt[n][0] - pkt[0][0], dy = pkt[n][1] - pkt[0][1], len = Math.hypot(dx, dy) || 1;
      pkt.forEach((q, i) => { const k = hub * len * Math.sin(Math.PI * i / n); q[0] += -dy / len * k; q[1] = Math.max(-84, Math.min(84, q[1] + dx / len * k)); });
    }
    return pkt;
  }
  const HUB = .09;   // Ausbiegung (Anteil der Bogenlänge): Exporte links, Importe rechts von der Linie Herkunft → Ziel
  const mitte = iso => NACH_ISO[iso] ? [NACH_ISO[iso].properties.lx, NACH_ISO[iso].properties.ly] : null;
  const wertFC = f => ({ type: "FeatureCollection", features: f });
  const mrdText = v => f0.format(v / 1e9) + " Mrd.";
  // Stufe 1: Bögen vom gewählten Kontinent zu den anderen (grün: Exporte hin, rot: Importe von dort); mit Gegenüber nur dieses Paar kräftig
  function kontDaten(richtung) {
    if (!HANDEL || !S.kont) return leerFC;
    if (S.k1 === "top15") {
      const l = k15Stroeme(), mx = Math.max(1, ...l.map(x => x.v));
      return wertFC(l.filter(x => x.richtung === richtung && mitte(x.x) && mitte(x.y)).map(x => ({ type: "Feature", geometry: { type: "LineString", coordinates: bogen(mitte(x.x), mitte(x.y), 48, HUB) },
        properties: { von: x.x, nach: x.y, richtung, wert: x.v, k: 1, k15: 1, w: 1.4 + 9 * Math.sqrt(x.v / mx), fokus: true } })));
    }
    const a = S.kont, mx = Math.max(1, ...KONT.filter(k => k[0] !== a).flatMap(k => [KMAT[a][k[0]], KMAT[k[0]][a]]));
    return wertFC(KONT.filter(k => k[0] !== a).map(k => {
      const b = k[0], wert = richtung === "export" ? KMAT[a][b] : KMAT[b][a], c1 = KONT.find(x => x[0] === a)[3], c2 = k[3];
      return { type: "Feature", properties: { von: richtung === "export" ? a : b, nach: richtung === "export" ? b : a, richtung, wert, k: 1, w: 2 + 16 * Math.sqrt(wert / mx), fokus: !S.kont2 || S.kont2 === b },
        geometry: { type: "LineString", coordinates: richtung === "export" ? bogen(c1, c2, 64, HUB) : bogen(c2, c1, 64, HUB) } };
    }));
  }
  function kontWerte() {
    if (!HANDEL || !S.kont) return leerFC;
    if (S.k1 === "top15") return wertFC(k15Stroeme().slice(0, 6).filter(x => mitte(x.x) && mitte(x.y)).map(x => { const bg = bogen(mitte(x.x), mitte(x.y), 48, HUB);
      return { type: "Feature", properties: { t: `${landKurz(x.x)} → ${landKurz(x.y)} ${mrdText(x.v)}`, richtung: x.richtung, wert: x.v }, geometry: { type: "Point", coordinates: bg[Math.floor(bg.length * .5)] } }; }));
    const a = S.kont, c1 = KONT.find(x => x[0] === a)[3], f = [];
    for (const k of KONT) if (k[0] !== a && (!S.kont2 || S.kont2 === k[0])) for (const richtung of ["export", "import"]) {
      const wert = richtung === "export" ? KMAT[a][k[0]] : KMAT[k[0]][a], bg = bogen(richtung === "export" ? c1 : k[3], richtung === "export" ? k[3] : c1, 64, HUB);
      f.push({ type: "Feature", properties: { t: (richtung === "export" ? "Export " : "Import ") + mrdText(wert), richtung, wert, dy: richtung === "export" ? -.8 : .8 }, geometry: { type: "Point", coordinates: bg[Math.floor(bg.length * (richtung === "export" ? .55 : .45))] } });
    }
    return wertFC(f);
  }
  const kontPunkte = () => wertFC(KONT.filter(k => S.k1 !== "top15" || k[0] === S.kont || k[0] === S.kont2).map(k => ({ type: "Feature", properties: { name: k[1], gewaehlt: k[0] === S.kont || k[0] === S.kont2 }, geometry: { type: "Point", coordinates: k[3] } })));
  const kontFuell = () => ["case", ["==", ["get", "kontinent"], (KONT.find(k => k[0] === S.kont) || [])[2] || ""], .34, ["==", ["get", "kontinent"], (KONT.find(k => k[0] === S.kont2) || [])[2] || ""], .34, .12];
  function kontAnwenden() {
    if (!map) return;
    ["k-x", "k-m"].forEach(q => map.getSource(q) && map.getSource(q).setData(kontDaten(q === "k-x" ? "export" : "import")));
    if (map.getSource("k-pkt")) map.getSource("k-pkt").setData(kontPunkte());
    if (map.getSource("k-wert")) map.getSource("k-wert").setData(kontWerte());
    if (map.getSource("k15-pkt")) map.getSource("k15-pkt").setData(k15Punkte());
    if (map.getLayer("k-flaeche")) map.setPaintProperty("k-flaeche", "fill-opacity", ["interpolate", ["linear"], ["zoom"], 2.2, kontFuell(), 2.7, 0]);
  }
  // Stufe 2: je Land die drei größten Export- und Importströme; ohne Auswahl die drei größten Exporte aller Länder (blass)
  function handelDaten(richtung) {
    if (!HANDEL) return leerFC;
    const bauen = (iso, alle) => {
      const h = HANDEL.laender[iso]; if (!h || !h[richtung] || !mitte(iso)) return [];
      const welt = h[richtung + "_welt"] || 1, heim = mitte(iso);
      return h[richtung].slice(0, 5).filter(([p]) => mitte(p)).map(([p, wert]) => ({ type: "Feature",
        properties: { land: iso, partner: p, name: landName(p), wert, anteil: wert / welt, richtung, alle },
        geometry: { type: "LineString", coordinates: richtung === "export" ? bogen(heim, mitte(p), 40, HUB) : bogen(mitte(p), heim, 40, HUB) } }));
    };
    // nur gewählte Länder (Shift für mehrere), Export und Import gleichermaßen; ohne Auswahl keine Ströme
    if (S.form !== "handel") return leerFC;
    return wertFC(S.auswahl.flatMap(iso => bauen(iso, false)));
  }
  // Stufe 3: Handel mit jedem Nachbarland (Paare, die in keiner Meldung unter den 15 größten Partnern stehen, fehlen)
  function nachbarDaten(richtung) {
    if (!HANDEL || !S.land) return leerFC;
    const h = HANDEL.laender[S.land], welt = (h && h[richtung + "_welt"]) || 1, heim = mitte(S.land), f = [];
    for (const q of partnerStufe3(S.land)) {
      const wert = richtung === "export" ? PAAR.get(S.land + ">" + q) : PAAR.get(q + ">" + S.land);
      if (!wert || !mitte(q)) continue;
      f.push({ type: "Feature", properties: { land: S.land, partner: q, name: landName(q), wert, anteil: wert / welt, richtung, nb: nachbarnVon(S.land).includes(q) ? 1 : 0 },
        geometry: { type: "LineString", coordinates: richtung === "export" ? bogen(heim, mitte(q), 24, HUB) : bogen(mitte(q), heim, 24, HUB) } });
    }
    return wertFC(f);
  }
  // Stufe 3 (Handel): alle Nachbarn und die fünf weiteren größten Partner (Summe aus Export und Import), in der Volkswirtschaft nur Nachbarn
  function partnerStufe3(iso) {
    const nb = nachbarnVon(iso), h = HANDEL && HANDEL.laender[iso];
    if (S.form !== "handel" || !h) return nb;
    const s = {}; (h.export || []).forEach(([p, v]) => { s[p] = (s[p] || 0) + v; }); (h.import || []).forEach(([p, v]) => { s[p] = (s[p] || 0) + v; });
    return nb.concat(Object.entries(s).filter(([p]) => !nb.includes(p) && p !== iso).sort((a, b) => b[1] - a[1]).slice(0, 5).map(x => x[0]));
  }
  // Stufe 3: Nettostrom des Landes und seiner Nachbarn (Ember), nur wo es keine bilateralen Eurostat-Werte gibt
  const stromText = iso => { const s = STUFEN.strom[iso]; return s ? `Strom ${s.netto >= 0 ? "Nettoimport" : "Nettoexport"} ${f1.format(Math.abs(s.netto))} TWh` : null; };
  function stromDaten() {
    if (!S.land || !["handel", "vwl"].includes(S.form) || hatStromBilateral(S.land)) return leerFC;
    return wertFC([S.land, ...nachbarnVon(S.land)].filter(i => STUFEN.strom[i] && mitte(i)).map(i => ({ type: "Feature",
      properties: { t: `${landName(i)}\n${stromText(i)}`, netto: STUFEN.strom[i].netto }, geometry: { type: "Point", coordinates: mitte(i) } })));
  }
  function handelAktualisieren() {
    if (!map) return;
    [["handel-x", () => handelDaten("export")], ["handel-m", () => handelDaten("import")], ["nb-x", () => nachbarDaten("export")], ["nb-m", () => nachbarDaten("import")], ["strom", stromDaten]]
      .forEach(([q, f]) => { if (map.getSource(q)) map.getSource(q).setData(f()); });
    kontAnwenden(); stromAktualisieren(); vwlAnwenden(); boerseAnwenden(); politikAnwenden(); unAnwenden();
  }
  function richtungAnwenden() {
    if (!map || !map.getLayer("handel-x")) return;
    const e = EBENEN.find(x => x.id === "handel"), an = !!e && ebeneAn(e);
    const v = (ids, ok) => ids.forEach(i => { for (const l of [i, i + "-pfeil"]) if (map.getLayer(l)) map.setLayoutProperty(l, "visibility", an && ok ? "visible" : "none"); });
    v(["handel-x", "nb-x"], S.handel !== "import"); v(["handel-m", "nb-m"], S.handel !== "export");
  }
  function punkteDaten() {
    const nb = S.form === "unternehmen" && S.land ? new Set([S.land, ...nachbarnVon(S.land)]) : null;
    let f = S.land && S.nurLand ? PUNKTE.filter(p => nb ? nb.has(p.properties.land) : p.properties.land === S.land) : PUNKTE;
    if (S.form === "boerse") f = f.filter(p => p.properties.notiert === 1);
    else if (S.form === "unternehmen" && ufAktiv()) f = f.filter(p => ufPasst(p.properties));
    return { type: "FeatureCollection", features: f };
  }
  function punkteAktualisieren() {
    if (!map || !map.getSource("unternehmen")) return;
    map.getSource("unternehmen").setData(punkteDaten());
    if (map.getSource("unt-land")) map.getSource("unt-land").setData(landRingDaten());
    if (map.getLayer("unt-offen")) map.setFilter("unt-offen", ["all", ["!", ["has", "point_count"]], ["in", ["get", "id"], ["literal", S.offen.filter(x => x.art === "firma" || x.art === "stamm").map(x => x.id)]]]);
  }

  /* ===== Darstellungsformen Handel und Volkswirtschaft: Daten ===== */
  const letzter = (iso, k) => { const l = WELT && WELT.laender[iso] && WELT.laender[iso][k]; return l && l.length ? l[l.length - 1] : null; };
  const RAEUME = WELT ? WELT.raeume : [];
  const RAUM_VON = {};   // Land -> Wirtschaftsraum (ohne übergreifende Räume wie Euroraum, RCEP)
  RAEUME.filter(r => r.art !== "uebergreifend").forEach(r => r.mitglieder.forEach(i => { if (!RAUM_VON[i]) RAUM_VON[i] = r.id; }));
  const raumVon = id => RAEUME.find(r => r.id === id);
  const bipUsd = iso => { const x = letzter(iso, "bip_usd"); return x ? x[1] : NACH_ISO[iso] && NACH_ISO[iso].properties.bip_mio_usd ? NACH_ISO[iso].properties.bip_mio_usd * 1e6 : 0; };
  const TOP15 = Object.keys(NACH_ISO).filter(bipUsd).sort((a, b) => bipUsd(b) - bipUsd(a)).slice(0, 15);
  // Schwerpunkt mehrerer Länder auf der Kugel (nach BIP gewichtet), für Beschriftungen von Räumen
  function schwerpunkt(isos) {
    const r = Math.PI / 180; let x = 0, y = 0, z = 0;
    for (const i of isos) { const m = mitte(i); if (!m) continue; const w = Math.sqrt(bipUsd(i) || 1); x += w * Math.cos(m[1] * r) * Math.cos(m[0] * r); y += w * Math.cos(m[1] * r) * Math.sin(m[0] * r); z += w * Math.sin(m[1] * r); }
    if (!x && !y && !z) return null;
    return [Math.atan2(y, x) / r, Math.atan2(z, Math.hypot(x, y)) / r];
  }
  /* Aktuellster Wert je Land: Monats-/Quartalswert aus dem VWL-Datensatz (Eurostat, OECD), sonst Jahreswert der Weltbank */
  const WERT = {};
  let VWL_UNVOLLST = false;      // API-Fassung: solange Reihen nachladen, Länderwerte nicht zwischenspeichern
  function aktuell(iso) {
    if (WERT[iso]) return WERT[iso];
    const geo = VWL_GEO(iso), d = vwlDaten();
    const ausVwl = ids => { if (!d) return null; const r = reihe(ids, geo); if (!r) return null; const ist = istTeil(r); if (!ist.length) return null; const [z, v] = ist[ist.length - 1]; return { v, zeit: zeitDe(z), quelle: r.s.quelle || "OECD/Eurostat", jahr: +String(z).slice(0, 4) }; };
    const ausWb = k => { const x = letzter(iso, k); return x ? { v: x[1], zeit: String(x[0]), quelle: "Weltbank", jahr: x[0] } : null; };
    // Monats-/Quartalswert nur, wenn er nicht älter ist als der jüngste Jahreswert (manche OECD-Reihen enden Jahre früher)
    const frischer = (a, b) => a && (!b || a.jahr >= b.jahr) ? a : b;
    const w = { bip: frischer(ausVwl(["bip_yoy", "oecd_bip_yoy"]), ausWb("bip_wachstum")), inf: frischer(ausVwl(["hicp_gesamt", "oecd_inflation"]), ausWb("inflation")),
      al: frischer(ausVwl(["arbeitslosenquote", "oecd_arbeitslosenquote"]), ausWb("arbeitslos")) };
    if (d && !VWL_UNVOLLST) WERT[iso] = w;
    return w;
  }
  const vz = (v, n = 1) => v == null ? "–" : (v > 0 ? "+" : "") + (n ? f1 : f0).format(v);
  function raumWerte(r) {
    const s = { bip: [0, 0], inf: [0, 0], al: [0, 0], lb: [0, 0] }; let bip = 0, ew = 0;
    for (const iso of r.mitglieder) {
      const w = bipUsd(iso); if (!w) continue; const a = aktuell(iso), lb = letzter(iso, "leistungsbilanz");
      bip += w; ew += (letzter(iso, "einwohner") || [0, 0])[1];
      if (a.bip) { s.bip[0] += a.bip.v * w; s.bip[1] += w; } if (a.inf) { s.inf[0] += a.inf.v * w; s.inf[1] += w; }
      if (a.al) { s.al[0] += a.al.v * w; s.al[1] += w; } if (lb) { s.lb[0] += lb[1] * w; s.lb[1] += w; }
    }
    const m = k => s[k][1] ? s[k][0] / s[k][1] : null;
    return { bip: m("bip"), inf: m("inf"), al: m("al"), lb: m("lb"), bipSumme: bip, einwohner: ew, abdeckung: bip ? s.bip[1] / bip : 0 };
  }
  const zollVon = iso => typeof HDL !== "undefined" ? HDL.zoll(iso) : { einfach: null };
  const saldoVon = iso => { const h = HANDEL && HANDEL.laender[iso]; return h && h.export_welt != null && h.import_welt != null ? h.export_welt - h.import_welt : null; };
  const zollText = iso => { const z = zollVon(iso); return z.effektiv ? `Zoll ${f1.format(z.effektiv.wert)} % eff.` : z.einfach != null ? `Zoll Ø ${f1.format(z.einfach)} %` : ""; };

  /* ===== Haupthandelsrouten, Engstellen, Meldungen (Formen Handel und Volkswirtschaft) ===== */
  const MELD = NEWS ? NEWS.meldungen : {};
  const meld = id => MLD.sichtbar(MELD[id]);      // nur Meldungen im gewählten Fenster (3, 7 oder 14 Tage), neueste zuerst
  const TRAEGER = { see: ["Schiff", "#7fb2e5"], binnen: ["Binnenschiff", "#7fb2e5"], bahn: ["Bahn", "#c39bd3"], strasse: ["Straße", "#e6c07b"], luft: ["Luftfracht", "#d7dee8"] };
  const STROM = "#f2c94c";
  const knotenVon = id => ROUTEN && ROUTEN.knoten.find(k => k.id === id);
  const datumKurz = d => d ? d.slice(8, 10) + "." + d.slice(5, 7) + "." : "";
  function routenDaten() {
    if (!ROUTEN) return leerFC;
    return wertFC(ROUTEN.korridore.filter(k => k.stufe <= Math.max(S.stufe, 1)).map(k => ({ type: "Feature", geometry: { type: "LineString", coordinates: k.linie },
      properties: { id: k.id, name: k.name, traeger: k.traeger, stoer: k.engstellen.some(e => meld(e).length) ? 1 : 0, schematisch: k.schematisch ? 1 : 0 } })));
  }
  function knotenDaten() {
    if (!ROUTEN) return leerFC;
    return wertFC(ROUTEN.knoten.filter(k => k.stufe <= Math.max(S.stufe, 1)).map(k => ({ type: "Feature", geometry: { type: "Point", coordinates: [k.lon, k.lat] },
      properties: { id: k.id, name: k.name, art: k.art, traeger: k.traeger, stufe: k.stufe, news: meld(k.id).length } })));
  }
  const newsDaten = () => wertFC(ROUTEN ? ROUTEN.knoten.filter(k => meld(k.id).length).map(k => { const m = meld(k.id)[0]; return { type: "Feature", geometry: { type: "Point", coordinates: [k.lon, k.lat] },
    properties: { id: k.id, name: k.name, n: meld(k.id).length, icon: MLD.bildName(MLD.typ(m), MLD.stand(MLD.alter(m.datum))) } }; }) : []);
  let meldBilderOffen = new WeakSet();
  const bildRaute = m => {
    if (m.hasImage("rt-raute")) return;
    const n = 20, data = new Uint8Array(n * n * 4);
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) data[(y * n + x) * 4 + 3] = Math.abs(x - n / 2 + .5) + Math.abs(y - n / 2 + .5) <= n / 2 - 2 ? 255 : 0;
    m.addImage("rt-raute", { width: n, height: n, data }, { sdf: true });
  };
  ebene({ id: "routen", name: "Haupthandelsrouten, Engstellen, Drehkreuze", gruppe: "Handel", an: !!ROUTEN, geplant: !ROUTEN, formen: ["handel", "vwl"],
    quellen: m => { m.addSource("rt-linien", { type: "geojson", data: routenDaten() }); m.addSource("rt-knoten", { type: "geojson", data: knotenDaten() }); m.addSource("rt-news", { type: "geojson", data: newsDaten() }); },
    schichten: m => {
      bildRaute(m);
      // gestörte Routen (Engstelle mit aktueller Meldung) bekommen einen bernsteinfarbenen Schein
      schicht("routen", { id: "rt-stoer", type: "line", source: "rt-linien", filter: ["==", ["get", "stoer"], 1], layout: { "line-join": "round" }, paint: { "line-color": "#ffb020", "line-opacity": .28, "line-width": ["interpolate", ["linear"], ["zoom"], 1, 4, 6, 9] } });
      const strich = { see: null, bahn: [3, 1.6], strasse: [1, 1.4], luft: [.4, 2] };
      for (const t of ["see", "bahn", "strasse", "luft"]) schicht("routen", { id: "rt-" + t, type: "line", source: "rt-linien", filter: ["==", ["get", "traeger"], t], layout: { "line-join": "round", "line-cap": t === "see" ? "round" : "butt" },
        paint: { "line-color": TRAEGER[t][1], "line-opacity": ["interpolate", ["linear"], ["zoom"], 4.6, t === "luft" ? .6 : .75, 5.4, .3], "line-width": ["interpolate", ["linear"], ["zoom"], 1, t === "see" ? 1.3 : 1, 6, t === "see" ? 2.4 : 2], ...(strich[t] ? { "line-dasharray": strich[t] } : {}) } });
      schicht("routen", { id: "rt-hub", type: "circle", source: "rt-knoten", filter: ["!=", ["get", "art"], "engstelle"], minzoom: ZG[0] - .2, paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 2.5, 2.6, 6, 4.5], "circle-color": ["match", ["get", "art"], "hafen", TRAEGER.see[1], "flughafen", TRAEGER.luft[1], TRAEGER.bahn[1]],
        "circle-stroke-color": "#07090c", "circle-stroke-width": 1 } });
      schicht("routen", { id: "rt-eng", type: "symbol", source: "rt-knoten", filter: ["==", ["get", "art"], "engstelle"], layout: { "icon-image": "rt-raute", "icon-size": ["interpolate", ["linear"], ["zoom"], 1, .5, 6, .8], "icon-allow-overlap": true,
        "text-field": ["get", "name"], "text-font": ["Noto Sans Regular"], "text-size": 10.5, "text-offset": [0, 1.1], "text-anchor": "top", "text-optional": true, "symbol-sort-key": ["get", "stufe"] },
        paint: { "icon-color": ["case", [">", ["get", "news"], 0], "#ffb020", "#e8ecf1"], "icon-halo-color": "#07090c", "icon-halo-width": 1.2, "text-color": "#c3cad3", "text-halo-color": "#07090c", "text-halo-width": 1.2,
          "text-opacity": ["interpolate", ["linear"], ["zoom"], 2, 0, 2.6, 1] } });
      schicht("routen", { id: "rt-hub-name", type: "symbol", source: "rt-knoten", filter: ["!=", ["get", "art"], "engstelle"], minzoom: 3.6, layout: { "text-field": ["get", "name"], "text-font": ["Noto Sans Regular"], "text-size": 10, "text-offset": [0, .9], "text-anchor": "top", "text-optional": true },
        paint: { "text-color": "#8b95a3", "text-halo-color": "#07090c", "text-halo-width": 1.1 } });
      // Meldungssymbol: eine Form je Typ (Angriff, Sperrung, Wetter, Streik, Stau, Unfall), Farbe nach Alter, rechts oberhalb der Engstelle
      if (!meldBilderOffen.has(m)) { meldBilderOffen.add(m); m.on("styleimagemissing", ev => { if (ev.id.startsWith("mld-")) MLD.bildLaden(m, ev.id); }); }
      schicht("routen", { id: "rt-news", type: "symbol", source: "rt-news", layout: { "icon-image": ["get", "icon"], "icon-size": 0.62, "icon-offset": [18, -18], "icon-allow-overlap": true, "icon-ignore-placement": true } });
    },
    klick: (e, m) => { const f = m.queryRenderedFeatures(e.point, { layers: ["rt-news", "rt-eng"].filter(l => m.getLayer(l)) }); if (!f.length) return false; meldungPopup(f[0].properties.id, e.lngLat); return true; } });
  function routenAktualisieren() {
    if (!map) return;
    if (map.getSource("rt-linien")) map.getSource("rt-linien").setData(routenDaten());
    if (map.getSource("rt-knoten")) map.getSource("rt-knoten").setData(knotenDaten());
    if (map.getSource("rt-news")) map.getSource("rt-news").setData(newsDaten());
    vorschauen();
  }
  let meldPop = null;
  function meldungHtml(id, n = 5) {
    const k = knotenVon(id), l = meld(id);
    const wege = ROUTEN.korridore.filter(x => x.engstellen.includes(id)).map(x => x.name);
    return `<b>${esc(k.name)}</b> <span class="pct">${esc((TRAEGER[k.traeger] || [k.traeger])[0])}</span><br><span class="pct">${esc(k.rolle)}</span>
      ${wege.length ? `<br><span class="pct">Hauptrouten: ${esc(wege.join(", "))}</span>` : ""}
      ${l.length ? `<ul class="gk-news">${l.slice(0, n).map(x => `<li><a href="${esc(x.url)}" target="_blank" rel="noopener">${MLD.symbol(x, 13)} ${esc(x.titel)}</a><span class="pct">${esc(x.quelle)} · ${esc(MLD.alterText(x.datum))}${x.unsicher ? " · Stand unsicher" : ""}</span></li>`).join("")}</ul>
        <span class="pct">Originaltitel über ${esc(NEWS.quelle.split(" (")[0])}, Abruf ${esc(NEWS.abruf.replace("T", " "))}</span>` : `<br><span class="pct">Keine Meldungen zu Störungen in den letzten ${MLD.S.fenster} Tagen.</span>`}`;
  }
  function meldungPopup(id, lngLat) {
    if (!knotenVon(id) || !map) return;
    if (meldPop) meldPop.remove();
    meldPop = new maplibregl.Popup({ className: "gk-pop", offset: 12, maxWidth: "360px" }).setLngLat(lngLat || [knotenVon(id).lon, knotenVon(id).lat]).setHTML(meldungHtml(id)).addTo(map);
  }
  /* Vorschauen echter Meldungen ab Stufe 2: Karten an den sichtbaren gestörten Engstellen (höchstens vier, neueste zuerst) */
  let vorschauMarker = [];
  function vorschauen() {
    vorschauMarker.forEach(x => x.remove()); vorschauMarker = [];
    if (!map || !ROUTEN || S.stufe < 2 || !["handel", "vwl"].includes(S.form)) return;
    const e = EBENEN.find(x => x.id === "routen"); if (!e || !ebeneAn(e)) return;
    const c = map.getCenter(), w = map.getCanvas(), r = Math.PI / 180;
    const sichtbar = k => { const d = Math.acos(Math.min(1, Math.sin(c.lat * r) * Math.sin(k.lat * r) + Math.cos(c.lat * r) * Math.cos(k.lat * r) * Math.cos((k.lon - c.lng) * r))) / r;
      if (d > 75) return false; const p = map.project([k.lon, k.lat]); return p.x > 20 && p.y > 70 && p.x < w.clientWidth - 220 && p.y < w.clientHeight - 40; };
    const l = ROUTEN.knoten.filter(k => meld(k.id).length && k.stufe <= S.stufe && sichtbar(k)).sort((a, b) => (meld(b.id)[0].datum || "").localeCompare(meld(a.id)[0].datum || "")).slice(0, 3);
    for (const k of l) {
      const m = meld(k.id)[0], el = document.createElement("button");
      el.type = "button"; el.className = "gk-newskarte"; el.dataset.gkmeldung = k.id;
      el.innerHTML = `<b>${MLD.symbol(m, 13)} ${esc(k.name)}</b><span class="t">${esc(m.titel)}</span><span class="q">${esc(m.quelle)} · ${esc(MLD.alterText(m.datum))}${meld(k.id).length > 1 ? ` · +${meld(k.id).length - 1}` : ""}</span>`;
      vorschauMarker.push(new maplibregl.Marker({ element: el, anchor: "bottom-left", offset: [14, -14] }).setLngLat([k.lon, k.lat]).addTo(map));
    }
  }

  /* ===== Handel Stufe 2/3: Zollsätze und Saldo aller sichtbaren Länder; Strom zwischen Wirtschaftsräumen und zu Nachbarn ===== */
  function infoDaten() {
    if (!HANDEL) return leerFC;
    return wertFC(LAENDER_PUNKTE.features.filter(f => HANDEL.laender[f.properties.iso] || zollVon(f.properties.iso).einfach != null).map(f => {
      const iso = f.properties.iso, s = saldoVon(iso), z = zollText(iso);
      return { type: "Feature", geometry: f.geometry, properties: { iso, name: landKurz(iso), z, s: s == null ? "" : `Saldo ${s > 0 ? "+" : ""}${f0.format(s / 1e9)} Mrd.`, plus: s == null ? 0 : s >= 0 ? 1 : -1, bip: bipUsd(iso), gewaehlt: S.auswahl.includes(iso) } };
    }));
  }
  ebene({ id: "handelinfo", name: "Zollsätze und Handelssaldo", gruppe: "Handel", an: !!HANDEL, geplant: !HANDEL, formen: ["handel"],
    quellen: m => m.addSource("h-info", { type: "geojson", data: infoDaten() }),
    schichten: m => schicht("handelinfo", { id: "h-info", type: "symbol", source: "h-info", minzoom: ZG[0], layout: {
      "text-field": ["format", ["get", "name"], { "text-color": ["case", ["get", "gewaehlt"], "#ffa828", "#e8ecf1"], "font-scale": 1.15 }, "\n", {}, ["get", "z"], { "text-color": "#a3acb8" }, "\n", {}, ["get", "s"], { "text-color": ["case", [">", ["get", "plus"], 0], HEX_EXP, ["<", ["get", "plus"], 0], HEX_IMP, "#c3cad3"] }],
      "text-font": ["Noto Sans Regular"], "text-size": 10, "text-line-height": 1.15, "text-padding": 3, "symbol-sort-key": ["-", 0, ["get", "bip"]] },
      paint: { "text-halo-color": "#07090c", "text-halo-width": 1.3, "text-opacity": ["interpolate", ["linear"], ["zoom"], ZG[0], 0, ZG[0] + .4, 1] } }) });
  // Strom: Gruppe = Wirtschaftsraum (EU, EFTA, UK, Türkei, EAWU …), sonst das Land selbst
  const stromGruppe = iso => RAUM_VON[iso] || iso;
  const gruppeName = g => raumVon(g) ? raumVon(g).kurz : landName(g);
  const gruppeMitte = g => raumVon(g) ? (raumVon(g).mitglieder.length > 1 ? schwerpunkt(raumVon(g).mitglieder) : mitte(raumVon(g).mitglieder[0])) : mitte(g);
  const STROM_PAARE = WELT && WELT.strom && WELT.strom.paare ? Object.entries(WELT.strom.paare).map(([k, [v]]) => { const [a, b] = k.split(">"); return { a, b, v }; }) : [];
  function stromRaumDaten() {
    if (S.form !== "handel" || !STROM_PAARE.length) return leerFC;
    const sum = {};
    STROM_PAARE.forEach(({ a, b, v }) => { const ga = stromGruppe(a), gb = stromGruppe(b); if (ga === gb) return; const k = ga < gb ? ga + "|" + gb : gb + "|" + ga, s = sum[k] = sum[k] || { [ga]: 0, [gb]: 0 }; s[ga] += v; });
    const l = Object.entries(sum).map(([k, s]) => { const [x, y] = k.split("|"); return { x, y, xy: s[x] || 0, yx: s[y] || 0 }; }).sort((p, q) => (q.xy + q.yx) - (p.xy + p.yx)).slice(0, 8);
    const mx = Math.max(1, ...l.map(p => p.xy + p.yx));
    return wertFC(l.filter(p => gruppeMitte(p.x) && gruppeMitte(p.y)).map(p => { const netto = p.xy - p.yx, von = netto >= 0 ? p.x : p.y, nach = netto >= 0 ? p.y : p.x;
      return { type: "Feature", geometry: { type: "LineString", coordinates: bogen(gruppeMitte(von), gruppeMitte(nach), 32, .12) },
        properties: { t: `${gruppeName(von)} → ${gruppeName(nach)} ${f1.format(Math.abs(netto) / 1000)} TWh`, von: gruppeName(von), nach: gruppeName(nach), netto: Math.abs(netto), brutto: p.xy + p.yx, hin: netto >= 0 ? p.xy : p.yx, rueck: netto >= 0 ? p.yx : p.xy, w: 1 + 3.5 * Math.sqrt((p.xy + p.yx) / mx), strom: 1 } }; }));
  }
  // Stufe 3: bilateraler Strom des gewählten Landes mit jedem Nachbarn (Eurostat, nur europäische Meldeländer)
  function stromNbDaten(richtung) {
    if (!S.land || !STROM_PAARE.length || richtung !== "export") return leerFC;   // eine Linie je Nachbar (Richtung des Nettoflusses)
    const f = [], wert = (a, b) => (STROM_PAARE.find(x => x.a === a && x.b === b) || {}).v || 0;
    for (const q of nachbarnVon(S.land)) {
      const aus = wert(S.land, q), ein = wert(q, S.land);
      if ((!aus && !ein) || !mitte(q)) continue;
      const von = aus >= ein ? S.land : q, nach = aus >= ein ? q : S.land;
      f.push({ type: "Feature", geometry: { type: "LineString", coordinates: bogen(mitte(von), mitte(nach), 24, -HUB * 1.8) },
        properties: { t: `↗ ${f1.format(aus / 1000)} · ↘ ${f1.format(ein / 1000)} TWh`, von: landName(von), nach: landName(nach), aus, ein, land: landName(S.land), partner: landName(q), netto: Math.abs(aus - ein), w: 1 + Math.min(4, Math.sqrt((aus + ein) / 1000) * .8), strom: 2 } });
    }
    return wertFC(f);
  }
  const hatStromBilateral = iso => STROM_PAARE.some(p => p.a === iso || p.b === iso);
  function stromSchichten(eb, id, quelle, gestrichelt, op) {
    schicht(eb, { id, type: "line", source: quelle, paint: { "line-color": STROM, "line-width": ["get", "w"], "line-opacity": op, ...(gestrichelt ? { "line-dasharray": [2, 1.4] } : {}) } });
    schicht(eb, { id: id + "-pfeil", type: "symbol", source: quelle, layout: { "symbol-placement": "line", "symbol-spacing": 80, "icon-image": "h-pfeil", "icon-size": .45, "icon-allow-overlap": true, "icon-ignore-placement": true, "icon-rotation-alignment": "map" }, paint: { "icon-color": STROM, "icon-opacity": op } });
    schicht(eb, { id: id + "-t", type: "symbol", source: quelle, layout: { "symbol-placement": "line-center", "text-field": ["get", "t"], "text-font": ["Noto Sans Regular"], "text-size": 10.5, "text-offset": [0, -.8], "text-padding": 4 },
      paint: { "text-color": STROM, "text-halo-color": "#07090c", "text-halo-width": 1.3, "text-opacity": op } });
  }
  ebene({ id: "strom", name: "Stromhandel (Räume in Stufe 2, Nachbarn in Stufe 3)", gruppe: "Handel", an: STROM_PAARE.length > 0, geplant: !STROM_PAARE.length, formen: ["handel", "vwl"],
    quellen: m => { m.addSource("st-raum", { type: "geojson", data: stromRaumDaten() }); m.addSource("st-x", { type: "geojson", data: stromNbDaten("export") }); m.addSource("st-m", { type: "geojson", data: stromNbDaten("import") }); },
    schichten: m => {
      hPfeil(m);
      stromSchichten("strom", "st-raum", "st-raum", false, ["interpolate", ["linear"], ["zoom"], ZG[0], 0, ZG[0] + .4, .9, 4.4, .9, 4.9, 0]);
      const op3 = ["interpolate", ["linear"], ["zoom"], 4.9, 0, 5.4, .95];
      stromSchichten("strom", "st-x", "st-x", false, op3); stromSchichten("strom", "st-m", "st-m", true, op3);
    } });
  function stromAktualisieren() {
    if (!map) return;
    [["st-raum", stromRaumDaten], ["st-x", () => stromNbDaten("export")], ["st-m", () => stromNbDaten("import")]].forEach(([q, f]) => { if (map.getSource(q)) map.getSource(q).setData(f()); });
  }

  /* ===== Handel: Exporte je Gut (CEPII BACI, gueter_baci.py) und die größten See- und Flughäfen (verkehrsknoten.py) ===== */
  const GUETER = (d => d && d.laender ? d : null)(roh("gueter-daten"));
  const VERKEHR = (d => d && d.haefen ? d : null)(roh("verkehr-daten"));
  const GUT_RAMPE = ["#2a2147", "#4b3a8f", "#7a5bd0", "#b08cf0", "#e6d3ff"];     // violett: Güter-Exportmenge (Grün/Rot bleiben Export/Import vorbehalten)
  const gutVon = id => GUETER ? GUETER.gruppen.find(g => g.id === id) : null;
  const gutJahr = () => GUETER ? GUETER.jahre.length - 1 : 0;
  const gutWert = (iso, id) => { const e = GUETER && GUETER.laender[iso] && GUETER.laender[iso][id]; return e ? e.v[gutJahr()] : null; };
  const gutMrd = v => v == null ? "–" : v >= 1000 ? f1.format(v / 1000) + " Mrd." : f0.format(v) + " Mio.";
  function gutRangliste(id) {
    if (!GUETER) return [];
    return Object.keys(GUETER.laender).map(iso => [iso, gutWert(iso, id)]).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]);
  }
  // Farbe nach Wurzel des Exportwerts (sonst bleibt alles außer den Spitzenreitern dunkel)
  function gutFarben(id) {
    const l = gutRangliste(id).filter(([iso]) => NACH_ISO[iso]); if (!l.length) return "rgba(0,0,0,0)";
    const mx = Math.sqrt(l[0][1]), ex = ["match", ["get", "iso"]];
    for (const [iso, v] of l) ex.push(iso, GUT_RAMPE[Math.min(4, Math.floor(Math.sqrt(v) / mx * 4.999))]);
    ex.push("rgba(0,0,0,0)");
    return ex;
  }
  function gutPunkte() {
    if (!GUETER || !S.gut) return leerFC;
    const l = gutRangliste(S.gut), welt = (GUETER.welt[S.gut] || {})[GUETER.jahre[gutJahr()]] || 0;
    return wertFC(l.slice(0, 40).map(([iso, v], i) => { const c = LAENDER_PUNKTE.features.find(f => f.properties.iso === iso); if (!c) return null;
      return { type: "Feature", geometry: c.geometry, properties: { iso, t: `${landKurz(iso)}\n${gutMrd(v)} USD`, rang: i + 1, anteil: welt ? v / welt : 0 } }; }).filter(Boolean));
  }
  ebene({ id: "gueter", name: "Exporte je Gut (Länder eingefärbt)", gruppe: "Handel", an: !!GUETER, geplant: !GUETER, formen: ["handel"],
    quellen: m => m.addSource("gu-punkte", { type: "geojson", data: gutPunkte() }),
    schichten: (m, vor) => {
      schicht("gueter", { id: "gu-flaeche", type: "fill", source: "laender", paint: { "fill-color": S.gut ? gutFarben(S.gut) : "rgba(0,0,0,0)",
        "fill-opacity": S.gut ? ["interpolate", ["linear"], ["zoom"], 3, .82, 5.5, .3, 7, .08] : 0 } }, vor);
      schicht("gueter", { id: "gu-text", type: "symbol", source: "gu-punkte", maxzoom: 5.5, layout: { "text-field": ["get", "t"], "text-font": ["Noto Sans Regular"], "text-size": 10.5, "text-line-height": 1.15,
        "text-padding": 3, "symbol-sort-key": ["get", "rang"], "text-optional": true }, paint: { "text-color": "#f1e8ff", "text-halo-color": "#1c1433", "text-halo-width": 1.4 } });
    } });
  function gutAnwenden() {
    if (!map || !map.getLayer("gu-flaeche")) return;
    map.setPaintProperty("gu-flaeche", "fill-color", S.gut ? gutFarben(S.gut) : "rgba(0,0,0,0)");
    map.setPaintProperty("gu-flaeche", "fill-opacity", S.gut ? ["interpolate", ["linear"], ["zoom"], 3, .82, 5.5, .3, 7, .08] : 0);
    if (map.getSource("gu-punkte")) map.getSource("gu-punkte").setData(gutPunkte());
  }
  function gutWaehlen(id) { S.gut = S.gut === id ? null : id; gutAnwenden(); seiteZeichnen(); }
  function gutBlock() {
    if (!GUETER) return "";
    const bereiche = [...new Set(GUETER.gruppen.map(g => g.bereich))];
    const chips = bereiche.map(b => `<div class="gk-chips" style="margin-top:6px"><span class="pct" style="min-width:92px">${esc(b)}</span>${GUETER.gruppen.filter(g => g.bereich === b).map(g => `<button type="button" data-gkgut="${esc(g.id)}" aria-pressed="${S.gut === g.id}">${esc(g.name)}</button>`).join("")}</div>`).join("");
    let rang = "";
    if (S.gut) {
      const g = gutVon(S.gut), l = gutRangliste(S.gut), welt = (GUETER.welt[S.gut] || {})[GUETER.jahre[gutJahr()]] || 0, rest = l.slice(0, 10);
      rang = `<h3 style="margin-top:12px">${esc(g.name)}: größte Exportländer ${esc(GUETER.jahre[gutJahr()])}</h3>
        <div class="gk-leg" aria-hidden="true" style="display:flex;height:8px;border-radius:4px;overflow:hidden;margin:6px 0 2px">${GUT_RAMPE.map(c => `<i style="flex:1;background:${c}"></i>`).join("")}</div>
        <p class="gk-quelle" style="display:flex;justify-content:space-between;margin:0 0 6px"><span>wenig</span><span>Farbe nach Wurzel des Exportwerts</span><span>viel</span></p>
        <table class="gk-tab"><thead><tr><th>Land</th><th style="text-align:right">Mio. USD</th><th style="text-align:right">Anteil</th></tr></thead><tbody>${rest.map(([iso, v]) => `<tr><td><button type="button" class="gk-link" data-gkland="${esc(iso)}">${esc(landName(iso))}</button></td><td>${f0.format(v)}</td><td>${welt ? f1.format(v / welt * 100) + " %" : "–"}</td></tr>`).join("")}</tbody></table>
        <p class="gk-quelle" style="margin-top:6px">Weltweit ${gutMrd(welt)} USD (${esc(g.hs.map(h => "HS " + h).join(", "))}). Exportwert laut Meldung der Handelspartner, bereinigt (BACI); Taiwan enthält „Other Asia, nes“.</p>`;
    }
    return `<div class="gk-block"><h3>Exporte nach Gut</h3><p class="unter" style="margin:2px 0 4px">Gut wählen: die Länder werden nach ihrer Exportmenge eingefärbt</p>${chips}${rang}
      <p class="gk-quelle" style="margin-top:8px">Quelle: <a href="${esc(GUETER.url)}" target="_blank" rel="noopener">CEPII BACI</a> (Etalab 2.0), Daten aus UN Comtrade; Version 202601, Zeitreihe ${esc(GUETER.jahre[0])}–${esc(GUETER.jahre[gutJahr()])}.</p></div>`;
  }
  function gutLandBlock(iso) {
    if (!GUETER || !GUETER.laender[iso]) return "";
    const z = Object.entries(GUETER.laender[iso]).map(([id, e]) => ({ id, v: e.v[gutJahr()], v0: e.v[0], p: e.partner || [] })).filter(x => x.v > 0).sort((a, b) => b.v - a.v).slice(0, 8);
    if (!z.length) return "";
    const rang = id => 1 + gutRangliste(id).findIndex(([i]) => i === iso);
    return `<div class="gk-block"><h3>Exportgüter ${esc(GUETER.jahre[gutJahr()])} (ausgewählte Gütergruppen)</h3>
      <table class="gk-tab"><thead><tr><th>Gut</th><th style="text-align:right">Mio. USD</th><th style="text-align:right">Rang Welt</th><th>Hauptabnehmer</th></tr></thead><tbody>${z.map(x => `<tr><td><button type="button" class="gk-link" data-gkgut="${esc(x.id)}">${esc(gutVon(x.id).name)}</button></td><td>${f0.format(x.v)}</td><td>${rang(x.id)}</td><td style="font-family:var(--sans)">${x.p.slice(0, 3).map(([p]) => esc(landKurz(p))).join(", ")}</td></tr>`).join("")}</tbody></table>
      <p class="gk-quelle" style="margin-top:6px">${GUETER.gruppen.length} Gütergruppen (Energie, Landwirtschaft, Metalle, Industrie); Gut anklicken färbt die Karte. CEPII BACI.</p></div>`;
  }

  const haefenPunkte = () => !VERKEHR ? leerFC : wertFC(VERKEHR.haefen.map((h, i) => ({ type: "Feature", geometry: { type: "Point", coordinates: [h.lon, h.lat] },
    properties: { id: "h" + i, name: h.name, w: Math.sqrt(Math.max(h.teu_tsd || 0, (h.kt || 0) / 12)), rang: Math.min(h.teu_rang || 99, (h.ton_rang || 99) + 5) } })));
  const flughafenPunkte = () => !VERKEHR ? leerFC : wertFC(VERKEHR.flughaefen.map((f, i) => ({ type: "Feature", geometry: { type: "Point", coordinates: [f.lon, f.lat] },
    properties: { id: "f" + i, name: f.iata + " " + f.name.replace(/ (International )?Airport$/, ""), w: Math.sqrt(Math.max((f.pax || 0) / 1e5, (f.fracht || 0) / 4000)), rang: Math.min(f.pax_rang || 99, (f.fracht_rang || 99) + 5) } })));
  const KNOTEN_RADIUS = (k, mx) => ["interpolate", ["linear"], ["zoom"], 1.5, ["*", k, ["/", ["get", "w"], mx]], 6, ["*", k * 2.1, ["/", ["get", "w"], mx]]];
  function haefenHtml(h) {
    const z = [h.teu_tsd ? `Container ${f0.format(h.teu_tsd)} Tsd. TEU (${h.teu_jahr || 2025}), Rang ${h.teu_rang}` : "", h.kt ? `Umschlag ${f1.format(h.kt / 1000)} Mio. t (2022), Rang ${h.ton_rang}` : ""].filter(Boolean);
    return `<b>${esc(h.name)}</b> <span class="pct">Seehafen · ${esc(landName(h.land || ""))}</span><br>${z.map(esc).join("<br>")}
      <br><span class="pct">Quellen: Wikipedia (CC BY-SA) nach Lloyd's List / SISI, Lage UN/LOCODE</span>`;
  }
  function flughafenHtml(f) {
    const z = [f.pax ? `Passagiere ${f1.format(f.pax / 1e6)} Mio. (2025), Rang ${f.pax_rang}` : "", f.fracht ? `Fracht ${f1.format(f.fracht / 1e6)} Mio. t (2025), Rang ${f.fracht_rang}` : ""].filter(Boolean);
    return `<b>${esc(f.name)}</b> <span class="pct">Flughafen ${esc(f.iata)} · ${esc(landName(f.land || ""))}</span><br>${z.map(esc).join("<br>")}
      <br><span class="pct">Quellen: Wikipedia (CC BY-SA) nach ACI, Lage OurAirports</span>`;
  }
  let knotenPop = null;
  function knotenOeffnen(art, i, fliegen) {
    const k = (art === "h" ? VERKEHR.haefen : VERKEHR.flughaefen)[i]; if (!k || !map) return;
    if (knotenPop) knotenPop.remove();
    if (fliegen) map.flyTo({ center: [k.lon, k.lat], zoom: Math.max(map.getZoom(), 4.2), duration: 1100 });
    knotenPop = new maplibregl.Popup({ className: "gk-pop", offset: 12, maxWidth: "320px" }).setLngLat([k.lon, k.lat]).setHTML(art === "h" ? haefenHtml(k) : flughafenHtml(k)).addTo(map);
  }
  const knotenKlick = (layer, art) => (e, m) => { const f = m.queryRenderedFeatures(e.point, { layers: [layer].filter(l => m.getLayer(l)) }); if (!f.length) return false; knotenOeffnen(art, +f[0].properties.id.slice(1), false); return true; };
  const KN_FARBE_H = "#4fd1c5", KN_FARBE_F = "#f6ad55";
  ebene({ id: "haefen", name: "Größte Seehäfen (Container, Umschlag)", gruppe: "Handel", an: !!VERKEHR, geplant: !VERKEHR, formen: ["handel", "vwl"], vorrang: true,
    quellen: m => m.addSource("vk-haefen", { type: "geojson", data: haefenPunkte() }),
    schichten: m => {
      const mx = Math.max(...haefenPunkte().features.map(f => f.properties.w), 1);
      schicht("haefen", { id: "vk-haefen", type: "circle", source: "vk-haefen", layout: { "circle-sort-key": ["-", 0, ["get", "w"]] }, paint: { "circle-radius": KNOTEN_RADIUS(9, mx), "circle-color": KN_FARBE_H, "circle-opacity": .78, "circle-stroke-color": "#07090c", "circle-stroke-width": 1 } });
      schicht("haefen", { id: "vk-haefen-t", type: "symbol", source: "vk-haefen", minzoom: 2.4, layout: { "text-field": ["get", "name"], "text-font": ["Noto Sans Regular"], "text-size": 10.5, "text-offset": [0, 1.1], "text-anchor": "top", "text-optional": true, "text-padding": 3, "symbol-sort-key": ["get", "rang"] },
        paint: { "text-color": KN_FARBE_H, "text-halo-color": "#07090c", "text-halo-width": 1.3 } });
    }, klick: knotenKlick("vk-haefen", "h") });
  ebene({ id: "flughaefen", name: "Größte Flughäfen (Passagiere, Fracht)", gruppe: "Handel", an: !!VERKEHR, geplant: !VERKEHR, formen: ["handel", "vwl"], vorrang: true,
    quellen: m => m.addSource("vk-flug", { type: "geojson", data: flughafenPunkte() }),
    schichten: m => {
      const mx = Math.max(...flughafenPunkte().features.map(f => f.properties.w), 1);
      schicht("flughaefen", { id: "vk-flug", type: "circle", source: "vk-flug", layout: { "circle-sort-key": ["-", 0, ["get", "w"]] }, paint: { "circle-radius": KNOTEN_RADIUS(8, mx), "circle-color": "rgba(246,173,85,.18)", "circle-stroke-color": KN_FARBE_F, "circle-stroke-width": 2 } });
      schicht("flughaefen", { id: "vk-flug-t", type: "symbol", source: "vk-flug", minzoom: 3, layout: { "text-field": ["get", "name"], "text-font": ["Noto Sans Regular"], "text-size": 10.5, "text-offset": [0, 1.1], "text-anchor": "top", "text-optional": true, "text-padding": 3, "symbol-sort-key": ["get", "rang"] },
        paint: { "text-color": KN_FARBE_F, "text-halo-color": "#07090c", "text-halo-width": 1.3 } });
    }, klick: knotenKlick("vk-flug", "f") });
  function verkehrBlock() {
    if (!VERKEHR) return "";
    const h = VERKEHR.haefen.map((x, i) => [x, i]).filter(([x]) => x.teu_rang).sort((a, b) => a[0].teu_rang - b[0].teu_rang).slice(0, 10);
    const f = VERKEHR.flughaefen.map((x, i) => [x, i]).filter(([x]) => x.pax_rang).sort((a, b) => a[0].pax_rang - b[0].pax_rang).slice(0, 10);
    const q = VERKEHR.quellen;
    return `<div class="gk-block"><h3>Größte Seehäfen und Flughäfen</h3>
      <p class="unter" style="margin:2px 0 4px"><span style="color:${KN_FARBE_H}">●</span> Seehäfen (Fläche nach Container- bzw. Gesamtumschlag) · <span style="color:${KN_FARBE_F}">◯</span> Flughäfen (Größe nach Passagieren bzw. Fracht) · anklicken für Zahlen</p>
      <table class="gk-tab"><thead><tr><th>Seehafen (Container)</th><th style="text-align:right">Mio. TEU</th></tr></thead><tbody>${h.map(([x, i]) => `<tr><td><button type="button" class="gk-link" data-gkverkehr="h${i}">${x.teu_rang}. ${esc(x.name)}</button></td><td>${f1.format(x.teu_tsd / 1000)}</td></tr>`).join("")}</tbody></table>
      <table class="gk-tab" style="margin-top:8px"><thead><tr><th>Flughafen (Passagiere)</th><th style="text-align:right">Mio.</th></tr></thead><tbody>${f.map(([x, i]) => `<tr><td><button type="button" class="gk-link" data-gkverkehr="f${i}">${x.pax_rang}. ${esc(x.iata)} ${esc(x.name.replace(/ (International )?Airport$/, ""))}</button></td><td>${f0.format(x.pax / 1e6)}</td></tr>`).join("")}</tbody></table>
      <p class="gk-quelle" style="margin-top:6px">Rangfolgen: ${VERKEHR.haefen.length} Seehäfen (Container 2025, Umschlag 2022) und ${VERKEHR.flughaefen.length} Flughäfen (Passagiere und Fracht 2025). Quellen: ${q.map(x => `<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.name.split(" (")[0].replace("Wikipedia: ", "Wikipedia "))}</a>`).join(", ")}; Abruf ${esc(VERKEHR.abruf)}.</p></div>`;
  }
  function verkehrLandBlock(iso) {
    if (!VERKEHR) return "";
    const h = VERKEHR.haefen.map((x, i) => [x, i]).filter(([x]) => x.land === iso), f = VERKEHR.flughaefen.map((x, i) => [x, i]).filter(([x]) => x.land === iso);
    if (!h.length && !f.length) return "";
    return `<div class="gk-block"><h3>Große Häfen und Flughäfen</h3><ul class="gk-liste">${h.map(([x, i]) => `<li><button type="button" data-gkverkehr="h${i}">⚓ ${esc(x.name)}</button><span class="r">${x.teu_tsd ? f1.format(x.teu_tsd / 1000) + " Mio. TEU" : f1.format((x.kt || 0) / 1000) + " Mio. t"}</span></li>`).join("")}
      ${f.map(([x, i]) => `<li><button type="button" data-gkverkehr="f${i}">✈ ${esc(x.iata)} ${esc(x.name.replace(/ (International )?Airport$/, ""))}</button><span class="r">${x.pax ? f0.format(x.pax / 1e6) + " Mio. Pass." : f1.format(x.fracht / 1e6) + " Mio. t"}</span></li>`).join("")}</ul></div>`;
  }

  /* ===== Volkswirtschaft: Wirtschaftsräume (Stufe 1) und Werte aller Länder (Stufe 2/3) ===== */
  const raumFarbe = () => ["match", ["get", "iso"], ...Object.entries(RAUM_VON).flatMap(([i, r]) => [i, raumVon(r).farbe]), "#3a4655"];
  function raumDeckkraft() {
    const r = raumVon(S.raum), mit = r ? r.mitglieder : [];
    return ["case", ["in", ["get", "iso"], ["literal", mit]], .62, r ? .14 : .32];
  }
  function raumFuellFarbe() {
    const r = raumVon(S.raum);
    return r && r.art === "uebergreifend" ? ["case", ["in", ["get", "iso"], ["literal", r.mitglieder]], r.farbe, raumFarbe()] : raumFarbe();
  }
  function raumPunkte() {
    if (!WELT) return leerFC;
    const liste = RAEUME.filter(r => r.art !== "uebergreifend" || r.id === S.raum);
    return wertFC(liste.map(r => { const p = r.mitglieder.length > 1 ? schwerpunkt(r.mitglieder) : mitte(r.mitglieder[0]); if (!p) return null; const w = raumWerte(r);
      return { type: "Feature", geometry: { type: "Point", coordinates: p }, properties: { id: r.id, kurz: r.kurz, gewaehlt: r.id === S.raum, bip: w.bip == null ? "–" : vz(w.bip) + " %", inf: w.inf == null ? "–" : f1.format(w.inf) + " %",
        bipv: w.bip == null ? 0 : w.bip, infv: w.inf == null ? 0 : w.inf, gr: w.bipSumme } }; }).filter(Boolean));
  }
  // Farben für Werte auf der Karte: Wachstum blau (positiv) bzw. orange (negativ); Inflation über 5 % orange, unter 0 % blau
  const farbeBip = v => ["case", [">", v, 0], "#7cc4ff", ["<", v, 0], "#ff9f6b", "#c3cad3"];
  const farbeInf = v => ["case", [">", v, 5], "#ff9f6b", ["<", v, 0], "#7cc4ff", "#e8ecf1"];
  function wertPunkte() {
    return wertFC(LAENDER_PUNKTE.features.map(f => { const a = aktuell(f.properties.iso); if (!a.bip && !a.inf) return null;
      return { type: "Feature", geometry: f.geometry, properties: { iso: f.properties.iso, name: landKurz(f.properties.iso), bip: a.bip ? vz(a.bip.v) + " %" : "–", inf: a.inf ? f1.format(a.inf.v) + " %" : "–",
        bipv: a.bip ? a.bip.v : 0, infv: a.inf ? a.inf.v : 0, gr: bipUsd(f.properties.iso), gewaehlt: S.auswahl.includes(f.properties.iso) } }; }).filter(Boolean));
  }
  ebene({ id: "vwl", name: "BIP-Wachstum und Inflation, Wirtschaftsräume", gruppe: "Volkswirtschaft", an: !!WELT, geplant: !WELT, formen: ["vwl"],
    quellen: m => { m.addSource("vw-raum", { type: "geojson", data: raumPunkte() }); m.addSource("vw-wert", { type: "geojson", data: wertPunkte() }); },
    schichten: (m, vor) => {
      schicht("vwl", { id: "vw-flaeche", type: "fill", source: "laender", paint: { "fill-color": raumFuellFarbe(), "fill-opacity": ["interpolate", ["linear"], ["zoom"], 2.2, raumDeckkraft(), 2.7, 0] } }, vor);
      schicht("vwl", { id: "vw-raum", type: "symbol", source: "vw-raum", layout: { "text-field": ["format", ["get", "kurz"], { "font-scale": 1.12, "text-color": ["case", ["get", "gewaehlt"], "#ffa828", "#e8ecf1"] }, "\n", {},
        "BIP ", { "text-color": "#8b95a3", "font-scale": .9 }, ["get", "bip"], { "text-color": farbeBip(["get", "bipv"]), "font-scale": .9 }, "  Inf. ", { "text-color": "#8b95a3", "font-scale": .9 }, ["get", "inf"], { "text-color": farbeInf(["get", "infv"]), "font-scale": .9 }],
        "text-font": ["Noto Sans Bold"], "text-size": 12, "text-line-height": 1.2, "text-padding": 4, "symbol-sort-key": ["-", 0, ["get", "gr"]] },
        paint: { "text-halo-color": "#07090c", "text-halo-width": 1.5, "text-opacity": ["interpolate", ["linear"], ["zoom"], 2.2, 1, 2.6, 0] } });
      schicht("vwl", { id: "vw-wert", type: "symbol", source: "vw-wert", minzoom: ZG[0] - .2, layout: { "text-field": ["format", ["get", "name"], { "text-color": ["case", ["get", "gewaehlt"], "#ffa828", "#e8ecf1"], "font-scale": 1.12 }, "\nBIP ", { "text-color": "#8b95a3" }, ["get", "bip"], { "text-color": farbeBip(["get", "bipv"]) },
        "  Inf. ", { "text-color": "#8b95a3" }, ["get", "inf"], { "text-color": farbeInf(["get", "infv"]) }], "text-font": ["Noto Sans Regular"], "text-size": 10.5, "text-line-height": 1.2, "text-padding": 2,
        "symbol-sort-key": ["-", 0, ["get", "gr"]] }, paint: { "text-halo-color": "#07090c", "text-halo-width": 1.3, "text-opacity": ["interpolate", ["linear"], ["zoom"], ZG[0] - .2, 0, ZG[0] + .2, 1] } });
    } });
  function vwlAnwenden() {
    if (!map) return;
    if (map.getSource("vw-raum")) map.getSource("vw-raum").setData(raumPunkte());
    if (map.getSource("vw-wert")) map.getSource("vw-wert").setData(wertPunkte());
    ["vw-flaeche", "bo-flaeche", "un-flaeche"].forEach(id => { if (map.getLayer(id)) { map.setPaintProperty(id, "fill-color", raumFuellFarbe()); map.setPaintProperty(id, "fill-opacity", ["interpolate", ["linear"], ["zoom"], 2.2, raumDeckkraft(), 2.7, 0]); } });
  }
  function raumWaehlen(id) { S.raum = S.raum === id ? null : id; vwlAnwenden(); if (typeof unAnwenden === "function") unAnwenden(); seiteZeichnen(); }

  /* ===== Börse & Finanzen (1A Börsenplätze, 2A Werte je Land, 3A Finanzplatz) =====
     Daten: data/boerse_welt.json (boerse_welt.py: Börsenplätze, Leitzinsen BIS, 10-j. Renditen OECD, EZB-Kurse, Rohstoffe FRED)
     und die Kurse des Bereichs BÖR (boerse.json, Yahoo Finance). */
  const BW = roh("boerse-welt-daten");
  const BD = () => (typeof BOE !== "undefined" && BOE.da() ? BOE.korr() : null);
  const indexNach = name => { const b = BD(); return b && name ? b.indizes.find(x => x.name === name) || null : null; };
  const PLAETZE = BW ? BW.plaetze.map(p => ({ ...p, lon: +p.lon, lat: +p.lat })) : [];
  const EURO = new Set((RAEUME.find(r => r.id === "EURO") || { mitglieder: [] }).mitglieder);
  const leitindex = iso => { const p = PLAETZE.find(x => x.iso === iso); return p ? indexNach(p.leitindex) : null; };
  const reiheLetzt = (obj, iso) => { const l = obj && obj[iso]; return l && l.length ? { zeit: l[l.length - 1][0], v: l[l.length - 1][1], l } : null; };
  const leitzins = iso => BW ? reiheLetzt(BW.leitzins, iso) || (EURO.has(iso) ? { ...reiheLetzt(BW.leitzins, "XM"), euro: true } : null) : null;
  const rendite10 = iso => BW ? reiheLetzt(BW.rendite10, iso) : null;
  const pctVz = v => v == null ? "–" : `${v > 0 ? "+" : ""}${f1.format(v * 100)} %`;
  const farbVz = v => v == null ? "var(--ink-3)" : `var(--${v >= 0 ? "up" : "down"})`;
  const WAEHRUNG = { US: "USD", GB: "GBP", JP: "JPY", CN: "CNY", CH: "CHF", IN: "INR", BR: "BRL", KR: "KRW", AU: "AUD", CA: "CAD", SE: "SEK", NO: "NOK", PL: "PLN", TR: "TRY", ZA: "ZAR", MX: "MXN", HK: "HKD", SG: "SGD" };
  const waehrungVon = iso => EURO.has(iso) ? "EUR" : WAEHRUNG[iso] || null;
  function platzPunkte() {
    return wertFC(PLAETZE.map(p => { const x = indexNach(p.leitindex);
      return { type: "Feature", geometry: { type: "Point", coordinates: [p.lon, p.lat] }, properties: { id: p.id, iso: p.iso, stadt: p.stadt, name: p.name, index: p.leitindex.replace(/ \(ETF.*$/, " (ETF)"),
        ytd: x && x.ytd != null ? pctVz(x.ytd) : "–", ytdv: x && x.ytd != null ? x.ytd : 0, hat: x && x.ytd != null ? 1 : 0, gr: bipUsd(p.iso), gewaehlt: S.auswahl.includes(p.iso) } }; }));
  }
  function boLandPunkte() {
    return wertFC(LAENDER_PUNKTE.features.map(f => { const iso = f.properties.iso, x = leitindex(iso), r = rendite10(iso);
      const mw = bmAktiv() ? FNZ.messWerte(S.bm)[iso] : null;
      if (bmAktiv()) return mw ? { type: "Feature", geometry: f.geometry, properties: { iso, name: landKurz(iso), idx: FNZ.mess().find(m => m.id === S.bm).name.replace(/ \(.*$/, ""), ytd: FNZ.messText(S.bm, mw), ytdv: 1, r10: "", gr: bipUsd(iso), gewaehlt: S.auswahl.includes(iso) } } : null;
      if (!x && !r) return null;
      return { type: "Feature", geometry: f.geometry, properties: { iso, name: landKurz(iso), idx: x ? x.name.replace(/ \(ETF.*$/, "").replace(/^.*\(ETF iShares MSCI (.*)\)$/, "MSCI $1") : "", ytd: x && x.ytd != null ? pctVz(x.ytd) : "", ytdv: x && x.ytd != null ? x.ytd : 0,
        r10: r ? "10J " + f2.format(r.v) + " %" : "", gr: bipUsd(iso), gewaehlt: S.auswahl.includes(iso) } }; }).filter(Boolean));
  }
  ebene({ id: "boerse", name: "Börsenplätze, Leitindizes und Renditen", gruppe: "Börse & Finanzen", an: !!BW, geplant: !BW, formen: ["boerse"],
    quellen: m => { m.addSource("bo-platz", { type: "geojson", data: platzPunkte() }); m.addSource("bo-land", { type: "geojson", data: boLandPunkte() }); },
    schichten: (m, vor) => {
      schicht("boerse", { id: "bo-flaeche", type: "fill", source: "laender", paint: { "fill-color": raumFuellFarbe(), "fill-opacity": ["interpolate", ["linear"], ["zoom"], 2.2, raumDeckkraft(), 2.7, 0] } }, vor);
      schicht("boerse", { id: "bo-kreis", type: "circle", source: "bo-platz", paint: {
        "circle-color": ["case", ["==", ["get", "hat"], 0], "#8b95a3", [">=", ["get", "ytdv"], 0], HEX_EXP, HEX_IMP],
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 1, ["step", ["get", "gr"], 3.5, 1e12, 5, 5e12, 7], 5, ["step", ["get", "gr"], 6, 1e12, 8, 5e12, 10]],
        "circle-stroke-color": ["case", ["get", "gewaehlt"], "#ffa828", "#07090c"], "circle-stroke-width": ["case", ["get", "gewaehlt"], 2.2, 1.2],
        "circle-opacity": ["interpolate", ["linear"], ["zoom"], 4.6, 1, 5.2, .35], "circle-stroke-opacity": ["interpolate", ["linear"], ["zoom"], 4.6, 1, 5.2, .35] } });
      schicht("boerse", { id: "bo-platz-t", type: "symbol", source: "bo-platz", maxzoom: ZG[0] + .1, layout: {
        "text-field": ["format", ["get", "stadt"], { "font-scale": 1.05, "text-color": "#e8ecf1" }, "\n", {}, ["get", "index"], { "text-color": "#8b95a3", "font-scale": .88 }, " ", {}, ["get", "ytd"], { "text-color": ["case", ["==", ["get", "hat"], 0], "#8b95a3", [">=", ["get", "ytdv"], 0], HEX_EXP, HEX_IMP], "font-scale": .88 }],
        "text-font": ["Noto Sans Regular"], "text-size": 11, "text-line-height": 1.15, "text-variable-anchor": ["top", "bottom", "left", "right"], "text-radial-offset": .9, "text-padding": 2,
        "symbol-sort-key": ["-", 0, ["get", "gr"]] }, paint: { "text-halo-color": "#07090c", "text-halo-width": 1.4, "text-opacity": ["interpolate", ["linear"], ["zoom"], 2.2, 1, 2.6, 0] } });
      schicht("boerse", { id: "bo-land-t", type: "symbol", source: "bo-land", minzoom: ZG[0] - .2, maxzoom: ZG[1] + .4, layout: {
        "text-field": ["format", ["get", "name"], { "text-color": ["case", ["get", "gewaehlt"], "#ffa828", "#e8ecf1"], "font-scale": 1.12 }, "\n", {}, ["get", "idx"], { "text-color": "#8b95a3" }, " ", {},
          ["get", "ytd"], { "text-color": ["case", [">=", ["get", "ytdv"], 0], HEX_EXP, HEX_IMP] }, "\n", {}, ["get", "r10"], { "text-color": "#c3cad3" }],
        "text-font": ["Noto Sans Regular"], "text-size": 10.5, "text-line-height": 1.2, "text-padding": 2, "symbol-sort-key": ["-", 0, ["get", "gr"]] },
        paint: { "text-halo-color": "#07090c", "text-halo-width": 1.3, "text-opacity": ["interpolate", ["linear"], ["zoom"], ZG[0] - .2, 0, ZG[0] + .2, 1] } });
    },
    klick: (e, m) => { const f = m.queryRenderedFeatures(e.point, { layers: ["bo-kreis"].filter(i => m.getLayer(i)) }); if (!f.length) return false;
      const iso = f[0].properties.iso; if (e.originalEvent && e.originalEvent.shiftKey) landUmschalten(iso); else landWaehlen(iso, { fliegen: S.stufe < 2 }); return true; } });
  const bmAktiv = () => S.bm !== "index" && typeof FNZ !== "undefined" && FNZ.makroDa();
  /* Messgröße: Länder nach dem gewählten Wert einfärben, sonst Wirtschaftsraum-Farben */
  function bmFarbe() {
    if (!bmAktiv()) return raumFuellFarbe();
    const w = FNZ.messWerte(S.bm), e = ["match", ["get", "iso"]];
    Object.entries(w).forEach(([i, x]) => { e.push(i, FNZ.messFarbe(S.bm, x.v)); });
    if (e.length === 2) return raumFuellFarbe();
    e.push("rgba(0,0,0,0)");
    return e;
  }
  function boerseAnwenden() {
    if (!map) return;
    if (map.getLayer("bo-flaeche")) { map.setPaintProperty("bo-flaeche", "fill-color", bmFarbe()); map.setPaintProperty("bo-flaeche", "fill-opacity", bmAktiv() ? ["interpolate", ["linear"], ["zoom"], 2.2, .85, 4.5, .5] : ["interpolate", ["linear"], ["zoom"], 2.2, raumDeckkraft(), 2.7, 0]); }
    if (map.getSource("bo-platz")) map.getSource("bo-platz").setData(platzPunkte());
    if (map.getSource("bo-land")) map.getSource("bo-land").setData(boLandPunkte());
  }
  /* Stufe 3: börsennotierte Unternehmen am Sitz, gefärbt nach Kursentwicklung seit Jahresbeginn (Wochenkurse des Terminals) */
  let PERF = null;
  function perfBerechnen() {
    if (PERF) return PERF;
    PERF = {};
    const k = typeof UNT !== "undefined" && UNT.korr ? UNT.korr() : null; if (!k) return PERF;
    const jahr = String(new Date().getFullYear());
    for (const p of PUNKTE) {
      if (p.properties.notiert !== 1 || p.properties.art !== "t") continue;
      const f = UNT.nachId(p.properties.id), h = f && k.kurse(f); if (!h || !h.kurse || h.kurse.length < 2) continue;
      const l = h.kurse, letzt = l[l.length - 1], vor = [...l].reverse().find(x => String(x[0]) < jahr);
      if (vor && letzt && vor[1] > 0 && String(letzt[0]) >= jahr) PERF[p.properties.id] = letzt[1] / vor[1] - 1;
    }
    PUNKTE.forEach(p => { const v = PERF[p.properties.id]; p.properties.perf = v == null ? -9 : Math.round(v * 1000) / 1000; });
    return PERF;
  }
  const perfFarbe = ["case", ["==", ["get", "perf"], -9], "#8b95a3", [">=", ["get", "perf"], .2], "#1f9d55", [">=", ["get", "perf"], 0], HEX_EXP, [">=", ["get", "perf"], -.2], HEX_IMP, "#b02a2a"];

  /* ===== Unternehmen (1A Dichte je Land bzw. Raum, 2A Sitze mit Filtern, 3A Netz, Profil und Nachbarländer) ===== */
  const UN_LAND = {};    // ISO -> { n, notiert, br: { Branche: n } } aus der ganzen Unternehmenstabelle (auch ohne Ort)
  function unLandBauen() {
    if (Object.keys(UN_LAND).length || !TABELLE) return UN_LAND;
    const sp = TABELLE.spalten, j = n => sp.indexOf(n), li = n => TABELLE.listen[n];
    const jl = j("land"), jb = j("branche"), jn = j("notiert");
    for (const z of TABELLE.zeilen) {
      const iso = z[jl]; if (!iso) continue;
      const e = UN_LAND[iso] || (UN_LAND[iso] = { n: 0, notiert: 0, br: {} });
      e.n++;
      const b0 = li("branche") ? li("branche")[z[jb]] : z[jb], b = b0 ? UNT.brName(b0) : ""; if (b) e.br[b] = (e.br[b] || 0) + 1;
      if ((li("notiert") ? li("notiert")[z[jn]] : z[jn]) === "ja") e.notiert++;
    }
    const b = BD();
    if (b) for (const u of b.unternehmen || []) { const iso = isoAusName(u.land); if (!iso || !u.boerswert) continue;
      const e = UN_LAND[iso] || (UN_LAND[iso] = { n: 0, notiert: 0, br: {} }); e.wert = (e.wert || 0) + u.boerswert; e.wn = (e.wn || 0) + 1; }
    return UN_LAND;
  }
  const NAME_ISO = {};
  function isoAusName(n) {
    if (!n) return null;
    if (!Object.keys(NAME_ISO).length) { Object.values(NACH_ISO).forEach(f => { NAME_ISO[f.properties.name] = f.properties.iso; if (f.properties.name_en) NAME_ISO[f.properties.name_en] = f.properties.iso; });
      Object.assign(NAME_ISO, { USA: "US", "Vereinigte Staaten": "US", "Vereinigtes Königreich": "GB", "Großbritannien": "GB", "Südkorea": "KR", "Tschechien": "CZ", "Niederlande": "NL", "Hongkong": "HK", "Taiwan": "TW" }); }
    return NAME_ISO[n] || null;
  }
  function unKreisPunkte() {
    const d = unLandBauen(), wert = S.u1 === "wert";
    return wertFC(Object.entries(d).filter(([iso, e]) => NACH_ISO[iso] && (wert ? e.wert : e.n)).map(([iso, e]) => ({ type: "Feature", geometry: { type: "Point", coordinates: mitte(iso) },
      properties: { iso, name: landKurz(iso), v: wert ? e.wert : e.n, t: wert ? f0.format(e.wert / 1000) + " Bio. $" : f0.format(e.n), raum: RAUM_VON[iso] || "", gewaehlt: S.auswahl.includes(iso) || (!!S.raum && RAUM_VON[iso] === S.raum) } })));
  }
  ebene({ id: "undichte", name: "Unternehmen je Land (Zahl oder Börsenwert)", gruppe: "Unternehmen", an: !!TABELLE, geplant: !TABELLE, formen: ["unternehmen"],
    quellen: m => m.addSource("un-kreis", { type: "geojson", data: unKreisPunkte() }),
    schichten: (m, vor) => {
      schicht("undichte", { id: "un-flaeche", type: "fill", source: "laender", paint: { "fill-color": raumFuellFarbe(), "fill-opacity": ["interpolate", ["linear"], ["zoom"], 2.2, raumDeckkraft(), 2.7, 0] } }, vor);
      schicht("undichte", { id: "un-kreis", type: "circle", source: "un-kreis", maxzoom: ZG[0] + .4, paint: {
        "circle-color": "rgba(255,168,40,.25)", "circle-stroke-color": ["case", ["get", "gewaehlt"], "#ffffff", "#ffa828"], "circle-stroke-width": ["case", ["get", "gewaehlt"], 2, 1.2],
        "circle-radius": ["interpolate", ["linear"], ["sqrt", ["get", "v"]], 0, 2, 10, 5, 40, 12, 100, 26],
        "circle-opacity": ["interpolate", ["linear"], ["zoom"], 2.2, 1, 2.8, 0], "circle-stroke-opacity": ["interpolate", ["linear"], ["zoom"], 2.2, 1, 2.8, 0] } });
      schicht("undichte", { id: "un-kreis-t", type: "symbol", source: "un-kreis", maxzoom: ZG[0] + .4, layout: { "text-field": ["format", ["get", "name"], { "font-scale": .95, "text-color": "#c3cad3" }, "\n", {}, ["get", "t"], { "text-color": "#ffe2b5" }],
        "text-font": ["Noto Sans Bold"], "text-size": 10.5, "text-line-height": 1.15, "text-padding": 3, "symbol-sort-key": ["-", 0, ["get", "v"]] },
        paint: { "text-halo-color": "#07090c", "text-halo-width": 1.3, "text-opacity": ["interpolate", ["linear"], ["zoom"], 2.2, 1, 2.6, 0] } });
    } });
  function unAnwenden() { if (map && map.getSource("un-kreis")) map.getSource("un-kreis").setData(unKreisPunkte()); }
  // Filter der Sitze (Stufe 2): Branche, Index, nur börsennotiert, nur mit Kennzahlen
  const UF = { branche: "", index: "", notiert: false, kennzahlen: false };
  let IDX_VON = null;
  function indexVon(id) {
    if (!IDX_VON) { IDX_VON = {}; if (TABELLE) { const sp = TABELLE.spalten, ji = sp.indexOf("index"), jid = sp.indexOf("id"), jk = sp.indexOf("k"), li = TABELLE.listen.index;
      for (const z of TABELLE.zeilen) { const v = li ? li[z[ji]] : z[ji]; if (v) { if (z[jid]) IDX_VON[z[jid]] = v; if (z[jk]) IDX_VON[z[jk]] = v; } } } }
    return IDX_VON[id] || "";
  }
  const ufAktiv = () => !!(UF.branche || UF.index || UF.notiert || UF.kennzahlen);
  function ufPasst(p) {
    if (UF.notiert && p.notiert !== 1) return false;
    if (UF.kennzahlen && p.art !== "t") return false;
    if (UF.branche && p.branche !== UF.branche) return false;
    if (UF.index && !indexVon(p.id).split(/[,;] */).includes(UF.index)) return false;
    return true;
  }
  function ufBlock() {
    const br = {}, ix = {};
    PUNKTE.forEach(p => { if (p.properties.branche) br[p.properties.branche] = (br[p.properties.branche] || 0) + 1; indexVon(p.properties.id).split(/[,;] */).filter(Boolean).forEach(i => { ix[i] = (ix[i] || 0) + 1; }); });
    const opt = (o, w) => Object.entries(o).sort((a, b) => b[1] - a[1]).map(([k, n]) => `<option value="${esc(k)}"${k === w ? " selected" : ""}>${esc(k)} (${f0.format(n)})</option>`).join("");
    const n = PUNKTE.filter(p => ufPasst(p.properties)).length;
    return `<div class="gk-block"><h3>Filter für die Sitze</h3>
      <label class="gk-filter">Branche <select data-gkuf="branche"><option value="">alle</option>${opt(br, UF.branche)}</select></label>
      <label class="gk-filter">Index <select data-gkuf="index"><option value="">alle</option>${opt(ix, UF.index)}</select></label>
      <div class="gk-chips" style="margin-top:6px"><button type="button" data-gkufk="notiert" aria-pressed="${UF.notiert}">nur börsennotiert</button><button type="button" data-gkufk="kennzahlen" aria-pressed="${UF.kennzahlen}">nur mit Kennzahlen</button>${ufAktiv() ? `<button type="button" data-gkufk="">Filter zurücksetzen</button>` : ""}</div>
      <p class="gk-quelle" style="margin-top:6px">${f0.format(n)} von ${f0.format(PUNKTE.length)} Unternehmen mit Ort passen. Shift+Klick auf Unternehmen nimmt sie in den Vergleich und öffnet die Fenster nebeneinander. Größe nach Umsatz ist noch offen (nur für Unternehmen mit Kennzahlen vorhanden).</p></div>`;
  }
  // Zoomgrenze der Sitze: in der Darstellung Unternehmen schon ab Stufe 2, sonst ab Stufe 3
  function untZoom() {
    if (!map || !map.getLayer("unt-cluster")) return;
    const ab = S.form === "unternehmen" ? ZG[0] : ZG[1], op = ["interpolate", ["linear"], ["zoom"], ab, 0, ab + .5, 1];
    ["unt-land-ring", "unt-land-zahl", "unt-cluster", "unt-anzahl", "unt-punkt"].forEach(id => { if (map.getLayer(id)) map.setLayerZoomRange(id, ab, 24); });
    ["unt-land-ring", "unt-cluster"].forEach(id => { map.setPaintProperty(id, "circle-opacity", op); map.setPaintProperty(id, "circle-stroke-opacity", op); });
    if (S.form === "boerse") { perfBerechnen(); map.setPaintProperty("unt-punkt", "circle-color", perfFarbe); }
    else map.setPaintProperty("unt-punkt", "circle-color", ["case", ["==", ["get", "notiert"], 1], "#ffa828", "#2f86dd"]);
  }
  function nachbarFirmenBlock(iso) {
    const nb = nachbarnVon(iso).filter(i => NACH_ISO[i]); if (!nb.length) return "";
    const d = unLandBauen();
    const zeilen = nb.map(i => ({ i, e: d[i] || { n: 0, notiert: 0 }, top: firmenImLand(i).filter(f => !f.stub).slice(0, 3) })).sort((a, b) => b.e.n - a.e.n);
    return `<div class="gk-block"><h3>Unternehmen in den Nachbarländern</h3><table class="gk-tab"><thead><tr><th>Land</th><th style="text-align:right">erfasst</th><th style="text-align:right">notiert</th></tr></thead><tbody>
      ${zeilen.map(z => `<tr><td><button type="button" class="gk-link" data-gkland="${esc(z.i)}">${esc(landName(z.i))}</button>${z.top.length ? `<br><span class="pct">${z.top.map(f => `<button type="button" class="gk-link" data-gkfirma="${esc(f.id)}">${esc(UNT.kurzName(f.name))}</button>`).join(", ")}</span>` : ""}</td><td>${f0.format(z.e.n)}</td><td>${f0.format(z.e.notiert)}</td></tr>`).join("")}</tbody></table>
      <p class="gk-quelle" style="margin-top:6px">Auf der Karte erscheinen in Stufe 3 auch die Sitze in den Nachbarländern. Zahlen aus der Unternehmenstabelle (auch Unternehmen ohne bekannten Ort).</p></div>`;
  }

  /* ===== Politik & Wahlen (1A Ausrichtung, Wahlkalender, Bündnisse; 2A Wer regiert, wann wird gewählt; 3A Regionen) =====
     Daten: data/politik.json (politik_daten.py: Wikidata, Wikipedia-Wahlkalender, Bundeswahlleiterin, DAWUM) und
     geo/de_laender.geojson (Natural Earth). */
  const PD = roh("politik-daten");
  const DE_GEO = roh("de-laender-geo");
  // Parlamente aller Staaten und der Gliedstaaten (parlamente_daten.py: IPU Parline, Wikipedia, Wikidata) und deren Umrisse
  const PA = roh("parlamente-daten");
  const GL_GEO = roh("gliedstaaten-geo");
  // Grenzen für die Wahlansicht (src/wahlen.js): Kommunen NRW (kommunal_flaechen.py) und Bundestagswahlkreise (wahlkreise_daten.py)
  const KO_GEO = roh("kommunen-geo");
  const WK = roh("wahlkreise-bund");
  const TYP_NAME = { einkammer: "Einkammerparlament", unterhaus: "Unterhaus", oberhaus: "Oberhaus", kammer: "Kammer" };
  const kammernVon = iso => PA && PA.staaten && PA.staaten[iso] ? PA.staaten[iso].kammern : [];
  const gliedVon = iso => PA && PA.gliedstaaten ? PA.gliedstaaten[iso] || null : null;
  const gliedstaat = code => { const g = code && gliedVon(code.slice(0, 2)); return g ? g[code] || null : null; };
  const SCHWELLE = PA ? PA.schwelle_tage || 30 : 30;
  // Sitze einer Kammer: heutige Zusammensetzung (Wikipedia-Infobox), sonst Ergebnis der letzten Wahl (IPU Parline)
  function sitzeVon(k) {
    if (!k) return null;
    if (k.aktuell && k.aktuell.sitze && k.aktuell.sitze.length) return { l: k.aktuell.sitze.map(g => ({ p: g.partei, n: g.sitze, f: g.farbe, r: g.regierung })), quelle: "aktuell" };
    if (k.wahl && k.wahl.sitze && k.wahl.sitze.length) {
      const rt = (k.wahl.regierung_text || "").toLowerCase();
      const inReg = p => { if (!rt) return null; const kurz = (p.match(/\(([^)]+)\)\s*$/) || [])[1]; return rt.includes(p.toLowerCase()) || (kurz ? rt.includes(kurz.toLowerCase()) : false); };
      return { l: k.wahl.sitze.filter(x => x[1] != null).map(x => ({ p: x[0], n: x[1], f: x[2], r: inReg(x[0]) })), quelle: "wahl" };
    }
    return null;
  }
  const staerkste = k => { const s = sitzeVon(k); return s ? [...s.l].filter(g => g.p !== "vakant").sort((a, b) => b.n - a.n)[0] || null : null; };
  // Wahlen der letzten SCHWELLE Tage: Kammern (parlamente.json) und nationaler Wahlkalender (politik.json, auch Präsidentschaftswahlen)
  function juengstNational(iso) {
    const k = PA && PA.juengst ? PA.juengst.filter(j => j.iso === iso && !j.region) : [];
    const w = PD && PD.wahlen_juengst ? (PD.wahlen_juengst[iso] || []) : [];
    const nah = (a, b) => Math.abs(Date.parse(a) - Date.parse(b)) <= 3 * 864e5;   // Wahlkalender und IPU weichen bei Stichwahlen um Tage ab
    const out = w.map(x => ({ datum: x.datum, was: x.was, url: x.url, status: (k.find(j => nah(j.datum, x.datum)) || {}).ergebnis || "" }));
    k.forEach(j => { if (!out.some(o => nah(o.datum, j.datum))) out.push({ datum: j.datum, was: j.kammer, url: j.url, status: j.ergebnis }); });
    return out.sort((a, b) => b.datum.localeCompare(a.datum));
  }
  const tageSeit = d => Math.round((Date.now() - Date.parse(d + "T12:00:00Z")) / 864e5);
  const parteiFarbeGlied = g => { if (!g) return "#8b95a3"; const c = g.regierungschef; if (c && c.farbe) return c.farbe;
    const k = g.kammern && g.kammern[0], s = sitzeVon(k); if (!s) return "#8b95a3"; const r = s.l.filter(x => x.r).sort((a, b) => b.n - a.n)[0] || staerkste(k); return (r && r.f) || "#8b95a3"; };
  const AUSR = [["links", "links", "#d9534f"], ["mitte-links", "Mitte-links", "#e8968f"], ["mitte", "Mitte", "#d8c27a"], ["mitte-rechts", "Mitte-rechts", "#8fb3e0"], ["rechts", "rechts", "#3d6fb6"]];
  const AUSR_FARBE = Object.fromEntries(AUSR.map(a => [a[0], a[2]]));
  const regVon = iso => PD && PD.regierungen ? PD.regierungen[iso] || null : null;
  const JAHR_JETZT = String(new Date().getFullYear());
  const wahlenVon = iso => PD && PD.wahlen ? (PD.wahlen[iso] || []).filter(w => w.datum !== JAHR_JETZT) : [];
  const BUENDNISSE = PD ? PD.buendnisse : [];
  const buendnis = id => BUENDNISSE.find(b => b.id === id);
  const PARTEI_FARBE = [[/Christlich Demokratische|^CDU/, "#6b6b6b", "CDU"], [/Christlich-Soziale|^CSU/, "#2f6db5", "CSU"], [/Sozialdemokratische|^SPD/, "#e3000f", "SPD"], [/Grünen|^Grüne|GRÜNE/, "#46962b", "Grüne"],
    [/Linke/, "#be3075", "Linke"], [/Alternative für|^AfD/, "#00a2de", "AfD"], [/Freie Demokratische|^FDP/, "#ffd600", "FDP"], [/Wagenknecht|^BSW/, "#7d254f", "BSW"], [/Freie Wähler/, "#f39200", "FW"], [/SSW|Südschleswig/, "#003c8f", "SSW"]];
  const parteiInfo = n => { const t = PARTEI_FARBE.find(([r]) => r.test(n || "")); return t ? { farbe: t[1], kurz: t[2] } : { farbe: "#8b95a3", kurz: n || "" }; };
  const datumWahl = d => !d ? "" : /^\d{4}-\d{2}-\d{2}$/.test(d) ? `${d.slice(8)}.${d.slice(5, 7)}.${d.slice(0, 4)}` : /^\d{4}-\d{2}$/.test(d) ? `${d.slice(5)}/${d.slice(0, 4)}` : d;
  const nachname = n => { if (!n) return ""; const t = n.split(" "); return t.length > 1 && !/^(Mohammed|Salman|Tamim|Abdullah|Hassan|Mohammad)/.test(n) ? t[t.length - 1] : n; };
  function polFarbe() {
    const e = PD ? Object.entries(PD.regierungen || {}).flatMap(([i, r]) => [i, r.ausrichtung ? AUSR_FARBE[r.ausrichtung] : "#3a4655"]) : [];
    return e.length ? ["match", ["get", "iso"], ...e, "#2a313b"] : "#2a313b";
  }
  function polDeckkraft() {
    const b = buendnis(S.buendnis), mit = b ? b.mitglieder : null;
    const basis = mit ? ["case", ["in", ["get", "iso"], ["literal", mit]], .62, .1] : .5;
    return ["interpolate", ["linear"], ["zoom"], ZG[1] - .3, basis, ZG[1] + .3, .14];
  }
  function polPunkte() {
    if (!PD) return leerFC;
    const b = buendnis(S.buendnis);
    return wertFC(LAENDER_PUNKTE.features.map(f => { const iso = f.properties.iso, r = regVon(iso), w = wahlenVon(iso);
      if (!r && !w.length && !juengstNational(iso).length) return null;
      const h = r && (r.regierungschef || r.staatsoberhaupt), pk = h && (h.partei_kurz || (h.partei && h.partei.length <= 14 ? h.partei : ""));
      const jn = juengstNational(iso);
      return { type: "Feature", geometry: f.geometry, properties: { iso, name: landKurz(iso), chef: h ? nachname(h.name) + (pk ? ` (${pk})` : "") : "", wahl: w.length ? "Wahl " + datumWahl(w[0].datum) : "",
        neu: jn.length ? 1 : 0, neuTxt: jn.length ? "gewählt am " + datumWahl(jn[0].datum) : "",
        hatWahl: w.length ? 1 : 0, gr: bipUsd(iso), imB: b ? (b.mitglieder.includes(iso) ? 1 : 0) : 1, gewaehlt: S.auswahl.includes(iso) } }; }).filter(Boolean));
  }
  function deLaenderDaten() {
    if (!DE_GEO || !PD || !PD.deutschland) return leerFC;
    const lr = PD.deutschland.landesregierungen || {};
    return { type: "FeatureCollection", features: DE_GEO.features.map((f, i) => { const r = lr[f.properties.code] || {}, pi = parteiInfo((r.parteien || [])[0]);
      const g = gliedstaat(f.properties.code), neu = g && g.kammern.some(k => k.juengst);
      return { ...f, id: i + 1, properties: { ...f.properties, mp: r.regierungschef || "", partei: pi.kurz, farbe: pi.farbe, neu: !!neu, gewaehlt: S.region === f.properties.code } }; }) };
  }
  function deLaenderPunkte() {
    const d = deLaenderDaten();
    return wertFC(d.features.map(f => { let sx = 0, sy = 0, n = 0; f.geometry.coordinates.forEach(poly => poly[0].forEach(([x, y]) => { sx += x; sy += y; n++; }));
      const lage = { "DE-BB": [13.4, 52.0], "DE-BE": [13.4, 52.52], "DE-HB": [8.8, 53.08], "DE-HH": [10.0, 53.55], "DE-NI": [9.4, 52.7] }[f.properties.code];
      return { type: "Feature", geometry: { type: "Point", coordinates: lage || [sx / n, sy / n] }, properties: f.properties }; }));
  }
  // Gliedstaaten der übrigen Bundesstaaten (Deutschland hat eigene, genauere Umrisse)
  function gliedDaten() {
    if (!GL_GEO || !PA) return leerFC;
    return { type: "FeatureCollection", features: GL_GEO.features.filter(f => f.properties.iso !== "DE").map((f, i) => { const g = gliedstaat(f.properties.code), c = g && g.regierungschef;
      return { ...f, id: i + 1, properties: { code: f.properties.code, iso: f.properties.iso, name: g ? g.name_de || g.name : f.properties.name, chef: c ? nachname(c.name) : "",
        partei: c ? c.partei_kurz || (c.partei && c.partei.length <= 16 ? c.partei : "") : "", farbe: parteiFarbeGlied(g), neu: !!(g && g.kammern.some(k => k.juengst)), daten: !!g, gewaehlt: S.region === f.properties.code } }; }) };
  }
  function gliedPunkte(d) {
    return wertFC(d.features.map(f => { let best = null, fl = -1; f.geometry.coordinates.forEach(poly => { const r = poly[0]; let a = 0; for (let i = 0; i < r.length - 1; i++) a += r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1]; if (Math.abs(a) > fl) { fl = Math.abs(a); best = r; } });
      let sx = 0, sy = 0; best.forEach(([x, y]) => { sx += x; sy += y; });
      return { type: "Feature", geometry: { type: "Point", coordinates: [sx / best.length, sy / best.length] }, properties: f.properties }; }));
  }
  ebene({ id: "politik", name: "Regierungen, Parlamente, Bündnisse, Gliedstaaten", gruppe: "Politik & Wahlen", an: !!PD, geplant: !PD, formen: ["politik"], ansicht: "regierungen",
    quellen: m => { m.addSource("po-land", { type: "geojson", data: polPunkte() }); m.addSource("po-de", { type: "geojson", data: deLaenderDaten() }); m.addSource("po-de-pkt", { type: "geojson", data: deLaenderPunkte() });
      const gd = gliedDaten(); m.addSource("po-gl", { type: "geojson", data: gd }); m.addSource("po-gl-pkt", { type: "geojson", data: gliedPunkte(gd) }); },
    schichten: (m, vor) => {
      schicht("politik", { id: "po-flaeche", type: "fill", source: "laender", paint: { "fill-color": polFarbe(), "fill-opacity": polDeckkraft() } }, vor);
      schicht("politik", { id: "po-de-flaeche", type: "fill", source: "po-de", minzoom: ZG[1] - .4, paint: { "fill-color": ["get", "farbe"], "fill-opacity": ["interpolate", ["linear"], ["zoom"], ZG[1] - .4, 0, ZG[1], ["case", ["get", "gewaehlt"], .6, .38]] } }, vor);
      schicht("politik", { id: "po-de-linie", type: "line", source: "po-de", minzoom: ZG[1] - .4, paint: { "line-color": ["case", ["any", ["get", "gewaehlt"], ["get", "neu"]], "#ffa828", "#c3cad3"], "line-width": ["case", ["get", "gewaehlt"], 2, ["get", "neu"], 1.6, .7], "line-opacity": .8 } });
      schicht("politik", { id: "po-gl-flaeche", type: "fill", source: "po-gl", minzoom: ZG[1] - .4, paint: { "fill-color": ["get", "farbe"], "fill-opacity": ["interpolate", ["linear"], ["zoom"], ZG[1] - .4, 0, ZG[1], ["case", ["get", "gewaehlt"], .6, ["get", "daten"], .36, .12]] } }, vor);
      schicht("politik", { id: "po-gl-linie", type: "line", source: "po-gl", minzoom: ZG[1] - .4, paint: { "line-color": ["case", ["any", ["get", "gewaehlt"], ["get", "neu"]], "#ffa828", "#c3cad3"], "line-width": ["case", ["get", "gewaehlt"], 2, ["get", "neu"], 1.6, .5], "line-opacity": .7 } });
      schicht("politik", { id: "po-gl-t", type: "symbol", source: "po-gl-pkt", minzoom: ZG[1] + .3, layout: {
        "text-field": ["format", ["get", "name"], { "text-color": ["case", ["get", "gewaehlt"], "#ffa828", ["get", "neu"], "#ffa828", "#e8ecf1"], "font-scale": 1.02 }, "\n", {}, ["get", "chef"], { "text-color": "#c3cad3", "font-scale": .88 }, " ", {}, ["get", "partei"], { "text-color": "#8b95a3", "font-scale": .88 }],
        "text-font": ["Noto Sans Regular"], "text-size": 10.5, "text-line-height": 1.15, "text-padding": 3, "text-max-width": 9 },
        paint: { "text-halo-color": "#07090c", "text-halo-width": 1.3, "text-opacity": ["interpolate", ["linear"], ["zoom"], ZG[1] + .3, 0, ZG[1] + .7, 1] } });
      schicht("politik", { id: "po-wahl", type: "circle", source: "po-land", filter: ["==", ["get", "hatWahl"], 1], maxzoom: ZG[1], paint: {
        "circle-color": "#9fd3ff", "circle-radius": ["interpolate", ["linear"], ["zoom"], 1, 5, 4, 8], "circle-stroke-color": "#07090c", "circle-stroke-width": 1.2,
        "circle-translate": [0, -14], "circle-opacity": ["case", ["==", ["get", "imB"], 1], 1, .25] } });
      schicht("politik", { id: "po-neu", type: "circle", source: "po-land", filter: ["==", ["get", "neu"], 1], maxzoom: ZG[1], paint: {
        "circle-color": "#ffa828", "circle-radius": ["interpolate", ["linear"], ["zoom"], 1, 5, 4, 8], "circle-stroke-color": "#07090c", "circle-stroke-width": 1.2,
        "circle-translate": [-17, -14], "circle-opacity": ["case", ["==", ["get", "imB"], 1], 1, .25] } });
      schicht("politik", { id: "po-neu-t", type: "symbol", source: "po-land", filter: ["==", ["get", "neu"], 1], maxzoom: ZG[1], layout: { "text-field": "N", "text-font": ["Noto Sans Bold"],
        "text-size": ["interpolate", ["linear"], ["zoom"], 1, 7, 4, 10], "text-allow-overlap": true, "text-ignore-placement": true }, paint: { "text-color": "#07090c", "text-translate": [-17, -14], "text-opacity": ["case", ["==", ["get", "imB"], 1], 1, .25] } });
      schicht("politik", { id: "po-wahl-t", type: "symbol", source: "po-land", filter: ["==", ["get", "hatWahl"], 1], maxzoom: ZG[1], layout: { "text-field": "W", "text-font": ["Noto Sans Bold"],
        "text-size": ["interpolate", ["linear"], ["zoom"], 1, 7, 4, 10], "text-allow-overlap": true, "text-ignore-placement": true, "text-offset": [0, -1.25] }, paint: { "text-color": "#07090c", "text-opacity": ["case", ["==", ["get", "imB"], 1], 1, .25] } });
      schicht("politik", { id: "po-land-t", type: "symbol", source: "po-land", minzoom: ZG[0] - .2, maxzoom: ZG[1] + .2, layout: {
        "text-field": ["format", ["get", "name"], { "text-color": ["case", ["get", "gewaehlt"], "#ffa828", "#e8ecf1"], "font-scale": 1.12 }, "\n", {}, ["get", "chef"], { "text-color": "#c3cad3" }, "\n", {}, ["get", "neuTxt"], { "text-color": "#ffa828" }, ["case", ["==", ["get", "neu"], 1], "\n", ""], {}, ["get", "wahl"], { "text-color": "#9fd3ff" }],
        "text-font": ["Noto Sans Regular"], "text-size": 10.5, "text-line-height": 1.2, "text-padding": 2, "symbol-sort-key": ["-", 0, ["get", "gr"]] },
        paint: { "text-halo-color": "#07090c", "text-halo-width": 1.3, "text-opacity": ["interpolate", ["linear"], ["zoom"], ZG[0] - .2, 0, ZG[0] + .2, 1] } });
      schicht("politik", { id: "po-de-t", type: "symbol", source: "po-de-pkt", minzoom: ZG[1] - .2, layout: {
        "text-field": ["format", ["get", "name"], { "text-color": ["case", ["get", "gewaehlt"], "#ffa828", "#e8ecf1"], "font-scale": 1.08 }, "\n", {}, ["get", "mp"], { "text-color": "#c3cad3", "font-scale": .9 }, " ", {}, ["get", "partei"], { "text-color": "#8b95a3", "font-scale": .9 }],
        "text-font": ["Noto Sans Regular"], "text-size": 11, "text-line-height": 1.15, "text-padding": 2, "text-max-width": 9 },
        paint: { "text-halo-color": "#07090c", "text-halo-width": 1.3, "text-opacity": ["interpolate", ["linear"], ["zoom"], ZG[1] - .2, 0, ZG[1] + .2, 1] } });
    },
    klick: (e, m) => {
      if (S.stufe < 3) return false;
      const f = m.queryRenderedFeatures(e.point, { layers: ["po-de-flaeche", "po-gl-flaeche"].filter(i => m.getLayer(i)) }); if (!f.length) return false;
      const code = f[0].properties.code, iso = code.slice(0, 2);
      S.region = S.region === code ? null : code; if (S.land !== iso) landWaehlen(iso); politikAnwenden(); seiteZeichnen(); return true; } });
  function politikAnwenden() {
    if (!map) return;
    if (map.getSource("po-land")) map.getSource("po-land").setData(polPunkte());
    if (map.getSource("po-de")) map.getSource("po-de").setData(deLaenderDaten());
    if (map.getSource("po-de-pkt")) map.getSource("po-de-pkt").setData(deLaenderPunkte());
    if (map.getSource("po-gl")) { const gd = gliedDaten(); map.getSource("po-gl").setData(gd); map.getSource("po-gl-pkt").setData(gliedPunkte(gd)); }
    if (map.getLayer("po-flaeche")) map.setPaintProperty("po-flaeche", "fill-opacity", polDeckkraft());
  }
  // Tooltips der drei Formen (Kreise der Börsenplätze und der Unternehmensdichte, Wahlsymbole, Bundesländer)
  const INFO_TIPS = {
    "bo-kreis": p => { const x = indexNach(PLAETZE.find(q => q.id === p.id).leitindex);
      return `<b>${esc(p.name)}</b> <span class="pct">${esc(p.stadt)}</span><br>${esc(p.index)}: ${x ? `<span style="color:${farbVz(x.ytd)}">${pctVz(x.ytd)}</span> seit Jahresbeginn · 1 J. ${pctVz(x.r1j)}` : "keine Kurse"}<br><span class="pct">${x ? "Stand " + esc(x.datum) + " · Yahoo Finance · " : ""}klicken für das Land</span>`; },
    "un-kreis": p => { const e = UN_LAND[p.iso] || {}; return `<b>${esc(landName(p.iso))}</b><br>${f0.format(e.n || 0)} Unternehmen erfasst, ${f0.format(e.notiert || 0)} börsennotiert${e.wert ? `<br>Börsenwert der ${f0.format(e.wn)} großen Unternehmen im Bereich BÖR: ${f0.format(e.wert)} Mrd. USD` : ""}`; },
    "po-wahl": p => `<b>${esc(landName(p.iso))}</b><br>${wahlenVon(p.iso).slice(0, 3).map(w => `${esc(datumWahl(w.datum))}: ${esc(w.was)}`).join("<br>")}<br><span class="pct">Wikipedia, nationaler Wahlkalender</span>`,
    "po-de-flaeche": p => `<b>${esc(p.name)}</b><br>${esc(p.mp || "–")}${p.partei ? ` (${esc(p.partei)})` : ""}${p.neu ? `<br><span style="color:#ffa828">Landtag in den letzten ${SCHWELLE} Tagen gewählt</span>` : ""}<br><span class="pct">Regierungschef laut Wikidata · klicken für Landtag, Wahl und Umfrage</span>`,
    "po-gl-flaeche": p => { const g = gliedstaat(p.code), k = g && g.kammern[0], st = staerkste(k);
      return `<b>${esc(p.name)}</b> <span class="pct">${esc(landName(p.iso))}</span><br>${g ? `${esc(g.regierungschef ? g.regierungschef.name : "–")}${p.partei ? ` (${esc(p.partei)})` : ""}${st ? `<br>stärkste Fraktion: ${esc(st.p)} (${f0.format(st.n)})` : ""}` : "keine Daten"}${p.neu ? `<br><span style="color:#ffa828">Parlament in den letzten ${SCHWELLE} Tagen gewählt</span>` : ""}<br><span class="pct">Wikidata, Wikipedia · klicken für Parlament und Wahl</span>`; },
    "po-neu": p => `<b>${esc(landName(p.iso))}: gerade gewählt</b><br>${juengstNational(p.iso).slice(0, 3).map(w => `${esc(datumWahl(w.datum))}: ${esc(w.was)}${w.status ? ` <span class="pct">(Ergebnis ${esc(w.status)})</span>` : ""}`).join("<br>")}<br><span class="pct">Wahlen der letzten ${SCHWELLE} Tage · Wikipedia-Wahlkalender, IPU Parline</span>`,
  };

  /* ===== Seitenleiste der drei Formen ===== */
  const kzKlein = (t, v, z, tip) => `<div${tip ? ` title="${esc(tip)}"` : ""}><div class="t" style="min-height:0">${esc(t)}</div><div class="v" style="font-size:15px">${v}</div><div class="z">${esc(z || "")}</div></div>`;
  function finanzKacheln(iso) {
    const x = leitindex(iso), lz = leitzins(iso), r = rendite10(iso), w = waehrungVon(iso), dv = BW && w && w !== "EUR" ? BW.devisen[w] : null, usd = BW && BW.devisen.USD;
    const wTxt = w === "EUR" ? (usd ? pctVz(usd.usd_ytd != null ? -usd.eur_ytd : null) : "–") : dv ? pctVz(dv.usd_ytd) : "–";
    return `<div class="gk-kz" style="grid-template-columns:1fr 1fr 1fr">${kzKlein(x ? x.name.replace(/ \(ETF.*$/, " (ETF)") : "Leitindex", x ? `<span style="color:${farbVz(x.ytd)}">${pctVz(x.ytd)}</span>` : "–", x ? "seit Jahresbeginn" : "keine Kurse", x ? `Stand ${x.kurs} am ${x.datum}, Yahoo Finance` : "")}
      ${kzKlein("10-j. Rendite", r ? f2.format(r.v) + " %" : "–", r ? zeitDe(r.zeit) : "OECD: keine Angabe", "OECD, langfristige Zinsen")}
      ${kzKlein("Leitzins", lz ? f2.format(lz.v) + " %" : "–", lz ? zeitDe(lz.zeit) + (lz.euro ? " · EZB" : "") : "BIS: keine Angabe", "BIS, Central bank policy rates")}
      ${kzKlein("Währung", esc(w || "–"), w && w !== "USD" ? `${wTxt} zum USD lfd. J.` : "", "EZB-Referenzkurse; positiv = Währung hat zum US-Dollar gewonnen")}</div>`;
  }
  const spark2 = l => { if (!l || l.length < 2) return ""; const ys = l.map(x => x[1]), lo = Math.min(...ys), hi = Math.max(...ys), sp = hi - lo || 1;
    return `<svg viewBox="0 0 100 22" preserveAspectRatio="none" style="width:80px;height:16px;vertical-align:middle" aria-hidden="true"><path d="${l.map((x, i) => `${i ? "L" : "M"}${(i / (l.length - 1) * 100).toFixed(1)},${(21 - (x[1] - lo) / sp * 20).toFixed(1)}`).join("")}" fill="none" stroke="#a3acb8" stroke-width="1.2" vector-effect="non-scaling-stroke"/></svg>`; };
  function boerseWelt() {
    const b = BD(); if (!b || !BW) return `<p class="gk-leer">Keine Börsendaten im Build.</p>`;
    const reg = {}; b.indizes.filter(x => x.kurs != null && x.region && !/ETF|VIX/.test(x.name)).forEach(x => { (reg[x.region] = reg[x.region] || []).push(x); });
    const indTab = Object.entries(reg).map(([r, l]) => `<tr><td colspan="3" class="pct" style="padding-top:6px">${esc(r)}</td></tr>${l.slice(0, r === "Welt" ? 4 : 6).map(x => `<tr><td>${esc(x.name)}</td><td>${f0.format(x.kurs)}</td><td style="color:${farbVz(x.ytd)}">${pctVz(x.ytd)}</td></tr>`).join("")}`).join("");
    const roh = BW.rohstoffe || [];
    const dv = Object.entries(BW.devisen || {}).filter(([w]) => w !== "USD").slice(0, 10);
    const usd = BW.devisen.USD;
    const zins = ["US", "XM", "GB", "JP", "CN", "IN", "BR", "CH", "KR", "TR"].map(i => [i, reiheLetzt(BW.leitzins, i)]).filter(x => x[1]);
    const r10 = ["US", "DE", "GB", "FR", "IT", "JP", "ES", "CA", "AU", "CH"].map(i => [i, reiheLetzt(BW.rendite10, i)]).filter(x => x[1]);
    const nm = i => i === "XM" ? "Euroraum" : landName(i);
    return `<div class="gk-block"><h3>Indizes nach Region</h3><table class="gk-tab"><thead><tr><th>Index</th><th style="text-align:right">Stand</th><th style="text-align:right">lfd. Jahr</th></tr></thead><tbody>${indTab}</tbody></table>
        <p class="gk-quelle" style="margin-top:6px">Schlusskurse über Yahoo Finance (Bereich BÖR), Stand ${esc(String(b.abruf || (b.indizes.find(x => x.datum) || {}).datum || "").slice(0, 10))}.</p></div>
      <div class="gk-block"><h3>Rohstoffe</h3><table class="gk-tab"><tbody>${roh.map(r => `<tr><td><a class="gk-link" href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.name)}</a><br><span class="pct">${esc(r.einheit)} · ${esc(r.datum)}</span></td><td>${f2.format(r.wert)}</td><td style="color:${farbVz(r.ytd)}">${pctVz(r.ytd)}</td><td>${spark2(r.verlauf)}</td></tr>`).join("")}</tbody></table>
        <p class="gk-quelle" style="margin-top:6px">FRED (EIA, IMF-Rohstoffpreise); Veränderung seit Jahresbeginn. Gold ist ohne Schlüssel nicht frei abrufbar (offen).</p></div>
      <div class="gk-block"><h3>Leitwährungen</h3><table class="gk-tab"><thead><tr><th>1 EUR =</th><th style="text-align:right">Kurs</th><th style="text-align:right">zum USD lfd. J.</th></tr></thead><tbody>
        ${usd ? `<tr><td>USD</td><td>${f2.format(usd.je_eur)}</td><td style="color:${farbVz(-usd.eur_ytd)}">EUR ${pctVz(-usd.eur_ytd)}</td></tr>` : ""}${dv.map(([w, d]) => `<tr><td>${esc(w)}</td><td>${f2.format(d.je_eur)}</td><td style="color:${farbVz(d.usd_ytd)}">${pctVz(d.usd_ytd)}</td></tr>`).join("")}</tbody></table>
        <p class="gk-quelle" style="margin-top:6px">EZB-Referenzkurse, Stand ${esc(usd ? usd.datum : "")}. Rechte Spalte: Wertveränderung der Währung gegenüber dem US-Dollar seit Jahresbeginn.</p></div>
      <div class="gk-block"><h3>Leitzinsen und 10-jährige Renditen</h3><div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
        <table class="gk-tab"><tbody>${zins.map(([i, z]) => `<tr><td><button type="button" class="gk-link" data-gkland="${esc(i === "XM" ? "DE" : i)}">${esc(nm(i))}</button></td><td>${f2.format(z.v)}</td></tr>`).join("")}</tbody></table>
        <table class="gk-tab"><tbody>${r10.map(([i, z]) => `<tr><td><button type="button" class="gk-link" data-gkland="${esc(i)}">${esc(nm(i))}</button></td><td>${f2.format(z.v)}</td></tr>`).join("")}</tbody></table></div>
        <p class="gk-quelle" style="margin-top:6px">Links Leitzins (BIS, Monatsende ${esc(zins.length ? zeitDe(zins[0][1].zeit) : "")}), rechts Rendite langfristiger Staatsanleihen (OECD, ${esc(r10.length ? zeitDe(r10[0][1].zeit) : "")}). Außerhalb der OECD offen.</p></div>`;
  }
  function bmChips() {
    if (typeof FNZ === "undefined" || !FNZ.makroDa()) return "";
    const l = [["index", "Leitindex lfd. Jahr"]].concat(FNZ.mess().map(m => [m.id, m.name.replace(/ \(.*$/, "")]));
    const d = S.bm !== "index" ? FNZ.mess().find(m => m.id === S.bm) : null, w = d ? Object.keys(FNZ.messWerte(S.bm)).length : 0;
    return `<div class="gk-block"><h3>Karte einfärben nach</h3><div class="gk-chips">${l.map(([id, n]) => `<button type="button" data-gkbm="${esc(id)}" aria-pressed="${S.bm === id}">${esc(n)}</button>`).join("")}</div>
      ${d ? `<p class="gk-quelle" style="margin-top:6px">${esc(d.name)} (${esc(d.einheit)}), ${w} Länder; neuester verfügbarer Wert, Stand je Land im Tooltip der Länderseite. Grau = keine Daten.</p>` : ""}</div>`;
  }
  function boerseStart() {
    const r = raumVon(S.raum);
    const chip = x => `<button type="button" data-gkraum="${esc(x.id)}" aria-pressed="${x.id === S.raum}" style="border-left:3px solid ${esc(x.farbe)}">${esc(x.kurz)}</button>`;
    const raeume = `<div class="gk-block"><h3>Wirtschaftsraum wählen</h3><div class="gk-chips">${RAEUME.map(chip).join("")}</div></div>`;
    if (S.stufe === 1 && r) {
      const mit = r.mitglieder.filter(i => leitindex(i) || rendite10(i) || leitzins(i)).sort((a, b) => bipUsd(b) - bipUsd(a));
      return `<div><div class="gk-chips" style="margin-bottom:8px"><button type="button" data-gkraum="${esc(r.id)}">← Alle Räume</button></div><h2>${esc(r.name)}: Börsen</h2></div>
        <div class="gk-block"><table class="gk-tab"><thead><tr><th>Land</th><th style="text-align:right">Index lfd. J.</th><th style="text-align:right">10J</th><th style="text-align:right">Zins</th></tr></thead><tbody>
        ${mit.map(i => { const x = leitindex(i), y = rendite10(i), z = leitzins(i); return `<tr><td><button type="button" class="gk-link" data-gkland="${esc(i)}">${esc(landName(i))}</button><br><span class="pct">${esc(x ? x.name : "")}</span></td><td style="color:${farbVz(x && x.ytd)}">${x ? pctVz(x.ytd) : "–"}</td><td>${y ? f2.format(y.v) : "–"}</td><td>${z ? f2.format(z.v) : "–"}</td></tr>`; }).join("") || `<tr><td colspan="4" class="gk-leer">Keine Börsendaten für die Mitglieder.</td></tr>`}</tbody></table></div>${raeume}`;
    }
    const puls = typeof FNZ !== "undefined" && FNZ.da() ? `<div class="gk-block"><h3>Marktpuls</h3>${FNZ.leiste()}<p class="gk-quelle" style="margin-top:6px">${esc(FNZ.leisteFuss())} ${FNZ.leisteLive()} <a class="gk-link" href="#b-puls">Zinskurven, Währungen, Sektoren im Terminal ↗</a></p></div>` : "";
    return `<div><h2>Börsen und Finanzmärkte</h2><p class="unter" style="margin-top:4px">${S.stufe === 1 ? "Kreise an den Börsenplätzen: Leitindex seit Jahresbeginn (grün gestiegen, rot gefallen) · Land anklicken wählt den Wirtschaftsraum · hineinzoomen für Werte je Land" : "Je Land Leitindex seit Jahresbeginn und 10-jährige Rendite · Land anklicken für alles · Shift+Klick für mehrere Länder"}</p></div>${bmChips()}${puls}${boerseWelt()}${S.stufe === 1 ? raeume : ""}`;
  }
  function bankenBlock(iso) {
    if (iso !== "DE" || typeof BANKEN === "undefined" || !BANKEN) return `<div class="gk-block"><h3>Banken</h3><p class="gk-leer">Bankdaten (Bilanzsumme, Kernkapitalquote) gibt es bisher nur für deutsche Banken (Bankenvergleich).</p></div>`;
    const l = BANKEN.filter(b => b.bs).sort((a, b) => b.bs - a.bs).slice(0, 15);
    return `<div class="gk-block"><h3>Größte Banken (Bankenvergleich)</h3><table class="gk-tab"><thead><tr><th>Bank</th><th style="text-align:right">Bilanzsumme Mrd. €</th><th style="text-align:right">CET1</th></tr></thead><tbody>
      ${l.map(b => `<tr><td title="${esc(b.bank)}">${esc(b.bank.replace(/ (Aktiengesellschaft|AG|SE|eG)$/, "").replace(/ Girozentrale$/, "").slice(0, 30))}</td><td>${f1.format(b.bs / 1000)}</td><td>${b.cet1_quote != null ? f1.format(b.cet1_quote * 100) + " %" : "–"}</td></tr>`).join("")}</tbody></table>
      <p class="gk-quelle" style="margin-top:6px">HGB-Abschlüsse und Offenlegung (KM1) aus dem Bankenvergleich des Terminals; ${f0.format(BANKEN.length)} Banken erfasst.</p></div>`;
  }
  function indexZusammensetzung(iso) {
    const x = leitindex(iso); if (!x) return "";
    const kurz = x.name.split(" ")[0], l = PUNKTE.filter(p => p.properties.land === iso && indexVon(p.properties.id).split(/[,;] */).some(i => i === x.name || i === kurz));
    if (!l.length) return "";
    const pf = perfBerechnen();
    const z = l.map(p => ({ p: p.properties, v: pf[p.properties.id] })).sort((a, b) => (b.v ?? -9) - (a.v ?? -9));
    return `<div class="gk-block"><h3>${esc(x.name)}: Mitglieder mit Sitz auf der Karte</h3><table class="gk-tab"><thead><tr><th>Unternehmen</th><th style="text-align:right">lfd. Jahr</th></tr></thead><tbody>
      ${z.map(({ p, v }) => `<tr><td><button type="button" class="gk-link" data-gkfirma="${esc(p.id)}">${esc(p.name)}</button></td><td style="color:${farbVz(v)}">${v == null ? "–" : pctVz(v)}</td></tr>`).join("")}</tbody></table>
      <p class="gk-quelle" style="margin-top:6px">Indexzugehörigkeit laut Unternehmenstabelle; Kursentwicklung aus Wochenschlusskursen des Terminals (Yahoo Finance).</p></div>`;
  }
  function boerseLand(iso, stufe) {
    const lz = leitzins(iso), r = rendite10(iso);
    const verlauf = (t, o) => o ? `<tr><td>${esc(t)}</td><td>${f2.format(o.v)} %</td><td>${spark2(o.l.slice(-60))}</td><td class="pct">${esc(zeitDe(o.l[Math.max(0, o.l.length - 60)][0]))}–${esc(zeitDe(o.zeit))}</td></tr>` : "";
    const zinsen = lz || r ? `<div class="gk-block"><h3>Zinsen, fünf Jahre</h3><table class="gk-tab"><tbody>${verlauf(lz && lz.euro ? "Leitzins (EZB)" : "Leitzins", lz)}${verlauf("Rendite 10 Jahre", r)}</tbody></table>
      <p class="gk-quelle" style="margin-top:6px">BIS (Leitzinsen, Monatsende), OECD (langfristige Zinsen, CC BY 4.0).</p></div>` : "";
    const stufe3 = stufe >= 3 ? indexZusammensetzung(iso) + bankenBlock(iso)
      : `<div class="gk-block"><h3>Finanzplatz</h3><p class="gk-leer">Näher heranzoomen (Stufe 3): börsennotierte Unternehmen am Sitz, gefärbt nach Kursentwicklung, Indexmitglieder und Banken.</p><div class="gk-chips" style="margin-top:8px"><button type="button" data-gkstufe="3">Zu Stufe 3</button></div></div>`;
    return `<div class="gk-block"><h3>Finanzdaten</h3>${finanzKacheln(iso)}</div>${zinsen}${typeof FNZ !== "undefined" ? FNZ.landBloecke(iso) : ""}${indizes(iso)}${stufe3}`;
  }
  function unternehmenWelt() {
    const d = unLandBauen(), r = raumVon(S.raum);
    const laender = Object.entries(d).filter(([i]) => !r || r.mitglieder.includes(i));
    const br = {}; let n = 0, no = 0; laender.forEach(([, e]) => { n += e.n; no += e.notiert; Object.entries(e.br).forEach(([b, k]) => { br[b] = (br[b] || 0) + k; }); });
    const top = laender.sort((a, b) => (S.u1 === "wert" ? (b[1].wert || 0) - (a[1].wert || 0) : b[1].n - a[1].n)).slice(0, 12);
    const bt = Object.entries(br).sort((a, b) => b[1] - a[1]).slice(0, 10), max = bt.length ? bt[0][1] : 1;
    const chip = x => `<button type="button" data-gkraum="${esc(x.id)}" aria-pressed="${x.id === S.raum}" style="border-left:3px solid ${esc(x.farbe)}">${esc(x.kurz)}</button>`;
    return `<div>${r ? `<div class="gk-chips" style="margin-bottom:8px"><button type="button" data-gkraum="${esc(r.id)}">← Alle Räume</button></div>` : ""}<h2>${r ? esc(r.name) + ": Unternehmen" : "Unternehmen weltweit"}</h2>
        <p class="unter" style="margin-top:4px">Kreis je Land nach ${S.u1 === "wert" ? "Börsenwert der großen Unternehmen (Bereich BÖR)" : "Zahl der erfassten Unternehmen"} · Land anklicken wählt den Wirtschaftsraum · hineinzoomen für die Sitze</p>
        <div class="gk-chips" style="margin-top:8px"><button type="button" data-gku1="anzahl" aria-pressed="${S.u1 !== "wert"}">Zahl der Unternehmen</button><button type="button" data-gku1="wert" aria-pressed="${S.u1 === "wert"}">Börsenwert</button></div></div>
      <div class="gk-block"><h3>${f0.format(n)} Unternehmen, ${f0.format(no)} börsennotiert</h3><table class="gk-tab"><tbody>
        ${top.map(([i, e]) => `<tr><td><button type="button" class="gk-link" data-gkland="${esc(i)}">${esc(landName(i))}</button></td><td>${S.u1 === "wert" ? (e.wert ? f0.format(e.wert) + " Mrd. $" : "–") : f0.format(e.n)}</td></tr>`).join("")}</tbody></table></div>
      <div class="gk-block"><h3>Branchenmix</h3>${bt.map(([b, k]) => `<div class="gk-balken"><span>${esc(b)}</span><i style="width:${(k / max * 100).toFixed(1)}%"></i><b>${f0.format(k)}</b></div>`).join("")}
        <p class="gk-quelle" style="margin-top:6px">Unternehmenstabelle (alle erfassten Unternehmen, auch ohne bekannten Ort); Börsenwert nur für die ${f0.format((BD() || { unternehmen: [] }).unternehmen.length)} großen Unternehmen des Bereichs BÖR (Yahoo Finance, Mrd. USD).</p></div>
      ${!r ? `<div class="gk-block"><h3>Wirtschaftsraum wählen</h3><div class="gk-chips">${RAEUME.filter(x => x.art !== "uebergreifend").map(chip).join("")}</div></div>` : ""}`;
  }
  function wahlListe(l, mitLand) {
    return l.length ? `<table class="gk-tab"><tbody>${l.map(w => `<tr><td class="pct" style="white-space:nowrap">${esc(datumWahl(w.datum))}</td><td style="font-family:var(--sans);text-align:left;white-space:normal">${mitLand ? `<button type="button" class="gk-link" data-gkland="${esc(w.iso)}">${esc(landName(w.iso))}</button>: ` : ""}${w.url ? `<a class="gk-link" href="${esc(w.url)}" target="_blank" rel="noopener">${esc(w.was)}</a>` : esc(w.was)}</td></tr>`).join("")}</tbody></table>` : `<p class="gk-leer">Keine nationalen Wahlen in den nächsten zwölf Monaten bekannt.</p>`;
  }
  function politikStart() {
    if (!PD) return `<div><h2>Politik & Wahlen</h2><p class="gk-leer">Keine Politikdaten im Build.</p></div>`;
    const b = buendnis(S.buendnis);
    const chips = `<div class="gk-block"><h3>Bündnis wählen</h3><div class="gk-chips">${BUENDNISSE.map(x => `<button type="button" data-gkbund="${esc(x.id)}" aria-pressed="${x.id === S.buendnis}" style="border-left:3px solid ${esc(x.farbe)}">${esc(x.kurz)}</button>`).join("")}</div></div>`;
    const leg = `<div class="gk-block"><h3>Ausrichtung der Regierung</h3><div class="gk-chips">${AUSR.map(([, t, c]) => `<span class="gk-leg"><i style="background:${c}"></i>${esc(t)}</span>`).join("")}<span class="gk-leg"><i style="background:#3a4655"></i>ohne Zuordnung</span></div>
      <p class="gk-quelle" style="margin-top:6px">Mittelwert der Wikidata-Angaben „politische Ausrichtung“ der Partei des Regierungschefs (ohne Partei: des Staatsoberhaupts). Ohne Partei oder Angabe (z. B. Monarchien, Einparteienstaaten): ohne Zuordnung. Wikidata (CC0), Abruf ${esc(PD.abruf)}.</p></div>`;
    const alle = Object.keys(PD.wahlen || {}).flatMap(iso => wahlenVon(iso).map(w => ({ ...w, iso }))).filter(w => !b || b.mitglieder.includes(w.iso)).sort((x, y) => x.datum.localeCompare(y.datum));
    if (b) {
      const mit = [...b.mitglieder].sort((x, y) => bipUsd(y) - bipUsd(x));
      return `<div><div class="gk-chips" style="margin-bottom:8px"><button type="button" data-gkbund="${esc(b.id)}">← Alle Länder</button></div><h2>${esc(b.name)}</h2><p class="unter" style="margin-top:4px">${f0.format(b.mitglieder.length)} Mitglieder${b.hinweis ? " · " + esc(b.hinweis) : ""} · <a class="gk-link" href="${esc(b.quelle)}" target="_blank" rel="noopener">Quelle</a>, Stand ${esc(b.stand)}</p></div>
        <div class="gk-block"><h3>Regierungen</h3><table class="gk-tab"><thead><tr><th>Land</th><th style="text-align:left">Regierungschef</th><th style="text-align:right">nächste Wahl</th></tr></thead><tbody>
        ${mit.map(i => { const r = regVon(i) || {}, h = r.regierungschef || r.staatsoberhaupt, w = wahlenVon(i)[0];
          return `<tr><td><span class="gk-punkt" style="background:${r.ausrichtung ? AUSR_FARBE[r.ausrichtung] : "#3a4655"}"></span><button type="button" class="gk-link" data-gkland="${esc(i)}">${esc(landName(i))}</button></td><td style="font-family:var(--sans);text-align:left">${esc(h ? h.name : "–")}${h && (h.partei_kurz || h.partei) ? ` <span class="pct">${esc(h.partei_kurz || h.partei)}</span>` : ""}</td><td class="pct">${w ? esc(datumWahl(w.datum)) : "–"}</td></tr>`; }).join("")}</tbody></table></div>
        <div class="gk-block"><h3>Wahlen der nächsten zwölf Monate</h3>${wahlListe(alle, true)}</div>${leg}`;
    }
    const zaehl = {}; Object.values(PD.regierungen || {}).forEach(r => { const k = r.ausrichtung || "ohne"; zaehl[k] = (zaehl[k] || 0) + 1; });
    const nat = [...new Set([...Object.keys(PD.wahlen_juengst || {}), ...(PA ? PA.juengst.filter(j => !j.region).map(j => j.iso) : [])])].flatMap(i => juengstNational(i).map(w => ({ ...w, iso: i }))).sort((x, y) => y.datum.localeCompare(x.datum));
    const reg = PA ? PA.juengst.filter(j => j.region) : [];
    const neuBlock = nat.length || reg.length ? `<div class="gk-block" style="border-left:3px solid #ffa828;padding-left:10px"><h3 style="color:#ffa828">Gerade gewählt (letzte ${SCHWELLE} Tage)</h3>
      <table class="gk-tab"><tbody>${nat.map(w => `<tr><td class="pct" style="white-space:nowrap">${esc(datumWahl(w.datum))}</td><td style="font-family:var(--sans);text-align:left;white-space:normal"><button type="button" class="gk-link" data-gkland="${esc(w.iso)}">${esc(landName(w.iso))}</button>: ${wpLink(w.url, w.was)}${w.status ? ` <span class="pct">(Ergebnis ${esc(w.status)})</span>` : ""}</td></tr>`).join("")}
      ${reg.map(j => `<tr><td class="pct" style="white-space:nowrap">${esc(datumWahl(j.datum))}</td><td style="font-family:var(--sans);text-align:left;white-space:normal"><button type="button" class="gk-link" data-gkland="${esc(j.iso)}">${esc(landName(j.iso))}</button>, <button type="button" class="gk-link" data-gkregion="${esc(j.region)}">${esc(j.region_name)}</button>: ${wpLink(j.url, j.kammer || "Parlament")} <span class="pct">(Ergebnis ${esc(j.ergebnis)})</span></td></tr>`).join("")}</tbody></table>
      <p class="gk-quelle" style="margin-top:6px">Schwelle ${SCHWELLE} Tage: so lange dauern in den meisten Staaten amtliches Endergebnis und konstituierende Sitzung (Deutschland: Art. 39 GG). „Ergebnis noch nicht in der Quelle“ heißt, die Sitzverteilung ist dort noch die alte.</p></div>` : "";
    return `<div><h2>Regierungen und Wahlen</h2><p class="unter" style="margin-top:4px">${S.stufe === 1 ? "Länder gefärbt nach Ausrichtung der Regierung, W = nationale Wahl in den nächsten zwölf Monaten, N = gerade gewählt · Bündnis wählen hebt die Mitglieder hervor · hineinzoomen für Regierungschefs" : "Je Land Regierungschef mit Partei und nächste Wahl · Land anklicken für Parlament mit Sitzverteilung · Shift+Klick für mehrere Länder · in Stufe 3 die Gliedstaaten der Bundesstaaten"}</p></div>
      ${neuBlock}${chips}<div class="gk-block"><h3>Wahlen der nächsten zwölf Monate</h3>${wahlListe(alle.slice(0, 30), true)}${alle.length > 30 ? `<p class="gk-quelle">und ${alle.length - 30} weitere</p>` : ""}
        <p class="gk-quelle" style="margin-top:6px">Wikipedia, „national electoral calendar“ ${esc(String(new Date().getFullYear()))} und ${esc(String(new Date().getFullYear() + 1))} (CC BY-SA 4.0), Abruf ${esc(PD.abruf)}.</p></div>
      ${leg.replace("</div>\n", `</div><p class="gk-quelle">${AUSR.map(([k, t]) => `${esc(t)} ${f0.format(zaehl[k] || 0)}`).join(" · ")} · ohne Zuordnung ${f0.format(zaehl.ohne || 0)}</p>\n`)}`;
  }
  // Sitzverteilung als Halbkreis (Punkte je Sitz, Parteien von links nach rechts)
  function halbkreis(sitze, ordnen = true) {
    const n = sitze.reduce((a, s) => a + s[1], 0); if (!n) return "";
    const reihen = Math.max(2, Math.min(28, Math.round(Math.sqrt(n * .3)))), r0 = reihen <= 4 ? 50 : 30, r1 = 96, punkte = [];
    let gesamt = 0; const radien = []; for (let i = 0; i < reihen; i++) { const r = r0 + (r1 - r0) * i / (reihen - 1); radien.push(r); gesamt += r; }
    radien.forEach(r => { const k = Math.round(n * r / gesamt); for (let j = 0; j < k; j++) { const w = Math.PI * (1 - (k === 1 ? .5 : j / (k - 1))); punkte.push([Math.cos(w) * r, -Math.sin(w) * r, w]); } });
    punkte.sort((a, b) => b[2] - a[2]);
    const reihenfolge = ["Die Linke", "SPD", "Grüne", "SSW", "CDU", "CSU", "FDP", "AfD"], sorted = ordnen ? [...sitze].sort((a, b) => reihenfolge.indexOf(a[0]) - reihenfolge.indexOf(b[0])) : sitze;
    const farbe = []; sorted.forEach(([, k, c]) => { for (let i = 0; i < k; i++) farbe.push(c === "#1a1a1a" ? "#6b6b6b" : c); });
    const proReihe = Math.max(1, ...radien.map(r => Math.round(n * r / gesamt))), rad = Math.min(4.2, reihen > 1 ? (r1 - r0) / (reihen - 1) * .42 : 4.2, Math.PI * r1 / proReihe * .45).toFixed(2);
    const legende = sorted.length > 12 ? [...sorted].sort((a, b) => b[1] - a[1]).slice(0, 11) : sorted, rest = sorted.length > 12 ? sorted.length - 11 : 0;
    return `<svg viewBox="-100 -100 200 104" style="width:100%;max-width:300px;display:block;margin:0 auto" role="img" aria-label="Sitzverteilung">${punkte.slice(0, farbe.length).map((p, i) => `<circle cx="${p[0].toFixed(1)}" cy="${p[1].toFixed(1)}" r="${rad}" fill="${esc(farbe[i])}"/>`).join("")}<text x="0" y="-4" text-anchor="middle" font-size="13" fill="#e8ecf1" font-family="var(--mono)">${n}</text></svg>
      <div class="gk-chips" style="justify-content:center;margin-top:4px">${legende.map(([p, k, c]) => `<span class="gk-leg"><i style="background:${esc(c === "#1a1a1a" ? "#6b6b6b" : c)}"></i>${esc(p)} ${k}</span>`).join("")}${rest ? `<span class="gk-leg">und ${rest} weitere</span>` : ""}</div>`;
  }
  function balken(werte, max) {
    return werte.map(([p, v]) => { const pi = parteiInfo(p); return `<div class="gk-balken"><span>${esc(p)}</span><i style="width:${(v / max * 100).toFixed(1)}%;background:${pi.farbe}"></i><b>${f1.format(v)}</b></div>`; }).join("");
  }
  function balkenFarbig(werte, max) {
    return werte.map(([p, v, c]) => `<div class="gk-balken"><span title="${esc(p)}">${esc(p)}</span><i style="width:${(v / max * 100).toFixed(1)}%;background:${esc(c || parteiInfo(p).farbe)}"></i><b>${f1.format(v)}</b></div>`).join("");
  }
  const wpLink = (url, t) => url ? `<a class="gk-link" href="${esc(url)}" target="_blank" rel="noopener">${esc(t)}</a>` : esc(t);
  function neuHinweis(j, wort) {
    if (!j) return "";
    return `<p class="gk-neu">Gerade gewählt: ${esc(wort || "Wahl")} am ${esc(datumWahl(j.datum))} (${j.tage === 0 ? "heute" : j.tage === 1 ? "gestern" : `vor ${f0.format(j.tage)} Tagen`}). ${j.ergebnis === "liegt vor" ? "Das Ergebnis ist in der Quelle eingetragen." : /vorläufig/.test(j.ergebnis) ? "Ein vorläufiges Ergebnis steht in Wikipedia." : "Das Ergebnis steht in den Quellen noch nicht" + (j.zusammensetzung_vor_wahl ? "; gezeigt ist die Zusammensetzung vor der Wahl." : ".")}${j.laufend ? " Auszählung läuft oder Ergebnis vorläufig." : ""}</p>`;
  }
  function kammerBlock(k) {
    const s = sitzeVon(k), j = k.juengst, lw = k.letzte_wahl, nw = k.naechste_wahl, st = k.stimmen;
    const summe = s ? s.l.reduce((a, g) => a + g.n, 0) : 0, reg = s ? s.l.filter(g => g.r).reduce((a, g) => a + g.n, 0) : 0;
    const titel = `<h3>${esc(k.name || "Parlament")} <span class="pct">${esc(TYP_NAME[k.typ] || "")}${k.sitze_soll ? " · " + f0.format(k.sitze_soll) + " Sitze" : ""}</span></h3>`;
    const bild = s ? halbkreis(s.l.filter(g => g.n > 0).map(g => [g.p, g.n, g.f || "#8b95a3"]), false) : `<p class="gk-leer">Keine Sitzverteilung in den Quellen${k.hinweis ? ": " + esc(k.hinweis) : ""}.</p>`;
    const regTxt = s && reg ? `<p class="pct" style="margin:4px 0">Regierungslager bzw. Mehrheit: ${f0.format(reg)} von ${f0.format(summe)} Sitzen (${f0.format(reg / summe * 100)} %) · ${esc(s.l.filter(g => g.r).map(g => g.p).join(", "))}</p>`
      : k.wahl && k.wahl.regierung_text ? `<p class="pct" style="margin:4px 0">Regierungsparteien nach der Wahl: ${esc(k.wahl.regierung_text)}</p>` : "";
    const quelle = !s ? "" : s.quelle === "aktuell" ? `Heutige Zusammensetzung laut ${wpLink(k.aktuell.url, "Wikipedia")} (Infobox, Abruf ${esc(datumWahl(k.aktuell.abruf))})`
      : `${esc(k.wahl.art)} vom ${esc(datumWahl(k.wahl.datum))} laut ${wpLink(k.wahl.url, "IPU Parline")}${k.wahl.vor_wahl ? " (Stand vor der jüngsten Wahl)" : ""}`;
    const nachWahl = s && s.quelle === "aktuell" && k.wahl && k.wahl.sitze && k.wahl.sitze.length ? `<p class="gk-quelle">${esc(k.wahl.art)} vom ${esc(datumWahl(k.wahl.datum))} (${wpLink(k.wahl.url, "IPU Parline")}): ${k.wahl.sitze.slice(0, 6).map(x => `${esc(x[0])} ${x[1]}`).join(" · ")}${k.wahl.sitze.length > 6 ? " …" : ""}</p>` : "";
    const sp = st && st.parteien ? st.parteien.filter(p => p.prozent != null && p.prozent <= 100) : [];
    const stimmen = sp.length ? `<h3 style="margin-top:8px">Letzte Wahl${st.datum ? " " + esc(datumWahl(st.datum)) : ""}: Stimmenanteil in %</h3>${balkenFarbig(sp.map(p => [p.partei, p.prozent, p.farbe]), Math.max(...sp.map(p => p.prozent), 1))}
      <p class="gk-quelle">${st.laufend ? "Auszählung läuft oder vorläufig. " : ""}Größte Parteien laut Infobox des ${wpLink(st.url, "Wikipedia-Wahlartikels")}${st.beteiligung ? `, Wahlbeteiligung ${f1.format(st.beteiligung)} %` : ""}.</p>` : "";
    const zeilen = [lw ? `<tr><td>letzte Wahl</td><td>${esc(datumWahl(lw.datum))}${lw.beginn ? ` <span class="pct">(ab ${esc(datumWahl(lw.beginn))})</span>` : ""}</td></tr>` : "",
      nw ? `<tr><td>nächste Wahl</td><td>${esc(datumWahl(nw.datum))}${nw.erwartet ? ` <span class="pct">(erwartet)</span>` : ""}</td></tr>` : "",
      k.wahl && k.wahl.beteiligung && !(st && st.beteiligung) ? `<tr><td>Wahlbeteiligung</td><td>${f1.format(k.wahl.beteiligung)} %</td></tr>` : ""].join("");
    return `<div class="gk-block"${j ? ' style="border-left:3px solid #ffa828;padding-left:10px"' : ""}>${titel}${neuHinweis(j, "Wahl")}${bild}${regTxt}${quelle ? `<p class="gk-quelle" style="margin-top:6px">${quelle}.</p>` : ""}${nachWahl}${stimmen}${zeilen ? `<table class="gk-tab" style="margin-top:6px"><tbody>${zeilen}</tbody></table>` : ""}</div>`;
  }
  function parlamentBlock(iso) {
    if (!PA) return "";
    const l = kammernVon(iso).filter(k => !(iso === "DE" && k.ipu === "DE-LC01"));
    if (!l.length) return iso === "DE" ? "" : `<div class="gk-block"><h3>Parlament</h3><p class="gk-leer">Für ${esc(landName(iso))} führt IPU Parline kein Parlament (oder es ist aufgelöst).</p></div>`;
    return l.map(kammerBlock).join("") + `<p class="gk-quelle" style="margin:-4px 0 10px">Kammern und Wahlergebnisse: ${esc((PA.quellen.ipu || {}).name || "IPU Parline")}, Stand ${esc(datumWahl((PA.quellen.ipu || {}).stand || PA.abruf))}; heutige Zusammensetzung und Stimmenanteile: Wikipedia (CC BY-SA 4.0).</p>`;
  }
  function chefZeile(c) {
    return c ? `<p style="margin:4px 0">Regierungschef: <b>${esc(c.name)}</b>${c.partei ? ` <span class="pct">${esc(c.partei)}</span>` : ""}</p>` : `<p class="gk-leer">Regierungschef in Wikidata nicht eingetragen.</p>`;
  }
  function glRegierung(sel, iso) {
    const c = sel.regierungschef, kam = sel.kammern.find(k => sitzeVon(k)), s = kam && sitzeVon(kam), rolle = PA && PA.rolle && PA.rolle[iso];
    const lager = (sel.koalition || []).length ? sel.koalition : (s ? s.l.filter(g => g.r).map(g => g.p) : []);
    const reg = s ? s.l.filter(g => g.r).reduce((a, g) => a + g.n, 0) : 0, summe = s ? s.l.reduce((a, g) => a + g.n, 0) : 0;
    const zeilen = [c ? `<tr><td>Regierungschef</td><td style="font-family:var(--sans);text-align:left;white-space:normal"><b>${esc(c.name)}</b>${c.partei ? `<br><span class="pct"><span class="gk-punkt" style="background:${esc(c.farbe || "#8b95a3")}"></span>${esc(c.partei)}</span>` : ""}</td></tr>` : "",
      c && c.seit ? `<tr><td>im Amt seit</td><td>${esc(datumWahl(c.seit))}</td></tr>` : "",
      rolle ? `<tr><td>Amt in dieser Ebene</td><td style="font-family:var(--sans);text-align:left;white-space:normal">${esc(rolle)}</td></tr>` : "",
      lager.length ? `<tr><td>Regierungslager</td><td style="font-family:var(--sans);text-align:left;white-space:normal">${esc(lager.join(", "))}${reg ? `<br><span class="pct">${f0.format(reg)} von ${f0.format(summe)} Sitzen (${f0.format(reg / summe * 100)} %)</span>` : ""}</td></tr>` : ""].join("");
    return `<div class="gk-block"><h3>Regierung</h3>${zeilen ? `<table class="gk-tab"><tbody>${zeilen}</tbody></table>` : `<p class="gk-leer">Regierungschef in Wikidata nicht eingetragen.</p>`}
      <p class="gk-quelle" style="margin-top:6px">Wikidata (CC0)${sel.wikidata ? `, <a class="gk-link" href="https://www.wikidata.org/wiki/${esc(sel.wikidata)}" target="_blank" rel="noopener">${esc(sel.wikidata)}</a>` : ""}, Abruf ${esc(datumWahl(PA.abruf))}; Regierungslager laut Infobox des Parlaments (Wikipedia).</p></div>`;
  }
  function gliedBlock(iso, teil) {   // teil "det": nur der gewählte Gliedstaat (kommt in der Seitenspalte nach oben), sonst nur die Liste
    const g = gliedVon(iso);
    if (teil === "det" && !g) return "";
    if (!g) return `<div class="gk-block"><h3>Regionen</h3><p class="gk-leer">${esc(landName(iso))} hat keine erfasste Regionalebene. Regionen und Gliedstaaten gibt es bisher für ${f0.format(PA ? (PA.foederal || []).length + (PA.regional || []).length : 0)} Staaten (Listen FOEDERAL und REGIONAL in app/parlamente_daten.py).</p></div>`;
    const sel = S.region && S.region.startsWith(iso + "-") ? g[S.region] : null;
    const det = sel ? `<div class="gk-block" style="border-left:3px solid #ffa828;padding-left:10px"><h3>${esc(sel.name_de || sel.name)} <span class="pct">${esc(landName(iso))}</span></h3><div class="gk-chips"><button type="button" data-gkregion="${esc(S.region)}">Auswahl aufheben</button></div></div>
      ${glRegierung(sel, iso)}
      ${sel.kammern.length ? sel.kammern.map(kammerBlock).join("") : `<div class="gk-block"><p class="gk-leer">Kein Parlament mit Wikipedia-Infobox gefunden.</p></div>`}` : "";
    const zeilen = Object.entries(g).sort((a, b) => (a[1].name_de || a[1].name).localeCompare(b[1].name_de || b[1].name, "de")).map(([c, x]) => {
      const k = x.kammern[0], st = staerkste(k), neu = x.kammern.some(q => q.juengst), ch = x.regierungschef;
      return `<tr><td><button type="button" class="gk-link" data-gkregion="${esc(c)}">${esc(x.name_de || x.name)}</button>${neu ? ` <span class="gk-neu-chip">neu gewählt</span>` : ""}</td><td style="font-family:var(--sans);text-align:left;white-space:normal">${esc(ch ? ch.name : "–")}${ch && (ch.partei_kurz || ch.partei) ? ` <span class="pct">${esc(ch.partei_kurz || ch.partei)}</span>` : ""}</td>
        <td style="text-align:left">${st ? `<span class="gk-punkt" style="background:${esc(st.f || "#8b95a3")}"></span>${esc(st.p)} ${f0.format(st.n)}` : "–"}</td><td class="pct">${k && k.letzte_wahl ? esc(datumWahl(k.letzte_wahl.datum)) : "–"}</td></tr>`; }).join("");
    if (teil === "det") return det;
    return `<div class="gk-block"><h3>Gliedstaaten und Regionen (${f0.format(Object.keys(g).length)})</h3><table class="gk-tab"><thead><tr><th>Gliedstaat</th><th style="text-align:left">Regierungschef</th><th style="text-align:left">stärkste Fraktion</th><th>letzte Wahl</th></tr></thead><tbody>${zeilen}</tbody></table>
      <p class="gk-quelle" style="margin-top:6px">Regierungschefs laut Wikidata (CC0), Parlamente laut Wikipedia-Infobox (CC BY-SA 4.0), Abruf ${esc(datumWahl(PA.abruf))}. Karte: Fläche in der Farbe der Partei des Regierungschefs (Wikidata), orange umrandet = in den letzten ${SCHWELLE} Tagen gewählt. Gliedstaat anklicken für Parlament und Wahl.</p></div>`;
  }
  function deutschlandBlock(stufe, teil) {
    const de = PD && PD.deutschland; if (!de) return "";
    const bt = de.bundestag, u = de.umfragen && de.umfragen.parlamente && de.umfragen.parlamente.Bundestag, btw = de.btw25 || {};
    const bund = {}; let summe = 0; Object.values(btw).forEach(l => Object.entries(l).forEach(([p, v]) => { bund[p] = (bund[p] || 0) + v; })); summe = Object.keys(btw).length;
    const lr = de.landesregierungen || {}, reg = S.region && DE_GEO ? DE_GEO.features.find(f => f.properties.code === S.region) : null;
    let region = "";
    if (reg) {
      const name = reg.properties.name, l = lr[S.region] || {}, w = btw[name] || btw[Object.keys(btw).find(k => k.startsWith(name.slice(0, 6)))] || {}, um = de.umfragen.parlamente[name] || de.umfragen.parlamente[Object.keys(de.umfragen.parlamente).find(k => k.startsWith(name.slice(0, 6)))];
      region = `<div class="gk-block" style="border-left:3px solid #ffa828;padding-left:10px"><h3>${esc(name)}</h3><p style="margin:4px 0">Regierungschef: <b>${esc(l.regierungschef || "–")}</b>${l.parteien && l.parteien.length ? ` (${esc(l.parteien.map(p => parteiInfo(p).kurz).join(", "))})` : ""}</p>${(() => { const gs = gliedstaat(S.region), c = gs && gs.regierungschef; return (c && c.seit ? `<p class="pct" style="margin:2px 0">im Amt seit ${esc(datumWahl(c.seit))}</p>` : "") + (gs && (gs.koalition || []).length ? `<p class="pct" style="margin:2px 0">Regierungslager: ${esc(gs.koalition.join(", "))}</p>` : ""); })()}
        <h3 style="margin-top:8px">Bundestagswahl 2025 in ${esc(name)} (Zweitstimmen %)</h3>${balken(Object.entries(w), Math.max(...Object.values(w), 1))}
        ${um ? `<h3 style="margin-top:8px">Jüngste Landtagsumfrage (${esc(um.institut)}, ${esc(datumWahl(um.datum))})</h3>${balken(um.werte, Math.max(...um.werte.map(x => x[1]), 1))}` : `<p class="gk-leer">Keine Landtagsumfrage bei DAWUM.</p>`}
        <p class="gk-quelle" style="margin-top:6px">Bundestagswahl: Bundeswahlleiterin; Umfrage: DAWUM. Landtag, letzte Landtagswahl und Regierungslager laut Wikipedia und Wikidata.</p></div>${(gliedstaat(S.region) || { kammern: [] }).kammern.map(kammerBlock).join("")}`;
    }
    const laender = stufe >= 3 && DE_GEO ? `<div class="gk-block"><h3>Bundesländer</h3><table class="gk-tab"><tbody>${DE_GEO.features.map(f => { const l = lr[f.properties.code] || {}, pi = parteiInfo((l.parteien || [])[0]);
      const g = gliedstaat(f.properties.code), k = g && g.kammern[0], neu = k && k.juengst;
      return `<tr><td><button type="button" class="gk-link" data-gkregion="${esc(f.properties.code)}">${esc(f.properties.name)}</button>${neu ? ` <span class="gk-neu-chip">neu gewählt</span>` : ""}</td><td style="font-family:var(--sans);text-align:left">${esc(l.regierungschef || "–")}</td><td><span class="gk-punkt" style="background:${pi.farbe}"></span>${esc(pi.kurz)}</td><td class="pct">${k && k.letzte_wahl ? esc(datumWahl(k.letzte_wahl.datum)) : ""}</td></tr>`; }).join("")}</tbody></table>
      <p class="gk-quelle" style="margin-top:6px">Ministerpräsidentinnen und -präsidenten laut Wikidata, Abruf ${esc(PD.abruf)}; rechts Datum der letzten Landtagswahl (Wikipedia). Auf der Karte Fläche in Parteifarbe; Land anklicken für Landtag, Wahl und Umfrage.</p></div>` : "";
    if (teil === "region") return region;
    return `<div class="gk-block"><h3>Bundestag</h3>${halbkreis(bt.sitze)}<p class="gk-quelle" style="margin-top:6px">${esc(bt.stand)}, <a class="gk-link" href="${esc(bt.quelle)}" target="_blank" rel="noopener">Bundeswahlleiterin</a>. Regierung: ${esc(bt.regierung.join(", "))}.</p></div>
      ${u ? `<div class="gk-block"><h3>Jüngste Umfrage Bundestag</h3>${balken(u.werte, Math.max(...u.werte.map(x => x[1]), 1))}<p class="gk-quelle" style="margin-top:6px">${esc(u.institut)}, ${esc(datumWahl(u.datum))}, ${esc(u.befragte || "")} Befragte · <a class="gk-link" href="${esc(u.url)}" target="_blank" rel="noopener">DAWUM</a> (${esc(de.umfragen.lizenz)})</p></div>` : ""}
      ${laender}`;
  }
  function personZeile(t, h) {
    if (!h) return "";
    return `<tr><td>${esc(t)}</td><td style="font-family:var(--sans);text-align:left;white-space:normal">${h.wikidata ? `<a class="gk-link" href="https://www.wikidata.org/wiki/${esc(h.wikidata)}" target="_blank" rel="noopener">${esc(h.name || h.wikidata)}</a>` : esc(h.name)}${h.partei ? `<br><span class="pct">${esc(h.partei)}${h.ausrichtung_angaben && h.ausrichtung_angaben.length ? " · " + esc(h.ausrichtung_angaben.join(", ")) : ""}</span>` : ""}</td></tr>`;
  }
  function juengstBlock(iso) {
    const l = juengstNational(iso); if (!l.length) return "";
    return `<div class="gk-block" style="border-left:3px solid #ffa828;padding-left:10px"><h3 style="color:#ffa828">Gerade gewählt</h3><table class="gk-tab"><tbody>${l.map(w => `<tr><td class="pct" style="white-space:nowrap">${esc(datumWahl(w.datum))}</td><td style="font-family:var(--sans);text-align:left;white-space:normal">${wpLink(w.url, w.was)}${w.status ? `<br><span class="pct">Ergebnis ${esc(w.status)}</span>` : ""}</td></tr>`).join("")}</tbody></table>
      <p class="gk-quelle" style="margin-top:6px">Wahlen der letzten ${SCHWELLE} Tage (Wikipedia-Wahlkalender, IPU Parline). Nach ${SCHWELLE} Tagen liegen in der Regel das amtliche Endergebnis und die konstituierende Sitzung vor.</p></div>`;
  }
  function politikLand(iso, stufe) {
    if (!PD) return `<p class="gk-leer">Keine Politikdaten im Build.</p>`;
    const r = regVon(iso) || {}, a = AUSR.find(x => x[0] === r.ausrichtung);
    const kopf = `<div class="gk-block"><h3>Regierung</h3><table class="gk-tab"><tbody>${personZeile("Regierungschef", r.regierungschef)}${personZeile("Staatsoberhaupt", r.staatsoberhaupt)}
        <tr><td>Ausrichtung</td><td style="font-family:var(--sans);text-align:left;white-space:normal">${a ? `<span class="gk-punkt" style="background:${a[2]}"></span>${esc(a[1])} <span class="pct">(nach Partei des ${r.ausrichtung_nach === "regierungschef" ? "Regierungschefs" : "Staatsoberhaupts"})</span>` : "ohne Zuordnung"}</td></tr></tbody></table>
        <p class="gk-quelle" style="margin-top:6px">Wikidata (CC0), Abruf ${esc(PD.abruf)}. Kabinettsmitglieder sind noch offen.</p></div>
      ${juengstBlock(iso)}<div class="gk-block"><h3>Nationale Wahlen, nächste zwölf Monate</h3>${wahlListe(wahlenVon(iso), false)}</div>`;
    const regionen = iso === "DE" ? deutschlandBlock(stufe) + parlamentBlock(iso) : parlamentBlock(iso) + (stufe >= 3 ? gliedBlock(iso) : gliedVon(iso) ? `<div class="gk-block"><h3>Gliedstaaten</h3><p class="gk-leer">${esc(landName(iso))} gliedert sich in ${f0.format(Object.keys(gliedVon(iso)).length)} Gliedstaaten bzw. Regionen. Näher heranzoomen (Stufe 3), dann erscheinen ihre Regierungen und Parlamente.</p><div class="gk-chips" style="margin-top:8px"><button type="button" data-gkstufe="3">Zu Stufe 3</button></div></div>` : "");
    const verbund = stufe >= 3 ? handelBlock(iso) + firmenBlock(iso) : "";
    // ausgewählter Gliedstaat bzw. Bundesland (Regierung, Parlament, Wahl) steht oben, darunter die Staatsebene
    const oben = stufe >= 3 && S.region && S.region.startsWith(iso + "-") ? (iso === "DE" ? deutschlandBlock(stufe, "region") : gliedBlock(iso, "det")) : "";
    return oben + kopf + regionen + verbund;
  }
  function karteForm(iso) {
    if (S.form === "boerse") return finanzKacheln(iso);
    if (S.form === "politik") { const r = regVon(iso) || {}, h = r.regierungschef || r.staatsoberhaupt, a = AUSR.find(x => x[0] === r.ausrichtung), w = wahlenVon(iso)[0];
      const jn = juengstNational(iso), k = kammernVon(iso)[0], st = staerkste(k);
      return `<p style="margin:4px 0">${esc(h ? h.name : "–")}${h && h.partei ? ` <span class="pct">${esc(h.partei_kurz || h.partei)}</span>` : ""}</p>${jn.length ? `<p class="gk-neu" style="margin:2px 0">Gerade gewählt: ${esc(datumWahl(jn[0].datum))}, ${esc(jn[0].was)}</p>` : ""}<p class="pct">${a ? `<span class="gk-punkt" style="background:${a[2]}"></span>${esc(a[1])}` : "ohne Zuordnung"}${st ? ` · stärkste Fraktion ${esc(st.p)} (${f0.format(st.n)})` : ""}${w ? ` · nächste Wahl ${esc(datumWahl(w.datum))}: ${esc(w.was)}` : ""}</p>`; }
    if (S.form === "unternehmen") { const e = unLandBauen()[iso] || { n: 0, notiert: 0, br: {} };
      return `<div class="gk-kz" style="grid-template-columns:1fr 1fr">${kzKlein("Unternehmen", f0.format(e.n), "erfasst")}${kzKlein("börsennotiert", f0.format(e.notiert), "")}</div><p class="pct" style="margin-top:4px">${Object.entries(e.br).sort((x, y) => y[1] - x[1]).slice(0, 3).map(([b, k]) => `${esc(b)} ${f0.format(k)}`).join(" · ")}</p>`; }
    return null;
  }

  /* ===== Handel Stufe 1: Ströme zwischen den 15 größten Volkswirtschaften (Kontinentauswahl filtert) ===== */
  function k15Knoten() {
    const k = new Set(TOP15);
    for (const kk of [S.kont, S.kont2]) if (kk && !TOP15.some(i => KONT_VON[i] === kk)) Object.keys(NACH_ISO).filter(i => KONT_VON[i] === kk && bipUsd(i)).sort((a, b) => bipUsd(b) - bipUsd(a)).slice(0, 3).forEach(i => k.add(i));
    return k;
  }
  function k15Stroeme() {
    const kn = k15Knoten(), a = S.kont, b = S.kont2, out = [];
    PAAR.forEach((v, key) => { const [x, y] = key.split(">"); if (!kn.has(x) || !kn.has(y)) return; const kx = KONT_VON[x], ky = KONT_VON[y];
      if (b ? !((kx === a && ky === b) || (kx === b && ky === a)) : !(kx === a || ky === a)) return;
      out.push({ x, y, v, richtung: kx === a ? "export" : "import" }); });
    return out.sort((p, q) => q.v - p.v).slice(0, 24);
  }
  const k15Punkte = () => wertFC(S.k1 !== "top15" ? [] : [...k15Knoten()].filter(mitte).map(i => ({ type: "Feature", geometry: { type: "Point", coordinates: mitte(i) },
    properties: { iso: i, name: landKurz(i), rang: TOP15.indexOf(i) + 1, imKont: KONT_VON[i] === S.kont || KONT_VON[i] === S.kont2 } })));

  /* ----- Grundkarten ----- */
  function glyphProtokoll() {
    if (glyphProtokoll.da) return; glyphProtokoll.da = true;
    const b64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0)).buffer;
    maplibregl.addProtocol("terminal", async p => {
      const m = p.url.match(/^terminal:\/\/glyphen\/([^/]+)\/(\d+-\d+)/);
      const font = m && decodeURIComponent(m[1]).split(",")[0];
      return { data: m && m[2] === "0-255" && GLYPHEN[font] ? b64(GLYPHEN[font]) : new ArrayBuffer(0) };
    });
  }
  const himmel = { "sky-color": "#0d1724", "horizon-color": "#18273b", "fog-color": "#07090c", "atmosphere-blend": ["interpolate", ["linear"], ["zoom"], 0, .9, 5, .4, 7, 0] };
  function stilEinfach() {
    return { version: 8, name: "Einfach (Natural Earth)", projection: { type: "globe" }, sky: himmel, glyphs: "terminal://glyphen/{fontstack}/{range}", sources: {},
      layers: [{ id: "hintergrund", type: "background", paint: { "background-color": "#0a1320" } }] };
  }
  function stilOSM() {
    const nm = ["coalesce", ["get", "name:de"], ["get", "name:latin"], ["get", "name"]];
    const txt = (id, filter, min, groesse, farbe) => ({ id, type: "symbol", source: "osm", "source-layer": "place", filter, minzoom: min,
      layout: { "text-field": nm, "text-font": ["Noto Sans Regular"], "text-size": groesse, "text-max-width": 8 }, paint: { "text-color": farbe, "text-halo-color": "#07090c", "text-halo-width": 1.2 } });
    const strasse = (id, klassen, min, farbe, breite) => ({ id, type: "line", source: "osm", "source-layer": "transportation", minzoom: min,
      filter: ["in", ["get", "class"], ["literal", klassen]], layout: { "line-cap": "round", "line-join": "round" },
      paint: { "line-color": farbe, "line-width": ["interpolate", ["exponential", 1.6], ["zoom"], min, breite[0], 18, breite[1]] } });
    return { version: 8, name: "OpenStreetMap (OpenFreeMap)", projection: { type: "globe" }, sky: himmel, glyphs: "terminal://glyphen/{fontstack}/{range}",
      sources: { osm: { type: "vector", url: OSM_URL, attribution: '<a href="https://openfreemap.org" target="_blank" rel="noopener">OpenFreeMap</a> · <a href="https://www.openmaptiles.org/" target="_blank" rel="noopener">© OpenMapTiles</a> · Daten <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">© OpenStreetMap-Mitwirkende</a>' } },
      layers: [
        { id: "osm-land", type: "background", paint: { "background-color": "#161c24" } },
        { id: "osm-landbedeckung", type: "fill", source: "osm", "source-layer": "landcover", filter: ["in", ["get", "class"], ["literal", ["wood", "grass", "farmland"]]], paint: { "fill-color": "#18211f", "fill-opacity": .6 } },
        { id: "osm-eis", type: "fill", source: "osm", "source-layer": "landcover", filter: ["==", ["get", "class"], "ice"], paint: { "fill-color": "#1f2731" } },
        { id: "osm-siedlung", type: "fill", source: "osm", "source-layer": "landuse", minzoom: 6, filter: ["in", ["get", "class"], ["literal", ["residential", "commercial", "industrial", "retail"]]], paint: { "fill-color": "#1c222c", "fill-opacity": .8 } },
        { id: "osm-wasser", type: "fill", source: "osm", "source-layer": "water", paint: { "fill-color": "#0a1320" } },
        { id: "osm-fluss", type: "line", source: "osm", "source-layer": "waterway", minzoom: 6, paint: { "line-color": "#0f1b2c", "line-width": ["interpolate", ["linear"], ["zoom"], 6, .5, 14, 2.5] } },
        { id: "osm-gebaeude", type: "fill", source: "osm", "source-layer": "building", minzoom: 14, paint: { "fill-color": "#222a35" } },
        strasse("osm-strasse-klein", ["minor", "service", "tertiary"], 11, "#222a35", [.4, 8]),
        strasse("osm-strasse", ["primary", "secondary", "trunk"], 7, "#2a3442", [.4, 12]),
        strasse("osm-autobahn", ["motorway"], 5, "#3a4554", [.5, 14]),
        { id: "osm-bahn", type: "line", source: "osm", "source-layer": "transportation", minzoom: 9, filter: ["==", ["get", "class"], "rail"], paint: { "line-color": "#2b313b", "line-width": .8, "line-dasharray": [3, 3] } },
        { id: "osm-grenze-region", type: "line", source: "osm", "source-layer": "boundary", minzoom: 4, filter: ["all", ["==", ["get", "admin_level"], 4], ["==", ["get", "maritime"], 0]], paint: { "line-color": "#323b48", "line-width": .7, "line-dasharray": [3, 2] } },
        { id: "osm-grenze-land", type: "line", source: "osm", "source-layer": "boundary", filter: ["all", ["==", ["get", "admin_level"], 2], ["==", ["get", "maritime"], 0]], paint: { "line-color": "#536072", "line-width": ["interpolate", ["linear"], ["zoom"], 1, .6, 6, 1.4] } },
        txt("osm-ort-dorf", ["in", ["get", "class"], ["literal", ["village", "suburb"]]], 11, 11, "#7d8794"),
        txt("osm-ort-stadt", ["==", ["get", "class"], "town"], 8, 11.5, "#949eab"),
        txt("osm-ort-grossstadt", ["==", ["get", "class"], "city"], 4.5, ["interpolate", ["linear"], ["zoom"], 4, 11, 10, 15], "#b9c1cc"),
      ] };
  }
  function grundkarte(art) {
    if (art === "osm" && osmFehler >= 99) art = "einfach";
    S.grund = art;
    document.querySelectorAll("[data-gkgrund]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.gkgrund === art)));
    if (!map) return;
    stilBereit = false;
    map.setStyle(art === "osm" ? stilOSM() : stilEinfach(), { diff: false });
    map.once("style.load", stilGeladen);
  }
  function stilGeladen() {
    if (S.grund === "einfach") { /* Grundfläche: Länder sind die Landmasse */ }
    stilBereit = true;
    EBENEN.forEach(ebeneAnlegen);
    ueberlagerung(); namenZoom(); untZoom();
    S.auswahl.forEach(i => { if (NACH_ISO[i]) map.setFeatureState({ source: "laender", id: NACH_ISO[i].id }, { gewaehlt: true }); });
    vorschauen();
  }

  /* ----- Karte anlegen ----- */
  function karteStarten() {
    if (map) return;
    if (typeof maplibregl === "undefined") { document.getElementById("gk-karte").innerHTML = `<p style="padding:80px 20px;color:var(--ink-2)">Die Kartenbibliothek konnte nicht geladen werden.</p>`; return; }
    glyphProtokoll();
    let start = "einfach";
    try { start = localStorage.getItem("globus-grund") || (navigator.onLine ? "osm" : "einfach"); } catch { start = navigator.onLine ? "osm" : "einfach"; }
    S.grund = start;
    try { map = karteNeu(start); } catch (e) {   // kein WebGL (alter Rechner, Testbrowser): Seitenleiste und Fenster gehen trotzdem
      map = null; console.warn("Karte nicht verfügbar", e);
      document.getElementById("gk-karte").insertAdjacentHTML("beforeend", `<p style="position:absolute;top:90px;left:20px;color:var(--ink-2)">Die Karte braucht WebGL, das dieser Browser nicht bereitstellt. Länder und Unternehmen sind über die Suche und die Seitenleiste erreichbar.</p>`);
      return;
    }
  }
  function karteNeu(start) {
    const map = new maplibregl.Map({ container: "gk-karte", style: start === "osm" ? stilOSM() : stilEinfach(), center: [10.4, 48.5], zoom: 1.7, minZoom: .8, maxZoom: 16,
      attributionControl: { compact: true, customAttribution: 'Grenzen: <a href="https://www.naturalearthdata.com" target="_blank" rel="noopener">Natural Earth</a> · Orte: <a href="https://www.geonames.org" target="_blank" rel="noopener">GeoNames</a> (CC BY 4.0)' },
      dragRotate: false, pitchWithRotate: false, boxZoom: false /* Shift+Klick wählt mehrere Länder */, renderWorldCopies: false, locale: { "NavigationControl.ZoomIn": "Hineinzoomen", "NavigationControl.ZoomOut": "Herauszoomen" } });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    map.touchZoomRotate.disableRotation();
    map.once("style.load", stilGeladen);
    map.on("error", e => {
      if (e && e.sourceId === "osm" || /openfreemap/.test(String(e && e.error && (e.error.url || e.error.message) || ""))) {
        osmFehler++;
        // Kachelserver nicht erreichbar (offline, Firewall, Vorschau ohne Netzzugriff): sofort auf die eingebettete Karte wechseln,
        // wenn noch keine Kachel kam, sonst erst nach mehreren Fehlern (einzelne Kacheln dürfen ausfallen)
        if (S.grund === "osm" && (!osmGeladen || osmFehler >= 8)) { osmFehler = 99; hinweis("OpenStreetMap-Kacheln nicht erreichbar, einfache Karte aus Natural Earth"); grundkarte("einfach"); }
      }
    });
    map.on("sourcedata", e => { if (e.sourceId === "osm" && e.isSourceLoaded) osmGeladen = true;
    });
    const quer = (p, ids) => map.queryRenderedFeatures(p, { layers: ids.filter(i => map.getLayer(i)) });
    // Schichten von Ebenen mit vorrang: true liegen über den Unternehmenspunkten (Klick und Tooltip gehen an die Ebene)
    const vorrangSchichten = () => (map.getStyle().layers || []).filter(l => l.metadata && EBENEN.some(eb => eb.vorrang && eb.an && eb.id === l.metadata.ebene)).map(l => l.id);
    map.on("mousemove", e => {
      const v = quer(e.point, vorrangSchichten()).length > 0;
      const u = v ? [] : quer(e.point, ["unt-cluster", "unt-punkt", "unt-land-ring"]), rt = u.length ? [] : quer(e.point, ["rt-news", "rt-eng", "rt-hub"]),
        hb = u.length || rt.length ? [] : quer(e.point, ["st-raum", "st-x", "st-m", "nb-x", "nb-m", "handel-x", "handel-m", "k-x", "k-m", "rt-see", "rt-bahn", "rt-strasse", "rt-luft"]), l = u.length ? [] : quer(e.point, ["laender-flaeche"]);
      const it = u.length || rt.length || hb.length ? [] : quer(e.point, Object.keys(INFO_TIPS));
      if (rt.length) routenTip(e, rt[0]); else if (hb.length) { handelTip(e, hb[0]); }
      else if (it.length) { if (!handelPop) handelPop = new maplibregl.Popup({ closeButton: false, closeOnClick: false, className: "gk-pop", offset: 10, maxWidth: "300px" }); handelPop.setLngLat(e.lngLat).setHTML(INFO_TIPS[it[0].layer.id](it[0].properties)).addTo(map); }
      else if (handelPop) { handelPop.remove(); handelPop = null; }
      map.getCanvas().style.cursor = v || u.length || rt.length || it.length || l.length ? "pointer" : "";
      const id = l.length ? l[0].id : null;
      if (id !== S.hover) {
        if (S.hover != null && map.getSource("laender")) map.setFeatureState({ source: "laender", id: S.hover }, { hover: false });
        S.hover = id;
        if (id != null) map.setFeatureState({ source: "laender", id }, { hover: true });
      }
      tooltip(e, u[0]);
    });
    map.getCanvas().addEventListener("mouseleave", () => tooltip(null));
    map.on("click", e => {
      for (const eb of EBENEN) if (ebeneAn(eb) && eb.vorrang && eb.klick && eb.klick(e, map) === true) return;
      const shift = !!(e.originalEvent && e.originalEvent.shiftKey);
      { const r = EBENEN.find(x => x.id === "routen"); if (r && ebeneAn(r) && r.klick(e, map) === true) return; }   // Meldungen und Engstellen
      if (S.stufe === 1 && !shift) {     // Stufe 1: Handel wählt den Kontinent, Volkswirtschaft den Wirtschaftsraum
        const l1 = quer(e.point, ["laender-flaeche"]), i1 = l1.length ? l1[0].properties.iso : null;
        if (S.form === "handel" && i1 && KONT_VON[i1]) return kontWaehlen(KONT_VON[i1]);
        if ((S.form === "vwl" || S.form === "boerse" || S.form === "unternehmen") && i1 && RAUM_VON[i1] && !quer(e.point, ["bo-kreis"]).length) { S.raum = RAUM_VON[i1]; vwlAnwenden(); unAnwenden(); seiteZeichnen(); return; }
      }
      const c = quer(e.point, ["unt-cluster"]);
      if (c.length) return clusterKlick(c[0]);
      const r = quer(e.point, ["unt-land-ring"]);
      if (r.length) return listeOeffnen(r[0].properties.iso);
      const p = quer(e.point, ["unt-punkt"]);
      if (p.length && shift && S.form === "unternehmen") {     // Shift+Klick: in den Vergleich, Fenster nebeneinander
        const id = p[0].properties.id; oeffnen(id);
        if (UNT.nachId(id) && !UNT.nachId(id).stub && !UNT.auswahl().includes(id)) UNT.setAuswahl([...UNT.auswahl(), id]);
        if (UNT.auswahl().length >= 2) vergleichOeffnen();
        alleZeichnen(); nebeneinander(); return;
      }
      if (p.length > 1) return listePopup(e.lngLat, p.map(x => x.properties));
      if (p.length) return oeffnen(p[0].properties.id);
      for (const eb of EBENEN) if (ebeneAn(eb) && !eb.vorrang && eb.id !== "routen" && eb.klick && eb.klick(e, map) === true) return;
      const l = quer(e.point, ["laender-flaeche"]);
      if (l.length && shift) landUmschalten(l[0].properties.iso);
      else if (l.length) landWaehlen(l[0].properties.iso, { fliegen: S.stufe < 2 || S.form === "unternehmen" });
      else if (!shift) landWaehlen(null);
    });
    map.on("zoomend", zoomHinweis);
    map.on("moveend", vorschauen);
    map.on("movestart", e => { S.nutzer = !!e.originalEvent; });
    map.on("zoom", stufeAktualisieren);
    return map;
  }

  let tipPop = null;
  let handelPop = null;
  function routenTip(e, f) {
    const p = f.properties, k = knotenVon(p.id); if (!k) return;
    const m = meld(k.id).length ? meld(k.id) : null;
    const t = `<b>${esc(k.name)}</b> <span class="pct">${esc(k.art === "engstelle" ? "Engstelle" : k.art === "hafen" ? "Hafen" : k.art === "flughafen" ? "Frachtflughafen" : "Bahnknoten")}</span><br><span class="pct">${esc(k.rolle)}</span>${m ? `<br>${MLD.symbol(m[0], 13)} ${esc(m[0].titel)}<br><span class="pct">${esc(m[0].quelle)} · ${esc(MLD.alterText(m[0].datum))}${m.length > 1 ? ` · ${m.length - 1} weitere` : ""} · klicken</span>` : ""}`;
    if (!handelPop) handelPop = new maplibregl.Popup({ closeButton: false, closeOnClick: false, className: "gk-pop", offset: 10, maxWidth: "320px" });
    handelPop.setLngLat(e.lngLat).setHTML(t).addTo(map);
  }
  function handelTip(e, f) {
    const p = f.properties;
    if (p.strom || f.layer.id.startsWith("rt-")) {
      const t = f.layer.id.startsWith("rt-") ? `<b>${esc(p.name)}</b><br><span class="pct">${esc((TRAEGER[p.traeger] || [p.traeger])[0])}${p.schematisch ? " · schematisch" : " · Seeweg berechnet"}${p.stoer ? " · ⚠ Meldung an einer Engstelle" : ""}</span>`
        : p.strom === 1 ? `<b>Strom ${esc(p.von)} → ${esc(p.nach)}</b><br>netto ${f1.format(p.netto / 1000)} TWh<br><span class="pct">${esc(p.von)} → ${esc(p.nach)} ${f1.format(p.hin / 1000)} TWh, zurück ${f1.format(p.rueck / 1000)} TWh · ${esc(WELT.strom.jahr)} · Eurostat</span>`
        : `<b>Strom ${esc(p.land)} ↔ ${esc(p.partner)}</b><br>Ausfuhr ${f1.format(p.aus / 1000)} TWh (↗) · Einfuhr ${f1.format(p.ein / 1000)} TWh (↘)<br><span class="pct">Pfeil in Richtung des Nettoflusses · ${esc(WELT.strom.jahr)} · Eurostat</span>`;
      if (!handelPop) handelPop = new maplibregl.Popup({ closeButton: false, closeOnClick: false, className: "gk-pop", offset: 10, maxWidth: "300px" });
      handelPop.setLngLat(e.lngLat).setHTML(t).addTo(map); return;
    }
    if (p.k) {      // Kontinentstrom
      const t = p.k15 ? `<b>${esc(landName(p.von))} → ${esc(landName(p.nach))}</b><br>Warenexporte ${mrdText(p.wert)} USD<br><span class="pct">${SPIEGEL.has(p.von + ">" + p.nach) ? "Spiegelmeldung des Importlandes" : "Meldung des Exportlandes"} · UN Comtrade</span>`
        : `<b>${esc(KONT_NAME[p.von])} → ${esc(KONT_NAME[p.nach])}</b><br>${p.richtung === "export" ? "Exporte" : "Importe"} ${mrdText(p.wert)} USD<br><span class="pct">Summe der Länderströme, Warenhandel ${esc(HANDEL_JAHRE)}</span>`;
      if (!handelPop) handelPop = new maplibregl.Popup({ closeButton: false, closeOnClick: false, className: "gk-pop", offset: 10, maxWidth: "300px" });
      handelPop.setLngLat(e.lngLat).setHTML(t).addTo(map); return;
    }
    const iso0 = p.land || S.land, h = HANDEL.laender[iso0];
    const t = `<b>${p.richtung === "export" ? `${esc(landName(iso0))} → ${esc(p.name)}` : `${esc(p.name)} → ${esc(landName(iso0))}`}</b><br>${p.richtung === "export" ? "Exporte" : "Importe"} ${f1.format(p.wert / 1e9)} Mrd. USD<br><span class="pct">${f1.format(p.anteil * 100)} % aller ${p.richtung === "export" ? "Exporte" : "Importe"} · ${esc(h.jahr)}${SPIEGEL.has(p.richtung === "export" ? iso0 + ">" + p.partner : p.partner + ">" + iso0) ? " · Spiegelmeldung des Partners" : ""}</span>`;
    if (!handelPop) handelPop = new maplibregl.Popup({ closeButton: false, closeOnClick: false, className: "gk-pop", offset: 10, maxWidth: "300px" });
    handelPop.setLngLat(e.lngLat).setHTML(t).addTo(map);
  }
  function tooltip(e, f) {
    if (!f || !e) { if (tipPop) { tipPop.remove(); tipPop = null; } return; }
    const p = f.properties;
    const html = p.iso ? `<b>${f0.format(p.n)} Unternehmen in ${esc(landName(p.iso))} ohne bekannten Ort</b><br><span class="pct">Sitz nur auf Landesebene bekannt · klicken für die Liste</span>`
      : p.cluster ? `<b>${f0.format(p.point_count)} Unternehmen</b><br><span class="pct">${f0.format(p.notiert)} börsennotiert · ${f0.format(p.kennzahlen)} mit Kennzahlen · klicken zum Aufteilen</span>`
      : `<b>${esc(p.name)}</b><br>${esc(p.branche)}${p.art === "s" ? " · nur Stammdaten" : ""}<br><span class="pct">${esc(p.ort)}${p.unsicher ? " · Sitz unsicher" : ""}</span>`;
    if (!tipPop) tipPop = new maplibregl.Popup({ closeButton: false, closeOnClick: false, className: "gk-pop", offset: 14, maxWidth: "300px" });
    tipPop.setLngLat(f.geometry.coordinates).setHTML(html).addTo(map);
  }
  async function clusterKlick(f) {
    const src = map.getSource("unternehmen"), id = f.properties.cluster_id;
    let z = null;
    try { z = await src.getClusterExpansionZoom(id); } catch { z = null; }
    if (z != null && z <= 11 && map.getZoom() < 11) { map.easeTo({ center: f.geometry.coordinates, zoom: Math.max(z + .2, map.getZoom() + 1) }); return; }
    // dieselbe Stadt: Punkte zerfallen nicht weiter, daher Liste zum Auswählen
    let blaetter = [];
    try { blaetter = await src.getClusterLeaves(id, 500, 0); } catch { blaetter = []; }
    listePopup(f.geometry.coordinates, blaetter.map(x => x.properties));
  }
  let listePop = null;
  function listePopup(lngLat, props) {
    if (listePop) listePop.remove();
    props.sort((a, b) => a.name.localeCompare(b.name, "de"));
    const orte = [...new Set(props.map(p => p.ort).filter(Boolean))];
    listePop = new maplibregl.Popup({ className: "gk-pop", offset: 14, maxWidth: "320px" }).setLngLat(lngLat)
      .setHTML(`<b>${f0.format(props.length)} Unternehmen</b> <span class="pct">${esc(orte.slice(0, 3).join(", "))}${orte.length > 3 ? " …" : ""}</span><ul>${props.map(p => `<li><button type="button" data-gkfirma="${esc(p.id)}">${esc(p.name)} <span class="pct">${esc(p.branche)}</span></button></li>`).join("")}</ul>`)
      .addTo(map);
  }

  /* ----- Zoomstufen und Kontinente ----- */
  const STUFEN_TEXT = [["Kontinente", 1.7], ["Länder", 3.6], ["Unternehmen & Nachbarn", 6.2]];
  // Bezeichnung der Stufen je Darstellungsform (Zoomziele bleiben gleich)
  const STUFEN_FORM = { handel: ["Welt", "Länder", "Land & Nachbarn"], vwl: ["Wirtschaftsräume", "Länder", "Land im Detail"], boerse: ["Börsenplätze", "Länder", "Finanzplatz"],
    unternehmen: ["Dichte", "Sitze", "Netz & Nachbarn"], politik: ["Bündnisse", "Regierungen", "Regionen"] };
  function stufeChips() {
    const el = document.getElementById("gk-stufen"); if (!el) return;
    const namen = STUFEN_FORM[S.form];
    el.hidden = S.form === "politik" && S.polAnsicht === "wahlen";      // dort führt die Ebenenleiter (src/wahlen.js)
    el.innerHTML = STUFEN_TEXT.map(([t], i) => `<button type="button" data-gkstufe="${i + 1}" aria-pressed="${S.stufe === i + 1}"><b>${i + 1}</b> ${esc(namen ? namen[i] : t)}</button>`).join("");
  }
  function stufeAktualisieren() {
    if (!map) return;
    const st = stufeVon(map.getZoom());
    if (st === S.stufe) return;
    S.stufe = st;
    stufeChips(); routenAktualisieren(); stromAktualisieren(); legendeKarte();
    // Heranzoomen aus Stufe 1 ohne Land: Land in der Mitte ist nicht gewählt, die Seitenleiste wechselt nur den Inhalt
    if (st === 1 && S.land && S.nutzer) { landWaehlen(null); return; }
    seiteZeichnen();
  }
  function kontWaehlen(k, k2) {
    if (k2 !== undefined) { S.kont = k; S.kont2 = k2 || null; }
    else if (k === S.kont) S.kont2 = null;
    else if (k === S.kont2) { S.kont = k; S.kont2 = null; }
    else if (!S.kont) S.kont = k;
    else S.kont2 = k;
    kontAnwenden(); if (S.land) landWaehlen(null); else seiteZeichnen();
    const c = (KONT.find(x => x[0] === S.kont) || [])[3];
    if (map && c && map.getZoom() < ZG[0]) map.easeTo({ center: c, zoom: Math.min(map.getZoom(), 1.9), duration: 900 });
  }
  function kontSeite() {
    const k = S.kont, kk = KONT.find(x => x[0] === k);
    if (!HANDEL) return `<div><h2>Weltkugel</h2><p class="gk-leer">Keine Handelsdaten im Build.</p></div>`;
    const summe = (a, nach) => KONT.reduce((t, b) => t + (nach ? KMAT[a][b[0]] : KMAT[b[0]][a]), 0) - KMAT[a][a];
    const kopf = `<tr><th></th>${KONT.map(b => `<th style="text-align:right;padding:3px 2px">${KURZ[b[0]]}</th>`).join("")}</tr>`;
    const matrix = KONT.map(a => `<tr><td><button type="button" class="gk-link" data-gkkont="${a[0]}"${a[0] === k ? ' style="color:var(--amber)"' : ""}>${esc(a[1])}</button></td>${KONT.map(b =>
      `<td style="padding:3px 2px${a[0] === k && b[0] === S.kont2 ? ";background:var(--panel-2);color:var(--amber)" : ""}"><button type="button" class="gk-link" style="color:inherit" data-gkkont="${a[0]}" data-gkkont2="${b[0]}">${f0.format(KMAT[a[0]][b[0]] / 1e9)}</button></td>`).join("")}</tr>`).join("");
    const paare = (x, y) => [...PAAR].filter(([q]) => KONT_VON[q.split(">")[0]] === x && KONT_VON[q.split(">")[1]] === y).sort((a, b) => b[1] - a[1]).slice(0, 5)
      .map(([q, v]) => { const [i, j] = q.split(">"); return `<tr><td>${esc(landName(i))} → ${esc(landName(j))}</td><td>${f1.format(v / 1e9)}</td></tr>`; }).join("");
    const paar = S.kont2 ? `<div class="gk-block"><h3>${esc(kk[1])} ↔ ${esc(KONT_NAME[S.kont2])}</h3>
      <table class="gk-tab"><tbody><tr><td>${esc(kk[1])} → ${esc(KONT_NAME[S.kont2])} (Exporte)</td><td>${f0.format(KMAT[k][S.kont2] / 1e9)} Mrd. USD</td></tr>
      <tr><td>${esc(KONT_NAME[S.kont2])} → ${esc(kk[1])} (Importe)</td><td>${f0.format(KMAT[S.kont2][k] / 1e9)} Mrd. USD</td></tr></tbody></table>
      <p class="gk-quelle" style="margin:8px 0 4px">Größte Länderströme ${esc(kk[1])} → ${esc(KONT_NAME[S.kont2])}</p><table class="gk-tab"><tbody>${paare(k, S.kont2)}</tbody></table>
      <p class="gk-quelle" style="margin:8px 0 4px">… und ${esc(KONT_NAME[S.kont2])} → ${esc(kk[1])}</p><table class="gk-tab"><tbody>${paare(S.kont2, k)}</tbody></table></div>` : "";
    const abd = KABD[k];
    const modus = `<div class="gk-chips"><button type="button" data-gkk1="top15" aria-pressed="${S.k1 === "top15"}">15 größte Volkswirtschaften</button><button type="button" data-gkk1="kont" aria-pressed="${S.k1 === "kont"}">Kontinente gesamt</button></div>`;
    const st = S.k1 === "top15" ? k15Stroeme() : [];
    const k15 = S.k1 !== "top15" ? "" : `<div class="gk-block"><h3>Größte Ströme ${S.kont2 ? `${esc(kk[1])} ↔ ${esc(KONT_NAME[S.kont2])}` : `mit ${esc(kk[1])}`}</h3><table class="gk-tab"><thead><tr><th>Exportland → Importland</th><th style="text-align:right">Mrd. USD</th></tr></thead><tbody>
      ${st.slice(0, 15).map(x => `<tr><td><span style="color:${x.richtung === "export" ? HEX_EXP : HEX_IMP}">${x.richtung === "export" ? "▲" : "▼"}</span> ${esc(landName(x.x))} → ${esc(landName(x.y))}</td><td>${f1.format(x.v / 1e9)}</td></tr>`).join("")}</tbody></table>
      <p class="gk-quelle" style="margin-top:6px">Zwischen den 15 größten Volkswirtschaften nach BIP (Weltbank: ${esc(TOP15.map(landName).join(", "))})${k15Knoten().size > TOP15.length ? `, ergänzt um die drei größten Volkswirtschaften von ${esc(kk[1])}` : ""}. Grün: Exporte aus ${esc(kk[1])}, rot: Importe nach ${esc(kk[1])}. Die 24 größten Ströme auf der Karte.</p></div>`;
    return `<div><h2>Welthandel: ${S.k1 === "top15" ? "die 15 größten Volkswirtschaften" : "Kontinente"}</h2><p class="unter" style="margin-top:4px">Ganz herausgezoomt: Kontinent anklicken, dann einen zweiten für den Vergleich · hineinzoomen für Länder</p><div style="margin-top:8px">${modus}</div></div>${gutBlock()}${k15}
      <div class="gk-block"><h3>${esc(kk[1])}</h3><div class="gk-kz" style="grid-template-columns:1fr 1fr 1fr">
        <div><div class="t" style="min-height:0">Exporte</div><div class="v" style="font-size:15px">${f0.format(summe(k, true) / 1e9)}</div><div class="z">Mrd. USD</div></div>
        <div><div class="t" style="min-height:0">Importe</div><div class="v" style="font-size:15px">${f0.format(summe(k, false) / 1e9)}</div><div class="z">Mrd. USD</div></div>
        <div><div class="t" style="min-height:0">Binnenhandel</div><div class="v" style="font-size:15px">${f0.format(KMAT[k][k] / 1e9)}</div><div class="z">Mrd. USD</div></div></div>
        <p class="gk-quelle" style="margin-top:6px">Exporte und Importe gegenüber den anderen fünf Kontinenten. Auf der Karte grün (durchgezogen) Exporte aus ${esc(kk[1])}, rot (gestrichelt) Importe nach ${esc(kk[1])}.</p>
        <div class="gk-chips" style="margin-top:8px"><button type="button" data-gkip>Standort per IP bestimmen</button></div></div>
      ${paar}
      <div class="gk-block"><h3>Alle Kontinente, Mrd. USD</h3><table class="gk-tab gk-matrix"><thead>${kopf}</thead><tbody>${matrix}</tbody></table>
        <p class="gk-quelle" style="margin-top:6px">Zeile = Exporteur, Spalte = Importeur; Zelle anklicken wählt das Paar. Summe der bilateralen Länderströme (UN Comtrade, Warenhandel, ${esc(HANDEL_JAHRE)}): je Länderpaar die Meldung des Exportlandes, fehlt sie, die Spiegelmeldung des Importlandes. Je Land liegen nur die 15 größten Partner vor, daher fehlen kleinere Ströme (erfasst sind für ${KONT.filter(x => KABD[x[0]] != null).map(x => esc(x[1]) + " " + Math.round(KABD[x[0]] * 100) + " %").join(", ")} der gemeldeten Exporte). Werte sind Untergrenzen. Quelle: <a href="${esc(HANDEL.url)}" target="_blank" rel="noopener">UN Comtrade</a>.</p></div>
      ${verkehrBlock()}
      <div class="gk-block"><p class="gk-quelle">Voreinstellung: Kontinent laut Zeitzone und Browsersprache. Die IP-Abfrage geht nur auf Knopfdruck an einen freien Dienst (geojs.io) und schickt dabei Ihre IP-Adresse dorthin.</p></div>`;
  }
  async function ipKontinent() {
    hinweis("Standort per IP wird abgefragt …");
    try {
      const c = new AbortController(), t = setTimeout(() => c.abort(), 5000);
      const r = await fetch("https://get.geojs.io/v1/ip/country.json", { signal: c.signal }); clearTimeout(t);
      const iso = ((await r.json()) || {}).country;
      if (iso && KONT_VON[iso]) { hinweis(`Standort laut IP: ${landName(iso)}`); kontWaehlen(KONT_VON[iso], null); return; }
      hinweis("IP-Abfrage ohne verwertbares Ergebnis, Zeitzone bleibt");
    } catch { hinweis("IP-Abfrage nicht möglich (gesperrt oder offline), Zeitzone bleibt"); }
  }

  /* ----- Länder ----- */
  function bbox(f) {
    let a = [180, 90, -180, -90];
    const lauf = c => { if (typeof c[0] === "number") { a = [Math.min(a[0], c[0]), Math.min(a[1], c[1]), Math.max(a[2], c[0]), Math.max(a[3], c[1])]; } else c.forEach(lauf); };
    // nur die größte Teilfläche zählt (Frankreich ohne Überseegebiete, USA ohne Alaska-Inseln)
    if (f.geometry.type === "MultiPolygon") {
      const flaeche = poly => { const r = poly[0]; let s = 0; for (let i = 0; i < r.length - 1; i++) s += r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1]; return Math.abs(s); };
      lauf([...f.geometry.coordinates].sort((x, y) => flaeche(y) - flaeche(x))[0]);
    } else lauf(f.geometry.coordinates);
    return a;
  }
  function auswahlZeigen(neu) {
    if (map && map.getSource("laender")) {
      S.auswahl.forEach(i => { if (NACH_ISO[i]) map.setFeatureState({ source: "laender", id: NACH_ISO[i].id }, { gewaehlt: false }); });
      neu.forEach(i => { if (NACH_ISO[i]) map.setFeatureState({ source: "laender", id: NACH_ISO[i].id }, { gewaehlt: true }); });
    }
    S.auswahl = neu; S.land = neu[0] || null;
  }
  // Shift+Klick: Land zur Auswahl hinzufügen bzw. herausnehmen (Kacheln beidseitig, Ströme aller gewählten Länder)
  function landUmschalten(iso) {
    if (!iso) return;
    auswahlZeigen(S.auswahl.includes(iso) ? S.auswahl.filter(x => x !== iso) : [...S.auswahl, iso]);
    if (map && map.getLayer("laender-name")) map.setPaintProperty("laender-name", "text-color", namensFarbe());
    punkteAktualisieren(); handelAktualisieren(); seiteZeichnen();
  }
  function landWaehlen(iso, opt = {}) {
    auswahlZeigen(iso ? [iso] : []);
    if (map && map.getLayer("laender-name")) map.setPaintProperty("laender-name", "text-color", namensFarbe());
    try { localStorage.setItem("globus-land", S.land || ""); } catch { /* kein Speicher */ }
    punkteAktualisieren();
    handelAktualisieren();
    seiteZeichnen();
    if (iso && opt.fliegen && map && NACH_ISO[iso]) {
      const b = bbox(NACH_ISO[iso]), w = b[2] - b[0], h = b[3] - b[1];
      if (w > 0 && w < 170) map.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: { top: 70, bottom: 60, left: 40, right: 40 }, maxZoom: ZG[1] - .6, duration: 1400 });
      else { const p = NACH_ISO[iso].properties; map.flyTo({ center: [p.lx, p.ly], zoom: 3, duration: 1400 }); }
    }
    if (iso && opt.fliegen) { setTimeout(zoomHinweis, 1500); map.once("moveend", () => { if (map.getZoom() < ZG[0] + .15) map.easeTo({ zoom: ZG[0] + .4, duration: 600 }); }); }
  }
  function zoomHinweis() {
    if (!map) return;
    const n = S.land ? PUNKTE.filter(p => p.properties.land === S.land).length : PUNKTE.length;
    if (map.getZoom() < ZG[1] && n && (S.form === "unternehmen" || S.form === "vwl")) hinweis(`Hineinzoomen, um ${f0.format(n)} Unternehmen nach Sitz zu sehen`);
  }
  /* Legende der Handelsströme auf der Karte: Farbe und Linienstil (nicht nur Farbe) */
  function legendeKarte() {
    const host = document.getElementById("gk-karte"); if (!host) return;
    let el = document.getElementById("gk-legkarte");
    if (!el) { el = document.createElement("div"); el.id = "gk-legkarte"; el.className = "gk-legkarte"; el.setAttribute("aria-label", "Legende der Karte"); host.appendChild(el); }
    const an = id => { const e = EBENEN.find(x => x.id === id); return !!e && ebeneAn(e); };
    const lin = (farbe, strich, pfeil = true) => `<svg width="34" height="10" aria-hidden="true"><line x1="1" y1="5" x2="${pfeil ? 26 : 33}" y2="5" stroke="${farbe}" stroke-width="2.6" ${strich ? `stroke-dasharray="${strich}"` : 'stroke-linecap="round"'}/>${pfeil ? `<path d="M33 5 L25 1.5 L25 8.5 Z" fill="${farbe}"/>` : ""}</svg>`;
    const teile = [];
    const handelSicht = (an("kontinente") || an("handel")) && HANDEL && (S.form !== "vwl" || S.stufe >= 3);
    if (handelSicht) teile.push(`<b>Handel</b><span>${lin(HEX_EXP, "")}<em style="color:${HEX_EXP}">Export</em> durchgezogen</span><span>${lin(HEX_IMP, "5 3")}<em style="color:${HEX_IMP}">Import</em> gestrichelt</span>
        <small>Pfeil = Richtung · Breite nach Wert${S.form === "handel" ? " · unter dem Land: Zollsatz und Saldo" : ""}</small>${S.netzOffen ? `<button type="button" data-gkhandelnetz>${S.handelMitNetz ? "Handel ausblenden" : "Handel zusätzlich zeigen"}</button>` : ""}`);
    if (an("strom") && S.form === "handel") teile.push(`<span>${lin(STROM, "")}<em style="color:${STROM}">Strom</em> netto, TWh</span>`);
    if (an("routen")) teile.push(`<b>Routen</b><span>${lin(TRAEGER.see[1], "", false)}See</span><span>${lin(TRAEGER.bahn[1], "6 3", false)}Bahn</span><span>${lin(TRAEGER.strasse[1], "2 3", false)}Straße</span><span>${lin(TRAEGER.luft[1], "1 4", false)}Luft</span>
        <span><svg width="14" height="14" aria-hidden="true"><path d="M7 1 L13 7 L7 13 L1 7 Z" fill="#e8ecf1"/></svg>Engstelle</span><span>${MLD.svg("angriff", "neu", 14)}${MLD.svg("sperrung", "neu", 14)}${MLD.svg("wetter", "neu", 14)}${MLD.svg("streik", "neu", 14)}${MLD.svg("stau", "neu", 14)}${MLD.svg("unfall", "neu", 14)}Meldung (Form = Typ, Farbe = Alter: Bernstein neu, dunkler bis 3 Tage, grau älter)</span>`);
    if (an("boerse") && bmAktiv()) { const d = FNZ.mess().find(m => m.id === S.bm); teile.push(`<b>${esc(d.name)}</b><span><svg width="12" height="12" aria-hidden="true"><circle cx="6" cy="6" r="5" fill="${d.diverg ? "rgba(62,207,110,.7)" : "rgba(255,168,40,.75)"}"/></svg>${d.diverg ? "positiv" : "hoch"}</span><span><svg width="12" height="12" aria-hidden="true"><circle cx="6" cy="6" r="5" fill="${d.diverg ? "rgba(255,82,72,.7)" : "rgba(255,168,40,.2)"}"/></svg>${d.diverg ? "negativ" : "niedrig"}</span><small>${esc(d.einheit)}; Länder ohne Daten bleiben unmarkiert</small>`); }
    else if (an("boerse")) teile.push(`<b>Börse</b><span><svg width="12" height="12" aria-hidden="true"><circle cx="6" cy="6" r="5" fill="${HEX_EXP}"/></svg>Leitindex seit Jahresbeginn gestiegen</span><span><svg width="12" height="12" aria-hidden="true"><circle cx="6" cy="6" r="5" fill="${HEX_IMP}"/></svg>gefallen</span>${S.stufe >= 3 ? `<small>Punkte: börsennotierte Unternehmen nach Kursentwicklung seit Jahresbeginn (dunkelgrün über +20 %, dunkelrot unter −20 %, grau ohne Kurse)</small>` : `<small>Stufe 2: je Land Leitindex und 10-jährige Rendite</small>`}`);
    if (an("undichte") && S.stufe === 1) teile.push(`<b>Unternehmen</b><span><svg width="14" height="14" aria-hidden="true"><circle cx="7" cy="7" r="6" fill="rgba(255,168,40,.25)" stroke="#ffa828"/></svg>${S.u1 === "wert" ? "Börsenwert" : "Zahl der Unternehmen"} je Land</span>`);
    if (an("politik")) teile.push(`<b>Regierung</b>${AUSR.map(([, t, c]) => `<span><svg width="12" height="12" aria-hidden="true"><rect width="12" height="12" rx="2" fill="${c}"/></svg>${esc(t)}</span>`).join("")}<span><svg width="12" height="12" aria-hidden="true"><rect width="12" height="12" rx="2" fill="#3a4655"/></svg>ohne Zuordnung</span>
        <span><svg width="14" height="14" aria-hidden="true"><circle cx="7" cy="7" r="6" fill="#9fd3ff"/><text x="7" y="10.5" text-anchor="middle" font-size="9" font-weight="700" fill="#07090c">W</text></svg>Wahl in den nächsten 12 Monaten</span>
        <span><svg width="14" height="14" aria-hidden="true"><circle cx="7" cy="7" r="6" fill="#ffa828"/><text x="7" y="10.5" text-anchor="middle" font-size="9" font-weight="700" fill="#07090c">N</text></svg>gerade gewählt (${SCHWELLE} Tage)</span>${S.stufe >= 3 ? "<small>Gliedstaaten in der Farbe der Partei des Regierungschefs, orange umrandet = gerade gewählt</small>" : ""}`);
    if (an("wahlen") && typeof WAHLEN !== "undefined") teile.push(WAHLEN.legende());
    if (an("vwl")) teile.push(`<b>Werte</b><span><em style="color:#7cc4ff">BIP +</em> / <em style="color:#ff9f6b">BIP −</em></span><span>Inflation <em style="color:#ff9f6b">über 5 %</em>, <em style="color:#7cc4ff">unter 0 %</em></span>`);
    el.hidden = !teile.length;
    el.innerHTML = teile.join("");
  }
  document.addEventListener("globus:netz", ev => { S.netzOffen = !!(ev.detail && ev.detail.offen); if (!S.netzOffen) S.handelMitNetz = false; ueberlagerung(); });
  function hinweis(text) {
    const el = document.getElementById("gk-hinweis"); if (!el) return;
    el.textContent = text; el.style.opacity = "1";
    clearTimeout(hinweisTimer); hinweisTimer = setTimeout(() => { el.style.opacity = "0"; }, 4200);
  }

  /* Wirtschaftliche Kerndaten aus dem VWL-Datensatz: Eurostat, wo vorhanden, sonst OECD (wie im Terminal) */
  const KERN = [
    { t: "BIP real, ggü. Vorjahr", s: ["bip_yoy", "oecd_bip_yoy"], gut: 1 },
    { t: "Inflation", s: ["hicp_gesamt", "oecd_inflation"], gut: 0 },
    { t: "Kerninflation", s: ["hicp_kern", "oecd_kerninflation"], gut: 0 },
    { t: "Arbeitslosenquote", s: ["arbeitslosenquote", "oecd_arbeitslosenquote"], gut: -1 },
    { t: "Staatsschulden", s: ["schuldenquote", "oecd_eo_schuldenquote"], gut: -1, einheit: "% BIP" },
    { t: "Finanzierungssaldo Staat", s: ["defizitquote", "oecd_eo_finanzierungssaldo"], gut: 1, einheit: "% BIP" },
    { t: "Leistungsbilanz", s: ["oecd_eo_leistungsbilanz"], gut: 0, einheit: "% BIP" },
    { t: "Rendite 10-j. Staatsanleihen", s: ["oecd_eo_langfristzins"], gut: 0 },
    { t: "Kurzfristzins", s: ["oecd_eo_kurzfristzins"], gut: 0 },
    { t: "BIP je Einwohner", s: ["oecd_eo_bip_je_einwohner"], gut: 1, einheit: "USD KKP" },
    { t: "Frühindikator (OECD CLI)", s: ["oecd_fruehindikator"], gut: 1, einheit: "Index" },
  ];
  const PROG = [["BIP real", ["oecd_eo_bip"]], ["Inflation", ["oecd_eo_inflation", "oecd_eo_inflation_hvpi"]], ["Arbeitslosenquote", ["oecd_eo_arbeitslosenquote"]],
    ["Finanzierungssaldo", ["oecd_eo_finanzierungssaldo"]], ["Staatsschulden", ["oecd_eo_schuldenquote"]]];
  let VD = null, SER = {};
  addEventListener("sphaerae:vwl", () => {        // nachgeladene Reihen: Länderwerte neu, Karte und Seitenleiste neu zeichnen
    VWL_UNVOLLST = false; for (const k of Object.keys(WERT)) delete WERT[k];
    if (map) [["vw-wert", wertPunkte], ["vw-raum", raumPunkte]].forEach(([q, f]) => { if (map.getSource(q)) map.getSource(q).setData(f()); });
    const g = document.getElementById("globus"); if (g && !g.hidden) seiteZeichnen();
  });
  function vwlDaten() { if (!VD && typeof VWL !== "undefined" && VWL.alleDaten) { VD = VWL.alleDaten(); SER = VD ? Object.fromEntries(VD.serien.map(s => [s.serie_id, s])) : {}; } return VD; }
  function reihe(ids, geo) {
    const d = vwlDaten(); if (!d) return null;
    const da = ids.map(id => VWL.bedarf ? VWL.bedarf(id) : true).every(Boolean);   // API-Fassung: fehlende Reihen nachladen
    if (!da) VWL_UNVOLLST = true;
    for (const id of ids) { const p = d.daten[id] && d.daten[id][geo]; if (p && p.length) return { id, s: SER[id] || {}, p }; }
    return null;
  }
  const istTeil = r => r.s.prognose_ab ? r.p.filter(x => x[0] < r.s.prognose_ab) : r.p;
  const zahl = (v, s) => v == null ? "–" : (s.format === "zahl0" ? f0 : s.format === "pct2" ? f2 : f1).format(v);
  const zeitDe = z => /^\d{4}-\d{2}$/.test(z) ? `${z.slice(5)}/${z.slice(0, 4)}` : z.replace("-Q", " Q");
  function spark(r) {
    const ist = istTeil(r), n = { M: 60, Q: 20, A: 10 }[r.s.frequenz] || 20, pkt = ist.slice(-n);
    const proj = r.s.prognose_ab ? r.p.filter(x => x[0] >= r.s.prognose_ab).slice(0, 2) : [];
    const alle = pkt.concat(proj); if (alle.length < 2) return "";
    const ys = alle.map(x => x[1]), lo = Math.min(...ys, 0 < Math.min(...ys) ? Math.min(...ys) : 0), hi = Math.max(...ys), sp = hi - lo || 1;
    const X = i => i / (alle.length - 1) * 100, Y = v => 24 - (v - lo) / sp * 22;
    const pfad = (arr, off) => arr.map((x, i) => `${i ? "L" : "M"}${X(i + off).toFixed(1)},${Y(x[1]).toFixed(1)}`).join("");
    const null0 = lo < 0 && hi > 0 ? `<line x1="0" x2="100" y1="${Y(0)}" y2="${Y(0)}" stroke="#2a313b" stroke-width=".6"/>` : "";
    return `<svg viewBox="0 0 100 26" preserveAspectRatio="none" aria-hidden="true">${null0}<path d="${pfad(pkt, 0)}" fill="none" stroke="#a3acb8" stroke-width="1.2" vector-effect="non-scaling-stroke"/>${proj.length ? `<path d="${pfad([pkt[pkt.length - 1], ...proj], pkt.length - 1)}" fill="none" stroke="#ffa828" stroke-width="1.2" stroke-dasharray="3 2" vector-effect="non-scaling-stroke"/>` : ""}</svg>`;
  }
  function kerndaten(iso) {
    const geo = VWL_GEO(iso), kacheln = [];
    for (const k of KERN) {
      const r = reihe(k.s, geo); if (!r) continue;
      const ist = istTeil(r); if (!ist.length) continue;
      const [z, v] = ist[ist.length - 1];
      const vj = r.s.frequenz === "M" ? ist[ist.length - 13] : r.s.frequenz === "Q" ? ist[ist.length - 5] : ist[ist.length - 2];
      const d = vj ? v - vj[1] : null, richtung = d == null || !k.gut || Math.abs(d) < 1e-9 ? "" : (d > 0) === (k.gut > 0) ? "up" : "down";
      const einheit = k.einheit || r.s.einheit || "";
      kacheln.push(`<div title="${esc(r.s.name || "")} · Quelle ${esc(r.s.quelle || "")}"><div class="t">${esc(k.t)}</div><div class="v">${zahl(v, r.s)}<span style="font-size:11px;color:var(--ink-3)"> ${esc(einheit === "%" ? "%" : einheit)}</span></div>
        <div class="z">${esc(zeitDe(z))}${d == null ? "" : ` · <span class="d ${richtung}">${d > 0 ? "+" : ""}${zahl(d, r.s)}</span> ggü. ${r.s.frequenz === "A" ? "Vorjahr" : "Vorjahreszeitraum"}`}</div>${spark(r)}</div>`);
    }
    return kacheln;
  }
  function prognosen(iso) {
    const geo = VWL_GEO(iso), jetzt = new Date().getFullYear(), jahre = [jetzt - 1, jetzt, jetzt + 1];
    const zeilen = PROG.map(([t, ids]) => { const r = reihe(ids, geo); if (!r) return "";
      const w = Object.fromEntries(r.p); const ab = r.s.prognose_ab || "9999";
      if (!jahre.some(j => w[j] != null)) return "";
      return `<tr><td>${esc(t)}</td>${jahre.map(j => `<td class="${String(j) >= ab ? "proj" : ""}">${w[j] == null ? "–" : zahl(w[j], r.s)}</td>`).join("")}</tr>`; }).join("");
    if (!zeilen) return "";
    const s = SER.oecd_eo_bip || {};
    return `<div class="gk-block"><h3>OECD-Projektion</h3><table class="gk-tab"><thead><tr><th>in %</th>${jahre.map(j => `<th style="text-align:right">${j}</th>`).join("")}</tr></thead><tbody>${zeilen}</tbody></table>
      <p class="gk-quelle" style="margin-top:6px">Kursiv = Projektion. ${esc(s.hinweis || "OECD Economic Outlook")}. Weitere Prognosen (Zentralbanken, Institute, Konsens) im Terminal unter VWL › Prognosen.</p></div>`;
  }
  function indizes(iso) {
    if (typeof BOE === "undefined" || !BOE.da()) return "";
    const b = BOE.korr(); if (!b) return "";
    const n = landName(iso), alias = { US: ["USA", "Vereinigte Staaten"], GB: ["Vereinigtes Königreich", "Großbritannien"], KR: ["Südkorea"], CZ: ["Tschechien"] }[iso] || [];
    const passt = x => x.land && (x.land === n || alias.includes(x.land) || (DN && x.land === DN.of(iso)));
    const ind = b.indizes.filter(passt), unt = (b.unternehmen || []).filter(passt).sort((a, c) => (c.boerswert || 0) - (a.boerswert || 0));
    if (!ind.length && !unt.length) return "";
    const r = v => v == null ? "–" : `<span style="color:var(--${v >= 0 ? "up" : "down"})">${v > 0 ? "+" : ""}${f1.format(v * 100)} %</span>`;
    return `<div class="gk-block"><h3>Börse</h3>${ind.length ? `<table class="gk-tab"><thead><tr><th>Index</th><th style="text-align:right">Stand</th><th style="text-align:right">lfd. Jahr</th><th style="text-align:right">1 J.</th></tr></thead><tbody>
      ${ind.map(x => `<tr><td>${esc(x.name)}</td><td>${x.kurs == null ? "–" : f0.format(x.kurs)}</td><td>${r(x.ytd)}</td><td>${r(x.r1j)}</td></tr>`).join("")}</tbody></table>` : ""}
      ${unt.length ? `<p class="gk-quelle" style="margin-top:8px">Große Börsenwerte (Bereich BÖR, ohne Sitzangabe): ${unt.slice(0, 8).map(x => esc(x.name)).join(", ")}${unt.length > 8 ? ` und ${unt.length - 8} weitere` : ""}.</p>` : ""}
      <p class="gk-quelle">Stand ${esc((ind[0] || unt[0]).datum || "")}, Schlusskurse über Yahoo Finance.</p></div>`;
  }
  function nachbarBlock(iso) {
    const nb = nachbarnVon(iso), weitere = partnerStufe3(iso).filter(q => !nb.includes(q));
    if (!nb.length) return `<div class="gk-block"><h3>Handel mit Nachbarländern</h3><p class="gk-leer">${esc(landName(iso))} hat keine Landgrenze (Natural-Earth-Flächen).</p></div>`;
    const mrd = v => v == null ? "–" : f1.format(v / 1e9);
    const z = nb.map(q => ({ q, x: PAAR.get(iso + ">" + q), m: PAAR.get(q + ">" + iso) })).sort((a, b) => ((b.x || 0) + (b.m || 0)) - ((a.x || 0) + (a.m || 0)));
    const w = weitere.map(q => ({ q, x: PAAR.get(iso + ">" + q), m: PAAR.get(q + ">" + iso) }));
    const sp = (a, b) => SPIEGEL.has(a + ">" + b) ? "*" : "";
    return `<div class="gk-block"><h3>Handel mit Nachbarländern</h3><table class="gk-tab"><thead><tr><th>Nachbar</th><th style="text-align:right">Export</th><th style="text-align:right">Import</th></tr></thead><tbody>
      ${z.map(r => `<tr><td><button type="button" class="gk-link" data-gkland="${esc(r.q)}">${esc(landName(r.q))}</button></td><td>${mrd(r.x)}${r.x ? sp(iso, r.q) : ""}</td><td>${mrd(r.m)}${r.m ? sp(r.q, iso) : ""}</td></tr>`).join("")}
      ${w.length ? `<tr><th colspan="3" style="padding-top:8px">Fünf weitere größte Partner</th></tr>${w.map(r => `<tr><td><button type="button" class="gk-link" data-gkland="${esc(r.q)}">${esc(landName(r.q))}</button></td><td>${mrd(r.x)}${r.x ? sp(iso, r.q) : ""}</td><td>${mrd(r.m)}${r.m ? sp(r.q, iso) : ""}</td></tr>`).join("")}` : ""}</tbody></table>
      <p class="gk-quelle" style="margin-top:6px">Mrd. USD. Auf der Karte grün (durchgezogen) Exporte, rot (gestrichelt) Importe je Nachbar. „–“ = nicht unter den 15 größten Partnern in den Meldungen beider Länder (kleiner oder nicht gemeldet). * = Spiegelmeldung des Nachbarn. Quelle: UN Comtrade; Nachbarn aus den Natural-Earth-Grenzen.</p></div>`;
  }
  function stromBlock(iso) {
    const zeile = i => { const s = STUFEN.strom[i]; return s ? `<tr><td>${i === iso ? "<b>" + esc(landName(i)) + "</b>" : `<button type="button" class="gk-link" data-gkland="${esc(i)}">${esc(landName(i))}</button>`}</td><td style="color:${s.netto >= 0 ? HEX_IMP : HEX_EXP}">${s.netto >= 0 ? "Import" : "Export"} ${f1.format(Math.abs(s.netto))}</td><td>${s.bedarf ? f1.format(Math.abs(s.netto) / s.bedarf * 100) + " %" : "–"}</td><td>${s.jahr}</td></tr>` : ""; };
    const z = [iso, ...nachbarnVon(iso)].map(zeile).join("");
    return `<div class="gk-block"><h3>Strom (Nettohandel)</h3>${z ? `<table class="gk-tab"><thead><tr><th></th><th style="text-align:right">Netto, TWh</th><th style="text-align:right">am Bedarf</th><th style="text-align:right">Jahr</th></tr></thead><tbody>${z}</tbody></table>` : `<p class="gk-leer">Für ${esc(landName(iso))} liegen keine Stromhandelsdaten vor.</p>`}
      <p class="gk-quelle" style="margin-top:6px">Saldo aus Importen und Exporten je Land, nicht nach Partnerland: frei zugängliche bilaterale Stromflüsse gibt es nur für Europa (ENTSO-E, Zugang mit Token), sie sind noch nicht angebunden. Quelle: <a href="${esc(STUFEN.quellen ? STUFEN.quellen.strom_url : "https://ourworldindata.org/electricity-mix")}" target="_blank" rel="noopener">Ember über Our World in Data</a> (CC BY 4.0).</p></div>`;
  }
  function handelBlock(iso) {
    if (!HANDEL) return "";
    const h = HANDEL.laender[iso];
    if (!h) return `<div class="gk-block"><h3>Handel</h3><p class="gk-leer">${esc(landName(iso))} meldet keine Handelsdaten an UN Comtrade (jüngste Jahre).</p></div>`;
    const mrd = v => v == null ? "–" : f1.format(v / 1e9);
    const nachP = {}; (h.export || []).forEach(([p, v]) => { (nachP[p] = nachP[p] || {}).x = v; }); (h.import || []).forEach(([p, v]) => { (nachP[p] = nachP[p] || {}).m = v; });
    const zeilen = Object.entries(nachP).sort((a, b) => ((b[1].x || 0) + (b[1].m || 0)) - ((a[1].x || 0) + (a[1].m || 0))).slice(0, 10);
    const saldo = h.export_welt != null && h.import_welt != null ? h.export_welt - h.import_welt : null;
    const knopf = (w, t) => `<button type="button" data-gkhandel="${w}" aria-pressed="${S.handel === w}">${t}</button>`;
    return `<div class="gk-block"><h3>Handel ${esc(h.jahr)}</h3>
      <div class="gk-kz" style="grid-template-columns:1fr 1fr 1fr;margin-bottom:8px">
        <div><div class="t" style="min-height:0">Exporte</div><div class="v" style="font-size:15px">${mrd(h.export_welt)}</div><div class="z">Mrd. USD</div></div>
        <div><div class="t" style="min-height:0">Importe</div><div class="v" style="font-size:15px">${mrd(h.import_welt)}</div><div class="z">Mrd. USD</div></div>
        <div><div class="t" style="min-height:0">Saldo</div><div class="v" style="font-size:15px;color:var(--${saldo == null ? "ink" : saldo >= 0 ? "up" : "down"})">${saldo == null ? "–" : (saldo > 0 ? "+" : "") + mrd(saldo)}</div><div class="z">Mrd. USD</div></div></div>
      <table class="gk-tab"><thead><tr><th>Partner</th><th style="text-align:right">Export</th><th style="text-align:right">Import</th></tr></thead><tbody>
        ${zeilen.map(([p, w]) => `<tr><td><button type="button" class="gk-link" data-gkland="${esc(p)}">${esc(landName(p))}</button></td><td>${mrd(w.x)}</td><td>${mrd(w.m)}</td></tr>`).join("")}</tbody></table>
      <div class="gk-chips" style="margin-top:8px">${knopf("beide", "Beide")}${knopf("export", "Exporte")}${knopf("import", "Importe")}<button type="button" data-gkhandelzeigen>Auf dem Globus zeigen</button></div>
      <p class="gk-quelle" style="margin-top:6px">Mrd. USD, Warenhandel laut Meldung von ${esc(landName(iso))} (Exporte FOB, Importe meist CIF); die zehn größten Partner; auf dem Globus in Stufe 2 die drei größten je Richtung (grün Exporte, rot Importe). Quelle: <a href="${esc(HANDEL.url)}" target="_blank" rel="noopener">UN Comtrade</a>, Abruf ${esc(HANDEL.abruf)}.</p></div>`;
  }
  function tabellenBlock(iso) {
    const st = stammImLand(iso); if (!st.length) return "";
    const genau = st.filter(r => r.genau).length, notiert = st.filter(r => r.notiert === "ja").length;
    const quelle = {}; st.filter(r => r.genau).forEach(r => { quelle[r.q] = (quelle[r.q] || 0) + 1; });
    return `<div class="gk-block"><h3>Weitere Unternehmen (nur Stammdaten) · ${f0.format(st.length)}</h3>
      <p class="gk-quelle">Aus der Unternehmenstabelle, ohne Kennzahlen im Terminal; ${f0.format(notiert)} börsennotiert. Sitz bekannt bei ${f0.format(genau)}${genau ? ` (${Object.entries(quelle).sort((a, b) => b[1] - a[1]).map(([q, n]) => `${f0.format(n)} ${esc({ tabelle: "aus der Tabelle", gleif: "über GLEIF", wikidata: "über Wikidata" }[q] || q)}`).join(", ")})` : ""};
      bei ${f0.format(st.length - genau)} ist nur das Land bekannt, sie stehen im grauen Ring „ohne Ort“ in der Landesmitte. Kleine Punkte auf der Karte öffnen die Stammdaten.</p>
      ${NUR_LAND[iso] ? `<div class="gk-chips" style="margin-top:8px"><button type="button" data-gkliste="${esc(iso)}">Liste ohne Ort (${f0.format(NUR_LAND[iso].length)})</button></div>` : ""}</div>`;
  }
  function firmenBlock(iso) {
    const alle = firmenImLand(iso);
    if (!alle.length) return `<div class="gk-block"><h3>Unternehmen</h3><p class="gk-leer">Im Terminal sind für ${esc(landName(iso))} noch keine Unternehmen mit Kennzahlen erfasst.</p></div>${tabellenBlock(iso)}`;
    const groesse = f => (f.werte && (f.werte.marktkap || f.werte.bilanzsumme || f.werte.umsatz)) || 0;
    const sortiert = [...alle].sort((a, b) => groesse(b) - groesse(a));
    const ohne = ohneSitz(iso).length;
    const nachBr = {}; alle.forEach(f => { const b = UNT.brName(f.branche); nachBr[b] = (nachBr[b] || 0) + 1; });
    return `<div class="gk-block"><h3>Unternehmen · ${f0.format(alle.length)}</h3>
      <div class="gk-chips" style="margin-bottom:8px">${Object.entries(nachBr).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([b, n]) => `<button type="button" disabled style="cursor:default">${esc(b)} ${f0.format(n)}</button>`).join("")}</div>
      <ul class="gk-liste">${sortiert.slice(0, 25).map(f => `<li><button type="button" data-gkfirma="${esc(f.id)}" title="${esc(f.name)}">${esc(UNT.kurzName(f.name))}</button><span class="r">${esc(UNT.brName(f.branche))}</span></li>`).join("")}</ul>
      ${sortiert.length > 25 ? `<p class="gk-quelle" style="margin-top:6px">Die 25 größten nach Börsenwert, Bilanzsumme bzw. Umsatz; alle über die Suche oben oder auf der Karte.</p>` : ""}
      <div class="gk-chips" style="margin-top:8px"><button type="button" data-gkzeigen="${esc(iso)}">Auf der Karte zeigen</button>
        <button type="button" data-gknurland aria-pressed="${S.nurLand}">Nur dieses Land auf der Karte</button></div>
      ${ohne ? `<p class="gk-quelle" style="margin-top:6px">${f0.format(ohne)} davon ohne bekannten Sitz und daher nicht auf der Karte (Liste in stammdaten/geo/sitz_geo.csv).</p>` : ""}</div>${tabellenBlock(iso)}`;
  }
  /* ----- Seitenleisten je Darstellungsform -----
     Rechts die Seitenleiste; bei Mehrfachauswahl (Shift) zusätzlich links: Kacheln abwechselnd rechts (1., 3. …) und links (2., 4. …). */
  const WB_KACHELN = [["bip_wachstum", "BIP real, ggü. Vorjahr", "%", 1], ["inflation", "Inflation", "%", 0], ["arbeitslos", "Arbeitslosenquote (ILO)", "%", -1], ["leistungsbilanz", "Leistungsbilanz", "% BIP", 0],
    ["schulden", "Schulden Zentralregierung", "% BIP", -1], ["bip_pk_kkp", "BIP je Einwohner (KKP)", "USD", 1], ["exporte_bip", "Exporte (Waren und Dienste)", "% BIP", 0], ["fdi", "Direktinvestitionen, Zufluss", "% BIP", 0],
    ["bip_usd", "BIP nominal", "Mrd. USD", 1], ["einwohner", "Einwohner", "Mio.", 0]];
  function weltbankBlock(iso, titel = "Jahreswerte (Weltbank)") {
    if (!WELT || !WELT.laender[iso]) return "";
    const kacheln = WB_KACHELN.map(([k, t, einheit, gut]) => {
      const p = WELT.laender[iso][k]; if (!p || !p.length) return "";
      const skal = k === "bip_usd" ? 1e9 : k === "einwohner" ? 1e6 : 1, s = { frequenz: "A", format: k === "bip_pk_kkp" || k === "bip_usd" ? "zahl0" : "" };
      const r = { s, p: p.map(([j, v]) => [String(j), v / skal]) }, [j, v] = r.p[r.p.length - 1], vj = r.p.length > 1 ? r.p[r.p.length - 2] : null;
      const d = vj ? v - vj[1] : null, richtung = d == null || !gut || Math.abs(d) < 1e-9 ? "" : (d > 0) === (gut > 0) ? "up" : "down";
      return `<div title="${esc(WELT.reihen[k] ? WELT.reihen[k].name : t)} · Weltbank ${esc(WELT.reihen[k] ? WELT.reihen[k].indikator : "")}"><div class="t">${esc(t)}</div><div class="v">${zahl(v, s)}<span style="font-size:11px;color:var(--ink-3)"> ${esc(einheit)}</span></div>
        <div class="z">${esc(j)}${d == null ? "" : ` · <span class="d ${richtung}">${d > 0 ? "+" : ""}${zahl(d, s)}</span> ggü. Vorjahr`}</div>${spark(r)}</div>`;
    }).filter(Boolean);
    if (!kacheln.length) return "";
    return `<div class="gk-block"><h3>${esc(titel)}</h3><div class="gk-kz">${kacheln.join("")}</div>
      <p class="gk-quelle" style="margin-top:6px">Letztes verfügbares Jahr, Linie = Verlauf bis zu zehn Jahre. <a href="${esc(WELT.url)}" target="_blank" rel="noopener">Weltbank, World Development Indicators</a> (CC BY 4.0), Abruf ${esc(WELT.abruf)}.</p></div>`;
  }
  function zollBlock(iso) {
    const z = zollVon(iso); if (z.einfach == null && !z.effektiv) return "";
    const us = WELT && WELT.us_zoll_effektiv;
    return `<div class="gk-block"><h3>Zölle</h3><table class="gk-tab"><tbody>
      ${z.einfach != null ? `<tr><td>Angewandter Zollsatz, einfacher Durchschnitt</td><td>${f1.format(z.einfach)} %</td></tr>` : ""}
      ${z.gewichtet != null ? `<tr><td>… handelsgewichtet</td><td>${f1.format(z.gewichtet)} %</td></tr>` : ""}
      ${z.effektiv ? `<tr><td>Effektive Zollbelastung ${esc(z.effektiv.zeit.replace("-Q", " Q"))}</td><td>${f1.format(z.effektiv.wert)} %</td></tr>` : ""}</tbody></table>
      <p class="gk-quelle" style="margin-top:6px">Zollsätze, die ${esc(landName(iso))} auf Einfuhren erhebt, alle Waren, Weltbank ${esc(z.jahr || "")} (jüngstes Jahr mit Angaben; Sonderzölle seit 2025 nicht enthalten).${z.effektiv && us ? ` Effektive Belastung: ${esc(us.quelle)}; abgeleitet, nicht amtlich.` : ""}</p></div>`;
  }
  function stromBilateralBlock(iso) {
    if (!hatStromBilateral(iso)) return stromBlock(iso);
    const nb = nachbarnVon(iso), twh = v => v == null ? "–" : f1.format(v / 1000);
    const wert = (a, b) => (STROM_PAARE.find(p => p.a === a && p.b === b) || {}).v;
    const z = nb.map(q => ({ q, x: wert(iso, q), m: wert(q, iso) })).filter(r => r.x != null || r.m != null);
    return `<div class="gk-block"><h3>Strom mit Nachbarländern ${esc(WELT.strom.jahr)}</h3>${z.length ? `<table class="gk-tab"><thead><tr><th>Nachbar</th><th style="text-align:right">Ausfuhr TWh</th><th style="text-align:right">Einfuhr TWh</th></tr></thead><tbody>
      ${z.map(r => `<tr><td><button type="button" class="gk-link" data-gkland="${esc(r.q)}">${esc(landName(r.q))}</button></td><td>${twh(r.x)}</td><td>${twh(r.m)}</td></tr>`).join("")}</tbody></table>` : `<p class="gk-leer">Keine Stromflüsse mit Nachbarn gemeldet.</p>`}
      <p class="gk-quelle" style="margin-top:6px">Auf der Karte gelb: Ausfuhr durchgezogen, Einfuhr gestrichelt. <a href="${esc(WELT.strom.url)}" target="_blank" rel="noopener">${esc(WELT.strom.quelle)}</a>.</p></div>`;
  }
  function stoerungBlock(max = 6) {
    if (!ROUTEN) return "";
    const l = ROUTEN.knoten.filter(k => meld(k.id).length).sort((a, b) => (meld(b.id)[0].datum || "").localeCompare(meld(a.id)[0].datum || ""));
    return `<div class="gk-block"><h3>Meldungen: Störungen an Engstellen</h3>${NEWS ? MLD.banner(NEWS.abruf, NEWS.fehler) : ""}${MLD.reiter(l.reduce((a, k) => a + meld(k.id).length, 0))}${l.length ? `<ul class="gk-liste">${l.slice(0, max).map(k => `<li><button type="button" data-gkmeldung="${esc(k.id)}">${MLD.symbol(meld(k.id)[0], 13)} ${esc(k.name)}</button><span class="r">${esc(MLD.alterText(meld(k.id)[0].datum))} · ${meld(k.id).length}</span></li>`).join("")}</ul>`
      : `<p class="gk-leer">Keine Meldungen in den letzten ${MLD.S.fenster} Tagen. Die Reiter 7 und 14 Tage zeigen ältere.</p>`}${MLD.legende()}<p class="gk-quelle" style="margin-top:6px">Echte Artikel (Originaltitel, Quelle, Datum)${NEWS ? ` über ${esc(NEWS.quelle.split(" (")[0])}, ${esc(MLD.stempel(NEWS.abruf))}` : ""}. Ein Symbol erscheint nur, wenn der Titel die Engstelle und eine Störung nennt; ältere als 14 Tage nie.</p></div>`;
  }
  function stromRaumBlock() {
    const f = stromRaumDaten().features; if (!f.length) return "";
    return `<div class="gk-block"><h3>Strom zwischen Wirtschaftsräumen ${esc(WELT.strom.jahr)}</h3><table class="gk-tab"><thead><tr><th>Netto</th><th style="text-align:right">TWh</th><th style="text-align:right">brutto</th></tr></thead><tbody>
      ${f.slice(0, 10).map(x => `<tr><td>${esc(x.properties.von)} → ${esc(x.properties.nach)}</td><td>${f1.format(x.properties.netto / 1000)}</td><td>${f1.format(x.properties.brutto / 1000)}</td></tr>`).join("")}</tbody></table>
      <p class="gk-quelle" style="margin-top:6px">Summe der Flüsse zwischen Ländern verschiedener Räume, nur Flüsse mit europäischen Meldeländern (Eurostat). Für andere Weltregionen gibt es keine freie bilaterale Quelle ohne Schlüssel.</p></div>`;
  }
  const kopfForm = () => { const f = FORMEN.find(x => x[0] === S.form);
    return `<div class="gk-formkopf"><span>${esc(f[1])}</span><a class="gk-link" href="#${f[2]}" title="Bereich im klassischen Terminal öffnen">Im Terminal ↗</a></div>${S.form === "politik" ? ansichtReiter() : ""}${ENTWURF[S.form] ? `<p class="gk-entwurf">Entwurf zur Freigabe: die Darstellung ${esc(f[1])} wird nach Robins Wahl der Varianten gebaut. Bis dahin ${S.form === "unternehmen" ? "die bisherige Darstellung (Unternehmen nach Sitz, Profil, Netz)" : S.form === "boerse" ? "Leitindizes und Börsenwerte je Land aus dem Bereich BÖR" : "ein Platzhalter"}.</p>` : ""}`; };
  // Politik: Ansicht Wahlen (Wahlergebnisse je Ebene, src/wahlen.js) oder Regierungen (Ausrichtung, Bündnisse, Regierungschefs, Parlamente heute)
  const ansichtReiter = () => `<div class="gk-ansicht" role="tablist" aria-label="Ansicht">${[["wahlen", "Wahlen"], ["regierungen", "Regierungen"]].map(([k, t]) => `<button type="button" role="tab" data-gkpolansicht="${k}" aria-selected="${S.polAnsicht === k}">${t}</button>`).join("")}</div>`;
  function politikAnsicht(v) {
    if (v !== "wahlen" && v !== "regierungen") return;
    S.polAnsicht = v;
    try { localStorage.setItem("globus-politik", v); } catch { /* kein Speicher */ }
    if (map && stilBereit) EBENEN.forEach(e => { if (e.quellen) sichtbar(e); });
    stufeChips(); legendeKarte(); seiteZeichnen();
    document.dispatchEvent(new CustomEvent("globus:politik", { detail: { ansicht: v } }));
  }
  const zurueck = () => `<div class="gk-chips" style="margin-bottom:8px"><button type="button" data-gkland="">← Alle Länder</button></div>`;
  function karteLand(iso) {
    const h = HANDEL && HANDEL.laender[iso], a = aktuell(iso), s = saldoVon(iso), mrd = v => v == null ? "–" : f1.format(v / 1e9);
    const kz = (t, v, z) => `<div><div class="t" style="min-height:0">${esc(t)}</div><div class="v" style="font-size:15px">${v}</div><div class="z">${esc(z || "")}</div></div>`;
    let inhalt;
    const fk = karteForm(iso);
    if (fk != null) inhalt = fk;
    else if (S.form === "handel") {
      const liste = (l, r) => (l || []).slice(0, 5).map(([p, v]) => `<li><button type="button" data-gkland="${esc(p)}">${esc(landName(p))}</button><span class="r" style="color:${r === "x" ? HEX_EXP : HEX_IMP}">${mrd(v)}</span></li>`).join("");
      inhalt = h ? `<div class="gk-kz" style="grid-template-columns:1fr 1fr 1fr">${kz("Exporte", mrd(h.export_welt), "Mrd. USD " + h.jahr)}${kz("Importe", mrd(h.import_welt), "Mrd. USD")}${kz("Saldo", `<span style="color:${s >= 0 ? HEX_EXP : HEX_IMP}">${s > 0 ? "+" : ""}${mrd(s)}</span>`, "Mrd. USD")}</div>
        <p class="gk-quelle" style="margin:6px 0">${esc(zollText(iso) || "Zollsatz unbekannt")}</p>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px"><div><h3>Export</h3><ul class="gk-liste">${liste(h.export, "x")}</ul></div><div><h3>Import</h3><ul class="gk-liste">${liste(h.import, "m")}</ul></div></div>` : `<p class="gk-leer">Keine Handelsmeldung an UN Comtrade.</p>`;
    } else {
      const lb = letzter(iso, "leistungsbilanz"), sch = letzter(iso, "schulden"), pk = letzter(iso, "bip_pk_kkp");
      inhalt = `<div class="gk-kz" style="grid-template-columns:1fr 1fr 1fr">${kz("BIP real", a.bip ? vz(a.bip.v) + " %" : "–", a.bip ? a.bip.zeit : "")}${kz("Inflation", a.inf ? f1.format(a.inf.v) + " %" : "–", a.inf ? a.inf.zeit : "")}${kz("Arbeitslose", a.al ? f1.format(a.al.v) + " %" : "–", a.al ? a.al.zeit : "")}
        ${kz("Leistungsbilanz", lb ? vz(lb[1]) + " %" : "–", lb ? "% BIP " + lb[0] : "")}${kz("Staatsschulden", sch ? f0.format(sch[1]) + " %" : "–", sch ? "% BIP " + sch[0] : "")}${kz("BIP je Einw.", pk ? f0.format(pk[1] / 1000) + " Tsd." : "–", pk ? "USD KKP " + pk[0] : "")}</div>`;
    }
    return `<div class="gk-landkarte"><div class="kopf"><button type="button" class="gk-link" data-gkland="${esc(iso)}" title="nur dieses Land">${esc(landName(iso))}</button><button type="button" class="zu" data-gkweg="${esc(iso)}" aria-label="${esc(landName(iso))} entfernen">×</button></div>${inhalt}</div>`;
  }
  function seiteMehrfach(el, links) {
    const rechts = S.auswahl.filter((_, i) => i % 2 === 0), li = S.auswahl.filter((_, i) => i % 2 === 1);
    el.innerHTML = `${kopfForm()}<div><h2>${f0.format(S.auswahl.length)} Länder</h2><p class="unter" style="margin-top:4px">Shift+Klick fügt Länder hinzu oder nimmt sie heraus · Klick ohne Shift wählt nur ein Land</p></div>${rechts.map(karteLand).join("")}
      <p class="gk-quelle">${{ handel: "Mrd. USD, Warenhandel laut Meldung des Landes (UN Comtrade). Auf der Karte je Land die fünf größten Export- (grün) und Importpartner (rot).",
        vwl: "Jüngster Wert je Land: Monats- bzw. Quartalswert aus Eurostat/OECD, sonst Jahreswert der Weltbank.", boerse: "Leitindex (Yahoo Finance), Rendite (OECD), Leitzins (BIS), Währung (EZB).",
        unternehmen: "Unternehmenstabelle (alle erfassten Unternehmen).", politik: "Wikidata (Regierung), Wikipedia (Wahlkalender, Zusammensetzung) und IPU Parline (Kammern, Wahlergebnisse)." }[S.form] || ""}</p>`;
    links.innerHTML = li.map(karteLand).join("");
    links.hidden = !li.length;
  }
  function handelStart() {
    const top = Object.entries(HANDEL.laender).filter(([i, h]) => h.export_welt && NACH_ISO[i]).sort((a, b) => b[1].export_welt - a[1].export_welt).slice(0, 12);
    return `<div><h2>Welthandel nach Ländern</h2><p class="unter" style="margin-top:4px">Land anklicken: die fünf größten Export- und Importpartner · Shift+Klick für mehrere Länder · unter jedem Land Zollsatz und Handelssaldo · hineinzoomen für Nachbarländer und Strom</p></div>
      <div class="gk-block"><h3>Größte Exportländer</h3><ul class="gk-liste">${top.map(([i, h]) => `<li><button type="button" data-gkland="${esc(i)}">${esc(landName(i))}</button><span class="r">${f0.format(h.export_welt / 1e9)} Mrd. USD</span></li>`).join("")}</ul>
        <p class="gk-quelle" style="margin-top:6px">UN Comtrade, Abruf ${esc(HANDEL.abruf)}.</p></div>${gutBlock()}${verkehrBlock()}${stoerungBlock()}${stromRaumBlock()}`;
  }
  function raumSeite() {
    const r = raumVon(S.raum);
    const chip = x => `<button type="button" data-gkraum="${esc(x.id)}" aria-pressed="${x.id === S.raum}" style="border-left:3px solid ${esc(x.farbe)}">${esc(x.kurz)}</button>`;
    const auswahl = `<div class="gk-block"><h3>Wirtschaftsräume</h3><div class="gk-chips">${RAEUME.filter(x => x.art !== "uebergreifend").map(chip).join("")}</div>
      <h3 style="margin-top:10px">Übergreifend</h3><div class="gk-chips">${RAEUME.filter(x => x.art === "uebergreifend").map(chip).join("")}</div></div>`;
    const leg = `<p class="gk-quelle">Auf der Karte je Raum: BIP-Wachstum (blau positiv, orange negativ) und Inflation (orange über 5 %), BIP-gewichteter Durchschnitt des jüngsten Werts je Mitglied (Monats-/Quartalswerte von Eurostat/OECD, sonst Jahreswerte der Weltbank).</p>`;
    if (!r) {
      const zeilen = RAEUME.filter(x => x.art !== "uebergreifend").map(x => ({ x, w: raumWerte(x) })).sort((a, b) => b.w.bipSumme - a.w.bipSumme);
      return `<div><h2>Volkswirtschaften nach Wirtschaftsräumen</h2><p class="unter" style="margin-top:4px">Ganz herausgezoomt: Land anklicken wählt seinen Wirtschaftsraum · hineinzoomen für alle Länder</p></div>
        <div class="gk-block"><table class="gk-tab"><thead><tr><th>Raum</th><th style="text-align:right">BIP %</th><th style="text-align:right">Infl. %</th><th style="text-align:right">BIP Bio.</th></tr></thead><tbody>
        ${zeilen.map(({ x, w }) => `<tr><td><button type="button" class="gk-link" data-gkraum="${esc(x.id)}">${esc(x.kurz)}</button></td><td>${vz(w.bip)}</td><td>${w.inf == null ? "–" : f1.format(w.inf)}</td><td>${f1.format(w.bipSumme / 1e12)}</td></tr>`).join("")}</tbody></table>${leg}</div>
        ${auswahl}${stoerungBlock(4)}`;
    }
    const w = raumWerte(r), kz = (t, v, z) => `<div><div class="t" style="min-height:0">${esc(t)}</div><div class="v" style="font-size:16px">${v}</div><div class="z">${esc(z)}</div></div>`;
    const mitglieder = [...r.mitglieder].sort((a, b) => bipUsd(b) - bipUsd(a));
    return `<div><div class="gk-chips" style="margin-bottom:8px"><button type="button" data-gkraum="${esc(r.id)}">← Alle Räume</button></div><h2>${esc(r.name)}</h2>
        <p class="unter" style="margin-top:4px">${esc(r.kurz)} · ${f0.format(r.mitglieder.length)} Mitglieder${r.hinweis ? " · " + esc(r.hinweis) : ""}</p></div>
      <div class="gk-block"><h3>Kerndaten des Raums</h3><div class="gk-kz" style="grid-template-columns:1fr 1fr 1fr">
        ${kz("BIP-Wachstum", w.bip == null ? "–" : vz(w.bip) + " %", "gewichtet")}${kz("Inflation", w.inf == null ? "–" : f1.format(w.inf) + " %", "gewichtet")}${kz("Arbeitslosenquote", w.al == null ? "–" : f1.format(w.al) + " %", "gewichtet")}
        ${kz("Leistungsbilanz", w.lb == null ? "–" : vz(w.lb) + " %", "% BIP, gewichtet")}${kz("BIP nominal", f1.format(w.bipSumme / 1e12), "Bio. USD")}${kz("Einwohner", f0.format(w.einwohner / 1e6), "Mio.")}</div>
        <p class="gk-quelle" style="margin-top:6px">Gewichtet mit dem nominalen BIP (Weltbank); erfasst ${f0.format(w.abdeckung * 100)} % des BIP des Raums. Mitgliedschaft laut <a href="${esc(r.quelle)}" target="_blank" rel="noopener">Quelle</a>, Stand ${esc(r.stand)}.</p></div>
      <div class="gk-block"><h3>Mitglieder</h3><table class="gk-tab"><thead><tr><th>Land</th><th style="text-align:right">BIP %</th><th style="text-align:right">Infl. %</th><th style="text-align:right">Arb.-l. %</th></tr></thead><tbody>
        ${mitglieder.map(i => { const a = aktuell(i); return `<tr><td><button type="button" class="gk-link" data-gkland="${esc(i)}">${esc(landName(i))}</button></td><td title="${esc(a.bip ? a.bip.zeit + " · " + a.bip.quelle : "")}">${a.bip ? vz(a.bip.v) : "–"}</td><td title="${esc(a.inf ? a.inf.zeit + " · " + a.inf.quelle : "")}">${a.inf ? f1.format(a.inf.v) : "–"}</td><td>${a.al ? f1.format(a.al.v) : "–"}</td></tr>`; }).join("")}</tbody></table>
        <p class="gk-quelle" style="margin-top:6px">Jüngster Wert je Land (Zeitraum und Quelle im Tooltip).</p></div>${auswahl}${stoerungBlock(4)}`;
  }
  function vwlStart() {
    const top = Object.keys(NACH_ISO).filter(i => aktuell(i).bip || aktuell(i).inf).sort((a, b) => bipUsd(b) - bipUsd(a)).slice(0, 20);
    return `<div><h2>Volkswirtschaften der Welt</h2><p class="unter" style="margin-top:4px">BIP-Wachstum und Inflation direkt auf der Karte · Land anklicken für alle Daten rechts · Shift+Klick für mehrere Länder (Kacheln beidseitig)</p></div>
      <div class="gk-block"><h3>Die 20 größten Volkswirtschaften</h3><table class="gk-tab"><thead><tr><th>Land</th><th style="text-align:right">BIP %</th><th style="text-align:right">Infl. %</th><th style="text-align:right">Stand</th></tr></thead><tbody>
      ${top.map(i => { const a = aktuell(i); return `<tr><td><button type="button" class="gk-link" data-gkland="${esc(i)}">${esc(landName(i))}</button></td><td>${a.bip ? vz(a.bip.v) : "–"}</td><td>${a.inf ? f1.format(a.inf.v) : "–"}</td><td class="pct">${esc(a.inf ? a.inf.zeit : a.bip ? a.bip.zeit : "")}</td></tr>`; }).join("")}</tbody></table>
      <p class="gk-quelle" style="margin-top:6px">Jüngster Wert je Land: Monats- bzw. Quartalswerte von Eurostat/OECD, sonst Jahreswerte der Weltbank (CC BY 4.0). Farben: Wachstum blau positiv, orange negativ; Inflation orange über 5 %, blau unter 0 %.</p></div>${stoerungBlock(4)}`;
  }
  function landSeite(iso, stufe) {
    const f = NACH_ISO[iso], p = f ? f.properties : {};
    const kopf = `<div>${zurueck()}<h2>${esc(p.name || landName(iso))}</h2><p class="unter" style="margin-top:4px">${esc(iso)}${p.region ? " · " + esc(p.region) : ""}${RAUM_VON[iso] ? " · " + esc(raumVon(RAUM_VON[iso]).name) : ""}</p></div>`;
    const basis = p.einwohner && !(WELT && WELT.laender[iso]) ? `<div class="gk-block"><h3>Grundangaben</h3><table class="gk-tab"><tbody>
      <tr><td>Einwohner</td><td>${f1.format(p.einwohner / 1e6)} Mio. <span class="pct">(${esc(p.einwohner_jahr)})</span></td></tr>
      <tr><td>BIP nominal</td><td>${f0.format(p.bip_mio_usd / 1000)} Mrd. USD <span class="pct">(${esc(p.bip_jahr)})</span></td></tr>
      <tr><td>Einkommensgruppe</td><td style="font-family:var(--sans)">${esc(p.einkommen || "–")}</td></tr></tbody></table>
      <p class="gk-quelle" style="margin-top:6px">Natural Earth (Weltbank-Schätzungen des genannten Jahres), nur zur Einordnung.</p></div>` : "";
    const k = kerndaten(iso);
    const kern = k.length ? `<div class="gk-block"><h3>Kerndaten (aktuell)</h3><div class="gk-kz">${k.join("")}</div>
        <p class="gk-quelle" style="margin-top:6px">Jüngster veröffentlichter Wert; Linie = Verlauf (5 Jahre bzw. 10 Jahre bei Jahreswerten), gestrichelt = OECD-Projektion. Eurostat, wo vorhanden, sonst OECD. Stand des Abrufs ${esc((vwlDaten() || {}).stand || "")}.</p></div>` : "";
    const stufe3 = (inhalt, was) => stufe >= 3 ? inhalt : `<div class="gk-block"><h3>${esc(was)}</h3><p class="gk-leer">Näher heranzoomen (Stufe 3), dann erscheinen ${esc(was)}.</p><div class="gk-chips" style="margin-top:8px"><button type="button" data-gkstufe="3">Zu Stufe 3</button></div></div>`;
    if (S.form === "handel") return kopf + handelBlock(iso) + gutLandBlock(iso) + verkehrLandBlock(iso) + zollBlock(iso) + stufe3(nachbarBlock(iso) + stromBilateralBlock(iso), "Nachbarländer, weitere Partner und Strom") + stoerungBlock(4);
    if (S.form === "unternehmen") return kopfForm() + kopf + (stufe < 3 ? ufBlock() : "") + firmenBlock(iso) + (stufe >= 3 ? nachbarFirmenBlock(iso) : "") + basis;
    if (S.form === "boerse") return kopfForm() + kopf + boerseLand(iso, stufe);
    if (S.form === "politik") return kopfForm() + kopf + politikLand(iso, stufe);
    // Volkswirtschaft; Stufe 3 = Kombination mit Handel, Strom, Unternehmen, Börse (Politik folgt nach Freigabe)
    return kopf + kern + weltbankBlock(iso, k.length ? "Jahreswerte (Weltbank)" : "Kerndaten (Jahreswerte, Weltbank)") + prognosen(iso)
      + stufe3(handelBlock(iso) + zollBlock(iso) + nachbarBlock(iso) + stromBilateralBlock(iso) + firmenBlock(iso) + indizes(iso)
        + politikLand(iso, 2), "Handel, Nachbarländer, Strom, Unternehmen, Börse und Politik") + basis;
  }
  function seiteZeichnen() {
    const el = document.getElementById("gk-seite"), links = document.getElementById("gk-seite-links"); if (!el) return;
    formLeiste();
    if (links) { links.hidden = true; links.innerHTML = ""; }
    const iso = S.land, stufe = map ? S.stufe : 3;       // ohne Karte (kein WebGL) alles in der Seitenleiste
    let html;
    if (S.auswahl.length > 1 && links) { seiteMehrfach(el, links); el.scrollTop = 0; return; }
    if (S.form === "handel") html = !HANDEL ? `<div><h2>Handel</h2><p class="gk-leer">Keine Handelsdaten im Build.</p></div>` : !iso && stufe === 1 ? kontSeite() : !iso ? handelStart() : landSeite(iso, stufe);
    else if (S.form === "vwl") html = !iso && stufe === 1 ? raumSeite() : !iso ? vwlStart() : landSeite(iso, stufe);
    else if (S.form === "boerse") html = iso ? landSeite(iso, stufe) : kopfForm() + boerseStart();
    else if (S.form === "politik") html = S.polAnsicht === "wahlen" && typeof WAHLEN !== "undefined" ? kopfForm() + WAHLEN.seite() : iso ? landSeite(iso, stufe) : kopfForm() + politikStart();
    else html = iso ? landSeite(iso, stufe) : kopfForm() + (stufe === 1 ? unternehmenWelt() : unternehmenStart());
    el.innerHTML = (S.form === "handel" || S.form === "vwl" ? kopfForm() : "") + html;
    el.scrollTop = 0;
  }
  function unternehmenStart() {
    const n = {}; PUNKTE.forEach(p => { n[p.properties.land] = (n[p.properties.land] || 0) + 1; });
    const top = Object.entries(n).sort((a, b) => b[1] - a[1]).slice(0, 12);
    return `<div><h2>Unternehmen</h2><p class="unter" style="margin-top:4px">Unternehmen nach Sitz, Gruppen zerfallen beim Hineinzoomen · Unternehmen anklicken für das Profil · Shift+Klick nimmt es in den Vergleich · Land anklicken für seine Unternehmen</p></div>${ufBlock()}
      <div class="gk-block"><h3>Länder mit den meisten Unternehmen</h3><ul class="gk-liste">${top.map(([iso2, k]) => `<li><button type="button" data-gkland="${esc(iso2)}">${esc(landName(iso2))}</button><span class="r">${f0.format(k)}</span></li>`).join("")}</ul></div>
      <div class="gk-block"><h3>Daten</h3><p class="gk-quelle">${f0.format(PUNKTE.length)} Unternehmen auf der Karte: ${f0.format(PUNKTE.filter(p => p.properties.art === "t").length)} mit Kennzahlen im Terminal, die übrigen mit Stammdaten aus der Unternehmenstabelle. Weitere ${f0.format(nurLandAnzahl())} Unternehmen, deren Sitz nur auf Landesebene bekannt ist, stehen in den grauen Ringen „ohne Ort“ in der Landesmitte.</p></div>`;
  }
  /* Leiste der Darstellungsformen oben auf der Karte */
  function formLeiste() {
    const el = document.getElementById("gk-formen"); if (!el) return;
    el.innerHTML = FORMEN.map(([id, t]) => `<button type="button" role="tab" data-gkform="${id}" aria-selected="${S.form === id}"${ENTWURF[id] ? ' title="Entwurf zur Freigabe"' : ""}>${esc(t)}${ENTWURF[id] ? "<sup>E</sup>" : ""}</button>`).join("");
  }
  // Ländernamen: im Handel tragen ab Stufe 2 die Beschriftungen (Name, Zoll, Saldo) den Namen, in der Volkswirtschaft die Werte
  function namenZoom() {
    if (!map || !map.getLayer("laender-name")) return;
    if (S.form === "handel" || S.form === "boerse" || S.form === "politik") map.setLayerZoomRange("laender-name", 0, ZG[0]);
    else if (S.form === "vwl") map.setLayoutProperty("laender-name", "visibility", "none");
    else map.setLayerZoomRange("laender-name", 0, 5.5);
    if (S.form !== "vwl") map.setLayoutProperty("laender-name", "visibility", "visible");
  }
  function formWaehlen(f) {
    if (!FORMEN.some(x => x[0] === f)) return;
    S.form = f;
    try { localStorage.setItem("globus-form", f); } catch { /* kein Speicher */ }
    if (map && stilBereit) { EBENEN.forEach(e => { if (e.quellen) sichtbar(e); }); handelAktualisieren(); routenAktualisieren(); stromAktualisieren(); vwlAnwenden(); namenZoom(); untZoom(); punkteAktualisieren(); }
    stufeChips();
    if (f !== "politik") S.region = null;
    ebenenListe(); legendeKarte(); seiteZeichnen(); vorschauen();
    document.dispatchEvent(new CustomEvent("globus:form", { detail: { form: f } }));
    if (ENTWURF[f]) hinweis(`${FORMEN.find(x => x[0] === f)[1]}: Entwurf zur Freigabe, bis dahin bisherige Darstellung`);
  }

  /* ----- Fenster (Pop-ups) für Unternehmen und Vergleich ----- */
  const fensterKey = x => x.art + ":" + (x.id || "");
  function fensterEl() { return document.getElementById("gk-fenster"); }
  // Andere Teile (z. B. das Unternehmensnetz, netz.js) hören auf "globus:firma" bzw. "globus:firma-zu"
  const melden = (typ, id) => document.dispatchEvent(new CustomEvent(typ, { detail: { id } }));
  function firmaOeffnen(id, opt = {}) {
    const f = UNT.nachId(id); if (!f) return;
    id = f.id;
    melden("globus:firma", id);
    const da = S.offen.find(x => x.art === "firma" && x.id === id);
    if (da) { nachVorne(da); return; }
    neuesFenster({ art: "firma", id });
    punkteAktualisieren();
    if (opt.fliegen && map) { const p = PUNKTE.find(x => x.properties.id === id); if (p) { if (S.land && S.nurLand && p.properties.land !== S.land) landWaehlen(p.properties.land); map.flyTo({ center: p.geometry.coordinates, zoom: Math.max(map.getZoom(), 8), duration: 1200 }); } else hinweis("Sitz nur auf Landesebene bekannt, daher ohne eigenen Punkt auf der Karte"); }
  }
  // Profil des Terminals, wenn es das Unternehmen kennt (auch als Platzhalter mit Registerdaten), sonst Stammdaten-Fenster
  const oeffnen = (id, opt = {}) => UNT.nachId(id) ? firmaOeffnen(id, opt) : stammOeffnen(id, opt);
  function stammOeffnen(k, opt = {}) {
    if (!STAMM[k]) return;
    melden("globus:firma", STAMM[k].id || k);
    const da = S.offen.find(x => x.art === "stamm" && x.id === k);
    if (da) { nachVorne(da); return; }
    neuesFenster({ art: "stamm", id: k });
    punkteAktualisieren();
    if (opt.fliegen && map) { const p = PUNKTE.find(x => x.properties.id === k); if (p) { if (S.land && S.nurLand && p.properties.land !== S.land) landWaehlen(p.properties.land); map.flyTo({ center: p.geometry.coordinates, zoom: Math.max(map.getZoom(), 8), duration: 1200 }); } else hinweis("Sitz nur auf Landesebene bekannt, daher ohne eigenen Punkt auf der Karte"); }
  }
  function listeOeffnen(iso) {
    if (!NUR_LAND[iso]) return;
    const da = S.offen.find(x => x.art === "liste" && x.id === iso);
    if (da) { nachVorne(da); return; }
    neuesFenster({ art: "liste", id: iso, filter: "" });
  }
  function listeEintraege(x) {
    const q = (x.filter || "").trim().toLowerCase(), alle = NUR_LAND[x.id] || [];
    const l = (q ? alle.filter(p => p.name.toLowerCase().includes(q) || (STAMM[p.id] && (STAMM[p.id].isin.toLowerCase() === q || STAMM[p.id].ticker.toLowerCase() === q))) : alle)
      .slice().sort((a, b) => b.art.localeCompare(a.art) || a.name.localeCompare(b.name, "de"));
    return `<p class="gk-quelle" style="margin:6px 0">${f0.format(l.length)} Treffer${l.length > 300 ? ", die ersten 300" : ""}</p><ul class="gk-liste">${l.slice(0, 300).map(p =>
      `<li><button type="button" data-gkfirma="${esc(p.id)}">${esc(p.name)}</button><span class="r">${esc(p.art === "t" ? "Kennzahlen" : p.branche)}</span></li>`).join("")}</ul>`;
  }
  function listeAnsicht(x) {
    const n = (NUR_LAND[x.id] || []).length;
    return `<div class="gk-stamm"><p class="gk-leer" style="margin:0 0 8px">Für diese ${f0.format(n)} Unternehmen ist der Sitz nur auf Landesebene bekannt, sie haben daher keinen eigenen Punkt auf der Karte. Herkunft: Unternehmenstabelle; weder die Tabelle noch GLEIF oder Wikidata nennen einen Ort.</p>
      <input type="search" class="gk-filter" data-gklistefilter placeholder="Name, ISIN oder Kürzel filtern" value="${esc(x.filter || "")}" aria-label="Liste filtern">
      <div class="gk-listeninhalt">${listeEintraege(x)}</div></div>`;
  }
  const QUELLE_GEO = { tabelle: "Spalte Sitz der Unternehmenstabelle", gleif: "Anschrift laut GLEIF (LEI-Register)", wikidata: "Hauptsitz laut Wikidata" };
  // API-Fassung: Rechtsform, Börse, LEI, Handelsregister, Website, Beschreibung und Quelle über die Plattform-API nachladen
  const stammLaeuft = {};
  async function stammNachladen(k) {
    const r = STAMM[k];
    try {
      const d = (await API.unternehmenEins(r.id)).data;
      Object.assign(r, { rf: d.legal_form || "", boerse: d.exchange || "", lei: d.lei || "", hr: d.register_no || "", web: d.website || "",
        bank: d.is_bank ? "ja" : "nein", text: d.description || "", quelle: d.source_url || "", _voll: true });
    } catch (e) { r._fehler = e.message || "Laden fehlgeschlagen"; }
    delete stammLaeuft[k];
    S.offen.filter(x => x.art === "stamm" && x.id === k).forEach(fensterInhalt);
  }
  function stammAnsicht(k) {
    const r = STAMM[k]; if (!r) return `<p class="n">Unbekannt.</p>`;
    if (TABELLE && TABELLE.schlank && !r._voll && !r._fehler && typeof API !== "undefined" && API.aktiv && !stammLaeuft[k]) stammLaeuft[k] = stammNachladen(k);
    const laedt = TABELLE && TABELLE.schlank && !r._voll
      ? (r._fehler ? `<p class="n">Weitere Stammdaten nicht geladen: ${esc(r._fehler)} <button type="button" class="chip" data-gstammretry="${esc(k)}">Erneut versuchen</button></p>`
        : `<p class="n" role="status">Weitere Stammdaten werden geladen …</p>`) : "";
    const link = u => /^https?:\/\//.test(u) ? `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(u.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, ""))}</a>` : esc(u);
    const zeile = (t, v, roh) => v ? `<tr><td>${t}</td><td style="font-family:var(--sans);text-align:left">${roh ? v : esc(v)}</td></tr>` : "";
    const sitz = r.genau ? `${esc(r.ort || r.sitz)} <span class="pct">(${esc(QUELLE_GEO[r.q] || r.q || "")})</span>` : `<span class="pct">nicht bekannt, daher kein eigener Punkt auf der Karte (im Ring „ohne Ort“ in der Mitte von ${esc(landName(r.land))})</span>`;
    return `<div class="gk-stamm"><p class="gk-leer" style="margin:0 0 10px">Für dieses Unternehmen liegen im Terminal noch keine Kennzahlen vor. Angezeigt werden die Stammdaten aus der Unternehmenstabelle.</p>
      <table class="gk-tab"><tbody>
      ${zeile("Name", r.name)}${zeile("Rechtsform", r.rf)}${zeile("Land", landName(r.land))}${zeile("Sitz", sitz, true)}
      ${zeile("Branche", r.branche)}${zeile("Bank", r.bank)}${zeile("Börsennotiert", r.notiert)}${zeile("Börse", r.boerse)}${zeile("Kürzel", r.ticker)}${zeile("ISIN", r.isin)}
      ${zeile("LEI", r.lei ? `<a href="https://search.gleif.org/#/record/${esc(r.lei)}" target="_blank" rel="noopener">${esc(r.lei)}</a>` : "", true)}${zeile("Handelsregister", r.hr)}
      ${zeile("Index", r.index)}${zeile("Website", r.web ? link(r.web) : "", true)}${zeile("Beschreibung", r.text)}
      ${zeile("Quelle", r.quelle ? link(r.quelle) : "", true)}${zeile("Unternehmens-ID", r.id)}</tbody></table>${laedt}</div>`;
  }
  function vergleichOeffnen() {
    const da = S.offen.find(x => x.art === "vergleich");
    if (da) { fensterInhalt(da); nachVorne(da); return; }
    neuesFenster({ art: "vergleich" });
  }
  function neuesFenster(x) {
    const rand = fensterEl(), n = S.offen.length, schmal = innerWidth < 820;
    const bw = Math.min(980, innerWidth - 420), bh = Math.min(720, innerHeight - 110);
    x.pos = schmal ? { l: 8, t: 56, w: innerWidth - 16, h: innerHeight - 64 } : { l: 24 + (n % 6) * 34, t: 64 + (n % 6) * 30, w: Math.max(420, bw), h: Math.max(320, bh) };
    const el = document.createElement("section");
    el.className = "gf"; el.setAttribute("role", "dialog"); el.setAttribute("aria-label", "Unternehmensprofil");
    el.style.cssText = `left:${x.pos.l}px;top:${x.pos.t}px;width:${x.pos.w}px;height:${x.pos.h}px`;
    el.innerHTML = `<header class="gf-kopf"><div class="titel"></div><div class="knoepfe"></div></header><div class="gf-inhalt"></div>`;
    x.el = el; rand.appendChild(el);
    S.offen.push(x);
    ziehen(x);
    el.addEventListener("pointerdown", () => nachVorne(x), true);
    fensterInhalt(x); nachVorne(x); dock(); speichern();
  }
  function kopfZeichnen(x) {
    const t = x.el.querySelector(".titel"), k = x.el.querySelector(".knoepfe"), vgl = UNT.auswahl();
    if (x.art === "firma") {
      const f = UNT.nachId(x.id);
      t.innerHTML = `${esc(f ? f.name : x.id)}<small>${esc(x.id)}</small>`;
      k.innerHTML = `<button type="button" data-gfvgl="${esc(x.id)}" aria-pressed="${vgl.includes(x.id)}" title="Zum Vergleich hinzufügen oder entfernen">${vgl.includes(x.id) ? "✓ im Vergleich" : "+ Vergleich"}</button>
        <button type="button" data-gfkarte title="Sitz auf der Karte zeigen">Karte</button><button type="button" data-gfterminal title="Im klassischen Terminal öffnen">Terminal ↗</button>
        <button type="button" data-gfmax aria-label="Fenster maximieren">□</button><button type="button" data-gfzu aria-label="Fenster schließen">✕</button>`;
    } else if (x.art === "liste") {
      t.innerHTML = `${esc(landName(x.id))}: ohne bekannten Ort<small>${f0.format((NUR_LAND[x.id] || []).length)} Unternehmen</small>`;
      k.innerHTML = `<button type="button" data-gfmax aria-label="Fenster maximieren">□</button><button type="button" data-gfzu aria-label="Fenster schließen">✕</button>`;
    } else if (x.art === "stamm") {
      const r = STAMM[x.id] || {};
      t.innerHTML = `${esc(r.name || x.id)}<small>Stammdaten</small>`;
      k.innerHTML = `<button type="button" data-gfkarte title="Punkt auf der Karte zeigen">Karte</button>
        <button type="button" data-gfmax aria-label="Fenster maximieren">□</button><button type="button" data-gfzu aria-label="Fenster schließen">✕</button>`;
    } else {
      t.innerHTML = `Vergleich<small>${f0.format(vgl.length)} Unternehmen</small>`;
      k.innerHTML = `<button type="button" data-gfmax aria-label="Fenster maximieren">□</button><button type="button" data-gfzu aria-label="Fenster schließen">✕</button>`;
    }
  }
  function fensterInhalt(x) {
    kopfZeichnen(x);
    const ziel = x.el.querySelector(".gf-inhalt"), oben = ziel.scrollTop;
    ziel.innerHTML = x.art === "firma" ? UNT.viewProfil(x.id) : x.art === "stamm" ? stammAnsicht(x.id) : x.art === "liste" ? listeAnsicht(x) : (UNT.auswahl().length ? UNT.viewVgl() : `<p class="n">Noch keine Unternehmen im Vergleich. In einem Unternehmensfenster „+ Vergleich“ wählen.</p>`);
    ziel.scrollTop = oben;
  }
  function alleZeichnen() {
    S.offen.forEach(fensterInhalt);
    UNT.nachRender();
    if (typeof fkInit === "function") fkInit();
    dock();
  }
  function nachVorne(x) {
    S.z += 1; x.el.style.zIndex = S.z;
    S.offen.forEach(o => o.el.classList.toggle("aktiv", o === x)); S.aktiv = x;
  }
  function schliessen(x) {
    x.el.remove(); S.offen = S.offen.filter(o => o !== x);
    if (x.art === "firma" || x.art === "stamm") melden("globus:firma-zu", x.art === "stamm" && STAMM[x.id] ? STAMM[x.id].id || x.id : x.id);
    punkteAktualisieren(); dock(); speichern();
  }
  function ziehen(x) {
    const kopf = x.el.querySelector(".gf-kopf");
    let start = null;
    kopf.addEventListener("pointerdown", e => {
      if (e.target.closest("button") || x.el.classList.contains("max") || innerWidth < 820) return;
      start = { x: e.clientX, y: e.clientY, l: x.el.offsetLeft, t: x.el.offsetTop }; kopf.setPointerCapture(e.pointerId);
    });
    kopf.addEventListener("pointermove", e => {
      if (!start) return;
      const l = Math.min(innerWidth - 80, Math.max(-x.el.offsetWidth + 120, start.l + e.clientX - start.x)), t = Math.min(innerHeight - 40, Math.max(0, start.t + e.clientY - start.y));
      x.el.style.left = l + "px"; x.el.style.top = t + "px";
    });
    const ende = () => { if (start) { start = null; speichern(); } };
    kopf.addEventListener("pointerup", ende); kopf.addEventListener("pointercancel", ende);
    kopf.addEventListener("dblclick", e => { if (!e.target.closest("button")) x.el.classList.toggle("max"); });
  }
  function nebeneinander() {
    const fs = S.offen; if (!fs.length) return;
    const breite = innerWidth - (innerWidth < 820 ? 0 : 392), hoehe = innerHeight - 110, n = fs.length;
    const sp = n <= 3 ? n : Math.ceil(Math.sqrt(n)), zl = Math.ceil(n / sp), w = Math.floor((breite - 16 - (sp - 1) * 8) / sp), h = Math.floor((hoehe - (zl - 1) * 8) / zl);
    fs.forEach((x, i) => { x.el.classList.remove("max"); Object.assign(x.el.style, { left: 8 + (i % sp) * (w + 8) + "px", top: 60 + Math.floor(i / sp) * (h + 8) + "px", width: w + "px", height: h + "px" }); });
    speichern();
  }
  function dock() {
    const d = document.getElementById("gk-dock"); if (!d) return;
    const vgl = UNT.auswahl();
    d.hidden = !imGlobus || (!S.offen.length && !vgl.length);
    d.innerHTML = S.offen.map((x, i) => { const f = x.art === "firma" && UNT.nachId(x.id);
      const name = x.art === "firma" ? (f ? UNT.kurzName(f.name) : x.id) : x.art === "stamm" ? ((STAMM[x.id] || {}).name || x.id) : x.art === "liste" ? `${landName(x.id)} ohne Ort` : "Vergleich";
      return `<span class="chip-f${x.art === "firma" && vgl.includes(x.id) ? " vgl" : ""}" data-gkvorne="${i}"><span>${esc(name)}</span><button type="button" data-gkzu="${i}" aria-label="schließen">×</button></span>`; }).join("")
      + (S.offen.length > 1 ? `<button type="button" class="gk-knopf" data-gkneben>Nebeneinander</button>` : "")
      + (vgl.length ? `<button type="button" class="gk-knopf" data-gkvgl aria-pressed="${!!S.offen.find(x => x.art === "vergleich")}">Vergleich (${f0.format(vgl.length)})</button>` : "")
      + (S.offen.length ? `<button type="button" class="gk-knopf" data-gkallezu>Alle schließen</button>` : "");
  }
  function speichern() {
    try { localStorage.setItem("globus-fenster", JSON.stringify(S.offen.map(x => ({ art: x.art, id: x.id, l: x.el.offsetLeft, t: x.el.offsetTop, w: x.el.offsetWidth, h: x.el.offsetHeight })))); } catch { /* kein Speicher */ }
  }
  function wiederherstellen() {
    let alt = [];
    try { alt = JSON.parse(localStorage.getItem("globus-fenster") || "[]"); } catch { alt = []; }
    alt.forEach(a => { if (a.art === "firma" && UNT.nachId(a.id)) firmaOeffnen(a.id); else if (a.art === "stamm" && STAMM[a.id]) stammOeffnen(a.id); else if (a.art === "liste" && NUR_LAND[a.id]) listeOeffnen(a.id); else if (a.art === "vergleich") vergleichOeffnen();
      const x = S.offen[S.offen.length - 1]; if (x && innerWidth >= 820 && a.w) Object.assign(x.el.style, { left: a.l + "px", top: a.t + "px", width: a.w + "px", height: a.h + "px" }); });
  }

  /* ----- Ebenen-Auswahl ----- */
  function ebenenListe() {
    const el = document.getElementById("gk-ebenen"); if (!el) return;
    const hier = EBENEN.filter(e => !e.formen || e.formen.includes(S.form)), gruppen = [...new Set(hier.map(e => e.gruppe))];
    el.innerHTML = `<h3>EBENEN · ${esc(FORMEN.find(x => x[0] === S.form)[1].toUpperCase())}</h3>${gruppen.map(g => `<div style="margin-top:4px"><div class="pct" style="font-size:11px">${esc(g)}</div>${hier.filter(e => e.gruppe === g).map(e => `<label class="${e.geplant ? "aus" : ""}"><input type="checkbox" data-gkebene="${esc(e.id)}" ${e.an ? "checked" : ""} ${e.geplant ? "disabled" : ""}> ${esc(e.name)}</label>`).join("")}</div>`).join("")}
      <h3 style="margin-top:8px">GRUNDKARTE</h3><div class="gk-chips"><button type="button" data-gkgrund="osm" aria-pressed="${S.grund === "osm"}">OpenStreetMap</button><button type="button" data-gkgrund="einfach" aria-pressed="${S.grund === "einfach"}">Einfach</button></div>
      <div class="gk-legende"><span><i style="width:8px;height:8px"></i>börsennotiert</span><span><i style="width:8px;height:8px;background:#2f86dd"></i>nicht notiert</span><span><i style="width:5px;height:5px"></i>nur Stammdaten</span><span><i style="width:12px;height:12px;background:transparent;border:1.4px solid #8b95a3"></i>ohne Ort (nur Land)</span><span><i style="width:14px;height:14px;background:rgba(255,168,40,.28);border:1px solid #ffa828"></i>Gruppe</span></div>`;
  }

  /* ----- Bedienung ----- */
  function klick(e) {
    const t = e.target, g = a => { const x = t.closest && t.closest("[" + a + "]"); return x ? x.getAttribute(a) : null; };
    const fx = () => S.offen.find(o => o.el.contains(t));
    let v;
    if ((v = g("data-weltform")) != null) { e.preventDefault(); location.hash = "#globus-" + v; return true; }
    if ((v = g("data-gkform")) != null) { formWaehlen(v); return true; }
    if ((v = g("data-gkraum")) != null) { raumWaehlen(v); return true; }
    if ((v = g("data-gkbund")) != null) { S.buendnis = S.buendnis === v ? null : v; politikAnwenden(); seiteZeichnen(); return true; }
    if ((v = g("data-gkregion")) != null) { S.region = S.region === v ? null : v; politikAnwenden(); seiteZeichnen(); return true; }
    if ((v = g("data-gkbm")) != null) { S.bm = v; boerseAnwenden(); legendeKarte(); seiteZeichnen(); return true; }
    if ((v = g("data-gku1")) != null) { S.u1 = v; unAnwenden(); legendeKarte(); seiteZeichnen(); return true; }
    if ((v = g("data-gkufk")) != null) { if (v) UF[v] = !UF[v]; else Object.assign(UF, { branche: "", index: "", notiert: false, kennzahlen: false }); punkteAktualisieren(); seiteZeichnen(); return true; }
    if ((v = g("data-gkk1")) != null) { S.k1 = v; kontAnwenden(); seiteZeichnen(); return true; }
    if (MLD.klick(t)) { routenAktualisieren(); seiteZeichnen(); return true; }
    if ((v = g("data-gkmeldung")) != null) { const k = knotenVon(v); if (k && map) { meldungPopup(v); if (!t.closest(".gk-newskarte")) map.easeTo({ center: [k.lon, k.lat], duration: 900 }); } return true; }
    if ((v = g("data-gkgut")) != null) { gutWaehlen(v); return true; }
    if ((v = g("data-gkverkehr")) != null) { knotenOeffnen(v[0], +v.slice(1), true); return true; }
    if ((v = g("data-gkweg")) != null) { landUmschalten(v); return true; }
    if ((v = g("data-gkland")) != null && e.shiftKey && v) { landUmschalten(v); return true; }
    if ((v = g("data-gkliste")) != null) { listeOeffnen(v); return true; }
    if ((v = g("data-gkstamm")) != null) { e.preventDefault(); if (listePop) listePop.remove(); stammOeffnen(v, { fliegen: !t.closest("#gk-fenster") }); return true; }
    if ((v = g("data-gkfirma")) != null) { e.preventDefault(); if (listePop) listePop.remove(); oeffnen(v, { fliegen: !t.closest("#gk-fenster") }); return true; }
    if ((v = g("data-gkland")) != null) { landWaehlen(v || null, { fliegen: !!v }); if (!v && map) map.flyTo({ zoom: 1.7, duration: 1000 }); return true; }
    if ((v = g("data-gkzeigen")) != null) { const ps = PUNKTE.filter(p => p.properties.land === v); if (ps.length && map) { const b = ps.reduce((a, p) => { const [x, y] = p.geometry.coordinates; return [Math.min(a[0], x), Math.min(a[1], y), Math.max(a[2], x), Math.max(a[3], y)]; }, [180, 90, -180, -90]); map.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 60, maxZoom: 9, duration: 1200 }); } return true; }
    if ((v = g("data-gkhandel")) != null) { S.handel = v; const eb = EBENEN.find(x => x.id === "handel"); if (eb && !eb.an) { eb.an = true; ebenenListe(); } richtungAnwenden(); seiteZeichnen(); return true; }
    if (g("data-gkhandelzeigen") != null) { const eb = EBENEN.find(x => x.id === "handel"); if (eb && !eb.an) { eb.an = true; if (map) sichtbar(eb); ebenenListe(); } const c = mitte(S.land); if (map && c) map.flyTo({ center: c, zoom: 3.6, duration: 1400 }); return true; }
    if ((v = g("data-gkkont")) != null) { const v2 = g("data-gkkont2"); if (t.closest("[data-gkkont2]")) kontWaehlen(v, v2); else kontWaehlen(v, null); return true; }
    if (g("data-gkip") != null) { ipKontinent(); return true; }
    if ((v = g("data-gkpolansicht")) != null) { politikAnsicht(v); return true; }
    if ((v = g("data-gkstufe")) != null) {
      const [, z] = STUFEN_TEXT[+v - 1], c = +v === 1 ? ((KONT.find(x => x[0] === S.kont) || [])[3]) : mitte(S.land);
      if (map) { if (+v === 1 && S.land) landWaehlen(null); map.flyTo({ center: c || map.getCenter(), zoom: z, duration: 1400 }); } return true; }
    if (g("data-gkhandelnetz") != null) { S.handelMitNetz = !S.handelMitNetz; ueberlagerung(); return true; }
    if (g("data-gknurland") != null) { S.nurLand = !S.nurLand; punkteAktualisieren(); seiteZeichnen(); return true; }
    if ((v = g("data-gkebene")) != null) { const eb = EBENEN.find(x => x.id === v); if (eb) { eb.an = t.checked; if (map) { sichtbar(eb); legendeKarte(); } } return true; }
    if ((v = g("data-gkgrund")) != null) { try { localStorage.setItem("globus-grund", v); } catch { /* */ } osmFehler = 0; grundkarte(v); ebenenListe(); return true; }
    if (g("data-gkebenen") != null) { const el = document.getElementById("gk-ebenen"); el.hidden = !el.hidden; t.closest("[data-gkebenen]").setAttribute("aria-pressed", String(!el.hidden)); return true; }
    if ((v = g("data-gkvorne")) != null && !t.closest("button")) { const x = S.offen[+v]; if (x) { nachVorne(x); x.el.classList.remove("max"); } return true; }
    if ((v = g("data-gkzu")) != null) { const x = S.offen[+v]; if (x) schliessen(x); return true; }
    if (g("data-gkneben") != null) { nebeneinander(); return true; }
    if (g("data-gkvgl") != null) { vergleichOeffnen(); return true; }
    if (g("data-gkallezu") != null) { [...S.offen].forEach(schliessen); return true; }
    if ((v = g("data-gstammretry")) != null) { if (STAMM[v]) { delete STAMM[v]._fehler; S.offen.filter(x => x.art === "stamm" && x.id === v).forEach(fensterInhalt); } return true; }
    if ((v = g("data-gfvgl")) != null) { const a = UNT.auswahl(); UNT.setAuswahl(a.includes(v) ? a.filter(x => x !== v) : [...a, v]); alleZeichnen(); return true; }
    if (g("data-gfzu") != null) { const x = fx(); if (x) schliessen(x); return true; }
    if (g("data-gfmax") != null) { const x = fx(); if (x) x.el.classList.toggle("max"); return true; }
    if (g("data-gfterminal") != null) { const x = fx(); if (x) location.hash = "firma-" + x.id; return true; }
    if (g("data-gfkarte") != null) { const x = fx(); if (x) { const p = PUNKTE.find(q => q.properties.id === x.id); if (p && map) { if (S.land && S.nurLand && p.properties.land !== S.land) landWaehlen(p.properties.land); map.flyTo({ center: p.geometry.coordinates, zoom: 10, duration: 1200 }); } else hinweis("Für dieses Unternehmen ist kein Sitz bekannt"); } return true; }
    return false;
  }
  function suchen(q) {
    q = (q || "").trim(); if (!q) return;
    const ql = q.toLowerCase();
    const land = LAENDER.features.find(f => f.properties.name.toLowerCase() === ql || f.properties.name_en.toLowerCase() === ql || f.properties.iso.toLowerCase() === ql)
      || LAENDER.features.find(f => f.properties.name.toLowerCase().startsWith(ql));
    const firma = UNT.finden(q);
    if (firma && (!land || firma.name.toLowerCase() === ql)) { firmaOeffnen(firma.id, { fliegen: true }); return; }
    if (land) { landWaehlen(land.properties.iso, { fliegen: true }); return; }
    if (firma) { firmaOeffnen(firma.id, { fliegen: true }); return; }
    // übrige Tabelle: Name, ISIN oder Kürzel, erst genau, dann Anfang, dann enthalten
    const alle = Object.values(STAMM), qu = q.toUpperCase();
    const st = alle.find(r => r.name.toLowerCase() === ql || r.isin === qu || r.ticker.toUpperCase() === qu) || alle.find(r => r.name.toLowerCase().startsWith(ql)) || (ql.length > 2 && alle.find(r => r.name.toLowerCase().includes(ql)));
    if (st) oeffnen(st.id || st.k, { fliegen: true }); else hinweis(`Nichts gefunden für „${q}“`);
  }

  /* ----- Einbindung in die Navigation des Terminals ----- */
  function globusZeigen(an) {
    imGlobus = an;
    document.getElementById("globus").hidden = !an;
    document.getElementById("gk-fenster").hidden = !an;
    document.querySelector(".wrap").style.display = an ? "none" : "";
    { const u = document.getElementById("gk-zurueck"); u.hidden = false; u.href = an ? "#start" : "#globus"; u.textContent = an ? "▤ Terminal" : "◉ Weltkugel"; }
    if (an) {
      document.getElementById("view").innerHTML = "";        // klassische Ansicht leeren (Diagramm-Hover nicht doppelt binden)
      if (typeof globalLand !== "undefined" && globalLand !== "alle") { const sel = document.getElementById("global-land"); if (sel) sel.value = "alle"; landAnwenden("alle"); }
      karteStarten(); if (map) map.resize();
    }
    dock();
  }
  function renderGlobus() {
    const h = location.hash.slice(1);
    if (!h || h === "globus") { globusZeigen(true); alleZeichnen(); return; }
    if (h.startsWith("globus-")) { history.replaceState(null, "", "#globus"); globusZeigen(true); formWaehlen(h.slice(7)); alleZeichnen(); return; }
    if (h.startsWith("firma-") && imGlobus) { history.replaceState(null, "", "#globus"); firmaOeffnen(h.slice(6)); return; }
    if (h === "u-vergleich" && imGlobus) { history.replaceState(null, "", "#globus"); vergleichOeffnen(); alleZeichnen(); return; }
    globusZeigen(false);
    klassisch();
  }

  function init() {
    if (!UNT.da()) { document.getElementById("gk-seite").innerHTML = "<p>Keine Unternehmensdaten im Terminal.</p>"; }
    punkteBauen();
    klassisch = render;
    try { const f = localStorage.getItem("globus-form"); if (f && FORMEN.some(x => x[0] === f)) S.form = f; } catch { /* kein Speicher */ }
    try { const a = localStorage.getItem("globus-politik"); if (a === "wahlen" || a === "regierungen") S.polAnsicht = a; } catch { /* kein Speicher */ }
    render = renderGlobus;                            // Hash-Navigation des Terminals läuft ab jetzt über die Weltkugel
    if (!UNT.auswahl().length) UNT.setAuswahl([]);
    document.getElementById("gk-liste").innerHTML = LAENDER.features.map(f => `<option value="${esc(f.properties.name)}">`).join("") + UNT.unternehmenAlle().map(f => `<option value="${esc(f.name)}">`).join("");
    document.getElementById("gk-suchfeld").addEventListener("keydown", e => { if (e.key === "Enter") { suchen(e.target.value); e.target.value = ""; } });
    document.getElementById("gk-suchfeld").addEventListener("change", e => { if (e.target.value && LAENDER.features.some(f => f.properties.name === e.target.value)) { suchen(e.target.value); e.target.value = ""; } });
    document.addEventListener("click", e => { if (imGlobus || e.target.closest("#gk-zurueck") || e.target.closest("[data-weltform]")) { if (klick(e)) e.stopImmediatePropagation(); } }, true);
    addEventListener("resize", () => { if (map) map.resize(); });
    document.addEventListener("change", e => { const t = e.target; if (!t.matches || !t.matches("[data-gkuf]")) return; UF[t.dataset.gkuf] = t.value; punkteAktualisieren(); seiteZeichnen(); });
    document.addEventListener("input", e => { const t = e.target; if (!t.matches || !t.matches("[data-gklistefilter]")) return;
      const x = S.offen.find(o => o.el.contains(t)); if (!x) return; x.filter = t.value; x.el.querySelector(".gk-listeninhalt").innerHTML = listeEintraege(x); });
    document.addEventListener("keydown", e => { if (e.key === "Escape" && imGlobus && S.aktiv && S.offen.includes(S.aktiv)) schliessen(S.aktiv); });
    if (!location.hash || location.hash === "#start") history.replaceState(null, "", "#globus");
    renderGlobus();
    ebenenListe();
    // Start in Stufe 1 mit dem Kontinent des Besuchers (Zeitzone/Sprache), Europa als Rückfall
    S.kont = besucherKontinent(); stufeChips();
    if (map) { const c = KONT.find(x => x[0] === S.kont)[3]; map.jumpTo({ center: c, zoom: 1.7 }); map.once("style.load", kontAnwenden); }
    seiteZeichnen();
    if (imGlobus) wiederherstellen();
  }
  return { init, ebene, landWaehlen, firmaOeffnen, oeffnen, bogen, hinweis, sichtbar: id => { const eb = EBENEN.find(x => x.id === id); if (eb && map) sichtbar(eb); },
    karte: () => map, ebenen: () => EBENEN, imGlobus: () => imGlobus,
    // für die Wahlansicht (src/wahlen.js)
    zustand: () => S, seiteZeichnen, legendeKarte, politikAnsicht, halbkreis, balkenFarbig, landName, bbox, ZG,
    geo: () => ({ LAENDER, DE_GEO, GL_GEO, KO_GEO, WK, KREISE: roh("kreise-de-geo") }) };
})();
// Daten des Terminals können (in der komprimierten Vorschau) erst nach dem Entpacken bereitstehen
(function warte(n) { if (UNT.da() || n > 400) GLOBUS.init(); else setTimeout(() => warte(n + 1), 50); })(0);
