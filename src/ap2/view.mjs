import {searchOtpAccounts} from './parser.mjs';

export function otpListNotice(snapshot, resultCount) {
    if (snapshot?.state !== 'ready') return '';
    const invalid = snapshot.invalidOtpCount || 0;
    const unsupported = snapshot.unsupportedOtpCount || 0;
    const total = snapshot.otpAccounts?.length || 0;
    let basic = total === 0 ? 'Keine gültigen TOTP-Konten vorhanden.'
        : resultCount === 0 ? 'Keine TOTP-Konten entsprechen der Suche.' : '';
    if (invalid > 0) basic += (basic ? ' ' : '') + invalid +
        ' OTP-Eintrag/Einträge wegen ungültiger Konfiguration ausgeblendet.';
    if (unsupported > 0) basic += (basic ? ' ' : '') + unsupported +
        ' OTP-Eintrag/Einträge mit nicht unterstütztem Typ (z. B. HOTP) ausgeblendet.';
    return basic;
}
/** Only validated public metadata is rendered, exclusively through textContent. */
export function renderOtpView(snapshot, query, nodes, doc, options = {}) {
    nodes.list.replaceChildren();
    const authorized = snapshot?.state === 'ready';
    nodes.section.hidden = !authorized;
    nodes.search.disabled = !authorized;
    if (nodes.count) nodes.count.textContent = authorized ? String(snapshot.otpCount) : '\u2013';
    if (nodes.invalid) nodes.invalid.textContent = authorized ? String(snapshot.invalidOtpCount) : '\u2013';
    if (!authorized) { nodes.empty.textContent = ''; return 0; }
    const results = searchOtpAccounts(snapshot.otpAccounts, query);
    for (const account of results) {
        if (account.type !== 'totp') continue;
        const item = doc.createElement('li');
        item.className = 'passwords-otp-ap2__item';
        const title = doc.createElement('strong');
        title.textContent = account.title;
        const details = doc.createElement('span');
        details.className = 'passwords-otp-ap2__details';
        const subtitle = [account.issuer, account.accountName, account.username]
            .filter((value, index, values) => value && values.indexOf(value) === index).join(' \u00b7 ');
        const configLabel = 'TOTP \u00b7 ' + account.algorithm.toUpperCase()
            + ' \u00b7 ' + String(account.digits) + ' Stellen';
        details.textContent = subtitle ? subtitle + ' \u00b7 ' + configLabel : configLabel;
        item.append(title, details);
        options.renderControls?.(account, item, doc);
        nodes.list.append(item);
    }
    nodes.empty.textContent = otpListNotice(snapshot, results.length);
    return results.length;
}
