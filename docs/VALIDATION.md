# Validation status – public source baseline v1.0.0

This page distinguishes **observed results** from unperformed deployment gates. **Automated v1.0.0 release checks passed; a real first-install test of the v1.0.0 package is still pending.** A successful ZIP build is not a production deployment approval, security certification, or Nextcloud App Store signature.

## Final tested v1.0.0 source and binary (10 November 2026)

The following evidence is specific to source commit `56d6de06e4825c9bd03b4b07dec5825d64228390`:

| Check | Observed result |
| --- | --- |
| JavaScript unit and integration contracts | 179 / 179 pass |
| Pinned original Passwords API client integration | 17 / 17 pass |
| Python package/installer/rollback tests | 66 / 66 pass |
| npm audit | 0 reported vulnerabilities at the time of testing |
| Browser JavaScript output | `js/app-100.js` built; syntax check pass; two independent builds byte-identical |
| Packaging | `PACKAGE_PASS` and `BUILD_PASS`; `production_approved=false` |
| Package contents | 12 payload files plus `BUILD.json`; every SHA256 matches the signed-off manifest |
| Repo-to-ZIP identity | All 10 tracked source files in the ZIP byte-identical to the source commit |
| Third-party notices | Full MIT/ISC notices for all eight locked runtime dependencies; seven identical to original package LICENSE files; standard ISC notice for `passwords-client` reconstructed and clearly identified |
| Archive integrity | No duplicate, traversal, absolute-path, or symlink entries; ZIP CRC verification pass |

**Verified v1.0.0 archive:** `passwords_otp-1.0.0.zip`

**SHA256:** `ffc002d7c41485cac4a4b7eb27659fd5d5dbbd4bd7fd40d78e3ea91373a12256`

The ZIP and separate SHA256/BUILD.json were independently inspected after the local build and attached to the GitHub v1.0.0 release draft. The ZIP itself is not committed to this repository.

**Release-tag rule:** Tag `v1.0.0` must identify **exactly** `56d6de06e4825c9bd03b4b07dec5825d64228390`. Subsequent documentation-only commits on `main` do not invalidate the already-tested ZIP and must not silently move the release tag. If any runtime, dependencies, or packaging code changes, rebuild and revalidate a new candidate.

## Earlier internal versions – evidence before re-versioning

The underlying OTP behavior passed the operator's earlier local environment:

| Gate | Observed result |
| --- | --- |
| PHP 8.5 security assertions | 51 pass (framework doubles, not real Nextcloud middleware) |
| Synthetic Chromium desktop layouts | 8 / 8 pass |
| Local install and verification | Successful for the earlier runtime |
| Real browser CSE retry / search-after-create / expiration | Operator confirmed pass |
| Real Nextcloud AIO/PostgreSQL pilot | Installation and personal/shared OTP display reported successful |

The PHP security contract was also reported to pass 51 assertions with PHP 8.4 against unchanged v1.0.0 application PHP files; the host's direct `npm run test:php` invocation could not run because PHP CLI was not installed there.

**Limitations:** The earlier browser and AIO pilot results must not be represented as a fresh installed-system acceptance of the newly packaged v1.0.0 binary. No independently documented live v1.0.0 first-install result, out-of-group negative test, or PostgreSQL/AIO production acceptance is available here. The existing 0.7.3 deployment was not upgraded by this release process.

The operator accepted the residual Passwords WebUI bearer-token privilege risk only for a limited private pilot; issue #1 tracks this architectural limitation. No security certification, generic production approval, or Nextcloud App Store approval is claimed.

## Release preparation complete and acceptance still outstanding

- **Done:** Annotated tag `v1.0.0` points to the exact tested commit, not moving `main`.
- **Done:** The verified ZIP, `.sha256` and matching `BUILD.json` are uploaded to a private GitHub release draft.
- **Done:** GitHub source history and release assets were checked to exclude the previously misidentified tag object; the former repositories remain private.
- **Pending:** Make the clean repository public, immediately enable private vulnerability reporting, secret scanning and push protection, and configure Dependabot alerts/security updates.
- **Pending:** Publish the existing v1.0.0 draft with the comprehensive release notes and checksum.
- **Pending:** Perform a real fresh Nextcloud 35 / Passwords 2026.11.20 first-install and out-of-group negative test before making broad compatibility claims.
- **Pending:** Enable appropriate branch/tag rulesets; status-check enforcement requires a working CI system.
- **Invariant:** A previously running internal 0.7.3 installation has not been upgraded to v1.0.0.

**Current status:** Automated v1.0.0 release checks passed; a real first-install test of the v1.0.0 package is still pending. The verified ZIP is attached to an unpublished release draft; publication and live deployment acceptance remain independent steps. `production_approved=false` is retained.
