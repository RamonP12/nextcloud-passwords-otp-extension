import {createApp} from 'vue';
import App from './App.vue';
import {clearSensitiveDom} from './ui/dom-safety.mjs';
import {createUiFailureBoundary} from './ui/failure-boundary.mjs';
import {createTranslator, resolveLocale} from './l10n/translator.mjs';
import './styles.css';

const root = document.getElementById('passwords-otp-app');
const stateElement = document.getElementById('initial-state-passwords_otp-ap1');
let config = {status: 'unavailable'};
try {
    if (stateElement) config = JSON.parse(atob(stateElement.value));
} catch (_) { /* No credentials or exception details enter the UI/logs. */ }
finally { stateElement?.remove(); }
if (root) {
    const locale = resolveLocale(navigator.languages, navigator.language);
    const t = createTranslator(locale);
    root.lang = locale;
    // Nextcloud's fixed #content creates a stacking context below its global
    // header. Put the dedicated portal beside that shell so NcDialog's modal
    // layer can cover it on narrow viewports. Keep the same explicit scrub
    // target and language; no credentials are stored in the portal itself.
    const dialogHost = document.getElementById('passwords-otp-dialog-host');
    if (dialogHost && document.body) {
        dialogHost.lang = locale;
        document.body.append(dialogHost);
    }
    root.setAttribute('data-js-build', 'PASSWORDS_OTP_JS_120_DEV_VERIFIED');
    const boundary = createUiFailureBoundary(() =>
        clearSensitiveDom(document, {inputs: true, codes: true, lock: true}));
    const app = createApp(App, {config, locale, t, onControllerReady: boundary.register});
    let mounted = false, fallbackQueued = false, fallbackRendered = false;
    function renderFallback() {
        if (fallbackRendered) return;
        fallbackRendered = true;
        boundary.fail();
        // Stop first, then remove the broken component tree. Neither the error
        // object nor any former form/code contents enter the fallback view.
        try { app.unmount(); } catch (_) { /* Render the fixed fallback anyway. */ }
        const portal = document.getElementById('passwords-otp-dialog-host');
        if (portal) { portal.replaceChildren(); portal.hidden = true; }
        const message = document.createElement('p');
        message.setAttribute('role', 'alert');
        message.textContent = t('interface-failed');
        const creationNotice = document.createElement('p');
        creationNotice.textContent = t('recovery-create-notice');
        const reload = document.createElement('button');
        reload.type = 'button';
        reload.id = 'passwords-otp-ap1-reload';
        reload.className = 'primary';
        reload.textContent = t('reload');
        reload.addEventListener('click', () => window.location.reload());
        root.replaceChildren(message, creationNotice, reload);
    }
    app.config.errorHandler = () => {
        boundary.fail();
        // Finish the current Vue patch before replacing its DOM. Erasure and
        // controller termination above remain synchronous. Guard reentrancy if
        // rendering or unmounting the failure state itself produces an error.
        if (mounted && !fallbackQueued && !fallbackRendered) {
            fallbackQueued = true;
            queueMicrotask(() => { fallbackQueued = false; renderFallback(); });
        }
    };
    try {
        app.mount(root);
        mounted = true;
        if (boundary.failed) renderFallback();
    }
    catch (_) {
        boundary.fail();
        renderFallback();
    }
}
