// Unternehmensnetz: Volkswagen über die Suche öffnen, Netz-Panel und Kartenebene prüfen, Standort und Beziehung wählen,
// Filter umschalten, über ein Tochterunternehmen (Porsche AG) einsteigen. Optional Bildschirmfotos: node netz-smoke.js <html> <ordner>
const { chromium } = require('playwright');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.stack || e.message));
  await page.goto('file://' + path.resolve(process.argv[2] || 'app/dist/weltkugel.html'));
  await page.waitForSelector('#gk-seite h2');
  const foto = async n => { if (process.argv[3]) { await page.waitForTimeout(2500); await page.screenshot({ path: path.join(process.argv[3], n + '.png') }); } };
  const netze = await page.evaluate(() => Object.keys(NETZ.netze()));
  if (!netze.includes('U000712')) throw Error('Kein Netz für Volkswagen eingebettet: ' + netze);
  await page.fill('#gk-suchfeld', 'Volkswagen AG'); await page.press('#gk-suchfeld', 'Enter');
  await page.waitForSelector('#netz-panel:not([hidden])', { timeout: 5000 });
  const titel = await page.locator('#netz-panel header b').innerText();
  if (!/Volkswagen/.test(titel)) throw Error('Falscher Netztitel: ' + titel);
  const orte = await page.locator('#netz-panel [data-nzort]').count();
  if (orte < 40) throw Error('Zu wenige Standorte in der Liste: ' + orte);
  const karte = await page.evaluate(() => { const m = GLOBUS.karte(); return m && m.getLayer('netz-linie-tochter') ? NETZ.daten().linien.features.length : -1; });
  await page.evaluate(() => { document.querySelectorAll('.gf [data-gfzu]').forEach(b => b.click()); });
  await foto('1-netz-volkswagen');
  // Standort wählen: Győr (Antriebe)
  await page.click('#netz-panel [data-nzort="gyoer"]');
  const det = await page.locator('#netz-panel .nz-inhalt').innerText();
  if (!/1\.585\.290/.test(det) || !/Antriebe/.test(det)) throw Error('Detail Győr ohne Antriebszahl');
  await foto('2-standort-gyoer');
  // Beziehung über die Detailliste wechseln, dann Filter: Lieferungen aus
  await page.click('#netz-panel [data-nzliste]');
  await page.click('#netz-panel [data-nzart="lieferung"]');
  const nachFilter = await page.evaluate(() => NETZ.daten().linien.features.filter(f => f.properties.art === 'lieferung').length);
  if (nachFilter) throw Error('Filter Lieferungen wirkt nicht');
  await page.click('#netz-panel [data-nzart="lieferung"]');
  // Einstieg über eine Tochter: Porsche AG
  await page.evaluate(() => GLOBUS.oeffnen('U000175', {}));
  await page.waitForTimeout(300);
  const wahl = await page.locator('#netz-panel .nz-inhalt h4').innerText().catch(() => '');
  if (!/Porsche/.test(wahl)) throw Error('Einstieg über Porsche zeigt nicht den Standort Zuffenhausen: ' + wahl);
  await page.evaluate(() => { document.querySelectorAll('.gf [data-gfzu]').forEach(b => b.click()); });
  await foto('3-porsche-zuffenhausen');
  await page.click('#netz-panel [data-nzzu]');
  if (!(await page.locator('#netz-panel').isHidden())) throw Error('Panel lässt sich nicht schließen');
  await browser.close();
  if (errors.length) throw Error(errors.join('\n'));
  console.log(`Unternehmensnetz: ${titel}, ${orte} Standorte in der Liste, ${karte < 0 ? 'ohne Karte (kein WebGL)' : karte + ' Bögen auf der Karte'}, Standortdetail, Filter, Einstieg über Porsche AG; keine JavaScript-Fehler`);
})().catch(e => { console.error(e); process.exit(1); });
