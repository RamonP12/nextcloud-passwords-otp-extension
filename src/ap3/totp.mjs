/**
 * RFC 6238 TOTP using WebCrypto. No network or persistent key storage.
 * Raw byte buffers are cleared; JavaScript strings/GC cannot be securely wiped.
 */
export class OtpCodeFault extends Error {
    constructor(code) { super(code); this.name = 'OtpCodeFault'; this.code = code; }
}
const HASHES = Object.freeze({sha1: 'SHA-1', sha256: 'SHA-256', sha512: 'SHA-512'});
const ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
function subtleOrThrow(subtle) {
    if (!subtle || typeof subtle.importKey !== 'function' || typeof subtle.sign !== 'function') {
        throw new OtpCodeFault('crypto-unavailable');
    }
    return subtle;
}
export function decodeBase32(value) {
    if (typeof value !== 'string' || value.length < 8 || value.length > 4096
            || !/^[A-Z2-7]+$/.test(value)) throw new OtpCodeFault('invalid-secret');
    const length = Math.floor(value.length * 5 / 8);
    const unusedBits = {0: 0, 2: 2, 4: 4, 5: 1, 7: 3}[value.length % 8];
    if (unusedBits === undefined || length < 5
            || (ALPHABET.indexOf(value.at(-1)) & ((1 << unusedBits) - 1)) !== 0) {
        throw new OtpCodeFault('invalid-secret');
    }
    const bytes = new Uint8Array(length);
    let accumulator = 0, bits = 0, position = 0;
    for (const symbol of value) {
        accumulator = (accumulator << 5) | ALPHABET.indexOf(symbol);
        bits += 5;
        if (bits >= 8) {
            bits -= 8;
            bytes[position++] = (accumulator >>> bits) & 0xff;
            accumulator &= (1 << bits) - 1;
        }
    }
    if (position !== length || accumulator !== 0) { bytes.fill(0); throw new OtpCodeFault('invalid-secret'); }
    return bytes;
}
export async function importTotpKey(config, subtle = globalThis.crypto?.subtle) {
    if (config?.type !== 'totp' || !Object.hasOwn(HASHES, config.algorithm)
            || !Number.isInteger(config.digits) || config.digits < 6 || config.digits > 9
            || !Number.isInteger(config.period) || config.period < 1 || config.period > 2_147_483_647) {
        throw new OtpCodeFault('invalid-otp-config');
    }
    const api = subtleOrThrow(subtle), raw = decodeBase32(config.secret);
    try {
        const key = await api.importKey('raw', raw,
            {name: 'HMAC', hash: {name: HASHES[config.algorithm]}}, false, ['sign']);
        return Object.freeze({key, digits: config.digits, period: config.period, algorithm: config.algorithm});
    } catch (_) { throw new OtpCodeFault('crypto-unavailable'); }
    finally { raw.fill(0); }
}
function timeStepBytes(step) {
    if (!Number.isSafeInteger(step) || step < 0) throw new OtpCodeFault('invalid-clock');
    const bytes = new Uint8Array(8);
    let value = BigInt(step);
    for (let i = 7; i >= 0; i--) { bytes[i] = Number(value & 0xffn); value >>= 8n; }
    return bytes;
}
// Dynamic HMAC truncation is an internal mathematical part of RFC 6238,
// not a public counter-based OTP feature or a persisted counter operation.
async function signTimeStep(keyInfo, step, subtle) {
    const api = subtleOrThrow(subtle);
    if (!keyInfo?.key || !Number.isInteger(keyInfo.digits) || keyInfo.digits < 6 || keyInfo.digits > 9) {
        throw new OtpCodeFault('invalid-otp-config');
    }
    const input = timeStepBytes(step);
    let digest;
    try {
        digest = new Uint8Array(await api.sign('HMAC', keyInfo.key, input));
        const offset = digest[digest.length - 1] & 0x0f;
        if (offset + 4 > digest.length) throw new OtpCodeFault('crypto-unavailable');
        const binary = (digest[offset] & 0x7f) * 0x1000000 + digest[offset + 1] * 0x10000
            + digest[offset + 2] * 0x100 + digest[offset + 3];
        return String(binary % (10 ** keyInfo.digits)).padStart(keyInfo.digits, '0');
    } catch (_) { throw new OtpCodeFault('crypto-unavailable'); }
    finally { input.fill(0); digest?.fill(0); }
}
export function timeSlot(nowMs, period) {
    if (!Number.isFinite(nowMs) || nowMs < 0 || !Number.isInteger(period)
            || period < 1 || period > 2_147_483_647) throw new OtpCodeFault('invalid-clock');
    const windowMs = period * 1000, counter = Math.floor(nowMs / windowMs);
    const expiresAt = (counter + 1) * windowMs;
    if (!Number.isSafeInteger(counter) || !Number.isSafeInteger(expiresAt)) throw new OtpCodeFault('invalid-clock');
    return {counter, expiresAt, remainingMs: Math.max(0, expiresAt - nowMs)};
}
export async function calculateTotp(keyInfo, nowMs = Date.now(), subtle = globalThis.crypto?.subtle) {
    if (!keyInfo || !Object.hasOwn(HASHES, keyInfo.algorithm)) throw new OtpCodeFault('invalid-otp-config');
    const slot = timeSlot(nowMs, keyInfo.period);
    const code = await signTimeStep(keyInfo, slot.counter, subtle);
    return {code, ...slot};
}
