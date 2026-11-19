# Compatibility and supported scope

## Current source: 1.1.1 Nextcloud Vue edition

Version 1.1.1 adds the maintainer's final wording changes to the locally accepted Vue migration. The [1.1.1 verification record](VALIDATION_VUE_1.1.1.md) separates final release checks, the [1.1.0 migration evidence](VALIDATION_VUE_1.1.0.md), and the maintainer-confirmed localhost acceptance. Historical 1.0.0 results must not be counted as migration test results.

| Component | Current target or declaration | Evidence boundary |
| --- | --- | --- |
| Nextcloud | Major 35; app metadata restricts this major | Real shell, routing, CSP and loading require an installed-server check |
| Nextcloud Passwords | 2026.11.20 | Internal PHP classes and API behavior require version-specific integration tests |
| PHP | Metadata permits 8.3–8.5 | A contract test does not establish every permitted PHP/server combination |
| Browser | Modern browser with ES modules, WebCrypto and clipboard support | Compiled Chromium checks use a synthetic shell/API; real-server and other-browser evidence is separate |
| Frontend | Vue 3.5.45 and @nextcloud/vue 9.14.1 | Dependencies pinned in the lockfile; no runtime CDN |
| Build host | Node.js 22.12+ within 22.x, or 24.x | Node/npm are not required on the installed Nextcloud server |
| Database | No own app tables or schema migration | The database behind Nextcloud/Passwords still needs environment-specific acceptance |
| Installation | Version-matched unsigned ZIP and first-install AIO tool | No supported production AIO in-place upgrade |

The automated 1.1.0 migration work used a disposable **Nextcloud 35.0.2.2 / Passwords 2026.11.20 / PHP 8.4.24 / SQLite** fixture. Separately, the maintainer installed candidate 1.1.0 on **Nextcloud 35.0.2.2 / Passwords 2026.11.20 / PHP 8.5 / MariaDB 11.8** in the existing localhost Docker Compose test environment and confirmed all five requested manual checks. The [1.1.1 record](VALIDATION_VUE_1.1.1.md) explains why the final presentation-only changes do not require repeating those five checks before publication. Neither environment establishes AIO/PostgreSQL compatibility or a production upgrade procedure.

**Newer Nextcloud or Passwords versions are not automatically supported.** In particular, changes to `ApiTokenHelper`, `EnvironmentService`, session behavior or encryption formats require another compatibility review.

## Historical published v1.0.0 evidence

| Component | Recorded evidence | Boundary |
| --- | --- | --- |
| Nextcloud | 35.0.2 / internal 35.0.2.2 | One version family |
| Passwords | 2026.11.20 | Exact upstream integration used at the time |
| PHP | 8.4.27 in an earlier AIO pilot; 8.5.12 in recorded synthetic contracts | These are distinct test contexts |
| Database | MariaDB for the exact public-ZIP localhost acceptance; PostgreSQL only for an earlier internal pilot | The public v1.0.0 ZIP was not accepted on AIO/PostgreSQL by that evidence |
| Browsers | Recorded real localhost Chrome/Firefox functional checks and synthetic Chromium tests | Not exhaustive browser/mobile or accessibility certification |

On **2026-11-11**, the exact public v1.0.0 ZIP passed first app installation into an existing disposable localhost Nextcloud/MariaDB fixture: **10/10 blocks and 49/49 checks**, including group denial, CSE and release-file integrity. The historical ZIP, hashes and source tag are unchanged. See [local acceptance](LOCAL_ACCEPTANCE_v1.0.0_2026-11-11.md), [release integrity/mutability](RELEASE_INTEGRITY_v1.0.0.md) and [historical validation](VALIDATION.md).

## Product and distribution boundaries

The app reads valid personal/shared **TOTP** fields and creates new Passwords entries. Existing entries are edited and shared through the original Passwords app. HOTP is not supported.

The AIO installer refuses existing OTP deployments. Current source tooling accepts **1.1.1** packages; the published **1.0.0** archive requires tooling checked out from `v1.0.0`. See [Installation](INSTALLATION.md).

This migration provides no signed App Store release or automatic update channel. The narrow `<bugs>` metadata correction from PR #5 is included in current metadata; the separate 1.0.1 and App Store/signing work in PR #9 is not merged or published by the conversion.

App text remains German. Language negotiation/catalogues and direct clicking of the displayed code remain issues #6 and #7. Responsive layouts and automated checks improve coverage, but native browser zoom, assistive-technology behavior and complete WCAG conformance require separate evidence.
