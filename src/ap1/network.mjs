/** Bounded, abortable transport owned solely by this OTP page. Never logs request data. */
const active = new WeakMap();
export class NetworkFault extends Error {
    constructor(code = 'api-error') { super(code); this.code = code; this.name = 'NetworkFault'; }
}
export function abortClientRequests(client) {
    for (const controller of active.get(client) || []) controller.abort();
    active.delete(client);
}
export async function boundedRequest(client, operation, {timeoutMs = 15000, signal} = {}) {
    if (!Number.isFinite(timeoutMs) || timeoutMs <= 0 || typeof operation !== 'function') throw new NetworkFault();
    const controller = new AbortController();
    let controllers = active.get(client);
    if (!controllers) { controllers = new Set(); active.set(client, controllers); }
    controllers.add(controller);
    let timer;
    const abort = () => controller.abort();
    if (signal?.aborted) controller.abort();
    else signal?.addEventListener('abort', abort, {once: true});
    try {
        return await Promise.race([
            new Promise((_, reject) => {
                const rejected = () => reject(new NetworkFault('request-aborted'));
                if (controller.signal.aborted) rejected();
                else controller.signal.addEventListener('abort', rejected, {once: true});
                timer = setTimeout(() => controller.abort(), timeoutMs);
            }),
            Promise.resolve().then(() => {
                if (controller.signal.aborted) throw new NetworkFault('request-aborted');
                return operation(controller.signal);
            })
        ]);
    } finally {
        clearTimeout(timer);
        signal?.removeEventListener('abort', abort);
        controllers.delete(controller);
        if (!controllers.size && active.get(client) === controllers) active.delete(client);
    }
}
export function validateApiTarget(value, rootValue, pageUrl) {
    try {
        // Reject traversal BEFORE URL normalization can erase it.
        if (typeof value !== 'string' || typeof rootValue !== 'string'
                || [value, rootValue].some(raw => /%(?:2e|2f|5c)|\\|(?:^|\/)\.{1,2}(?:\/|$)/i.test(raw))) {
            throw new NetworkFault('invalid-api-url');
        }
        const page = new URL(pageUrl), root = new URL(rootValue, page), target = new URL(value, page);
        if (page.protocol !== 'https:' || root.origin !== page.origin || target.origin !== page.origin
                || root.protocol !== 'https:' || target.protocol !== 'https:'
                || root.username || root.password || root.search || root.hash
                || target.username || target.password || target.search || target.hash
                || !root.pathname.endsWith('/apps/passwords/api/')
                || !target.pathname.startsWith(root.pathname)) throw new NetworkFault('invalid-api-url');
        return {href: target.href, route: target.pathname.slice(root.pathname.length)};
    } catch (_) { throw new NetworkFault('invalid-api-url'); }
}
