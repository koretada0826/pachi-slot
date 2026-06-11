const NM='/Users/koretada/.npm/_npx/9833c18b2d85bc59/node_modules';
const {chromium}=require(NM+'/playwright');
const {pathToFileURL}=require('url');
(async()=>{
  const b=await chromium.launch({headless:true,executablePath:''});
  const page=await b.newPage({viewport:{width:390,height:844},deviceScaleFactor:2});
  await page.goto(pathToFileURL('/Users/koretada/Desktop/投資/pachislot/slot_tool.html').href,{waitUntil:'networkidle'}).catch(e=>console.log('goto',e.message));
  await page.waitForTimeout(400);
  // 天井タブ:現在G入れて判定
  await page.fill('#curG','450');
  await page.click('button:has-text("拾える")');
  await page.waitForTimeout(300);
  await page.screenshot({path:'ui_tenjo.png'});
  // 記録タブ
  await page.click('.tab:has-text("記録")');
  await page.fill('#lg_date','6/11'); await page.fill('#lg_hall','ジュラク王子');
  await page.fill('#lg_kishu','絆2'); await page.fill('#lg_in','8000'); await page.fill('#lg_out','12000');
  await page.click('button:has-text("記録する")');
  await page.waitForTimeout(300);
  await page.screenshot({path:'ui_log.png'});
  // 設定タブ
  await page.click('.tab:has-text("設定")');
  await page.waitForTimeout(200);
  await page.screenshot({path:'ui_settei.png'});
  await b.close(); console.log('done');
})();
