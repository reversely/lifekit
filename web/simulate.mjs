// Simulate the online/offline loop in a real Chrome. Usage: node simulate.mjs <outdir> <stamp>
// 1. Offline: ask a question the library cannot answer; it is stored in the browser.
// 2. Online: open the digest, sync; the stored question is sent, worked, and answered.
import puppeteer from 'puppeteer-core';
const [outDir, stamp] = process.argv.slice(2);
const question = process.argv[4] ?? 'how long does a bee sting hurt';
const browser = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const page = await browser.newPage();
await page.setViewport({ width: 390, height: 1100, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
page.on('pageerror', (e) => console.log('pageerror:', String(e).slice(0, 200)));

// warm the app while online so the SQLite file and wasm are loaded
await page.goto('http://localhost:4173/#/search', { waitUntil: 'networkidle0' });
await page.waitForSelector('.bar input');

// 1. offline
await page.setOfflineMode(true);
await page.evaluate(() => window.dispatchEvent(new Event('offline')));
await new Promise((r) => setTimeout(r, 300));
const state1 = await page.evaluate(() => navigator.onLine);
await page.type('.bar input', question);
await page.click('.chip.ask');
await page.waitForSelector('.res', { timeout: 10000 });
const storedText = await page.$eval('.res p', (el) => el.textContent);
const queued = await page.evaluate(() => JSON.parse(localStorage.getItem('lifekit.questions') || '[]').length);
console.log(`offline: navigator.onLine=${state1}; stored="${storedText.slice(0, 60)}"; localStorage queue=${queued}`);
await page.screenshot({ path: `${outDir}/${stamp}_sim-1-offline-stored.png` });

// search still works offline (the index is local)
await page.evaluate(() => { location.hash = '#/search?q=signs%20of%20hypothermia'; });
await page.waitForSelector('.res', { timeout: 10000 });
const offlineHits = await page.$$eval('.res', (els) => els.length);
console.log(`offline: local search returned ${offlineHits} result cards`);
await page.screenshot({ path: `${outDir}/${stamp}_sim-2-offline-search.png` });

// 2. online again
await page.setOfflineMode(false);
await page.evaluate(() => window.dispatchEvent(new Event('online')));
await page.evaluate(() => { location.hash = '#/digest'; });
await page.waitForSelector('.res.sync', { timeout: 10000 });
await page.screenshot({ path: `${outDir}/${stamp}_sim-3-online-pending.png` });
await page.click('.res.sync');
await page.waitForFunction(() => document.querySelector('.res.sync') && !document.querySelector('.res.sync').disabled, { timeout: 300000 });
await new Promise((r) => setTimeout(r, 500));
const status = await page.$eval('.hint', (el) => el.textContent).catch(() => '');
const answered = await page.$$eval('.group', (els) => els.map((e) => e.textContent));
console.log(`online: sync status="${status.slice(0, 160)}"; groups=${JSON.stringify(answered)}`);
const queuedAfter = await page.evaluate(() => JSON.parse(localStorage.getItem('lifekit.questions') || '[]').length);
console.log(`online: localStorage queue after sync=${queuedAfter}`);
await page.screenshot({ path: `${outDir}/${stamp}_sim-4-online-digest.png`, fullPage: false });
await browser.close();
