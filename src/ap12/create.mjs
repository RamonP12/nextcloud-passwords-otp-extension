import {normalizeBase32Secret, parseOtpCustomFields} from '../ap2/parser.mjs';
export class OtpCreateFault extends Error {
    constructor(code) { super(code); this.name = 'OtpCreateFault'; this.code = code; }
}
const ROOT_FOLDER = '00000000-0000-0000-0000-000000000000';
const plainString = value => typeof value === 'string';
export function buildNewOtpValues({label, username = '', password, secret} = {}) {
    if (!plainString(label) || !label.trim() || label.trim().length > 160) throw new OtpCreateFault('create-invalid-label');
    if (!plainString(username) || username.trim().length > 160) throw new OtpCreateFault('create-invalid-username');
    if (!plainString(password) || !password.trim() || password === '0' || password.length > 4096) {
        throw new OtpCreateFault('create-invalid-password');
    }
    const canonical = normalizeBase32Secret(secret, {minBytes: 10});
    if (canonical === null) throw new OtpCreateFault('create-invalid-secret');
    const title = label.trim(), user = username.trim();
    const otpConfiguration = {secret: canonical, type: 'totp', algorithm: 'sha1', digits: 6,
        period: 30, issuer: title, accountName: user || null};
    const customFields = JSON.stringify([{label: 'client.ios.otp', type: 'data', value: JSON.stringify(otpConfiguration)}]);
    if (parseOtpCustomFields(customFields).status !== 'valid') throw new OtpCreateFault('create-invalid-secret');
    return {label: title, username: user, password, url: '', notes: '', customFields,
        cseType: 'none', folder: ROOT_FOLDER, hidden: false, favorite: false, tags: []};
}
export async function sha1ForPasswords(value, subtle = globalThis.crypto?.subtle) {
    if (!subtle || !plainString(value)) throw new OtpCreateFault('create-crypto-unavailable');
    const bytes = new TextEncoder().encode(value);
    let digest;
    try {
        digest = new Uint8Array(await subtle.digest('SHA-1', bytes));
        return Array.from(digest, b => b.toString(16).padStart(2, '0')).join('');
    } finally { bytes.fill(0); digest?.fill(0); }
}
export async function prepareOtpCreatePayload(form, {
    mode, cseEncryption = null, subtle = globalThis.crypto?.subtle
} = {}) {
    const plain = buildNewOtpValues(form);
    if (mode === 'none') return plain;
    if (mode !== 'CSEv1r1' || !cseEncryption || typeof cseEncryption.encrypt !== 'function'
            || cseEncryption.enabled?.() !== true) throw new OtpCreateFault('create-cse-unavailable');
    try {
        const hash = await sha1ForPasswords(plain.password, subtle);
        let encrypted;
        try { encrypted = await cseEncryption.encrypt({...plain, hash}, 'password'); }
        catch (_) { throw new OtpCreateFault('create-cse-unavailable'); }
        if (encrypted?.cseType !== 'CSEv1r1' || !plainString(encrypted.cseKey) || !encrypted.cseKey
                || encrypted.hash !== hash) throw new OtpCreateFault('create-cse-unavailable');
        // Every NONEMPTY sensitive field must be transformed, including username.
        // Empty url/notes may remain empty in the original client format.
        for (const field of ['password', 'label', 'username', 'customFields', 'url', 'notes']) {
            if (plain[field] && (!plainString(encrypted[field]) || !encrypted[field]
                    || encrypted[field] === plain[field])) throw new OtpCreateFault('create-cse-unavailable');
        }
        return encrypted;
    } finally {
        plain.password = '';
        plain.customFields = '';
    }
}
export function readEncryptionPreference(raw) {
    const mode = raw?.['user.encryption.cse'];
    if (mode === 1 || mode === '1') return 'CSEv1r1';
    if (mode === 0 || mode === '0') return 'none';
    throw new OtpCreateFault('create-encryption-unknown');
}
/** Compare the new record only; ordinary list reads never decrypt stored passwords. */
export function verifyCreatedRecord(record, plain, expected) {
    const otp = parseOtpCustomFields(plain.customFields);
    const source = parseOtpCustomFields(expected.values.customFields);
    if (!record || record.id !== expected.id || record.revision !== expected.revision
            || (record.cseType || 'none') !== expected.mode
            || plain.label !== expected.values.label || plain.username !== expected.values.username
            || plain.password !== expected.values.password
            || otp.status !== 'valid' || source.status !== 'valid'
            || ['secret', 'type', 'algorithm', 'digits', 'period', 'issuer', 'accountName']
                .some(key => otp.otp[key] !== source.otp[key])) {
        throw new OtpCreateFault('create-unverified');
    }
}
