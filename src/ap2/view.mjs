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
