// Screenshot routes at real device viewports. Usage: node shoot.mjs <outdir> <stamp>
import puppeteer from 'puppeteer-core';
const BASE = process.env.BASE ?? 'http://localhost:4173';
const [outDir, stamp] = process.argv.slice(2);
const browser = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const W = { phone: { width: 390, height: 1400, deviceScaleFactor: 2, isMobile: true, hasTouch: true }, tablet: { width: 768, height: 1400, deviceScaleFactor: 2 }, desktop: { width: 1280, height: 1400, deviceScaleFactor: 1 } };
const routes = [['home', '#/'], ['library', '#/library'], ['recent', '#/recent'], ['section-water', '#/section/water'], ['search', '#/search?q=how%20much%20bleach%20for%20a%20gallon'], ['volume', '#/volume/cdc-make-water-safe-emergency-2024?page=1'], ['digest', '#/digest']];
const shots = [];
for (const [wname, viewport] of Object.entries(W)) for (const [name, route] of routes) shots.push([`${name}-${wname}`, route, viewport]);
for (const [name, route, viewport] of shots) {
  const page = await browser.newPage();
  await page.setViewport(viewport);
  await page.goto(`${BASE}/${route}`, { waitUntil: 'networkidle0' });
  await page.waitForSelector('.wordmark, .card, .row, .res, .hint, .page, .chips, .input-row', { timeout: 15000 });
  await page.screenshot({ path: `${outDir}/${stamp}_${name}.png`, fullPage: false });
  await page.close();
}
await browser.close();
