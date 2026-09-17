// Checks for the three.js scene behind desktop screens (docs/content/biome-scene.md).
// Usage: BASE=http://host:port node scene-checks.mjs [outdir] [stamp]
import puppeteer from 'puppeteer-core';
const BASE = process.env.BASE ?? 'http://localhost:4173';
const [outDir, stamp] = process.argv.slice(2);
const browser = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true, args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const out = [];
const check = (name, ok, note = '') => { const line = `${ok ? 'PASS' : 'FAIL'}  ${name}${note ? '  (' + note + ')' : ''}`; out.push(line); console.log(line); };
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const errors = [];

async function open(viewport, route, opts = {}) {
  const page = await browser.newPage();
await page.evaluateOnNewDocument((tok) => { try { if (tok) localStorage.setItem('lifekit.token', tok); localStorage.setItem('lifekit.test', '1'); } catch {} }, process.env.TOKEN ?? '');
  await page.setViewport(viewport);
  page.on('pageerror', (e) => errors.push(String(e).slice(0, 160)));
  if (opts.reducedMotion) await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
  await page.evaluateOnNewDocument(() => { try { localStorage.setItem('lifekit.welcomeDone', '1'); } catch {} });
  if (opts.theme) await page.evaluateOnNewDocument((t) => { try { localStorage.setItem('lifekit.theme', t); } catch {} }, opts.theme);
  const requests = [];
  page.on('request', (r) => requests.push(r.url()));
  await page.goto(`${BASE}/${route}`, { waitUntil: 'networkidle0' });
  await wait(1500);
  return { page, requests };
}
const frames = (page) => page.evaluate(() => Number(document.querySelector('canvas[data-scene="three"]')?.dataset.frames ?? -1));
const hasScene = (page) => page.evaluate(() => !!document.querySelector('canvas[data-scene="three"]'));
// The applied top colour, written to data-tint by the scene; the drawing buffer itself is
// not preserved after compositing, so a pixel read would return zeros.
const tint = async (page) => page.evaluate(() => {
  const hex = document.querySelector('canvas[data-scene="three"]')?.dataset.tint ?? '#000000';
  return [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
});
const shot = async (page, name) => { if (outDir) await page.screenshot({ path: `${outDir}/${stamp}_scene-${name}.png` }); };

const desktop = { width: 1440, height: 900 };
for (const [name, route] of [['home', '#/'], ['digest', '#/digest'], ['section', '#/section/water'], ['volume', '#/volume/nhs-hypothermia?page=2']]) {
  const { page } = await open(desktop, route, { theme: 'dark' });
  check(`scene canvas present on ${name}`, await hasScene(page));
  if (name === 'home') await shot(page, 'home');
  if (name === 'volume') await shot(page, 'volume');
  await page.close();
}

// Rendering happens on scroll and stops when idle; the once-per-second firefly frame is allowed.
{
  const { page } = await open(desktop, '#/recent');
  await wait(1200);
  const before = await frames(page);
  await page.evaluate(() => window.scrollTo(0, 600)); await wait(200);
  await page.evaluate(() => window.scrollTo(0, 1200)); await wait(200);
  const after = await frames(page);
  check('frame counter advances on scroll', after > before, `${before} -> ${after}`);
  const idle1 = await frames(page); await wait(2600); const idle2 = await frames(page);
  check('at most three frames in 2.6 s while idle (the once-per-second firefly frame)', idle2 - idle1 <= 3, `${idle1} -> ${idle2}`);
  await page.close();
}

// Reduced motion: one render, then no more without scroll.
{
  const { page } = await open(desktop, '#/recent', { reducedMotion: true });
  const a = await frames(page); await wait(2500); const b = await frames(page);
  check('reduced motion renders once and holds', a >= 1 && b === a, `${a} -> ${b}`);
  await page.close();
}

// Phones request no three.js chunk.
{
  const { page, requests } = await open({ width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true }, '#/');
  check('no scene canvas at phone width', !(await hasScene(page)));
  check('no three.js chunk requested at phone width', !requests.some((u) => /Scene-|three/.test(u)), requests.filter((u) => /Scene-|three/.test(u)).join(' ').slice(0, 80));
  await page.close();
}

// The tint differs between two sections in dark mode; light mode uses the paper field for every section.
{
  const water = await open(desktop, '#/section/water', { theme: 'dark' }); await wait(1200);
  const pw = await tint(water.page);
  await shot(water.page, 'section-water'); await water.page.close();
  const hazards = await open(desktop, '#/section/hazards', { theme: 'dark' }); await wait(1200);
  const ph = await tint(hazards.page);
  await shot(hazards.page, 'section-hazards'); await hazards.page.close();
  const diff = pw.map((v, i) => Math.abs(v - ph[i])).reduce((a, b) => a + b, 0);
  check('background tint differs between water and hazards', diff >= 6, `${pw.join(',')} vs ${ph.join(',')}`);
}

// Light mode renders the scene with a paper background.
{
  const { page } = await open(desktop, '#/', { theme: 'light' }); await wait(1200);
  const p = await tint(page);
  check('light mode renders a light background', await hasScene(page) && p[0] > 180 && p[1] > 180 && p[2] > 180, p.join(','));
  await shot(page, 'home-light');
  await page.close();
}

check('no page errors', errors.length === 0, errors[0] ?? '');
console.log(`${out.filter((l) => l.startsWith('PASS')).length}/${out.length} passed`);
await browser.close();
