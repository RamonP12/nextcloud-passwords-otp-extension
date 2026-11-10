# Installation – Nextcloud Passwords OTP 1.0.0

**Status:** manual source distribution; no Nextcloud App Store package or generic supported upgrade path.

## Requirements

- Nextcloud **35.0.2** with the original **Passwords 2026.11.20** app enabled (tested combination).
- PHP 8.3–8.5 per app metadata; actual production pilot uses PHP 8.4.27.
- An authenticated browser with WebCrypto.
- Database and persistent app data backups with a known restore procedure.
- For AIO: writable persistent custom_apps mount, PostgreSQL, local Unix Docker and Python 3.10+.

## Obtain a commit-bound archive

Use a clean checkout of the **public main** at the exact intended release commit; verify the source and then build the ZIP. No unverified third-party ZIP or mixed-commit scripts.

~~~sh
git clone https://github.com/RamonP12/nextcloud-passwords-otp-extension.git
cd nextcloud-passwords-otp-extension
npm ci
npm test
npm run test:client
npm run build
python3 scripts/release.py .build/package
sha256sum .build/package/passwords_otp-1.0.0.zip
~~~

Keep the reported commit SHA and package SHA256 together. The build manifest embeds its source commit and SHA256 hashes of bundled files.

## First-time installation on Nextcloud AIO

Follow the complete [AIO manual installation guide](AIO_MANUAL_INSTALL.md), including:
1. Verify backups and restore access.
2. Use a valid, existing pilot group; do not use --all-users as a shortcut.
3. Copy the ZIP **and** scripts/aio_install.py + scripts/release.py from the same checkout.
4. Run inspect and the package/group-bound preflight.
5. Explicitly authorize installation, then verify installed app hashes and scope.
6. Test an in-group and out-of-group user in real browsers.

**Do not use this first-install tool for an already installed passwords_otp, including 0.7.3.** It intentionally refuses to overwrite an existing app or registration. A future update mechanism must be separately developed and tested.

## Non-AIO installations

The app code targets Nextcloud 35, but there is **no documented or tested general-purpose non-AIO deployment procedure** in 1.0.0. Do not assume the AIO installer supports arbitrary Docker or bare-metal setups.

## After installation

Open the new Nextcloud navigation entry **Passwort OTP Code Generator** as an enabled user. Confirm that personal and shared TOTP entries load, that codes match a known *synthetic* test source, that session expiry and logout behave correctly, and that users outside the pilot group cannot access the app.

See [User guide](USER_GUIDE.md), [Compatibility](COMPATIBILITY.md) and [Security review](SECURITY_REVIEW.md).
