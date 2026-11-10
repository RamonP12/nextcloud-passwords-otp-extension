/** Android-compatible TOTP custom-field decoding. No counter-based OTP support. */
export const ANDROID_OTP_LABEL = 'client.ios.otp';
const ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
const MAX_CUSTOM_FIELDS_LENGTH = 1_048_576;
const MAX_OTP_VALUE_LENGTH = 16_384;
const MAX_BASE32_SOURCE_LENGTH = 4_096;
const MAX_FIELDS = 512;
const MAX_DISPLAY_LENGTH = 160;
const MAX_ANDROID_INT = 2_147_483_647;
const absent = Object.freeze({status: 'absent'});
const invalid = Object.freeze({status: 'invalid'});
const unsupported = Object.freeze({status: 'unsupported'});
function plainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}
function readJson(text, limit) {
    if (typeof text !== 'string' || text.length > limit) return null;
    try { return JSON.parse(text); } catch { return null; }
}
export function normalizeBase32Secret(raw, {minBytes = 5} = {}) {
    if (typeof raw !== 'string' || !raw.length || raw.length > MAX_BASE32_SOURCE_LENGTH) return null;
    const normalized = raw.trim().replace(/[\s-]/g, '').toUpperCase();
    const match = /^([A-Z2-7]+)(=*)$/.exec(normalized);
    if (!match) return null;
    const chars = match[1], padding = match[2], remainder = chars.length % 8;
    const unusedBits = {0: 0, 2: 2, 4: 4, 5: 1, 7: 3}[remainder];
    if (unusedBits === undefined) return null;
    if (padding && padding.length !== (8 - remainder) % 8) return null;
    // Existing interoperable TOTP secrets may be shorter than 80 bits.
    // New secrets are still required to be at least 80 bits at creation.
    if (Math.floor(chars.length * 5 / 8) < minBytes) return null;
    if ((ALPHABET.indexOf(chars.at(-1)) & ((1 << unusedBits) - 1)) !== 0) return null;
    return chars;
}
export function parseAndroidOtpJson(text) {
    const value = readJson(text, MAX_OTP_VALUE_LENGTH);
    if (!plainObject(value)) return null;
    const secret = normalizeBase32Secret(value.secret);
    if (!secret) return null;
    const type = value.type === undefined ? 'totp' : value.type;
    const algorithm = value.algorithm === undefined ? 'sha1' : value.algorithm;
    const digits = value.digits === undefined ? 6 : value.digits;
    const period = value.period === undefined ? 30 : value.period;
    if (type !== 'totp' || !['sha1', 'sha256', 'sha512'].includes(algorithm)) return null;
    if (!Number.isInteger(digits) || digits < 6 || digits > 9) return null;
    if (!Number.isInteger(period) || period < 1 || period > MAX_ANDROID_INT) return null;
    for (const name of ['issuer', 'accountName']) {
        if (value[name] !== undefined && value[name] !== null && typeof value[name] !== 'string') return null;
    }
    return {secret, type, algorithm, digits, period,
        issuer: value.issuer ?? null, accountName: value.accountName ?? null};
}
export function parseOtpCustomFields(raw) {
    if (raw === undefined || raw === null || raw === '') return absent;
    const fields = Array.isArray(raw) ? raw : readJson(raw, MAX_CUSTOM_FIELDS_LENGTH);
    if (!Array.isArray(fields) || fields.length > MAX_FIELDS) return invalid;
    let field = null;
    for (const item of fields) {
        if (!plainObject(item) || typeof item.label !== 'string') return invalid;
        if (item.label !== ANDROID_OTP_LABEL) continue;
        if (field !== null) return invalid;
        field = item;
    }
    if (field === null) return absent;
    if (field.type !== 'data' || typeof field.value !== 'string') return invalid;
    const data = readJson(field.value, MAX_OTP_VALUE_LENGTH);
    if (plainObject(data) && typeof data.type === 'string' && data.type !== 'totp') return unsupported;
    const otp = parseAndroidOtpJson(field.value);
    return otp === null ? invalid : {status: 'valid', otp};
}
function visibleText(value) {
    if (typeof value !== 'string') return '';
    return value.replace(/[\u0000-\u001F\u007F-\u009F\u202A-\u202E\u2066-\u2069]/g, ' ')
        .trim().slice(0, MAX_DISPLAY_LENGTH);
}
export function toPublicOtpAccount(record, otp) {
    if (!plainObject(record) || typeof record.id !== 'string' || !record.id.length
            || record.id.length > 200 || !plainObject(otp) || otp.type !== 'totp') return null;
    const issuer = visibleText(otp.issuer), accountName = visibleText(otp.accountName);
    return Object.freeze({id: record.id, title: visibleText(record.label) || issuer || 'OTP-Konto',
        username: visibleText(record.username), issuer, accountName, type: 'totp',
        algorithm: otp.algorithm, digits: otp.digits, period: otp.period});
}
export function searchOtpAccounts(accounts, query) {
    if (!Array.isArray(accounts)) return [];
    if (typeof query !== 'string' || query.trim() === '') return accounts.slice();
    const needle = query.trim().toLocaleLowerCase().slice(0, MAX_DISPLAY_LENGTH);
    return accounts.filter(account => [account.title, account.username, account.issuer, account.accountName]
        .some(value => typeof value === 'string' && value.toLocaleLowerCase().includes(needle)));
}
export function filterUnencryptedOtpRecords(records) {
    if (!Array.isArray(records)) return {accounts: [], invalidOtpCount: 0};
    const accounts = [], seenIds = new Set();
    let invalidOtpCount = 0;
    for (const record of records) {
        if (!plainObject(record)) { invalidOtpCount++; continue; }
        const result = parseOtpCustomFields(record.customFields);
        if (result.status === 'invalid') { invalidOtpCount++; continue; }
        if (result.status !== 'valid') continue;
        const account = toPublicOtpAccount(record, result.otp);
        if (!account || seenIds.has(account.id)) { invalidOtpCount++; continue; }
        seenIds.add(account.id);
        accounts.push(account);
    }
    return {accounts, invalidOtpCount};
}
