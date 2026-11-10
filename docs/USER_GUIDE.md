# User guide

The app is available as **Passwort OTP Code Generator** in the Nextcloud navigation for users assigned access by their administrator.

## View and copy codes

1. Sign in to Nextcloud and open the OTP app.
2. If requested, complete the Nextcloud Passwords master-passphrase/CSE or secondary-factor challenge.
3. Find the account in the list of valid TOTP records. The list can include your own records and records shared with you through the original Passwords app.
4. Use the account's explicit copy button to place its current one-time code on the clipboard. Enter that code promptly in the corresponding service.
5. Use the search field to filter accounts; clear it to return to all visible accounts.

TOTP codes normally change at the account's configured interval. Incorrect device time can prevent successful verification. Unsupported HOTP records do not produce TOTP codes.

## Create a new OTP entry

Choose **Neues OTP Passwort hinzufügen**. Supply a title, an account password and the service's Base32 TOTP setup secret. A username is optional. The new record is stored through the original Passwords API and can subsequently be managed and shared in **Nextcloud Passwords**.

The current create dialog uses SHA-1, six digits and 30-second period. Check that these settings match the service before saving. New Base32 secrets must meet the application's minimum length validation.

**Never share an OTP setup secret or master passphrase in bug reports.**

## Session behavior

The app checks login validity before generating codes in new time windows and on focus. If your Nextcloud or Passwords API session expires, unlock or reload as prompted. An already copied code cannot be revoked by signing out of Nextcloud.

The interface is currently primarily **German**. Browser extensions and the system clipboard may retain sensitive data; use a trusted browser.

See [Security review](SECURITY_REVIEW.md) for limitations.
