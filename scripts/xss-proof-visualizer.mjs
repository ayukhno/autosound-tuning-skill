// The end-to-end proof for HUB-040, run by a PERSON — it needs Chrome, so it is deliberately
// not part of `scripts/run-selftests.sh` (the lint that is, and that CI runs, is
// `scripts/html-data-check.py`).
//
// In a real (headless) browser it hands the curve visualizer a curve whose NAME is
// `<img src=x onerror=alert(1)>` by each of the three carriers the page accepts — the dropped
// file's NAME, a `# NTT: Name` line inside the file's BODY, and the `#curve=` link fragment —
// then reports whether that name renders as TEXT or executes as markup. An alert() from the
// injected markup is caught two ways: the dialog is recorded, and the hung renderer it causes
// ends as a FAIL through the watchdog instead of a run that never returns.
//
//   node scripts/xss-proof-visualizer.mjs \
//       skills/autosound-tuning/references/patterns/target-curves/target_curves_visualizer.html
//
// Exit 0 = text stayed text. To see it FAIL on purpose, point it at the file as it was before
// the fix: `git show v3.0.46:<path> > /tmp/before.html && node scripts/... /tmp/before.html`.
// CHROME=/path/to/chrome overrides the browser. Node 22+ (global fetch and WebSocket).
import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { existsSync, realpathSync } from 'node:fs';

const arg = process.argv[2];
if (!arg) {
  console.error('usage: node scripts/xss-proof-visualizer.mjs <html file>');
  process.exit(2);
}
if (!existsSync(arg)) { console.error(`no such file: ${arg}`); process.exit(2); }
const file = realpathSync(arg);                 // Chrome needs an absolute path in file://
const PAYLOAD = '<img src=x onerror=alert(1)>';
const PORT = 9331 + (process.pid % 200);
const CHROME_CANDIDATES = [
  process.env.CHROME,
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
  '/snap/bin/chromium',
].filter(Boolean);
const CHROME = CHROME_CANDIDATES.find(p => existsSync(p));
if (!CHROME) {
  console.error('no Chrome found — set CHROME=/path/to/chrome. Tried:\n  ' + CHROME_CANDIDATES.join('\n  '));
  process.exit(2);
}
const profile = mkdtempSync(join(tmpdir(), 'xssproof-'));
const chrome = spawn(CHROME, [
  '--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--no-default-browser-check', '--disable-gpu', '--window-size=1400,900',
  'file://' + file,
], { stdio: 'ignore' });
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function target() {
  for (let i = 0; i < 100; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const p = list.find(t => t.type === 'page' && t.url.startsWith('file://'));
      if (p && p.webSocketDebuggerUrl) return p;
    } catch (e) { /* not up yet */ }
    await sleep(150);
  }
  throw new Error('chrome did not come up');
}
const t = await target();
const ws = new WebSocket(t.webSocketDebuggerUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
let id = 0; const waiting = new Map(); const dialogs = [];
ws.onmessage = (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && waiting.has(m.id)) { waiting.get(m.id)(m); waiting.delete(m.id); return; }
  // A REAL alert() opens a modal dialog and freezes the renderer — which is how the
  // unpatched page hangs this harness. Record it as evidence and dismiss it.
  if (m.method === 'Page.javascriptDialogOpening') {
    dialogs.push(m.params.type + ': ' + m.params.message);
    ws.send(JSON.stringify({ id: ++id, method: 'Page.handleJavaScriptDialog', params: { accept: true } }));
  }
};
// a hung renderer must end as a FAIL, not as a session that never returns
const watchdog = setTimeout(() => {
  console.log('dialogs seen:', dialogs);
  console.log('VERDICT: FAIL — the page stopped answering (a modal dialog from the injected markup)');
  try { ws.close(); } catch (e) {}
  chrome.kill('SIGKILL');
  process.exit(1);
}, 75000);
const send = (method, params) => new Promise(res => {
  const n = ++id; waiting.set(n, res); ws.send(JSON.stringify({ id: n, method, params }));
});
async function evaluate(expression) {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true, userGesture: true });
  const ex = r.result?.exceptionDetails;
  if (ex) throw new Error(ex.exception?.description || JSON.stringify(ex));
  return r.result?.result?.value;
}
async function ready() {
  for (let i = 0; i < 80; i++) {
    if (await evaluate("document.readyState === 'complete' && typeof curveChart !== 'undefined'")) return;
    await sleep(150);
  }
  throw new Error('page never finished loading');
}
const trap = `window.__alerted = false;
  window.alert = function () { window.__alerted = true; };
  window.prompt = function () { return null; };`;   // keep the level dialog out of the way

await send('Runtime.enable');
await send('Page.enable');
await ready();
// localStorage from a previous run would restore old curves and muddy the count
await evaluate('try { localStorage.clear(); } catch (e) {} location.reload()');
await sleep(500); await ready();

const PAIRS = '20 0\\n100 0\\n1000 0\\n10000 0\\n20000 0\\n';
// carrier 1: the dropped file's NAME.  carrier 2: a `# NTT: Name` line in its BODY.
await evaluate(`(() => {
  ${trap}
  const drop = (name, body) => {
    const dt = new DataTransfer();
    dt.items.add(new File([body], name, { type: 'text/plain' }));
    document.getElementById('dropZone').dispatchEvent(
      new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true }));
  };
  drop(${JSON.stringify(PAYLOAD + '.txt')}, '${PAIRS}');
  return true;
})()`);
await sleep(500);
await evaluate(`(() => {
  const dt = new DataTransfer();
  dt.items.add(new File(['# NTT: Name - ${PAYLOAD}\\n${PAIRS}'], 'body-name.txt', { type: 'text/plain' }));
  document.getElementById('dropZone').dispatchEvent(
    new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true }));
  return true;
})()`);
await sleep(600);

// every panel that prints a curve name: crosshair readout, comparison table, deviation report
const seen = await evaluate(`(() => {
  const cv = document.getElementById('curvesChart'), r = cv.getBoundingClientRect();
  cv.dispatchEvent(new MouseEvent('mousemove', { clientX: r.left + r.width * 0.5, clientY: r.top + r.height * 0.5, bubbles: true }));
  const click = (id) => { const e = document.getElementById(id); if (e) e.click(); };
  click('compareBtn'); click('analyzeBtn'); click('anzRunBtn');
  const txt = (sel) => { const e = document.querySelector(sel); return e ? e.textContent.replace(/\\s+/g, ' ').trim() : null; };
  const cards = Array.from(document.querySelectorAll('.info-grid .card'))
    .map(c => (c.querySelector('.card-title span') || {}).textContent || '');
  return {
    cards,
    cursorInfo: txt('#cursorInfo'),
    comparePanel: (txt('#comparePanel') || '').slice(0, 200),
    analyzePanel: (txt('#analyzePanel') || '').slice(0, 200),
  };
})()`);

// carrier 3: the #curve= link fragment — a URL someone can send
// a fresh document, not just a fragment change: the loader runs at load time only, so the
// same URL with a new hash would not re-run it. The extra query is ignored by the page.
const hashUrl = 'file://' + file + '?proof=1#curve=' + encodeURIComponent(PAYLOAD) + '&data=' + encodeURIComponent('20 0\n1000 0\n20000 0\n');
await evaluate('try { localStorage.clear(); } catch (e) {}');
await send('Page.navigate', { url: hashUrl });
await sleep(900); await ready();
await evaluate(trap);
await sleep(400);
const fromHash = await evaluate(`(() => {
  const cards = Array.from(document.querySelectorAll('.info-grid .card'))
    .map(c => (c.querySelector('.card-title span') || {}).textContent || '');
  return { url: location.href.slice(-90), cards, imgs: document.querySelectorAll('img').length, onerror: document.querySelectorAll('[onerror]').length };
})()`);

await sleep(600);
const dom = await evaluate(`({
  imgs: document.querySelectorAll('img').length,
  onerror: document.querySelectorAll('[onerror]').length,
  alerted: window.__alerted === true,
})`);

const inText = (s) => (s || '').includes(PAYLOAD);
const checks = [
  ['file NAME renders as text on its card', seen.cards.some(inText)],
  ['file BODY name (# NTT) renders as text', seen.cards.filter(inText).length >= 2],
  ['crosshair readout prints it as text', inText(seen.cursorInfo)],
  ['comparison table prints it as text', inText(seen.comparePanel)],
  ['deviation report prints it as text', inText(seen.analyzePanel)],
  ['#curve= link renders as text (one added curve)', fromHash.cards.filter(inText).length === 1],
  ['no <img> element anywhere', dom.imgs === 0 && fromHash.imgs === 0],
  ['no onerror= attribute anywhere', dom.onerror === 0 && fromHash.onerror === 0],
  ['alert() never fired', !dom.alerted && dialogs.length === 0],
];
console.log(JSON.stringify({ seen, fromHash, dom, dialogs }, null, 2));
console.log('---');
for (const [what, ok] of checks) console.log((ok ? '  ok   ' : '  FAIL ') + what);
const pass = checks.every(c => c[1]);
console.log(pass ? 'VERDICT: text stays text — nothing from a file or a link reached the DOM as markup'
                 : 'VERDICT: FAIL — the name executed as markup');
clearTimeout(watchdog);
ws.close(); chrome.kill('SIGKILL');
try { rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 }); } catch (e) {}
process.exit(pass ? 0 : 1);
