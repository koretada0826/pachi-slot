const NM='/Users/koretada/.npm/_npx/9833c18b2d85bc59/node_modules';
let chromium;
try { chromium = require(NM+'/playwright').chromium; }
catch(e){ chromium = require(NM+'/playwright-core').chromium; }
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36' });
  await page.goto('https://min-repo.com/3006964/', { waitUntil: 'networkidle', timeout: 30000 }).catch(e=>console.log('goto err', e.message));
  const len = (await page.content()).length;
  console.log('HTML length:', len);
  const hasJug = (await page.content()).includes('マイジャグ');
  console.log('マイジャグ含む:', hasJug);
  // 機種テーブルの最初の数行テキスト
  const txt = await page.evaluate(() => {
    const rows = [...document.querySelectorAll('tr')].slice(0,6).map(r=>r.innerText.replace(/\s+/g,' ').trim());
    return rows.join(' || ');
  }).catch(e=>'eval err '+e.message);
  console.log('rows:', txt.slice(0,400));
  await browser.close();
})();
