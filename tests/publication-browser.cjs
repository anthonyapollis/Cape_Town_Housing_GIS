const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const {pathToFileURL}=require('node:url');
(async()=>{const browser=await chromium.launch({headless:true,channel:'msedge'});const ctx=await browser.newContext({offline:true,viewport:{width:1440,height:1050}});const page=await ctx.newPage();let errors=[];page.on('pageerror',e=>errors.push(e.message));const root=path.resolve(__dirname,'..');const base=process.env.PUBLICATION_URL||pathToFileURL(root+path.sep).href;if(process.env.PUBLICATION_URL)await ctx.setOffline(false);
const output=process.env.QA_OUTPUT||require('node:os').tmpdir();fs.mkdirSync(output,{recursive:true});
await page.goto(base+'index.html');assert.equal(await page.locator('.chapter').count(),30);assert.equal(await page.locator('.reader>h1').innerText(),'Cape Town.\nA closer look.');
assert.equal(await page.locator('img').evaluateAll(imgs=>imgs.every(i=>i.complete&&i.naturalWidth>0)),true);
await page.screenshot({path:path.join(output,'report-home-desktop.png')});
await page.locator('.sidebar a[href="#page-23"]').click();assert.equal(await page.locator('#page-23 tbody tr').count(),30);
await page.locator('.reportheader a[href="docs/legacy.html"]').click();assert((await page.locator('body').innerText()).includes('Where Cape Town can still build'));
await page.getByRole('link',{name:'Report home',exact:true}).click();assert.equal(await page.locator('.chapter').count(),30);
await page.locator('.reportheader a[href="library.html"]').click();assert.equal(await page.locator('.route').count(),4);assert.equal(await page.locator('.contents a').count(),18);
for(const name of ['index.html','library.html','docs/report.html']){await page.setViewportSize({width:390,height:844});await page.goto(base+name);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Mobile overflow: '+name);if(name==='index.html')await page.screenshot({path:path.join(output,'report-home-mobile.png')});}
assert.equal(errors.length,0);console.log('PASS: report homepage, 30 chapters, images, site index, original atlas round-trip, library, three mobile layouts and browser runtime checks.');await browser.close();})().catch(e=>{console.error(e);process.exit(1)});
