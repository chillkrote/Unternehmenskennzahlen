// Alle Unternehmensnetze: jedes eingebettete Netz über die Weltkugel-Suche bzw. GLOBUS.oeffnen öffnen und prüfen,
// dass das Netz-Panel mit dem richtigen Konzern, allen Standorten und Bögen erscheint. Aufruf: node netze-alle-smoke.js <html> [ordner]
const { chromium } = require('playwright');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.stack || e.message));
  await page.goto('file://' + path.resolve(process.argv[2] || 'app/dist/weltkugel.html'));
  await page.waitForSelector('#gk-seite h2');
  const netze = await page.evaluate(() => Object.entries(NETZ.netze()).map(([id, d]) => ({ id, name: d.name, orte: d.standorte.length, bez: d.beziehungen.length })));
  const erwartet = ['U000712', 'U000061', 'U000065', 'U000124', 'U000744', 'U000745', 'U004835'];
  for (const id of erwartet) if (!netze.find(n => n.id === id)) throw Error('Netz fehlt: ' + id + ' (vorhanden: ' + netze.map(n => n.id) + ')');
  const zeilen = [];
  for (const n of netze) {
    await page.evaluate(() => { document.querySelectorAll('.gf [data-gfzu]').forEach(b => b.click()); });
    await page.evaluate(id => GLOBUS.oeffnen(id, {}), n.id);
    await page.waitForSelector('#netz-panel:not([hidden])', { timeout: 5000 });
    const titel = await page.locator('#netz-panel header b').innerText();
    if (titel.trim() !== n.name.trim()) throw Error(`${n.id}: falscher Netztitel ${titel} statt ${n.name}`);
    const orte = await page.locator('#netz-panel [data-nzort]').count();
    if (orte !== n.orte) throw Error(`${n.id}: ${orte} von ${n.orte} Standorten in der Liste`);
    const boegen = await page.evaluate(() => NETZ.daten().linien.features.length);
    if (boegen !== n.bez) throw Error(`${n.id}: ${boegen} von ${n.bez} Bögen auf der Karte`);
    if (process.argv[3]) { await page.evaluate(() => { document.querySelectorAll('.gf [data-gfzu]').forEach(b => b.click()); }); await page.waitForTimeout(2500); await page.screenshot({ path: path.join(process.argv[3], `netz-${n.id}.png`) }); }
    zeilen.push(`${n.name} (${orte} Standorte, ${boegen} Bögen)`);
  }
  // Einstieg über die Suche (wie ein Nutzer)
  await page.evaluate(() => { document.querySelectorAll('.gf [data-gfzu]').forEach(b => b.click()); });
  await page.fill('#gk-suchfeld', 'BASF SE'); await page.press('#gk-suchfeld', 'Enter');
  await page.waitForSelector('#netz-panel:not([hidden])', { timeout: 5000 });
  if (!/BASF/.test(await page.locator('#netz-panel header b').innerText())) throw Error('Suche nach BASF öffnet nicht das BASF-Netz');
  if (errors.length) throw Error('JavaScript-Fehler: ' + errors.join('\n'));
  await browser.close();
  console.log('Unternehmensnetze: ' + zeilen.join('; ') + '; Suche BASF; keine JavaScript-Fehler');
})().catch(e => { console.error(e); process.exit(1); });
