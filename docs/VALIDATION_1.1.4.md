# Passwords OTP Generator 1.1.4 verification

The [published v1.1.4 release](https://github.com/RamonP12/nextcloud-passwords-otp-extension/releases/tag/v1.1.4)
records the localhost acceptance, disposable SQLite upgrade, automated checks
and reference build toolchain. This record adds the subsequent production AIO
result for the same compiled release.

## Maintainer-confirmed production AIO upgrade (2026-11-20)

**Result: PASS on one existing Nextcloud AIO installation.** The administrator
upgraded `passwords_otp` from 1.1.3 to 1.1.4. The administrator verified the
browser workflows and confirmed deletion of the temporary installation files.

| Item | Verified value |
| --- | --- |
| Nextcloud | 35.0.3 (internal version 35.0.3.2) |
| PHP and persistence | PHP 8.4.28, PostgreSQL, Redis file locking |
| Passwords | 2026.11.20, enabled for all users before and after |
| OTP activation | 1.1.3 → 1.1.4, enabled for all users before and after |
| Release source | `a45e794822b448f170a8daeceed6f97630ffe32c` (`v1.1.4`) |
| Compiled archive | `passwords_otp-1.1.4.tar.gz`, SHA-256 `23667190b1a5b529041acd1351b7e72a42df7f434ef546fbc7064dafb6526720` |

### App-only upgrade procedure

1. Verify `occ status --output=json`, the enabled state and installed versions
   of Passwords and OTP, and the live OTP path with
   `occ app:getpath passwords_otp`. On AIO, run `occ` inside
   `nextcloud-aio-nextcloud` as `www-data`. Record the OTP activation scope
   before proceeding. The procedure below was exercised with `enabled=yes`.
2. Verify the release TAR.GZ against the published SHA-256 and check the
   version and source commit in `BUILD.json`. Stage the single
   `passwords_otp/` directory in a temporary directory on the same persistent
   `custom_apps` volume. Check `appinfo/info.xml`, the compiled `app-114`
   assets and that the candidate files are readable by the container's PHP
   user before changing the live app.
3. Run `occ app:disable passwords_otp` and check that its enabled value is
   `no`. Move the previous app directory into the temporary directory, then
   move the staged 1.1.4 directory to the original app path. Keep the previous
   directory until browser acceptance. If placing the candidate fails, restore
   the previous directory and inspect the app registration before continuing.
4. Check that `occ status --output=json` still reports `maintenance=false`
   and `needsDbUpgrade=false`. Run `occ app:enable passwords_otp` to register
   1.1.4 and restore all-user access. A group-scoped installation needs its
   original group IDs passed to `app:enable --groups` and verified separately.
   Recheck both app versions, activation scope and Nextcloud status. A
   failed registration requires inspection of files, app version and logs
   before retrying or attempting a rollback.
5. Reload OTP in the browser and check vault access, existing personal and
   shared records, code rotation, clipboard and test-entry creation. After
   acceptance, remove the temporary staging and download directories after
   checking that 1.1.4 is active at the expected app path.

Production OCC reported `passwords_otp 1.1.3 disabled`, then
`passwords_otp 1.1.4 enabled` and `OTP_UPGRADE_PASS`. All three status samples
reported `maintenance=false` and `needsDbUpgrade=false`. OTP was briefly
unavailable during the file exchange. A separate disposable 35.0.3.2 fixture
also served Files and Passwords in the same session before, during and after
the OTP-only exchange. The production administrator confirmed that the browser
tests passed and subsequently reported `OTP_CLEANUP_PASS`.

### Scope of acceptance

This confirms one manual upgrade of an existing production installation.
Full-stack AIO first-install tooling and production rollback remain separate
verification tasks. The archive is unsigned for Nextcloud, its manifest carries
`production_approved=false`, and App Store signing is tracked in
[#14](https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues/14).
See the [historical 1.1.3 record](VALIDATION_1.1.3.md) for the prior AIO core
upgrade and manual OTP reactivation.

[Nextcloud 35 OCC app commands](https://docs.nextcloud.com/server/stable/admin_manual/occ_apps.html#apps-commands)
