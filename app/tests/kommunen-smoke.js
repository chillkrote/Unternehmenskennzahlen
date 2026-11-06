// Weltkugel, Politik: Kommunen NRW erscheinen ab Zoom ~5 als Flächen; Klick öffnet die Sitzverteilung in der Seitenleiste.
const { chromium } = require('playwright');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.stack || e.message));
  await page.goto('file://' + path.resolve(process.argv[2] || 'app/dist/weltkugel.html'));
  await page.waitForSelector('#gk-seite h2');
  await page.click('[data-gkform="politik"]');
  await page.evaluate(() => GLOBUS.landWaehlen('DE'));
  if (!(await page.evaluate(() => !!GLOBUS.karte()))) { console.log('ohne WebGL: Kartenteil übersprungen'); await browser.close(); return; }
  await page.evaluate(() => GLOBUS.karte().jumpTo({ center: [6.78, 51.23], zoom: 8.2 })); await page.waitForTimeout(1500);
  const n = await page.evaluate(() => GLOBUS.karte().queryRenderedFeatures({ layers: ['po-kom-stadt', 'po-kom-gem'] }).length);
  if (n < 3) throw Error('Kommunenpunkte fehlen: ' + n);
  const pt = await page.evaluate(() => { const m = GLOBUS.karte(); if (!m.queryRenderedFeatures({ layers: ['po-kom-stadt'] }).some(x => x.properties.id === 'duesseldorf')) throw Error('Fläche Düsseldorf fehlt'); const p = m.project([6.7767, 51.2256]); return { x: p.x, y: p.y }; });
  const box = await page.locator('#gk-karte, #karte, .maplibregl-map').first().boundingBox();
  await page.mouse.click(box.x + pt.x, box.y + pt.y); await page.waitForTimeout(500);
  const txt = (await page.locator('#gk-seite').innerText()).toLowerCase();
  if (!txt.includes('rat düsseldorf') || !txt.includes('bezirksvertretungen')) throw Error('Sitzverteilung Düsseldorf fehlt in der Seitenleiste');
  if (!(await page.locator('#gk-seite svg[aria-label="Sitzverteilung"]').count())) throw Error('Halbkreis fehlt');
  await page.screenshot({ path: '/tmp/claude-0/kom-globus.png' });
  if (errors.length) throw Error(errors.join('\n'));
  console.log('Kommunen-Smoke OK, Punkte im Bild:', n);
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
