import test from 'node:test';
import assert from 'node:assert/strict';
import {TotpPresenter} from '../../src/ap3/ui.mjs';
import {timeSlot} from '../../src/ap3/totp.mjs';
import {dom,deferred,settle} from './helpers.mjs';
function setup({period=30,now=1000,verify=async()=>true,calculate}={}) {
 const d=dom();let clock=now,checks=0,calculations=0,copies=0,fatals=0;
 const session={state:'ready',disposed:false,dispose(){this.state='locked';this.disposed=true;},
  async totpFor(id,time){calculations++;return calculate?calculate(id,time):{code:'123456',...timeSlot(time,period)};}};
 const p=new TotpPresenter(d.nodes,d.doc,{now:()=>clock,verifySession:async()=>{checks++;return verify();},
  writeClipboard:()=>{copies++;return Promise.resolve();},fatal:()=>fatals++});
 const snapshot={state:'ready',count:1,otpCount:1,invalidOtpCount:0,otpAccounts:[{id:'one',title:'one',type:'totp',algorithm:'sha1',digits:6,period}]};
 p.setSession(session);p.render(snapshot);
 return {...d,p,session,snapshot,setClock:v=>{clock=v;},checks:()=>checks,calculations:()=>calculations,copies:()=>copies,fatals:()=>fatals,
 code:()=>d.find('passwords-otp-ap3__code')?.textContent,copyDisabled:()=>d.find('passwords-otp-ap3__copy')?.disabled};
}
test('Normal TOTP guard is once per slot; countdown is local; clipboard is synchronous',async t=>{
 const f=setup();t.after(()=>f.p.dispose());await settle();assert.equal(f.checks(),1);assert.equal(f.code(),'123456');
 f.setClock(2000);await f.p.refresh();assert.equal(f.checks(),1);f.p.copy('one');assert.equal(f.copies(),1);
 f.setClock(30000);await f.p.refresh();await settle();assert.equal(f.checks(),2);assert.equal(f.calculations(),2);
});
test('Missing verification defaults to fail closed',async()=>{
 const d=dom();let disposed=0;const session={state:'ready',dispose(){disposed++;this.state='locked';}};
 const p=new TotpPresenter(d.nodes,d.doc);p.setSession(session);p.render({state:'ready',otpCount:0,invalidOtpCount:0,otpAccounts:[]});await settle();assert.equal(disposed,1);p.dispose();
});
test('Delayed successful response from previous slot cannot authorize new slot',async t=>{
 const first=deferred(),second=deferred();let count=0;
 const f=setup({now:29999,verify:()=>++count===1?first.promise:second.promise});t.after(()=>f.p.dispose());
 f.setClock(30001);first.resolve(true);await settle();assert.equal(f.checks(),2);assert.equal(f.calculations(),0);assert.notEqual(f.code(),'123456');
 second.resolve(false);await settle();assert.equal(f.session.disposed,true);assert.equal(f.calculations(),0);
});
test('Focus generation rejects stale successful response and checks again',async t=>{
 const first=deferred(),second=deferred();let count=0;
 const f=setup({verify:()=>++count===1?first.promise:second.promise});t.after(()=>f.p.dispose());
 f.p.focusChanged();first.resolve(true);await settle();assert.equal(f.checks(),2);assert.equal(f.calculations(),0);
 second.resolve(false);await settle();assert.equal(f.session.disposed,true);
});
test('45-second account still checks at 30-second boundary and at own boundary',async t=>{
 const f=setup({period:45,now:29000});t.after(()=>f.p.dispose());await settle();
 f.setClock(30000);await f.p.refresh();await settle();assert.equal(f.checks(),2);
 f.setClock(45000);await f.p.refresh();await settle();assert.equal(f.checks(),3);
});
test('Timer-throttled clipboard cannot copy through a 30-second auth boundary',async t=>{
 const d=deferred();let calls=0;const f=setup({period:60,now:29000,verify:()=>++calls===1?true:d.promise});t.after(()=>f.p.dispose());
 await settle();assert.equal(f.code(),'123456');f.setClock(31000);f.p.copy('one');assert.equal(f.copies(),0);assert.notEqual(f.code(),'123456');
 d.resolve(false);await settle();assert.equal(f.session.disposed,true);
});
test('Expired/near-expiry code is not copied',async t=>{
 const f=setup();t.after(()=>f.p.dispose());await settle();f.setClock(29000);f.p.copy('one');assert.equal(f.copies(),0);
});
test('HMAC finishing in a later 30-second window requires fresh session proof even for 60s account',async t=>{
 const sign=deferred(),check=deferred();let checks=0;
 const f=setup({period:60,now:29999,verify:()=>++checks===1?true:check.promise,
  calculate:()=>sign.promise});t.after(()=>f.p.dispose());await settle();assert.equal(f.calculations(),1);
 f.setClock(30001);sign.resolve({code:'123456',...timeSlot(29999,60)});await settle();assert.equal(f.checks(),2);assert.notEqual(f.code(),'123456');
 check.resolve(false);await settle();assert.equal(f.session.disposed,true);
});
test('Session disposal during signing never displays late code',async t=>{
 const d=deferred();const f=setup({calculate:()=>d.promise});t.after(()=>f.p.dispose());await settle();
 f.session.dispose();d.resolve({code:'123456',...timeSlot(1000,30)});await settle();assert.notEqual(f.code(),'123456');f.p.copy('one');assert.equal(f.copies(),0);
});
test('Search rerender during pending verification does not accept the stale result',async t=>{
 const d=deferred();let n=0;const f=setup({verify:()=>++n===1?d.promise:false});t.after(()=>f.p.dispose());
 f.p.render(f.snapshot,'one');d.resolve(true);await settle();await f.p.refresh();await settle();assert.equal(f.calculations(),0);assert.equal(f.session.disposed,true);
});
test('Hidden tab hides codes; return requires a fresh guard',async t=>{
 const f=setup();t.after(()=>f.p.dispose());await settle();f.doc.hidden=true;f.p.visibilityChanged();assert.notEqual(f.code(),'123456');
 f.doc.hidden=false;f.p.visibilityChanged();await settle();assert.equal(f.checks(),2);
});
test('Backward time jump inside one slot is revalidated',async t=>{
 const f=setup({now:10000});t.after(()=>f.p.dispose());await settle();f.setClock(9000);await f.p.refresh();await settle();assert.equal(f.checks(),2);
});
test('Invalid clock stops, hides codes and disposes session',async t=>{
 const f=setup();t.after(()=>f.p.dispose());await settle();f.setClock(NaN);await f.p.refresh();assert.equal(f.session.disposed,true);assert.notEqual(f.code(),'123456');
});
test('Session HTTP failure at next slot never issues successor code',async t=>{
 let allow=true;const f=setup({verify:async()=>allow});t.after(()=>f.p.dispose());await settle();allow=false;
 f.setClock(30000);await f.p.refresh();await settle();assert.equal(f.calculations(),1);assert.equal(f.session.disposed,true);assert.equal(f.fatals(),1);
});
test('Malformed calculated value never reaches DOM or clipboard',async t=>{
 const f=setup({calculate:async()=>({code:'<script>PRIVATE</script>',...timeSlot(1000,30)})});t.after(()=>f.p.dispose());await settle();assert.equal(f.session.disposed,true);assert.doesNotMatch(f.code(),/PRIVATE/);
});

test('No statistics DOM: code generation, search and automatic revocation still work',async t=>{
 const d=dom();delete d.nodes.count;delete d.nodes.invalid;
 let allowed=true,copied=null;
 const session={state:'ready',disposed:false,dispose(){this.state='locked';this.disposed=true;},
  async totpFor(id,now){return {code:'123456',...timeSlot(now,30)};}};
 const p=new TotpPresenter(d.nodes,d.doc,{now:()=>1000,verifySession:async()=>allowed,
  writeClipboard:value=>{copied=value;return Promise.resolve();}});
 t.after(()=>p.dispose());p.setSession(session);
 const snapshot={state:'ready',otpCount:1,invalidOtpCount:0,otpAccounts:[{id:'one',title:'Own or shared OTP',type:'totp',algorithm:'sha1',digits:6,period:30}]};
 p.render(snapshot);await settle();assert.equal(d.find('passwords-otp-ap3__code').textContent,'123456');
 p.copy('one');assert.equal(copied,'123456');
 p.render(snapshot,'not-found');await settle();assert.equal(d.nodes.list.children.length,1);
 assert.equal(d.nodes.list.children[0].hidden,true);
 p.render(snapshot,'shared');await settle();assert.equal(d.nodes.list.children.length,1);
 assert.equal(d.nodes.list.children[0].hidden,false);
 allowed=false;p.focusChanged();await settle();assert.equal(session.disposed,true);
 assert.notEqual(d.find('passwords-otp-ap3__code')?.textContent,'123456');
});

test('Search filter retains current verified code without re-render, re-signing or extra auth',async t=>{
 const f=setup();t.after(()=>f.p.dispose());await settle();
 const oldCode=f.code(),checks=f.checks(),calculations=f.calculations();
 assert.equal(oldCode,'123456');
 f.p.filter('not-present');assert.equal(f.nodes.list.children.length,1);
 assert.equal(f.nodes.list.children[0].hidden,true);
 assert.equal(f.code(),oldCode);
 assert.equal(f.copyDisabled(),false);
 f.p.copy('one');assert.equal(f.copies(),0,'filtered-out code must not be copied');
 f.p.filter('one');
 assert.equal(f.nodes.list.children[0].hidden,false);
 assert.equal(f.code(),oldCode);
 assert.equal(f.checks(),checks);
 assert.equal(f.calculations(),calculations);
});

test('After CREATE with active search, rerender ALL rows and clearing query restores accounts',async t=>{
 const d=dom(), calls=[];
 const session={state:'ready',disposed:false,dispose(){this.disposed=true;this.state='locked';},
  async totpFor(id,now){calls.push(id);return {code:'654321',...timeSlot(now,30)};}};
 const p=new TotpPresenter(d.nodes,d.doc,{now:()=>1000,verifySession:async()=>true});
 t.after(()=>p.dispose());p.setSession(session);
 const mk=(id,title)=>({id,title,type:'totp',algorithm:'sha1',digits:6,period:30});
 const existing={state:'ready',otpCount:2,invalidOtpCount:0,unsupportedOtpCount:0,
  otpAccounts:[mk('git','GitHub'),mk('bank','Bank')]};
 p.render(existing,'git');await settle();
 assert.equal(d.nodes.list.children.length,2,'search must not omit Bank DOM');
 assert.deepEqual(d.nodes.list.children.map(x=>x.hidden),[false,true]);
 const afterCreate={...existing,otpCount:3,otpAccounts:[...existing.otpAccounts,mk('new','New account')]};
 p.render(afterCreate,'git');await settle();
 assert.equal(d.nodes.list.children.length,3,'create rerender still owns all three rows');
 assert.deepEqual(d.nodes.list.children.map(x=>x.hidden),[false,true,true]);
 p.filter('');await settle();
 assert.equal(d.nodes.list.children.filter(x=>!x.hidden).length,3,'clearing search restores Bank and New');
 assert.deepEqual(d.nodes.list.children.map(x=>x.children[0].textContent),['GitHub','Bank','New account']);
 assert.ok(calls.includes('bank'),'previously filtered row can calculate its OTP');
});
