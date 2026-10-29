// Country selection persists across every route; no cross-country records in scoped data.
const { chromium } = require('playwright');
const path = require('node:path');
(async()=>{
  const browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push((e.stack||e.message)+' ['+page.url().split('#')[1]+']'));
  await page.goto('file://'+path.resolve(process.argv[2]||'app/dist/bankterminal.html'));
  await page.waitForSelector('#global-land option[value="DE"]',{state:'attached'});
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
  const profiles=await page.evaluate(()=>['EUR','CHF'].map(currency=>UNT.unternehmenAlle().find(f=>(f.abschluesse||[]).some(a=>a.waehrung===currency))).filter(Boolean).map(f=>({id:f.id,currency:f.abschluesse[0].waehrung})));
  for(const profile of profiles){
    await page.evaluate(id=>{location.hash='firma-'+id;},profile.id);await page.waitForTimeout(100);
    const body=await page.locator('#view').innerText();if(!body.toLowerCase().includes('originalposten')||!body.includes(profile.currency))throw Error('Missing original statement/currency '+JSON.stringify(profile)+' '+body.slice(-1000)+' ERRORS: '+errors.join('\n'));
  }
  await browser.close();if(errors.length)throw Error(errors.join('\n'));
  console.log('18 routes × 4 country selections; 702 companies; original statement profiles; no JavaScript errors');
})().catch(e=>{console.error(e);process.exit(1)});
