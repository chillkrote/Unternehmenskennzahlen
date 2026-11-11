// Landtagswahlen aus amtlichen Dateien (app/landtagswahlen.py) auf der Weltkugel: Ergebniskarte mit Zweit- und Erststimmen,
// Veränderung zur Vorwahl, Sitze, Landkreise und Landtagswahlkreise mit Direktmandat. Die Sollwerte stehen im amtlichen Endergebnis.
// Aufruf: node app/tests/landtagswahl-smoke.js [app/dist/weltkugel.html | http://localhost:8080/weltkugel.html]
const { chromium } = require('playwright');
const path = require('node:path');
const fs = require('node:fs');
// je Wahl: Texte der Ergebniskarte und ein Punkt [Länge, Breite] in einem Wahlkreis mit dem dort erwarteten Text
const WAHLEN_SOLL = [
  { id: 'DE-ST-parl-2026', karte: [/Landtag Sachsen-Anhalt/, /Zweitstimmen/, /AfD/, /43,8/, /Landtagswahl 2021/, /77,8/, /endgültig/i, /Statistisches Landesamt Sachsen-Anhalt/],
    punkt: [11.97, 51.48], zoom: 9.5, kreis: [/Landtagswahlkreis/, /Halle/, /Direktmandat/] },
  { id: 'DE-BW-parl-2026', karte: [/Landtag Baden-Württemberg/, /Zweitstimmen/, /GRÜNE/, /30,2/, /Landtagswahl 2021/, /69,6/, /endgültig/i, /Statistisches Landesamt Baden-Württemberg/],
    punkt: [8.876, 47.814], zoom: 9.5, kreis: [/Landtagswahlkreis/, /Singen/, /Direktmandat/] },
  { id: 'DE-BE-parl-2026', karte: [/Abgeordnetenhaus/, /Zweitstimmen/, /Die Linke/, /25,7/, /Wiederholungswahl 2023/, /74,2/, /endgültig/i, /Landeswahlleitung Berlin/],
    punkt: [13.1666, 52.4937], zoom: 11, kreis: [/Wahlkreis/, /Spandau 5/, /Direktmandat/] },
  { id: 'DE-RP-parl-2026', karte: [/Landtag Rheinland-Pfalz/, /Landesstimmen/, /CDU/, /31,0/, /Landtagswahl 2021/, /68,4/, /endgültig/i, /Landeswahlleiter Rheinland-Pfalz/],
    punkt: [8.2505, 49.9994], zoom: 11, kreis: [/Landtagswahlkreis/, /Mainz \(Wahlkreise 27, 28 und 29\)/, /Ergebnis der ganzen Stadt/] },   // geteilte Stadt ohne offene Stadtteilgrenzen
  { id: 'DE-MV-parl-2026', karte: [/Landtag Mecklenburg-Vorpommern/, /Zweitstimmen/, /AfD/, /38,2/, /Landtagswahl 2021/, /78,0/, /endgültig/i, /Landeswahlleiter Mecklenburg-Vorpommern/],
    punkt: [12.135, 54.090], zoom: 10.5, kreis: [/Landtagswahlkreis/, /Rostock IV/, /Direktmandat/] },   // Rostock: Wahlkreise aus statistischen Bezirken
];
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.stack || e.message));
  const http = /^https?:/.test(process.argv[2] || '');
  const datei = path.resolve(http ? 'app/dist/weltkugel.html' : (process.argv[2] || 'app/dist/weltkugel.html')), wurzel = path.dirname(datei);
  const server = require('node:http').createServer((q, a) => {      // über HTTP: Wahlkreisgrenzen kommen per fetch aus wahlgeo/
    const f = path.join(wurzel, decodeURIComponent(q.url.split('?')[0]));
    if (!f.startsWith(wurzel)) { a.writeHead(403); a.end(); return; }
    fs.readFile(f, (e, d) => { if (e) { a.writeHead(404); a.end(); } else { a.writeHead(200, { 'content-type': f.endsWith('.json') ? 'application/json' : 'text/html; charset=utf-8' }); a.end(d); } });
  });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  await page.goto(http ? process.argv[2] : `http://127.0.0.1:${server.address().port}/${path.basename(datei)}`);
  await page.waitForSelector('#gk-seite h2');
  const ok = (b, t) => { if (!b) throw Error(t); };
  const seite = () => page.locator('#gk-seite').innerText();
  await page.click('[data-gkform="politik"]');
  await page.waitForFunction(() => typeof WAHLEN !== 'undefined' && !!WAHLEN.wahl('DE-BT-2025'), null, { timeout: 60000 });
  const mitKarte = await page.evaluate(() => !!GLOBUS.karte());
  for (const s of WAHLEN_SOLL) {
    const w = await page.evaluate(id => { const x = WAHLEN.wahl(id); return x && { e: x.einheiten.map(u => [u.id, u.geo, Object.keys(u.werte || {}).length || u.anzahl || 0]), sitze: x.g.sitze_n }; }, s.id);
    ok(w, `${s.id} fehlt im Wahlregister`);
    ok(w.e.some(u => u[0] === 'lwk' && u[2] > 0), `${s.id}: Einheit Landtagswahlkreise fehlt (${JSON.stringify(w.e)})`);
    await page.evaluate(id => WAHLEN.wahlWaehlen(id, false), s.id); await page.waitForTimeout(800);
    let t = await seite();
    for (const m of s.karte) ok(m.test(t), `${s.id}: ${m} fehlt in der Ergebniskarte:\n${t.slice(0, 900)}`);
    if (!mitKarte) continue;
    await page.evaluate(([c, z]) => GLOBUS.karte().jumpTo({ center: c, zoom: z }), [s.punkt, s.zoom]); await page.waitForTimeout(2500);
    const box = await page.locator('#gk-karte canvas').first().boundingBox();
    const q = await page.evaluate(x => { const r = GLOBUS.karte().project(x); return { x: r.x, y: r.y }; }, s.punkt);
    await page.mouse.click(box.x + q.x, box.y + q.y); await page.waitForTimeout(1500);
    t = await seite();
    for (const m of s.kreis) ok(m.test(t), `${s.id}: ${m} fehlt nach Klick in den Wahlkreis:\n${t.slice(0, 900)}`);
  }
  ok(!errors.length, 'JavaScript-Fehler:\n' + errors.join('\n'));
  console.log(`OK landtagswahl-smoke: ${WAHLEN_SOLL.map(s => s.id).join(', ')}${mitKarte ? ' (mit Karte)' : ' (ohne WebGL: Kartenteil übersprungen)'}`);
  await browser.close(); server.close();
})().catch(e => { console.error(e); process.exit(1); });
