// Weltkugel, Politik & Wahlen: eine Wahl je Karte, Ebenenleiter E0–E4, Satzleiste, Ergebniskarte.
// Aufruf: node app/tests/wahlen-smoke.js [app/dist/weltkugel.html] [Bildordner]
const { chromium } = require('playwright');
const path = require('node:path');
const BILD = process.argv[3] || require('node:os').tmpdir() + '/wahlen-smoke';
require('node:fs').mkdirSync(BILD, { recursive: true });
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.stack || e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  // über HTTP ausliefern: die Wahlkreisgrenzen werden per fetch aus wahlgeo/ nachgeladen (file:// erlaubt das nicht)
  const datei = path.resolve(process.argv[2] || 'app/dist/weltkugel.html'), wurzel = path.dirname(datei);
  const server = require('node:http').createServer((q, a) => {
    const f = path.join(wurzel, decodeURIComponent(q.url.split('?')[0]));
    if (!f.startsWith(wurzel)) { a.writeHead(403); a.end(); return; }
    require('node:fs').readFile(f, (e, d) => { if (e) { a.writeHead(404); a.end(); } else { a.writeHead(200, { 'content-type': f.endsWith('.json') ? 'application/json' : 'text/html; charset=utf-8' }); a.end(d); } });
  });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  await page.goto(`http://127.0.0.1:${server.address().port}/${path.basename(datei)}`);
  await page.waitForSelector('#gk-seite h2');
  const ok = (b, t) => { if (!b) throw Error(t); };
  const seite = () => page.locator('#gk-seite').innerText();
  const warte = ms => page.waitForTimeout(ms);
  const bild = n => page.screenshot({ path: `${BILD}/${n}.png` });
  await page.click('[data-gkform="politik"]'); await warte(800);
  ok(typeof (await page.evaluate(() => typeof WAHLEN)) === 'string', 'WAHLEN fehlt');
  ok(await page.locator('#wa-satz').isVisible(), 'Satzleiste fehlt');
  ok(await page.locator('#wa-leiter').isVisible(), 'Ebenenleiter fehlt');
  const mitKarte = await page.evaluate(() => !!GLOBUS.karte());
  if (!mitKarte) { console.log('ohne WebGL: Kartenteil übersprungen'); await browser.close(); server.close(); return; }
  await warte(1500); await bild('1-welt-e1');
  // Welt E1: Deutschland anklicken -> Bundestagswahl 2025
  await page.evaluate(() => WAHLEN.wahlWaehlen('DE-BT-2025')); await warte(2500);
  let t = await seite();
  ok(/Bundestag/.test(t) && /E1/.test(t), 'Ergebniskarte Bundestagswahl fehlt');
  await bild('2-de-gesamt');
  // Zoom auf Länder, dann Wahlkreise
  await page.evaluate(() => GLOBUS.karte().jumpTo({ center: [10.4, 51.1], zoom: 4.6 })); await warte(1500);
  await bild('3-de-laender');
  await page.evaluate(() => GLOBUS.karte().jumpTo({ center: [6.9, 51.3], zoom: 7.2 })); await warte(1800);
  await bild('4-de-wahlkreise');
  const box = await page.locator('.maplibregl-map').first().boundingBox();
  const p = await page.evaluate(() => { const q = GLOBUS.karte().project([6.78, 51.23]); return { x: q.x, y: q.y }; });
  await page.mouse.click(box.x + p.x, box.y + p.y); await warte(700);
  t = await seite();
  ok(/Düsseldorf/.test(t), 'Wahlkreis Düsseldorf nicht ausgewählt:\n' + t.slice(0, 400));
  await bild('5-wk-klick');
  // E0 Europawahl nach Kreisen
  await page.evaluate(() => WAHLEN.ebeneWaehlen(0)); await warte(1800);
  t = await seite(); ok(/Europ/.test(t), 'Europawahl fehlt');
  await bild('6-e0-kreise');
  // E2 Landtag NRW
  await page.evaluate(() => WAHLEN.ebeneWaehlen(2)); await warte(1800);
  await bild('7-e2');
  // Landtagswahlkreise NRW (Landeswahlleiterin): der Ortsanker wählt beim Ebenenwechsel den Landtagswahlkreis in Düsseldorf
  t = await seite(); ok(/Landtagswahl/.test(t), 'Landtagswahl NRW fehlt');
  ok(/Düsseldorf/.test(t) && /Direktmandat/.test(t) && /Landtagswahlkreis/.test(t), 'Landtagswahlkreis Düsseldorf fehlt:\n' + t.slice(0, 500));
  await bild('7b-e2-lwk');
  await page.evaluate(() => WAHLEN.ebeneWaehlen(3)); await warte(1800);
  await bild('8-e3');
  await page.evaluate(() => WAHLEN.ebeneWaehlen(4)); await warte(1800);
  await bild('9-e4');
  // Vereinigtes Königreich: Unterhauswahl 2024 mit 650 Wahlkreisen; Klick in Westminster zeigt die gewählte Person
  await page.evaluate(() => WAHLEN.wahlWaehlen('GB-unterhaus-2024', false));
  await page.evaluate(() => GLOBUS.karte().jumpTo({ center: [-0.13, 51.5], zoom: 8 })); await warte(1800);
  t = await seite(); ok(/House of Commons/.test(t) && /650/.test(t), 'Unterhauswahl 2024 fehlt');
  const pl = await page.evaluate(() => { const q = GLOBUS.karte().project([-0.127, 51.4995]); return { x: q.x, y: q.y }; });
  await page.mouse.click(box.x + pl.x, box.y + pl.y); await warte(700);
  t = await seite(); ok(/Gewählt:/.test(t) && /Labour|Conservatives|Lib Dems/.test(t), 'Wahlkreis in London fehlt:\n' + t.slice(0, 500));
  await bild('9b-gb-wahlkreis');
  // Frankreich: Assemblée nationale 2024, 577 Wahlkreise mit zwei Wahlgängen; Klick in Paris
  await page.evaluate(() => WAHLEN.wahlWaehlen('FR-unterhaus-2024', false));
  await page.evaluate(() => GLOBUS.karte().jumpTo({ center: [2.35, 48.86], zoom: 8 })); await warte(1800);
  t = await seite(); ok(/Assemblée nationale/.test(t) && /577/.test(t), 'Assemblée nationale 2024 fehlt');
  const pf = await page.evaluate(() => { const q = GLOBUS.karte().project([2.3, 48.87]); return { x: q.x, y: q.y }; });
  await page.mouse.click(box.x + pf.x, box.y + pf.y); await warte(700);
  t = await seite(); ok(/Gewählt:/.test(t) && /Wahlgang/.test(t) && /Paris/.test(t), 'Wahlkreis in Paris fehlt:\n' + t.slice(0, 500));
  await bild('9c-fr-wahlkreis');
  // Kanada, Australien, Schweiz, Österreich: je ein Klick in einen Wahlkreis bzw. eine Gemeinde
  const klick = async (id, mitte, zoom, pt, muster, name) => {
    await page.evaluate(i => WAHLEN.wahlWaehlen(i, false), id);
    await page.evaluate(([c, z]) => GLOBUS.karte().jumpTo({ center: c, zoom: z }), [mitte, zoom]); await warte(1800);
    const q = await page.evaluate(x => { const r = GLOBUS.karte().project(x); return { x: r.x, y: r.y }; }, pt);
    await page.mouse.click(box.x + q.x, box.y + q.y); await warte(700);
    t = await seite(); ok(muster.every(m => m.test(t)), `${name} fehlt:\n` + t.slice(0, 500));
    await bild('9d-' + id);
  };
  await klick('CA-unterhaus-2025', [-79.4, 43.7], 8, [-79.38, 43.65], [/Gewählt:/, /Liberale|Konservative|NDP/], 'Wahlkreis in Toronto');
  await klick('AU-unterhaus-2025', [151.2, -33.87], 8, [151.21, -33.87], [/Gewählt:/, /nach Präferenzen/], 'Division in Sydney');
  await klick('CH-unterhaus-2023', [8.5, 47.2], 6.5, [8.55, 47.4], [/Kanton Zürich/, /Sitzverteilung/i], 'Kanton Zürich');
  await klick('AT-unterhaus-2024', [15.4, 47.07], 8, [15.44, 47.07], [/Graz/, /FPÖ|ÖVP|SPÖ/], 'Gemeinde Graz');
  // Ansicht Regierungen
  await page.evaluate(() => document.querySelector('[data-gkpolansicht="regierungen"]').click()); await warte(1200);
  ok(!(await page.locator('#wa-satz').isVisible()), 'Satzleiste in Regierungen sichtbar');
  await bild('10-regierungen');
  await page.evaluate(() => document.querySelector('[data-gkpolansicht="wahlen"]').click()); await warte(800);
  ok(await page.locator('#wa-satz').isVisible(), 'Satzleiste kommt nicht zurück');
  // andere Form blendet alles aus
  await page.click('[data-gkform="laender"]').catch(() => {}); await warte(600);
  if (errors.length) throw Error(errors.join('\n'));
  console.log('Wahlen-Smoke OK');
  await browser.close(); server.close();
})().catch(e => { console.error(e); process.exit(1); });
