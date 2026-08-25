// Edge cases through the built app in a real Chrome. Prints one line per case: PASS or FAIL
// with what was observed. Usage: node edgecases.mjs
import puppeteer from 'puppeteer-core';
const browser = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const page = await browser.newPage();
await page.setViewport({ width: 390, height: 1100, deviceScaleFactor: 1, isMobile: true });
const errors = [];
page.on('pageerror', (e) => errors.push(String(e).slice(0, 160)));
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text().slice(0, 160)); });
const results = [];
const check = (name, ok, note = '') => results.push(`${ok ? 'PASS' : 'FAIL'}  ${name}${note ? '  (' + note + ')' : ''}`);
const go = async (hash, sel = 'body') => { await page.goto(`http://localhost:4173/${hash}`, { waitUntil: 'networkidle0' }); await page.waitForSelector(sel, { timeout: 20000 }); await new Promise((r) => setTimeout(r, 300)); };
const noHScroll = async () => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);

await go('#/', '.row');
check('directory renders twelve rows', (await page.$$eval('.row', (e) => e.length)) === 12);
check('directory: no horizontal scroll', await noHScroll());

await go('#/search', '.bar input');
check('empty search shows no result groups', (await page.$$eval('.group', (e) => e.length)) === 0);
await page.type('.bar input', 'qwxzvbn plkjhgf');
await new Promise((r) => setTimeout(r, 400));
const noRes = await page.$$eval('.hint', (els) => els.map((e) => e.textContent).join(' | ')).catch(() => '');
check('nonsense query shows the stored-for-later hint', /Nothing in the library/.test(noRes), noRes.slice(0, 50));

await go('#/search?q=%22%3B%20DROP%20TABLE%20volume%3B--', 'body');
check('punctuation query does not break the page', errors.length === 0, errors.join(' | ').slice(0, 120));

await go('#/search?q=tick', '.res');
const tickHits = await page.$$eval('.res', (e) => e.length);
check('one-word query returns results', tickHits > 0, `${tickHits} cards`);

await go('#/search?q=how%20much%20bleach%20for%20a%20gallon%20of%20water', '.res');
const openLinks = await page.$$eval('.res .open', (e) => e.map((a) => a.getAttribute('href')));
check('page links carry page and passage', openLinks.some((h) => /page=\d+&passage=/.test(h)), openLinks[0]);

await go('#/section/nonexistent', 'body');
check('unknown section does not throw', errors.length === 0, errors.join(' | ').slice(0, 120));

await go('#/recent', '.card');
const before = await page.$$eval('.card', (e) => e.length);
await page.evaluate(() => [...document.querySelectorAll('.chip')].find((c) => c.textContent.startsWith('Pages')).click());
await new Promise((r) => setTimeout(r, 300));
const firstPages = await page.$eval('.card .foot', (e) => parseInt(e.textContent));
check('sort by pages puts the longest volume first', firstPages >= 500, `${firstPages} pages first`);
await page.evaluate(() => [...document.querySelectorAll('.chip')].find((c) => c.textContent.startsWith('A to Z')).click());
await new Promise((r) => setTimeout(r, 300));
const titles = await page.$$eval('.card h2', (e) => e.slice(0, 3).map((h) => h.textContent));
check('A to Z sorts titles', titles.join('') === [...titles].sort((a, b) => a.localeCompare(b)).join(''), titles.map((t) => t.slice(0, 12)).join(', '));
await page.evaluate(() => [...document.querySelectorAll('.chip')].find((c) => c.textContent.startsWith('NHS')).click());
await new Promise((r) => setTimeout(r, 300));
const nhsCount = await page.$$eval('.card', (e) => e.length);
check('publisher filter narrows the list', nhsCount > 0 && nhsCount < before, `${before} -> ${nhsCount}`);
check('recent: no horizontal scroll', await noHScroll());

await go('#/volume/fm-3-05-70-2002?page=600', '.page');
const pager = await page.$eval('.pager span', (e) => e.textContent);
check('676-page volume opens at page 600', /Page 600 of 676/.test(pager), pager);
await page.click('.pager .chip:last-child');
await new Promise((r) => setTimeout(r, 200));
check('pager advances', /Page 601/.test(await page.$eval('.pager span', (e) => e.textContent)));

await go('#/volume/nhs-hypothermia?page=99', 'body');
const outOfRange = await page.$('.page');
check('out-of-range page shows no page body', outOfRange === null);

await go('#/volume/does-not-exist', 'body');
check('missing volume shows the not-in-library screen', (await page.$eval('h1', (e) => e.textContent)).includes('Not in the library'));

const longTitle = await page.evaluate(async () => { location.hash = '#/recent'; await new Promise((r) => setTimeout(r, 600)); return [...document.querySelectorAll('.card h2')].map((h) => h.textContent.length); });
check('card titles clamp under 66 characters', Math.max(...longTitle) <= 66, `max ${Math.max(...longTitle)}`);

await go('#/digest', '.screen');
check('digest renders online', (await page.$('.res.sync')) !== null);

check('no page errors across the run', errors.length === 0, errors.join(' | ').slice(0, 200));
console.log(results.join('\n'));
await browser.close();
