import {englishText} from '../l10n/translator.mjs';

const CREATE_KEYS = Object.freeze({
    'create-invalid-label': 'create-error.create-invalid-label',
    'create-invalid-username': 'create-error.create-invalid-username',
    'create-invalid-password': 'create-error.create-invalid-password',
    'create-invalid-secret': 'create-error.create-invalid-secret',
    'create-cse-unavailable': 'create-error.create-cse-unavailable',
    'cse-unavailable': 'create-error.cse-unavailable',
    'create-crypto-unavailable': 'create-error.create-crypto-unavailable',
    'create-encryption-unknown': 'create-error.create-encryption-unknown',
    'create-busy': 'create-error.create-busy',
    'create-auth-unavailable': 'create-error.create-auth-unavailable',
    'passwords-session-expired': 'create-error.passwords-session-expired',
    'auth-rate-limited': 'create-error.auth-rate-limited',
    'create-uncertain': 'create-error.create-uncertain',
});
const SESSION_KEYS = Object.freeze({
    'https-required': 'session-error.https-required',
    'invalid-config': 'session-error.invalid-config',
    'invalid-api-url': 'session-error.invalid-api-url',
    'invalid-bootstrap-url': 'session-error.invalid-bootstrap-url',
    'csrf-unavailable': 'session-error.csrf-unavailable',
    'bootstrap-failed': 'session-error.bootstrap-failed',
    'disposed': 'session-error.disposed',
    'unsupported-challenge': 'session-error.unsupported-challenge',
    'unsupported-token-provider': 'session-error.unsupported-token-provider',
    'invalid-password-input': 'session-error.invalid-password-input',
    'invalid-master-key': 'session-error.invalid-master-key',
    'auth-invalid': 'session-error.auth-invalid',
    'auth-rate-limited': 'session-error.auth-rate-limited',
    'auth-required': 'session-error.auth-required',
    'invalid-list': 'session-error.invalid-list',
    'cse-unavailable': 'session-error.cse-unavailable',
    'unsupported-cse': 'session-error.unsupported-cse',
    'crypto-unavailable': 'session-error.crypto-unavailable',
});

export function safeCreateErrorCode(code) {
    return typeof code === 'string' && Object.hasOwn(CREATE_KEYS, code) ? code : 'create-failed';
}

export function createErrorMessage(code, t = englishText) {
    return t(CREATE_KEYS[safeCreateErrorCode(code)] ?? 'create-error.generic');
}

export function messageFor(code, t = englishText) {
    return t(typeof code === 'string' && Object.hasOwn(SESSION_KEYS, code) ? SESSION_KEYS[code]
        : 'session-error.generic');
}
