import test from 'node:test';
import assert from 'node:assert/strict';
import {boundedRequest,abortClientRequests,validateApiTarget} from '../../src/ap1/network.mjs';
import {assertOtpApiOperation,withOneCreatePermit} from '../../src/ap12/api-policy.mjs';
import {loadBootstrap,validateBootstrapUrl,csrfRequestToken} from '../../src/ap1/bootstrap.mjs';
import {makeSessionCheck} from '../../src/ap9/session-check.mjs';
import {deriveServerRoot} from '../../src/ap1/session.mjs';
import {deferred,tick} from './helpers.mjs';
const page='https://cloud.local/nc/apps/passwords_otp/', root='https://cloud.local/nc/index.php/apps/passwords/api/';
const initial={status:'ready',bootstrapUrl:page+'bootstrap',sessionStatusUrl:page+'session-status',sessionFingerprint:'a'.repeat(64)};
const credentials={status:'ready',login:'synthetic',token:'PRIVATE-TOKEN',sessionFingerprint:initial.sessionFingerprint,
 sessionRequestUrl:root+'1.0/session/request',sessionOpenUrl:root+'1.0/session/open',passwordListUrl:root+'1.0/password/list'};
const doc={head:{getAttribute:()=> 'csrf-synthetic-value'}};
for(const [method,path] of [['PATCH','1.0/password/update'],['DELETE','1.0/password/delete'],['POST','1.0/password/show'],['POST','1.0/share/create'],
 ['POST','1.0/settings/set'],['POST','1.0/keychain/set'],['POST','1.0/password/create?x=1'],['POST','1.0/password/../password/create'],['GET','https://other/']]) {
 test('Policy rejects '+method+' '+path,()=>assert.throws(()=>assertOtpApiOperation(path,method,{}),/otp-api-operation-denied/));
}
test('CREATE needs exactly one synchronous single-use permit; nested permits forbidden',async()=>{
 const client={};assert.throws(()=>assertOtpApiOperation('1.0/password/create','POST',client));
 await withOneCreatePermit(client,async()=>{
  assert.doesNotThrow(()=>assertOtpApiOperation('1.0/password/create','POST',client));
  assert.throws(()=>assertOtpApiOperation('1.0/password/create','POST',client));
  await assert.rejects(withOneCreatePermit(client,async()=>{}));
 });assert.throws(()=>assertOtpApiOperation('1.0/password/create','POST',client));
});
test('Permit is cleared after exceptional completion',async()=>{
 const c={};await assert.rejects(withOneCreatePermit(c,async()=>{throw Error('synthetic');}));
 assert.throws(()=>assertOtpApiOperation('1.0/password/create','POST',c));
});
for(const target of ['http://cloud.local/nc/index.php/apps/passwords/api/1.0/password/list','https://evil.invalid/nc/index.php/apps/passwords/api/1.0/password/list',
 root+'1.0/password/list?secret=x',root+'1.0/password/list#x','https://user:pass@cloud.local/nc/index.php/apps/passwords/api/1.0/password/list']) {
 test('Transport rejects untrusted URL '+target,()=>assert.throws(()=>validateApiTarget(target,root,page)));
}
test('Nextcloud subpath is retained without allowing roots on another origin',()=>{
 assert.equal(deriveServerRoot(credentials,page).baseUrl,'https://cloud.local/nc/');
 assert.equal(validateApiTarget(root+'1.0/password/list',root,page).route,'1.0/password/list');
 assert.throws(()=>validateApiTarget(root+'1.0/password/list','https://evil.invalid/apps/passwords/api/',page));
});
test('Deadline also covers a response body that never resolves',async()=>{
 let signal;await assert.rejects(boundedRequest({},async s=>{signal=s;return new Promise(()=>{});},{timeoutMs:5}));assert.equal(signal.aborted,true);
});
test('External abort is propagated and abortClientRequests blocks late operations',async()=>{
 const client={},d=deferred();let signal;const pending=boundedRequest(client,async s=>{signal=s;return d.promise;});await tick();abortClientRequests(client);
 await assert.rejects(pending);assert.equal(signal.aborted,true);d.resolve('late');
 let calls=0;const abort=new AbortController();abort.abort();await assert.rejects(boundedRequest({},()=>calls++,{signal:abort.signal}));assert.equal(calls,0);
});
test('Aborted old request cleanup does not unregister a new request for same client',async()=>{
 const client={};const first=boundedRequest(client,()=>new Promise(()=>{}));await tick();abortClientRequests(client);
 const second=boundedRequest(client,()=>new Promise(()=>{}));const p=assert.rejects(first);await p;abortClientRequests(client);await assert.rejects(second);
});
test('Bootstrap supplies CSRF/session fingerprint but never follows redirects or sends credential cookies to API',async()=>{
 const result=await loadBootstrap(initial,page,doc,async(url,options)=>{
  assert.equal(url,initial.bootstrapUrl);assert.equal(options.method,'POST');assert.equal(options.credentials,'same-origin');
  assert.equal(options.redirect,'error');assert.equal(options.cache,'no-store');assert.equal(options.headers['X-Passwords-OTP-Session'],initial.sessionFingerprint);
  assert.equal(options.headers.requesttoken,'csrf-synthetic-value');return new Response(JSON.stringify(credentials),{headers:{'content-type':'application/json'}});
 });assert.equal(result.user,'synthetic');assert.equal(result.baseUrl,'https://cloud.local/nc/');
});
for(const status of [301,401,403,412,429,500])test('Bootstrap rejects HTTP '+status,async()=>{
 await assert.rejects(loadBootstrap(initial,page,doc,async()=>new Response('{}',{status,headers:{'content-type':'application/json'}})),/bootstrap-failed/);
});
test('Bootstrap rejects credentials for a different originating browser session',async()=>{
 await assert.rejects(loadBootstrap(initial,page,doc,async()=>new Response(JSON.stringify({...credentials,sessionFingerprint:'b'.repeat(64)}),{headers:{'content-type':'application/json'}})),/bootstrap-failed/);
});
test('Bootstrap rejects initial-state credentials and bad CSRF before network',async()=>{
 let requests=0;await assert.rejects(loadBootstrap({...initial,token:'PRIVATE'},page,doc,()=>requests++));assert.equal(requests,0);
 assert.throws(()=>csrfRequestToken({head:{getAttribute:()=>''}}));assert.throws(()=>validateBootstrapUrl('https://other.invalid/bootstrap',page));
});
for(const data of [{authenticated:false},{authenticated:true,sessionFingerprint:'b'.repeat(64)},null])test('Session check rejects wrong authentication/fingerprint '+JSON.stringify(data),async()=>{
 const check=makeSessionCheck(initial,page,async()=>new Response(JSON.stringify(data),{headers:{'content-type':'application/json'}}));assert.equal(await check(),false);
});
test('Session check rejects login HTML, exceptions and non-OK response',async()=>{
 for(const requester of [async()=>new Response('<html>Login</html>',{headers:{'content-type':'text/html'}}),async()=>{throw Error('PRIVATE');},async()=>new Response('{}',{status:403})]) {
  assert.equal(await makeSessionCheck(initial,page,requester)(),false);
 }
});
test('Session fingerprint is immutable per checker, even if original config is mutated',async()=>{
 const config={...initial};const checker=makeSessionCheck(config,page,async()=>new Response(JSON.stringify({authenticated:true,sessionFingerprint:initial.sessionFingerprint}),{headers:{'content-type':'application/json'}}));
 config.sessionFingerprint='b'.repeat(64);assert.equal(await checker(),true);
});
for(const path of ['1.0/password/../password/list','1.0/password/%2e%2e/password/list','1.0/password%2flist','1.0/password\\list']) {
 test('Reject raw traversal before URL normalization '+path,()=>assert.throws(()=>validateApiTarget(root+path,root,page)));
}
