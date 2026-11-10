import {parseOtpCustomFields, toPublicOtpAccount} from '../ap2/parser.mjs';
import {buildNewOtpValues, prepareOtpCreatePayload, readEncryptionPreference, verifyCreatedRecord} from '../ap12/create.mjs';
import {withOneCreatePermit} from '../ap12/api-policy.mjs';
import {importTotpKey, calculateTotp} from '../ap3/totp.mjs';
import {abortClientRequests, boundedRequest} from './network.mjs';
export class SessionFault extends Error {
    constructor(code) { super(code); this.name = 'SessionFault'; this.code = code; }
}
export function deriveServerRoot(config, pageUrl) {
    if (!config || typeof config.login !== 'string' || !config.login
            || typeof config.token !== 'string' || !config.token) throw new SessionFault('invalid-config');
    let current;
    try { current = new URL(pageUrl); } catch { throw new SessionFault('invalid-api-url'); }
    if (current.protocol !== 'https:' || current.username || current.password) throw new SessionFault('https-required');
    const urls = [[config.sessionRequestUrl, '/apps/passwords/api/1.0/session/request'],
        [config.passwordListUrl, '/apps/passwords/api/1.0/password/list'],
        [config.sessionOpenUrl, '/apps/passwords/api/1.0/session/open']];
    let prefix = null;
    for (const [value, suffix] of urls) {
        if (typeof value !== 'string' || !value) throw new SessionFault('invalid-api-url');
        let url;
        try { url = new URL(value, current); } catch { throw new SessionFault('invalid-api-url'); }
        const pathname = url.pathname.replace(/\/index\.php\/apps\//, '/apps/');
        if (url.origin !== current.origin || url.protocol !== 'https:' || url.username || url.password
                || url.search || url.hash || !pathname.endsWith(suffix)) throw new SessionFault('invalid-api-url');
        const candidate = pathname.slice(0, -suffix.length);
        if (prefix === null) prefix = candidate;
        if (prefix !== candidate) throw new SessionFault('invalid-api-url');
    }
    if (prefix === null || /%(?:2e|2f|5c)/i.test(prefix) || prefix.includes('/../') || prefix.includes('/./')) {
        throw new SessionFault('invalid-api-url');
    }
    const baseUrl = current.origin + (prefix || '') + '/';
    return {baseUrl, apiRoot: baseUrl + 'index.php/apps/passwords/api/', user: config.login, token: config.token};
}
export function safeStatusCode(error) {
    const status = error?.response?.status ?? error?.getHttpStatus?.() ?? error?.status ?? null;
    return Number.isInteger(status) ? status : null;
}
export function classifyError(error) {
    const code = safeStatusCode(error);
    if (error instanceof SessionFault) return error.code;
    if (code === 401) return 'auth-invalid';
    if (code === 403 || code === 429) return 'auth-rate-limited';
    if (code === 412) return 'auth-required';
    return 'api-error';
}
/** Passwords 2026.11.0 ChallengeV1Helper::solveChallenge throws
 * HTTP 401, "Passphrase invalid", API ID ab6e13ba for a wrong master key.
 * The separate HTTP 500 / 033d1943 ("Passphrase verification failed")
 * indicates failure loading/verifying the saved challenge, NOT a typo.
 * Only the precise 401+API-ID reply may retain the unlock form for retry.
 */
async function isWrongMasterReply(error) {
    if (safeStatusCode(error) !== 401 || typeof error?.response?.clone !== 'function') return false;
    try {
        const body = await boundedRequest({}, async () => {
            const text = await error.response.clone().text();
            if (text.length > 2048) return null;
            return JSON.parse(text);
        }, {timeoutMs: 1500});
        return body?.status === 'error' && body?.id === 'ab6e13ba';
    } catch (_) { return false; }
}
function providerModel(provider) {
    const type = provider.getType();
    return {id: provider.getId(), type, label: String(provider.getLabel() || provider.getId()).slice(0, 100),
        requiresRequest: !!provider.requiresRequest(), supported: type === 'user-token' && !provider.requiresRequest()};
}
export class OtpVaultSession {
    #totpKeys = new Map();
    #knownIds = new Set();
    #creating = false;
    #createBlocked = false;
    constructor(client, options = {}) {
        this.client = client;
        this.authorization = null;
        this.state = 'new';
        this.providers = [];
        this.requiresChallenge = false;
        this.requiresToken = false;
        this.count = null;
        this.cseChecked = 0;
        this.otpAccounts = [];
        this.invalidOtpCount = 0;
        this.unsupportedOtpCount = 0;
        this.disposed = false;
        this.decryptTimeoutMs = options.decryptTimeoutMs ?? 12000;
        this.subtle = options.subtle ?? globalThis.crypto?.subtle;
    }
    _checkActive() { if (this.disposed) throw new SessionFault('disposed'); }
    async _crypto(work) {
        let timer;
        try {
            const result = await Promise.race([Promise.resolve().then(work), new Promise((_, reject) => {
                timer = setTimeout(() => reject(new SessionFault('cse-unavailable')), this.decryptTimeoutMs);
            })]);
            this._checkActive();
            return result;
        } finally { clearTimeout(timer); }
    }
    async begin() {
        this._checkActive();
        if (this.state !== 'new') throw new SessionFault('invalid-state');
        this.state = 'loading';
        try {
            this.authorization = this.client.getSessionAuthorization();
            await this.authorization.load();
            this._checkActive();
            this.requiresChallenge = !!this.authorization.requiresChallenge();
            this.requiresToken = !!this.authorization.requiresToken();
            this.providers = this.requiresToken ? this.authorization.getTokens().map(providerModel) : [];
            if (this.requiresChallenge || this.requiresToken) {
                if (this.requiresChallenge && !this.authorization.getChallenge?.()) throw new SessionFault('unsupported-challenge');
                this.state = 'needs-auth';
                return this.snapshot();
            }
            await this.authorization.authorize();
            this._checkActive();
            return await this.readCount();
        } catch (error) { this.dispose(); throw new SessionFault(classifyError(error)); }
    }
    async unlock({password = '', providerId = '', otpCode = ''} = {}) {
        this._checkActive();
        if (this.state !== 'needs-auth') throw new SessionFault('invalid-state');
        if (this.requiresChallenge && (typeof password !== 'string' || password.length < 12 || password.length > 128)) {
            throw new SessionFault('invalid-password-input');
        }
        let token = null;
        if (this.requiresToken) {
            const matching = this.authorization.getTokens().find(p => p.getId() === providerId);
            if (!matching || matching.getType() !== 'user-token' || matching.requiresRequest()
                    || typeof otpCode !== 'string' || !otpCode.trim()) throw new SessionFault('unsupported-token-provider');
            token = matching;
            token.setToken(otpCode.trim());
        }
        this.state = 'unlocking';
        try {
            // Keep the loaded challenge only for the exact wrong-passphrase
            // HTTP 401 / ab6e13ba response. Other 401/412/500 errors lock.
            try {
                await this.authorization.authorize(password, token ? token.getId() : undefined);
                this._checkActive();
                if (this.client.getSession?.()?.getAuthorized?.() === false) {
                    throw new SessionFault('auth-required');
                }
            } catch (error) {
                // Never treat arbitrary HTTP 401/412/500 as a wrong passphrase.
                if (this.requiresChallenge && await isWrongMasterReply(error)) {
                    this.state = 'needs-auth';
                    throw new SessionFault('invalid-master-key');
                }
                throw error;
            }
            return await this.readCount();
        } catch (error) {
            if (error?.code === 'invalid-master-key' && this.state === 'needs-auth') throw error;
            this.dispose(); throw new SessionFault(classifyError(error));
        } finally { if (token) token.setToken(''); }
    }
    /** Normal reads decrypt only customFields plus metadata of valid TOTP accounts. */
    async readCount({expectedCreation = null} = {}) {
        this._checkActive();
        let staged = new Map();
        try {
            const response = await this.client.getRequest().setPath('1.0/password/list').send();
            this._checkActive();
            const records = response.getData();
            if (!Array.isArray(records)) throw new SessionFault('invalid-list');
            let cseChecked = 0, invalidOtpCount = 0, unsupportedOtpCount = 0, verified = 0, encryption = null, encryptionReady = false;
            const accounts = [], seenIds = new Set();
            for (const record of records) {
                this._checkActive();
                if (!record || typeof record !== 'object' || Array.isArray(record)) throw new SessionFault('invalid-list');
                let rawCustomFields = record.customFields;
                let publicSource = {id: record.id, label: record.label, username: record.username};
                const isCreated = expectedCreation !== null && record.id === expectedCreation.id;
                if (record.cseType === 'CSEv1r1') {
                    encryption ??= this.client.getCseV1Encryption();
                    if (!encryptionReady) { await this._crypto(() => encryption.ready()); encryptionReady = true; }
                    const onlyCustom = {cseType: record.cseType, cseKey: record.cseKey,
                        url: null, label: null, notes: null, password: null, username: null,
                        customFields: record.customFields ?? null};
                    await this._crypto(() => encryption.decrypt(onlyCustom, 'password'));
                    rawCustomFields = onlyCustom.customFields;
                    onlyCustom.customFields = null;
                    cseChecked++;
                } else if (record.cseType && record.cseType !== 'none') throw new SessionFault('unsupported-cse');
                const parsed = parseOtpCustomFields(rawCustomFields);
                if (parsed.status === 'invalid') { invalidOtpCount++; continue; }
                if (parsed.status === 'unsupported') { unsupportedOtpCount++; continue; }
                if (parsed.status !== 'valid') continue;
                try {
                    if (record.cseType === 'CSEv1r1') {
                        const selected = {cseType: record.cseType, cseKey: record.cseKey, url: null, notes: null,
                            label: record.label ?? null, username: record.username ?? null, customFields: null,
                            password: isCreated ? record.password : null};
                        try {
                            await this._crypto(() => encryption.decrypt(selected, 'password'));
                            publicSource = {id: record.id, label: selected.label, username: selected.username};
                            if (isCreated) {
                                verifyCreatedRecord(record, {...selected, customFields: rawCustomFields}, expectedCreation);
                                verified++;
                            }
                        } finally { selected.password = null; }
                    } else if (isCreated) {
                        verifyCreatedRecord(record, record, expectedCreation);
                        verified++;
                    }
                    const account = toPublicOtpAccount(publicSource, parsed.otp);
                    if (!account || seenIds.has(account.id)) { invalidOtpCount++; continue; }
                    const key = await importTotpKey(parsed.otp, this.subtle);
                    this._checkActive();
                    staged.set(account.id, key);
                    seenIds.add(account.id);
                    accounts.push(account);
                } finally { parsed.otp.secret = ''; rawCustomFields = null; }
            }
            if (expectedCreation && verified !== 1) throw new SessionFault('create-unverified');
            this._checkActive();
            this.#knownIds = new Set(records.map(record => record.id).filter(id => typeof id === 'string'));
            this.count = records.length;
            this.cseChecked = cseChecked;
            this.otpAccounts = accounts;
            this.invalidOtpCount = invalidOtpCount;
            this.unsupportedOtpCount = unsupportedOtpCount;
            this.#totpKeys.clear();
            this.#totpKeys = staged;
            staged = null;
            this.state = 'ready';
            return this.snapshot();
        } catch (error) { staged?.clear(); this.dispose(); throw new SessionFault(classifyError(error)); }
    }
    /** Read-only Passwords-API authorization probe, NOT a Nextcloud login check.
     *  The upstream session/request endpoint returns {} for an authorized
     *  session and renewed challenge/token requirements after CSE expiry.
     *  Unlike session/keepalive, this response exposes authorization state.
     *  Probe only on user action, never keep a dormant tab alive indefinitely.
     */
    async assertCreateAccess() {
        this._checkActive();
        if (this.state !== 'ready') throw new SessionFault('auth-required');
        try {
            const response = await this.client.getRequest().setPath('1.0/session/request').send();
            this._checkActive();
            const requirements = response.getData();
            if (!requirements || typeof requirements !== 'object' || Array.isArray(requirements)) {
                throw new SessionFault('create-auth-unavailable');
            }
            if (Object.keys(requirements).length !== 0) {
                this.dispose();
                throw new SessionFault('passwords-session-expired');
            }
            return true;
        } catch (error) {
            if (error instanceof SessionFault) throw error;
            const status = safeStatusCode(error);
            if (status === 401 || status === 412) {
                this.dispose();
                throw new SessionFault('passwords-session-expired');
            }
            if (status === 403 || status === 429) {
                this.dispose();
                throw new SessionFault('auth-rate-limited');
            }
            // Unexpected transport failure is not proof of expired auth.
            // Fail before POST, but allow retry if the vault is still valid.
            throw new SessionFault('create-auth-unavailable');
        }
    }
    async createNewOtp(form, {verifySession} = {}) {
        // An ambiguous request is blocked in the session itself, not merely by the button.
        if (this.#createBlocked) throw new SessionFault('create-uncertain');
        this._checkActive();
        if (this.state !== 'ready') throw new SessionFault('auth-required');
        if (this.#creating) throw new SessionFault('create-busy');
        if (typeof verifySession !== 'function') throw new SessionFault('create-auth-unavailable');
        const values = buildNewOtpValues(form);
        const immutableForm = {label: values.label, username: values.username, password: values.password,
            secret: parseOtpCustomFields(values.customFields).otp.secret};
        const existingIds = new Set(this.#knownIds);
        this.#creating = true;
        let attempted = false, payload = null;
        try {
            if (await verifySession() !== true) { this.dispose(); throw new SessionFault('auth-required'); }
            this._checkActive();
            const settings = await this.client.getRequest().setPath('1.0/settings/list').send();
            this._checkActive();
            const mode = readEncryptionPreference(settings.getData());
            let encryption = null;
            if (mode === 'CSEv1r1') {
                if (!this.requiresChallenge) throw new SessionFault('create-cse-unavailable');
                encryption = this.client.getCseV1Encryption();
                if (!encryption || typeof encryption.ready !== 'function') throw new SessionFault('create-cse-unavailable');
                await this._crypto(() => encryption.ready());
            }
            payload = await this._crypto(() => prepareOtpCreatePayload(immutableForm,
                {mode, cseEncryption: encryption, subtle: this.subtle}));
            this._checkActive();
            // This is a fresh check, never the presenter's cached TOTP slot decision.
            if (await verifySession() !== true) { this.dispose(); throw new SessionFault('auth-required'); }
            this._checkActive();
            if (this.state !== 'ready') throw new SessionFault('auth-required');
            // Final Passwords authorization after encryption, BEFORE attempted=true.
            await this.assertCreateAccess();
            this._checkActive();
            attempted = true;
            const response = await withOneCreatePermit(this.client, () =>
                this.client.getRequest().setPath('1.0/password/create').setMethod('POST')
                    .setAcceptedStatusCodes([201]).setData(payload).send());
            this._checkActive();
            const created = response.getData();
            if (!created || typeof created.id !== 'string' || !created.id || created.id.length > 200
                    || typeof created.revision !== 'string' || !created.revision || created.revision.length > 200
                    || existingIds.has(created.id)) throw new SessionFault('create-unverified');
            if (await verifySession() !== true) { this.dispose(); throw new SessionFault('auth-required'); }
            this._checkActive();
            const snapshot = await this.readCount({expectedCreation: {...created, mode, values}});
            if (await verifySession() !== true) { this.dispose(); throw new SessionFault('auth-required'); }
            this._checkActive();
            return {snapshot, id: created.id};
        } catch (error) {
            if (attempted) {
                this.#createBlocked = true;
                this.dispose();
                throw new SessionFault('create-uncertain');
            }
            if ([401, 403, 412].includes(safeStatusCode(error))
                    || ['auth-required', 'auth-invalid', 'disposed'].includes(error?.code)) this.dispose();
            if (error?.code?.startsWith?.('create-')) throw error;
            throw new SessionFault(classifyError(error));
        } finally {
            values.password = ''; values.customFields = '';
            immutableForm.password = ''; immutableForm.secret = '';
            if (payload) { payload.password = ''; payload.customFields = ''; }
            this.#creating = false;
        }
    }
    async totpFor(id, nowMs = Date.now()) {
        this._checkActive();
        if (this.state !== 'ready') throw new SessionFault('auth-required');
        if (typeof id !== 'string' || !this.#totpKeys.has(id)) throw new SessionFault('unsupported-otp-type');
        try {
            const result = await calculateTotp(this.#totpKeys.get(id), nowMs, this.subtle);
            this._checkActive();
            if (this.state !== 'ready') throw new SessionFault('auth-required');
            return result;
        } catch (error) {
            this.dispose();
            throw new SessionFault(error instanceof SessionFault ? error.code : 'crypto-unavailable');
        }
    }
    snapshot() {
        const ready = this.state === 'ready' && !this.disposed;
        return {state: this.state, needsChallenge: this.requiresChallenge, needsToken: this.requiresToken,
            providers: this.providers.map(p => ({...p})), count: ready ? this.count : null,
            cseChecked: ready ? this.cseChecked : 0, otpCount: ready ? this.otpAccounts.length : null,
            invalidOtpCount: ready ? this.invalidOtpCount : 0,
            unsupportedOtpCount: ready ? this.unsupportedOtpCount : 0,
            otpAccounts: ready ? this.otpAccounts.map(item => ({...item})) : []};
    }
    _invalidate() {
        this.#totpKeys.clear();
        this.#knownIds.clear();
        this.state = 'locked'; this.count = null; this.cseChecked = 0;
        this.otpAccounts = []; this.invalidOtpCount = 0; this.unsupportedOtpCount = 0;
    }
    _release() {
        try { this.client.getCseV1Encryption().unsetKeychain(); } catch (_) { /* no secret logging */ }
        try { this.client.renewSession(); } catch (_) { /* no secret logging */ }
        this.authorization = null; this.providers = [];
        this.client = null;
    }
    async close() {
        if (this.disposed) return;
        const wasReady = this.state === 'ready';
        // Clear keys and block late read/create completions BEFORE awaiting the close request.
        this.disposed = true;
        this._invalidate();
        this.authorization = null; this.providers = [];
        abortClientRequests(this.client);
        try { this.client.getCseV1Encryption().unsetKeychain(); } catch (_) { /* safe */ }
        try { if (wasReady) await this.client.getRequest().setPath('1.0/session/close').send(); }
        catch (_) { /* Local lock must not depend on upstream network availability. */ }
        finally { abortClientRequests(this.client); this._release(); }
    }
    dispose() {
        if (this.disposed) return;
        this.disposed = true;
        this._invalidate();
        abortClientRequests(this.client);
        this._release();
    }
}
