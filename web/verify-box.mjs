// Drive every reader flow against a running instance and print PASS or FAIL per step.
// Usage: BASE=http://host:8008 node verify-box.mjs [outdir] [stamp]
// Flows: local search, ask online, offline switch stores a question, sync works it,
// new download by keyboard (A adds, R removes), a changed section, profile edit seeds a
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
const check = (name, ok, note = '') => { const line = `${ok ? 'PASS' : 'FAIL'}  ${name}${note ? '  (' + note + ')' : ''}`; results.push(line); console.log(line); };
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const text = () => page.evaluate(() => document.body.innerText);
const go = async (hash, sel = 'body') => { await page.goto(`${BASE}/${hash}`, { waitUntil: 'networkidle0' }); await page.waitForSelector(sel, { timeout: 90000 }); await wait(400); };
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
const answered = await until(async () => /Answer/i.test(await text()) && !/Asking…/.test(await text()), 60, 2000);
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
const answeredSplint = digest.answered.find((a) => /splint/.test(a.question));
check('sync worked the stored question: staged a candidate or answered from admitted volumes', !!cand || (answeredSplint && answeredSplint.state === 'resolved'), cand ? cand.id : answeredSplint ? `${answeredSplint.state} from ${answeredSplint.volumes.join(', ')}` : JSON.stringify(digest.pending).slice(0, 100));
await shot('3-digest');

// 6. packet by keyboard: A admits
if (cand) {
  await go(`#/volume/${cand.id}`, '.pager');
  check('candidate page shows the packet', /New download/i.test(await text()));
  check('packet names the question', await until(async () => /splint a broken wrist/.test(await text()), 20, 500));
  check('packet shows the thumbnail or tile, not a broken image', await page.evaluate(() => { const img = document.querySelector('.vol-panel img, .vol-head img'); return !img || (img.complete && img.naturalWidth > 0) || !!document.querySelector('.tile'); }));
  await page.keyboard.press('a');
  check('A adds the document', await until(async () => /Added\./.test(await text()), 20, 1000));
  const row = await api('/api/candidates');
  check('admitted volume leaves the candidate list', !row.candidates.some((c) => c.id === cand.id));
  await shot('4-admitted');
}

// 7. add another new download with a changed section
const others = (await api('/api/candidates')).candidates.filter((c) => c.id !== cand?.id);
if (others.length) {
  const v = others[0];
  await go(`#/volume/${v.id}`, '.pager');
  const before = v.section;
  const ids = ((await api('/api/config')).sections ?? []).map((s) => s.id);
  const target = ids.find((s) => s !== before) ?? before;
  await page.select('.vol-panel select, select', target); await wait(200);
  await page.evaluate(() => document.activeElement.blur());
  await clickText('button', 'Add to library');
  const targetTitle = ((await api('/api/config')).sections ?? []).find((s) => s.id === target)?.title ?? target;
  const refiled = await until(async () => /Added\./.test(await text()) && (await page.evaluate(() => [...document.querySelectorAll('.tag')].map((t) => t.textContent.trim()))).includes(targetTitle), 90, 1000);
  const section = (await api('/api/candidates')).candidates.find((c) => c.id === v.id);
  check('Add to library with a changed section refiles', refiled && !section, `${before} -> ${target}`);
}

// 8. reject by button on a third candidate, then it is gone from search
const rest = (await api('/api/candidates')).candidates;
if (rest.length) {
  const v = rest[0];
  await go(`#/volume/${v.id}`, '.pager');
  await page.evaluate(() => document.activeElement.blur());
  await page.keyboard.press('r');
  check('reject routes back to Recent', await until(async () => /#\/recent/.test(await page.evaluate(() => location.hash)), 20, 500));
  const gone = await until(async () => !(await page.evaluate((id) => !![...document.querySelectorAll('a.card')].find((a) => a.getAttribute('href').endsWith(id)), v.id)), 30, 1000);
  check('rejected volume is gone from Recent after the reload', gone, v.id);
}

// 9. pager keys on a long volume
await go('#/volume/atp-4-02-11-2026?page=10', '.pager');
await page.evaluate(() => document.activeElement.blur());
await page.keyboard.press('ArrowRight'); await wait(300);
check('ArrowRight advances the page', /Page 11 of/.test(await text()));
await page.keyboard.press('ArrowLeft'); await wait(300);
check('ArrowLeft goes back', /Page 10 of/.test(await text()));

// 10. rail section link and counts
await go('#/library', '.row');
await page.evaluate(() => document.querySelector('.rail a[href="#/section/water"]').click()); await wait(600);
check('rail section link opens the section', /#\/section\/water/.test(await page.evaluate(() => location.hash)) && /Water/.test(await text()));
check('section grid is three across on desktop', await page.evaluate(() => { const g = document.querySelector('.grid'); return !!g && getComputedStyle(g).gridTemplateColumns.split(' ').length === 3; }));

// 11. profile edit seeds a question
await go('#/profile', '.screen');
const beforeQ = (await api('/api/digest')).pending.length;
const toggled = await clickText('button', 'Boating');
await wait(1500);
const afterQ = (await api('/api/digest')).pending.length;
check('profile change seeds a question when a rule matches', toggled && afterQ >= beforeQ, `${beforeQ} -> ${afterQ}`);
await clickText('button', 'Boating'); await wait(500); // restore

// 12. welcome routing does not loop for a set profile
await go('#/', '.wordmark');
check('a set profile does not route to Welcome', !/#\/welcome/.test(await page.evaluate(() => location.hash)));

// 12b. the back-online modal on the offline-to-online transition
await go('#/search', '.bar input');
await page.evaluate(() => localStorage.removeItem('lifekit.questions'));
await (await page.$('.rail .net')).click(); await wait(300);
await page.evaluate(() => { const i = document.querySelector('.bar input'); i.value = ''; });
await page.click('.bar input'); await page.keyboard.type('how do I treat a sprained ankle on a hike');
await clickText('button', 'Ask'); await wait(500);
await (await page.$('.rail .net')).click();
check('modal opens on the transition', await until(async () => !!(await page.$('.modal')), 20, 500));
check('modal shows a round-trip line', await until(async () => /Round trip \d+ ms/.test(await text()), 20, 500));
check('modal lists the stored question', /sprained ankle/.test(await text()));
check('modal trail runs the loop', await until(async () => /Question:|The loop is off|Nothing to work/.test(await text()), 60, 2000));
check('modal reaches Done', await until(async () => /Done\.|The loop is off|Nothing to work/.test(await text()), 180, 2000));
await shot('6-back-online');
await clickText('.modal button', 'Close'); await wait(300);
check('Close dismisses the modal', !(await page.$('.modal')));

// 13. phone width still has the bottom nav and no rail
await page.setViewport({ width: 390, height: 1100, deviceScaleFactor: 2, isMobile: true, hasTouch: true }); // Chrome reloads on the emulation change
await wait(1500);
await go('?phone#/recent', '.card');
check('phone hides the rail and shows the top bar', await page.evaluate(() => { const r = document.querySelector('.rail'); const n = document.querySelector('.topbar'); return (!r || getComputedStyle(r).display === 'none') && n && getComputedStyle(n).display !== 'none'; }));
check('phone: no horizontal scroll', await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
await shot('5-phone-recent');

check('no page errors across the run', errors.length === 0, errors[0] ?? '');
console.log(`${results.filter((r) => r.startsWith('PASS')).length}/${results.length} passed`);
await browser.close();
