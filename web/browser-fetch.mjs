// Fetch documents that refuse non-browser clients, through a real Chrome. Writes the same
// source file and source.meta.json the Python fetcher writes.
import puppeteer from 'puppeteer-core';
import fs from 'fs';
import crypto from 'crypto';
const list = JSON.parse(fs.readFileSync('browser-fetch.json', 'utf8'));
const browser = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const page = await browser.newPage();
await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36');
for (const v of list) {
  const dir = `../packs/volumes/${v.id}`;
  fs.mkdirSync(dir, { recursive: true });
  try {
    let bytes;
    if (v.format === 'pdf') {
      const b64 = await page.evaluate(async (url) => {
        const r = await fetch(url); const buf = await r.arrayBuffer();
        let s = ''; const a = new Uint8Array(buf); for (let i = 0; i < a.length; i++) s += String.fromCharCode(a[i]); return btoa(s);
      }, v.url);
      bytes = Buffer.from(b64, 'base64');
      if (!bytes.subarray(0, 4).equals(Buffer.from('%PDF'))) throw new Error('not a PDF');
    } else {
      const response = await page.goto(v.url, { waitUntil: 'networkidle2', timeout: 60000 });
      if (!response || response.status() >= 400) throw new Error(`HTTP ${response && response.status()}`);
      await new Promise((r) => setTimeout(r, 1500));
      bytes = Buffer.from(await page.content(), 'utf8');
      if (bytes.length < 2000) throw new Error('page too small, likely a block page');
    }
    const ext = v.format === 'pdf' ? 'pdf' : 'html';
    fs.writeFileSync(`${dir}/source.${ext}`, bytes);
    fs.writeFileSync(`${dir}/source.meta.json`, JSON.stringify({ id: v.id, url: v.url, sha256: crypto.createHash('sha256').update(bytes).digest('hex'), bytes: bytes.length, content_type: v.format === 'pdf' ? 'application/pdf' : 'text/html', retrieved: new Date().toISOString().slice(0, 19) + '+00:00', fetched_by: 'browser-fetch.mjs (Chrome via puppeteer) 0.1' }, null, 1));
    console.log(`ok   ${v.id}  ${bytes.length}`);
  } catch (e) {
    console.log(`FAIL ${v.id}  ${String(e.message).slice(0, 80)}`);
  }
}
await browser.close();
