// Meldungen: gemeinsame Regeln (Fenster 3/7/14 Tage, ein Symbol je Typ, Alter) im Terminal (HDL) und auf der Weltkugel.
const { chromium } = require('playwright');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const errors = [];
  // Terminal
  let page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on('pageerror', e => errors.push(e.stack || e.message));
  await page.goto('file://' + path.resolve(process.argv[2] || 'app/dist/bankterminal.html') + '#h-ueb');
  await page.waitForSelector('.mld-reiter');
  const regeln = await page.evaluate(() => {
    const iso = d => new Date(Date.now() - d * 864e5).toISOString().slice(0, 10);
    const l = [{ datum: iso(0), typ: 'angriff' }, { datum: iso(2), typ: 'stau' }, { datum: iso(6), typ: 'wetter' }, { datum: iso(13), typ: 'streik' }, { datum: iso(20), typ: 'sperrung' }, { datum: '' }];
    const out = [3, 7, 14].map(f => MLD.sichtbar(l, f).length);
    return { out, text: [MLD.alterText(iso(0)), MLD.alterText(iso(1)), MLD.alterText(iso(5))], st: [MLD.stand(0), MLD.stand(1), MLD.stand(2), MLD.stand(4)], typen: Object.keys(MLD.TYPEN).length };
  });
  if (JSON.stringify(regeln.out) !== '[2,3,4]') throw Error('Fenster falsch: ' + JSON.stringify(regeln.out));
  if (regeln.text.join('|') !== 'heute|gestern|vor 5 Tagen') throw Error('Alterstext falsch: ' + regeln.text);
  if (regeln.st.join() !== 'neu,neu,aktuell,aelter') throw Error('Stand falsch');
  const vorher = await page.locator('.mld-reiter button.on').first().innerText();
  if (vorher !== '3 Tage') throw Error('Vorgabe ist nicht 3 Tage: ' + vorher);
  if (await page.locator('#app, body').first().innerText().then(t => t.includes('⚠'))) throw Error('altes ⚠-Zeichen noch vorhanden');
  await page.click('[data-mfenster="14"]');
  if ((await page.locator('.mld-reiter button.on').first().innerText()) !== '14 Tage') throw Error('Reiter 14 Tage nicht gesetzt');
  // Weltkugel
  page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on('pageerror', e => errors.push(e.stack || e.message));
  await page.goto('file://' + path.resolve(process.argv[3] || 'app/dist/weltkugel.html'));
  await page.waitForSelector('#gk-seite h2');
  await page.click('[data-gkform="handel"]');
  await page.evaluate(() => GLOBUS.landWaehlen('DE'));
  await page.waitForSelector('#gk-seite .mld-reiter');
  await page.click('#gk-seite [data-mfenster="7"]');
  if ((await page.locator('#gk-seite .mld-reiter button.on').innerText()) !== '7 Tage') throw Error('Reiter 7 Tage fehlt auf der Weltkugel');
  if ((await page.locator('#gk-seite').innerText()).includes('⚠')) throw Error('⚠ auf der Weltkugel');
  await browser.close();
  if (errors.length) throw Error('Seitenfehler:\n' + errors.join('\n'));
  console.log('Meldungen-Smoketest ok');
})().catch(e => { console.error(e); process.exit(1); });
