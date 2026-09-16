const { chromium } = require(process.env.QA_PLAYWRIGHT ||
  'C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const output = process.argv[2];
(async () => {
  const browser = await chromium.launch({headless:true, executablePath: process.env.QA_CHROMIUM ||
    'C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1187/chrome-win/chrome.exe'});
  const results = [];
  try {
    for (const origin of ['http://127.0.0.1:18080', 'https://127.0.0.1:18443']) {
      const context = await browser.newContext({ignoreHTTPSErrors:true, viewport:{width:1280,height:900}});
      const page = await context.newPage();
      const errors = [], urls = [], sockets = [];
      page.on('pageerror', e => errors.push(e.message));
      page.on('request', r => urls.push(r.url()));
      page.on('websocket', s => sockets.push(s.url()));
      const api = async (method, url, data, token) => {
        const response = await context.request.fetch(origin + url, {method, data,
          headers: token ? {Authorization:`Bearer ${token}`} : {}});
        assert(response.ok(), `${method} ${url}: ${response.status()} ${await response.text()}`);
        return response.json();
      };
      for (const entry of ['', 'admin', 'screen', 'user']) {
        const r = await context.request.get(`${origin}/${entry}?x=1`, {maxRedirects:0});
        assert.equal(r.status(), entry ? 301 : 302);
        assert.equal(r.headers().location, `/${entry || 'admin'}/?x=1`);
      }
      for (const entry of ['admin','screen','user']) {
        assert.equal((await context.request.get(`${origin}/${entry}/assets/missing.js`)).status(),404);
        await page.goto(`${origin}/${entry}/`);
        await page.waitForTimeout(300);
        assert((await page.locator('body').innerText()).trim().length > 0);
        await page.screenshot({path:path.join(output, `${origin.startsWith('https')?'tls':'http'}-${entry}.png`)});
      }
      await page.goto(`${origin}/admin/login`);
      await page.getByPlaceholder('请输入用户名').fill('qaadmin');
      await page.getByPlaceholder('请输入密码').fill('qa-test-password-123');
      await page.getByRole('button', {name:'登录工作台'}).click();
      await page.waitForURL(`${origin}/admin/`);
      const token = await page.evaluate(() => localStorage.getItem('active_admin_token'));
      assert(token);
      const activity = await api('POST','/api/v1/admin/activities', {name:'Proxy QA'}, token);
      const id = activity.activity_id;
      const user = await api('POST',`/api/v1/activities/${id}/auth/register`,
        {username:'QA User',phone:'13800000001'});
      await api('POST',`/api/v1/admin/activities/${id}/open`, undefined, token);
      await page.goto(`${origin}/admin/activities/${id}`);
      await page.reload();
      await page.waitForSelector('img[alt="活动移动端二维码"]');
      const expected = `${origin}/user/activity/${id}`;
      assert((await page.locator('body').innerText()).includes(expected));
      await page.screenshot({path:path.join(output, `${origin.startsWith('https')?'tls':'http'}-activity-qr.png`)});
      const config = await api('GET',`/api/v1/admin/activities/${id}/lottery`,undefined,token);
      const prizeId = config.prizes[0].prize_id;
      const image = await context.request.post(
        `${origin}/api/v1/admin/activities/${id}/lottery/prizes/${prizeId}/image`,
        {headers:{Authorization:`Bearer ${token}`},multipart:{file:{name:'qa.png',mimeType:'image/png',
          buffer:fs.readFileSync(path.join(output,'http-admin.png'))}}});
      assert.equal(image.status(),201,await image.text());
      const imageURL = (await image.json()).image_url;
      assert.equal((await context.request.get(origin + imageURL)).status(),200);
      assert.equal((await context.request.get(origin + imageURL.replace(id,'wrong-activity'))).status(),404);
      const popupPromise = page.waitForEvent('popup');
      await page.getByRole('button', {name:'打开抽奖大屏'}).click();
      const popup = await popupPromise;
      await popup.waitForLoadState();
      assert(popup.url().startsWith(`${origin}/screen/?activity_id=${id}`));
      await popup.close();
      await page.evaluate(({id,token}) => localStorage.setItem(`active_user_token:${id}`,token),
        {id,token:user.access_token});
      await page.goto(expected + '/chat');
      await page.reload();
      await page.waitForTimeout(400);
      assert(page.url().startsWith(expected));
      assert(sockets.some(url => url.endsWith(`/activities/${id}/chat/ws`)));
      await page.screenshot({path:path.join(output, `${origin.startsWith('https')?'tls':'http'}-user-deep.png`)});
      const wsResult = await page.evaluate(async ({origin,id,userToken}) => {
        const base = origin.replace(/^http/,'ws');
        const exchange = (url, auth, message) => new Promise((resolve,reject) => {
          const ws = new WebSocket(url);
          const timer = setTimeout(() => {ws.close();reject(Error('WS timeout'));},10000);
          ws.onerror = () => reject(Error('WS failed'));
          ws.onopen = () => {if(auth) ws.send(JSON.stringify({type:'auth',token:auth}));};
          ws.onmessage = ({data}) => {
            const event = JSON.parse(data);
            if (message && event.type.endsWith('.ready')) {ws.send(JSON.stringify(message));return;}
            clearTimeout(timer);ws.close();resolve(event);
          };
        });
        const chat = await exchange(`${base}/api/v1/activities/${id}/chat/ws`,userToken,
          {type:'message.send',body:'proxy QA message'});
        const lottery = await exchange(`${base}/api/v1/activities/${id}/lottery/ws`);
        return {chat:chat.type,lottery:lottery.type};
      }, {origin,id,userToken:user.access_token});
      assert.equal(wsResult.chat,'message.created');
      assert.equal(wsResult.lottery,'lottery.ready');
      const draw = await page.evaluate(({origin,id,token,prizeId}) => new Promise((resolve,reject) => {
        const base = origin.replace(/^http/,'ws');
        const publicSocket = new WebSocket(`${base}/api/v1/activities/${id}/lottery/ws`);
        let adminSocket, result, publicResult;
        const timer = setTimeout(() => {publicSocket.close();adminSocket?.close();reject(Error('draw timeout'));},10000);
        const finish = () => {if(result && publicResult) {
          clearTimeout(timer);publicSocket.close();adminSocket.close();resolve({result,publicResult});
        }};
        publicSocket.onmessage = ({data}) => {
          const event = JSON.parse(data);
          if(event.type === 'lottery.ready') {
            adminSocket = new WebSocket(`${base}/api/v1/admin/activities/${id}/lottery/ws`);
            adminSocket.onopen = () => adminSocket.send(JSON.stringify({type:'auth',token}));
            adminSocket.onmessage = ({data}) => {
              const event = JSON.parse(data);
              if(event.type === 'lottery.ready') adminSocket.send(JSON.stringify(
                {type:'lottery.draw.request',prize_id:prizeId,request_id:'proxy-qa-draw'}));
              else if(event.type === 'lottery.draw.result') {result=event;finish();}
              else if(event.type === 'lottery.draw.error') reject(Error(JSON.stringify(event)));
            };
          } else if(event.type === 'lottery.drawn') {publicResult=event;finish();}
        };
      }),{origin,id,token,prizeId});
      assert.equal(draw.result.draw.draw_id,draw.publicResult.draw.draw_id);
      assert.equal(draw.publicResult.draw.winner.activity_user_id,user.activity_user_id);
      assert(!JSON.stringify(draw.publicResult).includes('13800000001'));
      assert(sockets.some(u => u.startsWith(origin.startsWith('https')?'wss:':'ws:')));
      assert(!urls.some(u => /localhost:8000|127\.0\.0\.1:8000/.test(u)));
      assert.deepEqual(errors,[]);
      results.push({origin,redirects:4,missingAssets:3,login:true,activity:true,qr:expected,
        deepRefresh:true,uploadReadIsolation:true,drawBroadcast:true,wsResult,sockets,pageErrors:errors});
      await context.close();
    }
    fs.writeFileSync(path.join(output,'results.json'),JSON.stringify(results,null,2));
    console.log(JSON.stringify(results,null,2));
  } finally {await browser.close();}
})().catch(error => {console.error(error);process.exitCode=1;});
