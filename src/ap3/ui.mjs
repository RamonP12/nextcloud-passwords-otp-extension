import {renderOtpView, otpListNotice} from '../ap2/view.mjs';
import {searchOtpAccounts} from '../ap2/parser.mjs';
import {timeSlot} from './totp.mjs';
/** Desktop TOTP presentation. Clipboard calls remain within the trusted click. */
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
    constructor(nodes, doc, {now = () => Date.now(),
        writeClipboard = text => globalThis.navigator?.clipboard?.writeText(text),
        fatal = () => {}, verifySession = async () => false, notify = () => {}} = {}) {
        this.nodes = nodes; this.doc = doc; this.now = now; this.writeClipboard = writeClipboard;
        this.fatal = fatal; this.verifySession = verifySession; this.notify = notify;
    }
    setSession(session) { this.#session = session; }
    render(snapshot, query = '') {
        if (this.#disposed) return;
        this.#stopClock();
        this.#epoch++;
        this.#checkedWindow = null; this.#checkedAt = -Infinity;
        this.#guardGeneration++; this.#refreshId++;
        this.#rows.clear(); this.#codes.clear();
        this.#snapshot = snapshot;
        if (this.nodes.feedback) this.nodes.feedback.textContent = '';
        // Always materialize every authorized OTP row on each new snapshot
        // (notably after CREATE). Search must only toggle visibility; otherwise
        // clearing the query cannot restore rows omitted during this render.
        renderOtpView(snapshot, '', this.nodes, this.doc,
            {renderControls: (account, item, doc) => this.#createControls(account, item, doc)});
        if (snapshot?.state === 'ready') this.filter(query);
        if (snapshot?.state === 'ready' && this.#session?.state === 'ready') {
            this.#interval = setInterval(() => { void this.refresh(); }, 1000);
            this.#interval?.unref?.();
            void this.refresh();
        }
    }
    /** Search only hides existing rows. Never discard a signed, still valid
     * code or reset the auth/30s guard merely because the user typed.
     */
    filter(query = '') {
        if (this.#disposed || this.#snapshot?.state !== 'ready') return;
        const matches = new Set(searchOtpAccounts(this.#snapshot.otpAccounts, query).map(a => a.id));
        for (const [id, row] of this.#rows) row.item.hidden = !matches.has(id);
        this.nodes.empty.textContent = otpListNotice(this.#snapshot, matches.size);
    }
    #createControls(account, item, doc) {
        const controls = doc.createElement('div');
        controls.className = 'passwords-otp-ap3__controls';
        const code = doc.createElement('output');
        code.className = 'passwords-otp-ap3__code'; code.textContent = '\u2014';
        code.setAttribute('aria-label', 'Einmalcode');
        const countdown = doc.createElement('span');
        countdown.className = 'passwords-otp-ap3__countdown'; countdown.textContent = 'Wird berechnet \u2026';
        const progress = doc.createElement('progress');
        progress.className = 'passwords-otp-ap3__progress'; progress.max = account.period; progress.value = 0;
        progress.setAttribute('aria-label', 'Restg\u00fcltigkeit in Sekunden');
        const copy = doc.createElement('button');
        copy.type = 'button'; copy.className = 'passwords-otp-ap3__copy'; copy.textContent = 'Code kopieren'; copy.disabled = true;
        copy.addEventListener('click', () => this.copy(account.id));
        controls.append(code, countdown, progress, copy); item.append(controls);
        this.#rows.set(account.id, {item, code, countdown, progress, copy, period: account.period});
    }
    #stopClock() { if (this.#interval !== null) { clearInterval(this.#interval); this.#interval = null; } }
    #hideCodes() {
        this.#refreshId++;
        this.#codes.clear();
        for (const row of this.#rows.values()) {
            row.code.textContent = '\u2014'; row.countdown.textContent = ''; row.progress.value = 0; row.copy.disabled = true;
        }
    }
    #fail(message) {
        this.#hideCodes(); this.#stopClock(); this.#epoch++; this.#guardGeneration++;
        this.#snapshot = {state: 'locked'};
        this.#session?.dispose?.();
        this.fatal(message);
    }
    visibilityChanged() {
        if (this.#disposed) return;
        if (this.doc.hidden) {
            this.#checkedWindow = null; this.#checkedAt = -Infinity;
            this.#guardGeneration++; this.#hideCodes();
        } else void this.refresh();
    }
    focusChanged() {
        if (this.#disposed) return;
        this.#checkedWindow = null; this.#checkedAt = -Infinity;
        this.#guardGeneration++; this.#hideCodes(); void this.refresh();
    }
    async refresh() {
        if (this.#disposed || this.doc.hidden || this.#snapshot?.state !== 'ready'
                || this.#session?.disposed || this.#session?.state !== 'ready') { this.#hideCodes(); return; }
        const requestedAt = this.now();
        let windowId, newPeriodSlot = false;
        try {
            windowId = timeSlot(requestedAt, 30).counter;
            for (const [id, row] of this.#rows) {
                const slot = timeSlot(requestedAt, row.period), previous = this.#codes.get(id);
                if ((!previous || previous.counter !== slot.counter)
                        && this.#checkedAt < slot.counter * row.period * 1000) { newPeriodSlot = true; break; }
            }
        } catch (_) { this.#fail('Die Systemzeit ist f\u00fcr OTP ung\u00fcltig.'); return; }
        if (this.#checkedWindow !== windowId || newPeriodSlot || requestedAt < this.#checkedAt) {
            this.#hideCodes();
            if (this.#guardPending) return;
            this.#guardPending = true;
            const guardEpoch = this.#epoch, guardGeneration = this.#guardGeneration;
            let permitted = false;
            try { permitted = (await this.verifySession()) === true; } catch (_) { /* fail closed */ }
            this.#guardPending = false;
            if (this.#disposed || guardEpoch !== this.#epoch || this.#session?.disposed) return;
            if (guardGeneration !== this.#guardGeneration) { void this.refresh(); return; }
            if (!permitted) { this.#fail('Nextcloud-Sitzung nicht mehr g\u00fcltig. Bitte erneut anmelden.'); return; }
            // Bind the result to the START of the request. Never certify a later slot
            // merely because an old successful HTTP response arrived after its boundary.
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
                const now = this.now(), slot = timeSlot(now, row.period);
                // The loop or signing can itself cross the mandatory 30-second boundary.
                if (timeSlot(now, 30).counter !== this.#checkedWindow || now < this.#checkedAt
                        || this.#checkedAt < slot.counter * row.period * 1000) {
                    this.#hideCodes(); void this.refresh(); return;
                }
                let current = this.#codes.get(id);
                if (!current || current.counter !== slot.counter) {
                    row.code.textContent = '\u2014'; row.countdown.textContent = 'Wird aktualisiert \u2026';
                    row.copy.disabled = true; this.#codes.delete(id);
                    const candidate = await this.#session.totpFor(id, now);
                    if (this.#disposed || this.doc.hidden || epoch !== this.#epoch || refreshId !== this.#refreshId
                            || this.#session?.state !== 'ready' || this.#session.disposed) return;
                    const afterNow = this.now(), after = timeSlot(afterNow, row.period);
                    if (after.counter !== candidate.counter || timeSlot(afterNow, 30).counter !== this.#checkedWindow
                            || afterNow < this.#checkedAt) { this.#hideCodes(); void this.refresh(); return; }
                    if (typeof candidate.code !== 'string' || !/^[0-9]{6,9}$/.test(candidate.code)) throw new Error('invalid-code');
                    current = candidate; this.#codes.set(id, current);
                }
                const afterNow = this.now(), after = timeSlot(afterNow, row.period);
                if (after.counter !== current.counter || timeSlot(afterNow, 30).counter !== this.#checkedWindow) {
                    this.#hideCodes(); void this.refresh(); return;
                }
                row.code.textContent = current.code;
                row.countdown.textContent = 'Noch ' + Math.ceil(after.remainingMs / 1000) + ' s g\u00fcltig';
                row.progress.value = Math.min(row.period, after.remainingMs / 1000);
                row.copy.disabled = after.remainingMs < 2500;
            } catch (_) { this.#fail('Die lokale OTP-Berechnung ist fehlgeschlagen. Tresor erneut entsperren.'); return; }
        }
    }
    copy(id) {
        if (this.#disposed || this.doc.hidden || this.#guardPending || this.#snapshot?.state !== 'ready'
                || this.#session?.state !== 'ready' || this.#session.disposed) return;
        const cached = this.#codes.get(id), row = this.#rows.get(id);
        if (!cached || !row || row.item.hidden) return;
        let slot, currentWindow, now;
        try { now = this.now(); slot = timeSlot(now, row.period); currentWindow = timeSlot(now, 30).counter; }
        catch (_) { this.#fail('Die Systemzeit ist f\u00fcr OTP ung\u00fcltig.'); return; }
        if (currentWindow !== this.#checkedWindow || now < this.#checkedAt || this.#checkedAt < slot.counter * row.period * 1000
                || slot.counter !== cached.counter || slot.remainingMs < 2500) {
            this.#hideCodes(); this.notify('Der Code wird gepr\u00fcft. Neuen Code verwenden.'); void this.refresh(); return;
        }
        const epoch = this.#epoch;
        try {
            const pending = this.writeClipboard(cached.code);
            if (!pending || typeof pending.then !== 'function') throw new Error('clipboard-unavailable');
            void Promise.resolve(pending).then(() => {
                if (!this.#disposed && epoch === this.#epoch && this.#session?.state === 'ready') this.notify('OTP-Code kopiert.');
            }).catch(() => {
                if (!this.#disposed && epoch === this.#epoch) this.notify('Kopieren nicht m\u00f6glich. Browser-Zwischenablage pr\u00fcfen.');
            });
        } catch (_) { this.notify('Kopieren nicht m\u00f6glich. Browser-Zwischenablage pr\u00fcfen.'); }
    }
    dispose() {
        if (this.#disposed) return;
        this.render({state: 'locked'}, '');
        this.#disposed = true; this.#session = null; this.#snapshot = {state: 'locked'};
        this.#rows.clear(); this.#codes.clear(); this.#stopClock();
    }
}
