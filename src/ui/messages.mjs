const CREATE_MESSAGES = Object.freeze({'create-invalid-label': 'Bitte eine Bezeichnung mit maximal 160 Zeichen eingeben.',
        'create-invalid-username': 'Der Benutzername ist zu lang.',
        'create-invalid-password': 'Bitte ein g\u00fcltiges, nicht leeres Dienstpasswort eingeben.',
        'create-invalid-secret': 'Ung\u00fcltiges Base32-Secret. Den Einrichtungsschl\u00fcssel pr\u00fcfen.',
        'create-cse-unavailable': 'Clientseitige Verschl\u00fcsselung nicht verf\u00fcgbar. Es wurde nichts gespeichert.',
        'cse-unavailable': 'Clientseitige Verschl\u00fcsselung nicht verf\u00fcgbar. Es wurde nichts gespeichert.',
        'create-crypto-unavailable': 'Die ben\u00f6tigte Browser-Kryptografie ist nicht verf\u00fcgbar.',
        'create-encryption-unknown': 'Der Verschl\u00fcsselungsmodus konnte nicht gepr\u00fcft werden. Es wurde nichts gespeichert.',
        'create-busy': 'Die Erstellung l\u00e4uft bereits.',
        'create-auth-unavailable': 'Die Passwords-API konnte nicht sicher gepr\u00fcft werden. Es wurde nichts gespeichert.',
        'passwords-session-expired': 'Die Passwords-API-Sitzung ist abgelaufen. Es wurde kein neuer Eintrag gespeichert. Bitte Seite neu laden.',
        'auth-rate-limited': 'Die Passwords-API begrenzt Anfragen (HTTP 403/429). Die Nextcloud-Anmeldung ist nicht als abgelaufen nachgewiesen. Nach einer Wartezeit neu laden.',
        'create-uncertain': 'Der Erstellungsstatus ist unklar. Vor einem neuen Versuch Passwords pr\u00fcfen und die Seite neu laden.'});
export function safeCreateErrorCode(code) {
    return typeof code === 'string' && Object.hasOwn(CREATE_MESSAGES, code) ? code : 'create-failed';
}
export function createErrorMessage(code) {
    return CREATE_MESSAGES[safeCreateErrorCode(code)]
        || 'Der Eintrag konnte nicht erstellt werden. Angaben und Sitzung pr\u00fcfen; Passwort und Secret erneut eingeben.';
}
const SESSION_MESSAGES = Object.freeze({'https-required': 'HTTPS ist erforderlich.', 'invalid-config': 'Ung\u00fcltige Initialisierung.',
        'invalid-api-url': 'Der Passwords-API-Endpunkt ist nicht vertrauensw\u00fcrdig.',
        'invalid-bootstrap-url': 'Der OTP-Verbindungsendpunkt ist nicht vertrauensw\u00fcrdig.',
        'csrf-unavailable': 'Die Nextcloud-Sitzung ist nicht vollst\u00e4ndig verf\u00fcgbar. Bitte neu anmelden.',
        'bootstrap-failed': 'Die Passwords-Zugangsdaten konnten nicht sicher geladen werden. Bitte neu anmelden.',
        'disposed': 'Die Sitzung wurde beendet. Bitte Seite neu laden.',
        'unsupported-challenge': 'Diese Master-Passwort-Challenge wird nicht unterst\u00fctzt.',
        'unsupported-token-provider': 'Dieser zus\u00e4tzliche Authentifizierungsanbieter wird nicht unterst\u00fctzt.',
        'invalid-password-input': 'Bitte den g\u00fcltigen Master-Schl\u00fcssel eingeben.',
        'invalid-master-key': 'Master-Schlüssel nicht akzeptiert. Bitte erneut versuchen.',
        'auth-invalid': 'Authentifizierung abgewiesen. Seite neu laden und erneut versuchen.',
        'auth-rate-limited': 'Authentifizierung vor\u00fcbergehend eingeschr\u00e4nkt.',
        'auth-required': 'Tresor gesperrt. Bitte erneut authentifizieren.',
        'invalid-list': 'Unerwartetes Antwortformat der Passwortliste.',
        'cse-unavailable': 'Der CSE-Schl\u00fcssel kann nicht freigegeben werden.',
        'unsupported-cse': 'Der Verschl\u00fcsselungsmodus wird nicht unterst\u00fctzt.',
        'crypto-unavailable': 'Der Browser kann OTP-Codes nicht sicher berechnen.'});
export function messageFor(code) {
    return typeof code === 'string' && Object.hasOwn(SESSION_MESSAGES, code) ? SESSION_MESSAGES[code]
        : 'Die OTP-Sitzung konnte nicht sicher ge\u00f6ffnet werden.';
}
