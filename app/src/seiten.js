// Fußleiste unten mittig: Impressum, Kontakt, About Sphaerae. Die Texte kommen aus app/seiten/*.md (eingebettet als #seiten-daten),
// nichts davon steht fest im Code. Kleiner Markdown-Leser: Überschriften, Absätze, Listen, fett, kursiv, Links, Platzhalter [[…]].
(() => {
  const el = document.getElementById("seiten-daten");
  let seiten = [];
  try { seiten = JSON.parse(el ? el.textContent : "[]") || []; } catch (e) { seiten = []; }
  if (!seiten.length) return;

  const esc = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const inline = s => {
    let t = esc(s);
    t = t.replace(/\[\[(.+?)\]\]/g, '<mark class="sf-platzhalter">[$1]</mark>');
    t = t.replace(/\[([^\]]+)\]\(((?:https?:\/\/|mailto:)[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    t = t.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/(^|[^*])\*([^*\s][^*]*?)\*(?!\*)/g, "$1<em>$2</em>");
    return t;
  };
  const render = md => {
    const zeilen = md.replace(/<!--[\s\S]*?-->/g, "").split(/\r?\n/);
    let html = "", absatz = [], liste = false;
    const absatzEnde = () => { if (absatz.length) html += "<p>" + absatz.map(inline).join("<br>") + "</p>"; absatz = []; };
    const listeEnde = () => { if (liste) html += "</ul>"; liste = false; };
    for (const z of zeilen) {
      let m;
      if (!z.trim()) { absatzEnde(); listeEnde(); }
      else if ((m = /^(#{1,3})\s+(.*)$/.exec(z))) { absatzEnde(); listeEnde(); html += `<h${m[1].length}>${inline(m[2])}</h${m[1].length}>`; }
      else if ((m = /^\s*[-*]\s+(.*)$/.exec(z))) { absatzEnde(); if (!liste) { html += "<ul>"; liste = true; } html += "<li>" + inline(m[1]) + "</li>"; }
      else { listeEnde(); absatz.push(z.trim()); }
    }
    absatzEnde(); listeEnde();
    return html;
  };

  const leiste = document.createElement("nav");
  leiste.id = "fussleiste";
  leiste.setAttribute("aria-label", "Impressum, Kontakt, About");
  const fenster = document.createElement("div");
  fenster.id = "sf-fenster"; fenster.hidden = true;
  fenster.innerHTML = '<div class="sf-kasten" role="dialog" aria-modal="true" aria-labelledby="sf-titel"><div class="sf-kopf"><b id="sf-titel"></b><button type="button" class="sf-zu" aria-label="Schließen">✕</button></div><div class="sf-text"></div></div>';
  const kasten = fenster.querySelector(".sf-kasten"), text = fenster.querySelector(".sf-text"), titel = fenster.querySelector("#sf-titel");
  let zuletzt = null;

  const zu = () => { fenster.hidden = true; if (zuletzt) zuletzt.focus(); };
  const auf = (s, knopf) => {
    zuletzt = knopf; titel.textContent = s.titel; text.innerHTML = render(s.text); text.scrollTop = 0;
    fenster.hidden = false; fenster.querySelector(".sf-zu").focus();
  };
  for (const s of seiten) {
    const b = document.createElement("button");
    b.type = "button"; b.textContent = s.titel; b.dataset.seite = s.id;
    b.addEventListener("click", () => auf(s, b));
    leiste.appendChild(b);
  }
  fenster.addEventListener("click", e => { if (e.target === fenster || e.target.closest(".sf-zu")) zu(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape" && !fenster.hidden) { e.stopPropagation(); zu(); } }, true);
  document.body.append(leiste, fenster);
})();
