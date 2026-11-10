// Teilbare Adresse der Korrelation (P4): #korr?a=…&b=… stellt das Paar her, Änderungen schreiben die Adresse fort.
// Aufruf: NODE_PATH=… node app/tests/korrelation-url-smoke.js app/dist/bankterminal.html   (oder http-Adresse der API-Fassung)
const { chromium } = require("playwright");
const path = require("path");
(async () => {
  const b = await chromium.launch(), p = await b.newPage(), fehler = [], js = [];
  p.on("pageerror", e => js.push(e.message));
  const pruefe = (ok, was) => { console.log(ok ? "ok    " : "FEHLER", was); if (!ok) fehler.push(was); };
  const ziel = process.argv[2] || "app/dist/bankterminal.html", basis = /^https?:/.test(ziel) ? ziel : "file://" + path.resolve(ziel);
  await p.goto(basis + "#korr?a=vwl~konsum_privat~DE&b=vwl~bip_yoy~DE&lag=1&von=2010&m=spearman");
  await p.waitForSelector("#klag", { timeout: 30000 });
  const zustand = () => p.evaluate(() => ({ lag: document.getElementById("klag").value, von: (document.getElementById("kvon") || {}).value,
    meth: (document.getElementById("kmeth") || {}).value, slotA: [...document.querySelectorAll('[data-slot="A"] select, [data-slot="A"] input')].map(e => e.value).join("|"),
    hash: location.hash }));
  let z = await zustand();
  pruefe(z.lag === "1" && z.von === "2010" && z.meth === "spearman", `Parameter übernommen (lag ${z.lag}, von ${z.von}, ${z.meth})`);
  pruefe(/konsum_privat/.test(z.slotA) && /DE/.test(z.slotA), "Reihe A aus der Adresse: " + z.slotA);
  await p.selectOption("#klag", "2");
  await p.waitForFunction(() => /[?&]lag=2/.test(location.hash));
  z = await zustand();
  pruefe(/^#korr\?/.test(z.hash) && /a=vwl~konsum_privat~DE/.test(decodeURIComponent(z.hash)), "Adresse fortgeschrieben: " + decodeURIComponent(z.hash));
  // neu laden mit der fortgeschriebenen Adresse: gleicher Zustand
  const neu = await b.newPage(); neu.on("pageerror", e => js.push(e.message));
  await neu.goto(basis + z.hash); await neu.waitForSelector("#klag", { timeout: 30000 });
  pruefe(await neu.evaluate(() => document.getElementById("klag").value) === "2", "geteilte Adresse stellt die Auswertung wieder her");
  await neu.evaluate(() => { location.hash = "u-ueb"; }); await neu.waitForTimeout(300);
  pruefe(!neu.url().includes("korr?"), "andere Ansicht behält keine Korrelationsparameter");
  pruefe(!js.length, "keine JavaScript-Fehler" + (js.length ? ": " + js.join(" | ") : ""));
  await b.close();
  if (fehler.length) process.exit(1);
  console.log("Korrelation-URL OK");
})().catch(e => { console.error(e); process.exit(1); });
