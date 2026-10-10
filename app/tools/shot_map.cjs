// Zrzuty mapy (desktop + mobile) dla konta klub_demo. Użycie: node shot_map.cjs <prefiks> [klikX klikY]
const { chromium } = require('playwright');
(async () => {
  const pre = process.argv[2] || 'map', cx = +process.argv[3], cy = +process.argv[4], mx = +process.argv[5], my = +process.argv[6];
  const b = await chromium.launch();
  const r = await fetch('http://localhost:8080/api/auth/login', {method:'POST', headers:{'content-type':'application/json','X-City-Preview-Session':'1'}, body: JSON.stringify({username:'klub_demo', password:'klub-demo-123'})});
  const j = await r.json();
  for (const [name, vp] of [['d', {width:1280,height:900}], ['m', {width:400,height:850}]]) {
    const p = await b.newPage({viewport: vp});
    await p.goto('http://localhost:8080/');
    await p.evaluate(([t,c]) => { localStorage.setItem('flutter.session.token', JSON.stringify(t)); localStorage.setItem('flutter.session.csrf', JSON.stringify(c)); localStorage.setItem('flutter.session.world', JSON.stringify(2)); }, [j.previewSessionToken, j.csrf]);
    await p.goto('http://localhost:8080/'); await p.waitForTimeout(8000); await p.keyboard.press('Escape'); await p.waitForTimeout(1500);
    await p.screenshot({path:`/home/user/city-empire/app/shots/${pre}-${name}.png`});
    if (name === 'm' && mx) { await p.mouse.move(mx,my); await p.waitForTimeout(300); await p.mouse.click(mx,my); await p.waitForTimeout(2500); await p.screenshot({path:`/home/user/city-empire/app/shots/${pre}-mclick.png`}); }
    if (name === 'd' && cx) { await p.mouse.move(cx,cy); await p.waitForTimeout(300); await p.mouse.click(cx,cy); await p.waitForTimeout(2500); await p.screenshot({path:`/home/user/city-empire/app/shots/${pre}-click.png`}); }
  }
  await b.close();
})();
