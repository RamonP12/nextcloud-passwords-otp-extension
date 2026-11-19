#!/usr/bin/env python3
"""Run the browser language matrix against disposable real Nextcloud 35."""
import argparse
import os
import time
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright

from nextcloud import RealFixture, accessibility, required


def assert_language(browser, base, *, locale, app_language, account_language, forced_language):
    fixture = RealFixture(browser, base, 'chromium', locale=locale, app_language=app_language)
    english_account = account_language == 'en'
    account = required('OTP_E2E_ENGLISH_USER' if english_account else 'OTP_E2E_USER')
    password = required('OTP_E2E_ENGLISH_PASSWORD' if english_account else 'OTP_E2E_PASSWORD')
    try:
        fixture.login(account, password)
        response = fixture.app()
        assert b'Checking session' in response.body()
        assert 'Sitzung wird geprüft' not in response.text()
        page = fixture.page
        german = app_language == 'de'
        expect(page.locator('html')).to_have_attribute('lang', forced_language or account_language)
        expect(page.locator('#passwords-otp-app')).to_have_attribute('lang', app_language)
        expect(page.get_by_role('heading', name='Passwords OTP Generator')).to_be_visible()
        expect(page.locator('#passwords-otp-ap2-search')).to_have_accessible_name(
            'TOTP-Konten durchsuchen' if german else 'Search TOTP accounts')
        page.locator('#passwords-otp-ap2-search').fill('NO-MATCH-LOCALE-FIXTURE')
        expect(page.locator('#passwords-otp-ap2-empty')).to_contain_text(
            'TOTP-Konten' if german else 'TOTP accounts')
        page.locator('#passwords-otp-ap2-search').fill('')
        accessibility(page)
        fixture.open()
        dialog = page.get_by_role('dialog')
        expect(dialog).to_have_attribute('lang', app_language)
        expect(dialog).to_have_accessible_name(
            'Neues OTP Passwort hinzufügen' if german else 'Add a new OTP entry')
        expect(page.locator('#passwords-otp-dialog-host')).to_have_attribute('lang', app_language)
        accessibility(page)
        page.keyboard.press('Escape')
        expect(dialog).to_have_count(0)
        expect(page.locator('#passwords-otp-ap12-open')).to_be_focused()

        if locale == 'en-US' and not forced_language:
            row = fixture.create(f'OTP-Language-Fixture-{time.time_ns()}')
            fixture.assert_code_and_copy(row)
            fixture.session_expiry()
        fixture.close()
    finally:
        fixture.context.close()
    print(f'REAL_LOCALIZATION_PASS browser={locale} app={app_language} '
          f'account={account_language} forced={forced_language or "none"}', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--forced-language', choices=['de', 'en'],
                        help='Expected Nextcloud force_language already configured on the fixture')
    args = parser.parse_args()
    base = required('OTP_E2E_BASE_URL').rstrip('/')
    parsed = urlparse(base)
    if required('OTP_E2E_DISPOSABLE') != '1' or parsed.scheme != 'https' or parsed.hostname not in {
        'localhost', '127.0.0.1', '::1'
    }:
        raise RuntimeError('This acceptance requires a disposable loopback HTTPS Nextcloud')
    cases = [('en-US', 'en', 'de'), ('de-DE', 'de', 'en'), ('de-CH', 'de', 'en'), ('fr-FR', 'en', 'de')]
    if args.forced_language:
        cases = [('en-US', 'en', 'en')] if args.forced_language == 'de' else [('de-CH', 'de', 'de')]
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get('CHROME_BIN'), args=['--no-sandbox'])
        for locale, app_language, account_language in cases:
            assert_language(browser, base, locale=locale, app_language=app_language,
                            account_language=account_language, forced_language=args.forced_language)
        browser.close()


if __name__ == '__main__':
    main()
