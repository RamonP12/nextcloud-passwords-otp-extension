import {OtpVaultSession, SessionFault} from '../ap1/session.mjs';
import {loadBootstrap} from '../ap1/bootstrap.mjs';
import {boundedRequest} from '../ap1/network.mjs';
import {makeSessionCheck} from '../ap9/session-check.mjs';
import {TotpPresenter} from '../ap3/ui.mjs';
import {createErrorMessage, messageFor, safeCreateErrorCode} from './messages.mjs';

/** Application lifecycle, independent of Vue. Only public display state leaves
 * this closure. Never put the session, client, keys or credential objects in a
 * reactive proxy/store: the domain classes use native private fields.
 */
export function createOtpController({config, pageUrl, doc, fetcher,
    createClient, sodiumReady, publish = () => {}, clear = () => {}, focus = () => {},
    createSession = client => new OtpVaultSession(client),
    createPresenter = options => new TotpPresenter(options),
    bootstrap = loadBootstrap, checkSession = makeSessionCheck} = {}) {
    let session = null, presenter = null, started = false, ended = false, pageHidden = false;
    const bootstrapAbort = new AbortController();
    let state = {mode: 'loading', status: 'Sitzung wird geprüft …', statusType: 'info',
        snapshot: null, otp: {state: 'locked', rows: [], notice: ''}, query: '', feedback: '',
        canReload: false, unlockBusy: false, unlockError: '', createOpening: false,
        createOpen: false, createBusy: false, createError: '', createBlocked: false};
    let verifySession = async () => false;
    const update = patch => { state = {...state, ...patch}; publish(state); };
    const active = () => !ended && !pageHidden && !session?.disposed;
    const ready = () => active() && session?.state === 'ready';

    function lockUi(message) {
        // Direct clearing is necessary before a queued Vue render or a BFCache
        // snapshot. Vue state is cleared too; the DOM is never a source of truth.
        try { clear({inputs: true, codes: true, lock: true}); }
        finally {
            update({mode: 'locked', snapshot: null, otp: {state: 'locked', rows: [], notice: ''},
                query: '', feedback: '', createOpen: false, createBusy: false, createOpening: false,
                unlockBusy: false, unlockError: '', createError: '', canReload: true,
                status: message, statusType: 'error'});
        }
    }
    function fail(message) {
        // The first terminal cause wins. A late async rejection must not replace
        // an uncertainty/rate-limit warning or revive a BFCache-restored page.
        if (ended) return;
        ended = true;
        bootstrapAbort.abort();
        try { session?.dispose(); }
        finally {
            try { presenter?.dispose(); }
            finally { lockUi(message); }
        }
    }
    async function requireSession() {
        if (!active() || await verifySession() !== true) {
            try { session?.dispose(); }
            finally { throw new SessionFault('auth-required'); }
        }
        if (!active()) throw new SessionFault('disposed');
    }
    function showResult(snapshot) {
        if (!active()) return;
        const authorized = snapshot.state === 'ready';
        update({mode: snapshot.state, snapshot, query: authorized ? state.query : '',
            status: authorized ? 'OTP-Konten geladen.' : 'Zusätzliche Tresor-Authentifizierung erforderlich.',
            statusType: 'info', unlockError: ''});
        presenter.render(snapshot, state.query);
        if (snapshot.state === 'needs-auth') {
            if (snapshot.needsToken && !snapshot.providers.some(provider => provider.supported)) {
                fail('Der konfigurierte 2FA-Anbieter wird nicht unterstützt.');
            } else focus(snapshot.needsChallenge ? 'master' : 'token');
        }
    }
    function createFailure(error) {
        if (ended || pageHidden) return;
        // Preserve the more precise API expiry/rate-limit messages even when
        // the domain session already disposed itself during the failed probe.
        if (['passwords-session-expired', 'auth-rate-limited', 'create-uncertain'].includes(error?.code)) {
            if (error.code === 'create-uncertain') update({createBlocked: true});
            fail(createErrorMessage(error.code));
        } else if (session?.disposed || ['auth-required', 'auth-invalid', 'disposed'].includes(error?.code)) {
            fail('Nextcloud-Sitzung nicht mehr gültig. Bitte erneut anmelden.');
        } else if (state.createOpen) {
            // Unknown exception details may contain upstream or input data.
            // Only our finite public error vocabulary may reach Vue state.
            update({createError: safeCreateErrorCode(error?.code)});
            focus(error?.code === 'create-invalid-secret' ? 'secret' : 'create-error');
        } else {
            update({status: 'Die Passwords-API konnte nicht überprüft werden. Bitte erneut versuchen.', statusType: 'warning'});
        }
    }
    async function start() {
        if (started || ended) return;
        started = true;
        publish(state);
        try {
            if (config?.status !== 'ready') {
                fail('Die Passwords-Integration ist nicht verfügbar.');
                return;
            }
            verifySession = checkSession(config, pageUrl, fetcher);
            presenter = createPresenter({verifySession, isHidden: () => doc.hidden || pageHidden,
                publish: otp => {
                    if (ended || pageHidden) return;
                    const nextRows = new Map(otp.rows.map(row => [row.account.id, row]));
                    // Only erase a previously visible code when it is revoked.
                    // Initial null rows and a later account being calculated
                    // must not repeatedly scrub other, already valid codes.
                    if (state.otp.rows.some(row => row.code !== null
                            && nextRows.get(row.account.id)?.code == null)) clear({codes: true});
                    update({otp});
                },
                notify: feedback => { if (active()) update({feedback}); },
                fatal: message => fail(message)});
            await boundedRequest({}, () => sodiumReady(), {timeoutMs: 15000, signal: bootstrapAbort.signal});
            await requireSession();
            const validated = await bootstrap(config, pageUrl, doc, fetcher, bootstrapAbort.signal);
            try {
                if (!active()) throw new SessionFault('disposed');
                session = createSession(createClient(validated));
            } finally { validated.token = ''; validated.user = ''; }
            presenter.setSession(session);
            await requireSession();
            const result = await session.begin();
            await requireSession();
            showResult(result);
        } catch (error) {
            if (!ended && !pageHidden) fail(messageFor(error?.code));
            else session?.dispose();
        }
    }
    async function unlock(auth) {
        if (!active() || state.unlockBusy || session?.state !== 'needs-auth') {
            auth.password = ''; auth.otpCode = '';
            return;
        }
        // Own the short-lived request values before a UI reset or a duplicate
        // submit can mutate the caller's object while session checks are pending.
        const credentials = {password: auth.password, providerId: auth.providerId, otpCode: auth.otpCode};
        auth.password = ''; auth.otpCode = '';
        try {
            clear({inputs: true});
            update({unlockBusy: true, unlockError: '', statusType: 'info',
                status: 'Tresor wird über die offizielle Passwords-API freigegeben …'});
            await requireSession();
            const updated = await session.unlock(credentials);
            await requireSession();
            showResult(updated);
        } catch (error) {
            if (ended || pageHidden) return;
            if (error?.code === 'invalid-master-key' && active() && session.state === 'needs-auth') {
                update({unlockError: error.code, status: messageFor(error.code), statusType: 'warning'});
                focus('master');
            } else fail(messageFor(error?.code));
        } finally {
            credentials.password = ''; credentials.otpCode = '';
            auth.password = ''; auth.otpCode = '';
            clear({inputs: true});
            if (!ended) update({unlockBusy: false});
        }
    }
    async function openCreate() {
        if (!ready() || state.createOpen || state.createBusy || state.createOpening || state.createBlocked) return;
        update({createOpening: true});
        try {
            await requireSession();
            await session.assertCreateAccess();
            await requireSession();
            if (!ready() || state.createBlocked) return;
            update({createOpen: true, createError: ''});
            focus('label');
        } catch (error) { createFailure(error); }
        finally { if (!ended) update({createOpening: false}); }
    }
    function closeCreate() {
        if (ended || pageHidden || state.createBusy) return false;
        clear({inputs: true});
        update({createOpen: false, createError: ''});
        if (ready()) focus('create');
        return true;
    }
    async function create(values) {
        if (!ready() || !state.createOpen || state.createBusy || state.createBlocked) {
            values.password = ''; values.secret = '';
            return;
        }
        const requestValues = {label: values.label, username: values.username,
            password: values.password, secret: values.secret};
        values.password = ''; values.secret = '';
        try {
            clear({inputs: true});
            update({createBusy: true, createError: ''});
            const created = await session.createNewOtp(requestValues, {verifySession});
            if (!ready()) return;
            update({createOpen: false, createBusy: false});
            showResult(created.snapshot);
            update({status: 'Neuer OTP-Eintrag in Passwords gespeichert.', statusType: 'success'});
            focus('create');
        } catch (error) { createFailure(error); }
        finally {
            requestValues.password = ''; requestValues.secret = '';
            values.password = ''; values.secret = '';
            clear({inputs: true});
            if (!ended) update({createBusy: false});
        }
    }
    function filter(query) {
        if (!ready()) return;
        update({query, feedback: ''});
        presenter.filter(query);
    }
    function pageHide() {
        if (pageHidden) return;
        pageHidden = true;
        ended = true;
        bootstrapAbort.abort();
        try { presenter?.dispose(); }
        finally {
            try { lockUi('Sitzung beendet. Bitte Seite neu laden.'); }
            finally {
                // Local invalidation occurs synchronously inside close(); the
                // network revocation remains best effort during navigation.
                try { void Promise.resolve(session?.close()).catch(() => {}); }
                catch (_) { session?.dispose(); }
            }
        }
    }
    function pageShow(event) {
        if (event.persisted) {
            pageHide();
            pageHidden = false;
            lockUi('Sitzung beendet. Bitte Seite neu laden.');
        }
    }
    return {
        start, unlock, openCreate, closeCreate, create, filter, pageHide, pageShow,
        copy: id => { if (ready()) presenter.copy(id); },
        visibilityChanged: () => {
            if (doc.hidden) clear({inputs: true, codes: true});
            presenter?.visibilityChanged();
        },
        focusChanged: () => presenter?.focusChanged(),
        fail: () => fail('Die Oberfläche konnte nicht sicher ausgeführt werden. Bitte Seite neu laden.'),
    };
}
