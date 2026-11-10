# Validation status – public source baseline v1.0.0

This page distinguishes **real measurements** from intended gates. Do not transfer the results of an earlier package to a newly versioned binary.

## Evidence for the underlying OTP runtime (before re-versioning)

The same OTP behavior used as the basis of 1.0.0 passed on the original operator's local checkout:

| Gate | Observed result |
| --- | --- |
| JavaScript unit and integration contracts | 178 / 178 pass |
| Pinned original Passwords API client integration | 17 / 17 pass |
| Python package/installer/rollback tests | 61 / 61 pass |
| PHP 8.5 security assertions | 51 pass |
| Synthetic Chromium desktop layouts | 8 / 8 pass |
| npm audit | 0 reported vulnerabilities |
| Deterministic source package | Build and local preflight pass |
| Local install and verification | Successful |
| Real browser CSE retry / search-after-create / expiration | Operator confirmed pass |
| Real Nextcloud AIO/PostgreSQL pilot | Installation and personal/shared OTP display reported successful |

The operator accepted the residual original Passwords WebUI token privilege risk **for that limited pilot**. The AIO pilot report is not proof of every security scenario or generic production compatibility; the detailed AIO --verify receipt was not independently supplied.

## Gates required before issuing a v1.0.0 binary

- Build and all test suites pass **on the final 1.0.0 commit**, including generated **js/app-100.js** and CSS reference checks.
- Archive is generated from exactly that commit, its SHA256 published, and all licenses/notices shipped.
- A real fresh Nextcloud 35 / Passwords 2026.11.20 first-install is verified or the absence of such a 1.0.0 install is explicitly stated.
- Scope enforcement and out-of-group negative tests are checked on the target.
- An existing 0.7.3 AIO installation is **not** silently represented as upgraded to 1.0.0.

**Current status:** v1.0.0 source tree prepared; commit-specific build and release-binary validation are pending. No general production or App Store approval is claimed.
