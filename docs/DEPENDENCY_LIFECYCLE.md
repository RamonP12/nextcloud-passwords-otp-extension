# Passwords prerequisite and lifecycle

`passwords_otp` is a companion to `passwords`, not an independent vault. Version
1.1.3 requires **Passwords 2026.11.20**, installed, enabled globally or for configured groups,
and with matching installed/on-disk versions. Each OTP user must additionally
have access to Passwords. Other Passwords versions require a new compatibility
review and an explicit change to the supported-version list.

This requirement reduces the risk of calling unavailable or changed upstream
classes. It does **not** turn Passwords' internal `ApiTokenHelper` or
`EnvironmentService` into public supported APIs, narrow the upstream WebUI
token's privileges, or establish App Store approval. Those boundaries remain in
[Security review](SECURITY_REVIEW.md) and [App Store packaging](APPSTORE_PACKAGING.md).

## Supported behavior

| Operation or condition | OTP behavior |
| --- | --- |
| Fresh installation, Passwords absent/disabled/unreviewed | The public migration callback rejects first registration before `installed_version` is written. No OTP table or schema change is made. |
| Activation through the standard Nextcloud app UI or `occ app:enable` | The registered `AppEnableEvent` listener checks the prerequisite, undoes Nextcloud's enablement write on failure, and reports an error. The CLI shows the prerequisite detail; the app-management UI may show a generic failure. The background check is restored after a valid activation. |
| Passwords globally disabled | `AppDisableEvent` causes OTP to disable itself in the same synchronous event flow. The cascade changes only the OTP app state. |
| Passwords normally removed | The normal remove command disables Passwords first, which invokes the same cascade. |
| Passwords removed with `--keep-data`, manually deleted, or an event is missed | Boot, authenticated OTP requests, and the scheduled dependency check detect the missing prerequisite. Requests fail closed; the check attempts persistent self-disable. |
| Passwords update changes its version, or installed/filesystem versions differ | OTP refuses access and disables itself. Updating Passwords does not implicitly approve a new integration version. |
| Passwords is restricted to groups | Global availability and per-user authorization are checked separately. A denied user receives no OTP credentials; his lack of access never disables OTP globally for other users. |
| Passwords becomes available again | OTP remains disabled until an administrator explicitly enables it. |
| Existing OTP upgrade with an unsatisfied prerequisite | OTP disables itself; its no-schema migration does not deliberately block the whole Nextcloud upgrade. A later enablement is still refused. |
| OTP disabled/uninstalled normally | Its own scheduled check is removed through the uninstall repair step. Re-enabling OTP restores that job. |

The timed job has a **300-second interval**, not a guaranteed five-minute
wall-clock deadline. Execution depends on Nextcloud's configured background-job
scheduler and queue. A request or app boot can detect the problem earlier. No
inactive application can react instantaneously to arbitrary filesystem or
database changes while no PHP process or job is running.

An already displayed code is not remotely erased by a server-side app event.
The existing browser session checks at tab return and before new code windows
remain in place. Existing Passwords records are never deleted by this dependency
handling.

## What Nextcloud can and cannot block

Nextcloud 35's metadata schema has no arbitrary app-to-app dependency element.
Adding a fictitious `<app>passwords</app>` dependency would make `info.xml`
invalid. Version 1.1.2 therefore uses the public PHP migration, app events,
background-job and app-manager interfaces, without patching Nextcloud or Passwords.

The initial proposal to throw from an **install repair step** was corrected
after reading and executing the actual core implementation: `Repair::run()`
catches ordinary exceptions and continues. A repair step is therefore unsuitable
as an installation veto. The new guard runs in
`SimpleMigrationStep::changeSchema()`, because a fresh app installation executes
schema-only migrations and skips the pre/post callbacks. The guard returns
`null` and never invokes the schema closure.

There are unavoidable distinctions:

- Nextcloud can already have downloaded/extracted the app files before the
  migration guard runs. A failed first registration can leave a disabled app
  directory available to the administrator; this is not a pre-download dependency
  resolver.
- A previously executed migration can remain recorded after a keep-data removal
  or a downgrade. It is not a repeating veto of every low-level `installApp`
  invocation. The standard activation listener and runtime checks enforce the
  operational requirement even when that one-time migration is skipped.
- `AppEnableEvent` is dispatched **after** the enablement configuration is
  written. The listener reverses it and raises an error. This is synchronous
  enforcement, not an atomic database constraint or a public before-enable hook.
- Direct database edits, a low-level core call that omits listener registration,
  unavailable config storage, and out-of-process file removal cannot be given
  the same instantaneous guarantee as the supported app UI/CLI flow. The runtime
  guard denies credentials on a failed prerequisite check even if persisting
  the disabled state fails.

## Upgrade and local rollback

Version 1.1.2 introduced a framework migration record and an own scheduled job. It adds
**no OTP data tables** and changes no Passwords schema or stored record.
The localhost deployment tool permits only the two exact reviewed hashes for
the dependency migration and job cleanup in 1.1.2; unknown or modified migration
files still prohibit its file/config-only rollback.

The rollback disables the candidate while its files are still available, so
the uninstall repair can remove its job, then restores the saved previous app.
The harmless Nextcloud migration-history record is retained; there is no direct
SQL deletion or shared-schema rollback. This restricted localhost process does
not establish a production AIO upgrade/downgrade procedure.

## Verification and remaining installed-server acceptance

[1.1.3 verification](VALIDATION_1.1.3.md) records the 1.1.2 → 1.1.3 upgrade
on MariaDB and the independent SQLite upgrade and rollback. It also records
24 cases against pinned Nextcloud core with service doubles.

The [1.1.2 verification record](VALIDATION_1.1.2.md) distinguishes standalone PHP
contracts, tests executing unmodified Nextcloud 35 core classes with isolated
service doubles, synthetic browser tests, and the maintainer's historical live
acceptance. Core component tests are reproducible from pinned upstream source
hashes; see [integration instructions](../tests/integration/README.md).

**Post-release positive-path acceptance:** On 2026-11-19, the maintainer
confirmed 1.1.2 upgrade and rendering on the real localhost fixture; normal
Passwords disable cascaded to OTP; a forbidden OTP re-enable exited with code 1;
Passwords recovery left OTP disabled until explicit successful activation. OTP
account display, changing codes and new test-entry creation also passed. See
[localhost acceptance](LOCAL_ACCEPTANCE_v1.1.2_2026-11-19.md). These are
operator-reported local results, not a fresh cross-platform CI run.

For a new server or full coverage of the remaining negative/destructive cases,
check:

1. Upgrade with Passwords 2026.11.20 enabled, open OTP, compare one TOTP value,
   and confirm the current app version and loaded assets.
2. Disable Passwords and verify that OTP is disabled. Attempt to enable OTP
   while Passwords is disabled: it must fail and remain disabled. Re-enable
   Passwords: OTP must remain disabled until explicitly enabled.
3. In a disposable fixture, test a genuinely fresh OTP install without
   Passwords, normal Passwords removal, and removal with retained data. Verify
   the delayed fallback separately from the normal synchronous event path.
4. With distinct test users, verify that Passwords group exclusion denies only
   the excluded user and leaves OTP available to an authorized user.

The five functional tests previously confirmed on the 1.1.0 Vue candidate remain
valuable historical evidence; the separate 1.1.2 localhost results above now
support the **normal** lifecycle flow. They do not establish fresh installation
without Passwords, removal with retained data, missed events or group isolation.

## Primary implementation references

All core links below are pinned to **Nextcloud v35.0.2**. Private core classes are
read and executed only by the development tests; the shipped dependency logic
uses the public `OCP` APIs.

- [Metadata schema](https://github.com/nextcloud/server/blob/v35.0.2/resources/app-info.xsd)
- [Public app manager](https://github.com/nextcloud/server/blob/v35.0.2/lib/public/App/IAppManager.php)
- [Public app events](https://github.com/nextcloud/server/tree/v35.0.2/lib/public/App/Events)
- [Public migration step](https://github.com/nextcloud/server/blob/v35.0.2/lib/public/Migration/SimpleMigrationStep.php)
- [Installer ordering](https://github.com/nextcloud/server/blob/v35.0.2/lib/private/Installer.php)
- [Migration execution](https://github.com/nextcloud/server/blob/v35.0.2/lib/private/DB/MigrationService.php)
- [Repair exception handling](https://github.com/nextcloud/server/blob/v35.0.2/lib/private/Repair.php)
- [App enable/disable/update behavior](https://github.com/nextcloud/server/blob/v35.0.2/lib/private/App/AppManager.php)
- [CLI removal and `--keep-data`](https://github.com/nextcloud/server/blob/v35.0.2/core/Command/App/Remove.php)
- [App Store rules](https://docs.nextcloud.com/server/stable/developer_manual/app_publishing_maintenance/publishing.html)
