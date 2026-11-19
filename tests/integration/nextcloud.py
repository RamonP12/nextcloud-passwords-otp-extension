#!/usr/bin/env python3
"""Acceptance against a real, disposable Nextcloud/Passwords installation.

No HTTP response, client, crypto, clipboard, clock or application module is mocked.
This creates synthetic Passwords records and changes the test user's theme.
See README.md for fixture requirements and environment variables.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import struct
import time
from urllib.parse import urljoin, urlparse

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
SEED = 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ'  # Public RFC 6238 SHA-1 test key.
SERVICE_PASSWORD = 'Synthetic-only-acceptance-service-password'


def required(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f'{name} is required; use a disposable fixture only')
    return value


def totp(milliseconds, secret=SEED):
    counter = int(milliseconds // 30000)
    digest = hmac.new(base64.b32decode(secret), struct.pack('>Q', counter), hashlib.sha1).digest()
    offset = digest[-1] & 15
    return str((struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7fffffff) % 1000000).zfill(6)


def settle_visual_transitions(page):
    # Contrast must be measured at the rendered end state, not during an opacity
    # fade. Keyboard tests intentionally do not call this helper.
    page.evaluate('''async () => {
        await Promise.all(document.getAnimations()
            .filter(animation => Number.isFinite(animation.effect?.getComputedTiming().endTime))
            .map(animation => animation.finished.catch(() => {})));
    }''')


def accessibility(page):
    settle_visual_transitions(page)
    page.evaluate((ROOT / 'node_modules/axe-core/axe.min.js').read_text())
    return page.evaluate('''async () => {
        const result = await axe.run({include: ['#passwords-otp-app', '#passwords-otp-dialog-host']},
            {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']}});
        const modalOpen = Boolean(document.querySelector('#passwords-otp-ap12-dialog'));
        return {passes: result.passes.length, incomplete: result.incomplete.map(item => item.id),
            manual_review: result.incomplete.map(item => ({id: item.id,
                classification: modalOpen && item.id === 'color-contrast' && item.nodes.every(node =>
                    node.target.length === 1 && document.querySelector(node.target[0])?.closest('#passwords-otp-app'))
                    ? 'background-covered-by-active-modal' : 'requires-manual-review',
                nodes: item.nodes.map(node => ({target: node.target, summary: node.failureSummary}))})),
            violations: result.violations.map(item => ({id: item.id, impact: item.impact,
                nodes: item.nodes.map(node => ({target: node.target, summary: node.failureSummary}))}))};
    }''')


class RealFixture:
    def __init__(self, browser, base, browser_name, *, locale='de-CH', app_language='de'):
        self.base = base
        self.origin = f'{urlparse(base).scheme}://{urlparse(base).netloc}'
        self.browser_name = browser_name
        self.app_language = app_language
        options = {'ignore_https_errors': os.environ.get('OTP_E2E_IGNORE_HTTPS_ERRORS') == '1',
                   'locale': locale, 'viewport': {'width': 1440, 'height': 900}}
        if browser_name == 'chromium':
            options['permissions'] = ['clipboard-read', 'clipboard-write']
        self.context = browser.new_context(**options)
        self.context.route('**/*', lambda route: route.continue_()
                           if urlparse(route.request.url).netloc == urlparse(base).netloc else route.abort())
        self.page = self.context.new_page()
        self.page.set_default_timeout(30000)
        self.errors = []
        self.creates = []
        self.list_metadata = []
        self.existing_record_mutations = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('request', self.record_request)
        self.page.on('response', self.record_response)
        self.page.add_init_script('''window.__otpAcceptanceCsp = [];
            document.addEventListener('securitypolicyviolation', event => {
                window.__otpAcceptanceCsp.push({directive: event.effectiveDirective,
                    application: event.blockedURI.includes('/passwords_otp/')});
            });''')

    def record_request(self, request):
        if re.search(r'/password/(update|delete|restore)$', urlparse(request.url).path):
            self.existing_record_mutations.append(request.method)
        if request.method == 'POST' and urlparse(request.url).path.endswith('/password/create'):
            # Bodies stay in process memory and are never written into evidence.
            data = request.post_data_json
            self.creates.append({'cse': data.get('cseType'),
                                 'contains_seed': SEED in json.dumps(data),
                                 'contains_password': SERVICE_PASSWORD in json.dumps(data)})

    def record_response(self, response):
        if response.status == 200 and urlparse(response.url).path.endswith('/password/list'):
            self.list_metadata = [{'label': item.get('label'), 'share': bool(item.get('share')),
                                   'editable': item.get('editable'), 'revision': item.get('revision')}
                                  for item in response.json()]

    def login(self, username, password):
        self.page.goto(self.base + '/index.php/login')
        self.page.locator('#user').fill(username)
        self.page.locator('#password').fill(password)
        self.page.locator('button[type=submit]').click()
        self.page.wait_for_url('**/apps/**')

    def app(self, ready=True):
        self.page.bring_to_front()
        response = self.page.goto(self.base + '/index.php/apps/passwords_otp/')
        assert response and response.status == 200
        if ready:
            expect(self.page.locator('#passwords-otp-ap1-status')).to_contain_text(
                'OTP-Konten geladen.' if self.app_language == 'de' else 'OTP accounts loaded.')
            if self.page.locator('#passwords-otp-ap2-list li').count():
                expect(self.page.locator('.passwords-otp-ap3__copy').first).to_be_enabled(timeout=45000)
        return response

    def open(self):
        self.page.locator('#passwords-otp-ap12-open').click()
        expect(self.page.locator('#passwords-otp-ap12-dialog')).to_be_visible()
        expect(self.page.locator('#passwords-otp-ap12-label')).to_be_focused()

    def create(self, name, encrypted=False):
        self.open()
        before = len(self.creates)
        for field, value in [('label', name), ('username', 'synthetic@example.invalid'),
                             ('password', SERVICE_PASSWORD), ('secret', SEED)]:
            self.page.locator('#passwords-otp-ap12-' + field).fill(value)
        self.page.keyboard.press('Enter')
        assert len(self.creates) == before, 'Enter in an input must not submit'
        self.page.locator('#passwords-otp-ap12-save').click()
        expect(self.page.locator('#passwords-otp-ap12-dialog')).to_be_hidden(timeout=45000)
        assert len(self.creates) == before + 1, 'Create must issue exactly one POST'
        saved = self.creates[-1]
        if encrypted:
            assert saved['cse'] == 'CSEv1r1', saved['cse']
            assert not saved['contains_seed'] and not saved['contains_password']
        else:
            assert saved['cse'] == 'none', saved['cse']
        row = self.page.locator('#passwords-otp-ap2-list li').filter(has_text=name)
        expect(row).to_be_visible()
        return row

    def assert_code_and_copy(self, row):
        button = row.locator('.passwords-otp-ap3__copy')
        displayed = row.locator('.passwords-otp-ap3__code')
        button.scroll_into_view_if_needed()
        expect(button).to_be_enabled(timeout=45000)
        # Copy deliberately rejects the final 2.5 seconds and validation-window
        # changes. Use the next naturally valid window, leaving room for browser
        # actionability/scroll latency; never freeze or replace the real clock.
        row_handle = row.element_handle()
        try:
            self.page.wait_for_function('''element => {
                const progress = element.querySelector('.passwords-otp-ap3__progress');
                return progress.value > 5 && !element.querySelector('.passwords-otp-ap3__copy').disabled;
            }''', arg=row_handle, timeout=45000)
        finally:
            row_handle.dispose()
        progress = row.locator('.passwords-otp-ap3__progress').bounding_box()
        assert progress and progress['height'] >= 4 and progress['width'] >= 64, 'Countdown progress bar must be visibly rendered'
        # Capture actual time, code and native progress semantics atomically.
        # Native fill transitions can be mid-animation in a screenshot; their
        # value/max and the textual countdown must still agree. Retry only
        # across a natural TOTP boundary, without replacing the real clock.
        for _ in range(3):
            sample = row.evaluate('''(element) => {
                const progress = element.querySelector('.passwords-otp-ap3__progress');
                return {now: Date.now(), code: element.querySelector('.passwords-otp-ap3__code').textContent,
                    progress_max: progress.max, progress_value: progress.value,
                    countdown: element.querySelector('.passwords-otp-account__time span').textContent};
            }''')
            if sample['code'] == totp(sample['now']):
                break
            self.page.wait_for_timeout(1100)
        assert sample['code'] == totp(sample['now']), 'TOTP differs from independent HMAC calculation'
        assert sample['progress_max'] == 30, 'Native progress maximum must match the RFC fixture period'
        countdown_pattern = r'Noch (\d+) s gültig' if self.app_language == 'de' else r'(\d+) s remaining'
        countdown = re.fullmatch(countdown_pattern, sample['countdown'])
        assert countdown and math.ceil(sample['progress_value']) == int(countdown[1]), 'Native progress value and textual countdown disagree'
        for control in (button, displayed):
            control.click()
            expect(self.page.locator('#passwords-otp-ap3-feedback')).to_contain_text(
                'OTP-Code kopiert.' if self.app_language == 'de' else 'OTP code copied.')
            if self.browser_name == 'chromium':
                copied = self.page.evaluate('navigator.clipboard.readText()')
                assert copied in {totp(sample['now']), totp(self.page.evaluate('Date.now()'))}

    def keyboard_and_filter(self, row):
        self.page.locator('#passwords-otp-ap2-search').fill('nonexistent-acceptance-account')
        expect(row).to_be_hidden()
        self.page.locator('#passwords-otp-ap2-search').fill('')
        expect(row).to_be_visible()
        self.open()
        for key in ['Tab'] * 12 + ['Shift+Tab'] * 12:
            self.page.keyboard.press(key)
            assert self.page.locator('#passwords-otp-ap12-dialog').evaluate(
                '(element) => element.contains(document.activeElement)')
        self.page.locator('#passwords-otp-ap12-secret').fill(SEED)
        self.page.keyboard.press('Escape')
        expect(self.page.locator('#passwords-otp-ap12-dialog')).to_be_hidden()
        expect(self.page.locator('#passwords-otp-ap12-open')).to_be_focused()
        self.open()
        expect(self.page.locator('#passwords-otp-ap12-secret')).to_have_value('')
        self.page.locator('#passwords-otp-ap12-cancel').click()

    def session_expiry(self):
        self.context.clear_cookies()
        self.page.evaluate("window.dispatchEvent(new Event('focus'))")
        # Nextcloud's own session listener can redirect to its login page
        # before the app completes its independent session-status request.
        expect(self.page.locator('#passwords-otp-ap1-reload, #user').first).to_be_visible()
        if urlparse(self.page.url).path.endswith('/login'):
            expect(self.page.locator('#user')).to_be_visible()
        else:
            expect(self.page.locator('#passwords-otp-ap1-reload')).to_have_text(
                'Seite neu laden' if self.app_language == 'de' else 'Reload page')
        expect(self.page.locator('#passwords-otp-ap2-section')).to_have_count(0)

    def theme(self, name):
        status = self.page.evaluate('''async ({base, name}) => {
            const response = await fetch(base + '/ocs/v2.php/apps/theming/api/v1/theme/' + name + '/enable',
                {method: 'PUT', headers: {'requesttoken': document.head.dataset.requesttoken,
                    'OCS-APIRequest': 'true', 'Accept': 'application/json'}});
            return response.status;
        }''', {'base': self.base, 'name': name})
        assert status == 200
        self.app()
        assert name in self.page.locator('body').get_attribute('data-themes').split(',')

    def close(self):
        assert not self.errors, self.errors
        assert not self.existing_record_mutations, 'Acceptance must not modify existing Passwords records'
        assert not [entry for entry in self.page.evaluate('window.__otpAcceptanceCsp || []') if entry['application']]
        # The upstream Nextcloud shell may store preference values; app secrets
        # must not occur in either browser persistence area.
        storage = self.page.evaluate('JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage)])')
        assert SEED not in storage and SERVICE_PASSWORD not in storage
        self.context.close()


def headers_and_boundaries(fixture, response):
    page = fixture.page
    headers = response.headers
    assert 'no-store' in headers.get('cache-control', '')
    assert headers.get('referrer-policy') == 'no-referrer'
    csp = headers.get('content-security-policy', '')
    assert "'wasm-unsafe-eval'" in csp and "'unsafe-eval'" not in csp
    assert page.locator('#passwords-otp-app').get_attribute('data-js-build') == 'PASSWORDS_OTP_JS_113_VERIFIED'
    assert page.locator('#initial-state-passwords_otp-ap1').count() == 0
    module = page.locator('script[src*="/passwords_otp/js/app-113.mjs"]')
    assert module.get_attribute('type') == 'module'
    asset = page.request.get(urljoin(fixture.base + '/', module.get_attribute('src')))
    assert asset.status == 200
    assert asset.headers['content-type'].split(';')[0] in {'text/javascript', 'application/javascript'}
    assert hashlib.sha256(asset.body()).hexdigest() == hashlib.sha256((ROOT / 'js/app-113.mjs').read_bytes()).hexdigest()
    csrf = page.locator('head').get_attribute('data-requesttoken')
    session = page.request.get(fixture.base + '/index.php/apps/passwords_otp/session-status')
    assert session.status == 200 and session.json()['authenticated'] is True
    assert 'no-store' in session.headers.get('cache-control', '')
    fingerprint = session.json()['sessionFingerprint']
    endpoint = fixture.base + '/index.php/apps/passwords_otp/bootstrap'
    no_csrf = page.request.post(endpoint, headers={'X-Passwords-OTP-Session': fingerprint})
    assert no_csrf.status in {403, 412}, f'Missing CSRF accepted: {no_csrf.status}'
    wrong_session = page.request.post(endpoint, headers={'requesttoken': csrf, 'X-Passwords-OTP-Session': '0' * 64})
    assert wrong_session.status == 403
    assert 'token' not in wrong_session.json() and 'login' not in wrong_session.json()


def visual_matrix(fixture, output, results):
    page = fixture.page
    for theme in ['light', 'dark']:
        fixture.theme(theme)
        for state in ['list', 'dialog']:
            if state == 'dialog':
                fixture.open()
            for width, height in [(1440, 900), (1024, 768), (640, 450), (320, 720)]:
                page.set_viewport_size({'width': width, 'height': height})
                settle_visual_transitions(page)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                assert page.locator('#app-content-vue').evaluate('(el) => el.scrollWidth <= el.clientWidth + 1')
                if state == 'list':
                    progress = page.locator('.passwords-otp-ap3__progress').first.bounding_box()
                    assert progress and progress['height'] >= 4 and progress['width'] >= 64
                if state == 'dialog':
                    assert page.evaluate('''Boolean(document.elementFromPoint(20, 20)
                        ?.closest('#passwords-otp-ap12-dialog'))'''), 'Nextcloud header must not paint over the modal'
                    # role=dialog spans the viewport; measure actual form content.
                    box = page.locator('#passwords-otp-ap12-dialog form').bounding_box()
                    assert box and box['width'] <= width + 1
                    page.locator('#passwords-otp-ap12-save').scroll_into_view_if_needed()
                    expect(page.locator('#passwords-otp-ap12-save')).to_be_visible()
                if width in {1440, 320}:
                    page.screenshot(path=str(output / f'{fixture.browser_name}-{theme}-{state}-{width}.png'))
                results.append({'name': f'reflow-{theme}-{state}-{width}x{height}', 'status': 'PASS'})
            page.set_viewport_size({'width': 1440, 'height': 900})
            result = accessibility(page)
            assert not result['violations'], json.dumps(result['violations'], ensure_ascii=False)
            results.append({'name': f'axe-{theme}-{state}', 'status': 'PASS', **result})
            if state == 'dialog':
                page.locator('#passwords-otp-ap12-cancel').click()
                expect(page.locator('#passwords-otp-ap12-dialog')).to_be_hidden()
    fixture.theme('light')


def group_boundary(browser, base, browser_name):
    fixture = RealFixture(browser, base, browser_name)
    fixture.login(required('OTP_E2E_OUTSIDER_USER'), required('OTP_E2E_OUTSIDER_PASSWORD'))
    for endpoint in ['session-status', 'bootstrap']:
        kwargs = {'max_redirects': 0}
        url = base + '/index.php/apps/passwords_otp/' + endpoint
        response = fixture.page.request.get(url, **kwargs) if endpoint == 'session-status' else fixture.page.request.post(url, **kwargs)
        assert response.status in {302, 303, 403, 404, 412}, f'Non-group user accepted by {endpoint}'
        assert '"token"' not in response.text() and '"sessionFingerprint"' not in response.text()
    fixture.context.close()


def administrator_brand(browser, fixture, output, results):
    """Exercise actual Nextcloud branding and always restore the previous color."""
    if not os.environ.get('OTP_E2E_ADMIN_USER'):
        results.append({'name': 'real-administrator-brand', 'status': 'SKIP',
                        'reason': 'Disposable fixture administrator not supplied'})
        return
    admin = RealFixture(browser, fixture.base, fixture.browser_name)
    admin.login(required('OTP_E2E_ADMIN_USER'), required('OTP_E2E_ADMIN_PASSWORD'))
    csrf = admin.page.locator('head').get_attribute('data-requesttoken')
    headers = {'requesttoken': csrf, 'OCS-APIRequest': 'true', 'Accept': 'application/json'}
    capabilities = admin.page.request.get(fixture.base + '/ocs/v2.php/cloud/capabilities?format=json', headers=headers)
    assert capabilities.status == 200
    original = capabilities.json()['ocs']['data']['capabilities']['theming']['primaryColor']
    endpoint = fixture.base + '/index.php/apps/theming/ajax/updateStylesheet'
    def set_color(value):
        response = admin.page.request.post(endpoint, headers=headers, data={'setting': 'primaryColor', 'value': value})
        assert response.status == 200 and response.json()['status'] == 'success'
    try:
        set_color('#7d2f93')
        fixture.theme('light')
        capabilities = fixture.page.request.get(fixture.base + '/ocs/v2.php/cloud/capabilities?format=json',
                                               headers={'OCS-APIRequest': 'true', 'Accept': 'application/json'})
        assert capabilities.json()['ocs']['data']['capabilities']['theming']['primaryColor'] == '#7d2f93'
        for state in ['list', 'dialog']:
            if state == 'dialog':
                fixture.open()
            result = accessibility(fixture.page)
            assert not result['violations'], json.dumps(result['violations'], ensure_ascii=False)
            fixture.page.screenshot(path=str(output / f'{fixture.browser_name}-brand-{state}.png'))
            results.append({'name': f'axe-real-administrator-brand-{state}', 'status': 'PASS', **result})
            if state == 'dialog':
                fixture.page.locator('#passwords-otp-ap12-cancel').click()
                expect(fixture.page.locator('#passwords-otp-ap12-dialog')).to_be_hidden()
    finally:
        set_color(original)
        admin.context.close()
        fixture.app()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--browser', choices=['chromium', 'firefox'], default='chromium')
    parser.add_argument('--output', default='.build/real-integration')
    parser.add_argument('--core-only', action='store_true', help='Skip theme/a11y/viewport matrix; keep real core/CSE/shared flows')
    args = parser.parse_args()
    if required('OTP_E2E_DISPOSABLE') != '1':
        raise RuntimeError('Set OTP_E2E_DISPOSABLE=1 only for a disposable test installation')
    base = required('OTP_E2E_BASE_URL').rstrip('/')
    parsed = urlparse(base)
    if parsed.scheme != 'https' or parsed.hostname not in {'localhost', '127.0.0.1', '::1'}:
        raise RuntimeError('This destructive acceptance script requires a loopback HTTPS fixture')
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    results = []
    def passed(name, **detail):
        results.append({'name': name, 'status': 'PASS', **detail})
        print('REAL_INTEGRATION_PASS', name, flush=True)
    run_id = str(time.time_ns())
    report = {'scope': 'Unmodified real Nextcloud and Passwords server; actual release Vue bundle, client, crypto, session, API and browser clipboard',
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'nextcloud': os.environ.get('OTP_E2E_NEXTCLOUD_VERSION', 'not supplied'),
              'passwords': os.environ.get('OTP_E2E_PASSWORDS_VERSION', 'not supplied'),
              'database': os.environ.get('OTP_E2E_DATABASE', 'not supplied'),
              'browser_engine': args.browser, 'native_browser_zoom_tested': False,
              'results': results, 'limitations': [
                  'Axe checks app and dialog scope; it is not a manual screen-reader audit.',
                  'Viewport reflow does not establish native browser zoom or OS text scaling.',
                  'Passwords-level live 2FA requires an upstream-enabled provider challenge; no upstream feature flags are overridden.',
                  'Rate limits, ambiguous write failures and BFCache events are covered by the separate synthetic browser/lifecycle suite.',
                  'This disposable fixture does not establish AIO, PostgreSQL, proxy-specific or production acceptance.'],
              'sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                         for name in ['js/app-113.mjs', 'css/app-113.css']}}
    if args.browser == 'firefox':
        report['limitations'].append('Firefox validates real user-triggered clipboard.writeText success; clipboard contents are independently read in Chromium only.')
    try:
        with sync_playwright() as playwright:
            options = {'headless': True}
            if args.browser == 'chromium':
                options['args'] = ['--no-sandbox']
                if os.environ.get('CHROME_BIN'):
                    options['executable_path'] = os.environ['CHROME_BIN']
            browser = getattr(playwright, args.browser).launch(**options)
            report['browser_version'] = browser.version
            fixture = RealFixture(browser, base, args.browser)
            fixture.login(required('OTP_E2E_USER'), required('OTP_E2E_PASSWORD'))
            response = fixture.app()
            headers_and_boundaries(fixture, response)
            passed('real-template-mjs-mime-csp-cache-csrf-session-binding')
            shared_label = os.environ.get('OTP_E2E_SHARED_LABEL')
            if shared_label:
                metadata = next(item for item in fixture.list_metadata if item['label'] == shared_label)
                assert metadata['share'] and metadata['editable'] is False, 'Fixture record must be an actual read-only incoming share'
                shared = fixture.page.locator('#passwords-otp-ap2-list li').filter(has_text=shared_label)
                expect(shared).to_be_visible()
                fixture.assert_code_and_copy(shared)
                passed('real-shared-readonly-record-totp-copy')
            else:
                results.append({'name': 'real-shared-readonly-record-totp-copy', 'status': 'SKIP', 'reason': 'OTP_E2E_SHARED_LABEL not supplied'})
            row = fixture.create('OTP-VUE-Acceptance-' + run_id)
            fixture.assert_code_and_copy(row)
            fixture.keyboard_and_filter(row)
            passed('real-own-create-once-rfc-totp-native-copy-filter-immediate-keyboard')
            if not args.core_only:
                visual_matrix(fixture, output, results)
                passed('real-user-theme-ocs-and-visual-matrix')
                administrator_brand(browser, fixture, output, results)
            fixture.session_expiry()
            passed('real-cookie-session-expiry-removes-protected-ui')
            fixture.close()
            if os.environ.get('OTP_E2E_OUTSIDER_USER'):
                group_boundary(browser, base, args.browser)
                passed('real-non-group-user-denied')
            else:
                results.append({'name': 'real-non-group-user-denied', 'status': 'SKIP', 'reason': 'Outsider account not supplied'})
            if os.environ.get('OTP_E2E_CSE_USER'):
                fixture = RealFixture(browser, base, args.browser)
                fixture.login(required('OTP_E2E_CSE_USER'), required('OTP_E2E_CSE_PASSWORD'))
                fixture.app(ready=False)
                form = fixture.page.locator('#passwords-otp-ap1-login')
                master = fixture.page.locator('#passwords-otp-ap1-password')
                expect(form).to_be_visible()
                master.fill('Incorrect synthetic master password')
                form.locator('button[type=submit]').click()
                expect(fixture.page.locator('#passwords-otp-ap1-status')).to_contain_text('nicht akzeptiert')
                expect(master).to_have_value('')
                expect(master).to_be_focused()
                master.fill(required('OTP_E2E_CSE_MASTER'))
                form.locator('button[type=submit]').click()
                expect(fixture.page.locator('#passwords-otp-ap1-status')).to_contain_text('OTP-Konten geladen.')
                row = fixture.create('OTP-VUE-CSE-Acceptance-' + run_id, encrypted=True)
                fixture.assert_code_and_copy(row)
                fixture.keyboard_and_filter(row)
                settle_visual_transitions(fixture.page)
                fixture.page.screenshot(path=str(output / f'{args.browser}-cse-record.png'))
                fixture.session_expiry()
                fixture.close()
                passed('real-cse-wrong-master-retry-encrypted-create-decrypt-totp-copy-expiry')
            else:
                results.append({'name': 'real-cse-master-encrypted-create', 'status': 'SKIP', 'reason': 'CSE fixture account not supplied'})
            browser.close()
        assert report['sha256'] == {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                   for name in report['sha256']}, 'Release assets changed during acceptance'
        report['status'] = 'PASS'
    except Exception as error:
        report['status'] = 'FAIL'
        # Exception type is sufficient in the persisted report. Playwright's
        # verbose exception can include input values, so do not serialize it.
        report['failure_type'] = type(error).__name__
        raise
    finally:
        (output / f'report-{args.browser}.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(f'REAL_INTEGRATION_SUITE_PASS cases={len(results)} browser={args.browser}', flush=True)


if __name__ == '__main__':
    main()
