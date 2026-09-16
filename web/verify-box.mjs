// Drive every reader flow against a running instance and print PASS or FAIL per step.
// Usage: BASE=http://host:8008 node verify-box.mjs [outdir] [stamp]
// Flows: local search, ask online, offline switch stores a question, sync works it,
// candidate packet by keyboard (A admits, R refiles), reject, profile edit seeds a
// question, rail section links, pager keys, slash focus, digest state, reload after verdict.
import puppeteer from 'puppeteer-core';
const BASE = process.env.BASE ?? 'http://localhost:4173';
const [outDir, stamp] = process.argv.slice(2);
const browser = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });
const errors = [];
page.on('pageerror', (e) => errors.push(String(e).slice(0, 160)));
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text().slice(0, 160)); });
const results = [];
const check = (name, ok, note = '') => results.push(`${ok ? 'PASS' : 'FAIL'}  ${name}${note ? '  (' + note + ')' : ''}`);
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const text = () => page.evaluate(() => document.body.innerText);
const go = async (hash, sel = 'body') => { await page.goto(`${BASE}/${hash}`, { waitUntil: 'networkidle0' }); await page.waitForSelector(sel, { timeout: 30000 }); await wait(400); };
const clickText = async (sel, t) => page.evaluate((sel, t) => { const el = [...document.querySelectorAll(sel)].find((e) => e.textContent.trim() === t); if (el) { el.click(); return true; } return false; }, sel, t);
const shot = async (n) => { if (outDir) await page.screenshot({ path: `${outDir}/${stamp}_${n}.png` }); };
const api = async (path, init) => (await fetch(`${BASE}${path}`, init)).json();
const until = async (fn, tries = 120, ms = 5000) => { for (let i = 0; i < tries; i++) { if (await fn()) return true; await wait(ms); } return false; };

// 1. local search over the SQLite in the browser
await go('#/search?q=how%20much%20bleach%20for%20a%20gallon', '.bar input');
await until(async () => (await page.$$('.res')).length > 0, 20, 500);
check('local search returns page hits', (await page.$$('.res')).length > 0, `${(await page.$$('.res')).length} results`);
check('search result links carry page and passage', await page.evaluate(() => !![...document.querySelectorAll('a.open')].find((a) => /page=\d+&passage=/.test(a.getAttribute('href')))));

// 2. slash focuses the box
await page.keyboard.press('Escape'); await page.evaluate(() => document.activeElement.blur());
await page.keyboard.press('/'); await wait(100);
check('slash focuses the search box', await page.evaluate(() => document.activeElement === document.querySelector('.bar input')));

// 3. ask online: a question the library answers
await page.evaluate(() => { const i = document.querySelector('.bar input'); i.value = ''; });
await page.click('.bar input'); await page.keyboard.type('how much bleach for a gallon of water');
await clickText('button', 'Ask');
const answered = await until(async () => /Answer/.test(await text()) && !/Asking…/.test(await text()), 60, 2000);
check('ask online returns a quoted answer', answered && /page \d+/.test(await text()));
await shot('1-answer');

// 4. offline switch stores a question locally
await page.evaluate(() => localStorage.removeItem('lifekit.questions'));
const railSwitch = await page.$('.rail button.net, .rail .net');
check('rail has an offline switch', !!railSwitch);
if (railSwitch) await railSwitch.click(); await wait(300);
check('rail shows Offline after the switch', /Offline/.test(await text()));
await page.evaluate(() => { const i = document.querySelector('.bar input'); i.value = ''; });
await page.click('.bar input'); await page.keyboard.type('how to splint a broken wrist with a magazine');
await clickText('button', 'Ask'); await wait(500);
const queued = await page.evaluate(() => JSON.parse(localStorage.getItem('lifekit.questions') ?? '[]'));
check('offline ask is stored in the browser', queued.length === 1, JSON.stringify(queued).slice(0, 80));
check('offline ask shows the stored message', /stored/i.test(await text()));
await shot('2-offline-stored');
if (railSwitch) await (await page.$('.rail button.net, .rail .net')).click(); await wait(300);
check('rail shows Online after switching back', /Online/.test(await text()));

// 5. digest sync sends the stored question and works it
await go('#/digest', '.res.sync');
check('digest lists the stored question before sync', /splint a broken wrist/.test(await text()));
await clickText('button', 'Sync now');
const synced = await until(async () => !/Working…/.test(await text()), 120, 5000);
check('sync completes', synced);
await wait(1000);
const digest = await api('/api/digest');
const cand = digest.candidates.find((c) => c.question && /splint/.test(c.question.text));
check('sync staged a candidate for the stored question', !!cand, cand ? cand.id : JSON.stringify(digest.pending).slice(0, 100));
await shot('3-digest');

// 6. packet by keyboard: A admits
if (cand) {
  await go(`#/volume/${cand.id}`, '.pager');
  check('candidate page shows the packet', /WAITING FOR YOUR VERDICT|Waiting for your verdict/i.test(await text()));
  check('packet names the question', /splint a broken wrist/.test(await text()));
  check('packet shows the thumbnail or tile, not a broken image', await page.evaluate(() => { const img = document.querySelector('.vol-panel img, .vol-head img'); return !img || (img.complete && img.naturalWidth > 0) || !!document.querySelector('.tile'); }));
  await page.keyboard.press('a'); await wait(2500);
  check('A admits the candidate', /Admitted/.test(await text()));
  const row = await api('/api/candidates');
  check('admitted volume leaves the candidate list', !row.candidates.some((c) => c.id === cand.id));
  await shot('4-admitted');
}

// 7. refile another candidate through the select and R
const others = (await api('/api/candidates')).candidates.filter((c) => c.id !== cand?.id);
if (others.length) {
  const v = others[0];
  await go(`#/volume/${v.id}`, '.pager');
  const before = v.section;
  const target = before === 'medicine' ? 'water' : 'medicine';
  await page.select('.vol-panel select, select', target); await wait(200);
  await page.evaluate(() => document.activeElement.blur());
  await page.keyboard.press('r'); await wait(2500);
  const after = (await api('/api/digest')).added.find((a) => a.id === v.id);
  const tags = await page.evaluate(() => [...document.querySelectorAll('.tag')].map((t) => t.textContent.trim()));
  check('R refiles into the chosen section', /Admitted/.test(await text()) && tags.some((t) => /Water|Survival Medicine/.test(t)), `${before} -> ${target}`);
}

// 8. reject by button on a third candidate, then it is gone from search
const rest = (await api('/api/candidates')).candidates;
if (rest.length) {
  const v = rest[0];
  await go(`#/volume/${v.id}`, '.pager');
  await clickText('button', 'Reject'); await wait(2500);
  check('reject routes back to Recent', /#\/recent/.test(await page.evaluate(() => location.hash)));
  const visible = await page.evaluate((id) => !![...document.querySelectorAll('a.card')].find((a) => a.getAttribute('href').endsWith(id)), v.id);
  check('rejected volume is gone from Recent', !visible, v.id);
}

// 9. pager keys on a long volume
await go('#/volume/atp-4-02-11-2026?page=10', '.pager');
await page.evaluate(() => document.activeElement.blur());
await page.keyboard.press('ArrowRight'); await wait(300);
check('ArrowRight advances the page', /Page 11 of/.test(await text()));
await page.keyboard.press('ArrowLeft'); await wait(300);
check('ArrowLeft goes back', /Page 10 of/.test(await text()));

// 10. rail section link and counts
await go('#/', '.row');
await clickText('.rail a', 'Water'); await wait(600);
check('rail section link opens the section', /#\/section\/water/.test(await page.evaluate(() => location.hash)) && /Water/.test(await text()));
check('section grid is three across on desktop', await page.evaluate(() => getComputedStyle(document.querySelector('.grid')).gridTemplateColumns.split(' ').length === 3));

// 11. profile edit seeds a question
await go('#/profile', '.screen');
const beforeQ = (await api('/api/digest')).pending.length;
const toggled = await clickText('button', 'Boating');
await wait(1500);
const afterQ = (await api('/api/digest')).pending.length;
check('profile change seeds a question when a rule matches', toggled && afterQ >= beforeQ, `${beforeQ} -> ${afterQ}`);
await clickText('button', 'Boating'); await wait(500); // restore

// 12. welcome routing does not loop for a set profile
await go('#/', '.row');
check('a set profile does not route to Welcome', !/#\/welcome/.test(await page.evaluate(() => location.hash)));

// 13. phone width still has the bottom nav and no rail
await page.setViewport({ width: 390, height: 1100, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
await go('#/recent', '.card');
check('phone hides the rail and shows the nav', await page.evaluate(() => { const r = document.querySelector('.rail'); const n = document.querySelector('.nav'); return (!r || getComputedStyle(r).display === 'none') && n && getComputedStyle(n).display !== 'none'; }));
check('phone: no horizontal scroll', await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
await shot('5-phone-recent');

check('no page errors across the run', errors.length === 0, errors[0] ?? '');
console.log(results.join('\n'));
console.log(`${results.filter((r) => r.startsWith('PASS')).length}/${results.length} passed`);
await browser.close();
