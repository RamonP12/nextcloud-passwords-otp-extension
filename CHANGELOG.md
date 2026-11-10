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

**Scope:** A public **source** baseline. Do not treat renaming the proven pilot runtime as an independently tested 1.0.0 binary; build and validate packages before creating a release. Existing pilot 0.7.3 instances require a separately developed and tested upgrade procedure.
