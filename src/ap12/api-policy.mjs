/** Accident-prevention policy; NOT a server-enforced restriction of the upstream bearer. */
const safeOperations = new Set([
    'GET 1.0/session/request', 'POST 1.0/session/open', 'GET 1.0/session/close',
    'GET 1.0/session/keepalive', 'GET 1.0/password/list',
    'GET 1.0/settings/list', 'GET 1.0/keychain/get', 'GET 1.0/account/challenge/get'
]);
const createLeases = new WeakMap();
export function assertOtpApiOperation(path, method, client) {
    if (typeof path !== 'string' || typeof method !== 'string'
            || !/^[a-z0-9/.-]+$/.test(path) || path.includes('..') || path.includes('//')) {
        throw new Error('otp-api-operation-denied');
    }
    const operation = method.toUpperCase() + ' ' + path;
    if (safeOperations.has(operation)) return;
    if (operation === 'POST 1.0/password/create') {
        const lease = client && createLeases.get(client);
        if (lease?.unused === true) { lease.unused = false; return; }
    }
    throw new Error('otp-api-operation-denied');
}
export async function withOneCreatePermit(client, work) {
    if ((typeof client !== 'object' && typeof client !== 'function') || client === null
            || typeof work !== 'function' || createLeases.has(client)) throw new Error('otp-api-create-busy');
    createLeases.set(client, {unused: true});
    try { return await work(); } finally { createLeases.delete(client); }
}
