import test from 'node:test';
import assert from 'node:assert/strict';
import {fixture,synthetic,record,deferred,tick,clone} from './helpers.mjs';
import {prepareOtpCreatePayload,readEncryptionPreference,sha1ForPasswords} from '../../src/ap12/create.mjs';
import {webcrypto} from 'node:crypto';
const rejectCode=(promise,code)=>assert.rejects(promise,error=>error.code===code&&!error.message.includes('PRIVATE'));
for(const [status,code] of [[401,'auth-invalid'],[403,'auth-rate-limited'],[412,'auth-required']]){
 for(const phase of ['load','authorize','list']) test(`Session ${phase} HTTP ${status} fails closed`,async()=>{
  const fail=()=>{throw {response:{status},message:'PRIVATE'};};
  const f=fixture({[phase]:fail,onRequest:phase==='list'?()=>fail():undefined});
  await rejectCode(f.session.begin(),code);assert.equal(f.session.disposed,true);assert.equal(f.session.snapshot().count,null);assert.ok(f.unsets());
 });
}
test('Challenge and factor required; incorrect provider never opens or reads',async()=>{
 const f=fixture({challenge:true,twoFactor:true});assert.equal((await f.session.begin()).state,'needs-auth');
 assert.equal(f.calls.length,1);await rejectCode(f.session.unlock({password:'short'}),'invalid-password-input');
 await rejectCode(f.session.unlock({password:'synthetic-master-password',providerId:'wrong',otpCode:'1'}),'unsupported-token-provider');
 assert.equal(f.calls.length,1);await f.session.unlock({password:'synthetic-master-password',providerId:'synthetic-factor',otpCode:'654321'});
 assert.equal(f.provider.value,'');f.session.dispose();
});
for(const config of [{providerType:'push-token'},{providerRequest:true}])test('Unsupported factor is fail-closed '+JSON.stringify(config),async()=>{
 const f=fixture({twoFactor:true,...config});await f.session.begin();
 await rejectCode(f.session.unlock({providerId:'synthetic-factor',otpCode:'654321'}),'unsupported-token-provider');assert.equal(f.calls.length,1);
});
test('Ordinary CSE records decrypt only custom fields; OTP metadata separately, never passwords',async()=>{
 const f=fixture({challenge:true,records:[{id:'normal',cseType:'CSEv1r1',cseKey:'x',password:'enc:PRIVATE',customFields:'enc:[]'},
 record('otp',{cseType:'CSEv1r1',cseKey:'x',label:'enc:label',username:'enc:user',password:'enc:PRIVATE',customFields:'enc:'+record().customFields})]});
 await f.ready();assert.equal(f.session.snapshot().otpCount,1);assert.equal(f.session.snapshot().cseChecked,2);
 assert.equal(f.decrypts.length,3);assert.ok(f.decrypts.every(x=>x.password===null));
 assert.doesNotMatch(JSON.stringify(f.session.snapshot()),/PRIVATE|JBSWY/);f.session.dispose();
});
test('Late list response after dispose does not revive any key or metadata',async()=>{
 const d=deferred();const f=fixture({onRequest:async({path})=>{if(path.endsWith('/list'))return d.promise;}});
 const work=f.session.begin();await tick();f.session.dispose();d.resolve([record()]);await rejectCode(work,'disposed');assert.equal(f.session.snapshot().otpCount,null);
});
test('Local lock invalidates state synchronously, even while upstream close is pending',async()=>{
 const d=deferred();const f=fixture({records:[record()],onRequest:async({path})=>{if(path.endsWith('/close'))return d.promise;}});
 await f.ready();const close=f.session.close();assert.equal(f.session.disposed,true);assert.equal(f.session.snapshot().count,null);
 assert.equal(f.session.authorization,null);await rejectCode(f.session.totpFor('one'),'disposed');d.resolve({success:true});await close;
});
test('Existing supported TOTP creates a non-extractable private key and is discarded on lock',async()=>{
 const f=fixture({records:[record()]});await f.ready();assert.match((await f.session.totpFor('one',59000)).code,/^\d{6}$/);
 assert.doesNotMatch(JSON.stringify(f.session.snapshot()),/JBSWY|SYNTHETIC-NOT|customFields/);f.session.dispose();await rejectCode(f.session.totpFor('one'),'disposed');
});
for(const mode of [0,1])test('Create with '+(mode?'CSE':'SSE')+' validates exact persisted contents and four fresh session checks',async()=>{
 const f=fixture({mode,challenge:!!mode,records:[{id:'regular',password:'untouched'}]});await f.ready();let checks=0;
 const original=clone(f.records[0]);const result=await f.session.createNewOtp(synthetic(),{verifySession:async()=>{checks++;return true;}});
 assert.equal(checks,4);assert.equal(result.snapshot.otpCount,1);assert.equal(f.writes().length,1);
 assert.equal(f.writes()[0].method,'POST');assert.deepEqual(f.writes()[0].accepted,[201]);assert.deepEqual(f.records[0],original);
 assert.equal(result.id,'new-1');assert.equal(result.snapshot.count,2);
 if(mode){assert.ok(f.writes()[0].data.password.startsWith('enc:'));assert.ok(f.decrypts.some(x=>x.password==='enc:'+synthetic().password));}
 assert.doesNotMatch(JSON.stringify(result),/JBSWY|SYNTHETIC-NOT|cseKey|customFields/);f.session.dispose();
});
for(const [key,value] of [['label',''],['label','x'.repeat(161)],['username',7],['password',''],['password','0'],['secret','BAD']])test('Invalid create '+key+' never sends any request',async()=>{
 const f=fixture();await f.ready();const count=f.calls.length;
 await assert.rejects(f.session.createNewOtp(synthetic({[key]:value}),{verifySession:async()=>true}));assert.equal(f.calls.length,count);assert.equal(f.writes().length,0);
});
for(const check of [1,2,3,4])test('Session failure at create checkpoint '+check+' blocks output and further mutation',async()=>{
 const f=fixture();await f.ready();let count=0;
 await rejectCode(f.session.createNewOtp(synthetic(),{verifySession:async()=>++count!==check}),check<3?'auth-required':'create-uncertain');
 assert.equal(f.writes().length,check<3?0:1);assert.equal(f.session.disposed,true);assert.equal(f.session.snapshot().count,null);
});
test('Concurrent double submit causes exactly one create',async()=>{
 const d=deferred();let entered=0;const f=fixture({afterCommit:async()=>{entered++;await d.promise;}});await f.ready();
 const first=f.session.createNewOtp(synthetic(),{verifySession:async()=>true});while(!entered)await tick();
 await rejectCode(f.session.createNewOtp(synthetic(),{verifySession:async()=>true}),'create-busy');
 d.resolve();await first;assert.equal(f.writes().length,1);f.session.dispose();
});
test('Input mutation during encryption cannot change the submitted account',async()=>{
 const d=deferred();let entered=false;const f=fixture();await f.ready();const form=synthetic();
 const work=f.session.createNewOtp(form,{verifySession:async()=>{if(!entered){entered=true;await d.promise;}return true;}});
 form.password='changed';form.secret='AAAAAAAAAAAAAAAA';d.resolve();await work;
 assert.equal(f.records[0].password,synthetic().password);f.session.dispose();
});
for(const status of [0,401,403,409,412,429,500])test('Ambiguous create failure '+status+' is one-shot even when session method is called again',async()=>{
 const f=fixture({afterCommit:()=>{throw {status,message:'PRIVATE upstream'};}});await f.ready();
 await rejectCode(f.session.createNewOtp(synthetic(),{verifySession:async()=>true}),'create-uncertain');
 await rejectCode(f.session.createNewOtp(synthetic(),{verifySession:async()=>true}),'create-uncertain');
 assert.equal(f.writes().length,1);assert.equal(f.records.length,1);assert.equal(f.session.disposed,true);
});
for(const field of ['label','username','password','customFields','revision','cseType'])test('Incorrect readback '+field+' never reports successful create',async()=>{
 const f=fixture({afterCommit:rec=>{rec[field]='WRONG';}});await f.ready();
 await rejectCode(f.session.createNewOtp(synthetic(),{verifySession:async()=>true}),'create-uncertain');assert.equal(f.session.snapshot().otpCount,null);assert.equal(f.writes().length,1);
});
test('CREATE returning an existing non-OTP ID is rejected',async()=>{
 const f=fixture({records:[{id:'existing'}],afterCommit:rec=>{rec.id='existing';}});await f.ready();
 await rejectCode(f.session.createNewOtp(synthetic(),{verifySession:async()=>true}),'create-uncertain');
});
test('Duplicate readback IDs are not an accepted creation',async()=>{
 const f=fixture({afterCommit:(rec,records)=>records.push(clone(rec))});await f.ready();
 await rejectCode(f.session.createNewOtp(synthetic(),{verifySession:async()=>true}),'create-uncertain');
});
test('Disposal while create acknowledgement is in flight cannot repopulate the vault',async()=>{
 const d=deferred();let entered=false;const f=fixture({afterCommit:async()=>{entered=true;await d.promise;}});await f.ready();
 const work=f.session.createNewOtp(synthetic(),{verifySession:async()=>true});while(!entered)await tick();f.session.dispose();d.resolve();
 await rejectCode(work,'create-uncertain');assert.equal(f.writes().length,1);assert.equal(f.session.snapshot().count,null);
});
test('CSE enabled without challenge refuses downgrade',async()=>{
 const f=fixture({mode:1});await f.ready();await rejectCode(f.session.createNewOtp(synthetic(),{verifySession:async()=>true}),'create-cse-unavailable');assert.equal(f.writes().length,0);
});
test('Unknown encryption setting cannot silently downgrade',async()=>{
 const f=fixture({mode:2});await f.ready();await rejectCode(f.session.createNewOtp(synthetic(),{verifySession:async()=>true}),'create-encryption-unknown');assert.equal(f.writes().length,0);
});
for(const field of ['password','label','username','customFields'])test('Plaintext '+field+' in CSE payload is rejected before CREATE',async()=>{
 const f=fixture({challenge:true,mode:1,encrypt:async obj=>{
  const original=obj[field];for(const key of ['password','label','username','customFields'])obj[key]='enc:'+obj[key];
  obj[field]=original;return {...obj,cseType:'CSEv1r1',cseKey:'key'};
 }});await f.ready();await rejectCode(f.session.createNewOtp(synthetic(),{verifySession:async()=>true}),'create-cse-unavailable');assert.equal(f.writes().length,0);
});
test('CSE readiness deadline does not write',async()=>{
 const f=fixture({challenge:true,mode:1,ready:()=>new Promise(()=>{}),decryptTimeoutMs:5});await f.ready();
 await assert.rejects(f.session.createNewOtp(synthetic(),{verifySession:async()=>true}));assert.equal(f.writes().length,0);f.session.dispose();
});
test('Original Passwords hash shape is retained without changing crypto protocol',async()=>{
 assert.equal(await sha1ForPasswords('abc',webcrypto.subtle),'a9993e364706816aba3e25717850c26c9cd0d89d');
 for(const raw of [{},null,{'user.encryption.cse':true}])assert.throws(()=>readEncryptionPreference(raw));
});

test('13-minute idle CSE challenge expires before any CREATE, no false ambiguity',async()=>{
 let elapsed=0;const f=fixture({challenge:true,mode:1,onRequest:({path})=>{
   if(path==='1.0/session/request')return elapsed>=600000?{challenge:{type:'PWDv1r1'}}:{};
 }});
 await f.ready();elapsed=13*60000;
 await rejectCode(f.session.createNewOtp(synthetic(),{verifySession:async()=>true}),'passwords-session-expired');
 assert.equal(f.writes().length,0);assert.equal(f.session.disposed,true);
 await rejectCode(f.session.createNewOtp(synthetic(),{verifySession:async()=>true}),'disposed');
});
for(const status of [401,412])test('Expired Passwords API/token '+status+' is a pre-write denial, not create-uncertain',async()=>{
 const f=fixture({onRequest:({path})=>{if(path==='1.0/session/request')throw {response:{status},message:'PRIVATE'};}});
 await f.ready();
 await rejectCode(f.session.createNewOtp(synthetic(),{verifySession:async()=>true}),'passwords-session-expired');
 assert.equal(f.writes().length,0);assert.equal(f.records.length,0);assert.equal(f.session.disposed,true);
});
test('Transient Passwords probe error is retryable and sends no CREATE before recovery',async()=>{
 let failed=true;const f=fixture({onRequest:({path})=>{if(path==='1.0/session/request'&&failed)throw {response:{status:503}};}});
 await f.ready();
 await rejectCode(f.session.createNewOtp(synthetic(),{verifySession:async()=>true}),'create-auth-unavailable');
 assert.equal(f.writes().length,0);assert.equal(f.session.disposed,false);
 failed=false;
 const result=await f.session.createNewOtp(synthetic(),{verifySession:async()=>true});
 assert.equal(result.id,'new-1');assert.equal(f.writes().length,1);f.session.dispose();
});
test('Unexpected nonempty session/request response refuses create, never trusts keepalive alone',async()=>{
 const f=fixture({onRequest:({path})=>path==='1.0/session/request'?{success:true}:undefined});
 await f.ready();
 await rejectCode(f.session.assertCreateAccess(),'passwords-session-expired');
 assert.equal(f.session.disposed,true);assert.equal(f.writes().length,0);
});

test('Incorrect CSE passphrase with upstream error ID can be retried without reload',async()=>{
 let attempts=0;
 const wrong={response:new Response(JSON.stringify({
  status:'error',id:'ab6e13ba',message:'Passphrase invalid'}),{status:401}),message:'HTTP 401'};
 const f=fixture({challenge:true,authorize:async()=>{if(++attempts===1)throw wrong;}});
 assert.equal((await f.session.begin()).state,'needs-auth');
 await rejectCode(f.session.unlock({password:'synthetic-master-password'}),'invalid-master-key');
 assert.equal(f.session.disposed,false);
 assert.equal(f.session.state,'needs-auth');
 assert.equal(f.writes().length,0);
 assert.equal((await f.session.unlock({password:'synthetic-master-password'})).state,'ready');
 assert.equal(attempts,2);f.session.dispose();
});
test('HTTP 500 / 033d1943 indicates challenge failure, not a wrong master password',async()=>{
 const err={response:new Response(JSON.stringify({
  status:'error',id:'033d1943',message:'Passphrase verification failed'}),{status:500}),message:'HTTP 500'};
 const f=fixture({challenge:true,authorize:async()=>{throw err;}});
 await f.session.begin();
 await rejectCode(f.session.unlock({password:'synthetic-master-password'}),'api-error');
 assert.equal(f.session.disposed,true);
});
test('Unrelated HTTP 401 is not a wrong master key',async()=>{
 const f=fixture({challenge:true,authorize:async()=>{throw {response:new Response(JSON.stringify({
  status:'error',id:'deadbeef',message:'Token invalid'}),{status:401})};}});
 await f.session.begin();
 await rejectCode(f.session.unlock({password:'synthetic-master-password'}),'auth-invalid');
 assert.equal(f.session.disposed,true);
});
test('Passphrase ID with HTTP 500 must not enable retry',async()=>{
 const f=fixture({challenge:true,authorize:async()=>{throw {response:new Response(JSON.stringify({
  status:'error',id:'ab6e13ba',message:'Passphrase invalid'}),{status:500})};}});
 await f.session.begin();
 await rejectCode(f.session.unlock({password:'synthetic-master-password'}),'api-error');
 assert.equal(f.session.disposed,true);
});
for(const status of [403,429])test('Passwords authorization probe rate limit '+status+' is not Nextcloud logout',async()=>{
 const f=fixture({onRequest:({path})=>{if(path==='1.0/session/request')throw {response:{status},message:'PRIVATE'};}});
 await f.ready();
 await rejectCode(f.session.createNewOtp(synthetic(),{verifySession:async()=>true}),'auth-rate-limited');
 assert.equal(f.writes().length,0);assert.equal(f.session.disposed,true);
});
test('Normal close is best effort but destroys local secret state synchronously',async()=>{
 const f=fixture();await f.ready();
 const pending=f.session.close();
 assert.equal(f.session.disposed,true);
 assert.equal(f.session.snapshot().otpAccounts.length,0);
 await pending;
 assert.ok(f.calls.some(c=>c.path==='1.0/session/close'));
});
