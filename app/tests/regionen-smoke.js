// Regionen (Volkswirtschaft, Kreisebene, src/regionen.js) auf der Weltkugel: Kreiskarte nach Kennzahl, Kreiskarte je Kreis mit
// Rang und Europawahl, „Wirtschaft und Wahl“ mit derselben Statistik wie die Korrelationsanalyse. Sollwerte aus volkswirtschaft/regional.
// Aufruf: node app/tests/regionen-smoke.js [app/dist/weltkugel.html | http://localhost:8080/weltkugel.html]
const { chromium } = require('playwright');
const path = require('node:path');
const fs = require('node:fs');
const csv = fs.readFileSync(path.resolve(__dirname, '../../volkswirtschaft/regional/zeitreihe_lang.csv'), 'utf8').trim().split('\n').slice(1).map(z => z.split(','));
const soll = (sid, nuts, jahr) => +(csv.find(z => z[0] === sid && z[1] === nuts && z[2] === jahr) || [])[3];
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [], fehler = [];
  page.on('pageerror', e => errors.push(e.stack || e.message));
  const pruefe = (ok, was) => { console.log(ok ? 'ok    ' : 'FEHLER', was); if (!ok) fehler.push(was); };
  const http = /^https?:/.test(process.argv[2] || '');
  const datei = path.resolve(http ? 'app/dist/weltkugel.html' : (process.argv[2] || 'app/dist/weltkugel.html')), wurzel = path.dirname(datei);
  const server = require('node:http').createServer((q, a) => {
    const f = path.join(wurzel, decodeURIComponent(q.url.split('?')[0]));
    if (!f.startsWith(wurzel)) { a.writeHead(403); a.end(); return; }
    fs.readFile(f, (e, d) => { if (e) { a.writeHead(404); a.end(); } else { a.writeHead(200, { 'content-type': f.endsWith('.json') ? 'application/json' : 'text/html; charset=utf-8' }); a.end(d); } });
  });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  await page.goto(http ? process.argv[2] : `http://127.0.0.1:${server.address().port}/${path.basename(datei)}`);
  await page.waitForSelector('#gk-seite h2');
  const seite = () => page.locator('#gk-seite').innerText();
  await page.click('[data-gkform="vwl"]');
  await page.waitForFunction(() => typeof REGIONEN !== 'undefined' && REGIONEN.daten() && REGIONEN.daten().serien, null, { timeout: 60000 });
  pruefe(true, 'Regionaldaten geladen');
  await page.evaluate(() => GLOBUS.landWaehlen('DE'));
  await page.waitForFunction(() => /Kreise \(Regionaldaten\)/i.test(document.getElementById('gk-seite').innerText), null, { timeout: 20000 });
  pruefe(/höchster Wert Wolfsburg/.test(await seite()), 'Länderseite Deutschland: Einstieg mit dem höchsten BIP je Einwohner (Wolfsburg)');
  await page.click('[data-rg-oeffnen=""], [data-rg-oeffnen]:not([data-rg-oeffnen="wahl"])');
  await page.waitForFunction(() => /Kreise in Deutschland/.test(document.getElementById('gk-seite').innerText), null, { timeout: 10000 });
  let t = await seite();
  pruefe(/400 von 400 Kreisen mit Wert/.test(t), 'Rangliste: 400 von 400 Kreisen');
  // Kreis aus der Liste: Stuttgart (08111 / DE111)
  await page.selectOption('[data-rg="serie"]', 'r3_bip');
  await page.waitForTimeout(300);
  await page.locator('[data-rg-kreis="08111"]').first().click();
  await page.waitForFunction(() => /NUTS-3 DE111/.test(document.getElementById('gk-seite').innerText), null, { timeout: 10000 });
  t = await seite();
  const bip = soll('r3_bip', 'DE111', '2024');
  pruefe(t.includes((bip / 1000).toLocaleString('de-DE', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' Mrd. €'), `Kreiskarte Stuttgart: BIP 2024 ${bip} Mio. € wie in der Datei`);
  pruefe(/Rang \d+ von 400/.test(t), 'Kreiskarte zeigt den Rang unter 400 Kreisen');
  const mitKarte = await page.evaluate(() => !!GLOBUS.karte());
  if (mitKarte) {
    await page.waitForFunction(() => { const m = GLOBUS.karte(); const s = m && m.getSource('rg-kreise'); return s && m.getLayer('rg-flaeche'); }, null, { timeout: 20000 });
    const n = await page.evaluate(async () => (await GLOBUS.karte().getSource('rg-kreise').getData()).features.filter(f => f.properties.farbe !== '#2a313b').length);
    pruefe(n === 400, `Karte: 400 eingefärbte Kreisflächen (${n})`);
    pruefe(/Kreise · BIP \(nominal\) 2024/i.test(await page.locator('#gk-legkarte').innerText()), 'Legende nennt Kennzahl und Jahr');
  } else console.log('hinweis Karte ohne WebGL, Kartenprüfungen übersprungen');
  // Wirtschaft und Wahl (Europawahl 2024 je Kreis)
  await page.click('[data-rg-wahlen]');
  await page.waitForFunction(() => /Pearson r/i.test(document.getElementById('gk-seite').innerText), null, { timeout: 60000 });
  await page.selectOption('[data-rg="x"]', 'r3_bip_je_einwohner');
  await page.selectOption('[data-rg="partei"]', 'AfD');
  await page.waitForTimeout(300);
  t = await seite();
  pruefe(/Europawahl 2024/.test(t) && /Kreise\s+400/.test(t), 'Wirtschaft und Wahl: Europawahl 2024 über 400 Kreise');
  // gleiche Statistik wie KOR.stat, aus den eingebetteten Daten nachgerechnet
  const r = await page.evaluate(() => {
    const D = REGIONEN.daten(), w = WAHLEN.wahl('DE-EP-2024'), u = w.einheiten.find(x => x.geo === 'kreise-de'), j = D.jahre.indexOf(2024);
    const xs = [], ys = []; for (const [a, v] of Object.entries(u.werte)) { const x = D.werte.r3_bip_je_einwohner[a][j]; const e = v.s.s.find(y => y[0] === 'AfD'); if (x != null) { xs.push(x); ys.push(e ? e[2] : 0); } }
    return KOR.stat(xs, ys).r;
  });
  pruefe(t.includes('Pearson r\t' + r.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })) || t.includes(r.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })), `Pearson r = ${r.toFixed(3)} wie KOR.stat`);
  pruefe(await page.locator('.rg-streu circle').count() === 400, 'Streudiagramm mit 400 Punkten');
  pruefe(/AfD/.test(t) && /Wahlbeteiligung/.test(t), 'Kreiskarte zeigt das Europawahlergebnis im Kreis');
  // Landtagswahl Sachsen-Anhalt 2026 (14 Kreise)
  const st = await page.locator('[data-rg="wahl"] option', { hasText: 'Sachsen-Anhalt' }).count();
  if (st) {
    await page.selectOption('[data-rg="wahl"]', 'DE-ST-parl-2026');
    await page.waitForFunction(() => /Kreise\s+14/.test(document.getElementById('gk-seite').innerText), null, { timeout: 20000 });
    pruefe(true, 'Landtagswahl Sachsen-Anhalt 2026: 14 Kreise');
  }
  pruefe(!errors.length, 'keine Skriptfehler' + (errors.length ? ': ' + errors.join(' | ') : ''));
  await page.screenshot({ path: process.env.SCREENSHOT || '/tmp/regionen.png' });
  await browser.close(); server.close();
  if (fehler.length) { console.log(fehler.length, 'Fehler'); process.exit(1); }
  console.log('alle Prüfungen bestanden');
})();
