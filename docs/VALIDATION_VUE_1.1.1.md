# Nextcloud Vue 1.1.1 — verification and local acceptance

**Date:** 2026-11-19. **Version:** 1.1.1. This record distinguishes the original 1.1.0 migration results, the maintainer's localhost acceptance, and verification of the final 1.1.1 source/package. Results from different source versions and environments are not combined into a single test total.

**Release preparation status:** the application checks below have completed; the clean-source package gate is recorded separately before publication. The intended distribution is an unsigned GitHub ZIP with `production_approved=false`, not an App Store release or general production/AIO approval.

## Changes since the accepted Vue candidate

The reference candidate is commit `ae4469cb61213dde29ea410795bf2a1654d2ed6c` (version 1.1.0).

- Replace the explanation under **Neues OTP Passwort hinzufügen** with the maintainer's exact requested wording:

  > Hier kann ein neuer OTP Eintrag zu deinen Passwörtern hinzugefügt werden. Er wird in der Passwords App zusammen mit deinen anderen Passwörtern gespeichert und kann über die Passwords App auch verwaltet (gelöscht, verändert) und mit anderen Nextcloud Benutzern geteilt werden.

- Remove the complete **Sicherheit und Bedienung** disclosure and its unused styling from the rendered interface.
- Set version 1.1.1 consistently in app/package metadata, build markers, output names, package validation and license inventory. The new assets are `js/app-111.mjs` and `css/app-111.css`.
- Preserve the localhost installer's 1.1.0 asset and `.mjs` mappings so it can verify/back up the existing Vue app and roll back a failed replacement.
- Update current documentation and release records while retaining historical reports and previously published artifacts.

The dependency versions, authentication, Passwords/CSE integration, TOTP calculation, session/clipboard guards and create-once operation are unchanged. Removing the explanatory disclosure changes no security behavior. The app has no separate database-schema migration.

## Maintainer-confirmed localhost acceptance of 1.1.0

The maintainer built the exact reference commit with `scripts/local.py --build`, then ran `--preflight`, `--install` and `--verify`. The shared terminal output records:

| Item | Recorded outcome |
| --- | --- |
| Build | `BUILD_PASS`, exit code 0; two production compilations and checked package |
| Local package | `passwords_otp-1.1.0.zip`; SHA256 `7519fca3fc63037a564407c83d4b541eaa773782645422ff9e793091e4b24a59` |
| Compiled browser suite during preflight | 30 cases passed; synthetic shell/API, not 30 manual live-server tests |
| Existing Nextcloud fixture | `LOCALHOST_PREFLIGHT_PASS` |
| Installation | Verified backup and transaction journal, `INSTALL_PASS: version=1.1.0` |
| Installed file and HTTP asset verification | `HTTP_ASSETS_PASS: app-110`; `LOCALHOST_VERIFY_PASS`; exit code 0 |
| Access scope | Enabled for all users in this test-only environment, explicitly authorized by the maintainer |

Environment: **Nextcloud 35.0.2.2**, **Passwords 2026.11.20**, **MariaDB 11.8**, **PHP 8.5**, existing localhost Docker Compose test installation. Build tools reported **Node.js 24.22.3**, **npm 12.2.3** and **Python 3.14.10**. Exact PHP/browser patch versions were not supplied in this final manual acceptance message. The original Passwords app was retained.

After browser use and the initial screenshots, the maintainer explicitly reported **“prüfungen 1-5 erfolgreich.”** The five requested checks were:

| Manual check | Maintainer-reported result |
| --- | --- |
| Compare TOTP with an independent generator, including a time-window rollover | Passed |
| Copy the code and paste it locally | Passed |
| Search/filter entries and clear the search | Passed |
| Verify the newly created test entry in Passwords and after reloading | Passed |
| Log out in a second tab, return to/focus the OTP tab, and verify codes/copy are blocked | Passed |

This is a maintainer-reported manual acceptance, not a newly generated automated browser trace. It does not independently add a CSE/provider-2FA, screen-reader, Mobile Safari or AIO/PostgreSQL test. User screenshots, credentials, OTP values, raw browser traces and local backup identifiers are not included in this public record.

## Earlier automated migration evidence

[1.1.0 candidate validation](VALIDATION_VUE_1.1.0.md) retains the version-bound automated evidence: unit/client/package/PHP checks, compiled Chromium/Firefox regressions and the actual disposable Nextcloud/Passwords integration. Its original source revision, asset hashes, SQLite fixture, results and limitations remain unchanged. Those results explain the migration coverage; they are not relabelled as fresh tests of 1.1.1.

## Final 1.1.1 verification

These results apply to the 1.1.1 source and compiled asset hashes recorded below. The browser report is bound to the JS/CSS bytes rather than a documentation commit.

| Check | Final 1.1.1 result |
| --- | --- |
| Source/version/asset consistency and review of the requested text changes | Passed; dependency and security/domain code unchanged |
| JavaScript unit and contract tests | **237/237 passed** |
| Actual pinned Passwords client integration | **17/17 passed**; synthetic API responses |
| Python package/installer/rollback contracts | **82/82 passed**; includes both 1.1.0 and 1.1.1 ESM asset verification |
| PHP contracts/syntax and Nextcloud metadata validation | **51/51 assertions, 6/6 syntax files passed** on PHP 8.4.27; official Nextcloud 35 app-info XSD passed |
| Compiled production-bundle browser regressions and final rendered wording | **Firefox 153.0: 30/30 passed**, Playwright 1.62.0; final light-theme screenshot visually reviewed |
| Chromium 156.0.8078.79 rerun | **Environment-blocked before app launch**: local socket creation returned `Operation not permitted`; no Chromium 1.1.1 pass is claimed |
| Locked dependency audit | `npm audit --audit-level=low`: **0 reported vulnerabilities** |
| Two production builds / deterministic ZIP construction | Pending |
| Clean source identity, runtime inventory, notices and package hashes | Pending |

### Final source and artifact identity

The final release archive must be built from the merged commit behind `v1.1.1`. Its self-referential commit/ZIP identity belongs in the published release assets, not in the commit being packaged.

| Item | Identity |
| --- | --- |
| Final source commit / release tag | Exact `source_commit` in the release's `BUILD.json`; tag `v1.1.1` must resolve to that commit |
| `js/app-111.mjs` SHA256 | `9bf219a6bc47b6e6868f7dd0c0e2ef0a70d59cfb60fcf36f5ffeeaf50cb71072` |
| `css/app-111.css` SHA256 | `75f9e35b68d2288378f5eca22cad25f971bb4842df31bd38a15d9bea62c7d3f3` |
| `passwords_otp-1.1.1.zip` SHA256 | Published in `passwords_otp-1.1.1.zip.sha256` and the release notes after final-commit packaging |
| Packaged `BUILD.json` and generated notices | Pending verification |

The source commit is embedded in `BUILD.json`; a different commit changes the archive identity even when runtime bytes are unchanged. Final release assets must match the source identified by the release tag.

### Current browser evidence

- [Firefox 30-case report](validation/vue-1.1.1/browser-firefox.json), bound to the final asset hashes.
- [Reviewed light-theme render](images/vue-1.1.1-light.png), using synthetic test data and shell. The requested full explanation is present and the bottom disclosure is absent.
- The historical Chromium and actual Nextcloud traces remain evidence for 1.1.0; they were not rerun or relabelled as 1.1.1.

The current suite uses the real compiled Vue application, pinned Passwords client, libsodium and browser WebCrypto with synthetic HTTPS API/shell/clipboard fixtures. It checks reflow down to 320 pixels, focus/dialog behavior, lifecycle failures and accessibility assertions. It does not represent a new installed Nextcloud instance or a full WCAG audit.

## Test sufficiency and distribution scope

No additional manual run on the maintainer's localhost is required before this 1.1.1 release, provided the final local gates above pass. The five manual workflows were accepted on the immediately preceding Vue candidate, and the final changes are wording, removal of static help content, versioned assets and associated packaging/installer mappings. The final build/browser/package checks cover the changed surface without claiming another real-server installation of 1.1.1.

After installing 1.1.1, a quick visual check of the revised explanation and absence of the bottom disclosure is useful to confirm the new assets are loaded. This is an update check, not an outstanding functional acceptance requirement. A broader change to authentication, CSE, session timing, OTP generation, upstream software versions or the deployment environment would need corresponding new integration tests.

GitHub Actions is unavailable because the quota is exhausted. No workflow run is required or claimed; the retained workflow is manual-only. The unsigned release and local acceptance do not supply an AIO/PostgreSQL production upgrade path, complete accessibility certification or App Store signing. Existing architectural limits, including the upstream token scope in [issue #1](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/1), remain documented in [Security Policy](../.github/SECURITY.md).
