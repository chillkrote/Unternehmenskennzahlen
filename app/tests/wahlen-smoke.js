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
  await page.goto('file://' + path.resolve(process.argv[2] || 'app/dist/weltkugel.html'));
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
  if (!mitKarte) { console.log('ohne WebGL: Kartenteil übersprungen'); await browser.close(); return; }
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
  await page.evaluate(() => WAHLEN.ebeneWaehlen(3)); await warte(1800);
  await bild('8-e3');
  await page.evaluate(() => WAHLEN.ebeneWaehlen(4)); await warte(1800);
  await bild('9-e4');
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
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
