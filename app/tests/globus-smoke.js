// Weltkugel: Land wählen (Kerndaten), Unternehmen als Fenster öffnen, zwei Fenster vergleichen, ins klassische Terminal und zurück.
// Läuft auch ohne WebGL (dann ohne Karte); Kartenkacheln aus dem Netz werden nicht verlangt.
const { chromium } = require('playwright');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.stack || e.message));
  await page.goto('file://' + path.resolve(process.argv[2] || 'app/dist/weltkugel.html'));
  await page.waitForSelector('#gk-seite h2');
  await page.fill('#gk-suchfeld', 'Deutschland'); await page.press('#gk-suchfeld', 'Enter');
  await page.waitForFunction(() => document.querySelector('#gk-seite h2').textContent === 'Deutschland');
  const kacheln = await page.locator('#gk-seite .gk-kz > div').count();
  if (kacheln < 5) throw Error('Zu wenige Kerndaten für Deutschland: ' + kacheln);
  const ids = await page.evaluate(() => [...document.querySelectorAll('#gk-seite [data-gkfirma]')].slice(0, 2).map(b => b.dataset.gkfirma));
  for (const id of ids) { await page.evaluate(id => { location.hash = 'firma-' + id; }, id); await page.waitForTimeout(150); }
  if (await page.locator('.gf').count() !== 2) throw Error('Erwartet zwei Unternehmensfenster');
  if (await page.evaluate(() => location.hash) !== '#globus') throw Error('Hash nicht auf #globus zurückgesetzt');
  await page.evaluate(() => document.querySelector('.gf:nth-child(1) [data-gfvgl]').click());
  await page.evaluate(() => document.querySelector('.gf:nth-child(2) [data-gfvgl]').click());
  await page.click('[data-gkvgl]');
  const vgl = await page.evaluate(() => UNT.auswahl().length);
  if (vgl !== 2 || await page.locator('.gf').count() !== 3) throw Error('Vergleichsfenster fehlt oder Auswahl falsch: ' + vgl);
  // Unternehmen nur aus der Unternehmenstabelle (ohne Kennzahlen): Stammdaten-Fenster über die Suche
  const stamm = await page.evaluate(() => { const r = document.getElementById('geo-tabelle'); const t = r && JSON.parse(r.textContent); if (!t) return null;
    const j = t.spalten.indexOf('id'), n = t.spalten.indexOf('name'); const z = t.zeilen.find(z => !z[j]); return z && z[n]; });
  if (stamm) {
    await page.fill('#gk-suchfeld', stamm); await page.press('#gk-suchfeld', 'Enter'); await page.waitForTimeout(150);
    if (!(await page.locator('.gf .gk-stamm').count())) throw Error('Stammdaten-Fenster für ' + stamm + ' fehlt');
  }
  await page.evaluate(() => { location.hash = 'u-ueb'; }); await page.waitForTimeout(150);
  if (!(await page.locator('#globus').isHidden()) || !(await page.locator('#view').innerText()).length) throw Error('Klassische Ansicht nicht erreichbar');
  await page.evaluate(() => { location.hash = 'globus'; }); await page.waitForTimeout(150);
  if (await page.locator('#globus').isHidden()) throw Error('Zurück zur Weltkugel geht nicht');
  await browser.close();
  if (errors.length) throw Error(errors.join('\n'));
  console.log(`Weltkugel: Land, ${kacheln} Kerndaten, 2 Unternehmensfenster, Vergleich,${stamm ? ' Stammdaten-Fenster,' : ''} Wechsel zum klassischen Terminal; keine JavaScript-Fehler`);
})().catch(e => { console.error(e); process.exit(1); });
