// Fußleiste: drei Schaltflächen, Text aus app/seiten/*.md, Platzhalter markiert, Schließen mit Esc.
const { chromium } = require('playwright');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.stack || e.message));
  await page.goto('file://' + path.resolve(process.argv[2] || 'app/dist/bankterminal.html'));
  await page.waitForSelector('#fussleiste');
  const namen = await page.locator('#fussleiste button').allInnerTexts();
  if (namen.join('|') !== 'Impressum|Kontakt|About Sphaerae') throw Error('Schaltflächen: ' + namen);
  for (const [id, wort] of [['impressum', 'Angaben gemäß'], ['kontakt', 'Erreichbar über'], ['about', 'Weltkugel']]) {
    await page.click(`#fussleiste [data-seite="${id}"]`);
    const t = await page.locator('.sf-text').innerText();
    if (!t.includes(wort)) throw Error(`${id}: "${wort}" fehlt`);
    if (t.includes('<!--')) throw Error(`${id}: Kommentar sichtbar`);
    if (id === 'impressum' && !(await page.locator('.sf-platzhalter').count())) throw Error('Platzhalter nicht markiert');
    await page.keyboard.press('Escape');
    if (await page.locator('#sf-fenster').isVisible()) throw Error('Esc schließt nicht');
  }
  if (errors.length) throw Error(errors.join('\n'));
  await browser.close();
  console.log('seiten-smoke ok');
})().catch(e => { console.error(e); process.exit(1); });
