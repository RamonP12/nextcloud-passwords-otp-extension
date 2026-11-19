import {otpListNotice} from '../ap2/view.mjs';
import {searchOtpAccounts} from '../ap2/parser.mjs';
import {timeSlot} from './totp.mjs';

/** Copy only the already validated public metadata, never a seed, key or client. */
function publicAccount(account) {
    const {id, title, username, issuer, accountName, type, algorithm, digits, period} = account;
    return Object.freeze({id, title, username, issuer, accountName, type, algorithm, digits, period});
}

/**
 * Framework-independent TOTP presentation and clipboard policy.
 *
 * Keep this instance and its OtpVaultSession OUTSIDE Vue's deep reactivity: both
 * own private fields. `publish` receives detached, immutable display snapshots;
 * it must replace the current view, never persist or log it. Only the ephemeral
 * displayed code is published, never OTP seeds, CryptoKeys or upstream tokens.
 *
 * Clearing publishes synchronously. A UI adapter must also clear sensitive DOM
 * synchronously on pagehide/lock, because a framework may defer DOM updates.
 * Clipboard writes deliberately happen synchronously in copy(), before awaiting
 * anything, so the browser's trusted user activation is preserved.
 */
export class TotpPresenter {
    #session = null;
    #snapshot = {state: 'locked'};
    #rows = new Map();
    #codes = new Map();
    #epoch = 0;
    #refreshId = 0;
    #interval = null;
    #disposed = false;
    #checkedWindow = null;
    #checkedAt = -Infinity;
    #guardPending = false;
    #guardGeneration = 0;

    constructor({now = () => Date.now(),
        isHidden = () => globalThis.document?.hidden === true,
        writeClipboard = text => globalThis.navigator?.clipboard?.writeText(text),
        fatal = () => {}, verifySession = async () => false, notify = () => {},
        publish = () => {}} = {}) {
        this.now = now;
        this.isHidden = isHidden;
        this.writeClipboard = writeClipboard;
        this.fatal = fatal;
        this.verifySession = verifySession;
        this.notify = notify;
        this.publish = publish;
    }

    setSession(session) {
        if (this.#disposed || this.#session === session) return;
        this.#reset();
        this.#session = session;
        this.#publish();
    }

    render(snapshot, query = '') {
        if (this.#disposed) return;
        this.#reset();
        const ready = snapshot?.state === 'ready';
        const accounts = ready ? (snapshot.otpAccounts || []).filter(account => account.type === 'totp')
            .map(publicAccount) : [];
        this.#snapshot = {state: snapshot?.state || 'locked', otpAccounts: accounts,
            invalidOtpCount: ready ? snapshot.invalidOtpCount || 0 : 0,
            unsupportedOtpCount: ready ? snapshot.unsupportedOtpCount || 0 : 0};
        // Materialize every authorized row, including after CREATE with active
        // search. Filtering changes visibility, never the cache or guard epoch.
        for (const account of accounts) {
            this.#rows.set(account.id, {account, code: null, remainingMs: 0,
                copyDisabled: true, hidden: false});
        }
        if (ready) this.#filter(query);
        this.#publish();
        if (ready && this.#session?.state === 'ready' && !this.#session.disposed) {
            this.#interval = setInterval(() => { void this.refresh(); }, 1000);
            this.#interval?.unref?.();
            void this.refresh();
        }
    }

    /** Search must not reset a verified code, restart the clock or reauthorize. */
    filter(query = '') {
        if (this.#disposed || this.#snapshot.state !== 'ready') return;
        this.#filter(query);
        this.#publish();
    }

    #filter(query) {
        const matches = new Set(searchOtpAccounts(this.#snapshot.otpAccounts, query).map(account => account.id));
        for (const [id, row] of this.#rows) row.hidden = !matches.has(id);
    }

    #publish() {
        const rows = Array.from(this.#rows.values(), row => Object.freeze({...row}));
        this.publish(Object.freeze({state: this.#snapshot.state,
            rows: Object.freeze(rows),
            notice: otpListNotice(this.#snapshot, rows.filter(row => !row.hidden).length)}));
    }

    #stopClock() {
        if (this.#interval !== null) { clearInterval(this.#interval); this.#interval = null; }
    }

    #reset() {
        this.#stopClock();
        this.#epoch++;
        this.#guardGeneration++;
        this.#refreshId++;
        this.#checkedWindow = null;
        this.#checkedAt = -Infinity;
        this.#codes.clear();
        this.#rows.clear();
        this.#snapshot = {state: 'locked'};
        // A verification already in flight remains single-flight. Its stale
        // completion will request verification of the new epoch, if still ready.
    }

    #hideCodes() {
        this.#refreshId++;
        this.#codes.clear();
        for (const row of this.#rows.values()) {
            row.code = null;
            row.remainingMs = 0;
            row.copyDisabled = true;
        }
        this.#publish();
    }

    #fail(message) {
        this.#reset();
        // Internal revocation is complete before any external callback. Even a
        // failing session cleanup must not prevent publication of the empty view.
        try { this.#session?.dispose?.(); }
        finally {
            try { this.#publish(); }
            finally { this.fatal(message); }
        }
    }

    visibilityChanged() {
        if (this.#disposed) return;
        if (this.isHidden()) {
            this.#checkedWindow = null;
            this.#checkedAt = -Infinity;
            this.#guardGeneration++;
            this.#hideCodes();
        } else void this.refresh();
    }

    focusChanged() {
        if (this.#disposed) return;
        this.#checkedWindow = null;
        this.#checkedAt = -Infinity;
        this.#guardGeneration++;
        this.#hideCodes();
        void this.refresh();
    }

    async refresh() {
        if (this.#disposed) return;
        if (this.#snapshot.state !== 'ready' || this.#session?.disposed || this.#session?.state !== 'ready') {
            this.#reset();
            this.#publish();
            return;
        }
        if (this.isHidden()) { this.#hideCodes(); return; }
        let requestedAt, windowId, newPeriodSlot = false;
        try {
            requestedAt = this.now();
            windowId = timeSlot(requestedAt, 30).counter;
            for (const [id, row] of this.#rows) {
                const period = row.account.period;
                const slot = timeSlot(requestedAt, period), previous = this.#codes.get(id);
                if ((!previous || previous.counter !== slot.counter)
                        && this.#checkedAt < slot.counter * period * 1000) {
                    newPeriodSlot = true;
                    break;
                }
            }
        } catch (_) { this.#fail('Die Systemzeit ist für OTP ungültig.'); return; }

        if (this.#checkedWindow !== windowId || newPeriodSlot || requestedAt < this.#checkedAt) {
            this.#hideCodes();
            if (this.#guardPending) return;
            this.#guardPending = true;
            const guardEpoch = this.#epoch, guardGeneration = this.#guardGeneration;
            let permitted = false;
            try { permitted = (await this.verifySession()) === true; } catch (_) { /* fail closed */ }
            this.#guardPending = false;
            if (this.#disposed || this.#session?.disposed) return;
            if (guardEpoch !== this.#epoch || guardGeneration !== this.#guardGeneration) {
                if (this.#snapshot.state === 'ready') void this.refresh();
                return;
            }
            if (!permitted) { this.#fail('Nextcloud-Sitzung nicht mehr gültig. Bitte erneut anmelden.'); return; }
            // Certify the START of the request, never a later slot reached while
            // awaiting HTTP. A boundary crossing therefore needs another guard.
            this.#checkedWindow = windowId;
            this.#checkedAt = requestedAt;
            void this.refresh();
            return;
        }
        if (this.#guardPending) return;

        const epoch = this.#epoch, refreshId = ++this.#refreshId;
        for (const [id, row] of this.#rows) {
            if (this.#disposed || epoch !== this.#epoch || refreshId !== this.#refreshId) return;
            try {
                const period = row.account.period;
                const now = this.now(), slot = timeSlot(now, period);
                if (timeSlot(now, 30).counter !== this.#checkedWindow || now < this.#checkedAt
                        || this.#checkedAt < slot.counter * period * 1000) {
                    this.#hideCodes(); void this.refresh(); return;
                }
                let current = this.#codes.get(id);
                if (!current || current.counter !== slot.counter) {
                    row.code = null;
                    row.remainingMs = 0;
                    row.copyDisabled = true;
                    this.#codes.delete(id);
                    this.#publish();
                    const candidate = await this.#session.totpFor(id, now);
                    if (this.#disposed || this.isHidden() || epoch !== this.#epoch || refreshId !== this.#refreshId
                            || this.#session?.state !== 'ready' || this.#session.disposed) return;
                    // A result must belong to the requested slot. A malformed or
                    // permanently stale result is an error, not an infinite retry.
                    if (!candidate || candidate.counter !== slot.counter
                            || typeof candidate.code !== 'string' || !/^[0-9]{6,9}$/.test(candidate.code)
                            || candidate.code.length !== row.account.digits) throw new Error('invalid-code');
                    const afterNow = this.now(), after = timeSlot(afterNow, period);
                    if (after.counter !== candidate.counter || timeSlot(afterNow, 30).counter !== this.#checkedWindow
                            || afterNow < this.#checkedAt) { this.#hideCodes(); void this.refresh(); return; }
                    // Retain only the values actually needed by the copy policy.
                    current = {code: candidate.code, counter: candidate.counter};
                    this.#codes.set(id, current);
                }
                const afterNow = this.now(), after = timeSlot(afterNow, period);
                if (after.counter !== current.counter || timeSlot(afterNow, 30).counter !== this.#checkedWindow
                        || afterNow < this.#checkedAt) {
                    this.#hideCodes(); void this.refresh(); return;
                }
                row.code = current.code;
                row.remainingMs = after.remainingMs;
                row.copyDisabled = after.remainingMs < 2500;
                this.#publish();
            } catch (_) {
                // A rejected signing operation from an obsolete render/focus
                // generation must not lock a newly authorized view.
                if (this.#disposed || epoch !== this.#epoch || refreshId !== this.#refreshId) return;
                this.#fail('Die lokale OTP-Berechnung ist fehlgeschlagen. Tresor erneut entsperren.');
                return;
            }
        }
    }

    copy(id) {
        if (this.#disposed || this.isHidden() || this.#guardPending || this.#snapshot.state !== 'ready'
                || this.#session?.state !== 'ready' || this.#session.disposed) return;
        const cached = this.#codes.get(id), row = this.#rows.get(id);
        if (!cached || !row || row.hidden) return;
        let slot, currentWindow, now;
        try {
            now = this.now();
            slot = timeSlot(now, row.account.period);
            currentWindow = timeSlot(now, 30).counter;
        } catch (_) { this.#fail('Die Systemzeit ist für OTP ungültig.'); return; }
        if (currentWindow !== this.#checkedWindow || now < this.#checkedAt
                || this.#checkedAt < slot.counter * row.account.period * 1000
                || slot.counter !== cached.counter || slot.remainingMs < 2500) {
            this.#hideCodes();
            this.notify('Der Code wird geprüft. Neuen Code verwenden.');
            void this.refresh();
            return;
        }
        const epoch = this.#epoch, generation = this.#guardGeneration;
        const current = () => !this.#disposed && epoch === this.#epoch && generation === this.#guardGeneration;
        try {
            const pending = this.writeClipboard(cached.code);
            if (!pending || typeof pending.then !== 'function') throw new Error('clipboard-unavailable');
            void Promise.resolve(pending).then(() => {
                if (current() && this.#session?.state === 'ready') this.notify('OTP-Code kopiert.');
            }).catch(() => {
                if (current()) this.notify('Kopieren nicht möglich. Browser-Zwischenablage prüfen.');
            });
        } catch (_) { this.notify('Kopieren nicht möglich. Browser-Zwischenablage prüfen.'); }
    }

    dispose() {
        if (this.#disposed) return;
        this.#reset();
        this.#disposed = true;
        this.#session = null;
        this.#publish();
    }
}
