# Local acceptance report — Passwords OTP v1.0.0 — 2026-11-11

**Result: PASS — 10/10 test blocks, 49/49 individual checks.** This is a **manual acceptance of the exact published v1.0.0 ZIP installed into a disposable local Nextcloud fixture**, not a generic security certification or production deployment approval.

The operator performed the actual browser, shell and Nextcloud tests and supplied their observations and selected full log excerpts for review. This report records that evidence faithfully; it does not claim that an independent automated browser agent or an external auditor executed the tests. No production Nextcloud instance was changed.

## Exact tested system

| Component | Observed configuration |
| --- | --- |
| Nextcloud | 35.0.2.2 (displayed 35.0.2); installed, maintenance=false, needsDbUpgrade=false |
| Original Passwords app | 2026.11.20, enabled and unchanged |
| OTP companion app | passwords_otp 1.0.0, installed from the official release ZIP |
| Deployment | Local laptop, Docker Compose with nginx / PHP-FPM / MariaDB, HTTPS on localhost |
| App access scope | Nextcloud group `otp-v1-pilot`; configuration value `["otp-v1-pilot"]` |
| Positive test users | `ap0-test` and `otp-share-test` |
| Negative access test user | `otp-outsider-test` (not a group member) |
| Data | Synthetic passwords, synthetic OTP seeds and local test accounts only |

The old private-development 0.7.3 app had been explicitly disabled, removed via `occ` and removed from the local app directory before installing the **official** v1.0.0 ZIP. This was a first installation of v1.0.0 **into an existing Nextcloud test fixture**, **not** a freshly initialized Nextcloud database. This distinction matters when interpreting the result.

## Manual acceptance matrix

| Block | Individual checks actually reported as passed | Result |
| --- | --- | --- |
| 1. Login and initialization | Login as `ap0-test`; navigation visible; app opens without observed PHP/JS failure; OTP list or expected vault challenge loads | **4/4 PASS** |
| 2. Desktop viewer | OTP entries displayed; countdown and code change; search/filter; clipboard copy | **4/4 PASS** |
| 3. Independent TOTP reference | Synthetic reference record created; standalone Python check printed `RFC6238_REFERENCE_PASS`; current six-digit code matches; code in following time window matches | **4/4 PASS** |
| 4. Passwords integration and persistence | Record exists in original Passwords; all entered fields are correct; exactly one record; survives reload; TOTP still matches independent calculation | **5/5 PASS** |
| 5. Sharing | Second user configured; original Passwords share works; shared OTP visible in companion; same code for owner/recipient; unshared owner entries not visible; revocation effective after reload | **6/6 PASS** |
| 6. App group restriction | Out-of-group user configured; original Passwords available; OTP navigation hidden; direct OTP URL denied | **4/4 PASS** |
| 7. Nextcloud session controls | Valid tab return works; logout in second tab succeeds; codes and copy are blocked after logout; new login does not silently unlock old tab; reload/reauthentication restores function | **5/5 PASS** |
| 8. Passwords CSE | CSE enabled on separate test user; master-passphrase challenge appears; wrong passphrase rejected; correct passphrase accepted; encrypted OTP record created and visible in both apps; after new session it decrypts and TOTP matches | **6/6 PASS** |
| 9. Input validation and write safety | Required fields rejected; invalid Base32 rejected; too-short seed rejected; invalid/cancelled forms create no record; rapid double-click creates exactly one record; no edit/delete controls for existing records | **6/6 PASS** |
| 10. Technical final check | Installed files identical to official ZIP; expected Nextcloud and app versions with healthy maintenance state; group-only enablement; no unexplained OTP app server errors; no browser JS errors or HTTP 5xx during final reload | **5/5 PASS** |

**Total: 49/49 checks; no reported failed check.** These are test observations, not a guarantee that all API routes, browsers, races or adversarial security scenarios are covered.

### Cryptographic reference

The operator created a **synthetic** SHA-1 / six-digit / 30-second TOTP record, checked a standalone RFC 6238 Python implementation against the standard eight-digit test vector at epoch 59 (expected `94287082`), and then compared current and next-slot six-digit OTP values against the live app. The tested parameters were SHA-1, 6 digits and 30 seconds; this is **not** a live-browser acceptance of every algorithm or period supported for existing Passwords records.

### Installed-package integrity

- Official `passwords_otp-1.0.0.zip` SHA256: `ffc002d7c41485cac4a4b7eb27659fd5d5dbbd4bd7fd40d78e3ea91373a12256`.
- Exact source commit: `56d6de06e4825c9bd03b4b07dec5825d64228390`.
- The operator ran a read-only verification comparing the official ZIP, its `BUILD.json` manifest, every extracted archive member and every **installed** application file in the running container. Output: `PACKAGE_INTEGRITY_PASS: Offizielles ZIP und alle installierten Dateien identisch`.
- `occ status`: `installed: true`, `version: 35.0.2.2`, `maintenance: false`, `needsDbUpgrade: false`.
- `occ app:list --shipped false`: `passwords: 2026.11.20` and `passwords_otp: 1.0.0` enabled.
- `occ config:app:get passwords_otp enabled`: `["otp-v1-pilot"]`.

See [release integrity record](RELEASE_INTEGRITY_v1.0.0.md) for the immutable source/tag identifiers and the **remaining release-asset mutability** limitation.

## Log analysis and browser results

The operator supplied a read-only extract of the Nextcloud log for 2026-11-11:

- Two level-2 `no app in context` events were failed local logins for `otp-share-test`. They were test account login attempts, not OTP application exceptions.
- One attempted duplicate Passwords share was logged at levels 3 and 4 **for the same request ID**; `Entity already shared with user` came from the **original Passwords** `share/create` API. The two log entries represent **one** rejected request, not two independent failures.
- No `passwords_otp` error was identified among those four Nextcloud warning/error entries.
- The supplied `docker compose logs --since 2h --tail 200 app web` slice showed successful OTP page, bootstrap, session-status and Passwords API requests, including one `POST /password/create` with HTTP 201 in nginx and a corresponding PHP-FPM 201 entry. No HTTP 5xx was observed **in that supplied slice**.
- Repeated Xdebug debugging-client connection notices and a PHP-JIT-disabled warning concern the local development runtime. One nginx HTTP 499 involved a cancelled Passwords favicon request; none of these establishes an OTP implementation failure.
- The operator separately reported **no new JavaScript errors or HTTP 5xx requests** when reloading the OTP page in the browser developer tools.

The Docker command used a `--tail 200` limit, so this does not amount to a complete retrospective audit of all raw container traffic. The initial four log events were evaluated and not considered blockers for this **local functional** acceptance.

## Boundaries and outstanding work

1. **Not a production release authorization.** The published `BUILD.json` retains `production_approved=false`. GitHub distribution is unsigned and outside the Nextcloud App Store.
2. **Upstream token privilege:** The original Passwords WebUI bearer token has broader rights than the OTP UI. Client-side restrictions are not a server-enforced least-privilege boundary; [issue #1](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/1) remains open.
3. **Metadata schema defect:** The v1.0.0 appinfo lacks required `<bugs>`; [issue #2](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/2) tracks a v1.0.1 correction. v1.0.0 assets must not be modified.
4. **Environment boundary:** A live first-install acceptance **of this exact published v1.0.0 ZIP on AIO/PostgreSQL** remains outstanding. The earlier AIO pilot used an internal pre-release and must not be counted as this test.
5. **Additional untested cases:** Natural idle timeout (rather than explicit logout), exhaustive direct API authorization/fuzzing, server-enforced bearer scoping, multi-browser/mobile coverage, all TOTP algorithm/period combinations and real target-device authentication were not part of these 49 checks.
6. **No supported in-place upgrade:** Neither earlier 0.7.3 installations nor an eventual 1.0.1 update can be overwritten with the first-install AIO tool.

## Decision and follow-up

**Accepted for the tested local functionality on the exact environment above.** Keep the v1.0.0 tag and ZIP unchanged. Update active documentation on `main`; develop future changes and releases on separate commits/tags. Before broader deployment, require a separately recorded AIO/PostgreSQL acceptance and explicit review of the known bearer-token risk.

Sources: operator-provided test results, terminal integrity/`occ` outputs, Nextcloud JSON log records and sampled nginx/PHP-FPM logs on 2026-11-11; verified release metadata from GitHub. No production host inspection was performed.
