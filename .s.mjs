import { chromium } from 'playwright';
const SP="/tmp/claude-0/-home-user-website/72a8db8f-e1ac-5f1c-943a-d109acf2cbd2/scratchpad";
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const p = await b.newPage({ viewport: { width: 1280, height: 950 } });
await p.goto('http://127.0.0.1:8099/archives.html', { waitUntil: 'networkidle' });
await p.evaluate(() => document.querySelectorAll('.reveal').forEach(e=>e.classList.add('is-in')));
await p.evaluate(() => document.querySelectorAll('.archive--page img[loading="lazy"]').forEach(i=>i.loading='eager'));
await p.evaluate(async () => { await Promise.all([...document.images].filter(i=>!i.complete && i.offsetParent!==null).map(i=>new Promise(r=>{i.onload=i.onerror=r;}))); });
await p.waitForTimeout(1800);
// Did the hidden frames stay unfetched?
const fetched = await p.evaluate(() => {
  const hidden=[...document.querySelectorAll('.archive-frames img')];
  return { total: hidden.length, loaded: hidden.filter(i=>i.complete && i.naturalWidth>0).length };
});
console.log('hidden frames:', JSON.stringify(fetched));
const sec = p.locator('#celebrity');
await sec.scrollIntoViewIfNeeded(); await p.waitForTimeout(700);
await sec.screenshot({ path: `${SP}/shoots-celebrity.jpg`, quality: 86, type: 'jpeg' });
await b.close();
