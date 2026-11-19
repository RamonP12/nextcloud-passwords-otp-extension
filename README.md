# Passwort OTP Code Generator – unofficial companion for Nextcloud Passwords

[![License: AGPL-3.0-or-later](https://img.shields.io/badge/license-AGPL--3.0--or--later-blue.svg)](LICENSE)
[![Release: v1.1.2](https://img.shields.io/badge/release-v1.1.2-blue.svg)](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.1.2)

An **independent, unofficial Nextcloud app** that displays time-based one-time password (TOTP) codes from [Nextcloud Passwords](https://apps.nextcloud.com/apps/passwords). It provides a focused interface without modifying the original Passwords application.

**Current source: 1.1.2 — Nextcloud Vue edition with enforced Passwords dependency.** Passwords **2026.11.20** must be installed and enabled. New installation registration is rejected when that prerequisite is absent; incompatible activation is reversed, and loss of the dependency disables OTP. Per-user group denial does not disable OTP for other users. See the [dependency lifecycle and its timing limits](docs/DEPENDENCY_LIFECYCLE.md).

Obtain the version-matched **tar.gz**, its checksum and build manifest from the [v1.1.2 GitHub Release](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.1.2). The ZIP is also provided for the existing transactional localhost installer. The published **v1.0.0** archive, tag and historical acceptance records remain unchanged. Distribution is manual and unsigned; this project is not in the Nextcloud App Store. [App Store packaging](docs/APPSTORE_PACKAGING.md) separates archive compatibility from certificate signing and publication.

## Vue migration

The current source uses **Vue 3.5.45** and **Nextcloud Vue 9.14.1** for the application layout, forms, dialogs, buttons and status messages. The existing Passwords authentication, encryption, OTP parsing, WebCrypto calculation and create-once API policy remain separate from the Vue presentation layer.

The migration includes a Vite build, local regression tests against the compiled application, and strict package and license checks. Read the [1.1.2 verification record](docs/VALIDATION_1.1.2.md), [historical 1.1.1 verification and local acceptance record](docs/VALIDATION_VUE_1.1.1.md), [migration implementation report](docs/NEXTCLOUD_VUE_MIGRATION.md) and [historical 1.1.0 candidate validation](docs/VALIDATION_VUE_1.1.0.md) for the exact scope of each result. **GitHub Actions is unavailable because the quota is exhausted; push and pull-request triggers are removed.** A manual workflow definition is retained for possible later use, and no hosted CI success is claimed.

## Features

- View and copy TOTP codes from your own and Passwords-shared entries.
- Search OTP accounts without losing the underlying entries or restarting authentication checks.
- Generate codes locally with WebCrypto (RFC 6238; supported existing SHA-1, SHA-256 and SHA-512 configurations).
- Create **new** Passwords entries with an Android-compatible TOTP custom field; manage sharing and later edits in the original Passwords app.
- Complete compatible Passwords CSE master-passphrase and secondary-factor challenges.
- Recheck the Nextcloud login before new code windows, on focus and when returning to the page; reject expired or near-expiry clipboard copies.
- Use Nextcloud component styling, keyboard-accessible controls, distinct status messages and responsive layouts.

The app's text remains **German**. Multilingual app content ([#6](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/6)) and clicking the displayed code itself to copy ([#7](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/7)) are separate feature requests; use the explicit copy button. The proposed display-name/icon change to **Passwords OTP Generator** is recorded in [#12](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/12) as **backlog only; not implemented**.

## Compatibility and verification

| Scope | Status |
| --- | --- |
| App metadata | Nextcloud 35; PHP 8.3–8.5 |
| Passwords integration target | Passwords 2026.11.20; exact version required; dependency enforcement does not turn internal upstream classes into public APIs |
| Version 1.1.2 | [Maintainer-confirmed localhost upgrade and normal dependency lifecycle](docs/LOCAL_ACCEPTANCE_v1.1.2_2026-11-19.md) passed on one Nextcloud/MariaDB fixture; fresh install/removal, group separation and production AIO remain untested |
| Vue localhost acceptance | Maintainer confirmed all five manual checks on candidate 1.1.0: independent TOTP reference, clipboard, search, persistence and logout invalidation |
| Published v1.0.0 | Exact ZIP passed the recorded 2026-11-11 localhost/Nextcloud/MariaDB acceptance: 10/10 blocks, 49/49 checks |
| Production AIO/PostgreSQL | No general production approval or tested in-place upgrade procedure |

The earlier v1.0.0 results are historical evidence, not test results for the Vue migration. See [compatibility](docs/COMPATIBILITY.md), [v1.0.0 local acceptance](docs/LOCAL_ACCEPTANCE_v1.0.0_2026-11-11.md), [historical validation](docs/VALIDATION.md) and the [v1.0.0 release integrity/mutability record](docs/RELEASE_INTEGRITY_v1.0.0.md).

## Installation

Start with [Installation](docs/INSTALLATION.md) and [AIO installation and rollback](docs/AIO_MANUAL_INSTALL.md). **Always use the installer scripts from the same source version as the archive.** Current 1.1.2 scripts accept the matching 1.1.2 package; use the `v1.1.2` tagged scripts for this release. Download the `v1.0.0` tagged scripts when working with the historical 1.0.0 archive.

The AIO tool supports **first-time installation only** and refuses an existing `passwords_otp` deployment, including older internal versions such as 0.7.3. The dependency migration checks prerequisites and adds no OTP data tables; it does not supply a production AIO upgrade path. The five accepted 1.1.0 functional checks alone did not cover the new 1.1.2 lifecycle. The maintainer has since accepted the 1.1.2 localhost upgrade, ordinary Passwords disable/enable safeguards and basic OTP operation. [The local acceptance report](docs/LOCAL_ACCEPTANCE_v1.1.2_2026-11-19.md) details what passed and what remains untested.

The Nextcloud server needs the compiled application assets and PHP files; **Node.js and npm are build-time tools**, not production server requirements.

## Security boundaries

- No HOTP counters, editing or deletion of existing Passwords entries in this interface.
- The upstream Passwords WebUI token has broader server-side privileges than this app's exposed operations. The client allowlist does not reduce those privileges.
- Storing passwords and TOTP seeds in one vault does not provide an independent second factor against compromise of that vault.
- Browser extensions, compromised same-origin scripts and clipboard history remain relevant attack surfaces.
- Tab closure clears local state, but immediate server-side Passwords-session revocation is best effort.

Read [Security boundaries](docs/SECURITY_REVIEW.md) before enabling the app. The Vue migration does not resolve the architectural token-scope issue [#1](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/1).

## Development

Use **Node.js 22.12+ within 22.x, or 24.x**, npm, Python 3.10+, PHP, and Chromium with Python Playwright for browser checks. A typical local sequence is:

```sh
npm ci
npm test
npm run test:client
python3 -m unittest discover -s tests/python -v
npm run test:php
npm audit --audit-level=low
npm run build
npm run test:browser
```

Package a **clean, committed checkout** with `python3 scripts/release.py .build/package`. The ZIP and TAR contain the same verified runtime payload, exact source commit and file hashes. No signing key or development fixture is packaged. See [Development](docs/DEVELOPMENT.md) for prerequisites, reproducibility and the distinction between synthetic browser checks, real Nextcloud integration and production acceptance.

## Support, security and licenses

Report functional issues using [GitHub Issues](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues). Report vulnerabilities **privately** as described in [Security Policy](.github/SECURITY.md). Never post real passwords, OTP seeds, API tokens, cookies or unredacted network traces.

Own code: **GNU AGPL-3.0-or-later**; see [LICENSE](LICENSE). Bundled dependencies retain their own licenses; see [Third-party notices](THIRD_PARTY_NOTICES.md).

**Unofficial community project.** Not affiliated with or endorsed by Nextcloud GmbH or the original Nextcloud Passwords maintainers.
