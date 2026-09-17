// The laptop camera source and the guided tour on the video screen, driven against a
// running instance with the browser's fake camera (a Y4M file stands in for the lens).
// Usage: CHROME=<chromium> FAKE_CAMERA=<file.y4m> BASE=http://host:8008 TOKEN=... node camera-drive.mjs [outdir]
import puppeteer from 'puppeteer-core';
const BASE = process.env.BASE ?? 'http://localhost:4173';
const TOKEN = process.env.TOKEN ?? '';
const outDir = process.argv[2];
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
let failures = 0;
const say = (ok, name, detail = '') => { if (!ok) failures += 1; console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  ' + detail : ''}`); };
const args = ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'];
if (process.env.FAKE_CAMERA) args.push(`--use-file-for-fake-video-capture=${process.env.FAKE_CAMERA}`);
if (process.env.CHROME) args.push('--no-sandbox');
const browser = await puppeteer.launch({ executablePath: process.env.CHROME ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true, args });

for (const [theme, width] of [['light', 1440], ['dark', 390]]) {
  const page = await browser.newPage();
  await page.evaluateOnNewDocument((tok, th) => { try { if (tok) localStorage.setItem('lifekit.token', tok); localStorage.setItem('lifekit.welcomeDone', '1'); localStorage.setItem('lifekit.theme', th); } catch {} }, TOKEN, theme);
  await page.setViewport({ width, height: 900, isMobile: width < 900 });
  await page.goto(`${BASE}/?c${width}${theme}#/video`, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForSelector('.screen.video select', { timeout: 240000 });
  await wait(800);

  // The tour: every step anchors to a control that is inside the viewport.
  await page.click('.screen.video .tour-open');
  const steps = await page.$$eval('.screen.video .callout', (els) => els.length);
  say(steps === 1, `${theme} ${width} tour opens with one callout`);
  let inside = true;
  let count = 0;
  const outside = [];
  for (;;) {
    await wait(300);
    const box = await page.evaluate(() => {
      const c = document.querySelector('.screen.video .callout');
      if (!c) return null;
      const r = c.getBoundingClientRect();
      const n = c.querySelector('.n')?.textContent;
      const title = c.querySelector('h3')?.textContent;
      const anchor = document.querySelector('.tour-on');
      const a = anchor?.getBoundingClientRect();
      return { n, title, ok: r.left >= 0 && r.right <= innerWidth && r.top >= 0 && r.bottom <= innerHeight, anchored: !!a && a.bottom > 0 && a.top < innerHeight };
    });
    if (!box) break;
    count += 1;
    if (!box.ok || !box.anchored) { inside = false; outside.push(`${box.n} ${box.title} callout ${box.ok ? 'in' : 'out'} anchor ${box.anchored ? 'in' : 'out'}`); }
    if (outDir && count <= 5) await page.screenshot({ path: `${outDir}/tour-${theme}-${width}-${count}.png` });
    const label = await page.$eval('.screen.video .callout .go', (el) => el.textContent);
    await page.click('.screen.video .callout .go');
    if (label === 'Done') break;
  }
  say(count === 5, `${theme} ${width} tour has five steps in order`, `${count} steps`);
  say(inside, `${theme} ${width} every callout and its anchor inside the viewport`, outside.join('; '));
  const closed = await page.$('.screen.video .callout');
  say(!closed, `${theme} ${width} tour closes on Done`);

  if (width === 1440) {
    // The camera run: pick the camera, Launch, see the Recording pill, wait for two
    // segments, Stop, read the report.
    await page.click('.screen.video .tab');
    await page.select('.screen.video select', 'camera');
    await wait(300);
    await page.click('.screen.video .chip.ask');
    await page.waitForSelector('.screen.video .recording', { timeout: 15000 });
    say(true, 'Recording pill shown over the camera view');
    await wait(1500);
    if (outDir) await page.screenshot({ path: `${outDir}/camera-${theme}-${width}-recording.png` });
    const preview = await page.$eval('.screen.video .capture video', (v) => v.videoWidth > 0 && !v.paused);
    say(preview, 'camera preview plays');
    await wait(21000);
    const t0 = performance.now();
    await page.click('.screen.video .chip.ask');
    await page.waitForSelector('.screen.video .report, .screen.video .fail', { timeout: 240000 });
    const seconds = Math.round((performance.now() - t0) / 1000);
    const fail = await page.$eval('.screen.video .fail', (el) => el.textContent).catch(() => '');
    say(!fail, 'no failure line', fail);
    const events = await page.$$eval('.screen.video .report .event', (els) => els.map((e) => e.textContent.trim()));
    say(events.length >= 2, 'at least two segments described', `${events.length} events, report ${seconds} s after Stop`);
    say(events.every((l) => /^\d+(\.\d+)?-\d+(\.\d+)?:/.test(l)), 'every event line starts with a start and end time stamp', events[0]?.slice(0, 70) ?? '');
    const stopped = await page.evaluate(() => !document.querySelector('.screen.video .recording'));
    say(stopped, 'recording ended');
    if (outDir) await page.screenshot({ path: `${outDir}/camera-${theme}-${width}-report.png`, fullPage: true });
  }
  await page.close();
}
await browser.close();
console.log(failures ? `${failures} failed` : 'PASS  camera and tour');
process.exit(failures ? 1 : 0);
