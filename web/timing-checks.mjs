// Load and execution time against a running instance, with budgets.
// Usage: BASE=http://host:8008 TOKEN=... node timing-checks.mjs
import puppeteer from 'puppeteer-core';
const BASE = process.env.BASE ?? 'http://localhost:4173';
const TOKEN = process.env.TOKEN ?? '';
const H = TOKEN ? { 'X-LifeKit-Token': TOKEN } : {};
const budgets = { firstPaintMs: 3000, firstCardMs: 15000, dbBytes: 120_000_000, dbMs: 20000, apiMs: 1500, chatMs: 30000, verdictMs: 3000, retrievalMs: 120000 };
let failures = 0;
const say = (name, value, budget, unit = 'ms') => { const ok = value <= budget; if (!ok) failures += 1; console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}  ${Math.round(value)} ${unit} (budget ${budget})`); };
const time = async (fn) => { const t = performance.now(); const r = await fn(); return [performance.now() - t, r]; };

const [dbMs, dbRes] = await time(() => fetch(`${BASE}/library.sqlite`, { headers: H }));
const dbBytes = Number(dbRes.headers.get('content-length') ?? (await dbRes.arrayBuffer()).byteLength);
say('database download', dbMs, budgets.dbMs); say('database size', dbBytes, budgets.dbBytes, 'bytes');
for (const path of ['/api/health', '/api/config', '/api/digest', '/api/candidates', '/api/events?since=0', '/api/profile', '/api/search?q=tick']) {
  const [ms] = await time(() => fetch(`${BASE}${path}`, { headers: H })); say(`GET ${path}`, ms, budgets.apiMs);
}
const [chatMs] = await time(() => fetch(`${BASE}/api/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json', ...H }, body: JSON.stringify({ question: 'how much bleach for a gallon of water', history: [] }) }));
say('chat reply', chatMs, budgets.chatMs);

const browser = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
for (const width of [390, 1440]) {
  const page = await browser.newPage();
  await page.setViewport({ width, height: 900, isMobile: width < 900 });
  for (const [name, route, sel] of [['home', '#/', '.wordmark'], ['recent', '#/recent', '.card'], ['digest', '#/digest', '.screen'], ['chat', '#/chat', '.input-row input']]) {
    const t0 = performance.now();
    await page.goto(`${BASE}/?t=${width}${route}`, { waitUntil: 'domcontentloaded' });
    const paint = await page.evaluate(() => performance.getEntriesByType('paint').find((e) => e.name === 'first-contentful-paint')?.startTime ?? 0);
    say(`${width} ${name} first paint`, paint, budgets.firstPaintMs);
    try { await page.waitForSelector(sel, { timeout: budgets.firstCardMs }); say(`${width} ${name} first content`, performance.now() - t0, budgets.firstCardMs); } catch { say(`${width} ${name} first content`, budgets.firstCardMs + 1, budgets.firstCardMs); }
  }
  await page.close();
}
await browser.close();
console.log(failures ? `${failures} over budget` : 'PASS  every measurement within budget');
