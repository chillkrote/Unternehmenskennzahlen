// Smoke-Test der API-Fassung (Build mit --api): Verzeichnis und Registerprofil laden über /api/v1, Fehler- und Ladezustände.
// Braucht den laufenden Server (docker compose, server/README.md). Aufruf:
//   node app/tests/api-smoke.js http://localhost:8080/bankterminal.html
const { chromium } = require("playwright");
(async () => {
  const url = process.argv[2] || "http://localhost:8080/bankterminal.html";
  const b = await chromium.launch();
  const p = await b.newPage();
  const fehler = [], api = [];
  p.on("pageerror", e => fehler.push(e.message));
  p.on("request", r => { if (r.url().includes("/api/v1/")) api.push(r.url()); });
  const pruefe = (ok, text) => { if (!ok) fehler.push(text); console.log((ok ? "ok    " : "FEHLER") + " " + text); };
  const html = await (await fetch(url)).text();      // HTML direkt lesen (der Browser hält 40 MB nicht im Inspektor-Cache)
  await p.goto(url);
  pruefe(/<script id="register" type="application\/json">null<\/script>/.test(html), "Register nicht in der Seite eingebettet");
  pruefe(/<meta name="sphaerae-api" content="[^"]+">/.test(html), "API-Adresse in der Seite gesetzt");
  await p.waitForTimeout(1500);
  // Länderauswahl auf „Alle Länder“ (auf der Weltkugel ist die Leiste verdeckt, deshalb direkt setzen)
  await p.evaluate(() => { location.hash = "u-verzeichnis"; });
  await p.waitForTimeout(300);
  await p.evaluate(() => { const s = document.getElementById("global-land"); s.value = "alle"; s.dispatchEvent(new Event("change")); });
  await p.waitForFunction(() => /Treffer/.test((document.getElementById("uzahl") || {}).textContent || ""), null, { timeout: 15000 });
  const gesamt = +(await p.textContent("#uzahl")).split(" ")[0].replace(/\./g, "");
  pruefe(gesamt > 30000, `Verzeichnis über die API: ${gesamt} Unternehmen`);
  pruefe((await p.$$("#uverz tr")).length === 100, "100 Zeilen je Seite");
  // Serverseitige Suche (entprellt)
  await p.fill("#usuche", "bawag");
  await p.waitForFunction(() => /^\d+ Treffer/.test(document.getElementById("uzahl").textContent) && document.querySelectorAll("#uverz tr").length < 10, null, { timeout: 10000 });
  pruefe((await p.textContent("#uverz")).includes("BAWAG"), "Suche „bawag“ findet BAWAG");
  pruefe(api.some(u => u.includes("q=bawag")), "Suche läuft über /api/v1/companies?q=");
  // Filter Land und Seitenwechsel
  await p.fill("#usuche", "");
  await p.waitForTimeout(600);
  await p.waitForFunction(() => document.querySelectorAll("#uland option").length > 5, null, { timeout: 10000 });
  await p.selectOption("#uland", "DE");
  await p.waitForFunction(() => /Seite 1 von/.test(document.getElementById("uzahl").textContent), null, { timeout: 10000 });
  const vorher = await p.textContent("#uverz tr:first-child");
  await p.click("#unx");
  await p.waitForFunction(() => /Seite 2 von/.test(document.getElementById("uzahl").textContent), null, { timeout: 10000 });
  pruefe(vorher !== await p.textContent("#uverz tr:first-child"), "Seite 2 zeigt andere Zeilen");
  pruefe(api.some(u => u.includes("country=DE") && u.includes("page=2")), "Land und Seite gehen an den Server");
  // Fehlerzustand: API nicht erreichbar -> Hinweis mit „Erneut versuchen“, danach wieder Daten
  await p.route("**/api/v1/companies?**", r => r.abort());
  await p.selectOption("#unot", "1");
  await p.waitForSelector("#uretry", { timeout: 20000 });
  pruefe(true, "Fehlermeldung mit „Erneut versuchen“ bei Ausfall");
  await p.unroute("**/api/v1/companies?**");
  await p.click("#uretry");
  await p.waitForFunction(() => /Treffer/.test(document.getElementById("uzahl").textContent), null, { timeout: 15000 });
  pruefe(!(await p.$("#uretry")), "nach erneutem Versuch wieder Daten");
  // Registerprofil eines Unternehmens ohne Kennzahlen (Deep Link #firma-<ID>)
  // (U021975 Mahanagar Telephone Nigam: im Register, ohne eingebettete Kennzahlen, mit Alias „MTNL“)
  await p.evaluate(() => { location.hash = "firma-U021975"; });
  await p.waitForFunction(() => document.body.textContent.includes("INE153A01019") && !document.getElementById("uregapi"), null, { timeout: 15000 });
  pruefe((await p.textContent("body")).includes("Weitere Namen: MTNL"), "Registerprofil über die API mit Aliasen");
  await p.evaluate(() => { location.hash = "firma-U999999"; });
  await p.waitForFunction(() => document.body.textContent.includes("Unternehmen nicht gefunden"), null, { timeout: 15000 });
  pruefe(true, "unbekannte ID: „nicht gefunden“");
  // Unternehmen mit Kennzahlen öffnet weiter das bisherige Profil (eingebettete Kennzahlen)
  await p.evaluate(() => { location.hash = "firma-U000148"; });
  await p.waitForFunction(() => document.getElementById("view").textContent.includes("Deutsche Bank AG"), null, { timeout: 15000 });
  pruefe(!(await p.textContent("#view")).includes("noch keine Kennzahlen"), "Profil mit Kennzahlen unverändert (Deutsche Bank)");
  console.log(`${api.length} API-Anfragen, ${fehler.length} Fehler`, fehler.slice(0, 5));
  await b.close();
  process.exit(fehler.length ? 1 : 0);
})();
