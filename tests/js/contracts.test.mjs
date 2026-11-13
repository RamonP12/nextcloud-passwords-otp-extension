import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,readdirSync,existsSync} from 'node:fs';
import {join} from 'node:path';
const root=new URL('../../',import.meta.url);
const read=p=>readFileSync(new URL(p,root),'utf8');
function sources(path){return readdirSync(new URL(path,root),{withFileTypes:true}).flatMap(entry=>entry.isDirectory()?sources(path+'/'+entry.name):[path+'/'+entry.name]);}
test('Version and asset references agree; dependency graph is pinned',()=>{
 const pkg=JSON.parse(read('package.json')),lock=JSON.parse(read('package-lock.json'));
 assert.equal(pkg.version,'1.0.1');assert.equal(lock.version,pkg.version);assert.equal(lock.packages[''].version,pkg.version);
 assert.deepEqual(pkg.dependencies,lock.packages[''].dependencies);assert.deepEqual(pkg.devDependencies,lock.packages[''].devDependencies);
 assert.equal(read('appinfo/info.xml').match(/<version>([^<]+)<\/version>/)?.[1],pkg.version);
 assert.equal(read('templates/main.php').match(/data-template-build="([^"]+)"/)?.[1],pkg.version);
 assert.equal(read('scripts/release.py').match(/^VERSION='([^']+)'/m)?.[1],pkg.version);
 assert.match(read('src/ap1/index.js'),/PASSWORDS_OTP_JS_101_VERIFIED/);assert.match(read('css/app-101.css'),/PASSWORDS_OTP_CSS_101_VERIFIED/);
 assert.equal((read('lib/Controller/PageController.php').match(/'app-101'/g)||[]).length,2);
 // 1.0.1 is a metadata/asset-version hotfix. The only runtime changes are the versioned asset names and build-marker text; business logic remains unchanged.
 assert.match(read('appinfo/info.xml'),/<bugs>https:\/\/github\.com\/RamonP12\/nextcloud-passwords-otp-extension\/issues<\/bugs>/);
 assert.ok(read('appinfo/info.xml').indexOf('</category>')<read('appinfo/info.xml').indexOf('<bugs>'));
 assert.ok(read('appinfo/info.xml').indexOf('</bugs>')<read('appinfo/info.xml').indexOf('<repository>'));
});
test('Removed event-counter implementation and versioned installers are absent',()=>{
 for(const path of ['src/ap4','src/release-policy.mjs','js/ap0.js','css/ap0.css','css/ap053.css','css/ap060.css','css/ap061.css','scripts/local-061-build-install.sh','scripts/matrix.py','tests/integration/e2e.mjs']) {
  assert.equal(existsSync(new URL(path,root)),false,path);
 }
 const code=sources('src').map(read).join('\n');assert.doesNotMatch(code,/hotpNext|importHotpKey|calculateHotp|OTP_HOTP_WRITE_TEST_ONLY|hotp-commit|passwords-otp-ap4/i);
});
test('Own runtime contains no console logging, HTML injection or persistent secret storage',()=>{
 const code=sources('src').map(read).join('\n');
 assert.doesNotMatch(code,/console\.(log|debug|error|warn)|\.innerHTML\s*=|insertAdjacentHTML|localStorage|sessionStorage|indexedDB|BroadcastChannel|SharedWorker|document\.cookie/);
});
test('Creation remains the only own password mutation endpoint',()=>{
 const code=sources('src').map(read).join('\n');assert.doesNotMatch(code,/password\/update|password\/delete|share\/create|share\/update|folder\/update/);
 assert.match(read('src/ap1/session.mjs'),/setAcceptedStatusCodes\(\[201\]\)/);
 assert.match(read('src/ap1/session.mjs'),/#createBlocked/);
});
test('Browser dialog is closed initially, scoped, modal and keyboard-cycle constrained',()=>{
 const tag=read('templates/main.php').match(/<dialog\b[^>]*>/s)?.[0];assert.ok(tag);assert.doesNotMatch(tag,/\sopen(?:\s|=|>)/);
 const css=read('css/app-101.css');assert.match(css,/:not\(\[open\]\)\s*\{display:none!important/);assert.match(css,/position:fixed;inset:0;margin:auto/);
 assert.match(read('src/ap1/index.js'),/event\.key !== 'Tab'/);assert.match(read('src/ap1/index.js'),/event\.persisted/);
});
test('Only current browser asset is built and no runtime test loader is used',()=>{
 const pkg=JSON.parse(read('package.json'));assert.match(pkg.scripts.build,/outfile=js\/app-101\.js/);
 assert.doesNotMatch(pkg.scripts.build,/reference|fixture|ap1\.js|ap061/);
 assert.doesNotMatch(sources('src').map(read).join('\n'),/__otpReferenceDependencies|fixture-client|__cryptoFixture/);
});

test('1.0.1 keeps the test badges, counters and manual lock REMOVED',()=>{
 const template=read('templates/main.php'), code=read('src/ap1/index.js');
 assert.doesNotMatch(template,/passwords-otp-ap0__(?:version|notice|metrics|metric)|Desktop-Testversion|isolierte Tests/);
 for(const id of ['passwords-otp-ap1-count','passwords-otp-ap1-cse','passwords-otp-ap2-count','passwords-otp-ap2-invalid','passwords-otp-ap1-lock']) {
  assert.ok(!template.includes('id="'+id+'"'),id);
  assert.ok(!code.includes(id),id+' must not be queried');
 }
 assert.doesNotMatch(code,/countEl|cseEl|lockButton/);
 assert.doesNotMatch(read('css/app-101.css'),/passwords-otp-ap0__(?:version|notice|metrics|metric)/);
});
test('1.0.1 uses the exact requested German title, subtitle and explanatory copy',()=>{
 const template=read('templates/main.php');
 assert.ok(template.includes('<h2>Passwort OTP Code Generator</h2>'));
 assert.ok(template.includes('OTP-Codes aus deinen eigenen gespeicherten OTP-Passw\u00f6rtern sowie aus den mit dir geteilten OTP-Passw\u00f6rtern'));
 assert.ok(template.includes('Hier kann ein neuer OTP Eintrag zu deinen Passw\u00f6rtern hinzugef\u00fcgt werden. Er wird in der Passwords App gespeichert und kann \u00fcber diese App auch verwaltet (gel\u00f6scht, ver\u00e4ndert) und mit anderen NextCloud Benutzern geteilt werden.'));
 assert.equal(template.split('Neues OTP Passwort hinzuf\u00fcgen').length-1,2);
 assert.ok(template.indexOf('id="passwords-otp-ap12-help"')>template.indexOf('id="passwords-otp-ap12-open"'));
 assert.doesNotMatch(template,/Add new OTP Password/);
});
test('1.0.1 retains automatic auth guards, page disposal and administrative version',()=>{
 const code=read('src/ap1/index.js');
 for(const fragment of ['makeSessionCheck','await requireSession()','verifySession','visibilitychange',"addEventListener('focus'","addEventListener('pagehide'",'session?.dispose()','event.persisted'])assert.ok(code.includes(fragment),fragment);
 assert.match(read('appinfo/info.xml'),/<id>passwords_otp<\/id>/);
 assert.equal(read('appinfo/info.xml').match(/<version>([^<]+)<\/version>/)?.[1],JSON.parse(read('package.json')).version);
});
test('Branch upgrade keeps previously generated assets ignored, without shipping them',()=>{
 const ignore=read('.gitignore').split('\n');
 assert.ok(ignore.includes('js/app-*.js'));
 assert.ok(ignore.includes('js/app-*.js.LEGAL.txt'));
 assert.doesNotMatch(JSON.parse(read('package.json')).scripts.build,/app-070/);
});

test('Creating after idle is guarded by authorized Passwords API, not by keepalive-only',()=>{
 const code=read('src/ap1/index.js'),session=read('src/ap1/session.mjs');
 assert.match(code,/await session\.assertCreateAccess\(\)/);
 assert.match(session,/setPath\('1\.0\/session\/request'\)/);
 assert.match(session,/await this\.assertCreateAccess\(\);[\s\S]{0,90}attempted = true/);
 assert.match(code,/passwords-session-expired/);
});

test('Security and UX review: rate-limit, search filter, CSE retry, best-effort close',()=>{
 const ui=read('src/ap1/index.js'),session=read('src/ap1/session.mjs'),view=read('src/ap2/view.mjs');
 assert.match(ui,/presenter\?\.filter\(otpNodes\.search\.value\)/);
 assert.match(ui,/error\?\.code === 'auth-rate-limited'/);
 assert.match(ui,/void session\?\.close\(\)/);
 assert.match(ui,/error\?\.code === 'invalid-master-key'/);
 assert.match(session,/body\?\.id === 'ab6e13ba'/);
 assert.match(session,/safeStatusCode\(error\) !== 401/);
 assert.doesNotMatch(session,/body\?\.id === '033d1943'/);
 assert.match(view,/unsupportedOtpCount/);
});
test('Opening create dialog checks rate limit BEFORE disposed catch; no duplicate submit branch',()=>{
 const code=read('src/ap1/index.js');
 const start=code.indexOf("createButton.addEventListener('click'");
 const end=code.indexOf("createCancel.addEventListener('click'",start);
 const handler=code.slice(start,end);
 assert.ok(start>=0 && end>start);
 assert.ok(handler.indexOf("error?.code === 'auth-rate-limited'")>=0);
 assert.ok(handler.indexOf("error?.code === 'auth-rate-limited'")<handler.indexOf('} else if (session.disposed ||'));
 assert.equal((code.match(/else if \(error\?\.code === 'auth-rate-limited'\)/g)||[]).length,2);
});
test('Full snapshot render creates all OTP rows before filtering; Chromium uses current CSS',()=>{
 const presenter=read('src/ap3/ui.mjs');
 assert.match(presenter,/renderOtpView\(snapshot, '', this\.nodes, this\.doc/);
 assert.match(presenter,/this\.filter\(query\)/);
 assert.match(read('tests/browser/desktop.py'),/css\/app-101\.css/);
});
