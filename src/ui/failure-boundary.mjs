/**
 * Register the controller stop hook during setup, before Vue can render or run
 * mounted hooks. UI failures must stop pending authentication even when mount()
 * has not returned a component instance yet. No exception details are exposed.
 */
export function createUiFailureBoundary(clear) {
    let failed = false, handling = false, stopController = null;
    function fail() {
        failed = true;
        if (handling) return;
        handling = true;
        try {
            const stop = stopController;
            stopController = null;
            try { stop?.(); } catch (_) { /* Continue synchronous erasure. */ }
            try { clear(); } catch (_) { /* The caller also replaces a broken view. */ }
        } finally { handling = false; }
    }
    function register(stop) {
        if (typeof stop !== 'function') { fail(); return; }
        stopController = stop;
        // Covers an initial failure before App's setup completed. A subsequent
        // onMounted/start must observe an already terminated controller.
        if (failed) fail();
    }
    return {fail, register, get failed() { return failed; }};
}
