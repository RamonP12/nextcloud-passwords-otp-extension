import {SessionFault, deriveServerRoot} from './session.mjs';
import {boundedRequest} from './network.mjs';
export function validateBootstrapUrl(value, pageUrl) {
    try {
        if (typeof value !== 'string' || !value) throw new SessionFault('invalid-bootstrap-url');
        const page = new URL(pageUrl);
        if (page.protocol !== 'https:' || page.username || page.password) throw new SessionFault('https-required');
        const url = new URL(value, page);
        const normalize = path => path.replace(/\/index\.php\/apps\//, '/apps/');
        const pagePath = normalize(page.pathname);
        const expected = pagePath.endsWith('/') ? pagePath + 'bootstrap' : pagePath + '/bootstrap';
        if (url.origin !== page.origin || url.protocol !== 'https:' || url.username || url.password
                || url.search || url.hash || normalize(url.pathname) !== expected) throw new SessionFault('invalid-bootstrap-url');
        return url.href;
    } catch (error) {
        if (error instanceof SessionFault) throw error;
        throw new SessionFault('invalid-bootstrap-url');
    }
}
export function csrfRequestToken(doc) {
    const token = doc?.head?.getAttribute?.('data-requesttoken');
    if (typeof token !== 'string' || token.length < 8 || token.length > 8192) throw new SessionFault('csrf-unavailable');
    return token;
}
export async function loadBootstrap(initial, pageUrl, doc, requester, signal) {
    if (!initial || initial.status !== 'ready' || Object.hasOwn(initial, 'login') || Object.hasOwn(initial, 'token')
            || !/^[0-9a-f]{64}$/.test(initial.sessionFingerprint || '')) throw new SessionFault('invalid-config');
    const url = validateBootstrapUrl(initial.bootstrapUrl, pageUrl), csrf = csrfRequestToken(doc);
    const fingerprint = initial.sessionFingerprint;
    try {
        return await boundedRequest({}, async requestSignal => {
            const response = await requester(url, {method: 'POST', credentials: 'same-origin', mode: 'same-origin',
                redirect: 'error', cache: 'no-store', referrerPolicy: 'no-referrer',
                headers: {requesttoken: csrf, 'X-Requested-With': 'XMLHttpRequest', Accept: 'application/json',
                    'X-Passwords-OTP-Session': fingerprint}, signal: requestSignal});
            if (!response?.ok || !(response.headers?.get('content-type') ?? '').includes('application/json')) {
                throw new SessionFault('bootstrap-failed');
            }
            const credentials = await response.json();
            if (credentials?.status !== 'ready' || credentials.sessionFingerprint !== fingerprint) throw new SessionFault('bootstrap-failed');
            return deriveServerRoot(credentials, pageUrl);
        }, {timeoutMs: 12000, signal});
    } catch (_) { throw new SessionFault('bootstrap-failed'); }
}
