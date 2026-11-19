# Compatibility and supported scope

## Current source and published baseline

Source on `main` targets 1.1.3 (unreleased). It adds the display name, shield icon and direct clipboard action on top of the published baseline below.

Version 1.1.2 enforces the Passwords dependency and adds an installable TAR alongside the installer ZIP. The [1.1.2 verification record](VALIDATION_1.1.2.md) distinguishes current tests from historical Vue acceptance. The [dependency lifecycle](DEPENDENCY_LIFECYCLE.md) documents installation registration, activation, automatic disabling and the limits of event/cron timing. Historical 1.0.0 and 1.1.0 results are not new lifecycle acceptance.

| Component | Current target or declaration | Evidence boundary |
| --- | --- | --- |
| Nextcloud | Major 35; app metadata restricts this major | One localhost Nextcloud 35/MariaDB upgrade and browser rendering were observed; other hosts, CSP configurations and installations remain untested |
| Nextcloud Passwords | **Exactly 2026.11.20**, installed and enabled; installed and on-disk versions must agree | Other versions fail closed until reviewed; internal PHP interfaces remain unsupported upstream coupling |
| PHP | Metadata permits 8.3–8.5 | A contract test does not establish every permitted PHP/server combination |
| Browser | Modern browser with ES modules, WebCrypto and clipboard support | Compiled browser checks use a synthetic shell/API; real-server and other-browser evidence is separate |
| Frontend | Vue 3.5.45 and @nextcloud/vue 9.14.1 | Dependencies pinned in the lockfile; no runtime CDN |
| Build host | Node.js 22.12+ within 22.x, or 24.x | Node/npm are not required on the installed Nextcloud server |
| Database | No own OTP tables; a framework migration checks the install prerequisite and a scheduled job checks dependency state | Migration/job bookkeeping uses Nextcloud facilities; rollback and the underlying database need environment-specific acceptance |
| Installation | Version-matched unsigned TAR; ZIP retained for transactional localhost and first-install AIO tooling | Localhost 1.1.0 to 1.1.2 upgrade passed; no supported production AIO in-place upgrade or signed Store release |

The automated 1.1.0 migration work used a disposable **Nextcloud 35.0.2.2 / Passwords 2026.11.20 / PHP 8.4.24 / SQLite** fixture. Separately, the maintainer installed candidate 1.1.0 on **Nextcloud 35.0.2.2 / Passwords 2026.11.20 / PHP 8.5 / MariaDB 11.8** in the existing localhost Docker Compose test environment and confirmed five manual functions. The maintainer subsequently **upgraded that localhost instance to 1.1.2** and verified its package contents, backup, updated assets, normal Passwords disable cascade, rejected OTP activation without Passwords, no automatic OTP re-enable, successful explicit recovery and basic OTP functions. See [local 1.1.2 acceptance](LOCAL_ACCEPTANCE_v1.1.2_2026-11-19.md). Fresh install without Passwords, removal/keep-data, group denial and incompatible Passwords versions are still untested on that live fixture. Neither environment establishes AIO/PostgreSQL compatibility or a production upgrade procedure.

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

Version 1.1.2 prepares a correctly structured TAR and a guarded signing workflow but provides no signed App Store release or automatic update channel. See [App Store packaging](APPSTORE_PACKAGING.md). Declaring and enforcing a Passwords dependency does not make private Passwords integration classes public Nextcloud APIs.

App text remains German. Language negotiation and catalogues remain tracked in issue #6. Responsive layouts and automated checks improve coverage, but native browser zoom, assistive-technology behavior and complete WCAG conformance require separate evidence.
