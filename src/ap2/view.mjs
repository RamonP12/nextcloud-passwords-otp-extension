export function otpListNotice(snapshot, resultCount, t) {
    if (snapshot?.state !== 'ready') return '';
    const invalid = snapshot.invalidOtpCount || 0;
    const unsupported = snapshot.unsupportedOtpCount || 0;
    const total = snapshot.otpAccounts?.length || 0;
    const notices = [];
    if (total === 0) notices.push(t('no-accounts'));
    else if (resultCount === 0) notices.push(t('no-matches'));
    if (invalid > 0) notices.push(t('invalid-entries', {count: invalid}));
    if (unsupported > 0) notices.push(t('unsupported-entries', {count: unsupported}));
    return notices.join(' ');
}
