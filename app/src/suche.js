/* Universelle Suche (P3.3): Vorschlagsliste unter einem Eingabefeld über GET /search der API.
   Gruppen: eine kombinierte Auswahl („Automobil · Deutschland“, wenn die API Land und Branche erkennt), Unternehmen, Länder, Branchen.
   Tastatur: Pfeil hoch/runter wählt, Enter übernimmt, Escape schließt; ohne markierten Vorschlag behält Enter das bisherige Verhalten
   des Feldes (Befehle im Terminal, lokale Suche der Weltkugel). Nur in der API-Fassung aktiv (API.aktiv); sonst ändert sich nichts.
   Einbindung: SUCHE.anbinden(input, treffer => …); treffer = { type: "company"|"country"|"sector"|"filter", id, label, countries, sectors }. */
"use strict";
const SUCHE = (() => {
  const TITEL = { filter: "Auswahl", company: "Unternehmen", country: "Länder", sector: "Branchen" };
  const REIHE = ["filter", "company", "country", "sector"];
  const WARTEN_MS = 180, MIN_ZEICHEN = 2;
  const html = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  let stil = false;
  function stilEinfuegen() {
    if (stil) return; stil = true;
    const s = document.createElement("style");
    s.textContent = `.su-anker{position:relative}
.su-box{position:absolute;left:0;right:0;top:calc(100% + 4px);z-index:60;max-height:min(70vh,460px);overflow:auto;background:var(--panel);border:1px solid var(--line,#2a3038);border-radius:8px;box-shadow:0 10px 30px var(--schatten);padding:4px 0;font:13px/1.35 var(--sans,system-ui,sans-serif);text-transform:none;color:var(--ink,#e8ecf1)}
.su-box h4{margin:6px 12px 2px;font:600 10.5px var(--mono,monospace);letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3,#7d8794)}
.su-box [role=option]{display:flex;gap:10px;align-items:baseline;padding:6px 12px;cursor:pointer}
.su-box [role=option] b{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:60%}
.su-box [role=option] span{color:var(--ink-3,#7d8794);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.su-box [role=option][aria-selected=true],.su-box [role=option]:hover{background:rgba(255,168,40,.14)}
.su-box p{margin:6px 12px;color:var(--ink-3,#7d8794);font-size:12px}`;
    document.head.appendChild(s);
  }
  // Antwort von /search -> flache Liste in Anzeigereihenfolge (mit Gruppe)
  function liste(d) {
    const g = (d && d.groups) || {}, i = (d && d.interpreted) || {}, out = [];
    const land = (g.country || []).find(x => (i.countries || []).includes(x.id)), br = (g.sector || []).find(x => (i.sectors || []).includes(x.id));
    if (br && (i.countries || []).length) {
      out.push({ type: "filter", id: "", label: `${br.label} · ${land ? land.label : i.countries.join(", ")}`, detail: "alle Unternehmen im Verzeichnis",
                 countries: i.countries, sectors: i.sectors });
    }
    ["company", "country", "sector"].forEach(t => (g[t] || []).forEach(x => out.push({ ...x, type: t })));
    return out;
  }
  function anbinden(input, waehlen) {
    if (!input || typeof API === "undefined" || !API.aktiv) return false;
    stilEinfuegen();
    const anker = input.closest("label") || input.parentElement;
    anker.classList.add("su-anker");
    if (input.hasAttribute("list")) input.removeAttribute("list");      // die Vorschlagsliste ersetzt die lokale Datalist
    const box = document.createElement("div");
    box.className = "su-box"; box.hidden = true; box.id = (input.id || "suche") + "-vorschlaege"; box.setAttribute("role", "listbox");
    anker.appendChild(box);
    input.setAttribute("role", "combobox"); input.setAttribute("aria-controls", box.id); input.setAttribute("aria-autocomplete", "list"); input.setAttribute("aria-expanded", "false");
    let uhr = 0, ctrl = null, treffer = [], markiert = -1, nr = 0;
    const zu = () => { box.hidden = true; input.setAttribute("aria-expanded", "false"); markiert = -1; };
    function zeichnen(meldung) {
      if (meldung) { box.innerHTML = `<p>${html(meldung)}</p>`; }
      else {
        let h = "", letzte = "";
        treffer.forEach((t, k) => {
          if (t.type !== letzte) { h += `<h4>${TITEL[t.type] || t.type}</h4>`; letzte = t.type; }
          h += `<div role="option" id="${box.id}-${k}" data-su="${k}" aria-selected="${k === markiert}"><b>${html(t.label)}</b><span>${html(t.detail || "")}</span></div>`;
        });
        box.innerHTML = h;
      }
      box.hidden = false; input.setAttribute("aria-expanded", "true");
      input.setAttribute("aria-activedescendant", markiert >= 0 ? `${box.id}-${markiert}` : "");
    }
    async function fragen(q) {
      if (ctrl) ctrl.abort();
      ctrl = new AbortController(); const meins = ++nr;
      try {
        const j = await API.get("/search", { q, types: "company,country,sector", limit: 6 }, { signal: ctrl.signal });
        if (meins !== nr || input.value.trim() !== q) return;
        const l = liste(j.data);
        treffer = REIHE.flatMap(t => l.filter(x => x.type === t)); markiert = -1;
        if (document.activeElement === input) zeichnen(treffer.length ? "" : `Nichts gefunden für „${q}“`);
      } catch (e) {
        if (meins !== nr || (e && e.code === "abgebrochen")) return;
        if (document.activeElement === input) { treffer = []; zeichnen("Suche nicht erreichbar: " + (e.message || e)); }
      }
    }
    function nehmen(t) { zu(); input.value = ""; nr++; if (ctrl) ctrl.abort(); waehlen(t); }
    input.addEventListener("input", () => {
      clearTimeout(uhr); const q = input.value.trim();
      if (q.length < MIN_ZEICHEN) { nr++; zu(); return; }
      uhr = setTimeout(() => fragen(q), WARTEN_MS);
    });
    // Erfassungsphase am Anker: läuft vor den Enter-Handlern des Feldes selbst
    anker.addEventListener("keydown", e => {
      if (e.target !== input) return;
      if (e.key === "Escape" && !box.hidden) { zu(); e.stopPropagation(); return; }
      if (box.hidden || !treffer.length) { if (e.key === "Enter") { nr++; clearTimeout(uhr); zu(); } return; }
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const n = treffer.length;                                        // Reihe -1 (nichts), 0 … n-1, umlaufend
        markiert = (markiert + 1 + (e.key === "ArrowDown" ? 1 : -1) + n + 1) % (n + 1) - 1;
        zeichnen();
        const el = markiert >= 0 && document.getElementById(`${box.id}-${markiert}`); if (el) el.scrollIntoView({ block: "nearest" });
      } else if (e.key === "Enter") {
        if (markiert >= 0) { e.preventDefault(); e.stopImmediatePropagation(); e.stopPropagation(); nehmen(treffer[markiert]); }
        else { nr++; clearTimeout(uhr); zu(); }
      }
    }, true);
    box.addEventListener("mousedown", e => e.preventDefault());      // Fokus im Feld lassen
    box.addEventListener("click", e => { const o = e.target.closest("[data-su]"); if (o) nehmen(treffer[+o.dataset.su]); });
    input.addEventListener("blur", () => setTimeout(zu, 120));
    input.addEventListener("focus", () => { if (treffer.length && input.value.trim().length >= MIN_ZEICHEN) zeichnen(); });
    return true;
  }
  return { anbinden, liste };
})();
