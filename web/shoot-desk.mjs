import puppeteer from 'puppeteer-core';
const BASE = process.env.BASE ?? 'http://localhost:4173';
const [outDir, stamp] = process.argv.slice(2);
const browser = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const V = { desktop: { width: 1440, height: 900, deviceScaleFactor: 1 }, break: { width: 900, height: 900, deviceScaleFactor: 1 }, phone: { width: 390, height: 1400, deviceScaleFactor: 2, isMobile: true, hasTouch: true } };
const routes = [['home', '#/'], ['library', '#/library'], ['recent', '#/recent'], ['section-water', '#/section/water'], ['search', '#/search?q=how%20much%20bleach%20for%20a%20gallon'], ['volume', '#/volume/wikipedia-bee-sting?page=2'], ['digest', '#/digest'], ['profile', '#/profile'], ['welcome', '#/welcome']];
const errors = [];
for (const [vn, vp] of Object.entries(V)) for (const [name, route] of routes) {
  const page = await browser.newPage();
await page.evaluateOnNewDocument((tok) => { try { if (tok) localStorage.setItem('lifekit.token', tok); localStorage.setItem('lifekit.test', '1'); } catch {} }, process.env.TOKEN ?? '');
  page.on('pageerror', (e) => errors.push(`${vn}/${name}: ${String(e).slice(0, 160)}`));
  await page.setViewport(vp);
  try { localStorage.setItem('lifekit.welcomeDone', '1'); } catch {}
  await page.goto(`${BASE}/${route}`, { waitUntil: 'networkidle0' });
  await page.evaluate(() => { try { localStorage.setItem('lifekit.welcomeDone', '1'); } catch {} });
  await new Promise((r) => setTimeout(r, 900));
  await page.screenshot({ path: `${outDir}/${stamp}_${name}-${vn}.png`, fullPage: false });
  await page.close();
}
console.log('errors:', errors.length ? errors.join('\n') : 'none');
await browser.close();
