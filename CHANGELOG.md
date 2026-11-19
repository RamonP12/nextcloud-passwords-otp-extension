# Changelog

All notable changes to the publicly maintained project are documented here. The first public source baseline is **1.0.0**; internal development candidates are not published as supported releases.

## [1.1.3] – Unreleased

- Use **Passwords OTP Generator** in Nextcloud app administration, navigation and the app heading. The shield icon contains a transparent, diagonal key. The app ID remains `passwords_otp`.
- Copy the displayed TOTP code by clicking it or using Enter or Space on the focused code. The separate **Code kopieren** button remains available. Both controls share the same validation and clipboard feedback.

## [1.1.2] – Passwords dependency and tar.gz distribution (2026-11-19)

- Require Passwords **2026.11.20**, installed and enabled, with matching installed/on-disk metadata before accepting the dependency. Other versions fail closed until a compatibility review explicitly adds support.
- Add a public Nextcloud prerequisite migration for new installation registration, activation checking, dependency disable handling and a scheduled fallback. No OTP data tables or record conversions are introduced. Files may already be downloaded before installation registration is rejected.
- Keep per-user/group authorization separate from global dependency failure. Do not globally disable OTP because one user lacks Passwords access. Do not automatically re-enable OTP when Passwords returns.
- Add deterministic single-root `passwords_otp-1.1.2.tar.gz` distribution with the exact verified runtime payload; retain ZIP transport for existing transactional installation tools. Extend archive tests to hostile paths, links, duplicate/hidden payloads and signed-stage changes.
- Add a separate signing workflow with Nextcloud 35 signature-format validation, real cryptographic checks, mandatory Nextcloud certificate-trust verification and detached archive-signature verification. Correct the leading-slash hash-path assumption in draft PR #9. No real release signing key/certificate was provided, and no App Store publication is claimed.
- Align version, `app-112` assets, package inventory and installer checks with 1.1.2, including the new migration/job bookkeeping. Preserve previous public tags/assets and historical evidence.
- Document current component verification and the additional disposable localhost lifecycle acceptance in [1.1.2 verification](docs/VALIDATION_1.1.2.md) and [dependency lifecycle](docs/DEPENDENCY_LIFECYCLE.md). The five accepted Vue checks on 1.1.0 are not proof of the new lifecycle behavior.

Ordinary GitHub artifacts remain unsigned, with `production_approved=false`. GitHub Actions is not used. Dependency enforcement does not convert internal Passwords interfaces into public APIs or resolve the broader WebUI bearer-token scope.

## [1.1.1] – Nextcloud Vue edition (2026-11-19)

- Include the complete Vue migration developed and verified as the internal 1.1.0 candidate below. Version 1.1.0 was not published as a separate GitHub release.
- Clarify that a newly created OTP entry is stored together with the user's other passwords in the Passwords app, which also provides editing, deletion and sharing.
- Remove the bottom **Sicherheit und Bedienung** disclosure from the interface. Session verification, secret clearing, clipboard guards and the documented security boundaries are unchanged.
- Align application metadata, package/lock versions, build markers, generated `app-111` assets, package validation and installer mappings with 1.1.1. Preserve the prior 1.1.0 mapping for local verification and rollback.
- Record the maintainer's successful five-point localhost acceptance of the 1.1.0 Vue candidate separately from the final 1.1.1 regression and package checks. See [1.1.1 verification](docs/VALIDATION_VUE_1.1.1.md).
- Keep the dependency versions and authentication/TOTP/CSE implementation unchanged. No database or stored-record migration is required.

Distribution remains an unsigned, version-matched GitHub ZIP. GitHub Actions was not used; local acceptance does not establish a production AIO/PostgreSQL upgrade path or Nextcloud App Store approval.

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
