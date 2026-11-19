/** Fail-closed, synchronous erasure before Vue's next rendering tick. These
 * selectors are restricted to this app and its explicit dialog portal. Never
 * remove managed nodes: state-driven rendering performs their normal teardown.
 */
export function clearSensitiveDom(doc, {inputs = false, codes = false, lock = false} = {}) {
    for (const root of [doc.getElementById('passwords-otp-app'), doc.getElementById('passwords-otp-dialog-host')]) {
        if (!root) continue;
        if (inputs) {
            for (const input of root.querySelectorAll('input[data-otp-secret]')) input.value = '';
        }
        if (codes) {
            for (const output of root.querySelectorAll('.passwords-otp-ap3__code')) output.textContent = '—';
            for (const button of root.querySelectorAll('.passwords-otp-ap3__copy')) button.disabled = true;
            for (const progress of root.querySelectorAll('.passwords-otp-ap3__progress')) progress.value = 0;
        }
        if (lock) {
            for (const element of root.querySelectorAll('[data-otp-protected]')) element.hidden = true;
            if (root.id === 'passwords-otp-dialog-host') root.hidden = true;
        }
    }
}
