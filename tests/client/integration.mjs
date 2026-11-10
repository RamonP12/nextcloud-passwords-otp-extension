import test from 'node:test';
import assert from 'node:assert/strict';
import {OtpVaultSession} from '../../src/ap1/session.mjs';
import {createClient,sodiumReady} from '../../src/ap1/upstream.js';
import {synthetic,clone} from '../js/helpers.mjs';
const root='https://cloud.local/index.php/apps/passwords/api/';
globalThis.window={location:{origin:'https://cloud.local',href:'https://cloud.local/apps/passwords_otp/'}};
const master='synthetic test master password';
async function scenario({challenge=false,twoFactor=false,cse=false,create=false,rejectOpen=false,wrongMasterOnce=false,serverChallengeFailure=false,rateLimitBeforeCreate=false,expireBeforeCreate=null}={}){
 await sodiumReady();const previous=globalThis.fetch,seen=[],records=[];let encryption,exportedKeychain;
 // Mock the real API authorization state. A challenge is required only until
 // session/open succeeds, not on every later session/request probe.
 let apiAuthorized=false,tokenExpired=false,openAttempts=0;
 if(cse){
  const seed=createClient({baseUrl:'https://cloud.local/',user:'fixture',token:'SYNTHETIC'});
  const keychain=seed.getClass('keychain.csev1',null,master);keychain.update();exportedKeychain=keychain.export();
  encryption=seed.getCseV1Encryption();encryption.setKeychain(keychain);await encryption.ready();
  const rec={label:'CSE fixture',username:'cse@example.invalid',password:'SYNTHETIC-EXISTING',customFields:JSON.stringify([{label:'client.ios.otp',type:'data',value:JSON.stringify({type:'totp',secret:synthetic().secret})}])};
  records.push({...await encryption.encrypt(rec,'password'),id:'seed',revision:'seed-r1'});
 }
 globalThis.fetch=async(request,options)=>{
  const url=typeof request==='string'?request:request.url,path=url.replace(root,'');
  assert.ok(url.startsWith(root));assert.equal(options.credentials,'omit');assert.equal(options.cache,'no-store');
  assert.equal(options.redirect,'error');assert.equal(options.referrerPolicy,'no-referrer');assert.ok(options.signal instanceof AbortSignal);
  assert.match(options.headers.get('authorization'),/^Basic /);seen.push({path,method:options.method});
  let value,status=200;
  if(path==='1.0/session/request'){
   if(tokenExpired){status=401;value={message:'PRIVATE expired token'};}
   else if(rateLimitBeforeCreate && apiAuthorized){status=403;value={message:'PRIVATE rate limit'};}
   else if(apiAuthorized)value={};
   else {
    value=challenge?{challenge:{type:'PWDv1r1',salts:['01'.repeat(256),'02'.repeat(64),'03'.repeat(16)]}}:{};
    if(twoFactor)value.token=[{type:'user-token',id:'factor',label:'Synthetic factor',description:'test',request:false}];
   }
  }else if(path==='1.0/session/open'){
   const params=JSON.parse(options.body);if(challenge)assert.match(params.challenge,/^[a-f0-9]{64}$/);
   if(twoFactor)assert.deepEqual(params.token,{'factor':'654321'});
   openAttempts++;
   const wrongNow=wrongMasterOnce && openAttempts===1;
   status=serverChallengeFailure?500:wrongNow?401:rejectOpen?401:200;
   value=serverChallengeFailure?{status:'error',id:'033d1943',message:'Passphrase verification failed'}
     :wrongNow?{status:'error',id:'ab6e13ba',message:'Passphrase invalid'}
     :rejectOpen?{message:'PRIVATE'}:{success:true,keys:cse?{CSEv1r1:exportedKeychain}:{}};
   if(!serverChallengeFailure&&!wrongNow&&!rejectOpen)apiAuthorized=true;
  }else if(path==='1.0/settings/list')value={'user.encryption.cse':cse?1:0};
  else if(path==='1.0/password/list')value=records;
  else if(path==='1.0/password/create'){
   assert.equal(options.method,'POST');const data=JSON.parse(options.body);
   if(cse){
    assert.equal(data.cseType,'CSEv1r1');assert.notEqual(data.password,synthetic().password);assert.notEqual(data.customFields.includes(synthetic().secret),true);
    const plain=await encryption.decrypt({...data},'password');assert.equal(plain.password,synthetic().password);assert.equal(plain.username,synthetic().username);
   }else{assert.equal(data.cseType,'none');assert.equal(data.password,synthetic().password);}
   records.push({...data,id:'created',revision:'created-r1'});value={id:'created',revision:'created-r1'};status=201;
  }else if(path==='1.0/session/close')value={success:true};
  else throw Error('Unexpected synthetic route');
  return new Response(JSON.stringify(value),{status,headers:{'content-type':'application/json','x-api-session':'SYNTHETIC-SESSION','cache-control':'no-store','date':new Date().toUTCString()}});
 };
 const client=createClient({baseUrl:'https://cloud.local/',user:'synthetic',token:'SYNTHETIC-TOKEN'});
 const session=new OtpVaultSession(client);
 try{
  let result=await session.begin();
  if(challenge||twoFactor){assert.equal(result.state,'needs-auth');assert.equal(seen.length,1);
   if(rejectOpen){await assert.rejects(session.unlock({password:master}),e=>e.code==='auth-invalid');assert.equal(seen.length,2);return;}
   if(serverChallengeFailure){
    await assert.rejects(session.unlock({password:master,providerId:'factor',otpCode:'654321'}),e=>e.code==='api-error');
    assert.equal(session.disposed,true,'server failure must not be retried as typo');
    assert.equal(seen.filter(x=>x.path==='1.0/session/open').length,1);
    return;
   }
   if(wrongMasterOnce){
    await assert.rejects(session.unlock({password:master,providerId:'factor',otpCode:'654321'}),
      e=>e.code==='invalid-master-key');
    assert.equal(session.state,'needs-auth');assert.equal(session.disposed,false);
   }
   result=await session.unlock({password:master,providerId:'factor',otpCode:'654321'});
  }
  assert.equal(result.state,'ready');assert.equal(result.otpCount,cse?1:0);
  if(create){
   const before=clone(records);
   if(rateLimitBeforeCreate){
    await assert.rejects(session.createNewOtp(synthetic(),{verifySession:async()=>true}),
      e=>e.code==='auth-rate-limited');
    assert.deepEqual(records,before);assert.equal(seen.filter(x=>x.path==='1.0/password/create').length,0);
    assert.equal(session.disposed,true);return;
   }
   // These expired-session scenarios go through the *genuine pinned client*.
   // The failed authorization probe must prevent password/create entirely.
   if(expireBeforeCreate){
    if(expireBeforeCreate==='challenge')apiAuthorized=false;
    else if(expireBeforeCreate==='token')tokenExpired=true;
    else throw Error('Unexpected expiry fixture');
    await assert.rejects(session.createNewOtp(synthetic(),{verifySession:async()=>true}),
      e=>e.code==='passwords-session-expired');
    assert.deepEqual(records,before);
    assert.equal(seen.filter(x=>x.path==='1.0/password/create').length,0);
    assert.equal(session.disposed,true);
    return;
   }
   const created=await session.createNewOtp(synthetic(),{verifySession:async()=>true});
   assert.equal(created.id,'created');assert.equal(created.snapshot.otpCount,cse?2:1);
   assert.deepEqual(records.slice(0,before.length),before);
   assert.equal(seen.filter(x=>x.path==='1.0/password/create').length,1);
   assert.equal(seen.filter(x=>x.path==='1.0/session/request').length,2, 'fresh authorization probe via pinned client');
   assert.doesNotMatch(JSON.stringify(created),/JBSWY3DPEHPK3PXP|SYNTHETIC-NOT-A-REAL-PASSWORD/);
  }
  await session.close();assert.equal(session.disposed,true);
 }finally{session.dispose();globalThis.fetch=previous;}
}
for(const config of [{},{challenge:true},{twoFactor:true},{challenge:true,twoFactor:true},{challenge:true,cse:true},
 {create:true},{challenge:true,cse:true,create:true},{challenge:true,twoFactor:true,cse:true,create:true},
 {challenge:true,cse:true,create:true,expireBeforeCreate:'challenge'},
 {challenge:true,twoFactor:true,cse:true,create:true,expireBeforeCreate:'challenge'},
 {create:true,expireBeforeCreate:'token'},
 {challenge:true,cse:true,create:true,expireBeforeCreate:'token'},
 {challenge:true,cse:true,create:true,wrongMasterOnce:true},
 {challenge:true,cse:true,serverChallengeFailure:true},
 {create:true,rateLimitBeforeCreate:true},
 {challenge:true,rejectOpen:true}]){
 test('Genuine pinned upstream client: '+JSON.stringify(config),async()=>scenario(config));
}
test('Actual upstream request wrapper blocks reuse and forbidden routes before fetch',async()=>{
 const prior=globalThis.fetch;let calls=0;globalThis.fetch=async()=>{calls++;return new Response('[]',{headers:{'content-type':'application/json'}});};
 try{
  const client=createClient({baseUrl:'https://cloud.local/',user:'synthetic',token:'SYNTHETIC'});
  const request=client.getRequest().setPath('1.0/password/list');await request.send();await assert.rejects(request.send());assert.equal(calls,1);
  await assert.rejects(client.getRequest().setPath('1.0/password/delete').setMethod('DELETE').send());assert.equal(calls,1);
 }finally{globalThis.fetch=prior;}
});
