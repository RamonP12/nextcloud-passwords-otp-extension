// Synthetic protocol fixture only. Not a substitute for the genuine pinned PasswordsClient/CSE test.
import {assertOtpApiOperation} from '/src/ap12/api-policy.mjs';
import {boundedRequest,abortClientRequests} from '/src/ap1/network.mjs';
export const sodiumReady=async()=>{};
export function createClient(config){
 const client={
  getSessionAuthorization(){return {
   async load(){await client.getRequest().setPath('1.0/session/request').send();},
   requiresChallenge:()=>false,requiresToken:()=>false,
   async authorize(){await client.getRequest().setPath('1.0/session/open').setMethod('POST').send();}
  };},
  getCseV1Encryption(){return {unsetKeychain(){}};},renewSession(){},
  getRequest(){let path,method='GET',data,accepted=null;return {
   setPath(v){path=v;return this;},setMethod(v){method=v;return this;},setData(v){data=v;return this;},setAcceptedStatusCodes(v){accepted=v;return this;},
   async send(){assertOtpApiOperation(path,method,client);return boundedRequest(client,async signal=>{
    const response=await fetch('/index.php/apps/passwords/api/'+path,{method,body:data?JSON.stringify(data):undefined,
     headers:{'content-type':'application/json',authorization:'Basic '+btoa(config.user+':'+config.token)},credentials:'omit',cache:'no-store',redirect:'error',signal});
    if(!(accepted?accepted.includes(response.status):response.ok))throw {status:response.status};
    const result=await response.json();return {getData:()=>result};
   });}
  };}
 };return client;
}
