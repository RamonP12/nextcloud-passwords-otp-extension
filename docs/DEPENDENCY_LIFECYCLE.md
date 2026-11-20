# Passwords prerequisite and lifecycle

The unreleased OTP source permits stable Passwords builds **2026.11.20 through
2026.11.29** in the 2026.11 release line. Passwords must be installed, enabled,
and accessible to the current user. The installed version must match the
on-disk manifest. The developer-reviewed upstream package is Passwords
2026.11.0, whose Nextcloud manifest reports 2026.11.20. The upstream version
script prefixes the patch with `2` for the normal distribution. The allowed
range covers its single-digit maintenance patches. Other release lines,
nightlies and LSR variants require a compatibility review. [Upstream version script](https://git.mdns.eu/nextcloud/passwords/-/blob/2026.11.0/scripts/set-version.mjs)

## What happens when Passwords is unavailable

| Situation | Unreleased OTP behavior |
| --- | --- |
| First installation with no recorded migration and Passwords absent, disabled or incompatible | The schema migration rejects registration. Nextcloud may already have extracted the app files. |
| A registered OTP instance opens while Passwords is absent, disabled, incompatible or has an update pending | Initial page state and bootstrap are unavailable. Session status denies continued use. |
| Passwords is removed with or without retained data | The runtime guard detects the missing registration or files on the next request. |
| Passwords is restricted to selected groups | Configured Passwords access is evaluated for the current user. Other users retain their permissions. |
| A compatible Passwords installation returns | Reload OTP to open a fresh vault session. The configured OTP group or all-user scope is preserved. |
| OTP was independently disabled by the administrator or an older OTP release | An administrator must activate it with its intended scope. |
| An existing OTP installation is being upgraded with Passwords unavailable | The migration completes without changing activation. The request-time guard controls access. |

The runtime guard reads the manifest directly from disk because Nextcloud can
cache app metadata by modification time. It requires callable public instance
methods `ApiTokenHelper::getWebUiToken()`, `EnvironmentService::getUserId()`
and `EnvironmentService::isImpersonating()` with no required arguments. The
adapter also checks the user's context and credentials at runtime. A matching
method signature gives a structural check. Upstream behavior, session and CSE
formats still need integration review.

Detection for an already open browser depends on its next session check. An
already copied code is outside the app's control. Read the [security review](SECURITY_REVIEW.md)
for the WebUI token scope and related limits.

## Transition from version 1.1.3

The published v1.1.3 requires exactly Passwords **2026.11.20** and can disable
itself at boot, on lifecycle events or through its scheduled job. The new source
checks the dependency on OTP requests. The old job class retires its own
persisted entry on its next run, or a normal disable removes that entry through
the existing repair step. There are no OTP data tables and the previous
migration record can be retained. If an old migration is already recorded,
the first-registration check may be skipped on reinstall. The runtime guard
still applies after that reinstall.

The AIO 15.1.1 record shows a failed OTP activation before Passwords activation
and a successful manual recovery. Its exact original exception is unavailable.
For systems running the released 1.1.3, follow the historical steps in the
[production upgrade record](VALIDATION_1.1.3.md#production-aio-core-upgrade-and-otp-reactivation).
The version-specific deployment tools use the exact reviewed dependency build
from [the PHP policy](../lib/Service/PasswordsDependency.php). On development
source this is `2026.11.20`, which also defines the runtime maintenance line.
See [deployment boundaries](DEVELOPMENT.md#maintainer-only-local-tools-and-deployment-boundaries).

## Verification and remaining installed-server acceptance

The test plan covers missing dependencies, on-disk version drift, recovery of
existing group scope, explicit OTP disablement, first registration, normal and
keep-data removal, and legacy job retirement. See the [core-component test instructions](../tests/integration/LIFECYCLE.md).
[1.1.3 verification](VALIDATION_1.1.3.md) and [1.1.2 verification](VALIDATION_1.1.2.md)
record the previous behavior of the published packages.

### Lifecycle verification for PR #22

On disposable Nextcloud **35.0.3.2**, PHP **8.4.27**, SQLite and Chromium
**156.0.8078.79**, first registration was rejected with Passwords disabled.
With the released Passwords **2026.11.20** package, the vault loaded and
creation, TOTP and both clipboard actions worked. A Passwords inactivity
duration of 30 seconds locked the vault and removed the codes while the
Nextcloud session was active. Disabling Passwords showed an unavailable vault
and denied session-status requests.
Re-enabling Passwords restored OTP on reload with the original group scope.

The test also changed only the Passwords version metadata while preserving its
file modification time. The mismatch blocked the dependency check. Matching
2026.11.21 metadata restored access. This case simulated a maintenance update
using the released 2026.11.20 code. It verifies the version and recovery logic.

The 20 pinned Nextcloud core-component cases and the 41 compiled-browser
cases passed. The complete `scripts/local.py --build` sequence passed on both
Node **22.22.2** and **24.22.3**, with identical JS/CSS output and verified
ZIP/TAR.GZ packages in each environment. See [PR #22](https://github.com/RamonP12/nextcloud-passwords-otp-extension/pull/22) for these results and [development verification](DEVELOPMENT.md#verification-on-2026-11-20) for the subsequent CI run.

## Primary implementation references

- [Nextcloud 35.0.3 metadata schema](https://github.com/nextcloud/server/blob/v35.0.3/resources/app-info.xsd)
- [Nextcloud metadata cache](https://github.com/nextcloud/server/blob/v35.0.3/lib/private/App/InfoParser.php)
- [Nextcloud app manager](https://github.com/nextcloud/server/blob/v35.0.3/lib/public/App/IAppManager.php)
- [Nextcloud migration step](https://github.com/nextcloud/server/blob/v35.0.3/lib/public/Migration/SimpleMigrationStep.php)
