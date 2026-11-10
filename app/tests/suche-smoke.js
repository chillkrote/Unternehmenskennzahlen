// Universelle Suche (P3.3, suche.js) in der API-Fassung: Vorschläge über /search an der Befehlszeile des Terminals und im
// Suchfeld der Weltkugel, Auswahl per Tastatur und Maus, kombinierte Auswahl „Branche · Land“, Enter ohne Vorschlag bleibt Befehl.
// Aufruf: node app/tests/suche-smoke.js http://localhost:8080   (Compose-Stack mit API; ohne API gibt es keine Vorschläge)
const { chromium } = require('playwright');
(async () => {
  const basis = (process.argv[2] || 'http://localhost:8080').replace(/\/+$/, '');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [], fehler = [];
  page.on('pageerror', e => errors.push(e.stack || e.message));
  const pruefe = (ok, was) => { console.log(ok ? 'ok    ' : 'FEHLER', was); if (!ok) fehler.push(was); };
  const vorschlaege = () => page.locator('#cmd-vorschlaege [role=option]');

  // Terminal: Befehlszeile
  await page.goto(basis + '/bankterminal.html#u-ueb');
  await page.waitForFunction(() => typeof UNT !== 'undefined' && UNT.da && UNT.da(), null, { timeout: 30000 });
  await page.fill('#cmd', 'Siemns');
  await page.waitForSelector('#cmd-vorschlaege [role=option]', { timeout: 15000 });
  const erste = await vorschlaege().allInnerTexts();
  pruefe(erste.some(t => /Siemens/.test(t)), 'fehlertoleranter Vorschlag „Siemns“ -> Siemens');
  await page.keyboard.press('ArrowDown');
  pruefe(await page.locator('#cmd-vorschlaege [aria-selected=true]').count() === 1, 'Pfeil runter markiert einen Vorschlag');
  const ziel = await page.locator('#cmd-vorschlaege [aria-selected=true] b').innerText();
  await page.keyboard.press('Enter');
  await page.waitForFunction(() => location.hash.startsWith('#firma-'), null, { timeout: 10000 });
  await page.waitForFunction(t => document.getElementById('view').textContent.includes(t), ziel, { timeout: 15000 });
  pruefe(true, `Enter öffnet das Profil (${ziel})`);
  pruefe(await page.locator('#cmd-vorschlaege').isHidden(), 'Vorschlagsliste danach geschlossen');

  await page.fill('#cmd', 'Deutschland Automobile');
  await page.waitForFunction(() => /Auswahl/i.test((document.getElementById('cmd-vorschlaege') || {}).textContent || ''), null, { timeout: 15000 });
  const kombi = page.locator('#cmd-vorschlaege [role=option]').first();
  pruefe(/Automobil · Deutschland/.test(await kombi.innerText()), 'kombinierte Auswahl „Automobil · Deutschland“ zuerst');
  await kombi.click();
  await page.waitForFunction(() => location.hash === '#u-verzeichnis', null, { timeout: 10000 });
  await page.waitForTimeout(800);
  const sel = await page.evaluate(() => [document.getElementById('uland') && document.getElementById('uland').value, document.getElementById('ubr') && document.getElementById('ubr').value]);
  pruefe(sel[0] === 'DE' && sel[1] === 'automobil', `Verzeichnis gefiltert (Land ${sel[0]}, Branche ${sel[1]})`);

  // Enter ohne markierten Vorschlag: bisheriger Befehl
  await page.fill('#cmd', 'MKT');
  await page.waitForTimeout(400);
  await page.press('#cmd', 'Enter');
  await page.waitForFunction(() => location.hash === '#mkt', null, { timeout: 10000 });
  pruefe(true, 'Enter ohne Vorschlag führt den Befehl MKT aus');
  await page.fill('#cmd', 'x'); await page.waitForTimeout(400);
  pruefe(await page.locator('#cmd-vorschlaege').isHidden(), 'unter zwei Zeichen keine Vorschläge');
  await page.fill('#cmd', '');

  // Weltkugel: Land und Unternehmen aus den Vorschlägen
  await page.goto(basis + '/weltkugel.html');
  await page.waitForSelector('#gk-seite h2');
  await page.fill('#gk-suchfeld', 'Frankr');
  await page.waitForFunction(() => /Frankreich/.test((document.getElementById('gk-suchfeld-vorschlaege') || {}).textContent || ''), null, { timeout: 15000 });
  await page.locator('#gk-suchfeld-vorschlaege [role=option]', { hasText: 'Frankreich' }).first().click();
  await page.waitForFunction(() => document.querySelector('#gk-seite h2').textContent === 'Frankreich', null, { timeout: 10000 });
  pruefe(true, 'Weltkugel: Land aus den Vorschlägen gewählt');
  const vorher = await page.locator('.gf').count();
  await page.fill('#gk-suchfeld', 'Deutsche Bank');
  await page.waitForFunction(() => /Unternehmen/i.test((document.getElementById('gk-suchfeld-vorschlaege') || {}).textContent || ''), null, { timeout: 15000 });
  await page.locator('#gk-suchfeld-vorschlaege [role=option]', { hasText: 'Deutsche Bank' }).first().click();
  await page.waitForFunction(n => document.querySelectorAll('.gf').length === n + 1, vorher, { timeout: 10000 });
  pruefe(true, 'Weltkugel: Unternehmensfenster aus den Vorschlägen geöffnet');

  const js = errors.filter(e => !/tile|openfreemap|Failed to fetch|NetworkError/i.test(e));
  pruefe(!js.length, 'keine JavaScript-Fehler' + (js.length ? ': ' + js.join(' | ') : ''));
  await browser.close();
  if (fehler.length) { console.error(fehler.length + ' Fehler'); process.exit(1); }
  console.log('Suche-Smoke OK');
})().catch(e => { console.error(e); process.exit(1); });
