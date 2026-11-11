// Farbmodi (thema.js): Zahnrad im Terminal und auf der Weltkugel, Wechsel Dunkel/Hell/Dunkelblau, Speicherung in localStorage,
// Kartenfarben werden umgerechnet und beim Zurückschalten wiederhergestellt.
// Aufruf: node app/tests/thema-smoke.js app/dist/weltkugel.html
const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const ziel = process.argv[2] || 'app/dist/weltkugel.html';
  const url = /^https?:/.test(ziel) ? ziel : 'file://' + path.resolve(ziel);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const fehler = [];
  page.on('pageerror', e => fehler.push(e.message));
  const pruefe = (bed, text) => { if (!bed) { console.error('FEHLER', text); process.exitCode = 1; } else console.log('ok    ', text); };
  const css = v => page.evaluate(v => getComputedStyle(document.documentElement).getPropertyValue(v).trim(), v);

  await page.goto(url + '#start');
  await page.waitForTimeout(3000);
  pruefe(await page.evaluate(() => !document.documentElement.hasAttribute('data-thema')), 'Standard ist Dunkel (kein data-thema)');
  pruefe(await css('--bg') === '#07090c', 'Dunkel: --bg unverändert');
  pruefe(await page.locator('.top .cmd .th-zahnrad').count() === 1, 'Zahnrad im Terminal-Kopf');

  await page.click('.th-zahnrad >> visible=true');      // Terminal-Kopf, auf der Weltkugel-Seite der Kartenkopf
  pruefe(await page.locator('#th-fenster').isVisible(), 'Einstellungsfenster öffnet');
  await page.click('#th-fenster input[value="hell"]');
  pruefe(await page.evaluate(() => document.documentElement.dataset.thema) === 'hell', 'Hell gesetzt');
  pruefe(await css('--bg') === '#f4f5f7', 'Hell: --bg hell');
  pruefe(await page.evaluate(() => localStorage.getItem('sphaerae-thema')) === 'hell', 'Hell gespeichert');
  await page.keyboard.press('Escape');
  pruefe(!(await page.locator('#th-fenster').isVisible()), 'Escape schließt das Fenster');

  await page.reload();
  await page.waitForTimeout(3000);
  pruefe(await page.evaluate(() => document.documentElement.dataset.thema) === 'hell', 'Hell bleibt nach dem Neuladen');

  // Weltkugel: Zahnrad im Kartenkopf, Kartenfarben folgen dem Modus
  if (await page.locator('#globus').count()) {
    await page.evaluate(() => { location.hash = '#globus'; });
    await page.waitForTimeout(5000);
    const knopf = page.locator('#globus .gk-kopf .th-zahnrad');
    pruefe(await knopf.count() === 1 && await knopf.isVisible(), 'Zahnrad auf der Weltkugel');
    const halo = () => page.evaluate(() => {
      const m = THEMA.karteObjekt(); if (!m) return null;
      const l = (m.getStyle().layers || []).find(x => x.paint && x.paint['text-halo-color']);
      return l ? String(m.getPaintProperty(l.id, 'text-halo-color')) : null;
    });
    const hHell = await halo();
    await knopf.click();
    await page.click('#th-fenster input[value="dunkelblau"]');
    await page.waitForTimeout(500);
    pruefe(await css('--bg') === '#040a14', 'Dunkelblau: --bg mitternachtsblau');
    const hBlau = await halo();
    await page.click('#th-fenster input[value="dunkel"]');
    await page.waitForTimeout(500);
    const hDunkel = await halo();
    if (hHell != null) pruefe(hHell !== hDunkel && hBlau !== hDunkel && hDunkel === '#07090c', `Kartenfarben je Modus (${hHell} / ${hBlau} / ${hDunkel})`);
    else console.log('hinweis Karte ohne WebGL, Kartenfarben nicht geprüft');
    pruefe(await page.evaluate(() => localStorage.getItem('sphaerae-thema')) === null, 'Dunkel löscht den Eintrag (Standard)');
  }
  pruefe(fehler.length === 0, 'keine JavaScript-Fehler ' + fehler.slice(0, 3).join(' | '));
  await browser.close();
  if (!process.exitCode) console.log('Thema OK');
})();
