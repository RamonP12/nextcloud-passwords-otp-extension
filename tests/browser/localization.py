"""Exercise app locale selection with the production bundle and independent shell language."""
import re
from playwright.sync_api import expect

from desktop import Fixture, record


def run_cases(browser, passed):
    title = '<img src="fixture" onerror="alert(1)"> $& {title}'
    for locale, preferences, language in [
        ('de-DE', None, 'de'),
        ('de-CH', None, 'de'),
        ('en-US', None, 'en'),
        ('fr-FR', ['fr-FR'], 'en'),
        ('fr-FR', ['fr-FR', 'de-CH', 'en-US'], 'de'),
        ('fr-FR', ['de_CH', '', None], 'en'),
        ('de-CH', [], 'de'),
    ]:
        shell_language = 'en' if language == 'de' else 'de'
        f = Fixture(browser, locale=locale, preferences=preferences, expected_language=language,
                    shell_language=shell_language, records=[record(title=title)])
        try:
            page = f.page
            expect(page.locator('html')).to_have_attribute('lang', shell_language)
            expect(page.locator('#passwords-otp-ap2-search')).to_have_accessible_name(
                'TOTP-Konten durchsuchen' if language == 'de' else 'Search TOTP accounts')
            expect(page.locator('#passwords-otp-ap2-list strong')).to_have_text(title)
            expect(page.locator('#passwords-otp-ap2-list img')).to_have_count(0)
            code = page.locator('.passwords-otp-ap3__code')
            expect(code).to_have_accessible_name(
                f'Angezeigten OTP-Code für {title} kopieren' if language == 'de'
                else f'Copy the displayed OTP code for {title}')
            code.click()
            expect(page.locator('#passwords-otp-ap3-feedback')).to_have_text(
                'OTP-Code kopiert.' if language == 'de' else 'OTP code copied.')
            page.evaluate("window.dispatchEvent(new Event('languagechange'))")
            expect(code).to_have_text(re.compile(r'^\d{6}$'))
            expect(page.locator('#passwords-otp-app')).to_have_attribute('lang', language)
            f.open()
            expect(page.locator('#passwords-otp-dialog-host')).to_have_attribute('lang', language)
            expect(page.get_by_role('dialog')).to_have_attribute('lang', language)
            expect(page.get_by_role('dialog')).to_have_accessible_name(
                'Neues OTP Passwort hinzufügen' if language == 'de' else 'Add a new OTP entry')
            f.save()
            label = page.locator('#passwords-otp-ap12-label')
            assert label.evaluate('(el) => el.validationMessage') == (
                'Fülle dieses Feld aus.' if language == 'de' else 'Fill in this field.')
            f.fill(secret='INVALID')
            f.save()
            expect(page.locator('#passwords-otp-ap12-feedback')).to_contain_text(
                'Ungültiges Base32-Secret' if language == 'de' else 'Invalid Base32 secret')
            assert f.created == 0
            f.fill()
            f.save()
            expect(page.get_by_role('dialog')).to_have_count(0)
            assert f.created == 1
        finally:
            f.close()
        passed(f'locale-{locale}-{language}-preferences-{preferences}')

    for locale, language, title, notice in [
        ('en-US', 'en', 'OTP account', 'Switching tabs cleared the password and OTP secret.'),
        ('de-CH', 'de', 'OTP-Konto', 'Beim Tab-Wechsel wurden Passwort und OTP-Secret geleert.'),
    ]:
        f = Fixture(browser, locale=locale, expected_language=language, records=[record(title='', issuer='')])
        try:
            page = f.page
            expect(page.locator('#passwords-otp-ap2-list strong')).to_have_text(title)
            expect(page.locator('.passwords-otp-ap3__code')).to_have_accessible_name(re.compile(title))
            search = page.locator('#passwords-otp-ap2-search')
            search.fill(title)
            expect(page.locator('#passwords-otp-ap2-list li')).to_be_visible()
            f.open()
            dialog = page.get_by_role('dialog')
            expect(dialog.get_by_text(notice, exact=False)).to_have_count(0)
            f.fill()
            page.locator('#passwords-otp-ap12-username').fill('Synthetic user')
            page.evaluate("""() => {
                Object.defineProperty(document, 'hidden', {value:true, configurable:true});
                document.dispatchEvent(new Event('visibilitychange'));
                Object.defineProperty(document, 'hidden', {value:false, configurable:true});
                document.dispatchEvent(new Event('visibilitychange'));
            }""")
            expect(dialog.get_by_role('status').filter(has_text=notice)).to_be_visible()
            expect(page.locator('#passwords-otp-ap12-label')).to_have_value('New fixture')
            expect(page.locator('#passwords-otp-ap12-username')).to_have_value('Synthetic user')
            expect(page.locator('#passwords-otp-ap12-password')).to_have_value('')
            expect(page.locator('#passwords-otp-ap12-secret')).to_have_value('')
            f.save()
            assert f.created == 0
            f.fill()
            f.save()
            expect(dialog).to_have_count(0)
            assert f.created == 1
        finally:
            f.close()
        passed(f'locale-{language}-untitled-account-and-tab-switch-notice')

    f = Fixture(browser, locale='en-US', expected_language='en', auth=True)
    try:
        page = f.page
        master = page.get_by_label('Passwords master password')
        factor = page.get_by_role('combobox', name='Second authentication factor')
        expect(factor).to_be_visible()
        verification = page.get_by_label('Verification code')
        unlock = page.get_by_role('button', name='Unlock vault')
        unlock.click()
        assert master.evaluate('(el) => el.validationMessage') == 'Fill in this field.'
        master.press_sequentially('short')
        unlock.click()
        assert master.evaluate('(el) => el.validationMessage') == 'Enter at least 12 characters.'
        f.wrong_master = True
        for attempt in range(2):
            master.fill('synthetic test master password')
            verification.fill('654321')
            unlock.click()
            if attempt == 0:
                expect(page.get_by_role('status').filter(has_text='Master password rejected')).to_be_visible()
                expect(master).to_be_focused()
                expect(master).to_have_value('')
        expect(page.locator('#passwords-otp-ap1-status')).to_contain_text('OTP accounts loaded.')
        expect(page.locator('.passwords-otp-ap3__code')).to_have_text(re.compile(r'^\d{6}$'))
        f.expired = True
        page.locator('#passwords-otp-ap12-open').click()
        expect(page.locator('#passwords-otp-ap1-status')).to_contain_text('The Passwords API session expired.')
        expect(page.get_by_role('button', name='Reload page')).to_be_visible()
    finally:
        f.close()
    passed('locale-en-cse-challenge-2fa-session-expiry')
