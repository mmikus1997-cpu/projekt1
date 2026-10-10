// E2E podglądu Flutter Web: Welcome → Login → świat → Dashboard (desktop/tablet/mobile).
// Użycie: node tools/e2e_flow.cjs [login] [hasło]   (wymaga playwright w ../online/node_modules)
const { chromium } = require('../../online/node_modules/playwright');
const OUT = __dirname + '/../screens/';
const [user = 'fluttertest', pass = 'test1234'] = process.argv.slice(2);
const assert = (c, m) => { if (!c) throw new Error(m); };
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await p.goto('http://127.0.0.1:8080/');
  await p.waitForURL(/#\/welcome/, { timeout: 20000 });
  await p.evaluate(() => document.querySelector('flt-semantics-placeholder')?.click());
  await p.waitForTimeout(600);
  await p.getByRole('button', { name: /Zaloguj się/ }).first().click();
  await p.waitForURL(/#\/login/);
  const type = async (name, v) => { const f = p.getByRole('textbox', { name }); await f.click(); await p.keyboard.press('Control+A'); await p.keyboard.type(v); };
  await type(/Login/, user); await type(/Hasło/, pass);
  await p.getByRole('button', { name: /^Zaloguj się$/ }).last().click();
  await p.waitForURL(/#\/(worlds|dashboard)/, { timeout: 15000 });
  if (p.url().includes('worlds')) { await p.getByRole('button', { name: /Wejdź/ }).first().click(); }
  await p.waitForURL(/#\/dashboard/, { timeout: 15000 }); await p.waitForTimeout(2500);
  await p.screenshot({ path: OUT + 'dashboard-desktop.png' });
  const txt = await p.evaluate(() => document.body.innerText);
  console.log('desktop ok, sojusz w semantyce:', /PKG|Port Kings/.test(txt));
  await p.setViewportSize({ width: 800, height: 1000 }); await p.waitForTimeout(1200); await p.screenshot({ path: OUT + 'dashboard-tablet.png' });
  await p.setViewportSize({ width: 390, height: 844 }); await p.waitForTimeout(1200); await p.screenshot({ path: OUT + 'dashboard-mobile.png' });
  // dolny pasek: Sojusz → i powrót na pulpit ikoną domku
  await p.getByRole('button', { name: /Sojusz/ }).last().click(); await p.waitForURL(/#\/alliance/);
  await p.waitForTimeout(800); await p.screenshot({ path: OUT + 'mobile-alliance-tab.png' });
  await p.getByRole('button', { name: /Pulpit/ }).first().click(); await p.waitForURL(/#\/dashboard/);
  assert(errs.length === 0, 'błędy konsoli: ' + errs.join(' | '));
  console.log('PASS e2e_flow');
  await b.close();
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
