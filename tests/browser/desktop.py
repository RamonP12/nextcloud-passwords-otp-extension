#!/usr/bin/env python3
"""Offline real Chromium DOM/native-dialog tests, actual app modules/template/CSS.
Only ESM linkage is adapted. Network, origin and crypto transport are synthetic
fixtures. This is NOT a real Nextcloud, real upstream-client or WebCrypto gate.
"""
from __future__ import annotations
import argparse, base64, hashlib, hmac, json, os, pathlib, re, shutil
from playwright.sync_api import sync_playwright, expect
ROOT=pathlib.Path(__file__).resolve().parents[2]
FP='a'*64
SECRET='JBSWY3DPEHPK3PXP'

def bundle():
    modules={};order=[]
    def visit(name):
        name=pathlib.PurePosixPath(name).as_posix()
        if name in modules:return
        text=(ROOT/name).read_text()
        if name=='src/ap1/upstream.js':text=(ROOT/'tests/browser/fixture-client.js').read_text()
        dependencies=[]
        def import_line(match):
            names,path=match.groups()
            target=(ROOT/path.lstrip('/')).resolve() if path.startswith('/') else (ROOT/name).parent.joinpath(path).resolve()
            target=target.relative_to(ROOT).as_posix();dependencies.append(target)
            return 'const {'+names+'} = modules['+json.dumps(target)+'];'
        text=re.sub(r"import\s*\{([^}]+)\}\s*from\s*['\"]([^'\"]+)['\"];",import_line,text,flags=re.S)
        exports=re.findall(r'export\s+(?:async\s+)?(?:class|function|const|let)\s+(\w+)',text)
        text=re.sub(r'\bexport\s+(?=(?:async\s+)?(?:class|function|const|let)\b)','',text)
        if re.search(r'^\s*(import|export)\b',text,re.M):raise ValueError('unsupported fixture linkage '+name)
        modules[name]=text
        for dependency in dependencies:visit(dependency)
        order.append((name,text,exports))
    visit('src/ap1/index.js')
    return '\n'.join('modules['+json.dumps(name)+']=(()=>{\n'+text+'\nreturn {'+','.join(exports)+'};})();' for name,text,exports in order)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',default='/tmp/passwords-otp-browser');args=ap.parse_args()
    out=pathlib.Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    template=re.sub(r'<\?php.*?\?>','',(ROOT/'templates/main.php').read_text(),flags=re.S)
    state={'status':'ready','bootstrapUrl':'https://fixture.invalid/apps/passwords_otp/bootstrap',
        'sessionStatusUrl':'https://fixture.invalid/apps/passwords_otp/session-status','sessionFingerprint':FP}
    initial=base64.b64encode(json.dumps(state).encode()).decode()
    html=f'''<!doctype html><html><head data-requesttoken="synthetic-csrf-token"><meta charset="utf-8"><style>
    body{{margin:0;font-family:Arial,sans-serif}}dialog{{display:block}}
    {(ROOT/'css/app-101.css').read_text()}</style></head><body>
    <input type="hidden" id="initial-state-passwords_otp-ap1" value="{initial}">{template}</body></html>'''
    runtime=bundle();passed=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROME_BIN') or shutil.which('chromium') or shutil.which('google-chrome') or shutil.which('brave') or shutil.which('brave-browser'),headless=True,args=['--no-sandbox'])
        for theme in ['light','dark']:
            for width,height in [(1440,900),(1366,768),(1024,768),(720,450)]:
                context=browser.new_context(viewport={'width':width,'height':height},color_scheme=theme)
                errors=[];page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
                # All browser network is forbidden; the protocol fixture below never reaches fetch.
                page.route('**/*',lambda route:route.abort())
                keys={}
                def crypto_call(operation,args):
                    if operation=='import':
                        key=str(len(keys)+1);keys[key]=bytes(args['bytes']);return key
                    if operation=='digest':return list(hashlib.new(args['hash'].replace('-','').lower(),bytes(args['bytes'])).digest())
                    return list(hmac.new(keys[args['key']],bytes(args['bytes']),args['hash'].replace('-','').lower()).digest())
                page.expose_function('__cryptoFixture',crypto_call)
                page.set_content(html)
                if theme=='dark':page.add_style_tag(content=':root{--color-main-background:#202020;--color-main-text:#eeeeee;--color-border:#444;--color-border-dark:#888;--color-background-hover:#292929;--color-text-maxcontrast:#bbb;}')
                prelude=r'''
                const modules={};
                const realWindow=globalThis.window;
                const window={location:{origin:'https://fixture.invalid',href:'https://fixture.invalid/apps/passwords_otp/',reload(){globalThis.__fixture.reloadRequested=true;}},
                    addEventListener:realWindow.addEventListener.bind(realWindow)};
                const subtle={async importKey(format,bytes,algorithm,extractable,uses){return {handle:await __cryptoFixture('import',{bytes:[...bytes]}),hash:algorithm.hash.name,extractable:false};},
                    async sign(algorithm,key,bytes){return new Uint8Array(await __cryptoFixture('sign',{key:key.handle,hash:key.hash,bytes:[...bytes]})).buffer;},
                    async digest(hash,bytes){return new Uint8Array(await __cryptoFixture('digest',{hash,bytes:[...bytes]})).buffer;}};
                Object.defineProperty(globalThis.crypto,'subtle',{value:subtle,configurable:true});
                const otp={secret:'JBSWY3DPEHPK3PXP',type:'totp',algorithm:'sha1',digits:6,period:30,issuer:'Fixture',accountName:'test@example.invalid'};
                const data=globalThis.__fixture={active:true,created:0,failCreate:false,passwordsTokenExpired:false,passwordsNeedsAuth:false,passwordsRateLimited:false,passwordsRateLimitStatus:403,records:[{id:'seed',revision:'r0',label:'Fixture',username:'test@example.invalid',password:'synthetic',cseType:'none',customFields:JSON.stringify([{label:'client.ios.otp',type:'data',value:JSON.stringify(otp)}])}]};
                const reply=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'content-type':'application/json'}});
                const fetch=async (url,options={})=>{
                    const path=new URL(url,window.location.href).pathname;
                    if(path.endsWith('/session-status'))return reply({authenticated:data.active,sessionFingerprint:'a'.repeat(64)},data.active?200:403);
                    if(path.endsWith('/bootstrap')){
                        if(options.method!=='POST'||options.headers['X-Passwords-OTP-Session']!=='a'.repeat(64)||!options.headers.requesttoken)throw Error('bad bootstrap');
                        return reply({status:'ready',login:'synthetic',token:'SYNTHETIC-TOKEN',sessionFingerprint:'a'.repeat(64),
                            sessionRequestUrl:'/index.php/apps/passwords/api/1.0/session/request',sessionOpenUrl:'/index.php/apps/passwords/api/1.0/session/open',passwordListUrl:'/index.php/apps/passwords/api/1.0/password/list'});
                    }
                    if(path.endsWith('/session/request'))return data.passwordsRateLimited ? reply({message:'rate limited'},data.passwordsRateLimitStatus) : data.passwordsTokenExpired ? reply({message:'expired'},401) : reply(data.passwordsNeedsAuth ? {challenge:{type:'PWDv1r1'}} : {});
                    if(path.endsWith('/session/open')||path.endsWith('/session/close'))return reply({success:true});
                    if(path.endsWith('/settings/list'))return reply({'user.encryption.cse':0});
                    if(path.endsWith('/password/list'))return reply(data.records);
                    if(path.endsWith('/password/create')){
                        if(options.method!=='POST')throw Error('method');data.created++;
                        const rec={...JSON.parse(options.body),id:'created-'+data.created,revision:'r1'};data.records.push(rec);
                        if(data.failCreate)throw Error('synthetic lost acknowledgement');
                        return reply({id:rec.id,revision:rec.revision},201);
                    }
                    throw Error('unexpected fixture route');
                };
                '''
                page.evaluate('()=>{'+prelude+runtime+'}')
                expect(page.locator('#passwords-otp-ap1-status')).to_have_text('OTP-Konten erfolgreich geladen.')
                expect(page.locator('.passwords-otp-ap3__code')).to_have_text(re.compile(r'^\d{6}$'))
                expect(page.locator('h2')).to_have_text('Passwort OTP Code Generator')
                expect(page.locator('.passwords-otp-ap0__subtitle')).to_have_text('OTP-Codes aus deinen eigenen gespeicherten OTP-Passw\u00f6rtern sowie aus den mit dir geteilten OTP-Passw\u00f6rtern')
                expect(page.locator('#passwords-otp-ap12-help')).to_have_text('Hier kann ein neuer OTP Eintrag zu deinen Passw\u00f6rtern hinzugef\u00fcgt werden. Er wird in der Passwords App gespeichert und kann \u00fcber diese App auch verwaltet (gel\u00f6scht, ver\u00e4ndert) und mit anderen NextCloud Benutzern geteilt werden.')
                expect(page.locator('.passwords-otp-ap0__version,.passwords-otp-ap0__notice,.passwords-otp-ap0__metrics,#passwords-otp-ap1-lock,#passwords-otp-ap1-count,#passwords-otp-ap1-cse,#passwords-otp-ap2-count,#passwords-otp-ap2-invalid')).to_have_count(0)
                assert 'Testversion' not in page.locator('body').inner_text()
                assert '1.0.1' not in page.locator('body').inner_text()
                assert page.locator('#passwords-otp-app').get_attribute('data-template-build')=='1.0.1'
                modal=page.locator('#passwords-otp-ap12-dialog');opener=page.locator('#passwords-otp-ap12-open')
                expect(opener).to_have_text('Neues OTP Passwort hinzuf\u00fcgen')
                expect(page.locator('#passwords-otp-ap12-title')).to_have_text('Neues OTP Passwort hinzuf\u00fcgen')
                expect(modal).to_be_hidden();assert modal.evaluate('(el)=>getComputedStyle(el).display')=='none'
                opener.click();expect(modal).to_be_visible()
                geometry=modal.evaluate('(el)=>{const b=el.getBoundingClientRect();return {modal:el.matches(":modal"),x:b.x+b.width/2,y:b.y+b.height/2,overflow:document.documentElement.scrollWidth>innerWidth+1}}')
                assert geometry['modal'] and abs(geometry['x']-width/2)<3 and abs(geometry['y']-height/2)<3 and not geometry['overflow']
                expect(page.locator('#passwords-otp-ap12-label')).to_be_focused()
                page.locator('#passwords-otp-ap12-password').fill('SYNTHETIC-SECRET')
                page.keyboard.press('Escape');expect(modal).to_be_hidden();expect(page.locator('#passwords-otp-ap12-password')).to_have_value('');expect(opener).to_be_focused()
                opener.click();page.locator('#passwords-otp-ap12-cancel').click();expect(modal).to_be_hidden()
                opener.click();expect(modal).to_be_visible()
                for _ in range(10):
                    page.keyboard.press('Tab');assert page.evaluate('document.querySelector("dialog").contains(document.activeElement)'), page.evaluate('({tag:document.activeElement.tagName,id:document.activeElement.id})')
                page.locator('#passwords-otp-ap12-save').click();assert page.evaluate('__fixture.created')==0
                for field,value in [('label','Desktop synthetic'),('username','desktop@example.invalid'),('password','SYNTHETIC-ONLY'),('secret','INVALID')]:page.locator('#passwords-otp-ap12-'+field).fill(value)
                page.keyboard.press('Enter');assert page.evaluate('__fixture.created')==0
                page.locator('#passwords-otp-ap12-save').click();expect(page.locator('#passwords-otp-ap12-feedback')).to_contain_text('Base32');assert page.evaluate('__fixture.created')==0
                page.locator('#passwords-otp-ap12-password').fill('SYNTHETIC-ONLY');page.locator('#passwords-otp-ap12-secret').fill(SECRET)
                page.locator('#passwords-otp-ap12-save').click();expect(page.locator('#passwords-otp-ap1-status')).to_have_text('Neuer OTP-Eintrag erfolgreich in Passwords gespeichert.')
                expect(modal).to_be_hidden();expect(page.locator('#passwords-otp-ap2-list li')).to_have_count(2);assert page.evaluate('__fixture.created')==1
                page.locator('#passwords-otp-ap2-search').fill('<img onerror=alert(1)>');expect(page.locator('#passwords-otp-ap2-list li:visible')).to_have_count(0)
                page.locator('#passwords-otp-ap2-search').fill('Desktop');expect(page.locator('#passwords-otp-ap2-list li:visible')).to_have_count(1)
                expect(page.locator('#passwords-otp-ap2-list li:visible .passwords-otp-ap3__code')).to_have_text(re.compile(r'^\d{6}$'))
                if width==1024 and theme=='light':
                    # Regression: CREATE while search filters out Bank must still
                    # materialize every authorized row for a subsequent clear.
                    opener.click();expect(modal).to_be_visible()
                    for field,value in [('label','Bank'),('password','SYNTHETIC-ONLY'),('secret',SECRET)]:
                        page.locator('#passwords-otp-ap12-'+field).fill(value)
                    page.locator('#passwords-otp-ap12-save').click()
                    expect(page.locator('#passwords-otp-ap1-status')).to_have_text('Neuer OTP-Eintrag erfolgreich in Passwords gespeichert.')
                    expect(page.locator('#passwords-otp-ap2-list li')).to_have_count(3)
                    expect(page.locator('#passwords-otp-ap2-list li:visible')).to_have_count(1)
                    page.locator('#passwords-otp-ap2-search').fill('')
                    expect(page.locator('#passwords-otp-ap2-list li:visible')).to_have_count(3)
                    labels=page.locator('#passwords-otp-ap2-list li strong').all_text_contents()
                    assert sorted(labels)==sorted(['Fixture','Desktop synthetic','Bank']), labels
                    page.locator('#passwords-otp-ap2-search').fill('Desktop')
                    expect(page.locator('#passwords-otp-ap2-list li:visible')).to_have_count(1)
                    assert page.evaluate('__fixture.created')==2
                if width==1440:page.screenshot(path=str(out/f'desktop-{theme}.png'),full_page=True)
                if width==1440:
                    # Authorization expired while Nextcloud itself is still logged in.
                    page.evaluate('__fixture.passwordsNeedsAuth=true' if theme=='light' else '__fixture.passwordsTokenExpired=true')
                    opener.click()
                    expect(modal).to_be_hidden()
                    expect(page.locator('#passwords-otp-ap1-status')).to_contain_text('Passwords-API-Sitzung ist abgelaufen')
                    expect(page.locator('#passwords-otp-ap1-reload')).to_be_visible()
                    assert page.evaluate('__fixture.created')==1
                elif width==1024:
                    page.evaluate('__fixture.passwordsRateLimited=true; __fixture.passwordsRateLimitStatus='+('403' if theme=='light' else '429'))
                    opener.click()
                    expect(modal).to_be_hidden()
                    expect(page.locator('#passwords-otp-ap1-status')).to_contain_text('Passwords-API begrenzt Anfragen')
                    assert 'Nextcloud-Sitzung nicht mehr' not in page.locator('#passwords-otp-ap1-status').inner_text()
                    assert page.evaluate('__fixture.created')==(2 if theme=='light' else 1)
                elif width==720 and theme=='dark':
                    # Dialog opened with valid API auth, but it expires while typing.
                    opener.click();expect(modal).to_be_visible()
                    page.locator('#passwords-otp-ap12-label').fill('Expired while editing')
                    page.locator('#passwords-otp-ap12-password').fill('SYNTHETIC-ONLY')
                    page.locator('#passwords-otp-ap12-secret').fill(SECRET)
                    page.evaluate('__fixture.passwordsNeedsAuth=true')
                    page.locator('#passwords-otp-ap12-save').click()
                    expect(modal).to_be_hidden()
                    expect(page.locator('#passwords-otp-ap1-status')).to_contain_text('Passwords-API-Sitzung ist abgelaufen')
                    assert page.evaluate('__fixture.created')==1
                elif width==720:
                    page.evaluate('__fixture.failCreate=true');opener.click()
                    for field,value in [('label','Ambiguous synthetic'),('password','SYNTHETIC-ONLY'),('secret',SECRET)]:page.locator('#passwords-otp-ap12-'+field).fill(value)
                    page.locator('#passwords-otp-ap12-save').click();expect(page.locator('#passwords-otp-ap1-status')).to_contain_text('unklar')
                    expect(opener).to_be_hidden();expect(page.locator('#passwords-otp-ap2-section')).to_be_hidden();assert page.evaluate('__fixture.created')==2
                else:
                    opener.click()
                    page.locator('#passwords-otp-ap12-password').fill('SYNTHETIC-ONLY')
                    page.locator('#passwords-otp-ap12-secret').fill(SECRET)
                    if width==1366:
                        page.evaluate('__fixture.active=false; window.dispatchEvent(new Event("focus"))')
                        expect(page.locator('#passwords-otp-ap1-status')).to_contain_text('Nextcloud-Sitzung nicht mehr')
                    else:
                        page.evaluate('window.dispatchEvent(new Event("pagehide")); window.dispatchEvent(new PageTransitionEvent("pageshow",{persisted:true}))')
                        expect(page.locator('#passwords-otp-ap1-status')).to_contain_text('Sitzung beendet')
                    expect(modal).to_be_hidden();expect(opener).to_be_hidden()
                    expect(page.locator('#passwords-otp-ap2-list li')).to_have_count(0)
                    expect(page.locator('#passwords-otp-ap12-password')).to_have_value('')
                    expect(page.locator('#passwords-otp-ap12-secret')).to_have_value('')
                    expect(page.locator('#passwords-otp-ap1-reload')).to_be_visible()
                    assert page.evaluate('__fixture.created')==1
                assert not errors,errors
                page.evaluate('window.dispatchEvent(new Event("pagehide"))')
                passed.append({'theme':theme,'viewport':f'{width}x{height}','status':'PASS'})
                print('DESKTOP_PASS',theme,width,height,flush=True);context.close()
        browser.close()
    report={'scope':'offline real Chromium DOM; actual app modules/template/CSS; synthetic origin/network/crypto fixture; NOT real Nextcloud/pinned client/browser WebCrypto',
        'scenarios':passed,'native_browser_zoom_tested':False,'desktop_reflow_tested':True}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('DESKTOP_SUITE_PASS variants='+str(len(passed)))
if __name__=='__main__':main()
