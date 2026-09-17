// Layout checks at every width, in dark and light mode, against a running instance.
// Usage: BASE=http://host:8008 node layout-checks.mjs [outdir] [stamp]
// Reports: boxes past the viewport, overlapping text or controls, horizontal scroll,
// off-centre elements that should be centred, text cut off by overflow, small touch targets.
import puppeteer from 'puppeteer-core';
const BASE = process.env.BASE ?? 'http://localhost:4173';
const [outDir, stamp] = process.argv.slice(2);
const WIDTHS = [390, 768, 900, 1024, 1280, 1440, 1920];
const ROUTES = [['home', '#/'], ['library', '#/library'], ['recent', '#/recent'], ['section', '#/section/water'], ['search', '#/search?q=tick'], ['volume', '#/volume/nhs-hypothermia?page=2'], ['digest', '#/digest'], ['chat', '#/chat'], ['chats', '#/chats'], ['profile', '#/profile'], ['welcome', '#/welcome'], ['demo', '#/demo/1']];
const browser = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
let failures = 0;
const report = (where, list) => { for (const line of list) { failures += 1; console.log(`FAIL  ${where}  ${line}`); } };

const measure = () => {
  const vw = window.innerWidth;
  const out = { overflow: [], overlap: [], cut: [], small: [], centre: [], hscroll: document.documentElement.scrollWidth > vw + 1 };
  const label = (el) => `${el.tagName.toLowerCase()}${el.className && typeof el.className === 'string' ? '.' + el.className.split(' ').slice(0, 2).join('.') : ''}:${(el.textContent || '').trim().slice(0, 24)}`;
  const visible = (el) => { const s = getComputedStyle(el); const r = el.getBoundingClientRect(); return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < window.innerHeight; };
  const els = [...document.querySelectorAll('button, a, input, select, h1, h2, h3, p, .card, .res, .chip, .pill, .bubble, .row, .modal')].filter(visible);
  for (const el of els) {
    const r = el.getBoundingClientRect();
    if (r.right > vw + 1 || r.left < -1) out.overflow.push(label(el));
    if (el.scrollWidth > el.clientWidth + 2 && getComputedStyle(el).overflowX === 'hidden' && !['H2', 'DIV'].includes(el.tagName)) out.cut.push(label(el));
    if (vw <= 768 && ['BUTTON', 'A', 'INPUT', 'SELECT'].includes(el.tagName) && !el.closest('.rail') && r.height < 28) out.small.push(label(el) + ` ${Math.round(r.height)}px`);
  }
  const controls = els.filter((el) => ['BUTTON', 'A', 'INPUT', 'SELECT', 'H1', 'H2', 'P'].includes(el.tagName) && !el.closest('.modal-backdrop'));
  for (let i = 0; i < controls.length; i++) for (let j = i + 1; j < controls.length; j++) {
    const a = controls[i], b = controls[j];
    if (a.contains(b) || b.contains(a)) continue;
    const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
    const x = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left), y = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
    if (x > 4 && y > 4 && !(a.closest('.bubble') && b.closest('.bubble')) && !(a.closest('.thumb') || b.closest('.thumb'))) out.overlap.push(`${label(a)} × ${label(b)}`);
  }
  const centred = [['.hero', '.main'], ['.ask-row', '.main'], ['.modal', 'body'], ['.wordmark', '.main']];
  for (const [sel, within] of centred) {
    const el = document.querySelector(sel), box = document.querySelector(within);
    if (!el || !box || !visible(el)) continue;
    const r = el.getBoundingClientRect(), c = box.getBoundingClientRect();
    const delta = Math.abs((r.left + r.right) / 2 - (c.left + c.right) / 2);
    if (delta > 2) out.centre.push(`${sel} off by ${Math.round(delta)}px within ${within}`);
  }
  return out;
};

for (const theme of ['dark', 'light']) {
  for (const width of WIDTHS) {
    const page = await browser.newPage();
    await page.evaluateOnNewDocument((tok) => { try { if (tok) localStorage.setItem('lifekit.token', tok); localStorage.setItem('lifekit.test', '1'); } catch {} }, process.env.TOKEN ?? '');
    await page.evaluateOnNewDocument((th) => { try { localStorage.setItem('lifekit.theme', th); localStorage.setItem('lifekit.welcomeDone', '1'); } catch {} }, theme);
    await page.setViewport({ width, height: 900, deviceScaleFactor: 1, isMobile: width < 900, hasTouch: width < 900 });
    for (const [name, route] of ROUTES) {
      try {
        await page.goto(`${BASE}/?w=${width}${route}`, { waitUntil: 'networkidle0', timeout: 60000 });
        await page.waitForFunction(() => !document.body.innerText.includes('Opening the library'), { timeout: 60000 });
        await wait(600);
      } catch (e) { report(`${theme} ${width} ${name}`, [`load: ${String(e).slice(0, 80)}`]); continue; }
      const m = await page.evaluate(measure);
      const where = `${theme} ${width} ${name}`;
      if (m.hscroll) report(where, ['horizontal scroll']);
      report(where, m.overflow.map((x) => `overflow ${x}`));
      report(where, m.overlap.map((x) => `overlap ${x}`));
      report(where, m.cut.map((x) => `cut off ${x}`));
      report(where, m.small.map((x) => `small target ${x}`));
      report(where, m.centre.map((x) => `off centre ${x}`));
      if (outDir) await page.screenshot({ path: `${outDir}/${stamp}_${theme}-${width}-${name}.png` });
    }
    await page.close();
  }
}
console.log(failures ? `${failures} findings` : 'PASS  no overflow, overlap, cut-off text, small targets, or off-centre elements at any width');
await browser.close();
