import {boundedRequest} from '../ap1/network.mjs';
/** The marker binds a page to its original login; it is not a bearer credential. */
export function makeSessionCheck(initial, pageUrl, requester = fetch) {
    if (!initial || initial.status !== 'ready' || !/^[0-9a-f]{64}$/.test(initial.sessionFingerprint || '')) {
        throw new Error('invalid-session-check-config');
    }
    const page = new URL(pageUrl), candidate = new URL(initial.sessionStatusUrl || '', page);
    const normalize = path => path.replace(/\/index\.php\/apps\//, '/apps/');
    const pagePath = normalize(page.pathname), expected = (pagePath.endsWith('/') ? pagePath : pagePath + '/') + 'session-status';
    if (page.protocol !== 'https:' || page.username || page.password || candidate.protocol !== 'https:'
            || candidate.origin !== page.origin || candidate.username || candidate.password || candidate.search || candidate.hash
            || normalize(candidate.pathname) !== expected) throw new Error('invalid-session-check-url');
    const fingerprint = initial.sessionFingerprint;
    const requestOwner = {};
    return async () => {
        try {
            return await boundedRequest(requestOwner, async signal => {
                const response = await requester(candidate.href, {method: 'GET', credentials: 'same-origin', mode: 'same-origin',
                    redirect: 'error', cache: 'no-store', referrerPolicy: 'no-referrer',
                    headers: {Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest'}, signal});
                if (!response?.ok || !(response.headers?.get('content-type') || '').includes('application/json')) return false;
                const data = await response.json();
                return data?.authenticated === true && data?.sessionFingerprint === fingerprint;
            }, {timeoutMs: 5000});
        } catch (_) { return false; }
    };
}
