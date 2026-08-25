// Accessibility scan with axe-core over the main routes. Prints violations by impact.
import puppeteer from 'puppeteer-core';
import fs from 'fs';
const axe = fs.readFileSync('node_modules/axe-core/axe.min.js', 'utf8');
const browser = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const page = await browser.newPage();
await page.setViewport({ width: 390, height: 1100 });
const routes = ['#/', '#/recent', '#/section/water', '#/search?q=tick', '#/volume/nhs-hypothermia?page=2', '#/digest'];
for (const r of routes) {
  await page.goto(`http://localhost:4173/${r}`, { waitUntil: 'networkidle0' });
  await page.waitForSelector('.row, .card, .res, .page, .res.sync', { timeout: 20000 });
  await page.evaluate(axe);
  const result = await page.evaluate(async () => await axe.run(document, { runOnly: ['wcag2a', 'wcag2aa'] }));
  const lines = result.violations.map((v) => `${v.impact}: ${v.id} (${v.nodes.length}) ${v.help}`);
  console.log(`${r}: ${result.violations.length} violation types${lines.length ? '\n  ' + lines.join('\n  ') : ''}`);
}
await browser.close();
