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
