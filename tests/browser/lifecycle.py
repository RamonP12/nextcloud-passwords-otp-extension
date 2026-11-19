#!/usr/bin/env python3
"""Lifecycle regressions against the unchanged production Vue bundle.

HTTP routes are held asynchronously by Playwright and later completed. There are
no sleeps inside route callbacks, injected application/controller hooks, fake
crypto, or replacements of production modules. All accounts and input values are
synthetic. `run_cases(browser)` can be included in the main desktop suite.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import time
from urllib.parse import urlparse

from playwright.sync_api import Error, expect
from desktop import Fixture, ORIGIN, PAGE, PREFIX, ROOT, encoded, shell, sync_playwright


def wait_for_held(fixture, timeout_ms=5000):
    """Pump Playwright's event loop until its nonblocking route callback ran."""
    deadline = time.monotonic() + timeout_ms / 1000
    while not fixture.held:
        if time.monotonic() >= deadline:
            raise AssertionError('Expected synthetic API request was not received')
        fixture.page.wait_for_timeout(10)
    assert len(fixture.held) == 1, 'Only one in-flight operation may be emitted'


class HeldRequestFixture(Fixture):
    def __init__(self, browser, *, endpoint='password/create'):
        self.endpoint = endpoint
        self.holding = True
        self.held = []
        super().__init__(browser)

    def route(self, route):
        path = urlparse(route.request.url).path
        if self.holding and path.endswith('/' + self.endpoint):
            self.calls.append((path, route.request.method))
            assert route.request.headers.get('authorization', '').startswith('Basic ')
            if self.endpoint == 'password/create':
                assert route.request.method == 'POST'
                # Model a server that committed the POST before its delayed
                # acknowledgment. Navigation cannot undo that server-side write.
                self.created += 1
                item = {**route.request.post_data_json, 'id': f'created-{self.created}', 'revision': 'r1'}
                self.records.append(item)
                response = (201, {'id': item['id'], 'revision': 'r1'})
            elif self.endpoint == 'settings/list':
                response = (200, {'user.encryption.cse': 0})
            else:
                raise AssertionError('Unsupported held fixture endpoint')
            self.held.append((route, response))
            return
        super().route(route)

    def release(self):
        self.holding = False
        pending, self.held = self.held, []
        for route, (status, response) in pending:
            try:
                route.fulfill(status=status, body=json.dumps(response), content_type='application/json',
                              headers={'x-api-session': 'SYNTHETIC-SESSION', 'cache-control': 'no-store'})
            except Error:
                # A pagehide must abort the client's pending request. Depending
                # on Chromium, completing its route then succeeds silently or
                # reports the already failed request. Neither is a fresh write.
                if not route.request.failure:
                    raise


def initial_render_failure(browser):
    context = browser.new_context(viewport={'width': 1280, 'height': 900}, locale='de-CH')
    page = context.new_page()
    errors, network = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.add_init_script(f'''
window.OC = {{config: {{version: '35.0.2.2'}}, filePath: (app, dir, file) => '{PREFIX}/apps/' + app + '/' + file}};
window._oc_webroot = '{PREFIX}'; window._oc_user = 'fixture'; window._oc_isadmin = false;
''')
    # The real NcAppContent setup expects an array and invokes apps.find(). A
    # validly encoded object produces an actual initial component setup error.
    html = re.sub(r'(id="initial-state-core-apps" value=")[^"]*(")',
                  lambda match: match.group(1) + encoded({'malformed': True}) + match.group(2), shell())

    def route(request_route):
        path = urlparse(request_route.request.url).path
        if path == PAGE:
            request_route.fulfill(body=html, content_type='text/html', headers={
                'Content-Security-Policy': "default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self' data:; base-uri 'none'"})
            return
        for name, mime in [('js/app-110.mjs', 'text/javascript'), ('css/app-110.css', 'text/css')]:
            if path == PREFIX + '/apps/passwords_otp/' + name:
                request_route.fulfill(body=(ROOT / name).read_bytes(), content_type=mime)
                return
        network.append((path, request_route.request.method))
        request_route.abort()

    page.route('**/*', route)
    try:
        page.goto(ORIGIN + PAGE)
        expect(page.locator('#passwords-otp-app')).to_contain_text('Oberfläche konnte nicht sicher ausgeführt werden')
        expect(page.locator('#passwords-otp-ap1-reload')).to_be_visible()
        expect(page.locator('input[data-otp-secret]')).to_have_count(0)
        expect(page.locator('.passwords-otp-ap3__code')).to_have_count(0)
        assert page.locator('#passwords-otp-dialog-host').evaluate('(el) => el.hidden && el.childElementCount === 0')
        # Drain queued mounted/start work after fallback, including promise jobs.
        page.wait_for_timeout(100)
        assert network == [], f'Initial rendering failure must stop before authentication: {network}'
        assert errors == [], 'The UI error handler must contain the component exception'
    finally:
        context.close()


def busy_dialog(browser):
    fixture = HeldRequestFixture(browser)
    page = fixture.page
    fixture.open()
    fixture.fill()
    fixture.save()
    wait_for_held(fixture)
    dialog = page.get_by_role('dialog')
    expect(dialog).to_have_attribute('aria-busy', 'true')
    expect(page.locator('#passwords-otp-ap12-save')).to_be_disabled()
    expect(page.locator('#passwords-otp-ap12-cancel')).to_be_disabled()
    for field in ['password', 'secret']:
        expect(page.locator('#passwords-otp-ap12-' + field)).to_have_value('')
    page.keyboard.press('Escape')
    expect(dialog).to_be_visible()
    for key in ['Tab', 'Tab', 'Shift+Tab', 'Tab']:
        page.keyboard.press(key)
        assert dialog.evaluate('(el) => el.contains(document.activeElement)'), 'Busy dialog must retain keyboard focus'
    # requestSubmit still emits a form submission even when user-visible submit
    # controls are disabled. The component and controller must both reject it.
    page.locator('#passwords-otp-ap12-dialog form').evaluate('''form => {
        form.requestSubmit();
        form.dispatchEvent(new SubmitEvent('submit', {bubbles:true, cancelable:true}));
    }''')
    assert len(fixture.held) == 1
    assert fixture.created == 1
    expect(page.locator('#passwords-otp-ap12-save')).to_be_disabled()
    fixture.release()
    expect(page.locator('#passwords-otp-ap1-status')).to_contain_text('in Passwords gespeichert.')
    expect(dialog).to_have_count(0)
    expect(page.locator('#passwords-otp-ap2-list li')).to_have_count(2)
    expect(page.locator('.passwords-otp-ap3__code').nth(1)).to_have_text(re.compile(r'^\d{6}$'))
    assert fixture.created == 1
    fixture.close()


def pagehide_during_request(browser, endpoint):
    fixture = HeldRequestFixture(browser, endpoint=endpoint)
    page = fixture.page
    fixture.open()
    fixture.fill()
    fixture.save()
    wait_for_held(fixture)
    committed = 1 if endpoint == 'password/create' else 0
    assert fixture.created == committed
    synchronous = page.evaluate('''() => {
        // Simulate late browser autofill without a Vue input event. Clearing
        // only reactive refs would miss this until the next component patch.
        for (const input of document.querySelectorAll('input[data-otp-secret]')) {
            input.value = 'SYNTHETIC-LATE-AUTOFILL';
        }
        window.dispatchEvent(new Event('pagehide'));
        const cleared = {
            codes: [...document.querySelectorAll('.passwords-otp-ap3__code')].every(el => !/\\d/.test(el.textContent)),
            inputs: [...document.querySelectorAll('input[data-otp-secret]')].every(el => el.value === ''),
            portal: document.getElementById('passwords-otp-dialog-host').hidden,
            protected: [...document.querySelectorAll('[data-otp-protected]')].every(el => el.hidden),
        };
        window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted:true}));
        return cleared;
    }''')
    assert all(synchronous.values()), f'Pagehide erasure must precede Vue flushing: {synchronous}'
    expect(page.get_by_role('dialog')).to_have_count(0)
    expect(page.locator('#passwords-otp-ap2-list li')).to_have_count(0)
    expect(page.locator('#passwords-otp-ap1-status')).to_contain_text('Sitzung beendet')
    expect(page.locator('#passwords-otp-ap1-reload')).to_be_visible()
    assert page.locator('#passwords-otp-dialog-host').evaluate('(el) => el.childElementCount === 0')
    fixture.release()
    # A delayed response or its abort rejection must not revive a restored page.
    page.wait_for_timeout(100)
    expect(page.locator('#passwords-otp-ap1-status')).to_contain_text('Sitzung beendet')
    expect(page.get_by_role('dialog')).to_have_count(0)
    expect(page.locator('.passwords-otp-ap3__code')).to_have_count(0)
    assert fixture.created == committed
    list_reads = [path for path, method in fixture.calls if path.endswith('/password/list')]
    assert len(list_reads) == 1, 'A late operation may not refresh/render the vault after termination'
    fixture.close()


def identical_code_repair(browser):
    fixture = Fixture(browser)
    page = fixture.page
    original = page.locator('.passwords-otp-ap3__code').inner_text()
    previous_checks = len([path for path, method in fixture.calls if path.endswith('/session-status')])
    synchronous = page.evaluate('''() => {
        document.querySelector('.passwords-otp-ap3__code').textContent = '—';
        document.querySelector('.passwords-otp-ap3__copy').disabled = true;
        document.querySelector('.passwords-otp-ap3__progress').value = 0;
        window.dispatchEvent(new Event('focus'));
        window.dispatchEvent(new Event('focus'));
        return document.querySelector('.passwords-otp-ap3__code').textContent === '—'
            && document.querySelector('.passwords-otp-ap3__copy').disabled;
    }''')
    assert synchronous
    # Date.now stays in the same slot, so the approved code is identical to the
    # old VNode text. Only correct DOM repair can restore a scrubbed same value.
    expect(page.locator('.passwords-otp-ap3__code')).to_have_text(original)
    expect(page.locator('.passwords-otp-ap3__copy')).to_be_enabled()
    assert page.locator('.passwords-otp-ap3__progress').evaluate('(el) => el.value') == 29
    checks = len([path for path, method in fixture.calls if path.endswith('/session-status')])
    assert checks > previous_checks
    page.locator('.passwords-otp-ap3__copy').click()
    expect(page.locator('#passwords-otp-ap3-feedback')).to_have_text('OTP-Code kopiert.')
    assert page.evaluate('__copied') == [original]
    fixture.close()


def same_tick_input_erasure(browser):
    for auth in [False, True]:
        fixture = Fixture(browser, auth=auth)
        page = fixture.page
        if not auth:
            fixture.open()
        erased = page.evaluate('''() => {
            const inputs = [...document.querySelectorAll('input[data-otp-secret]')];
            if (inputs.length !== 2) throw new Error('Expected exactly two sensitive inputs');
            for (const input of inputs) {
                input.value = 'SYNTHETIC-SAME-TICK-SECRET';
                input.dispatchEvent(new Event('input', {bubbles:true}));
            }
            // The models receive and clear the value in the same task, before
            // any Vue component has flushed its updated props to the DOM.
            Object.defineProperty(document, 'hidden', {value:true, configurable:true});
            document.dispatchEvent(new Event('visibilitychange'));
            const erased = inputs.every(input => input.value === '');
            Object.defineProperty(document, 'hidden', {value:false, configurable:true});
            document.dispatchEvent(new Event('visibilitychange'));
            return erased;
        }''')
        assert erased, 'Sensitive native input values must be erased in the current task'
        for index in range(2):
            expect(page.locator('input[data-otp-secret]').nth(index)).to_have_value('')
        page.wait_for_timeout(100)
        assert page.locator('input[data-otp-secret]').evaluate_all('(inputs) => inputs.every(input => input.value === "")')
        if not auth:
            expect(page.get_by_role('dialog')).to_be_visible()
            expect(page.locator('.passwords-otp-ap3__code')).to_have_text(re.compile(r'^\d{6}$'))
        fixture.close()


def run_cases(browser):
    """Run lifecycle cases, returning PASS dictionaries for desktop.report.json."""
    assets = [ROOT / name for name in ['js/app-110.mjs', 'css/app-110.css']]
    expected_hashes = [hashlib.sha256(path.read_bytes()).digest() for path in assets]
    results = []
    for name, run in [
        ('initial-component-error-stops-before-bootstrap', lambda: initial_render_failure(browser)),
        ('busy-dialog-escape-tab-and-duplicate-submit', lambda: busy_dialog(browser)),
        ('pagehide-before-create-post-late-settings', lambda: pagehide_during_request(browser, 'settings/list')),
        ('pagehide-after-create-post-late-ack-bfcache', lambda: pagehide_during_request(browser, 'password/create')),
        ('same-tick-identical-code-directive-repair', lambda: identical_code_repair(browser)),
        ('same-tick-secret-input-model-and-dom-erasure', lambda: same_tick_input_erasure(browser)),
    ]:
        run()
        assert [hashlib.sha256(path.read_bytes()).digest() for path in assets] == expected_hashes, \
            'Compiled assets changed during the browser run; rebuild and rerun the suite'
        results.append({'name': name, 'status': 'PASS'})
        print('BROWSER_PASS', name, flush=True)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='.build/browser-lifecycle')
    args = parser.parse_args()
    output = pathlib.Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    executable = os.environ.get('CHROME_BIN') or shutil.which('chromium-headless-shell') or shutil.which('chromium') or shutil.which('google-chrome')
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=executable, headless=True, args=['--no-sandbox'])
        try:
            results = run_cases(browser)
        finally:
            browser.close()
    report = {'scope': 'Production compiled Vue modules and pinned client; synthetic HTTPS shell/API/clipboard',
              'results': results, 'sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                           for name in ['js/app-110.mjs', 'css/app-110.css']}}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'BROWSER_LIFECYCLE_PASS cases={len(results)}')


if __name__ == '__main__':
    main()
