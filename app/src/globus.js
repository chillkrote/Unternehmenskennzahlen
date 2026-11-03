/* ---------- Weltkugel: alternative Oberfläche des Terminals ----------
   Karte: MapLibre GL (BSD-3, im Build eingebettet) in Globus-Projektion. Grundkarte aus OpenStreetMap-Daten über OpenFreeMap
   (Vektorkacheln, kostenlos, ohne Schlüssel); ohne Netz oder bei gesperrten Kacheln eine einfache Karte aus den eingebetteten
   Natural-Earth-Ländergrenzen. Schriften für Beschriftungen sind eingebettet (Noto Sans, Bereich 0–255).

   Ebenen: jede Darstellung auf der Karte ist eine Ebene in EBENEN (Länder, Unternehmen, später Handelsströme, Lieferketten).
   Eine Ebene bringt ihre Quellen und Schichten selbst mit und wird nach jedem Wechsel der Grundkarte neu angelegt.
   Neue Ebenen: GLOBUS.ebene({ id, name, gruppe, an, quellen(map), schichten(map, vor), klick?(e, map) }).

   Läuft nach dem Hauptskript des Terminals im selben Dokument und nutzt dessen Teile weiter:
   UNT.viewProfil (Profil im Fenster), UNT.viewVgl (Vergleich), VWL (Länderdaten), BOE (Indizes), render/gehe (Hash-Navigation). */
"use strict";
const GLOBUS = (() => {
  const roh = id => { try { return JSON.parse(document.getElementById(id).textContent); } catch { return null; } };
  const LAENDER = roh("geo-laender") || { type: "FeatureCollection", features: [] };
  const SITZE = roh("geo-sitze") || { spalten: [], zeilen: [] };
  const GLYPHEN = roh("geo-glyphen") || {};
  const HANDEL = (d => d && d.laender ? d : null)(roh("geo-handel"));
  const TABELLE = (d => d && d.zeilen ? d : null)(roh("geo-tabelle"));    // gesamte Unternehmenstabelle mit Punkt (tabelle_geo.csv)
  const DN = (() => { try { return new Intl.DisplayNames(["de"], { type: "region" }); } catch { return null; } })();
  const landName = iso => { const f = NACH_ISO[iso]; if (f) return f.properties.name; try { return (DN && DN.of(iso)) || iso; } catch { return iso; } };
  const NACH_ISO = {};
  LAENDER.features.forEach(f => { NACH_ISO[f.properties.iso] = f; });
  // ein Beschriftungspunkt je Land (sonst beschriftet MapLibre jedes Kachelstück der Fläche)
  const LAENDER_PUNKTE = { type: "FeatureCollection", features: LAENDER.features.map(f => ({ type: "Feature", geometry: { type: "Point", coordinates: [f.properties.lx, f.properties.ly] },
    properties: { iso: f.properties.iso, name: f.properties.name, einwohner: f.properties.einwohner || 0 } })) };
  const namensFarbe = () => ["case", ["==", ["get", "iso"], S.land || ""], "#ffa828", "#8b95a3"];
  const VWL_GEO = iso => ({ GB: "UK", GR: "EL" }[iso] || iso);       // Eurostat-/OECD-Kürzel im VWL-Datensatz
  const OSM_URL = "https://tiles.openfreemap.org/planet";
  const S = { land: null, handel: "beide", nurLand: true, grund: null, offen: [], aktiv: null, z: 10, hover: null, ebenenOffen: false };
  let map = null, klassisch = null, imGlobus = false, hinweisTimer = 0, osmFehler = 0, osmGeladen = false;

  /* ----- Unternehmen mit Sitz-Koordinaten -----
     Zwei Quellen: Unternehmen des Terminals (Sitz aus sitz_geo.csv, Fenster mit Profil und Kennzahlen) und die übrigen Zeilen der
     Unternehmenstabelle (tabelle_geo.csv, Fenster mit Stammdaten). Ist nur das Land bekannt (genau = 0), gibt es keinen eigenen
     Punkt (er würde einen Ort vortäuschen), sondern je Land einen Ring in der Landesmitte mit der Anzahl; er öffnet die Liste. */
  let PUNKTE = [];       // GeoJSON-Features je Unternehmen
  const STAMM = {};      // Schlüssel der Tabelle -> Zeile als Objekt (nur Unternehmen ohne Profil im Terminal)
  const NUR_LAND = {};   // ISO -> [{ id, name, branche, art }] Unternehmen, deren Sitz nur auf Landesebene bekannt ist
  function tabZeile(z) {
    const o = {}; TABELLE.spalten.forEach((s, j) => { o[s] = TABELLE.listen[s] ? TABELLE.listen[s][z[j]] : z[j]; }); return o;
  }
  function punkteBauen() {
    const sp = SITZE.spalten, i = n => sp.indexOf(n);
    PUNKTE = [];
    const terminal = new Set(), punkt = (lon, lat, p) => PUNKTE.push({ type: "Feature", geometry: { type: "Point", coordinates: [lon, lat] }, properties: p });
    const firmaProps = f => ({ id: f.id, name: UNT.kurzName(f.name).replace(/ Aktiengesellschaft$/, ""), branche: UNT.brName(f.branche), notiert: f.notiert ? 1 : 0, art: "t" });
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
      if (!f) STAMM[r.k] = r;
      const p = f ? { ...firmaProps(f), land: r.land || f.land_code || "" } : { id: r.k, name: r.name, branche: r.branche, land: r.land, notiert: r.notiert === "ja" ? 1 : 0, art: "s" };
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
  function ebene(def) { EBENEN.push({ an: true, gruppe: "Karte", ...def }); if (map && map.isStyleLoaded()) ebeneAnlegen(EBENEN[EBENEN.length - 1]); ebenenListe(); }
  const vorBeschriftung = () => { const l = (map.getStyle().layers || []).find(x => x.type === "symbol" && x.id.startsWith("osm-")); return l ? l.id : undefined; };
  function ebeneAnlegen(e) {
    if (!e.quellen) return;
    try { e.quellen(map); e.schichten(map, vorBeschriftung()); sichtbar(e); }
    catch (err) { console.warn("Ebene", e.id, err); }
  }
  function sichtbar(e) { (map.getStyle().layers || []).filter(l => l.metadata && l.metadata.ebene === e.id).forEach(l => map.setLayoutProperty(l.id, "visibility", e.an ? "visible" : "none")); if (e.id === "handel") richtungAnwenden(); }
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
        paint: { "text-color": namensFarbe(), "text-halo-color": "#07090c", "text-halo-width": 1.2 } });
    } });

  /* Unternehmen nach Sitz: Cluster, die beim Hineinzoomen in kleinere Gruppen und Einzelpunkte zerfallen */
  ebene({ id: "unternehmen", name: "Unternehmen (Sitz)", gruppe: "Unternehmen", an: true,
    quellen: m => {
      m.addSource("unternehmen", { type: "geojson", data: punkteDaten(), cluster: true, clusterRadius: 46, clusterMaxZoom: 11,
        clusterProperties: { notiert: ["+", ["get", "notiert"]], kennzahlen: ["+", ["case", ["==", ["get", "art"], "t"], 1, 0]] } });
      m.addSource("unt-land", { type: "geojson", data: landRingDaten() });
    },
    schichten: (m) => {
      const ab = 2.2;   // erst beim Hineinzoomen sichtbar
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

  /* Handelsströme (data/handel.json, handel_abruf.py): beim gewählten Land Bögen zu den wichtigsten Partnern, Exporte gelb vom Land
     weg, Importe blau zum Land hin; Breite nach Wert. Format je Land: { jahr, export_welt, import_welt, export: [[ISO2, USD], …], import: […] }.
     Vorbereitet: Lieferketten zwischen Unternehmens-IDs, z. B. { lieferketten: [{ von: "U000123", nach: "U000456", art, gut, quelle }] },
     als Bögen zwischen den Sitzen. */
  ebene({ id: "handel", name: "Handelsströme (gewähltes Land)", gruppe: "Handel", an: !!HANDEL, geplant: !HANDEL,
    quellen: m => { m.addSource("handel-x", { type: "geojson", data: handelDaten("export"), lineMetrics: true }); m.addSource("handel-m", { type: "geojson", data: handelDaten("import"), lineMetrics: true }); },
    schichten: m => {
      const breite = ["interpolate", ["linear"], ["get", "anteil"], 0, 1, .25, 7];
      // Verlauf von blass (Herkunft) nach kräftig (Ziel) zeigt die Richtung
      schicht("handel", { id: "handel-x", type: "line", source: "handel-x", layout: { "line-cap": "round", visibility: "visible" },
        paint: { "line-width": breite, "line-gradient": ["interpolate", ["linear"], ["line-progress"], 0, "rgba(255,168,40,0.08)", 1, "rgba(255,168,40,0.95)"] } });
      schicht("handel", { id: "handel-m", type: "line", source: "handel-m", layout: { "line-cap": "round" },
        paint: { "line-width": breite, "line-gradient": ["interpolate", ["linear"], ["line-progress"], 0, "rgba(77,163,255,0.08)", 1, "rgba(77,163,255,0.95)"] } });
      richtungAnwenden();
    } });
  ebene({ id: "lieferketten", name: "Lieferketten", gruppe: "In Vorbereitung", an: false, geplant: true });

  /* Großkreisbogen zwischen zwei Punkten; Längengrade fortlaufend, damit Bögen über die Datumsgrenze nicht quer über die Karte springen */
  function bogen(a, b, n = 64) {
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
    return pkt;
  }
  const mitte = iso => NACH_ISO[iso] ? [NACH_ISO[iso].properties.lx, NACH_ISO[iso].properties.ly] : null;
  function handelDaten(richtung) {
    const leer = { type: "FeatureCollection", features: [] };
    const h = HANDEL && S.land && HANDEL.laender[S.land];
    if (!h || !h[richtung] || !mitte(S.land)) return leer;
    const welt = h[richtung + "_welt"] || 1, heim = mitte(S.land);
    return { type: "FeatureCollection", features: h[richtung].slice(0, 12).filter(([p]) => mitte(p)).map(([p, wert]) => ({ type: "Feature",
      properties: { partner: p, name: landName(p), wert, anteil: wert / welt, richtung },
      geometry: { type: "LineString", coordinates: richtung === "export" ? bogen(heim, mitte(p)) : bogen(mitte(p), heim) } })) };
  }
  function handelAktualisieren() {
    if (!map) return;
    if (map.getSource("handel-x")) map.getSource("handel-x").setData(handelDaten("export"));
    if (map.getSource("handel-m")) map.getSource("handel-m").setData(handelDaten("import"));
  }
  function richtungAnwenden() {
    if (!map || !map.getLayer("handel-x")) return;
    const an = (EBENEN.find(e => e.id === "handel") || {}).an;
    map.setLayoutProperty("handel-x", "visibility", an && S.handel !== "import" ? "visible" : "none");
    map.setLayoutProperty("handel-m", "visibility", an && S.handel !== "export" ? "visible" : "none");
  }

  function punkteDaten() {
    const f = S.land && S.nurLand ? PUNKTE.filter(p => p.properties.land === S.land) : PUNKTE;
    return { type: "FeatureCollection", features: f };
  }
  function punkteAktualisieren() {
    if (!map || !map.getSource("unternehmen")) return;
    map.getSource("unternehmen").setData(punkteDaten());
    if (map.getSource("unt-land")) map.getSource("unt-land").setData(landRingDaten());
    if (map.getLayer("unt-offen")) map.setFilter("unt-offen", ["all", ["!", ["has", "point_count"]], ["in", ["get", "id"], ["literal", S.offen.filter(x => x.art === "firma" || x.art === "stamm").map(x => x.id)]]]);
  }

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
    map.setStyle(art === "osm" ? stilOSM() : stilEinfach(), { diff: false });
    map.once("style.load", stilGeladen);
  }
  function stilGeladen() {
    if (S.grund === "einfach") { /* Grundfläche: Länder sind die Landmasse */ }
    EBENEN.forEach(ebeneAnlegen);
    if (S.land && NACH_ISO[S.land]) map.setFeatureState({ source: "laender", id: NACH_ISO[S.land].id }, { gewaehlt: true });
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
      dragRotate: false, pitchWithRotate: false, renderWorldCopies: false, locale: { "NavigationControl.ZoomIn": "Hineinzoomen", "NavigationControl.ZoomOut": "Herauszoomen" } });
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
    map.on("mousemove", e => {
      const u = quer(e.point, ["unt-cluster", "unt-punkt", "unt-land-ring"]), hb = u.length ? [] : quer(e.point, ["handel-x", "handel-m"]), l = u.length ? [] : quer(e.point, ["laender-flaeche"]);
      if (hb.length) { handelTip(e, hb[0]); } else if (handelPop) { handelPop.remove(); handelPop = null; }
      map.getCanvas().style.cursor = u.length || l.length ? "pointer" : "";
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
      const c = quer(e.point, ["unt-cluster"]);
      if (c.length) return clusterKlick(c[0]);
      const r = quer(e.point, ["unt-land-ring"]);
      if (r.length) return listeOeffnen(r[0].properties.iso);
      const p = quer(e.point, ["unt-punkt"]);
      if (p.length > 1) return listePopup(e.lngLat, p.map(x => x.properties));
      if (p.length) return p[0].properties.art === "s" ? stammOeffnen(p[0].properties.id) : firmaOeffnen(p[0].properties.id);
      for (const eb of EBENEN) if (eb.an && eb.klick && eb.klick(e, map) === true) return;
      const l = quer(e.point, ["laender-flaeche"]);
      if (l.length) landWaehlen(l[0].properties.iso, { fliegen: true });
      else landWaehlen(null);
    });
    map.on("zoomend", zoomHinweis);
    return map;
  }

  let tipPop = null;
  let handelPop = null;
  function handelTip(e, f) {
    const p = f.properties, h = HANDEL.laender[S.land];
    const t = `<b>${p.richtung === "export" ? `${esc(landName(S.land))} → ${esc(p.name)}` : `${esc(p.name)} → ${esc(landName(S.land))}`}</b><br>${p.richtung === "export" ? "Exporte" : "Importe"} ${f1.format(p.wert / 1e9)} Mrd. USD<br><span class="pct">${f1.format(p.anteil * 100)} % aller ${p.richtung === "export" ? "Exporte" : "Importe"} · ${esc(h.jahr)}</span>`;
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
      .setHTML(`<b>${f0.format(props.length)} Unternehmen</b> <span class="pct">${esc(orte.slice(0, 3).join(", "))}${orte.length > 3 ? " …" : ""}</span><ul>${props.map(p => `<li><button type="button" ${p.art === "s" ? "data-gkstamm" : "data-gkfirma"}="${esc(p.id)}">${esc(p.name)} <span class="pct">${esc(p.branche)}</span></button></li>`).join("")}</ul>`)
      .addTo(map);
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
  function landWaehlen(iso, opt = {}) {
    if (map && map.getSource("laender")) {
      if (S.land && NACH_ISO[S.land]) map.setFeatureState({ source: "laender", id: NACH_ISO[S.land].id }, { gewaehlt: false });
      if (iso && NACH_ISO[iso]) map.setFeatureState({ source: "laender", id: NACH_ISO[iso].id }, { gewaehlt: true });
    }
    S.land = iso || null;
    if (map && map.getLayer("laender-name")) map.setPaintProperty("laender-name", "text-color", namensFarbe());
    try { localStorage.setItem("globus-land", S.land || ""); } catch { /* kein Speicher */ }
    punkteAktualisieren();
    handelAktualisieren();
    seiteZeichnen();
    if (iso && opt.fliegen && map && NACH_ISO[iso]) {
      const b = bbox(NACH_ISO[iso]), w = b[2] - b[0], h = b[3] - b[1];
      if (w > 0 && w < 170) map.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: { top: 70, bottom: 60, left: 40, right: 40 }, maxZoom: 6.5, duration: 1400 });
      else { const p = NACH_ISO[iso].properties; map.flyTo({ center: [p.lx, p.ly], zoom: 2.4, duration: 1400 }); }
    }
    if (iso && opt.fliegen) setTimeout(zoomHinweis, 1500);
  }
  function zoomHinweis() {
    if (!map) return;
    const n = S.land ? PUNKTE.filter(p => p.properties.land === S.land).length : PUNKTE.length;
    if (map.getZoom() < 2.2 && n) hinweis(`Hineinzoomen, um ${f0.format(n)} Unternehmen nach Sitz zu sehen`);
  }
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
  function vwlDaten() { if (!VD && typeof VWL !== "undefined" && VWL.alleDaten) { VD = VWL.alleDaten(); SER = VD ? Object.fromEntries(VD.serien.map(s => [s.serie_id, s])) : {}; } return VD; }
  function reihe(ids, geo) {
    const d = vwlDaten(); if (!d) return null;
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
      <p class="gk-quelle" style="margin-top:6px">Mrd. USD, Warenhandel laut Meldung von ${esc(landName(iso))} (Exporte FOB, Importe meist CIF); die zehn größten Partner, auf dem Globus bis zu zwölf je Richtung (gelb Exporte, blau Importe). Quelle: <a href="${esc(HANDEL.url)}" target="_blank" rel="noopener">UN Comtrade</a>, Abruf ${esc(HANDEL.abruf)}.</p></div>`;
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
  function seiteZeichnen() {
    const el = document.getElementById("gk-seite"); if (!el) return;
    const iso = S.land;
    if (!iso) {
      const n = {}; PUNKTE.forEach(p => { n[p.properties.land] = (n[p.properties.land] || 0) + 1; });
      const top = Object.entries(n).sort((a, b) => b[1] - a[1]).slice(0, 12);
      const d = vwlDaten();
      el.innerHTML = `<div><h2>Weltkugel</h2><p class="unter" style="margin-top:4px">Land anklicken für Kerndaten · hineinzoomen für Unternehmen nach Sitz · Unternehmen anklicken für das Profil</p></div>
        <div class="gk-block"><h3>Länder mit den meisten Unternehmen</h3><ul class="gk-liste">${top.map(([iso2, k]) => `<li><button type="button" data-gkland="${esc(iso2)}">${esc(landName(iso2))}</button><span class="r">${f0.format(k)}</span></li>`).join("")}</ul></div>
        <div class="gk-block"><h3>Daten</h3><p class="gk-quelle">${f0.format(PUNKTE.length)} Unternehmen auf der Karte: ${f0.format(PUNKTE.filter(p => p.properties.art === "t").length)} mit Kennzahlen im Terminal, die übrigen mit Stammdaten aus der Unternehmenstabelle. Weitere ${f0.format(nurLandAnzahl())} Unternehmen, deren Sitz nur auf Landesebene bekannt ist, stehen in den grauen Ringen „ohne Ort“ in der Landesmitte. Volkswirtschaftliche Kerndaten für ${d ? f0.format(d.laender.filter(l => l.oecd === "1").length) : 0} OECD-Länder (Eurostat, OECD); für die übrigen Länder Grundangaben aus Natural Earth.</p></div>`;
      return;
    }
    const f = NACH_ISO[iso], p = f ? f.properties : {};
    const k = kerndaten(iso);
    const basis = p.einwohner ? `<div class="gk-block"><h3>Grundangaben</h3><table class="gk-tab"><tbody>
      <tr><td>Einwohner</td><td>${f1.format(p.einwohner / 1e6)} Mio. <span class="pct">(${esc(p.einwohner_jahr)})</span></td></tr>
      <tr><td>BIP nominal</td><td>${f0.format(p.bip_mio_usd / 1000)} Mrd. USD <span class="pct">(${esc(p.bip_jahr)})</span></td></tr>
      <tr><td>Einkommensgruppe</td><td style="font-family:var(--sans)">${esc(p.einkommen || "–")}</td></tr></tbody></table>
      <p class="gk-quelle" style="margin-top:6px">Natural Earth (Weltbank-Schätzungen des genannten Jahres), nur zur Einordnung.</p></div>` : "";
    el.innerHTML = `<div><div class="gk-chips" style="margin-bottom:8px"><button type="button" data-gkland="">← Alle Länder</button></div>
        <h2>${esc(p.name || landName(iso))}</h2><p class="unter" style="margin-top:4px">${esc(iso)}${p.region ? " · " + esc(p.region) : ""}</p></div>
      ${k.length ? `<div class="gk-block"><h3>Kerndaten</h3><div class="gk-kz">${k.join("")}</div>
        <p class="gk-quelle" style="margin-top:6px">Jüngster veröffentlichter Wert; Linie = Verlauf (5 Jahre bzw. 10 Jahre bei Jahreswerten), gestrichelt = OECD-Projektion. Eurostat, wo vorhanden, sonst OECD. Stand des Abrufs ${esc((vwlDaten() || {}).stand || "")}.</p></div>`
        : `<div class="gk-block"><h3>Kerndaten</h3><p class="gk-leer">Für ${esc(p.name || iso)} liegen im Terminal noch keine volkswirtschaftlichen Reihen vor (bisher OECD-Länder und Europa).</p></div>`}
      ${prognosen(iso)}
      ${handelBlock(iso)}
      ${firmenBlock(iso)}
      ${indizes(iso)}
      ${basis}`;
    el.scrollTop = 0;
  }

  /* ----- Fenster (Pop-ups) für Unternehmen und Vergleich ----- */
  const fensterKey = x => x.art + ":" + (x.id || "");
  function fensterEl() { return document.getElementById("gk-fenster"); }
  function firmaOeffnen(id, opt = {}) {
    const f = UNT.nachId(id); if (!f) return;
    id = f.id;
    const da = S.offen.find(x => x.art === "firma" && x.id === id);
    if (da) { nachVorne(da); return; }
    neuesFenster({ art: "firma", id });
    punkteAktualisieren();
    if (opt.fliegen && map) { const p = PUNKTE.find(x => x.properties.id === id); if (p) map.flyTo({ center: p.geometry.coordinates, zoom: Math.max(map.getZoom(), 8), duration: 1200 }); }
  }
  function stammOeffnen(k, opt = {}) {
    if (!STAMM[k]) return;
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
      `<li><button type="button" ${p.art === "s" ? "data-gkstamm" : "data-gkfirma"}="${esc(p.id)}">${esc(p.name)}</button><span class="r">${esc(p.art === "t" ? "Kennzahlen" : p.branche)}</span></li>`).join("")}</ul>`;
  }
  function listeAnsicht(x) {
    const n = (NUR_LAND[x.id] || []).length;
    return `<div class="gk-stamm"><p class="gk-leer" style="margin:0 0 8px">Für diese ${f0.format(n)} Unternehmen ist der Sitz nur auf Landesebene bekannt, sie haben daher keinen eigenen Punkt auf der Karte. Herkunft: Unternehmenstabelle; weder die Tabelle noch GLEIF oder Wikidata nennen einen Ort.</p>
      <input type="search" class="gk-filter" data-gklistefilter placeholder="Name, ISIN oder Kürzel filtern" value="${esc(x.filter || "")}" aria-label="Liste filtern">
      <div class="gk-listeninhalt">${listeEintraege(x)}</div></div>`;
  }
  const QUELLE_GEO = { tabelle: "Spalte Sitz der Unternehmenstabelle", gleif: "Anschrift laut GLEIF (LEI-Register)", wikidata: "Hauptsitz laut Wikidata" };
  function stammAnsicht(k) {
    const r = STAMM[k]; if (!r) return `<p class="n">Unbekannt.</p>`;
    const link = u => /^https?:\/\//.test(u) ? `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(u.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, ""))}</a>` : esc(u);
    const zeile = (t, v, roh) => v ? `<tr><td>${t}</td><td style="font-family:var(--sans);text-align:left">${roh ? v : esc(v)}</td></tr>` : "";
    const sitz = r.genau ? `${esc(r.ort || r.sitz)} <span class="pct">(${esc(QUELLE_GEO[r.q] || r.q || "")})</span>` : `<span class="pct">nicht bekannt, daher kein eigener Punkt auf der Karte (im Ring „ohne Ort“ in der Mitte von ${esc(landName(r.land))})</span>`;
    return `<div class="gk-stamm"><p class="gk-leer" style="margin:0 0 10px">Für dieses Unternehmen liegen im Terminal noch keine Kennzahlen vor. Angezeigt werden die Stammdaten aus der Unternehmenstabelle.</p>
      <table class="gk-tab"><tbody>
      ${zeile("Name", r.name)}${zeile("Rechtsform", r.rf)}${zeile("Land", landName(r.land))}${zeile("Sitz", sitz, true)}
      ${zeile("Branche", r.branche)}${zeile("Bank", r.bank)}${zeile("Börsennotiert", r.notiert)}${zeile("Börse", r.boerse)}${zeile("Kürzel", r.ticker)}${zeile("ISIN", r.isin)}
      ${zeile("LEI", r.lei ? `<a href="https://search.gleif.org/#/record/${esc(r.lei)}" target="_blank" rel="noopener">${esc(r.lei)}</a>` : "", true)}${zeile("Handelsregister", r.hr)}
      ${zeile("Index", r.index)}${zeile("Website", r.web ? link(r.web) : "", true)}${zeile("Beschreibung", r.text)}
      ${zeile("Quelle", r.quelle ? link(r.quelle) : "", true)}${zeile("Unternehmens-ID", r.id)}</tbody></table></div>`;
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
    const gruppen = [...new Set(EBENEN.map(e => e.gruppe))];
    el.innerHTML = `<h3>EBENEN</h3>${gruppen.map(g => `<div style="margin-top:4px"><div class="pct" style="font-size:11px">${esc(g)}</div>${EBENEN.filter(e => e.gruppe === g).map(e => `<label class="${e.geplant ? "aus" : ""}"><input type="checkbox" data-gkebene="${esc(e.id)}" ${e.an ? "checked" : ""} ${e.geplant ? "disabled" : ""}> ${esc(e.name)}</label>`).join("")}</div>`).join("")}
      <h3 style="margin-top:8px">GRUNDKARTE</h3><div class="gk-chips"><button type="button" data-gkgrund="osm" aria-pressed="${S.grund === "osm"}">OpenStreetMap</button><button type="button" data-gkgrund="einfach" aria-pressed="${S.grund === "einfach"}">Einfach</button></div>
      <div class="gk-legende"><span><i style="width:8px;height:8px"></i>börsennotiert</span><span><i style="width:8px;height:8px;background:#2f86dd"></i>nicht notiert</span><span><i style="width:5px;height:5px"></i>nur Stammdaten</span><span><i style="width:12px;height:12px;background:transparent;border:1.4px solid #8b95a3"></i>ohne Ort (nur Land)</span><span><i style="width:14px;height:14px;background:rgba(255,168,40,.28);border:1px solid #ffa828"></i>Gruppe</span></div>`;
  }

  /* ----- Bedienung ----- */
  function klick(e) {
    const t = e.target, g = a => { const x = t.closest && t.closest("[" + a + "]"); return x ? x.getAttribute(a) : null; };
    const fx = () => S.offen.find(o => o.el.contains(t));
    let v;
    if ((v = g("data-gkliste")) != null) { listeOeffnen(v); return true; }
    if ((v = g("data-gkstamm")) != null) { e.preventDefault(); if (listePop) listePop.remove(); stammOeffnen(v, { fliegen: !t.closest("#gk-fenster") }); return true; }
    if ((v = g("data-gkfirma")) != null) { e.preventDefault(); if (listePop) listePop.remove(); firmaOeffnen(v, { fliegen: !t.closest("#gk-fenster") }); return true; }
    if ((v = g("data-gkland")) != null) { landWaehlen(v || null, { fliegen: !!v }); if (!v && map) map.flyTo({ zoom: 1.7, duration: 1000 }); return true; }
    if ((v = g("data-gkzeigen")) != null) { const ps = PUNKTE.filter(p => p.properties.land === v); if (ps.length && map) { const b = ps.reduce((a, p) => { const [x, y] = p.geometry.coordinates; return [Math.min(a[0], x), Math.min(a[1], y), Math.max(a[2], x), Math.max(a[3], y)]; }, [180, 90, -180, -90]); map.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 60, maxZoom: 9, duration: 1200 }); } return true; }
    if ((v = g("data-gkhandel")) != null) { S.handel = v; const eb = EBENEN.find(x => x.id === "handel"); if (eb && !eb.an) { eb.an = true; ebenenListe(); } richtungAnwenden(); seiteZeichnen(); return true; }
    if (g("data-gkhandelzeigen") != null) { const eb = EBENEN.find(x => x.id === "handel"); if (eb && !eb.an) { eb.an = true; if (map) sichtbar(eb); ebenenListe(); } const c = mitte(S.land); if (map && c) map.flyTo({ center: c, zoom: 1.5, duration: 1400 }); return true; }
    if (g("data-gknurland") != null) { S.nurLand = !S.nurLand; punkteAktualisieren(); seiteZeichnen(); return true; }
    if ((v = g("data-gkebene")) != null) { const eb = EBENEN.find(x => x.id === v); if (eb) { eb.an = t.checked; if (map) sichtbar(eb); } return true; }
    if ((v = g("data-gkgrund")) != null) { try { localStorage.setItem("globus-grund", v); } catch { /* */ } osmFehler = 0; grundkarte(v); ebenenListe(); return true; }
    if (g("data-gkebenen") != null) { const el = document.getElementById("gk-ebenen"); el.hidden = !el.hidden; t.closest("[data-gkebenen]").setAttribute("aria-pressed", String(!el.hidden)); return true; }
    if ((v = g("data-gkvorne")) != null && !t.closest("button")) { const x = S.offen[+v]; if (x) { nachVorne(x); x.el.classList.remove("max"); } return true; }
    if ((v = g("data-gkzu")) != null) { const x = S.offen[+v]; if (x) schliessen(x); return true; }
    if (g("data-gkneben") != null) { nebeneinander(); return true; }
    if (g("data-gkvgl") != null) { vergleichOeffnen(); return true; }
    if (g("data-gkallezu") != null) { [...S.offen].forEach(schliessen); return true; }
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
    if (st) stammOeffnen(st.k, { fliegen: true }); else hinweis(`Nichts gefunden für „${q}“`);
  }

  /* ----- Einbindung in die Navigation des Terminals ----- */
  function globusZeigen(an) {
    imGlobus = an;
    document.getElementById("globus").hidden = !an;
    document.getElementById("gk-fenster").hidden = !an;
    document.querySelector(".wrap").style.display = an ? "none" : "";
    document.getElementById("gk-zurueck").hidden = an;
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
    if (h.startsWith("firma-") && imGlobus) { history.replaceState(null, "", "#globus"); firmaOeffnen(h.slice(6)); return; }
    if (h === "u-vergleich" && imGlobus) { history.replaceState(null, "", "#globus"); vergleichOeffnen(); alleZeichnen(); return; }
    globusZeigen(false);
    klassisch();
  }

  function init() {
    if (!UNT.da()) { document.getElementById("gk-seite").innerHTML = "<p>Keine Unternehmensdaten im Terminal.</p>"; }
    punkteBauen();
    klassisch = render;
    render = renderGlobus;                            // Hash-Navigation des Terminals läuft ab jetzt über die Weltkugel
    if (!UNT.auswahl().length) UNT.setAuswahl([]);
    document.getElementById("gk-liste").innerHTML = LAENDER.features.map(f => `<option value="${esc(f.properties.name)}">`).join("") + UNT.unternehmenAlle().map(f => `<option value="${esc(f.name)}">`).join("");
    document.getElementById("gk-suchfeld").addEventListener("keydown", e => { if (e.key === "Enter") { suchen(e.target.value); e.target.value = ""; } });
    document.getElementById("gk-suchfeld").addEventListener("change", e => { if (e.target.value && LAENDER.features.some(f => f.properties.name === e.target.value)) { suchen(e.target.value); e.target.value = ""; } });
    document.addEventListener("click", e => { if (imGlobus || e.target.closest("#gk-zurueck")) { if (klick(e)) e.stopImmediatePropagation(); } }, true);
    addEventListener("resize", () => { if (map) map.resize(); });
    document.addEventListener("input", e => { const t = e.target; if (!t.matches || !t.matches("[data-gklistefilter]")) return;
      const x = S.offen.find(o => o.el.contains(t)); if (!x) return; x.filter = t.value; x.el.querySelector(".gk-listeninhalt").innerHTML = listeEintraege(x); });
    document.addEventListener("keydown", e => { if (e.key === "Escape" && imGlobus && S.aktiv && S.offen.includes(S.aktiv)) schliessen(S.aktiv); });
    let land = null; try { land = localStorage.getItem("globus-land"); } catch { land = null; }
    if (!location.hash || location.hash === "#start") history.replaceState(null, "", "#globus");
    renderGlobus();
    ebenenListe();
    if (land && NACH_ISO[land]) { if (map) map.once("style.load", () => landWaehlen(land, { fliegen: true })); else landWaehlen(land); }
    else seiteZeichnen();
    if (imGlobus) wiederherstellen();
  }
  return { init, ebene, landWaehlen, firmaOeffnen, karte: () => map, ebenen: () => EBENEN };
})();
// Daten des Terminals können (in der komprimierten Vorschau) erst nach dem Entpacken bereitstehen
(function warte(n) { if (UNT.da() || n > 400) GLOBUS.init(); else setTimeout(() => warte(n + 1), 50); })(0);
