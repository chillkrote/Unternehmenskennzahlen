/* ---------- Datenzugriff über die Plattform-API (server/, /api/v1) ----------
   Gemeinsamer Adapter für alle Module: Basisadresse, Zeitlimit, begrenzte Wiederholung bei vorübergehenden Fehlern,
   Zwischenspeicher, einheitliche Fehler. Ohne konfigurierte API (GitHub Pages, Artifact, lokale Datei) ist API.aktiv false und
   die Module arbeiten wie bisher mit den eingebetteten Daten.
   Basisadresse (erste Fundstelle gewinnt): ?api=<url> in der Adresse, <meta name="sphaerae-api" content="/api/v1">, window.SPHAERAE_API. */
"use strict";
const API = (() => {
  const basis = (() => {
    try { const u = new URLSearchParams(location.search).get("api"); if (u) return u.replace(/\/+$/, ""); } catch (e) { /* ohne location */ }
    const m = document.querySelector('meta[name="sphaerae-api"]');
    if (m && m.content) return m.content.replace(/\/+$/, "");
    return (typeof window !== "undefined" && window.SPHAERAE_API) ? String(window.SPHAERAE_API).replace(/\/+$/, "") : null;
  })();
  const ZEITLIMIT_MS = 10000, VERSUCHE = 3, CACHE_MS = 5 * 60 * 1000, CACHE_MAX = 300;
  const cache = new Map();                    // Adresse -> { t, wert }
  class ApiFehler extends Error {
    constructor(status, code, meldung, details) { super(meldung); this.status = status; this.code = code; this.details = details; }
    get voruebergehend() { return this.status === 0 || this.status === 429 || this.status >= 500; }
  }
  const warte = ms => new Promise(r => setTimeout(r, ms));
  function adresse(pfad, params) {
    const q = new URLSearchParams();
    Object.entries(params || {}).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") q.set(k, Array.isArray(v) ? v.join(",") : String(v)); });
    const s = q.toString();
    return basis + pfad + (s ? "?" + s : "");
  }
  async function einmal(url, signalAussen) {
    const ctrl = new AbortController(), uhr = setTimeout(() => ctrl.abort(), ZEITLIMIT_MS);
    const ab = () => ctrl.abort(); if (signalAussen) signalAussen.addEventListener("abort", ab);
    try {
      const r = await fetch(url, { signal: ctrl.signal, headers: { Accept: "application/json" } });
      let j = null; try { j = await r.json(); } catch (e) { j = null; }
      if (!r.ok) {
        const e = (j && j.error) || {};
        const f = new ApiFehler(r.status, e.code || "http_" + r.status, e.message || `Antwort ${r.status}`, e.details);
        f.warten = +(r.headers.get("Retry-After") || 0);
        throw f;
      }
      return j;
    } catch (e) {
      if (e instanceof ApiFehler) throw e;
      if (signalAussen && signalAussen.aborted) throw new ApiFehler(0, "abgebrochen", "Abgebrochen");
      throw new ApiFehler(0, ctrl.signal.aborted ? "zeitlimit" : "netz", ctrl.signal.aborted ? "Zeitüberschreitung beim Laden" : "Server nicht erreichbar");
    } finally { clearTimeout(uhr); if (signalAussen) signalAussen.removeEventListener("abort", ab); }
  }
  /* GET mit Zwischenspeicher. Wiederholt nur vorübergehende Fehler (Netz, Zeitlimit, 429, 5xx), höchstens VERSUCHE-mal mit wachsender Pause. */
  async function get(pfad, params, opt) {
    if (!basis) throw new ApiFehler(0, "keine_api", "Keine API konfiguriert");
    const o = opt || {}, url = adresse(pfad, params), c = cache.get(url);
    if (c && Date.now() - c.t < CACHE_MS && !o.frisch) return c.wert;
    let letzter;
    for (let i = 0; i < VERSUCHE; i++) {
      try {
        const wert = await einmal(url, o.signal);
        cache.set(url, { t: Date.now(), wert });
        if (cache.size > CACHE_MAX) cache.delete(cache.keys().next().value);
        return wert;
      } catch (e) {
        letzter = e;
        if (!e.voruebergehend || e.code === "abgebrochen" || i === VERSUCHE - 1) break;
        await warte(Math.min(5000, e.warten ? e.warten * 1000 : 400 * 2 ** i));
      }
    }
    throw letzter;
  }
  return {
    get aktiv() { return !!basis; }, basis, ApiFehler, get,
    unternehmen: (filter, opt) => get("/companies", filter, opt),
    unternehmenEins: (id, opt) => get("/companies/" + encodeURIComponent(id), null, opt),
    profil: (id, opt) => get("/companies/" + encodeURIComponent(id) + "/profile", null, opt),
    kennzahlen: (id, filter, opt) => get("/companies/" + encodeURIComponent(id) + "/metrics", filter, opt),
    suche: (q, opt) => get("/search", { q, limit: 8 }, opt),
    laender: () => get("/countries"), branchen: () => get("/sectors"),
  };
})();

/* ---------- Datenblöcke als Dateien (API-Fassung) ----------
   build.py --api ersetzt große Blöcke (z. B. parlamente-daten) durch {"_nach": "data/<datei>.json"}. BLOCK.jetzt(id) liefert die Daten,
   null wenn der Block fehlt, oder undefined, solange die Datei lädt (der erste Aufruf startet das Laden). Danach meldet das Ereignis
   „sphaerae:block“ (detail.id) den Ansichten, dass sie neu zeichnen können. In der Pages-Fassung sind die Blöcke eingebettet.
   Aufgeschobene Blöcke (AUFGESCHOBEN, Audit 2026-11, 4.7): Daten, die nur eine Ansicht braucht (Politik, Wahlen, Güterhandel), laden
   nicht mehr beim Start, sondern erst, wenn die Ansicht sie mit BLOCK.freigeben(id) anfordert. Bis dahin meldet status() „lädt“
   und jetzt() undefined, wie bei einem laufenden Abruf; eingebettete Blöcke (Pages-Fassung) sind davon nicht berührt. */
const BLOCK = (() => {
  const daten = {}, laeuft = {}, fehler = {};
  function roh(id) { try { return JSON.parse(document.getElementById(id).textContent); } catch (e) { return null; } }
  function laden(id, url) {
    if (laeuft[id] || fehler[id]) return;
    laeuft[id] = fetch(url).then(r => r.ok ? r.json() : Promise.reject(Error("HTTP " + r.status)))
      .then(d => { daten[id] = d; }).catch(e => { fehler[id] = e.message || String(e); })
      .then(() => { delete laeuft[id]; dispatchEvent(new CustomEvent("sphaerae:block", { detail: { id } })); });
  }
  const AUFGESCHOBEN = ["gueter-daten", "parlamente-daten", "gliedstaaten-geo", "wahlen-daten"];
  // erst beim Zugriff geprüft: manche Blöcke stehen im Dokument hinter diesem Skript (wahlen-daten der Weltkugel)
  const frei = new Set();
  const spaeter = { has: id => AUFGESCHOBEN.includes(id) && !frei.has(id) && !(id in daten) && !laeuft[id] && !fehler[id] && (d => !!d && typeof d._nach === "string")(roh(id)),
                    delete: id => { const war = spaeter.has(id); frei.add(id); return war; } };
  function freigeben(...ids) { ids.forEach(id => { if (spaeter.delete(id)) jetzt(id); }); }
  function jetzt(id) {
    if (id in daten) return daten[id];
    if (spaeter.has(id)) return undefined;
    const d = roh(id);
    if (d && typeof d._nach === "string") { laden(id, d._nach); return undefined; }
    return (daten[id] = d);
  }
  const status = id => fehler[id] ? { fehler: fehler[id] } : laeuft[id] ? { laedt: true } : spaeter.has(id) ? { laedt: true, aufgeschoben: true } : {};
  function erneut(id) { delete fehler[id]; spaeter.delete(id); jetzt(id); }
  // als Promise: Daten, sobald da (eingebettet sofort); null, wenn der Block fehlt oder nicht geladen werden konnte
  function warte(id) {
    freigeben(id);
    const d = jetzt(id);
    if (d !== undefined) return Promise.resolve(d);
    return laeuft[id].then(() => id in daten ? daten[id] : null);
  }
  return { jetzt, status, erneut, warte, freigeben, aufgeschoben: () => AUFGESCHOBEN.filter(id => spaeter.has(id)) };
})();
