const NM='/Users/koretada/.npm/_npx/9833c18b2d85bc59/node_modules';
const {chromium}=require(NM+'/playwright');
const FILE='/Users/koretada/Desktop/投資/pachislot/deploy/index.html';
(async()=>{
  const b=await chromium.launch({channel:'chrome',headless:true});
  const page=await b.newPage();
  await page.goto('https://app.netlify.com/drop',{waitUntil:'domcontentloaded',timeout:30000});
  await page.waitForTimeout(3000);
  const inputs=await page.$$('input[type=file]');
  console.log('inputs:',inputs.length);
  let done=false;
  for(let idx=0; idx<inputs.length && !done; idx++){
    try{
      await inputs[idx].setInputFiles(FILE);
      console.log('set file on input',idx,'-> waiting...');
      for(let i=0;i<15;i++){
        await page.waitForTimeout(3000);
        const c=await page.content();
        const m=c.match(/https?:\/\/[a-z0-9-]+\.netlify\.app/);
        if(m){console.log('DEPLOY_URL:',m[0]); done=true; break;}
      }
    }catch(e){ console.log('input',idx,'err:',e.message.split('\n')[0]); }
  }
  if(!done) console.log('URL得られず');
  await b.close();
})();
