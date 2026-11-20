import {createTranslator} from '../../src/l10n/translator.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
import {createOtpController} from '../../src/ui/controller.mjs';
import {clearSensitiveDom} from '../../src/ui/dom-safety.mjs';
import {createErrorMessage, messageFor, safeCreateErrorCode} from '../../src/ui/messages.mjs';
import {SessionFault} from '../../src/ap1/session.mjs';
import {deferred, settle} from './helpers.mjs';

const german = createTranslator('de');

const account = {id: 'synthetic', title: 'Synthetic account', type: 'totp', period: 30,
    algorithm: 'sha1', digits: 6};
const snapshot = (state = 'ready', extra = {}) => ({state, needsChallenge: false, needsToken: false,
    providers: [], otpCount: state === 'ready' ? 1 : null,
    invalidOtpCount: 0, unsupportedOtpCount: 0, otpAccounts: state === 'ready' ? [account] : [], ...extra});
const otp = (code = '001234', extraRows = []) => ({state: 'ready', notice: '', rows: [
    {account, code, remainingMs: code === null ? 0 : 29000, copyDisabled: code === null, hidden: false}, ...extraRows]});
const emptyOtp = () => ({state: 'locked', rows: [], notice: ''});
const auth = () => ({password: 'SYNTHETIC-MASTER-PASSWORD', providerId: 'provider', otpCode: '001234'});
const values = () => ({label: 'Synthetic service', username: 'synthetic@example.invalid',
    password: 'SYNTHETIC-SERVICE-PASSWORD', secret: 'JBSWY3DPEHPK3PXP'});

function fixture(options = {}) {
    const calls = [], publications = [], clears = [], focuses = [], unlockInputs = [], createInputs = [];
    let state, presenterOptions, verificationCount = 0, bootstrapSignal;
    const doc = {hidden: false};
    const config = options.config || {status: 'ready', sessionFingerprint: 'a'.repeat(64)};
    const validated = {baseUrl: 'https://fixture.invalid/', apiRoot: 'https://fixture.invalid/apps/passwords/api/',
        user: 'SYNTHETIC-USER', token: 'SYNTHETIC-TOKEN'};
    const client = {syntheticClient: true};
    const session = {
        state: 'new', disposed: false,
        async begin() {
            calls.push('begin');
            const result = options.begin ? await options.begin(session) : snapshot(options.initial || 'ready', options.initialFields);
            if (!session.disposed) session.state = result.state;
            return result;
        },
        async unlock(credentials) {
            calls.push('unlock');
            unlockInputs.push({reference: credentials, received: {...credentials}});
            const result = options.unlock ? await options.unlock(credentials, session) : snapshot();
            if (!session.disposed) session.state = result.state;
            return result;
        },
        async assertCreateAccess() {
            calls.push('probe');
            return options.probe ? options.probe(session) : true;
        },
        async createNewOtp(input, context) {
            calls.push('create');
            createInputs.push({reference: input, received: {...input}, context});
            return options.create ? options.create(input, context, session) : {snapshot: snapshot(), id: 'new'};
        },
        dispose() {
            calls.push('dispose');
            session.disposed = true;
            session.state = 'locked';
            options.dispose?.();
        },
        close() {
            calls.push('close');
            session.disposed = true;
            session.state = 'locked';
            return options.close ? options.close() : Promise.resolve();
        },
    };
    const verify = async () => {
        calls.push('verify');
        verificationCount++;
        return options.verify ? options.verify(verificationCount, session) : true;
    };
    const presenter = {
        setSession(value) { assert.equal(value, session); calls.push('set-session'); },
        render(value, query) {
            calls.push(['render', value.state, query]);
            presenterOptions.publish(value.state === 'ready' ? otp() : emptyOtp());
        },
        filter(query) { calls.push(['filter', query]); },
        copy(id) { calls.push(['copy', id]); },
        visibilityChanged() { calls.push('visibility'); },
        focusChanged() { calls.push('focus'); },
        dispose() {
            calls.push('presenter-dispose');
            presenterOptions.publish(emptyOtp());
            options.presenterDispose?.();
        },
    };
    const controller = createOtpController({config, t: german, now: options.now, pageUrl: 'https://fixture.invalid/apps/passwords_otp/',
        doc, fetcher: () => { throw new Error('network must be injected'); },
        publish: next => { state = next; publications.push(next); },
        clear: instruction => { clears.push(instruction); options.clear?.(instruction); },
        focus: name => { focuses.push(name); },
        sodiumReady: async () => { calls.push('sodium'); return options.sodium?.(); },
        bootstrap: async (initial, pageUrl, document, fetcher, signal) => {
            calls.push('bootstrap'); bootstrapSignal = signal;
            if (options.bootstrap) return options.bootstrap(validated, signal);
            return validated;
        },
        createClient: credentials => {
            calls.push('client');
            assert.equal(credentials, validated);
            assert.equal(credentials.token, 'SYNTHETIC-TOKEN');
            if (options.createClient) return options.createClient(credentials);
            return client;
        },
        createSession: instance => {
            calls.push('session');
            assert.equal(instance, client);
            if (options.createSession) return options.createSession(instance);
            return session;
        },
        createPresenter: callbacks => { presenterOptions = callbacks; calls.push('presenter'); return presenter; },
        checkSession: initial => { assert.equal(initial, config); calls.push('check-factory'); return verify; },
    });
    return {controller, calls, publications, clears, focuses, session, doc, validated,
        unlockInputs, createInputs, verify, state: () => state,
        presenterOptions: () => presenterOptions, bootstrapSignal: () => bootstrapSignal,
        count: name => calls.filter(value => value === name).length,
        async ready() { await controller.start(); assert.equal(state.mode, options.initial || 'ready'); return this; },
    };
}

test('Startup checks session before credentials, after session construction, and after begin', async () => {
    const f = fixture();
    await f.ready();
    assert.deepEqual(f.calls.filter(value => typeof value === 'string'), [
        'check-factory', 'presenter', 'sodium', 'verify', 'bootstrap', 'client', 'session', 'set-session', 'verify', 'begin', 'verify']);
    assert.equal(f.validated.token, '');
    assert.equal(f.validated.user, '');
    assert.doesNotMatch(JSON.stringify(f.publications), /SYNTHETIC-TOKEN|SYNTHETIC-USER|syntheticClient/);
    await f.controller.start();
    assert.equal(f.count('bootstrap'), 1, 'startup is one-shot');
    f.controller.pageHide();
});

test('Unavailable integration fails before bootstrap and cannot be restarted', async () => {
    const f = fixture({config: {status: 'unavailable'}});
    await f.controller.start();
    assert.equal(f.state().mode, 'locked');
    assert.equal(f.state().canReload, true);
    assert.equal(f.count('bootstrap'), 0);
    await f.controller.start();
    assert.equal(f.count('bootstrap'), 0);
});

test('Rejected initial session never requests a bearer token', async () => {
    const f = fixture({verify: () => false});
    await f.controller.start();
    assert.equal(f.count('bootstrap'), 0);
    assert.equal(f.count('client'), 0);
    assert.equal(f.state().mode, 'locked');
});

test('Startup clears bootstrap credentials when client construction throws', async () => {
    const f = fixture({createClient: () => { throw new Error('PRIVATE-CONSTRUCTION-ERROR'); }});
    await f.controller.start();
    assert.equal(f.validated.user, '');
    assert.equal(f.validated.token, '');
    assert.equal(f.state().mode, 'locked');
    assert.doesNotMatch(JSON.stringify(f.publications), /PRIVATE-CONSTRUCTION-ERROR/);
});

test('Startup clears bootstrap credentials when session construction throws', async () => {
    const f = fixture({createSession: () => { throw new Error('PRIVATE-CONSTRUCTION-ERROR'); }});
    await f.controller.start();
    assert.equal(f.validated.user, '');
    assert.equal(f.validated.token, '');
    assert.equal(f.state().mode, 'locked');
});

test('Pagehide while waiting for sodium aborts startup before credentials', async () => {
    const sodium = deferred();
    const f = fixture({sodium: () => sodium.promise});
    const pending = f.controller.start();
    await settle();
    f.controller.pageHide();
    assert.equal(f.state().mode, 'locked');
    sodium.resolve();
    await pending;
    assert.equal(f.count('bootstrap'), 0);
    assert.equal(f.count('client'), 0);
});

test('Late bootstrap after pagehide is wiped without constructing a client', async () => {
    const pendingBootstrap = deferred();
    const f = fixture({bootstrap: async value => { await pendingBootstrap.promise; return value; }});
    const pending = f.controller.start();
    await settle();
    f.controller.pageHide();
    assert.equal(f.bootstrapSignal().aborted, true);
    pendingBootstrap.resolve();
    await pending;
    assert.equal(f.validated.user, '');
    assert.equal(f.validated.token, '');
    assert.equal(f.count('client'), 0);
    assert.equal(f.state().mode, 'locked');
});

test('Late begin completion after pagehide cannot publish ready state', async () => {
    const pendingBegin = deferred();
    const f = fixture({begin: () => pendingBegin.promise});
    const pending = f.controller.start();
    await settle();
    f.controller.pageHide();
    const closedAt = f.publications.length;
    pendingBegin.resolve(snapshot());
    await pending;
    assert.equal(f.count('close'), 1);
    assert.equal(f.state().mode, 'locked');
    assert.equal(f.state().snapshot, null);
    assert.equal(f.publications.slice(closedAt).some(state => state.mode === 'ready'), false);
});

test('Unsupported or missing required 2FA providers fail closed', async () => {
    for (const providers of [[], [{id: 'unsupported', supported: false}]]) {
        const f = fixture({initial: 'needs-auth', initialFields: {needsToken: true, providers}});
        await f.controller.start();
        assert.equal(f.state().mode, 'locked');
        assert.equal(f.session.disposed, true);
        assert.match(f.state().status, /2FA-Anbieter/);
        assert.equal(f.count('unlock'), 0);
    }
});

test('Challenge and supported token requirements focus the relevant field', async () => {
    for (const [fields, expected] of [
        [{needsChallenge: true}, 'master'],
        [{needsToken: true, providers: [{id: 'provider', supported: true}]}, 'token'],
    ]) {
        const f = fixture({initial: 'needs-auth', initialFields: fields});
        await f.ready();
        assert.equal(f.focuses.at(-1), expected);
        f.controller.pageHide();
    }
});

test('Unlock scrubs caller values immediately and duplicate submit cannot alter the in-flight values or busy flag', async () => {
    const gate = deferred();
    const f = fixture({initial: 'needs-auth', verify: number => number === 4 ? gate.promise : true});
    await f.ready();
    const input = auth();
    const pending = f.controller.unlock(input);
    assert.equal(f.state().unlockBusy, true);
    assert.equal(input.password, '');
    assert.equal(input.otpCode, '');
    await f.controller.unlock(input);
    assert.equal(f.state().unlockBusy, true);
    gate.resolve(true);
    await pending;
    assert.equal(f.count('unlock'), 1);
    assert.equal(f.unlockInputs[0].received.password, 'SYNTHETIC-MASTER-PASSWORD');
    assert.equal(f.unlockInputs[0].received.otpCode, '001234');
    assert.equal(f.unlockInputs[0].reference.password, '');
    assert.equal(f.unlockInputs[0].reference.otpCode, '');
    assert.equal(f.state().unlockBusy, false);
    assert.equal(f.state().mode, 'ready');
    assert.doesNotMatch(JSON.stringify(f.publications), /SYNTHETIC-MASTER-PASSWORD/);
    f.controller.pageHide();
});

test('Only the precise invalid-master-key error permits an unlock retry', async () => {
    let attempt = 0;
    const f = fixture({initial: 'needs-auth', initialFields: {needsChallenge: true},
        unlock: async () => { if (++attempt === 1) throw new SessionFault('invalid-master-key'); return snapshot(); }});
    await f.ready();
    const first = auth();
    await f.controller.unlock(first);
    assert.equal(f.state().mode, 'needs-auth');
    assert.equal(f.state().unlockError, 'invalid-master-key');
    assert.equal(f.state().unlockBusy, false);
    assert.equal(f.session.disposed, false);
    assert.equal(f.focuses.at(-1), 'master');
    await f.controller.unlock(auth());
    assert.equal(f.state().mode, 'ready');
    assert.equal(f.count('unlock'), 2);
    f.controller.pageHide();
});

test('Arbitrary authentication errors never masquerade as a wrong master password', async () => {
    for (const code of ['auth-invalid', 'auth-required', 'api-error', 'PRIVATE-ERROR-CODE', '__proto__']) {
        const f = fixture({initial: 'needs-auth', unlock: async () => { throw new SessionFault(code); }});
        await f.ready();
        await f.controller.unlock(auth());
        assert.equal(f.state().mode, 'locked');
        assert.equal(f.state().unlockError, '');
        assert.equal(f.session.disposed, true);
        assert.doesNotMatch(JSON.stringify(f.publications), /PRIVATE-ERROR-CODE|SYNTHETIC-MASTER-PASSWORD/);
    }
});

test('Nextcloud proof is required before and after unlocking', async () => {
    for (const failingCheck of [4, 5]) {
        const f = fixture({initial: 'needs-auth', verify: number => number !== failingCheck});
        await f.ready();
        await f.controller.unlock(auth());
        assert.equal(f.count('unlock'), failingCheck === 4 ? 0 : 1);
        assert.equal(f.state().mode, 'locked');
        assert.equal(f.session.disposed, true);
    }
});

test('Pagehide during unlock prevents a late success from reopening the vault', async () => {
    const gate = deferred();
    const f = fixture({initial: 'needs-auth', unlock: () => gate.promise});
    await f.ready();
    const input = auth();
    const pending = f.controller.unlock(input);
    await settle();
    f.controller.pageHide();
    const closedAt = f.publications.length;
    gate.resolve(snapshot());
    await pending;
    assert.equal(f.state().mode, 'locked');
    assert.equal(f.state().snapshot, null);
    assert.equal(f.unlockInputs[0].reference.password, '');
    assert.equal(f.publications.slice(closedAt).some(state => state.mode === 'ready'), false);
});

test('Opening CREATE performs Nextcloud, Passwords and Nextcloud checks in sequence', async () => {
    const f = fixture();
    await f.ready();
    const start = f.calls.length;
    await f.controller.openCreate();
    assert.deepEqual(f.calls.slice(start), ['verify', 'probe', 'verify']);
    assert.equal(f.state().createOpen, true);
    assert.equal(f.state().createOpening, false);
    assert.equal(f.focuses.at(-1), 'label');
    await f.controller.openCreate();
    assert.equal(f.count('probe'), 1);
    assert.equal(f.controller.closeCreate(), true);
    assert.equal(f.state().createOpen, false);
    assert.equal(f.focuses.at(-1), 'create');
    f.controller.pageHide();
});

test('Duplicate open while probing never makes a second request or clears opening state', async () => {
    const gate = deferred();
    const f = fixture({probe: () => gate.promise});
    await f.ready();
    const pending = f.controller.openCreate();
    await settle();
    await f.controller.openCreate();
    assert.equal(f.count('probe'), 1);
    assert.equal(f.state().createOpening, true);
    assert.equal(f.state().createOpen, false);
    gate.resolve(true);
    await pending;
    assert.equal(f.state().createOpen, true);
    f.controller.pageHide();
});

test('Pagehide during CREATE probe cannot open the late dialog', async () => {
    const gate = deferred();
    const f = fixture({probe: () => gate.promise});
    await f.ready();
    const pending = f.controller.openCreate();
    await settle();
    f.controller.pageHide();
    gate.resolve(true);
    await pending;
    assert.equal(f.state().mode, 'locked');
    assert.equal(f.state().createOpen, false);
    assert.equal(f.focuses.includes('label'), false);
});

test('Both Nextcloud guards around the CREATE probe are mandatory', async () => {
    for (const failingCheck of [4, 5]) {
        const f = fixture({verify: number => number !== failingCheck});
        await f.ready();
        await f.controller.openCreate();
        assert.equal(f.count('probe'), failingCheck === 4 ? 0 : 1);
        assert.equal(f.state().createOpen, false);
        assert.equal(f.state().mode, 'locked');
    }
});

test('Disposed API expiry and rate-limit errors preserve their precise cause', async () => {
    for (const code of ['passwords-session-expired', 'auth-rate-limited']) {
        const f = fixture({probe: session => { session.dispose(); throw new SessionFault(code); }});
        await f.ready();
        await f.controller.openCreate();
        assert.equal(f.state().mode, 'locked');
        assert.equal(f.state().status, createErrorMessage(code, german));
        assert.equal(f.state().createOpen, false);
        if (code === 'auth-rate-limited') assert.match(f.state().status, /nicht als abgelaufen nachgewiesen/);
    }
});

test('Transient probe failure before POST allows an explicit retry', async () => {
    let attempt = 0;
    const f = fixture({probe: () => { if (++attempt === 1) throw new SessionFault('create-auth-unavailable'); return true; }});
    await f.ready();
    await f.controller.openCreate();
    assert.equal(f.state().mode, 'ready');
    assert.equal(f.state().statusType, 'warning');
    assert.equal(f.state().createOpen, false);
    assert.equal(f.state().createOpening, false);
    await f.controller.openCreate();
    assert.equal(f.state().createOpen, true);
    assert.equal(f.count('probe'), 2);
    f.controller.pageHide();
});

test('CREATE requires an opened, ready dialog and clears refused secrets', async () => {
    const f = fixture();
    await f.ready();
    const input = values();
    await f.controller.create(input);
    assert.equal(input.password, '');
    assert.equal(input.secret, '');
    assert.equal(f.count('create'), 0);
    f.controller.pageHide();
});

test('CREATE passes the live verifier to the domain; duplicate submits cannot unblock the in-flight write', async () => {
    const gate = deferred();
    const f = fixture({create: () => gate.promise});
    await f.ready();
    await f.controller.openCreate();
    const input = values();
    const pending = f.controller.create(input);
    assert.equal(input.password, '');
    assert.equal(input.secret, '');
    assert.equal(f.state().createBusy, true);
    const checks = f.count('verify');
    assert.equal(await f.createInputs[0].context.verifySession(), true);
    assert.equal(f.count('verify'), checks + 1);
    assert.equal(f.controller.closeCreate(), false);
    await f.controller.create(input);
    assert.equal(f.count('create'), 1);
    assert.equal(f.state().createBusy, true);
    gate.resolve({snapshot: snapshot(), id: 'new'});
    await pending;
    assert.equal(f.createInputs[0].received.password, 'SYNTHETIC-SERVICE-PASSWORD');
    assert.equal(f.createInputs[0].reference.password, '');
    assert.equal(f.createInputs[0].reference.secret, '');
    assert.equal(f.state().createBusy, false);
    assert.equal(f.state().createOpen, false);
    assert.equal(f.state().statusType, 'success');
    assert.equal(f.focuses.at(-1), 'create');
    assert.doesNotMatch(JSON.stringify(f.publications), /SYNTHETIC-SERVICE-PASSWORD|JBSWY3DPEHPK3PXP/);
    f.controller.pageHide();
});

test('Validation error preserves the dialog, clears secrets and focuses its error field', async () => {
    const f = fixture({create: async () => { throw new SessionFault('create-invalid-secret'); }});
    await f.ready();
    await f.controller.openCreate();
    const input = values();
    await f.controller.create(input);
    assert.equal(f.state().mode, 'ready');
    assert.equal(f.state().createOpen, true);
    assert.equal(f.state().createBusy, false);
    assert.equal(f.state().createError, 'create-invalid-secret');
    assert.equal(f.focuses.at(-1), 'secret');
    assert.equal(input.secret, '');
    assert.equal(f.createInputs[0].reference.secret, '');
    f.controller.pageHide();
});

test('Unknown CREATE errors never carry secret exception details into public state', async () => {
    for (const code of ['create-PRIVATE-SECRET', '__proto__', 'constructor', {private: 'PRIVATE-SECRET'}]) {
        const f = fixture({create: async () => { throw {code, message: 'PRIVATE-MESSAGE', stack: 'PRIVATE-STACK'}; }});
        await f.ready();
        await f.controller.openCreate();
        await f.controller.create(values());
        assert.equal(f.state().createError, 'create-failed');
        assert.doesNotMatch(JSON.stringify(f.publications), /PRIVATE/);
        f.controller.pageHide();
    }
});

test('Ambiguous CREATE blocks all retry paths and preserves the warning against late callbacks', async () => {
    const f = fixture({create: async (input, context, session) => {
        session.dispose(); throw new SessionFault('create-uncertain');
    }});
    await f.ready();
    await f.controller.openCreate();
    await f.controller.create(values());
    assert.equal(f.state().mode, 'locked');
    assert.equal(f.state().createBlocked, true);
    const status = f.state().status;
    assert.equal(status, createErrorMessage('create-uncertain', german));
    await f.controller.openCreate();
    await f.controller.create(values());
    f.presenterOptions().fatal('LATE-LESS-PRECISE-CAUSE');
    f.presenterOptions().notify('LATE-FEEDBACK');
    f.presenterOptions().publish(otp());
    assert.equal(f.count('create'), 1);
    assert.equal(f.state().status, status);
    assert.equal(f.state().otp.rows.length, 0);
    assert.equal(f.state().feedback, '');
});

test('Late CREATE success after pagehide cannot publish an entry or a success message', async () => {
    const gate = deferred();
    const f = fixture({create: () => gate.promise});
    await f.ready();
    await f.controller.openCreate();
    const pending = f.controller.create(values());
    f.controller.pageHide();
    const closedAt = f.publications.length;
    gate.resolve({snapshot: snapshot(), id: 'new'});
    await pending;
    assert.equal(f.state().mode, 'locked');
    assert.equal(f.state().createOpen, false);
    assert.equal(f.state().createBusy, false);
    assert.equal(f.createInputs[0].reference.secret, '');
    assert.equal(f.publications.slice(closedAt).some(state => state.statusType === 'success'), false);
});

test('BFCache restore remains terminal and cannot be overwritten by late CREATE errors', async () => {
    const gate = deferred();
    const f = fixture({create: () => gate.promise});
    await f.ready();
    await f.controller.openCreate();
    const pending = f.controller.create(values());
    f.controller.pageHide();
    f.controller.pageShow({persisted: true});
    const restoredStatus = f.state().status;
    gate.reject(new SessionFault('create-invalid-secret'));
    await pending;
    assert.equal(f.state().status, restoredStatus);
    assert.equal(f.state().createError, '');
    assert.equal(f.state().mode, 'locked');
    assert.equal(f.state().canReload, true);
    await f.controller.start();
    await f.controller.openCreate();
    assert.equal(f.count('bootstrap'), 1);
    assert.equal(f.count('probe'), 1);
    assert.equal(f.controller.closeCreate(), false);
});

test('Persisted pageshow locks even when no pagehide event was observed', async () => {
    const f = fixture();
    await f.ready();
    f.controller.pageShow({persisted: true});
    assert.equal(f.state().mode, 'locked');
    assert.equal(f.count('close'), 1);
    f.controller.copy('synthetic');
    assert.equal(f.calls.some(value => Array.isArray(value) && value[0] === 'copy'), false);
});

test('Regular pageshow preserves the current session', async () => {
    const f = fixture();
    await f.ready();
    f.controller.pageShow({persisted: false});
    assert.equal(f.state().mode, 'ready');
    assert.equal(f.count('close'), 0);
    f.controller.pageHide();
});

test('Pagehide locks synchronously without waiting for best-effort server revocation', async () => {
    const closed = deferred();
    const f = fixture({close: () => closed.promise});
    await f.ready();
    f.controller.pageHide();
    assert.equal(f.state().mode, 'locked');
    assert.equal(f.session.disposed, true);
    assert.equal(f.state().otp.rows.length, 0);
    assert.equal(f.clears.at(-1).lock, true);
    f.controller.pageHide();
    assert.equal(f.count('close'), 1);
    closed.reject(new Error('synthetic failed best-effort revocation'));
    await settle();
});

test('Cleanup exceptions cannot prevent terminal view clearing or server close attempts', async () => {
    const f = fixture({dispose: () => { throw new Error('synthetic dispose failure'); }});
    await f.ready();
    assert.throws(() => f.controller.fail(), /synthetic dispose failure/);
    assert.equal(f.state().mode, 'locked');
    assert.equal(f.count('presenter-dispose'), 1);
    assert.equal(f.clears.at(-1).lock, true);
    const g = fixture({presenterDispose: () => { throw new Error('synthetic presenter failure'); }});
    await g.ready();
    assert.throws(() => g.controller.pageHide(), /synthetic presenter failure/);
    assert.equal(g.state().mode, 'locked');
    assert.equal(g.count('close'), 1);
    assert.equal(g.session.disposed, true);
});

test('Search and copy delegate only while authorized, preserving the active query after CREATE', async () => {
    const f = fixture();
    await f.ready();
    f.controller.filter('service');
    f.controller.copy('synthetic');
    assert.equal(f.state().query, 'service');
    assert.ok(f.calls.some(value => Array.isArray(value) && value[0] === 'filter' && value[1] === 'service'));
    await f.controller.openCreate();
    await f.controller.create(values());
    assert.ok(f.calls.some(value => Array.isArray(value) && value[0] === 'render' && value[2] === 'service'));
    f.controller.pageHide();
    const at = f.calls.length;
    f.controller.filter('must-not-appear');
    f.controller.copy('synthetic');
    assert.equal(f.calls.length, at);
    assert.equal(f.state().query, '');
});

test('Background clears input and code DOM before delegating the visibility event', async () => {
    const f = fixture();
    await f.ready();
    f.doc.hidden = true;
    f.controller.visibilityChanged();
    assert.deepEqual(f.clears.at(-1), {inputs: true, codes: true});
    assert.equal(f.calls.at(-1), 'visibility');
    assert.equal(f.presenterOptions().isHidden(), true);
    f.doc.hidden = false;
    assert.equal(f.presenterOptions().isHidden(), false);
    f.controller.focusChanged();
    assert.equal(f.calls.at(-1), 'focus');
    f.controller.pageHide();
});

test('Presenter partial calculation does not scrub existing codes; revocation does', async () => {
    const f = fixture();
    await f.ready();
    const second = {account: {...account, id: 'second'}, code: null, remainingMs: 0, copyDisabled: true, hidden: false};
    const before = f.clears.length;
    f.presenterOptions().publish(otp('001234', [second]));
    assert.equal(f.clears.length, before, 'an added null row is not a revocation of the first row');
    f.presenterOptions().publish(otp(null, [second]));
    assert.deepEqual(f.clears.at(-1), {codes: true});
    const revoked = f.clears.length;
    f.presenterOptions().publish(otp(null, [second]));
    assert.equal(f.clears.length, revoked, 'already empty rows do not need repeated DOM scrubs');
    f.presenterOptions().publish(otp());
    f.presenterOptions().publish(emptyOtp());
    assert.deepEqual(f.clears.at(-1), {codes: true});
    f.controller.pageHide();
});

test('Message lookup rejects prototype keys and unknown exception objects', () => {
    for (const code of ['__proto__', 'constructor', 'toString', 'PRIVATE', undefined, null, {}]) {
        assert.equal(safeCreateErrorCode(code), 'create-failed');
        assert.equal(typeof createErrorMessage(code), 'string');
        assert.equal(typeof messageFor(code), 'string');
        assert.doesNotMatch(createErrorMessage(code), /PRIVATE/);
        assert.doesNotMatch(messageFor(code), /PRIVATE/);
    }
    assert.equal(safeCreateErrorCode('create-invalid-secret'), 'create-invalid-secret');
});

test('Synchronous DOM erasure is restricted to the app and dialog portal', () => {
    function root(id) {
        const selectors = {
            'input[data-otp-secret]': [{value: 'SYNTHETIC-SECRET'}],
            '.passwords-otp-ap3__code': [{textContent: '001234', disabled: false}],
            '.passwords-otp-ap3__copy': [{disabled: false}],
            '.passwords-otp-ap3__progress': [{value: 29}],
            '[data-otp-protected]': [{hidden: false}],
        };
        return {id, hidden: false, selectors, querySelectorAll: selector => selectors[selector]};
    }
    const app = root('passwords-otp-app'), dialog = root('passwords-otp-dialog-host'), unrelated = root('other-app');
    const doc = {getElementById: id => [app, dialog, unrelated].find(item => item.id === id)};
    clearSensitiveDom(doc, {inputs: true, codes: true, lock: true});
    for (const current of [app, dialog]) {
        assert.equal(current.selectors['input[data-otp-secret]'][0].value, '');
        assert.equal(current.selectors['.passwords-otp-ap3__code'][0].textContent, '—');
        assert.equal(current.selectors['.passwords-otp-ap3__code'][0].disabled, true);
        assert.equal(current.selectors['.passwords-otp-ap3__copy'][0].disabled, true);
        assert.equal(current.selectors['.passwords-otp-ap3__progress'][0].value, 0);
        assert.equal(current.selectors['[data-otp-protected]'][0].hidden, true);
    }
    assert.equal(app.hidden, false, 'the reload/status surface must remain usable');
    assert.equal(dialog.hidden, true);
    assert.equal(unrelated.selectors['input[data-otp-secret]'][0].value, 'SYNTHETIC-SECRET');
    assert.equal(unrelated.selectors['.passwords-otp-ap3__code'][0].textContent, '001234');
    assert.equal(unrelated.selectors['.passwords-otp-ap3__code'][0].disabled, false);
    assert.doesNotThrow(() => clearSensitiveDom({getElementById: () => null}, {inputs: true, codes: true, lock: true}));
});

test('Idle expiry blocks a late copy and clears the UI before upstream close finishes', async () => {
    let now = 1000;
    const close = deferred();
    const f = fixture({initialFields: {idlePolicy: {lifetimeMs: 300000, requestsOnly: false}},
        now: () => now, close: () => close.promise});
    await f.ready();
    now += 299999;
    assert.equal(await f.presenterOptions().verifySession(), true);
    f.controller.focusChanged();
    now++;
    f.controller.copy('synthetic');
    assert.equal(f.state().status, german('inactive'));
    assert.deepEqual(f.state().otp, emptyOtp());
    assert.deepEqual(f.clears.at(-1), {inputs: true, codes: true, lock: true});
    assert.equal(f.count('close'), 1);
    assert.equal(f.calls.some(call => Array.isArray(call) && call[0] === 'copy'), false);
    f.controller.activity();
    assert.equal(await f.presenterOptions().verifySession(), false);
    close.resolve();
});

test('Only the configured activity extends the idle deadline', async () => {
    for (const requestsOnly of [false, true]) {
        let now = 1000;
        const f = fixture({initialFields: {idlePolicy: {lifetimeMs: 300000, requestsOnly}}, now: () => now});
        await f.ready();
        now += 290000;
        f.controller.activity();
        if (requestsOnly) await f.controller.openCreate();
        now += 290000;
        f.controller.focusChanged();
        assert.equal(f.state().mode, 'ready');
        now += 10000;
        f.controller.focusChanged();
        assert.equal(f.state().status, german('inactive'));
        assert.equal(f.count('close'), 1);
    }
    let now = 1000;
    const f = fixture({initialFields: {idlePolicy: {lifetimeMs: 300000, requestsOnly: true}}, now: () => now});
    await f.ready();
    now += 299999;
    f.controller.activity();
    now++;
    f.controller.focusChanged();
    assert.equal(f.state().status, german('inactive'), 'input alone never extends request-only mode');
});

test('Idle lock while saving preserves the uncertain-write warning and rejects a late success', async () => {
    let now = 1000;
    const gate = deferred();
    const f = fixture({initialFields: {idlePolicy: {lifetimeMs: 300000, requestsOnly: false}},
        now: () => now, create: () => gate.promise});
    await f.ready();
    await f.controller.openCreate();
    const save = f.controller.create(values());
    now += 300000;
    f.controller.visibilityChanged();
    gate.resolve({snapshot: snapshot(), id: 'new'});
    await save;
    assert.equal(f.state().status, german('inactive-create'));
    assert.equal(f.state().createOpen, false);
    assert.equal(f.count('close'), 1);
});
