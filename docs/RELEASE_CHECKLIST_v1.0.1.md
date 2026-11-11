# v1.0.1 release and verification checklist

**Release status:** source-maintenance candidate. A candidate ZIP produced in an isolated workspace is not a published GitHub release or a production-approved installer.

## Source integrity

- [ ] Exact source commit frozen after all v1.0.1 edits; working checkout clean and tagged only when release is ready.
- [ ] Verify `appinfo/info.xml` with the official [Nextcloud App Store info.xsd](https://raw.githubusercontent.com/nextcloud/appstore/master/nextcloudappstore/api/v1/release/info.xsd). Mandatory `<bugs>` appears between `<category>` and `<repository>`.
- [ ] Check version **1.0.1** in `appinfo/info.xml`, `templates/main.php`, `package.json`, both root values in `package-lock.json`, `scripts/release.py`, `scripts/aio_install.py` and versioned tests.
- [ ] Verify no OTP business-logic changes compared with the v1.0.0 baseline: only JS/CSS asset names, version marker and the PHP loader reference change.
- [ ] Verify npm dependency lock and third-party licence inventory are unchanged except application package version.
- [ ] Ensure GitHub Issue #1 (bearer-token residual risk) remains open; no production approval claimed.

## Automated tests (new commit, not borrowed from v1.0.0)

- [ ] `npm ci` with locked dependencies and Node.js >=22.
- [ ] `npm test` — JavaScript contracts, parser, OTP calculation and transport.
- [ ] `npm run test:client` — real upstream Passwords API client with synthetic fixtures.
- [ ] `python3 -m unittest discover -s tests/python -v` — release, installer, rollback and dev safeguards.
- [ ] `npm run test:php` plus PHP syntax lint on all application and test PHP files.
- [ ] `npm audit --audit-level=high` — note date and results, not assume prior clean audit.
- [ ] `npm run build` twice — generated `js/app-101.js` must match both builds; compare to v1.0.0 `app-100.js` after allowing only the intentional marker replacement.
- [ ] Run synthetic desktop Chromium/Playwright checks; record browser version, PHP and environment when unavailable.
- [ ] Generate package from **exact final source commit** with `scripts/release.py` and record ZIP SHA256 and manifest, including `production_approved=false`.
- [ ] Independently verify all ZIP file hashes, deterministic output, original locked licence notices, no traversal/symlink/extra runtime files.

## Real environment and publication

- [ ] Fresh app installation in disposable **Nextcloud 35 / Passwords 2026.11.20** instance; verify version, group-only enablement, in-group access and out-of-group direct URL denial.
- [ ] Re-test synthetic TOTP reference, shared-entry revocation, logout/session reuse, CSE challenge and encrypted record readback.
- [ ] For **AIO/PostgreSQL** claims, perform independent first-install and `--verify` on the **new exact ZIP** and check backup/rollback readiness; **do not** reuse previous pilot or 1.0.0 evidence.
- [ ] Repository admin: enable [GitHub immutable releases](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/establish-provenance-and-integrity/prevent-release-changes) **before publishing v1.0.1** (tracked by [Issue #3](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/3)).
- [ ] Create protected `v1.0.1` tag from exact tested source commit; upload verified ZIP, SHA256 and BUILD.json **to a draft**; publish only when all release gates have passed.
- [ ] Confirm published release reports `immutable=true`, with matching tag/asset identity, and does not overwrite v1.0.0.

**STOP:** No broad production or App Store approval unless an explicit independent decision is documented. CI currently disabled; do not present omitted hosted CI as passing.
