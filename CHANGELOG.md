# Changelog

All notable changes to the publicly maintained project are documented here. The first public source baseline is **1.0.0**; internal development candidates are not published as supported releases.

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
