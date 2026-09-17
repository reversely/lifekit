// Accessibility scan with axe-core over the main routes. Prints violations by impact.
import puppeteer from 'puppeteer-core';
import fs from 'fs';
const BASE = process.env.BASE ?? 'http://localhost:4173';
const axe = fs.readFileSync('node_modules/axe-core/axe.min.js', 'utf8');
const browser = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const page = await browser.newPage();
await page.evaluateOnNewDocument((tok) => { try { if (tok) localStorage.setItem('lifekit.token', tok); localStorage.setItem('lifekit.test', '1'); } catch {} }, process.env.TOKEN ?? '');
const THEME = process.env.THEME;
if (THEME) await page.evaluateOnNewDocument((th) => { try { localStorage.setItem('lifekit.theme', th); } catch {} }, THEME);
await page.setViewport({ width: 390, height: 1100 });
const routes = ['#/', '#/library', '#/recent', '#/section/water', '#/search?q=tick', '#/volume/nhs-hypothermia?page=2', '#/digest'];
for (const r of routes) {
  await page.goto(`${BASE}/${r}`, { waitUntil: 'networkidle0' });
  await page.waitForSelector('.wordmark, .row, .card, .res, .page, .res.sync, .chips, .input-row', { timeout: 20000 });
  await page.evaluate(axe);
  const result = await page.evaluate(async () => await axe.run(document, { runOnly: ['wcag2a', 'wcag2aa'] }));
  const lines = result.violations.map((v) => `${v.impact}: ${v.id} (${v.nodes.length}) ${v.help}`);
  console.log(`${r}: ${result.violations.length} violation types${lines.length ? '\n  ' + lines.join('\n  ') : ''}`);
}
await browser.close();
