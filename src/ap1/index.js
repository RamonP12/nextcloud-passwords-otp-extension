import {OtpVaultSession, SessionFault} from './session.mjs';
import {createClient, sodiumReady} from './upstream.js';
import {loadBootstrap} from './bootstrap.mjs';
import {renderOtpView} from '../ap2/view.mjs';
import {TotpPresenter} from '../ap3/ui.mjs';
import {makeSessionCheck} from '../ap9/session-check.mjs';
import {boundedRequest} from './network.mjs';
document.getElementById('passwords-otp-app')?.setAttribute('data-js-build', 'PASSWORDS_OTP_JS_101_VERIFIED');
const byId = id => document.getElementById(id);
const el = id => byId('passwords-otp-ap1-' + id);
const statusEl = el('status'), form = el('login');
const passwordInput = el('password'), codeInput = el('code'), providerSelect = el('provider');
const tokenContainer = el('token-area'), reloadButton = el('reload');
const createEl = id => byId('passwords-otp-ap12-' + id);
const createButton = createEl('open'), createDialog = createEl('dialog'), createForm = createEl('form');
const createLabel = createEl('label'), createUsername = createEl('username'), createPassword = createEl('password');
const createSecret = createEl('secret'), createFeedback = createEl('feedback'), createSave = createEl('save'), createCancel = createEl('cancel');
const otpNodes = {section: byId('passwords-otp-ap2-section'), list: byId('passwords-otp-ap2-list'),
    search: byId('passwords-otp-ap2-search'), empty: byId('passwords-otp-ap2-empty'), feedback: byId('passwords-otp-ap3-feedback')};
let lastPublicSnapshot = null, presenter = null, session = null, pageHidden = false;
let createBusy = false, createBlocked = false, createOpening = false;
const bootstrapAbort = new AbortController();
const status = message => { statusEl.textContent = message; };
function closeCreateDialog() {
    if (createDialog.open) createDialog.close();
    createForm.reset(); createFeedback.textContent = ''; createForm.removeAttribute('aria-busy');
}
function clearSensitiveInputs() { passwordInput.value = ''; codeInput.value = ''; createPassword.value = ''; createSecret.value = ''; }
function clearOtpView() {
    lastPublicSnapshot = null; otpNodes.search.value = '';
    if (presenter) presenter.render({state: 'locked'}, '');
    // Also clear the DOM if the presenter has already been disposed.
    renderOtpView({state: 'locked'}, '', otpNodes, document);
}
function lockUi(message) {
    createButton.hidden = true; form.hidden = true;
    closeCreateDialog(); clearSensitiveInputs(); clearOtpView();
    if (!pageHidden) { status(message); reloadButton.hidden = false; }
}
function createErrorMessage(code) {
    return ({'create-invalid-label': 'Bitte eine Bezeichnung mit maximal 160 Zeichen eingeben.',
        'create-invalid-username': 'Der Benutzername ist zu lang.',
        'create-invalid-password': 'Bitte ein g\u00fcltiges, nicht leeres Dienstpasswort eingeben.',
        'create-invalid-secret': 'Ung\u00fcltiges Base32-Secret. Den Einrichtungsschl\u00fcssel pr\u00fcfen.',
        'create-cse-unavailable': 'Clientseitige Verschl\u00fcsselung nicht verf\u00fcgbar. Es wurde nichts gespeichert.',
        'cse-unavailable': 'Clientseitige Verschl\u00fcsselung nicht verf\u00fcgbar. Es wurde nichts gespeichert.',
        'create-crypto-unavailable': 'Die ben\u00f6tigte Browser-Kryptografie ist nicht verf\u00fcgbar.',
        'create-encryption-unknown': 'Der Verschl\u00fcsselungsmodus konnte nicht gepr\u00fcft werden. Es wurde nichts gespeichert.',
        'create-busy': 'Die Erstellung l\u00e4uft bereits.',
        'create-auth-unavailable': 'Die Passwords-API konnte nicht sicher gepr\u00fcft werden. Es wurde nichts gespeichert.',
        'passwords-session-expired': 'Die Passwords-API-Sitzung ist abgelaufen. Es wurde kein neuer Eintrag gespeichert. Bitte Seite neu laden.',
        'auth-rate-limited': 'Die Passwords-API begrenzt Anfragen (HTTP 403/429). Die Nextcloud-Anmeldung ist nicht als abgelaufen nachgewiesen. Nach einer Wartezeit neu laden.',
        'create-uncertain': 'Der Erstellungsstatus ist unklar. Vor einem neuen Versuch Passwords pr\u00fcfen und die Seite neu laden.'})[code]
        || 'Der Eintrag konnte nicht erstellt werden. Angaben und Sitzung pr\u00fcfen; Passwort und Secret erneut eingeben.';
}
function messageFor(code) {
    return ({'https-required': 'HTTPS ist erforderlich.', 'invalid-config': 'Ung\u00fcltige Initialisierung.',
        'invalid-api-url': 'Der Passwords-API-Endpunkt ist nicht vertrauensw\u00fcrdig.',
        'invalid-bootstrap-url': 'Der OTP-Verbindungsendpunkt ist nicht vertrauensw\u00fcrdig.',
        'csrf-unavailable': 'Die Nextcloud-Sitzung ist nicht vollst\u00e4ndig verf\u00fcgbar. Bitte neu anmelden.',
        'bootstrap-failed': 'Die Passwords-Zugangsdaten konnten nicht sicher geladen werden. Bitte neu anmelden.',
        'disposed': 'Die Sitzung wurde beendet. Bitte Seite neu laden.',
        'unsupported-challenge': 'Diese Master-Passwort-Challenge wird nicht unterst\u00fctzt.',
        'unsupported-token-provider': 'Dieser zus\u00e4tzliche Authentifizierungsanbieter wird nicht unterst\u00fctzt.',
        'invalid-password-input': 'Bitte den g\u00fcltigen Master-Schl\u00fcssel eingeben.',
        'invalid-master-key': 'Master-Schlüssel nicht akzeptiert. Bitte erneut versuchen.',
        'auth-invalid': 'Authentifizierung abgewiesen. Seite neu laden und erneut versuchen.',
        'auth-rate-limited': 'Authentifizierung vor\u00fcbergehend eingeschr\u00e4nkt.',
        'auth-required': 'Tresor gesperrt. Bitte erneut authentifizieren.',
        'invalid-list': 'Unerwartetes Antwortformat der Passwortliste.',
        'cse-unavailable': 'Der CSE-Schl\u00fcssel kann nicht freigegeben werden.',
        'unsupported-cse': 'Der Verschl\u00fcsselungsmodus wird nicht unterst\u00fctzt.',
        'crypto-unavailable': 'Der Browser kann OTP-Codes nicht sicher berechnen.'})[code]
        || 'Die OTP-Sitzung konnte nicht sicher ge\u00f6ffnet werden.';
}
function showResult(snapshot) {
    if (pageHidden || session?.disposed) return;
    lastPublicSnapshot = snapshot.state === 'ready' ? snapshot : null;
    if (snapshot.state !== 'ready') otpNodes.search.value = '';
    presenter.render(snapshot, otpNodes.search.value);
    form.hidden = snapshot.state !== 'needs-auth';
    createButton.hidden = snapshot.state !== 'ready' || createBlocked;
    if (snapshot.state === 'ready') status('OTP-Konten erfolgreich geladen.');
    else if (snapshot.state === 'needs-auth') {
        status('Zus\u00e4tzliche Tresor-Authentifizierung erforderlich.');
        passwordInput.required = snapshot.needsChallenge;
        passwordInput.closest('.passwords-otp-ap1__field').hidden = !snapshot.needsChallenge;
        tokenContainer.hidden = !snapshot.needsToken; codeInput.required = snapshot.needsToken;
        providerSelect.replaceChildren();
        if (snapshot.needsToken) {
            for (const provider of snapshot.providers) {
                if (!provider.supported) continue;
                const option = document.createElement('option'); option.value = provider.id; option.textContent = provider.label;
                providerSelect.append(option);
            }
            if (!providerSelect.options.length) {
                status('Der konfigurierte 2FA-Anbieter wird nicht unterst\u00fctzt.'); form.querySelector('[type=submit]').disabled = true;
            }
        }
    }
}
function getConfig() {
    const stateEl = byId('initial-state-passwords_otp-ap1');
    if (!stateEl) throw new SessionFault('invalid-config');
    try { return JSON.parse(atob(stateEl.value)); }
    catch (_) { throw new SessionFault('invalid-config'); }
    finally { stateEl.remove(); }
}
reloadButton.addEventListener('click', () => window.location.reload());
otpNodes.search.addEventListener('input', () => {
    if (lastPublicSnapshot?.state === 'ready') presenter?.filter(otpNodes.search.value);
});
document.addEventListener('visibilitychange', () => presenter?.visibilityChanged());
window.addEventListener('focus', () => presenter?.focusChanged());
window.addEventListener('pagehide', () => {
    pageHidden = true; bootstrapAbort.abort(); lockUi(''); presenter?.dispose();
    // Best effort only: browser navigation may cancel the network request.
    void session?.close().catch(() => {});
}, {once: true});
window.addEventListener('pageshow', event => {
    if (event.persisted) { pageHidden = false; lockUi('Sitzung beendet. Bitte Seite neu laden.'); }
});
(async () => {
    try {
        const state = getConfig();
        if (state.status !== 'ready') { lockUi('Die Passwords-Integration ist nicht verf\u00fcgbar.'); return; }
        const verifySession = makeSessionCheck(state, window.location.href, (...args) => fetch(...args));
        const requireSession = async () => {
            if (pageHidden || await verifySession() !== true) { session?.dispose(); throw new SessionFault('auth-required'); }
            if (pageHidden || session?.disposed) throw new SessionFault('disposed');
        };
        presenter = new TotpPresenter(otpNodes, document, {verifySession,
            notify: message => { if (!pageHidden) otpNodes.feedback.textContent = message; },
            fatal: message => { session?.dispose(); lockUi(message); }});
        await boundedRequest({}, () => sodiumReady(), {timeoutMs: 15000, signal: bootstrapAbort.signal});
        await requireSession();
        const validated = await loadBootstrap(state, window.location.href, document, (...args) => fetch(...args), bootstrapAbort.signal);
        if (pageHidden) throw new SessionFault('disposed');
        session = new OtpVaultSession(createClient(validated));
        validated.token = ''; validated.user = '';
        presenter.setSession(session);
        await requireSession();
        const result = await session.begin();
        await requireSession();
        showResult(result);
        createButton.addEventListener('click', async () => {
            if (pageHidden || createBusy || createOpening || createBlocked || session.disposed || session.state !== 'ready') return;
            createOpening = true; createButton.disabled = true;
            try {
                await requireSession();
                // Authoritative Passwords-API probe. The Nextcloud login can
                // remain valid after the separate Passwords token/CSE expires.
                await session.assertCreateAccess();
                await requireSession();
                if (pageHidden || session.disposed || createBlocked || createBusy) return;
                createFeedback.textContent = ''; createForm.reset(); createDialog.showModal(); createLabel.focus();
            } catch (error) {
                if (pageHidden) return;
                if (error?.code === 'passwords-session-expired') {
                    session.dispose(); presenter.dispose(); lockUi(createErrorMessage(error.code));
                } else if (error?.code === 'auth-rate-limited') {
                    session.dispose(); presenter.dispose(); lockUi(createErrorMessage(error.code));
                } else if (session.disposed || ['auth-required', 'auth-invalid'].includes(error?.code)) {
                    session.dispose(); presenter.dispose(); lockUi('Nextcloud-Sitzung nicht mehr gültig. Bitte erneut anmelden.');
                } else {
                    status('Die Passwords-API konnte nicht überprüft werden. Bitte erneut versuchen.');
                }
            } finally {
                createOpening = false; createButton.disabled = false;
            }
        });
        createCancel.addEventListener('click', () => { if (!createBusy) closeCreateDialog(); });
        createDialog.addEventListener('cancel', event => { if (createBusy) event.preventDefault(); else closeCreateDialog(); });
        createDialog.addEventListener('close', () => {
            createForm.reset(); createFeedback.textContent = '';
            if (!pageHidden && !createButton.hidden) createButton.focus();
        });
        createDialog.addEventListener('keydown', event => {
            if (event.key !== 'Tab' || !createDialog.open) return;
            const controls = [...createDialog.querySelectorAll('input:not(:disabled), select:not(:disabled), button:not(:disabled), [tabindex="0"]')]
                .filter(control => control.getClientRects().length > 0);
            if (!controls.length) { event.preventDefault(); return; }
            const first = controls[0], last = controls.at(-1);
            if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
            else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
        });
        createForm.addEventListener('keydown', event => {
            if (event.key === 'Enter' && event.target instanceof HTMLInputElement) event.preventDefault();
        });
        createForm.addEventListener('submit', async event => {
            event.preventDefault();
            if (pageHidden || createBusy || createBlocked || session.disposed || session.state !== 'ready' || !createDialog.open) return;
            if (!createForm.reportValidity()) return;
            createBusy = true; createSave.disabled = true; createCancel.disabled = true;
            createForm.setAttribute('aria-busy', 'true'); createFeedback.textContent = 'Neuer OTP-Eintrag wird erstellt \u2026';
            const values = {label: createLabel.value, username: createUsername.value, password: createPassword.value, secret: createSecret.value};
            createPassword.value = ''; createSecret.value = '';
            try {
                const created = await session.createNewOtp(values, {verifySession});
                if (pageHidden || session.disposed || session.state !== 'ready') return;
                closeCreateDialog(); showResult(created.snapshot); status('Neuer OTP-Eintrag erfolgreich in Passwords gespeichert.');
            } catch (error) {
                if (pageHidden) return;
                if (error?.code === 'passwords-session-expired') {
                    // The probe failed BEFORE a password/create POST was sent.
                    session.dispose(); presenter.dispose(); lockUi(createErrorMessage(error.code));
                } else if (error?.code === 'auth-rate-limited') {
                    session.dispose(); presenter.dispose(); lockUi(createErrorMessage(error.code));
                } else if (error?.code === 'create-uncertain') {
                    createBlocked = true; session.dispose(); presenter.dispose(); lockUi(createErrorMessage(error.code));
                } else if (session.disposed || ['auth-required', 'auth-invalid'].includes(error?.code)) {
                    session.dispose(); presenter.dispose(); lockUi('Nextcloud-Sitzung nicht mehr g\u00fcltig. Bitte erneut anmelden.');
                } else createFeedback.textContent = createErrorMessage(error?.code);
            } finally {
                values.password = ''; values.secret = ''; createPassword.value = ''; createSecret.value = '';
                createBusy = false; createSave.disabled = false; createCancel.disabled = false; createForm.removeAttribute('aria-busy');
            }
        });
        form.addEventListener('submit', async event => {
            event.preventDefault();
            if (pageHidden || session.disposed || session.state !== 'needs-auth') return;
            const submit = form.querySelector('[type=submit]');
            const auth = {password: passwordInput.value, otpCode: codeInput.value, providerId: providerSelect.value};
            clearSensitiveInputs(); submit.disabled = true;
            status('Tresor wird \u00fcber die offizielle Passwords-API freigegeben \u2026');
            try { await requireSession(); const updated = await session.unlock(auth); await requireSession(); showResult(updated); }
            catch (error) {
                if (error?.code === 'invalid-master-key' && !session.disposed && session.state === 'needs-auth') {
                    status('Master-Schlüssel nicht akzeptiert. Bitte erneut versuchen.');
                    form.hidden = false; passwordInput.focus();
                } else { session.dispose(); presenter.dispose(); lockUi(messageFor(error?.code)); }
            }
            finally { auth.password = ''; auth.otpCode = ''; clearSensitiveInputs(); submit.disabled = false; }
        });
    } catch (error) {
        session?.dispose(); presenter?.dispose(); lockUi(messageFor(error?.code));
    }
})();
