const { open } = require('./lib.js');
async function pick(p, f, x, y, text, exact) {
  await p.mouse.click(x, y); await p.waitForTimeout(3000);
  const vis = f.locator('input.searchInput:visible');
  if (await vis.count()) { await vis.first().click(); await vis.first().pressSequentially(text, { delay: 80 }); await p.waitForTimeout(4000); }
  const it = f.locator('.slicerItemContainer:visible', { hasText: exact || text });
  console.log('items', await it.allInnerTexts());
  await it.first().click(); await p.waitForTimeout(3000);
  await p.keyboard.press('Escape'); await p.waitForTimeout(1500);
}
exports.pick = pick;
if (require.main === module) (async () => {
  const { b, p, fr } = await open();
  const f = fr();
  await pick(p, f, 1396, 677, 'CC2', 'K_66.02');
  await pick(p, f, 488, 676, '31/12/2025');
  await p.screenshot({ path: 'sel.png' });
  await p.mouse.click(1725, 662); await p.waitForTimeout(20000);
  await p.screenshot({ path: 'rep.png' });
  const t = await fr().$$eval('.slicer-header-text, h3, .visualTitle', e => e.map(x => x.innerText.trim()));
  console.log(t);
  await b.close();
})();
