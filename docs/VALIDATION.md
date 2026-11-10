# Validation status – public source baseline v1.0.0

This page distinguishes **observed results** from unperformed deployment gates. A successful ZIP build is not a production deployment approval, security certification, or Nextcloud App Store signature.

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

The ZIP and separate SHA256/BUILD.json were independently inspected after the local build. The ZIP itself is not committed to this repository; it is intended to be attached as a GitHub release asset.

**Release-tag rule:** Tag `v1.0.0` must identify **exactly** `56d6de06e4825c9bd03b4b07dec5825d64228390`. Subsequent documentation-only commits on `main` do not invalidate the already-tested ZIP and must not silently move the release tag. If any runtime, dependencies, or packaging code changes, rebuild and revalidate a new candidate.

## Earlier runtime and deployment evidence (before re-versioning)

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

## Remaining publication and installation gates

- Create tag `v1.0.0` **on the tested source commit**, not an arbitrary later `main` commit.
- Publish the exact SHA256-verified ZIP, the `.sha256` file and matching `BUILD.json` with clear compatibility and residual-risk notes.
- Enable private vulnerability reporting immediately after the new repository becomes public, and keep the previous development archive private.
- Before making *installation-wide compatibility* claims, perform a real fresh Nextcloud 35 / Passwords 2026.11.20 first-install, inspect access restrictions including out-of-group users, and document the result.
- Never infer that a previously running 0.7.3 installation has been upgraded to v1.0.0.

**Current status:** The source-specific v1.0.0 automated build, ZIP integrity, Git source identity and third-party license review have passed. Publishing the GitHub release and any new live v1.0.0 installation tests are separate outstanding steps. `production_approved=false` is retained.
