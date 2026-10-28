// Country selection persists across every route; no cross-country records in scoped data.
const { chromium } = require('playwright');
const path = require('node:path');
(async()=>{
  const browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('file://'+path.resolve(process.argv[2]||'app/dist/bankterminal.html'));
  await page.waitForSelector('#global-land option[value="DE"]');
  const routes=['u-ueb','u-branche','u-vergleich','u-verzeichnis','u-termine','u-abschluesse','grp','quot','cmp','rank','mkt','ts','v-ueb','v-reihe','v-laender','v-quellen','v-prog','korr'];
  for(const country of ['DE','GB','CH','alle']){
    await page.selectOption('#global-land',country);
    for(const route of routes){
      await page.evaluate(route=>{location.hash=route;},route);await page.waitForTimeout(80);
      if(await page.inputValue('#global-land')!==country)throw Error('Country reset on '+route);
    }
    const ok=await page.evaluate(code=>code==='alle'||UNT.korr().firmen.every(f=>f.land_code===code),country);
    if(!ok)throw Error('Country leaked into scoped companies');
  }
  await page.evaluate(()=>{location.hash='u-abschluesse';});await page.waitForTimeout(100);
  const rows=await page.locator('#view table tbody tr').count();if(rows!==702)throw Error('Expected 702 companies, got '+rows);
  await browser.close();if(errors.length)throw Error(errors.join('\n'));
  console.log('18 routes × 4 country selections; 702 companies; no JavaScript errors');
})().catch(e=>{console.error(e);process.exit(1)});
