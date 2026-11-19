# Compatibility and supported scope

## Current published version 1.1.3

[The 1.1.3 release](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.1.3) adds the display name, shield icon and direct clipboard action. See [1.1.3 verification](VALIDATION_1.1.3.md) for checks tied to the published release.

Version 1.1.2 enforces the Passwords dependency and adds an installable TAR alongside the installer ZIP. The [1.1.2 verification record](VALIDATION_1.1.2.md) records the evidence for that version. The [dependency lifecycle](DEPENDENCY_LIFECYCLE.md) documents installation registration, activation, automatic disabling and the limits of event/cron timing. Historical 1.0.0 and 1.1.0 results are not new lifecycle acceptance.

| Component | Current target or declaration | Evidence boundary |
| --- | --- | --- |
| Nextcloud | Major 35, as restricted by app metadata | Nextcloud 35.0.2 upgrade evidence includes MariaDB, SQLite and PostgreSQL. A 35.0.3 fresh install passed on PostgreSQL/Redis. |
| Nextcloud Passwords | **Exactly 2026.11.20**, installed and enabled; installed and on-disk versions must agree | Other versions fail closed until reviewed; internal PHP interfaces remain unsupported upstream coupling |
| PHP | Metadata permits 8.3–8.5 | A contract test does not establish every permitted PHP/server combination |
| Browser | Modern browser with ES modules, WebCrypto and clipboard support | Compiled browser checks use a synthetic shell/API; real-server and other-browser evidence is separate |
| Frontend | Vue 3.5.45 and @nextcloud/vue 9.14.1 | Dependencies pinned in the lockfile; no runtime CDN |
| Build host | Node.js 22.12+ within 22.x, or 24.x | Node/npm are not required on the installed Nextcloud server |
| Database | No own OTP tables; a framework migration checks the install prerequisite and a scheduled job checks dependency state | Migration/job bookkeeping uses Nextcloud facilities; rollback and the underlying database need environment-specific acceptance |
| Installation | Version-matched unsigned TAR and ZIP for manual distribution and version-specific tools | One manual AIO 0.7.3 → 1.1.3 replacement passed. Full-stack AIO first-install tooling, production rollback and signed App Store installation remain open. |

The maintainer upgraded the existing **Nextcloud 35.0.2.2 / PHP 8.5.12 / MariaDB /
Passwords 2026.11.20** fixture from 1.1.2 to 1.1.3. A separate **Nextcloud 35.0.2 /
PHP 8.4.27 / SQLite** fixture passed upgrade and rollback. Isolated PostgreSQL/Redis
tests and the manual production AIO result are recorded in [1.1.3 verification](VALIDATION_1.1.3.md).
The [1.1.2 localhost
record](LOCAL_ACCEPTANCE_v1.1.2_2026-11-19.md) covers the earlier live dependency
disable/re-enable checks. Live tests for missing or incompatible Passwords,
eventless removal and per-user **Passwords** group isolation remain open.

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

The AIO installer refuses existing OTP deployments. Current source tooling accepts **1.1.3** packages. For published versions, use the exact tagged tooling. See [Installation](INSTALLATION.md).

The GitHub release includes a compiled unsigned TAR. App Store signing and an automatic Store update channel remain open. See [App Store packaging](APPSTORE_PACKAGING.md). Declaring and enforcing a Passwords dependency does not make private Passwords integration classes public Nextcloud APIs.

Published 1.1.3 uses German. The [unreleased language support](LOCALIZATION.md) covers German and English selected by browser preference, with separate Nextcloud shell language settings. Responsive layouts and automated checks improve coverage, but native browser zoom, assistive-technology behavior and complete WCAG conformance require separate evidence.
