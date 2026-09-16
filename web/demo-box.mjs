// Drive the box instance through onboarding, sync, and a verdict; screenshot each station.
import puppeteer from 'puppeteer-core';
const B = 'http://100.97.186.57:8008';
const [outDir, stamp] = process.argv.slice(2);
const browser = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const page = await browser.newPage();
await page.setViewport({ width: 390, height: 1100, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
page.on('pageerror', (e) => console.log('pageerror:', String(e).slice(0, 200)));
const shot = (n) => page.screenshot({ path: `${outDir}/${stamp}_${n}.png`, fullPage: false });
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const clickText = async (sel, text) => {
  const ok = await page.evaluate((sel, text) => { const el = [...document.querySelectorAll(sel)].find((e) => e.textContent.trim() === text); if (el) { el.click(); return true; } return false; }, sel, text);
  if (!ok) console.log('missing:', text);
  await wait(400);
};
await page.goto(`${B}/#/`, { waitUntil: 'networkidle0' });
await wait(1500);
console.log('start route:', await page.evaluate(() => location.hash));
if (!(await page.evaluate(() => location.hash)).includes('welcome')) await page.goto(`${B}/#/welcome`, { waitUntil: 'networkidle0' });
await wait(800); await shot('1-welcome');
await clickText('button', 'United States'); await clickText('button', 'Next'); await wait(800);
await clickText('button', 'Washington'); await clickText('button', 'Next');
await clickText('button', 'Forest'); await clickText('button', 'Mountains'); await shot('2-terrain'); await clickText('button', 'Next');
await clickText('button', 'Hiking'); await clickText('button', 'Camping'); await clickText('button', 'Next');
await clickText('button', 'Children'); await clickText('button', 'Next');
await clickText('button', 'Next'); await wait(1200); await shot('3-what-it-looks-for');
console.log('final text:', (await page.evaluate(() => document.body.innerText)).slice(0, 600).replace(/\n+/g, ' | '));
await clickText('button', 'Start'); 
for (let i = 0; i < 60; i++) { await wait(5000); const t = await page.evaluate(() => document.body.innerText); if (!/Working|Finding sources|Sending|Looking/.test(t)) break; }
await wait(1500); await shot('4-digest');
console.log('digest:', (await page.evaluate(() => document.body.innerText)).slice(0, 900).replace(/\n+/g, ' | '));
const href = await page.evaluate(() => { const a = [...document.querySelectorAll('a')].find((x) => x.textContent.trim() === 'Open'); return a && a.getAttribute('href'); });
console.log('first candidate:', href);
if (href) {
  await page.goto(`${B}/${href}`, { waitUntil: 'networkidle0' }); await wait(1200); await shot('5-packet');
  console.log('packet:', (await page.evaluate(() => document.body.innerText)).slice(0, 700).replace(/\n+/g, ' | '));
  await clickText('button', 'Add to library'); await wait(2500); await shot('6-admitted');
}
await page.goto(`${B}/#/recent`, { waitUntil: 'networkidle0' }); await wait(1200); await shot('7-recent');
await page.goto(`${B}/#/`, { waitUntil: 'networkidle0' }); await wait(1200); await shot('8-library');
await browser.close();
