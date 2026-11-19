# Passwords dependency lifecycle verification

There are two different levels of evidence. The dependency unit suite uses
framework contract doubles. The component suite below loads unmodified,
hash-pinned Nextcloud **35.0.2** core classes, but still replaces persistence,
metadata parsing, service construction and bootstrap registration. Neither suite
is a running Nextcloud/Passwords installation or a browser acceptance result.

## Reproducible core-component suite

From the repository root, with PHP 8.3–8.5 and Python 3.10 or newer:

```sh
python3 tests/integration/nextcloud_lifecycle.py --fetch-sources
```

The first invocation downloads only the official source files listed in
`nextcloud-35.0.2-sources.json` from the tagged Nextcloud repository. Every size and
SHA-256 digest is checked before PHP loads any code. Later runs need no network:

```sh
python3 tests/integration/nextcloud_lifecycle.py
```

Use `--php /absolute/path/to/php` to select a PHP runtime. `--source-dir` selects
an already downloaded source directory. `--output` defaults to
`.build/lifecycle-core/report.json`. The report binds the result to the PHP
runtime, official source manifest, test files and current application PHP/XML
hashes. A changed or truncated source file fails verification. GitHub Actions is
not required.

The test executes Nextcloud's actual `AppManager`, `Installer`,
`MigrationService`, `Repair`, `ServiceEventListener`, public event and migration
classes, `TimedJob`, and CLI `app:enable` / `app:remove` command implementations.
The fake database records migration execution in memory; it does not test SQL,
transactions or a database server. The fake bootstrap calls this app's real
`Application::register`, but does not exercise Nextcloud's DI container or the
full request bootstrap. Dependency fixtures are synthetic metadata, not the
Passwords application. The test writes only its isolated synthetic metadata
under `.build/`; no real app directory is removed.

### Covered behavior

| Case | Expected outcome |
| --- | --- |
| Fresh installation with no previous migration record; Passwords missing, unregistered, disabled, incompatible or awaiting update | Schema-only migration rejects registration before OTP `installed_version`, migration completion and background jobs are written. Downloaded app files may remain. |
| Valid fresh installation | Registers 1.1.3 and permits activation. |
| Reactivation for all users or a group with invalid dependency | The real core writes the enabled state before dispatching the event; the listener reverses it, clears availability and reports an error. |
| Passwords disabled | Real `AppDisableEvent` handling persistently disables OTP. |
| Passwords limited to a group | A user outside the group is denied Passwords access; OTP remains globally available for authorised users. |
| Normal CLI removal | Core disables Passwords before removing it, causing immediate OTP deactivation. |
| CLI removal with `--keep-data` | Core skips the disable event; OTP is disabled on its next boot or scheduled dependency check. |
| Manual removal of Passwords files | Next boot or scheduled dependency check detects the missing files. |
| 1.1.1 → 1.1.3 upgrade, valid dependency | The real core upgrade completes and retains the enabled state and background job. |
| 1.1.1 → 1.1.3 upgrade, invalid dependency | The Nextcloud upgrade completes with OTP disabled. |
| Passwords upgraded to an unvalidated version | The real core update event disables OTP. |
| Passwords restored later | OTP remains disabled until the administrator activates it. |
| Background check | The actual `TimedJob::start` path invokes dependency enforcement; the configured interval is 300 seconds. |

Three negative controls make the practical limits explicit:

1. A normal install repair exception is caught by Nextcloud's `Repair::run`.
   Consequently, an ordinary repair exception is not an installation veto.
2. A direct public `IAppManager::enableApp` call without registered listeners can
   temporarily set `enabled=yes`; the runtime guard rejects it on the next OTP
   boot. The standard CLI activation path installs/registers the app first and
   is covered separately.
3. If migration history is retained after a previous installation, Nextcloud can
   skip the migration guard and register the app in the disabled state even
   while Passwords is absent. Activation remains blocked by the event/runtime
   checks. This is not a universal pre-download or pre-registration veto.

## Live localhost acceptance still distinct

The core-component result must not be described as a new live acceptance on
the maintainer’s laptop. See the [1.1.3 verification record](../../docs/VALIDATION_1.1.3.md) for live results. Use the following synthetic-account checks for a fresh assignment to a disposable fixture:

1. Normal opening, OTP generation and creation with Passwords 2026.11.20.
2. Disabling Passwords disables OTP; restoring Passwords alone leaves OTP
   disabled; explicit OTP activation then succeeds.
3. OTP activation while Passwords is disabled fails with the prerequisite
   message and leaves OTP disabled.
4. With Passwords restricted to a test group, an outsider cannot bootstrap OTP
   credentials, while a group member can still use the app.
5. In a disposable copy, test first registration without Passwords, ordinary
   removal, removal with `--keep-data`, and recovery. Expect delayed persistent
   deactivation for removal paths that do not emit the core event.

The 300-second background interval is not a wall-clock guarantee: it depends on
Nextcloud's background-job runner executing. Request-time checks protect the OTP
credential path independently. The previously accepted browser/TOTP tests do not
establish these new lifecycle results automatically.

## Primary source references

- [Nextcloud 35.0.2 app manager](https://github.com/nextcloud/server/blob/v35.0.2/lib/private/App/AppManager.php)
- [Nextcloud 35.0.2 installer](https://github.com/nextcloud/server/blob/v35.0.2/lib/private/Installer.php)
- [Nextcloud 35.0.2 migration service](https://github.com/nextcloud/server/blob/v35.0.2/lib/private/DB/MigrationService.php)
- [Nextcloud 35.0.2 repair runner](https://github.com/nextcloud/server/blob/v35.0.2/lib/private/Repair.php)
- [Nextcloud 35.0.2 CLI removal](https://github.com/nextcloud/server/blob/v35.0.2/core/Command/App/Remove.php)

Private core classes are used only to verify the integration in this test.
Application lifecycle code uses public `OCP` interfaces and events. The separate
Passwords authentication adapter still depends on Passwords-internal PHP classes;
declaring and enforcing a dependency does not make those APIs public.
