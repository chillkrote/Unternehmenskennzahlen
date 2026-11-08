// Börse & Finanzen: Marktpuls, Zinskurven, Währungen, Sektoren im Terminal; Marktpuls-Leiste auf der Weltkugel.
const { chromium } = require('playwright');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.stack || e.message));
  await page.goto('file://' + path.resolve(process.argv[2] || 'app/dist/bankterminal.html') + '#b-puls');
  const ansicht = async (hash, wort, anzahl) => {
    await page.evaluate(h => { location.hash = h; }, hash); await page.waitForTimeout(150);
    const t = (await page.locator('main').innerText()).toLowerCase();
    if (!t.includes(wort)) throw Error(`${wort} fehlt in ${hash}`);
    if (anzahl && (await page.locator('main svg path').count()) < anzahl) throw Error(`zu wenige Diagramme in ${hash}`);
    if (/\bnan\b|undefined/.test(t)) throw Error(`NaN/undefined in ${hash}`);
  };
  await ansicht('#b-puls', 'marktpuls', 5);
  await ansicht('#b-puls', 'realisierte volatilität');
  await ansicht('#b-kurven', 'zinsstrukturkurve euroraum', 4);
  await ansicht('#b-kurven', 'zinsstrukturkurve usa');
  await ansicht('#b-waehr', 'kreuzkurse');
  await ansicht('#b-sektoren', 'technologie');
  await page.click('[data-fsektor="Technologie"]'); await page.waitForTimeout(150);
  if (!(await page.locator('main').innerText()).includes('größte Unternehmen')) throw Error('Sektorauswahl zeigt keine Unternehmen');
  await ansicht('#b-makro', 'realzins', 3);
  await ansicht('#b-makro', 'renditeaufschläge');
  await ansicht('#b-bank', 'bankensektor im länderbild');
  await ansicht('#b-ueb', 'marktpuls');
  // Live-Kurse: live.json (hier abgefangen) überschreibt Kacheln und Indexkurse an Ort und Stelle
  await page.evaluate(() => { location.hash = '#b-puls'; }); await page.waitForTimeout(150);
  const fake = { abruf: '2026-11-09T10:00:00Z', werte: { vix: { k: 77.7, v: 70, z: '2026-11-09T09:45:00Z' }, gold: { k: 5000, v: 4000, z: '2026-11-09T09:45:00Z' }, '^GDAXI': { k: 30000, v: 29000, z: '2026-11-09T09:45:00Z' } } };
  await page.route('https://example.test/live.json', r => r.fulfill({ contentType: 'application/json', body: JSON.stringify(fake) }));
  if (!(await page.evaluate(() => FNZ.liveHolen('https://example.test/live.json')))) throw Error('live.json wurde nicht übernommen');
  const vix = await page.locator('[data-lv="vix"]').first().innerText();
  const gold = await page.locator('[data-lv="gold"]').first().innerText();
  if (!vix.includes('77,7') || !gold.includes('+25,0 %')) throw Error('Live-Kacheln nicht aktualisiert: ' + vix + ' | ' + gold);
  if (!(await page.locator('[data-lvfuss]').first().innerText()).includes('Live-Kurse')) throw Error('Live-Hinweis fehlt');
  if (await page.evaluate(() => BOE.korr().indizes.find(x => x.id === '^GDAXI').kurs) !== 30000) throw Error('Indexkurs nicht live');
  if (await page.evaluate(() => FNZ.liveHolen('https://example.test/gibt-es-nicht.json'))) throw Error('Fehler beim Laden muss still bleiben');
  // Weltkugel: Leiste in der Darstellung Börse
  const wk = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  wk.on('pageerror', e => errors.push(e.stack || e.message));
  await wk.goto('file://' + path.resolve('app/dist/weltkugel.html'));
  await wk.waitForSelector('#gk-seite h2');
  await wk.click('[data-gkform="boerse"]'); await wk.waitForTimeout(200);
  if (!(await wk.locator('#gk-seite').innerText()).toLowerCase().includes('marktpuls')) throw Error('Marktpuls-Leiste fehlt auf der Weltkugel');
  // Messgröße: Karte nach Inflation einfärben, Länderseite zeigt Realzins und Bankensektor
  await wk.click('[data-gkbm="inflation"]'); await wk.waitForTimeout(200);
  await wk.evaluate(() => GLOBUS.landWaehlen('DE')); await wk.waitForTimeout(200);
  const lt = (await wk.locator('#gk-seite').innerText()).toLowerCase();
  if (!lt.includes('realzins') || !lt.includes('bankensektor')) throw Error('Länderseite Börse zeigt Realzins oder Bankensektor nicht');
  await browser.close();
  if (errors.length) { console.error(errors.join('\n')); process.exit(1); }
  console.log('Finanz-Ansichten ok');
})().catch(e => { console.error(e); process.exit(1); });
