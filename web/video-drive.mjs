// The video screen driven against a running instance: the clip and prompts load, Launch
// streams each chunk, the report shows time-stamped events; screenshots of both tabs.
// Usage: BASE=http://host:8008 TOKEN=... node video-drive.mjs [outdir]
import puppeteer from 'puppeteer-core';
const BASE = process.env.BASE ?? 'http://localhost:4173';
const TOKEN = process.env.TOKEN ?? '';
const outDir = process.argv[2];
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
let failures = 0;
const say = (ok, name, detail = '') => { if (!ok) failures += 1; console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  ' + detail : ''}`); };
const browser = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
for (const [theme, width] of [['dark', 1440], ['light', 1440], ['dark', 390]]) {
  const page = await browser.newPage();
  await page.evaluateOnNewDocument((tok, th) => { try { if (tok) localStorage.setItem('lifekit.token', tok); localStorage.setItem('lifekit.welcomeDone', '1'); localStorage.setItem('lifekit.theme', th); } catch {} }, TOKEN, theme);
  await page.setViewport({ width, height: 900, isMobile: width < 900 });
  await page.goto(`${BASE}/?v${width}${theme}#/video`, { waitUntil: 'networkidle0' });
  await page.waitForSelector('.screen.video textarea', { timeout: 30000 });
  await wait(800);
  const prompt = await page.$eval('.screen.video textarea', (el) => el.value);
  say(prompt.includes('natural hazard'), `${theme} ${width} summarization prompt loaded from packs`, prompt.slice(0, 40));
  const clipSrc = await page.$eval('.screen.video video', (el) => el.getAttribute('src'));
  say(clipSrc === '/vss/seattleish-minute.mp4', `${theme} ${width} clip in the player`, clipSrc ?? '');
  const centred = await page.evaluate(() => { const s = document.querySelector('.screen.video').getBoundingClientRect(); const m = document.querySelector('.main').getBoundingClientRect(); return Math.abs((s.left + s.right) / 2 - (m.left + m.right) / 2) < 2; });
  say(centred, `${theme} ${width} screen centred in the content column`);
  if (outDir) await page.screenshot({ path: `${outDir}/video-${theme}-${width}-input.png` });
  if (theme === 'dark' && width === 1440) {
    const t0 = performance.now();
    await page.click('.screen.video .chip.ask');
    await page.waitForSelector('.screen.video .progress', { timeout: 10000 });
    say(true, 'progress shown after Launch');
    await wait(15000);
    if (outDir) await page.screenshot({ path: `${outDir}/video-dark-1440-working.png` });
    const steps = await page.$$eval('.screen.video .step', (els) => els.length);
    const reported = await page.$('.screen.video .report');
    say(steps >= 1 || !!reported, 'chunk lines appear while the run works, or the run has already finished', `${steps} lines`);
    await page.waitForSelector('.screen.video .report', { timeout: 240000 });
    const seconds = Math.round((performance.now() - t0) / 1000);
    say(seconds <= 180, 'report within 180 s', `${seconds} s`);
    const eventLines = await page.$$eval('.screen.video .report .event', (els) => els.map((e) => e.textContent.trim()));
    say(eventLines.length >= 2 && eventLines.every((l) => /^\d+(\.\d+)?-\d+(\.\d+)?:/.test(l)), 'every event line starts with a start and end time stamp', `${eventLines.length} events; first: ${eventLines[0]?.slice(0, 60)}`);
    const headings = await page.$$eval('.screen.video .report h4', (els) => els.length);
    say(headings >= 2, 'a heading per time range', `${headings} headings`);
    if (outDir) await page.screenshot({ path: `${outDir}/video-dark-1440-output.png`, fullPage: true });
  }
  await page.close();
}
await browser.close();
console.log(failures ? `${failures} failed` : 'PASS  video screen');
process.exit(failures ? 1 : 0);
