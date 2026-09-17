const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const path=require('node:path');
const fs=require('node:fs');
const url=pathToFileURL(path.resolve(__dirname,'../docs/index.html')).href;
const pixel=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==','base64');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const checks=[],errors=[];
 const check=(name,value)=>{assert(value,name);checks.push(name);};
 async function pageFor(mode){
  const ctx=await browser.newContext({viewport:{width:1440,height:1050}});
  let requests=0;
  if(mode!=='live')await ctx.route('https://**/*',async route=>{
   if(mode==='blocked')return route.abort();
   if(mode==='stalled')return;
   if(mode==='labels-blocked'&&route.request().url().includes('/Reference/'))return route.abort();
   if(mode==='partial'&&!route.request().url().includes('/Reference/')&&Number(route.request().url().split('/').pop())%2===0)return route.abort();
   return route.fulfill({status:200,contentType:'image/png',body:pixel});
  });
  const page=await ctx.newPage();page.on('pageerror',e=>{errors.push(e.message);console.error('Browser error in '+mode+': '+e.stack);});
  await page.goto(url,{waitUntil:'domcontentloaded'});
  return {ctx,page};
 }
 let {ctx,page}=await pageFor('success');
 await page.waitForFunction(()=>tile&&tile._tiles&&Object.values(tile._tiles).some(t=>t.loaded)&&!map.hasLayer(geography));
 check('Fresh atlas defaults to loaded satellite imagery',await page.locator('#basemap').inputValue()==='satellite');
 check('Satellite labels enabled',await page.evaluate(()=>labelTiles&&map.hasLayer(labelTiles)));
 await page.locator('#imagerylabels').uncheck();check('Labels can be hidden',await page.evaluate(()=>labelTiles===null));
 await page.locator('#satellitesite').click();check('Site inspection uses satellite at neighbourhood scale',await page.evaluate(()=>map.getZoom()===16&&$('basemap').value==='satellite'));
 await page.evaluate(()=>{window.previousTiles=tile;setBasemap('vector',true);window.previousTiles.fire('tileerror');window.previousTiles.fire('load');});
 check('Late tile events cannot override manual offline selection',await page.evaluate(()=>tile===null&&map.hasLayer(geography)&&$('basemap').value==='vector'));
 await page.reload();check('Explicit offline preference survives reload',await page.locator('#basemap').inputValue()==='vector');
 for(const width of [390,768,1440]){await page.setViewportSize({width,height:900});check('No horizontal overflow at '+width,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}
 await ctx.close();
 for(const mode of ['blocked','partial','stalled']){
  console.log('Testing recovery:',mode);
  ({ctx,page}=await pageFor(mode));
  try{await page.waitForFunction(()=>$('basemap').value==='vector'&&tile===null&&map.hasLayer(geography),{},{timeout:16000});}catch(e){console.log(await page.evaluate(()=>({base:$('basemap').value,note:$('imagery-status').textContent,geography:map.hasLayer(geography),timer:basemapTimer,tiles:tile&&Object.values(tile._tiles).map(t=>({loaded:t.loaded,current:t.current}))})));throw e;}
  check(mode+' tiles recover to embedded geography',await page.locator('#k-sites').textContent()==='30');
  await ctx.close();
 }
 ({ctx,page}=await pageFor('labels-blocked'));
 await page.waitForFunction(()=>labelTiles===null&&tile&&!map.hasLayer(geography));
 check('Label failure does not discard working imagery',await page.locator('#basemap').inputValue()==='satellite');await ctx.close();
 if(process.env.LIVE_SATELLITE==='1'){
  ({ctx,page}=await pageFor('live'));
  await page.waitForFunction(()=>$('basemap').value==='satellite'&&tile&&!map.hasLayer(geography)&&Object.values(tile._tiles).some(t=>t.loaded),{},{timeout:20000});
  await page.waitForTimeout(1500);
  check('Real Esri imagery loads',await page.locator('#basemap').inputValue()==='satellite');
  const out=process.env.QA_OUTPUT||require('node:os').tmpdir();fs.mkdirSync(out,{recursive:true});
  await page.locator('.workspace').screenshot({path:path.join(out,'satellite-metro.png')});
  await page.locator('#search').fill('Wingfield');await page.locator('#satellitesite').click();await page.waitForTimeout(3000);
  await page.locator('.workspace').screenshot({path:path.join(out,'satellite-neighbourhood.png')});
  check('Neighbourhood imagery stays active',await page.locator('#basemap').inputValue()==='satellite');
  await page.setViewportSize({width:390,height:900});await page.locator('.mapcolumn').screenshot({path:path.join(out,'satellite-mobile.png')});
  await ctx.close();
 }
 check('No browser runtime errors',errors.length===0);
 console.log(JSON.stringify({passed:checks.length,checks,errors},null,2));await browser.close();
})().catch(e=>{console.error(e);process.exit(1);});
