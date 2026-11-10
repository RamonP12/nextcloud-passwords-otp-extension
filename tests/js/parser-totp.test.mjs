import test from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto,createHmac} from 'node:crypto';
import {normalizeBase32Secret,parseOtpCustomFields,filterUnencryptedOtpRecords,searchOtpAccounts} from '../../src/ap2/parser.mjs';
import {decodeBase32,importTotpKey,calculateTotp,timeSlot} from '../../src/ap3/totp.mjs';
import {record,fixture} from './helpers.mjs';
import {buildNewOtpValues} from '../../src/ap12/create.mjs';
const alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
const base32=bytes=>{let bits=0,value=0,out='';for(const byte of bytes){value=(value<<8)|byte;bits+=8;while(bits>=5){bits-=5;out+=alphabet[(value>>>bits)&31];}}if(bits)out+=alphabet[(value<<(5-bits))&31];return out;};
const vectors=[
 [59,'94287082','46119246','90693936'],[1111111109,'07081804','68084774','25091201'],
 [1111111111,'14050471','67062674','99943326'],[1234567890,'89005924','91819424','93441116'],
 [2000000000,'69279037','90698825','38618901'],[20000000000,'65353130','77737706','47863826']];
for(const [j,algorithm] of ['sha1','sha256','sha512'].entries()) for(const row of vectors) {
 test(`RFC6238 ${algorithm} time=${row[0]}`,async()=>{
    const bytes=Buffer.from('1234567890'.repeat(7).slice(0,[20,32,64][j]));
    const key=await importTotpKey({type:'totp',secret:base32(bytes),algorithm,digits:8,period:30},webcrypto.subtle);
    assert.equal(key.key.extractable,false);assert.equal((await calculateTotp(key,row[0]*1000,webcrypto.subtle)).code,row[j+1]);
 });
}
test('Base32 canonical round trip and tolerated separators',()=>{
 const raw=Buffer.from('12345678901234567890'), encoded=base32(raw);
 assert.deepEqual(Buffer.from(decodeBase32(encoded)),raw);
 assert.equal(normalizeBase32Secret('jbsw y3dp-ehpk 3pxp'),'JBSWY3DPEHPK3PXP');
 for(const bad of ['',null,'A','JBSWY3DP0HPK3PXP','JBSWY3DPEHPK3PXP===','A'.repeat(4097)])assert.equal(normalizeBase32Secret(bad),null);
 const x=base32(Buffer.alloc(11,1));assert.equal(normalizeBase32Secret(x),x);
 const bad=x.slice(0,-1)+alphabet[alphabet.indexOf(x.at(-1))|1];assert.equal(normalizeBase32Secret(bad),null);
});
const fields=value=>JSON.stringify([{label:'client.ios.otp',type:'data',value:JSON.stringify(value)}]);
for(const type of ['hotp','HOTP','event','totp-unknown']) test('Unsupported type is not converted to TOTP: '+type,()=>{
 assert.equal(parseOtpCustomFields(fields({type,secret:'JBSWY3DPEHPK3PXP'})).status,'unsupported');
});
for(const [key,value] of [['secret','BAD'],['digits',5],['digits','6'],['period',0],['period',1.5],['algorithm','md5'],['issuer',{}]])test('Reject invalid '+key+' '+JSON.stringify(value),()=>{
 assert.equal(parseOtpCustomFields(fields({secret:'JBSWY3DPEHPK3PXP',type:'totp',[key]:value})).status,'invalid');
});
test('Reject duplicate OTP fields, malformed JSON, and incorrect field type',()=>{
 const r=record();const one=JSON.parse(r.customFields)[0];
 for(const v of ['{','{}',JSON.stringify([one,one]),JSON.stringify([{...one,type:'text'}])])assert.equal(parseOtpCustomFields(v).status,'invalid');
});
test('50 records filter to exactly 3 public OTP records; no secret in snapshots/search',()=>{
 const rows=Array.from({length:50},(_,i)=>i<3?record('id-'+i):{id:'id-'+i,label:'ordinary',password:'SENSITIVE'});
 const got=filterUnencryptedOtpRecords(rows);assert.equal(got.accounts.length,3);assert.equal(got.invalidOtpCount,0);
 assert.equal(searchOtpAccounts(got.accounts,'ordinary').length,0);
 assert.doesNotMatch(JSON.stringify(got),/JBSWY|SENSITIVE|SYNTHETIC-NOT/);
 const duplicate=filterUnencryptedOtpRecords([record('same'),record('same')]);assert.equal(duplicate.accounts.length,1);assert.equal(duplicate.invalidOtpCount,1);
});
test('Public metadata strips control/bidi while leaving display text inert',()=>{
 const r=filterUnencryptedOtpRecords([record('x',{label:'<img onerror=x>\u202e\u0000'})]);
 assert.equal(r.accounts[0].title,'<img onerror=x>');
});
test('Parser bounded malformed-input fuzz never throws',()=>{
 let seed=12345; for(let i=0;i<1000;i++){seed=(Math.imul(seed,1664525)+1013904223)>>>0;
 const text=String.fromCharCode(seed%128).repeat(seed%100);assert.doesNotThrow(()=>parseOtpCustomFields(text));}
});
test('Variable period/digits compare with independent node HMAC',async()=>{
 for(const digits of [6,7,8,9]) for(const period of [1,45,60]) {
  const secret='JBSWY3DPEHPK3PXP', now=1234567890123, counter=Math.floor(now/(period*1000));
  const input=Buffer.alloc(8);input.writeBigUInt64BE(BigInt(counter));
  const hash=createHmac('sha256',decodeBase32(secret)).update(input).digest(), offset=hash.at(-1)&15;
  const expected=String((hash.readUInt32BE(offset)&0x7fffffff)%(10**digits)).padStart(digits,'0');
  const key=await importTotpKey({type:'totp',secret,algorithm:'sha256',digits,period},webcrypto.subtle);
  assert.equal((await calculateTotp(key,now,webcrypto.subtle)).code,expected);
 }
});
test('Clock/period boundaries reject nonfinite, negative and unsafe input',()=>{
 assert.equal(timeSlot(30000,30).counter,1);assert.equal(timeSlot(29999,30).remainingMs,1);
 for(const value of [-1,NaN,Infinity,Number.MAX_VALUE])assert.throws(()=>timeSlot(value,30));
 for(const value of [0,-1,1.1,'30',Infinity])assert.throws(()=>timeSlot(1000,value));
});

test('Legacy 5-byte TOTP secret is readable, whitespace tolerated, but new weak key is refused',async()=>{
 const legacy='JBSWY3DP'; // 5 bytes, valid RFC4648 canonical Base32
 assert.equal(normalizeBase32Secret(' jbsw\ty3dp '),legacy);
 assert.equal(decodeBase32(legacy).length,5);
 const otp={type:'totp',secret:legacy,algorithm:'sha1',digits:6,period:30};
 const parsed=parseOtpCustomFields(JSON.stringify([{label:'client.ios.otp',type:'data',value:JSON.stringify(otp)}]));
 assert.equal(parsed.status,'valid');
 const key=await importTotpKey(parsed.otp,webcrypto.subtle);
 assert.match((await calculateTotp(key,0,webcrypto.subtle)).code,/^[0-9]{6}$/);
 assert.throws(()=>buildNewOtpValues({label:'Too weak',username:'x',password:'synthetic',secret:legacy}),
  e=>e.code==='create-invalid-secret');
});
test('Non-TOTP and malformed OTP entries are counted separately without exposing secret data',async()=>{
 const hotp=record('unsupported',{customFields:JSON.stringify([{
  label:'client.ios.otp',type:'data',value:JSON.stringify({type:'hotp',secret:'JBSWY3DPEHPK3PXP'})}])});
 const bad=record('bad',{customFields:JSON.stringify([{
  label:'client.ios.otp',type:'data',value:'{INVALID-PRIVATE'}])});
 const f=fixture({records:[record('valid'),hotp,bad]});
 await f.ready();const snap=f.session.snapshot();
 assert.equal(snap.otpCount,1);assert.equal(snap.invalidOtpCount,1);
 assert.equal(snap.unsupportedOtpCount,1);
 assert.doesNotMatch(JSON.stringify(snap),/INVALID-PRIVATE|JBSWY3DPEHPK3PXP/);
 f.session.dispose();
});
