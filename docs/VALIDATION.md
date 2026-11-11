# Validation status — v1.0.0 and v1.0.1 candidate

> **v1.0.1 is a metadata-only source candidate.** The 10/10 manual blocks and 49/49 checks below are evidence for the **published v1.0.0 ZIP only**. They must not be copied as a fresh real-browser or AIO/PostgreSQL acceptance of v1.0.1. The coordinated version bump and appinfo schema regression are tracked in [issue #2](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/2), with candidate notes at [v1.0.1](RELEASE_NOTES_v1.0.1.md). Existing OTP logic remains unchanged; only versioned JS/CSS markers, asset names and the PHP loader reference differ. General production approval remains withheld.

**As of 2026-11-11: local installation and functional acceptance of the exact published v1.0.0 ZIP PASSED (10/10 blocks, 49/49 checks).** The separate **Nextcloud AIO/PostgreSQL** first-install gate for this published ZIP has **not** been performed. No generic production approval, independent security audit, App Store approval or signing is claimed.

- [Full local acceptance evidence (49/49)](LOCAL_ACCEPTANCE_v1.0.0_2026-11-11.md)
- [Published release identity, SHA256 and protection status](RELEASE_INTEGRITY_v1.0.0.md)
- [Security limits](SECURITY_REVIEW.md) and [compatibility](COMPATIBILITY.md)

## Published source and binary: automated release checks

Results for the **exact source commit** `56d6de06e4825c9bd03b4b07dec5825d64228390`, before the public release:

| Gate | Observed result |
| --- | --- |
| JavaScript unit and integration contracts | **179 / 179 pass** |
| Pinned original Passwords API client integration | **17 / 17 pass** |
| Python package, installer and rollback tests | **66 / 66 pass** |
| npm audit | **0 reported vulnerabilities** at the time of testing |
| Browser JS bundle | `js/app-100.js` syntax pass; two builds byte-identical |
| Package generator | `PACKAGE_PASS` and `BUILD_PASS`; `production_approved=false` |
| Package contents and provenance | All 12 payload files + `BUILD.json`; SHA256 values matched the manifest |
| Repo-to-ZIP identity | 10 tracked source files in the ZIP byte-identical to the tagged commit |
| Licensing | MIT/ISC notices for all 8 locked runtime dependencies; reconstructed `passwords-client` ISC notice identified as such |
| ZIP structure | CRC, duplicate path, traversal, absolute path and symlink checks passed |

**Official ZIP:** `passwords_otp-1.0.0.zip`, **SHA256:** `ffc002d7c41485cac4a4b7eb27659fd5d5dbbd4bd7fd40d78e3ea91373a12256`.

The annotated tag `v1.0.0` points to that exact source commit. Rebuilding from moving `main` cannot be claimed equivalent to the already-published binary. The public release is published, not a draft. **Do not edit, replace, re-upload or republish v1.0.0 assets to update this documentation.**

Additional pre-release evidence for the unchanged PHP/browser runtime included 51 PHP 8.5 security assertions (mocked Nextcloud boundaries), 8/8 synthetic desktop Chromium layouts and a PHP 8.4 contract pass. These tests are separate from the subsequent real browser acceptance; they are not a broad Nextcloud middleware penetration test.

## Live local acceptance of the published v1.0.0 ZIP (2026-11-11)

The operator removed the previous local internal 0.7.3 app, extracted the official v1.0.0 ZIP into an **existing disposable** Docker Compose Nextcloud fixture and activated it **only** for the `otp-v1-pilot` group.

| Environment | Verified |
| --- | --- |
| Nextcloud | `35.0.2.2`; `maintenance=false`; `needsDbUpgrade=false` |
| Passwords | `2026.11.20` unchanged, enabled |
| Companion | `passwords_otp 1.0.0` enabled for `["otp-v1-pilot"]` |
| Local stack | HTTPS `localhost`, Docker Compose, PHP-FPM/nginx and MariaDB |
| Accounts | In-group `ap0-test` and `otp-share-test`; negative `otp-outsider-test` |
| Integrity | Official ZIP checksum, internal `BUILD.json` and all **installed** application files match: `PACKAGE_INTEGRITY_PASS` |
| Manual functional checks | **10 / 10 blocks; 49 / 49 individual checks passed** |
| Server logs | All four relevant Nextcloud log events classified as local failed logins or a duplicate share operation of original Passwords; no `passwords_otp` exception |
| Browser | Final manual reload: no JS errors or HTTP 5xx reported |

The 49 checks cover navigation, OTP UI, an independently calculated RFC 6238 synthetic SHA-1 reference, persistence, sharing/revocation, out-of-group URL rejection, logout/session reuse, Passwords CSE wrong/correct passphrase and encrypted record readback, input validation, double-submit protection, checksums and logs. Full evidence and counting methodology are in [the acceptance report](LOCAL_ACCEPTANCE_v1.0.0_2026-11-11.md).

**What this proves:** the exact published binary worked in the tested, nonproduction local environment. **What it does not prove:** a newly initialized Nextcloud database, an AIO/PostgreSQL first install, an exhaustive security test, every browser or future dependency combination.

## Earlier internal pre-release pilots — not the released v1.0.0 ZIP

An internal AIO/PostgreSQL deployment previously demonstrated earlier OTP behavior, including personal and shared entries. The internal 0.7.3 state was never upgraded in-place to v1.0.0 and remains separate from the 2026-11-11 local Compose acceptance. Earlier tests are useful development evidence but **must not be represented as a production deployment of the officially published ZIP**.

## Remaining release gates and risks

1. **AIO/PostgreSQL:** installation, `aio_install.py --verify`, restore/rollback readiness and in-/out-of-group browser regression must be checked on the **actual AIO target** before such a deployment is approved.
2. **WebUI bearer privilege:** issue [#1](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/1) remains open; the Passwords WebUI token has privileges broader than OTP read/create UI. UI allowlists are not server-side authorization limits.
3. **Appinfo schema:** issue [#2](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/2) tracks missing `<bugs>` metadata for v1.0.1. Do **not** patch the published v1.0.0 ZIP or tag.
4. **Distribution:** source/manual ZIP, unsigned, not in Nextcloud App Store; `production_approved=false` unchanged.
5. **Deployment lifecycle:** the v1.0.0 AIO installer is first-install only; no supported in-place upgrades from internal 0.7.3 or to future releases.
6. **GitHub release integrity:** tag changes/deletion are blocked by a ruleset, but the already-published GitHub release reports `immutable=false`, so **release assets are not protected by GitHub immutable releases**. See [integrity record](RELEASE_INTEGRITY_v1.0.0.md).
7. **Automation:** GitHub Actions workflows are intentionally disabled, and no passing hosted CI status is claimed.

**Status:** **Local functional acceptance = PASS. AIO/PostgreSQL first-install acceptance and general production security approval = OPEN.**
