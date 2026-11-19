import test from 'node:test';
import assert from 'node:assert/strict';
import {TotpPresenter} from '../../src/ap3/ui.mjs';
import {timeSlot} from '../../src/ap3/totp.mjs';
import {deferred, settle} from './helpers.mjs';

const account = (id = 'one', title = 'one', options = {}) =>
    ({id, title, type: 'totp', algorithm: 'sha1', digits: 6, period: 30, ...options});
const ready = (accounts, options = {}) => ({state: 'ready', otpCount: accounts.length,
    invalidOtpCount: 0, unsupportedOtpCount: 0, otpAccounts: accounts, ...options});

function setup({period = 30, now = 1000, verify = async () => true, calculate,
    writeClipboard = () => Promise.resolve(), accounts} = {}) {
    let clock = now, hidden = false, checks = 0, calculations = 0, copies = 0, fatals = 0;
    let view = {state: 'locked', rows: [], notice: ''};
    const notifications = [];
    const session = {state: 'ready', disposed: false,
        dispose() { this.state = 'locked'; this.disposed = true; },
        async totpFor(id, time) {
            calculations++;
            return calculate ? calculate(id, time) : {code: '123456', ...timeSlot(time, period)};
        }};
    const p = new TotpPresenter({now: () => clock, isHidden: () => hidden,
        verifySession: async () => { checks++; return verify(); },
        writeClipboard: value => { copies++; return writeClipboard(value); },
        fatal: () => fatals++, notify: message => notifications.push(message),
        publish: next => { view = next; }});
    const snapshot = ready(accounts || [account('one', 'one', {period})]);
    p.setSession(session);
    p.render(snapshot);
    return {p, session, snapshot, notifications,
        setClock: value => { clock = value; }, setHidden: value => { hidden = value; },
        checks: () => checks, calculations: () => calculations, copies: () => copies,
        fatals: () => fatals, view: () => view,
        code: () => view.rows[0]?.code ?? null,
        copyDisabled: () => view.rows[0]?.copyDisabled ?? true};
}

test('Normal guard is once per slot; countdown is local; clipboard is synchronous', async t => {
    let copied;
    const f = setup({writeClipboard: value => { copied = value; return Promise.resolve(); }});
    t.after(() => f.p.dispose());
    await settle();
    assert.equal(f.checks(), 1);
    assert.equal(f.code(), '123456');
    assert.equal(f.view().rows[0].remainingMs, 29000);
    f.setClock(2000);
    await f.p.refresh();
    assert.equal(f.checks(), 1);
    assert.equal(f.view().rows[0].remainingMs, 28000);
    f.p.copy('one');
    assert.equal(f.copies(), 1);
    assert.equal(copied, '123456', 'clipboard invocation must precede the next microtask');
    f.setClock(30000);
    await f.p.refresh();
    await settle();
    assert.equal(f.checks(), 2);
    assert.equal(f.calculations(), 2);
});

test('Missing verification defaults to fail closed and publishes no metadata', async () => {
    let disposed = 0, view;
    const session = {state: 'ready', dispose() { disposed++; this.state = 'locked'; }};
    const p = new TotpPresenter({publish: next => { view = next; }});
    p.setSession(session);
    p.render(ready([]));
    await settle();
    assert.equal(disposed, 1);
    assert.deepEqual(view, {state: 'locked', rows: [], notice: ''});
    p.dispose();
});

test('Delayed successful response from previous slot cannot authorize the new slot', async t => {
    const first = deferred(), second = deferred();
    let count = 0;
    const f = setup({now: 29999, verify: () => ++count === 1 ? first.promise : second.promise});
    t.after(() => f.p.dispose());
    f.setClock(30001);
    first.resolve(true);
    await settle();
    assert.equal(f.checks(), 2);
    assert.equal(f.calculations(), 0);
    assert.equal(f.code(), null);
    second.resolve(false);
    await settle();
    assert.equal(f.session.disposed, true);
    assert.equal(f.calculations(), 0);
    assert.equal(f.view().rows.length, 0);
});

test('Focus generation rejects a stale response and checks again', async t => {
    const first = deferred(), second = deferred();
    let count = 0;
    const f = setup({verify: () => ++count === 1 ? first.promise : second.promise});
    t.after(() => f.p.dispose());
    f.p.focusChanged();
    first.resolve(true);
    await settle();
    assert.equal(f.checks(), 2);
    assert.equal(f.calculations(), 0);
    second.resolve(false);
    await settle();
    assert.equal(f.session.disposed, true);
});

test('45-second account checks at the 30-second and its own boundary', async t => {
    const f = setup({period: 45, now: 29000});
    t.after(() => f.p.dispose());
    await settle();
    f.setClock(30000);
    await f.p.refresh();
    await settle();
    assert.equal(f.checks(), 2);
    f.setClock(45000);
    await f.p.refresh();
    await settle();
    assert.equal(f.checks(), 3);
});

test('Timer-throttled clipboard cannot cross a 30-second auth boundary', async t => {
    const check = deferred();
    let calls = 0;
    const f = setup({period: 60, now: 29000, verify: () => ++calls === 1 ? true : check.promise});
    t.after(() => f.p.dispose());
    await settle();
    assert.equal(f.code(), '123456');
    f.setClock(31000);
    f.p.copy('one');
    assert.equal(f.copies(), 0);
    assert.equal(f.code(), null);
    check.resolve(false);
    await settle();
    assert.equal(f.session.disposed, true);
});

test('Copy permits exactly 2500 ms validity and rejects anything below', async t => {
    const f = setup();
    t.after(() => f.p.dispose());
    await settle();
    f.setClock(27500);
    await f.p.refresh();
    assert.equal(f.copyDisabled(), false);
    f.p.copy('one');
    assert.equal(f.copies(), 1);
    f.setClock(27501);
    f.p.copy('one');
    assert.equal(f.copies(), 1);
    await settle();
    assert.equal(f.copyDisabled(), true);
    f.setClock(30000);
    f.p.copy('one');
    assert.equal(f.copies(), 1);
});

test('HMAC finishing in a later 30-second window requires new proof for a 60s account', async t => {
    const sign = deferred(), check = deferred();
    let checks = 0;
    const f = setup({period: 60, now: 29999, verify: () => ++checks === 1 ? true : check.promise,
        calculate: () => sign.promise});
    t.after(() => f.p.dispose());
    await settle();
    assert.equal(f.calculations(), 1);
    f.setClock(30001);
    sign.resolve({code: '123456', ...timeSlot(29999, 60)});
    await settle();
    assert.equal(f.checks(), 2);
    assert.equal(f.code(), null);
    check.resolve(false);
    await settle();
    assert.equal(f.session.disposed, true);
});

test('Session disposal during signing never publishes a late code', async t => {
    const sign = deferred();
    const f = setup({calculate: () => sign.promise});
    t.after(() => f.p.dispose());
    await settle();
    f.session.dispose();
    sign.resolve({code: '123456', ...timeSlot(1000, 30)});
    await settle();
    assert.equal(f.code(), null);
    f.p.copy('one');
    assert.equal(f.copies(), 0);
    await f.p.refresh();
    assert.deepEqual(f.view(), {state: 'locked', rows: [], notice: ''});
});

test('Rerender during verification rejects stale result and resumes without waiting for timer', async t => {
    const check = deferred();
    let n = 0;
    const f = setup({verify: () => ++n === 1 ? check.promise : false});
    t.after(() => f.p.dispose());
    f.p.render(f.snapshot, 'one');
    assert.equal(f.checks(), 1, 'verification remains single-flight');
    check.resolve(true);
    await settle();
    assert.equal(f.checks(), 2);
    assert.equal(f.calculations(), 0);
    assert.equal(f.session.disposed, true);
});

test('Hidden tab clears codes synchronously; return needs a fresh guard', async t => {
    const f = setup();
    t.after(() => f.p.dispose());
    await settle();
    f.setHidden(true);
    f.p.visibilityChanged();
    assert.equal(f.code(), null);
    assert.equal(f.copyDisabled(), true);
    assert.equal(f.view().rows[0].remainingMs, 0);
    f.p.copy('one');
    assert.equal(f.copies(), 0);
    f.setHidden(false);
    f.p.visibilityChanged();
    await settle();
    assert.equal(f.checks(), 2);
});

test('Hide and return during verification rejects the old generation', async t => {
    const first = deferred(), second = deferred();
    let n = 0;
    const f = setup({verify: () => ++n === 1 ? first.promise : second.promise});
    t.after(() => f.p.dispose());
    f.setHidden(true);
    f.p.visibilityChanged();
    f.setHidden(false);
    f.p.visibilityChanged();
    first.resolve(true);
    await settle();
    assert.equal(f.checks(), 2);
    assert.equal(f.calculations(), 0);
    second.resolve(true);
    await settle();
    assert.equal(f.code(), '123456');
});

test('Backward time jump inside one slot is revalidated', async t => {
    const f = setup({now: 10000});
    t.after(() => f.p.dispose());
    await settle();
    f.setClock(9000);
    await f.p.refresh();
    await settle();
    assert.equal(f.checks(), 2);
});

test('Clipboard cannot bypass a backward time jump', async t => {
    const check = deferred();
    let n = 0;
    const f = setup({now: 10000, verify: () => ++n === 1 ? true : check.promise});
    t.after(() => f.p.dispose());
    await settle();
    f.setClock(9000);
    f.p.copy('one');
    assert.equal(f.copies(), 0);
    assert.equal(f.code(), null);
    check.resolve(false);
    await settle();
});

test('Invalid clock stops, clears metadata and disposes the session', async t => {
    const f = setup();
    t.after(() => f.p.dispose());
    await settle();
    f.setClock(NaN);
    await f.p.refresh();
    assert.equal(f.session.disposed, true);
    assert.deepEqual(f.view(), {state: 'locked', rows: [], notice: ''});
});

test('Session failure at next slot never issues a successor code', async t => {
    let allow = true;
    const f = setup({verify: async () => allow});
    t.after(() => f.p.dispose());
    await settle();
    allow = false;
    f.setClock(30000);
    await f.p.refresh();
    await settle();
    assert.equal(f.calculations(), 1);
    assert.equal(f.session.disposed, true);
    assert.equal(f.fatals(), 1);
});

test('Rejected verification fails closed', async t => {
    const f = setup({verify: async () => { throw new Error('synthetic transport failure'); }});
    t.after(() => f.p.dispose());
    await settle();
    assert.equal(f.session.disposed, true);
    assert.equal(f.calculations(), 0);
    assert.equal(f.fatals(), 1);
});

test('Malformed code never reaches presentation or clipboard', async t => {
    const f = setup({calculate: async () => ({code: '<script>PRIVATE</script>', ...timeSlot(1000, 30)})});
    t.after(() => f.p.dispose());
    await settle();
    assert.equal(f.session.disposed, true);
    assert.doesNotMatch(JSON.stringify(f.view()), /PRIVATE/);
    f.p.copy('one');
    assert.equal(f.copies(), 0);
});

test('Configured digit length is enforced without numeric conversion', async t => {
    let copied;
    const f = setup({calculate: async () => ({code: '001234', ...timeSlot(1000, 30)}),
        writeClipboard: value => { copied = value; return Promise.resolve(); }});
    t.after(() => f.p.dispose());
    await settle();
    f.p.copy('one');
    assert.equal(f.code(), '001234');
    assert.equal(copied, '001234');
    const bad = setup({calculate: async () => ({code: '1234567', ...timeSlot(1000, 30)})});
    t.after(() => bad.p.dispose());
    await settle();
    assert.equal(bad.session.disposed, true);
    assert.equal(bad.code(), null);
});

test('Search retains verified codes without resigning, reauthorization or timer reset', async t => {
    const f = setup();
    t.after(() => f.p.dispose());
    await settle();
    const oldCode = f.code(), checks = f.checks(), calculations = f.calculations();
    f.p.filter('not-present');
    assert.equal(f.view().rows.length, 1);
    assert.equal(f.view().rows[0].hidden, true);
    assert.equal(f.code(), oldCode);
    assert.equal(f.copyDisabled(), false);
    f.p.copy('one');
    assert.equal(f.copies(), 0, 'a filtered-out row must never be copied');
    f.p.filter('one');
    assert.equal(f.view().rows[0].hidden, false);
    assert.equal(f.code(), oldCode);
    assert.equal(f.checks(), checks);
    assert.equal(f.calculations(), calculations);
});

test('After CREATE with active search, all rows survive and clearing search restores accounts', async t => {
    const calls = [];
    const f = setup({accounts: [account('git', 'GitHub'), account('bank', 'Bank')],
        calculate: async (id, now) => { calls.push(id); return {code: '654321', ...timeSlot(now, 30)}; }});
    t.after(() => f.p.dispose());
    f.p.filter('git');
    await settle();
    assert.equal(f.view().rows.length, 2);
    assert.deepEqual(f.view().rows.map(row => row.hidden), [false, true]);
    f.p.render(ready([...f.snapshot.otpAccounts, account('new', 'New account')]), 'git');
    await settle();
    assert.equal(f.view().rows.length, 3);
    assert.deepEqual(f.view().rows.map(row => row.hidden), [false, true, true]);
    f.p.filter('');
    assert.equal(f.view().rows.filter(row => !row.hidden).length, 3);
    assert.deepEqual(f.view().rows.map(row => row.account.title), ['GitHub', 'Bank', 'New account']);
    assert.ok(calls.includes('bank'));
});

test('Failed session cleanup still revokes internal clipboard state', async t => {
    const f = setup();
    t.after(() => f.p.dispose());
    await settle();
    f.session.dispose = () => { f.session.disposed = true; throw new Error('synthetic cleanup failure'); };
    f.setClock(NaN);
    await assert.rejects(f.p.refresh(), /synthetic cleanup failure/);
    assert.deepEqual(f.view(), {state: 'locked', rows: [], notice: ''});
    f.p.copy('one');
    assert.equal(f.copies(), 0);
    assert.equal(f.fatals(), 1);
});

test('Public rows are detached, immutable and contain only selected metadata', async t => {
    const input = account('one', 'Safe title', {secret: 'PRIVATE-SEED', key: {private: true},
        token: 'PRIVATE-TOKEN', password: 'PRIVATE-PASSWORD'});
    const f = setup({accounts: [input]});
    t.after(() => f.p.dispose());
    await settle();
    const state = f.view();
    assert.doesNotMatch(JSON.stringify(state), /PRIVATE|"secret"|"key"|"token"|"password"/);
    assert.equal(Object.isFrozen(state), true);
    assert.equal(Object.isFrozen(state.rows), true);
    assert.equal(Object.isFrozen(state.rows[0]), true);
    assert.equal(Object.isFrozen(state.rows[0].account), true);
    input.title = 'Mutated outside';
    assert.equal(state.rows[0].account.title, 'Safe title');
    assert.throws(() => { state.rows[0].code = '999999'; }, TypeError);
});

test('Dispose publishes an empty view synchronously and rejects late successful guards', async () => {
    const check = deferred();
    const f = setup({verify: () => check.promise});
    f.p.dispose();
    assert.deepEqual(f.view(), {state: 'locked', rows: [], notice: ''});
    check.resolve(true);
    await settle();
    assert.equal(f.calculations(), 0);
    f.p.render(f.snapshot);
    f.p.filter('');
    f.p.focusChanged();
    f.p.visibilityChanged();
    await f.p.refresh();
    f.p.copy('one');
    assert.equal(f.copies(), 0);
    assert.deepEqual(f.view(), {state: 'locked', rows: [], notice: ''});
});

test('Dispose during HMAC completion cannot resurrect codes', async () => {
    const sign = deferred();
    const f = setup({calculate: () => sign.promise});
    await settle();
    f.p.dispose();
    assert.equal(f.view().rows.length, 0);
    sign.resolve({code: '123456', ...timeSlot(1000, 30)});
    await settle();
    assert.equal(f.view().rows.length, 0);
    f.p.copy('one');
    assert.equal(f.copies(), 0);
});

test('A rejected obsolete signing operation does not lock the new render', async t => {
    const sign = deferred();
    let n = 0;
    const f = setup({calculate: async (id, now) => ++n === 1 ? sign.promise : {code: '654321', ...timeSlot(now, 30)}});
    t.after(() => f.p.dispose());
    await settle();
    f.p.render(f.snapshot);
    await settle();
    assert.equal(f.code(), '654321');
    sign.reject(new Error('obsolete signing operation'));
    await settle();
    assert.equal(f.code(), '654321');
    assert.equal(f.session.disposed, false);
    assert.equal(f.fatals(), 0);
});

test('Clipboard rejection reports failure, never a false success', async t => {
    const f = setup({writeClipboard: async () => { throw new Error('denied'); }});
    t.after(() => f.p.dispose());
    await settle();
    f.p.copy('one');
    await settle();
    assert.equal(f.notifications.length, 1);
    assert.match(f.notifications[0], /Kopieren nicht möglich/);
    assert.doesNotMatch(f.notifications[0], /OTP-Code kopiert/);
});

test('Unavailable clipboard reports failure', async t => {
    const f = setup({writeClipboard: () => undefined});
    t.after(() => f.p.dispose());
    await settle();
    f.p.copy('one');
    assert.match(f.notifications[0], /Kopieren nicht möglich/);
});

test('Delayed clipboard feedback is ignored after hide or disposal', async t => {
    const copy = deferred();
    const f = setup({writeClipboard: () => copy.promise});
    t.after(() => f.p.dispose());
    await settle();
    f.p.copy('one');
    f.setHidden(true);
    f.p.visibilityChanged();
    copy.resolve();
    await settle();
    assert.deepEqual(f.notifications, []);
    const secondCopy = deferred();
    const second = setup({writeClipboard: () => secondCopy.promise});
    await settle();
    second.p.copy('one');
    second.p.dispose();
    secondCopy.reject(new Error('late denial'));
    await settle();
    assert.deepEqual(second.notifications, []);
});

test('Replacing the session clears the former codes and rejects its pending signing operation', async t => {
    const sign = deferred();
    const f = setup({calculate: () => sign.promise});
    t.after(() => f.p.dispose());
    await settle();
    const replacement = {state: 'ready', disposed: false,
        async totpFor(id, now) { return {code: '654321', ...timeSlot(now, 30)}; }};
    f.p.setSession(replacement);
    assert.deepEqual(f.view(), {state: 'locked', rows: [], notice: ''});
    f.p.render(f.snapshot);
    await settle();
    assert.equal(f.code(), '654321');
    sign.resolve({code: '123456', ...timeSlot(1000, 30)});
    await settle();
    assert.equal(f.code(), '654321');
});

test('Not-ready snapshots publish neither accounts nor counts from prior ready snapshots', async t => {
    const f = setup();
    t.after(() => f.p.dispose());
    await settle();
    f.p.render({...f.snapshot, state: 'needs-auth'});
    assert.deepEqual(f.view(), {state: 'needs-auth', rows: [], notice: ''});
    f.p.copy('one');
    assert.equal(f.copies(), 0);
});

test('Empty and filtered views retain distinct explanatory notices', async t => {
    const f = setup();
    t.after(() => f.p.dispose());
    await settle();
    f.p.filter('absent');
    assert.match(f.view().notice, /entsprechen der Suche/);
    f.p.render(ready([], {invalidOtpCount: 1, unsupportedOtpCount: 2}));
    assert.match(f.view().notice, /Keine gültigen TOTP-Konten/);
    assert.match(f.view().notice, /1 OTP-Eintrag/);
    assert.match(f.view().notice, /2 OTP-Eintrag/);
});

test('Malformed signing responses fail once instead of retrying indefinitely', async t => {
    for (const candidate of [undefined, null, {}, {counter: '0', code: '123456'},
        {counter: 1, code: '123456'}, {counter: 0, code: 123456}]) {
        const f = setup({calculate: async () => candidate});
        t.after(() => f.p.dispose());
        await settle();
        assert.equal(f.calculations(), 1);
        assert.equal(f.session.disposed, true);
        assert.equal(f.fatals(), 1);
        assert.equal(f.code(), null);
    }
});

test('A boundary crossed while signing a later account clears every earlier code', async t => {
    const sign = deferred(), check = deferred();
    let checks = 0;
    const f = setup({now: 29999, accounts: [account('first'), account('second')],
        verify: () => ++checks === 1 ? true : check.promise,
        calculate: async (id, time) => id === 'first'
            ? {code: '111111', ...timeSlot(time, 30)} : sign.promise});
    t.after(() => f.p.dispose());
    await settle();
    assert.equal(f.view().rows[0].code, '111111');
    assert.equal(f.view().rows[1].code, null);
    f.setClock(30001);
    sign.resolve({code: '222222', ...timeSlot(29999, 30)});
    await settle();
    assert.equal(f.checks(), 2);
    assert.deepEqual(f.view().rows.map(row => row.code), [null, null]);
    f.p.copy('first');
    f.p.copy('second');
    assert.equal(f.copies(), 0);
    check.resolve(false);
    await settle();
    assert.equal(f.view().rows.length, 0);
});

test('Mixed account periods use one central guard at each necessary boundary', async t => {
    const accounts = [account('short', 'short', {period: 15}), account('long', 'long', {period: 60})];
    const f = setup({accounts, calculate: async (id, time) =>
        ({code: '123456', ...timeSlot(time, accounts.find(item => item.id === id).period)})});
    t.after(() => f.p.dispose());
    await settle();
    assert.equal(f.checks(), 1);
    f.setClock(15000);
    await f.p.refresh();
    await settle();
    assert.equal(f.checks(), 2, 'one shared guard for the short account boundary');
    f.setClock(30000);
    await f.p.refresh();
    await settle();
    assert.equal(f.checks(), 3, 'coincident account and 30-second boundaries share one guard');
});

test('Locked render synchronously clears an already displayed code before any microtask', async t => {
    const f = setup();
    t.after(() => f.p.dispose());
    await settle();
    assert.equal(f.code(), '123456');
    f.p.render({state: 'locked'});
    assert.deepEqual(f.view(), {state: 'locked', rows: [], notice: ''});
    f.p.copy('one');
    assert.equal(f.copies(), 0);
});
