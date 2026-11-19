# User guide

The app in [v1.1.3](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.1.3) appears as **Passwords OTP Generator** in Nextcloud navigation and on the administrator’s Apps page. The icon is a shield with a diagonal key cut-out. Published version 1.1.2 appears as **Passwort OTP Code Generator**.

## Required Passwords app

The administrator must install and enable Passwords **2026.11.20** before enabling OTP. Users need access to both apps. A Passwords group restriction can deny an individual user without disabling OTP for other authorized users. If Passwords is disabled, removed or changed to an unsupported version, OTP denies further operations and disables itself through the documented lifecycle checks. After restoring the prerequisite, the administrator must enable OTP explicitly; it does not reactivate itself.

The interface cannot revoke a code already copied to another application. Normal session/window checks remain active. See [dependency lifecycle](DEPENDENCY_LIFECYCLE.md) for detection timing and administrator recovery.

## View and copy codes

1. Sign in to Nextcloud and open the OTP app.
2. If requested, complete the Passwords master-passphrase/CSE or supported secondary-factor challenge. A wrong master passphrase can be corrected without resubmitting other operations.
3. Find the account in the valid TOTP list. It can contain your own Passwords entries and entries shared with you through the original app.
4. Click the displayed code or activate **Code kopieren** for that account. Both controls support Tab, Enter and Space. In 1.1.2, use **Code kopieren**. Enter the copied code promptly in the service requesting it.
5. Use **TOTP-Konten durchsuchen** to filter accounts; clear the search to restore the list. Searching does not discard accounts or reset their valid codes.

Copying is temporarily unavailable close to expiry or while session validity is being checked. A failed clipboard request is reported rather than presented as success. Leading zeroes are part of the code.

![Version 1.1.3 showing a clickable code and the separate copy button in a synthetic Nextcloud fixture](images/vue-1.1.3-light.png)

Codes change according to each account's configured period. Incorrect device time can prevent verification. HOTP and invalid or unsupported configurations do not produce TOTP codes; the interface explains omitted records when applicable.

## Create a new OTP entry

Choose **Neues OTP Passwort hinzufügen**. The app checks access before opening the dialog. Supply a title, the service account's password and its **Base32 TOTP setup secret**. A username is optional. This password is not the Nextcloud master passphrase.

Creation uses **SHA-1, six digits and a 30-second period**. Check these settings against the service before saving. New secrets must meet the application's minimum-length validation.

Choose **OTP speichern** to confirm. Pressing Enter in an input field does not create an entry; keyboard activation of the save button still works. **Abbrechen** or Escape closes an idle dialog and clears the secret fields. While a save is in progress, closing and repeated submission are disabled. On completion the new record is stored together with your other passwords in the original Passwords app. Use the Passwords app to edit, delete or share it with other Nextcloud users.

If the interface reports an uncertain save result, verify the original Passwords records before attempting another create operation. The app blocks a blind retry because the first request might already have been stored.

## Session and keyboard behavior

The app checks login validity before new mandatory time windows and when returning to the page. Leaving or hiding the page clears displayed codes and secret inputs; focus restoration requires appropriate verification before codes are shown again. Navigating away and returning through browser history can require a reload and fresh vault authentication.

Keyboard focus follows the active form/dialog and returns to the opener when an idle create dialog closes. Errors distinguish authentication, validation, rate-limit and clipboard problems. If Nextcloud or the Passwords API session expires, reload or sign in as prompted. Signing out cannot revoke a code that has already been copied.

The app's own interface remains **German**, with an explicit German language annotation. Additional app languages are tracked in [#6](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/6).

Use a trusted browser. Browser extensions and clipboard history can retain sensitive data. Never place a real OTP setup secret, master passphrase, token or cookie in a bug report. See [Security review](SECURITY_REVIEW.md) for the unchanged architecture and threat boundaries.
