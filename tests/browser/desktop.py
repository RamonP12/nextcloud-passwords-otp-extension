#!/usr/bin/env python3
"""Production Vue bundle + real pinned client, libsodium and browser WebCrypto.
Only HTTP responses and the Nextcloud shell are synthetic. No runtime module
replacement, fake DOM, crypto substitute or test hooks in production sources.
This is separate from tests/integration/ against an actual Nextcloud server.
"""
from __future__ import annotations
import argparse, base64, hashlib, json, os, pathlib, re, shutil
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect
ROOT = pathlib.Path(__file__).resolve().parents[2]
ORIGIN = 'https://fixture.invalid'
PREFIX = '/nextcloud'
PAGE = PREFIX + '/index.php/apps/passwords_otp/'
FP = 'a' * 64
SECRET = 'JBSWY3DPEHPK3PXP'
TIME = 1735689601000


def encoded(value):
    return base64.b64encode(json.dumps(value).encode()).decode()


def shell(theme='light', direction='ltr'):
    state = {'status': 'ready', 'bootstrapUrl': PREFIX + '/apps/passwords_otp/bootstrap',
             'sessionStatusUrl': PREFIX + '/apps/passwords_otp/session-status', 'sessionFingerprint': FP}
    template = re.sub(r'<\?php.*?\?>', '', (ROOT/'templates/main.php').read_text(), flags=re.S)
    css = (ROOT/'tests/browser/shell.css').read_text()
    return f'''<!doctype html><html lang="de" dir="{direction}" data-theme="{theme}"><head data-requesttoken="SYNTHETIC-CSRF">
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>OTP fixture</title>
<style>{css}</style><link rel="stylesheet" href="{PREFIX}/apps/passwords_otp/css/app-111.css"></head>
<body><header id="header">Nextcloud fixture</header><div id="skip-actions"></div><div id="content">
<input type="hidden" id="initial-state-passwords_otp-ap1" value="{encoded(state)}">
<input type="hidden" id="initial-state-core-capabilities" value="{encoded({'theming': {'name': 'Nextcloud fixture'}})}">
<input type="hidden" id="initial-state-core-apps" value="{encoded([{'id': 'passwords_otp', 'name': 'Passwort OTP Code Generator'}])}">
{template}</div><script type="module" src="{PREFIX}/apps/passwords_otp/js/app-111.mjs"></script></body></html>'''


def record(identifier='seed', title='Fixture account'):
    return {'id': identifier, 'revision': 'r0', 'label': title, 'username': 'test@example.invalid',
            'password': 'SYNTHETIC-EXISTING', 'cseType': 'none',
            'customFields': json.dumps([{'label': 'client.ios.otp', 'type': 'data', 'value': json.dumps({
                'secret': SECRET, 'type': 'totp', 'algorithm': 'sha1', 'digits': 6, 'period': 30,
                'issuer': 'Fixture', 'accountName': 'test@example.invalid'})}])}


class Fixture:
    def __init__(self, browser, *, theme='light', width=1280, height=900, direction='ltr', auth=False, records=None):
        self.context = browser.new_context(viewport={'width': width, 'height': height},
                                          color_scheme='dark' if theme == 'dark' else 'light', locale='de-CH')
        self.active = True
        self.expired = False
        self.rate = 0
        self.uncertain = False
        self.created = 0
        self.auth = auth
        self.authorized = not auth
        self.wrong_master = False
        self.records = [record()] if records is None else records
        self.unexpected = []
        self.calls = []
        self.errors = []
        self.page = self.context.new_page()
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.add_init_script(f'''
window.OC = {{config: {{version: '35.0.2.2'}}, filePath: (app, dir, file) => '{PREFIX}/apps/' + app + '/' + file}};
window._oc_webroot = '{PREFIX}'; window._oc_user = 'fixture'; window._oc_isadmin = false;
window.__otpTestTime = {TIME}; Date.now = () => window.__otpTestTime;
window.__copied = []; window.__clipboardFailure = false;
Object.defineProperty(navigator, 'clipboard', {{value: {{writeText(value) {{
    if (window.__clipboardFailure) return Promise.reject(new Error('synthetic permission denial'));
    window.__copied.push(value); return Promise.resolve();
}}}}}});
''')
        self.html = shell(theme, direction)
        self.page.route('**/*', self.route)
        self.page.goto(ORIGIN + PAGE)
        expect(self.page.locator('#passwords-otp-ap1-status')).to_contain_text(
            'Authentifizierung erforderlich' if auth else 'OTP-Konten geladen.', timeout=20000)
        if not auth and self.records:
            expect(self.page.locator('.passwords-otp-ap3__code').first).to_have_text(re.compile(r'^\d{6}$'))
        self.page.evaluate('''() => {
            window.__vueFailures = [];
            const app = document.getElementById('passwords-otp-app').__vue_app__;
            const handler = app.config.errorHandler;
            app.config.errorHandler = (error, instance, info) => {
                window.__vueFailures.push({message: String(error), info, stack: error.stack});
                handler(error, instance, info);
            };
        }''')

    def route(self, route):
        req = route.request
        path = urlparse(req.url).path
        if path == PAGE:
            route.fulfill(body=self.html, content_type='text/html', headers={
                'Content-Security-Policy': "default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self' data:; base-uri 'none'"})
            return
        for name, mime in [('js/app-111.mjs', 'text/javascript'), ('css/app-111.css', 'text/css')]:
            if path == PREFIX + '/apps/passwords_otp/' + name:
                route.fulfill(body=(ROOT/name).read_bytes(), content_type=mime)
                return
        self.calls.append((path, req.method))
        status = 200
        if path.endswith('/session-status'):
            value = {'authenticated': self.active, 'sessionFingerprint': FP}
            status = 200 if self.active else 403
        elif path.endswith('/bootstrap'):
            assert req.method == 'POST'
            assert req.headers.get('x-passwords-otp-session') == FP
            assert req.headers.get('requesttoken') == 'SYNTHETIC-CSRF'
            value = {'status': 'ready', 'login': 'fixture', 'token': 'SYNTHETIC-TOKEN', 'sessionFingerprint': FP,
                     'sessionRequestUrl': PREFIX + '/index.php/apps/passwords/api/1.0/session/request',
                     'sessionOpenUrl': PREFIX + '/index.php/apps/passwords/api/1.0/session/open',
                     'passwordListUrl': PREFIX + '/index.php/apps/passwords/api/1.0/password/list'}
        elif path.startswith(PREFIX + '/index.php/apps/passwords/api/'):
            assert req.headers.get('authorization', '').startswith('Basic ')
            if path.endswith('/session/request'):
                if self.rate:
                    status, value = self.rate, {'message': 'synthetic rate limit'}
                elif self.expired:
                    status, value = 401, {'message': 'synthetic expiry'}
                elif self.auth and not self.authorized:
                    value = {'challenge': {'type': 'PWDv1r1', 'salts': ['01'*256, '02'*64, '03'*16]},
                             'token': [{'type': 'user-token', 'id': 'factor', 'label': 'Synthetic factor', 'request': False}]}
                else:
                    value = {}
            elif path.endswith('/session/open'):
                if self.auth:
                    data = req.post_data_json
                    assert re.fullmatch('[a-f0-9]{64}', data['challenge'])
                    assert data['token'] == {'factor': '654321'}
                if self.wrong_master:
                    self.wrong_master = False
                    status, value = 401, {'status': 'error', 'id': 'ab6e13ba', 'message': 'synthetic wrong master'}
                else:
                    self.authorized = True
                    value = {'success': True, 'keys': {}}
            elif path.endswith('/session/close'):
                value = {'success': True}
            elif path.endswith('/settings/list'):
                value = {'user.encryption.cse': 0}
            elif path.endswith('/password/list'):
                value = self.records
            elif path.endswith('/password/create'):
                assert req.method == 'POST'
                self.created += 1
                item = {**req.post_data_json, 'id': f'created-{self.created}', 'revision': 'r1'}
                self.records.append(item)
                if self.uncertain:
                    route.abort('failed')
                    return
                status, value = 201, {'id': item['id'], 'revision': 'r1'}
            else:
                self.unexpected.append(path)
                route.abort()
                return
        else:
            self.unexpected.append(path)
            route.abort()
            return
        route.fulfill(status=status, body=json.dumps(value), content_type='application/json',
                      headers={'x-api-session': 'SYNTHETIC-SESSION', 'cache-control': 'no-store'})

    def open(self):
        self.page.locator('#passwords-otp-ap12-open').click()
        try:
            expect(self.page.get_by_role('dialog')).to_be_visible()
        except AssertionError as error:
            raise AssertionError(str(error) + '\nHandled Vue failures: ' + json.dumps(self.page.evaluate('__vueFailures'))) from error
        expect(self.page.locator('#passwords-otp-ap12-label')).to_be_focused()

    def fill(self, label='New fixture', secret=SECRET):
        for field, value in [('label', label), ('password', 'SYNTHETIC-ONLY'), ('secret', secret)]:
            self.page.locator('#passwords-otp-ap12-' + field).fill(value)

    def save(self):
        self.page.locator('#passwords-otp-ap12-save').click()

    def close(self):
        assert not self.errors, self.errors
        assert not self.page.evaluate('__vueFailures'), self.page.evaluate('__vueFailures')
        assert not self.unexpected, self.unexpected
        # Secret fields, codes and tokens never enter browser persistence.
        storage = self.page.evaluate('JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage)])')
        for marker in [SECRET, 'SYNTHETIC-TOKEN', 'SYNTHETIC-ONLY']:
            assert marker not in storage
        self.page.evaluate("window.dispatchEvent(new Event('pagehide'))")
        self.context.close()


def no_overflow(page):
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    assert page.locator('#app-content-vue').evaluate('(el) => el.scrollWidth <= el.clientWidth + 1')


def accessibility(page):
    # Contrast is measured in the completed visual state. Keyboard lifecycle
    # tests deliberately do not wait for these entrance transitions.
    page.evaluate('''async () => Promise.all(document.getAnimations()
        .filter(animation => animation.effect.getComputedTiming().iterations !== Infinity)
        .map(animation => animation.finished.catch(() => {})))''')
    page.evaluate((ROOT/'node_modules/axe-core/axe.min.js').read_text())
    result = page.evaluate('''async () => {
        const report = await axe.run({include: ['#passwords-otp-app', '#passwords-otp-dialog-host']},
            {runOnly: {type:'tag', values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}});
        return report.violations.map(item => ({id:item.id, impact:item.impact,
            nodes:item.nodes.map(node => ({target:node.target, summary:node.failureSummary}))}));
    }''')
    assert not result, json.dumps(result, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', default='.build/browser')
    ap.add_argument('--browser', choices=['chromium', 'firefox'], default='chromium')
    args = ap.parse_args()
    out = pathlib.Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    results = []
    asset_hashes = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                    for name in ['js/app-111.mjs', 'css/app-111.css']}
    executable = os.environ.get('CHROME_BIN') or shutil.which('chromium-headless-shell') or shutil.which('chromium') or shutil.which('google-chrome')
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True) if args.browser == 'firefox' else p.chromium.launch(executable_path=executable, headless=True, args=['--no-sandbox'])
        def passed(name):
            results.append({'name': name, 'status': 'PASS'})
            print('BROWSER_PASS', name, flush=True)
        # Actual precompiled release modules, real browser crypto and real upstream client.
        f = Fixture(browser)
        page = f.page
        expect(page.get_by_role('heading', level=1)).to_have_text('Passwort OTP Code Generator')
        assert page.locator('#passwords-otp-app').get_attribute('data-js-build') == 'PASSWORDS_OTP_JS_111_VERIFIED'
        code = page.locator('.passwords-otp-ap3__code').inner_text()
        page.get_by_role('button', name='Code kopieren für Fixture account').click()
        expect(page.locator('#passwords-otp-ap3-feedback')).to_have_text('OTP-Code kopiert.')
        assert page.evaluate('__copied') == [code]
        page.evaluate('__clipboardFailure = true')
        page.get_by_role('button', name='Code kopieren für Fixture account').click()
        expect(page.locator('#passwords-otp-ap3-feedback')).to_contain_text('Kopieren nicht möglich')
        f.open()
        for _ in range(12):
            page.keyboard.press('Tab')
            assert page.get_by_role('dialog').evaluate('(el) => el.contains(document.activeElement)')
        f.fill()
        page.keyboard.press('Enter')
        assert f.created == 0
        page.keyboard.press('Escape')
        expect(page.get_by_role('dialog')).to_have_count(0)
        expect(page.locator('#passwords-otp-ap12-open')).to_be_focused()
        f.open()
        expect(page.locator('#passwords-otp-ap12-secret')).to_have_value('')
        f.fill(secret='INVALID')
        f.save()
        expect(page.locator('#passwords-otp-ap12-feedback')).to_contain_text('Base32')
        expect(page.locator('#passwords-otp-ap12-secret')).to_have_attribute('aria-invalid', 'true')
        expect(page.locator('#passwords-otp-ap12-secret')).to_be_focused()
        assert f.created == 0
        f.fill()
        f.save()
        expect(page.locator('#passwords-otp-ap1-status')).to_contain_text('in Passwords gespeichert.')
        assert f.created == 1
        expect(page.locator('#passwords-otp-ap2-list li')).to_have_count(2)
        page.locator('#passwords-otp-ap2-search').fill('New')
        expect(page.locator('#passwords-otp-ap2-list li:visible')).to_have_count(1)
        f.open(); f.fill(label='Bank'); f.save()
        expect(page.locator('#passwords-otp-ap2-list li')).to_have_count(3)
        page.locator('#passwords-otp-ap2-search').fill('')
        expect(page.locator('#passwords-otp-ap2-list li:visible')).to_have_count(3)
        expect(page.locator('.passwords-otp-ap3__code').nth(2)).to_have_text(re.compile(r'^\d{6}$'))
        page.locator('#passwords-otp-ap2-search').fill('<img onerror=alert(1)>')
        expect(page.locator('#passwords-otp-ap2-list li:visible')).to_have_count(0)
        page.locator('#passwords-otp-ap2-search').fill('')
        f.close(); passed('copy-errors-create-validation-focus-filter')
        for mode in ['expired-open', 'expired-submit', 'rate403', 'rate429', 'uncertain', 'focus-revocation', 'pagehide-bfcache']:
            f = Fixture(browser)
            page = f.page
            if mode == 'expired-open':
                f.expired = True
                page.locator('#passwords-otp-ap12-open').click()
            elif mode.startswith('rate'):
                f.rate = int(mode[4:])
                page.locator('#passwords-otp-ap12-open').click()
            else:
                f.open(); f.fill()
                if mode == 'expired-submit':
                    f.expired = True; f.save()
                elif mode == 'uncertain':
                    f.uncertain = True; f.save()
                elif mode == 'focus-revocation':
                    f.active = False; page.evaluate("window.dispatchEvent(new Event('focus'))")
                else:
                    cleared = page.evaluate('''() => {
                        window.dispatchEvent(new Event('pagehide'));
                        const code = [...document.querySelectorAll('.passwords-otp-ap3__code')].every(el => !/\\d/.test(el.textContent));
                        const inputs = [...document.querySelectorAll('input[data-otp-secret]')].every(el => el.value === '');
                        const dialogHidden = document.getElementById('passwords-otp-dialog-host').hidden;
                        window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted:true}));
                        return code && inputs && dialogHidden;
                    }''')
                    assert cleared, 'security erasure must be synchronous, before Vue nextTick'
            expected = 'Passwords-API-Sitzung ist abgelaufen' if mode.startswith('expired') else 'begrenzt Anfragen' if mode.startswith('rate') else 'unklar' if mode == 'uncertain' else 'Nextcloud-Sitzung nicht mehr' if mode == 'focus-revocation' else 'Sitzung beendet'
            expect(page.locator('#passwords-otp-ap1-status')).to_contain_text(expected)
            expect(page.get_by_role('dialog')).to_have_count(0)
            expect(page.locator('#passwords-otp-ap2-list li')).to_have_count(0)
            expect(page.locator('#passwords-otp-ap1-reload')).to_be_visible()
            assert f.created == (1 if mode == 'uncertain' else 0)
            f.close(); passed(mode)
        f = Fixture(browser, auth=True)
        f.wrong_master = True
        for attempt in range(2):
            f.page.locator('#passwords-otp-ap1-password').fill('synthetic test master password')
            f.page.locator('#passwords-otp-ap1-code').fill('654321')
            f.page.get_by_role('button', name='Tresor entsperren').click()
            if attempt == 0:
                expect(f.page.locator('#passwords-otp-ap1-status')).to_contain_text('nicht akzeptiert')
                expect(f.page.locator('#passwords-otp-ap1-password')).to_be_focused()
                expect(f.page.locator('#passwords-otp-ap1-password')).to_have_value('')
        expect(f.page.locator('#passwords-otp-ap1-status')).to_contain_text('OTP-Konten geladen.')
        expect(f.page.locator('.passwords-otp-ap3__code')).to_have_text(re.compile(r'^\d{6}$'))
        f.close(); passed('real-client-master-challenge-2fa-retry')
        f = Fixture(browser, records=[])
        expect(f.page.locator('#passwords-otp-ap2-empty')).to_contain_text('Keine TOTP-Konten')
        f.close(); passed('empty-vault')
        f = Fixture(browser)
        original = f.page.locator('.passwords-otp-ap3__code').inner_text()
        f.page.evaluate("window.dispatchEvent(new Event('focus')); window.dispatchEvent(new Event('focus'))")
        expect(f.page.locator('.passwords-otp-ap3__code')).to_have_text(original)
        expect(f.page.locator('.passwords-otp-ap3__copy')).to_be_enabled()
        f.page.evaluate("Object.defineProperty(document, 'hidden', {value:true, configurable:true}); document.dispatchEvent(new Event('visibilitychange'))")
        expect(f.page.locator('.passwords-otp-ap3__code')).to_have_text('—')
        f.page.evaluate("Object.defineProperty(document, 'hidden', {value:false, configurable:true}); document.dispatchEvent(new Event('visibilitychange'))")
        expect(f.page.locator('.passwords-otp-ap3__code')).to_have_text(original)
        expect(f.page.locator('.passwords-otp-ap3__copy')).to_be_enabled()
        f.close(); passed('same-code-focus-and-background-dom-repair')
        for theme in ['light', 'dark', 'brand']:
            for width, height in [(1440, 900), (1024, 768), (640, 450), (320, 720)]:
                f = Fixture(browser, theme=theme, width=width, height=height)
                no_overflow(f.page)
                if width == 1440:
                    accessibility(f.page)
                f.open()
                no_overflow(f.page)
                if width == 1440:
                    accessibility(f.page)
                box = f.page.get_by_role('dialog').bounding_box()
                assert box and box['width'] <= width + 1
                f.page.locator('#passwords-otp-ap12-cancel').click()
                expect(f.page.get_by_role('dialog')).to_have_count(0)
                if width == 1440:
                    f.page.screenshot(path=str(out / f'vue-{theme}.png'))
                f.close(); passed(f'layout-{theme}-{width}x{height}')
        f = Fixture(browser, direction='rtl', width=640)
        no_overflow(f.page); f.open(); no_overflow(f.page); f.close(); passed('rtl-reflow')
        from lifecycle import run_cases
        results.extend(run_cases(browser))
        browser.close()
    assert {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in asset_hashes} == asset_hashes, \
        'Compiled assets changed during the browser run; rebuild and rerun the suite'
    report = {'scope': 'Production compiled Vue assets, real pinned client/libsodium/browser WebCrypto; synthetic HTTPS API/shell/clipboard only',
              'browser': args.browser, 'results': results, 'native_browser_zoom_tested': False,
              'sha256': asset_hashes}
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(f'BROWSER_SUITE_PASS cases={len(results)}')

if __name__ == '__main__':
    main()
