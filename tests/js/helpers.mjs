import {webcrypto} from 'node:crypto';
import {OtpVaultSession} from '../../src/ap1/session.mjs';
import {buildNewOtpValues} from '../../src/ap12/create.mjs';
import {assertOtpApiOperation} from '../../src/ap12/api-policy.mjs';
export const synthetic = (overrides = {}) => ({label:'Synthetic desktop test', username:'test@example.invalid',
    password:'SYNTHETIC-NOT-A-REAL-PASSWORD', secret:'JBSWY3DPEHPK3PXP', ...overrides});
export const clone = value => structuredClone(value);
export function deferred() { let resolve, reject; const promise = new Promise((a,b) => {resolve=a;reject=b;}); return {promise,resolve,reject}; }
export const tick = () => new Promise(resolve => setImmediate(resolve));
export async function settle() { for(let i=0;i<12;i++) await tick(); }
export function fixture(options = {}) {
    const calls = [], decrypts = [], records = clone(options.records || []);
    let sequence=0, unset=0;
    const encryption = {
        enabled: () => options.cryptoEnabled !== false,
        ready: async () => { if(options.ready) await options.ready(); },
        async encrypt(value) {
            if(options.encrypt) return options.encrypt(value);
            for(const key of ['password','label','username','customFields','url','notes']) {
                if(value[key]) value[key]='enc:'+value[key];
            }
            return {...value,cseType:'CSEv1r1',cseKey:'synthetic-key'};
        },
        async decrypt(value) {
            decrypts.push(clone(value));
            if(options.decrypt) return options.decrypt(value);
            for(const key of ['password','label','username','customFields','url','notes']) {
                if(typeof value[key]==='string' && value[key].startsWith('enc:')) value[key]=value[key].slice(4);
            }
            return value;
        },
        unsetKeychain(){unset++;}
    };
    const provider = {
        getId:()=> 'synthetic-factor', getType:()=> options.providerType || 'user-token',
        getLabel:()=> 'Synthetic factor', requiresRequest:()=> !!options.providerRequest,
        setToken(value){ this.value=value; }
    };
    const auth = {
        async load(){calls.push({path:'session/request'}); if(options.load) await options.load();},
        requiresChallenge:()=>!!options.challenge, requiresToken:()=>!!options.twoFactor,
        getChallenge:()=> options.challenge ? {} : null, getTokens:()=>[provider],
        async authorize(password,id){calls.push({path:'session/open'}); if(options.authorize) await options.authorize(password,id);}
    };
    const client = {
        getSessionAuthorization:()=>auth, getCseV1Encryption:()=>encryption, renewSession(){},
        getRequest(){
            let path, method='GET', data, accepted;
            const request = {
                setPath(v){path=v;return this;},setMethod(v){method=v;return this;},setData(v){data=v;return this;},
                setAcceptedStatusCodes(v){accepted=v;return this;},
                async send(){
                    assertOtpApiOperation(path,method,client);
                    const call={path,method,data:data?clone(data):undefined,accepted}; calls.push(call);
                    if(options.onRequest){ const result=await options.onRequest(call,{records,encryption}); if(result!==undefined) return {getData:()=>clone(result)}; }
                    if(path==='1.0/session/request') return {getData:()=>({})};
                    if(path==='1.0/settings/list') return {getData:()=>({'user.encryption.cse':options.mode ?? 0})};
                    if(path==='1.0/password/list') return {getData:()=>clone(records)};
                    if(path==='1.0/password/create'){
                        const record={...clone(data),id:'new-'+(++sequence),revision:'rev-'+sequence}; records.push(record);
                        const acknowledgement={id:record.id,revision:record.revision};
                        if(options.afterCommit) await options.afterCommit(record,records);
                        return {getData:()=>acknowledgement};
                    }
                    if(path==='1.0/session/close') return {getData:()=>({success:true})};
                    throw Error('unexpected synthetic route');
                }
            };return request;
        }
    };
    const session=new OtpVaultSession(client,{subtle:webcrypto.subtle,decryptTimeoutMs:options.decryptTimeoutMs ?? 50});
    return {session,client,auth,provider,calls,records,encryption,decrypts,unsets:()=>unset,
        async ready(){await session.begin(); if(options.challenge||options.twoFactor) await session.unlock({password:'synthetic-master-password',providerId:'synthetic-factor',otpCode:'654321'});return session;},
        writes:()=>calls.filter(x=>x.path==='1.0/password/create')};
}
export const record = (id='one', overrides={}) => ({...buildNewOtpValues(synthetic()),id,revision:'rev-initial',...overrides});
export class Element {
    constructor(tag='div'){this.tagName=tag;this.children=[];this.textContent='';this.hidden=false;this.disabled=false;this.attributes={};this.events={};}
    append(...nodes){this.children.push(...nodes);} replaceChildren(...nodes){this.children=nodes;}
    setAttribute(name,value){this.attributes[name]=value;} addEventListener(name,fn){this.events[name]=fn;}
}
export function dom() {
    const doc={hidden:false,createElement:tag=>new Element(tag)};
    const nodes=Object.fromEntries(['section','list','search','count','invalid','empty','feedback'].map(key=>[key,new Element()]));
    const find=(className,node=nodes.list)=>node.className===className?node:node.children.map(child=>find(className,child)).find(Boolean);
    return {doc,nodes,find};
}
