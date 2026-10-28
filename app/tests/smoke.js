// Smoke-Test: öffnet das gebaute Terminal und schaltet durch Ansichten; Exit-Code 1 bei JavaScript-Fehlern.
// Aufruf: NODE_PATH=$(npm root -g) node app/tests/smoke.js app/dist/bankterminal.html
const { chromium } = require("playwright");
const path = require("path");
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  const fehler = [];
  p.on("pageerror", e => fehler.push(e.message));
  await p.goto("file://" + path.resolve(process.argv[2] || "app/dist/bankterminal.html"));
  await p.waitForTimeout(1500);
  const ansichten = await p.evaluate(() => [...new Set([...document.querySelectorAll('a[href^="#"], [data-view], [data-tab]')].map(a => (a.getAttribute("href") || "").slice(1)).filter(h => h && !h.startsWith("firma-")))].slice(0, 40));
  for (const h of ansichten.concat(["u-ueb", "u-verzeichnis", "v-reihe"])) {
    await p.evaluate(h => { location.hash = h; }, h);
    await p.waitForTimeout(300);
  }
  console.log(`${ansichten.length + 3} Ansichten, ${fehler.length} JavaScript-Fehler`, fehler.slice(0, 5));
  await b.close();
  process.exit(fehler.length ? 1 : 0);
})();
