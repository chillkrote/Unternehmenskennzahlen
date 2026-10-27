// Usage: node exp.js <template-search> <template-exact> <refdate|ALL> <outfile>
const { open } = require('./lib.js');
const { pick } = require('./s4.js');
const [,, tsearch, texact, ref, out, col] = process.argv;
(async () => {
  const { b, p, fr } = await open();
  await pick(p, fr(), 1396, 677, tsearch, texact);
  if (ref !== 'ALL') await pick(p, fr(), 488, 676, ref);
  await p.mouse.click(1725, 662); await p.waitForTimeout(20000);
  if (col) await pick(p, fr(), 1290, 197, col);
  await p.mouse.click(290, 186); await p.waitForTimeout(4000);
  await p.mouse.click(396, 257); await p.waitForTimeout(3000);
  for (let i = 0; i < 8; i++) {
    const g = fr().locator('.slicerItemContainer:visible', { hasText: 'Germany' });
    if (await g.count()) { await g.first().click(); break; }
    await p.mouse.move(395, 420); await p.mouse.wheel(0, 100); await p.waitForTimeout(1500);
  }
  await p.waitForTimeout(3000); await p.mouse.click(400, 190); await p.waitForTimeout(2000);
  await p.screenshot({ path: 'e1.png' });
  await p.mouse.click(562, 157); await p.waitForTimeout(15000);
  await p.mouse.move(1200, 500); await p.waitForTimeout(1500);
  await p.screenshot({ path: 'e2.png' });
  await p.mouse.click(1766, 262); await p.waitForTimeout(3000);
  await p.screenshot({ path: 'e3.png' });
  const f = fr();
  const ex = f.getByText('Export data', { exact: true });
  console.log('export items', await ex.count());
  await ex.first().click(); await p.waitForTimeout(5000);
  await p.screenshot({ path: 'e4.png' });
  const txt = await f.locator('[role=dialog]:visible, .pbi-modal:visible, mat-dialog-container:visible').allInnerTexts();
  console.log(txt);
  const sum = f.getByText('Summarized data', { exact: false });
  if (await sum.count()) await sum.first().click();
  await p.waitForTimeout(2000);
  await p.screenshot({ path: 'e5.png' });
  const dl = p.waitForEvent('download', { timeout: 240000 });
  await f.getByRole('button', { name: 'Export' }).last().click();
  const d = await dl; await d.saveAs(out);
  console.log('saved', out);
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
