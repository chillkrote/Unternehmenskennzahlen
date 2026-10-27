const { chromium } = require('playwright');
exports.open = async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1800, height: 1100 }, acceptDownloads: true });
  const p = await ctx.newPage();
  await p.goto('https://edap-public.eba.europa.eu/Report/index/MTE2', { waitUntil: 'load', timeout: 120000 });
  for (let i = 0; i < 60; i++) {
    const f = p.frames().find(f => f.url().includes('powerbi'));
    if (f && (await f.$$('.slicer-dropdown-menu')).length >= 4) break;
    await p.waitForTimeout(2000);
  }
  await p.waitForTimeout(3000);
  return { b, p, fr: () => p.frames().find(f => f.url().includes('powerbi')) };
};
