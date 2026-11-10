// Weltkugel, Reiter Handel: Güterwahl färbt die Länder ein, Länderseite zeigt Exportgüter, Häfen und Flughäfen sind angeklickt erreichbar.
const { chromium } = require('playwright');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', e => errors.push(e.stack || e.message));
  const ziel = process.argv[2] || 'app/dist/weltkugel.html';      // Datei oder http(s)-Adresse (API-Fassung lädt data/gueter.json nach)
  await page.goto(/^https?:/.test(ziel) ? ziel : 'file://' + path.resolve(ziel));
  await page.waitForSelector('#gk-seite h2');
  await page.click('[data-gkform="handel"]');
  const seite = async () => (await page.locator('#gk-seite').innerText()).toLowerCase();   // Überschriften sind per CSS in Großbuchstaben
  await page.waitForFunction(() => document.querySelector('#gk-seite').innerText.toLowerCase().includes('exporte nach gut'), null, { timeout: 15000 });
  if (!(await seite()).includes('exporte nach gut')) throw Error('Güterauswahl fehlt in der Startseite Handel');
  if (!(await seite()).includes('seehäfen und flughäfen')) throw Error('Hafenblock fehlt');
  await page.click('[data-gkgut="oel"]');
  const t = await seite();
  if (!t.includes('exportländer 2024') || !/saudi/.test(t)) throw Error('Rangliste Rohöl fehlt oder ohne Saudi-Arabien');
  const hatKarte = await page.evaluate(() => !!GLOBUS.karte());
  if (hatKarte) {
    await page.waitForTimeout(1500);
    const farbe = await page.evaluate(() => JSON.stringify(GLOBUS.karte().getPaintProperty('gu-flaeche', 'fill-color')));
    if (!farbe.includes('"SA"')) throw Error('Länderfüllung nicht nach Rohöl gesetzt');
    const ebenen = await page.evaluate(() => ['vk-haefen', 'vk-flug', 'gu-text'].map(l => !!GLOBUS.karte().getLayer(l)));
    if (ebenen.includes(false)) throw Error('Schichten fehlen: ' + ebenen);
    await page.screenshot({ path: process.env.SHOT || '/tmp/gueter.png' });
  }
  await page.click('[data-gkgut="oel"]');     // abwählen
  await page.click('[data-gkverkehr="h0"]'); await page.waitForTimeout(500);
  if (hatKarte && !(await page.locator('.gk-pop').innerText()).includes('Shanghai')) throw Error('Hafen-Popup fehlt');
  await page.evaluate(() => GLOBUS.landWaehlen('DE')); await page.waitForTimeout(300);
  const de = await seite();
  if (!de.includes('exportgüter') || !de.includes('personenkraftwagen')) throw Error('Exportgüter Deutschland fehlen');
  if (!de.includes('hamburg') || !de.includes('fra')) throw Error('Häfen/Flughäfen Deutschland fehlen');
  const fehler = errors.filter(e => !/tile|openfreemap|Failed to fetch|NetworkError/i.test(e));
  if (fehler.length) throw Error('Skriptfehler: ' + fehler.join('\n'));
  console.log('OK handel-gueter-smoke', hatKarte ? '(mit Karte)' : '(ohne Karte)');
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
