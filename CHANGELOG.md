# Changelog

All notable changes to the publicly maintained project are documented here. The first public source baseline is **1.0.0**; internal development candidates are not published as supported releases.

## [1.1.0] – Vue migration candidate (unreleased)

- Migrate the complete app presentation to Vue 3.5.45 and Nextcloud Vue 9.14.1: application content, vault authentication, search/list, status cards and new-entry dialog.
- Separate application lifecycle and OTP presentation from DOM rendering. Keep the existing domain session, parser, cryptography, Passwords client and create-once policy.
- Preserve mandatory session/window checks, stale-response protection, synchronous clipboard validation, filtered-account denial, input clearing and pagehide/BFCache handling. Add focused regression coverage for the Vue rendering boundary.
- Replace the imperative frontend build with a pinned Vite/official Vue-plugin build producing one ES module and one stylesheet. Keep dependencies local, production devtools disabled and development fixtures outside the runtime.
- Extend package checks to bind actual bundled modules to a reviewed production dependency and original-license inventory; preserve archive, hash, path and provenance checks.
- Rework compiled-browser tests to exercise the actual production application, client/libsodium and WebCrypto with synthetic API responses. Document current live-server integration separately from the historical release.
- Include the missing appinfo `<bugs>` URL identified in PR #5 without merging or publishing its separate 1.0.1 branch.
- Retain first-install-only AIO behavior, version-matched tooling and earlier localhost rollback asset mappings. No production AIO upgrade or signed App Store release is added; PR #9 remains separate.
- Remove automatic GitHub Actions push/PR triggers while quota is exhausted; keep a manual workflow definition for future use. Local evidence is documented in the [migration report](docs/NEXTCLOUD_VUE_MIGRATION.md).

The app's German wording and explicit copy button remain. Full localization (#6) and clicking the code to copy (#7) are separate features. **Published v1.0.0 source, tag, release assets and historical test reports are unchanged.**

## [1.0.0] – initial public source baseline (2026-11-10)

- Independent TOTP viewer for personal and shared Nextcloud Passwords records.
- Local WebCrypto TOTP generation, search, countdown and explicit copy action.
- New Passwords entry creation with OTP custom field and session/authorization safeguards.
- Passwords master-passphrase, compatible CSE and secondary-challenge handling.
- Session verification before new TOTP time windows and on page focus.
- Scoped first-install AIO tool with checksum validation, explicit confirmation, verification and guarded disable/rollback.
- Public project metadata, security policy, development instructions and licensing.

**Compatibility:** Nextcloud 35.0.2, Passwords 2026.11.20; broader versions are unverified.

**Post-release acceptance (2026-11-11):** The **exact published v1.0.0 ZIP** passed installation and functional verification in the maintainer's disposable local Nextcloud 35.0.2.2 / Passwords 2026.11.20 / Docker Compose / MariaDB fixture: **10/10 blocks, 49/49 checks**. See [local acceptance](docs/LOCAL_ACCEPTANCE_v1.0.0_2026-11-11.md). The verified ZIP remains bound to tag `v1.0.0` (source commit `56d6de06e4825c9bd03b4b07dec5825d64228390`); **no tagged code or release asset has been changed**. Fresh published-ZIP AIO/PostgreSQL acceptance remains outstanding. No general production approval is claimed.

**Earlier internal versions:** 0.7.3 was not publicly released. An installation already running an internal candidate requires a separately developed and tested upgrade procedure.
