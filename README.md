# Passwort OTP Code Generator – unofficial companion for Nextcloud Passwords

[![License: AGPL-3.0-or-later](https://img.shields.io/badge/license-AGPL--3.0--or--later-blue.svg)](LICENSE)
[![Release: v1.0.0](https://img.shields.io/badge/release-v1.0.0-blue.svg)](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.0.0)

An **independent, unofficial Nextcloud app** that displays time-based one-time password (TOTP) codes from [Nextcloud Passwords](https://apps.nextcloud.com/apps/passwords). It provides a focused desktop interface without modifying the original Passwords application.

**Version: 1.0.1 (unreleased source candidate)** · **Latest published release: v1.0.0** · **License: AGPL-3.0-or-later** · **Distribution: manual source ZIP; not in the Nextcloud App Store**

**v1.0.1 maintenance status:** fixes the mandatory `<bugs>` URL in Nextcloud app metadata, while retaining the validated 1.0.0 OTP business logic and updating only versioned JS/CSS markers, asset names and the PHP loader reference. The source candidate is **not** a new public release, has not received fresh live installation acceptance and does **not** resolve [the upstream WebUI bearer privilege issue](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/1). Do not use this development branch or moving `main` instead of a versioned, checksum-verified release. See [v1.0.1 candidate notes](docs/RELEASE_NOTES_v1.0.1.md).

## Features

- View and copy TOTP codes from your own and Passwords-shared entries.
- Search OTP accounts without losing the underlying entries.
- Generate TOTP codes locally with WebCrypto (RFC 6238; supported existing SHA-1, SHA-256, SHA-512 configurations).
- Create **new** Passwords entries with an Android-compatible TOTP custom field; the source Passwords app manages sharing and later edits.
- Support Passwords vault authentication, including compatible CSE master-passphrase and two-factor challenges.
- Recheck the Nextcloud login before generating codes for new 30-second time windows and when returning to the page.

## Tested environment

| Component | Validation |
| --- | --- |
| Nextcloud | 35.0.2 (internal 35.0.2.2) |
| Nextcloud Passwords | 2026.11.20 |
| PHP | 8.4.27 on a Nextcloud AIO pilot; automated security checks on PHP 8.5 |
| Database | PostgreSQL (earlier internal AIO pilot); MariaDB (published v1.0.0 local acceptance) |
| Browser | Real desktop browser acceptance on localhost; earlier pilot and synthetic Chromium tests |

**The exact published v1.0.0 ZIP (not the new 1.0.1 candidate) passed a manual localhost/Docker Compose acceptance on 2026-11-11: 10/10 test blocks and 49/49 individual checks.** This was a fresh v1.0.0 app installation into an existing disposable Nextcloud/MariaDB test fixture after removing an older internal candidate. **A real AIO/PostgreSQL first-install of the published ZIP is still outstanding**; the earlier internal AIO pilot does not satisfy that gate. See [full local acceptance](docs/LOCAL_ACCEPTANCE_v1.0.0_2026-11-11.md), [validation](docs/VALIDATION.md), [compatibility](docs/COMPATIBILITY.md) and [release integrity / mutability record](docs/RELEASE_INTEGRITY_v1.0.0.md).

## Requirements and installation

- Nextcloud 35 and the original, enabled Nextcloud Passwords app.
- A compatible PHP installation and a browser supporting WebCrypto.
- A verified full Nextcloud/database backup and a documented restore path.
- For the supplied AIO installer: Docker with a local Unix socket, PostgreSQL, persistent custom_apps storage, Python 3.10+, a verified package, and a real target group.

**The supplied AIO installer performs first-time installs only.** It deliberately refuses an installation where passwords_otp already exists, including upgrades from earlier pilot versions. In particular, **do not run the 1.0.0 AIO first-install command against an existing 0.7.3 deployment**.

Start with [Installation](docs/INSTALLATION.md) and [AIO installation and rollback](docs/AIO_MANUAL_INSTALL.md). Download the exact release ZIP and verify its published SHA256, or build **from tag `v1.0.0` rather than moving `main`**. This project is not distributed through the Nextcloud App Store.

## What it does not do

- No HOTP counter support.
- No editing or deleting existing Passwords entries in this interface.
- No independent, read-only API credential: the Passwords WebUI bearer token has broader privileges than the buttons exposed by this app.
- No server-guaranteed immediate Passwords API logout when a browser tab closes.
- No general, tested in-place upgrade tool for production AIO installations.
- Current user interface is primarily **German**.

Storing account passwords and their TOTP secrets in the same vault may reduce the independence of the second factor. The app is **not** an additional factor protecting access to that vault. Review [Security boundaries](docs/SECURITY_REVIEW.md) before enabling it.

## Development

Requires Node.js 22+, Python 3.10+, and the locked npm dependencies.

~~~sh
npm ci
npm test
npm run test:client
npm run build
python3 scripts/release.py .build/package
~~~

The repository also includes Python, PHP and synthetic Chromium tests. A green build does not substitute for real Nextcloud/Passwords compatibility testing. The CI workflow is currently disabled, so no CI passing-status badge is displayed. See [Development and contributions](CONTRIBUTING.md).

## Support, security and licenses

Report functional issues using [GitHub Issues](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues). Report security vulnerabilities **privately** as described in [Security Policy](.github/SECURITY.md). Never post real passwords, TOTP secrets, API tokens, cookies or unredacted network traces.

Own code: **GNU AGPL-3.0-or-later**; see [LICENSE](LICENSE). Bundled dependencies retain their own licenses; see [Third-party notices](THIRD_PARTY_NOTICES.md).

**Unofficial community project.** Not affiliated with or endorsed by Nextcloud GmbH or the original Nextcloud Passwords maintainers.
