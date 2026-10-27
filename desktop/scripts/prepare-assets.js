// Kopiert das zuletzt gebaute Terminal (app/dist/bankterminal.html) und die Schriften nach build/.
const fs = require("fs");
const path = require("path");

const hier = path.resolve(__dirname, "..");
const quelle = path.resolve(hier, "../app/dist/bankterminal.html");
const ziel = path.join(hier, "build");
fs.rmSync(ziel, { recursive: true, force: true });
fs.mkdirSync(path.join(ziel, "fonts"), { recursive: true });
fs.copyFileSync(quelle, path.join(ziel, "terminal.html"));

// Schriften aus den npm-Paketen (lateinischer Zeichensatz genügt für Deutsch)
const familien = [
  ["ibm-plex-mono", "IBM Plex Mono", [400, 500, 600]],
  ["ibm-plex-sans", "IBM Plex Sans", [400, 500, 600]],
  ["ibm-plex-sans-condensed", "IBM Plex Sans Condensed", [500, 600]],
];
let css = "";
for (const [paket, name, gewichte] of familien) {
  for (const w of gewichte) {
    const datei = `${paket}-latin-${w}-normal.woff2`;
    const von = path.join(hier, "node_modules/@fontsource", paket, "files", datei);
    fs.copyFileSync(von, path.join(ziel, "fonts", datei));
    css += `@font-face{font-family:"${name}";font-style:normal;font-weight:${w};font-display:swap;src:url("${datei}") format("woff2")}\n`;
  }
}
fs.writeFileSync(path.join(ziel, "fonts/fonts.css"), css);
console.log("Assets bereit:", fs.statSync(path.join(ziel, "terminal.html")).size, "Bytes Terminal");
