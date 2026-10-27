// Startet die App kurz, wartet auf das Terminal und speichert einen Screenshot (Entwicklung):
// xvfb-run -a npx electron --no-sandbox scripts/smoketest.js --out=/pfad/smoke.png
const { app, BrowserWindow } = require("electron");
const fs = require("fs");
require("../main.js");
const out = (process.argv.find(a => a.startsWith("--out=")) || "--out=smoke.png").slice(6);
app.whenReady().then(() => setTimeout(async () => {
  const w = BrowserWindow.getAllWindows()[0];
  const info = await w.webContents.executeJavaScript(`({t:document.title,n:document.body.innerText.length})`);
  console.log(JSON.stringify(info));
  const bild = await Promise.race([w.webContents.capturePage(), new Promise(r => setTimeout(() => r(null), 8000))]);
  if (bild) fs.writeFileSync(out, bild.toPNG());
  app.exit(info.n > 300 ? 0 : 1);
}, 10000));
