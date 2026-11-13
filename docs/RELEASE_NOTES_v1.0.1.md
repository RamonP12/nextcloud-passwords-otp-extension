# v1.0.1 — Nextcloud appinfo schema maintenance

> **UNRELEASED SOURCE CANDIDATE.** This document describes the proposed v1.0.1 maintenance release. It is not evidence that a tagged GitHub release or release ZIP is publicly available, nor approval to install it on a production Nextcloud. The latest published and locally accepted release remains [v1.0.0](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.0.0).

## Changes since v1.0.0

- Fix [issue #2](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/2): add the mandatory `<bugs>` URL to `appinfo/info.xml`, after `<category>` and before `<repository>`, matching the [Nextcloud App Store info.xsd](https://raw.githubusercontent.com/nextcloud/appstore/master/nextcloudappstore/api/v1/release/info.xsd).
- Update `1.0.1` consistently across application metadata, `package.json`, `package-lock.json`, `scripts/release.py`, `scripts/aio_install.py`, UI template's build identity and version-specific tests.
- Move the versioned browser assets to `js/app-101.js` and `css/app-101.css`, updating only the build-marker strings. `PageController.php` now loads `app-101`; the remaining OTP JavaScript/CSS logic and PHP security/business logic are unchanged from v1.0.0. This is a metadata and cache-busting asset hotfix, not an OTP feature change.
- Update package's third-party notice header to identify the new package version. Locked dependency versions and full notices remain unchanged.

## Compatibility and limits

- Target: Nextcloud **35.0.2** (internal 35.0.2.2), original Passwords **2026.11.20**, PHP **8.3–8.5** declared.
- Intended manual/group-restricted **first install only**. Existing published v1.0.0 or internal 0.7.3 installations **must not** be overwritten by the first-install AIO tool. A migration/upgrade procedure is not yet approved.
- No HOTP support and no update/delete operations in the OTP user interface.
- The Passwords WebUI bearer token still has broader server-side privileges than the UI's actions. This [security architecture limitation](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/1) remains unresolved.
- No independent security audit, generic platform compatibility guarantee, signing, App Store listing or general production approval. `production_approved=false` stays mandatory.

## Candidate release gates

See [v1.0.1 release checklist](RELEASE_CHECKLIST_v1.0.1.md).

The previously reported **10/10 browser blocks and 49/49 checks** apply exclusively to the exact v1.0.0 ZIP on local Docker Compose/MariaDB. A new commit, ZIP and checksum must be recorded **after** tests on the final v1.0.1 source. A **fresh real Nextcloud 35 installation** and an **in-group/out-of-group negative test** of the v1.0.1 package are required before claiming live-version acceptance. The separate AIO/PostgreSQL first-install gate also remains open.

**Do not alter, re-sign, retag or overwrite v1.0.0** as part of this maintenance release.
